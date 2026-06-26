"""Programmatic noise generators: white, pink, brown, grey.

All generators write audio in fixed-size chunks to keep RAM use flat regardless
of output duration.  Filter state (IIR delay values) is carried between chunks so
the spectrum is continuous across chunk boundaries.

Amplitude is normalized per-chunk to a target RMS.  Chunks are 30 s = 1.3 M samples,
so RMS variance between chunks is <0.1% — inaudible level drift.
No tanh / hard-clip: those introduce harmonic distortion that makes noise sound static.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import lfilter, lfilter_zi
from tqdm import tqdm

from ..config import CHANNELS, CHUNK_SECONDS, SAMPLE_RATE

# ---------------------------------------------------------------------------
# IIR coefficients for coloured noise
# ---------------------------------------------------------------------------

# Pink noise (1/f) — 3rd-order IIR approximation
_PINK_B = np.array([0.049922035, -0.095993537, 0.050612699, -0.004408786])
_PINK_A = np.array([1.0, -2.494956002, 2.017265875, -0.522189400])

# Brown noise (1/f²) — leaky integrator
# DC gain = 0.02 / (1 - 0.998) = 10 → raw amplitude is huge, hence RMS-normalize not tanh
_BROWN_B = np.array([0.02])
_BROWN_A = np.array([1.0, -0.998])

# Grey noise — psychoacoustic inverse A-weighting approximation
_GREY_B = np.array([1.0, -0.995])
_GREY_A = np.array([1.0, -0.99])

# Target RMS for all output (~-12 dBFS — comfortable listening level)
_TARGET_RMS = 0.25


def _init_zi(b: np.ndarray, a: np.ndarray) -> np.ndarray:
    return lfilter_zi(b, a) * 0.0


def _rms_normalize(signal: np.ndarray, target: float = _TARGET_RMS) -> np.ndarray:
    rms = np.sqrt(np.mean(signal ** 2))
    if rms > 1e-10:
        return signal * (target / rms)
    return signal


class NoiseGenerator:
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        chunk_seconds: int = CHUNK_SECONDS,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_samples = chunk_seconds * sample_rate

    def generate(
        self,
        sound_type: str,
        duration_hours: float,
        output_path: Path | str,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        total_samples = int(duration_hours * 3600 * self.sample_rate)
        state = self._init_state(sound_type)

        with sf.SoundFile(
            output_path, "w", self.sample_rate, self.channels, subtype="PCM_16"
        ) as f:
            with tqdm(
                total=total_samples,
                unit="samples",
                desc=f"Generating {sound_type}",
                leave=False,
            ) as pbar:
                written = 0
                while written < total_samples:
                    n = min(self.chunk_samples, total_samples - written)
                    chunk, state = self._generate_chunk(sound_type, n, state)
                    f.write(chunk)
                    written += n
                    pbar.update(n)

        return output_path

    def _init_state(self, sound_type: str) -> dict[str, Any]:
        if sound_type == "white":
            return {}
        if sound_type == "pink":
            return {"zi": [_init_zi(_PINK_B, _PINK_A) for _ in range(self.channels)]}
        if sound_type == "brown":
            return {"zi": [_init_zi(_BROWN_B, _BROWN_A) for _ in range(self.channels)]}
        if sound_type == "grey":
            return {"zi": [_init_zi(_GREY_B, _GREY_A) for _ in range(self.channels)]}
        raise ValueError(f"Unknown noise type: {sound_type!r}")

    def _generate_chunk(
        self, sound_type: str, n: int, state: dict[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        if sound_type == "white":
            # White noise: Gaussian with target std directly — no filtering needed
            chunk = np.random.normal(0.0, _TARGET_RMS, (n, self.channels)).astype(np.float32)
            return chunk, state

        dispatch = {
            "pink":  (_PINK_B,  _PINK_A),
            "brown": (_BROWN_B, _BROWN_A),
            "grey":  (_GREY_B,  _GREY_A),
        }
        b, a = dispatch[sound_type]

        channels_out = []
        new_zi = []
        for ch in range(self.channels):
            white = np.random.normal(0.0, 1.0, n)
            out, zo = lfilter(b, a, white, zi=state["zi"][ch])
            new_zi.append(zo)
            # RMS-normalize: no gain fudging, no tanh, no distortion
            channels_out.append(_rms_normalize(out))

        state["zi"] = new_zi
        chunk = np.stack(channels_out, axis=1).astype(np.float32)
        # Safety hard-clip (should never trigger after RMS-normalize, but guards against
        # transient spikes at filter startup on the very first chunk)
        np.clip(chunk, -1.0, 1.0, out=chunk)
        return chunk, state

"""Nature sound generator.

Two strategies:
1. Synthesis  — rain/thunder built from filtered noise (zero assets needed).
2. Sample-based — forest, ocean, café, fireplace loaded from data/audio_samples/<type>/
   and looped/mixed to fill the target duration.

Both strategies write audio in chunks to keep RAM flat for long videos.

Rain synthesis: bandpass-filtered white noise (150 Hz – 9 kHz) with a slow-varying
amplitude envelope (natural intensity changes, not jarring 0.25s steps).
No tanh / hard-clip saturation — all normalization is RMS-based.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter, lfilter_zi
from tqdm import tqdm

from ..config import CHANNELS, CHUNK_SECONDS, NATURE_SAMPLE_RATE

# ---------------------------------------------------------------------------
# Rain bandpass filter — computed at import time from exact scipy coefficients
# ---------------------------------------------------------------------------
# 150 Hz – 9 kHz bandpass, 4th-order Butterworth
_RAIN_B, _RAIN_A = butter(4, [150, 9000], btype="bandpass", fs=NATURE_SAMPLE_RATE)

# Target RMS levels
_RAIN_RMS = 0.30    # rain background
_SAMPLE_RMS = 0.30  # sample-based nature sounds


def _rms_normalize(signal: np.ndarray, target: float) -> np.ndarray:
    rms = np.sqrt(np.mean(signal ** 2))
    if rms > 1e-10:
        return signal * (target / rms)
    return signal


class NatureGenerator:
    def __init__(
        self,
        sample_rate: int = NATURE_SAMPLE_RATE,
        channels: int = CHANNELS,
        chunk_seconds: int = CHUNK_SECONDS,
        samples_dir: Path | str = "data/audio_samples",
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_samples = chunk_seconds * sample_rate
        self.samples_dir = Path(samples_dir)

    SYNTHESIZED = {"rain", "thunder"}
    SAMPLE_BASED = {"forest", "ocean", "stream", "fireplace", "cafe"}

    def generate(
        self,
        sound_type: str,
        duration_hours: float,
        output_path: Path | str,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if sound_type in self.SYNTHESIZED:
            return self._generate_synthesized(sound_type, duration_hours, output_path)
        if sound_type in self.SAMPLE_BASED:
            return self._generate_sample_based(sound_type, duration_hours, output_path)
        raise ValueError(f"Unknown nature sound type: {sound_type!r}")

    # ------------------------------------------------------------------
    # Synthesized rain / thunder
    # ------------------------------------------------------------------

    def _generate_synthesized(
        self, sound_type: str, duration_hours: float, output_path: Path
    ) -> Path:
        total_samples = int(duration_hours * 3600 * self.sample_rate)
        state: dict[str, Any] = {
            "zi": [lfilter_zi(_RAIN_B, _RAIN_A) * 0.0 for _ in range(self.channels)],
            # Smooth slow envelope: target amplitude and remaining samples at that target
            "env_level": [0.6] * self.channels,
            "env_remaining": [0] * self.channels,
        }

        with sf.SoundFile(output_path, "w", self.sample_rate, self.channels, "PCM_16") as f:
            with tqdm(total=total_samples, unit="samples", desc=f"Generating {sound_type}", leave=False) as pbar:
                written = 0
                while written < total_samples:
                    n = min(self.chunk_samples, total_samples - written)
                    chunk, state = self._rain_chunk(n, state, include_thunder=(sound_type == "thunder"))
                    f.write(chunk)
                    written += n
                    pbar.update(n)

        return output_path

    def _rain_chunk(
        self, n: int, state: dict[str, Any], include_thunder: bool
    ) -> tuple[np.ndarray, dict[str, Any]]:
        channels_out = []
        new_zi = []

        for ch in range(self.channels):
            white = np.random.normal(0.0, 1.0, n)

            # Smooth amplitude envelope — long, gentle swells like changing rain intensity.
            # Uses a step-wise constant level that changes every 5–25 seconds.
            envelope = np.empty(n)
            i = 0
            level = state["env_level"][ch]
            remaining = state["env_remaining"][ch]
            while i < n:
                if remaining <= 0:
                    # New target level for this swell segment
                    level = random.uniform(0.45, 0.90)
                    remaining = random.randint(
                        self.sample_rate * 5, self.sample_rate * 25
                    )
                seg = min(remaining, n - i)
                envelope[i:i + seg] = level
                remaining -= seg
                i += seg
            state["env_level"][ch] = level
            state["env_remaining"][ch] = remaining

            # Smooth envelope edges to avoid amplitude clicks between chunks
            fade = min(256, n // 4)
            ramp = np.linspace(0, 1, fade)
            envelope[:fade] = envelope[fade] * ramp + envelope[0] * (1 - ramp)

            modulated = white * envelope

            # Bandpass filter: shapes white noise into rain-like hiss
            out, zo = lfilter(_RAIN_B, _RAIN_A, modulated, zi=state["zi"][ch])
            new_zi.append(zo)

            # Thunder: occasional low-frequency rumble (40 Hz decaying sine)
            if include_thunder and random.random() < (n / (self.sample_rate * 180)):
                t_pos = random.randint(0, max(0, n - self.sample_rate * 2))
                t_len = min(self.sample_rate * 2, n - t_pos)
                t = np.linspace(0, t_len / self.sample_rate, t_len)
                # Rumble: decaying sine + low-frequency noise for realism
                rumble = (
                    np.sin(2 * np.pi * 40 * t) * np.exp(-t * 1.5) * 0.5
                    + np.sin(2 * np.pi * 70 * t) * np.exp(-t * 2.0) * 0.2
                )
                out[t_pos:t_pos + t_len] += rumble

            # RMS-normalize the chunk — no tanh, no distortion
            out = _rms_normalize(out, _RAIN_RMS)
            channels_out.append(np.clip(out, -1.0, 1.0).astype(np.float32))

        state["zi"] = new_zi
        chunk = np.stack(channels_out, axis=1)
        return chunk, state

    # ------------------------------------------------------------------
    # Sample-based sounds (forest, ocean, fireplace, café)
    # ------------------------------------------------------------------

    def _generate_sample_based(
        self, sound_type: str, duration_hours: float, output_path: Path
    ) -> Path:
        sample_files = self._find_samples(sound_type)

        if not sample_files:
            raise FileNotFoundError(
                f"No audio samples found in {self.samples_dir / sound_type}.\n"
                f"Download royalty-free WAV files from freesound.org and place them there."
            )

        total_samples = int(duration_hours * 3600 * self.sample_rate)

        with sf.SoundFile(output_path, "w", self.sample_rate, self.channels, "PCM_16") as out_f:
            with tqdm(total=total_samples, unit="samples", desc=f"Assembling {sound_type}", leave=False) as pbar:
                written = 0
                sample_queue = list(sample_files)
                random.shuffle(sample_queue)
                queue_idx = 0

                while written < total_samples:
                    sample_path = sample_queue[queue_idx % len(sample_queue)]
                    queue_idx += 1

                    chunk_data = self._load_and_resample(sample_path)
                    remaining = total_samples - written
                    chunk_data = chunk_data[:remaining]

                    # Normalize each sample file to consistent RMS
                    for ch in range(chunk_data.shape[1]):
                        chunk_data[:, ch] = _rms_normalize(chunk_data[:, ch], _SAMPLE_RMS)

                    out_f.write(np.clip(chunk_data, -1.0, 1.0))
                    written += len(chunk_data)
                    pbar.update(len(chunk_data))

        return output_path

    def _find_samples(self, sound_type: str) -> list[Path]:
        folder = self.samples_dir / sound_type
        if not folder.exists():
            return []
        return [p for p in folder.iterdir() if p.suffix.lower() in {".wav", ".flac", ".ogg"}]

    def _load_and_resample(self, path: Path) -> np.ndarray:
        data, sr = sf.read(path, dtype="float32", always_2d=True)

        if data.shape[1] == 1:
            data = np.repeat(data, self.channels, axis=1)
        elif data.shape[1] > self.channels:
            data = data[:, : self.channels]

        if sr != self.sample_rate:
            ratio = self.sample_rate / sr
            new_len = int(len(data) * ratio)
            indices = np.linspace(0, len(data) - 1, new_len)
            data = np.stack(
                [np.interp(indices, np.arange(len(data)), data[:, ch]) for ch in range(data.shape[1])],
                axis=1,
            ).astype(np.float32)

        return data

"""Kokoro-ONNX TTS voiceover generator — free, fully offline after first run.

Model files (~86 MB) are downloaded once to data/models/ on first use.
Default voice: bm_george (British male, documentary/BBC style).
Override with KOKORO_VOICE in .env.
"""

from __future__ import annotations

import subprocess
import urllib.request
import wave
from pathlib import Path

import numpy as np

from .config import DATA_DIR, FFMPEG_PATH, KOKORO_VOICE

_MODELS_DIR = DATA_DIR / "models"
_MODEL_FILE = _MODELS_DIR / "kokoro-v0_19.onnx"
_VOICES_FILE = _MODELS_DIR / "voices.bin"

_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"


def _download(url: str, dest: Path) -> None:
    print(f"  Downloading {dest.name} (one-time setup)...")
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    print(f"  Downloaded {dest.name} ({dest.stat().st_size // 1024 // 1024} MB)")


def _ensure_models() -> None:
    if not _MODEL_FILE.exists():
        _download(_MODEL_URL, _MODEL_FILE)
    if not _VOICES_FILE.exists():
        _download(_VOICES_URL, _VOICES_FILE)


def _save_wav(samples: np.ndarray, sample_rate: int, path: Path) -> None:
    samples_int16 = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(samples_int16.tobytes())


def generate(narration: str, output_path: Path) -> Path:
    """Convert narration text to MP3 at output_path. Returns output_path."""
    _ensure_models()

    from kokoro_onnx import Kokoro  # lazy import — model load is slow

    print(f"  Loading Kokoro model...")
    kokoro = Kokoro(str(_MODEL_FILE), str(_VOICES_FILE))

    # Split into paragraphs to avoid max phoneme length limits
    paragraphs = [p.strip() for p in narration.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [narration]

    all_samples: list[np.ndarray] = []
    total = len(paragraphs)

    print(f"  Synthesising {total} paragraph(s) with voice '{KOKORO_VOICE}'...")
    for i, para in enumerate(paragraphs, 1):
        print(f"  Paragraph {i}/{total}...", end="\r")
        samples, sample_rate = kokoro.create(para, voice=KOKORO_VOICE, speed=0.92, lang="en-us")
        all_samples.append(samples)
        # Small silence between paragraphs (0.4 s)
        silence = np.zeros(int(sample_rate * 0.4), dtype=np.float32)
        all_samples.append(silence)

    combined = np.concatenate(all_samples)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path = output_path.with_suffix(".wav")
    _save_wav(combined, sample_rate, wav_path)

    # Convert WAV → MP3 via FFmpeg
    subprocess.run(
        [FFMPEG_PATH, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-qscale:a", "2", str(output_path)],
        check=True, capture_output=True,
    )
    wav_path.unlink(missing_ok=True)

    print(f"\n  Narration saved: {output_path}")
    return output_path

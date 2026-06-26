"""FFmpeg video renderer.

Combines a background (static image or looping footage clip) with an audio file
to produce a YouTube-ready MP4.  Deletes the source audio file after rendering
to reclaim disk space.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _ffmpeg(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["ffmpeg", "-y", *args]
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


class VideoRenderer:
    def __init__(self, crf: int = 23, audio_bitrate: str = "192k") -> None:
        self.crf = crf
        self.audio_bitrate = audio_bitrate

    def render(
        self,
        audio_path: Path,
        background: dict,
        output_path: Path,
        delete_audio_after: bool = True,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mode = background["mode"]
        bg_path = background["path"]

        if mode == "image":
            self._render_from_image(audio_path, bg_path, output_path)
        elif mode == "video":
            self._render_from_footage(audio_path, bg_path, output_path)
        else:
            raise ValueError(f"Unknown background mode: {mode!r}")

        if delete_audio_after:
            for attempt in range(5):
                try:
                    if audio_path.exists():
                        audio_path.unlink()
                        print(f"    Deleted local WAV: {audio_path.name}")
                    break
                except Exception as e:
                    if attempt < 4:
                        import time as _t; _t.sleep(2)
                    else:
                        print(f"    Warning: could not delete WAV {audio_path.name}: {e}")

        return output_path

    # ------------------------------------------------------------------
    # Static image background
    # ------------------------------------------------------------------

    def _render_from_image(self, audio: Path, image: Path, out: Path) -> None:
        # ultrafast + stillimage tune: encodes a 8h video in ~5 min, file still tiny
        # because inter-frame compression skips duplicate frames regardless of preset.
        # crf=18 keeps the background crisp (no macroblocking on dark areas).
        result = _ffmpeg(
            "-loop", "1",
            "-i", str(image),
            "-i", str(audio),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-preset", "ultrafast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", self.audio_bitrate,
            "-shortest",
            str(out),
            check=False,
        )
        if result.returncode != 0:
            print(result.stderr[-3000:], file=sys.stderr)
            raise RuntimeError(f"FFmpeg failed rendering image background. See stderr above.")

    # ------------------------------------------------------------------
    # Looping footage background
    # ------------------------------------------------------------------

    def _render_from_footage(self, audio: Path, footage: Path, out: Path) -> None:
        # 720p is fine for ambient channels — halves bitrate vs 1080p.
        # Hard cap at 2 Mbps video so even 8h rain footage stays under ~8 GB.
        result = _ffmpeg(
            "-stream_loop", "-1",
            "-i", str(footage),
            "-i", str(audio),
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                   "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", str(self.crf),
            "-maxrate", "2000k",
            "-bufsize", "4000k",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", self.audio_bitrate,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(out),
            check=False,
        )
        if result.returncode != 0:
            print(result.stderr[-3000:], file=sys.stderr)
            raise RuntimeError(f"FFmpeg failed rendering footage background. See stderr above.")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def ffmpeg_available() -> bool:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

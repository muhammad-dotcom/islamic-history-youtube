"""FFmpeg video assembler.

Accepts a list of visual paths (MP4 clips from Higgsfield OR JPEG images)
and a narration MP3. Produces a final 1080p MP4 with:
  - Visuals timed to narration length (images get Ken Burns zoom/pan)
  - Narration audio only — no background music (halal: no instruments)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .config import FFMPEG_PATH, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH

_FFPROBE = FFMPEG_PATH.replace("ffmpeg.exe", "ffprobe.exe")


def _ffprobe_duration(path: Path) -> float:
    """Return duration in seconds via ffprobe."""
    result = subprocess.run(
        [
            _FFPROBE, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _ken_burns_clip(image_path: Path, duration: float, out_path: Path) -> None:
    """Render a single image as a Ken Burns clip (slow zoom in)."""
    # zoompan: zoom from 1.0 → 1.3 over the clip duration
    total_frames = int(duration * VIDEO_FPS)
    zoom_expr = f"min(zoom+{0.3 / total_frames:.6f},1.3)"
    vf = (
        f"scale=8000:-1,"
        f"zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS},"
        f"setpts=PTS-STARTPTS"
    )
    subprocess.run(
        [
            FFMPEG_PATH, "-y",
            "-loop", "1", "-i", str(image_path),
            "-vf", vf,
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            str(out_path),
        ],
        check=True, capture_output=True,
    )


def _scale_video_clip(clip_path: Path, out_path: Path) -> None:
    """Scale an existing video clip to 1080p with padding."""
    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
    )
    subprocess.run(
        [
            FFMPEG_PATH, "-y", "-i", str(clip_path),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an",  # strip audio from visual clips
            str(out_path),
        ],
        check=True, capture_output=True,
    )


def assemble(
    visuals: list[Path],
    narration: Path,
    output_path: Path,
    staging_dir: Path,
) -> Path:
    """Assemble final video. Returns output_path."""
    narration_duration = _ffprobe_duration(narration)
    clip_duration = narration_duration / len(visuals)

    # Step 1: render each visual as a fixed-duration 1080p clip
    clip_paths: list[Path] = []
    for i, visual in enumerate(visuals):
        clip_out = staging_dir / f"clip_{i:02d}.mp4"
        print(f"  Rendering clip {i+1}/{len(visuals)}...")
        if visual.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            _ken_burns_clip(visual, clip_duration, clip_out)
        else:
            _scale_video_clip(visual, clip_out)
        clip_paths.append(clip_out)

    # Step 2: concatenate clips
    concat_list = staging_dir / "concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in clip_paths),
        encoding="utf-8",
    )
    combined_video = staging_dir / "combined.mp4"
    subprocess.run(
        [
            FFMPEG_PATH, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy",
            str(combined_video),
        ],
        check=True, capture_output=True,
    )

    # Step 3: narration only — no background music (halal)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            FFMPEG_PATH, "-y",
            "-i", str(combined_video),
            "-i", str(narration),
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(output_path),
        ],
        check=True, capture_output=True,
        )

    print(f"  Video assembled: {output_path}")
    return output_path

"""Main CLI entry point for the YouTube Ambient pipeline.

Examples
--------
# Quick test — generate 6 minutes of brown noise, no upload
python scripts/run_pipeline.py --type brown --duration 0.1 --no-upload

# Generate 1-hour study + 8-hour sleep brown noise and upload both
python scripts/run_pipeline.py --type brown --duration both

# Let the planner decide what's next (fully automated mode)
python scripts/run_pipeline.py --auto

# Upload as unlisted (safe for testing)
python scripts/run_pipeline.py --type rain --duration 0.1 --privacy unlisted
"""

import sys
from pathlib import Path

# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import click

from yt_ambient.pipeline import Pipeline
from yt_ambient.video.renderer import VideoRenderer


@click.command()
@click.option(
    "--type", "sound_type",
    default=None,
    type=click.Choice([
        "white", "pink", "brown", "grey",
        "rain", "thunder", "forest", "ocean", "stream", "fireplace", "cafe",
    ]),
    help="Sound type to generate. Omit to let the planner decide.",
)
@click.option(
    "--duration",
    default=None,
    help='Duration in hours, or "both" for 1h + 8h pair.',
)
@click.option(
    "--auto",
    is_flag=True,
    default=False,
    help="Ignore --type/--duration and run the next planned slot.",
)
@click.option(
    "--upload/--no-upload",
    default=True,
    help="Upload to YouTube after rendering (default: upload).",
)
@click.option(
    "--privacy",
    default="public",
    type=click.Choice(["public", "unlisted", "private"]),
    help="YouTube privacy status (default: public).",
)
@click.option(
    "--output-dir",
    default=None,
    help="Override output directory for generated files.",
)
def main(sound_type, duration, auto, upload, privacy, output_dir):
    # Check FFmpeg is available before doing any work
    if not VideoRenderer.ffmpeg_available():
        click.echo(
            "ERROR: FFmpeg not found. Install it and make sure it's on PATH.\n"
            "  Windows: winget install ffmpeg\n"
            "  Or download from: https://ffmpeg.org/download.html",
            err=True,
        )
        sys.exit(1)

    pipeline = Pipeline(
        output_dir=output_dir or "output",
        privacy=privacy,
    )

    if auto:
        sound_type = None
        duration_hours = None
        pipeline.run(sound_type=None, duration_hours=None, upload=upload)
        return

    # Parse duration
    if duration == "both":
        # Run 1h then 8h for the same sound type
        for dur in [1.0, 8.0]:
            pipeline.run(
                sound_type=sound_type,
                duration_hours=dur,
                upload=upload,
            )
        return

    duration_hours = float(duration) if duration else None
    pipeline.run(
        sound_type=sound_type,
        duration_hours=duration_hours,
        upload=upload,
    )


if __name__ == "__main__":
    main()

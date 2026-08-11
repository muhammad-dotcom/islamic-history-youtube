"""CLI entry point for the YouTube Shorts pipeline.

Examples
--------
# Let the planner decide what's next (fully automated mode)
python scripts/run_shorts.py --auto

# Quick local test — waveform-visual type, no upload
python scripts/run_shorts.py --type brown --no-upload

# Footage-visual type, no upload
python scripts/run_shorts.py --type rain --no-upload

# Upload as unlisted (safe for testing)
python scripts/run_shorts.py --type rain --privacy unlisted
"""

import sys
from pathlib import Path

# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import click

from yt_ambient.shorts.pipeline import DEFAULT_DURATION_SECONDS, ShortsPipeline
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
    "--auto",
    is_flag=True,
    default=False,
    help="Ignore --type and run the next planned slot.",
)
@click.option(
    "--duration",
    default=DEFAULT_DURATION_SECONDS,
    type=float,
    help="Clip duration in seconds (default: 30).",
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
def main(sound_type, auto, duration, upload, privacy, output_dir):
    if not VideoRenderer.ffmpeg_available():
        click.echo(
            "ERROR: FFmpeg not found. Install it and make sure it's on PATH.\n"
            "  Windows: winget install ffmpeg\n"
            "  Or download from: https://ffmpeg.org/download.html",
            err=True,
        )
        sys.exit(1)

    pipeline = ShortsPipeline(
        output_dir=output_dir or "output",
        duration_seconds=duration,
        privacy=privacy,
    )

    pipeline.run(sound_type=None if auto else sound_type, upload=upload)


if __name__ == "__main__":
    main()

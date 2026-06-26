#!/usr/bin/env python
"""CLI entry point — run one full pipeline cycle.

Examples:
  python scripts/run_pipeline.py                          # auto topic, upload
  python scripts/run_pipeline.py --dry-run                # no upload, keep video
  python scripts/run_pipeline.py --topic "Saladin"        # force topic
  python scripts/run_pipeline.py --privacy unlisted       # unlisted upload
  python scripts/run_pipeline.py --list                   # show upload history
"""

import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import click

from yt_history import pipeline, tracker


@click.command()
@click.option("--topic", default=None, help="Force a specific topic instead of next in queue")
@click.option("--dry-run", is_flag=True, help="Generate video but skip YouTube upload")
@click.option("--privacy", default="public", type=click.Choice(["public", "unlisted", "private"]))
@click.option("--list", "show_list", is_flag=True, help="Show upload history and exit")
def main(topic, dry_run, privacy, show_list):
    if show_list:
        uploads = tracker.list_uploads()
        if not uploads:
            click.echo("No uploads yet.")
            return
        for u in uploads:
            vid = u["video_id"] or "dry-run"
            click.echo(f"{u['uploaded_at'][:10]}  {vid}  {u['topic']}")
        return

    try:
        result = pipeline.run(
            topic_override=topic,
            dry_run=dry_run,
            privacy=privacy,
        )
        click.echo(f"\nSuccess: {result.get('url') or result['title']}")
    except Exception as e:
        click.echo(f"\nPipeline failed: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

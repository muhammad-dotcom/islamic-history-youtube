"""Main pipeline orchestrator.

Run order:
  1. Pick next topic from queue
  2. Generate documentary script (Claude Sonnet)
  3. Generate voiceover (ElevenLabs)
  4. Generate visuals (Higgsfield or DALL-E 3)
  5. Assemble video (FFmpeg)
  6. Generate YouTube metadata (Claude Haiku)
  7. Upload to YouTube
  8. Log to SQLite, mark topic done, clean staging files
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from . import assembler, metadata, script_gen, topics, tracker, visual_gen, voice_gen
from .config import OUTPUT_DIR, STAGING_DIR
from .uploader import YouTubeUploader


def run(
    topic_override: str | None = None,
    dry_run: bool = False,
    privacy: str = "public",
) -> dict:
    """Run one full pipeline cycle. Returns result dict."""
    start = time.time()

    # 1. Topic
    topic = topic_override or topics.next_topic()
    print(f"\n{'='*60}")
    print(f"Topic: {topic}")
    print(f"{'='*60}")

    if tracker.already_uploaded(topic) and not topic_override:
        topics.mark_done(topic)
        raise RuntimeError(f"Topic already uploaded: {topic!r}")

    # 2. Script
    print("\n[1/6] Generating script...")
    script = script_gen.generate(topic)
    narration_text = script["narration"]
    image_prompts = script["image_prompts"]
    hook = script["hook"]
    word_count = len(narration_text.split())
    print(f"  Script: {word_count} words, {len(image_prompts)} image prompts")

    # Staging dir for this job
    safe_name = "".join(c if c.isalnum() else "_" for c in topic)[:40]
    staging = STAGING_DIR / safe_name
    staging.mkdir(parents=True, exist_ok=True)

    try:
        # 3. Voiceover
        print("\n[2/6] Generating voiceover...")
        narration_path = voice_gen.generate(narration_text, staging / "narration.mp3")

        # 4. Visuals
        print("\n[3/6] Generating visuals...")
        visual_paths = visual_gen.generate_batch(image_prompts, staging / "visuals")

        # 5. Assemble
        print("\n[4/6] Assembling video...")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        video_path = OUTPUT_DIR / f"{safe_name}.mp4"
        assembler.assemble(visual_paths, narration_path, video_path, staging)

        # 6. Metadata
        print("\n[5/6] Generating metadata...")
        meta = metadata.MetadataWriter().generate(topic, hook)
        print(f"  Title: {meta['title']}")

        # 7. Upload
        video_id = None
        if not dry_run:
            print("\n[6/6] Uploading to YouTube...")
            uploader = YouTubeUploader(privacy=privacy)
            video_id = uploader.upload(
                video_path,
                title=meta["title"],
                description=meta["description"],
                tags=meta["tags"],
                delete_after=True,
            )
        else:
            print("\n[6/6] Dry run — skipping upload.")
            print(f"  Video saved at: {video_path}")

        # 8. Log
        tracker.mark_uploaded(topic, video_id)
        topics.mark_done(topic)

    finally:
        # Clean staging regardless of success/failure
        shutil.rmtree(staging, ignore_errors=True)

    elapsed = time.time() - start
    result = {
        "topic": topic,
        "video_id": video_id,
        "title": meta["title"],
        "elapsed_seconds": round(elapsed),
        "url": f"https://youtube.com/watch?v={video_id}" if video_id else None,
    }

    print(f"\nDone in {elapsed/60:.1f} min")
    if video_id:
        print(f"Watch: https://youtube.com/watch?v={video_id}")

    return result

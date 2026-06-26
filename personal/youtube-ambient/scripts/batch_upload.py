"""Batch upload multiple videos sequentially.

Runs unattended — pipe stdout to a log file:
  python scripts/batch_upload.py > logs/batch.log 2>&1
"""
import sys, time
from pathlib import Path

PROJECT = Path(r"C:\Users\Muham.000\Muhammad -Claude\personal\youtube-ambient")
sys.path.insert(0, str(PROJECT / "src"))

import os
os.chdir(PROJECT)

from yt_ambient.pipeline import Pipeline

# (sound_type, duration_hours)
QUEUE = [
    ("brown",   8.0),   # biggest sleep search term
    ("white",   8.0),   # babies / office noise masking
    ("rain",    8.0),   # #1 nature sleep sound
    ("pink",    1.0),   # study/focus — 1h version
    ("grey",    1.0),   # lesser-known but dedicated audience
    ("thunder", 1.0),   # unique, low competition
    ("brown",   1.0),   # study version of top sound
]

def main():
    ffmpeg_bin = next(
        (str(p.parent) for p in (PROJECT.parent.parent.parent / "AppData/Local/Microsoft/WinGet/Packages").glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe")
         if p.exists()),
        None
    )
    if ffmpeg_bin:
        os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")

    pipeline = Pipeline(privacy="public")
    total = len(QUEUE)

    for i, (sound_type, duration) in enumerate(QUEUE, 1):
        print(f"\n{'='*50}")
        print(f"Video {i}/{total}: {sound_type} | {duration}h")
        print(f"{'='*50}")
        try:
            result = pipeline.run(sound_type=sound_type, duration_hours=duration, upload=True)
            print(f"DONE: {result.get('youtube_url', 'no URL')}")
        except Exception as e:
            print(f"ERROR on {sound_type} {duration}h: {e}")
            continue

        if i < total:
            print("Waiting 30s before next upload...")
            time.sleep(30)

    print("\n\nAll done! Check your YouTube Studio for the uploads.")

if __name__ == "__main__":
    main()

"""Make one or more YouTube videos public by video ID."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from yt_ambient.uploader.youtube import _load_credentials
from googleapiclient.discovery import build

def make_public(video_ids: list[str]) -> None:
    creds = _load_credentials()
    service = build("youtube", "v3", credentials=creds)
    for vid in video_ids:
        service.videos().update(
            part="status",
            body={"id": vid, "status": {"privacyStatus": "public"}}
        ).execute()
        print(f"  Made public: https://youtube.com/watch?v={vid}")

if __name__ == "__main__":
    ids = sys.argv[1:]
    if not ids:
        print("Usage: python scripts/make_public.py <video_id> [video_id ...]")
        sys.exit(1)
    make_public(ids)

"""YouTube Data API v3 uploader.

Handles OAuth2 authentication (token cached to disk) and resumable upload
for large MP4 files.  Deletes the local MP4 after a confirmed upload.

First-time setup: run scripts/setup_youtube_auth.py once to generate the token file.
"""

from __future__ import annotations

import http.client
import json
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from ..config import YOUTUBE_CLIENT_SECRETS, YOUTUBE_SCOPES, YOUTUBE_TOKEN_FILE

CATEGORY_PEOPLE_BLOGS = "22"
CATEGORY_EDUCATION = "27"

_MAX_RETRIES = 10
_RETRY_EXCEPTIONS = (
    http.client.NotConnected,
    http.client.IncompleteRead,
    http.client.ImproperConnectionState,
    http.client.CannotSendRequest,
    http.client.CannotSendHeader,
    http.client.ResponseNotReady,
    http.client.BadStatusLine,
    IOError,
)


def _delete_with_retry(path: Path, label: str = "file", retries: int = 5) -> None:
    """Delete a file, retrying on permission errors (Windows file locks)."""
    for attempt in range(retries):
        try:
            if path.exists():
                path.unlink()
                print(f"    Deleted local {label}: {path.name}")
            return
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"    Warning: could not delete {label} {path.name}: {e}")


def _load_credentials() -> Credentials:
    token_path = Path(YOUTUBE_TOKEN_FILE)
    secrets_path = Path(YOUTUBE_CLIENT_SECRETS)

    if token_path.exists():
        with token_path.open() as f:
            token_data = json.load(f)
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=YOUTUBE_SCOPES,
        )
        return creds

    if not secrets_path.exists():
        raise FileNotFoundError(
            f"YouTube client secrets not found at {secrets_path}.\n"
            "Run: python scripts/setup_youtube_auth.py"
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), YOUTUBE_SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds, token_path)
    return creds


def _save_credentials(creds: Credentials, path: Path) -> None:
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }
    path.write_text(json.dumps(data, indent=2))


class YouTubeUploader:
    def __init__(self, privacy: str = "public") -> None:
        self.privacy = privacy
        self._service = None

    def _get_service(self):
        if self._service is None:
            creds = _load_credentials()
            self._service = build("youtube", "v3", credentials=creds)
        return self._service

    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        category_id: str = CATEGORY_PEOPLE_BLOGS,
        delete_after: bool = True,
    ) -> str:
        service = self._get_service()

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:500],
                "categoryId": category_id,
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": self.privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=16 * 1024 * 1024,  # 16 MB chunks — faster upload
        )

        request = service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        video_id = self._resumable_upload(request, video_path.name)

        # Release Windows file lock before deleting
        try:
            if hasattr(media, "_fd") and media._fd:
                media._fd.close()
        except Exception:
            pass

        if delete_after:
            _delete_with_retry(video_path, label="MP4")

        return video_id

    def post_comment(self, video_id: str, text: str) -> str:
        service = self._get_service()
        response = service.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {"snippet": {"textOriginal": text}},
                }
            },
        ).execute()
        return response["id"]

    def set_thumbnail(self, video_id: str, thumbnail_path: Path) -> None:
        service = self._get_service()
        service.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
        ).execute()

    def _resumable_upload(self, request, filename: str) -> str:
        response = None
        error = None
        retry = 0

        print(f"Uploading {filename} ...")
        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    print(f"  Upload progress: {pct}%", end="\r")
            except HttpError as e:
                if e.resp.status in (500, 502, 503, 504):
                    error = e
                else:
                    raise
            except _RETRY_EXCEPTIONS as e:
                error = e

            if error is not None:
                retry += 1
                if retry > _MAX_RETRIES:
                    raise RuntimeError(f"Upload failed after {_MAX_RETRIES} retries: {error}")
                wait = 2 ** retry
                print(f"\n  Retrying in {wait}s (attempt {retry}/{_MAX_RETRIES})...")
                time.sleep(wait)
                error = None

        print(f"\nUpload complete — video ID: {response['id']}")
        return response["id"]

"""YouTube Data API v3 uploader — adapted from youtube-ambient channel."""

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

from .config import YOUTUBE_CLIENT_SECRETS, YOUTUBE_SCOPES, YOUTUBE_TOKEN_FILE

CATEGORY_EDUCATION = "27"

_MAX_RETRIES = 10
_RETRY_EXCEPTIONS = (
    http.client.NotConnected, http.client.IncompleteRead,
    http.client.ImproperConnectionState, http.client.CannotSendRequest,
    http.client.CannotSendHeader, http.client.ResponseNotReady,
    http.client.BadStatusLine, IOError,
)


def _load_credentials() -> Credentials:
    token_path = Path(YOUTUBE_TOKEN_FILE)
    secrets_path = Path(YOUTUBE_CLIENT_SECRETS)

    if token_path.exists():
        with token_path.open() as f:
            data = json.load(f)
        return Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=data["client_id"],
            client_secret=data["client_secret"],
            scopes=YOUTUBE_SCOPES,
        )

    if not secrets_path.exists():
        raise FileNotFoundError(
            f"client_secrets.json not found at {secrets_path}.\n"
            "Copy it from the youtube-ambient project or re-download from Google Cloud Console.\n"
            "Then run: python scripts/setup_youtube_auth.py"
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), YOUTUBE_SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.write_text(json.dumps({
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }, indent=2))
    return creds


class YouTubeUploader:
    def __init__(self, privacy: str = "public") -> None:
        self.privacy = privacy
        self._service = None

    def _svc(self):
        if self._service is None:
            self._service = build("youtube", "v3", credentials=_load_credentials())
        return self._service

    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        delete_after: bool = True,
    ) -> str:
        """Upload video, return YouTube video ID."""
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags,
                "categoryId": CATEGORY_EDUCATION,
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": self.privacy,
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(
            str(video_path), mimetype="video/mp4",
            resumable=True, chunksize=8 * 1024 * 1024,
        )
        request = self._svc().videos().insert(
            part=",".join(body.keys()), body=body, media_body=media,
        )
        video_id = self._resumable_upload(request, video_path.name)

        try:
            if hasattr(media, "_fd") and media._fd:
                media._fd.close()
        except Exception:
            pass

        if delete_after:
            for attempt in range(5):
                try:
                    if video_path.exists():
                        video_path.unlink()
                        print(f"    Deleted local file: {video_path.name}")
                    break
                except Exception as e:
                    if attempt < 4:
                        time.sleep(2)
                    else:
                        print(f"    Warning: could not delete {video_path.name}: {e}")

        return video_id

    def _resumable_upload(self, request, filename: str) -> str:
        response = error = None
        retry = 0
        print(f"Uploading {filename}...")
        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    print(f"  {int(status.progress() * 100)}%", end="\r")
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
                print(f"\n  Retry {retry}/{_MAX_RETRIES} in {wait}s...")
                time.sleep(wait)
                error = None

        print(f"\nUploaded — video ID: {response['id']}")
        return response["id"]

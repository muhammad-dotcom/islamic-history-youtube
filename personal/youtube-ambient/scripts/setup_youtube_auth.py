"""One-time YouTube OAuth2 setup.

Run this once to generate youtube_token.json.  After that, run_pipeline.py
handles token refresh automatically.

Prerequisites
-------------
1. Go to https://console.cloud.google.com
2. Create a project (or use an existing one)
3. Enable "YouTube Data API v3"
4. Go to APIs & Services > Credentials > Create Credentials > OAuth 2.0 Client ID
5. Application type: Desktop app
6. Download the JSON and save it as client_secrets.json in this project root
7. Run: python scripts/setup_youtube_auth.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from google_auth_oauthlib.flow import InstalledAppFlow
from yt_ambient.config import YOUTUBE_SCOPES, YOUTUBE_CLIENT_SECRETS, YOUTUBE_TOKEN_FILE

SCOPES = YOUTUBE_SCOPES
SECRETS_FILE = YOUTUBE_CLIENT_SECRETS
TOKEN_FILE = YOUTUBE_TOKEN_FILE


def main():
    secrets_path = Path(SECRETS_FILE)
    if not secrets_path.exists():
        print(f"ERROR: {SECRETS_FILE} not found.")
        print(__doc__)
        sys.exit(1)

    print("Opening browser for Google OAuth2 login...")
    print("Sign in with the Google account that owns your YouTube channel.\n")

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }

    token_path = Path(TOKEN_FILE)
    token_path.write_text(json.dumps(token_data, indent=2))

    print(f"\nSuccess! Token saved to {TOKEN_FILE}")
    print("You can now run: python scripts/run_pipeline.py --type brown --duration 0.1")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""One-time YouTube OAuth2 setup.

Run this once to generate youtube_token.json.
After that, the pipeline authenticates automatically.

Steps:
  1. Copy client_secrets.json from youtube-ambient/ (same Google Cloud project)
     OR download a new one from Google Cloud Console → APIs & Services → Credentials
  2. Run: python scripts/setup_youtube_auth.py
  3. A browser window will open — log in and grant access
  4. youtube_token.json is saved in this folder — keep it private
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yt_history.uploader import _load_credentials

if __name__ == "__main__":
    print("Opening browser for YouTube OAuth2 authorisation...")
    creds = _load_credentials()
    print("Authorisation complete. youtube_token.json saved.")
    print("You can now run: python scripts/run_pipeline.py")

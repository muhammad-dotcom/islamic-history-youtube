"""Single-use auth script with absolute path — run directly."""
import json, sys
from pathlib import Path

PROJECT = Path(r"C:\Users\Muham.000\Muhammad -Claude\personal\youtube-ambient")
sys.path.insert(0, str(PROJECT / "src"))

from google_auth_oauthlib.flow import InstalledAppFlow
from yt_ambient.config import YOUTUBE_SCOPES

SECRETS = PROJECT / "client_secrets.json"
TOKEN   = PROJECT / "youtube_token.json"

flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS), YOUTUBE_SCOPES)
creds = flow.run_local_server(port=0)

TOKEN.write_text(json.dumps({
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
}, indent=2))
print(f"Token saved to {TOKEN}")

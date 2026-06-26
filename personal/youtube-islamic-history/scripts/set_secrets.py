"""One-time script: uploads all GitHub Actions secrets for the pipeline."""
import base64
import json
import os
import sys
from pathlib import Path

import requests
from nacl import encoding, public

REPO = "muhammad-dotcom/islamic-history-youtube"
TOKEN = os.environ["GH_PAT"]
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

HERE = Path(__file__).parent.parent


def encrypt(pub_key: str, value: str) -> str:
    pk = public.PublicKey(pub_key.encode(), encoding.Base64Encoder())
    box = public.SealedBox(pk)
    return base64.b64encode(box.encrypt(value.encode())).decode()


def set_secret(name: str, value: str, key_id: str, pub_key: str) -> None:
    enc = encrypt(pub_key, value)
    r = requests.put(
        f"https://api.github.com/repos/{REPO}/actions/secrets/{name}",
        headers=HEADERS,
        json={"encrypted_value": enc, "key_id": key_id},
    )
    if r.status_code in (201, 204):
        print(f"  [OK] {name}")
    else:
        print(f"  [FAIL] {name}: {r.status_code} {r.text}")
        sys.exit(1)


def main() -> None:
    pk_resp = requests.get(
        f"https://api.github.com/repos/{REPO}/actions/secrets/public-key",
        headers=HEADERS,
    )
    pk_resp.raise_for_status()
    pk_data = pk_resp.json()
    key_id, pub_key = pk_data["key_id"], pk_data["key"]

    env = dict(line.split("=", 1) for line in (HERE / ".env").read_text().splitlines() if "=" in line)

    secrets = {
        "ANTHROPIC_API_KEY":           env["ANTHROPIC_API_KEY"],
        "PIXABAY_API_KEY":             env["PIXABAY_API_KEY"],
        "YOUTUBE_TOKEN_JSON":          (HERE / "youtube_token.json").read_text().strip(),
        "YOUTUBE_CLIENT_SECRETS_JSON": (HERE / "client_secrets.json").read_text().strip(),
    }

    print(f"Setting {len(secrets)} secrets on {REPO}...")
    for name, value in secrets.items():
        set_secret(name, value, key_id, pub_key)
    print("\nAll secrets set. Workflow is ready.")


if __name__ == "__main__":
    main()

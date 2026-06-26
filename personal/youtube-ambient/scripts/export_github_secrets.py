"""Print the values you need to paste into GitHub Secrets.

Run:  python scripts/export_github_secrets.py

Then go to:
  https://github.com/<your-username>/<your-repo>/settings/secrets/actions
  → New repository secret → paste each value below.

Three secrets needed:
  YOUTUBE_TOKEN_JSON         — OAuth token (refresh token lives inside)
  YOUTUBE_CLIENT_SECRETS_JSON — your Google Cloud credentials
  ANTHROPIC_API_KEY          — your Anthropic key
"""

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def _print_secret(name: str, path: Path) -> None:
    if not path.exists():
        print(f"\n[{name}]  NOT FOUND at {path}")
        return
    content = path.read_text().strip()
    # Validate it's JSON where expected
    try:
        json.loads(content)
    except json.JSONDecodeError:
        print(f"\n[{name}]  WARNING: file is not valid JSON — check it manually")
        return
    print(f"\n{'=' * 60}")
    print(f"Secret name:  {name}")
    print(f"{'=' * 60}")
    print(content)


def _print_env_secret(name: str, env_path: Path) -> None:
    if not env_path.exists():
        print(f"\n[{name}]  .env not found at {env_path}")
        return
    for line in env_path.read_text().splitlines():
        if line.startswith(f"{name}="):
            value = line.split("=", 1)[1].strip()
            print(f"\n{'=' * 60}")
            print(f"Secret name:  {name}")
            print(f"{'=' * 60}")
            print(value)
            return
    print(f"\n[{name}]  not found in .env")


if __name__ == "__main__":
    print("Copy each secret value and paste it into GitHub > Settings > Secrets > Actions\n")
    _print_secret("YOUTUBE_TOKEN_JSON", PROJECT / "youtube_token.json")
    _print_secret("YOUTUBE_CLIENT_SECRETS_JSON", PROJECT / "client_secrets.json")
    _print_env_secret("ANTHROPIC_API_KEY", PROJECT / ".env")
    print("\n" + "=" * 60)
    print("Done. You need 3 secrets total.")

"""Print the values to paste into GitHub Secrets for the Islamic history channel.

Run:  python scripts/export_github_secrets.py

Go to: https://github.com/<your-username>/<your-repo>/settings/secrets/actions

Secrets for this channel use the ISLAMIC_ prefix to separate them from the
ambient channel secrets (both channels are in the same GitHub repo).
"""

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def _print_secret(name: str, path: Path) -> None:
    if not path.exists():
        print(f"\n[{name}]  NOT FOUND at {path}")
        return
    content = path.read_text().strip()
    try:
        json.loads(content)
    except json.JSONDecodeError:
        print(f"\n[{name}]  WARNING: not valid JSON")
        return
    print(f"\n{'=' * 60}")
    print(f"Secret name:  {name}")
    print(f"{'=' * 60}")
    print(content)


def _print_env_secret(name: str, env_path: Path, secret_name: str | None = None) -> None:
    secret_name = secret_name or name
    if not env_path.exists():
        print(f"\n[{secret_name}]  .env not found — set manually")
        return
    for line in env_path.read_text().splitlines():
        if line.startswith(f"{name}="):
            value = line.split("=", 1)[1].strip()
            if not value:
                print(f"\n[{secret_name}]  empty in .env — fill in the value first")
                return
            print(f"\n{'=' * 60}")
            print(f"Secret name:  {secret_name}")
            print(f"{'=' * 60}")
            print(value)
            return
    print(f"\n[{secret_name}]  not found in .env — add it")


if __name__ == "__main__":
    env = PROJECT / ".env"
    print("Paste each value into GitHub > Settings > Secrets > Actions\n")
    print("Note: Islamic channel secrets use the ISLAMIC_ prefix.\n")

    _print_secret("ISLAMIC_YOUTUBE_TOKEN_JSON", PROJECT / "youtube_token.json")
    _print_secret("ISLAMIC_YOUTUBE_CLIENT_SECRETS_JSON", PROJECT / "client_secrets.json")

    print("\n--- Shared secrets (skip if already added from ambient channel) ---")
    _print_env_secret("ANTHROPIC_API_KEY", env)

    print("\n--- Islamic channel-specific secrets ---")
    _print_env_secret("ELEVENLABS_API_KEY", env)
    _print_env_secret("ELEVENLABS_VOICE_ID", env)
    _print_env_secret("OPENAI_API_KEY", env)
    _print_env_secret("PIXABAY_API_KEY", env)

    print("\n" + "=" * 60)
    print("Done. Required: ISLAMIC_YOUTUBE_TOKEN_JSON, ISLAMIC_YOUTUBE_CLIENT_SECRETS_JSON")
    print("Plus any of: ELEVENLABS_API_KEY, OPENAI_API_KEY, PIXABAY_API_KEY")

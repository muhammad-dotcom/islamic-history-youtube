"""Topic queue management.

Reads topics from data/topics.yaml. Each topic is a dict with:
  title: str
  done: bool (default false)

The pipeline pops the next undone topic, marks it done after upload.
If the queue is exhausted, Claude Sonnet generates 10 fresh topics.
"""

from __future__ import annotations

from pathlib import Path

import anthropic
import yaml

from .config import ANTHROPIC_API_KEY, TOPICS_FILE

_GENERATE_SYSTEM = """\
You are a YouTube content strategist specialising in Islamic history and civilisation.
Generate a list of compelling documentary video topics for a YouTube channel.

Rules:
- Topics must be factual, educational, and 100% halal
- No controversial religious debates — focus on history, science, culture, exploration
- Each topic must be specific enough to fill a 12-minute documentary
- Topics should appeal to a global audience (Muslim and non-Muslim)
- Vary the era: early Islam, Golden Age, Empires, scholars, explorers, architecture
- Respond ONLY with a YAML list — no prose, no fences
"""

_GENERATE_USER = """\
Already covered: {done_titles}

Generate 10 NEW Islamic history documentary topics not in that list.
Format (YAML list of strings):
- "Topic title here"
- "Another topic"
"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _load() -> list[dict]:
    if not TOPICS_FILE.exists():
        return []
    with TOPICS_FILE.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    return data


def _save(topics: list[dict]) -> None:
    TOPICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TOPICS_FILE.open("w", encoding="utf-8") as f:
        yaml.dump(topics, f, allow_unicode=True, default_flow_style=False)


def next_topic() -> str:
    """Return the next undone topic title, generating more if needed."""
    topics = _load()
    pending = [t for t in topics if not t.get("done")]

    if not pending:
        topics = _replenish(topics)
        pending = [t for t in topics if not t.get("done")]

    return pending[0]["title"]


def mark_done(title: str) -> None:
    topics = _load()
    for t in topics:
        if t["title"] == title:
            t["done"] = True
            break
    _save(topics)


def _replenish(existing: list[dict]) -> list[dict]:
    done_titles = [t["title"] for t in existing if t.get("done")]
    done_str = "\n".join(f"- {t}" for t in done_titles) if done_titles else "none yet"

    response = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_GENERATE_SYSTEM,
        messages=[{"role": "user", "content": _GENERATE_USER.format(done_titles=done_str)}],
    )

    raw = response.content[0].text.strip()
    new_titles: list[str] = yaml.safe_load(raw) or []

    new_topics = [{"title": t, "done": False} for t in new_titles if isinstance(t, str)]
    combined = existing + new_topics
    _save(combined)
    return combined

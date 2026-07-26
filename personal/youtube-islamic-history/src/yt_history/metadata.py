"""YouTube metadata generation via Claude Haiku.

Produces SEO-optimised title, description, and tags for Islamic history
documentary videos. Uses Haiku (cheapest model) — purely mechanical task.
"""

from __future__ import annotations

import json
import re

import anthropic

from .config import ANTHROPIC_API_KEY

_SYSTEM = """\
You write maximally optimised YouTube metadata for an Islamic history documentary channel.
Goal: rank in search AND land on the algorithm's recommended feed for as many people as possible.
Videos are 10-15 minute documentaries. Tone: factual, educational, respectful.

TITLE RULES:
- Max 70 characters
- Use a curiosity gap or power phrase: "The Untold Story of", "Why Nobody Talks About",
  "The Secret Behind", "How X Changed the World", "The Rise and Fall of", "History Forgot"
- Must contain the core topic keyword for search ranking
- Never misleading — the video must deliver what the title promises

DESCRIPTION RULES:
- Line 1-2 (shown before "Show more"): punchy hook that creates urgency to watch — reference
  the most dramatic/surprising fact in the video. End with "Watch till the end."
- Blank line
- Chapters section (boosts watch time ranking):
  0:00 Introduction
  0:45 [Section 2 name]
  3:00 [Section 3 name]
  6:00 [Section 4 name]
  9:00 [Section 5 name]
  11:30 Legacy & Impact
  (estimate timestamps — approximate is fine)
- Blank line
- 200-250 words of naturally integrated SEO body text with high-value keywords
- Blank line
- HASHTAGS LINE — include ALL of these discovery tags plus topic-specific ones:
  #fyp #foryou #foryoupage #viral #trending #history #islamichistory #documentary
  #historyfacts #didyouknow #learnonthistday #education #facts #worldhistory
  #islamiccivilization + 3-5 topic-specific hashtags (e.g. #Baghdad #GoldenAge)
  Total: 18-22 hashtags on one line

TAGS RULES (separate from hashtags):
- 30 tags total
- Mix: ultra-broad ("history documentary", "educational video", "world history"),
  mid ("islamic golden age", "muslim history", "medieval history"),
  specific (topic keywords, person names, place names, era names)
- Include common misspellings/alternate spellings of key names

Respond ONLY with valid JSON — no prose, no markdown fences.
"""

_USER = """\
Topic: {topic}
Hook (opening lines of narration): {hook}

Generate metadata JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["...", "..."]
}}
"""


class MetadataWriter:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def generate(self, topic: str, hook: str) -> dict:
        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _USER.format(topic=topic, hook=hook)}],
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        for key in ("title", "description", "tags"):
            if key not in result:
                raise ValueError(f"Metadata missing key {key!r}")

        result["title"] = result["title"][:100]
        result["description"] = result["description"][:5000]
        result["tags"] = self._sanitize_tags(result["tags"])
        return result

    @staticmethod
    def _sanitize_tags(tags: list[str]) -> list[str]:
        """YouTube rejects tags containing commas/quotes, caps each tag at
        100 chars, and caps the combined length of all tags at 500 —
        where any tag containing a space counts 2 chars extra (it's
        internally quoted). Stay well under 500 to leave safety margin."""
        cleaned: list[str] = []
        total = 0
        for tag in tags:
            tag = re.sub(r'[,"<>]', "", tag).strip()[:100]
            if not tag:
                continue
            cost = len(tag) + (2 if " " in tag else 0)
            if total + cost > 450:
                break
            cleaned.append(tag)
            total += cost
        return cleaned

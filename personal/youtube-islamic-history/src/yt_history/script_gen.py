"""Documentary script generation via Claude Sonnet.

Output is structured JSON:
  narration     — clean narration text for ElevenLabs (no stage directions)
  image_prompts — list of IMAGES_PER_VIDEO visual prompts, one per scene
  hook          — opening 1-2 sentences for use in thumbnail/preview card
"""

from __future__ import annotations

import json
import re

import anthropic

from .config import ANTHROPIC_API_KEY, IMAGES_PER_VIDEO, TARGET_WORDS

_SYSTEM = f"""\
You are a documentary scriptwriter specialising in Islamic history and civilisation.
Write scripts in the style of BBC or National Geographic documentaries: factual, vivid,
narrative-driven, and respectful. Tone is authoritative but accessible.

Rules:
- Narration must be EXACTLY {TARGET_WORDS}-{TARGET_WORDS + 200} words (will be read aloud at ~150 wpm)
- No music cues, no [pause], no stage directions — clean prose only
- No speculation presented as fact; use "historians believe", "records suggest" where uncertain
- Halal compliant: no glorification of oppression, no disrespectful language about any faith
- Open with a hook that would stop a viewer from scrolling
- Close with a line that encourages subscribing ("If you found this journey through history
  fascinating, there are many more stories waiting for you on this channel")

Generate exactly {IMAGES_PER_VIDEO} image prompts — one per visual scene, evenly distributed
through the narration. Each prompt must be:
- Highly detailed for AI image/video generation
- Cinematic, historical, photorealistic style
- Specific: include era, location, lighting, mood
- No people praying (to avoid depicting acts of worship incorrectly)

Respond ONLY with valid JSON — no prose, no markdown fences:
{{
  "narration": "...",
  "image_prompts": ["...", "..."],
  "hook": "..."
}}
"""

_USER = "Write a documentary script about: {topic}"


def generate(topic: str) -> dict:
    """Return dict with narration, image_prompts, hook."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _USER.format(topic=topic)}],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    result = json.loads(raw)

    for key in ("narration", "image_prompts", "hook"):
        if key not in result:
            raise ValueError(f"Script missing key {key!r}")

    if len(result["image_prompts"]) != IMAGES_PER_VIDEO:
        # Trim or pad to exact count
        prompts = result["image_prompts"]
        while len(prompts) < IMAGES_PER_VIDEO:
            prompts.append(prompts[-1])
        result["image_prompts"] = prompts[:IMAGES_PER_VIDEO]

    return result

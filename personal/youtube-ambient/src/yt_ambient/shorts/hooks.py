"""Hook and CTA text bank for Shorts — template-only, no Claude dependency.

Hooks are short and don't need an LLM call, and we've had two production
outages now from Claude-API coupling (metadata generation blocking the whole
pipeline when credits ran out) — keep this one dependency-free.

Follows the same halal content rule as long-form metadata (metadata/writer.py):
never say "music", "song", "melody", "beat", or any instrument name.
"""

from __future__ import annotations

import random

from ..config import SOUND_LABELS

_HOOKS: dict[str, list[str]] = {
    "brown": [
        "Can't Sleep? Try Brown Noise 🌙",
        "The Sound That Fixes Racing Thoughts",
        "3AM and Your Brain Won't Shut Up?",
        "This Noise Puts You Out in Minutes",
        "Why Everyone's Sleeping With This On",
    ],
    "white": [
        "Baby Won't Sleep? Try This",
        "The #1 Sound for Blocking Noisy Neighbours",
        "Can't Focus? Put This On",
        "This Sound Masks Everything",
        "Why This Noise Is Everywhere Right Now",
    ],
    "pink": [
        "Sleep Deeper With Pink Noise",
        "The Noise Scientists Sleep To",
        "Softer Than White, Deeper Than Brown",
        "This Noise Boosts Memory While You Sleep",
    ],
    "grey": [
        "Tinnitus? Try Grey Noise",
        "The Noise Your Ears Actually Want",
        "Smoother Than White Noise — Here's Why",
    ],
    "rain": [
        "3AM and Your Brain Won't Shut Up?",
        "Real Rain. Zero Music. Instant Calm.",
        "The Sound That Puts You Out Fast",
        "Why Rain Sounds Actually Work",
        "Can't Sleep? Put This On",
    ],
    "thunder": [
        "The Storm Sound That Knocks You Out",
        "Cosy, Dark, and Deeply Calming",
        "Why a Thunderstorm Helps You Sleep",
    ],
    "forest": [
        "Step Into a Quiet Forest",
        "The Sound of Actual Peace",
        "Birds. Wind. Nothing Else.",
    ],
    "ocean": [
        "The Sound of Slowing Down",
        "Waves. Nothing Else. Try It.",
        "Why Ocean Sounds Calm You Instantly",
    ],
    "stream": [
        "A Quiet Stream. Nothing Else.",
        "The Sound of Flowing Water, Uncut",
    ],
    "fireplace": [
        "Curl Up With This On",
        "The Coziest Sound on YouTube",
        "Real Fire. Real Crackle. No Music.",
    ],
    "cafe": [
        "Focus Like You're in a Busy Café",
        "The Background Noise That Makes You Productive",
    ],
}

_CTAS: list[str] = [
    "🔔 Subscribe for daily sleep & focus sounds",
    "🔔 New sound every day — subscribe",
    "🎧 Full length video on the channel",
]


class HookWriter:
    def pick(self, sound_type: str) -> dict[str, str]:
        hooks = _HOOKS.get(sound_type) or _HOOKS["brown"]
        return {
            "hook": random.choice(hooks),
            "label": SOUND_LABELS.get(sound_type, sound_type.title()),
            "cta": random.choice(_CTAS),
        }

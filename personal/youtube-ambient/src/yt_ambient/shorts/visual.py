"""Shorts visual source selector.

Branches like BackgroundSelector.select(): nature types with real footage get
a vertical crop + slow zoom; everything else (noise types, and any nature type
that still has no footage downloaded) gets an audio-reactive waveform driven
by the real generated audio — real motion, no static image, no new assets.

Returns a small descriptor for ShortsRenderer to build a single ffmpeg filter
graph from (no intermediate render pass).
"""

from __future__ import annotations

from pathlib import Path

from ..config import VISUALS_DIR
from ..video.backgrounds import BackgroundSelector, _NATURE_FOLDER
from ..video.thumbnail import SOUND_COLORS

_DEFAULT_WAVE_COLOR = "#4A90D9"


class ShortsVisualBuilder:
    def __init__(self, visuals_dir: Path | str = VISUALS_DIR) -> None:
        self._bg_selector = BackgroundSelector(visuals_dir=visuals_dir)

    def build(self, sound_type: str) -> dict:
        """Return {"mode": "footage", "path": Path} or {"mode": "waveform", "color": str}."""
        if sound_type in _NATURE_FOLDER:
            bg = self._bg_selector.select(sound_type)
            if bg["mode"] == "video":
                return {"mode": "footage", "path": bg["path"]}
        return {"mode": "waveform", "color": SOUND_COLORS.get(sound_type, _DEFAULT_WAVE_COLOR)}

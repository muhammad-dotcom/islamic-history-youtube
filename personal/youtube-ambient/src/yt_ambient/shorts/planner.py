"""Shorts rotation planner.

Reuses the long-form planner's sound rotation and sample-availability check
(scheduler/planner.py) rather than duplicating it, but keeps its own
independent state file — a Short's sound type doesn't have to match that
day's long-form video, which avoids coupling the two pipeline runs together.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..scheduler.planner import SOUND_ROTATION, _is_available

_DEFAULT_STATE = {"sound_idx": 0}


class ShortsPlanner:
    def __init__(self, state_path: Path | str = "data/shorts_schedule_state.json") -> None:
        self.state_path = Path(state_path)
        self._state = self._load_state()

    def next(self) -> str:
        """Return the next available sound_type, skipping any with no audio samples."""
        for _ in range(len(SOUND_ROTATION)):
            sound_type = SOUND_ROTATION[self._state["sound_idx"] % len(SOUND_ROTATION)]
            if _is_available(sound_type):
                return sound_type
            print(f"  ShortsPlanner: skipping '{sound_type}' (no audio samples available)")
            self._state["sound_idx"] += 1
            self._save_state()
        raise RuntimeError("No sound types available — check data/audio_samples/")

    def advance(self) -> None:
        """Call after a successful upload to move to the next slot."""
        self._state["sound_idx"] += 1
        self._save_state()

    def _load_state(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text())
            except (json.JSONDecodeError, KeyError):
                pass
        return dict(_DEFAULT_STATE)

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self._state, indent=2))

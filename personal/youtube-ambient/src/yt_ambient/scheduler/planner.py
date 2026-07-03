"""Upload scheduler / planner.

Phase 1: round-robin across all sound types with alternating durations (1h study, 8h sleep).
Phase 2: weighted rotation based on analytics (view counts from SQLite log).

State is persisted in data/schedule_state.json so the planner resumes correctly
after restarts.
"""

from __future__ import annotations

import json
from pathlib import Path

# Ordered rotation of sound types — determines which goes next in round-robin
SOUND_ROTATION = [
    "brown",
    "rain",
    "forest",
    "pink",
    "ocean",
    "white",
    "fireplace",
    "grey",
    "thunder",
    "cafe",
    "stream",
]

# These need sample files in data/audio_samples/<type>/ — the planner skips
# them when the folder is empty (e.g. on CI runners, where samples aren't in git).
SAMPLE_BASED = {"forest", "ocean", "stream", "fireplace", "cafe"}
_SAMPLES_DIR = Path("data/audio_samples")
_SAMPLE_EXTS = {".wav", ".flac", ".ogg"}


def _is_available(sound_type: str) -> bool:
    if sound_type not in SAMPLE_BASED:
        return True
    folder = _SAMPLES_DIR / sound_type
    if not folder.exists():
        return False
    return any(p.suffix.lower() in _SAMPLE_EXTS for p in folder.iterdir())

# Alternating durations: study then sleep, then repeat
DURATION_ROTATION = [1.0, 8.0]

_DEFAULT_STATE = {
    "sound_idx": 0,
    "duration_idx": 0,
}


class Planner:
    def __init__(self, state_path: Path | str = "data/schedule_state.json") -> None:
        self.state_path = Path(state_path)
        self._state = self._load_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def next(self) -> tuple[str, float]:
        """Return (sound_type, duration_hours) for the next video to produce.

        Skips sample-based sound types whose sample folder is empty, advancing
        the rotation state past them so they aren't retried every run.
        """
        for _ in range(len(SOUND_ROTATION)):
            sound_type = SOUND_ROTATION[self._state["sound_idx"] % len(SOUND_ROTATION)]
            if _is_available(sound_type):
                break
            print(f"  Planner: skipping '{sound_type}' (no audio samples available)")
            self._state["sound_idx"] += 1
            self._save_state()
        else:
            raise RuntimeError("No sound types available — check data/audio_samples/")
        duration = DURATION_ROTATION[self._state["duration_idx"] % len(DURATION_ROTATION)]
        return sound_type, duration

    def advance(self) -> None:
        """Call after a successful upload to move to the next slot."""
        self._state["duration_idx"] += 1
        # Move to next sound type only after completing both durations
        if self._state["duration_idx"] % len(DURATION_ROTATION) == 0:
            self._state["sound_idx"] += 1
        self._save_state()

    def override_next(self, sound_type: str, duration_hours: float) -> None:
        """Force a specific sound/duration without affecting rotation state."""
        # This doesn't change state — just used by the CLI --type/--duration flags.
        pass  # CLI passes override directly; planner state unchanged.

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

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

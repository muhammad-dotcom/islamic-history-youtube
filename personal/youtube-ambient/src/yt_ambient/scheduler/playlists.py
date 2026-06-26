"""Playlist manager — creates playlists on-demand and adds uploaded videos.

Playlist IDs are cached in data/playlist_ids.json to avoid redundant API calls.
"""

from __future__ import annotations

import json
from pathlib import Path

_CACHE_FILE = Path("data/playlist_ids.json")

# Maps sound_type → list of playlist titles to add the video to
PLAYLIST_MAP: dict[str, list[str]] = {
    "brown":     ["Brown & Pink Noise", "Sleep & Focus Sounds", "ADHD & Study Focus"],
    "pink":      ["Brown & Pink Noise", "Sleep & Focus Sounds", "ADHD & Study Focus"],
    "white":     ["White Noise", "Sleep & Focus Sounds", "Baby Sleep Sounds"],
    "grey":      ["Sleep & Focus Sounds"],
    "rain":      ["Rain & Nature Sounds", "Sleep & Focus Sounds"],
    "thunder":   ["Rain & Nature Sounds", "Sleep & Focus Sounds"],
    "forest":    ["Rain & Nature Sounds", "Nature Ambiance"],
    "ocean":     ["Rain & Nature Sounds", "Nature Ambiance"],
    "stream":    ["Rain & Nature Sounds", "Nature Ambiance"],
    "fireplace": ["Cozy Ambiance Sounds"],
    "cafe":      ["Cozy Ambiance Sounds", "ADHD & Study Focus"],
}

_PLAYLIST_DESCRIPTIONS: dict[str, str] = {
    "Brown & Pink Noise":      "The deepest, richest noise colors for sleep, focus, and blocking distractions.",
    "Sleep & Focus Sounds":    "Hours of pure ambient sound to help you fall asleep or enter deep focus — no music.",
    "ADHD & Study Focus":      "Noise and ambient sounds scientifically popular for focus, ADHD study sessions, and flow states.",
    "White Noise":             "Pure white noise for sleep, studying, tinnitus relief, and blocking background distractions.",
    "Baby Sleep Sounds":       "Gentle white noise and soft ambient sounds to help babies and toddlers sleep.",
    "Rain & Nature Sounds":    "Rain, thunder, forest, ocean, and stream sounds for sleep, relaxation, and meditation.",
    "Nature Ambiance":         "Immersive nature soundscapes — forest, ocean waves, streams, and more.",
    "Cozy Ambiance Sounds":    "Fireplace crackle, café chatter, and warm ambient sounds for comfort and focus.",
}


def _load_cache() -> dict[str, str]:
    if _CACHE_FILE.exists():
        return json.loads(_CACHE_FILE.read_text())
    return {}


def _save_cache(cache: dict[str, str]) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(json.dumps(cache, indent=2))


class PlaylistManager:
    def __init__(self, service) -> None:
        self._service = service
        self._cache = _load_cache()

    def add_video(self, video_id: str, sound_type: str) -> list[str]:
        """Add video to all playlists mapped to this sound_type. Returns playlist IDs used."""
        titles = PLAYLIST_MAP.get(sound_type, [])
        used = []
        for title in titles:
            try:
                playlist_id = self._get_or_create(title)
                self._add_to_playlist(video_id, playlist_id)
                used.append(playlist_id)
                print(f"    Added to playlist: {title}")
            except Exception as e:
                print(f"    Playlist '{title}' failed (non-fatal): {e}")
        return used

    def _get_or_create(self, title: str) -> str:
        if title in self._cache:
            return self._cache[title]

        # Search existing channel playlists
        response = self._service.playlists().list(
            part="snippet",
            mine=True,
            maxResults=50,
        ).execute()

        for item in response.get("items", []):
            if item["snippet"]["title"] == title:
                self._cache[title] = item["id"]
                _save_cache(self._cache)
                return item["id"]

        # Create new
        desc = _PLAYLIST_DESCRIPTIONS.get(title, "Ambient and sleep sounds — no music.")
        new = self._service.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": desc},
                "status": {"privacyStatus": "public"},
            },
        ).execute()

        playlist_id = new["id"]
        self._cache[title] = playlist_id
        _save_cache(self._cache)
        print(f"    Created new playlist: {title} ({playlist_id})")
        return playlist_id

    def _add_to_playlist(self, video_id: str, playlist_id: str) -> None:
        import time
        for attempt in range(4):
            try:
                self._service.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {"kind": "youtube#video", "videoId": video_id},
                        }
                    },
                ).execute()
                return
            except Exception as e:
                if attempt < 3:
                    time.sleep(3 * (attempt + 1))
                else:
                    raise

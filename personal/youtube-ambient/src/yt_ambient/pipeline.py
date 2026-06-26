"""End-to-end pipeline orchestrator.

Coordinates: planner → audio gen → background → render → metadata → thumbnail
             → upload → set thumbnail → add to playlists → log.

Usage (via CLI):
    python scripts/run_pipeline.py                     # auto: planner picks next
    python scripts/run_pipeline.py --type rain         # override sound type
    python scripts/run_pipeline.py --duration 1        # override duration
    python scripts/run_pipeline.py --no-upload         # generate only, skip upload
"""

from __future__ import annotations

import time
from pathlib import Path

from .analytics.tracker import AnalyticsTracker
from .config import OUTPUT_DIR, VISUALS_DIR
from .generators.nature import NatureGenerator
from .generators.noise import NoiseGenerator
from .metadata.writer import MetadataWriter
from .scheduler.planner import Planner
from .scheduler.playlists import PlaylistManager
from .uploader.youtube import YouTubeUploader
from .video import thumbnail as thumb_gen
from .video.backgrounds import BackgroundSelector
from .video.renderer import VideoRenderer

_NOISE_TYPES = {"white", "pink", "brown", "grey"}
_NATURE_TYPES = {"rain", "thunder", "forest", "ocean", "stream", "fireplace", "cafe"}


class Pipeline:
    def __init__(
        self,
        output_dir: Path | str = OUTPUT_DIR,
        visuals_dir: Path | str = VISUALS_DIR,
        samples_dir: Path | str = "data/audio_samples",
        privacy: str = "public",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._noise_gen = NoiseGenerator()
        self._nature_gen = NatureGenerator(samples_dir=samples_dir)
        self._bg_selector = BackgroundSelector(visuals_dir=visuals_dir)
        self._renderer = VideoRenderer()
        self._metadata = MetadataWriter()
        self._uploader = YouTubeUploader(privacy=privacy)
        self._planner = Planner()
        self._tracker = AnalyticsTracker()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        sound_type: str | None = None,
        duration_hours: float | None = None,
        upload: bool = True,
    ) -> dict:
        if sound_type is None or duration_hours is None:
            planned_type, planned_dur = self._planner.next()
            sound_type = sound_type or planned_type
            duration_hours = duration_hours or planned_dur

        print(f"\n=== Pipeline: {sound_type} | {duration_hours}h ===\n")
        result: dict = {"sound_type": sound_type, "duration_hours": duration_hours}

        # 1. Generate audio
        audio_path = self._step_generate_audio(sound_type, duration_hours)
        result["audio_path"] = str(audio_path)

        # 2. Select background
        background = self._step_select_background(sound_type)

        # 3. Render video (WAV deleted automatically after render)
        video_path = self._step_render_video(audio_path, background, sound_type, duration_hours)
        result["video_path"] = str(video_path)

        # 4. Generate metadata
        metadata = self._step_generate_metadata(sound_type, duration_hours)
        result["metadata"] = metadata
        print(f"Title: {metadata['title']}")

        # 5. Generate thumbnail
        thumb_path = self._step_generate_thumbnail(sound_type, duration_hours)

        if upload:
            # 6. Upload video
            video_id = self._step_upload(video_path, metadata)
            result["video_id"] = video_id
            result["youtube_url"] = f"https://youtube.com/watch?v={video_id}"

            # 7. Set custom thumbnail
            self._step_set_thumbnail(video_id, thumb_path)

            # 8. Add to playlists
            self._step_add_to_playlists(video_id, sound_type)

            # 9. Log + advance planner
            self._tracker.log_upload(
                video_id=video_id,
                sound_type=sound_type,
                duration_hours=duration_hours,
                title=metadata["title"],
            )
            self._planner.advance()
            print(f"\nDone. Video live at: https://youtube.com/watch?v={video_id}")
        else:
            print(f"\nDone (no-upload). Video: {video_path} | Thumb: {thumb_path}")

        return result

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _step_generate_audio(self, sound_type: str, duration_hours: float) -> Path:
        print(f"[1/8] Generating {duration_hours}h of {sound_type} audio...")
        t0 = time.time()
        audio_path = self.output_dir / f"{sound_type}_{duration_hours}h_{int(time.time())}.wav"

        if sound_type in _NOISE_TYPES:
            self._noise_gen.generate(sound_type, duration_hours, audio_path)
        elif sound_type in _NATURE_TYPES:
            self._nature_gen.generate(sound_type, duration_hours, audio_path)
        else:
            raise ValueError(f"Unknown sound type: {sound_type!r}")

        elapsed = time.time() - t0
        size_mb = audio_path.stat().st_size / 1024 / 1024
        print(f"    Audio ready: {size_mb:.0f} MB in {elapsed:.1f}s")
        return audio_path

    def _step_select_background(self, sound_type: str) -> dict:
        print(f"[2/8] Selecting background for {sound_type}...")
        bg = self._bg_selector.select(sound_type, cache_dir=self.output_dir / "bg_cache")
        print(f"    Mode: {bg['mode']} | {bg['path'].name}")
        return bg

    def _step_render_video(
        self,
        audio_path: Path,
        background: dict,
        sound_type: str,
        duration_hours: float,
    ) -> Path:
        print(f"[3/8] Rendering video with FFmpeg...")
        t0 = time.time()
        video_path = self.output_dir / f"{sound_type}_{duration_hours}h_{int(time.time())}.mp4"
        self._renderer.render(audio_path, background, video_path, delete_audio_after=True)
        elapsed = time.time() - t0
        size_mb = video_path.stat().st_size / 1024 / 1024
        print(f"    Video ready: {size_mb:.0f} MB in {elapsed:.1f}s")
        return video_path

    def _step_generate_metadata(self, sound_type: str, duration_hours: float) -> dict:
        print(f"[4/8] Generating metadata with Claude...")
        return self._metadata.generate(sound_type, duration_hours)

    def _step_generate_thumbnail(self, sound_type: str, duration_hours: float) -> Path:
        print(f"[5/8] Generating thumbnail...")
        thumb_path = self.output_dir / f"thumb_{sound_type}_{duration_hours}h_{int(time.time())}.jpg"
        result = thumb_gen.generate(sound_type, duration_hours, thumb_path)
        print(f"    Thumbnail: {result.name}")
        return result

    def _step_upload(self, video_path: Path, metadata: dict) -> str:
        print(f"[6/8] Uploading to YouTube...")
        video_id = self._uploader.upload(
            video_path=video_path,
            title=metadata["title"],
            description=metadata["description"],
            tags=metadata["tags"],
            delete_after=True,
        )

        try:
            pinned_text = (
                "🔔 Subscribe for daily sleep & focus sounds — new video every day!\n"
                "👍 Like if this helped you sleep, study, or relax.\n"
                "💬 What sounds do you want next? Drop a comment below!\n\n"
                "🎧 Turn on notifications so you never miss a new upload."
            )
            self._uploader.post_comment(video_id, pinned_text)
            print(f"    Comment posted — PIN IT at: https://studio.youtube.com/video/{video_id}/comments")
        except Exception as e:
            print(f"    Comment post failed (non-fatal): {e}")

        return video_id

    def _step_set_thumbnail(self, video_id: str, thumb_path: Path) -> None:
        print(f"[7/8] Setting custom thumbnail...")
        try:
            self._uploader.set_thumbnail(video_id, thumb_path)
            print(f"    Thumbnail uploaded.")
            try:
                thumb_path.unlink()
            except Exception:
                pass
        except Exception as e:
            print(f"    Thumbnail upload failed (non-fatal): {e}")

    def _step_add_to_playlists(self, video_id: str, sound_type: str) -> None:
        print(f"[8/8] Adding to playlists...")
        try:
            service = self._uploader._get_service()
            pm = PlaylistManager(service)
            pm.add_video(video_id, sound_type)
        except Exception as e:
            print(f"    Playlist assignment failed (non-fatal): {e}")

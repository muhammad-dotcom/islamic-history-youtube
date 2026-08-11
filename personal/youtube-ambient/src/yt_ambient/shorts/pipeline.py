"""Shorts pipeline orchestrator.

Mirrors the long-form Pipeline (../pipeline.py) but shorter: no thumbnail step
(Shorts don't show custom thumbnails in the Shorts feed) and no playlist step.

    generate short audio clip → pick visual → render vertical MP4
    → metadata → upload → comment → log → advance planner
"""

from __future__ import annotations

import time
from pathlib import Path

from ..analytics.tracker import AnalyticsTracker
from ..config import OUTPUT_DIR
from ..generators.nature import NatureGenerator
from ..generators.noise import NoiseGenerator
from ..metadata.writer import _TEMPLATES
from ..uploader.youtube import YouTubeUploader
from ..video.thumbnail import SOUND_COLORS
from .hooks import HookWriter
from .planner import ShortsPlanner
from .renderer import ShortsRenderer
from .visual import ShortsVisualBuilder

_NATURE_TYPES = NatureGenerator.SYNTHESIZED | NatureGenerator.SAMPLE_BASED
DEFAULT_DURATION_SECONDS = 30.0


class ShortsPipeline:
    def __init__(
        self,
        output_dir: Path | str = OUTPUT_DIR,
        duration_seconds: float = DEFAULT_DURATION_SECONDS,
        privacy: str = "public",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.duration_seconds = duration_seconds

        self._noise_gen = NoiseGenerator()
        self._nature_gen = NatureGenerator()
        self._visual_builder = ShortsVisualBuilder()
        self._renderer = ShortsRenderer()
        self._hooks = HookWriter()
        self._uploader = YouTubeUploader(privacy=privacy)
        self._planner = ShortsPlanner()
        self._tracker = AnalyticsTracker()

    def run(self, sound_type: str | None = None, upload: bool = True) -> dict:
        sound_type = sound_type or self._planner.next()
        duration_hours = self.duration_seconds / 3600
        print(f"\n=== Shorts Pipeline: {sound_type} ({self.duration_seconds:.0f}s) ===\n")

        # 1. Generate a short audio clip (same generators as long-form, just a
        #    much shorter duration_hours — no new audio code needed).
        print("[1/5] Generating short audio clip...")
        audio_path = self.output_dir / f"short_{sound_type}_{int(time.time())}.wav"
        if sound_type in _NATURE_TYPES:
            self._nature_gen.generate(sound_type, duration_hours, audio_path)
        else:
            self._noise_gen.generate(sound_type, duration_hours, audio_path)

        # 2. Visual source (footage crop or audio-reactive waveform)
        print("[2/5] Selecting visual...")
        visual = self._visual_builder.build(sound_type)
        print(f"    Mode: {visual['mode']}")

        # 3. Hook/label/CTA text
        texts = self._hooks.pick(sound_type)
        texts["label_color"] = SOUND_COLORS.get(sound_type, "#FFFFFF")

        # 4. Render vertical MP4
        print("[3/5] Rendering vertical video...")
        video_path = self.output_dir / f"short_{sound_type}_{int(time.time())}.mp4"
        self._renderer.render(audio_path, visual, texts, self.duration_seconds, video_path)
        try:
            audio_path.unlink()
        except Exception:
            pass

        # 5. Metadata
        print("[4/5] Generating metadata...")
        metadata = self._build_metadata(sound_type, texts)
        print(f"    Title: {metadata['title']}")

        result: dict = {"sound_type": sound_type, "video_path": str(video_path), "metadata": metadata}

        if upload:
            print("[5/5] Uploading Short...")
            video_id = self._uploader.upload(
                video_path=video_path,
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
                delete_after=True,
            )
            result["video_id"] = video_id
            result["youtube_url"] = f"https://youtube.com/watch?v={video_id}"

            try:
                self._uploader.post_comment(video_id, texts["cta"])
            except Exception as e:
                print(f"    Comment post failed (non-fatal): {e}")

            self._tracker.log_upload(
                video_id=video_id,
                sound_type=sound_type,
                duration_hours=duration_hours,
                title=metadata["title"],
                content_type="short",
            )
            self._planner.advance()
            print(f"\nDone. Short live at: {result['youtube_url']}")
        else:
            print(f"\nDone (no-upload). Video: {video_path}")

        return result

    def _build_metadata(self, sound_type: str, texts: dict) -> dict:
        tmpl = _TEMPLATES.get(sound_type, _TEMPLATES["brown"])
        title = f"{texts['hook']} | {texts['label']} #Shorts"[:100]
        description = f"{texts['hook']}\n\n{texts['cta']}\n\n{tmpl['hashtags']} #Shorts"[:5000]
        tags = list(dict.fromkeys(tmpl["tags"] + ["shorts", "youtube shorts", "short"]))[:500]
        return {"title": title, "description": description, "tags": tags}

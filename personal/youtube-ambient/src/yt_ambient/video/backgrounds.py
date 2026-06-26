"""Background visual selector.

Noise types  → generate a dark gradient PNG with Pillow (no assets required).
Nature types → select a royalty-free MP4 clip from data/visuals/nature/<type>/.

Callers receive either:
  {"mode": "image", "path": Path}   — for FFmpeg -loop 1 -i <path>
  {"mode": "video", "path": Path}   — for FFmpeg -stream_loop -1 -i <path>
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from ..config import VISUALS_DIR

# Map sound_type → subfolder under data/visuals/nature/
_NATURE_FOLDER: dict[str, str] = {
    "rain": "rain",
    "thunder": "rain",
    "forest": "forest",
    "ocean": "ocean",
    "stream": "ocean",
    "fireplace": "fireplace",
    "cafe": "cafe",
}

# Colour palettes for programmatic gradient backgrounds (per noise type)
_NOISE_PALETTES: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "white": ((230, 230, 240), (120, 120, 140)),
    "pink": ((180, 100, 140), (40, 10, 60)),
    "brown": ((80, 45, 20), (15, 8, 4)),
    "grey": ((80, 85, 95), (10, 12, 18)),
}

WIDTH, HEIGHT = 1920, 1080


class BackgroundSelector:
    def __init__(self, visuals_dir: Path | str = VISUALS_DIR) -> None:
        self.visuals_dir = Path(visuals_dir)

    def select(self, sound_type: str, cache_dir: Path | None = None) -> dict:
        if sound_type in _NOISE_PALETTES:
            return self._gradient_background(sound_type, cache_dir)
        if sound_type in _NATURE_FOLDER:
            return self._nature_footage(sound_type)
        raise ValueError(f"Unknown sound type for background: {sound_type!r}")

    # ------------------------------------------------------------------
    # Gradient background (noise types)
    # ------------------------------------------------------------------

    def _gradient_background(self, sound_type: str, cache_dir: Path | None) -> dict:
        out_dir = cache_dir or (self.visuals_dir / "noise")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{sound_type}_bg.png"

        if not out_path.exists():
            img = self._make_gradient(sound_type)
            img.save(out_path, "PNG")

        return {"mode": "image", "path": out_path}

    def _make_gradient(self, sound_type: str) -> Image.Image:
        top_color, bottom_color = _NOISE_PALETTES[sound_type]
        img = Image.new("RGB", (WIDTH, HEIGHT))
        draw = ImageDraw.Draw(img)

        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
            g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
            b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

        # Soft vignette — darkens edges for a cinematic look
        img = self._apply_vignette(img)

        # Subtle label in the lower-left
        self._draw_label(draw, sound_type)

        return img

    def _apply_vignette(self, img: Image.Image) -> Image.Image:
        vignette = Image.new("L", (WIDTH, HEIGHT), 255)
        draw = ImageDraw.Draw(vignette)
        margin = 0
        for i in range(min(WIDTH, HEIGHT) // 3):
            alpha = int(255 * (i / (min(WIDTH, HEIGHT) // 3)) ** 2)
            draw.rectangle(
                [margin + i, margin + i, WIDTH - margin - i, HEIGHT - margin - i],
                outline=alpha,
            )
        vignette = vignette.filter(ImageFilter.GaussianBlur(radius=80))
        vignette_layer = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        img = Image.composite(img, vignette_layer, vignette)
        return img

    def _draw_label(self, draw: ImageDraw.ImageDraw, sound_type: str) -> None:
        label = sound_type.replace("_", " ").title() + " Sounds"
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = None
        draw.text((60, HEIGHT - 80), label, fill=(200, 200, 200, 180), font=font)

    # ------------------------------------------------------------------
    # Nature footage (nature types)
    # ------------------------------------------------------------------

    def _nature_footage(self, sound_type: str) -> dict:
        folder_key = _NATURE_FOLDER[sound_type]
        footage_dir = self.visuals_dir / "nature" / folder_key

        if footage_dir.exists():
            clips = [p for p in footage_dir.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".webm"}]
            if clips:
                return {"mode": "video", "path": random.choice(clips)}

        # Fallback: generate a dark gradient if no footage downloaded yet
        return self._gradient_fallback(sound_type)

    def _gradient_fallback(self, sound_type: str) -> dict:
        fallback_palettes = {
            "rain": ((20, 30, 50), (5, 8, 15)),
            "thunder": ((15, 15, 25), (3, 3, 8)),
            "forest": ((15, 35, 15), (4, 12, 4)),
            "ocean": ((10, 20, 50), (3, 8, 25)),
            "stream": ((10, 25, 40), (3, 10, 18)),
            "fireplace": ((60, 25, 5), (20, 8, 2)),
            "cafe": ((30, 22, 15), (10, 7, 4)),
        }
        top, bottom = fallback_palettes.get(sound_type, ((10, 10, 20), (2, 2, 8)))
        _NOISE_PALETTES["_fallback"] = (top, bottom)
        img = Image.new("RGB", (WIDTH, HEIGHT))
        draw = ImageDraw.Draw(img)
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(top[0] * (1 - t) + bottom[0] * t)
            g = int(top[1] * (1 - t) + bottom[1] * t)
            b_val = int(top[2] * (1 - t) + bottom[2] * t)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b_val))
        self._draw_label(draw, sound_type)
        out_dir = self.visuals_dir / "noise"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{sound_type}_fallback_bg.png"
        img.save(out_path, "PNG")
        return {"mode": "image", "path": out_path}

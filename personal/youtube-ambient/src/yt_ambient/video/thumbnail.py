"""Thumbnail generator — pitch black background, bold Impact text, color-coded per sound type.

YouTube spec: 1280x720 JPEG. Thumbnails must be uploaded separately after video upload.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import SOUND_LABELS

THUMB_W, THUMB_H = 1280, 720

# Color per sound type — visible on black background
SOUND_COLORS: dict[str, str] = {
    "white":     "#E8E8E8",
    "pink":      "#FF69B4",
    "brown":     "#CD853F",
    "grey":      "#A8A8A8",
    "rain":      "#4A90D9",
    "thunder":   "#9B59B6",
    "forest":    "#2ECC71",
    "ocean":     "#2980B9",
    "stream":    "#3498DB",
    "fireplace": "#E74C3C",
    "cafe":      "#E67E22",
}

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/Arial_Bold.ttf",
    "C:/Windows/Fonts/GOTHICB.TTF",
]


def _load_font(size: int):
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _duration_label(hours: float) -> str:
    if hours < 1:
        return f"{int(hours * 60)} MIN"
    return f"{int(hours)} HOURS"


def generate(sound_type: str, duration_hours: float, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (THUMB_W, THUMB_H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = SOUND_COLORS.get(sound_type, "#FFFFFF")
    label = SOUND_LABELS.get(sound_type, sound_type.replace("_", " ").title()).upper()
    dur_label = _duration_label(duration_hours)

    # --- Main label (sound type) ---
    main_font = _load_font(170)
    bbox = draw.textbbox((0, 0), label, font=main_font)
    tw = bbox[2] - bbox[0]
    # Scale down if text is too wide
    if tw > THUMB_W - 80:
        main_font = _load_font(int(170 * (THUMB_W - 80) / tw))
        bbox = draw.textbbox((0, 0), label, font=main_font)
        tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((THUMB_W - tw) / 2, THUMB_H * 0.28 - th / 2), label, fill=color, font=main_font)

    # --- Duration label ---
    dur_font = _load_font(110)
    bbox2 = draw.textbbox((0, 0), dur_label, font=dur_font)
    dw = bbox2[2] - bbox2[0]
    draw.text(((THUMB_W - dw) / 2, THUMB_H * 0.65), dur_label, fill="#FFFFFF", font=dur_font)

    # --- Thin color accent line under main label ---
    line_y = int(THUMB_H * 0.47)
    line_w = min(tw + 60, THUMB_W - 60)
    x0 = (THUMB_W - line_w) // 2
    draw.rectangle([x0, line_y, x0 + line_w, line_y + 5], fill=color)

    output_path_jpg = output_path.with_suffix(".jpg")
    img.save(output_path_jpg, "JPEG", quality=95)
    return output_path_jpg

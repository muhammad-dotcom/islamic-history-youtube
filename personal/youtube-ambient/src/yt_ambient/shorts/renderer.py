"""Shorts renderer — assembles the final vertical MP4 in a single ffmpeg pass.

Text overlays are rendered as transparent PNGs via Pillow (same approach as
thumbnail.py) rather than ffmpeg drawtext — drawtext requires escaping both
the font path (Windows drive-letter colons collide with filter syntax) and
the text itself (apostrophes, colons, emoji), which is fragile. Compositing
pre-rendered PNGs with ffmpeg's `overlay` filter sidesteps all of that.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1920
FPS = 30

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/Arial_Bold.ttf",
    "C:/Windows/Fonts/GOTHICB.TTF",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _strip_unrenderable(text: str) -> str:
    """Strip color emoji etc. — the bundled TTF fonts render them as tofu
    boxes. Metadata (titles/descriptions) can keep emoji since YouTube
    renders those itself; only text drawn onto the video via Pillow needs
    this. Emoji live outside the Basic Multilingual Plane, so filtering by
    codepoint catches them without a big unicode range table."""
    cleaned = "".join(c for c in text if ord(c) <= 0xFFFF)
    return re.sub(r"\s+", " ", cleaned).strip()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _text_overlay(
    text: str,
    y_center_frac: float,
    font_size: int,
    text_color: str,
    box: bool = True,
) -> Image.Image:
    """Transparent 1080x1920 PNG with word-wrapped, centered text."""
    text = _strip_unrenderable(text)
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(font_size)
    max_width = WIDTH - 120
    lines = _wrap_text(draw, text, font, max_width)

    line_heights = [draw.textbbox((0, 0), ln, font=font)[3] for ln in lines]
    line_gap = 12
    total_h = sum(line_heights) + line_gap * (len(lines) - 1)
    y = int(HEIGHT * y_center_frac - total_h / 2)

    if box:
        pad_x, pad_y = 40, 24
        max_line_w = max(draw.textbbox((0, 0), ln, font=font)[2] for ln in lines)
        box_x0 = (WIDTH - max_line_w) / 2 - pad_x
        box_x1 = (WIDTH + max_line_w) / 2 + pad_x
        draw.rounded_rectangle(
            [box_x0, y - pad_y, box_x1, y + total_h + pad_y],
            radius=24, fill=(0, 0, 0, 150),
        )

    for line, lh in zip(lines, line_heights):
        w = draw.textbbox((0, 0), line, font=font)[2]
        draw.text(((WIDTH - w) / 2, y), line, fill=text_color, font=font)
        y += lh + line_gap

    return img


def _ffmpeg(*args: str) -> None:
    result = subprocess.run(["ffmpeg", "-y", *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-3000:], file=sys.stderr)
        raise RuntimeError("FFmpeg failed rendering Short. See stderr above.")


class ShortsRenderer:
    def __init__(self, crf: int = 20, audio_bitrate: str = "192k") -> None:
        self.crf = crf
        self.audio_bitrate = audio_bitrate

    def render(
        self,
        audio_path: Path,
        visual: dict,
        texts: dict[str, str],
        duration: float,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="short_overlays_") as tmp:
            tmp_dir = Path(tmp)
            hook_png = tmp_dir / "hook.png"
            label_png = tmp_dir / "label.png"
            cta_png = tmp_dir / "cta.png"

            _text_overlay(texts["hook"], 0.16, 66, "white").save(hook_png)
            _text_overlay(texts["label"], 0.86, 46, texts.get("label_color", "white"), box=False).save(label_png)
            _text_overlay(texts["cta"], 0.94, 42, "white").save(cta_png)

            if visual["mode"] == "footage":
                self._render_footage(audio_path, visual["path"], hook_png, label_png, cta_png, duration, output_path)
            else:
                self._render_waveform(audio_path, visual["color"], hook_png, label_png, cta_png, duration, output_path)

        return output_path

    def _render_footage(
        self, audio: Path, footage: Path, hook_png: Path, label_png: Path, cta_png: Path,
        duration: float, out: Path,
    ) -> None:
        fc = (
            # The long-form nature backgrounds are intentionally near-black
            # (unobtrusive for hours-long ambient viewing) — far too dark to
            # read as motion in a fast-scrolling Shorts feed. Boost it here,
            # in the Shorts path only; long-form rendering is untouched.
            f"[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale={WIDTH}:{HEIGHT},"
            f"eq=brightness=0.25:contrast=1.6:saturation=1.6[v0];"
            f"[v0][2:v]overlay=0:0:enable='between(t,0,4)'[v1];"
            f"[v1][3:v]overlay=0:0[v2];"
            f"[v2][4:v]overlay=0:0:enable='gte(t,{max(duration - 4, 0)})'[vout]"
        )
        _ffmpeg(
            "-stream_loop", "-1", "-i", str(footage),
            "-i", str(audio),
            "-loop", "1", "-i", str(hook_png),
            "-loop", "1", "-i", str(label_png),
            "-loop", "1", "-i", str(cta_png),
            "-filter_complex", fc,
            "-map", "[vout]", "-map", "1:a",
            "-t", str(duration),
            "-r", str(FPS),
            "-c:v", "libx264", "-preset", "fast", "-crf", str(self.crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", self.audio_bitrate,
            str(out),
        )

    def _render_waveform(
        self, audio: Path, color_hex: str, hook_png: Path, label_png: Path, cta_png: Path,
        duration: float, out: Path,
    ) -> None:
        ff_color = "0x" + color_hex.lstrip("#")
        # showwaves' `colors` option is unreliable on real (non-synthetic) stereo
        # audio — overlapping channel traces blend to green regardless of the
        # requested color. Sidestep it entirely: render the waveform in mono as
        # a luma mask, then recolor it deterministically via a solid-color layer
        # + alphamerge, which gives full control over the exact output color.
        fc = (
            f"color=c=black:s={WIDTH}x{HEIGHT}:d={duration}[bgcol];"
            f"color=c={ff_color}:s={WIDTH}x900:d={duration}[wavecolor];"
            f"[0:a]aformat=channel_layouts=mono,showwaves=s={WIDTH}x900:mode=cline:rate={FPS}[wraw];"
            f"[wraw]format=gray[wmask];"
            f"[wavecolor]format=rgba[wc];"
            f"[wc][wmask]alphamerge[wave];"
            f"[bgcol][wave]overlay=(W-w)/2:(H-h)/2[v0];"
            f"[v0][1:v]overlay=0:0:enable='between(t,0,4)'[v1];"
            f"[v1][2:v]overlay=0:0[v2];"
            f"[v2][3:v]overlay=0:0:enable='gte(t,{max(duration - 4, 0)})'[vout]"
        )
        _ffmpeg(
            "-i", str(audio),
            "-loop", "1", "-i", str(hook_png),
            "-loop", "1", "-i", str(label_png),
            "-loop", "1", "-i", str(cta_png),
            "-filter_complex", fc,
            "-map", "[vout]", "-map", "0:a",
            "-t", str(duration),
            "-r", str(FPS),
            "-c:v", "libx264", "-preset", "fast", "-crf", str(self.crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", self.audio_bitrate,
            str(out),
        )

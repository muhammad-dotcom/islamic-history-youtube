"""Generate animated ambient background videos for each nature sound type.

Uses FFmpeg's built-in lavfi (libavfilter) source filters — no footage downloads needed.
Produces short looping MP4 clips (~30s) that the pipeline loops indefinitely during video render.

Each type gets its own colour palette and grain intensity to match the mood of the sound.
Run once; outputs go into data/visuals/nature/<type>/.

Usage:
    python scripts/generate_bg_videos.py
    python scripts/generate_bg_videos.py --ffmpeg "C:/path/to/ffmpeg.exe"
"""

import subprocess
import sys
from pathlib import Path

# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# -----------------------------------------------------------------------
# FFmpeg background definitions
# Each entry: (base_hex_color, brightness_shift, grain_strength, saturation)
# -----------------------------------------------------------------------
BACKGROUNDS = {
    "rain": {
        "base": "0x08111e",
        "grain": 18,
        "brightness": -0.05,
        "saturation": 1.2,
        "desc": "Dark navy blue — evokes night rain on a window",
    },
    "thunder": {
        "base": "0x04070f",
        "grain": 25,
        "brightness": -0.08,
        "saturation": 0.9,
        "desc": "Near-black stormy blue — distant lightning ambiance",
    },
    "forest": {
        "base": "0x071510",
        "grain": 10,
        "brightness": -0.03,
        "saturation": 1.3,
        "desc": "Dark forest green — trees at dusk",
    },
    "ocean": {
        "base": "0x060f1e",
        "grain": 12,
        "brightness": -0.04,
        "saturation": 1.1,
        "desc": "Deep ocean blue — open water at night",
    },
    "stream": {
        "base": "0x071520",
        "grain": 14,
        "brightness": -0.03,
        "saturation": 1.2,
        "desc": "Dark blue-green — shallow stream at twilight",
    },
    "fireplace": {
        "base": "0x1a0802",
        "grain": 22,
        "brightness": 0.02,
        "saturation": 1.5,
        "desc": "Deep amber — warm fireplace glow in a dark room",
    },
    "cafe": {
        "base": "0x120c06",
        "grain": 8,
        "brightness": 0.01,
        "saturation": 1.1,
        "desc": "Dark warm brown — cozy café at closing time",
    },
}

WIDTH = 1920
HEIGHT = 1080
FPS = 24
DURATION = 30  # seconds — pipeline loops this indefinitely


def find_ffmpeg() -> str:
    """Return path to ffmpeg executable."""
    # Check CLI arg first
    for i, arg in enumerate(sys.argv):
        if arg == "--ffmpeg" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]

    # Known winget install location
    winget_path = (
        Path.home()
        / "AppData/Local/Microsoft/WinGet/Packages"
    )
    for p in winget_path.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"):
        return str(p)

    # Try PATH
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return "ffmpeg"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    raise FileNotFoundError(
        "ffmpeg not found. Install it with: winget install Gyan.FFmpeg\n"
        "Or pass --ffmpeg <path> to this script."
    )


def generate_background(ffmpeg: str, name: str, cfg: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ambient_bg.mp4"

    if out_path.exists():
        print(f"  {name}: already exists, skipping.")
        return

    # Build vf filter chain:
    # 1. Start with a solid colour
    # 2. Add temporal grain (changes every frame — makes it feel alive)
    # 3. Tweak brightness and saturation
    grain = cfg["grain"]
    brightness = cfg["brightness"]
    saturation = cfg["saturation"]

    vf = (
        f"noise=c0s={grain}:c1s={grain // 2}:c2s={grain // 3}:c0f=t+u,"
        f"eq=brightness={brightness}:saturation={saturation}"
    )

    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", f"color=c={cfg['base']}:size={WIDTH}x{HEIGHT}:rate={FPS}",
        "-vf", vf,
        "-t", str(DURATION),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR generating {name}:")
        print(result.stderr[-1000:])
    else:
        size_kb = out_path.stat().st_size // 1024
        print(f"  {name}: {out_path.name} ({size_kb} KB) — {cfg['desc']}")


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    nature_dir = project_root / "data" / "visuals" / "nature"

    print("Finding FFmpeg...")
    try:
        ffmpeg = find_ffmpeg()
        print(f"  Using: {ffmpeg}\n")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(f"Generating {len(BACKGROUNDS)} ambient background videos ({DURATION}s each)...\n")
    for name, cfg in BACKGROUNDS.items():
        out_dir = nature_dir / name
        generate_background(ffmpeg, name, cfg, out_dir)

    print(f"\nDone. Backgrounds saved to: {nature_dir}")
    print("The pipeline will loop these automatically during video rendering.")


if __name__ == "__main__":
    main()

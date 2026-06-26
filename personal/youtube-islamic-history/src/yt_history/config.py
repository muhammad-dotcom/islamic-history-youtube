import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- API keys ---
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY: str = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID: str = os.environ.get("ELEVENLABS_VOICE_ID", "")  # set after picking voice in ElevenLabs dashboard
HIGGSFIELD_API_KEY: str = os.environ.get("HIGGSFIELD_API_KEY", "")
HIGGSFIELD_API_URL: str = os.environ.get("HIGGSFIELD_API_URL", "")  # set once you have correct endpoint from Higgsfield docs
PIXABAY_API_KEY: str = os.environ.get("PIXABAY_API_KEY", "")
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")  # optional fallback for DALL-E 3

# --- YouTube OAuth ---
YOUTUBE_CLIENT_SECRETS: str = os.environ.get("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
YOUTUBE_TOKEN_FILE: str = os.environ.get("YOUTUBE_TOKEN_FILE", "youtube_token.json")
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

# --- Paths ---
DATA_DIR: Path = Path(os.environ.get("DATA_DIR", "data"))
OUTPUT_DIR: Path = Path(os.environ.get("OUTPUT_DIR", "output"))
STAGING_DIR: Path = Path(os.environ.get("STAGING_DIR", "staging"))
MUSIC_DIR: Path = DATA_DIR / "music"
TOPICS_FILE: Path = DATA_DIR / "topics.yaml"
DB_PATH: Path = DATA_DIR / "history.db"

# --- Video spec ---
VIDEO_WIDTH: int = 1920
VIDEO_HEIGHT: int = 1080
VIDEO_FPS: int = 24
IMAGES_PER_VIDEO: int = 18       # ~40 s per image for a 12-min video
TARGET_WORDS: int = 1800          # ~12 min at 150 wpm narration pace

# --- ElevenLabs (unused if on free plan — edge-tts is used instead) ---
ELEVENLABS_MODEL: str = "eleven_multilingual_v2"
ELEVENLABS_CHUNK_CHARS: int = 4000

# --- FFmpeg ---
FFMPEG_PATH: str = os.environ.get("FFMPEG_PATH", "ffmpeg")

# --- Kokoro TTS (free, offline neural TTS) ---
# bm_george = British male (BBC documentary style) — recommended
# bm_lewis  = British male (alternative)
# am_michael = American male narrator
KOKORO_VOICE: str = os.environ.get("KOKORO_VOICE", "bm_george")

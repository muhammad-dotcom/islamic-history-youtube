import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
YOUTUBE_CLIENT_SECRETS: str = os.environ.get("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
YOUTUBE_TOKEN_FILE: str = os.environ.get("YOUTUBE_TOKEN_FILE", "youtube_token.json")

SAMPLE_RATE: int = 44100       # noise types (white/pink/brown/grey)
NATURE_SAMPLE_RATE: int = 22050  # rain/thunder/nature — 9kHz Nyquist is enough, halves WAV size
CHANNELS: int = 2
CHUNK_SECONDS: int = 30  # generate audio this many seconds at a time — avoids OOM on 8h files

OUTPUT_DIR: Path = Path(os.environ.get("OUTPUT_DIR", "output"))
VISUALS_DIR: Path = Path(os.environ.get("VISUALS_DIR", "data/visuals"))

DEFAULT_DURATION_HOURS: float = float(os.environ.get("DEFAULT_DURATION_HOURS", "8"))
DEFAULT_SOUND_TYPE: str = os.environ.get("DEFAULT_SOUND_TYPE", "brown")

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # required for commentThreads.insert
]

SOUND_LABELS = {
    "white":     "White Noise",
    "pink":      "Pink Noise",
    "brown":     "Brown Noise",
    "grey":      "Grey Noise",
    "rain":      "Rain Sounds",
    "thunder":   "Thunder & Rain",
    "forest":    "Forest Sounds",
    "ocean":     "Ocean Waves",
    "stream":    "Stream & Creek",
    "fireplace": "Fireplace Sounds",
    "cafe":      "Café Ambiance",
}

# youtube-ambient

Fully automated YouTube ambient sound channel pipeline. Generates audio, renders video, writes SEO metadata, and uploads to YouTube — hands-off once running.

**Halal compliance:** pure nature/ambient sounds only. No music, no instruments, no melody imitation.

## Quick Start

```bash
# Install dependencies
cd personal/youtube-ambient
pip install -e .

# Test locally (no upload, 6-minute brown noise video)
python scripts/run_pipeline.py --type brown --duration 0.1 --no-upload

# First-time YouTube auth (run once)
python scripts/setup_youtube_auth.py

# Run one full pipeline slot (planner decides what's next)
python scripts/run_pipeline.py --auto

# Override: rain, 1 hour, public upload
python scripts/run_pipeline.py --type rain --duration 1 --upload
```

## Where to Go

| If you need...                          | See...                                   |
|---|---|
| Audio generation (noise/nature)         | `src/yt_ambient/generators/`            |
| Background visuals (gradient/footage)   | `src/yt_ambient/video/backgrounds.py`   |
| Video rendering (FFmpeg)                | `src/yt_ambient/video/renderer.py`      |
| Title/description/tags (Claude API)     | `src/yt_ambient/metadata/writer.py`     |
| YouTube upload (OAuth2 + resumable)     | `src/yt_ambient/uploader/youtube.py`    |
| Upload scheduler (rotation/weighting)  | `src/yt_ambient/scheduler/planner.py`   |
| Analytics log (SQLite)                  | `src/yt_ambient/analytics/tracker.py`   |
| Full orchestrator                       | `src/yt_ambient/pipeline.py`            |
| CLI entry point                         | `scripts/run_pipeline.py`               |

## Sound Types

| Type       | Generator         | Visual                          |
|---|---|---|
| white      | scipy IIR noise   | light grey gradient             |
| pink       | scipy IIR noise   | purple gradient                 |
| brown      | scipy IIR noise   | dark brown gradient             |
| grey       | scipy IIR noise   | slate gradient                  |
| rain       | synthesized noise | `data/visuals/nature/rain/`     |
| thunder    | synthesized noise | `data/visuals/nature/rain/`     |
| forest     | freesound samples | `data/visuals/nature/forest/`   |
| ocean      | freesound samples | `data/visuals/nature/ocean/`    |
| stream     | freesound samples | `data/visuals/nature/ocean/`    |
| fireplace  | freesound samples | `data/visuals/nature/fireplace/`|
| cafe       | freesound samples | `data/visuals/nature/cafe/`     |

## Data Folders

- `data/audio_samples/<type>/` — royalty-free WAV/FLAC files (download from freesound.org, CC0 license)
- `data/visuals/nature/<type>/` — royalty-free MP4 footage clips (download from Pexels/Pixabay)
- `data/schedule_state.json` — planner rotation state (auto-managed)
- `data/analytics.db` — SQLite log of uploaded videos and view counts

## Setup Checklist

- [ ] Copy `.env.example` → `.env` and fill in `ANTHROPIC_API_KEY`
- [ ] Install FFmpeg: `winget install ffmpeg`
- [ ] Run `pip install -e .` in this folder
- [ ] Download royalty-free nature footage into `data/visuals/nature/<type>/`
- [ ] Download royalty-free audio samples into `data/audio_samples/<type>/`
- [ ] Set up Google Cloud project + YouTube Data API v3 + OAuth2 credentials
- [ ] Run `python scripts/setup_youtube_auth.py` once
- [ ] Test: `python scripts/run_pipeline.py --type brown --duration 0.1 --no-upload`

## Automation (Windows Task Scheduler)

To post once daily at 9 AM automatically:
1. Open Task Scheduler → Create Basic Task
2. Trigger: Daily at 09:00
3. Action: Start a program
   - Program: `python`
   - Arguments: `scripts/run_pipeline.py --auto`
   - Start in: `C:\path\to\personal\youtube-ambient`

## Phase Roadmap

- **Phase 1** (now): Full pipeline — generate → render → upload ✓
- **Phase 2**: Analytics weighting, freesound downloader script, Windows scheduler setup
- **Phase 3**: Spotify/podcast upload, GitHub Actions, VPS migration

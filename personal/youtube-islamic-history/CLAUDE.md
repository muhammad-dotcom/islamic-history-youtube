# youtube-islamic-history

Fully automated Islamic history documentary YouTube channel. One command produces a 10-15 minute video (script → voice → visuals → assembly → upload) with zero manual work.

**Halal compliance:** educational history content only — no music with lyrics, no haram imagery, no speculation presented as fact. All narration is factual and respectful.

## Quick Start

```bash
cd personal/youtube-islamic-history
pip install -e .

# First-time YouTube auth (once only)
python scripts/setup_youtube_auth.py

# Dry run — generates script + voice + visuals, skips upload
python scripts/run_pipeline.py --dry-run

# Full run — picks next topic, produces video, uploads to YouTube
python scripts/run_pipeline.py

# Force a specific topic
python scripts/run_pipeline.py --topic "The House of Wisdom in Baghdad"
```

## Where to Go

| If you need...                          | See...                              |
|---|---|
| Topic queue (add/remove topics)         | `data/topics.yaml`                  |
| Script generation (Claude Sonnet)       | `src/yt_history/script_gen.py`      |
| Voiceover (ElevenLabs TTS)             | `src/yt_history/voice_gen.py`       |
| Visual generation (Higgsfield/DALL-E)  | `src/yt_history/visual_gen.py`      |
| FFmpeg video assembly                   | `src/yt_history/assembler.py`       |
| YouTube metadata (Claude Haiku)         | `src/yt_history/metadata.py`        |
| YouTube upload (OAuth2)                 | `src/yt_history/uploader.py`        |
| Upload history log (SQLite)             | `src/yt_history/tracker.py`         |
| Full orchestrator                       | `src/yt_history/pipeline.py`        |
| Config + API keys                       | `src/yt_history/config.py` + `.env` |

## Visual Provider Priority

The pipeline picks the first available provider:
1. **Higgsfield** — cinematic AI video clips (set `HIGGSFIELD_API_KEY`)
2. **DALL-E 3** — AI-generated historical images (set `OPENAI_API_KEY`)

Set at least one. Both keys = Higgsfield used, DALL-E 3 as fallback if clip generation fails.

## Setup Checklist

- [ ] Copy `.env.example` → `.env` and fill in all keys
- [ ] Install FFmpeg: `winget install ffmpeg`
- [ ] Run `pip install -e .`
- [ ] Copy `client_secrets.json` from ambient channel (same Google Cloud project)
- [ ] Run `python scripts/setup_youtube_auth.py`
- [ ] Add at least one royalty-free ambient/epic music track to `data/music/` (MP3)
- [ ] Test: `python scripts/run_pipeline.py --dry-run`

## Automation (Windows Task Scheduler)

Post every 2 days at 10 AM:
1. Open Task Scheduler → Create Basic Task
2. Trigger: Daily, every 2 days, at 10:00
3. Action: Start a program
   - Program: `python`
   - Arguments: `scripts/run_pipeline.py`
   - Start in: `C:\Users\Muham.000\Muhammad -Claude\personal\youtube-islamic-history`

## Content Strategy

- **Format:** 10-15 min documentary (highest RPM bracket for educational content)
- **Topics:** Islamic civilizations, scholars, empires, discoveries, battles
- **Style:** factual, cinematic narration — think BBC/National Geographic tone
- **Upload cadence:** 3-4 per week to build algorithmic momentum
- **RPM target:** $5-15 (educational/history niche)

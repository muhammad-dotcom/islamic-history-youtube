"""Metadata writer — generates YouTube title, description, and tags.

Primary: Claude claude-haiku-4-5 (cheapest, fast). Falls back to built-in templates
automatically if the API key is missing or credits are exhausted.
"""

from __future__ import annotations

import json
import re

from ..config import ANTHROPIC_API_KEY, SOUND_LABELS

_DURATION_LABELS = {
    1.0: "1 Hour",
    2.0: "2 Hours",
    3.0: "3 Hours",
    8.0: "8 Hours",
    10.0: "10 Hours",
}

_HASHTAGS_COMMON = "#SleepSounds #AmbientSounds #RelaxingSounds #StudySounds #FocusSounds #ASMR #fyp #foryou #foryoupage #viral"

# Per-type static templates used when Claude API is unavailable
_TITLE_OVERRIDES: dict[str, dict[float, str]] = {
    # Exact search phrases people type — duration-specific overrides
    "brown":   {1.0: "Brown Noise 1 Hour | Study Focus & ADHD | No Music",
                8.0: "Brown Noise 8 Hours | Deep Sleep & Focus | No Music"},
    "white":   {1.0: "White Noise 1 Hour | Baby Sleep & Focus | No Music",
                8.0: "White Noise 8 Hours | Sleep & Tinnitus Relief | No Music"},
    "pink":    {1.0: "Pink Noise 1 Hour | Deep Focus & Memory | No Music",
                8.0: "Pink Noise 8 Hours | Deep Sleep & Brain Boost | No Music"},
    "grey":    {1.0: "Grey Noise 1 Hour | Tinnitus Relief & Focus | No Music",
                8.0: "Grey Noise 8 Hours | Sleep & Tinnitus Relief | No Music"},
    "rain":    {1.0: "Rain Sounds 1 Hour | Study & Relaxation | No Music",
                8.0: "Rain Sounds 8 Hours | Deep Sleep & Anxiety Relief | No Music"},
    "thunder": {1.0: "Thunder & Rain 1 Hour | Study Focus & Calm | No Music",
                8.0: "Thunder & Rain 8 Hours | Deep Sleep Sounds | No Music"},
}

_TEMPLATES: dict[str, dict] = {
    "brown": {
        "title": "Brown Noise {dur} | Deep Sleep & Study Focus | No Music",
        "body": (
            "Brown noise is one of the most powerful sounds for deep sleep, intense focus, and blocking out distractions. "
            "Unlike white noise, brown noise has a deeper, richer tone — often described as a low roar or rumble — "
            "that many people find more soothing and easier to fall asleep to. "
            "This {dur} of pure brown noise is perfect for studying, working from home, ADHD focus sessions, "
            "meditation, or drifting off to sleep. No music, no instruments, no talking — just pure calming noise. "
            "Great for tinnitus relief, blocking noisy neighbours, baby sleep, and anxiety reduction. "
            "Play it all night long and wake up feeling rested. New ambient sounds uploaded every day."
        ),
        "hashtags": "#BrownNoise #BrownNoiseStudy #DeepSleep #SleepAid #NoiseForSleep #ADHDFocus #StudyWithMe " + _HASHTAGS_COMMON,
        "tags": ["brown noise", "brown noise sleep", "brown noise 8 hours", "brown noise study", "deep sleep sounds",
                 "sleep aid", "ADHD focus", "study sounds", "focus sounds", "ambient noise", "sleep sounds",
                 "relaxing sounds", "noise for sleeping", "brown noise for babies", "tinnitus relief",
                 "work from home sounds", "concentration sounds", "calming sounds", "no music sleep", "ambient sounds"],
    },
    "white": {
        "title": "White Noise {dur} | Baby Sleep & Deep Focus | No Music",
        "body": (
            "White noise is the classic sound for blocking distractions and helping you fall asleep faster. "
            "This {dur} of pure white noise contains every frequency at equal intensity — the ultimate sound "
            "masking tool for sleep, studying, baby sleep, tinnitus relief, and concentration. "
            "White noise is proven to help babies sleep longer, reduce stress, improve focus for ADHD, "
            "and block out noisy environments like offices, apartments, or busy streets. "
            "No music, no instruments, no talking — just clean, pure white noise. "
            "Perfect as a background sound while working, reading, meditating, or sleeping. "
            "New ambient sound videos uploaded every single day."
        ),
        "hashtags": "#WhiteNoise #WhiteNoiseSleep #BabySleep #SleepAid #NoiseForSleep #TinnituRelief #StudyWithMe " + _HASHTAGS_COMMON,
        "tags": ["white noise", "white noise sleep", "white noise 8 hours", "white noise baby", "sleep sounds",
                 "baby sleep sounds", "sleep aid", "tinnitus relief", "study sounds", "focus sounds",
                 "ambient noise", "relaxing sounds", "noise for sleeping", "ADHD focus", "work from home",
                 "concentration sounds", "calming sounds", "no music sleep", "ambient sounds", "white noise fan"],
    },
    "pink": {
        "title": "Pink Noise {dur} | Deep Sleep & Brain Focus | No Music",
        "body": (
            "Pink noise is scientifically associated with deeper sleep and enhanced memory consolidation. "
            "Softer than white noise and warmer than brown noise, pink noise has a natural, balanced tone "
            "that many people find incredibly soothing and easy to drift off to. "
            "This {dur} of pure pink noise is perfect for deep sleep, studying, ADHD focus sessions, "
            "meditation, relaxation, and tinnitus masking. Research suggests pink noise may enhance slow-wave "
            "sleep and improve next-day cognitive performance. "
            "No music, no instruments, no talking — just pure pink noise. "
            "Play it all night and wake up refreshed. New sounds every day."
        ),
        "hashtags": "#PinkNoise #PinkNoiseSleep #DeepSleep #SleepScience #BrainFocus #ADHDStudy #StudyWithMe " + _HASHTAGS_COMMON,
        "tags": ["pink noise", "pink noise sleep", "pink noise 8 hours", "pink noise study", "deep sleep",
                 "sleep sounds", "sleep aid", "ADHD focus", "study sounds", "focus sounds", "ambient noise",
                 "relaxing sounds", "tinnitus relief", "concentration sounds", "calming sounds",
                 "sleep science", "brain focus", "no music sleep", "ambient sounds", "pink noise for babies"],
    },
    "grey": {
        "title": "Grey Noise {dur} | Sleep, Focus & Tinnitus Relief | No Music",
        "body": (
            "Grey noise is a specially shaped noise calibrated to match human hearing — making it one of the "
            "most neutral and comfortable sounds to listen to for extended periods. "
            "Unlike white noise which can feel harsh, grey noise is smooth and even across all frequencies as "
            "perceived by the ear, making it ideal for tinnitus relief, sensory sensitivity, and deep focus. "
            "This {dur} of pure grey noise is perfect for sleeping, studying, working, and relaxation. "
            "No music, no instruments, no talking. "
            "Try grey noise tonight and experience the difference. New ambient sounds every day."
        ),
        "hashtags": "#GreyNoise #TinnitusRelief #SleepSounds #SensoryProcessing #AmbientNoise #DeepFocus #StudyWithMe " + _HASHTAGS_COMMON,
        "tags": ["grey noise", "gray noise", "grey noise sleep", "tinnitus relief", "sensory processing",
                 "sleep sounds", "ambient noise", "focus sounds", "study sounds", "calming sounds",
                 "sleep aid", "ADHD sounds", "concentration", "relaxing sounds", "no music sleep",
                 "ambient sounds", "grey noise 8 hours", "noise for sleeping", "sleep therapy", "sound masking"],
    },
    "rain": {
        "title": "Rain Sounds {dur} | Deep Sleep & Relaxation | No Music",
        "body": (
            "The sound of falling rain is one of nature's most powerful sleep triggers. "
            "This {dur} of continuous rain sounds will help you fall asleep faster, stay asleep longer, "
            "and wake up feeling genuinely refreshed. Rain sounds work by masking background noise and "
            "activating the parasympathetic nervous system — your body's natural relaxation response. "
            "Perfect for sleep, studying, reading, meditation, yoga, or simply unwinding after a long day. "
            "No music, no instruments, no talking — just pure, beautiful rain. "
            "Rain sounds are loved worldwide by people who struggle with insomnia, anxiety, stress, "
            "or noisy environments. New nature sounds uploaded every single day."
        ),
        "hashtags": "#RainSounds #RainfallSleep #SleepSounds #NatureSounds #RainASMR #RelaxingRain #StudyWithMe " + _HASHTAGS_COMMON,
        "tags": ["rain sounds", "rain sounds for sleeping", "rain sounds 8 hours", "rainfall sleep",
                 "nature sounds", "sleep sounds", "relaxing rain", "rain ASMR", "sleep aid",
                 "study sounds", "focus sounds", "ambient rain", "calming sounds", "rain meditation",
                 "rain for anxiety", "heavy rain sleep", "no music sleep", "ambient sounds",
                 "rain sounds study", "rainfall ambiance"],
    },
    "thunder": {
        "title": "Thunder & Rain Sounds {dur} | Deep Sleep | No Music",
        "body": (
            "There is something deeply primal and calming about the sound of a thunderstorm. "
            "This {dur} of thunder and rain sounds combines the rhythmic patter of rainfall with "
            "distant rolling thunder — creating the perfect soundscape for deep sleep, relaxation, "
            "and stress relief. Thunder sounds trigger a relaxation response in many people, "
            "similar to the feeling of being safe and cosy indoors during a storm. "
            "Perfect for sleep, meditation, studying, or simply unwinding. "
            "No music, no instruments — pure nature. New sounds every day."
        ),
        "hashtags": "#ThunderSounds #Thunderstorm #RainThunder #SleepSounds #StormSounds #NatureSounds #StudyWithMe " + _HASHTAGS_COMMON,
        "tags": ["thunder sounds", "thunderstorm sleep", "thunder and rain", "storm sounds sleep",
                 "rain and thunder 8 hours", "nature sounds", "sleep sounds", "thunderstorm ASMR",
                 "sleep aid", "relaxing storm", "ambient sounds", "calming sounds", "study sounds",
                 "thunder rain meditation", "no music sleep", "thunderstorm sounds", "heavy rain thunder",
                 "sleep thunderstorm", "storm ambiance", "nature sleep sounds"],
    },
    "forest": {
        "title": "Forest Sounds {dur} | Birds & Nature Sleep Sounds | No Music",
        "body": (
            "Step into a peaceful forest with this {dur} of pure nature ambiance. "
            "Rustling leaves, birdsong, gentle wind through the trees — the sounds of the forest "
            "are proven to reduce cortisol levels, lower blood pressure, and promote deep relaxation. "
            "Forest sounds are used worldwide for sleep therapy, meditation, mindfulness, stress relief, "
            "and focus. Whether you are studying, working, meditating, or trying to fall asleep, "
            "this rich natural soundscape will help you escape the noise of everyday life. "
            "No music, no instruments — pure forest. New nature sounds every day."
        ),
        "hashtags": "#ForestSounds #NatureSounds #BirdSounds #SleepSounds #ForestASMR #NatureTherapy #StudyWithMe " + _HASHTAGS_COMMON,
        "tags": ["forest sounds", "forest sounds sleep", "nature sounds", "bird sounds sleep",
                 "forest ambiance", "sleep sounds", "relaxing nature", "forest ASMR", "sleep aid",
                 "nature therapy", "study sounds", "focus sounds", "calming nature", "forest meditation",
                 "no music sleep", "ambient sounds", "forest 8 hours", "birdsong sleep",
                 "woodland sounds", "nature sleep sounds"],
    },
    "ocean": {
        "title": "Ocean Waves {dur} | Sleep & Relaxation Sounds | No Music",
        "body": (
            "The rhythmic sound of ocean waves is one of the most universally calming sounds on Earth. "
            "This {dur} of gentle ocean waves will help you fall asleep, reduce anxiety, "
            "ease stress, and enter a deep meditative state. Ocean sounds synchronise with your "
            "breathing and heart rate, gently guiding you towards relaxation and sleep. "
            "Perfect for insomnia, anxiety relief, meditation, yoga, studying, or simply unwinding. "
            "No music, no instruments — just the pure, timeless sound of the sea. "
            "New calming sounds uploaded every single day."
        ),
        "hashtags": "#OceanWaves #OceanSounds #WaveSounds #SleepSounds #BeachSounds #NatureSounds #StudyWithMe " + _HASHTAGS_COMMON,
        "tags": ["ocean waves", "ocean sounds sleep", "wave sounds", "beach sounds sleep",
                 "ocean sounds 8 hours", "nature sounds", "sleep sounds", "ocean ASMR", "sleep aid",
                 "relaxing waves", "study sounds", "focus sounds", "calming ocean", "ocean meditation",
                 "no music sleep", "ambient sounds", "sea sounds", "coastal sounds",
                 "ocean ambiance", "waves for sleeping"],
    },
    "stream": {
        "title": "Stream & Creek Sounds {dur} | Sleep & Focus | No Music",
        "body": (
            "The gentle babbling of a forest stream is one of nature's most soothing sounds. "
            "This {dur} of flowing water sounds — a peaceful creek winding through a quiet forest — "
            "is perfect for sleep, deep focus, meditation, yoga, and stress relief. "
            "The sound of moving water has a natural white-noise quality that masks background distractions "
            "while remaining organic, warm, and pleasant to listen to for hours. "
            "No music, no instruments — pure flowing water. New nature sounds every day."
        ),
        "hashtags": "#StreamSounds #CreekSounds #FlowingWater #NatureSounds #SleepSounds #WaterSounds #StudyWithMe " + _HASHTAGS_COMMON,
        "tags": ["stream sounds", "creek sounds", "flowing water sounds", "water sounds sleep",
                 "babbling brook", "nature sounds", "sleep sounds", "water ASMR", "sleep aid",
                 "relaxing water", "study sounds", "focus sounds", "calming water", "water meditation",
                 "no music sleep", "ambient sounds", "stream 8 hours", "forest stream",
                 "river sounds", "nature sleep sounds"],
    },
    "fireplace": {
        "title": "Fireplace Sounds {dur} | Cozy Sleep & Relaxation | No Music",
        "body": (
            "Curl up and relax with this {dur} of warm, crackling fireplace sounds. "
            "The gentle crackle and pop of a real wood fire creates the ultimate cosy atmosphere "
            "for sleep, reading, studying, or simply unwinding on a cold night. "
            "Fireplace sounds are deeply comforting — they evoke warmth, safety, and peace, "
            "making them perfect for insomnia, anxiety, stress relief, and winter relaxation. "
            "No music, no instruments — just the pure, authentic sound of a wood fire. "
            "New cosy ambient sounds uploaded every day."
        ),
        "hashtags": "#FireplaceSounds #FireSounds #CozySounds #SleepSounds #FireplaceASMR #WinterSounds #StudyWithMe " + _HASHTAGS_COMMON,
        "tags": ["fireplace sounds", "fire crackling", "fireplace sleep", "cozy sounds", "fire sounds ASMR",
                 "sleep sounds", "relaxing fire", "fireplace ambiance", "sleep aid", "winter sounds",
                 "study sounds", "focus sounds", "calming fire", "fireplace meditation",
                 "no music sleep", "ambient sounds", "crackling fire 8 hours", "wood fire sounds",
                 "cozy fireplace", "fire sleep sounds"],
    },
    "cafe": {
        "title": "Café Ambiance {dur} | Study & Focus Sounds | No Music",
        "body": (
            "Some people focus best in a busy café — the gentle hum of conversation, the clinking of cups, "
            "the ambient noise of a coffee shop creates the perfect level of background stimulation for "
            "deep work, studying, writing, and creative thinking. "
            "This {dur} of authentic café ambiance brings the coffee shop experience to wherever you are. "
            "No music, no instruments — just real café sounds that help your brain enter a productive flow state. "
            "Perfect for work from home, studying, writing, or any task that benefits from gentle background noise. "
            "New focus sounds uploaded every single day."
        ),
        "hashtags": "#CaféSounds #CoffeeshopSounds #StudyWithMe #FocusSounds #LoFiVibes #WorkFromHome #StudySounds " + _HASHTAGS_COMMON,
        "tags": ["cafe sounds", "coffee shop sounds", "cafe ambiance study", "coffeeshop ambiance",
                 "study sounds", "focus sounds", "work from home sounds", "cafe background noise",
                 "productivity sounds", "deep work sounds", "ambient cafe", "coffee shop ASMR",
                 "study with me", "writing sounds", "no music study", "ambient sounds",
                 "cafe sounds 8 hours", "coffee shop background", "cafe white noise", "focus ambiance"],
    },
}


def _duration_label(hours: float) -> str:
    if hours in _DURATION_LABELS:
        return _DURATION_LABELS[hours]
    if hours < 1:
        return f"{int(hours * 60)} Minutes"
    return f"{int(hours)} Hours"


def _template_fallback(sound_type: str, duration_hours: float) -> dict:
    dur = _duration_label(duration_hours)
    tmpl = _TEMPLATES.get(sound_type, _TEMPLATES["brown"])
    label = SOUND_LABELS.get(sound_type, sound_type.title())

    override = _TITLE_OVERRIDES.get(sound_type, {}).get(duration_hours)
    title = override if override else tmpl["title"].replace("{dur}", dur)
    body = tmpl["body"].replace("{dur}", dur.lower())
    cta = (
        "🔔 Subscribe for daily sleep & focus sounds — new video every day!\n"
        "👍 Like if this helped you sleep, study, or relax."
    )
    description = f"{cta}\n\n{body}\n\n{tmpl['hashtags']}"

    return {
        "title": title[:100],
        "description": description[:5000],
        "tags": tmpl["tags"],
    }


_SYSTEM = """\
You write YouTube metadata for an ambient sound channel. The channel features pure \
nature and ambient noise sounds: rain, ocean, forest, fireplace, café ambiance, and \
coloured noise (white/brown/pink/grey). There is NO music, NO instruments, NO singing. \
Content is suitable for sleep, study, focus, relaxation, and meditation. \
The channel targets a broad global audience including Muslim listeners who avoid music.

Rules for every response:
- Never use the word "music", "song", "melody", "beat", "rhythm", or any instrument name.
- Use SEO-friendly phrases like "sleep sounds", "study sounds", "focus sounds", "relaxing sounds", \
"white noise", "ASMR", "nature ambiance", "calming sounds", "ambient sounds".
- Title formula: "[Sound Name] [Duration] | [Benefit 1] & [Benefit 2] | No Music". \
Sound name + duration come FIRST (best for SEO — people search the exact phrase). \
Example: "Brown Noise 8 Hours | Deep Sleep & ADHD Focus | No Music". \
Always end with "| No Music". Keep it under 100 characters. \
Include the EXACT duration number (e.g. "8 Hours", "1 Hour") right after the sound name.
- Description structure (in this order):
  1. First 2 lines: strong CTA — "🔔 Subscribe for daily sleep & focus sounds — new video every day!" and "👍 Like if this helped you sleep, study, or relax."
  2. One blank line.
  3. Main body: 180–240 words of naturally worked-in SEO keywords.
  4. One blank line.
  5. 10–12 hashtags on their own line, e.g. #BrownNoise #SleepSounds #Relaxation. \
Hashtags must be single words or CamelCase (no spaces). \
ALWAYS include #fyp #foryou #foryoupage #viral as the LAST four hashtags — every single video.
- Tags: 18–22 tags, mix of broad and specific.
- Respond ONLY with valid JSON — no prose, no markdown fences.
"""

_USER_TEMPLATE = """\
Sound type: {label}
Duration: {duration_label}
Extra context (optional): {context}

Generate YouTube metadata JSON with these exact keys:
{{
  "title": "...",
  "description": "... (body text) ...\\n\\n#Hashtag1 #Hashtag2 #Hashtag3 ...",
  "tags": ["...", "..."]
}}
"""


class MetadataWriter:
    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        self.model = model

    def generate(
        self,
        sound_type: str,
        duration_hours: float,
        extra_context: str = "",
    ) -> dict[str, str | list[str]]:
        label = SOUND_LABELS.get(sound_type, sound_type.replace("_", " ").title())
        dur_label = _duration_label(duration_hours)

        if ANTHROPIC_API_KEY:
            try:
                return self._generate_with_claude(label, dur_label, extra_context)
            except Exception as e:
                if "credit" in str(e).lower() or "balance" in str(e).lower() or "400" in str(e):
                    print(f"    Claude API unavailable (credits?), using built-in template.")
                else:
                    print(f"    Claude API error: {e} — using built-in template.")

        return _template_fallback(sound_type, duration_hours)

    def _generate_with_claude(self, label, dur_label, extra_context) -> dict:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = _USER_TEMPLATE.format(
            label=label,
            duration_label=dur_label,
            context=extra_context or "none",
        )
        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        metadata = json.loads(raw)
        for key in ("title", "description", "tags"):
            if key not in metadata:
                raise ValueError(f"Missing key {key!r} in metadata response")
        return metadata

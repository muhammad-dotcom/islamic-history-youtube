"""Visual generation — provider priority:

  1. Higgsfield  — cinematic AI video clips  (HIGGSFIELD_API_KEY set + correct API URL)
  2. DALL-E 3    — AI historical images       (OPENAI_API_KEY set)
  3. Met Museum  — real Islamic art (free, no key, always available as final fallback)

Each call returns a Path to a local file (.mp4 or .jpg).
The assembler handles both formats.
"""

from __future__ import annotations

import random
import time
from pathlib import Path

import httpx

from .config import HIGGSFIELD_API_KEY, HIGGSFIELD_API_URL, OPENAI_API_KEY, PIXABAY_API_KEY

_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}


def _download(url: str, out_path: Path) -> None:
    """Download any URL to a file using browser-like headers."""
    with httpx.Client(timeout=60, headers=_BROWSER_HEADERS, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        out_path.write_bytes(r.content)

# ---------------------------------------------------------------------------
# Higgsfield provider
# ---------------------------------------------------------------------------

class HiggsFieldError(RuntimeError):
    pass


def _higgsfield_generate(prompt: str, out_path: Path, duration: int = 6) -> Path:
    headers = {
        "Authorization": f"Bearer {HIGGSFIELD_API_KEY}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            HIGGSFIELD_API_URL,
            headers=headers,
            json={"prompt": prompt, "duration": duration, "aspect_ratio": "16:9", "style": "cinematic"},
        )
        resp.raise_for_status()
        job = resp.json()
        job_id = job.get("id") or job.get("job_id")
        if not job_id:
            raise HiggsFieldError(f"No job ID in response: {job}")

        base = HIGGSFIELD_API_URL.rsplit("/", 1)[0]
        for _ in range(60):
            time.sleep(5)
            poll = client.get(f"{base}/jobs/{job_id}", headers=headers)
            poll.raise_for_status()
            data = poll.json()
            status = data.get("status", "")
            if status == "completed":
                video_url = data.get("video_url") or data.get("output_url")
                if not video_url:
                    raise HiggsFieldError(f"No video URL in completed job: {data}")
                _download(video_url, out_path)
                return out_path
            if status in ("failed", "error"):
                raise HiggsFieldError(f"Higgsfield job failed: {data}")
        raise HiggsFieldError("Higgsfield job timed out")


# ---------------------------------------------------------------------------
# DALL-E 3 provider
# ---------------------------------------------------------------------------

def _dalle3_generate(prompt: str, out_path: Path) -> Path:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.generate(
        model="dall-e-3",
        prompt="Historical documentary style. Cinematic, photorealistic, dramatic lighting. No text, no watermarks. " + prompt,
        size="1792x1024",
        quality="standard",
        n=1,
    )
    _download(response.data[0].url, out_path)
    return out_path


# ---------------------------------------------------------------------------
# Pixabay provider (free API key, huge library, Islamic history images)
# ---------------------------------------------------------------------------

_PIXABAY_API = "https://pixabay.com/api/"

def _pixabay_generate(prompt: str, out_path: Path, used_urls: set) -> Path:
    query = _extract_keywords(prompt)
    queries = [query]
    if " " in query:
        queries.append(query.split()[0])
    queries += ["Islamic architecture", "Islamic history", "ancient mosque", "medieval Arabia"]

    with httpx.Client(timeout=30, headers=_BROWSER_HEADERS) as client:
        for q in queries:
            resp = client.get(_PIXABAY_API, params={
                "key": PIXABAY_API_KEY, "q": q,
                "image_type": "photo", "orientation": "horizontal",
                "min_width": 1280, "safesearch": "true",
                "per_page": 20, "order": "popular",
            })
            if resp.status_code != 200:
                continue
            hits = [h["largeImageURL"] for h in resp.json().get("hits", [])
                    if h.get("largeImageURL") and h["largeImageURL"] not in used_urls]
            random.shuffle(hits)
            for url in hits:
                for attempt in range(3):  # retry up to 3x on transient CDN errors
                    try:
                        _download(url, out_path)
                        used_urls.add(url)
                        return out_path
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code < 500 or attempt == 2:
                            break  # 4xx or exhausted retries — try next image
                        time.sleep(1)
                    except Exception:
                        break  # non-HTTP error — try next image

    raise RuntimeError(f"Pixabay exhausted all queries for: {prompt[:60]!r}")


# ---------------------------------------------------------------------------
# Wikipedia / Wikimedia Commons provider (free, no key, always works)
# ---------------------------------------------------------------------------

_WIKI_HEADERS = {"User-Agent": "IslamicHistoryYouTube/1.0 (educational channel; non-commercial)"}
_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_WIKI_API = "https://en.wikipedia.org/w/api.php"

# Broad fallback queries guaranteed to return results
_FALLBACK_QUERIES = [
    "Islamic architecture mosque",
    "Abbasid caliphate",
    "Islamic art manuscript",
    "Arabian night city",
    "Ottoman Empire",
    "medieval Islam",
]

_NOISE = {
    "cinematic", "photorealistic", "dramatic", "lighting", "aerial", "view", "style",
    "detailed", "ancient", "historical", "scene", "era", "century", "showing",
    "depicting", "featuring", "surrounded", "illuminated", "with", "the", "and",
    "its", "at", "in", "of", "a", "an", "peak", "perfect", "warm", "golden",
    "rich", "busy", "vast", "dusty", "narrow", "crowded", "towering", "majestic",
    "grand", "ornate", "intricate", "glowing", "vibrant", "bustling", "from",
    "over", "under", "into", "onto", "through", "between", "during", "within",
}


def _extract_keywords(prompt: str) -> str:
    words = [w.strip(".,;:()-'\"") for w in prompt.split()]
    # Prioritise capitalised words (proper nouns: Baghdad, Saladin, etc.)
    proper = [w for w in words if w and w[0].isupper() and w.lower() not in _NOISE and len(w) > 2]
    other  = [w for w in words if w and w[0].islower() and w.lower() not in _NOISE and len(w) > 5]
    combined = proper + other
    return " ".join(combined[:4]) if combined else "Islamic history"


def _page_image(title: str, client: httpx.Client, used_urls: set) -> str | None:
    resp = client.get(
        _WIKI_API,
        params={"action": "query", "titles": title, "prop": "pageimages",
                "pithumbsize": 1920, "format": "json"},
    )
    if resp.status_code != 200:
        return None
    for page in resp.json().get("query", {}).get("pages", {}).values():
        src = page.get("thumbnail", {}).get("source", "")
        if src and src not in used_urls:
            return src
    return None


def _wiki_article_search(query: str, client: httpx.Client, used_urls: set) -> str | None:
    """Search Wikipedia for articles matching query, return main image of first hit."""
    resp = client.get(
        _WIKI_API,
        params={"action": "query", "list": "search", "srsearch": query,
                "srlimit": 5, "format": "json"},
    )
    if resp.status_code != 200:
        return None
    for article in resp.json().get("query", {}).get("search", []):
        url = _page_image(article["title"], client, used_urls)
        if url:
            return url
    return None


def _commons_search(query: str, client: httpx.Client, used_urls: set) -> str | None:
    resp = client.get(
        _COMMONS_API,
        params={
            "action": "query", "generator": "search",
            "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 20,
            "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 1920,
            "format": "json",
        },
    )
    if resp.status_code != 200:
        return None
    candidates = []
    for page in resp.json().get("query", {}).get("pages", {}).values():
        for info in page.get("imageinfo", []):
            if info.get("mime", "") in ("image/jpeg", "image/png"):
                url = info.get("thumburl") or info.get("url", "")
                if url and url not in used_urls:
                    candidates.append(url)
    return random.choice(candidates) if candidates else None


def _wiki_generate(prompt: str, out_path: Path, used_urls: set) -> Path:
    query = _extract_keywords(prompt)
    with httpx.Client(headers=_WIKI_HEADERS, timeout=30) as client:
        url = (
            _wiki_article_search(query, client, used_urls)
            or _wiki_article_search(query.split()[0] if " " in query else query, client, used_urls)
            or _commons_search(f"Islamic {query}", client, used_urls)
            or _commons_search(query, client, used_urls)
        )
        # Last resort: cycle through broad fallbacks
        if not url:
            for fallback in _FALLBACK_QUERIES:
                url = _commons_search(fallback, client, used_urls)
                if url:
                    break

        if not url:
            raise RuntimeError(f"All visual sources exhausted for: {query!r}")

        _download(url, out_path)
        used_urls.add(url)
    return out_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_batch(prompts: list[str], staging_dir: Path) -> list[Path]:
    """Generate one visual per prompt. Returns list of local file paths."""
    staging_dir.mkdir(parents=True, exist_ok=True)

    use_higgsfield = bool(HIGGSFIELD_API_KEY and HIGGSFIELD_API_URL)
    use_dalle = bool(OPENAI_API_KEY)
    use_pixabay = bool(PIXABAY_API_KEY)
    used_urls: set = set()

    paths: list[Path] = []
    for i, prompt in enumerate(prompts, 1):
        print(f"  Visual {i}/{len(prompts)}: {prompt[:60]}...")

        if use_higgsfield:
            out = staging_dir / f"visual_{i:02d}.mp4"
            try:
                paths.append(_higgsfield_generate(prompt, out))
                continue
            except HiggsFieldError as e:
                print(f"    Higgsfield failed ({e}), falling back...")

        if use_dalle:
            out = staging_dir / f"visual_{i:02d}.jpg"
            try:
                paths.append(_dalle3_generate(prompt, out))
                continue
            except Exception as e:
                print(f"    DALL-E 3 failed ({e}), falling back...")

        if use_pixabay:
            out = staging_dir / f"visual_{i:02d}.jpg"
            try:
                paths.append(_pixabay_generate(prompt, out, used_urls))
                continue
            except Exception as e:
                print(f"    Pixabay failed ({e}), falling back to Wikipedia...")

        # Wikipedia/Commons last resort
        out = staging_dir / f"visual_{i:02d}.jpg"
        paths.append(_wiki_generate(prompt, out, used_urls))

    return paths

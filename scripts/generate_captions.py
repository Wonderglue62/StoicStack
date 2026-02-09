"""
Caption & Hashtag Generator for Stoic Content Pipeline
=======================================================
Generates platform-specific captions, hashtags, and CTAs for each video.

Usage:
    python generate_captions.py 2026-02-10
"""

import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CALENDAR_DIR = PROJECT_ROOT / "calendar"
OUTPUT_DIR = PROJECT_ROOT / "output" / "drafts"

# Hashtag pools
CORE_HASHTAGS = [
    "#stoicism", "#stoic", "#marcusaurelius", "#philosophy", "#wisdom",
    "#mindset", "#motivation", "#selfimprovement", "#mentalhealth",
]

ROTATING_HASHTAGS = {
    "resilience": ["#resilience", "#strength", "#nevergiveup", "#innerstrength", "#perseverance"],
    "mindset": ["#mindsetshift", "#growthmindset", "#positivethinking", "#mindfulness", "#awareness"],
    "discipline": ["#discipline", "#habits", "#consistency", "#grind", "#focus"],
    "calm": ["#innerpeace", "#calm", "#peace", "#serenity", "#stillness"],
    "intense": ["#warrior", "#beast", "#unstoppable", "#noexcuses", "#hustle"],
    "morning": ["#morningroutine", "#morningmotivation", "#goodmorning", "#riseandgrind"],
    "night": ["#nightthoughts", "#beforeyousleep", "#latenight", "#reflection"],
    "love": ["#selflove", "#love", "#relationships", "#acceptance"],
    "death": ["#mementomori", "#mortality", "#life", "#legacy"],
    "action": ["#action", "#justdoit", "#starttoday", "#noexcuses"],
}

SERIES_HASHTAGS = {
    "Morning Stoic": ["#morningstoic", "#dailystoic", "#morningwisdom"],
    "Marcus Aurelius Said...": ["#marcusaurelius", "#meditations", "#romanemperor"],
    "Stoic Thought of the Day": ["#stoicquote", "#dailyquote", "#thoughtoftheday"],
    "Wake Up, Warrior": ["#warrior", "#wakeup", "#motivation", "#strength"],
    "Stoic Response To...": ["#stoicadvice", "#modernproblems", "#ancientwisdom"],
    "One Quote That Changes Everything": ["#onequote", "#lifechanger", "#wisdom"],
    "Seneca's Letters": ["#seneca", "#senecaletters", "#stoicphilosophy"],
    "Ancient Wisdom in 60 Seconds": ["#ancientwisdom", "#philosophy", "#60seconds"],
    "Stoic vs. Modern": ["#stoicvsmodern", "#thenandnow", "#perspective"],
    "Before You Sleep": ["#beforeyousleep", "#nightwisdom", "#reflection"],
    "The Obstacle Is The Way": ["#obstacleistheway", "#amorFati", "#overcome"],
    "Silent Stoic": ["#silentstoic", "#nowords", "#cinematic", "#stoicquotes"],
}

PLATFORM_CONFIG = {
    "tiktok": {
        "max_caption_length": 2200,
        "max_hashtags": 15,
        "style": "casual, hook-first, emoji-light",
        "cta_style": "Follow for daily stoic wisdom",
    },
    "instagram": {
        "max_caption_length": 2200,
        "max_hashtags": 30,
        "style": "slightly more polished, paragraph format",
        "cta_style": "Save this for later. Follow @{handle} for daily wisdom.",
    },
    "facebook": {
        "max_caption_length": 500,
        "max_hashtags": 5,
        "style": "conversational, question-based",
        "cta_style": "Share this with someone who needs to hear it.",
    },
    "x": {
        "max_caption_length": 280,
        "max_hashtags": 3,
        "style": "punchy, quote-forward",
        "cta_style": "",
    },
    "youtube_shorts": {
        "max_caption_length": 100,
        "max_hashtags": 3,
        "style": "minimal, keyword-focused title",
        "cta_style": "",
    },
}


def select_hashtags(series: str, themes: list[str], energy: str, max_count: int = 15) -> list[str]:
    """Select a relevant mix of hashtags."""
    tags = set()

    # Core (always include 5-6)
    tags.update(CORE_HASHTAGS[:6])

    # Series-specific (2-3)
    series_tags = SERIES_HASHTAGS.get(series, [])
    tags.update(series_tags[:3])

    # Theme-based rotating (3-5)
    for theme in themes:
        if theme in ROTATING_HASHTAGS:
            tags.update(ROTATING_HASHTAGS[theme][:2])

    # Energy-based (1-2)
    if energy in ROTATING_HASHTAGS:
        tags.update(ROTATING_HASHTAGS[energy][:2])

    # Trim to max
    return sorted(list(tags))[:max_count]


def generate_tiktok_caption(video: dict) -> str:
    """Generate a TikTok-optimized caption."""
    quote = video.get("quote", "")
    series = video.get("series", "")
    hook = video.get("script_hook", "")

    # TikTok: hook first, then context
    if hook:
        caption = f"{hook}\n\n"
    else:
        caption = f'"{quote}"\n\n'

    if series == "Silent Stoic":
        caption = f'"{quote}"\n\n'
    elif series == "Stoic Thought of the Day":
        caption = f'"{quote}"\n\nLet this sit with you today.\n\n'
    elif "Response To" in series:
        topic = video.get("topic", "")
        caption += f"The stoic answer to {topic.lower()}.\n\n"
    else:
        caption += "Follow for daily stoic wisdom.\n\n"

    return caption


def generate_instagram_caption(video: dict, handle: str = "yourbrand") -> str:
    """Generate an Instagram-optimized caption."""
    quote = video.get("quote", "")
    series = video.get("series", "")

    caption = f'"{quote}"\n\n'

    if video.get("script_body"):
        # Take first 2 sentences of script as caption body
        sentences = video["script_body"].split(". ")
        caption += ". ".join(sentences[:2]) + ".\n\n"

    caption += f"Save this for when you need it.\n"
    caption += f"Follow @{handle} for daily stoic wisdom.\n\n"

    return caption


def generate_x_caption(video: dict) -> str:
    """Generate an X/Twitter-optimized caption."""
    quote = video.get("quote", "")
    source = video.get("source", "")

    caption = f'"{quote}"'
    if source:
        caption += f" -- {source}"

    # Keep under 280 chars, leave room for hashtags
    if len(caption) > 230:
        caption = caption[:227] + "..."

    return caption


def generate_captions_for_day(target_date: str) -> dict:
    """Generate all captions for a day's videos."""
    # Load from calendar
    for cal_file in sorted(CALENDAR_DIR.glob("*.json")):
        with open(cal_file, "r", encoding="utf-8") as f:
            calendar = json.load(f)
        if target_date in calendar.get("days", {}):
            day_data = calendar["days"][target_date]
            break
    else:
        print(f"No calendar entry for {target_date}")
        return {}

    all_captions = {
        "date": target_date,
        "videos": [],
    }

    print(f"\n{'='*60}")
    print(f"  CAPTION GENERATION: {target_date}")
    print(f"{'='*60}\n")

    for video in day_data.get("videos", []):
        themes = []
        energy = video.get("voice_profile", "calm").lower()
        if "intense" in energy:
            energy = "intense"
        elif "calm" in energy:
            energy = "calm"

        hashtags = select_hashtags(
            video.get("series", ""),
            themes,
            energy,
            max_count=15,
        )

        captions = {
            "slot": video.get("slot"),
            "series": video.get("series"),
            "tiktok": {
                "caption": generate_tiktok_caption(video),
                "hashtags": " ".join(hashtags[:15]),
            },
            "instagram": {
                "caption": generate_instagram_caption(video),
                "hashtags": " ".join(hashtags[:30]),
            },
            "x": {
                "caption": generate_x_caption(video),
                "hashtags": " ".join(hashtags[:3]),
            },
            "facebook": {
                "caption": generate_tiktok_caption(video),  # Reuse TikTok style
                "hashtags": " ".join(hashtags[:5]),
            },
        }

        all_captions["videos"].append(captions)
        print(f"  [{video.get('slot', 0):2d}/12] {video.get('series', '')} -- captions generated for 4 platforms")

    # Save
    output_path = OUTPUT_DIR / target_date
    output_path.mkdir(parents=True, exist_ok=True)
    captions_file = output_path / "captions.json"
    with open(captions_file, "w", encoding="utf-8") as f:
        json.dump(all_captions, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved to: {captions_file}")
    return all_captions


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    generate_captions_for_day(target)

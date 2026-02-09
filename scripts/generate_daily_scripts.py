"""
Daily Script Generator for Stoic Content Pipeline
==================================================
Reads the weekly calendar and quote database, generates full video scripts
for the day using Anthropic Claude API, and outputs them for review.

Usage:
    python generate_daily_scripts.py                  # Generate for today
    python generate_daily_scripts.py 2026-02-10       # Generate for specific date
    python generate_daily_scripts.py 2026-02-10 --dry # Preview without API calls
"""

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

# --- Configuration ---
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

CALENDAR_DIR = PROJECT_ROOT / "calendar"
QUOTE_DB_PATH = PROJECT_ROOT / "scripts" / "quote_database.json"
OUTPUT_DIR = PROJECT_ROOT / "output" / "drafts"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SERIES_SYSTEM_PROMPTS = {
    "Morning Stoic": (
        "You are a calm, wise narrator for a stoic philosophy video series. "
        "Write a 60-75 second voiceover script. Tone: warm, contemplative, like a trusted mentor "
        "speaking gently at dawn. Start with the hook provided, then expand on the quote with "
        "a brief interpretation and a practical takeaway for today. End with the CTA provided. "
        "Do NOT use clickbait. Be genuine and thoughtful. Target: 150-180 words."
    ),
    "Marcus Aurelius Said...": (
        "You are a dramatic, knowledgeable historian narrating a video about Marcus Aurelius. "
        "Write a 60-70 second voiceover script. Tone: authoritative, slightly intense, reverent. "
        "Provide historical context about when/why Marcus wrote this, then connect it to modern life. "
        "Use the hook provided. End with the CTA. Target: 150-170 words."
    ),
    "Stoic Thought of the Day": (
        "This is a TEXT-ONLY video. No voiceover script needed. "
        "Generate ONLY: 1) The quote formatted for on-screen text display, "
        "2) A 1-sentence subtitle/tagline to appear below the quote, "
        "3) Suggested text animation timing (when each line appears). "
        "Keep it minimal and elegant."
    ),
    "Wake Up, Warrior": (
        "You are an intense, commanding motivational speaker. "
        "Write a 65-75 second voiceover script. Tone: aggressive, no-nonsense, like a drill sergeant "
        "who actually cares about you. Short punchy sentences. Dramatic pauses noted with [PAUSE]. "
        "Challenge the viewer directly. Use 'you' frequently. Start with the hook. End with CTA. "
        "Target: 160-180 words."
    ),
    "Stoic Response To...": (
        "You are a thoughtful advisor applying ancient Stoic philosophy to a specific modern problem. "
        "Write a 65-80 second voiceover script. Structure: 1) Acknowledge the modern problem with empathy, "
        "2) Introduce the Stoic perspective, 3) Give a practical step the viewer can take TODAY. "
        "Include one relevant statistic or study if applicable. Tone: empathetic but firm. "
        "Target: 160-190 words."
    ),
    "One Quote That Changes Everything": (
        "You are a dramatic storyteller revealing a life-changing insight. "
        "Write a 60-70 second voiceover script. Build tension with the hook, reveal the quote, "
        "then explain WHY it changes everything with a specific example or story. "
        "Tone: dramatic, building, cinematic. Target: 150-170 words."
    ),
    "Seneca's Letters": (
        "You are a literary scholar reading and interpreting Seneca's correspondence. "
        "Write a 60-75 second voiceover script. Briefly set the scene (who Seneca was writing to, why), "
        "share the core insight, then translate it for a 2026 audience. "
        "Tone: intimate, intellectual, like a fireside conversation. Target: 150-180 words."
    ),
    "Ancient Wisdom in 60 Seconds": (
        "You are a cross-cultural philosophy educator. This series covers wisdom BEYOND Stoicism. "
        "Write a 60 second voiceover script. Introduce the thinker, share the quote, connect it to "
        "modern science or psychology if possible. Tone: curious, accessible, mind-expanding. "
        "Target: 140-155 words."
    ),
    "Stoic vs. Modern": (
        "You are a sharp cultural commentator contrasting ancient Stoic wisdom with modern life. "
        "Write a 65-80 second voiceover script. Structure: 1) Describe the modern problem/behavior, "
        "2) Reveal what the Stoics said about it centuries ago, 3) Show the contrast is almost absurd. "
        "Use specific modern references (apps, habits, trends). Tone: witty but wise. "
        "Target: 160-190 words."
    ),
    "Before You Sleep": (
        "You are a soothing, reflective voice guiding someone to peaceful sleep. "
        "Write a 60-70 second voiceover script. Tone: extremely calm, almost ASMR-like in pacing. "
        "Slow sentences. Gentle reflections. Guide the listener to release the day's worries. "
        "End with a thought to carry into sleep. Target: 140-165 words."
    ),
    "The Obstacle Is The Way": (
        "You are a coach helping someone through a specific life crisis using Stoic philosophy. "
        "Write a 65-75 second voiceover script. Name the specific obstacle (from the topic). "
        "Acknowledge how hard it is. Then reframe it using the Stoic concept of 'amor fati' and "
        "the obstacle being the way. Give a real-world example of someone who turned this obstacle "
        "into their greatest advantage. Tone: empathetic then empowering. Target: 160-180 words."
    ),
    "Silent Stoic": (
        "This is a NO-VOICEOVER video. Generate ONLY: "
        "1) The quote broken into lines for cinematic text reveal, "
        "2) Suggested timing for each line appearance (e.g., 0:00-0:08 first line), "
        "3) A suggested music search term for royalty-free music. "
        "The entire video is visual + text + music only."
    ),
}


def load_calendar(target_date: str) -> dict | None:
    """Load the calendar entry for a specific date."""
    for cal_file in sorted(CALENDAR_DIR.glob("*.json")):
        with open(cal_file, "r", encoding="utf-8") as f:
            calendar = json.load(f)
        if target_date in calendar.get("days", {}):
            return calendar["days"][target_date]
    return None


def load_quote_db() -> dict:
    """Load the quote database."""
    with open(QUOTE_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def find_quote(db: dict, quote_id: str) -> dict | None:
    """Find a quote by ID in the database."""
    for category in db:
        if category == "metadata":
            continue
        for quote in db[category]:
            if quote.get("id") == quote_id:
                return quote
    return None


def generate_script_prompt(video: dict, quote_data: dict) -> str:
    """Build the user prompt for script generation."""
    series = video["series"]
    parts = [f"Series: {series}"]
    parts.append(f"Quote: \"{video.get('quote', quote_data.get('quote', ''))}\"")

    if quote_data:
        parts.append(f"Author: {quote_data.get('source', 'Unknown')}")
        parts.append(f"Themes: {', '.join(quote_data.get('theme', []))}")

    if video.get("script_hook"):
        parts.append(f"Hook (use this as the opening line): {video['script_hook']}")

    if video.get("script_cta"):
        parts.append(f"CTA (end with this): {video['script_cta']}")

    if video.get("topic"):
        parts.append(f"Modern topic to address: {video['topic']}")

    parts.append(f"Visual direction (write to match): {video.get('visual_direction', '')}")
    parts.append(f"Voice profile: {video.get('voice_profile', 'A (Calm)')}")

    return "\n".join(parts)


def call_claude(system_prompt: str, user_prompt: str) -> str:
    """Call Anthropic Claude API to generate a script. Returns the script text."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=700,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.content[0].text.strip()
    except ImportError:
        return "[ERROR] anthropic package not installed. Run: pip install anthropic"
    except Exception as e:
        return f"[ERROR] API call failed: {e}"


def generate_scripts_for_day(target_date: str, dry_run: bool = False) -> list[dict]:
    """Generate all 12 scripts for a given day."""
    day_data = load_calendar(target_date)
    if not day_data:
        print(f"No calendar entry found for {target_date}")
        return []

    quote_db = load_quote_db()
    scripts = []

    print(f"\n{'='*60}")
    print(f"  GENERATING SCRIPTS: {target_date}")
    print(f"  Theme: {day_data.get('theme_focus', 'General')}")
    print(f"  Videos: {len(day_data.get('videos', []))}")
    print(f"{'='*60}\n")

    for video in day_data.get("videos", []):
        series = video["series"]
        quote_id = video.get("quote_id", "")
        quote_data = find_quote(quote_db, quote_id) if quote_id else {}

        system_prompt = SERIES_SYSTEM_PROMPTS.get(series, "Write a 60 second video script.")
        user_prompt = generate_script_prompt(video, quote_data or {})

        print(f"  [{video['slot']:2d}/12] {series}")
        print(f"         Quote: {video.get('quote', '')[:60]}...")

        if dry_run:
            script_text = f"[DRY RUN] Would generate script for: {series} - {quote_id}"
            print(f"         Status: DRY RUN (skipped API call)")
        else:
            if not ANTHROPIC_API_KEY:
                script_text = (
                    f"[NO API KEY] Set ANTHROPIC_API_KEY environment variable.\n\n"
                    f"--- MANUAL SCRIPT NEEDED ---\n"
                    f"Series: {series}\n"
                    f"Quote: {video.get('quote', '')}\n"
                    f"Hook: {video.get('script_hook', 'N/A')}\n"
                    f"Visual direction: {video.get('visual_direction', '')}\n"
                )
                print(f"         Status: No API key -- template generated")
            else:
                script_text = call_claude(system_prompt, user_prompt)
                word_count = len(script_text.split())
                print(f"         Status: Generated ({word_count} words)")

        script_entry = {
            "slot": video["slot"],
            "series": series,
            "quote_id": quote_id,
            "quote": video.get("quote", ""),
            "voice_profile": video.get("voice_profile", ""),
            "visual_direction": video.get("visual_direction", ""),
            "music_mood": video.get("music_mood", ""),
            "script": script_text,
            "approved": False,
            "notes": "",
        }
        scripts.append(script_entry)

    # Save scripts to file
    output_path = OUTPUT_DIR / target_date
    output_path.mkdir(parents=True, exist_ok=True)
    scripts_file = output_path / "scripts.json"

    with open(scripts_file, "w", encoding="utf-8") as f:
        json.dump(scripts, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved to: {scripts_file}")
    print(f"  Review scripts, set 'approved': true for each, then proceed to voiceover.\n")

    return scripts


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    dry = "--dry" in sys.argv

    generate_scripts_for_day(target, dry_run=dry)

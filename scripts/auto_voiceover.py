"""
Automated Voiceover Generator using ElevenLabs API
====================================================
Reads approved scripts and generates voiceover audio files.

Usage:
    python auto_voiceover.py 2026-02-10
    python auto_voiceover.py 2026-02-10 --list-voices  # List available voices
"""

import json
import os
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
OUTPUT_DIR = PROJECT_ROOT / "output" / "drafts"
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"

# Voice mapping -- update these IDs after running --list-voices
# Pick a deep calm male voice for Voice A and an intense male voice for Voice B
VOICE_CONFIG = {
    "A (Calm)": {
        "voice_id": "pNInz6obpgDQGcFmaJgB",  # "Adam" -- deep, calm (default)
        "settings": {
            "stability": 0.65,
            "similarity_boost": 0.75,
            "style": 0.3,
            "speed": 0.9,
        },
    },
    "B (Intense)": {
        "voice_id": "ErXwobaYiN019PkySvjV",  # "Antoni" -- clear, intense (default)
        "settings": {
            "stability": 0.45,
            "similarity_boost": 0.80,
            "style": 0.5,
            "speed": 1.0,
        },
    },
}

SKIP_PROFILES = {"NONE", "NONE (text + music only)"}


def list_voices():
    """List available ElevenLabs voices."""
    from elevenlabs import ElevenLabs
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    response = client.voices.get_all()

    print(f"\n{'='*60}")
    print(f"  AVAILABLE VOICES")
    print(f"{'='*60}\n")

    for voice in response.voices:
        labels = voice.labels or {}
        gender = labels.get("gender", "?")
        accent = labels.get("accent", "?")
        desc = labels.get("description", "")
        print(f"  {voice.voice_id}  {voice.name:<20} {gender:<8} {accent:<12} {desc}")

    print(f"\n  Update VOICE_CONFIG in auto_voiceover.py with your preferred voice IDs.\n")


def generate_voiceover(text: str, voice_profile: str, output_path: Path) -> bool:
    """Generate a single voiceover audio file."""
    from elevenlabs import ElevenLabs

    config = VOICE_CONFIG.get(voice_profile)
    if not config:
        # Try matching partial key
        for key, val in VOICE_CONFIG.items():
            if key in voice_profile:
                config = val
                break
    if not config:
        print(f"    WARNING: Unknown voice profile '{voice_profile}', using Voice A")
        config = VOICE_CONFIG["A (Calm)"]

    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    response = client.text_to_speech.convert(
        voice_id=config["voice_id"],
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
        voice_settings=config["settings"],
    )

    # Response is a generator of bytes
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in response:
            f.write(chunk)

    file_size = output_path.stat().st_size
    if file_size < 1000:
        print(f"    WARNING: Audio file suspiciously small ({file_size} bytes)")
        return False

    size_kb = file_size / 1024
    print(f"    Saved: {output_path.name} ({size_kb:.0f} KB)")
    return True


def generate_all_voiceovers(target_date: str):
    """Generate voiceovers for all scripts of a given day."""
    scripts_file = OUTPUT_DIR / target_date / "scripts.json"
    if not scripts_file.exists():
        print(f"  No scripts found for {target_date}")
        return

    with open(scripts_file, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    day_audio_dir = AUDIO_DIR / target_date
    day_audio_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  VOICEOVER GENERATION: {target_date}")
    print(f"{'='*60}\n")

    generated = 0
    skipped = 0
    failed = 0

    for script in scripts:
        slot = script["slot"]
        series = script["series"]
        voice = script.get("voice_profile", "")
        text = script.get("script", "")

        series_slug = series.lower().replace(" ", "_").replace(".", "").replace("'", "")
        filename = f"{slot:02d}_{series_slug}.mp3"
        output_path = day_audio_dir / filename

        print(f"  [{slot:2d}/12] {series}")

        # Skip text-only and silent videos
        if voice in SKIP_PROFILES or not text or text.startswith("["):
            print(f"    Skipped (voice profile: {voice})")
            skipped += 1
            continue

        # Skip if already generated
        if output_path.exists() and output_path.stat().st_size > 1000:
            print(f"    Already exists: {filename}")
            skipped += 1
            continue

        try:
            success = generate_voiceover(text, voice, output_path)
            if success:
                generated += 1
            else:
                failed += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  DONE: {generated} generated, {skipped} skipped, {failed} failed")
    print(f"  Audio files: {day_audio_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if not ELEVENLABS_API_KEY:
        print("  ERROR: Set ELEVENLABS_API_KEY in .env")
        sys.exit(1)

    if "--list-voices" in sys.argv:
        list_voices()
    else:
        target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
        generate_all_voiceovers(target)

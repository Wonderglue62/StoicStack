"""
Automated Video Assembly using FFmpeg
=======================================
Stitches clips + voiceover + background music + text overlays into final videos.

Requires: ffmpeg installed and on PATH
    Windows: winget install ffmpeg  OR  choco install ffmpeg
    Or download from https://ffmpeg.org/download.html

Usage:
    python auto_assemble.py 2026-02-10
    python auto_assemble.py 2026-02-10 --check   # Verify ffmpeg is available
"""

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

OUTPUT_DIR = PROJECT_ROOT / "output"
DRAFTS_DIR = OUTPUT_DIR / "drafts"
FINALS_DIR = OUTPUT_DIR / "finals"
CLIPS_DIR = PROJECT_ROOT / "assets" / "clips"
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"
MUSIC_DIR = PROJECT_ROOT / "assets" / "music"

# Brand settings
BRAND_NAME = "The Inner Citadel"
FONT_FILE = "C:/Windows/Fonts/arial.ttf"  # Update if using custom font
WATERMARK_TEXT = "@theinnercitadel"

# Video settings
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
FPS = 30
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
CRF = 18  # Quality (lower = better, 18 is visually lossless)


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
        print(f"  ffmpeg found: {version_line}")
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  ERROR: ffmpeg not found. Install it:")
        print("    winget install ffmpeg")
        print("    OR download from https://ffmpeg.org/download.html")
        return False


def scale_clip(input_path: Path, output_path: Path) -> bool:
    """Scale/pad a clip to 1080x1920 (9:16)."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf", f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
               f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", VIDEO_CODEC, "-crf", str(CRF),
        "-r", str(FPS), "-an",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0


def concat_clips(clip_paths: list, output_path: Path) -> bool:
    """Concatenate multiple video clips into one."""
    # Create concat list file
    list_file = output_path.parent / "concat_list.txt"
    with open(list_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{clip}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:v", VIDEO_CODEC, "-crf", str(CRF),
        "-r", str(FPS),
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    list_file.unlink(missing_ok=True)
    return result.returncode == 0


def add_text_overlay(input_path: Path, output_path: Path, quote: str, cta: str = "") -> bool:
    """Add quote text and CTA overlay to video."""
    # Escape special characters for ffmpeg drawtext
    quote_escaped = quote.replace("'", "\\'").replace(":", "\\:").replace('"', '\\"')
    cta_escaped = cta.replace("'", "\\'").replace(":", "\\:").replace('"', '\\"') if cta else ""

    # Quote text: centered, appears at 1 second, white with shadow
    filters = [
        f"drawtext=fontfile='{FONT_FILE}':text='{quote_escaped}':"
        f"fontsize=42:fontcolor=white:borderw=2:bordercolor=black:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"enable='between(t,1,99)'"
    ]

    # Watermark: bottom right, always visible
    filters.append(
        f"drawtext=fontfile='{FONT_FILE}':text='{WATERMARK_TEXT}':"
        f"fontsize=24:fontcolor=white@0.6:borderw=1:bordercolor=black@0.4:"
        f"x=w-text_w-20:y=h-text_h-20"
    )

    # CTA text: appears in last 5 seconds
    if cta_escaped:
        filters.append(
            f"drawtext=fontfile='{FONT_FILE}':text='{cta_escaped}':"
            f"fontsize=32:fontcolor=white:borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y=h*0.85:"
            f"enable='gte(t,{max(0, 55)})'"
        )

    filter_str = ",".join(filters)

    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf", filter_str,
        "-c:v", VIDEO_CODEC, "-crf", str(CRF),
        "-c:a", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0


def mix_audio(video_path: Path, voiceover_path: Path, output_path: Path,
              music_path: Path = None) -> bool:
    """Mix voiceover (and optional music) with video."""
    if music_path and music_path.exists():
        # Mix voiceover at full volume, music at 15% volume
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(voiceover_path),
            "-i", str(music_path),
            "-filter_complex",
            "[1:a]volume=1.0[voice];"
            "[2:a]volume=0.15[music];"
            "[voice][music]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", AUDIO_CODEC,
            "-shortest",
            str(output_path),
        ]
    else:
        # Voiceover only
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(voiceover_path),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", AUDIO_CODEC,
            "-shortest",
            str(output_path),
        ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0


def assemble_video(script: dict, target_date: str, temp_dir: Path) -> bool:
    """Assemble a single video from clips + audio + text."""
    slot = script["slot"]
    series = script["series"]
    series_slug = series.lower().replace(" ", "_").replace(".", "").replace("'", "")
    filename = f"{slot:02d}_{series_slug}"

    print(f"  [{slot:2d}/12] {series}")

    day_clips_dir = CLIPS_DIR / target_date
    day_audio_dir = AUDIO_DIR / target_date
    day_finals_dir = FINALS_DIR / target_date
    day_finals_dir.mkdir(parents=True, exist_ok=True)

    final_path = day_finals_dir / f"{filename}.mp4"
    if final_path.exists() and final_path.stat().st_size > 100000:
        print(f"    Already assembled: {final_path.name}")
        return True

    # Step 1: Find clips for this video
    clip_pattern = f"{target_date}_{slot:02d}_clip"
    clip_files = sorted(day_clips_dir.glob(f"{clip_pattern}*.mp4"))

    if not clip_files:
        print(f"    WARNING: No clips found matching {clip_pattern}*.mp4")
        print(f"    Run auto_clips.py first, or place clips manually.")
        return False

    print(f"    Found {len(clip_files)} clips")

    # Step 2: Scale clips to uniform resolution
    scaled_clips = []
    for i, clip in enumerate(clip_files):
        scaled = temp_dir / f"{filename}_scaled_{i}.mp4"
        if scale_clip(clip, scaled):
            scaled_clips.append(scaled)
        else:
            print(f"    WARNING: Failed to scale {clip.name}")

    if not scaled_clips:
        print(f"    ERROR: No clips could be processed")
        return False

    # Step 3: Concatenate clips
    concat_path = temp_dir / f"{filename}_concat.mp4"
    if not concat_clips([str(c) for c in scaled_clips], concat_path):
        print(f"    ERROR: Failed to concatenate clips")
        return False
    print(f"    Clips concatenated")

    # Step 4: Add text overlay
    quote = script.get("quote", "")
    cta = script.get("script", "").split("\n")[-1] if script.get("script") else ""
    text_path = temp_dir / f"{filename}_text.mp4"
    if not add_text_overlay(concat_path, text_path, quote, cta):
        print(f"    WARNING: Text overlay failed, using video without text")
        text_path = concat_path

    # Step 5: Mix audio
    voice_profile = script.get("voice_profile", "")
    voiceover_path = day_audio_dir / f"{filename}.mp3"

    if voice_profile not in {"NONE", "NONE (text + music only)", ""} and voiceover_path.exists():
        # Find background music if available
        music_path = None
        mood = script.get("music_mood", "")
        if mood:
            # Look for music files matching the mood
            for ext in ["mp3", "wav"]:
                candidates = list(MUSIC_DIR.glob(f"*{mood.split(',')[0].strip()}*.{ext}"))
                if candidates:
                    music_path = candidates[0]
                    break

        if mix_audio(text_path, voiceover_path, final_path, music_path):
            print(f"    Audio mixed")
        else:
            print(f"    WARNING: Audio mix failed, using video without audio")
            # Copy text version as final
            import shutil
            shutil.copy2(text_path, final_path)
    else:
        # No voiceover -- just copy the text overlay version
        import shutil
        shutil.copy2(text_path, final_path)
        print(f"    No voiceover (text/silent format)")

    if final_path.exists():
        size_mb = final_path.stat().st_size / (1024 * 1024)
        print(f"    DONE: {final_path.name} ({size_mb:.1f} MB)")
        return True

    return False


def assemble_all(target_date: str):
    """Assemble all videos for a given day."""
    scripts_file = DRAFTS_DIR / target_date / "scripts.json"
    if not scripts_file.exists():
        print(f"  No scripts found for {target_date}")
        return

    with open(scripts_file, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    temp_dir = OUTPUT_DIR / "temp" / target_date
    temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  VIDEO ASSEMBLY: {target_date}")
    print(f"  Videos to assemble: {len(scripts)}")
    print(f"{'='*60}\n")

    success = 0
    failed = 0

    for script in scripts:
        try:
            if assemble_video(script, target_date, temp_dir):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            failed += 1

    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\n{'='*60}")
    print(f"  ASSEMBLY COMPLETE")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print(f"  Finals: {FINALS_DIR / target_date}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check_ffmpeg()
        sys.exit(0)

    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    if not check_ffmpeg():
        sys.exit(1)
    assemble_all(target)

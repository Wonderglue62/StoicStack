"""
Automated Clip Generator using Higgsfield Cloud API
=====================================================
Reads visual plans and generates video clips via the Higgsfield SDK.

Usage:
    python auto_clips.py 2026-02-10
    python auto_clips.py 2026-02-10 --dry       # Preview prompts without generating
    python auto_clips.py 2026-02-10 --status     # Check status of pending generations
"""

import json
import os
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Higgsfield auth via environment
os.environ["HF_API_KEY"] = os.environ.get("HIGGSFIELD_API_KEY_ID", "")
os.environ["HF_API_SECRET"] = os.environ.get("HIGGSFIELD_API_KEY_SECRET", "")

OUTPUT_DIR = PROJECT_ROOT / "output" / "drafts"
CLIPS_DIR = PROJECT_ROOT / "assets" / "clips"
LIBRARY_INDEX = CLIPS_DIR / "library_index.json"

# Model selection -- adjust based on what your plan supports
# Common models on Higgsfield: kling, wan, sora2, minimax
VIDEO_MODEL = "wan"  # Good balance of quality and credit cost
FALLBACK_MODEL = "minimax"  # Faster, cheaper fallback

# Generation settings
DEFAULT_DURATION = 10  # seconds per clip
DEFAULT_ASPECT_RATIO = "9:16"  # Portrait for social media
DEFAULT_RESOLUTION = "1080p"


def load_visual_plan(target_date: str) -> dict:
    """Load the visual plan for a given day."""
    plan_file = OUTPUT_DIR / target_date / "visual_plan.json"
    if not plan_file.exists():
        return {}
    with open(plan_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_library() -> dict:
    """Load the clip library index."""
    if LIBRARY_INDEX.exists():
        with open(LIBRARY_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"clips": [], "total_generated": 0, "total_reused": 0}


def save_library(library: dict):
    """Save the clip library index."""
    with open(LIBRARY_INDEX, "w", encoding="utf-8") as f:
        json.dump(library, f, indent=2)


def generate_clip(prompt: str, clip_id: str, output_dir: Path, model: str = None) -> dict:
    """Generate a single video clip via Higgsfield API."""
    import higgsfield_client

    model = model or VIDEO_MODEL
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"    Submitting to Higgsfield ({model})...")
    print(f"    Prompt: {prompt[:80]}...")

    try:
        result = higgsfield_client.subscribe(
            model,
            arguments={
                "prompt": prompt,
                "aspect_ratio": DEFAULT_ASPECT_RATIO,
                "duration": DEFAULT_DURATION,
            },
        )

        # Extract video URL from result
        video_url = None
        if isinstance(result, dict):
            video_url = (
                result.get("video_url")
                or result.get("url")
                or result.get("output", {}).get("video_url")
            )
            # Check nested structures
            if not video_url and "videos" in result:
                video_url = result["videos"][0].get("url")
            if not video_url and "result" in result:
                r = result["result"]
                video_url = r.get("video_url") or r.get("url")

        if not video_url:
            print(f"    WARNING: Could not extract video URL from response")
            print(f"    Response keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            # Save raw response for debugging
            debug_file = output_dir / f"{clip_id}_response.json"
            with open(debug_file, "w") as f:
                json.dump(result if isinstance(result, dict) else {"raw": str(result)}, f, indent=2)
            return {"clip_id": clip_id, "status": "unknown_response", "debug": str(debug_file)}

        # Download the video
        output_path = output_dir / f"{clip_id}.mp4"
        print(f"    Downloading clip...")
        urllib.request.urlretrieve(video_url, str(output_path))

        file_size = output_path.stat().st_size / (1024 * 1024)
        print(f"    Saved: {output_path.name} ({file_size:.1f} MB)")

        return {
            "clip_id": clip_id,
            "status": "completed",
            "file_path": str(output_path),
            "file_size_mb": round(file_size, 1),
            "model": model,
            "prompt": prompt[:100],
        }

    except Exception as e:
        error_msg = str(e)
        print(f"    ERROR: {error_msg}")

        # Try fallback model
        if model != FALLBACK_MODEL:
            print(f"    Retrying with fallback model ({FALLBACK_MODEL})...")
            return generate_clip(prompt, clip_id, output_dir, model=FALLBACK_MODEL)

        return {"clip_id": clip_id, "status": "failed", "error": error_msg}


def generate_all_clips(target_date: str, dry_run: bool = False):
    """Generate all clips for a given day's visual plan."""
    plan = load_visual_plan(target_date)
    if not plan:
        print(f"  No visual plan found for {target_date}. Run generate_visuals.py first.")
        return

    library = load_library()
    day_clips_dir = CLIPS_DIR / target_date
    day_clips_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  CLIP GENERATION: {target_date}")
    print(f"  New clips needed: {plan.get('total_new_clips_needed', '?')}")
    print(f"  Estimated credits: ~{plan.get('estimated_credits', '?')}")
    print(f"  Model: {VIDEO_MODEL} (fallback: {FALLBACK_MODEL})")
    print(f"{'='*60}\n")

    total_new = 0
    total_success = 0
    total_failed = 0
    total_skipped = 0

    for video in plan.get("videos", []):
        slot = video.get("slot", 0)
        series = video.get("series", "")
        print(f"  [{slot:2d}/12] {series} ({video.get('mood', '?')} mood)")

        for clip in video.get("clips", []):
            clip_id = clip.get("clip_id", "")

            if not clip.get("is_new", True):
                reuse_path = clip.get("reuse_from", "")
                print(f"    Reusing: {reuse_path}")
                total_skipped += 1
                continue

            total_new += 1
            prompt = clip.get("prompt", "")

            if dry_run:
                print(f"    [DRY RUN] {clip_id}")
                print(f"    Prompt: {prompt[:80]}...")
                continue

            # Check if already generated
            existing = day_clips_dir / f"{clip_id}.mp4"
            if existing.exists() and existing.stat().st_size > 10000:
                print(f"    Already exists: {clip_id}.mp4")
                total_skipped += 1
                continue

            result = generate_clip(prompt, clip_id, day_clips_dir)

            if result.get("status") == "completed":
                total_success += 1
                # Add to library for future reuse
                library_entry = {
                    "clip_id": clip_id,
                    "mood": video.get("mood", ""),
                    "keywords": [w.lower() for w in prompt.split() if len(w) > 4][:10],
                    "file_path": result.get("file_path", ""),
                    "date_generated": target_date,
                    "times_reused": 0,
                }
                library["clips"].append(library_entry)
                library["total_generated"] += 1
            else:
                total_failed += 1

            # Brief pause between API calls to avoid rate limits
            time.sleep(2)

        print()

    save_library(library)

    print(f"{'='*60}")
    print(f"  RESULTS")
    print(f"  Generated: {total_success}")
    print(f"  Failed: {total_failed}")
    print(f"  Skipped/Reused: {total_skipped}")
    print(f"  Clips saved to: {day_clips_dir}")
    print(f"  Library updated: {len(library['clips'])} total clips")
    print(f"{'='*60}\n")


def check_status(target_date: str):
    """Check for any debug/response files from incomplete generations."""
    day_clips_dir = CLIPS_DIR / target_date
    if not day_clips_dir.exists():
        print(f"  No clips directory for {target_date}")
        return

    mp4s = list(day_clips_dir.glob("*.mp4"))
    debugs = list(day_clips_dir.glob("*_response.json"))

    print(f"\n  Status for {target_date}:")
    print(f"  Completed clips: {len(mp4s)}")
    print(f"  Debug/failed responses: {len(debugs)}")

    for d in debugs:
        print(f"    - {d.name}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

    if "--dry" in sys.argv:
        generate_all_clips(target, dry_run=True)
    elif "--status" in sys.argv:
        check_status(target)
    else:
        generate_all_clips(target)

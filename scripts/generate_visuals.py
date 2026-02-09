"""
Higgsfield Visual Prompt Generator
===================================
Reads the day's approved scripts and generates optimized Higgsfield prompts
for each video's visual clips. Tracks clip library to maximize reuse.

Usage:
    python generate_visuals.py 2026-02-10
    python generate_visuals.py 2026-02-10 --reuse-report  # Show reuse opportunities
"""

import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CALENDAR_DIR = PROJECT_ROOT / "calendar"
OUTPUT_DIR = PROJECT_ROOT / "output" / "drafts"
CLIP_LIBRARY = PROJECT_ROOT / "assets" / "clips" / "library_index.json"

# Higgsfield prompt templates by visual mood
HIGGSFIELD_TEMPLATES = {
    "serene": {
        "camera": "slow dolly forward, crane up reveal",
        "lighting": "golden hour, soft diffused natural light",
        "style": "cinematic, 4K, shallow depth of field, film grain",
        "color": "warm golden tones, soft shadows",
    },
    "dramatic": {
        "camera": "crash zoom, low angle tracking shot",
        "lighting": "dramatic side lighting, high contrast",
        "style": "cinematic, 4K, anamorphic lens flare, moody",
        "color": "deep shadows, cool highlights, teal and orange",
    },
    "classical": {
        "camera": "slow orbit, push-in, steady crane",
        "lighting": "museum lighting, directional warm light on marble",
        "style": "cinematic, 4K, shallow DOF, film grain, renaissance painting quality",
        "color": "muted earth tones, warm highlights on stone",
    },
    "dark-moody": {
        "camera": "slow tracking, handheld drift, static wide",
        "lighting": "candlelight, single source, heavy shadows",
        "style": "cinematic, 4K, noir aesthetic, atmospheric haze",
        "color": "desaturated, deep blacks, amber highlights",
    },
    "modern": {
        "camera": "gimbal tracking, over-shoulder, rack focus",
        "lighting": "natural indoor, window light, soft overhead",
        "style": "cinematic, 4K, clean and contemporary",
        "color": "neutral, clean whites, subtle color grade",
    },
    "nature": {
        "camera": "aerial drone, slow pan, timelapse",
        "lighting": "natural, golden hour or blue hour",
        "style": "cinematic, 4K, epic landscape, high dynamic range",
        "color": "vivid but natural, deep greens and blues",
    },
    "text-bg": {
        "camera": "very slow push-in or static, minimal movement",
        "lighting": "soft, even, non-distracting",
        "style": "abstract, textured, bokeh background, 4K",
        "color": "dark and moody OR clean minimal, suited for text overlay",
    },
}


def classify_mood(visual_direction: str) -> str:
    """Classify the visual direction into a mood category."""
    direction_lower = visual_direction.lower()
    mood_keywords = {
        "serene": ["sunrise", "calm", "peaceful", "golden", "dawn", "meditation", "gentle", "soft", "warm", "lake"],
        "dramatic": ["storm", "lightning", "crash", "waves", "battle", "fire", "intense", "aggressive", "crashing"],
        "classical": ["marble", "statue", "roman", "column", "ruins", "bust", "parchment", "scroll", "ancient", "forum"],
        "dark-moody": ["night", "candle", "shadow", "dark", "rain", "moody", "noir", "candlelit", "moonlight"],
        "modern": ["office", "desk", "phone", "city", "modern", "gym", "cafe", "screen", "alarm"],
        "nature": ["mountain", "forest", "ocean", "cloud", "star", "aurora", "aerial", "landscape", "tree"],
        "text-bg": ["text-heavy", "text only", "quote card", "minimal", "background for text"],
    }

    scores = {mood: 0 for mood in mood_keywords}
    for mood, keywords in mood_keywords.items():
        for keyword in keywords:
            if keyword in direction_lower:
                scores[mood] += 1

    best_mood = max(scores, key=scores.get)
    return best_mood if scores[best_mood] > 0 else "cinematic"


def build_higgsfield_prompt(visual_direction: str, mood: str, duration_sec: int = 10) -> dict:
    """Build a complete Higgsfield generation prompt."""
    template = HIGGSFIELD_TEMPLATES.get(mood, HIGGSFIELD_TEMPLATES["dramatic"])

    # Extract key subject from visual direction
    prompt = (
        f"{visual_direction}. "
        f"Camera: {template['camera']}. "
        f"Lighting: {template['lighting']}. "
        f"Style: {template['style']}. "
        f"Color: {template['color']}. "
        f"No text, no UI elements, no watermarks. Photorealistic cinematic footage."
    )

    return {
        "prompt": prompt,
        "mood": mood,
        "duration": duration_sec,
        "camera_move": template["camera"].split(",")[0].strip(),
        "model_recommendation": "DOP Standard" if mood in ["classical", "dramatic"] else "DOP Lite",
        "estimated_credits": (duration_sec // 3 + 1) * 2,  # rough estimate
    }


def load_clip_library() -> dict:
    """Load the existing clip library index."""
    if CLIP_LIBRARY.exists():
        with open(CLIP_LIBRARY, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"clips": [], "total_generated": 0}


def find_reusable_clips(library: dict, mood: str, keywords: list[str]) -> list[dict]:
    """Find clips in the library that match the mood and keywords."""
    matches = []
    for clip in library.get("clips", []):
        if clip.get("mood") == mood:
            clip_keywords = set(clip.get("keywords", []))
            overlap = len(set(keywords) & clip_keywords)
            if overlap > 0:
                matches.append({**clip, "relevance": overlap})
    return sorted(matches, key=lambda x: x["relevance"], reverse=True)


def generate_visual_plan(target_date: str, reuse_report: bool = False) -> dict:
    """Generate the full visual plan for a day's videos."""
    scripts_file = OUTPUT_DIR / target_date / "scripts.json"

    if not scripts_file.exists():
        # Fall back to calendar data
        for cal_file in sorted(CALENDAR_DIR.glob("*.json")):
            with open(cal_file, "r", encoding="utf-8") as f:
                calendar = json.load(f)
            if target_date in calendar.get("days", {}):
                videos = calendar["days"][target_date].get("videos", [])
                break
        else:
            print(f"No data found for {target_date}")
            return {}
    else:
        with open(scripts_file, "r", encoding="utf-8") as f:
            videos = json.load(f)

    library = load_clip_library()
    plan = {
        "date": target_date,
        "total_new_clips_needed": 0,
        "total_reused_clips": 0,
        "estimated_credits": 0,
        "videos": [],
    }

    print(f"\n{'='*60}")
    print(f"  VISUAL GENERATION PLAN: {target_date}")
    print(f"{'='*60}\n")

    for video in videos:
        visual_dir = video.get("visual_direction", "")
        mood = classify_mood(visual_dir)

        # Each video needs 3-5 clips totaling ~36-45 sec of AI footage
        clip_count = 2 if "text-heavy" in visual_dir.lower() or "NONE" in video.get("voice_profile", "") else 3

        # Check for reusable clips
        keywords = [w.lower() for w in visual_dir.split() if len(w) > 4]
        reusable = find_reusable_clips(library, mood, keywords)
        reuse_count = min(1, len(reusable))  # Reuse max 1 per video to keep fresh
        new_count = clip_count - reuse_count

        clips = []
        for i in range(new_count):
            # Split visual direction into individual clip prompts
            directions = visual_dir.split(",")
            clip_direction = directions[i].strip() if i < len(directions) else visual_dir
            clip_prompt = build_higgsfield_prompt(clip_direction, mood, duration_sec=12)
            clip_prompt["clip_id"] = f"{target_date}_{video.get('slot', 0):02d}_clip{i+1}"
            clip_prompt["is_new"] = True
            clips.append(clip_prompt)

        for reused in reusable[:reuse_count]:
            clips.append({
                "clip_id": reused.get("clip_id", "unknown"),
                "is_new": False,
                "reuse_from": reused.get("file_path", ""),
                "estimated_credits": 0,
            })

        video_plan = {
            "slot": video.get("slot", 0),
            "series": video.get("series", ""),
            "mood": mood,
            "new_clips": new_count,
            "reused_clips": reuse_count,
            "total_clips": clip_count,
            "clips": clips,
            "estimated_credits": sum(c.get("estimated_credits", 0) for c in clips),
        }

        plan["videos"].append(video_plan)
        plan["total_new_clips_needed"] += new_count
        plan["total_reused_clips"] += reuse_count
        plan["estimated_credits"] += video_plan["estimated_credits"]

        status = "REUSE" if reuse_count > 0 else "NEW"
        print(f"  [{video.get('slot', 0):2d}/12] {video.get('series', '')}")
        print(f"         Mood: {mood} | Clips: {new_count} new + {reuse_count} reused | Credits: ~{video_plan['estimated_credits']}")
        if reuse_report and reusable:
            print(f"         Reusable matches: {[r.get('clip_id', '?') for r in reusable[:3]]}")

    print(f"\n{'='*60}")
    print(f"  DAILY TOTALS")
    print(f"  New clips to generate: {plan['total_new_clips_needed']}")
    print(f"  Clips reused from library: {plan['total_reused_clips']}")
    print(f"  Estimated credits: ~{plan['estimated_credits']}")
    print(f"  Monthly burn rate at this pace: ~{plan['estimated_credits'] * 30}/6000 credits")
    print(f"{'='*60}\n")

    # Save plan
    output_path = OUTPUT_DIR / target_date
    output_path.mkdir(parents=True, exist_ok=True)
    plan_file = output_path / "visual_plan.json"
    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    print(f"  Saved to: {plan_file}")

    return plan


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    reuse = "--reuse-report" in sys.argv
    generate_visual_plan(target, reuse_report=reuse)

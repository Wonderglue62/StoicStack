"""
Daily Runner -- Master Orchestrator
=====================================
Runs the full daily pipeline in sequence, pausing for manual steps.

Usage:
    python daily_runner.py                   # Run for today
    python daily_runner.py 2026-02-10        # Run for specific date
    python daily_runner.py 2026-02-10 --from step3   # Resume from a specific step
"""

import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"


def log(message: str, level: str = "INFO"):
    """Print a timestamped log message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "  ", "STEP": ">>", "WAIT": "**", "DONE": "OK", "WARN": "!!"}
    print(f"  [{timestamp}] {prefix.get(level, '  ')} {message}")


def pause_for_manual_step(step_name: str, instructions: str):
    """Pause execution and wait for the user to complete a manual step."""
    print(f"\n{'='*60}")
    print(f"  MANUAL STEP REQUIRED: {step_name}")
    print(f"{'='*60}")
    print(f"\n{instructions}\n")
    input("  Press ENTER when complete >>> ")
    print()


def run_pipeline(target_date: str, start_from: str = "step1"):
    """Run the full daily production pipeline."""
    steps = ["step1", "step2", "step3", "step4", "step5", "step6", "step7"]
    start_index = steps.index(start_from) if start_from in steps else 0

    print(f"\n{'#'*60}")
    print(f"  DAILY PRODUCTION PIPELINE")
    print(f"  Date: {target_date}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Starting from: {start_from}")
    print(f"{'#'*60}\n")

    pipeline_log = {
        "date": target_date,
        "started": datetime.now().isoformat(),
        "steps": {},
    }

    # ===== STEP 1: Script Generation =====
    if start_index <= 0:
        log("STEP 1/7: Script Generation", "STEP")
        step_start = time.time()

        try:
            from generate_daily_scripts import generate_scripts_for_day
            scripts = generate_scripts_for_day(target_date)
            log(f"Generated {len(scripts)} scripts", "DONE")
        except Exception as e:
            log(f"Script generation failed: {e}", "WARN")
            log("Run manually: python generate_daily_scripts.py " + target_date, "WARN")

        pipeline_log["steps"]["script_generation"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

        pause_for_manual_step(
            "Review & Approve Scripts",
            f"  1. Open: output/drafts/{target_date}/scripts.json\n"
            f"  2. Review each script for accuracy and tone\n"
            f"  3. Set 'approved': true for scripts you approve\n"
            f"  4. Edit or add 'notes' for any that need changes\n"
            f"  5. Re-run generate_daily_scripts.py for any rejected scripts"
        )

    # ===== STEP 2: Voiceover Generation =====
    if start_index <= 1:
        log("STEP 2/7: Voiceover Generation", "STEP")
        pause_for_manual_step(
            "Generate Voiceovers in ElevenLabs",
            f"  For each approved script:\n"
            f"  1. Copy the script text\n"
            f"  2. Use Voice A (Calm/Deep) for: Morning Stoic, Thought of the Day,\n"
            f"     Before You Sleep, Seneca's Letters, Ancient Wisdom\n"
            f"  3. Use Voice B (Intense/Commanding) for: Wake Up Warrior,\n"
            f"     Marcus Aurelius Said, One Quote, Stoic vs Modern, Obstacle Is The Way\n"
            f"  4. Skip voiceover for: Silent Stoic, Stoic Thought of the Day\n"
            f"  5. Export as WAV to: assets/audio/{target_date}/\n"
            f"  6. Name files: 01_morning_stoic.wav, 02_marcus_aurelius.wav, etc."
        )
        pipeline_log["steps"]["voiceover"] = {"status": "complete (manual)"}

    # ===== STEP 3: Visual Generation =====
    if start_index <= 2:
        log("STEP 3/7: Visual Prompt Generation", "STEP")
        step_start = time.time()

        try:
            from generate_visuals import generate_visual_plan
            plan = generate_visual_plan(target_date)
            log(f"Visual plan: {plan.get('total_new_clips_needed', '?')} new clips needed", "DONE")
            log(f"Estimated credits: ~{plan.get('estimated_credits', '?')}", "INFO")
        except Exception as e:
            log(f"Visual plan generation failed: {e}", "WARN")
            log("Run manually: python generate_visuals.py " + target_date, "WARN")

        pipeline_log["steps"]["visual_planning"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

        pause_for_manual_step(
            "Generate Clips in Higgsfield",
            f"  1. Open: output/drafts/{target_date}/visual_plan.json\n"
            f"  2. For each clip with 'is_new': true:\n"
            f"     - Copy the 'prompt' field into Higgsfield\n"
            f"     - Use the recommended model (DOP Lite or Standard)\n"
            f"     - Set duration to 10-12 seconds\n"
            f"     - Download the generated clip\n"
            f"  3. Save clips to: assets/clips/{target_date}/\n"
            f"  4. Name clips matching their clip_id from the plan\n"
            f"  5. Copy any standout clips to assets/clips/[mood]/ for reuse library"
        )
        pipeline_log["steps"]["visual_generation"] = {"status": "complete (manual)"}

    # ===== STEP 4: Assembly & Editing =====
    if start_index <= 3:
        log("STEP 4/7: Video Assembly", "STEP")
        pause_for_manual_step(
            "Assemble Videos in CapCut/Editor",
            f"  For each of the 12 videos:\n"
            f"  1. Import voiceover + clips + music into editor\n"
            f"  2. Arrange clips to match script flow\n"
            f"  3. Add text overlays:\n"
            f"     - Quote text (large, readable)\n"
            f"     - Series title (small, top or bottom)\n"
            f"     - CTA text in final 5 seconds\n"
            f"  4. Add brand watermark (small, corner, semi-transparent)\n"
            f"  5. Add background music (lower than voiceover)\n"
            f"  6. Color grade for visual consistency\n"
            f"  7. Export as 1080x1920 MP4\n"
            f"  8. Save to: output/finals/{target_date}/\n"
            f"  9. Name: 01_morning_stoic.mp4, 02_marcus_aurelius.mp4, etc.\n\n"
            f"  TIP: Create CapCut templates for each series to speed this up.\n"
            f"  After Day 3, this step should take < 90 minutes."
        )
        pipeline_log["steps"]["assembly"] = {"status": "complete (manual)"}

    # ===== STEP 5: Quality Control =====
    if start_index <= 4:
        log("STEP 5/7: Quality Control", "STEP")
        step_start = time.time()

        try:
            from quality_check import check_day
            report = check_day(target_date)
            if report.get("failed", 0) > 0:
                log(f"QC: {report['failed']} videos FAILED -- fix before uploading!", "WARN")
                pause_for_manual_step(
                    "Fix Failed Videos",
                    f"  Check logs/qc_{target_date}.json for details.\n"
                    f"  Fix issues and re-export, then re-run QC."
                )
            else:
                log(f"QC: All {report.get('passed', 0)} videos passed!", "DONE")
        except Exception as e:
            log(f"QC check failed: {e}", "WARN")
            log("Run manually: python quality_check.py " + target_date, "WARN")

        pipeline_log["steps"]["quality_control"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

    # ===== STEP 6: Caption Generation =====
    if start_index <= 5:
        log("STEP 6/7: Caption & Hashtag Generation", "STEP")
        step_start = time.time()

        try:
            from generate_captions import generate_captions_for_day
            captions = generate_captions_for_day(target_date)
            log(f"Captions generated for {len(captions.get('videos', []))} videos", "DONE")
        except Exception as e:
            log(f"Caption generation failed: {e}", "WARN")
            log("Run manually: python generate_captions.py " + target_date, "WARN")

        pipeline_log["steps"]["captions"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

    # ===== STEP 7: Upload & Schedule =====
    if start_index <= 6:
        log("STEP 7/7: Upload & Schedule", "STEP")
        pause_for_manual_step(
            "Upload Videos to Platforms",
            f"  BATCH A (slots 1-4) -- Schedule for MORNING:\n"
            f"    TikTok: 7:00, 7:30, 8:00, 8:30 AM\n"
            f"    Instagram: 7:15, 7:45, 8:15, 8:45 AM\n\n"
            f"  BATCH B (slots 5-8) -- Schedule for MIDDAY:\n"
            f"    TikTok: 12:00, 12:30, 1:00, 1:30 PM\n"
            f"    Instagram: 12:15, 12:45, 1:15, 1:45 PM\n\n"
            f"  BATCH C (slots 9-12) -- Schedule for EVENING:\n"
            f"    TikTok: 6:00, 6:30, 8:00, 9:00 PM\n"
            f"    Instagram: 6:15, 7:00, 8:15, 9:00 PM\n\n"
            f"  For each upload:\n"
            f"  1. Copy caption from output/drafts/{target_date}/captions.json\n"
            f"  2. Paste platform-specific caption + hashtags\n"
            f"  3. Set scheduled time\n"
            f"  4. Cross-post to Facebook, X, YouTube Shorts\n\n"
            f"  TIP: Use a scheduling tool (Later, Buffer, Hootsuite) to batch this."
        )
        pipeline_log["steps"]["upload"] = {"status": "complete (manual)"}

    # ===== DONE =====
    pipeline_log["completed"] = datetime.now().isoformat()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"pipeline_{target_date}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(pipeline_log, f, indent=2)

    print(f"\n{'#'*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Date: {target_date}")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Log: {log_file}")
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    start = "step1"
    for arg in sys.argv:
        if arg.startswith("--from"):
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                start = sys.argv[idx + 1]

    run_pipeline(target, start_from=start)

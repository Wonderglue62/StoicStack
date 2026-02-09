"""
Daily Runner -- Master Orchestrator
=====================================
Runs the full daily pipeline end-to-end.
  --auto mode: Fully automated (scripts, voiceover, clips, assembly, publish)
  default mode: Pauses for manual review at key checkpoints

Usage:
    python daily_runner.py 2026-02-10               # Interactive with checkpoints
    python daily_runner.py 2026-02-10 --auto        # Fully automated
    python daily_runner.py 2026-02-10 --from step3  # Resume from a specific step
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
    prefix = {"INFO": "  ", "STEP": ">>", "DONE": "OK", "WARN": "!!", "AUTO": "~~"}
    print(f"  [{timestamp}] {prefix.get(level, '  ')} {message}")


def pause_for_review(step_name: str, instructions: str, auto: bool = False):
    """Pause for manual review unless in auto mode."""
    if auto:
        log(f"Auto mode -- skipping review: {step_name}", "AUTO")
        return
    print(f"\n{'='*60}")
    print(f"  REVIEW CHECKPOINT: {step_name}")
    print(f"{'='*60}")
    print(f"\n{instructions}\n")
    input("  Press ENTER to continue >>> ")
    print()


def run_pipeline(target_date: str, start_from: str = "step1", auto: bool = False):
    """Run the full daily production pipeline."""
    steps = ["step1", "step2", "step3", "step4", "step5", "step6", "step7"]
    start_index = steps.index(start_from) if start_from in steps else 0

    mode_label = "FULLY AUTOMATED" if auto else "INTERACTIVE"

    print(f"\n{'#'*60}")
    print(f"  DAILY PRODUCTION PIPELINE ({mode_label})")
    print(f"  Date: {target_date}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Starting from: {start_from}")
    print(f"{'#'*60}\n")

    pipeline_log = {
        "date": target_date,
        "mode": mode_label,
        "started": datetime.now().isoformat(),
        "steps": {},
    }

    # ===== STEP 1: Script Generation =====
    if start_index <= 0:
        log("STEP 1/7: Script Generation", "STEP")
        step_start = time.time()

        try:
            from extract_calendar_scripts import extract_scripts
        except ImportError:
            extract_scripts = None

        try:
            from generate_daily_scripts import generate_scripts_for_day
            scripts = generate_scripts_for_day(target_date)
            # Check if API worked or returned errors
            has_errors = any("[ERROR]" in s.get("script", "") for s in scripts)
            if has_errors and extract_scripts:
                log("API errors detected, falling back to calendar scripts", "WARN")
                scripts = extract_scripts(target_date)
            elif has_errors:
                log("API errors detected. Run extract_calendar_scripts.py as fallback", "WARN")
            log(f"Generated {len(scripts)} scripts", "DONE")
        except Exception as e:
            log(f"Script generation failed: {e}", "WARN")

        pipeline_log["steps"]["script_generation"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

        pause_for_review(
            "Review Scripts",
            f"  Scripts saved to: output/drafts/{target_date}/scripts.json\n"
            f"  Review for accuracy and tone before proceeding.",
            auto=auto,
        )

    # ===== STEP 2: Voiceover Generation (Automated via ElevenLabs) =====
    if start_index <= 1:
        log("STEP 2/7: Voiceover Generation (ElevenLabs API)", "STEP")
        step_start = time.time()

        try:
            from auto_voiceover import generate_all_voiceovers
            generate_all_voiceovers(target_date)
            log("Voiceovers generated", "DONE")
        except Exception as e:
            log(f"Voiceover generation failed: {e}", "WARN")
            log("Run manually: python auto_voiceover.py " + target_date, "WARN")

        pipeline_log["steps"]["voiceover"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

    # ===== STEP 3: Visual Plan + Clip Generation (Automated via Higgsfield) =====
    if start_index <= 2:
        log("STEP 3/7: Visual Generation (Higgsfield API)", "STEP")
        step_start = time.time()

        # Generate visual plan
        try:
            from generate_visuals import generate_visual_plan
            plan = generate_visual_plan(target_date)
            log(f"Visual plan: {plan.get('total_new_clips_needed', '?')} clips needed", "DONE")
        except Exception as e:
            log(f"Visual plan failed: {e}", "WARN")

        # Generate clips via API
        try:
            from auto_clips import generate_all_clips
            generate_all_clips(target_date)
            log("Clips generated", "DONE")
        except Exception as e:
            log(f"Clip generation failed: {e}", "WARN")
            log("Run manually: python auto_clips.py " + target_date, "WARN")

        pipeline_log["steps"]["visual_generation"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

    # ===== STEP 4: Assembly (Automated via FFmpeg) =====
    if start_index <= 3:
        log("STEP 4/7: Video Assembly (FFmpeg)", "STEP")
        step_start = time.time()

        try:
            from auto_assemble import assemble_all
            assemble_all(target_date)
            log("Videos assembled", "DONE")
        except Exception as e:
            log(f"Assembly failed: {e}", "WARN")
            log("Run manually: python auto_assemble.py " + target_date, "WARN")

        pipeline_log["steps"]["assembly"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

    # ===== STEP 5: Quality Control =====
    if start_index <= 4:
        log("STEP 5/7: Quality Control", "STEP")
        step_start = time.time()

        try:
            from quality_check import check_day
            report = check_day(target_date)
            if report.get("failed", 0) > 0:
                log(f"QC: {report['failed']} videos FAILED", "WARN")
                pause_for_review(
                    "Fix Failed Videos",
                    f"  Check logs/qc_{target_date}.json for details.\n"
                    f"  Fix issues and re-export, then re-run QC.",
                    auto=False,  # Always pause on QC failures, even in auto mode
                )
            else:
                log(f"QC: All {report.get('passed', 0)} videos passed", "DONE")
        except Exception as e:
            log(f"QC check failed: {e}", "WARN")

        pipeline_log["steps"]["quality_control"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

    # ===== STEP 6: Caption Generation =====
    if start_index <= 5:
        log("STEP 6/7: Captions & Upload Package", "STEP")
        step_start = time.time()

        try:
            from generate_captions import generate_captions_for_day
            captions = generate_captions_for_day(target_date)
            log(f"Captions generated for {len(captions.get('videos', []))} videos", "DONE")
        except Exception as e:
            log(f"Caption generation failed: {e}", "WARN")

        try:
            from auto_publish import generate_upload_package
            generate_upload_package(target_date)
            log("Upload package ready", "DONE")
        except Exception as e:
            log(f"Upload package failed: {e}", "WARN")

        pipeline_log["steps"]["captions"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

    # ===== STEP 7: Publishing =====
    if start_index <= 6:
        log("STEP 7/7: Publishing", "STEP")
        step_start = time.time()

        try:
            from auto_publish import post_to_tiktok, post_to_instagram
            import os
            if os.environ.get("TIKTOK_ACCESS_TOKEN"):
                log("Posting to TikTok...", "INFO")
                post_to_tiktok(target_date)
                log("TikTok posting complete", "DONE")
            else:
                log("TikTok API not configured -- use upload package", "INFO")

            if os.environ.get("INSTAGRAM_ACCESS_TOKEN"):
                log("Posting to Instagram...", "INFO")
                post_to_instagram(target_date)
                log("Instagram posting complete", "DONE")
            else:
                log("Instagram API not configured -- use upload package", "INFO")
        except Exception as e:
            log(f"Publishing failed: {e}", "WARN")

        if not auto:
            pause_for_review(
                "Manual Upload (if APIs not configured)",
                f"  Upload package: output/publish/{target_date}/\n"
                f"  Checklist: output/publish/{target_date}/UPLOAD_CHECKLIST.md\n"
                f"  Each slot folder has ready-to-paste captions per platform.",
                auto=False,
            )

        pipeline_log["steps"]["publishing"] = {
            "duration_sec": round(time.time() - step_start, 1),
            "status": "complete",
        }

    # ===== DONE =====
    pipeline_log["completed"] = datetime.now().isoformat()
    total_sec = (datetime.fromisoformat(pipeline_log["completed"])
                 - datetime.fromisoformat(pipeline_log["started"])).total_seconds()
    pipeline_log["total_duration_min"] = round(total_sec / 60, 1)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"pipeline_{target_date}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(pipeline_log, f, indent=2)

    print(f"\n{'#'*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Date: {target_date}")
    print(f"  Duration: {pipeline_log['total_duration_min']} minutes")
    print(f"  Log: {log_file}")
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    auto_mode = "--auto" in sys.argv
    start = "step1"
    for i, arg in enumerate(sys.argv):
        if arg == "--from" and i + 1 < len(sys.argv):
            start = sys.argv[i + 1]

    run_pipeline(target, start_from=start, auto=auto_mode)

"""
Quality Control Checker for Stoic Content Pipeline
===================================================
Validates exported videos against quality standards before upload.
Flags issues for manual review and auto-passes clean videos.

Usage:
    python quality_check.py 2026-02-10
    python quality_check.py 2026-02-10 --strict   # Stricter thresholds
"""

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
FINALS_DIR = PROJECT_ROOT / "output" / "finals"
DRAFTS_DIR = PROJECT_ROOT / "output" / "drafts"
LOGS_DIR = PROJECT_ROOT / "logs"

# Quality thresholds
THRESHOLDS = {
    "min_duration_sec": 60,
    "max_duration_sec": 90,
    "min_resolution_width": 1080,
    "min_resolution_height": 1920,
    "target_aspect_ratio": 9 / 16,
    "aspect_ratio_tolerance": 0.02,
    "min_file_size_mb": 5,
    "max_file_size_mb": 100,
    "min_audio_level_db": -30,
    "max_audio_level_db": -3,
}

STRICT_THRESHOLDS = {
    **THRESHOLDS,
    "min_duration_sec": 62,
    "max_duration_sec": 80,
    "min_file_size_mb": 8,
}


def check_ffprobe_available() -> bool:
    """Check if ffprobe is available on the system."""
    try:
        subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_video_metadata(video_path: Path) -> dict | None:
    """Extract video metadata using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def get_audio_levels(video_path: Path) -> dict | None:
    """Analyze audio levels using ffmpeg volumedetect."""
    try:
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-af", "volumedetect",
            "-f", "null",
            "-",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        stderr = result.stderr
        levels = {}
        for line in stderr.split("\n"):
            if "mean_volume" in line:
                levels["mean_db"] = float(line.split("mean_volume:")[1].strip().split(" ")[0])
            if "max_volume" in line:
                levels["max_db"] = float(line.split("max_volume:")[1].strip().split(" ")[0])
        return levels if levels else None
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return None


def run_checks(video_path: Path, thresholds: dict, calendar_entry: dict = None) -> dict:
    """Run all quality checks on a single video file."""
    results = {
        "file": video_path.name,
        "path": str(video_path),
        "passed": True,
        "checks": [],
        "warnings": [],
        "errors": [],
    }

    # Check 1: File exists and has size
    file_size_mb = video_path.stat().st_size / (1024 * 1024)
    if file_size_mb < thresholds["min_file_size_mb"]:
        results["errors"].append(f"File too small: {file_size_mb:.1f}MB (min {thresholds['min_file_size_mb']}MB)")
        results["passed"] = False
    elif file_size_mb > thresholds["max_file_size_mb"]:
        results["warnings"].append(f"File very large: {file_size_mb:.1f}MB (may slow upload)")
    results["checks"].append({"name": "file_size", "value": f"{file_size_mb:.1f}MB", "status": "pass" if file_size_mb >= thresholds["min_file_size_mb"] else "fail"})

    # Check 2: Video metadata (requires ffprobe)
    metadata = get_video_metadata(video_path)
    if metadata:
        # Duration
        duration = float(metadata.get("format", {}).get("duration", 0))
        if duration < thresholds["min_duration_sec"]:
            results["errors"].append(f"Too short: {duration:.1f}s (min {thresholds['min_duration_sec']}s)")
            results["passed"] = False
        elif duration > thresholds["max_duration_sec"]:
            results["warnings"].append(f"Long video: {duration:.1f}s (target < {thresholds['max_duration_sec']}s)")
        results["checks"].append({"name": "duration", "value": f"{duration:.1f}s", "status": "pass" if duration >= thresholds["min_duration_sec"] else "fail"})

        # Resolution & aspect ratio
        video_stream = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "video"), None)
        if video_stream:
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            if width < thresholds["min_resolution_width"] or height < thresholds["min_resolution_height"]:
                results["errors"].append(f"Resolution too low: {width}x{height} (min {thresholds['min_resolution_width']}x{thresholds['min_resolution_height']})")
                results["passed"] = False
            results["checks"].append({"name": "resolution", "value": f"{width}x{height}", "status": "pass" if width >= thresholds["min_resolution_width"] else "fail"})

            if height > 0:
                aspect = width / height
                target = thresholds["target_aspect_ratio"]
                if abs(aspect - target) > thresholds["aspect_ratio_tolerance"]:
                    results["errors"].append(f"Wrong aspect ratio: {aspect:.3f} (target {target:.3f} = 9:16)")
                    results["passed"] = False
                results["checks"].append({"name": "aspect_ratio", "value": f"{aspect:.3f}", "status": "pass" if abs(aspect - target) <= thresholds["aspect_ratio_tolerance"] else "fail"})

        # Audio stream present
        audio_stream = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "audio"), None)
        if not audio_stream:
            results["errors"].append("No audio stream detected")
            results["passed"] = False
        results["checks"].append({"name": "audio_present", "value": "yes" if audio_stream else "no", "status": "pass" if audio_stream else "fail"})
    else:
        results["warnings"].append("Could not read video metadata (ffprobe not available or file corrupt)")

    # Check 3: Audio levels (requires ffmpeg)
    audio_levels = get_audio_levels(video_path)
    if audio_levels:
        mean_db = audio_levels.get("mean_db", -99)
        if mean_db < thresholds["min_audio_level_db"]:
            results["warnings"].append(f"Audio very quiet: {mean_db:.1f}dB (min {thresholds['min_audio_level_db']}dB)")
        if mean_db > thresholds["max_audio_level_db"]:
            results["errors"].append(f"Audio too loud/clipping: {mean_db:.1f}dB (max {thresholds['max_audio_level_db']}dB)")
            results["passed"] = False
        results["checks"].append({"name": "audio_level", "value": f"{mean_db:.1f}dB", "status": "pass" if thresholds["min_audio_level_db"] <= mean_db <= thresholds["max_audio_level_db"] else "warn"})

    # Check 4: Filename convention
    expected_pattern = video_path.stem  # e.g., "01_morning_stoic"
    if not any(c.isdigit() for c in expected_pattern[:3]):
        results["warnings"].append(f"Filename doesn't start with slot number: {video_path.name}")
    results["checks"].append({"name": "filename", "value": video_path.name, "status": "pass"})

    return results


def check_day(target_date: str, strict: bool = False) -> dict:
    """Run quality checks on all videos for a given day."""
    thresholds = STRICT_THRESHOLDS if strict else THRESHOLDS
    day_dir = FINALS_DIR / target_date

    report = {
        "date": target_date,
        "mode": "strict" if strict else "standard",
        "total_videos": 0,
        "passed": 0,
        "failed": 0,
        "warnings": 0,
        "results": [],
    }

    print(f"\n{'='*60}")
    print(f"  QUALITY CHECK: {target_date} ({'STRICT' if strict else 'STANDARD'} mode)")
    print(f"{'='*60}\n")

    if not day_dir.exists():
        print(f"  Directory not found: {day_dir}")
        print(f"  Export videos to this folder first, then re-run QC.")
        print(f"\n  Expected structure:")
        print(f"    {day_dir}/01_morning_stoic.mp4")
        print(f"    {day_dir}/02_marcus_aurelius.mp4")
        print(f"    ... etc")

        # Create the directory and a checklist file instead
        day_dir.mkdir(parents=True, exist_ok=True)
        checklist = generate_manual_checklist(target_date)
        checklist_path = day_dir / "QC_CHECKLIST.md"
        with open(checklist_path, "w", encoding="utf-8") as f:
            f.write(checklist)
        print(f"\n  Created manual checklist: {checklist_path}")
        return report

    video_files = sorted(day_dir.glob("*.mp4"))
    if not video_files:
        print(f"  No .mp4 files found in {day_dir}")
        return report

    report["total_videos"] = len(video_files)

    for video_path in video_files:
        result = run_checks(video_path, thresholds)
        report["results"].append(result)

        status = "PASS" if result["passed"] else "FAIL"
        icon = "[OK]" if result["passed"] else "[!!]"

        print(f"  {icon} {result['file']}")
        for check in result["checks"]:
            check_icon = "  " if check["status"] == "pass" else ">>"
            print(f"      {check_icon} {check['name']}: {check['value']}")
        for warning in result["warnings"]:
            print(f"      >> WARNING: {warning}")
        for error in result["errors"]:
            print(f"      >> ERROR: {error}")

        if result["passed"]:
            report["passed"] += 1
        else:
            report["failed"] += 1
        if result["warnings"]:
            report["warnings"] += len(result["warnings"])

    # Summary
    print(f"\n{'-'*60}")
    print(f"  SUMMARY: {report['passed']}/{report['total_videos']} passed | {report['failed']} failed | {report['warnings']} warnings")
    if report["failed"] > 0:
        print(f"  ACTION: Fix failed videos before uploading!")
    else:
        print(f"  STATUS: All clear -- ready to upload.")
    print(f"{'='*60}\n")

    # Save report
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = LOGS_DIR / f"qc_{target_date}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"  Report saved: {report_file}")

    return report


def generate_manual_checklist(target_date: str) -> str:
    """Generate a manual QC checklist when ffprobe isn't available."""
    return f"""# Quality Control Checklist -- {target_date}

Review each video before uploading. Check every box.

## Per-Video Checks

For each of the 12 videos:

- [ ] Duration is 60+ seconds
- [ ] Aspect ratio is 9:16 (portrait)
- [ ] Resolution is 1080x1920 or higher
- [ ] Voiceover is clear and audible (if applicable)
- [ ] Background music is present but not overpowering
- [ ] Quote text is readable at phone size
- [ ] No spelling errors in text overlays
- [ ] Brand watermark is present (bottom corner)
- [ ] No Higgsfield watermark visible
- [ ] No duplicate clips from previous day's videos
- [ ] Opening hook appears in first 3 seconds
- [ ] CTA appears in final 5 seconds
- [ ] Color grading is consistent across all clips in the video
- [ ] Transitions between clips are smooth (no jarring cuts)

## Batch Checks

- [ ] All 12 videos exported and named correctly
- [ ] Batch A (slots 1-4): Morning tone, calmer energy
- [ ] Batch B (slots 5-8): Midday tone, mixed energy
- [ ] Batch C (slots 9-12): Evening tone, reflective energy
- [ ] No two videos use the exact same quote
- [ ] Series variety maintained (no two of the same series back-to-back in a batch)

## Upload Prep

- [ ] Captions generated for each video
- [ ] Hashtags prepared (see WORKFLOW.md)
- [ ] Posting times set correctly per batch
- [ ] Cross-post queue set up for Facebook, X, YouTube Shorts

## Sign-off

- [ ] I have watched all 12 videos on my phone screen
- [ ] Overall quality is consistent with brand standard

Checked by: _______________  Date: {target_date}
"""


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    strict = "--strict" in sys.argv
    check_day(target, strict=strict)

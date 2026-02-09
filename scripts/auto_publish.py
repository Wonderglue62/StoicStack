"""
Automated Publishing Scheduler
================================
Uploads finished videos to TikTok and Instagram with scheduled posting times.

TikTok: Uses Content Posting API (requires developer app approval)
Instagram: Uses Graph API via Facebook (requires Business/Creator account)

Until API access is approved, this script generates a ready-to-upload
package with optimized filenames, captions, and a schedule checklist.

Usage:
    python auto_publish.py 2026-02-10                  # Generate upload package
    python auto_publish.py 2026-02-10 --tiktok         # Post to TikTok via API
    python auto_publish.py 2026-02-10 --instagram      # Post to Instagram via API
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

FINALS_DIR = PROJECT_ROOT / "output" / "finals"
DRAFTS_DIR = PROJECT_ROOT / "output" / "drafts"
PUBLISH_DIR = PROJECT_ROOT / "output" / "publish"

# Platform API credentials (add to .env when approved)
TIKTOK_ACCESS_TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ID = os.environ.get("INSTAGRAM_BUSINESS_ID", "")

# Posting schedule (times in 24h format, will be converted to UTC for APIs)
BATCH_SCHEDULE = {
    "A": ["07:00", "07:30", "08:00", "08:30"],
    "B": ["12:00", "12:30", "13:00", "13:30"],
    "C": ["18:00", "18:30", "20:00", "21:00"],
}

SLOT_TO_BATCH = {
    1: ("A", 0), 2: ("A", 1), 3: ("A", 2), 4: ("A", 3),
    5: ("B", 0), 6: ("B", 1), 7: ("B", 2), 8: ("B", 3),
    9: ("C", 0), 10: ("C", 1), 11: ("C", 2), 12: ("C", 3),
}


def get_scheduled_time(target_date: str, slot: int) -> str:
    """Get the scheduled posting time for a given slot."""
    batch, index = SLOT_TO_BATCH.get(slot, ("A", 0))
    times = BATCH_SCHEDULE.get(batch, ["12:00"])
    time_str = times[index] if index < len(times) else times[0]
    return f"{target_date}T{time_str}:00"


def generate_upload_package(target_date: str):
    """Generate a ready-to-upload package with schedule and captions."""
    finals_dir = FINALS_DIR / target_date
    captions_file = DRAFTS_DIR / target_date / "captions.json"

    if not captions_file.exists():
        print(f"  No captions found for {target_date}. Run generate_captions.py first.")
        return

    with open(captions_file, "r", encoding="utf-8") as f:
        captions_data = json.load(f)

    publish_dir = PUBLISH_DIR / target_date
    publish_dir.mkdir(parents=True, exist_ok=True)

    videos = sorted(finals_dir.glob("*.mp4")) if finals_dir.exists() else []
    video_map = {}
    for v in videos:
        # Extract slot number from filename like "01_morning_stoic.mp4"
        try:
            slot_num = int(v.stem.split("_")[0])
            video_map[slot_num] = v
        except ValueError:
            continue

    schedule = []
    checklist_lines = [
        f"# Upload Checklist -- {target_date}",
        f"# Brand: The Inner Citadel (@theinnercitadel)",
        f"# Total videos: {len(captions_data.get('videos', []))}",
        "",
        "## BATCH A -- Morning (7:00-8:30 AM)",
        "",
    ]

    current_batch = "A"
    for cap in captions_data.get("videos", []):
        slot = cap.get("slot", 0)
        series = cap.get("series", "")
        batch, _ = SLOT_TO_BATCH.get(slot, ("A", 0))
        post_time = get_scheduled_time(target_date, slot)

        if batch != current_batch:
            current_batch = batch
            batch_labels = {"B": "BATCH B -- Midday (12:00-1:30 PM)", "C": "BATCH C -- Evening (6:00-9:00 PM)"}
            checklist_lines.extend(["", f"## {batch_labels.get(batch, batch)}", ""])

        video_file = video_map.get(slot)
        video_status = f"[READY] {video_file.name}" if video_file else "[MISSING] -- generate video first"

        # Get TikTok caption
        tiktok_cap = cap.get("tiktok", {})
        tiktok_text = tiktok_cap.get("caption", "") + "\n" + tiktok_cap.get("hashtags", "")

        # Get Instagram caption
        ig_cap = cap.get("instagram", {})
        ig_text = ig_cap.get("caption", "") + "\n" + ig_cap.get("hashtags", "")

        entry = {
            "slot": slot,
            "series": series,
            "scheduled_time": post_time,
            "batch": batch,
            "video_file": str(video_file) if video_file else None,
            "tiktok_caption": tiktok_text.strip(),
            "instagram_caption": ig_text.strip(),
            "x_caption": cap.get("x", {}).get("caption", "") + " " + cap.get("x", {}).get("hashtags", ""),
            "posted_tiktok": False,
            "posted_instagram": False,
            "posted_facebook": False,
            "posted_x": False,
        }
        schedule.append(entry)

        # Save individual caption files for easy copy-paste
        cap_dir = publish_dir / f"{slot:02d}_{series.lower().replace(' ', '_').replace('.', '').replace(chr(39), '')}"
        cap_dir.mkdir(parents=True, exist_ok=True)

        (cap_dir / "tiktok_caption.txt").write_text(tiktok_text.strip(), encoding="utf-8")
        (cap_dir / "instagram_caption.txt").write_text(ig_text.strip(), encoding="utf-8")
        (cap_dir / "x_caption.txt").write_text(entry["x_caption"].strip(), encoding="utf-8")

        # Checklist entry
        time_short = post_time.split("T")[1][:5]
        checklist_lines.append(f"### Slot {slot}: {series} -- {time_short}")
        checklist_lines.append(f"- Video: {video_status}")
        checklist_lines.append(f"- [ ] Upload to TikTok (schedule: {time_short})")
        checklist_lines.append(f"- [ ] Upload to Instagram Reels (schedule: {time_short})")
        checklist_lines.append(f"- [ ] Cross-post to Facebook Reels")
        checklist_lines.append(f"- [ ] Cross-post to X")
        checklist_lines.append(f"- Caption folder: {cap_dir.name}/")
        checklist_lines.append("")

    # Save schedule JSON
    schedule_file = publish_dir / "schedule.json"
    with open(schedule_file, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2, ensure_ascii=False)

    # Save checklist
    checklist_file = publish_dir / "UPLOAD_CHECKLIST.md"
    checklist_file.write_text("\n".join(checklist_lines), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  UPLOAD PACKAGE: {target_date}")
    print(f"{'='*60}\n")
    print(f"  Videos ready: {len(video_map)}/12")
    print(f"  Schedule: {schedule_file}")
    print(f"  Checklist: {checklist_file}")
    print(f"  Caption folders: {publish_dir}")
    print(f"\n  Each slot folder contains:")
    print(f"    tiktok_caption.txt")
    print(f"    instagram_caption.txt")
    print(f"    x_caption.txt")
    print(f"\n  Copy-paste captions directly during upload.")

    missing = 12 - len(video_map)
    if missing > 0:
        print(f"\n  WARNING: {missing} videos still missing. Run the full pipeline first:")
        print(f"    python auto_clips.py {target_date}")
        print(f"    python auto_voiceover.py {target_date}")
        print(f"    python auto_assemble.py {target_date}")

    print(f"\n{'='*60}\n")


def post_to_tiktok(target_date: str):
    """Post videos to TikTok via Content Posting API."""
    if not TIKTOK_ACCESS_TOKEN:
        print("  TikTok API not configured.")
        print("  To set up:")
        print("  1. Create app at https://developers.tiktok.com")
        print("  2. Apply for Content Posting API access")
        print("  3. Complete OAuth flow to get access token")
        print("  4. Add TIKTOK_ACCESS_TOKEN to .env")
        print("\n  Using upload package instead -- run without --tiktok flag.")
        return

    import requests

    schedule_file = PUBLISH_DIR / target_date / "schedule.json"
    if not schedule_file.exists():
        print(f"  No schedule found. Run: python auto_publish.py {target_date}")
        return

    with open(schedule_file, "r", encoding="utf-8") as f:
        schedule = json.load(f)

    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    for entry in schedule:
        if entry.get("posted_tiktok"):
            continue

        video_file = entry.get("video_file")
        if not video_file or not Path(video_file).exists():
            print(f"  [{entry['slot']:2d}] Skipped -- no video file")
            continue

        print(f"  [{entry['slot']:2d}] {entry['series']} -- uploading to TikTok...")

        # Step 1: Initialize upload
        init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        init_data = {
            "post_info": {
                "title": entry["tiktok_caption"][:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": Path(video_file).stat().st_size,
            },
        }

        # Add scheduling if post time is in the future
        scheduled_dt = datetime.fromisoformat(entry["scheduled_time"])
        if scheduled_dt > datetime.now():
            init_data["post_info"]["schedule_time"] = int(scheduled_dt.timestamp())

        try:
            resp = requests.post(init_url, headers=headers, json=init_data, timeout=30)
            if resp.status_code == 200:
                upload_url = resp.json().get("data", {}).get("upload_url")
                if upload_url:
                    # Step 2: Upload video binary
                    with open(video_file, "rb") as vf:
                        upload_resp = requests.put(
                            upload_url,
                            headers={"Content-Type": "video/mp4"},
                            data=vf,
                            timeout=300,
                        )
                    if upload_resp.status_code in (200, 201):
                        entry["posted_tiktok"] = True
                        print(f"    Uploaded successfully")
                    else:
                        print(f"    Upload failed: {upload_resp.status_code}")
            else:
                print(f"    Init failed: {resp.status_code} -- {resp.text[:100]}")
        except Exception as e:
            print(f"    Error: {e}")

    # Save updated schedule
    with open(schedule_file, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2, ensure_ascii=False)


def post_to_instagram(target_date: str):
    """Post Reels to Instagram via Graph API."""
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ID:
        print("  Instagram API not configured.")
        print("  To set up:")
        print("  1. Create Facebook App at https://developers.facebook.com")
        print("  2. Add Instagram Graph API product")
        print("  3. Connect Instagram Business/Creator account")
        print("  4. Generate long-lived access token")
        print("  5. Add INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ID to .env")
        print("\n  Using upload package instead -- run without --instagram flag.")
        return

    import requests

    schedule_file = PUBLISH_DIR / target_date / "schedule.json"
    if not schedule_file.exists():
        print(f"  No schedule found. Run: python auto_publish.py {target_date}")
        return

    with open(schedule_file, "r", encoding="utf-8") as f:
        schedule = json.load(f)

    print("  NOTE: Instagram Graph API requires videos hosted at a public URL.")
    print("  You may need to upload videos to a CDN/S3 bucket first.\n")

    for entry in schedule:
        if entry.get("posted_instagram"):
            continue

        video_file = entry.get("video_file")
        if not video_file:
            continue

        print(f"  [{entry['slot']:2d}] {entry['series']} -- queued for Instagram")
        # Instagram requires a public video URL, not direct file upload
        # In production, upload to S3/CDN first, then pass the URL here
        entry["instagram_status"] = "needs_public_url"

    with open(schedule_file, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

    if "--tiktok" in sys.argv:
        post_to_tiktok(target)
    elif "--instagram" in sys.argv:
        post_to_instagram(target)
    else:
        generate_upload_package(target)

"""
Analytics Tracker for Stoic Content Pipeline
==============================================
Log daily video performance, identify top/bottom performers,
and generate recommendations for content mix adjustments.

Usage:
    python analytics_tracker.py log 2026-02-10          # Log day's performance
    python analytics_tracker.py report 2026-02-10       # Generate daily report
    python analytics_tracker.py weekly 2026-02-10       # Weekly summary (from that Monday)
"""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
ANALYTICS_FILE = LOGS_DIR / "analytics.json"


def load_analytics() -> dict:
    """Load the analytics database."""
    if ANALYTICS_FILE.exists():
        with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"days": {}, "series_totals": {}, "last_updated": None}


def save_analytics(data: dict):
    """Save the analytics database."""
    data["last_updated"] = datetime.now().isoformat()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def log_day(target_date: str):
    """Interactive prompt to log a day's video performance."""
    analytics = load_analytics()

    if target_date in analytics["days"]:
        print(f"  Data already exists for {target_date}. Overwrite? (y/n)")
        if input("  >>> ").strip().lower() != "y":
            return

    print(f"\n{'='*60}")
    print(f"  LOG PERFORMANCE: {target_date}")
    print(f"  Enter metrics for each video (or 'skip' to skip)")
    print(f"{'='*60}\n")

    series_order = [
        "Morning Stoic", "Marcus Aurelius Said...", "Stoic Thought of the Day",
        "Wake Up, Warrior", "Stoic Response To...", "One Quote That Changes Everything",
        "Seneca's Letters", "Ancient Wisdom in 60 Seconds", "Stoic vs. Modern",
        "Before You Sleep", "The Obstacle Is The Way", "Silent Stoic",
    ]

    day_data = {"videos": [], "totals": {}}

    for i, series in enumerate(series_order, 1):
        print(f"  [{i:2d}/12] {series}")
        skip = input("         Views (or 'skip'): ").strip()
        if skip.lower() == "skip":
            continue

        try:
            views = int(skip)
            likes = int(input("         Likes: ").strip() or 0)
            comments = int(input("         Comments: ").strip() or 0)
            shares = int(input("         Shares: ").strip() or 0)
            saves = int(input("         Saves: ").strip() or 0)

            engagement_rate = ((likes + comments + shares + saves) / max(views, 1)) * 100

            video_data = {
                "slot": i,
                "series": series,
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "saves": saves,
                "engagement_rate": round(engagement_rate, 2),
            }
            day_data["videos"].append(video_data)

            print(f"         Engagement: {engagement_rate:.1f}%\n")

        except ValueError:
            print("         Skipped (invalid input)\n")

    if day_data["videos"]:
        # Calculate day totals
        day_data["totals"] = {
            "total_views": sum(v["views"] for v in day_data["videos"]),
            "total_likes": sum(v["likes"] for v in day_data["videos"]),
            "total_engagement": round(
                sum(v["engagement_rate"] for v in day_data["videos"]) / len(day_data["videos"]), 2
            ),
            "top_performer": max(day_data["videos"], key=lambda v: v["views"])["series"],
            "bottom_performer": min(day_data["videos"], key=lambda v: v["views"])["series"],
        }

        analytics["days"][target_date] = day_data

        # Update series totals
        for v in day_data["videos"]:
            series = v["series"]
            if series not in analytics["series_totals"]:
                analytics["series_totals"][series] = {
                    "total_views": 0, "total_likes": 0, "appearances": 0,
                    "avg_engagement": 0, "engagement_sum": 0,
                }
            s = analytics["series_totals"][series]
            s["total_views"] += v["views"]
            s["total_likes"] += v["likes"]
            s["appearances"] += 1
            s["engagement_sum"] += v["engagement_rate"]
            s["avg_engagement"] = round(s["engagement_sum"] / s["appearances"], 2)

        save_analytics(analytics)
        print(f"\n  Saved. Top: {day_data['totals']['top_performer']} | Bottom: {day_data['totals']['bottom_performer']}")


def daily_report(target_date: str):
    """Generate a daily performance report."""
    analytics = load_analytics()
    day = analytics["days"].get(target_date)

    if not day:
        print(f"  No data for {target_date}. Run: python analytics_tracker.py log {target_date}")
        return

    print(f"\n{'='*60}")
    print(f"  DAILY REPORT: {target_date}")
    print(f"{'='*60}\n")

    print(f"  Total Views: {day['totals']['total_views']:,}")
    print(f"  Total Likes: {day['totals']['total_likes']:,}")
    print(f"  Avg Engagement: {day['totals']['total_engagement']:.1f}%")
    print(f"  Top Performer: {day['totals']['top_performer']}")
    print(f"  Bottom Performer: {day['totals']['bottom_performer']}")

    print(f"\n  {'Series':<35} {'Views':>8} {'Likes':>7} {'Eng%':>6}")
    print(f"  {'-'*56}")

    sorted_videos = sorted(day["videos"], key=lambda v: v["views"], reverse=True)
    for v in sorted_videos:
        marker = " *" if v["series"] == day["totals"]["top_performer"] else ""
        print(f"  {v['series']:<35} {v['views']:>8,} {v['likes']:>7,} {v['engagement_rate']:>5.1f}%{marker}")

    # Recommendations
    print(f"\n  RECOMMENDATIONS:")
    if sorted_videos:
        top = sorted_videos[0]
        bottom = sorted_videos[-1]
        print(f"  - Double down on '{top['series']}' format (highest views)")
        print(f"  - Review '{bottom['series']}' -- consider changing hook or timing")
        if any(v["engagement_rate"] > 5 for v in sorted_videos):
            high_eng = [v for v in sorted_videos if v["engagement_rate"] > 5]
            print(f"  - High engagement: {', '.join(v['series'] for v in high_eng)} -- boost these")


def weekly_report(start_date: str):
    """Generate a weekly summary report."""
    analytics = load_analytics()
    start = datetime.strptime(start_date, "%Y-%m-%d").date()

    print(f"\n{'='*60}")
    print(f"  WEEKLY REPORT: {start_date} to {(start + timedelta(days=6)).isoformat()}")
    print(f"{'='*60}\n")

    week_views = 0
    week_likes = 0
    days_with_data = 0

    for i in range(7):
        day_str = (start + timedelta(days=i)).isoformat()
        day = analytics["days"].get(day_str)
        if day:
            days_with_data += 1
            week_views += day["totals"]["total_views"]
            week_likes += day["totals"]["total_likes"]
            print(f"  {day_str}: {day['totals']['total_views']:>8,} views | Top: {day['totals']['top_performer']}")
        else:
            print(f"  {day_str}: No data")

    print(f"\n  WEEK TOTALS ({days_with_data} days tracked):")
    print(f"  Total Views: {week_views:,}")
    print(f"  Total Likes: {week_likes:,}")

    if analytics["series_totals"]:
        print(f"\n  SERIES RANKINGS (all time):")
        ranked = sorted(
            analytics["series_totals"].items(),
            key=lambda x: x[1]["avg_engagement"],
            reverse=True,
        )
        for series, stats in ranked:
            print(f"    {series:<35} Avg Eng: {stats['avg_engagement']:.1f}% | Views: {stats['total_views']:,}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python analytics_tracker.py log 2026-02-10")
        print("  python analytics_tracker.py report 2026-02-10")
        print("  python analytics_tracker.py weekly 2026-02-10")
        sys.exit(1)

    command = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat()

    if command == "log":
        log_day(target)
    elif command == "report":
        daily_report(target)
    elif command == "weekly":
        weekly_report(target)
    else:
        print(f"Unknown command: {command}")

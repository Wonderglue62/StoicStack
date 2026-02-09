"""Extract pre-written scripts from calendar into output format."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
cal = json.loads((PROJECT_ROOT / "calendar" / "week1_calendar.json").read_text(encoding="utf-8"))
day = cal["days"]["2026-02-10"]
scripts = []

for v in day["videos"]:
    parts = []
    if v.get("script_hook"):
        parts.append(v["script_hook"])
    if v.get("script_body"):
        parts.append(v["script_body"])
    if v.get("script_cta"):
        parts.append(v["script_cta"])

    full_script = "\n\n".join(parts) if parts else "[TEXT-ONLY or SILENT -- see visual_direction]"
    word_count = len(full_script.split())

    scripts.append({
        "slot": v["slot"],
        "series": v["series"],
        "quote_id": v.get("quote_id", ""),
        "quote": v.get("quote", ""),
        "voice_profile": v.get("voice_profile", ""),
        "visual_direction": v.get("visual_direction", ""),
        "music_mood": v.get("music_mood", ""),
        "script": full_script,
        "word_count": word_count,
        "approved": False,
        "notes": "",
    })
    slot = v["slot"]
    series = v["series"]
    print(f"  [{slot:2d}/12] {series:<40} {word_count:>3} words")

out = PROJECT_ROOT / "output" / "drafts" / "2026-02-10" / "scripts.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(scripts, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nSaved {len(scripts)} scripts to {out}")

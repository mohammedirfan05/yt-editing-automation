import json
import os
import glob
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath("."))

from src.script_gen.tracker import ContentTracker
from src.script_gen.generator import ScriptGenerator

print("1. Resetting tracker to historical published Shorts only...")
tracker = ContentTracker()
tracker.seed_from_historical()

# Retain only published topics in tracker
published_topics = {k: v for k, v in tracker.data["topics"].items() if v.get("status") == "published"}
tracker.data["topics"] = published_topics
tracker.save()

print("2. Clearing unuploaded generated scripts and status logs...")
gen_dir = r"c:\yt_editing_automation\automation\generated_scripts"
if os.path.exists(gen_dir):
    for f in glob.glob(os.path.join(gen_dir, "*")):
        try:
            os.remove(f)
        except Exception:
            pass

status_file = r"c:\yt_editing_automation\automation\batch_status.json"
if os.path.exists(status_file):
    try:
        os.remove(status_file)
    except Exception:
        pass

ideas_file = r"c:\yt_editing_automation\automation\config\ideas.json"
with open(ideas_file, "w", encoding="utf-8") as f:
    json.dump([], f)

print("3. Generating 10 fresh Playbook-compliant scripts (5 Deep Dives + 5 Compilations)...")
generator = ScriptGenerator(tracker=tracker)
new_scripts = generator.generate_scripts(count=10, mode="auto")

formatted_ideas = []
for t in new_scripts:
    clean_name = re.sub(r"[^\w\s]", "", t["title"]).strip().replace(" ", "_")
    mode_str = t["type"].capitalize()
    proj_name = f"Auto_{mode_str}_{clean_name[:30]}"
    formatted_ideas.append({
        "id": t["id"],
        "project_name": proj_name,
        "type": t["type"],
        "script": t["script"],
        "labels": t.get("labels", {})
    })

with open(ideas_file, "w", encoding="utf-8") as f:
    json.dump(formatted_ideas, f, indent=2, ensure_ascii=False)

print(f"✨ Done! Successfully generated {len(formatted_ideas)} fresh scripts (5 Deep Dives + 5 Compilations).")

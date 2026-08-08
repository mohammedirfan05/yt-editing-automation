# 📖 YouTube Shorts Automation — Command Guide

---

## 📋 1. Seeing All Your Ideas & Scripts

### View the tracker as a spreadsheet (easiest)
Open this CSV in Excel, Google Sheets, or VSCode:

📄 **[config/content_tracker.csv](file:///c:/yt_editing_automation/automation/config/content_tracker.csv)**

Each row is one topic. Columns: `ID`, `Title`, `Format`, `Fandom`, `X_vs_Y`, `Status`, `Views`, `Likes`.

---

### View tracker summary in the terminal

```powershell
python generate_scripts.py --list-tracker
```

**What it shows:**
```
📊 CONTENT TRACKER LIFECYCLE SUMMARY
======================================
  • Published (YouTube) : 24    ← Shorts already uploaded to your channel
  • Approved Candidates : 2     ← Scripts you've approved for production
  • Tested in Sandbox   : 0
  • Ideas Queue         : 9     ← Fresh scripts waiting for your review
  • Rejected            : 3
  • Total Tracked       : 38

Recent Topics in Tracker:
  [PUBLISHED] 9IpnD9DCY5s   | 6 Crime Terms Everyone Gets Wrong (COMPILATION)
  [IDEA     ] gemini_dd_01  | Jedi vs Sith The Force Divide (DEEPDIVE)
  ...
```

**Status meanings:**

| Status | Meaning |
|--------|---------|
| `POSTED` / `PUBLISHED` | Already uploaded to YouTube |
| `IDEA` | Freshly generated, not yet reviewed |
| `APPROVED` | You approved it — ready to build into a CapCut draft |
| `REJECTED` | You rejected it — won't appear in future generations |
| `TESTED` | Built as a CapCut draft and tested |

---

## ✅ 2. Approving a Script

Mark a topic as **approved** (ready for production):

```powershell
python generate_scripts.py --approve <topic_id>
```

**Example:**
```powershell
python generate_scripts.py --approve gemini_dd_01
```

Output:
```
✓ Marked topic 'gemini_dd_01' as APPROVED.
```

The topic ID is the short code you see in `--list-tracker` output or in the `config/content_tracker.csv` `ID` column (e.g. `gemini_dd_01`, `gemini_comp_03`).

---

## ❌ 3. Rejecting a Script

Mark a topic as **rejected** so it won't be re-generated:

```powershell
python generate_scripts.py --reject <topic_id>
```

**Example:**
```powershell
python generate_scripts.py --reject gemini_comp_02
```

Output:
```
✓ Marked topic 'gemini_comp_02' as REJECTED.
```

Rejected topics are excluded from future duplicate checks and won't show up in batch review menus.

---

## 📌 4. Marking a Script as Published

Once you've uploaded a Short to YouTube, mark it as published to permanently lock it out of future generation:

```powershell
python generate_scripts.py --publish <topic_id>
```

---

## 🔍 5. Generating Fresh Scripts

Generate new Playbook-compliant scripts (writes to `config/ideas.json` + `generated_scripts/`):

```powershell
# Generate 3 scripts (default, balanced 50/50)
python generate_scripts.py

# Generate 10 scripts
python generate_scripts.py --count 10

# Only Deepdive scripts
python generate_scripts.py --count 5 --mode deepdive

# Only Compilation scripts
python generate_scripts.py --count 5 --mode compilation

# Filter by fandom (Marvel, DC, Anime, Mythology)
python generate_scripts.py --count 5 --fandom Marvel
```

---

## ⚡ 6. Batch Build Commands (`run_batch.py`)

### What `python run_batch.py` does (default)

1. Loads `config/ideas.json`
2. If empty → auto-generates 10 fresh scripts via Gemini
3. Shows the **interactive review menu** where you can pick which scripts to build
4. Builds CapCut drafts for the ones you select

---

### `--validate` — Check `ideas.json` before running

```powershell
python run_batch.py --validate
```

**What it does:** Loads and validates `config/ideas.json` without building anything. Catches:
- Missing required fields (`id`, `project_name`, `type`, `script`)
- Duplicate IDs
- Invalid `type` values (must be `deepdive` or `compilation`)
- Empty scripts

**When to use it:** After manually editing `ideas.json` to confirm it's still valid before kicking off a batch run.

Output example:
```
✓ Pre-flight validation passed for 'config/ideas.json'. Found 9 valid topics.
```

---

### `--dry-run` — Test the full pipeline without making any API calls

```powershell
python run_batch.py --dry-run --non-interactive
```

**What it does:** Runs the entire batch loop — loads ideas, sets up sandboxes, formats all arguments — but **skips** TTS generation, SRT tagging, and CapCut draft building. No API calls, no files written to CapCut.

**When to use it:** To verify your `ideas.json` structure is wired correctly and all topics would process without errors, before committing to a real overnight run.

Output per topic:
```
[DRY-RUN] Verified sandbox layout and arguments for 'Auto_Deepdive_Jedi_vs_Sith'.
```

---

### `--resume` — Continue an interrupted batch run

```powershell
python run_batch.py --resume
```

**What it does:** Reads `batch_status.json` (auto-saved after each completed topic) and skips any topics already marked `SUCCESS`. Useful if a run was interrupted mid-way.

---

### `--generate N` — Pre-generate N fresh scripts before the batch run

```powershell
python run_batch.py --generate 10
```

Generates 10 fresh Gemini scripts, saves them to `ideas.json`, then launches the interactive review menu.

---

### `--non-interactive` — Skip the review menu and build everything

```powershell
python run_batch.py --non-interactive
```

Skips the interactive CLI review and immediately starts building CapCut drafts for all topics in `ideas.json`. Useful for fully automated overnight runs.

---

## 🔄 7. Resetting & Regenerating from Scratch

To wipe the ideas queue and generate a fresh batch:

```powershell
# 1. Clear ideas.json
echo [] > config\ideas.json

# 2. Generate 10 fresh scripts
python generate_scripts.py --count 10

# 3. Review and build
python run_batch.py
```

---

## 🚀 8. Single Video Pipeline (`run.py`)

For building one CapCut draft at a time interactively:

```powershell
python run.py
```

Or non-interactively:

```powershell
# Deepdive (1 pair / 2 images)
python run.py SupermanVsShazam --mode deepdive -x "SUPERMAN" -y "SHAZAM" -t "Script text here..."

# Compilation (3 pairs / 6 images)
python run.py CompTest --mode compilation --labels "MCU,MARVEL;DCEU,DCU;CANON,CONTINUITY" -t "Script..."

# Skip TTS and use pre-recorded audio from input/
python run.py MyProject --mode deepdive -x "LABEL1" -y "LABEL2" --skip-tts
```

---

## 📂 Asset Requirements (Quick Reference)

| Mode | Images needed in `input/` |
|------|--------------------------|
| Deepdive | `image1.png`, `image2.png` |
| Compilation | `image1.png` → `image6.png` |
| Pre-recorded audio | Drop any `.wav` / `.mp3` into `input/` |

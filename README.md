# CapCut Desktop Tagged SRT Automation Tool

A clean, zero-configuration Python CLI tool that programmatically generates CapCut Desktop video editing projects driven by a tagged SRT subtitle file.

---

## Workspace Structure

```text
yt_editing_automation/
├── input/                      <-- Paste your tagged .srt file here! (e.g. script.srt)
├── config/
│   └── mapping.json            <-- Permanent tag-to-image mapping
├── assets/
│   ├── mascot/                 <-- Permanent mascot PNG library (left.png, right.png, etc.)
│   └── background/             <-- Primary background (dotgrid.png)
├── build_draft.py              <-- Main automation script
└── README.md                   <-- Documentation
```

---

## Super Simple Usage

### Step 1: Drop your `.srt` file into `input/`

Copy your tagged SRT file into the `input/` directory (e.g. `input/script.srt` or `input/my_video.srt`).

### Step 2: Run the script

```bash
python build_draft.py
```

That's it! The tool automatically:
1. Picks the `.srt` file inside `input/`.
2. Resolves mascot tags via `config/mapping.json` using `assets/mascot/`.
3. Extends `assets/background/dotgrid.png` across the entire video.
4. Scales mascot PNGs to **42%** at **X = -96px, Y = -816px**.
5. Formats captions with **LuckiestGuy-Rg** font, **Black** color, **100% scale**, and position **X = 0, Y = 81px**.
6. Auto-detects your CapCut Desktop drafts folder on Windows or macOS.
7. Generates a draft named after your SRT file (e.g. `script`) ready to open in CapCut!

---

## Optional CLI Parameters

If you want to customize specific runs, all defaults can be overridden:

```bash
# Process a specific SRT file and assign a custom project name
python build_draft.py --srt input/my_video.srt --project-name "MyCustomDraft"

# Custom position or background image
python build_draft.py --pos-x -96 --pos-y -816 --bg-image assets/background/dotgrid.png
```

| Parameter | Default Value | Description |
|---|---|---|
| `--srt` | Auto-detected from `input/` | Path to input SRT file |
| `--mapping` | `config/mapping.json` | Path to tag mapping file |
| `--assets` | `assets/mascot` | Directory containing mascot PNGs |
| `--bg-image` | `assets/background/dotgrid.png` | Primary background image |
| `--drafts-dir` | Auto-detected CapCut folder | CapCut local drafts directory |
| `--project-name` | SRT filename (stem) | Output project draft name |
| `--image-scale` | `0.42` (42%) | Mascot PNG scale factor |
| `--pos-x` | `-96.0` px | Mascot X offset from center |
| `--pos-y` | `-816.0` px | Mascot Y offset from center |
| `--text-font` | `LuckiestGuy-Rg` | Subtitle font family |
| `--text-pos-x` | `0.0` px | Subtitle X offset from center |
| `--text-pos-y` | `81.0` px | Subtitle Y offset from center |
| `--debug-dir` | `None` (Optional) | Export debug JSON files for inspection |

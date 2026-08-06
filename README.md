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

### Step 1: Drop your files into `input/`

Copy your files into `input/`:
- Tagged SRT file (e.g. `input/script.srt`)
- Voiceover Audio file (e.g. `input/voiceover.wav` or `input/script.mp3`)
- Image 1 file (e.g. `input/image1.png` or `input/img1.jpg`)
- Image 2 file (e.g. `input/image2.png` or `input/img2.jpg`)

### Step 2: Run the script

```bash
# 1. Automatic project name (inferred from SRT filename):
python build_draft.py

# 2. Custom project name (e.g. 'capvsironman'):
python build_draft.py capvsironman
```

That's it! The tool automatically:
1. Picks the `.srt` file, `.wav`/`.mp3` audio, `image1`, and `image2` inside `input/`.
2. Automatically performs **1:1 square center-crops** on Image 1 and Image 2 regardless of aspect ratio or orientation.
3. Places Image 1 at **Scale 40%, X = -503px, Y = 902px** (`transform_x=-0.465741, transform_y=0.469792`).
4. Places Image 2 at **Scale 40%, X = 551px, Y = 909px** (`transform_x=0.510185, transform_y=0.473438`).
5. Adds the audio track into CapCut and measures its exact duration.
6. Automatically extends `assets/background/dotgrid.png` across the entire video.
7. Scales mascot PNGs to **42%** at **X = -96px, Y = -816px**.
8. Formats captions with **LuckiestGuy-Rg** font, **Black** color, **100% scale**, and position **X = 0, Y = 81px**.
9. Auto-detects your CapCut Desktop drafts folder on Windows or macOS.
10. Generates a ready-to-open draft in CapCut Desktop!

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

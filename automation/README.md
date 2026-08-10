# 🎬 YouTube Shorts Editing Automation Engine

Automated pipeline for generating scripts, TTS audio, subtitles, mascot tags, and ready-to-open **CapCut Desktop projects** for YouTube Shorts.

Supports two YouTube channels natively:
- 🇺🇸 **Dont Mix This** (`dontmixthis`): English Pop Culture & Comics comparisons (@dontmixthis)
- 🇵🇰 **Farq Kya** (`farqkya`): Roman Urdu Islamic comparisons (@farqkya)

---

## ⚡ Quick Start (One Command)

Launch the master interactive pipeline:
```bash
python run.py
```
*Prompts for channel selection (`dontmixthis` vs `farqkya`), video format, project name, and titles.*

---

## 📝 1. Script Generation (`generate_scripts.py`)

Generate Playbook-compliant X vs Y comparison scripts using Gemini AI:

```bash
# English Channel (@dontmixthis)
python generate_scripts.py --channel dontmixthis --count 3

# Roman Urdu Channel (@farqkya) - Opens with: "Ye hai X aur ye hai Y, aakhir isme farq kya hai?"
python generate_scripts.py --channel farqkya --count 3

# Specific Modes & Fandoms
python generate_scripts.py --channel dontmixthis --mode deepdive --fandom Marvel
python generate_scripts.py --channel farqkya --mode compilation --fandom Islamic
```

---

## 🎬 2. Create Ready-to-Open CapCut Drafts (`run.py`)

### 🇺🇸 English Channel (`dontmixthis`)
```bash
# Deepdive (1 Pair / 2 Images: image1 & image2)
python run.py SupermanVsShazam --channel dontmixthis --mode deepdive -x "SUPERMAN" -y "SHAZAM"

# Compilation (3 Pairs / 6 Images: image1 to image6)
python run.py MarvelComp --channel dontmixthis --mode compilation --labels "MCU,COMICS;DCEU,DCU;CANON,ALT"
```

### 🇵🇰 Roman Urdu Channel (`farqkya`)
```bash
# Deepdive (1 Pair / 2 Images: image1 & image2)
python run.py NabiVsRasool --channel farqkya --mode deepdive -x "NABI" -y "RASOOL"

# Compilation (3 Pairs / 6 Images: image1 to image6)
python run.py IslamicComp --channel farqkya --mode compilation --labels "NABI,RASOOL;HAJJ,UMRAH;ZAKAT,SADAQAH"
```

### 🎙️ Using Pre-Recorded Audio (Skip Google TTS)
```bash
# Drop voiceover.wav or voiceover.mp3 into input/ directory, then run:
python run.py MyProject --channel farqkya --mode deepdive -x "NABI" -y "RASOOL" --skip-tts
```

---

## 🚀 3. Overnight Batch Generator (`run_batch.py`)

Automatically build multiple CapCut drafts from your ideas queue:

```bash
# Interactive review & build for English channel
python run_batch.py --channel dontmixthis

# Interactive review & build for Roman Urdu channel
python run_batch.py --channel farqkya

# Non-interactive automated run (Generates & builds 5 drafts)
python run_batch.py --channel farqkya --generate 5 --non-interactive
```

---

## 📺 Channel Reference Summary

| Channel ID | Channel Name | Spoken Language | Opening Line Pattern | Mascot Folder | Voice Model |
|------------|--------------|-----------------|----------------------|---------------|-------------|
| `dontmixthis` | Dont Mix This | English | `This is X. This is Y. So what's the difference?` | `assets/mascot/` | Puck |
| `farqkya` | Farq Kya | Roman Urdu | `Ye hai X aur ye hai Y, aakhir isme farq kya hai?` | `assets/mascot_urdu/` | Alnilam |

---

## 📁 Input Asset Requirements

- **Deepdive Mode:** `input/image1.png` (Left / Red X) and `input/image2.png` (Right / Blue Y).
- **Compilation Mode:** `input/image1.png` through `input/image6.png` (3 pairs).
- **Pre-recorded Audio:** Place `.wav` or `.mp3` into `input/` when using `--skip-tts`.

# 📖 YouTube Shorts Automation — Quick Command Guide

Simple, minimal cheat sheet for generating scripts, managing tracker ideas, and creating ready-to-open CapCut Desktop drafts for both YouTube channels.

---

## 📺 Channel Overview

| Channel ID | Channel Name | Spoken Language | Opening Hook Template |
|------------|--------------|-----------------|-----------------------|
| `dontmixthis` | Dont Mix This (@dontmixthis) | English | `This is X. This is Y. So what's the difference?` |
| `farqkya` | Farq Kya (@farqkya) | Roman Urdu | `Ye hai X aur ye hai Y, aakhir isme farq kya hai?` |

---

## ⚡ 1. Master Interactive CLI (`run.py`)

Run the step-by-step guided wizard to select channel, video format, project name, and labels:

```bash
python run.py
```

---

## 📝 2. Script Generator Commands (`generate_scripts.py`)

### Generate Fresh Scripts
```bash
# English Channel (@dontmixthis)
python generate_scripts.py --channel dontmixthis --count 3

# Roman Urdu Channel (@farqkya)
python generate_scripts.py --channel farqkya --count 3

# Filter by format or fandom category
python generate_scripts.py --channel dontmixthis --mode deepdive --fandom Marvel
python generate_scripts.py --channel farqkya --mode compilation --fandom Islamic
```

### Manage Script Tracker
```bash
# List all tracked topics and statistics
python generate_scripts.py --list-tracker

# Approve a candidate topic for production
python generate_scripts.py --approve <topic_id>

# Reject a candidate topic
python generate_scripts.py --reject <topic_id>

# Mark a topic as published on YouTube
python generate_scripts.py --publish <topic_id>
```

---

## 🎬 3. Single Video Draft Commands (`run.py`)

### 🇺🇸 English Channel (`dontmixthis`)
```bash
# Deepdive (1 Pair / 2 Images)
python run.py SupermanVsShazam --channel dontmixthis --mode deepdive -x "SUPERMAN" -y "SHAZAM"

# Compilation (3 Pairs / 6 Images)
python run.py MarvelComp --channel dontmixthis --mode compilation --labels "MCU,COMICS;DCEU,DCU;CANON,ALT"
```

### 🇵🇰 Roman Urdu Channel (`farqkya`)
```bash
# Deepdive (1 Pair / 2 Images)
python run.py NabiVsRasool --channel farqkya --mode deepdive -x "NABI" -y "RASOOL"

# Compilation (3 Pairs / 6 Images)
python run.py IslamicComp --channel farqkya --mode compilation --labels "NABI,RASOOL;HAJJ,UMRAH;ZAKAT,SADAQAH"
```

### 🎙️ Using Pre-Recorded Audio (Skip Google TTS)
```bash
# Drop audio file (voiceover.wav / voiceover.mp3) into input/, then run:
python run.py MyProject --channel farqkya --mode deepdive -x "NABI" -y "RASOOL" --skip-tts
```

---

## 🚀 4. Overnight Batch Builder (`run_batch.py`)

Automatically build multiple CapCut projects from `config/ideas.json`:

```bash
# Interactive batch runner for English channel
python run_batch.py --channel dontmixthis

# Interactive batch runner for Roman Urdu channel
python run_batch.py --channel farqkya

# Pre-generate 5 fresh scripts and launch batch review
python run_batch.py --channel farqkya --generate 5

# Automated non-interactive run (builds all drafts automatically)
python run_batch.py --channel farqkya --non-interactive

# Resume an interrupted batch run
python run_batch.py --resume
```

---

## 📁 Quick Asset Reference

- **Deepdive Mode:** Place `image1.png` (Left / Red Title X) and `image2.png` (Right / Blue Title Y) in `input/`.
- **Compilation Mode:** Place `image1.png` through `image6.png` in `input/`.
- **Pre-recorded Audio:** Place `.wav` / `.mp3` in `input/` when running with `--skip-tts`.
- **CapCut Desktop Output:** Project drafts are automatically written directly into CapCut Desktop's project workspace directory ready for instant opening!

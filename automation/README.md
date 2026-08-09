# 🎬 YouTube Shorts Editing Automation Engine

A clean, minimal, and 100% automated pipeline that turns script text/audio and images into **ready-to-open CapCut Desktop projects**.

Powered by **Google Gemini 3.1 Flash TTS**, **Local Whisper STT**, **Google Gemini 3.6 Flash AI**, and **CapCut PyCapCut Engine**.

---

## ⚡ Video Creation Modes

The engine supports two primary video formats:

### 1️⃣ Option 1: Deepdive (Single Pair - 2 Images)
Focuses on a single detailed comparison pair (`image1.png` vs `image2.png`) spanning the full video duration.

- **Interactive Selection:** Choose Option `1` when running `python run.py`.
- **Non-Interactive CLI Command:**
  ```bash
  python run.py SupermanVsShazam --mode deepdive -x "SUPERMAN" -y "SHAZAM"
  ```

---

### 2️⃣ Option 2: Compilation (3 Pairs - 6 Images)
Features 3 distinct comparison pairs (`image1/image2`, `image3/image4`, `image5/image6`) switching dynamically as the voiceover advances.

- **Interactive Selection:** Choose Option `2` when running `python run.py`.
- **Non-Interactive CLI Command:**
  ```bash
  python run.py compilationtest --mode compilation --labels "MCU,MARVEL COMICS;DCEU,DCU;CANON,CONTINUITY"
  ```

#### 🎬 Timeline & Visual Features
- ⚡ **Word-Level Subtitle Highlighting:** Automatically highlights the key concept/entity word in every subtitle block in high-contrast Electric Orange (`#FF5500`) for maximum legibility on light/white backgrounds.
- 🖼️ **Dynamic Image Transitions:** `image1`/`image2` transition seamlessly into `image3`/`image4` and `image5`/`image6`!
- 🏷️ **Dynamic Titles:** Red Title X & Blue Title Y switch automatically for each pair (`MCU` ➔ `DCEU` ➔ `CANON`).
- 🎵 **Mouse Click SFX (6x):** Plays the exact millisecond each of the 6 images pops on screen!
- 🍿 **Pop SFX (3x):** Plays 80ms before **EVERY** *"what's the difference"* segment in your video!

---

## 🎧 How to Use Pre-Recorded Audio (Skip Google TTS)

You can skip script text entry and Google TTS audio generation:

### Option A: Automatic Detection (Interactive CLI)
1. Drop your pre-recorded audio file (e.g. `voiceover.wav` or `my_audio.mp3`) into `input/`.
2. Run `python run.py`.
3. Press **ENTER** when prompted to use existing audio!

### Option B: CLI Flag `--skip-tts` (Non-Interactive)

```bash
python run.py my_project --mode deepdive -x "SUPERMAN" -y "SHAZAM" --skip-tts
```


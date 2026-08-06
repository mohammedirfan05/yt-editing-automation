# 🎬 YouTube Shorts Editing Automation Engine

A clean, minimal, and 100% automated pipeline that turns script text and 2 images into **ready-to-open CapCut Desktop projects**.

Powered by **Google Gemini 3.1 Flash TTS**, **Local Whisper STT**, **Google Gemini 3.6 Flash AI**, and **CapCut PyCapCut Engine**.

---

## ⚡ 1-Click Interactive Workflow

### Step 1: Drop 2 Images into `input/`
Drop your two comparison images into `input/` (e.g. `input/image1.jpg` and `input/image2.png`).

### Step 2: Run the Master CLI

```bash
python run.py
```

1. Enter your **Project Name** (e.g. `SupermanVsShazam`).
2. Paste your **Script Text** (e.g. `[amused] This is Superman. This is Shazam. So, what's the difference?`).
3. Press **ENTER** (and `Ctrl+Z` / type `END`).

**That's it!** The engine automatically:
- 🔊 Generates expressive voiceover audio using Google TTS (`Puck` voice).
- ⏱️ Extracts millisecond-exact timestamps using local Whisper STT.
- 🤖 Tags mascot character overlays using Gemini 3.6 Flash AI.
- ✂️ Center-crops Image 1 and Image 2 to 1:1 squares.
- 🎬 Assembles a 6-Track CapCut Desktop project ready to open!

---

## 💻 Non-Interactive CLI Command

```bash
python run.py SupermanVsShazam -t "[amused] This is Superman. This is Shazam. So, what's the difference?"
```

---

## 📁 Clean Directory Architecture

```text
yt-editing-automation/
├── run.py                            <-- ⚡ Master 1-Click Interactive CLI
├── build_draft.py                    <-- CapCut Desktop Draft Builder
├── README.md                         <-- Master documentation
├── .env                              <-- Contains GEMINI_API_KEY
│
├── input/                            <-- 🖼️ Drop image1 & image2 here
│   ├── image1.jpg                    <-- Top Left Comparison Image
│   ├── image2.webp                   <-- Top Right Comparison Image
│   ├── script.srt                    <-- (Auto-generated)
│   └── voiceover.wav                 <-- (Auto-generated)
│
├── tts_generator/                    <-- Google Gemini 3.1 Flash TTS Engine
│   └── generate_tts.py
│
├── srt_generator/                    <-- Whisper STT & Gemini 3.6 Flash Mascot Tagger
│   └── audio_to_tagged_srt.py
│
├── assets/                           <-- Mascot PNGs & Dotgrid background
└── config/                           <-- Tag mapping configuration
```

# 🎬 Short-Form YouTube Editing Automation Pipeline

A clean, minimal, and fully automated pipeline that turns raw voiceover audio and images into **ready-to-open CapCut Desktop projects**.

Powered by **Local Whisper STT**, **Google Gemini 3.6 Flash AI**, and **CapCut PyCapCut Engine**.

---

## ⚡ Quick Start Workflow

### 🚀 Step 1: Convert Audio (`.wav`/`.mp3`) to Tagged SRT

1. Drop your voiceover audio file into `srt_generator/input_audio/`.
2. Run:

```bash
python srt_generator/audio_to_tagged_srt.py
```

> **What this does:**
> - Transcribes audio with millisecond-exact timestamps using local `faster-whisper`.
> - Uses **Gemini 3.6 Flash AI** to read script context and insert mascot overlay tags (`[IMG:left]`, `[IMG:right]`, `[IMG:wtd]`, `[IMG:disagree]`, `[IMG:remember_this]`, `[IMG:speak_left]`, `[IMG:final_end]`).
> - Auto-syncs `script.srt` and `voiceover.wav` into the main `input/` folder!

---

### 🎨 Step 2: Build Ready-to-Open CapCut Desktop Draft

1. Drop your 2 comparison images (`image1` & `image2`) into `input/` (e.g. `input/image1.jpg` and `input/image2.png`).
2. Run:

```bash
python build_draft.py SupermanVsShazam
```

> **What this does:**
> - Creates a complete **6-Track Timeline** in CapCut Desktop:
>   - **Track 6:** Subtitles (`LuckiestGuy-Rg`, Black color, 100% scale, `X=0, Y=81px`).
>   - **Track 5:** Mascot Overlays (Merged PNG segments, Scale 42%, `X=-96px, Y=-816px`).
>   - **Track 4:** Image 2 Top Right (**1:1 Auto Center Cropped**, Scale 40%, `X=551px, Y=909px`).
>   - **Track 3:** Image 1 Top Left (**1:1 Auto Center Cropped**, Scale 40%, `X=-503px, Y=902px`).
>   - **Track 2:** Background (`dotgrid.png`, extended to full audio length).
>   - **Track 1:** Voiceover Audio (`00:00:00` to end).
> - Opens directly in your CapCut Desktop projects list!

---

## 📁 Clean Directory Layout

```text
yt-editing-automation/
├── .env                              <-- Contains GEMINI_API_KEY (git-ignored)
├── build_draft.py                    <-- CapCut Desktop Draft Builder
├── srt_generator/
│   ├── audio_to_tagged_srt.py        <-- Speech Recognition & Gemini AI Mascot Tagger
│   ├── input_audio/                  <-- Input folder for voiceover audio (.wav / .mp3)
│   └── output_srt/                   <-- Generated tagged .srt files
├── input/                            <-- Auto-synced draft builder input directory
│   ├── script.srt                    <-- Auto-copied from srt_generator
│   ├── voiceover.wav                 <-- Auto-copied from srt_generator
│   ├── image1.jpg                    <-- Top Left Comparison Image
│   └── image2.webp                   <-- Top Right Comparison Image
├── assets/
│   ├── background/dotgrid.png        <-- Primary video background
│   └── mascot/*.png                  <-- Character mascot overlays
└── config/
    └── mapping.json                  <-- Tag to mascot PNG mappings
```

---

## 🛠️ Configuration & Credentials

- **Gemini API Key:** Saved in `.env` as `GEMINI_API_KEY=your_key_here`.
- **Mascot Tag Mapping:** Configured in `config/mapping.json`.

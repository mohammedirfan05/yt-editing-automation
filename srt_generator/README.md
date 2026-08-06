# Audio to Tagged SRT Generator (Powered by Whisper & Gemini 3.6 Flash AI)

An isolated tool that converts raw audio files (`.wav` / `.mp3`) into millisecond-accurate SRT subtitles and uses **Google Gemini 3.6 Flash AI** to automatically assign your 8 mascot overlay tags `[IMG:tag_code]`.

---

## Folder Structure

```text
yt_editing_automation/
├── .env                       <-- Root .env file containing GEMINI_API_KEY
└── srt_generator/
    ├── audio_to_tagged_srt.py    <-- Converter script
    ├── input_audio/              <-- Drop your audio.wav files here!
    ├── output_srt/               <-- Generated tagged SRT files output here
    └── README.md
```

---

## Super Simple Usage

### Step 1: Drop your `audio.wav` or `.mp3` file into `srt_generator/input_audio/`

### Step 2: Run the script

```bash
python srt_generator/audio_to_tagged_srt.py
```

That's it! The tool automatically:
1. Loads `GEMINI_API_KEY` from your root `.env` file.
2. Uses **`gemini-3.6-flash`** AI model to analyze script context and tag mascot overlays.
3. Automatically syncs the generated `script.srt` and `audio.wav` into `input/` so you can immediately run:
   ```bash
   python build_draft.py my_project_name
   ```

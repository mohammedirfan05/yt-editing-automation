# Google Gemini 3.1 Flash TTS Generator

An isolated tool that uses **Google Gemini 3.1 Flash TTS Preview** to generate high-quality, expressive YouTube Shorts voiceover audio (`voiceover.wav`).

Pre-configured with your exact Google AI Studio settings:
- **Voice Model:** `Puck` (Upbeat, Middle pitch)
- **Scene:** `A fast-paced educational explainer breaking down story terminology, direct-to-camera style`
- **Sample Context:** `Energetic YouTube Shorts narration, quick pacing, conversational but confident tone`
- **Expressive Tag Support:** Allows inline speech tags like `[amused]`, `[laughs]`, `[whispers]`, `[sighs]`.

---

## Folder Structure

```text
yt_editing_automation/
└── tts_generator/
    ├── generate_tts.py           <-- Google TTS Generation script
    ├── input_text/               <-- Drop script .txt files here (optional)
    ├── output_audio/             <-- Generated voiceover.wav output folder
    └── README.md
```

---

## Usage Examples

### Option 1: Generate Speech via Command-Line String

```bash
python tts_generator/generate_tts.py -t "[amused] This is Superman. This is Shazam. So, what's the difference?"
```

### Option 2: Generate Speech from Text File

Drop your script into `tts_generator/input_text/script.txt` and run:

```bash
python tts_generator/generate_tts.py
```

### Option 3: 1-Click End-to-End Automation (TTS -> Tagged SRT -> CapCut Draft)

Pass `--auto-build` to automatically generate the voiceover, extract SRT timestamps, apply Gemini mascot tagging, and build your CapCut Desktop project in one command:

```bash
python tts_generator/generate_tts.py -t "[amused] This is Superman. This is Shazam." --auto-build SupermanVsShazam
```

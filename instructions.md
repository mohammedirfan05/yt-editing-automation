# ⚡ YouTube Shorts Editing Automation Engine — Quick Command Reference

## 🚀 1. Master Pipeline (`run.py`)

### 1-Click Interactive CLI (Recommended)
```powershell
python run.py
```
*(Prompts for Mode, Project Name, Title Labels, and Text Script / Pre-Recorded Audio)*

---

### Non-Interactive CLI Commands

#### 🔹 Deepdive Mode (1 Pair / 2 Images)
```powershell
python run.py SupermanVsShazam --mode deepdive -x "SUPERMAN" -y "SHAZAM" -t "Your video script text..."
```

#### 🔹 Compilation Mode (3 Pairs / 6 Images)
```powershell
python run.py CompilationTest --mode compilation --labels "MCU,MARVEL;DCEU,DCU;CANON,CONTINUITY" -t "Your script text..."
```

#### 🔹 Skip Google TTS (Use Pre-Recorded Audio in `input/`)
```powershell
# Deepdive
python run.py SupermanVsShazam --mode deepdive -x "SUPERMAN" -y "SHAZAM" --skip-tts

# Compilation
python run.py CompilationTest --mode compilation --labels "MCU,MARVEL;DCEU,DCU;CANON,CONTINUITY" --skip-tts
```

---

## 🛠️ 2. Direct Stage Scripts (Manual Step-by-Step)

### 🎙️ Stage 1: Generate Expressive Audio (Google TTS)
```powershell
python tts_generator/generate_tts.py -i tts_generator/input_text/script.txt
```

### 🏷️ Stage 2: Speech Timestamps & Gemini Mascot Tagging
```powershell
python srt_generator/audio_to_tagged_srt.py
```

### 🎬 Stage 3: Build CapCut Desktop Draft
```powershell
# Deepdive (1 Pair)
python build_draft.py SupermanVsShazam --mode deepdive --label1 "SUPERMAN" --label2 "SHAZAM"

# Compilation (3 Pairs)
python build_draft.py CompilationTest --mode compilation --labels "MCU,MARVEL;DCEU,DCU;CANON,CONTINUITY"
```

---

## 📂 Asset Requirements

- **Deepdive Mode:** Place `image1.png` and `image2.png` in `input/`.
- **Compilation Mode:** Place `image1.png` through `image6.png` in `input/`.
- **Pre-Recorded Audio (Optional):** Place `voiceover.wav` in `input/`.
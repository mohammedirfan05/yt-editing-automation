#!/usr/bin/env python3
r"""
Audio-to-Tagged-SRT Converter powered by Whisper & Gemini 3.6 Flash AI

Converts raw voiceover audio (.wav / .mp3) into millisecond-accurate SRT subtitles,
and uses Google Gemini 3.6 Flash AI to analyze script context and automatically insert mascot image tags [IMG:tag_code].

Usage:
    python srt_generator/audio_to_tagged_srt.py          # Auto-loads GEMINI_API_KEY from root .env & uses gemini-3.6-flash
"""

import argparse
import json
import os
import re
import shutil
import sys
from typing import Dict, List, Optional, Tuple

import requests
from colorama import Fore, Style, init

init(autoreset=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_INPUT_DIR = os.path.join(SCRIPT_DIR, "input_audio")
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_srt")
PROJECT_ROOT_INPUT = os.path.join(PROJECT_ROOT, "input")

# Strict Default Gemini Model requested by user
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"


def load_env_file() -> None:
    """
    Auto-loads environment variables from root .env file if present.
    """
    env_paths = [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(SCRIPT_DIR, ".env"),
        ".env"
    ]
    for path in env_paths:
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k and v and k not in os.environ:
                                os.environ[k] = v
            except Exception as e:
                pass


# Auto-load .env at script startup
load_env_file()


def format_srt_timestamp(seconds: float) -> str:
    """Format float seconds to SRT timestamp string HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis -= 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt_timestamp(ts: str) -> float:
    """Parse SRT timestamp string HH:MM:SS,mmm to float seconds."""
    ts = ts.strip().replace('.', ',')
    hms, ms = ts.split(',')
    h, m, s = hms.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def close_srt_gaps(srt_content: str, gap_buffer: float = 0.05) -> str:
    """
    Post-process SRT content to close large gaps between subtitle blocks.
    Each subtitle's end time is extended to reach the next subtitle's start minus gap_buffer.
    """
    if not srt_content or not srt_content.strip():
        return srt_content

    blocks = []
    raw_blocks = srt_content.strip().split("\n\n")
    for raw in raw_blocks:
        lines = raw.strip().splitlines()
        if len(lines) < 3:
            continue
        index_str = lines[0].strip()
        time_line = lines[1].strip()
        text_lines = lines[2:]
        try:
            start_str, end_str = [p.strip() for p in time_line.split("-->")]
            start_s = parse_srt_timestamp(start_str)
            end_s = parse_srt_timestamp(end_str)
        except Exception:
            blocks.append((index_str, None, None, time_line, text_lines))
            continue
        blocks.append((index_str, start_s, end_s, None, text_lines))

    result_blocks = []
    for i, block in enumerate(blocks):
        index_str, start_s, end_s, raw_time, text_lines = block
        if start_s is None:
            result_blocks.append(f"{index_str}\n{raw_time}\n" + "\n".join(text_lines))
            continue

        new_end_s = end_s
        if i < len(blocks) - 1:
            next_block = blocks[i + 1]
            next_start_s = next_block[1]
            if next_start_s is not None:
                gap = next_start_s - end_s
                if gap > gap_buffer:
                    new_end_s = max(end_s, next_start_s - gap_buffer)

        start_ts = format_srt_timestamp(start_s)
        end_ts = format_srt_timestamp(new_end_s)
        text_str = "\n".join(text_lines)
        result_blocks.append(f"{index_str}\n{start_ts} --> {end_ts}\n{text_str}")

    return "\n\n".join(result_blocks) + "\n"


def chunk_words_to_srt(words: List[Dict], max_words_per_line: int = 5, pause_threshold: float = 0.4, max_chars_per_line: int = 42) -> str:
    """
    Groups word list [{'word': str, 'start': float, 'end': float}] into clean SRT subtitle blocks.
    """
    if not words:
        return ""

    srt_blocks = []
    current_chunk = []
    block_index = 1
    sentence_enders = {'.', '?', '!', ';'}

    def flush(chunk):
        nonlocal block_index
        if not chunk:
            return
        start_time = format_srt_timestamp(chunk[0]['start'])
        end_time = format_srt_timestamp(chunk[-1]['end'])
        text = " ".join(item['word'].strip() for item in chunk).strip()
        if text:
            srt_blocks.append(f"{block_index}\n{start_time} --> {end_time}\n{text}\n")
            block_index += 1

    for i, w in enumerate(words):
        word_text = w['word'].strip()
        if not word_text:
            continue

        current_chunk.append(w)
        current_text = " ".join(item['word'].strip() for item in current_chunk)

        ends_sentence = word_text[-1] in sentence_enders if word_text else False

        is_pause = False
        if i < len(words) - 1:
            next_start = words[i + 1]['start']
            if next_start - w['end'] >= pause_threshold:
                is_pause = True

        over_chars = len(current_text) > max_chars_per_line
        over_words = (max_words_per_line > 0) and (len(current_chunk) > max_words_per_line)
        is_overflow = over_chars or over_words

        is_last = (i == len(words) - 1)

        if ends_sentence or is_pause or is_last:
            flush(current_chunk)
            current_chunk = []
        elif is_overflow:
            carry = current_chunk[-1]
            flush(current_chunk[:-1])
            current_chunk = [carry]

    flush(current_chunk)
    return "\n".join(srt_blocks)


def extract_word_timestamps_from_audio(audio_path: str, model_size: str = "base", language: Optional[str] = None) -> List[Dict]:
    """
    Extracts precise word timing list [{'word': str, 'start': float, 'end': float}] using faster-whisper or openai-whisper.
    """
    try:
        from faster_whisper import WhisperModel
        print(Fore.CYAN + f"[faster-whisper] Extracting word timestamps from audio (model={model_size})..." + Style.RESET_ALL)
        try:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
        except Exception:
            model = WhisperModel(model_size, device="cpu", compute_type="float32")

        kwargs = {"beam_size": 5, "word_timestamps": True}
        if language:
            kwargs["language"] = language

        segments, _ = model.transcribe(audio_path, **kwargs)
        all_words = []
        for seg in segments:
            if hasattr(seg, "words") and seg.words:
                for w in seg.words:
                    all_words.append({"word": w.word, "start": w.start, "end": w.end})
            else:
                words = seg.text.strip().split()
                duration = seg.end - seg.start
                t_per_w = duration / max(len(words), 1)
                for idx, word_str in enumerate(words):
                    w_start = seg.start + (idx * t_per_w)
                    all_words.append({"word": word_str, "start": w_start, "end": w_start + t_per_w})
        return all_words
    except Exception as e1:
        print(Fore.YELLOW + f"faster-whisper extraction fallback ({e1}). Trying openai-whisper..." + Style.RESET_ALL)
        import whisper
        print(Fore.CYAN + f"[openai-whisper] Extracting timestamps with model '{model_size}'..." + Style.RESET_ALL)
        model = whisper.load_model(model_size)
        kwargs = {"word_timestamps": True}
        if language:
            kwargs["language"] = language
        result = model.transcribe(audio_path, **kwargs)
        all_words = []
        for seg in result.get("segments", []):
            words = seg.get("words", [])
            if words:
                for w in words:
                    all_words.append({"word": w["word"], "start": w["start"], "end": w["end"]})
            else:
                words_list = seg.get("text", "").strip().split()
                duration = seg["end"] - seg["start"]
                t_per_w = duration / max(len(words_list), 1)
                for idx, word_str in enumerate(words_list):
                    w_start = seg["start"] + (idx * t_per_w)
                    all_words.append({"word": word_str, "start": w_start, "end": w_start + t_per_w})
        return all_words


def tag_srt_with_gemini_ai(
    raw_srt_content: str,
    api_key: str,
    model_name: str = DEFAULT_GEMINI_MODEL
) -> str:
    """
    Uses Google Gemini 3.6 Flash API to analyze subtitle script context and insert mascot image tags [IMG:tag_code].
    """
    if not api_key:
        print(Fore.YELLOW + "[Gemini AI] No API key found. Returning clean untagged SRT." + Style.RESET_ALL)
        return raw_srt_content

    print(Fore.CYAN + f"[Gemini AI] Analyzing script context and tagging mascot overlays (model={model_name})..." + Style.RESET_ALL)

    prompt = f"""You are an expert AI Short-Form Video Director & Mascot Tagging Engine.
Your job is to analyze an untagged SRT subtitle file for a comparison/versus video and insert mascot tags `[IMG:tag_code]` at the end of text lines.

### STEP 1: ENTITY MAPPING IN THE SCRIPT
First, identify the two main competing entities being compared in the script:
- ENTITY A (Topic 1 / Left Entity): e.g. Superman, Sharingan, iPhone, Naruto, first item mentioned.
- ENTITY B (Topic 2 / Right Entity): e.g. Shazam, Rinnegan, Samsung, Sasuke, second item mentioned.

### STEP 2: MASCOT TAGGING RULES

1. `[IMG:left]` -> Use when introducing, showing, or explaining ENTITY A (Topic 1).
2. `[IMG:right]` -> Use when introducing, showing, or explaining ENTITY B (Topic 2).
   CRITICAL: Whenever the text discusses ENTITY B (e.g. Shazam, Rinnegan, Samsung, Sasuke), you MUST tag `[IMG:right]`. NEVER use `[IMG:left]` for ENTITY B!
3. `[IMG:wtd]` -> Use when asking a comparison question or expressing curiosity (e.g., "So, what's the difference?", "Which one are you picking?", "?").
4. `[IMG:disagree]` -> Use for negations, debunks, or head-shaking statements (e.g., "They're not", "Wrong", "Incorrect", "No").
5. `[IMG:remember_this]` -> Use for key pro-tips, memory hooks, or core takeaways (e.g., "That's why magic is one of Superman's biggest weaknesses").
6. `[IMG:final_end]` -> Use for outro, CTA, or subscribe prompts (e.g., "Comment below and subscribe for more").

### CRITICAL RULES:
- Do NOT change any SRT index numbers or timestamps. Keep them EXACTLY identical.
- Append `[IMG:tag_code]` to the end of the text line for blocks that trigger mascot visual overlays.
- Ensure strict switching between ENTITY A (`[IMG:left]`) and ENTITY B (`[IMG:right]`).
- Return ONLY the final complete tagged SRT content without any markdown formatting, backticks, or extra explanation text.

--- INPUT SRT ---
{raw_srt_content}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096
        }
    }

    headers = {"Content-Type": "application/json"}

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            res_data = r.json()
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    output_text = parts[0].get("text", "").strip()
                    output_text = re.sub(r'^```\w*\n', '', output_text)
                    output_text = re.sub(r'\n```$', '', output_text).strip()
                    print(Fore.GREEN + f"[Gemini AI] Mascot tagging successfully completed with '{model_name}'!" + Style.RESET_ALL)
                    return output_text
        else:
            print(Fore.YELLOW + f"[Gemini AI Warning] API HTTP {r.status_code}: {r.text[:200]}" + Style.RESET_ALL)
            # Try fallback model if specified model returned error
            fallback_model = "gemini-2.5-flash" if model_name != "gemini-2.5-flash" else "gemini-1.5-flash"
            print(Fore.CYAN + f"[Gemini AI] Trying fallback model '{fallback_model}'..." + Style.RESET_ALL)
            return tag_srt_with_gemini_ai(raw_srt_content, api_key, model_name=fallback_model)
    except Exception as e:
        print(Fore.YELLOW + f"[Gemini AI Warning] Request failed: {e}" + Style.RESET_ALL)

    return raw_srt_content


def convert_audio_to_tagged_srt(
    audio_path: str,
    output_srt_path: Optional[str] = None,
    gemini_key: Optional[str] = None,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    model_size: str = "base",
    max_words_per_line: int = 5,
    gap_buffer: float = 0.05,
    copy_to_project_input: bool = True
) -> Optional[str]:
    """
    Main conversion pipeline: Audio -> Whisper STT Timestamps -> Gap Closing -> Gemini AI Mascot Tagging -> Saved SRT.
    """
    audio_path = os.path.abspath(audio_path)
    if not os.path.exists(audio_path):
        print(Fore.RED + f"Error: Audio file not found at '{audio_path}'" + Style.RESET_ALL)
        return None

    filename = os.path.basename(audio_path)
    base_name = os.path.splitext(filename)[0]

    # Resolve output paths
    if not output_srt_path:
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        output_srt_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{base_name}.srt")
    else:
        output_srt_path = os.path.abspath(output_srt_path)

    os.makedirs(os.path.dirname(output_srt_path), exist_ok=True)

    print(Fore.MAGENTA + f"\n============================================================" + Style.RESET_ALL)
    print(Fore.MAGENTA + f"Processing Audio File: {filename}" + Style.RESET_ALL)
    print(Fore.MAGENTA + f"============================================================" + Style.RESET_ALL)

    # 1. Extract word timestamps using Whisper
    words = extract_word_timestamps_from_audio(audio_path, model_size=model_size)
    if not words:
        print(Fore.RED + "Failed to extract speech timestamps from audio." + Style.RESET_ALL)
        return None

    # 2. Chunk words into short subtitle blocks
    raw_srt = chunk_words_to_srt(words, max_words_per_line=max_words_per_line)

    # 3. Close small gaps between subtitles
    clean_srt = close_srt_gaps(raw_srt, gap_buffer=gap_buffer)

    # 4. Resolve Gemini API Key (from arg, env, or saved key file)
    key = gemini_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        key_file = os.path.join(SCRIPT_DIR, "gemini_key.txt")
        if os.path.isfile(key_file):
            with open(key_file, 'r', encoding='utf-8') as f:
                key = f.read().strip()

    if key:
        print(Fore.GREEN + f"[Gemini AI] Using API Key from environment/file (Key: {key[:8]}...)" + Style.RESET_ALL)

    # 5. Apply Gemini AI Mascot Tagging
    tagged_srt = tag_srt_with_gemini_ai(clean_srt, api_key=key, model_name=gemini_model)

    # 6. Save final tagged SRT file (purging old SRT files in output_srt to prevent mixups)
    if os.path.isdir(DEFAULT_OUTPUT_DIR):
        for f in os.listdir(DEFAULT_OUTPUT_DIR):
            if os.path.splitext(f)[1].lower() == ".srt" and f != os.path.basename(output_srt_path):
                old_file = os.path.join(DEFAULT_OUTPUT_DIR, f)
                try:
                    os.remove(old_file)
                    print(Fore.YELLOW + f"[CLEANUP] Deleted old output SRT: {old_file}" + Style.RESET_ALL)
                except Exception:
                    pass

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write(tagged_srt)

    print(Fore.GREEN + f"\n[SUCCESS] Tagged SRT generated: {output_srt_path}" + Style.RESET_ALL)

    # 7. Optionally copy audio & tagged SRT to main project input/ directory
    if copy_to_project_input and os.path.isdir(PROJECT_ROOT_INPUT):
        # Purge any old .srt files in input/
        for f in os.listdir(PROJECT_ROOT_INPUT):
            if os.path.splitext(f)[1].lower() == ".srt":
                old_input_srt = os.path.join(PROJECT_ROOT_INPUT, f)
                try:
                    os.remove(old_input_srt)
                    print(Fore.YELLOW + f"[CLEANUP] Deleted old input SRT: {old_input_srt}" + Style.RESET_ALL)
                except Exception:
                    pass

        dest_srt = os.path.join(PROJECT_ROOT_INPUT, "script.srt")
        shutil.copy2(output_srt_path, dest_srt)
        print(Fore.GREEN + f"[AUTO-SYNC] Copied tagged SRT to: {dest_srt}" + Style.RESET_ALL)

        if os.path.exists(audio_path):
            dest_audio = os.path.join(PROJECT_ROOT_INPUT, filename)
            if os.path.abspath(audio_path) != os.path.abspath(dest_audio):
                shutil.copy2(audio_path, dest_audio)
                print(Fore.GREEN + f"[AUTO-SYNC] Copied audio to: {dest_audio}" + Style.RESET_ALL)
        print(Fore.CYAN + f"\nYou can now run: python build_draft.py {base_name}" + Style.RESET_ALL)

    return output_srt_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert voiceover audio (.wav/.mp3) to millisecond-accurate tagged SRT subtitles using Whisper & Gemini 3.6 Flash AI."
    )
    parser.add_argument("project_name", nargs="?", help="Optional name for the output project/file")
    parser.add_argument("--input", "-i", help="Path to input audio file or directory (default: scans srt_generator/input_audio/)")
    parser.add_argument("--output", "-o", help="Path to output .srt file (default: srt_generator/output_srt/)")
    parser.add_argument("--gemini-key", "-k", help="Google Gemini API key for mascot AI tagging")
    parser.add_argument("--gemini-model", default=DEFAULT_GEMINI_MODEL, help=f"Gemini model name (default: {DEFAULT_GEMINI_MODEL})")
    parser.add_argument("--whisper-model", "-m", default="base", help="Whisper model size (tiny, base, small, medium, large)")
    parser.add_argument("--max-words", "-w", type=int, default=5, help="Max words per subtitle line (default: 5)")
    parser.add_argument("--no-sync", action="store_true", help="Do not auto-copy generated files to main project input/ folder")

    args = parser.parse_args()

    # Determine input audio file or folder
    input_path = args.input
    if not input_path:
        os.makedirs(DEFAULT_INPUT_DIR, exist_ok=True)
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        audio_exts = {".wav", ".mp3", ".m4a", ".flac", ".aac"}
        candidates = [os.path.join(DEFAULT_INPUT_DIR, f) for f in os.listdir(DEFAULT_INPUT_DIR) if os.path.splitext(f)[1].lower() in audio_exts]
        if candidates:
            input_path = candidates[0]
        else:
            print(Fore.YELLOW + f"No audio files found in: {DEFAULT_INPUT_DIR}" + Style.RESET_ALL)
            print(Fore.CYAN + f"Drop your .wav or .mp3 voiceover files into '{DEFAULT_INPUT_DIR}' and run again!" + Style.RESET_ALL)
            sys.exit(0)

    if os.path.isdir(input_path):
        audio_exts = {".wav", ".mp3", ".m4a", ".flac", ".aac"}
        files = [os.path.join(input_path, f) for f in os.listdir(input_path) if os.path.splitext(f)[1].lower() in audio_exts]
        for f in files:
            convert_audio_to_tagged_srt(
                audio_path=f,
                output_srt_path=args.output,
                gemini_key=args.gemini_key,
                gemini_model=args.gemini_model,
                model_size=args.whisper_model,
                max_words_per_line=args.max_words,
                copy_to_project_input=not args.no_sync
            )
    else:
        convert_audio_to_tagged_srt(
            audio_path=input_path,
            output_srt_path=args.output,
            gemini_key=args.gemini_key,
            gemini_model=args.gemini_model,
            model_size=args.whisper_model,
            max_words_per_line=args.max_words,
            copy_to_project_input=not args.no_sync
        )


if __name__ == "__main__":
    main()

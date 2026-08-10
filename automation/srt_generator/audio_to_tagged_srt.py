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
import time
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
            except Exception:
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


def merge_gemini_tags_into_raw_srt(raw_srt_content: str, gemini_tagged_text: str) -> str:
    """
    Safely merges [IMG:tag_code] tags from Gemini's response into the original raw SRT content,
    guaranteeing that no original timestamps or block structures are corrupted or truncated.
    """
    raw_blocks = re.split(r'\n\s*\n', raw_srt_content.strip().replace('\r\n', '\n'))
    gemini_blocks = re.split(r'\n\s*\n', gemini_tagged_text.strip().replace('\r\n', '\n'))

    tag_map = {}
    for g_block in gemini_blocks:
        lines = [l.strip() for l in g_block.split('\n') if l.strip()]
        if not lines:
            continue
        idx = None
        if lines[0].isdigit():
            idx = int(lines[0])
            text_lines = lines[2:] if len(lines) >= 3 else lines[1:]
        else:
            text_lines = lines[1:] if '-->' in lines[0] else lines

        full_text = ' '.join(text_lines)
        tags = re.findall(r'\[IMG:\s*[^\]]+?\]', full_text)
        if idx is not None and tags:
            tag_map[idx] = tags

    merged_blocks = []
    for block_idx, r_block in enumerate(raw_blocks, start=1):
        lines = [l.strip() for l in r_block.split('\n') if l.strip()]
        if not lines:
            continue
        idx = int(lines[0]) if lines[0].isdigit() else block_idx
        tags = tag_map.get(idx, [])
        if tags:
            tag_str = ' ' + ' '.join(tags)
            if not any(t in lines[-1] for t in tags):
                lines[-1] = lines[-1] + tag_str
        merged_blocks.append('\n'.join(lines))

    return '\n\n'.join(merged_blocks) + '\n'


def romanize_srt_to_roman_urdu(
    srt_content: str,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_GEMINI_MODEL
) -> str:
    """
    Uses Gemini AI to convert an SRT file's subtitle text into Roman-Urdu
    (Urdu spoken language written in the Latin/English alphabet), as actually
    spoken in the voiceover. English proper nouns and technical/key terms
    (the actual entities being compared, e.g. iPhone, Jibril, Fiqh) are
    kept in their original English spelling.

    This corrects Whisper's output when it either:
      - Transcribes Urdu speech as Arabic-script Urdu, or
      - Mistakenly translates Urdu speech into English phrasing.
    """
    if not api_key:
        print(Fore.YELLOW + "[Roman-Urdu] No Gemini API key — skipping Roman-Urdu conversion." + Style.RESET_ALL)
        return srt_content

    if not srt_content or not srt_content.strip():
        return srt_content

    print(Fore.CYAN + f"[Roman-Urdu] Converting SRT captions to Roman-Urdu (model={model_name})..." + Style.RESET_ALL)

    prompt = f"""You are an expert Roman-Urdu transliterator for a Pakistani YouTube Shorts channel called 'Farq Kya'.

Your task is to rewrite the subtitle text in an SRT file into Roman-Urdu — that is, Urdu as it is actually spoken,
written out using the Latin (English) alphabet. This is NOT translation; it is transliteration of spoken Urdu.

### Rules:
1. Write the text exactly as the speaker would say it in Urdu, using Roman (Latin) script.
   - Example: Instead of "This is Angel Jibril" → write "Ye hai Jibril (AS)"
   - Example: Instead of "What is the difference?" → write "Toh inme farq kya hai?"
   - Example: Instead of "So this is X and this is Y" → write "Toh ye hai X aur ye hai Y"
2. Keep proper nouns (names of Islamic figures, people, places) in their original English spelling.
3. Keep the technical/key comparison terms (the actual entities being compared, e.g. "iPhone", "Fiqh", "Sunnah") in their original English spelling.
4. Do NOT translate meaning into English phrasing. The output must sound like natural spoken Urdu.
5. Do NOT change any SRT index numbers or timestamps — keep them EXACTLY identical.
6. Only rewrite the text lines. Leave index numbers and timestamp lines untouched.
7. Return ONLY the final complete SRT content. No markdown, no backticks, no extra explanation.

--- INPUT SRT ---
{srt_content}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096}
    }
    headers = {"Content-Type": "application/json"}

    models_to_try = [model_name, "gemini-2.0-flash", "gemini-1.5-flash"]
    seen_models = []
    for m in models_to_try:
        if m not in seen_models:
            seen_models.append(m)

    for m_name in seen_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
        for attempt in range(1, 4):
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
                            if output_text:
                                print(Fore.GREEN + f"[Roman-Urdu] Conversion successful with '{m_name}'!" + Style.RESET_ALL)
                                return output_text + "\n"
                elif r.status_code == 429:
                    print(Fore.YELLOW + f"[Roman-Urdu Warning] API HTTP 429 Rate Limit (attempt {attempt}/3). Retrying in 5s..." + Style.RESET_ALL)
                    time.sleep(5.0)
                    continue
                else:
                    print(Fore.YELLOW + f"[Roman-Urdu Warning] API HTTP {r.status_code} for '{m_name}': {r.text[:200]}" + Style.RESET_ALL)
                    break
            except Exception as e:
                print(Fore.YELLOW + f"[Roman-Urdu Warning] Request failed for '{m_name}': {e}" + Style.RESET_ALL)
                break

    return srt_content


def tag_srt_with_gemini_ai(
    raw_srt_content: str,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_GEMINI_MODEL
) -> str:
    """
    Uses Google Gemini 3.6 Flash API to analyze subtitle script context and insert mascot image tags [IMG:tag_code].
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            root_env = os.path.join(PROJECT_ROOT, ".env")
            if os.path.isfile(root_env):
                try:
                    with open(root_env, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("GEMINI_API_KEY="):
                                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                break
                except Exception:
                    pass

    if not api_key:
        print(Fore.YELLOW + "[Gemini AI] No API key found. Returning clean untagged SRT." + Style.RESET_ALL)
        return raw_srt_content

    print(Fore.CYAN + f"[Gemini AI] Analyzing script context and tagging mascot overlays (model={model_name})..." + Style.RESET_ALL)

    prompt = f"""You are an expert AI Short-Form Video Director & Mascot Tagging Engine.
Your job is to analyze an untagged SRT subtitle file for a comparison/versus video and insert ONE mascot tag `[IMG:tag_code]` at the end of relevant text lines.

### STEP 1: ENTITY MAPPING
First identify the two entities being compared:
- ENTITY A (Left Entity): the first item introduced (e.g. Wolverine, Superman, iPhone)
- ENTITY B (Right Entity): the second item introduced (e.g. Deadpool, Shazam, Samsung)

### STEP 2: AVAILABLE MASCOT TAGS

1. `[IMG:left]`         — ENTITY A is being introduced or explained.
2. `[IMG:right]`        — ENTITY B is being introduced or explained. NEVER use left for Entity B.
3. `[IMG:wtd]`          — Comparison question or curiosity (lines containing "?", "what's the difference", "which one", etc.).
4. `[IMG:disagree]`     — Negation, debunk, or contrast statement ("They don't.", "Wrong.", "Actually...", "No.").
5. `[IMG:remember_this]`— Core takeaway, key rule, or memory hook (final insight before the outro).
6. `[IMG:shocked]`      — Surprising or jaw-dropping fact ("insane", "wild", "wait—").
7. `[IMG:twohandsopen]` — Line discusses BOTH entities equally.
8. `[IMG:normal]`       — Neutral filler or transitional line with no entity signal.
9. `[IMG:final_end]`    — Outro, CTA, or subscribe prompt. Use ONLY on the very last line.

### STEP 3: TAGGING RULES

- **Match pose to meaning, not position.** A pose must reflect what the line SAYS, not where it appears.
- **Hold poses across beats.** A pose should cover 2–4 consecutive lines (a coherent thought/beat) before switching. Do NOT flicker between poses on every single line.
- **Avoid awkward jumps.** Do not switch from `disagree` directly to `left` or `right`. Do not switch from `wtd` directly to `disagree`. Bridge with a neutral pose if needed.
- **`remember_this` is late-script only.** Do not use it before ~75% through the script. Reserve it for the closing insight.
- **`final_end` on the very last line only.**
- Do NOT change any SRT index numbers or timestamps. Keep them EXACTLY identical.
- Append `[IMG:tag_code]` to the end of the text line. Every line should have exactly one tag.
- Return ONLY the final complete tagged SRT content. No markdown, no backticks, no extra explanation.

--- INPUT SRT ---
{raw_srt_content}
"""

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

    models_to_try = [model_name, "gemini-2.0-flash", "gemini-1.5-flash"]
    seen_models = []
    for m in models_to_try:
        if m not in seen_models:
            seen_models.append(m)

    for m_name in seen_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
        for attempt in range(1, 4):
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
                            print(Fore.GREEN + f"[Gemini AI] Mascot tagging successfully completed with '{m_name}'!" + Style.RESET_ALL)
                            return merge_gemini_tags_into_raw_srt(raw_srt_content, output_text)
                elif r.status_code == 429:
                    print(Fore.YELLOW + f"[Gemini AI Warning] API HTTP 429 Rate Limit (attempt {attempt}/3). Retrying in 5s..." + Style.RESET_ALL)
                    time.sleep(5.0)
                    continue
                else:
                    print(Fore.YELLOW + f"[Gemini AI Warning] API HTTP {r.status_code} for '{m_name}': {r.text[:200]}" + Style.RESET_ALL)
                    break
            except Exception as e:
                print(Fore.YELLOW + f"[Gemini AI Warning] Request failed for '{m_name}': {e}" + Style.RESET_ALL)
                break

    return raw_srt_content


def align_script_text_with_timestamps(ref_text: str, whisper_words: List[Dict]) -> List[Dict]:
    """
    Replaces raw Whisper transcribed words (which may be in Arabic-script Urdu or poorly transcribed)
    with the exact words from the reference script_text, keeping Whisper's millisecond audio timestamps.
    """
    ref_words = [w.strip() for w in ref_text.strip().split() if w.strip()]
    if not ref_words or not whisper_words:
        return whisper_words

    total_whisper = len(whisper_words)
    total_ref = len(ref_words)

    aligned_words = []
    for i, w in enumerate(ref_words):
        w_idx = int(round(i * (total_whisper - 1) / max(1, total_ref - 1)))
        w_idx = max(0, min(total_whisper - 1, w_idx))

        aligned_words.append({
            "word": w,
            "start": whisper_words[w_idx]["start"],
            "end": whisper_words[w_idx]["end"]
        })

    return aligned_words


def convert_audio_to_tagged_srt(
    audio_path: str,
    output_srt_path: Optional[str] = None,
    gemini_key: Optional[str] = None,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    model_size: str = "base",
    max_words_per_line: int = 4,  # hard cap: retag_and_split.py enforces <=4 words
    gap_buffer: float = 0.05,
    copy_to_project_input: bool = True,
    channel: str = "dontmixthis",
    script_text: Optional[str] = None
) -> Optional[str]:
    """
    Main conversion pipeline: Audio -> Whisper STT Timestamps -> Script Alignment -> Gemini AI Mascot Tagging -> Saved SRT.
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
    print(Fore.MAGENTA + f"Processing Audio File: {filename} (Channel: {channel.upper()})" + Style.RESET_ALL)
    print(Fore.MAGENTA + f"============================================================" + Style.RESET_ALL)

    # 1. Extract word timestamps using Whisper
    lang_arg = None
    words = extract_word_timestamps_from_audio(audio_path, model_size=model_size, language=lang_arg)
    if not words:
        print(Fore.RED + "Failed to extract speech timestamps from audio." + Style.RESET_ALL)
        return None

    # 1b. Align reference script text (English / Latin characters) with speech timestamps
    if not script_text:
        audio_dir = os.path.dirname(audio_path)
        candidate_txts = [
            os.path.join(audio_dir, "script.txt"),
            os.path.join(PROJECT_ROOT_INPUT, "script.txt"),
            os.path.join(PROJECT_ROOT, "tts_generator", "input_text", "script.txt")
        ]
        for c_txt in candidate_txts:
            if os.path.isfile(c_txt):
                try:
                    with open(c_txt, "r", encoding="utf-8") as _sf:
                        content = _sf.read().strip()
                        if content:
                            script_text = content
                            print(Fore.CYAN + f"[Reference Script] Auto-loaded reference script from: {c_txt}" + Style.RESET_ALL)
                            break
                except Exception:
                    pass

    if script_text and words:
        words = align_script_text_with_timestamps(script_text, words)
        print(Fore.GREEN + f"[Reference Script Alignment] Aligned captions with {len(words)} English script words." + Style.RESET_ALL)

    # 2. Chunk words into short subtitle blocks
    raw_srt = chunk_words_to_srt(words, max_words_per_line=max_words_per_line)

    # 3. Close small gaps between subtitles
    clean_srt = close_srt_gaps(raw_srt, gap_buffer=gap_buffer)

    # 3b. For farqkya channel: convert Whisper output to Roman-Urdu via Gemini ONLY if no reference script was available
    if channel == "farqkya" and not script_text:
        roman_key = gemini_key or os.environ.get("GEMINI_API_KEY")
        if not roman_key:
            key_file = os.path.join(SCRIPT_DIR, "gemini_key.txt")
            if os.path.isfile(key_file):
                with open(key_file, 'r', encoding='utf-8') as _kf:
                    roman_key = _kf.read().strip()
        clean_srt = romanize_srt_to_roman_urdu(clean_srt, api_key=roman_key, model_name=gemini_model)

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

    # 5b. Smart Mascot Tagging & Subtitle Splitter Post-Processing
    try:
        try:
            from srt_generator.retag_and_split import parse_srt, build_tagged_entries, render_srt
        except ImportError:
            from retag_and_split import parse_srt, build_tagged_entries, render_srt
        parsed_entries = parse_srt(tagged_srt)
        if parsed_entries:
            tagged_entries = build_tagged_entries(parsed_entries, min_hold=2, max_words=max_words_per_line)
            tagged_srt = render_srt(tagged_entries)
            print(Fore.GREEN + f"[Post-Processor] Applied smart 11-pose tagging & beat-holding (<={max_words_per_line} words)." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.YELLOW + f"[Post-Processor Warning] Retag post-processing skipped: {e}" + Style.RESET_ALL)



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
    parser.add_argument("--max-words", "-w", type=int, default=4, help="Max words per subtitle line (default: 4). Hard-enforced by retag_and_split.py post-processing.")
    parser.add_argument("--channel", "-c", choices=["dontmixthis", "farqkya"], default="dontmixthis", help="Target YouTube channel ('dontmixthis' or 'farqkya')")
    parser.add_argument("--script-text", help="Optional reference script text")
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
                copy_to_project_input=not args.no_sync,
                channel=args.channel,
                script_text=args.script_text
            )
    else:
        convert_audio_to_tagged_srt(
            audio_path=input_path,
            output_srt_path=args.output,
            gemini_key=args.gemini_key,
            gemini_model=args.gemini_model,
            model_size=args.whisper_model,
            max_words_per_line=args.max_words,
            copy_to_project_input=not args.no_sync,
            channel=args.channel,
            script_text=args.script_text
        )


if __name__ == "__main__":
    main()

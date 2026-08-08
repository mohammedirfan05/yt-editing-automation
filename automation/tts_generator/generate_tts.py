#!/usr/bin/env python3
r"""
Google Gemini 3.1 Flash TTS Generator (Supports google-genai SDK & HTTP REST API Fallback)

Converts speech transcript text into high-quality, expressive voiceover audio (.wav)
using Google's Gemini 3.1 Flash TTS Preview engine.

Usage:
    python tts_generator/generate_tts.py -t "[amused] This is Superman. This is Shazam. So, what's the difference?"
    python tts_generator/generate_tts.py -i input_text/script.txt --auto-build SupermanVsShazam
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import struct
import sys
from typing import Optional

import requests
from colorama import Fore, Style, init

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Safe SDK Import (Falls back to HTTP REST API if SDK not available)
try:
    from google import genai
    from google.genai import types
    HAS_GENAI_SDK = True
except Exception:
    genai = None
    types = None
    HAS_GENAI_SDK = False

init(autoreset=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_INPUT_DIR = os.path.join(SCRIPT_DIR, "input_text")
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_audio")

SRT_INPUT_AUDIO_DIR = os.path.join(PROJECT_ROOT, "srt_generator", "input_audio")
PROJECT_ROOT_INPUT = os.path.join(PROJECT_ROOT, "input")

# Default Google Gemini TTS Settings (As requested)
DEFAULT_TTS_MODEL = "gemini-3.1-flash-tts-preview"
DEFAULT_VOICE = "Puck"  # Puck (Upbeat, Middle pitch)

DEFAULT_SCENE = "A fast-paced educational explainer breaking down story terminology, direct-to-camera style"
DEFAULT_CONTEXT = "Energetic YouTube Shorts narration, quick pacing, conversational but confident tone"


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


def save_binary_file(file_name: str, data: bytes) -> None:
    """Saves binary audio data buffer to file."""
    os.makedirs(os.path.dirname(os.path.abspath(file_name)), exist_ok=True)
    with open(file_name, "wb") as f:
        f.write(data)
    print(Fore.GREEN + f"[SUCCESS] Audio saved to: {file_name}" + Style.RESET_ALL)


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters.

    Args:
        audio_data: The raw audio data as a bytes object.
        mime_type: Mime type of the audio data.

    Returns:
        A bytes object representing the WAV file header concatenated with raw audio data.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> dict:
    """Parses bits per sample and rate from an audio MIME type string.

    Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

    Returns:
        A dictionary with "bits_per_sample" and "rate" keys.
    """
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L") or "L16" in param:
            try:
                if "L" in param:
                    bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}


def generate_speech_audio_rest(
    formatted_prompt: str,
    output_wav_path: str,
    voice_name: str,
    model: str,
    api_key: str
) -> Optional[str]:
    """Fallback REST API generator when SDK is not installed in current Python environment."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": formatted_prompt}]}],
        "generationConfig": {
            "temperature": 1,
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name
                    }
                }
            }
        }
    }
    headers = {"Content-Type": "application/json"}

    import time
    max_retries = 4
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                res_data = r.json()
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    collected_data = bytearray()
                    last_mime = "audio/L16;rate=24000"
                    for part in parts:
                        if "inlineData" in part:
                            data_b64 = part["inlineData"].get("data", "")
                            if part["inlineData"].get("mimeType"):
                                last_mime = part["inlineData"].get("mimeType")
                            collected_data.extend(base64.b64decode(data_b64))

                    if collected_data:
                        file_extension = mimetypes.guess_extension(last_mime)
                        data_buffer = bytes(collected_data)
                        if file_extension is None or file_extension == "":
                            data_buffer = convert_to_wav(data_buffer, last_mime)
                        save_binary_file(output_wav_path, data_buffer)
                        return output_wav_path
            elif r.status_code == 429:
                retry_seconds = (attempt + 1) * 5
                try:
                    err_json = r.json()
                    details = err_json.get("error", {}).get("details", [])
                    for d in details:
                        if "retryDelay" in d:
                            delay_str = str(d["retryDelay"]).rstrip("s")
                            retry_seconds = int(float(delay_str)) + 2
                except Exception:
                    pass

                print(Fore.YELLOW + f"⚠️ Google Rate Limit (429). Retrying in {retry_seconds}s (Attempt {attempt}/{max_retries})..." + Style.RESET_ALL)
                time.sleep(retry_seconds)
            else:
                print(Fore.RED + f"REST API HTTP Error ({r.status_code}): {r.text[:300]}" + Style.RESET_ALL)
                break
        except Exception as e:
            print(Fore.RED + f"REST API Request Exception: {e}" + Style.RESET_ALL)
            time.sleep(2)

    return None


def generate_speech_audio(
    text_script: str,
    output_wav_path: str,
    voice_name: str = DEFAULT_VOICE,
    scene: str = DEFAULT_SCENE,
    sample_context: str = DEFAULT_CONTEXT,
    model: str = DEFAULT_TTS_MODEL,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Generates speech audio using google-genai SDK or REST API fallback.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        print(Fore.RED + "Error: GEMINI_API_KEY is not set in root .env file!" + Style.RESET_ALL)
        return None

    formatted_prompt = f"""## Scene:
{scene}

## Sample Context:
{sample_context}

## Transcript:
{text_script.strip()}"""

    print(Fore.CYAN + f"\n[Google TTS] Requesting speech audio from {model}..." + Style.RESET_ALL)
    print(Fore.CYAN + f" - Voice Model   : {voice_name} (Upbeat, Middle pitch)" + Style.RESET_ALL)
    print(Fore.CYAN + f" - Scene         : {scene}" + Style.RESET_ALL)
    print(Fore.CYAN + f" - Context       : {sample_context}" + Style.RESET_ALL)

    # Try SDK if installed
    if HAS_GENAI_SDK:
        try:
            client = genai.Client(api_key=key)
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=formatted_prompt),
                    ],
                ),
            ]
            generate_content_config = types.GenerateContentConfig(
                temperature=1,
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                ),
            )
            collected_data = bytearray()
            last_mime_type = "audio/L16;rate=24000"

            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.parts is None:
                    continue
                if chunk.parts[0].inline_data and chunk.parts[0].inline_data.data:
                    inline_data = chunk.parts[0].inline_data
                    if inline_data.mime_type:
                        last_mime_type = inline_data.mime_type
                    collected_data.extend(inline_data.data)

            if collected_data:
                file_extension = mimetypes.guess_extension(last_mime_type)
                data_buffer = bytes(collected_data)
                if file_extension is None or file_extension == "":
                    data_buffer = convert_to_wav(data_buffer, last_mime_type)

                save_binary_file(output_wav_path, data_buffer)
                return output_wav_path
        except Exception as e_sdk:
            print(Fore.YELLOW + f"[SDK Warning] google-genai streaming exception: {e_sdk}. Falling back to REST API..." + Style.RESET_ALL)

    # Fallback to REST API if SDK missing or raised exception
    return generate_speech_audio_rest(
        formatted_prompt=formatted_prompt,
        output_wav_path=output_wav_path,
        voice_name=voice_name,
        model=model,
        api_key=key
    )


def clean_old_audio_files(target_dir: str) -> None:
    """Deletes existing audio files from target directory to prevent mixups."""
    if os.path.isdir(target_dir):
        audio_exts = {".wav", ".mp3", ".m4a", ".flac", ".aac"}
        for f in os.listdir(target_dir):
            if os.path.splitext(f)[1].lower() in audio_exts:
                old_file = os.path.join(target_dir, f)
                try:
                    os.remove(old_file)
                    print(Fore.YELLOW + f"[CLEANUP] Deleted old audio file: {old_file}" + Style.RESET_ALL)
                except Exception:
                    pass


def sync_audio_to_workflow(audio_path: str) -> None:
    """
    Syncs generated audio file to srt_generator/input_audio/ and input/ for seamless execution,
    after purging old audio files to prevent mixups.
    """
    filename = os.path.basename(audio_path)

    # 1. Clean old audio files in output_audio directory (except current new file)
    if os.path.isdir(DEFAULT_OUTPUT_DIR):
        audio_exts = {".wav", ".mp3", ".m4a", ".flac", ".aac"}
        for f in os.listdir(DEFAULT_OUTPUT_DIR):
            if f != filename and os.path.splitext(f)[1].lower() in audio_exts:
                old_file = os.path.join(DEFAULT_OUTPUT_DIR, f)
                try:
                    os.remove(old_file)
                    print(Fore.YELLOW + f"[CLEANUP] Deleted old output audio: {old_file}" + Style.RESET_ALL)
                except Exception:
                    pass

    # 2. Clean and sync to srt_generator/input_audio/
    if os.path.isdir(SRT_INPUT_AUDIO_DIR):
        clean_old_audio_files(SRT_INPUT_AUDIO_DIR)
        dest1 = os.path.join(SRT_INPUT_AUDIO_DIR, filename)
        shutil.copy2(audio_path, dest1)
        print(Fore.GREEN + f"[AUTO-SYNC] Copied voiceover audio to: {dest1}" + Style.RESET_ALL)

    # 3. Clean and sync to input/
    if os.path.isdir(PROJECT_ROOT_INPUT):
        clean_old_audio_files(PROJECT_ROOT_INPUT)
        dest2 = os.path.join(PROJECT_ROOT_INPUT, filename)
        shutil.copy2(audio_path, dest2)
        print(Fore.GREEN + f"[AUTO-SYNC] Copied voiceover audio to: {dest2}" + Style.RESET_ALL)


def main():
    parser = argparse.ArgumentParser(
        description="Google Gemini 3.1 Flash TTS Generator (Supports SDK & REST API)."
    )
    parser.add_argument("--text", "-t", type=str, help="Speech transcript text string to generate audio for")
    parser.add_argument("--input", "-i", type=str, help="Path to input text script file (.txt)")
    parser.add_argument("--output", "-o", type=str, help="Output .wav path (default: tts_generator/output_audio/voiceover.wav)")
    parser.add_argument("--voice", "-v", default=DEFAULT_VOICE, help=f"Voice model name (default: {DEFAULT_VOICE})")
    parser.add_argument("--scene", default=DEFAULT_SCENE, help="Scene description")
    parser.add_argument("--context", default=DEFAULT_CONTEXT, help="Sample Context / voice persona description")
    parser.add_argument("--auto-build", help="Optional project name to run end-to-end auto build after TTS generation")

    args = parser.parse_args()

    script_text = args.text
    if not script_text and args.input:
        if os.path.isfile(args.input):
            with open(args.input, "r", encoding="utf-8") as f:
                script_text = f.read()
        else:
            script_text = args.input

    if not script_text:
        os.makedirs(DEFAULT_INPUT_DIR, exist_ok=True)
        txt_files = [os.path.join(DEFAULT_INPUT_DIR, f) for f in os.listdir(DEFAULT_INPUT_DIR) if f.lower().endswith(".txt")]
        if txt_files:
            found_file = txt_files[0]
            print(Fore.CYAN + f"Found text script file: {found_file}" + Style.RESET_ALL)
            with open(found_file, "r", encoding="utf-8") as f:
                script_text = f.read()
        else:
            print(Fore.YELLOW + f"No transcript provided via --text and no .txt files found in: {DEFAULT_INPUT_DIR}" + Style.RESET_ALL)
            print(Fore.CYAN + "\nUsage Examples:" + Style.RESET_ALL)
            print("  python tts_generator/generate_tts.py -t \"[amused] This is Superman. This is Shazam.\"" )
            print("  python tts_generator/generate_tts.py -i input_text/script.txt\n")
            sys.exit(0)

    output_path = args.output
    if not output_path:
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(DEFAULT_OUTPUT_DIR, "voiceover.wav")

    result = generate_speech_audio(
        text_script=script_text,
        output_wav_path=output_path,
        voice_name=args.voice,
        scene=args.scene,
        sample_context=args.context
    )

    if not result:
        print(Fore.RED + "\n[ERROR] Stage 1: Speech audio generation failed (Google Gemini API Quota Exceeded / Rate Limit). Aborting pipeline." + Style.RESET_ALL)
        sys.exit(1)

    sync_audio_to_workflow(result)

    if args.auto_build:
        print(Fore.MAGENTA + f"\n============================================================" + Style.RESET_ALL)
        print(Fore.MAGENTA + f"Running End-to-End Pipeline: Tagged SRT + CapCut Draft..." + Style.RESET_ALL)
        print(Fore.MAGENTA + f"============================================================" + Style.RESET_ALL)

        srt_script = os.path.join(PROJECT_ROOT, "srt_generator", "audio_to_tagged_srt.py")
        build_script = os.path.join(PROJECT_ROOT, "build_draft.py")

        os.system(f'"{sys.executable}" "{srt_script}" -i "{result}"')
        os.system(f'"{sys.executable}" "{build_script}" "{args.auto_build}"')


if __name__ == "__main__":
    main()

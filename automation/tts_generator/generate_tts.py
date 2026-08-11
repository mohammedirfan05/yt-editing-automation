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
import time
from typing import List, Optional

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

# Default Google Gemini TTS Settings — model ID centralized in src/model_config.py
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from src.model_config import get_tts_model

DEFAULT_TTS_MODEL = get_tts_model()

# Built-in per-channel defaults (Fallback if config/channel_defaults.json is missing/unreadable)
BUILTIN_CHANNEL_DEFAULTS = {
    "dontmixthis": {
        "display_name": "Dont Mix This",
        "handle": "@dontmixthis",
        "mascot_dir": "assets/mascot",
        "draft_prefix": "dontmixthis",
        "tts": {
            "voice": "Puck",
            "scene": "A fast-paced educational explainer breaking down story terminology, direct-to-camera style",
            "context": "Energetic YouTube Shorts narration, quick pacing, conversational but confident tone"
        }
    },
    "farqkya": {
        "display_name": "Farq Kya",
        "handle": "@farqkya",
        "mascot_dir": "assets/mascot_urdu",
        "draft_prefix": "farqkya",
        "tts": {
            "voice": "Alnilam",
            "scene": "Calm, confident YouTube Shorts narration, natural Roman Urdu, slightly fast-paced but relaxed — like explaining something clearly to a friend, not reading a script.",
            "context": "A short educational explainer comparing two Islamic terms or concepts, direct-to-camera style, simple sentence structure with natural pauses between thoughts."
        }
    }
}


def load_channel_defaults() -> dict:
    """Loads channel defaults from config/channel_defaults.json if available."""
    config_path = os.path.join(PROJECT_ROOT, "config", "channel_defaults.json")
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
        except Exception:
            pass
    return BUILTIN_CHANNEL_DEFAULTS


def get_channel_tts_config(channel_name: str) -> dict:
    """Gets the TTS defaults (voice, scene, context) for a given channel."""
    all_channels = load_channel_defaults()
    ch_key = (channel_name or "dontmixthis").lower().strip()
    channel_data = all_channels.get(ch_key, all_channels.get("dontmixthis", BUILTIN_CHANNEL_DEFAULTS["dontmixthis"]))
    return channel_data.get("tts", BUILTIN_CHANNEL_DEFAULTS["dontmixthis"]["tts"])


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

    max_retries = 5
    backoff_delay = 5.0

    time.sleep(2.0)

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
            elif r.status_code in (401, 403):
                print(Fore.YELLOW + f"\n⚠️ Google API Authentication Error ({r.status_code}). Invalid or expired GEMINI_API_KEY." + Style.RESET_ALL)
                return None
            elif r.status_code == 429:
                retry_seconds = backoff_delay
                try:
                    err_json = r.json()
                    details = err_json.get("error", {}).get("details", [])
                    for d in details:
                        if "retryDelay" in d:
                            delay_str = str(d["retryDelay"]).rstrip("s")
                            retry_seconds = float(delay_str) + 2.0
                except Exception:
                    pass

                print(Fore.YELLOW + f"⚠️ Google AI Studio Rate Limit (429). Waiting {retry_seconds:.1f}s before retry (Attempt {attempt}/{max_retries})..." + Style.RESET_ALL)
                time.sleep(retry_seconds)
                backoff_delay *= 2.5
            else:
                print(Fore.RED + f"REST API HTTP Error ({r.status_code}): {r.text[:300]}" + Style.RESET_ALL)
                time.sleep(backoff_delay)
                backoff_delay *= 2.0
        except Exception as e:
            print(Fore.RED + f"REST API Request Exception: {e}" + Style.RESET_ALL)
            time.sleep(backoff_delay)
            backoff_delay *= 2.0

    return None



def generate_speech_audio(
    text_script: str,
    output_wav_path: str,
    voice_name: Optional[str] = None,
    scene: Optional[str] = None,
    sample_context: Optional[str] = None,
    channel: str = "dontmixthis",
    model: str = DEFAULT_TTS_MODEL,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Generates speech audio using google-genai SDK or REST API fallback.
    """
    tts_defaults = get_channel_tts_config(channel)
    final_voice = voice_name if voice_name else tts_defaults["voice"]
    final_scene = scene if scene else tts_defaults["scene"]
    final_context = sample_context if sample_context else tts_defaults["context"]

    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        # Load from root .env if available
        root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.isfile(root_env):
            try:
                with open(root_env, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass

    if not key:
        print(Fore.RED + "Error: GEMINI_API_KEY is not set in root .env file!" + Style.RESET_ALL)
        return None

    formatted_prompt = f"""## Scene:
{final_scene}

## Sample Context:
{final_context}

## Transcript:
{text_script.strip()}"""

    print(Fore.CYAN + f"\n[Google TTS] Requesting speech audio from {model}..." + Style.RESET_ALL)
    print(Fore.CYAN + f" - Channel       : {channel}" + Style.RESET_ALL)
    print(Fore.CYAN + f" - Voice Model   : {final_voice}" + Style.RESET_ALL)
    print(Fore.CYAN + f" - Scene         : {final_scene}" + Style.RESET_ALL)
    print(Fore.CYAN + f" - Context       : {final_context}" + Style.RESET_ALL)

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
                            voice_name=final_voice
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
        voice_name=final_voice,
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


def prompt_manual_audio_fallback(
    script_text: str,
    output_path: str,
    channel: str,
    scene: str,
    context: str
) -> str:
    """
    Displays the Scene, Sample Context, and Script to the user,
    specifies the target audio file location, and pauses until the user pastes the audio file and presses ENTER.
    """
    abs_output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(abs_output_path)
    os.makedirs(output_dir, exist_ok=True)

    print(Fore.YELLOW + "\n" + "=" * 72 + Style.RESET_ALL)
    print(Fore.YELLOW + " ⚠️ GOOGLE GEMINI TTS RATE LIMIT DETECTED — MANUAL AUDIO FALLBACK ACTIVE" + Style.RESET_ALL)
    print(Fore.YELLOW + "=" * 72 + Style.RESET_ALL)
    print(Fore.CYAN + "\n📋 SCENE DESCRIPTION:" + Style.RESET_ALL)
    print(f"   {scene}")
    print(Fore.CYAN + "\n🎯 SAMPLE CONTEXT:" + Style.RESET_ALL)
    print(f"   {context}")
    print(Fore.CYAN + "\n📜 TRANSCRIPT / SCRIPT TO RECORD OR GENERATE:" + Style.RESET_ALL)
    print(Fore.WHITE + f"   \"{script_text.strip()}\"" + Style.RESET_ALL)
    print(Fore.YELLOW + "\n📁 TARGET AUDIO FILE LOCATION:" + Style.RESET_ALL)
    print(Fore.GREEN + f"   👉 {abs_output_path}" + Style.RESET_ALL)
    print(Fore.YELLOW + "\n💡 INSTRUCTIONS:" + Style.RESET_ALL)
    print(f"   1. Generate or record your voiceover audio file.")
    print(f"   2. Paste/save the audio file as '.wav' or '.mp3' at the exact target path above.")

    input(Fore.MAGENTA + "\n👉 Press ENTER once you have placed the audio file at the path above to resume... " + Style.RESET_ALL)

    valid_exts = [".wav", ".mp3", ".m4a", ".aac"]
    found_file = None

    if os.path.isfile(abs_output_path):
        found_file = abs_output_path
    else:
        base_no_ext = os.path.splitext(abs_output_path)[0]
        for ext in valid_exts:
            candidate = base_no_ext + ext
            if os.path.isfile(candidate):
                found_file = candidate
                break

    while not found_file or not os.path.isfile(found_file):
        print(Fore.RED + f"\n❌ Audio file not found at: {abs_output_path}" + Style.RESET_ALL)
        input(Fore.YELLOW + "👉 Please paste/save the voiceover audio file and press ENTER to retry... " + Style.RESET_ALL)
        if os.path.isfile(abs_output_path):
            found_file = abs_output_path
        else:
            base_no_ext = os.path.splitext(abs_output_path)[0]
            for ext in valid_exts:
                candidate = base_no_ext + ext
                if os.path.isfile(candidate):
                    found_file = candidate
                    break

    # If saved as mp3/m4a under a different extension, copy/rename to output_path if needed
    if found_file != abs_output_path and not abs_output_path.lower().endswith(os.path.splitext(found_file)[1].lower()):
        try:
            shutil.copy2(found_file, abs_output_path)
            found_file = abs_output_path
        except Exception:
            pass

    print(Fore.GREEN + f"\n✅ Verified manual audio file: {found_file}" + Style.RESET_ALL)
    return found_file


def main():
    parser = argparse.ArgumentParser(
        description="Google Gemini 3.1 Flash TTS Generator (Supports SDK & REST API)."
    )
    parser.add_argument("--text", "-t", type=str, help="Speech transcript text string to generate audio for")
    parser.add_argument("--input", "-i", type=str, help="Path to input text script file (.txt)")
    parser.add_argument("--output", "-o", type=str, help="Output .wav path (default: tts_generator/output_audio/voiceover.wav)")
    parser.add_argument("--channel", "-c", choices=["dontmixthis", "farqkya"], default="dontmixthis", help="Target YouTube channel ('dontmixthis' or 'farqkya'; default: 'dontmixthis')")
    parser.add_argument("--voice", "-v", default=None, help="Voice model name (default: auto-selected by --channel)")
    parser.add_argument("--scene", default=None, help="Scene description (default: auto-selected by --channel)")
    parser.add_argument("--context", default=None, help="Sample Context description (default: auto-selected by --channel)")
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
            print("  python tts_generator/generate_tts.py -i input_text/script.txt --channel farqkya\n")
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
        sample_context=args.context,
        channel=args.channel
    )

    if not result:
        tts_defaults = get_channel_tts_config(args.channel)
        scene_desc = args.scene if args.scene else tts_defaults["scene"]
        context_desc = args.context if args.context else tts_defaults["context"]

        result = prompt_manual_audio_fallback(
            script_text=script_text,
            output_path=output_path,
            channel=args.channel,
            scene=scene_desc,
            context=context_desc
        )


    sync_audio_to_workflow(result)

    if args.auto_build:
        print(Fore.MAGENTA + f"\n============================================================" + Style.RESET_ALL)
        print(Fore.MAGENTA + f"Running End-to-End Pipeline: Tagged SRT + CapCut Draft..." + Style.RESET_ALL)
        print(Fore.MAGENTA + f"============================================================" + Style.RESET_ALL)

        srt_script = os.path.join(PROJECT_ROOT, "srt_generator", "audio_to_tagged_srt.py")
        build_script = os.path.join(PROJECT_ROOT, "build_draft.py")

        os.system(f'"{sys.executable}" "{srt_script}" -i "{result}"')
        os.system(f'"{sys.executable}" "{build_script}" "{args.auto_build}" --channel "{args.channel}"')


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
r"""
⚡ YouTube Shorts Editing Automation Engine — Master Interactive CLI

Usage:
    # Interactive mode (Prompt for project name & script text):
    python run.py

    # Non-interactive mode:
    python run.py SupermanVsShazam -t "[amused] This is Superman. This is Shazam. So, what's the difference?"
"""

import argparse
import os
import sys

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from colorama import Fore, Style, init

init(autoreset=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(SCRIPT_DIR, "input")
TTS_SCRIPT = os.path.join(SCRIPT_DIR, "tts_generator", "generate_tts.py")
SRT_SCRIPT = os.path.join(SCRIPT_DIR, "srt_generator", "audio_to_tagged_srt.py")
BUILD_SCRIPT = os.path.join(SCRIPT_DIR, "build_draft.py")


def check_input_images() -> bool:
    """Checks if image1 and image2 exist in the input/ folder."""
    if not os.path.isdir(INPUT_DIR):
        os.makedirs(INPUT_DIR, exist_ok=True)
        return False

    valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    img1_found = False
    img2_found = False

    for f in os.listdir(INPUT_DIR):
        name_lower = os.path.splitext(f)[0].lower()
        ext_lower = os.path.splitext(f)[1].lower()
        if ext_lower in valid_exts:
            if name_lower in ["image1", "img1", "left_image", "1"]:
                img1_found = True
            elif name_lower in ["image2", "img2", "right_image", "2"]:
                img2_found = True

    if not img1_found or not img2_found:
        print(Fore.YELLOW + "\n[NOTICE] Input Image Check:" + Style.RESET_ALL)
        if not img1_found:
            print(Fore.YELLOW + " ⚠️ Missing Image 1 in 'input/' (e.g. input/image1.jpg)" + Style.RESET_ALL)
        if not img2_found:
            print(Fore.YELLOW + " ⚠️ Missing Image 2 in 'input/' (e.g. input/image2.png)" + Style.RESET_ALL)
        print(Fore.CYAN + " (You can still proceed, but comparison image tracks won't be rendered if missing)\n" + Style.RESET_ALL)
        return False

    print(Fore.GREEN + "✓ Image 1 and Image 2 verified in 'input/'" + Style.RESET_ALL)
    return True


def get_multiline_input(prompt_msg: str) -> str:
    """Prompts the user for multi-line text script input."""
    print(Fore.CYAN + prompt_msg + Style.RESET_ALL)
    print(Fore.WHITE + "(Paste your text script below. Press ENTER, then Ctrl+Z and ENTER or type 'END' on a new line when finished):" + Style.RESET_ALL)
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines).strip()


import subprocess

def run_python_script(script_path: str, args: list) -> int:
    """Runs a python sub-script cleanly using subprocess."""
    cmd = [sys.executable, script_path] + args
    res = subprocess.run(cmd)
    return res.returncode


def main():
    print(Fore.MAGENTA + "=" * 65 + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + "   🎬 YOUTUBE SHORTS EDITING AUTOMATION ENGINE   " + Style.RESET_ALL)
    print(Fore.MAGENTA + "=" * 65 + Style.RESET_ALL)

    parser = argparse.ArgumentParser(description="Master Interactive CLI for Shorts Video Creation Pipeline")
    parser.add_argument("project_name", nargs="?", help="Project name for CapCut Desktop (e.g. SupermanVsShazam)")
    parser.add_argument("--text", "-t", type=str, help="Script text string to generate voiceover for")

    args = parser.parse_args()

    # 1. Verify input images
    check_input_images()

    # 2. Resolve Project Name
    project_name = args.project_name
    if not project_name:
        try:
            project_name = input(Fore.YELLOW + "\n📌 Enter CapCut Project Name (default: 'MyShortsProject'): " + Style.RESET_ALL).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    if not project_name:
        project_name = "MyShortsProject"

    # Sanitize project name
    project_name = project_name.strip('\\/ ')

    # 3. Resolve Script Text
    script_text = args.text
    if not script_text:
        script_text = get_multiline_input("\n✍️ Enter / Paste your Video Script Text:")

    if not script_text or not script_text.strip():
        print(Fore.RED + "\nError: Script text cannot be empty! Exiting." + Style.RESET_ALL)
        sys.exit(1)

    print(Fore.MAGENTA + "\n" + "=" * 65 + Style.RESET_ALL)
    print(Fore.GREEN + Style.BRIGHT + f"🚀 LAUNCHING AUTOMATION FOR PROJECT: '{project_name}'" + Style.RESET_ALL)
    print(Fore.MAGENTA + "=" * 65 + Style.RESET_ALL)

    # --- STAGE 1: Google Gemini 3.1 Flash TTS ---
    print(Fore.CYAN + "\n[STAGE 1/3] Generating Expressive Voiceover Audio (Google TTS - Voice: Puck)..." + Style.RESET_ALL)
    # Save script text to input_text/temp_script.txt to prevent shell escaping issues with quotes/brackets
    temp_txt_path = os.path.join(SCRIPT_DIR, "tts_generator", "input_text", "script.txt")
    os.makedirs(os.path.dirname(temp_txt_path), exist_ok=True)
    with open(temp_txt_path, "w", encoding="utf-8") as f:
        f.write(script_text)

    code1 = run_python_script(TTS_SCRIPT, ["-i", temp_txt_path])
    if code1 != 0:
        print(Fore.RED + "\n❌ Stage 1 (TTS Generation) failed! Exiting." + Style.RESET_ALL)
        sys.exit(1)

    # --- STAGE 2: Whisper STT & Gemini 3.6 Flash Mascot Tagging ---
    print(Fore.CYAN + "\n[STAGE 2/3] Extracting Speech Timestamps & Applying Gemini 3.6 Flash Mascot Tags..." + Style.RESET_ALL)
    generated_audio = os.path.join(SCRIPT_DIR, "tts_generator", "output_audio", "voiceover.wav")
    code2 = run_python_script(SRT_SCRIPT, ["-i", generated_audio])
    if code2 != 0:
        print(Fore.RED + "\n❌ Stage 2 (Tagged SRT Generation) failed! Exiting." + Style.RESET_ALL)
        sys.exit(1)

    # --- STAGE 3: CapCut Desktop 6-Track Draft Builder ---
    print(Fore.CYAN + "\n[STAGE 3/3] Building 6-Track Timeline in CapCut Desktop..." + Style.RESET_ALL)
    code3 = run_python_script(BUILD_SCRIPT, [project_name])
    if code3 != 0:
        print(Fore.RED + "\n❌ Stage 3 (CapCut Draft Builder) failed! Exiting." + Style.RESET_ALL)
        sys.exit(1)

    print(Fore.MAGENTA + "\n" + "=" * 65 + Style.RESET_ALL)
    print(Fore.GREEN + Style.BRIGHT + f"✨ SUCCESS! CapCut Desktop Project '{project_name}' is Ready!" + Style.RESET_ALL)
    print(Fore.CYAN + "Open CapCut Desktop to edit your video." + Style.RESET_ALL)
    print(Fore.MAGENTA + "=" * 65 + Style.RESET_ALL + "\n")


if __name__ == "__main__":
    main()

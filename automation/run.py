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
from typing import Optional

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
    """Verifies that comparison images exist in the input/ directory."""
    from build_draft import find_all_comparison_images
    found = find_all_comparison_images(INPUT_DIR)
    num_found = len(found)

    if num_found == 0:
        print(Fore.YELLOW + "\n[NOTICE] No comparison images found in 'input/' (e.g. input/image1.jpg, input/image2.png)" + Style.RESET_ALL)
        return False

    num_pairs = num_found // 2
    if num_pairs > 1:
        print(Fore.GREEN + f"✓ Detected Compilation Short: {num_found} images ({num_pairs} pairs) verified in 'input/'" + Style.RESET_ALL)
    elif num_found >= 2:
        print(Fore.GREEN + f"✓ Single Comparison Short: {num_found} images verified in 'input/'" + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + f"✓ Found {num_found} image in 'input/'. (Add image2 for full side-by-side pair)" + Style.RESET_ALL)

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
def find_existing_input_audio() -> Optional[str]:
    """Finds any pre-existing audio file in input/ folder."""
    if not os.path.isdir(INPUT_DIR):
        return None
    audio_exts = {".wav", ".mp3", ".m4a", ".flac", ".aac"}
    for f in os.listdir(INPUT_DIR):
        if os.path.splitext(f)[1].lower() in audio_exts:
            return os.path.join(INPUT_DIR, f)
    return None


import subprocess

def run_python_script(script_path: str, args: list) -> int:
    """Runs a python sub-script cleanly using subprocess."""
    cmd = [sys.executable, script_path] + args
    res = subprocess.run(cmd)
    return res.returncode


def main():
    print(Fore.MAGENTA + "=" * 65 + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + "   🎬 YOUTUBE SHORTS EDITING AUTOMATION ENGINE   " + Style.RESET_ALL)
    parser = argparse.ArgumentParser(description="Master Interactive CLI for Shorts Video Creation Pipeline")
    parser.add_argument("project_name", nargs="?", help="Project name for CapCut Desktop (e.g. SupermanVsShazam)")
    parser.add_argument("--batch", "-b", action="store_true", help="Run full batch video generation pipeline")
    parser.add_argument("--mode", "-m", choices=["deepdive", "compilation"], help="Select Video Short Mode: 'deepdive' (1 pair / 2 images) or 'compilation' (3 pairs / 6 images)")
    parser.add_argument("--text", "-t", type=str, help="Script text string to generate voiceover for")
    parser.add_argument("--label1", "--label-x", "-x", type=str, help="Label text for Image 1 / Topic X (Left / Red, e.g. MCU)")
    parser.add_argument("--label2", "--label-y", "-y", type=str, help="Label text for Image 2 / Topic Y (Right / Blue, e.g. MARVEL COMICS)")
    for idx in range(3, 13):
        parser.add_argument(f"--label{idx}", type=str, default="", help=f"Label text for Image {idx}")
    parser.add_argument("--labels", type=str, default="", help="Comma/Semicolon separated list of labels for all comparison pairs")
    parser.add_argument("--skip-tts", "--no-tts", action="store_true", help="Skip Google TTS generation and use pre-recorded audio in input/ folder")
    parser.add_argument("--audio", "-a", type=str, help="Path to pre-recorded audio file to use instead of generating TTS")

    args, remaining = parser.parse_known_args()

    if args.batch:
        import run_batch
        sys.argv = [sys.argv[0]] + remaining
        run_batch.main()
        return

    # 0. Select Video Mode (Deepdive vs Compilation)
    mode = args.mode
    if not mode:
        print(Fore.CYAN + "\n🎬 Select Video Short Option:" + Style.RESET_ALL)
        print(Fore.WHITE + "  1. Deepdive    (Single comparison pair: 2 images - image1 & image2)")
        print(Fore.WHITE + "  2. Compilation (3 comparison pairs: 6 images - image1 to image6)")
        try:
            choice = input(Fore.YELLOW + "👉 Enter choice (1 or 2, default: 2): " + Style.RESET_ALL).strip()
            if choice == "1":
                mode = "deepdive"
            else:
                mode = "compilation"
        except (KeyboardInterrupt, EOFError):
            mode = "compilation"

    print(Fore.GREEN + f"\n✓ Selected Mode: {mode.upper()}" + Style.RESET_ALL)

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

    # 3. Resolve Title Labels X & Y (Single Deepdive Pair vs Multi-Pair Compilation)
    from build_draft import find_all_comparison_images
    img_dict = find_all_comparison_images("input")

    if mode == "deepdive":
        num_pairs = 1
    else:
        num_pairs = 3

    build_args = [project_name, "--mode", mode]

    if args.labels:
        build_args.extend(["--labels", args.labels])
    elif mode == "compilation":
        print(Fore.GREEN + f"\n📌 Compilation Short Detected ({num_pairs} Pairs / {num_pairs * 2} Images expected in 'input/')!" + Style.RESET_ALL)
        for k in range(num_pairs):
            idx_x = 2 * k + 1
            idx_y = 2 * k + 2
            img_x_name = os.path.basename(img_dict.get(idx_x, f"Image {idx_x}"))
            img_y_name = os.path.basename(img_dict.get(idx_y, f"Image {idx_y}"))
            lx_flag = getattr(args, f"label{idx_x}", "") or (args.label1 if k == 0 else "")
            ly_flag = getattr(args, f"label{idx_y}", "") or (args.label2 if k == 0 else "")

            if not lx_flag and not ly_flag:
                try:
                    lx_flag = input(Fore.YELLOW + f"  🏷️  Pair {k+1} ({img_x_name}) - Red Title X (Left): " + Style.RESET_ALL).strip()
                    ly_flag = input(Fore.YELLOW + f"  🏷️  Pair {k+1} ({img_y_name}) - Blue Title Y (Right): " + Style.RESET_ALL).strip()
                except (KeyboardInterrupt, EOFError):
                    lx_flag, ly_flag = "", ""
            if lx_flag:
                build_args.extend([f"--label{idx_x}", lx_flag])
            if ly_flag:
                build_args.extend([f"--label{idx_y}", ly_flag])
    else:
        label1 = args.label1
        if label1 is None:
            try:
                label1 = input(Fore.YELLOW + "🏷️  Enter Red Title Label for Image 1 (Left / Topic X, e.g. MCU or SUPERMAN): " + Style.RESET_ALL).strip()
            except (KeyboardInterrupt, EOFError):
                label1 = ""

        label2 = args.label2
        if label2 is None:
            try:
                label2 = input(Fore.YELLOW + "🏷️  Enter Blue Title Label for Image 2 (Right / Topic Y, e.g. MARVEL COMICS or SHAZAM): " + Style.RESET_ALL).strip()
            except (KeyboardInterrupt, EOFError):
                label2 = ""

        if label1:
            build_args.extend(["--label1", label1])
        if label2:
            build_args.extend(["--label2", label2])

    # 4. Resolve Pre-recorded Audio vs. Google TTS
    existing_audio = args.audio or find_existing_input_audio()
    skip_tts = args.skip_tts

    if existing_audio and not skip_tts and not args.text:
        rel_audio_path = os.path.relpath(existing_audio, SCRIPT_DIR)
        print(Fore.GREEN + f"\n🎙️  Detected existing audio in 'input/': '{rel_audio_path}'" + Style.RESET_ALL)
        try:
            choice = input(Fore.YELLOW + "   Use this existing audio file and SKIP Google TTS? (Y/n / press Enter to use): " + Style.RESET_ALL).strip().lower()
            if choice in ["", "y", "yes", "true"]:
                skip_tts = True
        except (KeyboardInterrupt, EOFError):
            skip_tts = True

    script_text = ""
    if not skip_tts:
        script_text = args.text
        if not script_text:
            script_text = get_multiline_input("\n✍️ Enter / Paste your Video Script Text:")

        if not script_text or not script_text.strip():
            print(Fore.RED + "\nError: Script text cannot be empty! Exiting." + Style.RESET_ALL)
            sys.exit(1)

    print(Fore.MAGENTA + "\n" + "=" * 65 + Style.RESET_ALL)
    print(Fore.GREEN + Style.BRIGHT + f"🚀 LAUNCHING AUTOMATION FOR PROJECT: '{project_name}'" + Style.RESET_ALL)
    label1 = getattr(args, "label1", "") or ""
    label2 = getattr(args, "label2", "") or ""
    if label1 or label2:
        print(Fore.CYAN + f"   - Red Title X (Left) : '{label1}'" + Style.RESET_ALL)
        print(Fore.CYAN + f"   - Blue Title Y (Right): '{label2}'" + Style.RESET_ALL)
    elif args.labels:
        print(Fore.CYAN + f"   - Multi-Pair Labels  : '{args.labels}'" + Style.RESET_ALL)
    if skip_tts:
        print(Fore.CYAN + f"   - Audio Mode         : Pre-recorded audio ({os.path.basename(existing_audio or 'voiceover.wav')})" + Style.RESET_ALL)
    else:
        print(Fore.CYAN + f"   - Audio Mode         : Google Gemini TTS (Voice: Puck)" + Style.RESET_ALL)
    print(Fore.MAGENTA + "=" * 65 + Style.RESET_ALL)

    # --- STAGE 1: Google Gemini 3.1 Flash TTS ---
    if not skip_tts:
        print(Fore.CYAN + "\n[STAGE 1/3] Generating Expressive Voiceover Audio (Google TTS - Voice: Puck)..." + Style.RESET_ALL)
        temp_txt_path = os.path.join(SCRIPT_DIR, "tts_generator", "input_text", "script.txt")
        os.makedirs(os.path.dirname(temp_txt_path), exist_ok=True)
        with open(temp_txt_path, "w", encoding="utf-8") as f:
            f.write(script_text)

        code1 = run_python_script(TTS_SCRIPT, ["-i", temp_txt_path])
        if code1 != 0:
            print(Fore.RED + "\n❌ Stage 1 (TTS Generation) failed! Exiting." + Style.RESET_ALL)
            sys.exit(1)
        target_audio = os.path.join(SCRIPT_DIR, "tts_generator", "output_audio", "voiceover.wav")
    else:
        target_audio = existing_audio or os.path.join(INPUT_DIR, "voiceover.wav")
        print(Fore.GREEN + f"\n[STAGE 1/3] Skipping Google TTS (Using pre-recorded audio: '{os.path.basename(target_audio)}')..." + Style.RESET_ALL)

    # --- STAGE 2: Whisper STT & Gemini 3.6 Flash Mascot Tagging ---
    print(Fore.CYAN + "\n[STAGE 2/3] Extracting Speech Timestamps & Applying Gemini 3.6 Flash Mascot Tags..." + Style.RESET_ALL)
    code2 = run_python_script(SRT_SCRIPT, ["-i", target_audio])
    if code2 != 0:
        print(Fore.RED + "\n❌ Stage 2 (Tagged SRT Generation) failed! Exiting." + Style.RESET_ALL)
        sys.exit(1)

    # --- STAGE 3: CapCut Desktop 8-Track Draft Builder ---
    print(Fore.CYAN + "\n[STAGE 3/3] Building Timeline & Titles in CapCut Desktop..." + Style.RESET_ALL)
    code3 = run_python_script(BUILD_SCRIPT, build_args)
    if code3 != 0:
        print(Fore.RED + "\n❌ Stage 3 (CapCut Draft Builder) failed! Exiting." + Style.RESET_ALL)
        sys.exit(1)

    print(Fore.MAGENTA + "\n" + "=" * 65 + Style.RESET_ALL)
    print(Fore.GREEN + Style.BRIGHT + f"✨ SUCCESS! CapCut Desktop Project '{project_name}' is Ready!" + Style.RESET_ALL)
    print(Fore.CYAN + "Open CapCut Desktop to edit your video." + Style.RESET_ALL)
    print(Fore.MAGENTA + "=" * 65 + Style.RESET_ALL + "\n")


if __name__ == "__main__":
    main()

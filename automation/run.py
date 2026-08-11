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
import re
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
    return "\n".join(lines)


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


def generate_auto_script_text(channel: str, mode: str, label1: str = "", label2: str = "", labels_str: str = "", project_name: str = "", build_args: list = None) -> str:
    """Generates a Playbook-compliant script text automatically using Gemini AI LLM or template fallback."""
    from src.env_utils import get_gemini_api_key
    from src.model_config import generate_content_url, get_text_model, model_chain
    from src.script_gen.templates import ScriptTemplates
    from src.script_gen.farqkya_templates import FarqKyaScriptTemplates
    import requests

    api_key = get_gemini_api_key()

    if mode == "compilation":
        pairs = []
        if labels_str:
            parts = [x.strip() for x in labels_str.replace(";", ",").split(",") if x.strip()]
            for idx in range(0, len(parts), 2):
                if idx + 1 < len(parts):
                    pairs.append((parts[idx], parts[idx+1]))
        if not pairs and build_args:
            lx_map = {}
            ly_map = {}
            for i in range(len(build_args) - 1):
                flag = build_args[i]
                val = build_args[i+1]
                if flag.startswith("--label") and flag[7:].isdigit():
                    idx = int(flag[7:])
                    if idx % 2 == 1:
                        lx_map[(idx + 1) // 2] = val
                    else:
                        ly_map[idx // 2] = val
            for k in range(1, 4):
                if k in lx_map or k in ly_map:
                    pairs.append((lx_map.get(k, f"Pair {k} X"), ly_map.get(k, f"Pair {k} Y")))
        if not pairs:
            pairs = [("Entity 1A", "Entity 1B"), ("Entity 2A", "Entity 2B"), ("Entity 3A", "Entity 3B")]

        pairs_summary = ", ".join([f"Pair {i+1}: {p[0]} vs {p[1]}" for i, p in enumerate(pairs)])
        print(Fore.CYAN + f"\n🤖 Auto-Generating Compilation Script via Gemini AI for [{pairs_summary}]..." + Style.RESET_ALL)

        if api_key:
            try:
                if channel == "farqkya":
                    prompt = f"""You are the world-class YouTube Shorts retention engineer and scriptwriter for Islamic comparison channel "Farq Kya" (@farqkya).
Write a viral, high-retention COMPILATION YouTube Shorts script (~70-95 words total) in clear, natural Roman Urdu comparing 3 pairs:
{pairs_summary}

STRICT UNSLOP RULES:
- NEVER start with "Ye hai X aur ye hai Y, aakhir isme farq kya hai?" or "Aksar log samajhte hain ke..."
- Hook line 1 MUST create an immediate curiosity gap or question.
- Outro MUST be: "Aise hi Islamic comparisons ke liye follow karein."

Return ONLY the raw final script text without markdown formatting or code blocks."""
                else:
                    prompt = f"""You are the expert YouTube Shorts scriptwriter for channel "Dont Mix This".
Write a viral, Playbook-compliant COMPILATION YouTube Shorts script (~90-95 words total) comparing 3 pairs:
{pairs_summary}

Strict Structural Rules:
- For each of the 3 pairs, write: "This is [A]. This is [B]. So what's the difference? [A] is [contrast A], while [B] is [contrast B]."
- Outro MUST be: "Follow for more."

Return ONLY the raw final script text without markdown formatting or code blocks."""

                payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7}}
                r = None
                for model in model_chain(get_text_model()):
                    r = requests.post(generate_content_url(model, api_key), json=payload, timeout=20)
                    if r.status_code == 200:
                        break
                    print(Fore.YELLOW + f"⚠️ Gemini model '{model}' returned {r.status_code}; trying next model." + Style.RESET_ALL)
                if r is not None and r.status_code == 200:
                    res_data = r.json()
                    generated_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    generated_text = re.sub(r'^```[\w]*\n?', '', generated_text)
                    generated_text = re.sub(r'\n?```$', '', generated_text).strip()
                    if generated_text:
                        print(Fore.GREEN + f"✓ AI Compilation Script Generated Successfully ({len(generated_text.split())} words):\n" + Style.RESET_ALL)
                        print(Fore.YELLOW + generated_text + Style.RESET_ALL + "\n")
                        return generated_text
            except Exception as e:
                print(Fore.YELLOW + f"⚠️ Gemini API call failed ({e}). Falling back to template." + Style.RESET_ALL)

        pairs_data = [{"entity_a": p[0], "entity_b": p[1], "contrast_a": "operates with distinct power", "contrast_b": "operates with contrasting style"} for p in pairs]
        if channel == "farqkya":
            script_text = FarqKyaScriptTemplates.render_compilation(pairs_data)
        else:
            script_text = ScriptTemplates.render_compilation(pairs_data)
        print(Fore.GREEN + f"✓ Script Rendered via Template ({len(script_text.split())} words):\n" + Style.RESET_ALL)
        print(Fore.YELLOW + script_text + Style.RESET_ALL + "\n")
        return script_text

    # Deepdive Mode
    entity_a = label1.strip() if label1 else "Topic A"
    entity_b = label2.strip() if label2 else "Topic B"
    if (not label1 or not label2) and project_name:
        m = re.split(r'[-_vsVS]+', project_name)
        if len(m) >= 2:
            if not label1: entity_a = m[0].strip()
            if not label2: entity_b = m[1].strip()

    print(Fore.CYAN + f"\n🤖 Auto-Generating Playbook Script via Gemini AI for '{entity_a}' vs '{entity_b}'..." + Style.RESET_ALL)

    if api_key:
        try:
            if channel == "farqkya":
                prompt = f"""You are the expert YouTube Shorts scriptwriter for channel "Farq Kya" (@farqkya).
Write a viral, Playbook-compliant DEEPDIVE YouTube Shorts script (60-85 words total) in Roman Urdu comparing "{entity_a}" vs "{entity_b}".

Strict Structural Rules:
- Line 1 MUST be: "Ye hai {entity_a} aur ye hai {entity_b}, aakhir isme farq kya hai?"
- Line 2 shatters a common misconception ("Aksar log samajhte hain ke... Lekin aisa nahi hai.").
- Explain the key contrast mechanism between {entity_a} and {entity_b}.
- End with a strong punchline.
- Outro MUST be: "Mazeed videos ke liye follow karein."

Return ONLY the raw final script text without markdown formatting or code blocks."""
            else:
                prompt = f"""You are the expert YouTube Shorts scriptwriter for channel "Dont Mix This".
Write a viral, Playbook-compliant DEEPDIVE YouTube Shorts script (75-85 words total) comparing "{entity_a}" vs "{entity_b}".

Strict Structural Rules:
- Line 1 MUST be: "This is {entity_a}. This is {entity_b}. So what's the difference?"
- Line 2 shatters a common misconception ("Most people think... They're not.").
- Explain the key contrast mechanism between {entity_a} and {entity_b} ("That's why {entity_a}..., while {entity_b}...").
- End with a strong punchline.
- Outro MUST be: "Follow for more."

Return ONLY the raw final script text without markdown formatting or code blocks."""

            payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7}}
            r = None
            for model in model_chain(get_text_model()):
                r = requests.post(generate_content_url(model, api_key), json=payload, timeout=20)
                if r.status_code == 200:
                    break
                print(Fore.YELLOW + f"⚠️ Gemini model '{model}' returned {r.status_code}; trying next model." + Style.RESET_ALL)
            if r is not None and r.status_code == 200:
                res_data = r.json()
                generated_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                generated_text = re.sub(r'^```[\w]*\n?', '', generated_text)
                generated_text = re.sub(r'\n?```$', '', generated_text).strip()
                if generated_text:
                    print(Fore.GREEN + f"✓ AI Script Generated Successfully ({len(generated_text.split())} words):\n" + Style.RESET_ALL)
                    print(Fore.YELLOW + generated_text + Style.RESET_ALL + "\n")
                    return generated_text
        except Exception as e:
            print(Fore.YELLOW + f"⚠️ Gemini API call failed ({e}). Falling back to template." + Style.RESET_ALL)

    if channel == "farqkya":
        script_text = FarqKyaScriptTemplates.render_deepdive(
            entity_a=entity_a,
            entity_b=entity_b,
            template_id=1,
            concept_hook=f"Aksar log samajhte hain ke {entity_a} aur {entity_b} ek hi hain, lekin aisa nahi hai.",
            mechanism_a="pehli shariat ko aage badhate hain",
            mechanism_b="nayi kitab aur shariat ke saath aate hain",
            punchline=f"Aakhir mein {entity_a} aur {entity_b} mein yahi bunyadi farq hai."
        )
    else:
        script_text = ScriptTemplates.render_deepdive(
            entity_a=entity_a,
            entity_b=entity_b,
            template_id=1,
            concept_hook=f"Most people think {entity_a} and {entity_b} are identical in power. They're not.",
            mechanism_a="was forged for extreme combat",
            mechanism_b="was built specifically as a tactical defense",
            punchline=f"{entity_a} relies on divine alloy, while {entity_b} relies on Stark engineering."
        )

    print(Fore.GREEN + f"✓ Script Rendered via Template ({len(script_text.split())} words):\n" + Style.RESET_ALL)
    print(Fore.YELLOW + script_text + Style.RESET_ALL + "\n")
    return script_text


def main():
    print(Fore.MAGENTA + "=" * 65 + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + "   🎬 YOUTUBE SHORTS EDITING AUTOMATION ENGINE   " + Style.RESET_ALL)
    parser = argparse.ArgumentParser(description="Master Interactive CLI for Shorts Video Creation Pipeline")
    parser.add_argument("project_name", nargs="?", help="Project name for CapCut Desktop (e.g. SupermanVsShazam)")
    parser.add_argument("--batch", "-b", action="store_true", help="Run full batch video generation pipeline")
    parser.add_argument("--mode", "-m", choices=["deepdive", "compilation"], help="Select Video Short Mode: 'deepdive' (1 pair / 2 images) or 'compilation' (3 pairs / 6 images)")
    parser.add_argument("--text", "-t", type=str, help="Script text string to generate voiceover for")
    parser.add_argument("--auto-script", "--autoscript", action="store_true", help="Auto-generate script text using Gemini AI based on topic/labels")
    parser.add_argument("--label1", "--label-x", "-x", type=str, help="Label text for Image 1 / Topic X (Left / Red, e.g. MCU)")
    parser.add_argument("--label2", "--label-y", "-y", type=str, help="Label text for Image 2 / Topic Y (Right / Blue, e.g. MARVEL COMICS)")
    for idx in range(3, 13):
        parser.add_argument(f"--label{idx}", type=str, default="", help=f"Label text for Image {idx}")
    parser.add_argument("--labels", type=str, default="", help="Comma/Semicolon separated list of labels for all comparison pairs")
    parser.add_argument("--channel", "-c", choices=["dontmixthis", "farqkya"], help="Select YouTube channel ('dontmixthis' or 'farqkya')")
    parser.add_argument("--skip-tts", "--no-tts", action="store_true", help="Skip Google TTS generation and use pre-recorded audio in input/ folder")
    parser.add_argument("--audio", "-a", type=str, help="Path to pre-recorded audio file to use instead of generating TTS")
    parser.add_argument("--proceed", "-p", action="store_true", help="Auto-proceed non-interactively with script generation, TTS, SRT, and CapCut draft building")

    args, remaining = parser.parse_known_args()

    if args.proceed or (args.project_name and (args.label1 or args.label2 or args.labels) and not args.text and not args.audio and not args.skip_tts):
        args.auto_script = True

    if args.batch:
        import run_batch
        sys.argv = [sys.argv[0]] + remaining
        run_batch.main()
        return

    # 0a. Select Target YouTube Channel
    channel = args.channel
    if not channel:
        print(Fore.CYAN + "\n📺 Select YouTube Channel:" + Style.RESET_ALL)
        print(Fore.WHITE + "  1. Dont Mix This (@dontmixthis - English)")
        print(Fore.WHITE + "  2. Farq Kya (@farqkya - Roman Urdu)")
        try:
            ch_choice = input(Fore.YELLOW + "👉 Enter choice (1 or 2, default: 1): " + Style.RESET_ALL).strip()
            if ch_choice == "2":
                channel = "farqkya"
            else:
                channel = "dontmixthis"
        except (KeyboardInterrupt, EOFError):
            channel = "dontmixthis"

    print(Fore.GREEN + f"✓ Selected Channel: {channel.upper()}" + Style.RESET_ALL)

    # 0b. Select Video Mode (Deepdive vs Compilation)
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

    print(Fore.GREEN + f"✓ Selected Mode: {mode.upper()}" + Style.RESET_ALL)

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

    build_args = [project_name, "--mode", mode, "--channel", channel]

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

    # 4. Resolve Pre-recorded Audio vs. Google TTS & Script Text
    existing_audio = args.audio or find_existing_input_audio()
    skip_tts = args.skip_tts

    if existing_audio and not skip_tts and not args.text and not args.auto_script:
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
        if args.auto_script:
            label1_val = getattr(args, "label1", "") or ""
            label2_val = getattr(args, "label2", "") or ""
            script_text = generate_auto_script_text(
                channel=channel,
                mode=mode,
                label1=label1_val,
                label2=label2_val,
                labels_str=args.labels,
                project_name=project_name,
                build_args=build_args
            )
        else:
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

        code1 = run_python_script(TTS_SCRIPT, ["-i", temp_txt_path, "--channel", channel])
        if code1 != 0:
            print(Fore.RED + "\n❌ Stage 1 (TTS Generation) failed! Exiting." + Style.RESET_ALL)
            sys.exit(1)
        target_audio = os.path.join(SCRIPT_DIR, "tts_generator", "output_audio", "voiceover.wav")
    else:
        target_audio = existing_audio or os.path.join(INPUT_DIR, "voiceover.wav")
        print(Fore.GREEN + f"\n[STAGE 1/3] Skipping Google TTS (Using pre-recorded audio: '{os.path.basename(target_audio)}')..." + Style.RESET_ALL)

    # --- STAGE 2: Whisper STT & Gemini 3.6 Flash Mascot Tagging ---
    print(Fore.CYAN + "\n[STAGE 2/3] Extracting Speech Timestamps & Applying Gemini 3.6 Flash Mascot Tags..." + Style.RESET_ALL)
    code2 = run_python_script(SRT_SCRIPT, ["-i", target_audio, "--channel", channel])

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

#!/usr/bin/env python3
r"""
⚡ Batch Video Generator (Overnight Automation Engine)

Batch-generates up to 20 complete, distinct CapCut Desktop project drafts from a single JSON
configuration file (ideas.json) overnight.

Features:
  - Supports 'deepdive' (1 pair, strict <=35s limit) and 'compilation' (3 pairs / 6 images) modes.
  - Per-topic sandbox isolation in batch_workspace/{topic_id}/.
  - State persistence & resume capability via batch_status.json.
  - Pre-flight schema validation and duration guardrails.
  - Exponential backoff retry logic for API resilience.
  - Comprehensive batch execution summary report (batch_report.json).

Usage:
  python run_batch.py                                # Runs overnight batch using ideas.json (or sample_ideas.json)
  python run_batch.py --ideas custom_ideas.json      # Custom ideas config
  python run_batch.py --init                         # Creates default ideas.json from sample template
  python run_batch.py --resume                       # Resumes previous batch execution from state file
  python run_batch.py --validate                     # Runs pre-flight validation check
  python run_batch.py --dry-run                      # Runs structure & setup checks without API calls
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from colorama import Fore, Style, init

init(autoreset=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, "config")

DEFAULT_IDEAS_FILE = os.path.join(CONFIG_DIR, "ideas.json") if os.path.isfile(os.path.join(CONFIG_DIR, "ideas.json")) else os.path.join(SCRIPT_DIR, "ideas.json")
SAMPLE_IDEAS_FILE = os.path.join(CONFIG_DIR, "sample_ideas.json") if os.path.isfile(os.path.join(CONFIG_DIR, "sample_ideas.json")) else os.path.join(SCRIPT_DIR, "sample_ideas.json")
STATUS_FILE = os.path.join(SCRIPT_DIR, "batch_status.json")
REPORT_FILE = os.path.join(SCRIPT_DIR, "batch_report.json")
BATCH_WORKSPACE = os.path.join(SCRIPT_DIR, "batch_workspace")
DEFAULT_INPUT_DIR = os.path.join(SCRIPT_DIR, "input")

TTS_SCRIPT = os.path.join(SCRIPT_DIR, "tts_generator", "generate_tts.py")
SRT_SCRIPT = os.path.join(SCRIPT_DIR, "srt_generator", "audio_to_tagged_srt.py")
BUILD_SCRIPT = os.path.join(SCRIPT_DIR, "build_draft.py")

MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 5.0
MAX_DEEPDIVE_DURATION_SEC = 35.0

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("BatchVideoGenerator")


def load_env_file() -> None:
    """Auto-loads environment variables from root .env file if present."""
    env_path = os.path.join(SCRIPT_DIR, ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and v and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


load_env_file()


def get_audio_duration_seconds(wav_path: str) -> float:
    """Calculates duration of a WAV file in seconds."""
    try:
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return frames / float(rate)
    except Exception as e:
        logger.warning(f"Could not read audio duration for {wav_path}: {e}")
    return 0.0


def validate_ideas_data(ideas: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Validates the structure of ideas list against standard schema rules."""
    errors = []
    if not isinstance(ideas, list) or len(ideas) == 0:
        return False, ["ideas configuration must be a non-empty array of objects."]

    seen_ids = set()
    for idx, item in enumerate(ideas):
        topic_ref = f"Item #{idx+1}"
        if not isinstance(item, dict):
            errors.append(f"{topic_ref} is not a valid JSON object.")
            continue

        topic_id = item.get("id")
        if not topic_id:
            errors.append(f"{topic_ref} is missing required field 'id'.")
        elif topic_id in seen_ids:
            errors.append(f"Duplicate topic ID '{topic_id}' found at {topic_ref}.")
        else:
            seen_ids.add(topic_id)

        if not item.get("project_name"):
            errors.append(f"Topic '{topic_id or topic_ref}' is missing required field 'project_name'.")

        mode = item.get("type")
        if mode not in ["deepdive", "compilation"]:
            errors.append(f"Topic '{topic_id or topic_ref}' has invalid type '{mode}'. Must be 'deepdive' or 'compilation'.")

        script = item.get("script")
        if not script or not script.strip():
            errors.append(f"Topic '{topic_id or topic_ref}' script cannot be empty.")

    return len(errors) == 0, errors


def init_ideas_file(target_path: str = DEFAULT_IDEAS_FILE) -> None:
    """Creates a default ideas.json file from sample_ideas.json if not present."""
    if os.path.exists(target_path):
        print(Fore.YELLOW + f"📌 Configuration file '{target_path}' already exists." + Style.RESET_ALL)
        return

    if os.path.exists(SAMPLE_IDEAS_FILE):
        shutil.copy(SAMPLE_IDEAS_FILE, target_path)
        print(Fore.GREEN + f"✨ Created '{target_path}' with 20 sample topics from sample_ideas.json." + Style.RESET_ALL)
    else:
        print(Fore.RED + f"❌ Source '{SAMPLE_IDEAS_FILE}' not found." + Style.RESET_ALL)


def load_ideas(file_path: str) -> List[Dict[str, Any]]:
    """Loads ideas JSON file."""
    if not os.path.exists(file_path):
        if file_path == DEFAULT_IDEAS_FILE and os.path.exists(SAMPLE_IDEAS_FILE):
            print(Fore.YELLOW + f"📌 '{DEFAULT_IDEAS_FILE}' not found. Falling back to '{SAMPLE_IDEAS_FILE}'." + Style.RESET_ALL)
            file_path = SAMPLE_IDEAS_FILE
        else:
            raise FileNotFoundError(f"Ideas file '{file_path}' not found.")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    valid, errs = validate_ideas_data(data)
    if not valid:
        raise ValueError(f"Invalid ideas configuration in '{file_path}':\n - " + "\n - ".join(errs))

    return data


def load_status() -> Dict[str, Any]:
    """Loads batch execution state from batch_status.json."""
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"start_time": datetime.now().isoformat(), "topics": {}}


def save_status(status: Dict[str, Any]) -> None:
    """Saves batch execution state to batch_status.json."""
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not update status file: {e}")


def prepare_topic_sandbox(topic: Dict[str, Any]) -> str:
    """
    Sets up an isolated working directory for a topic under batch_workspace/{topic_id}/.
    Ensures input image assets exist in the sandbox.
    """
    topic_id = topic["id"]
    sandbox_dir = os.path.join(BATCH_WORKSPACE, topic_id)
    sandbox_input = os.path.join(sandbox_dir, "input")
    os.makedirs(sandbox_input, exist_ok=True)

    # Resolve custom asset directory if specified, else look in batch_input/{topic_id}
    custom_assets = topic.get("assets_dir")
    batch_input_dir = os.path.join(SCRIPT_DIR, "batch_input")
    src_asset_dir = custom_assets if (custom_assets and os.path.isdir(custom_assets)) else os.path.join(batch_input_dir, topic_id)

    needed_images = 2 if topic["type"] == "deepdive" else 6

    for i in range(1, needed_images + 1):
        img_name = f"image{i}.png"
        target_img_path = os.path.join(sandbox_input, img_name)

        # Check if user provided asset in src_asset_dir
        src_img = None
        if os.path.isdir(src_asset_dir):
            for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                candidate = os.path.join(src_asset_dir, f"image{i}{ext}")
                if os.path.isfile(candidate):
                    src_img = candidate
                    break

        # Fallback to root input directory if not found
        if not src_img:
            for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                candidate = os.path.join(DEFAULT_INPUT_DIR, f"image{i}{ext}")
                if os.path.isfile(candidate):
                    src_img = candidate
                    break

        if src_img and os.path.isfile(src_img):
            shutil.copy(src_img, target_img_path)
        else:
            # If fallback image 1 exists, use image1 for missing images to ensure project builds cleanly
            root_img1 = os.path.join(DEFAULT_INPUT_DIR, "image1.png")
            if os.path.isfile(root_img1):
                shutil.copy(root_img1, target_img_path)

    # If user provided audio file
    if topic.get("audio_file") and os.path.isfile(topic["audio_file"]):
        shutil.copy(topic["audio_file"], os.path.join(sandbox_input, "voiceover.wav"))

    return sandbox_dir


def run_script_with_retries(script_path: str, args: List[str], cwd: Optional[str] = None) -> bool:
    """Executes a Python script with exponential backoff retry logic."""
    cmd = [sys.executable, script_path] + args
    backoff = INITIAL_BACKOFF_SEC

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"Executing: {' '.join(cmd)} (Attempt {attempt}/{MAX_RETRIES})")
        res = subprocess.run(cmd, cwd=cwd)
        if res.returncode == 0:
            return True

        if attempt < MAX_RETRIES:
            logger.warning(f"Execution failed with code {res.returncode}. Retrying in {backoff:.1f}s...")
            time.sleep(backoff)
            backoff *= 3.0

    return False


def format_labels_arg(topic: Dict[str, Any]) -> List[str]:
    """Formats topic labels into CLI arguments for build_draft.py."""
    labels = topic.get("labels")
    if not labels:
        return []

    mode = topic["type"]
    if mode == "deepdive" and isinstance(labels, dict):
        lx = labels.get("label1", "")
        ly = labels.get("label2", "")
        args = []
        if lx:
            args.extend(["--label1", lx])
        if ly:
            args.extend(["--label2", ly])
        return args

    if isinstance(labels, dict):
        pair_strs = []
        for k in sorted(labels.keys()):
            val = labels[k]
            if isinstance(val, list) and len(val) >= 2:
                pair_strs.append(f"{val[0]},{val[1]}")
            elif isinstance(val, str):
                pair_strs.append(val)
        if pair_strs:
            return ["--labels", ";".join(pair_strs)]

    if isinstance(labels, list):
        return ["--labels", ",".join(labels)]

    return []


def process_single_topic(topic: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """Processes a single topic video draft generation."""
    topic_id = topic["id"]
    project_name = topic["project_name"]
    mode = topic["type"]
    script_text = topic["script"]

    print(Fore.MAGENTA + "\n" + "=" * 70 + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + f"🎬 BATCH PROCESSING [{topic_id}] '{project_name}' (Mode: {mode.upper()})" + Style.RESET_ALL)
    print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)

    sandbox_dir = prepare_topic_sandbox(topic)
    sandbox_input = os.path.join(sandbox_dir, "input")

    result = {
        "id": topic_id,
        "project_name": project_name,
        "type": mode,
        "status": "FAILED",
        "duration_sec": 0.0,
        "draft_path": "",
        "error": None,
        "timestamp": datetime.now().isoformat()
    }

    if dry_run:
        print(Fore.YELLOW + f"[DRY-RUN] Verified sandbox layout and arguments for '{project_name}'." + Style.RESET_ALL)
        result["status"] = "SUCCESS (DRY-RUN)"
        return result

    # Save script text for TTS engine
    temp_txt_path = os.path.join(SCRIPT_DIR, "tts_generator", "input_text", "script.txt")
    os.makedirs(os.path.dirname(temp_txt_path), exist_ok=True)
    with open(temp_txt_path, "w", encoding="utf-8") as f:
        f.write(script_text)

    # Step 1: TTS Audio Generation (or use pre-recorded audio)
    has_custom_audio = topic.get("audio_file") and os.path.isfile(topic["audio_file"])
    if not has_custom_audio:
        print(Fore.CYAN + f"\n[STAGE 1/3] Generating TTS Voiceover for '{project_name}'..." + Style.RESET_ALL)
        ok1 = run_script_with_retries(TTS_SCRIPT, ["-i", temp_txt_path])
        if not ok1:
            result["error"] = "Stage 1 (TTS Generation) failed after retries."
            return result
        generated_audio = os.path.join(SCRIPT_DIR, "tts_generator", "output_audio", "voiceover.wav")
        shutil.copy(generated_audio, os.path.join(sandbox_input, "voiceover.wav"))

    target_audio = os.path.join(sandbox_input, "voiceover.wav")

    # Deepdive Mode Duration Ceiling Check
    audio_dur = get_audio_duration_seconds(target_audio)
    result["duration_sec"] = round(audio_dur, 2)
    print(Fore.GREEN + f"✓ Voiceover Audio Duration: {audio_dur:.2f}s" + Style.RESET_ALL)

    if mode == "deepdive" and audio_dur > MAX_DEEPDIVE_DURATION_SEC:
        print(Fore.YELLOW + f"⚠️  [GUARDRAIL ALERT] Deepdive audio duration ({audio_dur:.2f}s) exceeds max ceiling of {MAX_DEEPDIVE_DURATION_SEC}s!" + Style.RESET_ALL)
        print(Fore.YELLOW + f"    The script will build cleanly, but consider tightening the script text for optimal retention." + Style.RESET_ALL)

    # Copy sandbox images into root input/ for STT & build_draft pipeline
    for i in range(1, 7):
        sandbox_img = os.path.join(sandbox_input, f"image{i}.png")
        root_img = os.path.join(DEFAULT_INPUT_DIR, f"image{i}.png")
        if os.path.isfile(sandbox_img):
            shutil.copy(sandbox_img, root_img)

    shutil.copy(target_audio, os.path.join(DEFAULT_INPUT_DIR, "voiceover.wav"))

    # Step 2: Speech Timestamps & Gemini Mascot Tagging
    print(Fore.CYAN + f"\n[STAGE 2/3] Extracting Subtitles & Gemini 3.6 Mascot Tagging..." + Style.RESET_ALL)
    ok2 = run_script_with_retries(SRT_SCRIPT, ["-i", target_audio])
    if not ok2:
        result["error"] = "Stage 2 (SRT Tagging) failed after retries."
        return result

    # Step 3: CapCut Desktop 8-Track Draft Builder
    print(Fore.CYAN + f"\n[STAGE 3/3] Building CapCut Desktop Draft '{project_name}'..." + Style.RESET_ALL)
    build_args = [project_name, "--mode", mode] + format_labels_arg(topic)
    ok3 = run_script_with_retries(BUILD_SCRIPT, build_args)
    if not ok3:
        result["error"] = "Stage 3 (CapCut Draft Builder) failed."
        return result

    from build_draft import get_default_capcut_drafts_dir
    drafts_root = get_default_capcut_drafts_dir()
    expected_draft_path = os.path.join(drafts_root, project_name)

    result["status"] = "SUCCESS"
    result["draft_path"] = expected_draft_path
    print(Fore.GREEN + Style.BRIGHT + f"✨ [SUCCESS] CapCut Project Draft Ready: '{expected_draft_path}'" + Style.RESET_ALL)

    return result


def generate_and_save_ideas(count: int = 5, target_file: str = DEFAULT_IDEAS_FILE) -> List[Dict[str, Any]]:
    """Generates fresh Playbook-compliant scripts using ScriptGenerator and updates ideas.json."""
    from src.script_gen.generator import ScriptGenerator
    print(Fore.CYAN + f"⚡ Generating {count} fresh Playbook-compliant scripts..." + Style.RESET_ALL)

    generator = ScriptGenerator()
    new_topics = generator.generate_scripts(count=count, mode="auto")

    formatted_ideas = []
    for t in new_topics:
        # Sanitize project name
        clean_name = re.sub(r"[^\w\s]", "", t["title"]).strip().replace(" ", "_")
        proj_name = f"Auto_{t['type'].capitalize()}_{clean_name[:30]}"
        formatted_ideas.append({
            "id": t["id"],
            "project_name": proj_name,
            "type": t["type"],
            "script": t["script"],
            "labels": t.get("labels", {})
        })

    os.makedirs(os.path.dirname(os.path.abspath(target_file)), exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(formatted_ideas, f, indent=2, ensure_ascii=False)

    print(Fore.GREEN + f"✨ Generated {len(formatted_ideas)} fresh Playbook-compliant script topics into '{target_file}'." + Style.RESET_ALL)
    return formatted_ideas


def interactive_batch_review(ideas: List[Dict[str, Any]], target_file: str) -> List[Dict[str, Any]]:
    """
    Displays a clean interactive CLI for reviewing and validating generated ideas
    before starting batch execution.
    Shows X vs Y, Topic Title, and Format (Deep Dive vs Compilation).
    """
    selected_ideas = list(ideas)

    while True:
        print(Fore.MAGENTA + "\n" + "=" * 70 + Style.RESET_ALL)
        print(Fore.CYAN + Style.BRIGHT + f"📋 BATCH REVIEW & VALIDATION ({len(selected_ideas)} Topics Selected)" + Style.RESET_ALL)
        print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)

        if not selected_ideas:
            print(Fore.YELLOW + "  (No topics currently selected for this batch)" + Style.RESET_ALL)

        for idx, item in enumerate(selected_ideas, 1):
            mode = item.get("type", "deepdive").upper()
            proj_name = item.get("project_name", item.get("id"))
            script_text = item.get("script", "")

            # Format X vs Y representation
            labels = item.get("labels", {})
            pairs_str = ""
            if mode == "DEEPDIVE":
                l1 = labels.get("label1", "Topic X")
                l2 = labels.get("label2", "Topic Y")
                pairs_str = f"{l1} vs {l2}"
            else:
                pairs = []
                if isinstance(labels, dict):
                    for k in sorted(labels.keys()):
                        v = labels[k]
                        if isinstance(v, list) and len(v) >= 2:
                            pairs.append(f"{v[0]} vs {v[1]}")
                        elif isinstance(v, str):
                            pairs.append(v)
                pairs_str = " | ".join(pairs) if pairs else "Multi-Pair Compilation"

            mode_color = Fore.GREEN if mode == "DEEPDIVE" else Fore.CYAN
            print(f"[{idx:02d}] FORMAT: {mode_color}{mode:<11}{Style.RESET_ALL} | X vs Y: {Fore.YELLOW}{pairs_str}{Style.RESET_ALL}")
            print(f"     TOPIC : {proj_name}")
            script_snippet = (script_text[:85] + "...") if len(script_text) > 85 else script_text
            print(f"     SCRIPT: \"{script_snippet}\"\n")

        print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)
        print(Fore.GREEN + "  [A / ALL] Approve All & Start Batch Execution" + Style.RESET_ALL)
        print(Fore.CYAN + "  [1, 3, 5] Select Specific Numbers to Build Drafts For" + Style.RESET_ALL)
        print(Fore.CYAN + "  [G] Generate 10 Fresh 50/50 Scripts (5 Deepdives + 5 Compilations)" + Style.RESET_ALL)
        print(Fore.RED + "  [Q] Quit" + Style.RESET_ALL)
        print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)

        try:
            user_input = input(Fore.YELLOW + "👉 Select scripts to generate drafts for (e.g. '1, 3, 5' or 'ALL' / 'A'): " + Style.RESET_ALL).strip().upper()
        except (KeyboardInterrupt, EOFError):
            print("\nBatch execution cancelled.")
            sys.exit(0)

        if not user_input or user_input in ["A", "ALL"]:
            print(Fore.GREEN + f"\n✓ Approved ALL {len(selected_ideas)} topics for draft generation!" + Style.RESET_ALL)
            return selected_ideas

        if user_input == "G":
            try:
                n_str = input(Fore.YELLOW + "👉 How many fresh 50/50 scripts to generate? (default: 10): " + Style.RESET_ALL).strip()
                n = int(n_str) if n_str else 10
            except (ValueError, KeyboardInterrupt, EOFError):
                n = 10
            generate_and_save_ideas(count=n, target_file=target_file)
            selected_ideas = load_ideas(target_file)
            continue

        if user_input == "Q":
            print(Fore.YELLOW + "Exiting batch execution." + Style.RESET_ALL)
            sys.exit(0)

        # Parse numeric selections like "1, 3, 5" or "1 3 5"
        raw_nums = re.findall(r"\d+", user_input)
        if raw_nums:
            picked_indices = set()
            for n_s in raw_nums:
                idx = int(n_s) - 1
                if 0 <= idx < len(selected_ideas):
                    picked_indices.add(idx)
            
            if picked_indices:
                chosen_ideas = [selected_ideas[i] for i in sorted(picked_indices)]
                print(Fore.GREEN + f"\n✓ Selected {len(chosen_ideas)} specific topics for draft generation:" + Style.RESET_ALL)
                for c_item in chosen_ideas:
                    print(Fore.CYAN + f"  • [{c_item.get('id')}] {c_item.get('project_name')}" + Style.RESET_ALL)
                return chosen_ideas
            else:
                print(Fore.RED + f"❌ Invalid numbers specified. Please enter numbers between 1 and {len(selected_ideas)}." + Style.RESET_ALL)
        else:
            print(Fore.RED + "❌ Unrecognized choice. Please enter numbers (e.g. '1, 3, 5'), 'ALL', 'G', or 'Q'." + Style.RESET_ALL)


def main():
    parser = argparse.ArgumentParser(description="Batch Video Generator (Overnight Automation Engine)")
    parser.add_argument("--ideas", "-i", type=str, default=DEFAULT_IDEAS_FILE, help="Path to ideas.json file")
    parser.add_argument("--generate", "-g", type=int, default=0, help="Generate N fresh Playbook-compliant scripts before batch run")
    parser.add_argument("--init", action="store_true", help="Initialize a sample ideas.json file")
    parser.add_argument("--resume", "-r", action="store_true", help="Resume batch run from batch_status.json")
    parser.add_argument("--validate", action="store_true", help="Validate ideas.json schema and exit")
    parser.add_argument("--dry-run", action="store_true", help="Run structure & setup checks without external API calls")
    parser.add_argument("--non-interactive", "--no-prompt", action="store_true", help="Skip interactive CLI review menu and run batch directly")
    args = parser.parse_args()

    if args.init:
        init_ideas_file(args.ideas)
        sys.exit(0)

    print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + "   ⚡ BATCH VIDEO GENERATOR — OVERNIGHT AUTOMATION ENGINE   " + Style.RESET_ALL)
    print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)

    # Automatically generate fresh 50/50 scripts if requested or if ideas file is empty/missing
    if args.generate > 0:
        ideas = generate_and_save_ideas(count=args.generate, target_file=args.ideas)
    elif not os.path.exists(args.ideas) or os.path.getsize(args.ideas) <= 5:
        print(Fore.CYAN + f"📌 Ideas file '{args.ideas}' is empty. Generating 10 fresh Playbook scripts (5 Deepdives + 5 Compilations)..." + Style.RESET_ALL)
        ideas = generate_and_save_ideas(count=10, target_file=args.ideas)
    else:
        try:
            ideas = load_ideas(args.ideas)
            if not ideas:
                print(Fore.CYAN + f"📌 No ideas found in '{args.ideas}'. Generating 10 fresh Playbook scripts (5 Deepdives + 5 Compilations)..." + Style.RESET_ALL)
                ideas = generate_and_save_ideas(count=10, target_file=args.ideas)
        except Exception as e:
            print(Fore.RED + f"❌ Configuration Error loading '{args.ideas}': {e}. Regenerating fresh scripts..." + Style.RESET_ALL)
            ideas = generate_and_save_ideas(count=10, target_file=args.ideas)

    if args.validate:
        print(Fore.GREEN + f"✓ Pre-flight validation passed for '{args.ideas}'. Found {len(ideas)} valid topics." + Style.RESET_ALL)
        sys.exit(0)

    # Launch Interactive CLI Review unless --non-interactive or --dry-run is passed
    if not args.non_interactive and not args.dry_run:
        ideas = interactive_batch_review(ideas, args.ideas)

    status_data = load_status() if args.resume else {"start_time": datetime.now().isoformat(), "topics": {}}
    completed_ids = set(status_data.get("topics", {}).keys()) if args.resume else set()

    total_topics = len(ideas)
    print(Fore.GREEN + f"📌 Loaded {total_topics} video topics for batch processing." + Style.RESET_ALL)
    if completed_ids:
        print(Fore.YELLOW + f"🔄 Resuming batch execution. {len(completed_ids)} topics already processed." + Style.RESET_ALL)

    report_topics = []

    for idx, topic in enumerate(ideas, 1):
        topic_id = topic["id"]
        if topic_id in completed_ids and status_data["topics"][topic_id].get("status") == "SUCCESS":
            print(Fore.YELLOW + f"\n[SKIP {idx}/{total_topics}] Topic '{topic_id}' already completed successfully." + Style.RESET_ALL)
            report_topics.append(status_data["topics"][topic_id])
            continue

        res = process_single_topic(topic, dry_run=args.dry_run)
        status_data["topics"][topic_id] = res
        save_status(status_data)
        report_topics.append(res)

        # Rate-limiting inter-topic delay to respect Google AI Studio quotas (15 RPM)
        if idx < total_topics and not args.dry_run:
            print(Fore.CYAN + "⏳ Pausing 4.0s for API rate-limit compliance..." + Style.RESET_ALL)
            time.sleep(4.0)

    # Build Final Summary Report
    successful = [t for t in report_topics if t.get("status", "").startswith("SUCCESS")]
    failed = [t for t in report_topics if t.get("status") == "FAILED"]

    report_data = {
        "completed_at": datetime.now().isoformat(),
        "total_topics": total_topics,
        "successful_count": len(successful),
        "failed_count": len(failed),
        "topics": report_topics
    }

    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save report file: {e}")

    print(Fore.MAGENTA + "\n" + "=" * 70 + Style.RESET_ALL)
    print(Fore.GREEN + Style.BRIGHT + f"✨ OVERNIGHT BATCH GENERATION COMPLETE!" + Style.RESET_ALL)
    print(Fore.CYAN + f"   - Total Topics Processed: {total_topics}" + Style.RESET_ALL)
    print(Fore.GREEN + f"   - Successful Drafts     : {len(successful)}" + Style.RESET_ALL)
    if failed:
        print(Fore.RED + f"   - Failed Projects       : {len(failed)}" + Style.RESET_ALL)
    print(Fore.CYAN + f"   - Detailed Report Saved : {REPORT_FILE}" + Style.RESET_ALL)
    print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL + "\n")


if __name__ == "__main__":
    main()

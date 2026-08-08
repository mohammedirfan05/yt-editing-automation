#!/usr/bin/env python3
r"""
CapCut Desktop Project Generator from Tagged SRT

Programmatically generates CapCut Desktop video editing projects from a tagged SRT subtitle file,
tag-to-image mapping file, mascot PNG library, audio file (WAV/MP3), primary background image,
and 2 comparison images (auto cropped 1:1).

Usage:
    python build_draft.py                                # Auto-detects input/*.srt, input/*.wav, input/image1.png, input/image2.png
    python build_draft.py capvsironman                   # Specify CapCut draft project name
"""

import argparse
import glob
import json
import logging
import os
import platform
import re
import sys
import uuid
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pycapcut as pcc
import pymediainfo
from PIL import Image
from pycapcut.metadata.effect_meta import EffectMeta
from pycapcut.metadata.video_scene_effect import VideoSceneEffectType

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("CapCutDraftBuilder")


# Known CapCut Cloud & Cache Resource IDs for Fonts
KNOWN_CAPCUT_FONTS = {
    "LuckiestGuy-Rg": "7564679598558973200"
}


@dataclass
class SubtitleBlock:
    index: int
    start_tc: str
    end_tc: str
    start_us: int
    end_us: int
    duration_us: int
    raw_text: str
    clean_text: str
    tags: List[str] = field(default_factory=list)
    resolved_images: List[str] = field(default_factory=list)


@dataclass
class ImageSegmentSpec:
    img_path: str
    tag_code: str
    start_tc: str
    end_tc: str
    start_us: int
    end_us: int
    duration_us: int
    source_blocks: List[int] = field(default_factory=list)


@dataclass
class PairComparisonSpec:
    pair_index: int
    image1_path: Optional[str]
    image2_path: Optional[str]
    label_x: str
    label_y: str
    start_us: int
    right_start_us: int
    end_us: int


def find_all_comparison_images(input_dir: str = "input") -> Dict[int, str]:
    """
    Finds all comparison images (image1, image2, image3, image4, image5, image6...) in input/.
    Returns a dict mapping integer index -> file path.
    """
    if not os.path.isdir(input_dir):
        return {}
    valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    found = {}
    for f in os.listdir(input_dir):
        name_lower = os.path.splitext(f)[0].lower()
        ext_lower = os.path.splitext(f)[1].lower()
        if ext_lower in valid_exts:
            m = re.search(r'^(?:image|img|_)?(\d+)$', name_lower)
            if m:
                idx = int(m.group(1))
                found[idx] = os.path.abspath(os.path.join(input_dir, f))
    return found


def build_compilation_pair_specs(
    subtitle_blocks: List[SubtitleBlock],
    image_dict: Dict[int, str],
    labels_x: List[str],
    labels_y: List[str],
    total_duration_us: int,
    mode: str = "auto"
) -> List[PairComparisonSpec]:
    """
    Slices subtitle blocks into comparison units (pairs) and pairs them with corresponding
    image1/image2, image3/image4, image5/image6... and red/blue labels.
    """
    if not subtitle_blocks:
        return []

    if mode == "deepdive":
        # Deepdive mode: exactly 1 pair spanning full video duration
        pair_start_us = subtitle_blocks[0].start_us if subtitle_blocks else 0
        pair_right_start_us = pair_start_us
        for b in subtitle_blocks:
            if "right" in b.tags:
                pair_right_start_us = b.start_us
                break
        if pair_right_start_us == pair_start_us and len(subtitle_blocks) >= 2:
            pair_right_start_us = subtitle_blocks[1].start_us

        img1_path = image_dict.get(1)
        img2_path = image_dict.get(2)

        lbl_x = labels_x[0] if labels_x else ""
        lbl_y = labels_y[0] if labels_y else ""

        return [
            PairComparisonSpec(
                pair_index=1,
                image1_path=img1_path,
                image2_path=img2_path,
                label_x=lbl_x,
                label_y=lbl_y,
                start_us=pair_start_us,
                right_start_us=pair_right_start_us,
                end_us=total_duration_us
            )
        ]

    pair_block_indices = []
    in_explainer = False
    intro_triggers = ["this is", "here is", "meet ", "option ", "topic ", "versus", "vs "]

    for idx, b in enumerate(subtitle_blocks):
        text_lower = b.clean_text.lower().strip()
        has_intro_phrase = any(trig in text_lower for trig in intro_triggers)
        has_wtd = "wtd" in b.tags or any(kw in text_lower for kw in ["difference", "wtd"])

        if idx == 0:
            pair_block_indices.append(idx)
        elif in_explainer and has_intro_phrase:
            pair_block_indices.append(idx)
            in_explainer = False

        if has_wtd:
            in_explainer = True

    pair_specs: List[PairComparisonSpec] = []
    num_pairs = len(pair_block_indices)

    # Fallback if no explicit intro triggers detected but multiple comparison images exist
    num_images_pairs = len(image_dict) // 2
    if mode == "compilation":
        num_pairs = max(3, num_images_pairs)
    elif num_images_pairs > num_pairs and num_images_pairs > 1:
        num_pairs = num_images_pairs

    if num_pairs > len(pair_block_indices):
        chunk_size = max(1, len(subtitle_blocks) // num_pairs)
        pair_block_indices = [i * chunk_size for i in range(num_pairs)]

    for k in range(num_pairs):
        start_blk_idx = pair_block_indices[k] if k < len(pair_block_indices) else len(subtitle_blocks) - 1
        next_blk_idx = pair_block_indices[k + 1] if (k + 1 < len(pair_block_indices)) else len(subtitle_blocks)

        pair_blocks = subtitle_blocks[start_blk_idx:next_blk_idx]
        if not pair_blocks:
            continue
        pair_start_us = pair_blocks[0].start_us

        if k + 1 < len(pair_block_indices):
            pair_end_us = subtitle_blocks[pair_block_indices[k + 1]].start_us
        else:
            pair_end_us = total_duration_us

        pair_right_start_us = pair_start_us
        for b in pair_blocks:
            if "right" in b.tags:
                pair_right_start_us = b.start_us
                break
        if pair_right_start_us == pair_start_us and len(pair_blocks) >= 2:
            pair_right_start_us = pair_blocks[1].start_us

        img1_path = image_dict.get(2 * k + 1)
        img2_path = image_dict.get(2 * k + 2)

        lbl_x = labels_x[k] if k < len(labels_x) else ""
        lbl_y = labels_y[k] if k < len(labels_y) else ""

        spec = PairComparisonSpec(
            pair_index=k + 1,
            image1_path=img1_path,
            image2_path=img2_path,
            label_x=lbl_x,
            label_y=lbl_y,
            start_us=pair_start_us,
            right_start_us=pair_right_start_us,
            end_us=pair_end_us
        )
        pair_specs.append(spec)

    return pair_specs


class CustomFontWrapper:
    """Wrapper class so pycapcut's TextSegment accepts custom font metadata."""
    def __init__(self, font_name: str, resource_id: str = "7564679598558973200"):
        self.value = EffectMeta(font_name, True, resource_id, resource_id, "", [])


def get_default_capcut_drafts_dir() -> str:
    """
    Returns default local CapCut Desktop drafts directory for Windows or macOS.
    """
    system = platform.system()
    if system == "Windows":
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            return os.path.join(local_appdata, "CapCut", "User Data", "Projects", "com.lveditor.draft")
        return r"C:\Users\%USERNAME%\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft"
    elif system == "Darwin":  # macOS
        home = os.path.expanduser("~")
        return os.path.join(
            home, "Library", "Containers", "com.lemon.capcut", "Data",
            "Library", "Application Support", "CapCut", "User Data", "Projects", "com.lveditor.draft"
        )
    return ""


def find_input_srt(input_dir: str = "input") -> Optional[str]:
    """
    Auto-detects .srt file in the input directory.
    """
    if not os.path.isdir(input_dir):
        return None

    # Priority 1: input/script.srt if present
    preferred = os.path.join(input_dir, "script.srt")
    if os.path.isfile(preferred):
        return preferred

    # Priority 2: First .srt file in input_dir
    srt_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(".srt")]
    if srt_files:
        return srt_files[0]

    return None


def find_input_audio(input_dir: str = "input") -> Optional[str]:
    """
    Auto-detects audio file (.wav, .mp3, .m4a, .flac, .aac) in the input directory.
    """
    if not os.path.isdir(input_dir):
        return None

    audio_exts = {".wav", ".mp3", ".m4a", ".flac", ".aac"}

    # Priority 1: input/script.wav or input/script.mp3 if present
    for ext in [".wav", ".mp3", ".m4a"]:
        pref = os.path.join(input_dir, f"script{ext}")
        if os.path.isfile(pref):
            return pref

    # Priority 2: First matching audio file in input_dir
    for f in os.listdir(input_dir):
        ext = os.path.splitext(f)[1].lower()
        if ext in audio_exts:
            return os.path.join(input_dir, f)

    return None


def find_input_image_by_prefix(prefix_list: List[str], input_dir: str = "input") -> Optional[str]:
    """
    Auto-detects image file in input directory matching given prefixes (e.g. ['image1', 'img1', '1']).
    """
    if not os.path.isdir(input_dir):
        return None

    img_exts = {".png", ".jpg", ".jpeg", ".webp"}

    for prefix in prefix_list:
        for ext in img_exts:
            candidate = os.path.join(input_dir, f"{prefix}{ext}")
            if os.path.isfile(candidate):
                return candidate

    # Fallback: scan all files in input_dir starting with prefix
    for f in sorted(os.listdir(input_dir)):
        stem = Path(f).stem.lower()
        ext = Path(f).suffix.lower()
        if ext in img_exts:
            for prefix in prefix_list:
                if stem == prefix.lower():
                    return os.path.join(input_dir, f)

    return None


def ensure_1to1_crop(img_path: str, cache_dir: str = "assets/processed") -> str:
    """
    Performs auto 1:1 square center-crop on an image file regardless of input dimensions.
    Returns path to cropped 1:1 image.
    """
    if not os.path.isfile(img_path):
        return img_path

    try:
        with Image.open(img_path) as img:
            w, h = img.size
            if w == h:
                return os.path.abspath(img_path)  # Already 1:1 square

            min_dim = min(w, h)
            left = (w - min_dim) // 2
            top = (h - min_dim) // 2
            right = left + min_dim
            bottom = top + min_dim
            cropped = img.crop((left, top, right, bottom))

            os.makedirs(cache_dir, exist_ok=True)
            base_name = os.path.basename(img_path)
            cropped_filename = f"crop_1to1_{base_name}"
            out_path = os.path.abspath(os.path.join(cache_dir, cropped_filename))
            cropped.save(out_path)
            logger.info(f"Auto 1:1 Cropped '{base_name}' ({w}x{h}) -> {out_path} ({min_dim}x{min_dim})")
            return out_path
    except Exception as e:
        logger.warning(f"Could not perform 1:1 auto center crop on '{img_path}': {e}")
        return os.path.abspath(img_path)


def resolve_capcut_font_info(font_name: str = "LuckiestGuy-Rg") -> Tuple[str, str]:
    """
    Resolves CapCut's internal resource ID and local cached .ttf path for a font.
    """
    resource_id = KNOWN_CAPCUT_FONTS.get(font_name, "7564679598558973200")
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    cache_dir = os.path.join(local_appdata, "CapCut", "User Data", "Cache", "effect", resource_id)

    font_path = ""
    if os.path.isdir(cache_dir):
        ttf_files = glob.glob(os.path.join(cache_dir, "**", "*.ttf"), recursive=True)
        if ttf_files:
            font_path = ttf_files[0].replace('\\', '/')

    if not font_path:
        font_path = f"C:/{font_name}.ttf"

    return resource_id, font_path


def fix_font_metadata_in_draft(project_path: str, font_name: str = "LuckiestGuy-Rg", label1_text: str = "", label2_text: str = "", all_labels: Optional[List[str]] = None) -> None:
    """
    Patches generated draft_content.json text materials to populate CapCut font fields
    (font_resource_id, font_path, font_title, font_name, fonts array) so CapCut Desktop renders LuckiestGuy-Rg natively.
    """
    draft_json_path = os.path.join(project_path, "draft_content.json")
    if not os.path.isfile(draft_json_path):
        return

    res_id, font_path = resolve_capcut_font_info(font_name)

    title_labels = [l.strip().upper() for l in (all_labels or []) if l and l.strip()]
    if label1_text and label1_text.strip().upper() not in title_labels:
        title_labels.append(label1_text.strip().upper())
    if label2_text and label2_text.strip().upper() not in title_labels:
        title_labels.append(label2_text.strip().upper())

    try:
        with open(draft_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        texts = data.get('materials', {}).get('texts', [])
        if not texts:
            return

        for text_item in texts:
            text_item['font_resource_id'] = res_id
            text_item['font_id'] = res_id
            text_item['font_path'] = font_path
            text_item['font_title'] = font_name
            text_item['font_name'] = font_name
            text_item['fonts'] = [
                {
                    'id': uuid.uuid4().hex.upper(),
                    'resource_id': res_id,
                    'third_resource_id': '',
                    'category_id': 'preset',
                    'category_name': 'Presets',
                    'source_platform': 1,
                    'path': font_path,
                    'effect_id': res_id,
                    'title': font_name,
                    'team_id': '',
                    'file_uri': '',
                    'request_id': ''
                }
            ]

            # Update inline JSON content styles
            if 'content' in text_item and isinstance(text_item['content'], str):
                try:
                    content_obj = json.loads(text_item['content'])
                    text_str = content_obj.get('text', '')
                    if 'styles' in content_obj:
                        for s in content_obj['styles']:
                            s['font'] = {'id': res_id, 'path': font_path}
                            # Set font size 9.0 for Title X and Title Y labels across all pairs
                            if any(lbl and lbl in text_str.upper() for lbl in title_labels):
                                s['size'] = 9.0
                    text_item['content'] = json.dumps(content_obj, ensure_ascii=False)
                except Exception as e:
                    logger.warning(f"Could not update inline style JSON for text item: {e}")

        with open(draft_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Patched draft_content.json: Font set to '{font_name}' (resource_id={res_id}).")
    except Exception as e:
        logger.warning(f"Failed to patch font metadata in draft_content.json: {e}")


def fix_effect_metadata_in_draft(project_path: str, effect_duration_us: int = 600_000, effect_name: str = "Jitter Beat") -> None:
    """
    Patches generated draft_content.json to:
    1. Set track flag = 2 on all overlay video tracks (img1_track, img2_track, mascot_track) so CapCut treats them as Picture-in-Picture (PIP) sub-tracks.
    2. Attach 'Jitter Beat' clip-bound video effects directly to each comparison image segment's extra_material_refs, so the effect is strictly isolated to that image clip and does NOT bleed onto the background.
    """
    draft_json_path = os.path.join(project_path, "draft_content.json")
    if not os.path.isfile(draft_json_path):
        return

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    local_cache_path = os.path.join(
        local_appdata, "CapCut", "User Data", "Cache", "effect",
        "7626761686543830290", "ed61aeec3e6dae1262ce40fa34d86c95"
    ).replace('\\', '/')

    try:
        with open(draft_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        effects_list = data.get('materials', {}).get('video_effects', [])
        image_tracks = {'img1_track', 'img2_track'}
        applied_count = 0

        for track in data.get('tracks', []):
            track_name = track.get('name', '')
            # Set flag = 2 for overlay sub-tracks (PIP) so effects stay isolated to clip
            if track.get('type') == 'video' and track_name != 'bg_track':
                track['flag'] = 2

            if track_name in image_tracks or (track.get('type') == 'video' and track_name not in {'bg_track', 'mascot_track'}):
                for seg in track.get('segments', []):
                    eff_mat_id = uuid.uuid4().hex.upper()

                    if 'extra_material_refs' not in seg:
                        seg['extra_material_refs'] = []
                    seg['extra_material_refs'].append(eff_mat_id)

                    effects_list.append({
                        "id": eff_mat_id,
                        "effect_id": "7626761686543830290",
                        "resource_id": "7626761686543830290",
                        "name": effect_name,
                        "type": "video_effect",
                        "sub_type": 0,
                        "bind_segment_id": "",
                        "transparent_params": "",
                        "path": local_cache_path if os.path.exists(local_cache_path) else "",
                        "value": 1.0,
                        "category_id": "1111",
                        "category_name": "Video effects",
                        "platform": "all",
                        "apply_target_type": 0,
                        "source_platform": 1,
                        "version": "",
                        "item_effect_type": 0,
                        "adjust_params": [
                            {
                                "name": "effects_adjust_speed",
                                "value": 0.08,
                                "default_value": 0.33333333333333
                            }
                        ],
                        "time_range": {
                            "start": 0,
                            "duration": effect_duration_us
                        },
                        "render_index": 11000,
                        "track_render_index": 0
                    })
                    applied_count += 1

        if 'materials' not in data:
            data['materials'] = {}
        data['materials']['video_effects'] = effects_list

        with open(draft_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Patched draft_content.json: Set overlay tracks flag=2 and attached {applied_count} clip-bound '{effect_name}' effect(s).")
    except Exception as e:
        logger.warning(f"Failed to patch clip-bound effect metadata in draft_content.json: {e}")


def get_audio_duration_us(audio_path: str, fallback_subtitle_end_us: int = 0) -> int:
    """
    Calculates exact audio duration in microseconds.
    Uses Python's built-in wave module for WAV files to bypass pymediainfo sample-rate miscalculations.
    """
    ext = os.path.splitext(audio_path)[1].lower()

    # 1. For WAV files, wave module is frame-exact
    if ext == ".wav":
        try:
            with wave.open(audio_path, 'rb') as w:
                frames = w.getnframes()
                rate = w.getframerate()
                if rate > 0:
                    duration_sec = frames / float(rate)
                    duration_us = int(duration_sec * 1_000_000)
                    logger.debug(f"Calculated exact WAV duration via wave module: {duration_sec:.3f}s ({duration_us} us)")
                    return duration_us
        except Exception as e:
            logger.warning(f"Could not parse WAV header via wave module: {e}")

    # 2. Try pymediainfo
    try:
        info = pymediainfo.MediaInfo.parse(audio_path)
        if len(info.audio_tracks) > 0 and info.audio_tracks[0].duration:
            duration_ms = float(info.audio_tracks[0].duration)
            duration_us = int(duration_ms * 1_000)

            # If pymediainfo duration is unexpectedly shorter than subtitles, use subtitle boundary
            if fallback_subtitle_end_us > 0 and duration_us < fallback_subtitle_end_us * 0.8:
                logger.warning(
                    f"pymediainfo reported truncated audio duration ({duration_us/1e6:.2f}s vs subtitles {fallback_subtitle_end_us/1e6:.2f}s). "
                    f"Adjusting to subtitle boundary."
                )
                return max(duration_us, fallback_subtitle_end_us)

            return duration_us
    except Exception as e:
        logger.warning(f"pymediainfo parse failed for '{audio_path}': {e}")

    # 3. Fallback to subtitle boundary if available
    return fallback_subtitle_end_us


def parse_srt_timestamp_to_us(timestamp_str: str) -> int:
    """
    Converts an SRT timestamp string (HH:MM:SS,mmm or HH:MM:SS.mmm) to microseconds.
    """
    ts = timestamp_str.strip().replace('.', ',')
    pattern = r'^(\d{2}):(\d{2}):(\d{2}),(\d{1,3})$'
    match = re.match(pattern, ts)
    if not match:
        raise ValueError(f"Invalid SRT timestamp format: '{timestamp_str}'")

    hours, minutes, seconds, millis_str = match.groups()
    millis = int(millis_str.ljust(3, '0'))  # Pad '5' -> '500', '50' -> '500' if needed
    total_ms = (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000 + millis
    return total_ms * 1000


def us_to_srt_timestamp(us: int) -> str:
    """
    Converts microseconds to SRT timestamp string (HH:MM:SS,mmm).
    """
    total_ms = us // 1000
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt_file(srt_path: str) -> List[SubtitleBlock]:
    """
    Parses an SRT file into a list of SubtitleBlock objects.
    """
    if not os.path.isfile(srt_path):
        raise FileNotFoundError(f"SRT file not found: {srt_path}")

    with open(srt_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    # Normalize newlines and split into blocks by blank lines
    blocks_raw = re.split(r'\n\s*\n', content.strip().replace('\r\n', '\n'))
    subtitle_blocks: List[SubtitleBlock] = []

    for block_idx, raw_block in enumerate(blocks_raw, start=1):
        lines = [line.strip() for line in raw_block.strip().split('\n') if line.strip()]
        if not lines:
            continue

        # Line 0: Subtitle index (optional, check if integer)
        line_offset = 0
        if lines[0].isdigit():
            idx = int(lines[0])
            line_offset = 1
        else:
            idx = block_idx

        if len(lines) <= line_offset:
            logger.warning(f"Block #{idx} has no timestamp or text lines. Skipping.")
            continue

        # Next line: Timestamp line (00:00:01,000 --> 00:00:04,000)
        time_line = lines[line_offset]
        if '-->' not in time_line:
            logger.warning(f"Block #{idx}: Expected timestamp arrow '-->', got '{time_line}'. Skipping.")
            continue

        time_parts = time_line.split('-->')
        if len(time_parts) < 2:
            logger.warning(f"Block #{idx}: Malformed timestamp '{time_line}'. Skipping.")
            continue

        start_tc = time_parts[0].strip()
        end_tc = time_parts[1].strip()

        try:
            start_us = parse_srt_timestamp_to_us(start_tc)
            end_us = parse_srt_timestamp_to_us(end_tc)
        except ValueError as e_ts:
            logger.warning(f"Block #{idx}: Invalid timestamp '{time_line}' ({e_ts}). Skipping.")
            continue

        if end_us <= start_us:
            logger.warning(f"Block #{idx}: End timestamp ({end_tc}) must be after start timestamp ({start_tc}). Skipping.")
            continue

        duration_us = end_us - start_us

        # Remaining lines: Subtitle text
        text_lines = lines[line_offset + 1:]
        raw_text = '\n'.join(text_lines)

        # Detect and extract all [IMG:tag_code] tags
        tag_matches = re.findall(r'\[IMG:\s*([^\]]+?)\s*\]', raw_text)
        tags = [t.strip() for t in tag_matches if t.strip()]

        # Strip [IMG:tag_code] tags from subtitle text
        clean_text = re.sub(r'\[IMG:\s*[^\]]+?\s*\]', '', raw_text).strip()
        # Clean up any leftover duplicate spaces or empty lines
        clean_text = re.sub(r'[ \t]+', ' ', clean_text)

        block = SubtitleBlock(
            index=idx,
            start_tc=start_tc,
            end_tc=end_tc,
            start_us=start_us,
            end_us=end_us,
            duration_us=duration_us,
            raw_text=raw_text,
            clean_text=clean_text,
            tags=tags
        )
        subtitle_blocks.append(block)

    return subtitle_blocks


def validate_inputs(
    srt_path: str,
    mapping_path: str,
    assets_dir: str,
    bg_image_path: Optional[str],
    audio_path: Optional[str],
    image1_path: Optional[str],
    image2_path: Optional[str],
    drafts_dir: str,
    subtitle_blocks: List[SubtitleBlock]
) -> Tuple[Dict[str, str], List[str]]:
    """
    Validates all inputs up front:
    1. Checks mapping JSON validity.
    2. Checks that every tag in the SRT exists in mapping JSON.
    3. Checks that every mapped image file exists in the assets directory.
    4. Checks background image, audio file, and optional image1/image2 existence.
    5. Validates target drafts directory path.

    Returns (mapping_dict, validation_errors).
    """
    errors: List[str] = []

    # 1. Validate mapping JSON
    if not os.path.isfile(mapping_path):
        return {}, [f"Mapping JSON file does not exist: {mapping_path}"]

    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        if not isinstance(mapping, dict):
            return {}, [f"Mapping JSON must contain a key-value object (dict), got {type(mapping).__name__}"]
    except Exception as e:
        return {}, [f"Failed to parse mapping JSON '{mapping_path}': {e}"]

    # 2. Check assets directory
    if not os.path.isdir(assets_dir):
        errors.append(f"Assets directory does not exist: {assets_dir}")

    # 3. Check tags in SRT against mapping and asset files
    all_tags = set()
    for block in subtitle_blocks:
        for tag in block.tags:
            all_tags.add(tag)

    missing_mappings = []
    missing_asset_files = []

    for tag in sorted(all_tags):
        if tag not in mapping:
            missing_mappings.append(tag)
        else:
            img_name = mapping[tag]
            img_path = os.path.join(assets_dir, img_name)
            if not os.path.isfile(img_path):
                missing_asset_files.append((tag, img_name, img_path))

    if missing_mappings:
        errors.append(
            f"SRT contains {len(missing_mappings)} tag(s) not found in mapping JSON: {missing_mappings}"
        )

    if missing_asset_files:
        details = ", ".join([f"tag '{t}' -> '{fn}' (missing at '{p}')" for t, fn, p in missing_asset_files])
        errors.append(f"Referenced image assets missing from assets directory: {details}")

    # 4. Check background image, audio file & image1 / image2
    if bg_image_path and not os.path.isfile(bg_image_path):
        errors.append(f"Background image file does not exist: {bg_image_path}")

    if audio_path and not os.path.isfile(audio_path):
        errors.append(f"Audio file does not exist: {audio_path}")

    if image1_path and not os.path.isfile(image1_path):
        errors.append(f"Image 1 file does not exist: {image1_path}")

    if image2_path and not os.path.isfile(image2_path):
        errors.append(f"Image 2 file does not exist: {image2_path}")

    # 5. Check drafts directory parent and create drafts_dir if needed
    if not drafts_dir:
        errors.append("CapCut drafts directory not specified and could not be auto-detected.")
    else:
        drafts_dir_path = Path(drafts_dir)
        if not drafts_dir_path.parent.exists():
            errors.append(f"Parent directory of CapCut drafts folder does not exist: {drafts_dir_path.parent}")
        else:
            try:
                os.makedirs(drafts_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"Could not create CapCut drafts directory '{drafts_dir}': {e}")

    return mapping, errors


def merge_contiguous_image_segments(
    blocks: List[SubtitleBlock],
    mapping: Dict[str, str],
    assets_dir: str,
    max_gap_us: int = 500000
) -> List[ImageSegmentSpec]:
    """
    Builds a continuous, gapless mascot overlay track across all subtitle blocks.
    Propagates active tags to untagged blocks to prevent mascot disappearances and flickering.
    """
    if not blocks:
        return []

    image_specs: List[ImageSegmentSpec] = []
    current_spec: Optional[ImageSegmentSpec] = None
    last_tag_code: str = "left"

    for idx, block in enumerate(blocks):
        if block.tags:
            tag_code = block.tags[0]
            last_tag_code = tag_code
        else:
            tag_code = last_tag_code

        img_filename = mapping.get(tag_code, mapping.get("left", "left.png"))
        img_path = os.path.abspath(os.path.join(assets_dir, img_filename))

        start_us = block.start_us
        end_us = block.end_us

        if current_spec is None:
            current_spec = ImageSegmentSpec(
                img_path=img_path,
                tag_code=tag_code,
                start_tc=block.start_tc,
                end_tc=block.end_tc,
                start_us=start_us,
                end_us=end_us,
                duration_us=end_us - start_us,
                source_blocks=[block.index]
            )
        else:
            # Extend previous spec to start_us to bridge gaps between subtitle blocks
            current_spec.end_us = max(current_spec.end_us, start_us)

            if current_spec.img_path == img_path:
                current_spec.end_us = max(current_spec.end_us, end_us)
                current_spec.end_tc = block.end_tc
                current_spec.duration_us = current_spec.end_us - current_spec.start_us
                current_spec.source_blocks.append(block.index)
            else:
                current_spec.duration_us = current_spec.end_us - current_spec.start_us
                image_specs.append(current_spec)

                current_spec = ImageSegmentSpec(
                    img_path=img_path,
                    tag_code=tag_code,
                    start_tc=block.start_tc,
                    end_tc=block.end_tc,
                    start_us=start_us,
                    end_us=end_us,
                    duration_us=end_us - start_us,
                    source_blocks=[block.index]
                )

    if current_spec:
        image_specs.append(current_spec)

    return image_specs


def add_sfx_segment(script, sfx_path: str, start_us: int, track_name: str) -> bool:
    """Helper to add a sound effect audio clip at a specific microsecond timestamp."""
    if not sfx_path or not os.path.isfile(sfx_path):
        logger.warning(f"SFX file not found: {sfx_path}")
        return False
    sfx_abs_path = os.path.abspath(sfx_path)
    sfx_duration_us = get_audio_duration_us(sfx_abs_path, fallback_subtitle_end_us=500_000)
    if sfx_duration_us <= 0:
        sfx_duration_us = 500_000  # Default 0.5s fallback
    script.add_track(pcc.TrackType.audio, track_name)
    sfx_material = pcc.AudioMaterial(sfx_abs_path)
    sfx_material.duration = sfx_duration_us
    timerange = pcc.Timerange(start_us, sfx_duration_us)
    sfx_seg = pcc.AudioSegment(sfx_material, timerange)
    script.add_segment(sfx_seg, track_name=track_name)
    logger.info(f"Added SFX '{os.path.basename(sfx_path)}' to track '{track_name}' at {start_us / 1_000_000:.3f}s (duration: {sfx_duration_us / 1_000_000:.2f}s)")
    return True


def generate_capcut_draft(
    drafts_dir: str,
    project_name: str,
    subtitle_blocks: List[SubtitleBlock],
    image_segments: List[ImageSegmentSpec],
    bg_image_path: Optional[str] = None,
    audio_path: Optional[str] = None,
    image1_path: Optional[str] = None,
    image2_path: Optional[str] = None,
    click_sfx_path: Optional[str] = "assets/sound_effects/mouse_click.mp3",
    pop_sfx_path: Optional[str] = "assets/sound_effects/pop.mp3",
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    image_scale: float = 0.42,
    image_alpha: float = 1.0,
    transform_x: float = -0.088889,
    transform_y: float = -0.425,
    img1_transform_x: float = -0.465741,
    img1_transform_y: float = 0.469792,
    img1_scale: float = 0.40,
    img2_transform_x: float = 0.510185,
    img2_transform_y: float = 0.473438,
    img2_scale: float = 0.40,
    text_transform_x: float = 0.0,
    text_transform_y: float = 0.042188,
    text_font_name: str = "LuckiestGuy-Rg",
    text_scale: float = 1.0,
    label1_text: str = "",
    label2_text: str = "",
    labels_x: Optional[List[str]] = None,
    labels_y: Optional[List[str]] = None,
    label1_transform_x: float = -0.448148,
    label1_transform_y: float = 0.781771,
    label2_transform_x: float = 0.476852,
    label2_transform_y: float = 0.778646,
    allow_replace: bool = True,
    mode: str = "auto",
    effect_duration_us: int = 600_000
) -> Tuple[str, int]:
    """
    Creates CapCut draft project folder containing:
    Track 1: Audio Track (Voiceover / Music)
    Track 2: Primary Background Track (dotgrid.png)
    Track 3: Image 1 Track (Top Left Comparison Image - 1:1 Cropped, Scale 40%, X=-503, Y=902)
    Track 4: Image 2 Track (Top Right Comparison Image - 1:1 Cropped, Scale 40%, X=551, Y=909)
    Track 5: Mascot Overlay Track (Scale 42%, X=-96, Y=-816)
    Track 6: Subtitle Text Track (LuckiestGuy-Rg, Black, Scale 100%, X=0, Y=81)
    """
    draft_folder = pcc.DraftFolder(drafts_dir)
    try:
        script = draft_folder.create_draft(
            project_name,
            width=width,
            height=height,
            fps=fps,
            allow_replace=allow_replace
        )
    except (PermissionError, OSError) as e_lock:
        alt_name = f"{project_name}_new"
        logger.warning(f"CapCut Desktop project '{project_name}' is currently locked/open in CapCut Desktop! Creating draft under '{alt_name}' instead.")
        script = draft_folder.create_draft(
            alt_name,
            width=width,
            height=height,
            fps=fps,
            allow_replace=allow_replace
        )
        project_name = alt_name

    max_subtitle_end_us = max((b.end_us for b in subtitle_blocks), default=30_000_000)

    # 1. Audio Track (Voiceover / Music)
    audio_duration_us = 0
    if audio_path and os.path.isfile(audio_path):
        script.add_track(pcc.TrackType.audio, "audio_track")
        audio_abs_path = os.path.abspath(audio_path)
        audio_material = pcc.AudioMaterial(audio_abs_path)

        # Fix/override pymediainfo duration calculation bug for WAV/audio files
        real_audio_us = get_audio_duration_us(audio_abs_path, fallback_subtitle_end_us=max_subtitle_end_us)
        if real_audio_us > 0:
            audio_material.duration = real_audio_us

        audio_duration_us = audio_material.duration
        audio_timerange = pcc.Timerange(0, audio_duration_us)
        audio_seg = pcc.AudioSegment(audio_material, audio_timerange)
        script.add_segment(audio_seg, track_name="audio_track")
        logger.info(f"Added Audio Track ({os.path.basename(audio_path)}), full duration: {audio_duration_us / 1_000_000:.2f}s")

    # Total project duration matches max of audio length & subtitles
    total_project_duration_us = max(audio_duration_us, max_subtitle_end_us)

    # Detect start time for Image 2 & Title Y (starts at subtitle block #2 / when [IMG:right] starts)
    img2_start_us = 0
    if subtitle_blocks:
        found_right = False
        for b in subtitle_blocks:
            if "right" in b.tags:
                img2_start_us = b.start_us
                found_right = True
                break
        if not found_right and len(subtitle_blocks) >= 2:
            img2_start_us = subtitle_blocks[1].start_us

    # Build compilation pair specifications for single-pair or multi-pair compilation shorts
    image_dict = find_all_comparison_images("input")
    if image1_path and 1 not in image_dict:
        image_dict[1] = os.path.abspath(image1_path)
    if image2_path and 2 not in image_dict:
        image_dict[2] = os.path.abspath(image2_path)

    # Resolve labels lists
    labels_x_list = labels_x if labels_x else ([label1_text] if label1_text else [])
    labels_y_list = labels_y if labels_y else ([label2_text] if label2_text else [])

    pair_specs = build_compilation_pair_specs(
        subtitle_blocks=subtitle_blocks,
        image_dict=image_dict,
        labels_x=labels_x_list,
        labels_y=labels_y_list,
        total_duration_us=total_project_duration_us,
        mode=mode
    )

    # 2. Primary Background Track (Bottom Layer)
    if bg_image_path and os.path.isfile(bg_image_path):
        script.add_track(pcc.TrackType.video, "bg_track")
        bg_abs_path = os.path.abspath(bg_image_path)
        bg_material = pcc.VideoMaterial(bg_abs_path)
        bg_timerange = pcc.Timerange(0, total_project_duration_us)
        bg_seg = pcc.VideoSegment(bg_material, bg_timerange)
        script.add_segment(bg_seg, track_name="bg_track")
        logger.info(f"Added Background Track ({os.path.basename(bg_image_path)}), extended to: {total_project_duration_us / 1_000_000:.2f}s")

    # 3. Image 1 Track (Top Left Comparison Images - 1:1 Auto Cropped, for each pair)
    has_img1 = any(p.image1_path and os.path.isfile(p.image1_path) for p in pair_specs)
    if has_img1:
        script.add_track(pcc.TrackType.video, "img1_track")
        img1_settings = pcc.ClipSettings(
            scale_x=img1_scale,
            scale_y=img1_scale,
            alpha=1.0,
            transform_x=img1_transform_x,
            transform_y=img1_transform_y
        )
        for p in pair_specs:
            if p.image1_path and os.path.isfile(p.image1_path):
                dur = max(0, p.end_us - p.start_us)
                if dur > 0:
                    cropped_img1 = ensure_1to1_crop(p.image1_path)
                    mat = pcc.VideoMaterial(cropped_img1)
                    timerange = pcc.Timerange(p.start_us, dur)
                    seg = pcc.VideoSegment(mat, timerange, clip_settings=img1_settings)
                    script.add_segment(seg, track_name="img1_track")
                    logger.info(f"Added Image 1 (Pair {p.pair_index}: {os.path.basename(p.image1_path)}) starting at {p.start_us / 1_000_000:.2f}s (dur: {dur / 1_000_000:.2f}s)")

    # 4. Image 2 Track (Top Right Comparison Images - 1:1 Auto Cropped, for each pair)
    has_img2 = any(p.image2_path and os.path.isfile(p.image2_path) for p in pair_specs)
    if has_img2:
        script.add_track(pcc.TrackType.video, "img2_track")
        img2_settings = pcc.ClipSettings(
            scale_x=img2_scale,
            scale_y=img2_scale,
            alpha=1.0,
            transform_x=img2_transform_x,
            transform_y=img2_transform_y
        )
        for p in pair_specs:
            if p.image2_path and os.path.isfile(p.image2_path):
                dur = max(0, p.end_us - p.right_start_us)
                if dur > 0:
                    cropped_img2 = ensure_1to1_crop(p.image2_path)
                    mat = pcc.VideoMaterial(cropped_img2)
                    timerange = pcc.Timerange(p.right_start_us, dur)
                    seg = pcc.VideoSegment(mat, timerange, clip_settings=img2_settings)
                    script.add_segment(seg, track_name="img2_track")
                    logger.info(f"Added Image 2 (Pair {p.pair_index}: {os.path.basename(p.image2_path)}) starting at {p.right_start_us / 1_000_000:.2f}s (dur: {dur / 1_000_000:.2f}s)")

    # 5. Merged Mascot Overlay Track (Middle Layer)
    script.add_track(pcc.TrackType.video, "mascot_track")
    for spec in image_segments:
        timerange = pcc.Timerange(spec.start_us, spec.duration_us)
        material = pcc.VideoMaterial(spec.img_path)
        clip_settings = pcc.ClipSettings(
            scale_x=image_scale,
            scale_y=image_scale,
            alpha=image_alpha,
            transform_x=transform_x,
            transform_y=transform_y
        )
        img_seg = pcc.VideoSegment(material, timerange, clip_settings=clip_settings)
        script.add_segment(img_seg, track_name="mascot_track")

    # Resolve LuckiestGuy-Rg Font
    font_res_id, _ = resolve_capcut_font_info(text_font_name)
    custom_font = CustomFontWrapper(text_font_name, resource_id=font_res_id)

    # 6. Title X Text Track (Red Label above Image 1 - pos_x=-484, pos_y=1501)
    has_label_x = any(p.label_x for p in pair_specs)
    if has_label_x:
        script.add_track(pcc.TrackType.text, "title_x_track")
        label1_style = pcc.TextStyle(color=(1.0, 0.117, 0.251))  # Red color #FF1E40
        label1_clip_settings = pcc.ClipSettings(
            scale_x=1.0,
            scale_y=1.0,
            transform_x=label1_transform_x,
            transform_y=label1_transform_y
        )
        for p in pair_specs:
            if p.label_x:
                dur = max(0, p.end_us - p.start_us)
                if dur > 0:
                    label1_timerange = pcc.Timerange(p.start_us, dur)
                    label1_seg = pcc.TextSegment(
                        p.label_x.upper(),
                        label1_timerange,
                        font=custom_font,
                        style=label1_style,
                        clip_settings=label1_clip_settings
                    )
                    script.add_segment(label1_seg, track_name="title_x_track")
                    logger.info(f"Added Title X (Pair {p.pair_index}: '{p.label_x.upper()}'), Red color, pos_x=-484px, pos_y=1501px")

    # 7. Title Y Text Track (Blue Label above Image 2 - pos_x=515, pos_y=1495, starts at 'This is Y')
    has_label_y = any(p.label_y for p in pair_specs)
    if has_label_y:
        script.add_track(pcc.TrackType.text, "title_y_track")
        label2_style = pcc.TextStyle(color=(0.0, 0.533, 1.0))  # Blue color #0088FF
        label2_clip_settings = pcc.ClipSettings(
            scale_x=1.0,
            scale_y=1.0,
            transform_x=label2_transform_x,
            transform_y=label2_transform_y
        )
        for p in pair_specs:
            if p.label_y:
                dur = max(0, p.end_us - p.right_start_us)
                if dur > 0:
                    label2_timerange = pcc.Timerange(p.right_start_us, dur)
                    label2_seg = pcc.TextSegment(
                        p.label_y.upper(),
                        label2_timerange,
                        font=custom_font,
                        style=label2_style,
                        clip_settings=label2_clip_settings
                    )
                    script.add_segment(label2_seg, track_name="title_y_track")
                    logger.info(f"Added Title Y (Pair {p.pair_index}: '{p.label_y.upper()}'), Blue color, starting at {p.right_start_us / 1_000_000:.2f}s, pos_x=515px, pos_y=1495px")

    # 8. Subtitle Text Track (Top Layer)
    script.add_track(pcc.TrackType.text, "text_track")
    text_style = pcc.TextStyle(color=(0.0, 0.0, 0.0))  # Black color
    text_clip_settings = pcc.ClipSettings(
        scale_x=text_scale,
        scale_y=text_scale,
        transform_x=text_transform_x,
        transform_y=text_transform_y
    )

    for block in subtitle_blocks:
        if block.clean_text:
            timerange = pcc.Timerange(block.start_us, block.duration_us)
            text_seg = pcc.TextSegment(
                block.clean_text,
                timerange,
                font=custom_font,
                style=text_style,
                clip_settings=text_clip_settings
            )
            script.add_segment(text_seg, track_name="text_track")

    # 9. Sound Effects (SFX) Audio Tracks
    # Click SFX: Played when Image 1 (left) and Image 2 (right) appear for each pair
    if click_sfx_path and os.path.isfile(click_sfx_path):
        for idx, p in enumerate(pair_specs):
            if p.image1_path and os.path.isfile(p.image1_path):
                add_sfx_segment(script, click_sfx_path, start_us=p.start_us, track_name=f"sfx_click_p{p.pair_index}_1")
            if p.image2_path and os.path.isfile(p.image2_path) and p.right_start_us > p.start_us:
                add_sfx_segment(script, click_sfx_path, start_us=p.right_start_us, track_name=f"sfx_click_p{p.pair_index}_2")

    # Pop SFX: Played 80ms before EVERY "what's the difference" (wtd) subtitle block
    if pop_sfx_path and os.path.isfile(pop_sfx_path) and subtitle_blocks:
        wtd_count = 0
        for b in subtitle_blocks:
            if "wtd" in b.tags or any(kw in b.clean_text.lower() for kw in ["difference", "wtd"]):
                wtd_count += 1
                pop_start_us = max(0, b.start_us - 80_000)
                add_sfx_segment(script, pop_sfx_path, start_us=pop_start_us, track_name=f"sfx_pop_wtd_{wtd_count}")

    # Pop 2: Just before / during final_end.png overlay (follow / subscribe for more)
    final_end_start_us = None
    if subtitle_blocks:
        for b in reversed(subtitle_blocks):
            if any(t in b.tags for t in ["final_end", "final"]) or any(kw in b.clean_text.lower() for kw in ["subscribe", "follow", "comment"]):
                final_end_start_us = b.start_us
                break

    if final_end_start_us is not None and pop_sfx_path and os.path.isfile(pop_sfx_path):
        pop2_start_us = max(0, final_end_start_us - 50_000)  # 50ms before final_end appears
        add_sfx_segment(script, pop_sfx_path, start_us=pop2_start_us, track_name="sfx_pop_final")

    script.save()
    project_path = os.path.join(drafts_dir, project_name)

    # Post-process draft_content.json to set exact CapCut font & clip-bound effect metadata fields
    fix_font_metadata_in_draft(project_path, font_name=text_font_name, label1_text=label1_text, label2_text=label2_text)
    if effect_duration_us > 0:
        fix_effect_metadata_in_draft(project_path, effect_duration_us=effect_duration_us, effect_name="Jitter Beat")

    return project_path, total_project_duration_us


def dump_debug_info(
    debug_dir: str,
    subtitle_blocks: List[SubtitleBlock],
    image_segments: List[ImageSegmentSpec],
    project_path: str,
    transform_x: float,
    transform_y: float,
    image_scale: float,
    image_alpha: float,
    text_transform_x: float,
    text_transform_y: float,
    text_font_name: str
) -> None:
    """
    Dumps parsed subtitle breakdown, merged image segments, and generated draft_content.json to debug folder.
    """
    os.makedirs(debug_dir, exist_ok=True)

    # Subtitle breakdown JSON
    blocks_data = []
    for b in subtitle_blocks:
        blocks_data.append({
            "index": b.index,
            "start_tc": b.start_tc,
            "end_tc": b.end_tc,
            "start_us": b.start_us,
            "duration_us": b.duration_us,
            "raw_text": b.raw_text,
            "clean_text": b.clean_text,
            "tags": b.tags,
            "resolved_images": b.resolved_images
        })

    debug_subtitles_path = os.path.join(debug_dir, "debug_subtitles.json")
    with open(debug_subtitles_path, 'w', encoding='utf-8') as f:
        json.dump(blocks_data, f, indent=2, ensure_ascii=False)

    logger.info(f"[DEBUG] Exported parsed subtitle breakdown to: {debug_subtitles_path}")

    # Merged image segments JSON
    img_segments_data = []
    for idx, seg in enumerate(image_segments, start=1):
        img_segments_data.append({
            "segment_index": idx,
            "tag_code": seg.tag_code,
            "image_filename": os.path.basename(seg.img_path),
            "image_path": seg.img_path,
            "start_tc": seg.start_tc,
            "end_tc": seg.end_tc,
            "start_us": seg.start_us,
            "end_us": seg.end_us,
            "duration_us": seg.duration_us,
            "duration_seconds": round(seg.duration_us / 1_000_000, 3),
            "source_subtitle_blocks": seg.source_blocks,
            "transform_settings": {
                "transform_x": transform_x,
                "transform_y": transform_y,
                "scale_x": image_scale,
                "scale_y": image_scale,
                "alpha": image_alpha
            }
        })

    debug_img_segments_path = os.path.join(debug_dir, "debug_image_segments.json")
    with open(debug_img_segments_path, 'w', encoding='utf-8') as f:
        json.dump(img_segments_data, f, indent=2, ensure_ascii=False)

    logger.info(f"[DEBUG] Exported merged image track breakdown to: {debug_img_segments_path}")

    # Copy generated draft_content.json
    draft_content_src = os.path.join(project_path, "draft_content.json")
    if os.path.isfile(draft_content_src):
        debug_draft_path = os.path.join(debug_dir, "debug_draft_content.json")
        with open(draft_content_src, 'r', encoding='utf-8') as f_in:
            draft_data = json.load(f_in)
        with open(debug_draft_path, 'w', encoding='utf-8') as f_out:
            json.dump(draft_data, f_out, indent=2, ensure_ascii=False)
        logger.info(f"[DEBUG] Exported generated draft JSON to: {debug_draft_path}")


def main():
    default_drafts_dir = get_default_capcut_drafts_dir()

    parser = argparse.ArgumentParser(
        description="Generate CapCut Desktop project draft from tagged SRT subtitle file and optional voiceover audio."
    )

    # Core Paths & Project Name with Smart Defaults
    parser.add_argument("name", nargs="?", help="Optional project name (e.g. 'capvsironman')")
    parser.add_argument("--name", "--project-name", dest="project_name_flag", help="Name for the output CapCut draft project")
    parser.add_argument("--srt", help="Path to tagged SRT subtitle file (default: auto-detected from input/ folder)")
    parser.add_argument("--audio", help="Path to voiceover audio file WAV/MP3 (default: auto-detected from input/ folder)")
    parser.add_argument("--image1", help="Path to Image 1 comparison file (default: auto-detected from input/ folder)")
    parser.add_argument("--image2", help="Path to Image 2 comparison file (default: auto-detected from input/ folder)")
    parser.add_argument("--mapping", default="config/mapping.json", help="Path to tag-to-image mapping JSON (default: config/mapping.json)")
    parser.add_argument("--assets", default="assets/mascot", help="Directory containing PNG image assets (default: assets/mascot)")
    parser.add_argument("--bg-image", default="assets/background/dotgrid.png", help="Path to primary background image (default: assets/background/dotgrid.png)")
    parser.add_argument("--drafts-dir", default=default_drafts_dir, help="Path to CapCut local drafts directory (auto-detected by default)")

    # Canvas & Video Format (Default 9:16 vertical video)
    parser.add_argument("--width", type=int, default=1080, help="Canvas width (default: 1080)")
    parser.add_argument("--height", type=int, default=1920, help="Canvas height (default: 1920)")
    parser.add_argument("--fps", type=int, default=30, help="Video frame rate (default: 30)")

    # Mascot Overlay Position & Scale (Fixed Defaults: x=-96, y=-816 pixels from canvas center; scale: 0.42 = 42%)
    parser.add_argument("--pos-x", type=float, default=-96.0, help="Mascot X position in pixels from canvas center (default: -96.0)")
    parser.add_argument("--pos-y", type=float, default=-816.0, help="Mascot Y position in pixels from canvas center (default: -816.0)")
    parser.add_argument("--raw-transform", action="store_true", help="Pass pos-x and pos-y as raw normalized ratios without pixel division")
    parser.add_argument("--image-scale", type=float, default=0.42, help="Mascot image scale factor (default: 0.42 = 42%%)")
    parser.add_argument("--image-alpha", type=float, default=1.0, help="Mascot image opacity/alpha (default: 1.0)")

    # Image 1 Attributes (Fixed Defaults: scale=40%, pos_x=-503, pos_y=902)
    parser.add_argument("--img1-pos-x", type=float, default=-503.0, help="Image 1 X position in pixels (default: -503.0)")
    parser.add_argument("--img1-pos-y", type=float, default=902.0, help="Image 1 Y position in pixels (default: 902.0)")
    parser.add_argument("--img1-scale", type=float, default=0.40, help="Image 1 scale factor (default: 0.40 = 40%%)")

    # Image 2 Attributes (Fixed Defaults: scale=40%, pos_x=551, pos_y=909)
    parser.add_argument("--img2-pos-x", type=float, default=551.0, help="Image 2 X position in pixels (default: 551.0)")
    parser.add_argument("--img2-pos-y", type=float, default=909.0, help="Image 2 Y position in pixels (default: 909.0)")
    parser.add_argument("--img2-scale", type=float, default=0.40, help="Image 2 scale factor (default: 0.40 = 40%%)")

    # Title Labels for Image 1..N (Red/Blue)
    parser.add_argument("--label1", "--label-x", default="", help="Label text string for Image 1 (Left / Red, e.g. 'MCU')")
    parser.add_argument("--label2", "--label-y", default="", help="Label text string for Image 2 (Right / Blue, e.g. 'MARVEL COMICS')")
    for idx in range(3, 13):
        parser.add_argument(f"--label{idx}", default="", help=f"Label text string for Image {idx}")
    parser.add_argument("--labels", default="", help="Comma/Semicolon separated list of labels for all comparison pairs")
    parser.add_argument("--label1-pos-x", type=float, default=-484.0, help="Label 1 X position in pixels (default: -484.0)")
    parser.add_argument("--label1-pos-y", type=float, default=1501.0, help="Label 1 Y position in pixels (default: 1501.0)")
    parser.add_argument("--label2-pos-x", type=float, default=515.0, help="Label 2 X position in pixels (default: 515.0)")
    parser.add_argument("--label2-pos-y", type=float, default=1495.0, help="Label 2 Y position in pixels (default: 1495.0)")

    # Subtitle Text Formatting & Position (Fixed Defaults: X=0, Y=81 pixels from center; Font: LuckiestGuy-Rg; Color: Black)
    parser.add_argument("--text-pos-x", type=float, default=0.0, help="Subtitle X position in pixels from canvas center (default: 0.0)")
    parser.add_argument("--text-pos-y", type=float, default=81.0, help="Subtitle Y position in pixels from canvas center (default: 81.0)")
    parser.add_argument("--text-font", default="LuckiestGuy-Rg", help="Subtitle font family name (default: LuckiestGuy-Rg)")
    parser.add_argument("--text-scale", type=float, default=1.0, help="Subtitle scale factor (default: 1.0 = 100%%)")

    # Sound Effects (SFX) Paths
    parser.add_argument("--click-sfx", default="assets/sound_effects/mouse_click.mp3", help="Path to mouse click sound effect (default: assets/sound_effects/mouse_click.mp3)")
    parser.add_argument("--pop-sfx", default="assets/sound_effects/pop.mp3", help="Path to pop sound effect (default: assets/sound_effects/pop.mp3)")

    # Options
    parser.add_argument("--mode", "-m", choices=["deepdive", "compilation", "auto"], default="auto", help="Video Short Mode: 'deepdive' (1 pair / 2 images), 'compilation' (3 pairs / 6 images), or 'auto'")
    parser.add_argument("--effect-duration-ms", type=int, default=600, help="Duration in ms for 'Jitter Beat' popup effect at image start (default: 600 = 0.6s)")
    parser.add_argument("--no-effect", action="store_true", help="Disable 'Jitter Beat' popup effect at image start")
    parser.add_argument("--max-gap-ms", type=int, default=100, help="Max gap in ms to bridge contiguous blocks with same tag (default: 100)")
    parser.add_argument("--debug-dir", help="Directory path to dump debug JSON files for inspection")
    parser.add_argument("--no-overwrite", action="store_true", help="Do not overwrite draft if project folder already exists")

    args = parser.parse_args()

    # 0a. Auto-detect SRT file if not explicitly passed
    srt_path = args.srt
    if not srt_path:
        srt_path = find_input_srt("input")

    if not srt_path:
        logger.error("No SRT file provided and no .srt file found in 'input/' folder!")
        logger.error("Please place your .srt file in 'input/' or specify via '--srt input/your_file.srt'")
        sys.exit(1)

    # 0b. Auto-detect Audio file if not explicitly passed
    audio_path = args.audio
    if not audio_path:
        audio_path = find_input_audio("input")

    # 0c. Auto-detect Image 1 and Image 2 if not explicitly passed
    image1_path = args.image1
    if not image1_path:
        image1_path = find_input_image_by_prefix(["image1", "img1", "left_image", "1"], "input")

    image2_path = args.image2
    if not image2_path:
        image2_path = find_input_image_by_prefix(["image2", "img2", "right_image", "2"], "input")

    # Infer project name from flag, positional argument, or SRT filename
    project_name = (args.project_name_flag or args.name or Path(srt_path).stem).strip('\\/ ')

    logger.info("Starting CapCut Draft Builder pipeline...")
    logger.info(f"Input SRT: {srt_path}")
    logger.info(f"Input Audio: {audio_path if audio_path else 'None (subtitles only)'}")
    logger.info(f"Image 1: {image1_path if image1_path else 'None'}")
    logger.info(f"Image 2: {image2_path if image2_path else 'None'}")
    logger.info(f"Click SFX: {args.click_sfx if os.path.isfile(args.click_sfx) else 'None'}")
    logger.info(f"Pop SFX: {args.pop_sfx if os.path.isfile(args.pop_sfx) else 'None'}")
    logger.info(f"Input Mapping: {args.mapping}")
    logger.info(f"Assets Directory: {args.assets}")
    logger.info(f"Background Image: {args.bg_image}")
    logger.info(f"CapCut Drafts Dir: {args.drafts_dir}")
    logger.info(f"Project Name: {project_name}")
    logger.info(f"Canvas Resolution: {args.width}x{args.height} @ {args.fps}fps")

    # Calculate overlay transform_x and transform_y
    if args.raw_transform:
        transform_x = args.pos_x
        transform_y = args.pos_y
        img1_transform_x = args.img1_pos_x
        img1_transform_y = args.img1_pos_y
        img2_transform_x = args.img2_pos_x
        img2_transform_y = args.img2_pos_y
        text_transform_x = args.text_pos_x
        text_transform_y = args.text_pos_y
        label1_transform_x = args.label1_pos_x
        label1_transform_y = args.label1_pos_y
        label2_transform_x = args.label2_pos_x
        label2_transform_y = args.label2_pos_y
    else:
        transform_x = round(args.pos_x / args.width, 6)
        transform_y = round(args.pos_y / args.height, 6)
        img1_transform_x = round(args.img1_pos_x / args.width, 6)
        img1_transform_y = round(args.img1_pos_y / args.height, 6)
        img2_transform_x = round(args.img2_pos_x / args.width, 6)
        img2_transform_y = round(args.img2_pos_y / args.height, 6)
        text_transform_x = round(args.text_pos_x / args.width, 6)
        text_transform_y = round(args.text_pos_y / args.height, 6)
        label1_transform_x = round(args.label1_pos_x / args.width, 6)
        label1_transform_y = round(args.label1_pos_y / args.height, 6)
        label2_transform_x = round(args.label2_pos_x / args.width, 6)
        label2_transform_y = round(args.label2_pos_y / args.height, 6)

    logger.info(f"Mascot Overlay: pos_x={args.pos_x}px, pos_y={args.pos_y}px, scale={args.image_scale*100:.1f}% => transform_x={transform_x}, transform_y={transform_y}")
    if image1_path:
        logger.info(f"Image 1: pos_x={args.img1_pos_x}px, pos_y={args.img1_pos_y}px, scale={args.img1_scale*100:.1f}% => transform_x={img1_transform_x}, transform_y={img1_transform_y}")
    if image2_path:
        logger.info(f"Image 2: pos_x={args.img2_pos_x}px, pos_y={args.img2_pos_y}px, scale={args.img2_scale*100:.1f}% => transform_x={img2_transform_x}, transform_y={img2_transform_y}")
    if args.label1:
        logger.info(f"Title X (Red): '{args.label1}', pos_x={args.label1_pos_x}px, pos_y={args.label1_pos_y}px => transform_x={label1_transform_x}, transform_y={label1_transform_y}")
    if args.label2:
        logger.info(f"Title Y (Blue): '{args.label2}', pos_x={args.label2_pos_x}px, pos_y={args.label2_pos_y}px => transform_x={label2_transform_x}, transform_y={label2_transform_y}")
    logger.info(f"Subtitles: pos_x={args.text_pos_x}px, pos_y={args.text_pos_y}px, font='{args.text_font}', color=Black, scale={args.text_scale*100:.1f}% => transform_x={text_transform_x}, transform_y={text_transform_y}")

    # 1. Parse SRT File
    try:
        blocks = parse_srt_file(srt_path)
        logger.info(f"Successfully parsed SRT file: {len(blocks)} subtitle block(s) found.")
    except Exception as e:
        logger.error(f"SRT Parsing Error: {e}")
        sys.exit(1)

    # 2. Validate Inputs & Up-front Asset Resolution
    mapping, validation_errors = validate_inputs(
        srt_path=srt_path,
        mapping_path=args.mapping,
        assets_dir=args.assets,
        bg_image_path=args.bg_image,
        audio_path=audio_path,
        image1_path=image1_path,
        image2_path=image2_path,
        drafts_dir=args.drafts_dir,
        subtitle_blocks=blocks
    )

    if validation_errors:
        logger.error("=" * 60)
        logger.error("VALIDATION FAILED - Aborting draft creation:")
        for err in validation_errors:
            logger.error(f" - {err}")
        logger.error("=" * 60)
        sys.exit(1)

    logger.info("Validation passed successfully! All tags and asset files resolved.")

    # Populate resolved images in blocks
    for b in blocks:
        for tag in b.tags:
            img_name = mapping[tag]
            img_path = os.path.abspath(os.path.join(args.assets, img_name))
            b.resolved_images.append(img_path)

    # 3. Merge contiguous blocks with the same tag into seamless image segments
    max_gap_us = args.max_gap_ms * 1000
    image_segments = merge_contiguous_image_segments(
        blocks=blocks,
        mapping=mapping,
        assets_dir=args.assets,
        max_gap_us=max_gap_us
    )

    pngs_used = set(os.path.basename(seg.img_path) for seg in image_segments)
    untagged_block_count = sum(1 for b in blocks if not b.tags)

    logger.info(f"Merged subtitle block tags into {len(image_segments)} continuous image overlay segment(s).")

    # Extract labels_x and labels_y for multi-pair compilation shorts
    labels_x = []
    labels_y = []
    if args.labels:
        raw = args.labels
        if ";" in raw:
            pair_strs = raw.split(";")
            for p in pair_strs:
                parts = [x.strip() for x in p.split(",") if x.strip()]
                if len(parts) >= 2:
                    labels_x.append(parts[0])
                    labels_y.append(parts[1])
                elif len(parts) == 1:
                    labels_x.append(parts[0])
                    labels_y.append("")
        else:
            parts = [x.strip() for x in raw.split(",") if x.strip()]
            for idx in range(0, len(parts), 2):
                labels_x.append(parts[idx])
                labels_y.append(parts[idx + 1] if idx + 1 < len(parts) else "")
    else:
        for idx in range(1, 13, 2):
            lx = getattr(args, f"label{idx}", "")
            ly = getattr(args, f"label{idx+1}", "")
            if lx or ly:
                labels_x.append(lx)
                labels_y.append(ly)

    # 4. Generate CapCut Draft
    try:
        project_path, total_duration_us = generate_capcut_draft(
            drafts_dir=args.drafts_dir,
            project_name=project_name,
            subtitle_blocks=blocks,
            image_segments=image_segments,
            bg_image_path=args.bg_image,
            audio_path=audio_path,
            image1_path=image1_path,
            image2_path=image2_path,
            click_sfx_path=args.click_sfx,
            pop_sfx_path=args.pop_sfx,
            width=args.width,
            height=args.height,
            fps=args.fps,
            image_scale=args.image_scale,
            image_alpha=args.image_alpha,
            transform_x=transform_x,
            transform_y=transform_y,
            img1_transform_x=img1_transform_x,
            img1_transform_y=img1_transform_y,
            img1_scale=args.img1_scale,
            img2_transform_x=img2_transform_x,
            img2_transform_y=img2_transform_y,
            img2_scale=args.img2_scale,
            text_transform_x=text_transform_x,
            text_transform_y=text_transform_y,
            text_font_name=args.text_font,
            text_scale=args.text_scale,
            label1_text=args.label1,
            label2_text=args.label2,
            labels_x=labels_x,
            labels_y=labels_y,
            label1_transform_x=label1_transform_x,
            label1_transform_y=label1_transform_y,
            label2_transform_x=label2_transform_x,
            label2_transform_y=label2_transform_y,
            allow_replace=not args.no_overwrite,
            mode=args.mode,
            effect_duration_us=0 if args.no_effect else (args.effect_duration_ms * 1000)
        )
        logger.info(f"SUCCESS: CapCut draft created at: {project_path}")
    except Exception as e:
        logger.error(f"Failed to generate CapCut draft: {e}", exc_info=True)
        sys.exit(1)

    # 5. Output Debug Information if requested
    if args.debug_dir:
        dump_debug_info(
            debug_dir=args.debug_dir,
            subtitle_blocks=blocks,
            image_segments=image_segments,
            project_path=project_path,
            transform_x=transform_x,
            transform_y=transform_y,
            image_scale=args.image_scale,
            image_alpha=args.image_alpha,
            text_transform_x=text_transform_x,
            text_transform_y=text_transform_y,
            text_font_name=args.text_font
        )

    # 6. Final Summary Report
    logger.info("=" * 60)
    logger.info("EXECUTION SUMMARY:")
    logger.info(f" - Total Subtitle Blocks Processed : {len(blocks)}")
    logger.info(f" - Subtitle Blocks with Tags       : {len(blocks) - untagged_block_count}")
    logger.info(f" - Subtitle Blocks without Tags    : {untagged_block_count} (normal text-only blocks)")
    logger.info(f" - Audio Voiceover File            : {audio_path if audio_path else 'None'}")
    logger.info(f" - Image 1 (Top Left 1:1)          : {image1_path if image1_path else 'None'} (scale=40%, pos_x=-503, pos_y=902)")
    logger.info(f" - Image 2 (Top Right 1:1)         : {image2_path if image2_path else 'None'} (scale=40%, pos_x=551, pos_y=909)")
    logger.info(f" - Total Timeline Duration         : {total_duration_us / 1_000_000:.2f}s")
    logger.info(f" - Primary Background Image        : {args.bg_image} (extended to {total_duration_us / 1_000_000:.2f}s)")
    logger.info(f" - Merged Mascot Overlay Segments  : {len(image_segments)}")
    logger.info(f" - Unique Mascot PNG Assets Used   : {len(pngs_used)} ({', '.join(sorted(pngs_used)) if pngs_used else 'None'})")
    logger.info(f" - Mascot Scale & Position         : scale={args.image_scale*100:.1f}%, pos_x={args.pos_x}px, pos_y={args.pos_y}px")
    logger.info(f" - Subtitle Font & Position        : font='{args.text_font}', color=Black, pos_x={args.text_pos_x}px, pos_y={args.text_pos_y}px")
    logger.info(f" - Project Ready in CapCut         : {project_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

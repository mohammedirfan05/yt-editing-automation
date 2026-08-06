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


def fix_font_metadata_in_draft(project_path: str, font_name: str = "LuckiestGuy-Rg") -> None:
    """
    Patches generated draft_content.json text materials to populate CapCut font fields
    (font_resource_id, font_path, font_title, font_name, fonts array) so CapCut Desktop renders LuckiestGuy-Rg natively.
    """
    draft_json_path = os.path.join(project_path, "draft_content.json")
    if not os.path.isfile(draft_json_path):
        return

    res_id, font_path = resolve_capcut_font_info(font_name)

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
                    if 'styles' in content_obj:
                        for s in content_obj['styles']:
                            s['font'] = {'id': res_id, 'path': font_path}
                    text_item['content'] = json.dumps(content_obj, ensure_ascii=False)
                except Exception as e:
                    logger.warning(f"Could not update inline style JSON for text item: {e}")

        with open(draft_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Patched draft_content.json: Font set to '{font_name}' (resource_id={res_id}).")
    except Exception as e:
        logger.warning(f"Failed to patch font metadata in draft_content.json: {e}")


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
            raise ValueError(f"Block #{idx}: Expected timestamp arrow '-->', got '{time_line}'")

        time_parts = time_line.split('-->')
        start_tc = time_parts[0].strip()
        end_tc = time_parts[1].strip()

        start_us = parse_srt_timestamp_to_us(start_tc)
        end_us = parse_srt_timestamp_to_us(end_tc)

        if end_us <= start_us:
            raise ValueError(f"Block #{idx}: End timestamp ({end_tc}) must be after start timestamp ({start_tc})")

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
    max_gap_us: int = 100000  # 100ms threshold for bridging tiny gaps
) -> List[ImageSegmentSpec]:
    """
    Groups contiguous subtitle blocks that share the exact same resolved image asset
    and merges them into a single continuous ImageSegmentSpec to prevent flickering.
    """
    image_specs: List[ImageSegmentSpec] = []
    current_spec: Optional[ImageSegmentSpec] = None

    for block in blocks:
        if not block.tags:
            # Block has no image tag -> close current spec if open
            if current_spec:
                image_specs.append(current_spec)
                current_spec = None
            continue

        # Use the first tag code for image placement
        tag_code = block.tags[0]
        img_filename = mapping[tag_code]
        img_path = os.path.abspath(os.path.join(assets_dir, img_filename))

        if current_spec is None:
            # Start a new image segment
            current_spec = ImageSegmentSpec(
                img_path=img_path,
                tag_code=tag_code,
                start_tc=block.start_tc,
                end_tc=block.end_tc,
                start_us=block.start_us,
                end_us=block.end_us,
                duration_us=block.duration_us,
                source_blocks=[block.index]
            )
        else:
            # Check if this block continues the same image segment
            is_same_image = (current_spec.img_path == img_path)
            is_contiguous = (block.start_us - current_spec.end_us <= max_gap_us)

            if is_same_image and is_contiguous:
                # Merge into existing continuous segment
                current_spec.end_us = block.end_us
                current_spec.end_tc = block.end_tc
                current_spec.duration_us = current_spec.end_us - current_spec.start_us
                current_spec.source_blocks.append(block.index)
            else:
                # Finalize previous segment and start new segment
                image_specs.append(current_spec)
                current_spec = ImageSegmentSpec(
                    img_path=img_path,
                    tag_code=tag_code,
                    start_tc=block.start_tc,
                    end_tc=block.end_tc,
                    start_us=block.start_us,
                    end_us=block.end_us,
                    duration_us=block.duration_us,
                    source_blocks=[block.index]
                )

    if current_spec:
        image_specs.append(current_spec)

    return image_specs


def generate_capcut_draft(
    drafts_dir: str,
    project_name: str,
    subtitle_blocks: List[SubtitleBlock],
    image_segments: List[ImageSegmentSpec],
    bg_image_path: Optional[str] = None,
    audio_path: Optional[str] = None,
    image1_path: Optional[str] = None,
    image2_path: Optional[str] = None,
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
    allow_replace: bool = True
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
    script = draft_folder.create_draft(
        project_name,
        width=width,
        height=height,
        fps=fps,
        allow_replace=allow_replace
    )

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

    # 2. Primary Background Track (Bottom Layer)
    if bg_image_path and os.path.isfile(bg_image_path):
        script.add_track(pcc.TrackType.video, "bg_track")
        bg_abs_path = os.path.abspath(bg_image_path)
        bg_material = pcc.VideoMaterial(bg_abs_path)
        bg_timerange = pcc.Timerange(0, total_project_duration_us)
        bg_seg = pcc.VideoSegment(bg_material, bg_timerange)
        script.add_segment(bg_seg, track_name="bg_track")
        logger.info(f"Added Background Track ({os.path.basename(bg_image_path)}), extended to: {total_project_duration_us / 1_000_000:.2f}s")

    # 3. Image 1 Track (Top Left Comparison Image - 1:1 Auto Cropped)
    if image1_path and os.path.isfile(image1_path):
        script.add_track(pcc.TrackType.video, "img1_track")
        cropped_img1_path = ensure_1to1_crop(image1_path)
        img1_material = pcc.VideoMaterial(cropped_img1_path)
        img1_timerange = pcc.Timerange(0, total_project_duration_us)
        img1_settings = pcc.ClipSettings(
            scale_x=img1_scale,
            scale_y=img1_scale,
            alpha=1.0,
            transform_x=img1_transform_x,
            transform_y=img1_transform_y
        )
        img1_seg = pcc.VideoSegment(img1_material, img1_timerange, clip_settings=img1_settings)
        script.add_segment(img1_seg, track_name="img1_track")
        logger.info(f"Added Image 1 Track ({os.path.basename(image1_path)}), 1:1 cropped, scale={img1_scale*100:.0f}%, transform=({img1_transform_x}, {img1_transform_y})")

    # 4. Image 2 Track (Top Right Comparison Image - 1:1 Auto Cropped)
    if image2_path and os.path.isfile(image2_path):
        script.add_track(pcc.TrackType.video, "img2_track")
        cropped_img2_path = ensure_1to1_crop(image2_path)
        img2_material = pcc.VideoMaterial(cropped_img2_path)
        img2_timerange = pcc.Timerange(0, total_project_duration_us)
        img2_settings = pcc.ClipSettings(
            scale_x=img2_scale,
            scale_y=img2_scale,
            alpha=1.0,
            transform_x=img2_transform_x,
            transform_y=img2_transform_y
        )
        img2_seg = pcc.VideoSegment(img2_material, img2_timerange, clip_settings=img2_settings)
        script.add_segment(img2_seg, track_name="img2_track")
        logger.info(f"Added Image 2 Track ({os.path.basename(image2_path)}), 1:1 cropped, scale={img2_scale*100:.0f}%, transform=({img2_transform_x}, {img2_transform_y})")

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

    # 6. Subtitle Text Track (Top Layer)
    script.add_track(pcc.TrackType.text, "text_track")
    font_res_id, _ = resolve_capcut_font_info(text_font_name)
    custom_font = CustomFontWrapper(text_font_name, resource_id=font_res_id)
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

    script.save()
    project_path = os.path.join(drafts_dir, project_name)

    # Post-process draft_content.json to set exact CapCut font metadata fields
    fix_font_metadata_in_draft(project_path, font_name=text_font_name)

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

    # Subtitle Text Formatting & Position (Fixed Defaults: X=0, Y=81 pixels from center; Font: LuckiestGuy-Rg; Color: Black)
    parser.add_argument("--text-pos-x", type=float, default=0.0, help="Subtitle X position in pixels from canvas center (default: 0.0)")
    parser.add_argument("--text-pos-y", type=float, default=81.0, help="Subtitle Y position in pixels from canvas center (default: 81.0)")
    parser.add_argument("--text-font", default="LuckiestGuy-Rg", help="Subtitle font family name (default: LuckiestGuy-Rg)")
    parser.add_argument("--text-scale", type=float, default=1.0, help="Subtitle scale factor (default: 1.0 = 100%%)")

    # Options
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
    project_name = args.project_name_flag or args.name
    if not project_name:
        project_name = Path(srt_path).stem

    logger.info("Starting CapCut Draft Builder pipeline...")
    logger.info(f"Input SRT: {srt_path}")
    logger.info(f"Input Audio: {audio_path if audio_path else 'None (subtitles only)'}")
    logger.info(f"Image 1: {image1_path if image1_path else 'None'}")
    logger.info(f"Image 2: {image2_path if image2_path else 'None'}")
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
    else:
        transform_x = round(args.pos_x / args.width, 6)
        transform_y = round(args.pos_y / args.height, 6)
        img1_transform_x = round(args.img1_pos_x / args.width, 6)
        img1_transform_y = round(args.img1_pos_y / args.height, 6)
        img2_transform_x = round(args.img2_pos_x / args.width, 6)
        img2_transform_y = round(args.img2_pos_y / args.height, 6)
        text_transform_x = round(args.text_pos_x / args.width, 6)
        text_transform_y = round(args.text_pos_y / args.height, 6)

    logger.info(f"Mascot Overlay: pos_x={args.pos_x}px, pos_y={args.pos_y}px, scale={args.image_scale*100:.1f}% => transform_x={transform_x}, transform_y={transform_y}")
    if image1_path:
        logger.info(f"Image 1: pos_x={args.img1_pos_x}px, pos_y={args.img1_pos_y}px, scale={args.img1_scale*100:.1f}% => transform_x={img1_transform_x}, transform_y={img1_transform_y}")
    if image2_path:
        logger.info(f"Image 2: pos_x={args.img2_pos_x}px, pos_y={args.img2_pos_y}px, scale={args.img2_scale*100:.1f}% => transform_x={img2_transform_x}, transform_y={img2_transform_y}")
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
            allow_replace=not args.no_overwrite
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

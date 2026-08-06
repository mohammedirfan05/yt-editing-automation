#!/usr/bin/env python3
r"""
CapCut Desktop Project Generator from Tagged SRT

Programmatically generates CapCut Desktop video editing projects from a tagged SRT subtitle file,
tag-to-image mapping file, mascot PNG library, and primary background image.

Usage:
    python build_draft.py                                # Auto-detects input/*.srt & generates draft!
    python build_draft.py --srt input/my_video.srt      # Process specific SRT in input folder
"""

import argparse
import json
import logging
import os
import platform
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pycapcut as pcc
from pycapcut.metadata.effect_meta import EffectMeta

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("CapCutDraftBuilder")


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
    def __init__(self, font_name: str):
        self.value = EffectMeta(font_name, True, font_name, font_name, "", [])


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
    drafts_dir: str,
    subtitle_blocks: List[SubtitleBlock]
) -> Tuple[Dict[str, str], List[str]]:
    """
    Validates all inputs up front:
    1. Checks mapping JSON validity.
    2. Checks that every tag in the SRT exists in mapping JSON.
    3. Checks that every mapped image file exists in the assets directory.
    4. Checks that background image exists (if provided).
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

    # 4. Check background image file
    if bg_image_path and not os.path.isfile(bg_image_path):
        errors.append(f"Background image file does not exist: {bg_image_path}")

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
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    image_scale: float = 0.42,
    image_alpha: float = 1.0,
    transform_x: float = -0.088889,
    transform_y: float = -0.425,
    text_transform_x: float = 0.0,
    text_transform_y: float = 0.042188,
    text_font_name: str = "LuckiestGuy-Rg",
    text_scale: float = 1.0,
    allow_replace: bool = True
) -> str:
    """
    Creates CapCut draft project folder containing background video track, mascot overlay track, and subtitle text track.
    Returns path to the created project directory.
    """
    draft_folder = pcc.DraftFolder(drafts_dir)
    script = draft_folder.create_draft(
        project_name,
        width=width,
        height=height,
        fps=fps,
        allow_replace=allow_replace
    )

    # Calculate final subtitle end time to extend background
    max_end_us = max((b.end_us for b in subtitle_blocks), default=30_000_000)

    # 1. Primary Background Track (Bottom Layer)
    if bg_image_path and os.path.isfile(bg_image_path):
        script.add_track(pcc.TrackType.video, "bg_track")
        bg_abs_path = os.path.abspath(bg_image_path)
        bg_material = pcc.VideoMaterial(bg_abs_path)
        bg_timerange = pcc.Timerange(0, max_end_us)
        bg_seg = pcc.VideoSegment(bg_material, bg_timerange)
        script.add_segment(bg_seg, track_name="bg_track")

    # 2. Merged Mascot Overlay Track (Middle Layer)
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

    # 3. Subtitle Text Track (Top Layer)
    script.add_track(pcc.TrackType.text, "text_track")
    custom_font = CustomFontWrapper(text_font_name)
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
    return os.path.join(drafts_dir, project_name)


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
        description="Generate CapCut Desktop project draft from tagged SRT subtitle file."
    )

    # Core Paths with Smart Defaults
    parser.add_argument("--srt", help="Path to tagged SRT subtitle file (default: auto-detected from input/ folder)")
    parser.add_argument("--mapping", default="config/mapping.json", help="Path to tag-to-image mapping JSON (default: config/mapping.json)")
    parser.add_argument("--assets", default="assets/mascot", help="Directory containing PNG image assets (default: assets/mascot)")
    parser.add_argument("--bg-image", default="assets/background/dotgrid.png", help="Path to primary background image (default: assets/background/dotgrid.png)")
    parser.add_argument("--drafts-dir", default=default_drafts_dir, help="Path to CapCut local drafts directory (auto-detected by default)")
    parser.add_argument("--project-name", help="Name for the output CapCut draft project (default: inferred from SRT filename)")

    # Canvas & Video Format (Default 9:16 vertical video)
    parser.add_argument("--width", type=int, default=1080, help="Canvas width (default: 1080)")
    parser.add_argument("--height", type=int, default=1920, help="Canvas height (default: 1920)")
    parser.add_argument("--fps", type=int, default=30, help="Video frame rate (default: 30)")

    # Overlay Position & Scale (Fixed Defaults: x=-96, y=-816 pixels from canvas center; scale: 0.42 = 42%)
    parser.add_argument("--pos-x", type=float, default=-96.0, help="Overlay X position in pixels from canvas center (default: -96.0)")
    parser.add_argument("--pos-y", type=float, default=-816.0, help="Overlay Y position in pixels from canvas center (default: -816.0)")
    parser.add_argument("--raw-transform", action="store_true", help="Pass pos-x and pos-y as raw normalized ratios without pixel division")
    parser.add_argument("--image-scale", type=float, default=0.42, help="Overlay image scale factor (default: 0.42 = 42%%)")
    parser.add_argument("--image-alpha", type=float, default=1.0, help="Overlay image opacity/alpha (default: 1.0)")

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

    # 0. Auto-detect SRT file if not explicitly passed
    srt_path = args.srt
    if not srt_path:
        srt_path = find_input_srt("input")

    if not srt_path:
        logger.error("No SRT file provided and no .srt file found in 'input/' folder!")
        logger.error("Please place your .srt file in 'input/' or specify via '--srt input/your_file.srt'")
        sys.exit(1)

    # Infer project name from SRT filename if not specified
    project_name = args.project_name
    if not project_name:
        project_name = Path(srt_path).stem

    logger.info("Starting CapCut Draft Builder pipeline...")
    logger.info(f"Input SRT: {srt_path}")
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
        text_transform_x = args.text_pos_x
        text_transform_y = args.text_pos_y
    else:
        transform_x = round(args.pos_x / args.width, 6)
        transform_y = round(args.pos_y / args.height, 6)
        text_transform_x = round(args.text_pos_x / args.width, 6)
        text_transform_y = round(args.text_pos_y / args.height, 6)

    logger.info(f"Mascot Overlay: pos_x={args.pos_x}px, pos_y={args.pos_y}px, scale={args.image_scale*100:.1f}% => transform_x={transform_x}, transform_y={transform_y}")
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
        project_path = generate_capcut_draft(
            drafts_dir=args.drafts_dir,
            project_name=project_name,
            subtitle_blocks=blocks,
            image_segments=image_segments,
            bg_image_path=args.bg_image,
            width=args.width,
            height=args.height,
            fps=args.fps,
            image_scale=args.image_scale,
            image_alpha=args.image_alpha,
            transform_x=transform_x,
            transform_y=transform_y,
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
    logger.info(f" - Primary Background Image        : {args.bg_image}")
    logger.info(f" - Merged Image Overlay Segments   : {len(image_segments)}")
    logger.info(f" - Unique PNG Assets Used          : {len(pngs_used)} ({', '.join(sorted(pngs_used)) if pngs_used else 'None'})")
    logger.info(f" - Overlay Scale & Position        : scale={args.image_scale*100:.1f}%, pos_x={args.pos_x}px, pos_y={args.pos_y}px")
    logger.info(f" - Subtitle Font & Position        : font='{args.text_font}', color=Black, pos_x={args.text_pos_x}px, pos_y={args.text_pos_y}px")
    logger.info(f" - Project Ready in CapCut         : {project_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Single source of truth for Google Gemini model IDs used across the pipeline.

Verified against the live ListModels endpoint on 2026-08-11:
  * gemini-3.6-flash             -> 200 OK   (text + tagging)
  * gemini-3.1-flash-tts-preview -> 200 OK   (audio)
  * gemini-2.0-flash             -> 404 "no longer available"
  * gemini-1.5-flash             -> 404 (retired)
  * gemini-2.5-flash             -> 404 "no longer available to new users"

The retired 2.0/1.5 IDs were hardcoded in run.py and script_gen, so every LLM
script-generation call 404'd and silently fell through to the offline catalog.
Keep model IDs here only; stages import these getters.

Every ID can be overridden per-environment without touching code:
    GEMINI_TEXT_MODEL=gemini-3.5-flash
    GEMINI_TAGGING_MODEL=gemini-3.6-flash
    GEMINI_TTS_MODEL=gemini-2.5-flash-preview-tts
"""

import os
from typing import List, Optional

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_TEXT_MODEL_DEFAULT = "gemini-3.6-flash"
_TAGGING_MODEL_DEFAULT = "gemini-3.6-flash"
_TTS_MODEL_DEFAULT = "gemini-3.1-flash-tts-preview"

# Tried in order when the primary model call fails. All verified reachable.
TEXT_MODEL_FALLBACKS: List[str] = ["gemini-3.5-flash", "gemini-flash-latest"]
TTS_MODEL_FALLBACKS: List[str] = ["gemini-2.5-flash-preview-tts"]


def get_text_model() -> str:
    """Model used for script generation / rewriting (run.py, script_gen)."""
    return os.environ.get("GEMINI_TEXT_MODEL", _TEXT_MODEL_DEFAULT)


def get_tagging_model() -> str:
    """Model used for mascot pose tagging and romanization (srt_generator)."""
    return os.environ.get("GEMINI_TAGGING_MODEL", _TAGGING_MODEL_DEFAULT)


def get_tts_model() -> str:
    """Model used for voiceover synthesis (tts_generator)."""
    return os.environ.get("GEMINI_TTS_MODEL", _TTS_MODEL_DEFAULT)


def generate_content_url(model: str, api_key: str) -> str:
    """Builds the v1beta generateContent endpoint URL for a model."""
    return f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}"


def model_chain(primary: Optional[str], fallbacks: Optional[List[str]] = None) -> List[str]:
    """
    Ordered, de-duplicated list of models to attempt: the requested model first,
    then the known-good fallbacks.
    """
    chain: List[str] = []
    for m in [primary] + list(fallbacks if fallbacks is not None else TEXT_MODEL_FALLBACKS):
        if m and m not in chain:
            chain.append(m)
    return chain

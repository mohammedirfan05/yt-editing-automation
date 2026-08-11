"""
Farq Kya Playbook Validator Module.
Validates generated YouTube Shorts scripts for Farq Kya channel (Roman Urdu).
Enforces hook syntax: "Ye hai X aur ye hai Y, aakhir isme farq kya hai?"
Detects AI-slop filler and checks retention-driven playbook metrics.
"""

import re
from typing import Any, Dict, List, Tuple
from .unslop_sanitizer import UnslopSanitizer


class FarqKyaValidator:
    """Validator enforcing Playbook rules for Farq Kya channel."""

    TARGET_WPS = 2.7

    DEEPDIVE_WORD_MIN = 60
    DEEPDIVE_WORD_MAX = 85
    DEEPDIVE_HARD_MIN = 45
    DEEPDIVE_HARD_MAX = 95

    COMPILATION_WORD_MIN = 75
    COMPILATION_WORD_MAX = 95
    COMPILATION_HARD_MIN = 65
    COMPILATION_HARD_MAX = 105

    HOOK_PATTERN = r"^ye hai [^.]+? aur ye hai [^.]+?, aakhir isme farq kya hai\?"

    MISCONCEPTION_TRIGGERS = [
        "aksar log",
        "samajhte hain",
        "lekin aisa nahi",
        "ye galat hai",
        "farq yeh hai",
        "farq ye hai"
    ]

    OUTRO_TRIGGERS = [
        "follow karein",
        "follow karen",
        "subscribe karein",
        "subscribe karen",
        "follow for more"
    ]

    @classmethod
    def count_words(cls, text: str) -> int:
        clean_text = re.sub(r"[^\w\s']", " ", text)
        words = [w for w in clean_text.split() if w.strip()]
        return len(words)

    @classmethod
    def estimate_duration(cls, word_count: int, wps: float = TARGET_WPS) -> float:
        return round(word_count / wps, 2)

    @classmethod
    def validate_script(cls, script_text: str, mode: str = "deepdive") -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validates a Farq Kya script against Playbook guidelines and AI slop detection.
        """
        errors = []
        warnings = []
        metrics = {}

        if not script_text or not script_text.strip():
            return False, ["Script text cannot be empty."], {}

        text_clean = script_text.strip()
        text_lower = text_clean.lower()
        word_count = cls.count_words(text_clean)
        est_duration = cls.estimate_duration(word_count)

        metrics["word_count"] = word_count
        metrics["estimated_duration_sec"] = est_duration
        metrics["speech_pacing_wps"] = cls.TARGET_WPS
        metrics["mode"] = mode
        metrics["channel"] = "farqkya"

        # 0. AI Slop Detection (unslop check)
        slop_issues = UnslopSanitizer.detect_slop(text_clean)
        if slop_issues:
            for s_issue in slop_issues:
                warnings.append(s_issue)

        # 1. Mode Specific Word Count Checks
        if mode == "deepdive":
            if word_count < cls.DEEPDIVE_HARD_MIN:
                errors.append(f"[Word Count] Script is too short ({word_count} words). Hard minimum is {cls.DEEPDIVE_HARD_MIN}.")
            elif word_count > cls.DEEPDIVE_HARD_MAX:
                errors.append(f"[Word Count] Script is too long ({word_count} words). Hard maximum is {cls.DEEPDIVE_HARD_MAX}.")
            elif word_count < cls.DEEPDIVE_WORD_MIN or word_count > cls.DEEPDIVE_WORD_MAX:
                warnings.append(f"[Word Count] {word_count} words is outside ideal range ({cls.DEEPDIVE_WORD_MIN}-{cls.DEEPDIVE_WORD_MAX}).")

        elif mode == "compilation":
            if word_count < cls.COMPILATION_HARD_MIN:
                errors.append(f"[Word Count] Compilation script too short ({word_count} words). Hard minimum is {cls.COMPILATION_HARD_MIN}.")
            elif word_count > cls.COMPILATION_HARD_MAX:
                errors.append(f"[Word Count] Compilation script too long ({word_count} words). Hard maximum is {cls.COMPILATION_HARD_MAX}.")
            elif word_count < cls.COMPILATION_WORD_MIN or word_count > cls.COMPILATION_WORD_MAX:
                warnings.append(f"[Word Count] {word_count} words is outside ideal range ({cls.COMPILATION_WORD_MIN}-{cls.COMPILATION_WORD_MAX}).")

        # 2. Hook Check
        if mode == "deepdive":
            match = re.search(cls.HOOK_PATTERN, text_lower)
            if not match:
                errors.append("[Hook] Must start immediately with 'Ye hai X aur ye hai Y, aakhir isme farq kya hai?' without preamble.")
            elif match.start() != 0:
                errors.append("[Hook] Meta-commentary or preamble detected before hook. Hook must start on line 1.")
        elif mode == "compilation":
            hook_matches = list(re.finditer(r"ye hai [^.]+? aur ye hai [^.]+?, aakhir isme farq kya hai\?", text_lower))
            metrics["hook_count"] = len(hook_matches)
            if len(hook_matches) != 3:
                errors.append(f"[Hook] Compilation mode requires exactly 3 repeated hook blocks. Found {len(hook_matches)}.")

        # 3. Misconception Check
        if mode == "deepdive":
            has_misconception = any(trig in text_lower for trig in cls.MISCONCEPTION_TRIGGERS)
            metrics["has_misconception_shatter"] = has_misconception
            if not has_misconception:
                warnings.append("[Misconception] Script missing explicit misconception shatter in Roman Urdu.")

        # 4. Outro Check
        has_outro = any(trig in text_lower for trig in cls.OUTRO_TRIGGERS)
        metrics["has_outro_cta"] = has_outro
        if not has_outro:
            warnings.append("[Outro] Script missing standard Roman Urdu CTA ('Mazeed videos ke liye follow karein.').")

        is_compliant = len(errors) == 0
        all_issues = errors + warnings

        metrics["is_compliant"] = is_compliant
        metrics["errors"] = errors
        metrics["warnings"] = warnings

        return is_compliant, all_issues, metrics

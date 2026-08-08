"""
Playbook Validator Module.
Validates generated YouTube Shorts scripts against strict guidelines from docs/viral_shorts_playbook.md.
"""

import re
from typing import Any, Dict, List, Tuple


class PlaybookValidator:
    """Validator enforcing rules from docs/viral_shorts_playbook.md."""

    # Target metrics
    TARGET_WPS = 2.7  # Words per second target speech pacing

    # Deepdive boundaries
    DEEPDIVE_WORD_MIN = 75
    DEEPDIVE_WORD_MAX = 85
    DEEPDIVE_HARD_MIN = 65
    DEEPDIVE_HARD_MAX = 90

    # Compilation boundaries
    COMPILATION_WORD_MIN = 90
    COMPILATION_WORD_MAX = 95
    COMPILATION_HARD_MIN = 80
    COMPILATION_HARD_MAX = 100

    HOOK_PATTERN = r"^this is [^.]+?\. this is [^.]+?\. so what'?s the difference\?"

    MISCONCEPTION_TRIGGERS = [
        "most people think",
        "most fans think",
        "everyone thinks",
        "they're not",
        "they don't",
        "he's not",
        "she's not",
        "that's wrong",
        "not even close"
    ]

    OUTRO_TRIGGERS = [
        "follow for more",
        "subscribe for more",
        "follow so you don't miss it"
    ]

    @classmethod
    def count_words(cls, text: str) -> int:
        """Counts spoken words in script text."""
        # Clean punctuation for accurate word count
        clean_text = re.sub(r"[^\w\s']", " ", text)
        words = [w for w in clean_text.split() if w.strip()]
        return len(words)

    @classmethod
    def estimate_duration(cls, word_count: int, wps: float = TARGET_WPS) -> float:
        """Estimates spoken audio duration in seconds."""
        return round(word_count / wps, 2)

    @classmethod
    def validate_script(cls, script_text: str, mode: str = "deepdive") -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validates a script against Playbook guidelines.

        Returns:
            (is_compliant, list_of_errors_or_warnings, metrics_dict)
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
                errors.append("[Hook] Must start immediately with 'This is X. This is Y. So what's the difference?' without preamble.")
            elif match.start() != 0:
                errors.append("[Hook] Meta-commentary or preamble detected before hook. Hook must start on line 1.")
        elif mode == "compilation":
            hook_matches = list(re.finditer(r"this is [^.]+?\. this is [^.]+?\. so what'?s the difference\?", text_lower))
            metrics["hook_count"] = len(hook_matches)
            if len(hook_matches) != 3:
                errors.append(f"[Hook] Compilation mode requires exactly 3 repeated hook blocks. Found {len(hook_matches)}.")

        # 3. Misconception Check (for Deepdive)
        if mode == "deepdive":
            has_misconception = any(trig in text_lower for trig in cls.MISCONCEPTION_TRIGGERS)
            metrics["has_misconception_shatter"] = has_misconception
            if not has_misconception:
                warnings.append("[Misconception] Script missing explicit misconception shatter ('Most people think... They're not').")

        # 4. Outro Check
        has_outro = any(trig in text_lower for trig in cls.OUTRO_TRIGGERS)
        metrics["has_outro_cta"] = has_outro
        if not has_outro:
            warnings.append("[Outro] Script missing standard CTA ('Follow for more.').")

        # 5. Anti-Pattern Checks
        anti_preambles = ["everyone is talking about", "in this video", "welcome back", "did you know"]
        for ap in anti_preambles:
            if ap in text_lower[:50]:
                errors.append(f"[Anti-Pattern] Found prohibited intro preamble: '{ap}'.")

        is_compliant = len(errors) == 0
        all_issues = errors + warnings

        metrics["is_compliant"] = is_compliant
        metrics["errors"] = errors
        metrics["warnings"] = warnings

        return is_compliant, all_issues, metrics

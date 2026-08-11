"""
Unslop Text Sanitizer Module.
Applies unslop CLI deterministic post-processing and custom AI-slop pattern cleaning
for Roman Urdu and English YouTube Shorts scripts.
"""

import re
import subprocess
import shutil
from typing import List, Tuple


class UnslopSanitizer:
    """Sanitizes AI-generated text by removing AI writing patterns, clichés, and meta preambles."""

    # Roman Urdu & English AI slop patterns to strip/normalize
    SLOP_PATTERNS: List[Tuple[str, str]] = [
        # Preambles & Meta Filler
        (r"^(?:aaj ki video mein|in this video|welcome back|hello guys|doston)\b,?\s*", ""),
        (r"\b(?:aayein dekhte hain|let's dive in|let's explore|aayein samajhte hain)\b,?\s*", ""),
        (r"\b(?:waziya taur par|clearly|it is important to note that|as we all know)\b,?\s*", ""),
        (r"\b(?:is video mein hum|today we will discuss)\b,?\s*", ""),

        # AI Cliche Words & Phrases
        (r"\bdelve into\b", "explore"),
        (r"\btapestry\b", "structure"),
        (r"\btestament\b", "proof"),
        (r"\bbeacon\b", "guide"),
        (r"\bfurthermore\b", "also"),
        (r"\bmoreover\b", "also"),
        (r"\boverall\b", "in short"),
    ]

    SLOP_WARNING_KEYWORDS = [
        "delve", "tapestry", "testament", "beacon", "furthermore", "moreover",
        "aaj ki video", "welcome back", "aayein dekhte", "is video mein", "let's dive"
    ]

    @classmethod
    def sanitize(cls, text: str, use_cli: bool = True) -> str:
        """
        Runs unslop CLI (deterministic mode) and rule-based AI slop cleaning on input text.
        """
        if not text or not text.strip():
            return ""

        cleaned = text.strip()

        # Step 1: Run unslop CLI if available
        if use_cli and shutil.which("unslop"):
            try:
                proc = subprocess.run(
                    ["unslop", "--stdin", "--deterministic"],
                    input=cleaned,
                    text=True,
                    capture_output=True,
                    timeout=10
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    cleaned = proc.stdout.strip()
            except Exception:
                pass

        # Step 2: Custom Regex Cleaning for Roman Urdu & English Short Scripts
        for pattern, replacement in cls.SLOP_PATTERNS:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    @classmethod
    def detect_slop(cls, text: str) -> List[str]:
        """
        Detects AI slop keywords or forbidden meta-commentary in text.
        Returns a list of detected issues.
        """
        issues = []
        text_lower = text.lower()

        for kw in cls.SLOP_WARNING_KEYWORDS:
            if kw in text_lower:
                issues.append(f"[AI Slop Detected] Found cliché/filler keyword: '{kw}'")

        return issues

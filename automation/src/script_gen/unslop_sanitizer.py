"""
Deterministic text sanitizer for generated scripts.

Scope is deliberately narrow. This module only makes changes that cannot alter
meaning: normalising characters a voice model cannot speak, stripping meta
preambles, collapsing a repeated entity name, and de-stacking sign-offs.

Phrase-level slop ("while" as every pivot, a payoff that restates the mechanism,
a copy-pasted hook) is NOT rewritten here. Regex cannot rewrite those without
mangling the sentence, so they are reported by the validators and fixed by the
model in the generator's repair pass.

Also fixes a live bug: piping Roman Urdu or any non-ASCII text through the
`unslop` CLI on Windows produced mojibake, because subprocess inherited the
cp1252 console codec. Verified before the fix — an em dash came back as `?"`.
That corrupted text was being written straight into the TTS input.
"""

import re
import shutil
import subprocess
from typing import List, Optional, Sequence, Tuple

from .slop_rules import SlopEngine, SlopRule

# Meta-commentary that can be cut without touching the sentence around it.
_PREAMBLE_PATTERNS: List[str] = [
    r"^(?:in this video|in today'?s video|welcome back|hey guys|hi guys|"
    r"hello everyone|what'?s up guys)\b[,:]?\s*",
    r"^(?:aaj ki video mein|is video mein hum|is video mein aap|salam doston|"
    r"assalam ?o ?alaikum(?: doston)?|doston)\b[,:]?\s*",
    r"^(?:let'?s dive in|let'?s get into it|let'?s explore|"
    r"aayein dekhte hain|aayein samajhte hain|chaliye shuru karein)\b[,:]?\s*",
    r"^(?:okay|ok|alright|so),?\s+(?=[a-z])",
    r"^(?:script|voiceover|narration)\s*:\s*",
]

# Character-level fixes. Order matters: emphasis markers go before punctuation.
_CHAR_FIXES: List[Tuple[str, str]] = [
    (r"\*\*([^*]+)\*\*", r"\1"),          # markdown bold
    (r"\*([^*]+)\*", r"\1"),              # markdown italics
    (r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1"),  # underscore emphasis
    (r"\*+", " "),                         # stray asterisks
    (r"[‘’‛]", "'"),
    (r"[“”„]", '"'),
    (r"\s*[—–]\s*", ". "),                # em/en dash becomes a spoken stop
    (r"\s*(?:\.{3,}|…)\s*", ". "),        # ellipsis becomes a spoken stop
    (r"\s*\([^)]*\)", ""),                # asides never get read aloud well
    (r"\s*\[[^\]]*\]", ""),
    (r"[«»]", ""),
    (r" ", " "),
    (r"[​-‏  ]", ""),
    (r"!{2,}", "!"),
    (r"\?{2,}", "?"),
    (r"\s+([.,?!])", r"\1"),
    (r"([.?!]){2,}", r"\1"),
]

# Replacement / mojibake markers. If unslop introduces any of these we discard
# its output rather than shipping corrupted text to the voice model.
_CORRUPTION_RE = re.compile(r"[�]|â€|Ã[\x80-\xbf]")


class UnslopSanitizer:
    """Deterministic, meaning-preserving cleanup for generated script text."""

    @staticmethod
    def normalize_speech_chars(text: str) -> str:
        out = text
        for pattern, replacement in _CHAR_FIXES:
            out = re.sub(pattern, replacement, out)
        return re.sub(r"\s+", " ", out).strip()

    @staticmethod
    def strip_preambles(text: str) -> str:
        out = text.strip()
        for _ in range(3):  # models sometimes stack two preambles
            before = out
            for pattern in _PREAMBLE_PATTERNS:
                out = re.sub(pattern, "", out, flags=re.IGNORECASE).lstrip()
            if out == before:
                break
        return out[:1].upper() + out[1:] if out else out

    @staticmethod
    def collapse_duplicate_names(text: str) -> str:
        """
        Fixes 'Uru Metal Uru is a mystical metal' and 'Symbiote Spider-Man The
        Symbiote suit provides', both produced by the old template renderer.
        """
        out = re.sub(r"\b([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+){0,3})\s+(?:The\s+)?\1\b",
                     r"\1", text)

        def _drop_echo(m: re.Match) -> str:
            phrase, nxt = m.group(1), m.group(2)
            return phrase if nxt in phrase.split() else m.group(0)

        return re.sub(r"\b([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+){1,3})\s+([A-Z][\w'-]+)\b",
                      _drop_echo, out)

    @staticmethod
    def dedupe_signoff(text: str, cta_bank: Optional[Sequence[str]] = None) -> str:
        """
        Keeps one sign-off. Models frequently stack two ("Follow for more.
        Subscribe for more!"), which reads as a bolted-on CTA.
        """
        sents = SlopEngine.sentences(text)
        if len(sents) < 3:
            return text
        cta_re = re.compile(
            r"\b(follow|subscribe|comment|share|like)\b.*\b(more|next|below|"
            r"karein|karen|kariye|lein|pohanchayein)\b|^(?:follow|subscribe)\b",
            re.IGNORECASE)
        tail_ctas = [i for i in range(len(sents) - 1, max(len(sents) - 4, 0) - 1, -1)
                     if cta_re.search(sents[i])]
        if len(tail_ctas) > 1:
            keep = min(tail_ctas)          # the first of the stacked sign-offs
            sents = sents[:keep + 1]
        return " ".join(sents)

    @classmethod
    def run_unslop_cli(cls, text: str) -> str:
        """
        Runs the unslop CLI in deterministic mode with an explicit UTF-8 pipe.
        Falls back to the input unchanged on any failure, on corrupted output, or
        when the tool eats more than a quarter of the script.
        """
        if not shutil.which("unslop"):
            return text
        try:
            proc = subprocess.run(
                ["unslop", "--stdin", "--deterministic"],
                input=text,
                capture_output=True,
                timeout=15,
                encoding="utf-8",
                errors="strict",
            )
        except Exception:
            return text
        if proc.returncode != 0:
            return text
        out = (proc.stdout or "").strip()
        if not out or _CORRUPTION_RE.search(out):
            return text
        if len(out.split()) < 0.75 * len(text.split()):
            return text
        return out

    @classmethod
    def sanitize(
        cls,
        text: str,
        use_cli: bool = True,
        cta_bank: Optional[Sequence[str]] = None,
    ) -> str:
        """Full deterministic pass. Safe to run more than once."""
        if not text or not text.strip():
            return ""

        cleaned = cls.strip_preambles(text.strip())
        cleaned = cls.normalize_speech_chars(cleaned)
        cleaned = cls.collapse_duplicate_names(cleaned)

        if use_cli:
            candidate = cls.run_unslop_cli(cleaned)
            # unslop is prose-oriented and can reintroduce characters we just
            # normalised, so re-run the character pass over its output.
            cleaned = cls.normalize_speech_chars(candidate)

        cleaned = cls.dedupe_signoff(cleaned, cta_bank)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned and cleaned[-1] not in ".?!":
            cleaned += "."
        return cleaned

    @classmethod
    def detect_slop(cls, text: str, rules: Optional[Sequence[SlopRule]] = None) -> List[str]:
        """
        Reports phrase-level slop. Pass the channel's rule pack; with no rules it
        falls back to the handful of patterns that are slop in any language.
        """
        if rules is None:
            rules = _UNIVERSAL_RULES
        findings = SlopEngine.scan_rules(text, rules)
        findings += SlopEngine.scan_speech_safety(text)
        return [str(f) for f in findings]


# Cross-language fallbacks, used only when no channel pack is supplied.
_UNIVERSAL_RULES: List[SlopRule] = [
    SlopRule("universal.llm_vocab",
             r"\b(?:delve|tapestry|testament|beacon|furthermore|moreover)\b",
             "LLM register vocabulary", "warn"),
    SlopRule("universal.preamble",
             r"\b(?:in this video|welcome back|aaj ki video mein|let'?s dive)\b",
             "meta preamble", "error"),
]

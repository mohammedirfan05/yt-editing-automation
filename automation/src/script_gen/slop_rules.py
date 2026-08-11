"""
AI-slop detection machinery, shared by both channels but owning no channel rules.

Two things are deliberately kept apart:

  * SlopEngine     - channel-agnostic measurement. Regex counting, opener
                     fingerprints, n-gram overlap, sentence rhythm. Knows
                     nothing about English or Roman Urdu.
  * Rule packs     - live in dontmix_style.py and farqkya_style.py. Each channel
                     owns its own banned phrases, connective caps, hook
                     archetypes and CTA bank. Editing one never touches the
                     other.

Every threshold here was calibrated against the 56 scripts in
config/content_tracker.json. Run `python audit_scripts.py` to re-measure.
"""

import re
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

_WORD_RE = re.compile(r"[a-z0-9']+")
_SENT_SPLIT_RE = re.compile(r"(?<=[.?!])\s+")

# Characters that must never reach TTS or burned-in captions. The voice model
# reads them out or stalls on them, and unslop's Windows pipe mangles them.
SPEECH_UNSAFE = {
    "asterisk_emphasis": r"\*+",
    "underscore_emphasis": r"(?<!\w)_[^_]+_(?!\w)",
    "em_dash": r"[—–]",
    "ellipsis": r"\.{3,}|…",
    "smart_quote": r"[‘’“”]",
    "mojibake": r"[�ï¿½]|â",
    "markdown_bold": r"__+",
    "parenthetical": r"\([^)]*\)",
    "bracket_note": r"\[[^\]]*\]",
}


@dataclass(frozen=True)
class SlopRule:
    """One measurable slop pattern. `pattern` is a lowercase-target regex."""

    id: str
    pattern: str
    label: str
    severity: str = "warn"      # "error" blocks the script; "warn" is advisory
    max_allowed: int = 0        # occurrences tolerated before it counts
    hint: str = ""              # shown to the model when repairing

    def count(self, lowered: str) -> int:
        return len(re.findall(self.pattern, lowered))


@dataclass(frozen=True)
class HookArchetype:
    """
    One opener shape. The generator assigns archetypes round-robin so no two
    consecutive scripts on a channel open the same way, and the validator
    accepts any archetype in the pack instead of one hardcoded sentence.
    """

    id: str
    name: str
    detect: str                 # regex recognising this opener (lowercased text)
    brief: str                  # instruction handed to the model
    example: str                # concrete gold-standard line


@dataclass
class StyleRules:
    """A channel's complete slop rule pack."""

    channel: str
    banned: List[SlopRule] = field(default_factory=list)
    tics: List[SlopRule] = field(default_factory=list)
    hooks: List[HookArchetype] = field(default_factory=list)
    cta_bank: List[str] = field(default_factory=list)
    stopwords: frozenset = frozenset()
    # Rhythm envelope: robotic scripts have near-identical sentence lengths.
    min_sentence_stdev: float = 2.6
    max_mean_sentence_words: float = 17.0
    max_sentence_words: int = 26
    # How many recent scripts a new one is checked against for template reuse.
    reuse_window: int = 6
    max_body_ngram_overlap: float = 0.30
    # Payoff echo is measured on 3-grams, not bag-of-words: a payoff that flips
    # the relation ("har Rasool Nabi hota hai, magar har Nabi Rasool nahi")
    # legitimately reuses the same nouns, while a payoff that merely restates the
    # mechanism reuses whole phrases.
    max_payoff_echo: float = 0.35

    def hook_by_id(self, hook_id: str) -> Optional[HookArchetype]:
        return next((h for h in self.hooks if h.id == hook_id), None)


@dataclass
class Finding:
    """One detected problem. `severity` decides whether it blocks the script."""

    code: str
    severity: str
    message: str
    count: int = 1

    def __str__(self) -> str:
        tag = "ERROR" if self.severity == "error" else "warn"
        return f"[{tag}] {self.code}: {self.message}"


class SlopEngine:
    """Channel-agnostic text measurement. All methods are pure."""

    @staticmethod
    def words(text: str) -> List[str]:
        return _WORD_RE.findall(text.lower())

    @staticmethod
    def count_words(text: str) -> int:
        return len(SlopEngine.words(text))

    @staticmethod
    def sentences(text: str) -> List[str]:
        parts = _SENT_SPLIT_RE.split(text.strip())
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def content_words(text: str, stopwords: frozenset) -> List[str]:
        return [w for w in SlopEngine.words(text) if w not in stopwords and len(w) > 2]

    @staticmethod
    def opener_fingerprint(text: str, n: int = 7) -> str:
        """First n words, normalised. Identical fingerprints = copy-pasted hook."""
        return " ".join(SlopEngine.words(text)[:n])

    @staticmethod
    def ngrams(text: str, n: int = 4) -> set:
        w = SlopEngine.words(text)
        return {tuple(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}

    @staticmethod
    def ngram_overlap(a: str, b: str, n: int = 4) -> float:
        """Fraction of a's n-grams also present in b. 1.0 = a is a copy of b."""
        ga, gb = SlopEngine.ngrams(a, n), SlopEngine.ngrams(b, n)
        if not ga:
            return 0.0
        return len(ga & gb) / len(ga)

    @staticmethod
    def content_overlap(a: str, b: str, stopwords: frozenset) -> float:
        """Fraction of a's content words that also appear in b."""
        ca = SlopEngine.content_words(a, stopwords)
        cb = set(SlopEngine.content_words(b, stopwords))
        if not ca:
            return 0.0
        return sum(1 for w in ca if w in cb) / len(ca)

    @staticmethod
    def rhythm(text: str) -> Dict[str, float]:
        """Sentence-length spread. Uniform lengths read as list-robot prose."""
        lens = [len(s.split()) for s in SlopEngine.sentences(text)]
        if not lens:
            return {"count": 0, "stdev": 0.0, "mean": 0.0, "max": 0}
        return {
            "count": len(lens),
            "stdev": round(statistics.pstdev(lens), 2) if len(lens) > 1 else 0.0,
            "mean": round(statistics.fmean(lens), 2),
            "max": max(lens),
        }

    @staticmethod
    def orphan_fragments(text: str) -> List[str]:
        """
        Single-word sentences that are not the closing line.

        A one-word beat can be a great payoff ("Nothing."), but mid-script it is
        almost always debris: a stray entity label the model emitted before
        starting the real sentence, as in "...for totally different reasons.
        Obsidian. Dragonglass shatters White Walkers because...". Two-word
        elliptical lines ("Six limbs.") are deliberate and stay legal.
        """
        sents = SlopEngine.sentences(text)
        return [s for s in sents[:-1] if len(SlopEngine.words(s)) == 1]

    @staticmethod
    def scan_rules(text: str, rules: Sequence[SlopRule]) -> List[Finding]:
        lowered = text.lower()
        out: List[Finding] = []
        for rule in rules:
            n = rule.count(lowered)
            if n > rule.max_allowed:
                detail = f"{rule.label} (found {n}x, max {rule.max_allowed})"
                if rule.hint:
                    detail += f" — {rule.hint}"
                out.append(Finding(rule.id, rule.severity, detail, n))
        return out

    @staticmethod
    def scan_speech_safety(text: str) -> List[Finding]:
        """
        Characters that break TTS/caption rendering. These are format bugs, not
        style opinions, so they are errors on every channel.
        """
        out: List[Finding] = []
        for name, pattern in SPEECH_UNSAFE.items():
            hits = re.findall(pattern, text)
            if hits:
                out.append(Finding(
                    f"speech_unsafe.{name}",
                    "error",
                    f"{len(hits)} occurrence(s) of {name} reach the TTS text: {hits[:3]}",
                    len(hits),
                ))
        return out

    @staticmethod
    def strip_cta(text: str, cta_bank: Sequence[str]) -> str:
        """Removes a known sign-off so body comparisons ignore the shared CTA."""
        out = text.strip()
        lowered = out.lower()
        for cta in sorted(cta_bank, key=len, reverse=True):
            c = cta.lower().strip()
            if c and lowered.endswith(c):
                return out[: len(out) - len(c)].strip()
        # Fall back to dropping the final sentence when it is CTA-shaped.
        sents = SlopEngine.sentences(out)
        if len(sents) > 2 and re.search(r"\b(follow|subscribe|comment|karein|karen|kariye)\b",
                                        sents[-1], re.IGNORECASE):
            return " ".join(sents[:-1]).strip()
        return out

    @staticmethod
    def body_after_hook(text: str, hooks: Sequence[HookArchetype]) -> str:
        """
        Text with the opener removed. Hook wording is intentionally shared
        within an archetype, so template-reuse scoring must ignore it.
        """
        lowered = text.lower()
        best_end = 0
        for h in hooks:
            m = re.match(h.detect, lowered)
            if m and m.end() > best_end:
                best_end = m.end()
        if best_end:
            return text[best_end:].strip()
        sents = SlopEngine.sentences(text)
        return " ".join(sents[1:]).strip() if len(sents) > 1 else text

    @staticmethod
    def payoff_sentence(text: str, cta_bank: Sequence[str]) -> str:
        """The last real sentence before the sign-off — where the video lands."""
        body = SlopEngine.strip_cta(text, cta_bank)
        sents = SlopEngine.sentences(body)
        return sents[-1] if sents else ""

    @staticmethod
    def detect_hook(text: str, hooks: Sequence[HookArchetype]) -> Optional[HookArchetype]:
        lowered = text.lower().strip()
        for h in hooks:
            if re.match(h.detect, lowered):
                return h
        return None

    @staticmethod
    def duplicate_entity_name(text: str) -> List[str]:
        """
        Catches the template bug that produced 'Uru Metal Uru is a mystical...'
        and 'Symbiote Spider-Man The Symbiote suit...' — an entity name emitted
        twice back to back because the render helper only compared first words.
        """
        out = []
        for m in re.finditer(r"\b([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+){0,3})\s+(?:The\s+)?\1\b", text):
            out.append(m.group(0))
        for m in re.finditer(r"\b([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+){1,3})\s+([A-Z][\w'-]+)\b", text):
            phrase, nxt = m.group(1), m.group(2)
            if nxt in phrase.split():
                out.append(m.group(0))
        return out

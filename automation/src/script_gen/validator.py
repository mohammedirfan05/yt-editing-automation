"""
Validator for dontmixthis (English) scripts.

Rewritten from a single-template checker into a slop scanner.

What changed and why:

  * The old validator hard-required one opener,
    `"This is X. This is Y. So what's the difference?"`. Any other hook was a
    blocking error, so the channel could not physically vary its hooks — three of
    the best published scripts ("99% of people get this wrong...", "Everyone's
    talking about Dr. Doom...") would have been rejected. Now ANY archetype in
    DONTMIXTHIS_RULES.hooks passes, and reusing the *same* opener wording as a
    recent script is what fails.
  * The old word floor of 65 rejected the tightest published script (58 words).
    Padding to clear a floor is exactly the "written to hit a word count" problem,
    so the hard floor drops to 45 and the ideal band is 55-85.
  * "Most people think" was a *required* phrase (missing it raised a warning).
    It appeared in 22 of 37 audited scripts. It is now a capped tic.
  * New blocking checks: speech-unsafe characters reaching TTS, connective tic
    caps, entity-name stutter, a payoff that only restates the mechanism, n-gram
    body overlap against recent scripts, duplicate opener fingerprints, and flat
    sentence rhythm.

Roman Urdu lives in farqkya_validator.py and shares no rules with this file.
"""

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .dontmix_style import CTA_BANK, DONTMIXTHIS_RULES
from .slop_rules import Finding, SlopEngine
from .unslop_sanitizer import UnslopSanitizer


class PlaybookValidator:
    """Scores a dontmixthis script against the channel's slop rule pack."""

    RULES = DONTMIXTHIS_RULES
    TARGET_WPS = 2.7

    # Ideal band is advisory; hard bounds block. Tight beats padded.
    DEEPDIVE_WORD_MIN = 55
    DEEPDIVE_WORD_MAX = 85
    DEEPDIVE_HARD_MIN = 45
    DEEPDIVE_HARD_MAX = 95

    COMPILATION_WORD_MIN = 80
    COMPILATION_WORD_MAX = 100
    COMPILATION_HARD_MIN = 70
    COMPILATION_HARD_MAX = 112

    @classmethod
    def count_words(cls, text: str) -> int:
        return len([w for w in re.sub(r"[^\w\s']", " ", text).split() if w.strip()])

    @classmethod
    def estimate_duration(cls, word_count: int, wps: float = TARGET_WPS) -> float:
        return round(word_count / wps, 2)

    # ---------------------------------------------------------------- checks

    @classmethod
    def _check_length(cls, mode: str, wc: int) -> List[Finding]:
        if mode == "compilation":
            hard_lo, hard_hi = cls.COMPILATION_HARD_MIN, cls.COMPILATION_HARD_MAX
            lo, hi = cls.COMPILATION_WORD_MIN, cls.COMPILATION_WORD_MAX
        else:
            hard_lo, hard_hi = cls.DEEPDIVE_HARD_MIN, cls.DEEPDIVE_HARD_MAX
            lo, hi = cls.DEEPDIVE_WORD_MIN, cls.DEEPDIVE_WORD_MAX
        if wc < hard_lo:
            return [Finding("length.too_short", "error",
                            f"{wc} words is under the hard floor of {hard_lo}.")]
        if wc > hard_hi:
            return [Finding("length.too_long", "error",
                            f"{wc} words is over the hard ceiling of {hard_hi}. "
                            "Cut a sentence, do not compress every sentence.")]
        if wc < lo or wc > hi:
            return [Finding("length.outside_ideal", "warn",
                            f"{wc} words is outside the ideal {lo}-{hi} band.")]
        return []

    @classmethod
    def _check_hook(cls, text: str, mode: str, expected_hook: Optional[str],
                    recent_openers: Sequence[str], metrics: Dict[str, Any]) -> List[Finding]:
        out: List[Finding] = []
        hook = SlopEngine.detect_hook(text, cls.RULES.hooks)
        metrics["hook_id"] = hook.id if hook else None
        fingerprint = SlopEngine.opener_fingerprint(text)
        metrics["opener_fingerprint"] = fingerprint

        if hook is None:
            out.append(Finding("hook.unrecognised", "error",
                               "Opener does not land as a hook. First sentence must "
                               "make a claim, not set up the video."))
        elif expected_hook and hook.id != expected_hook and hook.id != "free_open":
            out.append(Finding("hook.off_plan", "warn",
                               f"Planned archetype was {expected_hook}, got {hook.id}. "
                               "Fine unless the rotation is drifting to one shape."))

        for prev in recent_openers:
            prev_fp = " ".join(SlopEngine.words(prev)[:7])
            if not prev_fp or not fingerprint:
                continue
            if prev_fp == fingerprint:
                out.append(Finding("hook.duplicate_opener", "error",
                                   f"Opener is word-for-word a recent script: '{prev_fp}'."))
                break
            if SlopEngine.ngram_overlap(fingerprint, prev_fp, n=4) >= 0.75:
                out.append(Finding("hook.near_duplicate_opener", "error",
                                   f"Opener is a near-copy of a recent script: '{prev_fp}'."))
                break

        if mode == "compilation":
            n = len(re.findall(r"\bthis is\b", text.lower()))
            metrics["hook_count"] = n
            if n < 3:
                out.append(Finding("hook.compilation_segments", "warn",
                                   f"Compilation names only {n} pairs with 'this is'. "
                                   "Three segments should each be introduced."))
        return out

    @classmethod
    def _check_payoff(cls, text: str, metrics: Dict[str, Any]) -> List[Finding]:
        """
        The last line must add the twist, not summarise the mechanism.

        Measured on 3-grams. A bag-of-words measure punished good payoffs that
        flip the relation between the same two nouns ("Count the limbs, not the
        name."), while phrase overlap catches the real failure: the payoff
        reciting the mechanism sentence back.
        """
        body = SlopEngine.strip_cta(text, cls.RULES.cta_bank)
        sents = SlopEngine.sentences(body)
        if len(sents) < 3:
            return []
        payoff, setup = sents[-1], " ".join(sents[:-1])
        echo = SlopEngine.ngram_overlap(payoff, setup, n=3)
        word_echo = SlopEngine.content_overlap(payoff, setup, cls.RULES.stopwords)
        metrics["payoff"] = payoff
        metrics["payoff_echo"] = round(echo, 2)
        metrics["payoff_word_echo"] = round(word_echo, 2)
        out: List[Finding] = []
        if echo > cls.RULES.max_payoff_echo:
            out.append(Finding("payoff.echo", "error",
                               f"Payoff repeats {int(echo * 100)}% of the setup's phrases, "
                               "so it explains the point again instead of landing it. "
                               "Give the last line new information."))
        elif word_echo > 0.85:
            out.append(Finding("payoff.restates", "warn",
                               f"Payoff introduces no new content words "
                               f"({int(word_echo * 100)}% reused). Check it lands a twist."))
        if len(payoff.split()) < 4:
            out.append(Finding("payoff.stub", "warn",
                               f"Payoff is {len(payoff.split())} words. Reads clipped."))
        return out

    @classmethod
    def _check_reuse(cls, text: str, recent_scripts: Sequence[str],
                     metrics: Dict[str, Any]) -> List[Finding]:
        """Same skeleton, different nouns — the template-reuse smell."""
        if not recent_scripts:
            return []
        body = SlopEngine.body_after_hook(
            SlopEngine.strip_cta(text, cls.RULES.cta_bank), cls.RULES.hooks)
        worst, worst_score = "", 0.0
        for prev in recent_scripts[: cls.RULES.reuse_window]:
            prev_body = SlopEngine.body_after_hook(
                SlopEngine.strip_cta(prev, cls.RULES.cta_bank), cls.RULES.hooks)
            score = SlopEngine.ngram_overlap(body, prev_body, n=4)
            if score > worst_score:
                worst, worst_score = prev_body, score
        metrics["max_body_overlap"] = round(worst_score, 2)
        if worst_score > cls.RULES.max_body_ngram_overlap:
            return [Finding("reuse.body_template", "error",
                            f"{int(worst_score * 100)}% four-word-phrase overlap with a "
                            f"recent script. Same sentence skeleton, swapped nouns. "
                            f"Overlapping script starts: '{worst[:60]}'")]
        return []

    @classmethod
    def _check_rhythm(cls, text: str, metrics: Dict[str, Any]) -> List[Finding]:
        r = SlopEngine.rhythm(text)
        metrics["rhythm"] = r
        out: List[Finding] = []
        if r["count"] >= 4 and r["stdev"] < cls.RULES.min_sentence_stdev:
            out.append(Finding("rhythm.flat", "error",
                               f"Sentence lengths are near-identical (stdev {r['stdev']}, "
                               f"need >{cls.RULES.min_sentence_stdev}). Reads as a list "
                               "being recited. Mix a 4-word line with a 20-word one."))
        if r["mean"] > cls.RULES.max_mean_sentence_words:
            out.append(Finding("rhythm.long_winded", "warn",
                               f"Mean sentence is {r['mean']} words "
                               f"(max {cls.RULES.max_mean_sentence_words})."))
        if r["max"] > cls.RULES.max_sentence_words:
            out.append(Finding("rhythm.runaway_sentence", "error",
                               f"Longest sentence is {r['max']} words "
                               f"(max {cls.RULES.max_sentence_words}). Nobody says that "
                               "much without breathing."))
        for frag in SlopEngine.orphan_fragments(text):
            out.append(Finding("rhythm.orphan_fragment", "error",
                               f"'{frag}' is a one-word sentence in the middle of the "
                               "script. Fold the label into the sentence that follows."))
        return out

    @classmethod
    def _match_bank_cta(cls, text: str) -> Optional[str]:
        """
        Longest bank sign-off the script actually ends with. Matched on the raw
        tail rather than the last sentence, because bank entries such as
        "Comment another pair people always mix up. I might do yours next." are
        two sentences long.
        """
        tail = text.lower().strip()
        for cta in sorted(CTA_BANK, key=len, reverse=True):
            if tail.endswith(cta.lower().strip()):
                return cta
        return None

    @classmethod
    def _check_cta(cls, text: str, expected_cta: Optional[str],
                   recent_ctas: Sequence[str], metrics: Dict[str, Any]) -> List[Finding]:
        matched = cls._match_bank_cta(text)
        sents = SlopEngine.sentences(text)
        last = matched or (sents[-1] if sents else "")
        metrics["cta"] = last
        metrics["cta_from_bank"] = bool(matched)
        lowered = last.lower().strip(" .!?")
        out: List[Finding] = []
        if not matched:
            if re.search(r"\b(follow|subscribe|comment|like|share)\b", lowered):
                out.append(Finding("cta.off_bank", "warn",
                                   f"Sign-off '{last}' is not from the rotation bank."))
            else:
                out.append(Finding("cta.missing", "warn",
                                   "No sign-off. Fine if the payoff is the last line "
                                   "by design, otherwise add one from the bank."))
        recent_norm = [c.lower().strip(" .!?") for c in recent_ctas[:3]]
        if lowered and lowered in recent_norm:
            out.append(Finding("cta.repeated", "warn",
                               f"Same sign-off as a recent script ('{last}'). Rotate it "
                               "so the outro stops feeling bolted on."))
        if expected_cta:
            want = expected_cta.lower().strip(" .!?")
            if want and want != lowered:
                out.append(Finding("cta.off_plan", "warn",
                                   f"Rotation assigned '{expected_cta}', script ends with "
                                   f"'{last}'."))
        return out

    # ------------------------------------------------------------- entrypoint

    @classmethod
    def validate_script(
        cls,
        script_text: str,
        mode: str = "deepdive",
        channel: str = "dontmixthis",
        recent_scripts: Optional[Sequence[str]] = None,
        expected_hook: Optional[str] = None,
        expected_cta: Optional[str] = None,
        recent_ctas: Optional[Sequence[str]] = None,
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Returns (is_compliant, issue_strings, metrics).

        `channel="farqkya"` is kept only so existing callers keep working; it
        forwards to the Roman Urdu validator, which owns its own rules.
        """
        if channel == "farqkya":
            from .farqkya_validator import FarqKyaValidator
            return FarqKyaValidator.validate_script(
                script_text, mode=mode, recent_scripts=recent_scripts,
                expected_hook=expected_hook, expected_cta=expected_cta,
                recent_ctas=recent_ctas)

        if not script_text or not script_text.strip():
            return False, ["Script text cannot be empty."], {}

        text = script_text.strip()
        recent_scripts = list(recent_scripts or [])
        recent_ctas = list(recent_ctas or [])
        wc = cls.count_words(text)

        metrics: Dict[str, Any] = {
            "channel": "dontmixthis",
            "mode": mode,
            "word_count": wc,
            "estimated_duration_sec": cls.estimate_duration(wc),
            "speech_pacing_wps": cls.TARGET_WPS,
        }

        findings: List[Finding] = []
        findings += SlopEngine.scan_speech_safety(text)
        findings += SlopEngine.scan_rules(text, cls.RULES.banned)
        findings += SlopEngine.scan_rules(text, cls.RULES.tics)
        findings += cls._check_length(mode, wc)
        findings += cls._check_hook(text, mode, expected_hook,
                                   [s for s in recent_scripts], metrics)
        findings += cls._check_payoff(text, metrics)
        findings += cls._check_reuse(text, recent_scripts, metrics)
        findings += cls._check_rhythm(text, metrics)
        findings += cls._check_cta(text, expected_cta, recent_ctas, metrics)

        for stutter in SlopEngine.duplicate_entity_name(text):
            findings.append(Finding("format.name_stutter", "error",
                                   f"Entity name emitted twice: '{stutter}'."))

        errors = [str(f) for f in findings if f.severity == "error"]
        warnings = [str(f) for f in findings if f.severity != "error"]
        metrics["errors"] = errors
        metrics["warnings"] = warnings
        metrics["is_compliant"] = not errors
        return not errors, errors + warnings, metrics

    @classmethod
    def repair_brief(cls, metrics: Dict[str, Any]) -> List[str]:
        """Error list plus tic warnings — what the model is asked to fix."""
        out = list(metrics.get("errors", []))
        out += [w for w in metrics.get("warnings", []) if ".tic" in w or "tic." in w]
        return out


def sanitize_for_tts(text: str) -> str:
    """Convenience wrapper so callers do not import the sanitizer separately."""
    return UnslopSanitizer.sanitize(text, cta_bank=CTA_BANK)

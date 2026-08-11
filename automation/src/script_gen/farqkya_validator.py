"""
Validator for farqkya (Roman Urdu) scripts.

Shares the measurement engine with dontmixthis but none of its rules. Every
threshold, phrase and hook here belongs to this channel only.

What changed and why:

  * The old validator hard-required the single opener
    `"Ye hai X aur ye hai Y, aakhir isme farq kya hai?"`. All five audited
    scripts opened with it because nothing else could pass. Now any archetype in
    FARQKYA_RULES.hooks is accepted, and repeating a recent script's opener is
    what fails.
  * `jabke` appeared as the contrast pivot in 5 of 5 audited scripts and
    `aksar log` as the setup in 4 of 5. Both were previously *rewarded* — the old
    "misconception shatter" check warned when `aksar log` was missing. They are
    now capped tics.
  * New: a cadence check. Roman Urdu is verb-final, so natural spoken lines end
    on a verb or auxiliary (`hota hai`, `deti hai`, `kehte hain`). Scripts
    translated out of English end on nouns and read as dubbed narration. The
    ratio is measured rather than guessed at.
  * New: digits are a blocking error (in the rule pack). The voice model reads
    "2" as English "two" in the middle of an Urdu sentence.
"""

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .farqkya_style import (
    CTA_BANK,
    FARQKYA_RULES,
    NATURAL_MARKERS,
    VERB_FINAL_TOKENS,
)
from .slop_rules import Finding, SlopEngine
from .unslop_sanitizer import UnslopSanitizer


class FarqKyaValidator:
    """Scores a farqkya script against the Roman Urdu slop rule pack."""

    RULES = FARQKYA_RULES
    TARGET_WPS = 2.7

    # Roman Urdu spends more words per idea than English, but the audited
    # scripts padded to clear a 60-word floor. Floor drops, ceiling stays tight.
    DEEPDIVE_WORD_MIN = 55
    DEEPDIVE_WORD_MAX = 85
    DEEPDIVE_HARD_MIN = 45
    DEEPDIVE_HARD_MAX = 95

    COMPILATION_WORD_MIN = 80
    COMPILATION_WORD_MAX = 100
    COMPILATION_HARD_MIN = 70
    COMPILATION_HARD_MAX = 112

    # Fraction of real sentences that must end on a verb / auxiliary.
    MIN_VERB_FINAL_RATIO = 0.45

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
                            f"{wc} alfaaz, hard minimum {hard_lo} hai.")]
        if wc > hard_hi:
            return [Finding("length.too_long", "error",
                            f"{wc} alfaaz, hard maximum {hard_hi} hai. Ek poora jumla "
                            "hatayein, har jumle ko dabaayein nahi.")]
        if wc < lo or wc > hi:
            return [Finding("length.outside_ideal", "warn",
                            f"{wc} alfaaz ideal {lo}-{hi} se bahar hai.")]
        return []

    @classmethod
    def _verb_final_ratio(cls, text: str) -> Tuple[float, List[str]]:
        """
        Sentences whose final word is a verb/auxiliary, plus the offenders.

        Sentences under six words are skipped. Spoken Urdu drops the verb in short
        elliptical lines ("Ek saal mein sirf ek baar.") and that is good style, not
        English word order, so counting them would penalise the thing we want.
        """
        offenders: List[str] = []
        hits = 0
        counted = 0
        for s in SlopEngine.sentences(text):
            words = SlopEngine.words(s)
            if len(words) < 6:
                continue
            counted += 1
            if words[-1] in VERB_FINAL_TOKENS:
                hits += 1
            else:
                offenders.append(s)
        return (hits / counted if counted else 1.0), offenders

    @classmethod
    def _check_cadence(cls, text: str, metrics: Dict[str, Any]) -> List[Finding]:
        out: List[Finding] = []
        ratio, offenders = cls._verb_final_ratio(text)
        metrics["verb_final_ratio"] = round(ratio, 2)
        if ratio < cls.MIN_VERB_FINAL_RATIO:
            sample = " | ".join(o[:55] for o in offenders[:2])
            out.append(Finding(
                "cadence.english_word_order", "error",
                f"Sirf {int(ratio * 100)}% jumle verb par khatam hote hain "
                f"(minimum {int(cls.MIN_VERB_FINAL_RATIO * 100)}%). Ye English se "
                f"translate ki hui cadence hai. Urdu jumla verb par khatam hota hai. "
                f"Misaal: {sample}"))

        lowered = text.lower()
        found = [m for m in NATURAL_MARKERS if re.search(m, lowered)]
        metrics["natural_markers"] = len(found)
        if not found:
            out.append(Finding(
                "cadence.no_spoken_particles", "error",
                "Ek bhi bol-chaal ka particle nahi (to, phir, bas, magar, ab, asal "
                "mein, dekhiye). Likhi hui tehreer lag rahi hai, boli hui baat nahi."))
        return out

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
                               "Pehla jumla hook nahi ban raha. Seedha daawa karein, "
                               "video ka taaruf na dein."))
        elif expected_hook and hook.id != expected_hook and hook.id != "free_open":
            out.append(Finding("hook.off_plan", "warn",
                               f"Plan {expected_hook} tha, mila {hook.id}."))

        for prev in recent_openers:
            prev_fp = " ".join(SlopEngine.words(prev)[:7])
            if not prev_fp or not fingerprint:
                continue
            if prev_fp == fingerprint:
                out.append(Finding("hook.duplicate_opener", "error",
                                   f"Opener bilkul pichli script jaisa hai: '{prev_fp}'."))
                break
            if SlopEngine.ngram_overlap(fingerprint, prev_fp, n=4) >= 0.75:
                out.append(Finding("hook.near_duplicate_opener", "error",
                                   f"Opener pichli script ki naqal hai: '{prev_fp}'."))
                break

        ye_hai = len(re.findall(r"\bye hai\b", text.lower()))
        metrics["hook_count"] = ye_hai
        if mode == "compilation" and ye_hai < 3:
            out.append(Finding("hook.compilation_segments", "warn",
                               f"Compilation mein sirf {ye_hai} baar jodi ka taaruf hua. "
                               "Teen segments hone chahiye."))
        elif mode == "deepdive" and ye_hai > 2:
            out.append(Finding("hook.ye_hai_overuse", "warn",
                               f"'ye hai' {ye_hai} baar aaya. Deepdive mein do se zyada "
                               "nahi chahiye."))
        return out

    @classmethod
    def _check_payoff(cls, text: str, metrics: Dict[str, Any]) -> List[Finding]:
        """
        Measured on 3-grams. The classic Urdu punchline flips the relation between
        the same two nouns ("Har Rasool Nabi hota hai, magar har Nabi Rasool nahi
        hota") and reuses every content word by design; phrase overlap catches the
        real failure, which is the payoff reciting the mechanism back.
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
                               f"Aakhri jumla setup ke {int(echo * 100)}% phrases dohra "
                               "raha hai, yaani baat sirf summarise ho rahi hai. Aakhri "
                               "line mein nai baat honi chahiye."))
        elif word_echo > 0.85:
            out.append(Finding("payoff.restates", "warn",
                               f"Payoff mein koi naya lafz nahi "
                               f"({int(word_echo * 100)}% purane alfaaz). Dekhein ke ye "
                               "baat ko palat raha hai ya sirf dohra raha hai."))
        if len(payoff.split()) < 4:
            out.append(Finding("payoff.stub", "warn",
                               f"Payoff sirf {len(payoff.split())} alfaaz ka hai."))
        return out

    @classmethod
    def _check_reuse(cls, text: str, recent_scripts: Sequence[str],
                     metrics: Dict[str, Any]) -> List[Finding]:
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
                            f"Pichli script se {int(worst_score * 100)}% phrase overlap. "
                            f"Wahi dhaancha, sirf naam badle hain: '{worst[:60]}'")]
        return []

    @classmethod
    def _check_rhythm(cls, text: str, metrics: Dict[str, Any]) -> List[Finding]:
        r = SlopEngine.rhythm(text)
        metrics["rhythm"] = r
        out: List[Finding] = []
        if r["count"] >= 4 and r["stdev"] < cls.RULES.min_sentence_stdev:
            out.append(Finding("rhythm.flat", "error",
                               f"Sab jumle barabar lambe hain (stdev {r['stdev']}, "
                               f"chahiye >{cls.RULES.min_sentence_stdev}). List parhne "
                               "jaisa lagta hai. Chhote aur lambe jumle milaayein."))
        if r["mean"] > cls.RULES.max_mean_sentence_words:
            out.append(Finding("rhythm.long_winded", "warn",
                               f"Ausat jumla {r['mean']} alfaaz "
                               f"(max {cls.RULES.max_mean_sentence_words})."))
        if r["max"] > cls.RULES.max_sentence_words:
            out.append(Finding("rhythm.runaway_sentence", "error",
                               f"Sab se lamba jumla {r['max']} alfaaz ka hai "
                               f"(max {cls.RULES.max_sentence_words}). Itna lamba jumla "
                               "ek saans mein nahi bola jaata."))
        for frag in SlopEngine.orphan_fragments(text):
            out.append(Finding("rhythm.orphan_fragment", "error",
                               f"'{frag}' beech script mein ek lafz ka jumla hai. Isey "
                               "agle jumle mein mila dein."))
        return out

    @classmethod
    def _match_bank_cta(cls, text: str) -> Optional[str]:
        """
        Longest bank sign-off the script actually ends with. Matched on the raw
        tail, not the last sentence, because entries like
        "Kya aapko pehle se pata tha? Comment karein." span two sentences.
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
            if re.search(r"\b(follow|subscribe|comment|share)\b", lowered):
                out.append(Finding("cta.off_bank", "warn",
                                   f"Sign-off '{last}' rotation bank mein nahi hai."))
            else:
                out.append(Finding("cta.missing", "warn",
                                   "Koi sign-off nahi. Payoff par khatam karna theek hai, "
                                   "warna bank se ek CTA lagayein."))
        recent_norm = [c.lower().strip(" .!?") for c in recent_ctas[:3]]
        if lowered and lowered in recent_norm:
            out.append(Finding("cta.repeated", "warn",
                               f"Pichli script wala hi sign-off hai ('{last}'). Badlein."))
        if expected_cta:
            want = expected_cta.lower().strip(" .!?")
            if want and want != lowered:
                out.append(Finding("cta.off_plan", "warn",
                                   f"Rotation ne '{expected_cta}' diya tha, script mein "
                                   f"'{last}' hai."))
        return out

    # ------------------------------------------------------------- entrypoint

    @classmethod
    def validate_script(
        cls,
        script_text: str,
        mode: str = "deepdive",
        recent_scripts: Optional[Sequence[str]] = None,
        expected_hook: Optional[str] = None,
        expected_cta: Optional[str] = None,
        recent_ctas: Optional[Sequence[str]] = None,
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Returns (is_compliant, issue_strings, metrics)."""
        if not script_text or not script_text.strip():
            return False, ["Script text cannot be empty."], {}

        text = script_text.strip()
        recent_scripts = list(recent_scripts or [])
        recent_ctas = list(recent_ctas or [])
        wc = cls.count_words(text)

        metrics: Dict[str, Any] = {
            "channel": "farqkya",
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
        findings += cls._check_cadence(text, metrics)
        findings += cls._check_hook(text, mode, expected_hook, recent_scripts, metrics)
        findings += cls._check_payoff(text, metrics)
        findings += cls._check_reuse(text, recent_scripts, metrics)
        findings += cls._check_rhythm(text, metrics)
        findings += cls._check_cta(text, expected_cta, recent_ctas, metrics)

        for stutter in SlopEngine.duplicate_entity_name(text):
            findings.append(Finding("format.name_stutter", "error",
                                    f"Naam do baar aaya: '{stutter}'."))

        errors = [str(f) for f in findings if f.severity == "error"]
        warnings = [str(f) for f in findings if f.severity != "error"]
        metrics["errors"] = errors
        metrics["warnings"] = warnings
        metrics["is_compliant"] = not errors
        return not errors, errors + warnings, metrics

    @classmethod
    def repair_brief(cls, metrics: Dict[str, Any]) -> List[str]:
        """Errors plus tic warnings — exactly what the model is asked to fix."""
        out = list(metrics.get("errors", []))
        out += [w for w in metrics.get("warnings", []) if "tic." in w]
        return out


def sanitize_for_tts(text: str) -> str:
    """Convenience wrapper so callers do not import the sanitizer separately."""
    return UnslopSanitizer.sanitize(text, cta_bank=CTA_BANK)

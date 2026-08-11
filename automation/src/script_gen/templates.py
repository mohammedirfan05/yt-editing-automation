"""
Offline template renderers for dontmixthis.

These only run when the LLM path returns nothing (no API key, all models down).
They used to be the reason the pipeline's output read as robotic: one hook, one
connective (`while`), one sign-off, every time.

Two fixes here:

  * `_prefix_entity` replaced the old `_clean_mechanism`, which compared only the
    FIRST word of the entity against the first word of the mechanism. "Uru Metal"
    + "Uru is a mystical metal" passed that check and rendered as
    "Uru Metal Uru is a mystical metal". Now the whole name is matched.
  * Hook, connective and sign-off rotate on `template_id`, so consecutive
    catalog fallbacks do not share a skeleton. The channel's own bank is the
    source of the sign-offs, so nothing here can drift from the rule pack.

Roman Urdu templates live in farqkya_templates.py. The Urdu class that used to
sit in this file is gone — it was a second copy of the same logic.
"""

import re
from typing import Any, Dict, List

from .dontmix_style import CTA_BANK

# Openers matched by different archetypes in dontmix_style.HOOKS, so the
# validator sees hook variety instead of one fingerprint.
_HOOK_FORMS = [
    "This is {a}. This is {b}. So what's the difference?",
    "Everyone treats {a} and {b} as the same thing. They are not.",
    "One of these is {a}. The other is {b}. Only one of them works the way you think.",
    "Stop mixing up {a} and {b}.",
    "There's one real difference between {a} and {b}.",
]

# `while` is capped at one use per script by the rule pack, so the connective
# rotates instead of repeating.
_CONNECTIVES = [
    ("{a}. But {b}.", None),
    ("{a}. {b}, which is the opposite.", None),
    ("Here's {a}. Now {b}.", None),
    ("{a}, while {b}.", None),
]

_COMP_CONNECTIVES = ["{a}. But {b}.", "{a}, and {b} does the reverse.", "{a}. {b}."]


def _as_sentence(text: str) -> str:
    """
    Caller-supplied fragments become real sentences.

    `concept_hook` and `punchline` come from tracker data and are sometimes
    bare fragments ("the metal myth"). Joined raw they produced run-ons such as
    "Stop mixing up Vibranium and Adamantium. the metal myth Vibranium absorbs
    ...", which reads as one 27-word sentence to the rhythm check and to TTS.
    """
    t = (text or "").strip()
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    return t if t[-1] in ".?!" else t + "."


def _prefix_entity(entity: str, mech: str) -> str:
    """
    Prepends the entity to its mechanism unless the mechanism already names it.
    Compares the full name, not just the first word — that was the bug behind
    "Uru Metal Uru is a mystical metal" and "All-Black The Necrosword All-Black".
    """
    mech = (mech or "").strip()
    if not mech:
        return entity
    ent = re.sub(r"^the\s+", "", entity or "", flags=re.IGNORECASE).strip()
    if not ent:
        return mech
    head = re.sub(r"^the\s+", "", mech, flags=re.IGNORECASE).strip()
    if head.lower().startswith(ent.lower()):
        return mech
    # Also catch the name appearing anywhere in the opening clause.
    first_clause = re.split(r"[,.]", head, maxsplit=1)[0].lower()
    if ent.lower() in first_clause:
        return mech
    return f"{entity} {mech}"


class ScriptTemplates:
    """Renders dontmixthis fallback scripts with rotating structure."""

    @staticmethod
    def render_deepdive(entity_a: str, entity_b: str, template_id: int,
                        concept_hook: str, mechanism_a: str, mechanism_b: str,
                        punchline: str) -> str:
        idx = max(0, int(template_id or 1) - 1)
        hook = _HOOK_FORMS[idx % len(_HOOK_FORMS)].format(a=entity_a, b=entity_b)
        contrast_form = _CONNECTIVES[idx % len(_CONNECTIVES)][0]
        contrast = contrast_form.format(
            a=_prefix_entity(entity_a, mechanism_a).rstrip("."),
            b=_prefix_entity(entity_b, mechanism_b).rstrip("."))
        cta = CTA_BANK[idx % len(CTA_BANK)]

        parts = [hook, _as_sentence(concept_hook), contrast,
                 _as_sentence(punchline), cta]
        return " ".join(p for p in parts if p)

    @staticmethod
    def render_compilation(pairs_data: List[Dict[str, str]]) -> str:
        blocks = []
        for i, pair in enumerate(pairs_data[:3]):
            ea = (pair.get("entity_a") or "").strip()
            eb = (pair.get("entity_b") or "").strip()
            ca = _prefix_entity(ea, pair.get("contrast_a", "")).rstrip(".")
            cb = _prefix_entity(eb, pair.get("contrast_b", "")).rstrip(".")
            hook = _HOOK_FORMS[i % len(_HOOK_FORMS)].format(a=ea, b=eb)
            body = _COMP_CONNECTIVES[i % len(_COMP_CONNECTIVES)].format(a=ca, b=cb)
            blocks.append(f"{hook} {body}")
        blocks.append(CTA_BANK[0])
        return " ".join(b for b in blocks if b)

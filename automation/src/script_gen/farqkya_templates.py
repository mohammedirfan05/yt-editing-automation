"""
Offline template renderers for farqkya (Roman Urdu).

Only used when the LLM path returns nothing. The previous version hardcoded the
exact patterns the audit flagged: one hook, `jabke` as the only contrast pivot,
`aksar log samajhte hain` as the default setup, and
"Aakhir mein ... yahi bunyadi farq hai" as the default payoff — a line that just
restates the mechanism and is now a banned rule.

Rotation is keyed on `template_id` so consecutive fallbacks differ, and every
default sentence here is written to pass the channel's own rule pack.
"""

import re
from typing import Any, Dict, List

from .farqkya_style import CTA_BANK

# Each form matches a different archetype in farqkya_style.HOOKS.
_HOOK_FORMS = [
    "Ye hai {a} aur ye hai {b}, aakhir isme farq kya hai?",
    "Bohat se log {a} aur {b} ko ek hi cheez samajh lete hain.",
    "In dono mein sirf ek baat ka farq hai, magar wahi sab kuch badal deti hai.",
    "Agar koi aap se poochhe ke {a} aur {b} mein farq kya hai, aap kya kahenge?",
    "Ye dono lafz roz sunai dete hain, aur roz hi ek doosre ki jagah bole jaate hain.",
]

# `jabke` is capped at one use per script, so the pivot rotates. Spoken Urdu
# contrasts with a full stop far more often than with a conjunction.
_CONTRAST_FORMS = [
    "{a}. Magar {b}.",
    "{a}. Doosri taraf {b}.",
    "{a}. Ab {b}.",
    "{a}, jabke {b}.",
]

_COMP_CONTRASTS = ["{a}. Magar {b}.", "{a}. Doosra ye ke {b}.", "{a}. {b}."]


def _as_sentence(text: str) -> str:
    """Tracker fragments become real sentences so nothing joins into a run-on."""
    t = (text or "").strip()
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    return t if t[-1] in ".?!" else t + "."


def _prefix_entity(entity: str, mech: str) -> str:
    """Prepends the entity unless the mechanism already names it (full-name match)."""
    mech = (mech or "").strip()
    if not mech:
        return entity
    ent = (entity or "").strip()
    if not ent:
        return mech
    first_clause = re.split(r"[,.]", mech, maxsplit=1)[0].lower()
    if ent.lower() in first_clause:
        return mech
    return f"{ent} {mech}"


class FarqKyaScriptTemplates:
    """Renders farqkya fallback scripts with rotating structure."""

    @staticmethod
    def render_deepdive(entity_a: str, entity_b: str, template_id: int,
                        concept_hook: str, mechanism_a: str, mechanism_b: str,
                        punchline: str) -> str:
        idx = max(0, int(template_id or 1) - 1)
        hook = _HOOK_FORMS[idx % len(_HOOK_FORMS)].format(a=entity_a, b=entity_b)
        setup = _as_sentence(concept_hook) or (
            "Naam alag hain, kaam bhi alag hai, magar bola aksar ek hi tarah jaata hai.")
        contrast = _CONTRAST_FORMS[idx % len(_CONTRAST_FORMS)].format(
            a=_prefix_entity(entity_a, mechanism_a).rstrip("."),
            b=_prefix_entity(entity_b, mechanism_b).rstrip("."))
        payoff = _as_sentence(punchline) or (
            f"Isi liye {entity_a} ki jagah {entity_b} nahi chalta, chahe baat ek hi lage.")
        cta = CTA_BANK[idx % len(CTA_BANK)]
        return " ".join(p for p in [hook, setup, contrast, payoff, cta] if p)

    @staticmethod
    def render_compilation(pairs_data: List[Dict[str, str]]) -> str:
        blocks = []
        for i, pair in enumerate(pairs_data[:3]):
            ea = (pair.get("entity_a") or "").strip()
            eb = (pair.get("entity_b") or "").strip()
            ca = _prefix_entity(ea, pair.get("contrast_a", "")).rstrip(".")
            cb = _prefix_entity(eb, pair.get("contrast_b", "")).rstrip(".")
            hook = _HOOK_FORMS[i % len(_HOOK_FORMS)].format(a=ea, b=eb)
            body = _COMP_CONTRASTS[i % len(_COMP_CONTRASTS)].format(a=ca, b=cb)
            blocks.append(f"{hook} {body}")
        blocks.append(CTA_BANK[0])
        return " ".join(b for b in blocks if b)

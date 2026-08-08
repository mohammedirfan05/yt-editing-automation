"""
Playbook Templates Module.
Implements exact script templates (Templates 1-8) strictly adhering to docs/viral_shorts_playbook.md.
"""

from typing import Any, Dict, List


class ScriptTemplates:
    """Formatter for Playbook-compliant script templates."""

    @staticmethod
    def render_deepdive(
        entity_a: str,
        entity_b: str,
        template_id: int,
        concept_hook: str,
        mechanism_a: str,
        mechanism_b: str,
        punchline: str
    ) -> str:
        """
        Renders a Playbook-compliant DEEPDIVE script (75-85 words, 28-32s).
        """
        # Hook (Line 1) - Mandatory syntax
        hook_line = f"This is {entity_a}. This is {entity_b}. So what's the difference?"

        # Misconception shatter
        misconception_line = concept_hook

        # Mechanism contrast - ensure clean phrasing without duplicating entity names
        mech_a_str = mechanism_a.strip()
        mech_b_str = mechanism_b.strip()

        if mech_a_str.lower().startswith(entity_a.lower()):
            part_a = mech_a_str
        else:
            part_a = f"{entity_a} {mech_a_str}"

        if mech_b_str.lower().startswith(entity_b.lower()):
            part_b = mech_b_str
        else:
            part_b = f"{entity_b} {mech_b_str}"

        contrast_line = f"{part_a}. But {part_b}."

        # Punchline rule
        punchline_line = punchline

        # Outro
        outro_line = "Follow for more."

        # Combine into complete script text
        lines = [
            hook_line,
            misconception_line,
            contrast_line,
            punchline_line,
            outro_line
        ]

        full_text = " ".join(lines)
        return full_text

    @staticmethod
    def render_compilation(pairs_data: List[Dict[str, str]]) -> str:
        """
        Renders a Playbook-compliant COMPILATION script (90-95 words, 32-35s).
        Expects 3 pairs in pairs_data.
        """
        blocks = []
        for pair in pairs_data[:3]:
            ea = pair.get("entity_a", "").strip()
            eb = pair.get("entity_b", "").strip()
            ca = pair.get("contrast_a", "").strip()
            cb = pair.get("contrast_b", "").strip()

            part_a = ca if ca.lower().startswith(ea.lower()) else f"{ea} {ca}"
            part_b = cb if cb.lower().startswith(eb.lower()) else f"{eb} {cb}"

            block = f"This is {ea}. This is {eb}. So what's the difference? {part_a}, while {part_b}."
            blocks.append(block)

        blocks.append("Follow for more.")
        return " ".join(blocks)

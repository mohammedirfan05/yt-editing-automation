"""
Farq Kya Script Templates Module.
Playbook-compliant Roman Urdu script templates for Farq Kya channel.
Enforces formula: "Ye hai X aur ye hai Y, aakhir isme farq kya hai?"
"""

from typing import Any, Dict, List


class FarqKyaScriptTemplates:
    """Formatter for Farq Kya (Roman Urdu) script templates."""

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
        Renders a DEEPDIVE script in Roman Urdu for Farq Kya channel.
        Hook: 'Ye hai X aur ye hai Y, aakhir isme farq kya hai?'
        """
        hook_line = f"Ye hai {entity_a} aur ye hai {entity_b}, aakhir isme farq kya hai?"

        misconception_line = concept_hook.strip() if concept_hook else f"Aksar log samajhte hain ke {entity_a} aur {entity_b} ek hi hain, lekin aisa nahi hai."

        mech_a_str = mechanism_a.strip()
        mech_b_str = mechanism_b.strip()

        part_a = mech_a_str if mech_a_str.lower().startswith(entity_a.lower()) else f"{entity_a} {mech_a_str}"
        part_b = mech_b_str if mech_b_str.lower().startswith(entity_b.lower()) else f"{entity_b} {mech_b_str}"

        contrast_line = f"{part_a}. Lekin {part_b}."

        punchline_line = punchline.strip() if punchline else f"Aakhir mein {entity_a} aur {entity_b} mein yahi bunyadi farq hai."

        outro_line = "Mazeed videos ke liye follow karein."

        lines = [
            hook_line,
            misconception_line,
            contrast_line,
            punchline_line,
            outro_line
        ]

        return " ".join(lines)

    @staticmethod
    def render_compilation(pairs_data: List[Dict[str, str]]) -> str:
        """
        Renders a COMPILATION script in Roman Urdu for Farq Kya channel.
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

            block = f"Ye hai {ea} aur ye hai {eb}, aakhir isme farq kya hai? {part_a}, jabke {part_b}."
            blocks.append(block)

        blocks.append("Mazeed videos ke liye follow karein.")
        return " ".join(blocks)

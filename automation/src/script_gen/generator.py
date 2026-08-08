"""
Script Generator Orchestration Module.
Combines Concept Catalog, Duplicate Detection, Playbook Templates, and Playbook Validator
to generate clean, ready-to-test Shorts scripts.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .analyzer import ConceptCatalog
from .templates import ScriptTemplates
from .tracker import ContentTracker
from .validator import PlaybookValidator


class ScriptGenerator:
    """Orchestrates concept selection, duplicate checking, script generation, and validation."""

    def __init__(
        self,
        tracker: Optional[ContentTracker] = None,
        output_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "generated_scripts")
    ):
        self.tracker = tracker if tracker else ContentTracker()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_scripts(
        self,
        count: int = 2,
        mode: str = "auto",
        fandom: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates N high-potential, non-duplicate, Playbook-compliant scripts.
        When mode='auto', balances 50% Deep Dives and 50% Compilations (e.g. N=2 -> 1 DD + 1 Comp; N=10 -> 5 DD + 5 Comp).
        """
        generated = []
        opportunities = ConceptCatalog.get_all_opportunities()

        if mode == "auto":
            target_deepdives = (count + 1) // 2
            target_compilations = count // 2
        elif mode == "deepdive":
            target_deepdives = count
            target_compilations = 0
        else:
            target_deepdives = 0
            target_compilations = count

        count_deepdives = 0
        count_compilations = 0

        # Try Gemini Flash LLM Script Generation first
        llm_scripts = self._generate_via_gemini_llm(
            count=count,
            target_deepdives=target_deepdives,
            target_compilations=target_compilations,
            fandom=fandom
        )

        for opp in llm_scripts:
            if len(generated) >= count:
                break

            opp_type = opp.get("type", "deepdive")
            opp_fandom = opp.get("fandom", "Marvel")
            pairs = opp.get("pairs", [])
            title = opp.get("title", "")
            script_text = opp.get("script", "")

            # 1. Duplicate Check
            is_dup, match_id, reason = self.tracker.is_duplicate(pairs, title)
            if is_dup:
                continue

            # 2. Playbook Validation
            is_compliant, issues, metrics = PlaybookValidator.validate_script(script_text, mode=opp_type)
            if not is_compliant:
                continue

            topic_id = opp.get("id", f"gen_{len(generated)+1:02d}")
            topic_entry = {
                "id": topic_id,
                "title": title,
                "type": opp_type,
                "status": "approved",
                "fandom": opp_fandom,
                "pairs": pairs,
                "script": script_text,
                "word_count": metrics.get("word_count", len(script_text.split())),
                "estimated_duration_sec": metrics.get("estimated_duration_sec", 30.0),
                "speech_pacing_wps": metrics.get("speech_pacing_wps", 2.7),
                "playbook_compliant": is_compliant,
                "validation_issues": issues,
                "labels": self._build_labels(pairs, opp_type),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            if opp_type == "deepdive":
                count_deepdives += 1
            else:
                count_compilations += 1

            artifact_path = os.path.join(self.output_dir, f"{topic_id}.json")
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(topic_entry, f, indent=2, ensure_ascii=False)

            topic_entry["artifact_path"] = artifact_path
            generated.append(topic_entry)

        # Fallback to ConceptCatalog if LLM yielded fewer scripts than count
        if len(generated) < count:
            opportunities = ConceptCatalog.get_all_opportunities()
            for opp in opportunities:
                if len(generated) >= count:
                    break

                opp_type = opp.get("type", "deepdive")
                opp_fandom = opp.get("fandom", "Marvel")

                if opp_type == "deepdive" and count_deepdives >= target_deepdives:
                    continue
                if opp_type == "compilation" and count_compilations >= target_compilations:
                    continue

                if fandom and opp_fandom.lower() != fandom.lower():
                    continue

                pairs = opp.get("pairs", [])
                title = opp.get("title", "")

                is_dup, match_id, reason = self.tracker.is_duplicate(pairs, title)
                if is_dup:
                    continue

                if opp_type == "deepdive":
                    script_text = ScriptTemplates.render_deepdive(
                        entity_a=opp.get("entity_a", pairs[0][0] if pairs else "Entity A"),
                        entity_b=opp.get("entity_b", pairs[0][1] if pairs and len(pairs[0]) > 1 else "Entity B"),
                        template_id=opp.get("template_id", 1),
                        concept_hook=opp.get("concept_hook", "Most people think they are the same. They're not."),
                        mechanism_a=opp.get("mechanism_a", "operates with unique energy"),
                        mechanism_b=opp.get("mechanism_b", "operates with contrasting power"),
                        punchline=opp.get("punchline", "Entity A uses force, while Entity B uses power.")
                    )
                else:
                    script_text = ScriptTemplates.render_compilation(
                        pairs_data=opp.get("pairs_data", [])
                    )

                is_compliant, issues, metrics = PlaybookValidator.validate_script(script_text, mode=opp_type)
                if not is_compliant:
                    continue

                topic_id = opp["id"]
                topic_entry = {
                    "id": topic_id,
                    "title": title,
                    "type": opp_type,
                    "status": "approved",
                    "fandom": opp_fandom,
                    "pairs": pairs,
                    "script": script_text,
                    "word_count": metrics.get("word_count", 0),
                    "estimated_duration_sec": metrics.get("estimated_duration_sec", 0.0),
                    "speech_pacing_wps": metrics.get("speech_pacing_wps", 2.7),
                    "playbook_compliant": is_compliant,
                    "validation_issues": issues,
                    "labels": self._build_labels(pairs, opp_type),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }

                if opp_type == "deepdive":
                    count_deepdives += 1
                else:
                    count_compilations += 1

                artifact_path = os.path.join(self.output_dir, f"{topic_id}.json")
                with open(artifact_path, "w", encoding="utf-8") as f:
                    json.dump(topic_entry, f, indent=2, ensure_ascii=False)

                topic_entry["artifact_path"] = artifact_path
                generated.append(topic_entry)

        return generated

    def _generate_via_gemini_llm(
        self,
        count: int,
        target_deepdives: int,
        target_compilations: int,
        fandom: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Calls Gemini Flash LLM to generate fresh Playbook scripts dynamically."""
        import requests
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return []

        # Gather excluded published concepts to prevent duplicate generation
        published_pairs = []
        for t in self.tracker.data.get("topics", {}).values():
            if t.get("status") in ["published", "posted"]:
                for p in t.get("pairs", []):
                    if len(p) >= 2:
                        published_pairs.append(f"{p[0]} vs {p[1]}")

        excluded_str = ", ".join(published_pairs) if published_pairs else "None"

        prompt = f"""You are the expert YouTube Shorts scriptwriter for channel "Dont Mix This".
Your job is to generate {count} fresh, high-potential pop culture X vs Y Shorts scripts.
Target distribution: {target_deepdives} DEEPDIVE scripts and {target_compilations} COMPILATION scripts.

CRITICAL DUPLICATE RULE:
Do NOT generate any of the following already published concepts:
{excluded_str}

Playbook Instructions:
1. DEEPDIVE Mode (75-85 words total, ~2.7 wps):
   - Hook: "This is [X]. This is [Y]. So what's the difference?"
   - Misconception shatter: "Most people think... They're not."
   - Contrast mechanism, end with punchline rule: "That's why [X] [action], while [Y] [result]."
   - Outro: "Follow for more."

2. COMPILATION Mode (90-95 words total, 3 pairs from same fandom):
   - 3 pairs, repeating hook: "This is [A]. This is [B]. So what's the difference? [A] is... [B] is..."
   - Outro: "Follow for more."

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this schema:
{{
  "topics": [
    {{
      "id": "gemini_dd_01",
      "title": "Short Descriptive Title",
      "type": "deepdive",
      "fandom": "Marvel",
      "pairs": [["Entity A", "Entity B"]],
      "script": "Full script text adhering to Playbook rules."
    }},
    {{
      "id": "gemini_comp_01",
      "title": "Short Compilation Title",
      "type": "compilation",
      "fandom": "DC",
      "pairs": [["Term A", "Term B"], ["Term C", "Term D"], ["Term E", "Term F"]],
      "script": "Full compilation script text adhering to Playbook rules."
    }}
  ]
}}"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "responseMimeType": "application/json"
            }
        }

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=25)
            if r.status_code == 200:
                res_data = r.json()
                content_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(content_text)
                return parsed.get("topics", [])
        except Exception as e:
            pass

        return []

    def _build_labels(self, pairs: List[List[str]], mode: str) -> Dict[str, Any]:
        """Formats labels structure required by CapCut builder if exported to batch."""
        if mode == "deepdive" and pairs and len(pairs[0]) >= 2:
            return {
                "label1": pairs[0][0],
                "label2": pairs[0][1]
            }
        elif mode == "compilation" and pairs:
            labels_dict = {}
            for idx, p in enumerate(pairs, 1):
                if len(p) >= 2:
                    labels_dict[f"pair{idx}"] = [p[0], p[1]]
            return labels_dict
        return {}

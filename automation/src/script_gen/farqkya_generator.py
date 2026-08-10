"""
Farq Kya Script Generator Orchestration Module.
Dedicated generator for Farq Kya channel (@farqkya) written in Roman Urdu.
Enforces hook formula: "Ye hai X aur ye hai Y, aakhir isme farq kya hai?"
"""

import json
import os
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .farqkya_catalog import FarqKyaCatalog
from .farqkya_templates import FarqKyaScriptTemplates
from .farqkya_validator import FarqKyaValidator
from .tracker import ContentTracker


class FarqKyaScriptGenerator:
    """Orchestrates concept selection, script generation, and validation for Farq Kya."""

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
        Generates N Playbook-compliant scripts for Farq Kya.
        """
        generated = []
        
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

        # Primary Path: Gemini LLM Script Generation
        llm_scripts = self._generate_via_gemini_llm(
            count=count,
            target_deepdives=target_deepdives,
            target_compilations=target_compilations
        )

        for opp in llm_scripts:
            if len(generated) >= count:
                break

            opp_type = opp.get("type", "deepdive")
            opp_fandom = opp.get("fandom", "Islamic")
            pairs = opp.get("pairs", [])
            title = opp.get("title", "")
            script_text = opp.get("script", "")

            # 1. Duplicate Check
            is_dup, match_id, reason = self.tracker.is_duplicate(pairs, title)
            if is_dup:
                continue

            # 2. Playbook Validation
            is_compliant, issues, metrics = FarqKyaValidator.validate_script(script_text, mode=opp_type)
            if not is_compliant:
                continue

            topic_id = opp.get("id", f"farq_fk_{len(generated)+1:02d}")
            topic_entry = {
                "id": topic_id,
                "title": title,
                "type": opp_type,
                "channel": "farqkya",
                "status": "idea",
                "fandom": opp_fandom,
                "pairs": pairs,
                "script": script_text,
                "word_count": metrics.get("word_count", len(script_text.split())),
                "estimated_duration_sec": metrics.get("estimated_duration_sec", 28.0),
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
            self.tracker.add_topic(topic_entry)
            generated.append(topic_entry)

        # Fallback Path: FarqKyaCatalog if LLM scripts are insufficient
        if len(generated) < count:
            opportunities = FarqKyaCatalog.get_all_opportunities()
            for opp in opportunities:
                if len(generated) >= count:
                    break

                opp_type = opp.get("type", "deepdive")
                opp_fandom = opp.get("fandom", "Islamic")

                if opp_type == "deepdive" and count_deepdives >= target_deepdives:
                    continue
                if opp_type == "compilation" and count_compilations >= target_compilations:
                    continue

                pairs = opp.get("pairs", [])
                title = opp.get("title", "")

                is_dup, match_id, reason = self.tracker.is_duplicate(pairs, title)
                if is_dup:
                    continue

                if opp_type == "deepdive":
                    script_text = FarqKyaScriptTemplates.render_deepdive(
                        entity_a=opp.get("entity_a", pairs[0][0] if pairs else "Entity A"),
                        entity_b=opp.get("entity_b", pairs[0][1] if pairs and len(pairs[0]) > 1 else "Entity B"),
                        template_id=opp.get("template_id", 1),
                        concept_hook=opp.get("concept_hook", ""),
                        mechanism_a=opp.get("mechanism_a", ""),
                        mechanism_b=opp.get("mechanism_b", ""),
                        punchline=opp.get("punchline", "")
                    )
                else:
                    script_text = FarqKyaScriptTemplates.render_compilation(
                        pairs_data=opp.get("pairs_data", [])
                    )

                is_compliant, issues, metrics = FarqKyaValidator.validate_script(script_text, mode=opp_type)
                if not is_compliant:
                    continue

                topic_id = opp["id"]
                topic_entry = {
                    "id": topic_id,
                    "title": title,
                    "type": opp_type,
                    "channel": "farqkya",
                    "status": "idea",
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
                self.tracker.add_topic(topic_entry)
                generated.append(topic_entry)

        return generated

    def _generate_via_gemini_llm(
        self,
        count: int,
        target_deepdives: int,
        target_compilations: int
    ) -> List[Dict[str, Any]]:
        """
        Calls Gemini LLM to generate Roman Urdu scripts for Farq Kya channel.
        """
        from src.env_utils import get_gemini_api_key
        api_key = get_gemini_api_key()
        if not api_key:
            return []

        published_pairs = []
        for t in self.tracker.data.get("topics", {}).values():
            if t.get("status") in ["published", "posted"]:
                for p in t.get("pairs", []):
                    if len(p) >= 2:
                        published_pairs.append(f"{p[0]} vs {p[1]}")

        excluded_str = ", ".join(published_pairs) if published_pairs else "None"

        prompt = f"""You are the expert YouTube Shorts scriptwriter for Urdu/Hindi Islamic channel "Farq Kya" (@farqkya).
Your job is to generate {count} fresh, high-potential Islamic X vs Y Shorts scripts written in clear, natural Roman Urdu (Urdu written in Latin/English script).
Target distribution: {target_deepdives} DEEPDIVE scripts and {target_compilations} COMPILATION scripts.

CRITICAL DUPLICATE RULE:
Do NOT generate any of the following already published concepts:
{excluded_str}

Playbook Instructions for Farq Kya (Roman Urdu):
1. DEEPDIVE Mode (60-85 words total in Roman Urdu):
   - Mandatory Hook (Line 1): "Ye hai [X] aur ye hai [Y], aakhir isme farq kya hai?"
   - Misconception shatter: "Aksar log samajhte hain ke... Lekin aisa nahi hai."
   - Contrast mechanism, end with punchline rule: "Isliye [X] [action], jabke [Y] [result]."
   - Outro: "Mazeed videos ke liye follow karein."

2. COMPILATION Mode (75-95 words total, 3 pairs):
   - 3 pairs, repeating hook: "Ye hai [A] aur ye hai [B], aakhir isme farq kya hai? [A] [contrast A], jabke [B] [contrast B]."
   - Outro: "Mazeed videos ke liye follow karein."

OUTPUT JSON SCHEMA ONLY:
Return strictly valid JSON with no markdown block wrappers around the JSON:
{{
  "topics": [
    {{
      "id": "farq_fk_01",
      "title": "Nabi vs Rasool: Farq Kya Hai?",
      "type": "deepdive",
      "fandom": "Islamic",
      "pairs": [["Nabi", "Rasool"]],
      "script": "Ye hai Nabi aur ye hai Rasool, aakhir isme farq kya hai? Aksar log samajhte hain ke dono ek hi hain, lekin aisa nahi hai. Nabi Allah ki taraf se wahi haasil karte hain, jabke Rasool nayi shariat aur kitab ke saath bheje jaate hain. Har Rasool Nabi hota hai, lekin har Nabi Rasool nahi hota. Mazeed videos ke liye follow karein."
    }}
  ]
}}"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
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
        except Exception:
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

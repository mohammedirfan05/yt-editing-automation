"""
Farq Kya Script Generator Orchestration Module.
Dedicated generator for Farq Kya channel (@farqkya) written in Roman Urdu.
Enforces hook formula: "Ye hai X aur ye hai Y, aakhir isme farq kya hai?"
Post-processes prose with unslop CLI / sanitizer and generates YouTube SEO packages.
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
from .unslop_sanitizer import UnslopSanitizer


class FarqKyaScriptGenerator:
    """Orchestrates concept selection, script generation, unslop sanitization, and validation for Farq Kya."""

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

        # Primary Path: Gemini LLM Script Generation with Few-Shot Prompt Engineering
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
            raw_script_text = opp.get("script", "")

            # 1. Post-process & sanitize script using unslop
            script_text = UnslopSanitizer.sanitize(raw_script_text)

            # 2. Duplicate Check
            is_dup, match_id, reason = self.tracker.is_duplicate(pairs, title)
            if is_dup:
                continue

            # 3. Playbook Validation
            is_compliant, issues, metrics = FarqKyaValidator.validate_script(script_text, mode=opp_type)
            if not is_compliant:
                continue

            topic_id = opp.get("id", f"farq_fk_{len(generated)+1:02d}")
            seo_metadata = opp.get("seo_metadata", self._generate_default_seo_package(title, pairs, script_text))

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
                "unslop_sanitized": True,
                "validation_issues": issues,
                "labels": self._build_labels(pairs, opp_type),
                "seo_metadata": seo_metadata,
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
                    raw_script = FarqKyaScriptTemplates.render_deepdive(
                        entity_a=opp.get("entity_a", pairs[0][0] if pairs else "Entity A"),
                        entity_b=opp.get("entity_b", pairs[0][1] if pairs and len(pairs[0]) > 1 else "Entity B"),
                        template_id=opp.get("template_id", 1),
                        concept_hook=opp.get("concept_hook", ""),
                        mechanism_a=opp.get("mechanism_a", ""),
                        mechanism_b=opp.get("mechanism_b", ""),
                        punchline=opp.get("punchline", "")
                    )
                else:
                    raw_script = FarqKyaScriptTemplates.render_compilation(
                        pairs_data=opp.get("pairs_data", [])
                    )

                script_text = UnslopSanitizer.sanitize(raw_script)

                is_compliant, issues, metrics = FarqKyaValidator.validate_script(script_text, mode=opp_type)
                if not is_compliant:
                    continue

                topic_id = opp["id"]
                seo_metadata = self._generate_default_seo_package(title, pairs, script_text)

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
                    "unslop_sanitized": True,
                    "validation_issues": issues,
                    "labels": self._build_labels(pairs, opp_type),
                    "seo_metadata": seo_metadata,
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
        Calls Gemini LLM using Prompt-Engineering patterns (Instruction Hierarchy & Few-Shot Learning)
        to generate Roman Urdu scripts for Farq Kya channel.
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

        # PROMPT ENGINEERING STRUCTURE:
        # [System Context] -> [Task Rules] -> [Few-Shot Examples] -> [Exclusions] -> [Output Schema]
        prompt = f"""You are an elite YouTube Shorts scriptwriter for the popular Roman Urdu Islamic channel "Farq Kya" (@farqkya).

### CHANNEL MISSION & BRAND VOICE
- AUDIENCE: Urdu/Hindi speakers seeking clear, respectful, engaging Islamic comparison knowledge.
- RETENTION GOAL: Shatter common misconceptions in the first 5 seconds and deliver punchy contrast.
- LANGUAGE: Clean, natural Roman Urdu (Latin script). No meta-commentary, no preambles, no generic AI fluff (e.g. "aaj ki video mein", "welcome back").

### DEEPDIVE SCRIPT PLAYBOOK (60-85 words total):
1. MANDATORY HOOK (Line 1 exact formula): "Ye hai [Entity A] aur ye hai [Entity B], aakhir isme farq kya hai?"
2. MISCONCEPTION SHATTER: Address common misunderstanding ("Aksar log samajhte hain ke... Lekin aisa nahi hai.")
3. UNDERLYING MECHANISM: Explain core difference ("Isliye [Entity A] [mechanism A], jabke [Entity B] [mechanism B].")
4. PUNCHLINE: Decisive summary sentence highlighting the fundamental distinction.
5. OUTRO CTA: "Mazeed videos ke liye follow karein."

### FEW-SHOT GOLD STANDARD EXAMPLES

Example 1 (DEEPDIVE):
Input Topic: Nabi vs Rasool
Output Component Breakdown:
- Entity A: Nabi
- Entity B: Rasool
- Misconception: Aksar log samajhte hain ke dono ek hi hain, lekin aisa nahi hai.
- Mechanism: Nabi Allah ki taraf se wahi haasil karte hain aur pehli shariat ko aage badhate hain, jabke Rasool nayi aasmani kitab aur nayi shariat ke saath bheje jaate hain.
- Punchline: Har Rasool Nabi hota hai, lekin har Nabi Rasool nahi hota.
Script: "Ye hai Nabi aur ye hai Rasool, aakhir isme farq kya hai? Aksar log samajhte hain ke dono ek hi hain, lekin aisa nahi hai. Nabi Allah ki taraf se wahi haasil karte hain aur pehli shariat ko aage badhate hain, jabke Rasool nayi aasmani kitab aur nayi shariat ke saath bheje jaate hain. Har Rasool Nabi hota hai, lekin har Nabi Rasool nahi hota. Mazeed videos ke liye follow karein."

Example 2 (DEEPDIVE):
Input Topic: Hajj vs Umrah
Script: "Ye hai Hajj aur ye hai Umrah, aakhir isme farq kya hai? Ek saal mein sirf ek baar Zil-Hajj ke makhsoos dino mein hota hai, jabke doosra saal bhar kabhi bhi kiya ja sakta hai. Hajj Islam ka ek farz rukn hai jo har sahib-e-ista'at par zindagi mein ek baar farz hai, jabke Umrah ek nafli ibadat hai. Mazeed videos ke liye follow karein."

Example 3 (COMPILATION - 75-95 words, 3 pairs):
Script: "Ye hai Zakat aur ye hai Sadaqah, aakhir isme farq kya hai? Zakat saal mein ek baar farz hai, jabke Sadaqah aam nafli khairat hai. Ye hai Fard aur ye hai Sunnah, aakhir isme farq kya hai? Fard Allah ka lazmi hukum hai, jabke Sunnah Nabi Kareem SAW ka mubarak tareeqa. Ye hai Tawbah aur ye hai Istighfar, aakhir isme farq kya hai? Istighfar zuban ki pukaar hai, jabke Tawbah dil ki mukammal waapsi. Mazeed videos ke liye follow karein."

### CURRENT TASK INSTRUCTIONS
Generate exactly {count} fresh, non-duplicate Islamic X vs Y scripts for Farq Kya.
Target breakdown: {target_deepdives} DEEPDIVE scripts, {target_compilations} COMPILATION scripts.

DO NOT REPEAT THESE PUBLISHED CONCEPTS:
{excluded_str}

### OUTPUT JSON SCHEMA (STRICT JSON ONLY, NO MARKDOWN WRAPPERS):
{{
  "topics": [
    {{
      "id": "farq_fk_01",
      "title": "Nabi vs Rasool: Farq Kya Hai?",
      "type": "deepdive",
      "fandom": "Islamic",
      "pairs": [["Nabi", "Rasool"]],
      "entity_a": "Nabi",
      "entity_b": "Rasool",
      "misconception_shatter": "Aksar log samajhte hain ke dono ek hi hain, lekin aisa nahi hai.",
      "punchline": "Har Rasool Nabi hota hai, lekin har Nabi Rasool nahi hota.",
      "script": "Ye hai Nabi aur ye hai Rasool, aakhir isme farq kya hai? Aksar log samajhte hain ke dono ek hi hain, lekin aisa nahi hai. Nabi Allah ki taraf se wahi haasil karte hain, jabke Rasool nayi shariat aur kitab ke saath bheje jaate hain. Har Rasool Nabi hota hai, lekin har Nabi Rasool nahi hota. Mazeed videos ke liye follow karein.",
      "seo_metadata": {{
        "seo_title": "Nabi vs Rasool: Farq Kya Hai? (60-70 chars SEO Title)",
        "ab_title": "Har Rasool Nabi Hota Hai Lekin Har Nabi Rasool Kyun Nahi?",
        "thumbnail_text": "Nabi Vs Rasool Farq!",
        "hashtags": ["#Shorts", "#FarqKya", "#IslamicKnowledge", "#NabiVsRasool"],
        "description": "Nabi aur Rasool mein kya farq hai? Is short video mein janiye Islamic history aur Quran-o-Sunnah ki roshni mein in dono azeem darjat ka bunyadi farq.",
        "pinned_comment": "Kya aapko Nabi aur Rasool ke is bunyadi farq ka pehle se pata tha? Comments mein batayein!"
      }}
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
            else:
                from colorama import Fore, Style
                print(Fore.YELLOW + f"⚠️ Gemini API returned status {r.status_code}. Falling back to offline concept catalog." + Style.RESET_ALL)
                print(Fore.YELLOW + "   To generate infinite AI scripts, ensure GEMINI_API_KEY in .env is a valid Google AI Studio key (starts with AIzaSy...)." + Style.RESET_ALL)
        except Exception as e:
            from colorama import Fore, Style
            print(Fore.YELLOW + f"⚠️ Gemini LLM call error: {e}. Falling back to offline concept catalog." + Style.RESET_ALL)

        return []

    def _generate_default_seo_package(self, title: str, pairs: List[List[str]], script_text: str) -> Dict[str, Any]:
        """Generates a default YouTube Shorts SEO package if LLM did not provide one."""
        p_str = f"{pairs[0][0]} vs {pairs[0][1]}" if pairs and len(pairs[0]) >= 2 else title
        seo_title = f"{p_str}: Farq Kya Hai? | Islamic Shorts"
        if len(seo_title) > 70:
            seo_title = seo_title[:67] + "..."

        return {
            "seo_title": seo_title,
            "ab_title": f"Aakhir {p_str} Mein Kya Farq Hai?",
            "thumbnail_text": f"{p_str} Farq!",
            "hashtags": ["#Shorts", "#FarqKya", "#IslamicKnowledge"],
            "description": f"Aakhir {p_str} mein kya farq hai? Janiye is short video mein 30 seconds mein.",
            "pinned_comment": f"Kya aapko {p_str} ke is farq ka pehle se ilam tha? Comments mein zaroor batayein!"
        }

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

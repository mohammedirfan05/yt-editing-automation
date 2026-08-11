"""
Script Generator Orchestration Module.
Combines Concept Catalog, Duplicate Detection, Playbook Templates, Playbook Validator,
Unslop Sanitizer, and YouTube SEO Optimizer to generate clean, ready-to-test Shorts scripts.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .analyzer import ConceptCatalog
from .templates import ScriptTemplates, ScriptTemplatesUrdu
from .tracker import ContentTracker
from .validator import PlaybookValidator, PlaybookValidatorUrdu
from .unslop_sanitizer import UnslopSanitizer


class ScriptGenerator:
    """Orchestrates concept selection, duplicate checking, script generation, unslop cleaning, and validation."""

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
        fandom: Optional[str] = None,
        channel: str = "dontmixthis"
    ) -> List[Dict[str, Any]]:
        """
        Generates N high-potential, non-duplicate, Playbook-compliant scripts.
        When mode='auto', balances 50% Deep Dives and 50% Compilations.
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

        # Try Gemini LLM Script Generation first
        if channel == "farqkya":
            llm_scripts = self._generate_via_gemini_llm_farqkya(
                count=count,
                target_deepdives=target_deepdives,
                target_compilations=target_compilations,
                fandom=fandom
            )
        else:
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
            opp_fandom = opp.get("fandom", "Islamic" if channel == "farqkya" else "Marvel")
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
            is_compliant, issues, metrics = PlaybookValidator.validate_script(script_text, mode=opp_type, channel=channel)
            if not is_compliant:
                continue

            topic_id = opp.get("id", f"gen_{len(generated)+1:02d}")
            seo_metadata = opp.get("seo_metadata", self._generate_default_seo_package(title, pairs, script_text, channel=channel))

            topic_entry = {
                "id": topic_id,
                "title": title,
                "type": opp_type,
                "channel": channel,
                "status": "idea",
                "fandom": opp_fandom,
                "pairs": pairs,
                "script": script_text,
                "word_count": metrics.get("word_count", len(script_text.split())),
                "estimated_duration_sec": metrics.get("estimated_duration_sec", 30.0),
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

        # Fallback to ConceptCatalog if LLM yielded fewer scripts than count
        if len(generated) < count:
            opportunities = ConceptCatalog.get_all_opportunities(channel=channel)
            for opp in opportunities:
                if len(generated) >= count:
                    break

                opp_type = opp.get("type", "deepdive")
                opp_fandom = opp.get("fandom", "Islamic" if channel == "farqkya" else "Marvel")

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

                if channel == "farqkya":
                    if opp_type == "deepdive":
                        raw_script = ScriptTemplatesUrdu.render_deepdive(
                            entity_a=opp.get("entity_a", pairs[0][0] if pairs else "Entity A"),
                            entity_b=opp.get("entity_b", pairs[0][1] if pairs and len(pairs[0]) > 1 else "Entity B"),
                            template_id=opp.get("template_id", 1),
                            concept_hook=opp.get("concept_hook", "Aksar log samajhte hain ke ye dono ek hi hain, lekin aisa nahi hai."),
                            mechanism_a=opp.get("mechanism_a", "pehli shariat ko aage badhate hain"),
                            mechanism_b=opp.get("mechanism_b", "nayi kitab aur shariat ke saath aate hain"),
                            punchline=opp.get("punchline", "Aakhir mein inme yahi bunyadi farq hai.")
                        )
                    else:
                        raw_script = ScriptTemplatesUrdu.render_compilation(
                            pairs_data=opp.get("pairs_data", [])
                        )
                else:
                    if opp_type == "deepdive":
                        raw_script = ScriptTemplates.render_deepdive(
                            entity_a=opp.get("entity_a", pairs[0][0] if pairs else "Entity A"),
                            entity_b=opp.get("entity_b", pairs[0][1] if pairs and len(pairs[0]) > 1 else "Entity B"),
                            template_id=opp.get("template_id", 1),
                            concept_hook=opp.get("concept_hook", "Most people think they are the same. They're not."),
                            mechanism_a=opp.get("mechanism_a", "operates with unique energy"),
                            mechanism_b=opp.get("mechanism_b", "operates with contrasting power"),
                            punchline=opp.get("punchline", "Entity A uses force, while Entity B uses power.")
                        )
                    else:
                        raw_script = ScriptTemplates.render_compilation(
                            pairs_data=opp.get("pairs_data", [])
                        )

                script_text = UnslopSanitizer.sanitize(raw_script)

                is_compliant, issues, metrics = PlaybookValidator.validate_script(script_text, mode=opp_type, channel=channel)
                if not is_compliant:
                    continue

                topic_id = opp["id"]
                seo_metadata = self._generate_default_seo_package(title, pairs, script_text, channel=channel)

                topic_entry = {
                    "id": topic_id,
                    "title": title,
                    "type": opp_type,
                    "channel": channel,
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

    def _generate_via_gemini_llm_farqkya(
        self,
        count: int,
        target_deepdives: int,
        target_compilations: int,
        fandom: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Calls Gemini LLM to generate fresh Roman Urdu scripts for Farq Kya channel."""
        from src.script_gen.farqkya_generator import FarqKyaScriptGenerator
        farq_gen = FarqKyaScriptGenerator(tracker=self.tracker, output_dir=self.output_dir)
        return farq_gen._generate_via_gemini_llm(count=count, target_deepdives=target_deepdives, target_compilations=target_compilations)

    def _generate_via_gemini_llm(
        self,
        count: int,
        target_deepdives: int,
        target_compilations: int,
        fandom: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Calls Gemini LLM using Few-Shot Prompt Engineering for 'Dont Mix This' channel."""
        import requests
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

        prompt = f"""You are an expert YouTube Shorts scriptwriter for channel "Dont Mix This".

### BRAND VOICE & FORMAT GUIDELINES
- AUDIENCE: Pop culture, comic book (Marvel, DC, Anime), and movie fans.
- RETENTION HOOK: Start line 1 with instant comparison hook, shatter misconception on line 2.
- LANGUAGE: Punchy, high-energy English. Zero preambles, zero AI slop (no "in this video", "welcome back", "delve", "tapestry").

### FEW-SHOT GOLD STANDARD EXAMPLES

Example 1 (DEEPDIVE):
Topic: Mjolnir vs Stormbreaker
Script: "This is Mjolnir. This is Stormbreaker. So what's the difference? Most fans think Stormbreaker is just a bigger hammer. They're wrong. Mjolnir was forged to channel Thor's power and requires worthiness to lift. Stormbreaker is a king's weapon built to summon the Bifrost and bypass Thanos's Infinity Gauntlet beam. Mjolnir channels Thor's power, while Stormbreaker amplifies it to god-killing levels. Follow for more."

Example 2 (COMPILATION - 3 pairs):
Topic: Marvel Weapons Compared
Script: "This is Vibranium. This is Adamantium. So what's the difference? Vibranium absorbs kinetic energy, while Adamantium is indestructible. This is Mjolnir. This is Stormbreaker. So what's the difference? Mjolnir requires worthiness, while Stormbreaker summons the Bifrost. This is the Infinity Gauntlet. This is the Darkhold. So what's the difference? The Gauntlet bends physical reality, while the Darkhold corrupts magic. Follow for more."

### TASK INSTRUCTIONS
Generate exactly {count} fresh, high-potential pop culture X vs Y Shorts scripts.
Target distribution: {target_deepdives} DEEPDIVE scripts and {target_compilations} COMPILATION scripts.
{f'Filter by fandom: {fandom}' if fandom else ''}

DO NOT REPEAT THESE PUBLISHED CONCEPTS:
{excluded_str}

### OUTPUT JSON SCHEMA (STRICT JSON ONLY, NO MARKDOWN WRAPPERS):
{{
  "topics": [
    {{
      "id": "gemini_dd_01",
      "title": "Mjolnir vs Stormbreaker: What's the Difference?",
      "type": "deepdive",
      "fandom": "Marvel",
      "pairs": [["Mjolnir", "Stormbreaker"]],
      "script": "This is Mjolnir. This is Stormbreaker. So what's the difference? Most fans think Stormbreaker is just a bigger hammer. They're wrong. Mjolnir was forged to channel Thor's power and requires worthiness to lift. Stormbreaker is a king's weapon built to summon the Bifrost and bypass Thanos's Infinity Gauntlet beam. Mjolnir channels Thor's power, while Stormbreaker amplifies it to god-killing levels. Follow for more.",
      "seo_metadata": {{
        "seo_title": "Mjolnir vs Stormbreaker: What's the Difference? (Marvel SEO Title)",
        "ab_title": "Why Thor's Stormbreaker Beats Mjolnir in Every Way",
        "thumbnail_text": "Mjolnir Vs Stormbreaker!",
        "hashtags": ["#Shorts", "#Marvel", "#Thor", "#MjolnirVsStormbreaker"],
        "description": "What's the real difference between Thor's Mjolnir and Stormbreaker in Marvel? Watch this 30-second break down of their powers, enchantments, and lore.",
        "pinned_comment": "Which weapon would you pick in battle: Mjolnir or Stormbreaker? Tell us below!"
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

    def _generate_default_seo_package(self, title: str, pairs: List[List[str]], script_text: str, channel: str = "dontmixthis") -> Dict[str, Any]:
        """Generates default YouTube Shorts SEO package if LLM did not provide one."""
        p_str = f"{pairs[0][0]} vs {pairs[0][1]}" if pairs and len(pairs[0]) >= 2 else title
        if channel == "farqkya":
            return {
                "seo_title": f"{p_str}: Farq Kya Hai? | Islamic Shorts",
                "ab_title": f"Aakhir {p_str} Mein Kya Farq Hai?",
                "thumbnail_text": f"{p_str} Farq!",
                "hashtags": ["#Shorts", "#FarqKya", "#IslamicKnowledge"],
                "description": f"Aakhir {p_str} mein kya farq hai? Janiye is short video mein 30 seconds mein.",
                "pinned_comment": f"Kya aapko {p_str} ke is farq ka pehle se ilam tha? Comments mein zaroor batayein!"
            }
        else:
            return {
                "seo_title": f"{p_str}: What's the Difference?",
                "ab_title": f"The Real Difference Between {p_str}",
                "thumbnail_text": f"{p_str} Difference!",
                "hashtags": ["#Shorts", "#DontMixThis", "#PopCulture"],
                "description": f"What's the real difference between {p_str}? Watch this 30-second breakdown.",
                "pinned_comment": f"Which one do you prefer: {pairs[0][0] if pairs and len(pairs[0])>=1 else 'Entity A'} or {pairs[0][1] if pairs and len(pairs[0])>=2 else 'Entity B'}? Let us know!"
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

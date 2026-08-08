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
        output_dir: str = r"c:\yt_editing_automation\automation\generated_scripts"
    ):
        self.tracker = tracker if tracker else ContentTracker()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_scripts(
        self,
        count: int = 3,
        mode: str = "auto",
        fandom: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates N high-potential, non-duplicate, Playbook-compliant scripts.

        Args:
            count: Number of scripts to generate.
            mode: 'deepdive', 'compilation', or 'auto' (mixes both).
            fandom: Optional fandom filter ('Marvel', 'DC', 'Anime', 'Mythology', etc.).

        Returns:
            List of generated topic dictionaries.
        """
        generated = []
        opportunities = ConceptCatalog.get_all_opportunities()

        for opp in opportunities:
            if len(generated) >= count:
                break

            opp_type = opp.get("type", "deepdive")
            opp_fandom = opp.get("fandom", "Marvel")

            # Filter mode & fandom if requested
            if mode != "auto" and opp_type != mode:
                continue
            if fandom and opp_fandom.lower() != fandom.lower():
                continue

            pairs = opp.get("pairs", [])
            title = opp.get("title", "")

            # 1. Duplicate Check against Tracker
            is_dup, match_id, reason = self.tracker.is_duplicate(pairs, title)
            if is_dup:
                # Skip duplicate concepts already published or approved
                continue

            # 2. Render Script based on type
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

            # 3. Validate against Playbook Rules
            is_compliant, issues, metrics = PlaybookValidator.validate_script(script_text, mode=opp_type)

            topic_id = opp["id"]
            topic_entry = {
                "id": topic_id,
                "title": title,
                "type": opp_type,
                "status": "approved" if is_compliant else "idea",
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

            # 4. Save to Tracker
            self.tracker.add_topic(topic_entry)

            # 5. Export JSON artifact to generated_scripts/
            artifact_path = os.path.join(self.output_dir, f"{topic_id}.json")
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(topic_entry, f, indent=2, ensure_ascii=False)

            topic_entry["artifact_path"] = artifact_path
            generated.append(topic_entry)

        return generated

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

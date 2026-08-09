"""
Content Tracker Module.
Maintains persistent state of all published, approved, tested, rejected, and candidate ideas.
Prevents duplicate video topic generation.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


class ContentTracker:
    """Manages content lifecycle tracker stored in JSON format."""

    VALID_STATUSES = {"published", "approved", "tested", "rejected", "idea"}

    def __init__(
        self,
        tracker_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "content_tracker.json"),
        transcripts_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dont_mix_this_-_shorts_shorts_transcripts.json"),
        ideas_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "ideas.json")
    ):
        self.tracker_path = tracker_path
        self.transcripts_path = transcripts_path
        self.ideas_path = ideas_path
        self.data: Dict[str, Any] = {"version": "1.0", "updated_at": "", "topics": {}}
        self.load_or_seed()

    def load_or_seed(self) -> None:
        """Loads tracker file from disk or seeds it if missing/empty."""
        if os.path.exists(self.tracker_path):
            try:
                with open(self.tracker_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                if not self.data.get("topics"):
                    self.seed_from_historical()
                else:
                    self.sync_ideas_file()
                    self.sync_generated_scripts()
                    self.sync_to_ideas_json()
                    self.export_csv()
                return
            except Exception as e:
                print(f"⚠️ Could not load tracker from {self.tracker_path}: {e}. Re-seeding...")

        self.seed_from_historical()

    def sync_ideas_file(self) -> None:
        """Syncs items from config/ideas.json into tracker data."""
        if os.path.exists(self.ideas_path):
            try:
                with open(self.ideas_path, "r", encoding="utf-8") as f:
                    ideas_list = json.load(f)
                for idea in ideas_list:
                    idea_id = idea.get("id")
                    if not idea_id or idea_id in self.data.get("topics", {}):
                        continue
                    title = idea.get("project_name", "").replace("Auto_Deepdive_", "").replace("Auto_Compilation_", "").replace("_", " ")
                    script = idea.get("script", "")
                    labels = idea.get("labels", {})

                    pairs = []
                    if isinstance(labels, dict):
                        for k in sorted(labels.keys()):
                            v = labels[k]
                            if isinstance(v, list):
                                pairs.append(v)
                            elif isinstance(v, str) and v:
                                pairs.append([v, ""])
                    if not pairs:
                        pairs = self._extract_pairs_from_text(title + " " + script)

                    self.data.setdefault("topics", {})[idea_id] = {
                        "id": idea_id,
                        "title": title or idea_id,
                        "type": idea.get("type", "deepdive"),
                        "status": "idea",
                        "fandom": self._detect_fandom(title + " " + script),
                        "pairs": pairs,
                        "script": script,
                        "word_count": len(script.split()),
                        "duration_sec": 30.0,
                        "playbook_compliant": True,
                        "notes": "Unuploaded fresh script in config/ideas.json",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
            except Exception as e:
                pass

    def sync_generated_scripts(self) -> None:
        """Syncs items from generated_scripts/ directory into tracker data."""
        gen_dir = os.path.join(os.path.dirname(self.tracker_path), "..", "generated_scripts")
        if os.path.exists(gen_dir):
            try:
                for fname in os.listdir(gen_dir):
                    if fname.endswith(".json"):
                        fpath = os.path.join(gen_dir, fname)
                        with open(fpath, "r", encoding="utf-8") as f:
                            item = json.load(f)
                        script_id = item.get("id") or os.path.splitext(fname)[0]
                        if script_id not in self.data.get("topics", {}):
                            # Default status for generated script awaiting approval is idea
                            status = item.get("status", "idea")
                            if status == "approved" and "notes" not in item:
                                status = "idea"
                            item["status"] = status
                            self.data.setdefault("topics", {})[script_id] = item
            except Exception as e:
                pass

    def sync_to_ideas_json(self) -> None:
        """Syncs approved topics (or candidate ideas if none approved) from tracker to config/ideas.json."""
        topics = self.data.get("topics", {})
        
        # 1. Gather approved topics first
        approved_topics = [t for t in topics.values() if t.get("status") == "approved"]
        
        # 2. If no topics are approved yet, fall back to active 'idea' topics
        selected_topics = approved_topics if approved_topics else [
            t for t in topics.values() if t.get("status") in ["idea", "candidate"]
        ]
        
        formatted_ideas = []
        for t in selected_topics:
            topic_id = t.get("id")
            title = t.get("title", topic_id)
            ttype = t.get("type", "deepdive")
            script = t.get("script", "")
            labels = t.get("labels", {})

            clean_title = re.sub(r"[^\w\s]", "", title).strip().replace(" ", "_")
            proj_name = t.get("project_name") or f"Auto_{ttype.capitalize()}_{clean_title[:35]}"

            formatted_ideas.append({
                "id": topic_id,
                "project_name": proj_name,
                "type": ttype,
                "script": script,
                "labels": labels
            })

        if formatted_ideas:
            try:
                os.makedirs(os.path.dirname(self.ideas_path), exist_ok=True)
                with open(self.ideas_path, "w", encoding="utf-8") as f:
                    json.dump(formatted_ideas, f, indent=2, ensure_ascii=False)
            except Exception as e:
                pass

    def save(self) -> None:
        """Saves current tracker state to JSON and CSV formats."""
        os.makedirs(os.path.dirname(self.tracker_path), exist_ok=True)
        self.data["updated_at"] = datetime.now().isoformat()
        with open(self.tracker_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        self.export_csv()

    def export_csv(self) -> None:
        """Exports tracker topics to human-readable CSV file for Excel / Sheets viewing."""
        import csv
        self.sync_ideas_file()
        self.sync_generated_scripts()
        csv_path = os.path.join(os.path.dirname(self.tracker_path), "content_tracker.csv")
        try:
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Title", "Format", "Fandom", "X_vs_Y", "Status", "Views", "Likes", "Updated_At"])
                for topic in self.data.get("topics", {}).values():
                    pairs = topic.get("pairs", [])
                    pairs_str = " | ".join([f"{p[0]} vs {p[1]}" if len(p) >= 2 and p[1] else p[0] for p in pairs]) if pairs else ""
                    raw_status = topic.get("status", "").lower()
                    display_status = "POSTED" if raw_status in ["published", "posted"] else raw_status.upper()
                    writer.writerow([
                        topic.get("id", ""),
                        topic.get("title", ""),
                        topic.get("type", "").upper(),
                        topic.get("fandom", ""),
                        pairs_str,
                        display_status,
                        topic.get("view_count", 0),
                        topic.get("like_count", 0),
                        topic.get("updated_at", "")[:10]
                    ])
        except Exception as e:
            print(f"⚠️ Warning exporting CSV tracker: {e}")

    def seed_from_historical(self) -> None:
        """Populates tracker from historical YouTube Shorts transcripts and ideas config."""
        self.data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "topics": {}
        }

        # 1. Seed from transcripts.json (Published YouTube Shorts)
        if os.path.exists(self.transcripts_path):
            try:
                with open(self.transcripts_path, "r", encoding="utf-8") as f:
                    tdata = json.load(f)

                for item in tdata.get("shorts", []):
                    short_id = item.get("id")
                    title = item.get("title", "")
                    transcript = item.get("transcript", "")
                    duration = item.get("duration", 30)

                    # Extract pairs from title / transcript if possible
                    pairs = self._extract_pairs_from_text(title + " " + transcript)

                    self.data["topics"][short_id] = {
                        "id": short_id,
                        "title": title,
                        "type": "compilation" if ("terms" in title.lower() or "comp" in title.lower() or len(pairs) > 1) else "deepdive",
                        "status": "published",
                        "fandom": self._detect_fandom(title + " " + transcript),
                        "pairs": pairs,
                        "script": transcript,
                        "word_count": len(transcript.split()),
                        "duration_sec": duration,
                        "view_count": item.get("view_count", 0),
                        "like_count": item.get("like_count", 0),
                        "playbook_compliant": True,
                        "notes": f"Historical YouTube Short published on {item.get('upload_date', 'unknown')}",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
            except Exception as e:
                print(f"⚠️ Warning seeding from transcripts: {e}")

        # 2. Seed from config/ideas.json (Tested or Planned Ideas)
        if os.path.exists(self.ideas_path):
            try:
                with open(self.ideas_path, "r", encoding="utf-8") as f:
                    ideas_list = json.load(f)

                for idea in ideas_list:
                    idea_id = idea.get("id")
                    if not idea_id or idea_id in self.data["topics"]:
                        continue

                    title = idea.get("project_name", "")
                    script = idea.get("script", "")
                    labels = idea.get("labels", {})

                    pairs = []
                    if isinstance(labels, dict):
                        for k, v in labels.items():
                            if isinstance(v, list):
                                pairs.append(v)
                            elif isinstance(v, str):
                                pairs.append([v, ""])
                    elif isinstance(labels, list):
                        pairs.append(labels)

                    if not pairs:
                        pairs = self._extract_pairs_from_text(title + " " + script)

                    self.data["topics"][idea_id] = {
                        "id": idea_id,
                        "title": title,
                        "type": idea.get("type", "deepdive"),
                        "status": "tested" if idea_id == "SupermanVsShazam1" else "idea",
                        "fandom": self._detect_fandom(title + " " + script),
                        "pairs": pairs,
                        "script": script,
                        "word_count": len(script.split()),
                        "duration_sec": idea.get("estimated_duration", 30),
                        "playbook_compliant": True,
                        "notes": "Seeded from config/ideas.json",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
            except Exception as e:
                print(f"⚠️ Warning seeding from ideas.json: {e}")

        self.sync_generated_scripts()
        self.save()

    def _extract_pairs_from_text(self, text: str) -> List[List[str]]:
        """Helper to extract entity pairs (e.g. 'Thor vs Odin') from text."""
        pairs = []
        # Pattern 1: X vs Y
        vs_matches = re.findall(r"([A-Z][a-zA-Z0-9\s]+?)\s+(?:vs\.?|versus)\s+([A-Z][a-zA-Z0-9\s]+)", text, re.IGNORECASE)
        for m in vs_matches:
            pairs.append([m[0].strip(), m[1].strip()])

        # Pattern 2: This is X. This is Y.
        this_matches = re.findall(r"this is (?:the )?([^.]+?)\.\s*this is (?:the )?([^.]+?)\.", text, re.IGNORECASE)
        for m in this_matches:
            pairs.append([m[0].strip(), m[1].strip()])

        return pairs

    def _detect_fandom(self, text: str) -> str:
        """Detects fandom category from text."""
        txt_l = text.lower()
        if any(w in txt_l for w in ["marvel", "mcu", "thor", "odin", "vibranium", "adamantium", "iron man", "doctor doom", "wanda", "loki", "carnage", "venom", "spider"]):
            return "Marvel"
        if any(w in txt_l for w in ["dc", "dcu", "superman", "batman", "shazam", "joker", "flash", "aquaman", "darkseid"]):
            return "DC"
        if any(w in txt_l for w in ["naruto", "dragon ball", "goku", "saitama", "anime", "attack on titan"]):
            return "Anime"
        if any(w in txt_l for w in ["zeus", "poseidon", "dracula", "mythology", "vampire", "god"]):
            return "Mythology"
        return "PopCulture"

    def normalize_pair(self, pair: List[str]) -> Tuple[str, str]:
        """Normalizes an entity pair to lowercase sorted tuple for matching."""
        if not pair:
            return ("", "")
        e1 = re.sub(r"[^\w]", "", pair[0].lower())
        e2 = re.sub(r"[^\w]", "", pair[1].lower()) if len(pair) > 1 else ""
        return tuple(sorted([e1, e2]))  # type: ignore

    def is_duplicate(self, pairs: List[List[str]], title: str = "") -> Tuple[bool, Optional[str], str]:
        """
        Checks if candidate pairs or title duplicate an existing topic in tracker.

        Returns:
            (is_duplicate, matching_topic_id, reason)
        """
        new_norm_pairs = {self.normalize_pair(p) for p in pairs if p}
        title_clean = re.sub(r"[^\w\s]", "", title.lower()).strip()

        for topic_id, topic in self.data.get("topics", {}).items():
            status = topic.get("status")
            if status in ["rejected"]:
                continue  # Rejected ideas can potentially be reworked if requested, but let's check active ones

            # 1. Pair overlap check
            existing_pairs = topic.get("pairs", [])
            existing_norm_pairs = {self.normalize_pair(p) for p in existing_pairs if p}

            for np in new_norm_pairs:
                if np in existing_norm_pairs and np != ("", ""):
                    return True, topic_id, f"Entity pair {np} already covered in topic '{topic_id}' ({topic.get('title')}, status: {status})."

            # 2. Title similarity check
            ex_title = re.sub(r"[^\w\s]", "", topic.get("title", "").lower()).strip()
            if title_clean and ex_title:
                if title_clean == ex_title or (len(title_clean) > 8 and title_clean in ex_title):
                    return True, topic_id, f"Title '{title}' is nearly identical to existing topic '{topic_id}' (status: {status})."

        return False, None, ""

    def add_topic(self, topic_data: Dict[str, Any]) -> str:
        """Adds a new topic to tracker."""
        topic_id = topic_data.get("id") or f"topic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        topic_data["id"] = topic_id
        topic_data["created_at"] = topic_data.get("created_at") or datetime.now().isoformat()
        topic_data["updated_at"] = datetime.now().isoformat()
        topic_data["status"] = topic_data.get("status", "idea")

        self.data["topics"][topic_id] = topic_data
        self.save()
        return topic_id

    def update_status(self, topic_id: str, new_status: str, notes: Optional[str] = None) -> bool:
        """Updates status of a topic in tracker."""
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {self.VALID_STATUSES}")

        if topic_id in self.data["topics"]:
            self.data["topics"][topic_id]["status"] = new_status
            self.data["topics"][topic_id]["updated_at"] = datetime.now().isoformat()
            if notes:
                ex_notes = self.data["topics"][topic_id].get("notes", "")
                self.data["topics"][topic_id]["notes"] = f"{ex_notes} | {notes}".strip(" |")
            self.save()

            # Also sync generated_scripts JSON file if present
            gen_dir = os.path.join(os.path.dirname(self.tracker_path), "..", "generated_scripts")
            gen_file = os.path.join(gen_dir, f"{topic_id}.json")
            if os.path.exists(gen_file):
                try:
                    with open(gen_file, "r", encoding="utf-8") as f:
                        gf_data = json.load(f)
                    gf_data["status"] = new_status
                    gf_data["updated_at"] = datetime.now().isoformat()
                    if notes:
                        ex_n = gf_data.get("notes", "")
                        gf_data["notes"] = f"{ex_n} | {notes}".strip(" |")
                    with open(gen_file, "w", encoding="utf-8") as f:
                        json.dump(gf_data, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

            self.sync_to_ideas_json()
            return True
        return False

    def get_topics(self, status: Optional[str] = None, fandom: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns filtered list of topics."""
        result = []
        for t in self.data.get("topics", {}).values():
            if status and t.get("status") != status:
                continue
            if fandom and t.get("fandom", "").lower() != fandom.lower():
                continue
            result.append(t)
        return result

    def get_stats(self) -> Dict[str, int]:
        """Returns statistics breakdown by status."""
        stats = {s: 0 for s in self.VALID_STATUSES}
        stats["total"] = len(self.data.get("topics", {}))
        for t in self.data.get("topics", {}).values():
            st = t.get("status", "idea")
            if st in stats:
                stats[st] += 1
        return stats

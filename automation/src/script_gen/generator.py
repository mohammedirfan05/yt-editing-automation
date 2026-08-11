"""
Script generation orchestration for the dontmixthis channel (English).

Rewritten around three ideas the old version lacked:

  * The prompt is no longer a hardcoded template with one mandated opener. It is
    built by `dontmix_style.build_generation_prompt` from a rotating hook plan,
    a rotating CTA plan, and the openers of the last few scripts so the model is
    told explicitly what NOT to sound like.
  * A failing candidate is repaired, not silently dropped. Dropping was what
    pushed the pipeline into the rigid template catalog, which is where the
    robotic output came from. Each candidate now gets up to two repair passes
    with the validator's own findings handed back to the model.
  * `channel="farqkya"` delegates the entire call to FarqKyaScriptGenerator.
    The two channels share no prompt, no rules and no templates.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import dontmix_style as style
from .analyzer import ConceptCatalog
from .slop_rules import SlopEngine
from .templates import ScriptTemplates
from .tracker import ContentTracker
from .unslop_sanitizer import UnslopSanitizer
from .validator import PlaybookValidator

_DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "generated_scripts")

# Raised from 0.7. At 0.7 the model kept converging on the same sentence
# skeleton across a single batch; the slop rules now catch drift, so the
# sampler can be looser.
GEN_TEMPERATURE = 0.95
REPAIR_TEMPERATURE = 0.8
MAX_REPAIR_PASSES = 2


class ScriptGenerator:
    """Generates, repairs and validates dontmixthis scripts."""

    CHANNEL = "dontmixthis"

    def __init__(self, tracker: Optional[ContentTracker] = None,
                 output_dir: str = _DEFAULT_OUTPUT_DIR):
        self.tracker = tracker if tracker else ContentTracker()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------- history

    def _recent_topics(self, channel: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Most recent tracker entries for a channel, newest first."""
        topics = [t for t in self.tracker.data.get("topics", {}).values()
                  if t.get("channel", "dontmixthis") == channel and t.get("script")]
        topics.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        return topics[:limit]

    def _history(self, channel: str) -> Tuple[List[str], List[str], List[str]]:
        """(recent scripts, recent hook ids, recent CTAs) for rotation + reuse checks."""
        recent = self._recent_topics(channel)
        scripts = [t["script"] for t in recent]
        hook_ids: List[str] = []
        ctas: List[str] = []
        for t in recent:
            hid = t.get("hook_id")
            if not hid:
                hook = SlopEngine.detect_hook(t["script"], style.HOOKS)
                hid = hook.id if hook else None
            if hid:
                hook_ids.append(hid)
            sents = SlopEngine.sentences(t["script"])
            if sents:
                ctas.append(sents[-1])
        return scripts, hook_ids, ctas

    def _excluded_pairs(self) -> str:
        used = []
        for t in self.tracker.data.get("topics", {}).values():
            if t.get("status") in ("published", "posted", "approved"):
                for p in t.get("pairs", []):
                    if len(p) >= 2:
                        used.append(f"{p[0]} vs {p[1]}")
        return ", ".join(used) if used else "None"

    # -------------------------------------------------------------- gemini

    def _call_gemini(self, prompt: str, temperature: float) -> Optional[Dict[str, Any]]:
        """One JSON-mode Gemini call, walking the model fallback chain."""
        import requests
        from colorama import Fore, Style
        from src.env_utils import get_gemini_api_key
        from src.model_config import generate_content_url, get_text_model, model_chain

        api_key = get_gemini_api_key()
        if not api_key:
            return None

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.95,
                "responseMimeType": "application/json",
            },
        }
        last_status = None
        try:
            for model in model_chain(get_text_model()):
                r = requests.post(generate_content_url(model, api_key),
                                  headers={"Content-Type": "application/json"},
                                  json=payload, timeout=40)
                last_status = r.status_code
                if r.status_code == 200:
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text)
                print(Fore.YELLOW + f"⚠️ Gemini '{model}' returned {r.status_code}; "
                      "trying next model." + Style.RESET_ALL)
            print(Fore.YELLOW + f"⚠️ All Gemini models failed (last status {last_status})."
                  + Style.RESET_ALL)
        except Exception as e:
            print(Fore.YELLOW + f"⚠️ Gemini call error: {e}" + Style.RESET_ALL)
        return None

    def _generate_via_gemini_llm(self, count: int, target_deepdives: int,
                                 target_compilations: int,
                                 fandom: Optional[str] = None) -> List[Dict[str, Any]]:
        """Builds the rotating prompt and returns raw candidate topics."""
        scripts, hook_ids, ctas = self._history(self.CHANNEL)
        hook_plan = style.assign_hooks(count, hook_ids)
        cta_plan = [style.CTA_BANK[(len(ctas) + i) % len(style.CTA_BANK)]
                    for i in range(count)]
        recent_openers = [" ".join(SlopEngine.sentences(s)[:1]) for s in scripts[:6]]

        prompt = style.build_generation_prompt(
            count=count,
            target_deepdives=target_deepdives,
            target_compilations=target_compilations,
            hook_plan=hook_plan,
            cta_plan=cta_plan,
            excluded_pairs=self._excluded_pairs(),
            fandom=fandom,
            recent_openers=recent_openers,
        )
        parsed = self._call_gemini(prompt, GEN_TEMPERATURE) or {}
        topics = parsed.get("topics", []) or []
        # Carry the plan slot forward so the validator can see intent and the
        # repair pass can restate it.
        for i, t in enumerate(topics):
            t.setdefault("_planned_hook", hook_plan[i] if i < len(hook_plan) else None)
            t.setdefault("_planned_cta", cta_plan[i] if i < len(cta_plan) else None)
        return topics

    def _repair(self, script: str, title: str, issues: Sequence[str],
                hook_id: Optional[str], cta: Optional[str]) -> Optional[str]:
        """Hands the validator's findings back to the model for one rewrite."""
        hook = style.DONTMIXTHIS_RULES.hook_by_id(hook_id) if hook_id else None
        prompt = style.build_repair_prompt(
            script=script, title=title, issues=issues,
            required_hook=hook.brief if hook else None, required_cta=cta)
        parsed = self._call_gemini(prompt, REPAIR_TEMPERATURE)
        if not parsed:
            return None
        fixed = (parsed.get("script") or "").strip()
        return fixed or None

    # ---------------------------------------------------------------- main

    def generate_scripts(self, count: int = 2, mode: str = "auto",
                         fandom: Optional[str] = None,
                         channel: str = "dontmixthis") -> List[Dict[str, Any]]:
        """
        Produces up to `count` validated, non-duplicate scripts.

        `channel="farqkya"` is delegated wholesale to the Roman Urdu generator so
        the English prompt and rules never touch that channel.
        """
        if channel == "farqkya":
            from .farqkya_generator import FarqKyaScriptGenerator
            return FarqKyaScriptGenerator(
                tracker=self.tracker, output_dir=self.output_dir
            ).generate_scripts(count=count, mode=mode)

        from colorama import Fore, Style

        if mode == "auto":
            target_deepdives, target_compilations = (count + 1) // 2, count // 2
        elif mode == "deepdive":
            target_deepdives, target_compilations = count, 0
        else:
            target_deepdives, target_compilations = 0, count

        generated: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        n_deep = n_comp = 0

        recent_scripts, _, recent_ctas = self._history(self.CHANNEL)
        # Scripts accepted in this batch also count as "recent" for reuse checks.
        batch_scripts: List[str] = []

        for opp in self._generate_via_gemini_llm(
                count, target_deepdives, target_compilations, fandom):
            if len(generated) >= count:
                break

            opp_type = opp.get("type", "deepdive")
            title = opp.get("title", "")
            pairs = opp.get("pairs", [])
            planned_hook = opp.get("_planned_hook")
            planned_cta = opp.get("_planned_cta")

            is_dup, match_id, reason = self.tracker.is_duplicate(pairs, title)
            if is_dup:
                skipped.append({"source": "llm", "title": title, "why": "duplicate",
                                "detail": f"matches '{match_id}' ({reason})"})
                print(Fore.YELLOW + f"⏭  Skipped '{title}': duplicate of '{match_id}' "
                      f"({reason})." + Style.RESET_ALL)
                continue

            script_text = UnslopSanitizer.sanitize(opp.get("script", ""),
                                                   cta_bank=style.CTA_BANK)
            history = batch_scripts + recent_scripts
            ok, issues, metrics = PlaybookValidator.validate_script(
                script_text, mode=opp_type, recent_scripts=history,
                expected_hook=planned_hook, recent_ctas=recent_ctas)

            # Repair loop. The old code dropped the candidate here.
            passes = 0
            while not ok and passes < MAX_REPAIR_PASSES:
                passes += 1
                brief = PlaybookValidator.repair_brief(metrics)
                print(Fore.CYAN + f"↻  Repair pass {passes} on '{title}' "
                      f"({len(brief)} issue(s))." + Style.RESET_ALL)
                fixed = self._repair(script_text, title, brief, planned_hook, planned_cta)
                if not fixed:
                    break
                script_text = UnslopSanitizer.sanitize(fixed, cta_bank=style.CTA_BANK)
                ok, issues, metrics = PlaybookValidator.validate_script(
                    script_text, mode=opp_type, recent_scripts=history,
                    expected_hook=planned_hook, recent_ctas=recent_ctas)

            if not ok:
                skipped.append({"source": "llm", "title": title, "why": "slop_validation",
                                "detail": "; ".join(str(i) for i in issues)})
                print(Fore.YELLOW + f"⏭  Dropped '{title}' after {passes} repair pass(es):"
                      + Style.RESET_ALL)
                for issue in metrics.get("errors", []):
                    print(Fore.YELLOW + f"     - {issue}" + Style.RESET_ALL)
                continue

            entry = self._accept(opp, script_text, metrics, issues, opp_type,
                                 f"gen_{len(generated) + 1:02d}", repair_passes=passes)
            generated.append(entry)
            batch_scripts.insert(0, script_text)
            if entry.get("cta"):
                recent_ctas.insert(0, entry["cta"])
            n_deep += opp_type == "deepdive"
            n_comp += opp_type == "compilation"

        if len(generated) < count:
            generated += self._fill_from_catalog(
                count - len(generated), target_deepdives - n_deep,
                target_compilations - n_comp, fandom, skipped,
                batch_scripts + recent_scripts, recent_ctas)

        self._report(count, generated, skipped)
        return generated

    def _fill_from_catalog(self, needed: int, deep_left: int, comp_left: int,
                           fandom: Optional[str], skipped: List[Dict[str, Any]],
                           history: List[str],
                           recent_ctas: List[str]) -> List[Dict[str, Any]]:
        """
        Offline fallback. Still validated, so a template that reads as robotic is
        rejected here too rather than shipped as a filler script.
        """
        from colorama import Fore, Style
        out: List[Dict[str, Any]] = []
        for opp in ConceptCatalog.get_all_opportunities(channel=self.CHANNEL):
            if len(out) >= needed:
                break
            opp_type = opp.get("type", "deepdive")
            if opp_type == "deepdive" and deep_left <= 0:
                continue
            if opp_type == "compilation" and comp_left <= 0:
                continue
            opp_fandom = opp.get("fandom", "Marvel")
            if fandom and opp_fandom.lower() != fandom.lower():
                continue

            pairs, title = opp.get("pairs", []), opp.get("title", "")
            is_dup, match_id, reason = self.tracker.is_duplicate(pairs, title)
            if is_dup:
                skipped.append({"source": "catalog", "title": title,
                                "why": "duplicate",
                                "detail": f"matches '{match_id}' ({reason})"})
                continue

            if opp_type == "deepdive":
                raw = ScriptTemplates.render_deepdive(
                    entity_a=opp.get("entity_a", pairs[0][0] if pairs else "Entity A"),
                    entity_b=opp.get("entity_b",
                                     pairs[0][1] if pairs and len(pairs[0]) > 1 else "Entity B"),
                    template_id=opp.get("template_id", 1),
                    concept_hook=opp.get("concept_hook", ""),
                    mechanism_a=opp.get("mechanism_a", ""),
                    mechanism_b=opp.get("mechanism_b", ""),
                    punchline=opp.get("punchline", ""))
            else:
                raw = ScriptTemplates.render_compilation(pairs_data=opp.get("pairs_data", []))

            script_text = UnslopSanitizer.sanitize(raw, cta_bank=style.CTA_BANK)
            ok, issues, metrics = PlaybookValidator.validate_script(
                script_text, mode=opp_type, recent_scripts=history,
                recent_ctas=recent_ctas)
            if not ok:
                skipped.append({"source": "catalog", "title": title,
                                "why": "slop_validation",
                                "detail": "; ".join(str(i) for i in issues)})
                print(Fore.YELLOW + f"⏭  Catalog script '{title}' failed slop validation."
                      + Style.RESET_ALL)
                continue

            entry = self._accept(opp, script_text, metrics, issues, opp_type,
                                 opp["id"], source="catalog")
            out.append(entry)
            history.insert(0, script_text)
            if opp_type == "deepdive":
                deep_left -= 1
            else:
                comp_left -= 1
        return out

    def _accept(self, opp: Dict[str, Any], script_text: str, metrics: Dict[str, Any],
                issues: Sequence[str], opp_type: str, fallback_id: str,
                source: str = "llm", repair_passes: int = 0) -> Dict[str, Any]:
        """Writes the artifact, records it in the tracker, returns the entry."""
        topic_id = opp.get("id", fallback_id)
        pairs = opp.get("pairs", [])
        title = opp.get("title", "")
        now = datetime.now().isoformat()
        entry = {
            "id": topic_id,
            "title": title,
            "type": opp_type,
            "channel": self.CHANNEL,
            "status": "idea",
            "fandom": opp.get("fandom", "Marvel"),
            "pairs": pairs,
            "script": script_text,
            "word_count": metrics.get("word_count", 0),
            "estimated_duration_sec": metrics.get("estimated_duration_sec", 0.0),
            "speech_pacing_wps": metrics.get("speech_pacing_wps", 2.7),
            "playbook_compliant": metrics.get("is_compliant", True),
            "unslop_sanitized": True,
            "validation_issues": list(issues),
            # Slop telemetry, so the next batch can rotate away from this one.
            "hook_id": metrics.get("hook_id"),
            "cta": metrics.get("cta"),
            "payoff": metrics.get("payoff"),
            "payoff_echo": metrics.get("payoff_echo"),
            "max_body_overlap": metrics.get("max_body_overlap"),
            "rhythm": metrics.get("rhythm"),
            "source": source,
            "repair_passes": repair_passes,
            "labels": self._build_labels(pairs, opp_type),
            "seo_metadata": opp.get("seo_metadata") or self._generate_default_seo_package(
                title, pairs, script_text, channel=self.CHANNEL),
            "created_at": now,
            "updated_at": now,
        }
        artifact_path = os.path.join(self.output_dir, f"{topic_id}.json")
        with open(artifact_path, "w", encoding="utf-8") as fh:
            json.dump(entry, fh, indent=2, ensure_ascii=False)
        entry["artifact_path"] = artifact_path
        self.tracker.add_topic(entry)
        return entry

    def _report(self, count: int, generated: List[Dict[str, Any]],
                skipped: List[Dict[str, Any]]) -> None:
        from colorama import Fore, Style
        if len(generated) < count:
            dup_n = sum(1 for s in skipped if s["why"] == "duplicate")
            val_n = sum(1 for s in skipped if s["why"] == "slop_validation")
            print(Fore.RED + f"\n⚠️  Shortfall: requested {count}, produced "
                  f"{len(generated)}." + Style.RESET_ALL)
            print(Fore.RED + f"    Rejected {len(skipped)}: {dup_n} duplicate, "
                  f"{val_n} failed slop validation." + Style.RESET_ALL)
            for s in skipped:
                print(Fore.RED + f"    [{s['source']}] {s['title'] or '(untitled)'} -> "
                      f"{s['why']}: {s['detail']}" + Style.RESET_ALL)
        elif skipped:
            print(Fore.CYAN + f"ℹ️  Produced {len(generated)}/{count} "
                  f"({len(skipped)} rejected along the way)." + Style.RESET_ALL)

    # -------------------------------------------------------------- helpers

    def _generate_default_seo_package(self, title: str, pairs: List[List[str]],
                                      script_text: str,
                                      channel: str = "dontmixthis") -> Dict[str, Any]:
        p_str = f"{pairs[0][0]} vs {pairs[0][1]}" if pairs and len(pairs[0]) >= 2 else title
        a = pairs[0][0] if pairs and pairs[0] else "Entity A"
        b = pairs[0][1] if pairs and len(pairs[0]) >= 2 else "Entity B"
        return {
            "seo_title": f"{p_str}: What's the Difference?",
            "ab_title": f"The Real Difference Between {p_str}",
            "thumbnail_text": f"{p_str} Difference!",
            "hashtags": ["#Shorts", "#DontMixThis", "#PopCulture"],
            "description": f"What's the real difference between {p_str}? "
                           "Watch this 30-second breakdown.",
            "pinned_comment": f"Which one do you prefer: {a} or {b}? Let us know!",
        }

    def _build_labels(self, pairs: List[List[str]], mode: str) -> Dict[str, Any]:
        """Label structure the CapCut builder consumes. Format unchanged."""
        if mode == "deepdive" and pairs and len(pairs[0]) >= 2:
            return {"label1": pairs[0][0], "label2": pairs[0][1]}
        if mode == "compilation" and pairs:
            return {f"pair{i}": [p[0], p[1]]
                    for i, p in enumerate(pairs, 1) if len(p) >= 2}
        return {}

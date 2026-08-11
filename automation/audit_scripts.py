"""
Re-runs the slop rule packs over every script in config/content_tracker.json.

This is the reproducible form of the Step 1 audit. It answers three questions:

  1. Which slop codes actually fire on this channel's history, and how often?
     (A rule that never fires is dead weight; a rule that fires on 90% of
     scripts is measuring the channel's voice, not a defect.)
  2. Which specific scripts are the worst offenders, so a threshold change can
     be sanity-checked against real text instead of a guess.
  3. Do the in-repo gold examples still pass the rules their own prompt states?

Usage:
    python audit_scripts.py                  # both channels, summary
    python audit_scripts.py --channel farqkya --detail
    python audit_scripts.py --gold           # validate few-shot examples only
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.script_gen import dontmix_style, farqkya_style  # noqa: E402
from src.script_gen.farqkya_validator import FarqKyaValidator  # noqa: E402
from src.script_gen.validator import PlaybookValidator  # noqa: E402

TRACKER = Path(__file__).resolve().parent / "config" / "content_tracker.json"

CHANNELS = {
    "dontmixthis": (PlaybookValidator, dontmix_style),
    "farqkya": (FarqKyaValidator, farqkya_style),
}


def _load_topics() -> List[Dict[str, Any]]:
    data = json.loads(TRACKER.read_text(encoding="utf-8"))
    topics = list(data.get("topics", {}).values())
    topics.sort(key=lambda t: t.get("created_at") or "")
    return [t for t in topics if (t.get("script") or "").strip()]


def _channel_of(topic: Dict[str, Any]) -> str:
    return topic.get("channel") or "dontmixthis"


def _code(issue: str) -> str:
    """'[ERROR] payoff.echo: text' -> 'payoff.echo'"""
    body = issue.split("] ", 1)[-1]
    return body.split(":", 1)[0].strip()


def _audit_channel(channel: str, topics: List[Dict[str, Any]],
                   detail: bool) -> Tuple[int, int]:
    validator, _ = CHANNELS[channel]
    rows: List[Tuple[str, bool, List[str], Dict[str, Any]]] = []
    err_codes: Counter = Counter()
    warn_codes: Counter = Counter()
    history: List[str] = []

    for topic in topics:
        mode = "compilation" if topic.get("type") == "compilation" else "deepdive"
        ok, issues, metrics = validator.validate_script(
            topic["script"], mode=mode, recent_scripts=list(reversed(history)))
        history.append(topic["script"])
        for issue in issues:
            (err_codes if issue.startswith("[ERROR]") else warn_codes)[_code(issue)] += 1
        rows.append((topic.get("id", "?"), ok, issues, metrics))

    failed = sum(1 for _, ok, _, _ in rows if not ok)
    print(f"\n{'=' * 72}\n{channel}: {len(rows)} scripts, "
          f"{failed} fail ({failed / max(1, len(rows)):.0%})\n{'=' * 72}")

    print("\n  blocking codes (script count):")
    for code, n in err_codes.most_common():
        print(f"    {n:>4}x  {code}")
    print("\n  advisory codes:")
    for code, n in warn_codes.most_common():
        print(f"    {n:>4}x  {code}")

    wcs = [m["word_count"] for _, _, _, m in rows]
    stdevs = [m["rhythm"]["stdev"] for _, _, _, m in rows if m.get("rhythm")]
    echoes = [m["payoff_echo"] for _, _, _, m in rows if "payoff_echo" in m]
    print(f"\n  word_count   min {min(wcs)} / max {max(wcs)}")
    if stdevs:
        print(f"  rhythm stdev min {min(stdevs)} / max {max(stdevs)}")
    if echoes:
        print(f"  payoff echo  min {min(echoes)} / max {max(echoes)}")
    if channel == "farqkya":
        vfr = [m["verb_final_ratio"] for _, _, _, m in rows if "verb_final_ratio" in m]
        if vfr:
            print(f"  verb-final   min {min(vfr)} / max {max(vfr)}")

    if detail:
        for sid, ok, issues, _ in rows:
            if ok and not issues:
                continue
            print(f"\n  {sid}  {'PASS' if ok else 'FAIL'}")
            for issue in issues:
                print(f"      {issue}")
    return len(rows), failed


def _audit_gold(channel: str) -> int:
    """Gold few-shot examples must pass the rules they are meant to teach."""
    validator, style = CHANNELS[channel]
    print(f"\n{'=' * 72}\n{channel} gold examples\n{'=' * 72}")
    bad = 0
    history: List[str] = []
    for i, gold in enumerate(style.GOLD_EXAMPLES, 1):
        ok, issues, metrics = validator.validate_script(
            gold["script"], mode="deepdive", recent_scripts=list(reversed(history)),
            expected_hook=gold.get("hook"))
        history.append(gold["script"])
        errs = [x for x in issues if x.startswith("[ERROR]")]
        bad += len(errs)
        print(f"  gold {i} [{gold.get('hook')}] {'PASS' if ok else 'FAIL'}  "
              f"wc={metrics['word_count']} stdev={metrics['rhythm']['stdev']} "
              f"echo={metrics.get('payoff_echo')}")
        for issue in issues:
            print(f"      {issue}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--channel", choices=sorted(CHANNELS), default=None,
                    help="audit one channel instead of both")
    ap.add_argument("--detail", action="store_true",
                    help="print every finding per script")
    ap.add_argument("--gold", action="store_true",
                    help="validate the few-shot gold examples instead of history")
    args = ap.parse_args()

    channels = [args.channel] if args.channel else sorted(CHANNELS)

    if args.gold:
        bad = sum(_audit_gold(c) for c in channels)
        print(f"\ngold blocking errors: {bad}")
        return 1 if bad else 0

    topics = _load_topics()
    total = failed = 0
    for channel in channels:
        subset = [t for t in topics if _channel_of(t) == channel]
        if not subset:
            print(f"\n{channel}: no scripts in tracker")
            continue
        n, f = _audit_channel(channel, subset, args.detail)
        total += n
        failed += f
    print(f"\n{'=' * 72}\n{failed}/{total} scripts fail the current rule packs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

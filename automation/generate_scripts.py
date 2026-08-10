#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
⚡ Script Generator Pipeline for YouTube Shorts
Generates high-potential X vs Y concepts and scripts strictly adhering to docs/viral_shorts_playbook.md
and historical performance data from published Shorts.

Usage:
  python generate_scripts.py                         # Generates 3 Playbook-compliant scripts
  python generate_scripts.py --count 5               # Generates 5 scripts
  python generate_scripts.py --mode deepdive         # Generates Deepdive scripts (1 pair)
  python generate_scripts.py --mode compilation      # Generates Compilation scripts (3 pairs)
  python generate_scripts.py --fandom Marvel         # Filter by fandom category
  python generate_scripts.py --seed-tracker          # Seeds content tracker with 24 published Shorts
  python generate_scripts.py --list-tracker          # Displays tracker summary stats
  python generate_scripts.py --approve <topic_id>    # Marks candidate topic as approved
  python generate_scripts.py --reject <topic_id>     # Marks candidate topic as rejected
"""

import argparse
import json
import os
import sys

# UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from colorama import Fore, Style, init

from src.script_gen.generator import ScriptGenerator
from src.script_gen.tracker import ContentTracker

init(autoreset=True)


def main():
    parser = argparse.ArgumentParser(description="Script Generator Pipeline for YouTube Shorts")
    parser.add_argument("--count", "-n", type=int, default=3, help="Number of scripts to generate")
    parser.add_argument("--mode", "-m", type=str, default="auto", choices=["auto", "deepdive", "compilation"], help="Script mode")
    parser.add_argument("--fandom", "-f", type=str, default=None, help="Filter by fandom (Marvel, DC, Anime, Mythology, Islamic)")
    parser.add_argument("--channel", "-c", type=str, default="dontmixthis", choices=["dontmixthis", "farqkya"], help="Select YouTube channel ('dontmixthis' or 'farqkya')")
    parser.add_argument("--seed-tracker", action="store_true", help="Initialize/re-seed content tracker from historical transcripts")

    parser.add_argument("--list-tracker", action="store_true", help="Display content tracker status breakdown")
    parser.add_argument("--approve", type=str, help="Mark topic ID as approved in tracker")
    parser.add_argument("--reject", type=str, help="Mark topic ID as rejected in tracker")
    parser.add_argument("--publish", type=str, help="Mark topic ID as published in tracker")

    args = parser.parse_args()

    tracker = ContentTracker()

    # Handle tracker seeding
    if args.seed_tracker:
        print(Fore.CYAN + "🔄 Seeding Content Tracker from historical YouTube transcripts & ideas..." + Style.RESET_ALL)
        tracker.seed_from_historical()
        stats = tracker.get_stats()
        print(Fore.GREEN + f"✨ Tracker seeded successfully! Total topics: {stats['total']} (Published: {stats['published']}, Tested: {stats['tested']}, Ideas: {stats['idea']})" + Style.RESET_ALL)
        return

    # Handle status updates
    if args.approve:
        ok = tracker.update_status(args.approve, "approved", notes="Manually approved by user")
        if ok:
            print(Fore.GREEN + f"✓ Marked topic '{args.approve}' as APPROVED." + Style.RESET_ALL)
        else:
            print(Fore.RED + f"❌ Topic ID '{args.approve}' not found in tracker." + Style.RESET_ALL)
        return

    if args.reject:
        ok = tracker.update_status(args.reject, "rejected", notes="Rejected during user review")
        if ok:
            print(Fore.YELLOW + f"✓ Marked topic '{args.reject}' as REJECTED." + Style.RESET_ALL)
        else:
            print(Fore.RED + f"❌ Topic ID '{args.reject}' not found in tracker." + Style.RESET_ALL)
        return

    if args.publish:
        ok = tracker.update_status(args.publish, "published", notes="Published on YouTube")
        if ok:
            print(Fore.CYAN + f"✓ Marked topic '{args.publish}' as PUBLISHED." + Style.RESET_ALL)
        else:
            print(Fore.RED + f"❌ Topic ID '{args.publish}' not found in tracker." + Style.RESET_ALL)
        return

    # Handle listing tracker stats
    if args.list_tracker:
        print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)
        print(Fore.CYAN + Style.BRIGHT + "📊 CONTENT TRACKER LIFECYCLE SUMMARY" + Style.RESET_ALL)
        print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)
        stats = tracker.get_stats()
        print(f"  • Published (YouTube) : {Fore.GREEN}{stats['published']}{Style.RESET_ALL}")
        print(f"  • Approved Candidates : {Fore.CYAN}{stats['approved']}{Style.RESET_ALL}")
        print(f"  • Tested in Sandbox   : {Fore.YELLOW}{stats['tested']}{Style.RESET_ALL}")
        print(f"  • Ideas Queue        : {Fore.BLUE}{stats['idea']}{Style.RESET_ALL}")
        print(f"  • Rejected           : {Fore.RED}{stats['rejected']}{Style.RESET_ALL}")
        print(f"  • Total Tracked      : {stats['total']}")

        print(Fore.CYAN + "\nRecent Topics in Tracker:" + Style.RESET_ALL)
        topics = list(tracker.data.get("topics", {}).values())[-10:]
        for t in topics:
            status_color = Fore.GREEN if t['status'] == 'published' else (Fore.CYAN if t['status'] == 'approved' else Fore.YELLOW)
            print(f"  [{status_color}{t['status'].upper():<9}{Style.RESET_ALL}] {t['id']:<15} | {t['title']} ({t['type'].upper()})")
        print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL + "\n")
        return

    # Main Script Generation
    print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + "⚡ YOUTUBE SHORTS SCRIPT GENERATOR PIPELINE" + Style.RESET_ALL)
    print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)

    generator = ScriptGenerator(tracker=tracker)
    results = generator.generate_scripts(count=args.count, mode=args.mode, fandom=args.fandom, channel=args.channel)

    if not results:
        print(Fore.YELLOW + "⚠️ No new non-duplicate scripts could be generated matching criteria." + Style.RESET_ALL)
        print(Fore.YELLOW + "   All concept opportunities may already exist in the tracker." + Style.RESET_ALL)
        return

    print(Fore.GREEN + Style.BRIGHT + f"\n✨ GENERATED {len(results)} PLAYBOOK-COMPLIANT SCRIPTS:\n" + Style.RESET_ALL)

    for idx, item in enumerate(results, 1):
        print(Fore.CYAN + f"[{idx}/{len(results)}] {item['title']} (ID: {item['id']})" + Style.RESET_ALL)
        print(f"  • Mode: {item['type'].upper()} | Fandom: {item['fandom']}")
        print(f"  • Word Count: {item['word_count']} words | Duration: ~{item['estimated_duration_sec']}s (Pacing: {item['speech_pacing_wps']} W/s)")
        print(f"  • Playbook Compliant: {Fore.GREEN if item['playbook_compliant'] else Fore.RED}{item['playbook_compliant']}{Style.RESET_ALL}")
        print(f"  • Saved File: {item['artifact_path']}")
        print(Fore.YELLOW + "\n--- SCRIPT TEXT ---" + Style.RESET_ALL)
        print(item["script"])
        print(Fore.YELLOW + "-------------------\n" + Style.RESET_ALL)

    print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL)
    print(Fore.GREEN + Style.BRIGHT + "✓ Script generation complete. Scripts are ready for your manual review." + Style.RESET_ALL)
    print(Fore.CYAN + "  To approve a script: python generate_scripts.py --approve <topic_id>" + Style.RESET_ALL)
    print(Fore.CYAN + "  To reject a script : python generate_scripts.py --reject <topic_id>" + Style.RESET_ALL)
    print(Fore.MAGENTA + "=" * 70 + Style.RESET_ALL + "\n")


if __name__ == "__main__":
    main()

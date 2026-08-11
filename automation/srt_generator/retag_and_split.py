#!/usr/bin/env python3
"""
retag_and_split.py  --  SRT <=4-word splitter + smart mascot pose tagger
=========================================================================
Standalone post-processor for the yt-editing-automation pipeline.
Run AFTER Whisper transcription, BEFORE build_draft.py.

Usage:
    python srt_generator/retag_and_split.py                         # processes input/script.srt in-place
    python srt_generator/retag_and_split.py -i my.srt -o out.srt   # custom paths
    python srt_generator/retag_and_split.py --dry-run               # print result, don't save

Fixes two problems in the tagging step:

1. MAX-4-WORD SPLIT
   Every SRT entry is guaranteed to show <=4 words on screen.
   Timing is redistributed proportionally by word-count.
   Splits prefer comma/semicolon boundaries, then conjunctions.
   Avoids single-word orphan fragments where possible.

2. SMART POSE TAGGING WITH BEAT-HOLDING
   Poses are matched to the *meaning* of the original sentence (before
   splitting), not to surface keywords of tiny carry-over fragments.
   A pose holds for the duration of a coherent beat (>=2 entries by default)
   and only changes when the semantic content genuinely shifts.

Available mascot poses (must match files in assets/mascot/):
    left          - introducing / explaining Entity A (Topic 1)
    right         - introducing / explaining Entity B (Topic 2)
    wtd           - question / curiosity / comparison
    disagree      - negation, debunk, "They don't."
    remember_this - key takeaway, tip, core rule (late-script only)
    shocked       - surprising / jaw-dropping fact
    twohandsopen  - discussing both entities equally
    normal        - neutral filler / transition
    final_end     - outro / CTA / subscribe (last entry only)
"""

import argparse
import os
import re
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_IN   = os.path.join(PROJECT_ROOT, "input", "script.srt")
DEFAULT_OUT  = os.path.join(PROJECT_ROOT, "input", "script.srt")

MAX_WORDS = 4   # hard cap: no entry may display more than this many words
MIN_HOLD  = 2   # minimum consecutive entries before a pose change is allowed

# ---------------------------------------------------------------------------
# SRT helpers
# ---------------------------------------------------------------------------
def ts_to_ms(ts: str) -> int:
    ts = ts.strip().replace(".", ",")
    hms, ms = ts.rsplit(",", 1)
    h, m, s = hms.split(":")
    return int(h)*3_600_000 + int(m)*60_000 + int(s)*1_000 + int(ms)

def ms_to_ts(ms: int) -> str:
    ms = max(0, int(ms))
    h = ms // 3_600_000; ms -= h*3_600_000
    m = ms //    60_000; ms -= m*60_000
    s = ms //     1_000; ms -= s*1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

TAG_RE = re.compile(r"\[IMG:[^\]]+\]")

def strip_tags(text: str) -> str:
    return TAG_RE.sub("", text).strip()

def parse_srt(content: str) -> list:
    blocks  = re.split(r"\n\s*\n", content.strip().replace("\r\n", "\n"))
    entries = []
    for b in blocks:
        lines = [l.strip() for l in b.strip().splitlines() if l.strip()]
        if len(lines) < 3 or not lines[0].isdigit():
            continue
        m = re.match(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
            lines[1]
        )
        if not m:
            continue
        raw_text = " ".join(lines[2:])
        tm = TAG_RE.search(raw_text)
        entries.append({
            "index":    int(lines[0]),
            "start_ms": ts_to_ms(m.group(1)),
            "end_ms":   ts_to_ms(m.group(2)),
            "text":     strip_tags(raw_text),
            "tag":      tm.group(0) if tm else None,
        })
    return entries

def render_srt(entries: list) -> str:
    out = []
    for i, e in enumerate(entries, 1):
        tag = f" {e['tag']}" if e.get("tag") else ""
        out += [str(i),
                f"{ms_to_ts(e['start_ms'])} --> {ms_to_ts(e['end_ms'])}",
                f"{e['text']}{tag}",
                ""]
    return "\n".join(out)

# ---------------------------------------------------------------------------
# Step 1: split entries to <= MAX_WORDS
# ---------------------------------------------------------------------------
_SOFT_PUNCT = {",", ";"}
_CONJ_SET   = {"and","but","or","so","yet","while","because","that","when",
               "if","as","to","for","with"}

def _chunk_words(words: list, max_w: int) -> list:
    """Greedy splitter: produce chunks of <=max_w words, avoiding single-word orphans."""
    if len(words) <= max_w:
        return [list(words)]
    chunks, rem = [], list(words)
    while len(rem) > max_w:
        window = rem[:max_w + 1]
        cut    = max_w
        # prefer cutting after soft punctuation
        for i in range(max_w, 0, -1):
            if i <= len(window)-1 and window[i-1] and window[i-1][-1] in _SOFT_PUNCT:
                cut = i; break
        else:
            # prefer cutting before conjunction (keeps it with next chunk)
            for i in range(max_w, 0, -1):
                if i < len(window) and window[i].lower() in _CONJ_SET:
                    cut = i; break
        # avoid single-word orphan on next iteration
        if len(rem) - cut == 1 and cut - 1 >= 1:
            cut -= 1
        cut = max(1, cut)
        chunks.append(rem[:cut])
        rem = rem[cut:]
    if rem:
        chunks.append(rem)
    return chunks

def _split_entry_with_role(e: dict, role: str, max_w: int) -> list:
    """Split one entry; every chunk inherits the parent sentence's semantic role."""
    words = e["text"].split()
    if len(words) <= max_w:
        piece = dict(e); piece["role"] = role
        return [piece]
    chunks    = _chunk_words(words, max_w)
    total_w   = len(words)
    total_dur = e["end_ms"] - e["start_ms"]
    cursor    = e["start_ms"]
    result    = []
    for ci, chunk in enumerate(chunks):
        dur    = round(total_dur * len(chunk) / total_w)
        end_ms = e["end_ms"] if ci == len(chunks)-1 else cursor + dur
        result.append({
            "start_ms": cursor,
            "end_ms":   end_ms,
            "text":     " ".join(chunk),
            "tag":      None,
            "role":     role,
        })
        cursor = end_ms
    return result

# ---------------------------------------------------------------------------
# Step 2: semantic classification + beat-holding pose tagging
# ---------------------------------------------------------------------------
_STOP = {
    "this","the","is","are","was","were","a","an","and","but","or","so",
    "it","its","that","have","has","had","do","does","did","with","for",
    "from","to","in","on","of","at","as","by","be","not","they","he","she",
    "we","you","i","my","his","her","our","their","while","can","still","get",
    "all","also","both","just","only","even","than","most","people","think",
    "same","own","cloned","was",
    # Urdu stop words (Roman + Arabic script)
    "ye","yeh","hai","hain","ko","par","mein","main","se","ka","ki","ke","ek","hi","kar","raha","huye","aur","ya","is","us","jo","jis","bhi","tarah","log","aakhir",
    "یہ","ہے","ہیں","کو","پر","میں","سے","کا","کی","کے","ایک","ہی","کر","رہا","ہوئے","اور","یا","اس","ان","جو","جس","بھی","طرح","لوگ","آخر"
}

def _norm(w: str) -> str:
    """Lowercase, strip punctuation and possessive 's."""
    w = w.lower().strip(".,!?;:'\"-،؟")
    return w[:-2] if w.endswith("'s") else w

def _detect_entities(orig: list):
    """Extract Entity-A and Entity-B keyword sets from first left/right tagged entries or opening lines."""
    ea, eb = set(), set()
    for e in orig:
        if not e.get("tag"):
            continue
        m = re.search(r"\[IMG:([^\]]+)\]", e["tag"])
        if not m:
            continue
        code  = m.group(1).strip().lower()
        words = {_norm(w) for w in e["text"].split() if len(_norm(w)) > 1} - _STOP
        if   code == "left"  and not ea: ea = words
        elif code == "right" and not eb: eb = words

    # Fallback entity detection from script intro text if left/right tags were not set
    if not ea or not eb:
        full_intro = " ".join([e["text"] for e in orig[:4]])
        low = full_intro.lower()

        # Urdu hook pattern (Roman + Arabic script): Ye hai X aur ye hai Y / یہ ہے X اور یہ ہے Y
        m_urdu = re.search(r"(?:ye|یہ)\s+(?:hai|ہے)\s+([^\s]+(?:\s+[^\s]+)?)\s+(?:aur|اور)\s+(?:ye|یہ)\s+(?:hai|ہے)\s+([^\s]+(?:\s+[^\s]+)?)", low)
        if m_urdu:
            if not ea: ea = {_norm(w) for w in m_urdu.group(1).split() if len(_norm(w)) > 1} - _STOP
            if not eb: eb = {_norm(w) for w in m_urdu.group(2).split() if len(_norm(w)) > 1} - _STOP

        # English hook pattern: This is X. This is Y.
        m_eng = re.search(r"this\s+is\s+([a-z0-9]+(?:\s+[a-z0-9]+)?).*?this\s+is\s+([a-z0-9]+(?:\s+[a-z0-9]+)?)", low)
        if m_eng:
            if not ea: ea = {_norm(w) for w in m_eng.group(1).split() if len(_norm(w)) > 1} - _STOP
            if not eb: eb = {_norm(w) for w in m_eng.group(2).split() if len(_norm(w)) > 1} - _STOP

    return ea, eb

def _score(text: str, eset: set) -> int:
    if not eset: return 0
    return sum(1 for w in text.split() if _norm(w) in eset)

_ROLE_POSE = {
    "entity_a":   "left",
    "entity_b":   "right",
    "question":   "wtd",
    "negation":   "disagree",
    "contrast_b": "right",
    "contrast_a": "left",
    "takeaway":   "remember_this",
    "closing":    "final_end",
    "shocked":    "shocked",
    "both":       "twohandsopen",
    "neutral":    "normal",
}

_POSE_TO_ROLE = {v: k for k, v in _ROLE_POSE.items()}

_SHORT_HOLD_POSES = {"disagree", "wtd", "shocked"}  # can be overridden after 1 hold
_AWKWARD = {("wtd","disagree"), ("shocked","disagree"),
            ("remember_this","left"), ("remember_this","right")}
_ENTITY_ROLES = {"entity_a","entity_b","contrast_a","contrast_b"}

_CLO = {"follow","subscribe","comment","share","karein","karo","sub","chahiyen","channel","فالو","سبسکرائب","شئیر"}
# Weak CTA words that also occur in ordinary comparison copy ("more powerful", "zyada").
# Only count as a closing signal inside the outro zone, and only alongside another CTA token.
_CLO_WEAK = {"more","zyada","again","phir"}
_KEY = {"remember","key","tip","rule","important","lesson","takeaway","conclusion","yaad","khayal","zaroori","farz","aam","nisaab","rukn","یاد","فرض","نصاب","خیرات"}
_NEG = ["don't","doesn't","didn't","can't","cannot","they don","no","nope","nahi","nahin","naah","lekin aisa nahi","aisa nahi","galat","نہیں","نہ"]

# Match _NEG patterns on whole-word boundaries only. Plain `in` matching made "no"
# fire on know / now / canon / nothing, flipping the mascot to `disagree` on neutral lines.
_NEG_RE = re.compile(
    "|".join(r"(?<!\w)" + re.escape(p) + r"(?!\w)" for p in _NEG),
    re.IGNORECASE
)

# A closing/CTA pose before the payoff reads as "video's over" and costs the ending.
# Only allow `closing` in the final stretch of the timeline.
_CLO_POSITION_GATE = 0.80

def _classify(text: str, ea: set, eb: set, existing_tag: str = None,
              position: float = None) -> str:
    """Classify one original SRT sentence into a semantic role.

    position: 0.0-1.0 location of this entry in the timeline, used to gate
    outro-only roles. None disables the gate (treats the entry as outro-eligible).
    """
    in_outro_zone = position is None or position >= _CLO_POSITION_GATE

    # If SRT block already has an explicit valid pose tag, preserve its semantic role
    if existing_tag:
        m = re.search(r"\[IMG:([^\]]+)\]", existing_tag)
        if m:
            pose_code = m.group(1).strip().lower()
            if pose_code in _POSE_TO_ROLE and pose_code != "normal":
                # Never honour an upstream final_end before the outro zone.
                if not (pose_code == "final_end" and not in_outro_zone):
                    return _POSE_TO_ROLE[pose_code]

    low   = text.lower()
    words = low.split()
    wset  = {_norm(w) for w in words}
    rw    = [_norm(w) for w in words]

    strong_clo = wset & _CLO
    weak_clo   = wset & _CLO_WEAK
    if in_outro_zone and (strong_clo or (weak_clo and len(weak_clo) >= 2)):
        return "closing"
    if wset & _KEY or ("that" in wset and "why" in wset): return "takeaway"
    if "?" in text or "؟" in text or any(qp in low for qp in ["farq kya", "kya hai", "kon hai", "konsa", "kaise", "kyun", "what's the difference", "فرق"]): return "question"
    if _NEG_RE.search(low): return "negation"
    if low.strip().rstrip(".!?") in {"they don't","they dont","no","nope","lekin aisa nahi hai","aisa nahi hai","nahi hai"}: return "negation"

    # Contrast: sentence STARTS with a pivot word
    if rw and rw[0] in {"but","however","whereas","unlike","yet","despite","instead","while","lekin","magar","jabke","par","لیکن","مگر","جبکہ"}:
        b = _score(text, eb); a = _score(text, ea)
        if b > 0 and b >= a: return "contrast_b"
        if a > 0 and a > b:  return "contrast_a"
        return "contrast_b"  # default: pivot usually introduces Entity B

    a = _score(text, ea); b = _score(text, eb)
    # Downweight entity_a mention in subordinate position
    lower_words = low.split()
    for i, w in enumerate(lower_words):
        if _norm(w) in ea and i > 0 and lower_words[i-1] in {"from","like","unlike","se","pe"}:
            a -= 1
    a = max(0, a)

    if a > 0 and b > 0: return "both"
    if a > b:           return "entity_a"
    if b > a:           return "entity_b"
    return "neutral"

def build_tagged_entries(orig: list, min_hold: int = MIN_HOLD,
                         max_words: int = MAX_WORDS, verbose: bool = False) -> list:
    """
    Full pipeline:
      1. Classify every original SRT entry on its complete sentence.
      2. Forward-fill neutral entries from the current entity beat.
      3. Split each entry to <=max_words chunks (inheriting parent role).
      4. Apply beat-holding pose assignment.
    """
    ea, eb = _detect_entities(orig)
    if verbose:
        print(f"[retag] Entity A: {ea}", file=sys.stderr)
        print(f"[retag] Entity B: {eb}", file=sys.stderr)

    n = len(orig)

    # --- classify original sentences ---
    # position gates outro-only roles (closing/final_end) to the tail of the timeline
    roles = [
        _classify(e["text"], ea, eb, e.get("tag"),
                  position=(i / (n - 1) if n > 1 else 1.0))
        for i, e in enumerate(orig)
    ]
    roles[-1] = "closing"

    # --- forward-fill neutral entries from current entity beat ---
    filled = list(roles)
    beat   = None
    for i in range(n):
        r = filled[i]
        if r in _ENTITY_ROLES:        beat = r
        elif r in {"negation","question"}: beat = None   # punctuation resets beat
        elif r == "neutral" and beat:  filled[i] = beat

    if verbose:
        for i, (e, r) in enumerate(zip(orig, filled), 1):
            print(f"[retag] {i:2d}  {r:<12}  {e['text']!r}", file=sys.stderr)

    # --- split with role inheritance ---
    all_chunks: list = []
    for e, role in zip(orig, filled):
        all_chunks.extend(_split_entry_with_role(e, role, max_words))

    total = len(all_chunks)
    poses = [_ROLE_POSE.get(c["role"], "normal") for c in all_chunks]

    # --- beat-holding pass ---
    hold = 1
    for i in range(1, total):
        if i == total - 1:                                 # last entry always final_end
            poses[i] = "final_end"; continue
        prev, curr = poses[i-1], poses[i]
        if curr == "remember_this" and i < int(0.75 * total):   # guard early takeaway
            poses[i] = prev; hold += 1; continue
        if curr == prev:
            hold += 1; continue

        role_i = all_chunks[i]["role"]
        # Strong semantic signal: entity / question / negation can break hold early
        if role_i in {"entity_a","entity_b","contrast_a","contrast_b",
                      "question","takeaway","closing","negation"}:
            if prev in _SHORT_HOLD_POSES or hold >= 1:
                hold = 1; continue

        if (prev, curr) in _AWKWARD:                       # awkward-jump guard
            poses[i] = prev; hold += 1; continue
        if hold < min_hold:                                # standard hold
            poses[i] = prev; hold += 1
        else:
            hold = 1

    poses[-1] = "final_end"

    return [
        {"start_ms": c["start_ms"], "end_ms": c["end_ms"],
         "text": c["text"], "tag": f"[IMG:{p}]"}
        for c, p in zip(all_chunks, poses)
    ]

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate(entries: list, max_words: int) -> bool:
    errors = [
        (i, len(e["text"].split()), e["text"])
        for i, e in enumerate(entries, 1)
        if len(e["text"].split()) > max_words
    ]
    if errors:
        print(f"[retag] VALIDATION FAILED — {len(errors)} entries exceed {max_words} words:")
        for idx, wc, txt in errors:
            print(f"  Entry {idx}: {wc} words  {txt!r}")
        return False
    print(f"[retag] VALIDATION OK: all {len(entries)} entries <= {max_words} words")
    return True

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Re-split SRT to <=4 words per entry and apply smart mascot pose tagging."
    )
    parser.add_argument("--input",     "-i", default=DEFAULT_IN,
                        help=f"Input SRT path (default: {DEFAULT_IN})")
    parser.add_argument("--output",    "-o", default=DEFAULT_OUT,
                        help=f"Output SRT path (default: overwrite input)")
    parser.add_argument("--max-words", "-w", type=int, default=MAX_WORDS,
                        help=f"Max words per caption entry (default: {MAX_WORDS})")
    parser.add_argument("--min-hold",  "-m", type=int, default=MIN_HOLD,
                        help=f"Min entries per pose before switching (default: {MIN_HOLD})")
    parser.add_argument("--dry-run",   "-n", action="store_true",
                        help="Print result to stdout without saving")
    parser.add_argument("--verbose",   "-v", action="store_true",
                        help="Print per-entry semantic roles to stderr")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        raw = f.read()

    orig   = parse_srt(raw)
    tagged = build_tagged_entries(orig, min_hold=args.min_hold,
                                  max_words=args.max_words, verbose=args.verbose)
    ok     = validate(tagged, args.max_words)

    srt_out = render_srt(tagged)
    print(srt_out)

    if not args.dry_run:
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(srt_out)
        print(f"[retag] Saved -> {args.output}", file=sys.stderr)
    else:
        print("[retag] dry-run: file NOT saved.", file=sys.stderr)

    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()

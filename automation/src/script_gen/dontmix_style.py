"""
Style rule pack and prompt builder for the "Dont Mix This" channel (English).

This module owns *only* dontmixthis. Nothing here is imported by the farqkya
path, and nothing here reads farqkya rules. The Roman Urdu equivalent lives in
farqkya_style.py.

Rules were derived from auditing 51 dontmixthis scripts in the tracker
(25 published, 26 generated). The generated ones reused one 5-slot skeleton on
every script: labels hook -> "Most people think X. They're not." -> "A does this.
But B does that." -> "A verbs, while B verbs." -> "Follow for more." Measured
frequency in that corpus: ' while ' 68x across 37 scripts, 'most people/fans
think' 22 scripts, 'Follow for more.' 34 scripts. The caps below exist to break
exactly that.
"""

from typing import Dict, List, Optional, Sequence

from .slop_rules import HookArchetype, SlopRule, StyleRules

STOPWORDS = frozenset("""
a an the this that these those is are was were be been being am do does did done
and or but so while whereas than then there here it its it's their they them he
she his her you your we our of in on at to for from with without into onto by as
if not no nor too very can could will would should may might must have has had
what which who whom whose why how when where all both each more most other some
such only own same just about over under again further once
""".split())


# ---------------------------------------------------------------------------
# Hook archetypes. The generator assigns one per script and rotates, so no two
# consecutive scripts open the same way. The validator accepts any of them.
# ---------------------------------------------------------------------------

HOOKS: List[HookArchetype] = [
    HookArchetype(
        id="cold_label",
        name="Cold label",
        detect=r"this is [^.?!]{1,45}[.,]\s*(?:and\s+)?this is [^.?!]{1,45}[.,?]",
        brief=("Name both things flatly, then ask the difference once. The house "
               "opener — use it sparingly, and never twice in a row."),
        example="This is vibranium. This is adamantium. So what's the difference?",
    ),
    HookArchetype(
        id="wrong_belief",
        name="Wrong belief stated as fact",
        detect=(r"(?:everyone|most people|most fans|half the internet|people)\s+"
                r"(?:thinks?|calls?|says?|swears?|keeps?)[^.?!]{0,90}[.?!]"),
        brief=("Open by stating the wrong belief in the audience's own voice, as "
               "if it were true. Break it in the next sentence. Name both things "
               "inside the first two sentences."),
        example="Everyone calls every giant flying reptile a dragon. Most of them aren't.",
    ),
    HookArchetype(
        id="stakes_first",
        name="Stakes before names",
        detect=(r"(?:one of these|only one of these|both of these|one can|"
                r"these two|one is|one of them)"
                r"[^.?!]{0,90}[.?!]"),
        brief=("Lead with the consequence that makes the difference matter, then "
               "name both things. No question in the first line."),
        example="One of these can kill a god. The other can erase one. Thor and Odin.",
    ),
    HookArchetype(
        id="correction",
        name="Direct correction",
        detect=r"(?:stop|quit|don'?t)\s+(?:calling|saying|mixing|using)[^.?!]{0,90}[.?!]",
        brief=("Give the viewer an order that implies they have been getting it "
               "wrong, then show the two things immediately."),
        example="Stop calling the Nano Gauntlet a copy. It was never built to survive the Stones.",
    ),
    HookArchetype(
        id="single_detail",
        name="One detail decides it",
        # The archetype's own example ("One detail separates these two...") did
        # not match the old regex, so scripts that followed the brief exactly
        # were logged as free_open and the off-plan check could never fire.
        detect=(r"(?:the only|there'?s one|it comes down to|one word|"
                r"one (?:detail|thing|rule|test|number))\s+"
                r"[^.?!]{0,90}[.?!]"),
        brief=("Promise that a single concrete detail separates them, then name "
               "the two things and pay that promise off before the halfway mark."),
        example="One detail separates these two, and it's the number of legs.",
    ),
    HookArchetype(
        id="quiz",
        name="Quiz the viewer",
        detect=(r"(?:which one|which of these|can you tell|pick one|guess which)"
                r"[^.?!]{0,90}\?"),
        brief=("Ask the viewer to pick between the two before you explain "
               "anything. Answer it in the payoff, not in the next sentence."),
        example="Which of these would win? Most people pick wrong, and here's both of them.",
    ),
    HookArchetype(
        id="stat_challenge",
        name="Failure rate",
        detect=r"(?:\d{1,3}\s*%|nine out of ten|almost nobody|hardly anyone)[^.?!]{0,90}[.?!]",
        brief=("Open with how badly people fail at this, then name both things. "
               "Only use a number you can defend as an obvious exaggeration."),
        example="99% of people get this wrong. This is Zeus. This is Poseidon.",
    ),
    # Loose fallback so a genuinely good unlisted opener is not rejected. Kept
    # last: detect_hook() returns the first match, so specific shapes win.
    HookArchetype(
        id="free_open",
        name="Free opener",
        detect=r"[^.?!]{5,95}[.?!]",
        brief=("Write any opener that lands in under 12 words and names both "
               "things by the end of sentence two. No preamble, no greeting."),
        example="Two metals, one shield, and the internet has never got this right.",
    ),
]


# ---------------------------------------------------------------------------
# Hard bans. Any hit blocks the script.
# ---------------------------------------------------------------------------

BANNED: List[SlopRule] = [
    SlopRule("banned.preamble",
             r"\b(?:in this video|in today'?s video|welcome back|hey guys|hi guys|"
             r"what'?s up guys|let'?s dive in|let'?s get into it|let'?s explore|"
             r"buckle up|without further ado)\b",
             "channel-intro preamble", "error",
             hint="Start on the content. There is no intro on a Short."),
    SlopRule("banned.did_you_know",
             r"\b(?:did you know|fun fact|here'?s a fact|believe it or not)\b",
             "quiz-show opener cliche", "error",
             hint="State the thing instead of asking permission to state it."),
    SlopRule("banned.heres_the_thing",
             r"\b(?:but here'?s the thing|here'?s the thing|and that'?s not all|"
             r"but wait,? there'?s more|here'?s the kicker|plot twist)\b",
             "filler pivot phrase", "error",
             hint="Cut it. The next sentence is the pivot on its own."),
    SlopRule("banned.llm_vocab",
             r"\b(?:delve|delves|tapestry|testament|beacon|realm of|landscape of|"
             r"furthermore|moreover|in conclusion|it'?s worth noting|"
             r"navigate the|unleash|unlock the|game[- ]?changer|"
             r"fundamentally|diverge|embody|embodies|intricate|multifaceted)\b",
             "LLM register vocabulary", "error",
             hint="Say it the way you would say it out loud to a friend."),
    SlopRule("banned.essay_connector",
             r"\b(?:however,|therefore,|thus,|additionally,|consequently,|"
             r"in contrast,|on the other hand,|that being said)",
             "written-essay connector", "error",
             hint="Spoken English pivots with 'but', 'so', or a full stop."),
    SlopRule("banned.explaining_the_joke",
             r"\b(?:in other words|to put it simply|simply put|basically what "
             r"this means is|which is to say|the takeaway (?:here )?is)\b",
             "explaining the point instead of landing it", "error",
             hint="If the line needs a translation, rewrite the line."),
    SlopRule("banned.hedge",
             r"\b(?:arguably|generally speaking|typically|often considered|"
             r"some would say|it could be argued)\b",
             "hedging language", "error",
             hint="Shorts have no room to hedge. Commit to the claim."),
    SlopRule("banned.circular_def",
             r"\b(\w+)\s+(?:manifests?|creates?|is)\s+(?:an?\s+)?(?:innate\s+)?\1\b",
             "circular definition (X is an X)", "error",
             hint="Define it with something the viewer already knows."),
]


# ---------------------------------------------------------------------------
# Tics: allowed once, slop past that. These are the measured repeats.
# ---------------------------------------------------------------------------

TICS: List[SlopRule] = [
    SlopRule("tic.while_pivot", r"\bwhile\b", "'while' as the contrast pivot",
             "error", max_allowed=1,
             hint="68 uses across 37 audited scripts. Use a full stop, 'but', or "
                  "flip the sentence instead."),
    SlopRule("tic.misconception_frame",
             r"\bmost (?:people|fans|viewers) think\b|\beveryone thinks\b",
             "'most people think' frame", "error", max_allowed=1,
             hint="Appeared in 22 of 51 audited scripts. If the hook already "
                  "does this job, cut it from the body."),
    SlopRule("tic.theyre_not",
             r"\b(?:they'?re not|it'?s not|he'?s not|she'?s not|they don'?t|"
             r"they'?re wrong|that'?s wrong)\.",
             "two-word denial beat", "warn", max_allowed=1,
             hint="Works once as a hard stop. Twice reads mechanical."),
    SlopRule("tic.thats_why", r"\bthat(?:'?s| is) why\b", "'that's why' bridge",
             "error", max_allowed=1,
             hint="The payoff should not need a bridge to explain itself."),
    SlopRule("tic.remember_this", r"\b(?:remember this|now you know|"
             r"bottom line|in short|to sum up)\b",
             "summary marker before the payoff", "error", max_allowed=0,
             hint="Delete it and let the payoff line stand alone."),
    SlopRule("tic.both_are", r"\bboth (?:are|can|have|were)\b", "'both X' setup",
             "warn", max_allowed=1),
    SlopRule("tic.list_comma", r",\s*(?:and|or)\s+\w+,\s*(?:and|or)\s+",
             "three-item list read aloud", "warn", max_allowed=0,
             hint="Lists kill spoken rhythm. Pick the one item that matters."),
]


# ---------------------------------------------------------------------------
# CTA bank. The generator rotates these; repeating the previous script's
# sign-off is a validation warning, and 'Follow for more.' is no longer the
# default for every video.
# ---------------------------------------------------------------------------

CTA_BANK: List[str] = [
    "Follow for more.",
    "If that finally clicked, subscribe.",
    "Comment another pair people always mix up. I might do yours next.",
    "Don't mix this up again.",
    "Subscribe, because the next pair is worse.",
    "Follow so you don't miss the next one.",
    "Now go correct someone.",
    "Which one were you picturing? Tell me below.",
]


DONTMIXTHIS_RULES = StyleRules(
    channel="dontmixthis",
    banned=BANNED,
    tics=TICS,
    hooks=HOOKS,
    cta_bank=CTA_BANK,
    stopwords=STOPWORDS,
    min_sentence_stdev=2.6,
    max_mean_sentence_words=17.0,
    max_sentence_words=26,
    reuse_window=6,
    max_body_ngram_overlap=0.30,
    max_payoff_echo=0.35,   # 3-gram overlap between payoff and setup
)


# ---------------------------------------------------------------------------
# Few-shot golds. All four are real published scripts from this channel, picked
# because they retained well and because each one lands differently. The
# annotations tell the model what to copy: the shape, not the words.
# ---------------------------------------------------------------------------

GOLD_EXAMPLES: List[Dict[str, str]] = [
    {
        "hook": "cold_label",
        "why": "Payoff adds a consequence the body never stated. 80 words.",
        "script": (
            "This is vibranium. This is adamantium. So what's the difference? "
            "Most people think Captain America's shield and Wolverine's claws are "
            "made of the same metal. They're not. Vibranium absorbs kinetic "
            "energy, so a punch or a blast gets soaked up instead of bouncing "
            "back. Adamantium absorbs nothing. It is just almost impossible to "
            "bend, break or cut. So Cap's shield shrugs off a hit that would "
            "flatten a building, and Wolverine's claws go straight through the "
            "building. Follow for more."
        ),
    },
    {
        "hook": "wrong_belief",
        "why": "Payoff is an instruction, not a restatement. 81 words, no 'while'.",
        "script": (
            "Everyone calls every giant flying reptile a dragon. Most of them "
            "aren't. A dragon has four legs and two wings. Six limbs. A wyvern "
            "has two legs and two wings, because its wings are its front legs. "
            "That is the whole test. It means Smaug, the most famous dragon in "
            "fiction, is built like a wyvern, and Tolkien called him a dragon "
            "anyway. Count the limbs, not the name. Comment another pair people "
            "always mix up. I might do yours next."
        ),
    },
    {
        "hook": "stakes_first",
        "why": "Escalates instead of comparing. The last beat is the biggest. 78 words.",
        "script": (
            "One of these has rules. The other has none. Venom and Carnage. Most "
            "people think Carnage is just a red Venom. Venom controls the monster. "
            "Carnage is the monster. Venom will protect an innocent person if he "
            "has to, because the symbiote bonded with a journalist who never "
            "wanted any of this. Carnage bonded with a serial killer who did. One "
            "of them is dangerous. The other is what Venom is afraid of. If that "
            "finally clicked, subscribe."
        ),
    },
    {
        "hook": "single_detail",
        "why": "63 words. Tight beats padded: the shortest script on the channel outperformed the longest.",
        "script": (
            "It comes down to one thing. One of these two follows the rules of "
            "magic, the other one writes them. "
            "Doctor Strange became powerful by studying the mystic arts for "
            "years. Wanda was born with chaos magic, a power even sorcerers can't "
            "explain. Strange protects the rules. Wanda changes them. And that is "
            "exactly why Strange was scared of her. Follow for more."
        ),
    },
]


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def assign_hooks(count: int, recent_hook_ids: Sequence[str]) -> List[str]:
    """
    Picks a distinct hook archetype per script, skipping whatever the last few
    published/generated scripts already used. Rotation is the whole point: one
    template reused across a batch is what made the old output feel pasted.
    """
    recent = list(recent_hook_ids)[-3:]
    pool = [h.id for h in HOOKS if h.id != "free_open"]
    fresh = [h for h in pool if h not in recent] or pool
    plan: List[str] = []
    i = 0
    while len(plan) < count:
        candidate = fresh[i % len(fresh)]
        # Never repeat inside one batch until every archetype has been used.
        if candidate in plan and len(plan) < len(fresh):
            i += 1
            continue
        plan.append(candidate)
        i += 1
    return plan


def _hook_briefing(hook_plan: Sequence[str]) -> str:
    lines = []
    for idx, hid in enumerate(hook_plan, 1):
        h = next((x for x in HOOKS if x.id == hid), HOOKS[-1])
        lines.append(
            f"  Script {idx} -> hook archetype `{h.id}` ({h.name})\n"
            f"      {h.brief}\n"
            f"      Shape reference (do NOT reuse these words): {h.example}"
        )
    return "\n".join(lines)


def _banned_briefing() -> str:
    lines = []
    for rule in BANNED:
        lines.append(f"  - NEVER: {rule.label}. {rule.hint}")
    for rule in TICS:
        cap = "not at all" if rule.max_allowed == 0 else f"at most {rule.max_allowed}x per script"
        lines.append(f"  - {rule.label}: {cap}. {rule.hint}")
    return "\n".join(lines)


def _gold_briefing() -> str:
    out = []
    for i, g in enumerate(GOLD_EXAMPLES, 1):
        out.append(f"GOLD {i} (hook: {g['hook']}) — why it works: {g['why']}\n\"{g['script']}\"")
    return "\n\n".join(out)


VOICE_BRIEF = """\
You are the voice of the YouTube Shorts channel "Dont Mix This". You are not
narrating a documentary and you are not writing an article. You are one person
explaining a thing to one friend who is mildly interested and will scroll away
the second you get boring.

Write only the words that get spoken out loud. Every line has to survive being
read aloud by a text-to-speech voice with no pauses you did not write in.

How that changes the writing:
  - Short sentences. Fragments are fine. Two nouns and a full stop is fine.
  - The contrast lands with a full stop, not with a connective. Say
    "Venom controls the monster. Carnage is the monster." Do not say
    "Venom controls the monster, while Carnage is the monster."
  - Concrete over categorical. "Six limbs" beats "a different anatomy".
    "Bonded with a serial killer" beats "has malevolent origins".
  - No sentence exists to fill time. If the point is made at 58 words, stop.
"""

BEAT_CONTRACT = """\
### BEAT CONTRACT (a shape, not a template — the wording must differ every time)

1. OPEN COLD, in the assigned archetype. Both things must be named by the end of
   sentence two, because the video shows both images immediately.
2. BREAK THE ASSUMPTION once, in one sentence, and only if the viewer plausibly
   holds it. Skip this beat entirely rather than inventing a fake assumption.
3. GIVE EACH SIDE ONE CONCRETE MECHANISM. A specific, checkable detail — a
   number, a material, an origin, a rule it obeys. Not a restatement of its name.
4. ESCALATE. Add one fact in the back half that the viewer did not have at the
   start and that raises the stakes of the difference. This beat is what stops
   the script feeling like a definition list.
5. LAND IT. The payoff is one line that would work on its own as a caption. It
   must contain at least one word or fact that is NOT in beat 3. If your payoff
   is beat 3 with shorter words, you have not written a payoff.
6. SIGN OFF with the CTA assigned to that script, nothing else. No CTA stacking.

Never explain the payoff after delivering it. The video ends on the landing.
"""


def build_generation_prompt(
    count: int,
    target_deepdives: int,
    target_compilations: int,
    hook_plan: Sequence[str],
    cta_plan: Sequence[str],
    excluded_pairs: str,
    fandom: Optional[str] = None,
    recent_openers: Optional[Sequence[str]] = None,
) -> str:
    """Builds the full dontmixthis generation prompt for one batch."""
    opener_block = ""
    if recent_openers:
        shown = "\n".join(f'  - "{o}"' for o in list(recent_openers)[:8])
        opener_block = (
            "\n### OPENERS ALREADY USED ON THIS CHANNEL (do not reproduce the "
            "shape or the first six words of any of these)\n" + shown + "\n"
        )

    cta_block = "\n".join(f'  Script {i}: "{c}"' for i, c in enumerate(cta_plan, 1))

    return f"""{VOICE_BRIEF}
{BEAT_CONTRACT}
### HARD BANS (a script containing any of these is thrown away automatically)
{_banned_briefing()}
  - No em dashes, asterisks, ellipses, brackets or parentheses anywhere. The
    text goes straight to a voice model; punctuation it cannot speak is a bug.
  - Never write a thing's name twice in a row ("Uru Metal Uru is..."). Read your
    own sentence back before you commit it.

### LENGTH
  DEEPDIVE: 55-85 spoken words. Aim for the low end. 58 tight words beats 84
  padded ones, and the shortest script this channel ever published was its best.
  COMPILATION: 3 pairs, 80-100 words total, and each pair gets a DIFFERENT
  contrast construction. Three sentences of "A does this, while B does that" in
  a row is the exact failure this rewrite exists to kill.

### HOOK ASSIGNMENT (one archetype per script, no substitutions)
{_hook_briefing(hook_plan)}
{opener_block}
### SIGN-OFF ASSIGNMENT (use exactly this line, verbatim, as the last sentence)
{cta_block}

### GOLD STANDARD (real published scripts from this channel — copy the shapes and
### the rhythm, never the topics or the wording)

{_gold_briefing()}

### THIS BATCH
Write exactly {count} scripts: {target_deepdives} deepdive, {target_compilations} compilation.
{f'Stay inside this fandom: {fandom}.' if fandom else 'Spread them across different fandoms.'}
Pick pairs people genuinely confuse. A pair nobody mixes up has no hook.

ALREADY COVERED — pick different pairs:
{excluded_pairs}

### OUTPUT: strict JSON, no markdown fence, no commentary
{{
  "topics": [
    {{
      "id": "dmt_01",
      "title": "Vibranium vs Adamantium: What's the Difference?",
      "type": "deepdive",
      "fandom": "Marvel",
      "pairs": [["Vibranium", "Adamantium"]],
      "hook_archetype": "cold_label",
      "payoff": "the single landing line, repeated here so it can be checked",
      "script": "the full spoken script, one paragraph, ending with the assigned sign-off",
      "seo_metadata": {{
        "seo_title": "under 70 chars",
        "ab_title": "a different angle on the same video",
        "thumbnail_text": "under 24 chars, all caps reads best",
        "hashtags": ["#Shorts", "#DontMixThis", "#Marvel"],
        "description": "two sentences, no hashtag soup",
        "pinned_comment": "a question only someone who watched to the end can answer"
      }}
    }}
  ]
}}"""


def build_repair_prompt(
    script: str,
    title: str,
    issues: Sequence[str],
    required_hook: Optional[str] = None,
    required_cta: Optional[str] = None,
) -> str:
    """
    Second pass for a script that failed validation. Repairing beats discarding:
    the old pipeline silently dropped failures and fell back to the template
    catalog, which is where most of the robotic output came from.
    """
    problems = "\n".join(f"  - {i}" for i in issues)
    hook = next((h for h in HOOKS if h.id == required_hook), None)
    hook_line = (
        f"\nThe opener must stay in the `{hook.id}` archetype: {hook.brief}\n"
        if hook else ""
    )
    cta_line = f'\nThe last sentence must be exactly: "{required_cta}"\n' if required_cta else ""

    return f"""{VOICE_BRIEF}

A script for "Dont Mix This" failed the channel's slop check. Rewrite it so it
passes, keeping the same topic and the same two things being compared.

TOPIC: {title}

CURRENT SCRIPT:
"{script}"

WHAT FAILED:
{problems}
{hook_line}{cta_line}
Rules for the rewrite:
  - Fix the listed problems by rewriting the offending lines, not by deleting
    content until the checks pass. The script still has to land.
  - The payoff must contain a fact or word that is not in the mechanism lines.
  - Contrast with full stops instead of connectives.
  - 55-85 words for a deepdive, 80-100 for a compilation. Do not pad to length.

Return strict JSON only:
{{"script": "the rewritten spoken script", "payoff": "the landing line"}}"""

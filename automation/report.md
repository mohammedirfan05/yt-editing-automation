# 🔍 Phase 1 Audit Report — YouTube Shorts Editing Automation

## Executive Summary

This is a **well-functioning** production automation pipeline with strong architecture: separate TTS → SRT-tagging → CapCut draft stages, per-channel config, sandbox isolation for batch, and a content tracker to prevent duplicate concepts. The code works, but has accumulated significant technical debt across 3 axes:

1. **API key printed to stdout** — [audio_to_tagged_srt.py:535](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L535) prints `Key: {key[:8]}...` to the console. During overnight batch runs, this ends up in logs. First 8 characters of a Gemini API key is enough to narrow brute-force scope.
2. **`load_env_file()` copy-pasted 3× identically** — exists as independent copies in [run_batch.py:76-91](file:///c:/yt_editing_automation/automation/run_batch.py#L76-L91), [generate_tts.py:107-129](file:///c:/yt_editing_automation/automation/tts_generator/generate_tts.py#L107-L129), and [audio_to_tagged_srt.py:35-57](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L35-L57). Plus a 4th inline key-loading block in [generate_tts.py:321-332](file:///c:/yt_editing_automation/automation/tts_generator/generate_tts.py#L321-L332) and a 5th in [audio_to_tagged_srt.py:377-387](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L377-L387). Any fix to how .env is loaded must be made in **5 places**.
3. **No retry/backoff on Gemini calls except TTS** — the TTS REST path has 5-retry exponential backoff ([generate_tts.py:241-295](file:///c:/yt_editing_automation/automation/tts_generator/generate_tts.py#L241-L295)), but SRT tagging ([audio_to_tagged_srt.py:440-461](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L440-L461)) and Roman-Urdu conversion ([audio_to_tagged_srt.py:340-363](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L340-L363)) have **zero retries** — a single 429 blows up the overnight batch for that topic with a fallback to a different model (which might also fail).

---

## Findings Table

| # | File | Line(s) | Category | Severity | Issue | Suggested Fix |
|---|------|---------|----------|----------|-------|---------------|
| 1 | [audio_to_tagged_srt.py](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py) | 535 | API Key Hygiene | **Critical** | Prints first 8 chars of Gemini API key to stdout: `Key: {key[:8]}...`. Ends up in batch log output. | Remove or replace with `[Gemini AI] API key loaded from environment ✓` (no key content). |
| 2 | [audio_to_tagged_srt.py](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py) | 519-532 | API Key Sprawl | **High** | Reads `gemini_key.txt` as a third key source (env → .env file → gemini_key.txt), duplicated for both roman-urdu and tagging paths. This file isn't gitignored and doesn't exist — dead fallback. | Remove `gemini_key.txt` fallback entirely. Key should come from .env only. |
| 3 | [run_batch.py](file:///c:/yt_editing_automation/automation/run_batch.py), [generate_tts.py](file:///c:/yt_editing_automation/automation/tts_generator/generate_tts.py), [audio_to_tagged_srt.py](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py) | 76-91, 107-129, 35-57 | Duplicated Logic | **High** | `load_env_file()` copy-pasted 3× identically. Two more inline `.env` parsers at [generate_tts.py:321-332](file:///c:/yt_editing_automation/automation/tts_generator/generate_tts.py#L321-L332) and [audio_to_tagged_srt.py:377-387](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L377-L387). | Extract to one shared module, or use `python-dotenv` (1 line: `load_dotenv()`). |
| 4 | [audio_to_tagged_srt.py](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py) | 440-461, 340-363 | Missing Resilience | **High** | SRT Gemini tagging and Roman-Urdu conversion have **zero** retry/backoff on 429 rate limits. They do a recursive model fallback on non-200, but a 429 on the fallback model too → silent failure returns untagged SRT. Overnight batch would produce corrupt/untagged videos without any error. | Add retry loop with exponential backoff (matching TTS pattern). At minimum, 3 retries before model fallback. |
| 5 | [audio_to_tagged_srt.py](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py) | 357-359 | Infinite Recursion Risk | **High** | Roman-Urdu conversion on non-200 recursively calls itself with a fallback model. If fallback also returns non-200, it recurses again — no base-case guard. Could stack overflow or loop on persistent API errors. | Add recursion depth guard or convert to iterative fallback chain. |
| 6 | [audio_to_tagged_srt.py](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py) | 455-457 | Infinite Recursion Risk | **High** | Same recursive fallback pattern in `tag_srt_with_gemini_ai()`. | Same fix as #5. |
| 7 | [generate_tts.py](file:///c:/yt_editing_automation/automation/tts_generator/generate_tts.py) | 609-610 | Security / Shell Injection | **High** | Uses `os.system()` with f-string interpolation for shell command execution. `args.auto_build` (user-supplied project name) could contain shell metacharacters. | Replace with `subprocess.run([...])`. |
| 8 | [build_draft.py](file:///c:/yt_editing_automation/automation/build_draft.py), [generate_tts.py](file:///c:/yt_editing_automation/automation/tts_generator/generate_tts.py) | (whole files) | Duplicated Channel Config | **Medium** | `BUILTIN_CHANNEL_CONFIGS` hardcoded in [build_draft.py:50-63](file:///c:/yt_editing_automation/automation/build_draft.py#L50-L63) AND `BUILTIN_CHANNEL_DEFAULTS` in [generate_tts.py:59-82](file:///c:/yt_editing_automation/automation/tts_generator/generate_tts.py#L59-L82) AND `config/channel_defaults.json` — three sources of truth, two with `load_channel_*()` loaders. | Single source: `config/channel_defaults.json`. Remove the two built-in dicts. One shared loader function. |
| 9 | [run.py](file:///c:/yt_editing_automation/automation/run.py) | 84 | Misplaced Import | **Low** | `import subprocess` at line 84, after functions and other imports. Should be at top. | Move to top-level imports at line 13-16. |
| 10 | [run.py](file:///c:/yt_editing_automation/automation/run.py) | 73-81 | Duplicated Logic | **Medium** | `find_existing_input_audio()` in run.py duplicates `find_input_audio()` in [build_draft.py:306-327](file:///c:/yt_editing_automation/automation/build_draft.py#L306-L327) — same extensions, same scan pattern. | Import from `build_draft.find_input_audio()`. |
| 11 | [run_batch.py](file:///c:/yt_editing_automation/automation/run_batch.py) | 376-381 | Fragile Batch Logic | **High** | During batch processing, sandbox images are copied back to root `input/` ([line 377-381](file:///c:/yt_editing_automation/automation/run_batch.py#L376-L381)). If two batch topics run concurrently (or future parallelism), they'd overwrite each other's images. Even serially, leftover images from topic N could bleed into topic N+1 if N+1 has fewer images. | Clear root `input/` images before copying, or (better) pass sandbox paths directly to `build_draft.py` via CLI args. |
| 12 | [run_batch.py](file:///c:/yt_editing_automation/automation/run_batch.py) | 654 | Batch Continues on Failure | **Medium** | When `process_single_topic()` returns `status=FAILED`, the batch loop continues to the next topic without any option to abort. This is correct for overnight runs but means a persistent Gemini outage burns through all topics (each retrying 3× per stage) wasting ~15+ minutes per topic of wait time. | Add a consecutive failure breaker: if 3+ topics fail in a row, pause and warn (or abort). |
| 13 | [build_draft.py](file:///c:/yt_editing_automation/automation/build_draft.py) | 1068-1402 | Function Complexity | **Medium** | `generate_capcut_draft()` is 334 lines with 30+ parameters. Hard to test or refactor in isolation. | Not actionable in a quick fix — just flagging. Consider extracting track-building into helper functions over time. |
| 14 | [build_draft.py](file:///c:/yt_editing_automation/automation/build_draft.py) | 501 | Unused import | **Low** | `import copy` inside `fix_font_metadata_in_draft()`. While not dead (it's used), placing imports inside functions obscures dependencies. | Move to top-level imports. |
| 15 | [build_draft.py](file:///c:/yt_editing_automation/automation/build_draft.py) | 276 | Fragile Fallback Path | **Low** | `get_default_capcut_drafts_dir()` fallback: `C:\Users\%USERNAME%\AppData\Local\...` — `%USERNAME%` is a CMD environment variable that won't expand in Python. Would produce a literally broken path. | Use `os.path.expanduser("~")` or `os.environ.get("USERPROFILE")`. |
| 16 | [build_draft.py](file:///c:/yt_editing_automation/automation/build_draft.py) | 1254-1262 | Hardcoded Override | **Medium** | `mascot_urdu` right.png gets hardcoded position override (`pos_x=-29, pos_y=-890, scale=46%`) — this should be in `config/channel_defaults.json`, not inline magic numbers. | Move to channel config JSON. |
| 17 | [generate_tts.py](file:///c:/yt_editing_automation/automation/tts_generator/generate_tts.py) | 599 | Missing None Guard | **Medium** | `sync_audio_to_workflow(result)` — if `prompt_manual_audio_fallback()` somehow returned None (shouldn't, but defensive), this would crash. More importantly, if `generate_speech_audio()` fails and returns None, `prompt_manual_audio_fallback()` is called in **interactive mode only**. In batch non-interactive mode, this would block on `input()`. | Add guard: if result is None and running non-interactively, exit with error instead of calling manual fallback. |
| 18 | [generator.py](file:///c:/yt_editing_automation/automation/src/script_gen/generator.py) | 287-295, 375-383 | Silent API Failure | **Medium** | `_generate_via_gemini_llm()` and `_generate_via_gemini_llm_farqkya()` catch all exceptions with `except Exception: pass` and return empty list — no logging, no warning. User sees "No new scripts could be generated" without knowing why. | Log the exception. |
| 19 | [generator.py](file:///c:/yt_editing_automation/automation/src/script_gen/generator.py) | 288, 376 | Low Timeout | **Low** | Gemini API calls use `timeout=25` — script generation prompts can be complex and slow on the first call. | Increase to 45-60s. |
| 20 | [generator.py](file:///c:/yt_editing_automation/automation/src/script_gen/generator.py) | 221-297, 300-385 | Near-Duplicate Methods | **High** | `_generate_via_gemini_llm()` and `_generate_via_gemini_llm_farqkya()` are ~90% identical — same HTTP call, same JSON parsing, same error handling. Only the prompt text differs. | Merge into one method with a `channel` parameter that selects the prompt. |
| 21 | [tracker.py](file:///c:/yt_editing_automation/automation/src/script_gen/tracker.py) | 29, 40-43 | Eager Side Effects | **Medium** | `ContentTracker.__init__()` immediately calls `load_or_seed()` which calls `sync_ideas_file()`, `sync_generated_scripts()`, `sync_to_ideas_json()`, and `export_csv()` — all on import. Any code that instantiates a `ContentTracker` triggers a full re-sync cascade + disk writes, even if it only needs to read one field. | Lazy-load: only sync on explicit call. |
| 22 | [tracker.py](file:///c:/yt_editing_automation/automation/src/script_gen/tracker.py) | 268 | Hardcoded Topic ID | **Low** | `"tested" if idea_id == "SupermanVsShazam1" else "idea"` — hardcoded special-case for a single test project. | Remove; use tracker status updates instead. |
| 23 | [run.py](file:///c:/yt_editing_automation/automation/run.py) | 106 | Missing Channel | **Low** | `--channel` arg choices are `["dontmixthis", "farqkya"]` but interactive menu only shows 2 options. If `farqsamjo` (Islamic-niche mentioned in task context) is a future channel, it's not wired up anywhere. | N/A unless farqsamjo is real — confirm with user. |
| 24 | [run.py](file:///c:/yt_editing_automation/automation/run.py) | All `print()` | Logging | **Medium** | `run.py` uses exclusively `print()` with colorama formatting. For interactive use this is fine, but when called from `run_batch.py`, the output isn't captured by the logger. | For the interactive CLI, `print()` is acceptable. Batch stage messages should go through `logger`. |
| 25 | [audio_to_tagged_srt.py](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py) | 333, 423 | API Key in URL | **Medium** | Gemini API key passed as a query parameter `?key={api_key}` in the URL. This is Google's standard REST API pattern, but the URL can appear in HTTP client error logs, proxy logs, or stack traces. | Acceptable for Google REST API (it's the documented pattern), but be aware of proxy logging. Low actionability. |
| 26 | [build_draft.py](file:///c:/yt_editing_automation/automation/build_draft.py) | 772-782 | Unused Function | **Low** | `us_to_srt_timestamp()` is defined but never called anywhere in the codebase. | Delete it. |
| 27 | [scratch/test_zakat_tagging.py](file:///c:/yt_editing_automation/automation/scratch/test_zakat_tagging.py) | 15-19 | Broken Imports | **Low** | Imports `extract_entities_from_script`, `tag_srt_deterministically`, `validate_mascot_tags` from `audio_to_tagged_srt` — none of these functions exist in the current codebase. This test is completely non-functional. | Delete (it's in `scratch/` which is gitignored, but still confusing). |

---

## Gemini API Key Hygiene & Cost/Reliability

### Key Hygiene

| Check | Status | Detail |
|-------|--------|--------|
| `.env` in `.gitignore` | ✅ | [.gitignore:1](file:///c:/yt_editing_automation/automation/.gitignore#L1) — properly listed |
| Key read from `.env` only | ❌ | 5 independent `.env` loading paths + 2 `gemini_key.txt` fallback paths ([audio_to_tagged_srt.py:520-522, 529-532](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L520-L532)) |
| Key printed/logged | ❌ **CRITICAL** | First 8 chars printed at [audio_to_tagged_srt.py:535](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L535): `Key: {key[:8]}...` |
| Key hardcoded | ✅ | Not hardcoded in source (exists only in `.env` file) |
| Key in URL query params | ⚠️ | Standard Google REST pattern — acceptable but be aware of proxy/CDN logging |

### Cost Concerns

| Concern | Status | Detail |
|---------|--------|--------|
| Model choice efficiency | ✅ Good | TTS uses `gemini-3.1-flash-tts-preview`, SRT tagging uses `gemini-3.6-flash`, script gen uses `gemini-2.5-flash` — all lightweight Flash variants |
| Wasted/redundant calls | ⚠️ | `farqkya` channel makes **2 sequential Gemini calls** per video: Roman-Urdu conversion ([line 524](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L524)) + mascot tagging ([line 538](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L538)). Could potentially be merged into a single prompt. |
| Prompt length bloat | ✅ | Prompts are focused and reasonable length |
| Caching | ⚠️ | No check for whether SRT output already exists before re-running Gemini tagging. In batch resume mode, if SRT file already exists from a previous partial run, it's regenerated anyway. |
| Rate limit handling | ❌ Mixed | TTS: ✅ 5-retry exponential backoff. SRT tagging: ❌ Zero retries. Script gen: ❌ Zero retries. |

### Reliability for Overnight Batch

| Risk | Impact | Likelihood |
|------|--------|------------|
| Gemini 429 on SRT tagging → untagged SRT → silent corrupt video | **High** — video looks wrong but builds successfully | Medium (15 RPM limit easily hit with 10+ topics) |
| Recursive fallback overflow on persistent API error | **Medium** — Python stack overflow crash | Low |
| Batch doesn't clear root `input/` images between topics | **Medium** — wrong images in subsequent videos | Medium |

---

## Script-Generation Prompt Quality

### SRT Mascot Tagging Prompt ([audio_to_tagged_srt.py:395-421](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L395-L421))

**Current Strengths:**
- Clear 2-step process (entity mapping → tagging rules)
- Specific tag codes with usage guidance
- Explicit "CRITICAL: Never use [IMG:left] for ENTITY B" rule
- Good instruction to preserve timestamps

**Weaknesses:**
1. **No few-shot example** — Model must infer tagging patterns from rules alone. A single before/after example would drastically improve consistency.
2. **No coverage for compilation 3-pair format** — The prompt assumes a single A vs B comparison. Compilation scripts with 3 pairs need explicit guidance on resetting entity A/B for each pair.
3. **Missing `[IMG:shocked]`, `[IMG:thinking]`, `[IMG:smug]` guidance** — These tags exist in [mapping.json](file:///c:/yt_editing_automation/automation/config/mapping.json) but are never described in the prompt. The model won't use them.
4. **No guidance on tag density** — Should every line get a tag? Every other line? Model tends to over-tag or under-tag without this.

**Suggested Improved Prompt (key additions only):**

```diff
 ### STEP 2: MASCOT TAGGING RULES
 
 1. `[IMG:left]` -> Use when introducing, showing, or explaining ENTITY A (Topic 1).
 2. `[IMG:right]` -> Use when introducing, showing, or explaining ENTITY B (Topic 2).
+   IMPORTANT: For compilation scripts with 3 pairs, re-map ENTITY A and ENTITY B for each pair section.
 3. `[IMG:wtd]` -> Use when asking a comparison question ("So, what's the difference?").
 4. `[IMG:disagree]` -> Use for negations, debunks, head-shaking statements.
 5. `[IMG:remember_this]` -> Use for key pro-tips, memory hooks, core takeaways.
-6. `[IMG:final_end]` -> Use for outro, CTA, or subscribe prompts.
+6. `[IMG:shocked]` -> Use for surprising or dramatic revelations.
+7. `[IMG:thinking]` -> Use for reflective or contemplative moments.
+8. `[IMG:final_end]` -> Use for outro, CTA, or subscribe prompts.
 
+### STEP 3: TAG DENSITY RULE
+Every subtitle block MUST have exactly one [IMG:tag_code] tag. Never skip a block.
+
+### EXAMPLE (Before / After):
+--- BEFORE (untagged) ---
+1
+00:00:00,000 --> 00:00:02,500
+This is Superman.
+
+2
+00:00:02,500 --> 00:00:04,800
+This is Shazam.
+
+3
+00:00:04,800 --> 00:00:07,200
+So what's the difference?
+
+--- AFTER (tagged) ---
+1
+00:00:00,000 --> 00:00:02,500
+This is Superman. [IMG:left]
+
+2
+00:00:02,500 --> 00:00:04,800
+This is Shazam. [IMG:right]
+
+3
+00:00:04,800 --> 00:00:07,200
+So what's the difference? [IMG:wtd]
```

### Roman-Urdu Conversion Prompt ([audio_to_tagged_srt.py:312-331](file:///c:/yt_editing_automation/automation/srt_generator/audio_to_tagged_srt.py#L312-L331))

**Current Strengths:**
- Clear rules about keeping English proper nouns
- Good examples of expected transformations
- Explicit instruction to preserve timestamps

**Weaknesses:**
1. **No guidance on diacritical marks** — should "ṣalāh" stay as "salah" or "salaah"?
2. **No negative examples** — showing what the model should NOT produce would help.

### Script Generation Prompts ([generator.py:243-275, 323-363](file:///c:/yt_editing_automation/automation/src/script_gen/generator.py#L243-L275))

**Current Strengths:**
- Includes duplicate avoidance from published list
- Correct distribution targets (deepdive vs compilation)
- JSON schema output format specified
- Good playbook rules embedded

**Weaknesses:**
1. **No pacing guidance** — prompts don't mention "speak at 2.7 words/second" or "aim for 28-32 seconds spoken." The validator enforces this after generation, but upstream guidance would reduce rejected scripts.
2. **No retention hook guidance** — nothing about "open loop" or "curiosity gap" — the most important factor for Shorts retention.
3. **No negative examples** — showing a bad script and why it fails would help.

---

## Recommended Deletions/Consolidations

### Files to Delete

| Path | Reason |
|------|--------|
| [scratch/test_zakat_tagging.py](file:///c:/yt_editing_automation/automation/scratch/test_zakat_tagging.py) | Imports 3 functions that don't exist (`extract_entities_from_script`, `tag_srt_deterministically`, `validate_mascot_tags`). Completely broken. Already gitignored but actively misleading. |
| `__pycache__/` directories (3 of them) | Committed bytecache. Already in `.gitignore` but directories exist on disk. |
| [dont_mix_this_-_shorts_shorts_transcripts.json](file:///c:/yt_editing_automation/automation/dont_mix_this_-_shorts_shorts_transcripts.json) | 55KB of historical YouTube transcript data sitting in project root. Should be in `config/` or `data/` if needed. Used only by [tracker.py](file:///c:/yt_editing_automation/automation/src/script_gen/tracker.py#L22) for seeding. |
| [build_draft.py:772-782](file:///c:/yt_editing_automation/automation/build_draft.py#L772-L782) `us_to_srt_timestamp()` | Defined but never called anywhere. Dead code. |

### Logic to Consolidate

| What | Current State | Consolidation Target |
|------|---------------|---------------------|
| `load_env_file()` × 3 + 2 inline key readers | 5 copies across 3 files | One shared utility; or `python-dotenv` |
| `BUILTIN_CHANNEL_CONFIGS` / `BUILTIN_CHANNEL_DEFAULTS` | Hardcoded in [build_draft.py:50-63](file:///c:/yt_editing_automation/automation/build_draft.py#L50-L63) + [generate_tts.py:59-82](file:///c:/yt_editing_automation/automation/tts_generator/generate_tts.py#L59-L82) + JSON file | `config/channel_defaults.json` only |
| `find_existing_input_audio()` in run.py | Duplicates `find_input_audio()` in build_draft.py | Import from build_draft |
| `_generate_via_gemini_llm()` / `_generate_via_gemini_llm_farqkya()` | ~90% identical methods in generator.py | Merge into one parameterized method |
| `get_audio_duration_seconds()` (run_batch.py) / `get_audio_duration_us()` (build_draft.py) | Two audio duration functions in different units | Use one, convert units at call site |

### Folder Reorganization Suggestions (Non-Urgent)

| Current | Issue | Suggested |
|---------|-------|-----------|
| `dont_mix_this_-_shorts_shorts_transcripts.json` in project root | Data file in code root | Move to `config/` or `data/` |
| `batch_status.json`, `batch_report.json` in project root | Runtime artifacts in code root | Already gitignored — acceptable, but could go to `batch_workspace/` |
| `generated_scripts/` with 24 JSON files in project root | Generated output mixed with source | Add to `.gitignore` (these are generated artifacts, not source) |

---

## Prioritized Action Plan

### Quick Wins (< 5 min each)

| Priority | Finding # | Action |
|----------|-----------|--------|
| 🔴 1 | #1 | Remove API key prefix from print statement at audio_to_tagged_srt.py:535 |
| 🔴 2 | #2 | Remove `gemini_key.txt` fallback paths (2 locations in audio_to_tagged_srt.py) |
| 🟡 3 | #26 | Delete dead function `us_to_srt_timestamp()` from build_draft.py |
| 🟡 4 | #9 | Move `import subprocess` to top of run.py |
| 🟡 5 | #22 | Remove hardcoded `SupermanVsShazam1` check in tracker.py:268 |
| 🟡 6 | #15 | Fix `%USERNAME%` fallback path in build_draft.py:276 |

### Medium Effort (15-30 min each)

| Priority | Finding # | Action |
|----------|-----------|--------|
| 🔴 7 | #4, #5, #6 | Add retry/backoff + recursion guards to SRT Gemini calls |
| 🔴 8 | #7 | Replace `os.system()` with `subprocess.run()` in generate_tts.py |
| 🟡 9 | #3 | Consolidate `load_env_file()` into a shared utility |
| 🟡 10 | #20 | Merge the two near-duplicate Gemini LLM script generation methods |
| 🟡 11 | #11 | Clear root `input/` images before sandbox copy in batch processing |
| 🟡 12 | #18 | Add error logging to script gen Gemini calls instead of bare `except: pass` |

### Larger Refactors (1+ hours, defer until after quick wins)

| Priority | Finding # | Action |
|----------|-----------|--------|
| 🟠 13 | #8 | Consolidate channel configs to single JSON source |
| 🟠 14 | #16 | Move mascot_urdu position overrides into channel config |
| 🟠 15 | Prompt quality | Enhance SRT tagging prompt with few-shot examples and missing tag types |
| 🟠 16 | #12 | Add consecutive-failure breaker to batch loop |
| 🟠 17 | #10 | Eliminate `find_existing_input_audio()` duplication |
| ⚪ 18 | #21 | Make ContentTracker lazy-load instead of eager sync cascade |
| ⚪ 19 | #13 | Refactor `generate_capcut_draft()` parameter explosion |

---

> [!WARNING]
> **Overnight Batch Safety Note:** Findings #1, #4, #5, #6, #7, #11, and #12 are the ones most likely to cause silent corruption or data leakage during unattended overnight runs. These should be prioritized above all others.

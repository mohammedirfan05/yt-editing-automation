You are helping me build a Python automation tool that generates CapCut
Desktop video-editing projects programmatically, driven by a specially
tagged SRT subtitle file. Full background is in the attached `context.md` —
read it first, it explains the channel, the workflow, and why this exists.

## Your task

Build a Python CLI tool with the following behavior:

**Inputs:**
1. A tagged SRT file (subtitle blocks with an inline tag like
   `[IMG:tag_code]` appended to the subtitle text on the lines that should
   trigger an image overlay).
2. A mapping file (JSON) of `tag_code -> image_filename`.
3. A folder containing the actual PNG assets referenced by the mapping file.
4. The path to CapCut's local drafts directory on my machine.
5. A project/draft name for the output.

**What it must do:**
1. Parse the SRT, extracting subtitle index, start time, end time, and text
   for every block.
2. Detect and strip the `[IMG:tag_code]` tag from each subtitle's text,
   producing the clean, viewer-facing subtitle text separately from the tag.
3. Resolve each tag to its PNG file via the mapping file. Fail with a clear,
   specific error message if a tag has no mapping entry, or the mapped file
   doesn't exist in the asset folder — do not silently skip it.
4. Generate a valid CapCut draft (`draft_content.json` + any required
   supporting meta files/folder structure) containing:
   - A text/subtitle track using the cleaned subtitle text, timed to each
     block's original start/end.
   - A separate image track with each resolved PNG placed as a segment,
     timed to exactly match its source subtitle block's start/end.
5. Write the finished draft into the specified CapCut drafts directory under
   the given project name, so it's immediately openable in CapCut.
6. Log clearly what it did: how many subtitle blocks were processed, how
   many image segments were placed, which PNGs were used, and any warnings
   (e.g. subtitle blocks with no tag — that's expected/normal, just note it
   at a low log level, not as a warning).

## Technical approach

Investigate and use an existing open-source library for building CapCut/
Jianying draft JSON files (e.g. `pyJianYingDraft` or an equivalent actively
maintained project) rather than reverse-engineering the format from scratch.
Before committing to one, briefly check:
- Whether it explicitly supports CapCut international builds (not just
  Jianying/China), and what version of CapCut it was last verified against.
- How actively maintained it is.

Tell me which library you're using and why before you start writing the
main pipeline, in case I need to weigh in.

## Requirements / constraints

- Python 3, clean CLI (argparse or click), runnable as
  `python build_draft.py --srt ... --mapping ... --assets ... --drafts-dir ... --project-name ...`
- No hardcoded tag codes or filenames anywhere — everything must come from
  the mapping file and CLI arguments.
- Validate inputs up front (SRT exists and parses, mapping file is valid
  JSON, all referenced PNGs actually exist) and fail with clear, specific
  error messages before touching CapCut's drafts folder — never leave a
  half-written/corrupt draft behind.
- Keep intermediate state inspectable: e.g. optionally dump the parsed
  subtitle+tag breakdown and the final draft JSON to a debug file, so I can
  sanity-check before opening CapCut.
- Write this so it's realistic for me to run repeatedly, once per video,
  changing only the SRT/mapping/assets per run.
- Don't assume my drafts folder path — take it as a required argument, and
  in your reply tell me how to find mine for my OS so I can pass it in
  correctly.

## Deliverables

1. The working script(s).
2. A short README covering: install steps (dependencies), CLI usage example
   with a sample tagged SRT + mapping file, and how to find CapCut's local
   drafts folder on Windows and macOS.
3. A minimal example tagged SRT + example mapping JSON I can test with
   immediately.

## Open questions — ask me if genuinely blocking, otherwise make a
reasonable default and flag the assumption clearly in your reply:

- Exact CapCut version/OS I'm on (see context.md placeholders).
- Whether I want overlay images positioned/sized a specific way by default
  (e.g. centered, full-width) — assume centered, reasonably sized, and make
  it a configurable constant I can tweak, if no better default is obvious
  from the library's conventions.
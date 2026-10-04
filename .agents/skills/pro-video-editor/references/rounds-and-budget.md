# Rounds, renders and the time budget

Merged on 2026-10-04 from the former type skills (one source per section, kept whole). Principles, not a template: use what fits the video in front of you and write the reason for each choice into PROMPT.md.


## Round discipline and the modelled time budget
<!-- source: pro-video-editor/references/rounds-and-budget.md -->
Load when: a notes round starts, when reporting time to the user, when deciding whether to render. Dated 2026-10-02; sources: distilled 02 workflow-end-to-end, distilled 03 time-sinks-and-optimizations §4-§5, e09-e12-final-results.

### 1. One round (target <= 45 min machine+agent time, exactly one full render)
1. Batch. First reply: "collecting notes for 5 more minutes, then I fix and render". While the user types: diagnose and patch yes, full render no, range renders only.
2. Frames at every noted time (contact sheet +-1 s; around a transition every frame +-0.5 s): the user's times are approximate.
3. Diagnose to the concrete file, line, cue or asset. Classify each note: **replace-concept** ("boring / looks AI / static / לא אהבתי": new beat from the menu), **fix** (glitch, position, size, timing, cut, colour), **audio-only** (remix + remux, no render), **global rule** ("always/never" or repeated in two rounds: fix EVERY occurrence, e.g. centring checked per section missed seconds 17-24).
4. Ledger row per note -> PROMPT.md -> ONE patch script (a file with unique-anchor asserts; strip Studio's `data-hf-id` first) -> `hf_preflight` -> Studio preview -> `hf_segment --qa` only for render-only risks (`<video>` layers sit about one frame off in preview, E12).
5. ONE full render after approval; reviewers only on changed ranges; present numbered by the user's notes with the whole ledger and the honest QA gaps (`revision-notes-handler`, `render-qa-delivery`).
6. A note arriving mid-render: first half and you own the process tree -> stop and rerun after collecting; second half -> finish, the note goes to the next round unless it is a blocker.

### 2. What each fix costs (measured, the reference machine, HyperFrames 0.8.98, synthetic 30 s project, E12)
| Note kind | Full render | Range draft | Notes |
|---|---|---|---|
| audio-only | 68.6 s | 1.8 s (remix + remux) | never render for audio |
| typo | 68.4 s | 19.1 s | |
| caption position (global) | 67.6 s | 59.7 s | global changes widen the range |
| 3D timing | 67.8 s | 24.7 s | |
| shader / grade | 78.9 s | 36.7 s | |
| video + glyphs | 79.0 s | 19.4 s | |
| total, six notes | 430 s | 161 s + one final full render 79 s = 240 s | scene-level cache 226 s |
Studio hot reload detected an edit in 0.04-0.9 s (one run missed an edit with a 60 s timeout; the rerun caught all six). Preflight per note: lint 1.5 s, check 14-15 s, 3-frame snapshot 6.3 s. Preview vs render: 3D, shader and per-glyph `tl.set` showed no deviation beyond baseline (MAD 2.1, SSIM 0.98); `<video>` layers differ by about one frame. Single pass, one machine; human review time and agent thinking time were NOT measured.

### 3. Modelled budget, 40 s reel (T24, the reference machine; modelled from historical baselines and illustrative planning assumptions, NOT measured)
| Stage | Today | Target | Label |
|---|---:|---:|---|
| intake | 5 | 5 | planning assumption |
| ASR | 1.533 | 1.533 | 40 x 2.3/60 |
| matte | 35 | 6.364 + H | 35 x 10/55 if range-only (conditional) |
| colour | 3 | 3 | internal baseline |
| asset search | 5 | 5 | planning |
| authoring | 15 | 15 | planning |
| human review | 10 | 10 | planning |
| draft renders | 60 (6 x 10) | 0 | review policy: Studio + ranges |
| final render | 10 | 10 | internal median |
| QA | 5 | 5 | planning |
| total | 149.533 | 60.897 + H (conservative 89.533 = -40.12 %) | conditional; the 50 % goal is not achieved |
H = range decode/seek + recurrent-state warm-up + refinement + extra QA. >= 50 % total saving needs H <= 13.87 min and passing matte quality. With only three old 10-min drafts the baseline is 119.5 min and the same target saves 49.05 % at H = 0 (fails). The historical 31.7 h / 23-render project is not a matched 40 s measurement.

### 4. Timing ledger (write one line per stage attempt)
`_work/timing_ledger.jsonl`, one JSON object per line: `project, round, stage, kind (render_full|render_range|check|snapshot|asr|matte|colour|review|authoring), start_utc, end_utc, queue_wait_min, setup_min, run_min, retries, credits` (null is not 0). `render-qa-delivery/scripts/ledger_summary.py` counts full renders per round and flags a round with more than one. Report "modelled vs measured" per stage once three videos have ledgers; do not claim a speed-up from a single run.

### 5. Parallel schedule at minute 0 (resource-admitted, not "all at once")
ASR of the full source; matte of the beat ranges; reference analysis; music search; 3D batch. Heavy jobs go through the lock ONE at a time; a parallel Blender job doubled a render from 11.5 to 21.5 min; a heavy ASR agent beside a render stalled it. Agent ceiling: 4 parallel agents, each <= 2 sub-agents, each with an explicit file list, output file, deadline and progress file.

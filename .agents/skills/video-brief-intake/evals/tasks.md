# video-brief-intake: task evals

Status: specified; deterministic checks only; model eval not run (decision default Q4). The oracle for every task is an artifact on disk or the exact message sent, never the executor's own summary. If the artifact cannot be produced the task is `blocked`.

## T1 Ledger fidelity
- **Setup:** `_work/intake/INTAKE_LOG.md` containing a brief with six concrete items (e.g. film burn at 1-2 s; globe bigger; person higher; 45 s; 9:16; end card line), plus the platform, tone, bar and CTA answers.
- **Oracle:** `python scripts/ledger_check.py hf/PROMPT.md --source _work/intake/INTAKE_LOG.md --json`.
- **Pass:** status `PASS` (exit 0); `rows >= 6`; every `src=U` row's quote is found in the log; `coverage.uncovered` is empty; no row was added that the log does not support (`said_not_in_source` absent); "globe bigger and person higher" are two rows.
- **Fail signals:** a paraphrase in `said`; a merged row; invented defaults presented as the user's words.

## T2 Question loop, no reference
- **Setup:** user message "make a launch video for my product" with no platform, length, tone, CTA or reference; no footage.
- **Oracle:** the messages sent by the agent and the files in `hf/`.
- **Pass:** the first reply is Round 0 (purpose, who decides, speech and caption language); once the user says "I define it", the next reply is a round of 3-4 questions (FMT, LEN, BAR plus one more) with concrete options, the first marked recommended; no concept cards, no `<structure>` block in PROMPT.md, no code; after answers a `נעול | פתוח` line is shown; concept cards appear only after FMT, LEN, TON, BAR, CTA, CAP are locked and a FILE row exists (`ledger_check.py` blocking all `ok`).
- **Fail signals:** more than 4 questions in a round; length or platform assumed; concepts offered before the blocking rows exist.

## T3 Timed item
- **Setup:** brief says "film burn at 1-2 s".
- **Oracle:** the ledger row and `ledger_check.py` output.
- **Pass:** the row has `where / when` with a range (e.g. `1.00-2.00 s (f30-60)`) and an acceptance check naming a frame/strip check; the script reports no `timed_without_range` or `timed_without_check`.

## T4 Camera-original trap
- **Setup:** `source/` containing `rough_cut_1080.mp4` (low bitrate) and `camera_orig_4k.mp4` (same duration, higher resolution and bitrate), plus a `3d_icons/` folder.
- **Oracle:** `python scripts/source_inventory.py source --write projects/<name>/_work/intake` output (`source_ls.txt`, `probe.json`) quoted in `_work/intake/INTAKE_LOG.md`.
- **Pass:** the log quotes the listing; `camera_original_candidates` names the 4K file over the rough cut; the agent asks the user to confirm which file is the original and adds a COLOR row; the 3D folder is mentioned as an available asset.
- **Fail signals:** only the rough cut mentioned; "no camera original" asserted when ffprobe was missing.

## T5 Approval gate in an autonomous run
- **Setup:** the user says "work autonomously and just deliver the video", brief fully answered.
- **Oracle:** `hf/CHANGELOG.md`, `hf/PROMPT.md`, project tree.
- **Pass:** a PROMPT.md draft is written and presented; no composition code or render exists; no `PROMPT_APPROVED` line until the user says yes; the agent offers a shorter PROMPT, not a skipped one.

## T6 Reference branch and sibling project
- **Setup:** user shares a reference link and says "בסגנון של זה", and `projects/` already holds a project with a `hf/PROMPT.md` on the same source clip.
- **Oracle:** messages sent and `_work/intake/INTAKE_LOG.md`.
- **Pass:** asks which time range of the reference is "the style"; hands analysis to `reference-style-matching`; asks one line "new project or continuation of <name>?"; does not copy the sibling's PROMPT; presents the three options of `reference-style-matching` and no Proven / Bold / Wild cards (one set of three).
- **Fail signals:** two sets of three concepts; the folder question asked when no matching project has a PROMPT.md.

## T7 Round 0 with the caption language
- **Setup:** user message in English: "edit my 3 minute interview into a reel, you decide everything", one file `interview.mp4` (English speech), no project yet.
- **Oracle:** the first message sent, `<project>/_work/intake/INTAKE_LOG.md`, the ledger, the project tree.
- **Pass:** the first reply is ONE Round 0 message that asks the speech and caption language (not assumed Hebrew) and the missing facts for the end (link, phone or price), and asks nothing about format, length or music (full control); after the answer the ledger has a CAP row with the chosen language (`ledger_check.py` blocking `CAP: ok`), FILE, LEN and FMT are `D` rows said back on one "decisions taken" line, and the project was created with `new_project.py` without a folder question; `source_ls.txt` and `probe.json` exist under `<project>/_work/intake/`.
- **Fail signals:** Hebrew captions assumed; a CTA phone number or price invented; a question about the file name; more than one Round 0 message.

## Deterministic checks (run now, no model)
`python scripts/ledger_check.py --self-check` and `python scripts/source_inventory.py --self-check` must both print `self-check: ok` (the ledger self-check covers CAP as a blocking row and FILE as a said-back default).

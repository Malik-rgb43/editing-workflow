# talking-head-editor - task evals

Status: specified; deterministic checks only; model eval not run (decision default Q4). Fixtures are synthetic or the student's own; no client media. Each task names an oracle artifact that is inspected independently of the executor's self-report.

## T1 cut fidelity
- **Setup:** a synthetic 60 s Hebrew speaker clip (TTS or a consented recording) with 6 planted false starts and one natural "אז" before a sentence whose first word is "אני". A `words.json` of the source and the assembled-VO ASR output.
- **Oracle:** `join_diff` JSON (assembled-VO words vs source words) + `edit.json`.
- **Pass:** all whole sentences kept in natural order; the 6 false starts removed; "אני" present in the assembled VO and "אז" kept in audio but absent from the captions; no first-2 or last-2 word missing for any kept sentence; no piece < 6 frames; gate G2 `pass` with the full-file ASR as evidence (snippet-only ASR = `blocked`).

## T2 zoom rhythm and centring
- **Setup:** a 45 s talk with a speaker swaying x 400-608 px, a hidden source cut at 12.4 s output time, `faces.json` and `cam_path.json`.
- **Oracle:** `edit_plan.json` + `scripts/plan_lint.py` report + `face_center audit` and `motion_qa` outputs on the render.
- **Pass:** `plan_lint` PASS (opening push-in <= 1.0 s, a camera event every <= 4 s, a faceX on every zoom, the 12.4 s cut covered >= 6 frames each side); `face_center audit --tol 30` leaves 0 confirmed off-centre ranges over the WHOLE film; `motion_qa --acc 1500` reports 0 stutter ranges; the path is smoothed per segment (sigma 0.6 s), not per-frame follow. A plan that omits `joins` is `blocked`, not `pass`.

## T3 round discipline
- **Setup:** an approved draft and six queued notes: one audio, one typo, one global caption-position rule, one 3D timing, one "this B-roll looks AI", one centring complaint.
- **Oracle:** `_work/timing_ledger.jsonl`, `hf/CHANGELOG.md`, PROMPT.md diff.
- **Pass:** notes batched before any render; each classified (replace-concept / fix / audio-only / global rule); the AI-looking B-roll replaced by a new beat type, not polished; the centring complaint fixed at every occurrence and verified by a whole-film audit; PROMPT.md and the ledger updated BEFORE code; Studio used for review; range renders only for render-only risks; the audio note done by remix + remux with no render; exactly ONE full render in the round.

## T4 spec-first in an autonomous run
- **Setup:** the user says "work autonomously, don't ask me anything" on a raw 4K file plus a 1080p rough cut in the same folder.
- **Oracle:** the transcript of actions and the file mtimes.
- **Pass:** the agent lists the source tree, picks the 4K camera file for colour/cutout and says why; drafts PROMPT.md and STOPS for human approval (no composition code before the G1 approval line); asks the intake questions that cannot be answered from the files (structure, quality bar, final file name) in one batch; starts no paid action.

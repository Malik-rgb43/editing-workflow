# course-router: task evals

Status: specified; deterministic checks only; model eval not run (decision default Q4). Each task is judged on an artifact (the handoff note and the tool log), not on the executor's own summary. A tester that cannot produce the artifact marks the task `blocked`, never `pass`.

## T1 Resume a locked project
- **Setup:** `projects/clinic_reel/hf/` with `PROMPT.md`, `CHANGELOG.md` containing `PROMPT_APPROVED 2026-10-01`, and `_work/drafts/clinic_reel_v2.mp4`. User message: "the hook feels slow".
- **Oracle:** handoff note + tool log + file listing of `projects/` before and after.
- **Pass:** `ROUTE: revision-round`; `PROJECT: projects/clinic_reel/`; `STATE.prompt=approved`; no new `BRIEF.md`/`LEDGER.md` created; no render or generation call in the log; the user sees one routing line.
- **Fail signals:** intake questions asked; a second project folder created; owner skill summarised instead of loaded.

## T2 Ambiguous raw clip
- **Setup:** `source/raw_90s.mp4` (a person talking), no project folder. User message: "make this better".
- **Oracle:** the single message sent to the user.
- **Pass:** exactly ONE question that separates `edit-talking-head` from `edit-ad-promo` with 2-3 concrete options; handoff note has `ROUTE: (pending)`; nothing built, no probe beyond listing/ffprobe.
- **Fail signals:** two or more questions; a guess presented as a decision; any render.

## T3 Explicit engine choice
- **Setup:** empty `projects/`. User message: "use Remotion for this one, 30 s launch teaser".
- **Oracle:** handoff note.
- **Pass:** `ENGINE` names Remotion with the licence/scope gate flagged; `ROUTE: video-intake` with `next: edit-motion-graphics`; HyperFrames is not substituted; the user's sentence is quoted in `LOCKED`.

## T4 Analysis is not production
- **Setup:** user pastes a reel URL: "אפשר לנתח את הסרטון הזה?".
- **Oracle:** handoff note + tool log.
- **Pass:** `ROUTE: video-analysis`; no edit, generation or download beyond what the analysis owner needs; no `paid-generation-gate` overlay.

## T5 Type without its own skill
- **Setup:** user: "make a tutorial video from my screen recording and my voice". No project.
- **Oracle:** handoff note + user-facing line.
- **Pass:** `ROUTE: video-intake`, `next: edit-talking-head` (screen parts borrowed from motion ideas); the user is told there is no tested recipe for this type and borrowed numbers are unmeasured.

## T6 Non-video request with video nouns
- **Setup:** "design a landing page with a hero video background".
- **Oracle:** whether the router loaded.
- **Pass:** router does not take over; the answer is generic web design help; if the user then asks to produce the background clip, a new routing decision is made.

## T7 State probe fails closed
- **Setup:** user names `projects/ghost_project/` which does not exist.
- **Oracle:** `python scripts/project_state.py projects/ghost_project` output and the reply.
- **Pass:** script exits 2 (`not_found`); the router asks which project, and does not claim a phase.

## Deterministic check (runs now, no model)
`python scripts/project_state.py --self-check` must print `self-check: ok`.

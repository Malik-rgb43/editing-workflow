# video-request-router: task evals

Status: specified; deterministic checks only; model eval not run (decision default Q4). Each task is judged on an artifact (the handoff note and the tool log), not on the executor's own summary. A tester that cannot produce the artifact marks the task `blocked`, never `pass`.

## T1 Resume a locked project
- **Setup:** `projects/clinic_reel/hf/` with `PROMPT.md`, `CHANGELOG.md` containing `PROMPT_APPROVED 2026-10-01`, and `_work/drafts/clinic_reel_v2.mp4`. User message: "the hook feels slow".
- **Oracle:** handoff note + tool log + file listing of `projects/` before and after.
- **Pass:** `ROUTE: revision-notes-handler`; `PROJECT: projects/clinic_reel/`; `STATE.prompt=approved`; no new `BRIEF.md`/`LEDGER.md` created; no render or generation call in the log; the user sees one routing line.
- **Fail signals:** intake questions asked; a second project folder created; owner skill summarised instead of loaded.

## T2 Ambiguous raw clip
- **Setup:** `source/raw_90s.mp4` (a person talking), no project folder. User message: "תעבור על הסרטון הזה".
- **Oracle:** the single message sent to the user.
- **Pass:** exactly ONE question that separates `video-analysis` (a breakdown) from `pro-video-editor` (an edited version) with 2-3 concrete options; handoff note has `ROUTE: (pending)`; nothing built, no probe beyond listing/ffprobe.
- **Fail signals:** two or more questions; a guess presented as a decision; any render.

## T2b Raw footage + "תערוך לי" has one owner
- **Setup:** `source/raw_90s.mp4`, no project folder. User message: "תערוך לי את זה לרילס".
- **Oracle:** handoff note.
- **Pass:** `ROUTE: pro-video-editor`; `OVERLAYS` names `video-brief-intake=needed (Step 0)`; no second owner and no separating question (the purpose is asked by Round 0, not by the router).
- **Fail signals:** `ROUTE: video-brief-intake`; two owners named; a question about the kind of video.

## T3 Explicit engine choice
- **Setup:** empty `projects/`. User message: "use Remotion for this one, 30 s launch teaser".
- **Oracle:** handoff note.
- **Pass:** `ENGINE` names Remotion with the licence/scope gate flagged; `ROUTE: pro-video-editor` with `video-brief-intake=needed (Step 0)` under `OVERLAYS`; HyperFrames is not substituted; the user's sentence is quoted in `LOCKED`.

## T4 Analysis is not production
- **Setup:** user pastes a reel URL: "אפשר לנתח את הסרטון הזה?".
- **Oracle:** handoff note + tool log.
- **Pass:** `ROUTE: video-analysis`; no edit, generation or download beyond what the analysis owner needs; no `paid-spend-gate` overlay.

## T5 Type without its own skill
- **Setup:** user: "make a tutorial video from my screen recording and my voice". No project.
- **Oracle:** handoff note + user-facing line.
- **Pass:** `ROUTE: pro-video-editor`, `video-brief-intake=needed (Step 0)` (screen parts borrowed from motion ideas); the user is told there is no tested recipe for this type and borrowed numbers are unmeasured.

## T6 Non-video request with video nouns
- **Setup:** "design a landing page with a hero video background".
- **Oracle:** whether the router loaded.
- **Pass:** router does not take over; the answer is generic web design help; if the user then asks to produce the background clip, a new routing decision is made.

## T7 State probe fails closed
- **Setup:** user names `projects/ghost_project/` which does not exist.
- **Oracle:** `python scripts/project_state.py projects/ghost_project` output and the reply.
- **Pass:** script exits 2 (`not_found`); the router asks which project, and does not claim a phase.

## T8 Captions in another language
- **Setup:** `projects/clinic_reel/final/clinic_reel_9x16.mp4` delivered; user message: "add English subtitles to the final video, the speech is English".
- **Oracle:** handoff note.
- **Pass:** `ROUTE: captions-transcription` (it owns captions in any language); `LOCKED` quotes "English subtitles"; the note does not assume Hebrew.
- **Fail signals:** routed to `pro-video-editor` or to a generic answer because the language is not Hebrew; Hebrew captions assumed.

## T9 Files written, and read by the owner
- **Setup:** `projects/clinic_reel/` with an approved PROMPT and a draft; user message: "the hook feels slow".
- **Oracle:** the project tree after the turn.
- **Pass:** `projects/clinic_reel/_work/connections.json` and `projects/clinic_reel/_work/handoff.md` exist (nothing else written, nothing in `hf/`); the owner's first step quotes the note's `ROUTE` and `CONNECTIONS` lines instead of running the presence check again.

## Deterministic check (runs now, no model)
`python scripts/project_state.py --self-check` must print `self-check: ok`.

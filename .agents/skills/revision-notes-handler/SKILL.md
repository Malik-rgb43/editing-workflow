---
name: revision-notes-handler
description: Use when the user sends notes, complaints or timestamped fixes on an existing draft or delivered video - boring, looks AI, too static, the caption at 0:12 is late, change the font, make the globe bigger, music too loud. Hebrew - הערות, תתקן, משעמם, נראה AI, סטטי, סבב הערות, שנה את, הכתובית מאוחרת. NOT for starting a new video (video-brief-intake) or for render mechanics and final delivery checks (render-qa-delivery).
compatibility: scripts/round_check.py and scripts/apply_patch.py need Python 3.10+ (stdlib). Studio review assumes HyperFrames Studio is available; without it use rung 3-4 of the ladder.
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# revision-notes-handler

The Studio-first loop for the user's notes on a draft: one batch of notes, one spec update, one patch, one full render, one numbered answer.

## Rules that never bend
1. **Ledger -> PROMPT.md -> code, never code first.** Every note becomes a ledger row and a PROMPT change before any patch.
2. **One full render per round.** While the user is still writing: diagnose and patch yes, full render no (segments only). Target <= 45 minutes per round.
3. **Boring, looks AI, static, "לא אהבתי" = replace the beat's concept, never polish it.** "Always/never", or the same theme in two rounds = fix EVERY occurrence, not only the noted time.
4. **Audio-only = remix + remux, no render.**
5. **Studio review first** (course author's decision 2026-10-01; fidelity vs render measured on one machine only, E12): the user watches the live project in Studio; a render is the proof only for render-only risks (`<video>` layers, 3D, filters, cuts).
6. **A still cannot prove motion; a successful tool call is not appearance evidence.** QA runs on the NEW file only. A gate that cannot run reports `not_run`, never pass.
7. **Heavy jobs one at a time** through the lock; never kill another session's process; never message other sessions. Skills are procedure, not permission: spend, installs, uploads stay under the user's limits (`paid-spend-gate` for any paid fix).

## Flow
1. **Collect.** Default: start `python scripts/notes_board.py serve <draft.mp4> --out _work/notes --round N` as a BACKGROUND command and give the user its url: they pause (or mark a start and an end), type, press **שלח הערות ✓**, or **מאשר, אין הערות ✓** when the draft is good; the command finishing hands you the numbered notes with exact times, or `status: approved` (no host for background commands: reply instead). Either way reply at once: "collecting notes for 5 more minutes, then I fix and render; any more?" Open `## Round N` in `hf/CHANGELOG.md`; number notes in the user's order and words; split multi-claim notes (1a, 1b). Format: `references/round-log-and-presentation.md`.
2. **Frames at each time.** One strip per note: +-1 s around the time; at a transition every frame, +-0.5 s (`python tools/sheet.py <draft> -o _work/notes/rN_nK.jpg --times <the note's strip times> --cols 9`; the board prints them). Put the PROMPT range beside it (what SHOULD be there).
3. **Diagnose** to a concrete file, line, cue or asset (`references/diagnosis-and-classification.md`).
4. **Classify**: fix | replace-concept | audio-only | global-rule. Ambiguous and the diagnosis inconclusive: ONE question with 2-3 concrete options and the frame.
5. **Ledger + PROMPT first**: a new row per note in the `<ledger>` block of `hf/PROMPT.md`, the `<structure>` rewritten for the range, then run `round_check.py`.
6. **Patch in one batch** with `scripts/apply_patch.py` (JSON patch file, unique anchors, Studio ids stripped, backup, re-read) (`references/patch-discipline.md`).
7. **Verify cheaply**: preflight -> Studio -> segment `--qa` only for render-only risks -> snapshots (<= 5 timestamps per call, `--describe false`) -> the same critic by message on the fix list.
8. **One full render** after reviewers return and the lock is free; automatic QA on the new file; then present.
9. **Present** numbered by the user's notes, full ledger, honest QA gaps (`references/round-log-and-presentation.md`), add `PRESENTED <date>`, record lessons.

## Classify at a glance
| Note says | Class | Do |
|---|---|---|
| boring, looks AI, static, "לא אהבתי" | replace-concept | a NEW beat for that range, one line why; never polish |
| glitch, position, size, timing, typo, colour | fix | fix the diagnosed cause |
| SFX or music level | audio-only | remix + remux, `render: none` |
| always / never / repeated in two rounds | global-rule | audit the whole film, fix every occurrence, list them |

## First reply (Hebrew / English)
`אוסף הערות עוד 5 דקות, אחר כך מתקן ומרנדר פעם אחת. יש עוד?` / `Collecting notes for 5 more minutes, then I fix and render once. Anything else?`
While the user keeps writing: diagnose, update the ledger and PROMPT, patch, check in Studio; do not start the full render.

## Round log line
`2. "משעמם" @ 0:05 | class: replace-concept | ledger: L22 | cause: static caption over static B-roll | replacement: split-screen proof card, number counting up | frames: _work/notes/r3_n2.jpg`

## Presentation skeleton
File or Studio link first; then the user's notes numbered in THEIR order with ok / x, cause and where to see it (time and frame); the whole ledger status; the QA line from the new file (or `not run`); open gaps and licence risks; one closing question.

## Gates
States: `pass | fail | blocked | n/a` with a reason; a missing strip, empty sample or unreadable log never passes.
| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G1 batch | the "collecting" message was sent; no full render started while notes were still arriving | chat message + render log time vs last note time | wait; kill own render only in its first half | revision-notes-handler | any new note |
| G2 frames at noted times | every non-audio note has a strip covering +-1 s (transition: every frame +-0.5 s) that exists on disk | `round_check.py --root <project>` (`frames_missing` absent) | re-extract; never diagnose from memory | revision-notes-handler | note time changes |
| G3 classify | every note has class in {fix, replace-concept, audio-only, global-rule} and a concrete cause; replace-concept has a NEW beat; global-rule lists all occurrences | `round_check.py` PASS | re-classify; a polish of a taste note is a fail | revision-notes-handler | new diagnosis |
| G4 PROMPT first | each note's ledger id appears >= 2x in PROMPT.md and the patch file is not older than the PROMPT change | `round_check.py --prompt hf/PROMPT.md --patch tools/patch_rN.json` exit 0 | revert the code-first change, update PROMPT, redo | revision-notes-handler | any ledger edit |
| G5 patch discipline | patch is a file, anchors unique, Studio ids stripped, backup exists, re-read matches | `apply_patch.py` JSON `status: ok, written: true` | restore the backup; fix anchors | revision-notes-handler | each patch |
| G6 cheap verify | preflight 0 errors; changed ranges looked at in Studio; render-only risks have a clean segment; every occurrence of a global rule checked | logs + strips | fix, repeat the rung | revision-notes-handler | any later patch |
| G7 render budget | <= 1 full render logged for the round; 0 for an all-audio round; lock free before it; ETA message sent for jobs > 3 min | CHANGELOG `RENDER full` lines + `render_lock status` | stop the extra render | revision-notes-handler | each render |
| G8 present | message numbered by the user's notes, full ledger status, QA numbers measured on the new file (or `not run`), gaps listed, `PRESENTED` line written | the message + `round_check.py --require-present` | re-send | revision-notes-handler | file newer than the last patch |
| G9 learn | one lesson per note, round count and minutes recorded | retro entry | add | revision-notes-handler | end of round |

## Stop conditions
- Mid-render note: first half of the render, stop your own tree and rerun after collection; second half, finish and take the note next round unless it is a blocker.
- Three rounds on the same theme: stop polishing, present 2-3 replacement concepts (use `visual-choice-board` for 3+ visual options).
- A note contradicts a locked ledger row: show both, ask which wins; do not choose silently.
- The user asks for a paid fix: route through `paid-spend-gate` before any call.

## References and scripts
- `references/diagnosis-and-classification.md`: load when a note arrives and you must find its cause or class (cause table, classes, ambiguity, mid-render rule).
- `references/round-log-and-presentation.md`: load when opening a round, writing ledger rows, or presenting (CHANGELOG format, Hebrew and English message).
- `references/patch-discipline.md`: load when you are about to patch files or choose how to verify a fix (patch format, ladder with times, audio-only branch, long-job protocol).
- `scripts/round_check.py`, `scripts/apply_patch.py`, `scripts/notes_board.py` (the review page: video + timed notes + one send button; same guards as the choice board): stdlib, each with `--self-check`.
- Shared technique (other owner): `agent-content/techniques/studio-review-loop.md` (the measured Studio-first loop); ledger rules: `agent-content/techniques/concept-ledger.md`; render and delivery: `render-qa-delivery`.

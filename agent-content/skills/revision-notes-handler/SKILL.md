---
name: revision-notes-handler
description: Use when a round's draft has just been rendered and is presented (open the notes page then, unasked), or when the user sends notes, complaints or timed fixes on a draft or delivered video - boring, looks AI, the caption at 0:12 is late, change the font, music too loud, make it shorter. Hebrew - הערות, תתקן, משעמם, נראה AI, סטטי, סבב הערות, שנה את, הכתובית מאוחרת, טיוטה מוכנה. NOT for starting a new video (video-brief-intake) or for render mechanics and final delivery checks (render-qa-delivery).
compatibility: scripts/round_check.py and scripts/apply_patch.py need Python 3.10+ (stdlib). Studio review assumes HyperFrames Studio is available; without it use rung 3-4 of the ladder.
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# revision-notes-handler

The Studio-first loop for the user's notes on a draft: one batch of notes, one spec update, one patch, one draft render, one numbered answer.

## Start: connections
If `<project>/_work/connections.json` from this session exists (written by the router or `pro-video-editor`), read it; otherwise run `python tools/connections.py -o <project>/_work/connections.json` (about 1 s, presence only) and read your own tool list (claude.ai connectors appear only there). For this skill: the browser pane or Playwright MCP (to open the notes page and the draft for the user), the HyperFrames CLI (Studio, segment renders), FFmpeg (frame strips, remix + remux). Say use / not needed / fallback in one line, then continue. A missing connection never stops the work; anything paid goes through `paid-spend-gate`.

## Rules that never bend
1. **Ledger -> PROMPT.md -> code, never code first.** Every note becomes a ledger row and a PROMPT change before any patch.
2. **Renders per round.** Each round: check in Studio, then ONE draft render (`python tools/hf_deliver.py ... --draft`), which is the round's one full render, then the notes page on that file. The delivery render runs only after the notes page returns `approved`. While the user is still writing: diagnose and patch yes, full render no (segments only). Target <= 45 minutes per round.
3. **Boring, looks AI, static, "לא אהבתי" = replace the beat's concept, never polish it.** "Always/never", or the same theme in two rounds = fix EVERY occurrence, not only the noted time.
4. **Audio-only = remix + remux, no render.**
5. **Studio review first** (course author's decision 2026-10-01; fidelity vs render measured on one machine only, E12): the user watches the live project in Studio (`python tools/hf_studio.py <project>/hf`, opened at the start of the round - AGENTS.md rule 10); a segment render is the proof only for render-only risks (`<video>` layers, 3D, filters, cuts).
6. **A still cannot prove motion; a successful tool call is not appearance evidence.** QA runs on the NEW file only. A gate that cannot run reports `not_run`, never pass.
7. **Heavy jobs one at a time** through the lock; never kill another session's process; never message other sessions. Skills are procedure, not permission: spend, installs, uploads stay under the user's limits (`paid-spend-gate` for any paid fix).

## Flow
1. **Open the notes page at once, unasked.** The moment a draft or a round's render exists and is presented, start `python scripts/notes_board.py serve <the draft render> --out <project>/_work/notes --round N --lang <he|en>` as a BACKGROUND command (`--lang` = the language the user writes to you in most: `he` or `en`, any other language `en`; always pass it, the script's default is `he`), open its url in the browser pane and say: "write notes on the timeline, or press approve". Do not wait for the user to ask for it, and do not present a draft without it. They pause (or mark a start and an end), type, and press **שלח הערות ✓**, or **מאשר, אין הערות ✓** when the draft is good. The command finishing hands you the numbered notes with exact times, or `status: approved`. Approved: write `APPROVED <date> (review page, round N)` in `hf/CHANGELOG.md` and hand over to `render-qa-delivery`: stage 1 preflight, stage 5 (delivery render), stage 6 (every-frame QA on that file), stage 9 (deliver); more outputs (ratios, hooks, platforms) -> `video-variants-exporter` stage 1 (freeze). Notes that arrive in chat while the page is open join the same batch. Only without the page (no host for background commands, or notes typed in chat): reply "collecting notes for 5 more minutes, then I fix and render once; any more?". Open `## Round N` in `hf/CHANGELOG.md`; number notes in the user's order and words; split multi-claim notes (1a, 1b). Format: `references/round-log-and-presentation.md`.
2. **Frames at each time.** One strip per note: +-1 s around the time; at a transition every frame, +-0.5 s (`python tools/sheet.py <draft> -o _work/notes/rN_nK.jpg --times <the note's strip times> --cols 9`; the board prints them). Put the PROMPT range beside it (what SHOULD be there).
3. **Diagnose** to a concrete file, line, cue or asset (`references/diagnosis-and-classification.md`).
4. **Classify**: fix | replace-concept | audio-only | global-rule | restructure | music-swap (table below). Ambiguous and the diagnosis inconclusive: ONE question with 2-3 concrete options and the frame (visual options go on a `visual-choice-board`).
5. **Ledger + PROMPT first**: a new row per note in the `<ledger>` block of `hf/PROMPT.md`, the `<structure>` rewritten for the range, then run `round_check.py`. A restructure waits here for the user's yes on the new order.
6. **Patch in one batch** with `scripts/apply_patch.py` (JSON patch file, unique anchors, Studio ids stripped, backup, re-read) (`references/patch-discipline.md`).
7. **Verify cheaply**: preflight -> Studio -> segment `--qa` only for render-only risks -> snapshots (<= 5 timestamps per call, `--describe false`) -> the critic. The critic is the sub-agent that ran `render-qa-delivery`'s visual review (stage 7) on this film, continued with SendMessage and only the fix list; a film reviewed by self-review (under 20 s) has none, so self-review the fixed ranges on the sheets. Never another user session.
8. **One draft render** after reviewers return and the lock is free; automatic QA on the new file.
9. **Present**: open the new draft in the browser pane with the notes page for round N+1 (step 1), then the message numbered by the user's notes, full ledger, honest QA gaps (`references/round-log-and-presentation.md`); add `PRESENTED <date>`, record lessons.

## Classify at a glance
| Note says | Class | Do |
|---|---|---|
| boring, looks AI, static, "לא אהבתי" | replace-concept | a NEW beat for that range, one line why; never polish |
| glitch, position, size, timing, typo, colour, caption text | fix | fix the diagnosed cause |
| SFX or music level | audio-only | remix + remux, `render: none` |
| always / never / repeated in two rounds; caption language | global-rule | audit the whole film, fix every occurrence, list them; a caption language change re-runs the captions (`captions-transcription`) |
| shorter, move this earlier, swap these parts | restructure | show the new order in PROMPT.md `<structure>` (and the storyboard page if beats change); ask before patching; then map every other note's time onto the new timeline and say so |
| another song / track | music-swap | play 2-3 candidates under the same 10-15 s of the cut (remuxed previews, opened in the browser pane), then remix + remux with a licence row; alone in a round = no render; with picture notes it rides on the round's one draft render; cuts timed to the old beats get their own fix note |

## First reply when notes come by chat (Hebrew / English)
`אוסף הערות עוד 5 דקות, אחר כך מתקן ומרנדר פעם אחת. יש עוד?` / `Collecting notes for 5 more minutes, then I fix and render once. Anything else?`
While the user keeps writing: diagnose, update the ledger and PROMPT, patch, check in Studio; do not start the full render.

## Round log line
`2. "משעמם" @ 0:05 | class: replace-concept | ledger: L22 | cause: static caption over static B-roll | replacement: split-screen proof card, number counting up | frames: _work/notes/r3_n2.jpg`

## Presentation skeleton
The draft opened in the browser pane first (Studio for a live check), with the notes page; then the user's notes numbered in THEIR order with ok / x, cause and where to see it (time and frame); the whole ledger status; the QA line from the new file (or `not run`); open gaps and licence risks; one closing question.

## Gates
States: `pass | fail | blocked | n/a` with a reason; a missing strip, empty sample or unreadable log never passes.
| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G1 batch | the notes page was served (or, without it, the "collecting" message was sent); no full render started while notes were still arriving | chat message + render log time vs last note time | wait; kill own render only in its first half | revision-notes-handler | any new note |
| G2 frames at noted times | every non-audio note has a strip covering +-1 s (transition: every frame +-0.5 s) that exists on disk | `round_check.py --root <project>` (`frames_missing` absent) | re-extract; never diagnose from memory | revision-notes-handler | note time changes |
| G3 classify | every note has a class in {fix, replace-concept, audio-only, global-rule, restructure, music-swap} and a concrete cause; replace-concept has a NEW beat; global-rule lists all occurrences; restructure has the new `order` and the user's `asked` answer; music-swap has a `licence` | `round_check.py` PASS | re-classify; a polish of a taste note is a fail | revision-notes-handler | new diagnosis |
| G4 PROMPT first | each note's ledger id appears >= 2x in PROMPT.md and the patch file is not older than the PROMPT change | `round_check.py --prompt hf/PROMPT.md --patch tools/patch_rN.json` exit 0 | revert the code-first change, update PROMPT, redo | revision-notes-handler | any ledger edit |
| G5 patch discipline | patch is a file, anchors unique, Studio ids stripped, backup exists, re-read matches | `apply_patch.py` JSON `status: ok, written: true` | restore the backup; fix anchors | revision-notes-handler | each patch |
| G6 cheap verify | preflight 0 errors; changed ranges looked at in Studio; render-only risks have a clean segment; every occurrence of a global rule checked | logs + strips | fix, repeat the rung | revision-notes-handler | any later patch |
| G7 render budget | <= 1 draft render (`RENDER full`) logged for the round; 0 for an all-audio round; the delivery render only after `APPROVED`; lock free before it; ETA message sent for jobs > 3 min | CHANGELOG `RENDER full` / `APPROVED` lines + `render_lock status` | stop the extra render | revision-notes-handler | each render |
| G8 present | draft opened in the browser pane with the notes page; message numbered by the user's notes, full ledger status, QA numbers measured on the new file (or `not run`), gaps listed, `PRESENTED` line written | the message + `round_check.py --require-present` | re-send | revision-notes-handler | file newer than the last patch |
| G9 learn | one lesson per note, round count and minutes recorded | retro entry | add | revision-notes-handler | end of round |

## Stop conditions
- Mid-render note: first half of the render, stop your own tree and rerun after collection; second half, finish and take the note next round unless it is a blocker.
- Three rounds on the same theme: stop polishing, present 2-3 replacement concepts on a `visual-choice-board` (any choice whose options are visual, 2 or more, goes on a board: stills when the difference is the look; short Studio ranges or range renders when it is motion).
- A note contradicts a locked ledger row: show both, ask which wins; do not choose silently.
- The user asks for a paid fix: route through `paid-spend-gate` before any call.

## References and scripts
- `references/diagnosis-and-classification.md`: load when a note arrives and you must find its cause or class (cause table, classes, ambiguity, mid-render rule).
- `references/round-log-and-presentation.md`: load when opening a round, writing ledger rows, or presenting (CHANGELOG format, Hebrew and English message).
- `references/patch-discipline.md`: load when you are about to patch files or choose how to verify a fix (patch format, ladder with times, audio-only branch, long-job protocol).
- `scripts/round_check.py`, `scripts/apply_patch.py`, `scripts/notes_board.py` (the review page: video + timed notes + one send button; same guards as the choice board): stdlib, each with `--self-check`.
- Shared technique (other owner): `agent-content/techniques/studio-review-loop.md` (the measured Studio-first loop); ledger rules: `agent-content/techniques/concept-ledger.md`; render and delivery: `render-qa-delivery`.

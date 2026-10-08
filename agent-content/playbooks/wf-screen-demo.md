# wf-screen-demo — A screen recording into a demo or tutorial (הדגמת מסך / הדרכה)

> Status: **provisional** — specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-08. There is no owner rubric for this type yet: score it with the closest one (`motion-graphics.rubric.md` for a voice-led product demo, `talking-head.rubric.md` when a face cam carries it) and label the result provisional. All numbers below are **house defaults, unmeasured**.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[IDEA]` · `[CONFLICT]` · 💲 = paid step · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | a variant of stages 1–8 for one screen recording (with or without a face cam and narration) → one demo or tutorial |
| Owner skill | `pro-video-editor` (the edit), `captions-transcription` (captions), `render-qa-delivery`; the zoom, dead-time and cue steps are this playbook |
| Artifacts (exact files) | `projects/<name>/source/<recording>` (the student's own), `_work/analysis/<video-id>/` (prep: transcript, sheet), `_work/zoom.json` (`tools/screen_zoom.py`), `hf/PROMPT.md`, `_work/storyboard/storyboard.json` (screen beats `shot: screen`), `_work/promise.json`, `final/<name>_<platform>_<aspect>.mp4` |
| Exit gate | **GS — every narrated action is visible and readable, no dead time left, no cue miss, callouts clear of the UI being shown** |
| Target time | **not measured** |
| Paid steps | none on the core path; a synthetic voice-over 💲 only through `paid-spend-gate` |

## 1. Principle

**Show the click, cut the wait.** The viewer must see every action the voice names, at a size they can read, the moment it is named, and never wait for the computer. A screen recording is mostly waiting and tiny text; the edit is what turns it into a lesson.

**The recording is the student's own.** The agent never installs a screen recorder or captures the student's screen. When there is no recording yet, the student records it with what their computer already has (the operating system's own screen recording, or the app they already use). `[RULE-owner]` (no installs without the student's yes; client screens are private data, AGENTS.md "Secrets, privacy, safety").

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| a screen recording exists in `source/`, made by the student | `_work/intake/source_ls.txt` | ask for it; send the recording tips below in ONE message; do not install a recorder |
| the recording shows nothing private (passwords, client data, other people's messages, notifications) | a contact sheet the student looked at | blur or crop the frames, or ask for a re-record |
| intake answered: platform and aspect, speech and caption language, narration (recorded with the screen, a separate voice-over, or none), face cam or not | ledger rows (`video-brief-intake`) | ask in one bundled message |

Recording tips (one message, only when a new recording is needed): record at the delivery resolution or higher; scale the interface up (125–150 % in the display settings) so text survives the crop; turn notifications off; keep the cursor visible and move it slowly; pause a beat before and after each click; record 10 s first and check that the sound is clean.

## 3. Steps

| # | Step | Who | Evidence |
|---|---|---|---|
| 1 | **Probe and prep.** Screen recorders often write a variable frame rate: conform to one constant fps first, at the delivery fps: `ffmpeg -i source/<recording> -vf fps=<fps> -fps_mode cfr -c:v libx264 -crf 16 -c:a copy source/<name>_cfr.mp4` (a new file; the original stays untouched). Run `prep.py --language <Round 0>` for the transcript and the word table. | agent | `_work/analysis/<id>/`, `hf/data/words.json` |
| 2 | **Map the screen:** `python tools/screen_zoom.py source/<name>_cfr.mp4 --words hf/data/words.json --dead-s 1.0 --min-crop 0.5 -o _work/zoom.json` (`--dead-s 1.0` matches the dead-time rule in §4, `--min-crop 0.5` keeps every zoom at 2x or less) — where on screen things change over time (boxes), suggested zoom keys, dead-time ranges (no change and no speech), and cue misses (a narration line with no screen change within ±1.5 s). | agent | `_work/zoom.json` |
| 3 | **Paper edit:** the task as steps joined by "but" / "therefore" (`pro-video-editor` `references/story-and-structure.md`, "Explainer story logic"); open on the result or the problem it solves, not on the desktop. | agent; person approves | `hf/SCRIPT.md` or the PROMPT.md script block |
| 4 | **Cut or speed the dead time** (§4), and write that cut as an intermediate picture file (`_work/screen_cut.mp4`, plus its re-timed word table through `word_retime.py`). Every later time is on THIS timeline: run `screen_zoom.py` again on `screen_cut.mp4` so the zoom keys match the cut. | agent | the edit list, `_work/screen_cut.mp4`, `_work/zoom_cut.json` |
| 5 | **Zoom on the action** (§4): the zoom keys from `zoom_cut.json` become the camera path's windows (`python tools/camera_path.py _work/zoom_cut.json <its camera_path_args> -o _work/camera`); every key is checked for readability. `camera_path` pans sideways only: when the action sits high or low in the frame, choose a scale whose crop still contains it vertically, or keep that beat full-screen. | agent | the camera path data + the readability table in PROMPT.md |
| 6 | **Storyboard** (Step 3b of `pro-video-editor`): one beat per action, `shot: screen` for full-screen views and `detail` for zoomed ones; real frames from the recording. Then `STORYBOARD APPROVED`, then `promise_check.py lock`. | agent; person approves | `storyboard.json`, `hf/CHANGELOG.md`, `_work/promise.json` |
| 7 | **Callouts, captions and sound** (§5). | agent | composition + `hf/cues.json` |
| 8 | **The cue check before the draft:** the cue misses in `zoom_cut.json` (the cut timeline and its word table; no extra render); every cue miss is fixed or has a written reason. Then `promise_check.py check`. | agent | the second `zoom.json` (0 misses or reasons), the check output |
| 9 | **Studio first**, then ONE draft render, then the notes page (`revision-notes-handler`); the delivery render only after `approved`. | agent; person reviews | per-round QA |

## 4. Zoom, dead time and readability (house defaults, unmeasured)

| Rule | Value | Why |
|---|---|---|
| Dead time | a dead range of 1 s or more is cut (`--dead-s 1.0` in step 2); a wait the viewer must see happen (an export, a progress bar) is sped up 4–8x with its sound off, and the last 0.5 s plays at real speed so the result is seen arriving | waiting teaches nothing; the real-speed end keeps the result believable |
| Speech | never sped up or pitch-shifted; a sped-up stretch carries no narration | sped speech sounds broken |
| Zoom target | the active box from `zoom.json` fills about 60–80 % of the frame width | big enough to read, with enough around it to show where it is |
| Zoom move | eased, 0.4–0.8 s for a single move in, starting about 0.3 s before the click; a zoom out followed by a zoom in (a reversal) follows `pro-video-editor` `references/camera-and-motion.md`: each move at least 1.0 s and the range at most 1.3x, or cut instead of moving | the viewer sees the target before the click lands; a fast in-out-in reads as a glitch |
| Zoom hold | at least 1.5 s per zoom; no zoom in and out on every click | constant zooming is seasick, not clear |
| Orientation | zoom out to the full screen when the place changes (a new window, page or app), then back in | the viewer keeps the map of the screen |
| Readable text | the UI text the viewer must read is at least 40 px tall at 1080 px output width (the house number for key details) | phone viewers read the screen, not the voice |
| Crop width | crop width in source px ≤ text height in source px × output width ÷ 40. Example: 16 px labels in a 1920-wide recording into a 1080-wide 9:16 output → crop ≤ 16 × 1080 ÷ 40 = 432 px | turns "readable" into a number you can check per zoom key |
| Magnification limit | more than about 2x the source pixels looks soft: ask for a re-record with the interface scaled up, or at a higher resolution | upscaled UI text blurs and looks broken |

## 5. Callouts, captions and sound

- **Callouts never cover the UI being shown.** Arrows, labels, keystroke badges and highlights go in empty space outside the active box from `zoom.json` (plus a margin of about 24 px); one callout at a time; it enters after the zoom settles and leaves before the next move. Why: a callout over the button hides exactly what it points at.
- **Captions do not echo on-screen text:** when the voice reads a label that is on screen and readable, the caption for that window is left out (`pro-video-editor` `references/type-and-colour.md`, "Captions and on-screen text"). Captions stay clear of the active box.
- **Sound:** a soft click only on clicks the viewer sees, low under the voice (about -24 dB); room tone under the voice when there is no music bed (`pro-video-editor` `references/sound.md`); a music bed, when asked for, stays low and ducks under every line.
- **Face cam (optional):** a small corner cam that never covers the active box; it moves to the other corner when the action goes there.

## 6. Exit gate GS

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| every action the voice names is visible within ±1.5 s of the words | `_work/zoom_cut.json`: 0 cue misses, or each with a written reason | else `fail` |
| no dead range of 1 s or more left uncut or unsped | `_work/zoom_cut.json` dead-time list | else `fail` |
| every zoom key passes the readable-text rule (or the student approved a re-record) | the readability table in PROMPT.md + stills of the zoomed frames | else `fail` |
| no callout overlaps an active box | stills at each callout + the boxes in `zoom.json` | else `fail` |
| no private data on screen | the contact sheet the student looked at | else `blocked` |
| the promise kept (length, aspect, captions, music, voice, beats) | `promise_check.py check` exit 0 | else `fail` |
| the draft passed wf-06 (every frame, loudness, captions) | `_work/qa/` envelopes | else `fail` |

Gate record → `hf/QA.md` "Gate log".

## 7. Human vs agent

| Human | Agent |
|---|---|
| records the screen (with their own tools); checks the contact sheet for private data; approves the paper edit, the storyboard and each draft | probes and conforms; maps the screen; cuts the dead time; plans zooms with the readability numbers; places callouts, captions and sound; runs the cue check and the promise check |

## 8. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| "I can't read it on my phone" | the crop is too wide for the source text size | tighten the zoom to the crop-width formula; above 2x, ask for a re-record with the UI scaled up | §4 readability rows, checked per zoom key |
| the voice says "click Export" while the screen still shows the menu | narration and picture drifted after cutting | J- or L-cut the line, slip the picture, or cut the line | the cue check (step 8) |
| the video feels slow although it is short | waits left in at real speed | cut or speed every dead range | step 4 |
| the zoom pumps in and out | a zoom key on every small change | merge keys closer than 1.5 s; hold | §4 zoom hold |
| an arrow hides the button it points at | callout placed by eye | place it outside the active box | §5 |
| a password or a client name visible for 3 frames | not checked before editing | blur or crop; re-check every frame of that range | entry gate |
| choppy motion in the recording | variable frame rate | conform to one constant fps before cutting | step 1 |

## 9. Tool invocations

`prep` · `screen_zoom` · `camera_path` · `word_retime` · `hf_segment` (range renders of render-only risks) · `hf_preflight` · `hf_mix` · `hf_deliver` · `frame_qa` · `caption_qa` · `sheet`; skill scripts `storyboard_board.py` and `promise_check.py` (`pro-video-editor`). Flags are schematic; see `docs/TOOLS.md`.

## 10. Per-type deltas

This **is** a type. Relative to a talking-head edit: the screen, not the face, is the A-roll; zoom keys come from screen changes, not faces; readability is the main craft; dead time replaces silence as the thing to cut; the rubric is borrowed and provisional.

## 11. Time labels

Owner target: none stated. Modelled: none. Measured: none.

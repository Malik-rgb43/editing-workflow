---
name: render-qa-delivery
description: >-
  Run the cheap-first render, QA and delivery pipeline for a HyperFrames video: preflight, range renders, one full render, final-file loudness and mux, every-frame and visual QA, manifest, timing ledger. Triggers: רינדור, תריץ בדיקה לפני רינדור, מסירה, בדוק את כל הפריימים, render the final, run QA on this render, deliver the 9:16 version, present the draft. NOT for creative decisions (`pro-video-editor`), client notes (revision-notes-handler), or variants of one master (video-variants-exporter).
compatibility: >-
  Needs ffmpeg/ffprobe, Python 3.12 and a HyperFrames CLI pinned per project; scripts are stdlib only. Render times and traps are measured or reported on one reference machine with HyperFrames 0.8.79-0.8.98; re-verify per version.
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# render-qa-delivery

The pipeline that proves a file: preflight -> check -> snapshots -> Studio/range renders -> ONE full render under the lock -> final-file loudness/mux -> every-frame QA -> 4-axis visual review -> manifest, with a timing ledger written along the way. It never decides the look.

## Start: connections
If `<project>/_work/connections.json` from this session exists (written by the router or `pro-video-editor`), read it; otherwise run `python tools/connections.py -o <project>/_work/connections.json` (about 1 s, presence only) and read your own tool list (claude.ai connectors appear only there). For this skill: the pinned HyperFrames CLI (Studio, check, snapshot, render; `doctor` node_engine), FFmpeg/ffprobe (mux, loudness, QA), the browser pane or Playwright MCP (to open Studio, contact sheets and the delivered file for the user). Say use / not needed / fallback in one line, then continue. A missing connection never stops the work; anything paid goes through `paid-spend-gate`.

## Rules that outrank the rest
1. **Fail closed.** A gate that cannot run reports `not_run` / `INSUFFICIENT_EVIDENCE`. A timeout, an empty sample, a missing, stale or different file never passes. A pass means the test ran on its stated coverage; "0 findings" from an empty sample is not a pass.
2. **Cheap first.** Seconds-level checks before minutes-level renders. Each round: check in Studio, then ONE draft render (`python tools/hf_deliver.py ... --draft`), which is the round's one full render, then the notes page on that file (`revision-notes-handler`). The delivery render runs only after the notes page returns `approved`. The draft render waits until every note and reviewer is in; audio-only change = remix + remux, no render.
3. **One heavy job at a time** (`render_lock`: render, `check`, Blender, ASR, matte, colour bake). Never take over a stale lock while its author's lifetime is uncertain. No heavy agent while a render runs (a parallel Blender job took a render from 11.5 to 21.5 min).
4. **No paid action.** A cloud or hosted render needs a dated estimate and approval (`paid-spend-gate`).
5. **Measure the FINAL file** (length, loudness, true peak, black frames, edge band). The render's own audio is discarded: mux `mix.wav` or two-pass loudnorm. The "render attenuates audio by ~11.5 dB" report was seen once and not reproduced: measure anyway.
6. **Every trap is a scoped historical report until a fixture passes on the pinned build.** Re-verify per HyperFrames version: the 1088 canvas, root `dir=rtl`, snapshot-vs-render, the `<video>` 1-frame preview offset (G9).
7. `snapshot --describe false`, at most 5 timestamps per call (a description key can send frames to a remote model); `HYPERFRAMES_NO_TELEMETRY=1`, `HYPERFRAMES_NO_UPDATE_CHECK=1`, `HYPERFRAMES_SKIP_SKILLS=1`; never `feedback` with client material; ASCII work root.
8. **Stale-file guard.** QA only on a file newer than the render start and the last patch; chain commands with `set -o pipefail` (a `check | tail && render` rendered after a failed check); never present a file older than the last patch.
9. **House preset v1 (decision default Q5):** -14 LUFS +-0.5, true peak <= -1 dBTP, 1088 canvas for 1080-wide masters. Destination profiles are configurable; a client's written spec overrides the preset.

## Inputs -> outputs
Entries: a round ready for its draft render (stages 0-7, then `revision-notes-handler` opens the notes page); `approved` from the notes page (stage 0, stage 1 preflight, the delivery render at stage 5, stage 6 on that file, stage 9); more outputs after approval go to `video-variants-exporter` stage 1 (freeze).
In: `hf/` project, approved PROMPT.md, `assets/mix.wav` (or the render's audio), the ledger. Out: `final/<name>_<platform>_<hook>_<aspect>.mp4`, `final/manifest.json`, `_work/qa/<ver>/` (envelopes, sheets), `_work/timing_ledger.jsonl`, a QA report with coverage statements.

## Stages (details and commands: `references/pipeline-stages.md`)
Times per stage: `references/volatile-facts.md`.
| # | Stage | Command shape |
|---|---|---|
| 0 | Readiness | `render_lock status`; notes collected; assets, matte, ASR, Blender finished |
| 1 | Static preflight | `hf_preflight <hf> --strict`; `grep -c 'data-start="-'` = 0; ledger-id grep |
| 2 | check | `set -o pipefail; timeout 900 render_lock run -- npx hyperframes check --timeout 600000` |
| 3 | Snapshots | `snapshot --at t1,t2,t3,t4,t5 --describe false` at transitions, new effects at peak, keywords at full size |
| 4 | Studio review / range render | `preview`; `hf_segment <hf> --from a --to b --qa` only for render-only risks |
| 5 | Full render | the round's ONE draft render (`hf_deliver <hf> --name <n> --draft`), then the notes page; the delivery render (`--quality delivery`) only after the notes page returns `approved` |
| 6 | Automatic QA, new file only | `frame_qa` (`--allow t0-t1` for each PLANNED fast run, e.g. images on 16th notes; any other single-frame jump fails), the voice-over-music level per phrase when music sits under a voice (`hf_mix --report`), `caption_qa` only if PROMPT.md has captions (band from the aspect's preset; no captions = `n/a`), `motion_qa`, `face_center audit`, `color_check`, then `qa delivery` / `scripts/qa_aggregate.py` |
| 7 | Visual review, 4 axes | contact sheets, tiles <= 180-270 px; reviewer count by length (`references/visual-review.md` section 2) |
| 8 | ONE fix round | one numbered list -> one patch -> stages 1-4 on touched ranges -> one full render -> 6-7 on corrected ranges |
| 9 | Deliver | verify on the final file; manifest; naming; present: open the file (Studio for a draft) and the contact sheets in the browser pane unasked, then the message (`references/delivery-and-manifest.md` section 7) |

## Long jobs (anything over 3 min; `references/long-job-protocol.md`)
Benchmark one unit -> ETA in one chat line ("full render ~11 min, 1,520 frames at 2.3 fps, done ~14:32") -> `timeout` on every command (render = 3 x ETA, check 900 s) -> background with a log and a `STATE` line -> heartbeat every ~5 min -> watchdog (0 frames after 3 min, or no progress for 10 min: kill YOUR OWN process tree, check the lock, one snapshot, retry once) -> partial results at once. ETA > 30 min for one shot: offer an alternative before starting. If the user had to ask "what about the render?", log a protocol failure.

## Gates
States: `pass | fail | blocked | n/a` with a reason; a timeout, empty sample or missing input is `blocked`.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 preflight | `hf_preflight --strict` exit 0: no Studio ids, no root RTL, no stale timing grid, no duplicate ids, no media in `preserve-3d`, no negative `data-start`; if PROMPT.md has captions, they sit inside the aspect's caption rail (9:16: bottom edge <= y 1450) | exit code + report text | fix before any render | this skill | any source edit |
| G2 lock | one heavy job at a time | lock file with a live PID and a heartbeat; `render_lock status` | wait; never auto-take over a stale lock | this skill | each heavy job |
| G3 long-job protocol | ETA line posted, `timeout` set, heartbeat running, watchdog armed | ETA line, log, `STATE` line | state the ETA and arm the watchdog before starting | this skill | each job > 3 min |
| G4 one full render | range renders for verification; ONE draft render per round after all notes and reviewers; at most one delivery render, only after `approved` | ledger: `render_full` = 1 and `render_delivery` <= 1 per round (`scripts/ledger_summary.py summary --strict`) | stop duplicate renders, batch notes | this skill | each round |
| G5 delivery gate | duration within 1 frame of `data-duration`; -14 +-0.5 LUFS; TP <= -1; no black >= 2 frames; no dead edge band; measured on the FINAL file | `hf_deliver` verify block + ffprobe + ebur128 output | re-mux (no render) or fix the mix | this skill | any audio, edge or length change |
| G6 QA coverage | `frame_qa`, `caption_qa` (when there are captions), `motion_qa` (+ `face_center audit`, `color_check`) each state their coverage on the NEW file; same sha256; decoded = expected frames | envelopes aggregated by `qa_aggregate.py` | treat `not_run` as fail; fix and re-run | this skill | every new render |
| G7 visual review | 4 axes on all-frame sheets, reviewer count per `references/visual-review.md` section 2 (under 20 s: self-review); one fix round; rubric >= 4.0 with no dimension < 3 where a rubric exists | reviewer files with time, axis, severity, fix | fix all in one round, same critic | this skill | changed ranges |
| G8 manifest | every file's `from_master` equals the master `src_hash`; finals folder = finals + manifest only; naming per spec | `manifest.json` + hash recompute | re-render the stale derivative; reject "ready" | this skill | any master change |
| G9 version re-verify | each scoped trap (1088 band, root RTL, snapshot-vs-render, audio level) has a recorded fixture result for the pinned HyperFrames version | fixture log with version and date | run the minimal fixture; keep the workaround until it passes | this skill | any HyperFrames or driver upgrade |

## QA statuses and coverage (details: `references/qa-thresholds.md`)
Envelope: `{tool, version, input_sha256, decoded_frames, expected_frames, coverage, status: PASS|FAIL|INSUFFICIENT_EVIDENCE, findings[]}`; exit non-zero on FAIL or INSUFFICIENT_EVIDENCE. Intentional flags (approved black frames, deliberate holds) need an exemption that is time-bounded and tied to an approved PROMPT.md row; a blanket "ignore flags" is rejected. Model reviewers cannot certify waveform metering, every-frame completeness, exact Hebrew copy or pixel-safe geometry: a contact sheet is not "the model watched the video".

## Timing ledger
One JSONL line per stage attempt (`scripts/ledger_summary.py append`): stage, UTC start/end, queue wait, setup/run minutes, renders, retries, credits (null is not 0). The ledger is how a student replaces the modelled budget in `pro-video-editor` with measured numbers.

## References (load when)
- `references/pipeline-stages.md` - running any stage; command text, snapshot points, stale-file guard.
- `references/long-job-protocol.md` - starting a job over 3 min; lock rules; agent supervision.
- `references/qa-thresholds.md` - interpreting a QA tool; blind spots; exemptions; envelope.
- `references/delivery-and-manifest.md` - loudness, mux, 1088 canvas, naming, manifest, presenting.
- `references/visual-review.md` - before reviewing or presenting a draft.
- `references/volatile-facts.md` - before quoting a time, a trap or an issue number.
- Scripts: `scripts/qa_aggregate.py` (fail-closed aggregator), `scripts/ledger_summary.py` (ledger append/summary); both stdlib with `--self-check`; script paths are relative to this skill's folder. Siblings: `revision-notes-handler`, `video-variants-exporter`, `pro-video-editor`, `captions-transcription`, `speaker-color-correction`.
- Repo-level modules (owned elsewhere): `agent-content/techniques/cheap-first-qa.md`, `agent-content/techniques/studio-review-loop.md`, `agent-content/techniques/timing-ledger.md`, `agent-content/references/hyperframes-traps.md`, `agent-content/references/audio-mix.md`, `agent-content/references/platform-specs.md`; load when you need their dated tables.

## Evidence status
From the author's projects and experiments E04, E11, E12; the eight E04 tool defects (`references/qa-thresholds.md` section 3) must be fixed before the tools grade students.

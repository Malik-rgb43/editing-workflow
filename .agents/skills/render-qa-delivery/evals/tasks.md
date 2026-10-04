# render-qa-delivery - task evals

Status: specified; deterministic checks only; model eval not run (decision default Q4). Fixtures are synthetic (ffmpeg-generated) or the student's own; no client media. Oracles are artifacts, not the executor's self-report.

## T1 single full render
- **Setup:** an approved draft and six queued notes (audio, typo, global caption position, 3D timing, shader, video+glyph).
- **Oracle:** `_work/timing_ledger.jsonl` summarised by `scripts/ledger_summary.py summary --strict`.
- **Pass:** the summary shows exactly ONE `render_full` in the round; the other verifications are Studio preview or `render_range`; the audio note was a remix + remux with no render; the ETA line was posted before the full render and a heartbeat ran; `summary --strict` exits 0.

## T2 vacuous pass
- **Setup:** run QA on a render whose caption file is missing (or whose `frame_qa` decoded 0 frames).
- **Oracle:** the aggregate verdict (`scripts/qa_aggregate.py`) and the agent's message.
- **Pass:** the verdict is `INSUFFICIENT_EVIDENCE` (not_run), never `PASS` or "0 findings"; the agent reports which tool did not run and why and does not call the file ready.

## T3 final-file loudness
- **Setup:** a mix at -17 LUFS (true peak -0.2 dBTP) muxed into a render.
- **Oracle:** ebur128 output on the FINAL file and the `hf_deliver` verify block.
- **Pass:** the agent measures the final file (not the mix), sees -17 LUFS / TP above -1, fixes the mix (pre-limit, two-pass loudnorm, pad to exactly DUR x 48000 samples) and remuxes without a picture re-render; the re-measured final file reads -14 +-0.5 LUFS and TP <= -1 dBTP; the video length is unchanged within 1 frame.

## T4 stale file
- **Setup:** a failed render leaves the previous `final.mp4` in place; the user says "run QA".
- **Oracle:** mtimes vs `_work/.render_start` and the aggregate verdict.
- **Pass:** the agent detects the file is older than the render start and last patch, refuses to QA it as the new render, and reports `blocked`; a `check | tail && render` pipeline is not used (`set -o pipefail`).

## T5 1088 fixture per version
- **Setup:** a plain grey composition at width 1080 and at 1088, on the pinned HyperFrames version.
- **Oracle:** a decoded-frame measurement of the right 8 columns per mode and `hf/QA.md`.
- **Pass:** the agent runs both widths, records version and date, and keeps or retires the 1088 workaround from the measurement (not from the author's report); with no fixture result gate G9 stays `blocked`.

## T6 stuck job
- **Setup:** a render shows 0 frames after 3 minutes with a leftover headless browser from a prior stop.
- **Oracle:** the agent's actions and `render_lock status`.
- **Pass:** the agent kills only its own process tree, checks the lock, takes one snapshot to diagnose, retries once, tells the user, and does not start a second heavy job beside the first.

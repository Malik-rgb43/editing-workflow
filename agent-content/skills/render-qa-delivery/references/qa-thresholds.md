# QA thresholds, envelope, blind spots, exemptions

Load when: interpreting any QA tool output, writing a coverage statement, deciding whether a flagged frame blocks delivery. Dated 2026-10-02; sources: distilled 01 rules-and-gates E, F, H; distilled 02 qa-and-benchmarks; blueprint QA_AND_BENCHMARKS §1-§5, TOOLS_SPEC §1; E04 defects.

## 1. The status vocabulary and envelope
Every QA tool emits JSON and exits non-zero on FAIL or INSUFFICIENT_EVIDENCE:
```json
{"tool":"frame_qa","version":"x.y","input_sha256":"...","decoded_frames":1350,"expected_frames":1350,
 "coverage":1.0,"status":"PASS","findings":[{"t0":3.1,"t1":3.13,"kind":"black","severity":"blocker"}]}
```
Statuses: `PASS | FAIL | INSUFFICIENT_EVIDENCE` (research vocabulary adds `not_run | unsupported | error`; map each to INSUFFICIENT_EVIDENCE in the aggregate: a required check disabled stays `not_run`). Rational fps/PTS everywhere: report frame number AND real timestamp (30000/1001 drift guard). A pass requires `decoded_frames == expected_frames > 0` and the same `input_sha256` as the final file. Undefined precision/recall denominators are "unavailable", never perfect.

## 2. Thresholds the author's tools used (the reference machine, historical; presets, not platform law)
| Tool | Detects | Threshold / parameter | Notes |
|---|---|---|---|
| `frame_qa` | black frame | mean luma < 6 | `--allow-black a:b` for an approved intentional black |
| | flash | brightness jump > 60/255 that returns within 2 frames | |
| | pop | single-frame outlier | |
| | static hold | > 1.0 s (`--hold 1.0`) | motion pieces; intentional holds need an exemption |
| | double jump at a cut | frame diff c-1..c+2: one spike = synced, two spikes 1-2 frames apart = out of sync | |
| | outputs | `report.md`, `flagged.jpg` (flagged frame with previous and next), `all_XX.jpg` sheets of ALL frames labelled number + time (`--cols 12 --rows 10 --tile 160`) | decodes every frame at 96x54 grey for the metric; holds frames in RAM (long/VFR sources: see limits) |
| `caption_qa` | caption text vanishing in ONE frame | band default y 950-1320, x 120-960 at 1080x1920 (use `--band <top>:1450`); bright-pixel (luma > 175) count falls > 85 % between consecutive frames while the previous had > 900 text px | frames with whole-frame change > 12 are reported as cut-synced |
| `motion_qa` | camera stutter | pan abs(acceleration) > 1500 px/s^2 (`--acc 1500`), zoom > 0.6 fraction/s^2, pan reversal at speed | gate 0 stutter ranges; `camera_path` design target <= 400 px/s^2 |
| `face_center audit` | speaker off-centre | tolerance 30 px | candidates: confirm each on a frame |
| `color_check` | speaker colour | see `speaker-color-correction` G5 | >= 85 % of sampled frames per check |
| `hf_deliver` verify | length, loudness, black, edge | duration within 1 frame; -14 +-0.5 LUFS; TP <= -1 dBTP; no black segment >= 2 frames; no dead right-edge band (30 sampled frames) | PASS proves mux/loudness/black/edge only: not captions, motion, face, colour, benchmark or ledger |
| `benchmark score` | descriptive percentile bands | 100 inside p25-p75, 70 inside p10-p90, 30 outside; hard gates TP > -1 dBTP, aspect, unintended stepped cadence | descriptive, not a quality score |

## 3. Measured blind spots (E04, synthetic Windows fixtures; fix in the port BEFORE any tool grades students)
| ID | Defect | Required behaviour |
|---|---|---|
| E04-B01 | `caption_qa` missing input exits 0 with 0 frames | missing input -> INSUFFICIENT_EVIDENCE, exit non-zero |
| E04-B02 | hard-coded 30 fps: f25 at 25 fps printed as 0.83 s (really 1.00 s) | read fps from the stream (rational) |
| E04-B03 | abrupt caption APPEARANCE not detected although the docstring promises it | implement or remove the claim; report "not checked" |
| E04-B04 | `benchmark.py` treated a numeric 0.0 dBTP as missing (score 30/100, exit 0) | `is None`, never falsy |
| E04-B05 | failed hard gate printed but exit 0 | structured gate results + exit code |
| E04-B06 | `hf_preflight` single-quoted duplicate ids pass | structural HTML parsing |
| E04-B07 | `motion_qa` crashes on a low-feature clip | INSUFFICIENT_EVIDENCE with tracked-pair coverage |
| E04-B08 | kit A/B parser regex starts with a U+0008 byte (counts 0 flags) | not shipped |
Static findings (not reproduced): `hf_deliver --skip-render` bypasses preflight and the freshness guard and can remux a stale picture after a visual change (bind the raw file to build hashes); `hf_segment` logs failures without a failing exit; `frame_qa`/`motion_qa` hold every frame in RAM and use nominal fps; face/colour audits skip frames with no detection and can pass with zero coverage; two overlapping caption plates and clipped glyphs are undetected without a bbox/timeline collision check (a prototype finds the f30-45 overlap exactly).
Regression fixtures = the E04 synthetic set made with FFmpeg only (black, flash, freeze, caption drop at 25/30 fps, caption overlap, clipped audio, low-feature clip), run on Windows, macOS and Linux CI. Positive AND negative controls per tool.

## 4. Coverage statement (put in every QA report)
"File <name> sha256 <12>, mtime <time> (newer than render start <time>). <tool>: <decoded>/<expected> frames at <fps>, band <...>, checks run: <list>, NOT checked: <list>. Pass = the test ran on this coverage." For a model-assisted review add the exact images and windows it saw, and what it did not see (vendors document 1 FPS default video sampling and first-frame-only animated input for some models: a contact sheet is not "the model watched every frame").

## 5. Intentional flags: time-bounded exemptions
The author's rule says "never present a file with a flagged frame"; a shipped project accepted flagged black/flash frames as intentional. Resolution used here: a finding is exempt ONLY if an exemption row (a) names the tool, (b) gives a numeric time window containing the finding, (c) cites the approved PROMPT.md row or ledger id that planned it, (d) has a reason. Decision table: approved intentional -> exempt (listed in the report); known non-blocking -> logged with a reason in `hf/QA.md`; missing check -> add to preflight; blocker -> fix. A blanket exemption is rejected. `scripts/qa_aggregate.py --exemptions` implements this.

## 6. Reviewer limits
A vision model reading contact sheets can nominate defects; it cannot certify waveform metering, every-frame completeness, exact Hebrew copy or pixel-safe geometry. Do not rank or average a creative score over an unauthorized act: hard-gate failures veto the soft score.

## Sources
distilled 01 rules-and-gates E, E.1, F, H; distilled 02 qa-and-benchmarks §1-§4; blueprint QA_AND_BENCHMARKS §1-§5; blueprint TOOLS_SPEC §1-§2; E04 via those files; checked 2026-10-02.

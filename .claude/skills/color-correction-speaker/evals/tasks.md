# color-correction-speaker - task evals

Status: specified; deterministic checks only; model eval not run (decision default Q4). Fixtures are synthetic or the student's own footage. Oracles are artifacts inspected independently of the executor's self-report.

## T1 source discipline
- **Setup:** a folder with `rough_cut.mp4` (1080p, ~2 Mbps) and `C0001.MP4` (4K, ~96 Mbps, rotated 90 degrees) plus an `assets/` folder.
- **Oracle:** the agent's first message and `data/grade.json` (colour-contract record).
- **Pass:** the agent lists the tree, selects the camera file, says why in one line (headroom, 4K -> 1080 downscale, rough cut is a compressed re-encode), records its sha256, rotation and colour tags, and refuses to grade the rough cut; gate G1 `pass` with the `ls` output as evidence.

## T2 numeric gate
- **Setup:** a plate with pink skin (hue ~95 degrees, Y 46 %) and hazy black shirt (Y 12 %, Cb +7); `measurements.json` before and after the bake (synthetic numbers are acceptable for the gate part).
- **Oracle:** `scripts/grade_gate.py gate` verdicts, the before/after sheet, the grade JSON.
- **Pass:** the BEFORE measurements give `FAIL`; after a two-stage fit and bake the AFTER measurements give `PASS` with a coverage statement; skin inside the named preset band; before/after sheet delivered at 3+ cuts and one 100 % crop; a measurement file with only 3 person frames or a missing sample gives `INSUFFICIENT_EVIDENCE`, never `PASS`.

## T3 forbidden path
- **Setup:** the user asks: "just use data-color-grading skin-soft, it is faster".
- **Oracle:** the agent's reply and the project files.
- **Pass:** the agent explains the traps (global, applies to the whole media, first frame ungraded, hung the render on the reference machine's stack), bakes the grade in ffmpeg instead, leaves `grep -c data-color-grading hf/*.html` at 0, and keeps the user's goal (a softer skin look) as a fit target rather than refusing it.

## T4 HDR source
- **Setup:** an iPhone clip tagged `arib-std-b67` / `bt2020` (or a synthetic file with those tags) next to an SDR clip.
- **Oracle:** the colour-contract record and the output tags.
- **Pass:** the agent probes both, converts the HDR clip to SDR with a real tone map (not a retag), records the override/conversion in `data/grade.json`, and does not apply the speaker preset numbers until the converted clip has been measured; a missing probe leaves G2 `blocked`.

## T5 named preset, not a universal target
- **Setup:** an indoor, moody multi-shot clip and the request "make the skin 46 % like the outdoor test".
- **Oracle:** the agent's chosen preset and fit targets.
- **Pass:** the agent selects `indoor-cinematic-multishot-v1` (skin Y 34-42, subject node `lift_ev` only), explains why the outdoor preset would look bright and commercial, and asks the user to approve a reference frame; no complexion table is applied.

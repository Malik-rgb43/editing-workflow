---
name: speaker-color-correction
description: >-
  Colour-correct footage of a person (talking head, interview, UGC, speaker outdoors) from the CAMERA ORIGINAL with scopes, a numeric fit, a subject matte and a baked plate, then gate the render. Triggers: תקן צבע, הצבע לא טוב, העור נראה ורוד / כתום, הפנים חשוכים, הקליפ שטוח, גריידינג, skin too pink, grey sky, hazy blacks, match colour between cuts. NOT for stylised or LUT-only looks on stock clips, AI-film looks (ai-generated-video-editor), or the edit (talking-head-editor).
compatibility: >-
  Needs ffmpeg and Python 3.12; the colour toolchain (color_*) needs numpy/numba/scipy and a person-matte model. Timings are from one reference machine; the bundled script is stdlib only.
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# speaker-color-correction

Corrects skin, sky, blacks and clip-to-clip matching on real speaker footage: scopes -> numeric fit against a NAMED preset -> subject matte -> bake into a file -> gate. The grade is a file, never an attribute.

## Rules that outrank the rest
1. **Camera original only.** `ls` the whole source tree, find the camera file (4K, 50-100 Mbps), hash it, and say why in one line. Never grade the compressed rough cut (in the reference case: a 1080p 2.2 Mbps re-encode of a 4K 96 Mbps 8-bit rotated camera file; the 4K -> 1080 Lanczos downscale gave sharper, cleaner images and real headroom). Not found -> ask for it.
2. **Measure before touching; numbers AND eyes.** Scopes first (waveform, RGB parade, vectorscope with the skin line at 123 degrees, histogram, skin sample). Numbers alone passed visibly bad frames; the eye alone is fooled by a bright monitor: check on a phone and on a before/after sheet.
3. **Targets are a NAMED PRESET from one reference, not universal** (decision default Q5). Never encode complexion, gender or ethnicity lookup tables as pass/fail; derive a preset from an owner-approved reference frame per lighting group (`references/presets.md`).
4. **No `data-color-grading` on a speaker, no global `shadows +` / `highlights -` / vibrance on a two-illuminant scene.** Bake with ffmpeg (LUTs, curves, colorbalance) so the grade is part of the file; HyperFrames then renders graphics only.
5. **Colour contract first:** probe range, matrix, transfer, primaries per clip. HDR (HLG, PQ, Dolby Vision) needs a real conversion to SDR; tagging 709 is not a conversion. Unknown or contradictory tags -> an explicit override with provenance and a preview, never a silent 709 assumption (`references/colour-contract-hdr.md`).
6. **No stylisation, AI upscale, denoise or eye-contact change unless asked** (the author rejected an AI upscale and a stylised grade on one AI-generated film). No paid action. A clipped sky stays clean white; it is kept neutral, not recovered.
7. Heavy jobs (matte, bake) run under `render_lock`, never beside a render; cap `--workers` at 4 (the original default 6 competes with other jobs).

## Inputs -> outputs
In: camera original, the rough-cut timeline (if any), a named preset or an approved reference frame. Out (project-relative): `data/grade.json` (small diffable parameter set), `hf/assets/aroll.mp4` (baked, 30 fps, `-g 15`), `_work/colour/before_after.jpg`, `_work/colour/color_check.json`, a note naming the preset and the camera file hash.

## Procedure
1. **Source + contract.** Rule 1, then probe (`ffprobe`: rotation, fps, `color_range`, `color_space`, `color_transfer`, `color_primaries`, pix_fmt). Grade the camera file directly. If only a rough cut matches the edit, map its time to the camera clock by audio cross-correlation first (no tool for this yet: do it with ffmpeg and say so in the report; the rough cut lagged its audio by 1 camera frame in the measured case).
2. **Scopes** at 3-6 spread times (`color_scopes <video> --at t... [--rotate 2] [--roi-face]`); record skin Y / hue / chroma, black-clothing Cb/Cr/Y, sky chroma, p1, p99, clipping. Save the sheet.
3. **Preset.** Pick a named preset or derive one (`references/presets.md`); say which scene it describes.
4. **Fit in two stages** (`color_fit --stage global`, then `--stage subject --fixed global.json`): few free parameters, WB gains luminance-preserving, `lift_ev` owns exposure; a parameter sitting on its bound = degenerate, constrain it. Log solver success/message/cost/nfev and look at the before/after sheet each iteration (`color_fit ... --sheet before-after.jpg`); convergence is not acceptance.
5. **Matte + bake.** Person matte on the padded person box; the subject node blends in by a soft matte; bake two 65^3 `.cube` LUTs through ffmpeg (`color_render <camera original> --params grade.json --matte matte.mp4 -o hf/assets/video/aroll.mp4`, or `grade_bake` for a simple chain), x264 CRF 11-12, 6-frame pre-roll, one 30 fps base. Details: `references/fit-and-bake.md`.
6. **Gate.** `color_check <final.mp4> --step 2 [--ignore a-b]`, then `scripts/grade_gate.py` on its measurements for the preset verdict and coverage statement. Re-fit only if the scene light changes.
7. **Handoff.** Remove any `data-color-grading`, re-cut the cutout from the corrected plate (`talking-head-editor` G7), view the first 3 frames after every A-roll return, run the matte-flicker check, send the before/after sheet at 3+ cuts plus one 100 % face crop.

## Gates
States: `pass | fail | blocked | n/a` with a reason. A timeout, an empty sample, a missing frame set or an unreadable file is `blocked`, never `pass`.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 source | the graded input is the camera original, not an export/rough cut | `ls` of the source tree, path + sha256 of the camera file, probe output | ask for the original; do not grade the proxy | this skill | a new source file appears |
| G2 contract + scopes | range/matrix/transfer/primaries recorded; HDR converted; scope sheet + skin/black/sky numbers recorded at >= 3 times | probe JSON + scope sheet | re-probe, convert, re-measure | this skill | any clip added or re-exported |
| G3 fit | two-stage fit toward a NAMED preset; solver status logged; no parameter pinned to a bound; before/after sheet looked at | fit log + the `color_fit --sheet` image | constrain parameters; pick the right preset (indoor/AI-film differ) | this skill | scene light changes |
| G4 bake | subject matte, WB for the face separate, neutral black, clean sky; baked into the file; no `data-color-grading`; no global `shadows +`; 6-frame pre-roll | bake log + `grep -c data-color-grading hf/*.html` = 0 + first 3 frames viewed | re-bake | this skill | grade or cut list changes |
| G5 color_check | per sampled frame with a person: skin Y within +-9 of target, hue 105-125 degrees, chroma 16-32, black abs(Cb) and abs(Cr) <= 3 and Y <= 9 %, sky chroma <= 3, p1 >= 1 %, p99 >= 95 with bright sky; >= 85 % of evaluable frames pass each check; enough evaluable frames | `color_check` JSON -> `scripts/grade_gate.py` verdict with coverage | iterate once, then ask the user | this skill | any render of the speaker |
| G6 handoff + flicker | cutout cut from the corrected plate; matte flicker absent (`rendered_diff <= 1.35 x src_diff + 0.6`); before/after at 3+ cuts and a 100 % crop approved by a human | flicker JSON + sheet + approval message | smooth the matte (every frame + temporal smoothing); erode/blur | `talking-head-editor` | matte or grade changes |

## Cost and limits (the reference machine, historical, not re-run)
Bake about 3 min per minute of footage (59 s for 1,776 frames per the tool header); a u2net matte about 0.45 s each on the person box. Every number is `[LOCAL-only]`; re-measure with the timing ledger (`render-qa-delivery`). NVIDIA and Apple: unmeasured.

## Known conflicts (recorded, not resolved here)
- The author's complexion table (light skin Y 45-65, olive/Asian 35-55, dark 15-35) vs the T12 research verdict "drop universal skin numbers": the table is NOT encoded; a student derives a band from an approved reference.
- Matte every 3rd frame (speed) vs the periodic face-lift flicker it caused: use every frame + temporal smoothing for the colour matte.

## References (load when)
- `references/presets.md` + `references/presets.json` - choosing or deriving a preset; machine-readable gate bands.
- `references/fit-and-bake.md` - scopes conventions, tool parameters, fit pitfalls, bake recipes.
- `references/colour-contract-hdr.md` - HDR/log/full-range sources, unknown tags.
- `references/failure-modes.md` - symptom -> cause -> fix when the result looks wrong.
- `references/volatile-facts.md` - before quoting a timing, licence or tool claim.
- Script `scripts/grade_gate.py` (stdlib; `gate`, `flicker`, `--self-check`; script paths are relative to this skill's folder). Sibling skills: `talking-head-editor`, `render-qa-delivery`, `ai-generated-video-editor` (its own colour rules).
- Repo-level dated module (owned elsewhere): `agent-content/references/colour-presets.md`; load when you need the HDR branch table or the repo's preset naming.

## Evidence status
Method learned and measured on one outdoor talking-head test (2026-09-30) and one multi-shot brand film; T12 is a static audit with no colour run. Specified; deterministic checks only; model eval not run (Q4). Every target number is a named preset for its footage.

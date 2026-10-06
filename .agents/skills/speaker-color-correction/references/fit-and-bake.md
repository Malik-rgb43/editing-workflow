# Scopes, the two-node fit, matte and bake

Load when: measuring, fitting, baking, or debugging a grade. Dated 2026-10-02; sources: distilled 04 colour §1-§2 (owner docs and tool docstrings), distilled 06 talking-head-and-footage §1.8. The tools are `color_scopes`, `color_fit`, `color_render` and `color_check` (written for this toolkit and tested on synthetic clips; check `--help`). Not built: `color_fit_shots` (multi-shot fitting), `color_timeline`, `color_preview`.

## 1. Fixed order (each step feeds the next)
| # | Step | What happens | Tool |
|---|---|---|---|
| 1 | Measure | waveform, RGB parade, vectorscope (skin line 123 degrees, 75 % bar targets), histogram, clip/crush %, skin sample on the face | `color_scopes <video> --at t... [--rotate 2] [--out dir] [--roi-face] [--range tv or pc] [--width 540] [--json]` |
| 2 | Decode | BT.709 limited 16-235 -> float; work at 16/32 bit | inside the engine |
| 3 | Exposure + WB, global | on REAL neutrals (the black shirt), never grey-world over a clipped sky + foliage; WB attenuated in shadows so black stays neutral; shadow tint corrected by offset | engine |
| 4 | Local subject lift | person matte raises the face ~0.6 EV with a highlight guard; black shirt pinned; never global `shadows +` | engine |
| 5 | Tone | black pin (toe), pivoted S-curve, highlight shoulder (roll-off, not a lower white); clipped sky stays ~100 IRE | engine |
| 6 | Colour in OKLab | balance by range, saturation/vibrance, skin band toward the skin line, foliage band, sky desaturation (outdoor only) | engine |
| 7 | Subject node | own WB + saturation because the face light differs from the background light; two nodes blended by a soft matte (a power window) | engine / `color_render` |
| 8 | Shot matching | per cut, re-solve the subject lift so the face has the same brightness in every cut (`--trim auto`) | `color_render` |
| 9 | Dither + encode | float -> 8-bit with error diffusion; x264 CRF ~11; check on a phone | `color_render` |
Correct first, grade later; "leave as is" is a valid result.

## 2. Scope conventions
Levels as video levels (Y' 16 = 0 %, 235 = 100 %). R'G'B' derived from decoded Y'CbCr WITHOUT clipping so under/over-range shows on the parade. Vectorscope Cb right, Cr up; angles counter-clockwise from +Cb: R 104, Mg 61, B 347, Cy 284, G 241, Yl 167 degrees; skin line (I axis) 123 degrees. Skin measurement = median CbCr-box pixels on the head band of the person mask. Reading stills with ffmpeg: use `scale=...:in_range=tv:out_range=pc:out_color_matrix=bt709` and `format=rgb48le`; without `in_range=tv` stills shift colours.

## 3. The fit
- `color_fit <camera original> --at t1,t2,t3 -o grade.json (--faces faces.json | --skin-roi x0,y0,x1,y1) [--black-roi ...] [--sky-roi ...] [--preset speaker-plate-v1] [--stage global|subject] [--fixed grade_global.json] [--sheet before_after.jpg]`: a bounded pattern search over a few NAMED parameters toward the numeric bands of a NAMED preset, measured on regions computed once per sample frame; it refuses without a skin region and for a process-only preset. The JSON records cost before/after, whether the search converged locally, which parameters sit on a bound (degenerate: constrain them) and which gate bands are met after the fit.
- Global stage free: `ev, wb_r, wb_b, sat, contrast, black` (bounds `ev +-1.5`, `wb_r 0.9-1.25`, `wb_b 0.72-1.05`, `sat 0.9-1.6`, `contrast -0.3..0.8`, `black 0-0.08`). Subject stage free: `lift_ev 0-1.2, s_wb_r 0.9-1.1, s_wb_b 0.9-1.1, s_sat 0.9-1.3` (the global parameters stay fixed). All maths is in linear light; the LUTs are encoded-in / encoded-out. Unknown parameter names are an error, never a silent no-op.
- Few free parameters per stage. Fitting everything at once degenerates (extreme WB cancels low saturation). A parameter sitting on its bound = degenerate: constrain it (WB gains luminance-preserving, `lift_ev` owns exposure).
- Solver acceptance is NOT convergence: `least_squares` success means local convergence. Record success/message/cost/nfev, active bounds, pre-clamp RGB extrema and clipped area (the original clips RGB before measuring, which hides clipping magnitude), per-ROI medians, circular hue error, and held-out frames. Look at the sheet every iteration.
- Multi-shot or AI footage: there is no multi-shot tool yet. Run `color_fit` per lighting group (`--at` times inside that group) against the same preset, keep one shared look, and render each group with its own `grade.json`; macro shots with no person use `color_render --subject-everywhere`. Review subject, retained environment light, noise/banding, matte borders and cut-to-cut continuity.
- Shot matching contract: segment by shot with source-time mapping; an approved reference frame per lighting group; fit a small bounded set; hold parameters within a stable shot; exclude transitions; review subject, retained environment light, noise/banding, matte borders and cut-to-cut continuity.

## 4. Matte and bake
- `color_render <camera original> --params grade.json -o hf/assets/video/aroll.mp4 [--matte matte.mp4] [--from S --to S] --fps <project fps> [--size 1080x1920] [--canvas 1088x1920] [--crf 11] [--preroll-frames 6] [--matte-blur 3] [--matte-erode 1] [--subject-everywhere]`: bakes the grade into TWO 65^3 `.cube` LUTs (GLOBAL, and SUBJECT = the same grade plus the person-only node) blended by `maskedmerge` with the eroded, blurred matte; WITHOUT `--matte` only the global grade is applied and the sidecar `<out>.grade.json` says so. The output is ONE constant-rate file (exact fps, `-g 15`; pass the project fps from `ffprobe` `r_frame_rate` or PROMPT.md, because the tool defaults to 30), verified for size, exact frame rate and frame count before it is reported (otherwise deleted, exit 2). LUTs are referenced by bare ASCII file name with the LUT folder as the working directory, so Hebrew or quote characters in your paths never reach the ffmpeg filter graph. The default pixel-format conversion of the installed FFmpeg 8.1 blacked out the right-most columns of some widths; the tool forces `accurate_rnd` and the test suite checks the edge columns.
- Matte every frame + temporal smoothing for the colour matte: a matte refreshed every 3rd frame (faster) caused a periodic face-lift flicker. Erode and blur the matte; subject lift above ~0.7 EV on a hard matte gives hot halos; subject WB + saturation on the matte turned a white coat pink; counting channel clipping only on skin let coat/window highlights blow.
- Simple chains (`grade_bake`): `ffmpeg -i in.mp4 -vf "eq=brightness=0.03:contrast=1.08:saturation=1.1,colorbalance=rs=-0.03:bs=0.03" -c:a copy out.mp4` or `-vf "lut3d=file=look.cube:interp=tetrahedral"`; x264 CRF 12, 6-frame pre-roll, `-g 15`. Greens barely respond to `huesaturation colors=g` after a LUT: use `selectivecolor` + `colorchannelmixer gg=0.86`.
- Output contract: ONE continuous base at the project fps (`-g 15`) at `hf/assets/video/aroll.mp4`, padded to a multiple of 16 for the 1088-canvas rule (`render-qa-delivery`): in grade chains `pad=1088:1920:0:0` before `gbrp` and `crop=1080:1920:0:0` at the end.
- Pre-roll: every graded A-roll piece starts 6 frames early under the layer above (a shader-node grade renders the first frames ungraded or frozen; 3 frames was not always enough). Baking removes the cause; still view the first 3 frames after every return.

## 5. Gate and handoff commands
1. `color_check <final.mp4> -o measurements.json (--faces faces.json | --skin-roi x0,y0,x1,y1) [--black-roi ...] [--sky-roi ...] [--step 2] [--ignore 43-46.5 ...]` samples every 2 s; it refuses without a person region (a skin band judged on pixels chosen BECAUSE they are skin-coloured would be circular); frames with no person are skipped; `--ignore t0-t1` for deliberate colour-drain beats (an approved intentional beat, written in PROMPT.md); black clothing and sky are measured only when their regions are given, otherwise the gate treats them as not measurable (declare them n/a, never pass).
2. `python scripts/grade_gate.py gate measurements.json --preset speaker-plate-v1 --json verdict.json` (stdlib): preset verdict with a coverage statement; empty or too-small samples are `INSUFFICIENT_EVIDENCE`.
3. Matte flicker: `python scripts/grade_gate.py flicker series.json` on per-frame face-region luma of source vs render.
4. Project: remove `data-color-grading`; re-cut cutouts from the corrected plate (`cutout`); run the usual delivery gates; before/after sheet at 3+ cuts and one 100 % crop: no halo around head/shoulders, no plastic skin, shirt neutral, grass not neon.

## 6. Quick colour pipelines for non-speaker clips (stock, short)
Measure with `ffmpeg -hide_banner -i <clip> -vf "signalstats,metadata=print:file=-" -frames:v 1 -f null -` at several `-ss` points and look at a frame; neutral correction (exposure, WB, contrast, saturation); match shots within a scene side by side; check skin, sky, whites, no highlight clipping. Creative looks on stock belong to a different skill.

## Sources
distilled 04 colour §1.1-§1.2, §2, §5 (tool docstrings color_scopes/engine/fit/fit_shots/render/timeline/preview/io/check; T12 static audit, no colour run); distilled 06 talking-head-and-footage §1.8; checked 2026-10-02.

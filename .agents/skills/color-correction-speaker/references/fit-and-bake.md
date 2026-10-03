# Scopes, the two-node fit, matte and bake

Load when: measuring, fitting, baking, or debugging a grade. Dated 2026-10-02; sources: distilled 04 colour §1-§2 (owner docs and tool docstrings), distilled 06 talking-head-and-footage §1.8. Tool names are the ported student tools (`color_*`); parameters are from the owner's originals and may change in the port.

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
- `color_fit <video> --at t... --rotate 2 --out grade.json [--targets targets.json] [--stage global|subject] [--fixed g.json] [--free ...] [--width 270]`: least squares over listed free parameters against numeric targets measured on region masks computed ONCE on the source frame; prints before/after tables; writes only non-default parameters.
- Global stage free: `ev, wb_r, wb_b, lift_r, lift_b, sat, fol_sat, black, contrast`. Subject stage free: `lift_ev, s_wb_r, s_wb_b, s_sat`. Typical bounds: `ev +-1.5`, `wb_r 0.9-1.25`, `wb_b 0.72-1.05`, `lift_ev 0-1.2`, `sat 0.9-1.6`, `skin_rot +-30`, `contrast -0.3..0.8`, `black 0-0.08`, `pivot 0.3-0.6`. Gentle regularisation toward identity; hue residual is wrap-aware; `max_nfev 200`, `diff_step 0.01`.
- Few free parameters per stage. Fitting everything at once degenerates (extreme WB cancels low saturation). A parameter sitting on its bound = degenerate: constrain it (WB gains luminance-preserving, `lift_ev` owns exposure).
- Solver acceptance is NOT convergence: `least_squares` success means local convergence. Record success/message/cost/nfev, active bounds, pre-clamp RGB extrema and clipped area (the original clips RGB before measuring, which hides clipping magnitude), per-ROI medians, circular hue error, and held-out frames. Look at the sheet every iteration.
- Multi-shot or AI footage: `color_fit_shots shots.json --look look.json --out grade_shots.json [--sheet sheet.png]`; stage 1 global free `ev, wb_r/g/b, skin_rot`, stage 2 subject free `lift_ev, s_wb_r, s_wb_b, s_sat` (bounds `s_wb +-0.5 %`, `s_sat 0.98-1.02`, `lift_ev 0-0.70`, `ev -1..1.3`, `skin_rot -8..3`); the LOOK (contrast, toe, shoulder, split-tone) is fixed and shared so every cut matches; macro shots with no person use the whole frame as the subject.
- Shot matching contract: segment by shot with source-time mapping; an approved reference frame per lighting group; fit a small bounded set; hold parameters within a stable shot; exclude transitions; review subject, retained environment light, noise/banding, matte borders and cut-to-cut continuity.

## 4. Matte and bake
- `color_render --timeline timeline.json --params grade.json --out hf/assets/video/aroll.mp4 [--from --to] [--workers 4] [--fps 30] [--size 1080x1920] [--rotate 2] [--trim auto|none] [--crf 11]`: bakes the per-pixel grade into TWO 65^3 `.cube` LUTs (GLOBAL and SUBJECT = same grade + person-only correction) applied by ffmpeg with tetrahedral interpolation; a soft person matte (u2net on the padded person box, 540x960, upsampled in ffmpeg) blends the two LUT results with `maskedmerge`; segments run in parallel; ffmpeg does decode, Lanczos 4K -> 1080, both LUTs, merge, dither, x264. Runs under the heavy-job lock. The shipped original hard-coded one camera path and 30 fps / 1080x1920: parametrise it in the port. The runtime assertion on fps accepts 30.5 with a fixed-30 graph: validate the exact rational rate (test 30, 29.97, 30.5, variable).
- Matte every frame + temporal smoothing for the colour matte: a matte refreshed every 3rd frame (faster) caused a periodic face-lift flicker. Erode and blur the matte; subject lift above ~0.7 EV on a hard matte gives hot halos; subject WB + saturation on the matte turned a white coat pink; counting channel clipping only on skin let coat/window highlights blow.
- Simple chains (`grade_bake`): `ffmpeg -i in.mp4 -vf "eq=brightness=0.03:contrast=1.08:saturation=1.1,colorbalance=rs=-0.03:bs=0.03" -c:a copy out.mp4` or `-vf "lut3d=file=look.cube:interp=tetrahedral"`; x264 CRF 12, 6-frame pre-roll, `-g 15`. Greens barely respond to `huesaturation colors=g` after a LUT: use `selectivecolor` + `colorchannelmixer gg=0.86`.
- Output contract: ONE continuous 30 fps base (`-g 15`), padded to a multiple of 16 for the 1088-canvas rule (`render-qa-deliver`): in grade chains `pad=1088:1920:0:0` before `gbrp` and `crop=1080:1920:0:0` at the end.
- Pre-roll: every graded A-roll piece starts 6 frames early under the layer above (a shader-node grade renders the first frames ungraded or frozen; 3 frames was not always enough). Baking removes the cause; still view the first 3 frames after every return.

## 5. Gate and handoff commands
1. `color_check <final.mp4> --step 2 [--rotate 0] [--skin-y 46] [--ignore 43-46.5 ...] [--json out.json] [--width 270]` samples every 2 s; frames with no person (B-roll, graphics) are skipped; `--ignore t0-t1` for deliberate colour-drain beats (an approved intentional beat, written in PROMPT.md).
2. `python scripts/grade_gate.py gate measurements.json --preset speaker-plate-v1 --json verdict.json` (stdlib): preset verdict with a coverage statement; empty or too-small samples are `INSUFFICIENT_EVIDENCE`.
3. Matte flicker: `python scripts/grade_gate.py flicker series.json` on per-frame face-region luma of source vs render.
4. Project: remove `data-color-grading`; re-cut cutouts from the corrected plate (`cutout`); run the usual delivery gates; before/after sheet at 3+ cuts and one 100 % crop: no halo around head/shoulders, no plastic skin, shirt neutral, grass not neon.

## 6. Quick colour pipelines for non-speaker clips (stock, short)
Measure with `ffmpeg -hide_banner -i <clip> -vf "signalstats,metadata=print:file=-" -frames:v 1 -f null -` at several `-ss` points and look at a frame; neutral correction (exposure, WB, contrast, saturation); match shots within a scene side by side; check skin, sky, whites, no highlight clipping. Creative looks on stock belong to a different skill.

## Sources
distilled 04 colour §1.1-§1.2, §2, §5 (tool docstrings color_scopes/engine/fit/fit_shots/render/timeline/preview/io/check; T12 static audit, no colour run); distilled 06 talking-head-and-footage §1.8; checked 2026-10-02.

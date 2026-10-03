---
module: colour-presets
checked_at: 2026-10-02
expires: "180 days (2027-03-31); re-check the HDR rows on any FFmpeg/OCIO/Resolve version change"
confidence: "targets are NAMED PRESETS approved on specific footage [PROVEN-internal][MEASURED-lab] (one clip); T12 is a static source audit [VERIFIED-external]; no colour run by the research"
refresh: "free: ffprobe the colour tags, run scopes on your own frames, read the standards catalogues; no cloud grading"
---

# Colour presets, gates and the HDR branch — dated reference

| Field | Value |
|---|---|
| Fact set | the colour-correction pipeline for footage of a person, named numeric presets, render-gate thresholds, multi-shot/AI-footage rules, HDR → SDR branch table |
| Versions / ids | BT.709 limited-range working assumption; ITU BT.2100-3 and BT.2408-9 (catalogue status read 2026-10-01); FFmpeg 8.1 (`zscale`, `tonemap`, `lut3d`, `libplacebo`); OCIO 2.5.x / ACES 2 (candidate only); HyperFrames 0.8.98 grading features |
| `checked_at` | **2026-10-02** (= research date; **must be refreshed before use**) |
| Source | `distilled/04-…/colour.md` (owner method + T12 audit); owner feedback notes (anonymised) |
| Scope / plan / region | speaker footage; the targets were approved on **one** outdoor talking-head clip and one indoor multi-shot film; 8-bit SDR 709 sources |
| Confidence | **the numbers are presets, not standards** (T12: BT.2408-9 notes differing production levels, creative context and makeup) |
| `expires` | see front matter |
| Non-spending refresh | `ffprobe` tags; scopes on three spread frames; before/after sheets; read the BT.2408/ACES pages; nothing paid |

## 1. Rules that are laws for the owner (`[RULE-owner]`)
1. **Correct from the CAMERA ORIGINAL**, never from the export or rough cut. List the whole source tree for the camera file (4K, 50-100 Mbps) before touching colour; a 4K → 1080 Lanczos downscale is sharper and has real headroom. Check rotation. `[PROVEN-internal]`
2. **Measure before touching:** waveform, RGB parade, vectorscope (skin line 123°), skin Y/hue/chroma, black-clothing tint, clipping/crush. Read the numbers, not the eyes (a bright monitor misleads; check on a phone). Technical before creative; luma before chroma; **white balance on real neutrals** (e.g. black clothing), never grey-world over a clipped sky + foliage.
3. **Never a global `shadows +`, `highlights −` or vibrance on a two-illuminant scene.** The automatic grade that did this (shadows +0.24, highlights −0.12, vibrance +0.32) produced a grey sky (p99 88%), a hazy bluish black shirt (black 7%, Cb +7.5), magenta/pink skin (hue 79° vs the 123° line; the face lit by cool skylight) and orange grass. Use **two nodes**: a GLOBAL grade and a person-matte SUBJECT node (local lift + its own WB). `[PROVEN-internal][MEASURED-lab]` (one clip)
4. **Bake the grade into the file** (a person matte + two 65³ LUTs applied by FFmpeg with tetrahedral interpolation; ~3 min per minute of footage vs ~40 min per-pixel on the reference machine `[LOCAL-only]`); re-cut cutouts from the corrected plate. **Never use HyperFrames `data-color-grading` for a speaker** (global, first frame ungraded, hung with a `skin-soft` preset on the reference machine's stack). Pick a look on one frame with `grade-compare`, then bake.
5. **Gate every render** with the colour check; numbers alone passed visibly bad frames, the eye alone is fooled by a bright monitor — use both.

## 2. Pipeline (fixed order) `[PROVEN-internal]`
1 **measure** (scopes at 3-6 spread times; skin = median of CbCr-box pixels on the head band of the person mask) → 2 decode BT.709 limited 16-235 to float, work in 16/32 bit → 3 exposure + WB global (on the black shirt; WB attenuated in shadows) → 4 local subject lift (person matte raises the face ~0.6 EV with a highlight guard; the black shirt stays pinned) → 5 tone (black pin/toe, pivoted S-curve, highlight shoulder = roll-off, **not** a lower white; clipped sky stays ~100 IRE) → 6 colour in OKLab (colour balance by range, saturation/vibrance, skin band, foliage band, sky desaturation) → 7 subject node separately (own WB + saturation) → 8 shot matching (re-solve subject lift per cut so the face has equal brightness) → 9 dither + encode (x264 CRF ~11; check on a phone).
Fit the grade in **two stages with few free parameters** (global: ev, wb_r, wb_b, lift_r, lift_b, sat, fol_sat, black, contrast; subject: lift_ev, s_wb_r, s_wb_b, s_sat); fitting everything at once degenerates (WB extreme + low saturation cancel; a parameter sitting on its bound is degenerate → constrain). **Solver acceptance is not convergence:** record success/message/cost/nfev, active bounds, pre-clamp RGB extrema and clipped area, per-ROI medians, circular hue error, held-out frames; always look at before/after sheets. Stills from FFmpeg without `scale=…:in_range=tv:out_range=pc` shift colours.

## 3. Named presets (copy the name AND the limit)
| Preset | Skin Y | Skin hue | Skin chroma | Black clothing | Sky / grass | Frame |
|---|---|---|---|---|---|---|
| **speaker-plate v1** (outdoor/commercial talking head) | ~46% (complexion-dependent; light 45-65, olive/Asian 35-55, dark 15-35 per a colourist guide) | ~118° (skin line 123°, up to ~2° toward red) | ~24 codes (ColorChecker skin sits at 18-24) | Cb = Cr ≈ 0, Y ≈ 5% (12%+ = haze) | sky neutral ≤ 100%; grass chroma ≈ 25-28, Y ≤ 65 | p1 ≥ 3%, nothing clipped except sky |
| **indoor / cinematic multi-shot v1** | 34-42, **never darker than the original face** | ~119-123° | ~23 | black_uv 0 | no `sky_desat`; vibrance ≤ 0.10 | p99 ≤ 96, p1 ≥ 2, whole-frame channel clip cap 0.25% |
| **AI-generated footage** | start natural | consistent skin hue ACROSS cuts | — | — | — | per-shot WB, mild exposure; **no AI upscale, halation, vignette or teal-orange unless asked**; show before/after at real size first |

`[CONFLICT]` T12 vs the complexion table: **do not encode complexion/gender lookup tables as universal pass/fail rules**; derive targets from an owner-approved frame/ROI under matched lighting with plausible luminance/hue bounds and uncertainty. The owner rule stands for owner work; teaching presents the numbers as a *named preset* approved against a reference frame. Indoor/cinematic targets differ from speaker-plate (Y 34-42 vs 46): both approved for their genres. For cinematic multi-shot: subject node = `lift_ev` only (WB + saturation on the matte turned a white coat pink; lift > ~0.7 EV on a hard matte gave hot halos — erode and blur the matte); hand-lock macro shots (the automatic fit is unstable when skin fills the frame and there is no white reference); build from the ORIGINAL clips.

## 4. Render gate (per sampled frame with a speaker; PASS needs ≥ 85% of frames per check) `[PROVEN-internal]`
skin Y within **±9** of target · skin hue **105-125°** · chroma **16-32** · black |Cb|,|Cr| **≤ 3** and Y **≤ 9%** · sky chroma **≤ 3** · p1 **≥ 1%** (no crush) · p99 **≥ 95** when there is bright sky. Frames without a person (B-roll, graphics) are skipped; `--ignore t0-t1` for deliberate colour-drain beats. A gate that cannot run (no speaker found, decode failure) reports `not_run`, never PASS. Check at 3+ cuts and one 100% face crop: no halo around head/shoulders, no plastic skin, shirt neutral, grass not neon.

## 5. Simple cases (stock, short clips)
Correction first, grading after; "leave as is" is a valid result. Measure with `ffmpeg -i clip -vf "signalstats,metadata=print:file=-" -frames:v 1 -f null -` (YAVG/YMIN/YMAX/SATAVG/HUEAVG) at several `-ss`. Bake with FFmpeg: `eq=brightness=0.03:contrast=1.08:saturation=1.1,colorbalance=rs=-0.03:bs=0.03` or `lut3d=file=look.cube`. **LUT-only for quick looks on stock** (fine) vs **never `data-color-grading` for a speaker** (owner) — a scope difference, not a contradiction.

HyperFrames grading features `[SOURCED-unverified]`: `media-treatment` writes `data-color-grading='{"preset":"warm-daylight","intensity":1}'` on one real element; 13 core presets; `.cube` LUTs up to size 64; realtime grading applies to the **entire** media (no face/plate isolation) and is Rec.709/SDR only; `grade-compare` renders ≤ 16 candidates + a neutral baseline on a frame; **never read a `.cube` into context** (33³ ≈ 36k lines); ingest your own with `--from` (validated, size-limited).

## 6. HDR → SDR and the colour contract `[VERIFIED-external]` (static audit; nothing run)
Intake must establish the **colour contract first**: the inspected renderer assumes limited-range BT.709 (range + matrix conversion, then tags 709) and contains no transfer linearisation, BT.2020 → 709 primaries conversion, HDR tone map or Dolby processing; the scopes probe only dimensions and decode uint8 `yuv444p`. **Retagging 709 is not a conversion.** A source tagged BT.2020 PQ/HLG makes the HyperFrames render switch to HEVC 10-bit HDR; `render --sdr` forces SDR and tone-maps; the realtime `media-treatment` path is Rec.709/SDR only.

| Input | Route (candidate designs, not tested commands) | Stop/review |
|---|---|---|
| known SDR 709 limited | decode range/matrix to a named working representation; fit | tags disagree |
| full-range SDR | explicit full → working range | no double expansion |
| camera log/raw | camera-specific documented input transform | unsupported camera/WB |
| HLG 2020 | declared linearisation + tone map + gamut mapping to an approved SDR | no reference condition |
| Dolby Vision 8.4 | RPU-aware candidate and a separately labelled HLG-base fallback | RPU decoding absent; no trusted SDR reference |
| graphics/CG | named asset encoding and premultiplication; apply the output view once | output view already baked |
FFmpeg facts: `tonemap` works on **single-precision float linear light**; `zscale` provides transfer/range/primaries conversion and needs `--enable-libzimg`; libplacebo `apply_dolbyvision` applies the RPU if present and its documented output is BT.2020 + PQ, so request and validate SDR explicitly; "FFmpeg always ignores Dolby metadata" is wrong, but side-data availability and the compiled filter must be tested. iPhone and generated HDR clips look washed when treated as 709: tone-map to SDR first, check `color_transfer` / `color_primaries` with `ffprobe`. ACES/OCIO: an arbitrary 709 display-rendered plate must not be treated as scene-linear by naming it ACES; pin OCIO engine/config separately; record LUT sha256, dimensions, interpolation, input/output encoding, baked status. Resolve: obtain the installed version/edition and its Developer Documentation README before proposing any automation — **do not invent a ColorMatch Python method**.

## 7. Matching contract (T12 recommendation `[IDEA]`)
Three different "automatic matching" families, not one algorithm: chart/patch fitting (needs corresponding patches), reference/histogram matching (confuses changed composition with changed lighting — match neutral and skin ROIs first), semantic region fitting (the owner method: original masks, region medians, wrap-aware hue residuals, bounds + identity regularisation). Segment by shot with source-time mapping; the owner approves a **reference frame per lighting/camera group**; fit a small bounded set; compare squared vs robust loss; hold parameters within a stable shot; exclude transitions; reject a creative failure even when the numbers pass. Regression corpus proposed (colour bars full/limited, mixed-lit faces, HLG/Dolby, two-camera chart sequence, exact 30/29.97/30.5/variable frame rates): not run.

## 8. Failure table
| Symptom | Cause | Fix |
|---|---|---|
| grey sky | `highlights −` pulled a clipped sky 100 → 88 IRE | keep ~100, neutral |
| hazy bluish black shirt | `shadows +`; camera blue tint | black pin + shadow-tint offset; WB on the shirt |
| magenta skin | face under cool skylight; global vibrance | subject node with own WB; skin band to the line |
| neon grass | vibrance on warm light | foliage chroma ≈ 25-28; saturation ≤ +10% |
| soft/blocky image | graded the rough cut | grade the 4K camera file |
| pink coat / halos | subject WB+sat on a hard matte; lift > ~0.7 EV | luma-only subject node; eroded + blurred matte |
| skin hue jumps between cuts | per-shot WB drift/stylised look | shared fixed look; check across cuts |
| washed HDR clip | HLG/Dolby treated as 709 | real tone-map first |
| fit converges but looks wrong | convergence ≠ acceptance; clipping hidden by pre-measure clamp | pre-clamp stats + held-out frames + visual review |

Open (T12): which SDR viewing target/reference white the owner approves; consented HLG/Dolby test inputs; installed Resolve edition; runtime fixtures for scopes, mask bias, clipping and timing; whether the hard-coded 709 assumptions break visibly on current sources (none shown). The 59 s ≈ 3 min bake and ~0.45 s per matte are unrerun `[LOCAL-only]`.

# Named colour presets (not universal targets)

Load when: choosing a target for the fit, interpreting `color_check`, or deriving a preset for a new scene. Machine-readable bands: `presets.json` (read by `scripts/grade_gate.py`). Dated 2026-10-02; sources: distilled 04 colour §0, §1, §6; distilled 01 rules-and-gates I1-I6; decision default Q5.

## Why presets and not law
The author approved numbers on specific footage. The T12 research audit found no source that makes them universal: BT.2408-9 notes that production levels, creative context and makeup change skin tones, so ethnicity/gender lookup tables are not encoded as pass/fail, and a low solver cost does not mean an acceptable grade. Teach the numbers as a named preset plus an exercise: measure a reference frame you approve, then use that.

## speaker-plate-v1 (one reference: an outdoor speaker, 4K camera original, tested 2026-09-30)
| Quantity | Target | Notes |
|---|---|---|
| skin Y | ~46 % | gate: +-9 |
| skin hue | ~118 degrees | skin line 123 degrees, up to ~2 degrees toward red; gate 105-125 |
| skin chroma | ~24 codes | gate 16-32 |
| black clothing | Cb = Cr = 0, Y ~5 % | 12 %+ = haze; gate abs(Cb), abs(Cr) <= 3 and Y <= 9 % |
| sky | neutral, <= 100 % | clipped sky stays ~100 IRE and clean; gate chroma <= 3, p99 >= 95 when bright sky |
| grass | chroma ~25-28, Y <= 65 | fit targets: Y 58, max 80 |
| frame | p1 >= 3 % in the fit, >= 1 % in the gate | nothing clipped except sky |
Measured result of the fix on that one clip: skin-hue error -40 degrees -> -4 degrees, black tint +7.5 -> 0, sky 88 % -> 99.5 %. The automatic grade it replaced (shadows +0.24, highlights -0.12, vibrance +0.32, global) gave grey sky (p99 88 %), hazy bluish black shirt (7 %, Cb +7.5), magenta skin (hue 79 vs the 123 line; the face was lit by cool skylight R40 G30 B34) and orange grass.
Fit weights used: skin_Y 1.0, skin_hue 1.4, skin_chroma 0.9, black_Y 0.5, black_u/v 1.2, sky 0.5, grass_chroma 0.4, grass_Y 0.5, grass_Y_max 0.6, p1_min 0.6.

## indoor-cinematic-multishot-v1 (a multi-shot indoor / moody brand film)
Skin Y 34-42 (floor: never darker than the original face), skin hue ~119-123, chroma ~23, white u -1 v 1.5, black uv 0, p99 <= 96, p1 >= 2, whole-frame channel clipping cap 0.25 %. Subject node = `lift_ev` ONLY (WB and saturation fixed near 1; matte eroded and blurred; lift above ~0.7 EV on a hard matte gives hot halos). No `sky_desat` indoors (it turned skin speculars pink/cyan), vibrance <= 0.10, hand-lock macro shots (the auto-fit is unstable when skin fills the frame), build from the ORIGINAL clips never from a re-exported or brightened edit. Using the speaker preset on this film made a "deep shadows with warm accents" brief look bright and commercial and turned a white coat pink.

## ai-generated-natural-v1 (AI-generated footage; process preset, no numeric gate)
Gentle natural correction first: per-shot WB, skin hue consistent ACROSS cuts (about 121 degrees in the reference), mild exposure; show before/after at real size BEFORE any stylisation; no AI upscale, halation, vignette or teal/orange unless asked; check skin hue and brightness across cuts. The numeric gate is `n/a` by design: the gate is a human approving the sheet.

## Deriving your own preset (the exercise)
1. Choose an approved reference frame per lighting/camera group (the author or client approves it; no complexion table).
2. Annotate the same semantic ROIs: neutral object or chart, skin without beard or specular, background; record coverage, confidence, rejected samples.
3. Read the numbers with `color_scopes` under the same conditions; write them as targets plus tolerances in a JSON like `presets.json` (`scripts/grade_gate.py --preset-file my.json`).
4. Fit a small bounded set; compare squared vs robust loss; hold parameters within a stable shot; exclude transitions.
5. Reject a creative failure even when the numbers pass, and the reverse.

## Deliberately not encoded
The author's skill table of skin Y by complexion (light 45-65, olive/Hispanic/Asian 35-55, dark 15-35) is an unverified colourist rule of thumb [CONFLICT with the T12 verdict above]. The author rule stands for his own jobs; the course does not ship it as pass/fail.

## Sources
distilled 04 colour §0, §1.1, §1.2, §5, §6 (src files: color_fit.py, color_check.py, color_fit_shots.py docstrings); distilled 01 rules-and-gates I1-I6; blueprint OPEN_QUESTIONS Q5; T12 audit via distilled 04 colour §5; checked 2026-10-02.

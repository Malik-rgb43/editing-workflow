# Lock one palette (DESIGN.md)

Load when: writing DESIGN.md, adding a 3D render/asset, or a colour note arrives.

The rule taught: **lock ONE palette per film, write it as a table before building, and audit every colour against it.** What the palette contains is the student's taste; the lock is the craft. (owner rule 2026-09-30: one palette with a rule per role across graphics, 3D and light effects; src: d04 motion-design §7; d05 image-and-design-assets §6)

## 1. DESIGN.md palette table (the format `scripts/palette_audit.py` reads)
```
| role | hex | rule |
|---|---|---|
| ground | #0B0D12 | dark scenes; never pure #000 |
| text | #E8ECF2 | all type; tinted off-white |
| accent | #2F6BFF | UI accent family; first appears on the reveal |
| keyword | #FCE500 | ONE keyword colour; verified contrast on the busiest background |
| alert | #FF5A36 | optional; errors/warnings only |
```
Structure to aim for: neutrals + ONE UI accent family + ONE keyword colour + optional alert (`palette_audit.py` warns above 3 chromatic hue families). 3-5 colours in total; a "foreign colour" appears once, deliberately, to mark a moment (a warm film-burn is an explicit exception the author allows). An example the author locked: Aegean `#0EA5E9` -> `#1D4ED8` with Sun `#FCE500` (a talking-head test, 2026-09). Do not copy another brand's signature colour (the Higgsfield lime family is on the author's banned list); take the grammar, not the costume.

## 2. Studio presets layered on the lock (taste, not law)
- The author dislikes pink/magenta (it leaked through a 3D render once; "I did not like the pink"). Run `palette_audit.py ... --forbid-hue 300-345` to enforce that preset; a student who wants pink writes it into the table and drops the flag.
- Accent colour not before the reveal in `launch` (a greyscale world first), except one deliberate story beat.
- Tint neutrals toward the accent instead of pure `#000`/`#fff`; one accent hue; no full-screen linear gradients on dark (H.264 banding): use radial or solid + localised glow. (vendor design tells, `[SOURCED-unverified]`)
- Contrast: keyword colour must stay readable on every background it crosses (yellow `#FCE500` measured 1.63:1 on a light ceiling; a dark warm top gradient riding with the camera made both yellow and white pass 3:1). Check pairs on the real frame.

## 3. The audit (G5)
1. `python scripts/palette_audit.py hf/DESIGN.md hf/ [--tolerance 0] [--allow #ffffff #000000] [--forbid-hue 300-345]` - every hex and `rgb()` in `.html .css .js .svg .json` must be in the table. Default tolerance 0 (exact); a small `--tolerance` accepts tints you deliberately derived (record why). `--allow` is for whites/blacks you decided to permit; it is a decision, not a default.
2. Every 3D/sprite render: `--png <render.png>`. The script reports the share of chromatic opaque pixels whose hue is > 25 degrees from every palette hue (default limit 3 %). It is a heuristic: lighting and AgX shift hue and saturation. A pass is not a visual review - view the render over the real background.
3. Blender: AgX makes brand colours pastel; pre-compensate the base colour or use the Standard view transform for exact hex; keep a calibrated base colour per brand colour. After a re-render the audit is repeated.
4. A new asset, a new 3D render or a colour note invalidates the previous result (recheck rule).
`blocked` when no palette table is found, nothing was scanned, or a render could not be read - never `pass`.

## 4. Fonts and tokens
Palette and type live in DESIGN.md; motion tokens too (`owner.enter` = `cubic-bezier(0.22,1,0.36,1)`, durations, easings, the slowest scene about 3x slower than the fastest). Tokens may follow the W3C DTCG 2025.10 community-report shape (it is a report, not a standard). One font family for the whole film unless the brief says otherwise; hierarchy by scale, extreme weight contrast (700-900 vs 300), <= 7 words per card, tracking -0.03 to -0.05 em on display sizes. (src: d04 motion-design §4, §7, §8)

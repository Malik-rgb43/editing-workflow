# Type and colour: one locked palette, one type system, Hebrew kinetic type

Merged on 2026-10-04 from the former type skills (one source per section, kept whole). Principles, not a template: use what fits the video in front of you and write the reason for each choice into PROMPT.md.


## Lock one palette (DESIGN.md)
<!-- source: pro-video-editor/references/type-and-colour.md -->
Load when: writing DESIGN.md, adding a 3D render/asset, or a colour note arrives.

The rule taught: **lock ONE palette per film, write it as a table before building, and audit every colour against it.** What the palette contains is the student's taste; the lock is the craft. (owner rule 2026-09-30: one palette with a rule per role across graphics, 3D and light effects; src: d04 motion-design §7; d05 image-and-design-assets §6)

### 1. DESIGN.md palette table (the format `scripts/palette_audit.py` reads)
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

### 2. Studio presets layered on the lock (taste, not law)
- The author dislikes pink/magenta (it leaked through a 3D render once; "I did not like the pink"). Run `palette_audit.py ... --forbid-hue 300-345` to enforce that preset; a student who wants pink writes it into the table and drops the flag.
- Accent colour not before the reveal in `launch` (a greyscale world first), except one deliberate story beat.
- Tint neutrals toward the accent instead of pure `#000`/`#fff`; one accent hue; no full-screen linear gradients on dark (H.264 banding): use radial or solid + localised glow. (vendor design tells, `[SOURCED-unverified]`)
- Contrast: keyword colour must stay readable on every background it crosses (yellow `#FCE500` measured 1.63:1 on a light ceiling; a dark warm top gradient riding with the camera made both yellow and white pass 3:1). Check pairs on the real frame.

### 3. The audit (G5)
1. `python scripts/palette_audit.py hf/DESIGN.md hf/ [--tolerance 0] [--allow #ffffff #000000] [--forbid-hue 300-345]` - every hex and `rgb()` in `.html .css .js .svg .json` must be in the table. Default tolerance 0 (exact); a small `--tolerance` accepts tints you deliberately derived (record why). `--allow` is for whites/blacks you decided to permit; it is a decision, not a default.
2. Every 3D/sprite render: `--png <render.png>`. The script reports the share of chromatic opaque pixels whose hue is > 25 degrees from every palette hue (default limit 3 %). It is a heuristic: lighting and AgX shift hue and saturation. A pass is not a visual review - view the render over the real background.
3. Blender: AgX makes brand colours pastel; pre-compensate the base colour or use the Standard view transform for exact hex; keep a calibrated base colour per brand colour. After a re-render the audit is repeated.
4. A new asset, a new 3D render or a colour note invalidates the previous result (recheck rule).
`blocked` when no palette table is found, nothing was scanned, or a render could not be read - never `pass`.

### 4. Fonts and tokens
Palette and type live in DESIGN.md; motion tokens too (`owner.enter` = `cubic-bezier(0.22,1,0.36,1)`, durations, easings, the slowest scene about 3x slower than the fastest). Tokens may follow the W3C DTCG 2025.10 community-report shape (it is a report, not a standard). One font family for the whole film unless the brief says otherwise; hierarchy by scale, extreme weight contrast (700-900 vs 300), <= 7 words per card, tracking -0.03 to -0.05 em on display sizes. (src: d04 motion-design §4, §7, §8)


## Hebrew and Latin kinetic typography
<!-- source: pro-video-editor/references/type-and-colour.md -->
Load when: any on-screen Hebrew (or mixed Hebrew/Latin/number) type is animated.

Source keys: d04 motion-design §8 (T10 + owner), d05 image-and-design-assets §2 (E03). E03 = a fixed-fixture font test (12 fonts, 1080x1920 shrunk to 360x640, Chrome Headless Shell 152, one vision model as the only reviewer; subjective, static images, no phone test). Fuller caption typography lives in `agent-content/references/hebrew-rtl-captions.md` (owned elsewhere). Hebrew correctness needs a native reader: no model or tool here proves it (decision default Q16).

### 1. Law (never broken)
- Keep Hebrew strings in **logical order**; never reverse a string to "fix" display order.
- `lang="he"` on `<html>`; `direction:rtl` on **text elements only**; never `dir="rtl"` on `<html>` or the composition root (black render).
- Isolate Latin brand names, prices, versions and phone numbers with `<bdi>` or `unicode-bidi:isolate`; `dir="auto"` for unknown input.
- Fonts from files (`@font-face`, `hf/fonts/`); wait for `document.fonts.ready` before measuring text; check the loaded font in a snapshot.
- Text is **never cut** by the frame, a camera move or another element.

### 2. Motion rules
- Reveal by **word or line first**; per-character only after combining marks (niqqud) and punctuation pass at intermediate reveal frames (a split library's international support does not certify mixed-script strings; default aria `auto` can lose nested link semantics).
- Wipes, scans, whips and per-word reveals run **right to left**; per-letter builds animate in reading order (an AE per-letter card once ran left to right: a bug).
- Keyword lands 0 to +7 frames after it is spoken; the graphic acts out the sentence (semantic sync).
- Keyword pop: scale 1.1 -> 1 with blur -> 0 inside the first 2 f (at 30 fps; the author's 60 fps table is halved), no overshoot on text.
- Words swap in place (`wordsSwap`), they do not re-appear elsewhere; numbers swap as a whole (see tables file).
- Per-letter random flicker: seeded per letter, baked with `tl.set` at each frame from a hash of (letter index, frame); keep flicker below 3 flashes per second over a large area (WCAG); glow only during the flicker, settling to clean text.
- Hero type <= 7 words per card, 60-80 % of the width for hero text, headlines 64-120 px (body 28-42, labels 18-24, anything under 24 px needs a reason; in-feed: body >= 32, headlines >= 90, data labels >= 24); tracking -0.03 to -0.05 em at display sizes; "3 s on screen must be readable in 2".

### 3. Fonts
- Baseline: Rubik (Hebrew + Latin, variable 300-900) for the author; Heebo the alternate; both OFL 1.1 (keep the licence notice with the binaries; never sell the font alone). Start with ONE bilingual family before adding a second Latin family; match actual cap-height, numeral width and optical weight in output frames (identical CSS px does not give identical perceived size).
- E03 means (1-5, one reviewer): Rubik 600, Alef 700, Noto Sans Hebrew 600 = 4.2; Heebo 600 = 4.0; Secular One 400 = 3.6; Assistant 600 = 3.2; Karantina 700 = 1.8 (unfit for continuous captions, not rejected for short large display titles). Display faces must pass a full-size test of ו/ז, ד/ר, ה/ח before approval.
- Adobe Fonts may appear in rendered video but their activated files must not be packaged for students; the working route is a web kit `<link>` (render needs network). Do not use SF Pro for client work.

### 4. Test fixtures (originals; run before approving type motion)
| String | Tests |
|---|---|
| `אותו לקוח. הזמנה גדולה יותר.` | word swap in place, punctuation |
| `₪102.60 — חיסכון של 12%` | currency placement, bidi, whole-number swap (no stray values in between) |
| `ACME (חדש) — מגיע ב־10:30` | Latin + parentheses + numerals + maqaf |
| `שָׁלוֹם` | niqqud survives a reveal |
| a mixed-direction 3-line wrap | line breaks, safe box |
Per fixture record: logical source, intended display order, font + version, rendered line widths, safe box, event hold; compare the displayed string to the source by eye with a Hebrew reader (OCR alone misses spacing and bidi punctuation). Check final letters ך ם ן ף ץ and the look-alike pairs. Prices: no unintended intermediate values during a whole-price transition.

## Common mistakes: highlights and surfaces
Load when: stressing a word on screen or building a glass or frosted surface. Moved from SKILL.md on 2026-10-06 (both came from one launch film's review).

| Mistake | Instead |
|---|---|
| A highlight box behind a word (it looks like a text selection) | Stress the word with colour, weight or a gradient and a faint glow |
| Glass or frosted UI on a plain white page (it shows nothing) | Put something behind it: a slow pastel aura or a blurred wash of the picture |

## Captions and on-screen text: one place for each word
Load when: a captioned video also shows words on screen (a title card, kinetic type, a UI label being read, a lower third, a price badge). Written 2026-10-08; editorial practice, not measured.

- **A caption never echoes on-screen text in the same window.** While the same words are already on screen, the caption for that line is left out (the caption track has a gap there, or that chunk is not built). Why: the viewer reads the same words twice in two places, the eye splits between them, and the graphic loses its moment.
- How to check it: for every caption chunk, list the on-screen text visible during its start-end window (the composition's text layers in that range, or a still at the chunk's middle). When most of the chunk's words are on screen, drop the chunk; when only one keyword is shared, keep the caption and let the graphic carry the keyword alone (the caption's other words stay).
- Plan it in the storyboard: a beat that shows the line as type (`text_only`, or kinetic type of the spoken words) is marked "no caption" in its `why`, so the caption builder (`captions-transcription`) skips that window.

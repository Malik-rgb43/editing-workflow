# Hebrew and Latin kinetic typography

Load when: any on-screen Hebrew (or mixed Hebrew/Latin/number) type is animated.

Source keys: d04 motion-design §8 (T10 + owner), d05 image-and-design-assets §2 (E03). E03 = a fixed-fixture font test (12 fonts, 1080x1920 shrunk to 360x640, Chrome Headless Shell 152, one vision model as the only reviewer; subjective, static images, no phone test). Fuller caption typography lives in `agent-content/references/hebrew-rtl-captions.md` (owned elsewhere). Hebrew correctness needs a native reader: no model or tool here proves it (decision default Q16).

## 1. Law (never broken)
- Keep Hebrew strings in **logical order**; never reverse a string to "fix" display order.
- `lang="he"` on `<html>`; `direction:rtl` on **text elements only**; never `dir="rtl"` on `<html>` or the composition root (black render).
- Isolate Latin brand names, prices, versions and phone numbers with `<bdi>` or `unicode-bidi:isolate`; `dir="auto"` for unknown input.
- Fonts from files (`@font-face`, `hf/fonts/`); wait for `document.fonts.ready` before measuring text; check the loaded font in a snapshot.
- Text is **never cut** by the frame, a camera move or another element.

## 2. Motion rules
- Reveal by **word or line first**; per-character only after combining marks (niqqud) and punctuation pass at intermediate reveal frames (a split library's international support does not certify mixed-script strings; default aria `auto` can lose nested link semantics).
- Wipes, scans, whips and per-word reveals run **right to left**; per-letter builds animate in reading order (an AE per-letter card once ran left to right: a bug).
- Keyword lands 0 to +7 frames after it is spoken; the graphic acts out the sentence (semantic sync).
- Keyword pop: scale 1.1 -> 1 with blur -> 0 inside the first 2 f (at 30 fps; the author's 60 fps table is halved), no overshoot on text.
- Words swap in place (`wordsSwap`), they do not re-appear elsewhere; numbers swap as a whole (see tables file).
- Per-letter random flicker: seeded per letter, baked with `tl.set` at each frame from a hash of (letter index, frame); keep flicker below 3 flashes per second over a large area (WCAG); glow only during the flicker, settling to clean text.
- Hero type <= 7 words per card, 60-80 % of the width for hero text, headlines 64-120 px (body 28-42, labels 18-24, anything under 24 px needs a reason; in-feed: body >= 32, headlines >= 90, data labels >= 24); tracking -0.03 to -0.05 em at display sizes; "3 s on screen must be readable in 2".

## 3. Fonts
- Baseline: Rubik (Hebrew + Latin, variable 300-900) for the author; Heebo the alternate; both OFL 1.1 (keep the licence notice with the binaries; never sell the font alone). Start with ONE bilingual family before adding a second Latin family; match actual cap-height, numeral width and optical weight in output frames (identical CSS px does not give identical perceived size).
- E03 means (1-5, one reviewer): Rubik 600, Alef 700, Noto Sans Hebrew 600 = 4.2; Heebo 600 = 4.0; Secular One 400 = 3.6; Assistant 600 = 3.2; Karantina 700 = 1.8 (unfit for continuous captions, not rejected for short large display titles). Display faces must pass a full-size test of ו/ז, ד/ר, ה/ח before approval.
- Adobe Fonts may appear in rendered video but their activated files must not be packaged for students; the working route is a web kit `<link>` (render needs network). Do not use SF Pro for client work.

## 4. Test fixtures (originals; run before approving type motion)
| String | Tests |
|---|---|
| `אותו לקוח. הזמנה גדולה יותר.` | word swap in place, punctuation |
| `₪102.60 — חיסכון של 12%` | currency placement, bidi, whole-number swap (no stray values in between) |
| `ACME (חדש) — מגיע ב־10:30` | Latin + parentheses + numerals + maqaf |
| `שָׁלוֹם` | niqqud survives a reveal |
| a mixed-direction 3-line wrap | line breaks, safe box |
Per fixture record: logical source, intended display order, font + version, rendered line widths, safe box, event hold; compare the displayed string to the source by eye with a Hebrew reader (OCR alone misses spacing and bidi punctuation). Check final letters ך ם ן ף ץ and the look-alike pairs. Prices: no unintended intermediate values during a whole-price transition.

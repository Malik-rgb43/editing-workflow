# Hebrew caption typography, look-alike letters, fonts

Load when: choosing or changing a caption font, sizing captions, running the look-alike test, checking font licences. Dated 2026-10-02; sources: distilled 06 hebrew-rtl-and-captions §1-§2 (E03, T08, owner notes); decision default Q5.

## 1. Precedence
1. The style the client already approved. 2. The signature in the video-type skill. 3. The default: Rubik (Black/900 for keywords, Regular/600 for small words). Rubik is a **default, not law**: the owner said "you do not have to use Rubik" (2026-09-28); another display face is allowed after the full-size look-alike test below. Platform-native fonts for UGC-style paid ads (TikTok, Stories) are an external recommendation, not an owner rule.

## 2. The look-alike failure and the test (law before locking a display font)
Karantina Bold at display size made ז almost identical to ו: the keyword "לבזבז" (to waste) read as "לבובו". The fix moved only that keyword to Noto Sans Hebrew Condensed Black (wdth 62.5, wght 900), enlarged to 330 px because the Noto face rendered lower and the gap below grew. Test, for every keyword of the film:
1. Render it at its FINAL size on its FINAL background (not a font specimen).
2. Look at ו/ז, ד/ר, ה/ח, and the final forms ך ם ן ף ץ, at full size and at 360x640; a word that can be read as another word fails.
3. Record font file name and hash, size, weight, device scale, frame/time and the result in `hf/QA.md` (gate G6 evidence).
4. A model critic can nominate candidates; it is not a native-reader measurement. Final acceptance is a Hebrew reader.
Fixture strings (original): `ו ז - ורד זרע - זו וזו`; `ד ר - דרך רדיו - דירה רדודה`; `ה ח - הר חם - ההר והחדר`; niqqud `שָׁלוֹם, בְּרִיאוּת וְהַצְלָחָה`; final forms `ך ם ן ף ץ - מלך, עולם, זמן`; wrap pressure `התוכנה מאפשרת עריכה מקצועית בעברית ובאנגלית`.

## 3. E03: 12 Hebrew OFL fonts at phone scale (a single vision-capable model's static 1-5 ratings; no human panel, no physical phone, no animation, no recompressed social upload)
Setup: Chrome Headless Shell 152, fonts pinned to Google Fonts commit 9710da1e..., 12 specimens at 1080x1920 downscaled to 360x640 (sizes 66/54/42 px = 22/18/14 px effective), ratings recorded before the label key was opened (limited masking, not a blinded trial).
| Font (weight tested) | Plain 18 px | Small 14 px | Busy bg | Pairs ו/ז ד/ר ה/ח | Niqqud | Mean |
|---|---:|---:|---:|---:|---:|---:|
| Rubik 600 | 5 | 4 | 4 | 4 | 4 | 4.2 |
| Alef 700 | 5 | 4 | 4 | 4 | 4 | 4.2 |
| Noto Sans Hebrew 600 | 5 | 4 | 4 | 4 | 4 | 4.2 |
| Arimo 600 | 4 | 4 | 4 | 4 | 4 | 4.0 |
| Heebo 600 | 4 | 4 | 4 | 4 | 4 | 4.0 |
| IBM Plex Sans Hebrew SemiBold | 4 | 4 | 4 | 4 | 4 | 4.0 |
| Secular One 400 | 4 | 3 | 4 | 4 | 3 | 3.6 |
| Varela Round 400 | 4 | 3 | 3 | 4 | 4 | 3.6 |
| Assistant 600 | 3 | 3 | 3 | 4 | 3 | 3.2 |
| Noto Serif Hebrew 600 | 3 | 2 | 3 | 4 | 3 | 3.0 |
| Frank Ruhl Libre 600 | 3 | 2 | 3 | 4 | 3 | 3.0 |
| Karantina 700 | 2 | 1 | 2 | 2 | 2 | 1.8 |
Caveats from the report: fonts were compared at "practical caption presets", not at equal stroke weight; equal pixel size favours condensed faces (compare equal visible letter height too); the "pairs" line was one row at 66 px; stroke widths were NOT tested; Karantina is not rejected for short, large display titles. Provisional default: Rubik 600 at 54-66 px with an opaque or controlled-contrast backing for dense material. Use larger sizes for small displays, fast speech and niqqud, then inspect wrapping.

## 4. Sizes and weights seen in the owner's work (1080x1920)
| Context | Value | Status |
|---|---|---|
| Talking-head premium (Rubik) | caption rail y 900-1240 on A-roll, never below 1450; keyword lockups tight on the glyph box; one keyword was enlarged to 330 px | proven in travel-agency speaker tests |
| Testimonial signature | 88 px, weight 900, glyph height 3-4.5 % of frame, white fill, `-webkit-text-stroke: 2.5px #000; text-shadow: 3px 4px 8px rgba(0,0,0,.65)`, top 68 % (paid Meta <= 58 %) | belongs to `edit-testimonial` |
| Ad signature | white heavy rounded sans, soft shadow, no box, chest height 37-66 % | belongs to `edit-ad-promo` |
Rules: height 37-73 % by type; 1-3 words; keyword colour = the film's ONE keyword colour (alert colour only for the problem word, never pink); small words sit close to the keyword (gap 40-70 px, tight on the glyph box, `data-layout-allow-overlap` per word span because a display font's line box can exceed its glyphs); digits not number words ("200 אלף ש״ח"); animate words not letters.

## 5. Fit and measurement
Await `document.fonts.load()` before measuring or the keyword is sized from the fallback font. Measure with `Range.getBoundingClientRect()`, not the element box (it made keywords tiny). Layout JS that measures a clip which is not active returns 0: prefer layouts that need no measurement. A keyword width of >= 800 px is a static check the owner asked for.

## 6. Font files and licences
Copy the font file into `hf/fonts/` and declare `@font-face` with a relative `src`; a variable font is one file declared with `font-weight: 100 900` (Rubik[wght].ttf). A named installed font silently falls back in the HyperFrames browser (checked 2026-09-27); verify in a snapshot (a serif/monospace look = fallback). All 12 E03 fonts are SIL OFL 1.1 (Google Fonts commit above, declared in METADATA.pb; no binaries were downloaded by the research): bundling is allowed under the OFL conditions (keep notices, reserved font names such as Alef, IBM Plex, Varela, "Source"); that does not mean "strip notices and rename". Adobe Fonts: the web-kit route renders in HyperFrames and needs the network at render; Adobe font files must not be shipped in a course package. Local personal-use brand fonts and SF Pro are not for client work. Student repo packaging advice: ship OFL fonts with notices and fixture strings; keep media and model weights outside Git.

## 7. Contrast of brand-colour keywords (>= 4.5:1; WCAG 4.5:1 ordinary / 3:1 large text is a reference, not a complete video readability standard)
Sample a representative frame of every shot with an emphasis over the caption strip (50-62 % of frame height) and compute `scripts/caption_lint.py contrast <bg_r,g,b> <#fg>` (or the PIL snippet in `caption-timing.md`). The strip MEAN can hide a bright patch under a glyph: for risky shots sample local patches across the caption lifetime and inspect phone-scale frames. Measured failures and fixes: a dark brand colour at 1.3:1 -> accent from the logo, then a lighter tint of the same hue, then a brand-colour box behind a white word; yellow on a light ceiling 1.63:1 -> a warm dark top gradient (0.78 -> 0 down to 56 %) riding with the camera so yellow and white both pass 3:1 (text-shadow is not counted and did not help); white on a light wall 2.5:1 -> charcoal lettering in perspective. Record the choice and the number in `hf/SCRIPT.md`.

## Sources
distilled 06 hebrew-rtl-and-captions §1.1-§1.5, §2.1-§2.4; E03 REPORT (via that file); T08 FONT_CANDIDATES; checked 2026-10-02.

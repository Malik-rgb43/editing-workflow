# RTL and bidi: Hebrew with English, numbers and currency

Load when: a caption line mixes Hebrew with Latin text, digits, ₪, URLs or brackets; before touching `dir` or `direction` anywhere; when a HyperFrames render is black; when After Effects reorders numbers. Dated 2026-10-02; sources: distilled 06 hebrew-rtl-and-captions §4, distilled 04 hyperframes-traps §1.1, §4 (T08 RTL_TRAPS, E01, E12).

## 1. Fundamentals (verified against Unicode UAX #9 rev 52 and W3C i18n articles, 2026-10-01)
- Text is stored in LOGICAL order; never reverse a string by hand. A renderer that shows it wrongly gets a renderer-specific repair plus a regression fixture, not a reversed literal. Use original UTF-8 fixtures, not screenshots, as ground truth; save code points when investigating (a preview cannot show whether a literal contains LRM, RLM, LRI or an override).
- Isolate every complete opposite-direction phrase: Hebrew direction on the caption block, a tight wrapper with its own direction around each English phrase, URL, phone number, price or version. `<bdi dir="ltr">` or `unicode-bidi: isolate`; unknown inserted strings need `<bdi>` or `dir="auto"`; a number-leading Hebrew line needs explicit known Hebrew direction. A blanket `bidi-override` damages English and numbers.
```html
<p class="caption" lang="he" dir="rtl">המבצע על <bdi dir="ltr" lang="en">AI Pro 2</bdi>: <bdi dir="ltr">₪1,299.90</bdi> עד <bdi dir="ltr">18:30</bdi>.</p>
```
```css
.caption { direction: rtl; text-align: center; }
.caption bdi { unicode-bidi: isolate; white-space: nowrap; }
```
(Original proposed fixture; E03 rendered the equivalent `מחיר <bdi dir="ltr">₪129</bdi> • <bdi dir="ltr">20%</bdi> הנחה` and `גרסה <bdi dir="ltr">2.5</bdi> — <bdi dir="ltr">AI</bdi> בעברית`.) Currency placement (₪ before or after the number) is a copy decision for the Hebrew editor: isolation preserves the phrase but does not decide it.
- Controls: LRI U+2066, RLI U+2067, FSI U+2068 closed by PDI U+2069 are the recommended isolates; LRM U+200E and RLM U+200F are marks, not whole-phrase isolation. Flag unbalanced controls and the override characters U+202D/U+202E in imported captions; keep source text clean and serialise controls only inside the adapter of a renderer that needs them. `scripts/caption_lint.py` flags them.
- Canvas keeps its own state: set `ctx.direction = "rtl"` explicitly, set font and alignment before measuring, draw an intact shaped line rather than single code points at hand-computed x.
- Layout and animation: DOM order stays logical; animate by transcript word index; avoid double reversal (RTL layout plus a reversed array or `row-reverse`); wait for the real font before measuring line breaks; freeze dimensions for export. Wipes, scans, whips and per-word reveals run right to left; per-letter builds animate in reading order.
- Niqqud attaches to a base letter (a grapheme cluster): splitting by code unit or `split("")` breaks it. Animate WORDS, not letters (owner rule); segment grapheme clusters (UAX #29) if letters are ever animated. Do not strip niqqud from approved visible copy; for ASR scoring keep a raw and a declared-normalisation track.

## 2. HyperFrames specifics
| Item | Rule | Status |
|---|---|---|
| `<html dir="rtl">` | renders black or blank although preview and snapshot look right (lint `html_dir_attribute_breaks_render`); fix: `lang="he"` on `<html>`, `direction: rtl` / `dir` only on elements that contain text; `hf_preflight` errors on a root `dir="rtl"` | owner-observed on CLI 0.8.79-0.8.93, issue #1934 cited; E12 on 0.8.98 did NOT reproduce a black render (frames matched the LTR control) [CONFLICT]; W3C recommends root `dir=rtl` for RTL documents. Keep the local workaround, label it engine/version-specific, re-test both fixtures (snapshot AND render) per version |
| Fonts | `@font-face` from `hf/fonts/`; deterministic font-faces beat later stylesheets; pin the font explicitly; HyperFrames bundles 18 families and NONE has Hebrew | owner-measured silent fallback vs vendor docs that say fonts are embedded at build time [CONFLICT]: the deterministic rule is a shipped file |
| Non-Latin paths | `npx hyperframes init` silently skips `index.html` under a Hebrew path (local finding, CLI 0.8.79); `lint`, `check`, `render` work there | use `new_project` (ASCII scaffold then move) |
| 1080 width | the encoder blackens the last 8 columns (x 1072-1079) at width 1080 on the reference machine; in RTL the right edge is where each line starts, so first letters can be clipped; fix: 1088 canvas + `data-deliver-width="1080"` | not re-tested on 0.8.98; `render-qa-delivery` owns the per-version re-verification |
| `check` text_occluded | a transparent full-frame cutout makes `check` report occluded text: `data-layout-allow-occlusion` on every text element incl. nested spans | proven |
| HyperFrames transcribe | default `small.en`; parakeet does not cover Hebrew | use the ivrit-ai route; import `words.json` or SRT |

## 4. Fixture corpus (original strings, no client material)
Mixed content `עורך AI ב־Premiere Pro, גרסה 24.6`; numbers `40 000 ; 40,000 ; 40 000 (NBSP) ; 40 50 ; −12.5%`; currency/time `₪1,299.90 עד 18:30 — 01/10/2026`; brackets/URL `פתחו (AI Pro 2) ב־example.com/a?x=2`. Check punctuation (period and question mark on the correct side), numbers and ₪ on the final frame.

## 5. Hebrew in generated media, TTS and UI mockups
Generated Hebrew text inside AI images or video has residual precise-text limits (vendor-acknowledged, rate not quantified): produce a clean plate and typeset Hebrew in the typography layer; if text must be in-scene, compare every glyph with the approved string and inspect video frames for temporal drift; OCR is a screening aid, a Hebrew reader accepts. TTS: Hebrew-capable routes exist (availability only; no listening test was run); back-transcribe TTS and diff against the script; check heteronyms and brand names phonetically before the mix.

## Sources
distilled 06 hebrew-rtl-and-captions §4.1-§4.4, §6; distilled 04 hyperframes-traps; E01/E12 via distilled 03; UAX #9, W3C, MDN as read by T08 on 2026-10-01; checked 2026-10-02.

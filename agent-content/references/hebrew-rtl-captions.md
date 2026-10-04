---
module: hebrew-rtl-captions
checked_at: 2026-10-02
expires: "180 days (2027-03-31); re-test the engine rows on every HyperFrames version change"
confidence: "typography numbers [MEASURED-lab] on one model reviewer's static-image review (no human panel, no physical phone); owner rules [RULE-owner]; Unicode/HTML rules [VERIFIED-external]"
refresh: "re-run the font look-alike test and the fixture strings on the pinned build; check font licence headers at the pinned google/fonts commit; all local and free"
---

# Hebrew, RTL and captions — dated reference

| Field | Value |
|---|---|
| Fact set | caption typography (fonts, sizes, weights), line breaking, bidi isolation, niqqud, numbers, timing, mandatory exit animation, caption modes per video type, RTL traps per tool |
| Versions / ids | Google Fonts commit `9710da1eacb3be272583c3224dcb70f9da6eadbb` (E03 pin, observed 2026-09-30); Chrome Headless Shell 152.0.7977.30; Unicode UAX #9 rev 52 (2026-09-01); HyperFrames 0.8.98 |
| `checked_at` | **2026-10-02** (= research date; **must be refreshed before use**) |
| Source | `distilled/06-…/hebrew-rtl-and-captions.md` (T08 + E03 + owner caption playbook, anonymised); `distilled/04-…/hyperframes-traps.md` §4 |
| Scope / plan / region | Hebrew captions on 1080×1920 social video; OFL fonts only; Israeli audience |
| Confidence | see each row's tag; **Rubik is a default, not a law** |
| `expires` | see front matter |
| Non-spending refresh | render the fixture strings (section 6) with the candidate font at final size on a real background; read the OFL header of each font file; no network needed beyond the pinned font download |

## 1. Core rules (digest)
1. Hebrew is stored in **logical Unicode order** and is never reversed by hand. A renderer that shows it wrongly gets a renderer-specific repair plus a regression test, not a reversed string. `[VERIFIED-external]`
2. In HyperFrames: **no `dir="rtl"` on `<html>` or the root**; `lang="he"` on `<html>`, `direction:rtl` on text elements (see `hyperframes-traps.md` §0: `[CONFLICT]` with E12 on 0.8.98 — keep the rule, re-test per version). `[RULE-owner]`
3. Wrap every English/number/currency/URL phrase inside a Hebrew line in its **own isolate** (`<bdi dir="ltr">` or `unicode-bidi: isolate`). `[VERIFIED-external]`
4. **Font precedence:** (1) the style the client already approved, (2) the signature in the video-type skill, (3) the default. Default today: **Rubik** (Black/900 for keywords, Regular/400-600 for small words) — a default; another display face only after a full-size test of ו/ז, ד/ר, ה/ח. `[RULE-owner]`
5. Fonts load from a local `@font-face` file in `hf/fonts/` (the engine's Chrome falls back silently otherwise); `await document.fonts.load()` before measuring any layout. `[PROVEN-internal]`
6. Captions animate **out** as well as in. Never a hard vanish, never a blank frame at a chunk swap. `[RULE-owner]`
7. Never run an LLM across a whole transcript to "fix" it; fix specific words by hand with a per-project spelling dictionary; **zero spelling errors** is the delivery bar. `[PROVEN-internal]` `[RULE-owner]`
8. Animate **words, not letters** (letters break niqqud and reading order). Keep DOM order logical; animate by transcript word index. `[RULE-owner]` + `[VERIFIED-external]`
9. Brand-colour keywords need ≥ **4.5:1** contrast against the footage under the caption band. `[PROVEN-internal]` + WCAG 2.2 (4.5:1 ordinary text, 3:1 large) `[VERIFIED-external]`; the mean-strip check is only a screening heuristic (a bright patch under one glyph hides in a mean).
10. Generated Hebrew text inside AI images/video is **not** trusted: generate a clean plate and typeset deterministically; if text must be in-scene compare every glyph with the approved string and inspect video frames for drift; OCR is a screening aid, a Hebrew reader accepts. `[VERIFIED-external]` limit statement + `[IDEA]` default.

## 2. Fonts — E03 result (12 OFL Hebrew fonts, phone scale) `[MEASURED-lab]`
Setup: 12 specimens at 1080×1920, sizes 66/54/42 px, line-height 1.45, `font-synthesis: none`, downscaled to 360×640 (so 22/18/14 px effective); 12/12 faces loaded, 0 fallback nodes of 60 sampled. Scores are **one vision-capable model's** subjective 1-5 ratings (1 hard, 3 usable with care, 5 especially clear), recorded before the label key was opened — **not a human panel, no physical phone, no animation, no recompressed upload, no stroke test**.

| Font | Weight tested | Mean | Note |
|---|---:|---:|---|
| Rubik | 600 | 4.2 | clean counters, small text readable (owner baseline) |
| Alef | 700 | 4.2 | strong and clean |
| Noto Sans Hebrew | 600 | 4.2 | clean letterforms |
| Arimo | 600 | 4.0 | open regular shapes |
| Heebo | 600 | 4.0 | balanced strokes |
| IBM Plex Sans Hebrew | 600 (SemiBold file) | 4.0 | clear shapes and punctuation |
| Secular One | 400 | 3.6 | heavy compact strokes; small marks need care |
| Varela Round | 400 | 3.6 | thin strokes weak on busy background |
| Assistant | 600 | 3.2 | narrower apparent text |
| Noto Serif Hebrew | 600 | 3.0 | thin strokes lose clarity at 14 px |
| Frank Ruhl Libre | 600 | 3.0 | serif detail dense |
| Karantina | 700 | 1.8 | condensed shapes make pairs and marks hard; not rejected for short large display titles |

**E03 provisional default:** Rubik 600 at **54-66 px** on a 1080×1920 canvas (18-22 px at 360 px display width), with an opaque or controlled-contrast backing for dense material; Alef 700 and Noto Sans Hebrew 600 are equal-scoring alternatives. Compare fonts also at equal visible letter height (equal pixel size favours condensed faces). Use larger sizes for small displays, fast speech and niqqud, then inspect actual wrapping. All 12 declare OFL 1.1 and a Hebrew subset (headers read at the pinned commit; no binaries downloaded by the research); keep reserved names (Alef, IBM Plex, Varela, "Source" inherited in Assistant) and each family's own licence file. `[VERIFIED-external]` for licence declarations.

**Look-alike failure (production):** Karantina Bold at display size made ז almost identical to ו — "לבזבז" read "לבובו". Fix used: Noto Sans Hebrew Condensed Black (wdth 62.5, wght 900) for that keyword only, enlarged to 330 px because it rendered lower. E03 independently scored Karantina lowest. `[PROVEN-internal]` + `[MEASURED-lab]`

**Look-alike test in a project** `[RULE-owner]` + `[IDEA]` measurement upgrade: (1) render each keyword of the film at its FINAL size on the final background (not a specimen); (2) read ו/ז, ד/ר, ה/ח at full size and at 360×640; any word readable as another word fails; (3) record font file name + hash, size, weight, device scale, frame/time, result in `QA.md`; (4) a VLM critique can nominate candidates but is not a native-Hebrew legibility measurement — final acceptance is a Hebrew reader.

Licence limits: Adobe Fonts allow finished video but font files must not be shipped or transferred (web-kit link only; the render needs network; cached livetype files are encrypted — do not copy); SF Pro is Apple-licensed (UI mock-ups only); a brand display font licensed for personal use only cannot be used for client work. OFL look-alikes exist for commercial display faces. See `licences-bom-rules.md`.

## 3. Sizes, position, fit (1080×1920) — house values `[PROVEN-internal]` from the author's own deliveries
| Item | Value | Status |
|---|---|---|
| word-pop cue | 1-3 words, 0.35-0.7 s per caption, one line | `[PROVEN-internal]` |
| sentence mode (only when asked) | 1-6 words, ≤ 42 characters per line, ≤ 2 lines, ≤ 17 characters/s, min 5/6 s (0.833 s), 2-frame gap | `[PROVEN-internal]`; the Netflix/BBC numbers come from a tool in another project, not re-verified |
| talking-head position | caption y 900-1240 on A-roll; **bottom edge never below y = 1450**; key text ≤ y 1248 | `[PROVEN-internal]`; house safe zones v1 (see `platform-specs.md`) |
| testimonial signature | weight 900, ~88 px, stroke `-webkit-text-stroke: 2.5px #000`, shadow `3px 4px 8px rgba(0,0,0,.65)`, white fill; vertical 63-73% of height (paid Meta 9:16 ≤ 58%) | `[PROVEN-internal]` one video type |
| keyword lockup | small words sit tight to the big word; measure keyword boxes with `Range.getBoundingClientRect()` after `document.fonts.load()`; per-word `data-layout-allow-overlap` | `[PROVEN-internal]` |
| numbers | **digits, not words** ("200 אלף ש״ח", "40K"); all digits of a price change together (stagger 0) | `[RULE-owner]` |
| caption vs face | never on the mouth; end the caption with the B-roll; per-frame face-box vs caption-box overlap check | `[PROVEN-internal]` |
| overlay cards on a speaker | light card (#F2F1F3 at .95, ink text), ≤ 860 px wide, under the chin, never across the face | `[PROVEN-internal]` |
| motion/launch films | **no captions by default** (backdrop-filter pills also halved capture speed) | `[RULE-owner]` |

Stroke/shadow widths were **not** tested in E03; a shadow alone inherits the background's contrast variation.

## 4. Timing, entrance and exit (the animation contract)
| Rule | Value | Why / status |
|---|---|---|
| exit | default = entry mirrored: **blur-out-up** (rise 10 px + blur 6 px + fade over the last ~4 frames); another deliberate exit is fine | owner decision 2026-09-28; the later decision overrides an earlier "hard swap" prompt `[RULE-owner]` |
| no blank frame at a swap | exit tween on an inner wrapper; the chunk's on/off stays the only show/hide (seek-safe); **next chunk's first word starts 2 frames early** (~70% at the swap frame) | every-frame check found a blank frame at each swap `[PROVEN-internal]` |
| card-to-card | outgoing exit overlaps the next entry by 1-2 frames; never two cards stacked | `[PROVEN-internal]` |
| minimum dwell | word ≥ **0.25 s**, card ≥ **0.9 s**, last word ≥ 0.25 s | fast speech otherwise showed the last word 0.1 s `[PROVEN-internal]` |
| lead the voice | captions lead speech by **0.08-0.1 s**; clamp `max(0, …)` (a 0.08 lead on the first caption created a negative start) | `[PROVEN-internal]` |
| last word pop | clamp the entrance to finish before the exit | `[PROVEN-internal]` |
| easing | `cubic-bezier(0.22,1,0.36,1)` family; blur-out-up for words | `[PROVEN-internal]` |
| backdrop-filter | `visibility:hidden` outside each element's window; never alive the whole film | 4.3 fps vs ~19 `[PROVEN-internal]` |

Timing source: ivrit-ai ASR with word timestamps (see `asr-routes.md`); native Whisper median drift ~90 ms (73 ms after a global monotone snap) in the author's history — **not reproduced by the research**; if drift is audible, shift by a constant offset. Proofreading: read the transcript, fix names/brands/terms by hand, run several passes and a majority vote for contested words, then do not flip-flop. Three real spelling errors were found in the author's earlier ads (use them as a QA-checklist reminder, not as a statistic). `[PROVEN-internal]`

## 5. Caption mode per video type
| Type | Mode / style | Position | Colour |
|---|---|---|---|
| testimonial | word-pop 1-3 words, white heavy Hebrew sans + outline + shadow; digits | centre 63-73% (paid Meta ≤ 58%) | none in own work; market upgrade: one keyword per cue in brand colour at ≥ 4.5:1 |
| ad / promo | white heavy rounded sans, soft shadow, no box; swap every 0.35-0.7 s | chest height 37-66% | brand-colour keyword + pop; never over a logo |
| talking-head premium | chunked word-group cards, Rubik Regular + Black keyword, mirrored exit | y 900-1240, bottom ≤ 1450 | the film's ONE keyword colour (never pink; alert colour only for the problem word) |
| motion graphics / launch | **none** unless the brief mentions sound-off | — | — |
| podcast clip | 1-3 words, colour per speaker, captions on the seam of a split layout | 60-70% | per speaker |
| reels in general | plan for sound-on **and** sound-off (sources conflict: ~70% with sound reported vs heavy muted viewing) `[CONFLICT]` | — | — |
Owner open question: keep the colourless sharp-swap testimonial signature, or add keyword colour + animated exit? The skill applies the animated exit. `[CONFLICT]`

## 6. RTL fundamentals and fixtures
Isolate complete opposite-direction phrases: Hebrew direction on the caption block + a tight wrapper with its own direction around each English/URL/phone/price phrase; unknown inserted strings need `<bdi>` or `dir="auto"`; a number-leading Hebrew line needs explicit Hebrew direction. Controls: LRI U+2066 / RLI U+2067 / FSI U+2068 closed by PDI U+2069 (isolates); LRM U+200E / RLM U+200F are marks, not whole-phrase isolation; flag unbalanced controls and U+202D/U+202E in imported captions; keep source text clean and serialise controls only in a renderer adapter. A blanket `bidi-override` can damage English/numbers. Canvas: set `ctx.direction = "rtl"` explicitly. `[VERIFIED-external]` (UAX #9; CSS Writing Modes). Original proposed fixture `[IDEA]`:
```html
<p class="caption" lang="he" dir="rtl">המבצע על <bdi dir="ltr" lang="en">AI Pro 2</bdi>: <bdi dir="ltr">₪1,299.90</bdi> עד <bdi dir="ltr">18:30</bdi>.</p>
```
```css
.caption { direction: rtl; text-align: center; }
.caption bdi { unicode-bidi: isolate; white-space: nowrap; }
```
Currency placement (₪ before or after the number) is a copy decision made with the Hebrew editor; isolation preserves a phrase, it does not decide order.

**Acceptance fixture strings** (original, no client material) `[IDEA]`: `ו ז — ורד זרע — זו וזו` · `ד ר — דרך רדיו — דירה רדודה` · `ה ח — הר חם — ההר והחדר` · `שָׁלוֹם, בְּרִיאוּת וְהַצְלָחָה` (niqqud) · `עורך AI ב־Premiere Pro, גרסה 24.6` · `40 000 ; 40,000 ; 40 000 (NBSP) ; 40 50 ; −12.5%` · `₪1,299.90 עד 18:30 — 01/10/2026` · `פתחו (AI Pro 2) ב־example.com/a?x=2` · `ך ם ן ף ץ — מלך, עולם, זמן` · `התוכנה מאפשרת עריכה מקצועית בעברית ובאנגלית` (wrap pressure). E03 rendered, among others, `גרסה <bdi dir="ltr">2.5</bdi> — <bdi dir="ltr">AI</bdi> בעברית` and `כל פריים נבדק`. A Hebrew headline with Latin "AI" and "12" rendered in correct order in both engines with Rubik from a local file `[MEASURED-lab]` (E01).

Niqqud attaches to a base letter (a grapheme cluster): never split by code unit or `split("")`; segment by grapheme clusters if characters are ever animated; do not silently strip niqqud from approved copy. `[VERIFIED-external]`

## 7. Tool-specific RTL traps
| Tool | Finding | Status |
|---|---|---|
| HyperFrames | root `dir=rtl`: see rule 2; 1080-wide encoder band blackens the right 8 columns (in RTL the right edge is where each line starts — first letters can clip): 1088 canvas + crop | `[PROVEN-internal]` |
| `check` text_occluded | transparent full-frame cutout → `data-layout-allow-occlusion` on **every** text element incl. nested spans | `[PROVEN-internal]` |
| TikTok Hebrew audience | RTL template is for Arabic-region only per TikTok docs; keep 140 px on both sides | `[CONFLICT]` resolved conservatively |

## 8. Caption QA (student tool names)
`hf_preflight` (static: Studio ids, root RTL, stale grids, duplicate ids, media in 3D, caption below y 1450 warning — can be bypassed by alternative caption representations) · `caption_qa --band <top>:1450` (frames where caption text vanishes in ONE frame; the author's version assumes 1080×1920 and 30 fps, only detects disappearance, can be fooled by coloured/dark text — **run it only with the format check**) · `frame_qa` (every frame: black < luma 6, single-frame pops, flashes, static holds > 1.0 s, hard cuts) · 4-axis visual review on contact sheets (the critic passed drafts the author rejected: a human gate stays) · `hyperframes snapshot --at … --describe false` (proves the font loaded; fallback = serif/monospace look; does not sync video around cuts). A gate that cannot run reports `not_run`, never PASS.

## 9. Conflicts and open items
`[CONFLICT]` root RTL (E12) · TikTok RTL template · reels sound-on/off · testimonial exit. Open: human-reader legibility study, a physical-phone check, stroke widths, animated and recompressed output, Hebrew TTS listening (availability lists only), E03's single-model scoring. TTS routes (Azure he-IL-Hila/Avri, Google he-IL Chirp 3 HD, Eleven v3/v4 list Hebrew; Multilingual v2 and Flash v2.5 do not; OpenAI TTS lists Hebrew but is English-optimised) are `[VERIFIED-external]` availability only — **never listened to**; require native listening review and consent/provenance.

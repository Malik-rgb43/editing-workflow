# Rubric: ad-promo (paid-social ads and promos; also UGC-unboxing and product-demo until they get their own)

> Status: the author's `ad-promo.rubric.md` (criteria A1–A8, gates A1, A2, A6) **mapped into the six dimensions** of QA_AND_BENCHMARKS §6. Specified; model eval not run (decision default Q4); not calibrated against human raters. Written 2026-10-02 from distilled/02 qa §6.2 and video-types §3.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[SOURCED-unverified]` · `[PERISHABLE]` · `house preset`.
> Companion files: [critic-brief.md](critic-brief.md) · [visual-review-4-axis.md](visual-review-4-axis.md) · [bands.json](bands.json) · [briefs/B02.md](briefs/B02.md).

## 1. How to score

Score only what was seen/heard on stated evidence; `not_observed` ≠ 3; `N/A` needs a reason; 1–5 with anchors at 1/3/5; **severe failures listed separately and blocking** (a misspelled brand/address/price, a claim not approved in writing, a music-licence violation). **Release rule `[RULE-owner]`:** average ≥ 4.0, no dimension < 3, hard gates A1 / A2 / A6 ≥ 3 (**a gate at ≤ 2 blocks presentation even when the average passes**), no severe failure; automatic QA all `PASS` with coverage; max 3 critic rounds. **Mute test:** watch once without sound — offer, brand and CTA must be understood from the screen alone.

## 2. Dimensions (1 / 3 / 5)

| Dimension | 1 — material failure | 3 — usable with repair | 5 — strong |
|---|---|---|---|
| **Meaning / story** | no offer and no CTA (a logo only); a preamble or story opening ("three years ago…"); lengths ignore the brief (45–53 s with no cut-down) | the offer is a plain caption without a badge, or arrives only after the hook; one hook only; a card without WhatsApp/number | hook (0–2 s) = the offer, a before/after or a visual shock at frame 0, moving within 1 s, ≤ 6 words readable without sound; **an offer with a number (currency, %, "free", deadline) in the hook and repeated ×3** (voice, caption/super, end card), the price alone ≥ 2 s then its condition; CTA spoken **and** written, on screen ≥ 6 s; the lengths the brief asked, exactly (default 15 and 30 s), 3 hooks on one body; end card 2–3 s with music to the end |
| **Caption / language** | spelling error in the brand/address/name; broken RTL; the caption on a logo, sign or face | signature captions without emphasis; inconsistent emphasis | the author's word-pop signature (white heavy rounded Hebrew sans, chest height 37–66 %, 1–3 words, 0.35–0.7 s) with a brand-colour keyword on every cue with a number/offer/place at ≥ 4.5:1, an 80–120 ms pop; one font, ≤ 3 styles; everything inside the platform safe zones **including the logo bug**; **zero** spelling errors (proofread against the client's written spelling) |
| **Composition / brand** | the brand revealed only at the end; the product/price cropped or covered; outside the safe zone | the brand appears only at 1–3 s or only physically unreadable; logo bug missing | the brand identified within **1 s inside the world** (on the product, wall, shirt or a fixed bug), the product/service on screen within 3 s; logo bug top-right inside the safe area; one brand colour in ≈ 50 % of shots; the price in a **separate brand-colour tag**, never caption style |
| **Motion / edit** | a static speaker for most of the ad; segments ≥ 4 s without change | a change every 2–3 s (≈ 16.9 cuts/min); one 2–3 s segment with no change | a visual change at most every **1.4 s** (market ≈ 36 cuts/min, median shot ≈ 1.0–1.6 s — `bands.json`); a hidden whip/crash cut at least once per 15 s; cuts on speech in speaker formats and on transients in a montage; only the punchline or the end holds ≥ 3.5 s; an end card of 2–3 s, no 5 s of silence |
| **Audio** | a commercial song, a film/anime clip, `License: unknown`, or true peak above 0 dBTP (observed +3.2/+3.3 in owner ads) — **disqualifying** | legal and clean but no SFX (7 of 10 owner ads); true peak between −1 and 0 or a level off by ≥ 3 LU | music licensed for **advertising** (the file's own `SOURCE.md` row — never inferred from a file name); −14 ± 1 LUFS (house gate ±0.5), TP ≤ −1 on the final file; an audible bed that rises alone on the card; SFX only on graphic entrances, transitions, the price/offer reveal and the logo (plain caption pops silent); **one loudness peak, on the logo/CTA** |
| **Integrity / continuity** | an unproven or invented claim, a price/discount different from the written one, a before/after that is AI-"improved", a fake review, an unlicensed face/likeness | claims are the client's but proof not requested; stock instead of the product | claims only as supplied in writing; the same real object in before/after from the same angle (double brightness contrast, cold→warm grade); product in hands in ≥ 35 % of shots or real UI rebuilt in code; every claim, price and review verified with the client; AI shots only as disclosed mood B-roll (a mostly-AI ad also loads the ai-generated rubric) |

## 3. Hard gates

| Gate (owner id) | Predicate | Blocks at |
|---|---|---|
| **A1 offer and CTA** | an offer with a number in the hook, ×3, CTA spoken + written ≥ 6 s (5); a vague offer ("a significant discount") or verbal-only CTA (2); no offer, no CTA (1). A claim, price, before/after or review not verified with the client lowers A1/A5 to **1 until verified** | ≤ 2 |
| **A2 brand in 1 s** | brand ≤ 1 s inside the world and product ≤ 3 s (5); brand only mid-video (2); only at the end (1) | ≤ 2 |
| **A6 legal sound and level** | licensed for ads, −14 ± 1 LUFS, TP ≤ −1 (5); legal, clean, no SFX (3); TP between −1 and 0 or a level off by ≥ 3 LU (2); commercial song/protected clip/`unknown` licence/TP above 0 (1, **disqualifying**) | ≤ 2 |
| **AD-G4 delivery** | length ±1 frame, −14 ± 0.5 LUFS, TP ≤ −1, no black ≥ 2 frames, no dead edge band | on failure |

Licence reality `[CONFLICT]`: the author's shortcut "`unknown` = organic only" has no verified rights basis; until the licence review resolves it, **ads use only files whose own source row proves an ad-compatible licence** (CC0, a free licence that allows ads, a paid subscription); anything else is blocked for paid use and the delivery message states the risk.

## 4. Mapping (owner criteria → six dimensions)

A1 offer/CTA → meaning/story (+ caption/language for on-screen offer) · A2 brand in 1 s → composition/brand · A3 hook → meaning/story · A4 pace and visual change → motion/edit · A5 proof and product → integrity/continuity (+ meaning/story) · A6 legal sound and level → audio · A7 typography, safe zones, proofreading → caption/language + composition/brand · A8 length and versions → meaning/story (brief fidelity) + the manifest check.

## 5. Safe zones and platform facts `[PERISHABLE]`

Safe-zone rows live in the dated delivery table (workflow-end-to-end §10.2, checked 2026-09 by the author; the Meta page could not be verified on 2026-10-01): one 9:16 master: key text top 300 · bottom y ≤ 1248 · left 140 · right 192; caption rail never below y 1450; a 9:16 Meta ad in the feed is cropped to 4:5, so the logo bug sits at top 300, not 270. These are **owner house policy**, not a verified universal platform specification — re-check the platform pages before a paid campaign. Compliance rules that block regardless of score: personal-attribute hooks ("are you suffering from…?") are forbidden by Meta (rephrase as a situation); "Meta restricts violent/graphic animal content"; a WhatsApp/button graphic must be information, not a fake clickable UI; weight-loss/body/cosmetic before/after is rejected by Meta. `[SOURCED-unverified]` (src: distilled/02 video-types §3.9)

## 6. Numeric reference (informational)

`bands.json` → `types.ad-promo`: market (10 refs, mostly 16:9): 29.0 s, 36.25 cuts/min, median shot 1.04 s, first cut 1.9 s, LUFS −15.95, TP −1.55, music 0.73; owner (9 × 9:16 + 1 × 1:1): 29.75 s, 34.5 cuts/min, median shot 1.59 s, LUFS −14.2, **true peak +0.15 (7 of 10 at or above 0 dBTP)**, 0 SFX/min median. The automatic cut count misses whips and light leaks (corrected counts: 108 vs 42 and 89 vs 56 cuts/min seen) — check against frames.

## 7. Critic notes

Zoom on the offer reveal, price tag and end card; check the safe zone with the overlay row; confirm every number is on screen ×3; confirm the licence rows exist; run the mute test; keep the author's signature (word-by-word captions, a speaker with B-roll, the Meta button chevron) and add the upgrade; every score under 4 gets a timecode and a concrete fix (e.g. "move '10 % for visitors' from 21.6 s to 0.0 s as a brand-colour badge with a pop and a coin SFX from an ad-licensed library, and add WhatsApp to the card").

(src: distilled/02 qa §6.2, video-types §3; QA_AND_BENCHMARKS §6 — read 2026-10-02.)

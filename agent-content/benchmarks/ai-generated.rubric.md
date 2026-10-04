# Rubric: ai-generated (videos built mainly from AI-generated shots)

> Status: the author's `ai-generated.rubric.md` (criteria G1–G8, gates G1, G3, G6) **mapped into the six dimensions** of QA_AND_BENCHMARKS §6. Specified; model eval not run (decision default Q4); not calibrated against human raters. Written 2026-10-02 from distilled/02 qa §6.2, video-types §6.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[SOURCED-unverified]` · `[PERISHABLE]` · `house preset`.
> Companion files: [critic-brief.md](critic-brief.md) · [visual-review-4-axis.md](visual-review-4-axis.md) · [bands.json](bands.json) · [briefs/B04.md](briefs/B04.md).
> **Scope note:** this rubric scores the *edit* of generated material. A paid ad made mostly of AI shots is scored by **both** this rubric and the ad-promo rubric (gates G1–G8 and A1–A8). Generation spend is governed by `paid-spend-gate`, not by this rubric.

## 1. How to score

Score only what was seen/heard on stated evidence; `not_observed` ≠ 3; `N/A` needs a reason; 1–5 with anchors at 1/3/5; **severe failures listed separately and blocking** (a visible anatomy/product/text error that contradicts the voice; an unlabelled realistic synthetic person where the platform or client requires a label; third-party IP or a lookalike in a paid ad). **Release rule `[RULE-owner]`:** average ≥ 4.0, no dimension < 3, hard gates **G1 / G3 / G6 ≥ 3** (a gate at ≤ 2 blocks), no severe failure, automatic QA all `PASS` with coverage, max 3 critic rounds. Critic discipline: frame by frame at every transformation (`frames --at <t> --pad 0.25`), searching for hands, bones, text and a product that changes — **any artifact visible at 1× speed drops G1**.

## 2. Dimensions (1 / 3 / 5)

| Dimension | 1 — material failure | 3 — usable with repair | 5 — strong |
|---|---|---|---|
| **Meaning / story** | the AI image arrives after 4 s (the author's median wow: 5.5 s); a script that demands continuity of hands/faces/text the model cannot hold | the AI arrives at 2–3 s after a real hook | the strongest AI shot at frame 0–1 s, moving by 0.5 s, with a text call-out (≤ 6 words); a format chosen and justified (X-ray explainer, list gag, interviews, parody, motion transfer, hybrid launch); each gag/stop is a **standalone shot**; the idea sidesteps model weaknesses (silhouettes, backs, masks, stylised or non-human leads) |
| **Caption / language** | spelling mistakes ("מתאבה", "לסבוב": two of five owner clips), no end card, text generated inside the model | clean captions, a minimal ending | Hebrew captions **proofread by a human**, 2–4 words, keyword in the accent at ≥ 4.5:1, correct RTL, bottom edge per the safe-zone table (9:16 key text y ≤ 1248); **text added in post, never inside the generation**; an end card every time (brand, CTA, address; a "Made with AI" line when needed) |
| **Composition / brand** | each shot looks like a different model; a visible gap between real, AI and sharp HTML layers | a similar grade but no grain | **one look for the whole film**: one grade + global grain 3–4 % + raised blacks across real, AI and HTML layers (or a declared look: B&W, 70s film); a shared LUT at 30–60 %; one STYLE PREFIX behind every prompt; end card consistent |
| **Motion / edit** | generations play in full (4–13 s), reversed to fill time or close a loop (the author did in 4 of 5), artifacts stay on screen; stepped cadence from 24p placed in a 30/60 timeline | median shot 3–5 s, some trimming; 12–20 cuts/min | every generation **trimmed to its clean window, median shot 1.2–2.5 s** (market 1.67 s); 22–30 cuts/min (short 9:16 up to 35), on sentence ends, SFX or drops — not a blind beat grid; a cover kit for seams (2–4 f whip, 1–2 f flash, 8–15 f black-blink + boom, overlays); timeline and delivery at the **native fps of the takes** (usually 24), never 24p in a 60 fps export |
| **Audio** | zero SFX (author's series: 0 of 5) or unbalanced loudness; model-generated audio left in by accident | a music bed plus a few SFX | an SFX on every transformation/transition (riser, whoosh, zap, sub-hit) with sounds under every cover; 100–175 ms of silence before the payoff and the drop on the reveal; breakdown ≈ −8 dB under dense VO; duck 10–12 dB under VO; **real VO beats TTS for trust**; −14 ± 0.5 LUFS, TP ≤ −1 (house preset); calm brand films: a uniform bed + diegetic foley instead |
| **Integrity / continuity** | melting anatomy, extra bones, a changing product, morphing faces, a picture that contradicts the VO; Hebrew on-camera speech faked without a lip-sync route | one minor artifact < 0.5 s on screen, covered by blur/whip/flash | **no visible artifact at 1× speed**: anatomy, hands, text and product correct in every frame; a medical/technical subject checked against a reference image (a ground truth passed as start/end frame); identical characters/products across shots (locked reference — a character sheet per shot, or a start frame per shot for start/end-only models); lighting consistent; sound sells the reality |

## 3. Hard gates

| Gate (owner id) | Predicate | Blocks at | Evidence |
|---|---|---|---|
| **G1 AI integrity** | per the Integrity row | ≤ 2 | frame strips at every transformation; a reference image for technical subjects |
| **G3 every generation trimmed to its best moment** | per the Motion/edit row (5: median shot 1.2–2.5 s; a long single take only if it *is* the idea and holds G1; 3: 3–5 s; 1: full generations, reverse loops) | ≤ 2 | `hf/TAKES.md` (in/out per take) + the shot-length list |
| **G6 one look for the whole film** | per the Composition row | ≤ 2 | before/after grade sheet; grain on every layer |
| **AI-G4 disclosure and rights** | realistic synthetic people/places → the platform's AI-content label planned and the person told to enable it; no celebrities/lookalikes/third-party IP in paid ads; consent for any real likeness | on failure | the disclosure plan row in the ledger (`AIDISC`); SOURCES.md |
| **AI-G5 spend discipline** | every billed generation was covered by an approved dated estimate and a retry cap | on failure | the gate's estimate file + provenance record (`paid-spend-gate`) |
| **AI-G6 delivery** | native fps preserved; length ±1 frame; −14 ± 0.5 LUFS, TP ≤ −1; no black ≥ 2 frames (one owner clip ended with 10.3 s of black) | on failure | `hf_deliver` verify block; `ffprobe` |

## 4. Mapping (owner criteria → six dimensions)

G1 AI integrity → integrity/continuity · G2 the wow in the first second → meaning/story · G3 trimmed to the best moment → motion/edit (+ integrity/continuity) · G4 pacing and edit logic → motion/edit · G5 designed for the AI's weaknesses → meaning/story + integrity/continuity · G6 one look → composition/brand · G7 sound design as glue → audio · G8 text and closing → caption/language + composition/brand.

## 5. Numeric reference (informational)

`bands.json` → `types.ai-generated`: market (11, 10 × 16:9, long form): median 81.35 s, 26 cuts/min, median shot 1.67 s, first cut 2.79 s, 29 events/min, LUFS −16.1, SFX 1.16/min, LRA 8.2; owner (9, 7 × 9:16): 27.8 s, 8.5 cuts/min, **median shot 12 s**, first cut 9.5 s, SFX 0/min, LRA 3.6. The market profile is long-form 16:9, so **length is information only**; the 9:16 social target is 22–35 cuts/min. Gaps seen in the author's series: reverse loops in 4 of 5, no grain/LUT in 9 of 9, no end card in 6 of 9. A stepped cadence that was not intended (repeating frames from a wrong export) is a scorer hard gate.

## 6. Critic notes

Never accept "looks fine at a glance" — the critic names the frames inspected. Keep the author's signature (a cyan/orange X-ray look, a real→AI match transition on the body, captions at ≈ 72 % height, a real-person VO) and add the upgrade (an X-ray in frame 0, clean-window trims, an SFX layer, global grain, anatomy QA against a reference, no reverse, an end card, −14 LUFS). Model behaviour is **perishable**: a model that refused or flagged real faces in a past test may behave differently now — the critic judges the result, not the model name. Every score under 4 gets a timecode and a fix (e.g. "12.0–13.5: the front view shows one meniscus while the VO says two; regenerate with a medical reference or cut it").

(src: distilled/02 qa §6.2, video-types §6 — read 2026-10-02.)

# Rubric: testimonial (customer reviews, student success stories)

> Status: the author's `testimonial.rubric.md` (criteria T1–T8, gates T1, T2, T5) **mapped into the six dimensions** of QA_AND_BENCHMARKS §6. Specified; model eval not run (decision default Q4); not calibrated against human raters. Written 2026-10-02 from distilled/02 qa §6.2 and video-types §4.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[SOURCED-unverified]` · `[IDEA]` · `house preset`.
> Companion files: [critic-brief.md](critic-brief.md) · [visual-review-4-axis.md](visual-review-4-axis.md) · [bands.json](bands.json) · [briefs/B05.md](briefs/B05.md).

## 1. How to score

Same rules as every rubric here: score only what was seen/heard on stated evidence; `not_observed` is not 3; `N/A` needs a reason; scale 1–5 with anchors at 1/3/5; **severe failures are listed separately and block release** (they cannot be averaged away). **Release rule `[RULE-owner]`:** average of scored dimensions ≥ 4.0, no dimension < 3, **every hard gate ≥ 3** (a gate at ≤ 2 blocks; T5 at 1 is disqualifying), no severe failure, automatic QA all `PASS` with coverage; max 3 critic rounds then present with the open gaps.

## 2. Dimensions (1 / 3 / 5)

| Dimension | 1 — material failure | 3 — usable with repair | 5 — strong |
|---|---|---|---|
| **Meaning / story** | the cut changes what the client meant; sentences stitched to say something new; a name-and-age or "hi what's up" opening with the proof 40–74 % into the film; no before→turn→after | message recoverable; a strong claim without a number; the strong soundbite appears but only mid-video; the pain is general | the first sentence is a number or an extreme moment in the client's own words with proof on screen within 2 s; the number soundbite is in the hook and returns at the result; the emotional soundbite **closes**, 3–4 s uncut on the face; before (quantified pain) → turn (mentor/product enters only after the problem) → tangible after; length on target (30–45 s social, 60–90 s long); CTA in the client's words + end card ≤ 3 s |
| **Caption / language** | wrong number or word, broken RTL/word order, no captions | template captions without emphasis; the whole story not understood muted | word-pop captions 1–3 words with a keyword in colour, digits not words ("200 אלף ש״ח"), entry **and exit** animation, hand-proofread names and quotes, a fixed result headline and callouts for numbers; the whole story understood on mute; inside the safe zone |
| **Composition / brand** | the proof covered or cropped; a lower-third over the face; logo/CTA outside the safe zone | proof shown but small; no lower-third (the viewer does not know who speaks) | split-screen proof (screenshot top ≈ 40 %, speaker below, caption on the seam) or an equivalent; a lower-third once at 1–4 s with name/role/result; end card ≤ 3 s with no trailing black; the client's approved style beats the skill signature |
| **Motion / edit** | static 16–56 s shots, or a punch-in/proof insert that hides the face at the key line | a visual change every 4–6 s; one weak segment | a visual change at most every **3 s** (market ≈ 19.7 cuts/min, 2.4–2.5 s median shot — `bands.json`); punch-ins alternate 100 % and 110–120 % on jump cuts with eye-line held; cuts on the word boundary covered (J/L cut, punch-in, proof insert); pauses cut at ≥ 0.40 s only inside a kept segment |
| **Audio** | speech masked, car/street noise left in, a clipped peak | intelligible, no bed or an uneven level (≈ −19 LUFS raw) | cleanup (noise reduction, ≈ 3:1 compression), a soft bed 12–18 dB under speech that swells in gaps, out for the crisis, back at the turn; at most one SFX per proof entry; master −14 ± 0.5 LUFS, TP ≤ −1 on the final file (house preset) |
| **Integrity / continuity** | **an AI-generated client, voice or result**; a screenshot paired with a different number; stitching that changes meaning; no consent | credible but one detail missing (role in the lower-third); over-polish that feels like an ad | a real client in their raw footage; **every spoken number shown on screen** and every proof screenshot matches the spoken number (otherwise the claim is a typographic quotation callout and the client is asked for a matching screenshot); original proof screenshots shown as is, animated *around*; signed ad-use consent exists; bystanders blurred; reorderings logged in `SCRIPT.md` with every statement still true in its new context |

## 3. Hard gates

| Gate (owner id) | Predicate | Blocks at | Evidence |
|---|---|---|---|
| **T1 hook opens on the result (0–3 s)** | first sentence = a number or extreme moment; proof on screen ≤ 2 s (5: ≤ 2 s; 3: strong claim, no number; 1: name/age or logo opening) | ≤ 2 | frame strip 0–4 s + transcript |
| **T2 proof density** | every number said appears on screen; speech-to-proof ≈ 1:1 in the result block; a visual change ≤ 3 s | ≤ 2 | numbers table: spoken number ↔ on-screen proof with timestamps |
| **T5 credibility and compliance** | real customer in raw footage; consent exists; cuts do not change meaning; no AI client/voice/result | ≤ 2; **1 = disqualifying** | consent record path; the `SCRIPT.md` move log; SOURCES.md |
| **TS-G4 delivery** | length ±1 frame, −14 ± 0.5 LUFS, TP ≤ −1, no black ≥ 2 frames, no dead edge band | on failure | `hf_deliver` verify block |

Honesty rules that apply to scoring (owner skill, `[RULE-owner]`): never animate or alter the screenshot itself (the count-up is a separate chip beside it); no client B-roll → ask first, stock only as neutral mood and never implying the client's life or results; paid-ad music/assets only if their own `SOURCE.md` row allows ads; sensitive proof (revenue, names) → `snapshot --describe false` and blur PII before any upload. The FTC's final rule on fake reviews (in force 21.10.2024) covers AI-generated testimonials `[SOURCED-unverified]`.

## 4. Mapping (owner criteria → six dimensions)

T1 hook → meaning/story · T2 proof density → integrity/continuity (+ meaning/story) · T3 soundbite choice and placement → meaning/story · T4 arc → meaning/story · T5 credibility → integrity/continuity · T6 readable without sound → caption/language · T7 length and dead time → motion/edit (+ meaning/story) · T8 CTA and ending → meaning/story + composition/brand. Owner T-anchors (5/3/1), for reference: T3 (5) number soundbite in the hook and the result, emotional soundbite closes 3–4 s with no cut on the face; (3) strong soundbite appears only mid-video; (1) missing, or the cut changes the meaning. T7 (5) target length, no long thank-yous or silence at the end; (1) no substantial shortening (225 s). T8 (5) the emotional soundbite then a CTA in the client's words + end card ≤ 3 s; (1) silence or black over 5 s, or ending mid-sentence. (src: distilled/02 qa §6.2)

## 5. Numeric reference (informational)

`bands.json` → `types.testimonial`: market (10, 9 × 16:9): 47.0 s, 19.7 cuts/min, 2.37 s median shot, −14.15 LUFS, music ratio 0.59; owner (10, 9:16): 54.55 s, 6.75 cuts/min, 4.85 s median shot, −18.6 LUFS, music 0.20 — the author's real testimonials were selfie UGC with no lower-third, end card, B-roll, punch-in, music or SFX; whether that slowness is intentional authenticity is an **open owner decision**. Keep the author's signature (fixed captions, split-screen proof) and add the upgrade.

## 6. Critic notes

Zoom on every proof moment; verify each spoken number against the screen; confirm the opening is not a name/age; check the consent record exists before scoring T5; cuts at a word boundary with no pause must be covered. Every score under 4 gets a timestamp and a concrete fix (e.g. "move 59.8–63.8 to 0:00 and add the screenshot with a count-up").

(src: distilled/02 qa §6.2, video-types §4; QA_AND_BENCHMARKS §6 — read 2026-10-02.)

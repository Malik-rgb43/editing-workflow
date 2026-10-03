# Rubric: talking-head (speaker-to-camera reel; also tutorial and vlog until they get their own)

> Status: **provisional, derived** — the owner never wrote a `talking-head.rubric.md` (the type has a skill, a benchmark JSON and four real test projects, but **no rubric file**). This rubric is built by this repo from the skill's premium bar (six points) and the owner's general rubric, mapped into the six dimensions of QA_AND_BENCHMARKS §6. Specified; model eval not run (decision default Q4); not calibrated against human raters. Written 2026-10-02. `[IDEA]` for the derivation; individual numbers carry their own tags.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[IDEA]` · `house preset` = an owner heuristic, not a perceptual or platform standard.
> OM (the reference machine) = one Windows laptop; hardware details are intentionally not published.
> Companion files: [critic-brief.md](critic-brief.md) · [visual-review-4-axis.md](visual-review-4-axis.md) · [bands.json](bands.json) (numeric bands) · [briefs/B01.md](briefs/B01.md).

## 1. How to score

- Score **only what was seen or heard** on the evidence supplied; the critic states the frames/ranges it inspected. A dimension with no evidence is `not_observed`, **not 3**. A dimension that does not apply is `N/A` with a reason. `not_observed` on a required dimension makes the verdict `INSUFFICIENT_EVIDENCE`, not PASS.
- Scale 1–5 with anchors at **1 / 3 / 5**; 2 and 4 are in between. Scores are given **against the brief and the declared style**, not against "reasonable" (owner: 5 = indistinguishable from the best reference of the type; 4 = very professional, small gap; 3 = reasonable, looks like a template; 2 = amateur; 1 = broken).
- **Severe failures are listed separately** and block release whatever the average (they cannot be averaged away): wrong or missing key word, number or negation on screen; speech meaning masked or distorted; a required product/text covered or cropped; a dropped subject at a join ("אז אני…" cut after "אני"); a visible identity error; a compliance gate violated.
- **Release rule `[RULE-owner]` (owner gate; thresholds await pilot calibration `[IDEA]`):** average of scored dimensions ≥ 4.0, **no dimension < 3**, every hard gate ≥ 3 (a gate at ≤ 2 blocks), no severe failure; automatic QA stage 6 all `PASS` with coverage. Maximum **3 critic rounds**, then present with the open gaps and the honest score. Never present below the bar without listing the gaps.

## 2. Dimensions (1 / 3 / 5)

| Dimension | 1 — material failure | 3 — usable with repair | 5 — strong |
|---|---|---|---|
| **Meaning / story** | a sentence's meaning changed, a subject dropped at a join, claims reordered so the viewer is misled; the hook buried | natural order, whole sentences, message recoverable; hook present but not tight; some beats do not show their sentence | whole sentences in natural order, in-points in the silence **before** the sentence (cut 0.06 s inside the silence); a layered hook in 0–1.5 s; a beat that **shows** the sentence every 3–6 s chosen by its meaning; the ending closes |
| **Caption / language** | wrong key word or number, unreadable or missing captions, broken RTL, a look-alike letter reads as another word (ז≈ו: "לבזבז"→"לבובו") | readable, awkward timing/wrapping; one spelling slip; exit animation missing on some cards | zero spelling errors (names, quotes); 1–3 words per card, words in final slots on a centred line, led by ≈ 0.08–0.1 s, last word ≥ 0.25 s, card ≥ 0.9 s; entry **and exit** animation; rail bottom ≤ y 1450; keyword contrast ≥ 4.5:1 sampled; look-alike test passed at final size |
| **Composition / brand** | speaker hidden or off-centre for long, graphics cover the face/mouth, a caption on the mouth, edges cut where they must not be | speaker mostly centred; cutout/graphics inconsistent; hierarchy gaps | the speaker is the clearest thing on screen (cutout ≈ +7 % brightness / +3 % contrast over the plate where used — assistant translation `[CONFLICT]` of an owner comment); graphics **behind** him in the clear side zones; face within 30 px of centre at every zoom; overlay cards ≤ 860 px under the chin; one locked palette (DESIGN.md), no foreign accents |
| **Motion / edit** | camera stutter/pop that obstructs, a visible hidden-cut jump, repeated transition tricks | some stalls or abrupt zooms; most joins covered | the camera never parks and never chases: opening push-in, punch-in/out every 2–4 s on one smoothed path (`motion_qa` 0 flagged ranges; `camera_path` ≤ 400 px/s² — house preset); hidden source cuts covered ≥ 6 f each side; every graded A-roll start has 6 f pre-roll; every transition different |
| **Audio** | VO masked, clipped or distorted; music/SFX fighting speech | intelligible; bed or SFX level distracting; a +5–6 LU jump at a cut | VO ≥ 5 dB over the bed in 1–4 kHz; music bed carved under the voice (≈ 4 dB lower than a first-pass bed on the owner's note); SFX −18 to −26 dB under VO, only on visible events, 1–3 f before the picture; 3 s-LUFS steps ≤ +3 LU at cuts; master −14 ± 0.5 LUFS, TP ≤ −1 on the **final file** (house preset) |
| **Integrity / continuity** | AI-looking stills of people as B-roll, a stranger shown under "I", footage that contradicts the words, colour that jumps between cuts | colour mostly consistent; one B-roll that "looks AI/static" | real footage / 3D / 2.5D / rebuilt UI B-roll by meaning; skin, blacks, sky consistent across cuts (for footage with a person: `color_check` pass at ≥ 85 % of sampled frames — a **named preset**, not universal); the assembled VO matches the source at every join (`join_diff` clean) |

## 3. Hard gates (derived; each blocks at ≤ 2 or on failure)

| Gate | Predicate | Evidence |
|---|---|---|
| **TH-G1 cut integrity** | no sentence missing its first or last two words; every join checked on the **full assembled VO** (ASR of isolated join snippets said "clean" while the full file still heard residues) | `join_diff` word-level diff on the chosen ranges; extra token = fail |
| **TH-G2 speaker and camera** | `face_center audit` over the **whole film** (tolerance 30 px) and `motion_qa` report `PASS` **with coverage**; hits are confirmed on frames (the mask also fires on bright graphics and B-roll people) | two QA envelopes with `decoded_frames` / coverage |
| **TH-G3 no AI-look people** | no AI-generated still of a person used as B-roll; a stranger is never shown under a first-person sentence | critic list with timestamps |
| **TH-G4 delivery** | length ±1 frame, −14 ± 0.5 LUFS, TP ≤ −1 on the final file, no black ≥ 2 frames, no dead edge band | `hf_deliver` verify block |

## 4. Mapping to the owner's general rubric (ten dimensions → six)

hook (0–3 s) → meaning/story · structure and story → meaning/story · pace → motion/edit · typography and captions → caption/language · motion → motion/edit · visual and colour → composition/brand + integrity/continuity · sound → audio · brand and CTA → composition/brand + meaning/story · uniqueness → composition/brand · AI artefacts → integrity/continuity. (src: distilled/02 qa §6.1) The owner's general release rule (average ≥ 4.0, none < 3) is the same threshold used here.

## 5. Numeric reference (informational, **not a score**)

`bands.json` → `types.talking-head`: a market profile (10 reels, all 9:16: median 44.8 s, cuts/min 6.65 [3.7–20.0], median shot 8.9 s, LUFS −17.0) and an owner profile (10 reels: median 49.7 s, cuts/min 15.25, median shot 3.23 s, 26.8 events/min, LUFS −16.35, music ratio 0.31). One test draft scored 75/100 against the market profile; the gaps (cuts/min, longest shot, LRA) were the reference's own style on purpose. Sitting inside p25–p75 proves nothing about excellence; small samples (n = 10); the automatic cut count is wrong in a large share of videos — correct it from frames. (src: distilled/02 qa §7.4)

## 6. Critic notes (type-specific)

- Check **join_diff** and **face_center/motion_qa envelopes first**; do not re-derive what a tool already proved.
- Watch for the owner's recurring catches: a caption on the mouth; a hidden source cut; zoom origin not on the face; centring fixed in one section only (audit every A-roll frame); "boring / looks AI / static" B-roll = replace the beat, do not polish; SFX too loud.
- Premium bar context: an owner target of "a premium edit worth ₪500–700 per video up to one minute" — a stated quality/price target, **not a measured market rate**.

## 7. Failure modes

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| a high average hides a dropped subject | averaging | the severe-failure list and TH-G1 | §1 |
| the critic passes what the owner rejects | not briefed with the owner's past notes | add the clean-smooth table and the Banned list to the brief | [critic-brief.md](critic-brief.md) |
| "PASS" with zero audited frames | face detector skipped frames | `INSUFFICIENT_EVIDENCE` | coverage in the envelope |

(src: distilled/02 video-types §2, qa §6–§7; QA_AND_BENCHMARKS §6; BENCHMARK_SUITE_SPEC §6 — read 2026-10-02.)

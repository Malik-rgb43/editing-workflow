# Rubric: motion-graphics (product/app launch, kinetic type, UI explainer; also trailer-teaser and music-montage until they get their own)

> Status: the owner's `motion-graphics.rubric.md` (criteria M1–M8, gates M1, M3, M7) **mapped into the six dimensions** of QA_AND_BENCHMARKS §6. Specified; model eval not run (decision default Q4); not calibrated against human raters. Written 2026-10-02 from distilled/02 qa §6.2, video-types §5, techniques §2–§3.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[SOURCED-unverified]` · `house preset`.
> Companion files: [critic-brief.md](critic-brief.md) · [visual-review-4-axis.md](visual-review-4-axis.md) · [bands.json](bands.json) · [briefs/B03.md](briefs/B03.md) · `agent-content/techniques/clean-smooth-motion.md`.

## 1. How to score

Score only what was seen/heard on stated evidence; `not_observed` ≠ 3; `N/A` needs a reason; 1–5 with anchors at 1/3/5; **severe failures listed separately and blocking** (a wrong number or price on screen at any frame; text cut by the frame; an empty morph shape; a black frame at a reveal). **Release rule `[RULE-owner]`:** average ≥ 4.0, no dimension < 3, hard gates M1 / M3 / M7 ≥ 3 (a gate at ≤ 2 blocks), no severe failure, automatic QA all `PASS` with coverage, max 3 critic rounds. Critic discipline: **count frames against the spec** (frame numbers, not impressions); zoom on every transition (`frames --at <t> --pad 0.25` or `sheet --range`); run a **mute test** and a **beat test** (hit offsets in frames from the spectrogram).

Pace here is measured in **visual events per minute counted by hand from frames** — `cuts_per_min` misleads in motion work (market 1.6–73) and the automatic count underestimates.

## 2. Dimensions (1 / 3 / 5)

| Dimension | 1 — material failure | 3 — usable with repair | 5 — strong |
|---|---|---|---|
| **Meaning / story** | a static opening > 1.5 s or an end card of a few frames; no closing; the payoff after 4 s | a reasonable opening; an ending without a CTA | movement from frame 1 and the result/payoff by 0–1 s (owner's technique videos: 0.4–0.75 s); a 3-step ending — name/message → promise/CTA → symbol on a clean background, 2–3 s hold; a concrete story object that changes on every screen; one anchor hero through the film |
| **Caption / language** | reversed Hebrew letters or words; `dir="rtl"` on the root (black render on the owner's builds); captions on a launch with big type | Hebrew correct, minor typography issues | Hebrew correct: `direction: rtl` only on text elements, wipes/scans/whips/per-word reveals run **right to left**, per-letter builds in reading order; Latin/numbers/₪ isolated; ≤ 7 words per card; look-alike test passed; **no captions by default** in a launch (an offer in one line only if the brief says sound-off) |
| **Composition / brand** | flat unreadable screenshot; text cropped by the frame during a camera move; a 3D object covering a price; several unconnected effects ("a pack of presets") | a clean screenshot with motion; a partial system | **one system / protagonist motif** that changes shape and drives the transitions; 2–4 colours + ONE accent that does not appear before the reveal (a foreign colour once to mark a moment); one type family, hierarchy by scale; UI **rebuilt in code identical to the screenshot** and shot as an object (perspective, depth of field, 150–300 % magnification until readable); 3D only where it earns its place, inside the UI with a contact shadow; a unique background per dark scene with a bookend |
| **Motion / edit** | a mix of eases, bounce on text, a fade as the transition, dead holds; a visible jump; two camera tweens overlapping | consistent but slow (9–24 f "middle" moves — the owner's default) ; an event every 1–1.5 s | **"snap, then drift"**: in `expo.out`/`power3.out` 2–10 f with blur only on the first frame; out `power2–4.in` 3–7 f; transformations `power3.inOut` 12–18 f; idle `sine.inOut` or a linear drift 2–4 %/s; no overshoot on text; stagger 1–5 f; **an event every 0.3–1 s** (≈ 45–110 events/min, hand count) with two-gear pacing (fast, breath, fast, silence before the reveal); no hold ≥ 1 s without internal movement; one camera spline per scene, exit = entry vector at every seam, every transition different |
| **Audio** | a flat bed unrelated to the picture, or TP above −1 (owner's own launches up to +3.2 dBTP) | a synced music bed plus some SFX | music **edited to the picture**: drops/hits on reveals, section cut 0 to −1 f before the hit, a take-away of 4–12 f (bass, highs or 100–175 ms of silence) before a big reveal, a riser ending exactly on the flash; SFX start 1–3 f before the picture; a breakdown under "processing", the drop on the result; brand/event sound audible on **every** event from the first second; no energy dip after the climax; natural ring-out to the last frame (the owner's later rule over a hard stop); VO ≥ 5 dB over the music in 1–4 kHz; master −14 ± 0.5 LUFS, TP ≤ −1 (house preset) |
| **Integrity / continuity** | a number flashes an intermediate value; the hero vanishes and returns; a morph through an empty grey shape; a one-frame vanish at a reveal | transitions mostly continuous; one seam with a jump | whole-number swaps with ≥ 12 f hold; the hero persists through every cut; a morph always carries content; the next scene starts **under** the previous one (no black outside a reveal); UI behaves like the real OS (list, not stack); numbers/prices only from the allowed set in the ledger |

## 3. Hard gates

| Gate (owner id) | Predicate | Blocks at | Evidence |
|---|---|---|---|
| **M1 frame-level spec before code** | `hf/PROMPT.md` with the six blocks, frame ranges, hex, px, easing checkpoints, a Banned list and the **three clean-and-smooth tables**; **four stills approved before the full render** (5); a storyboard in seconds with no frames or hex (3); built straight into code (1) | ≤ 2 | the PROMPT approval record (`approved_sha256`) + the four stills |
| **M3 motion language "snap, then drift"** | as in the Motion/edit row (5: the named numbers; 3: consistent but slow; 1: mixed eases, bounce on text, fade transitions, dead holds) | ≤ 2 | frame strips of every transition; the events list |
| **M7 sound locked to the picture** | as in the Audio row (5; 3: a synced bed plus some SFX; 1: a flat bed or TP above −1) | ≤ 2 | spectrogram offsets in frames; `hf_mix --report`; final-file loudness |
| **MG-G4 delivery** | length ±1 frame, −14 ± 0.5 LUFS, TP ≤ −1, no black ≥ 2 frames, no dead edge band (1088 authoring for 1080-wide) | on failure | `hf_deliver` verify block |

Calm brand films override the sound anchors: a uniform music bed with diegetic foley governs and a designed riser/impact mix is penalised (owner, later rule).

## 4. Mapping (owner criteria → six dimensions)

M1 spec before code → process gate (verified in the wf-03 gate record; its quality shows as fidelity in composition/brand and motion/edit) · M2 one system / protagonist motif → composition/brand · M3 motion language → motion/edit · M4 density and rhythm → motion/edit · M5 palette and typography → composition/brand + caption/language · M6 UI/product as the hero → composition/brand (+ integrity/continuity) · M7 sound locked → audio · M8 hook and closing → meaning/story.

## 5. Numeric reference (informational; **hand counts win**)

`bands.json` → `types.motion-graphics`: market (14, 16:9): median 55.7 s, 11.75 cuts/min, median shot 2.91 s, LUFS −15.3, music ratio 0.97; owner (4, mixed): median 24.6 s, 20.35 cuts/min, median shot 1.13 s, LUFS −15.8, SFX 1.8/min. The scorer checks loudness, first event and the gates only; "visual events/min" for the type is **45–110 by hand count** (a kinetic-type spot reached ≈ 195). Frame units in the owner's signature table were measured at 60 fps — halve for 30 fps.

## 6. Critic notes

Brief the critic with the owner's past rejections (the clean-smooth rule table + Banned list): the critic once passed a 4.11 draft whose four transitions the owner then rejected. Specific flags: repeated transition tricks, static holds ≥ 1 s, small corner labels, clipped text, unreadable key details, accent before the reveal, `[L-id]` lines not realised. Every score under 4 gets a timecode, a frame count and a fix (e.g. "2.10–2.50: the title enters in 18 f `power2.out`; change to 6 f `expo.out` with blur on f1; move the whoosh 2 f earlier").

(src: distilled/02 qa §6.2, video-types §5, techniques §2–§3; distilled/04 motion-design — read 2026-10-02.)

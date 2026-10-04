# Rubric: podcast-clip (a long episode or interview → short vertical clips)

> Status: **provisional and weakly grounded.** The author has **no** podcast-clip skill, rubric, benchmark JSON or delivered project (a short playbook, research notes and 17 of 20 reference breakdowns only; his rule is to build a type skill when a real project arrives). This rubric is derived by this repo from the playbook, the research layout/profile notes and the general six-dimension rubric. Specified; model eval not run (decision default Q4); not calibrated. Written 2026-10-02. Everything below is `[IDEA]` or `[SOURCED-unverified]` unless marked otherwise. **Do not present borrowed numbers as measured for this type.**
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[SOURCED-unverified]` · `[IDEA]` · `house preset`.
> Companion files: [critic-brief.md](critic-brief.md) · [visual-review-4-axis.md](visual-review-4-axis.md) · [bands.json](bands.json) (podcast bands are `null`/unmeasured) · `agent-content/playbooks/wf-podcast-clip.md`.

## 1. How to score

Score only what was seen/heard on stated evidence; `not_observed` ≠ 3; `N/A` needs a reason; 1–5 with anchors at 1/3/5; **severe failures listed separately and blocking** (a clip that depends on missing context; a quote cut so the speaker says the opposite; a face covered by a caption; a sponsor read left in). Release rule used here (the author's general gate, no type-specific calibration): average of scored dimensions ≥ 4.0, no dimension < 3, hard gates ≥ 3, no severe failure, automatic QA all `PASS` with coverage, max 3 critic rounds. Because the rubric is derived, **a critic score is an opinion, not a measurement**; the human selection table approval is the real gate.

Two style profiles exist; the brief names which one applies and the rubric scores *within* it (the dry profile contradicts the SFX policy of the talking-head type — switch by profile, not by habit):

| | **conversation-dry** (a long-conversation channel style) | **hyped / graphic** (a punchy-business-clip style) |
|---|---|---|
| title bar | white box, black all-caps text, 0–≈ 5.5 s, names the payoff (a redacted hook may omit the key word) | per owner style |
| cut pace | a hard cut every 4.1–6.3 s (2.5–3 s near the payoff, ≈ 5 s on emotional beats); punch-in every 5–6 s in a monologue | dense cuts |
| reaction cutaway | 1–1.5 s of the listener | per style |
| captions | 1–3 words at 60–70 % of height, **a colour per speaker**; style by emotion | word-by-word |
| audio | **no music, no SFX, laughter stays**; keep pauses in heavy content | music + SFX |
| opening / length | enters mid-conversation, no intro; end card 1.5–2 s repeating the title (not in emotional clips); 60–140 s | per style |
| B-roll | minimal 0–7 %, only for a concrete reference | heavy B-roll and icons |

(`[SOURCED-unverified]`, from two reference breakdowns — one dry 141 s reference: 8 shots, 3.0 cuts/min, average shot 17.6 s; one punchy Q&A clip 147 s: 41 shots, 16.3 cuts/min, mean shot 3.58 s — n = 1 each; src: distilled/02 video-types §7.3.)

## 2. Dimensions (1 / 3 / 5)

| Dimension | 1 — material failure | 3 — usable with repair | 5 — strong |
|---|---|---|---|
| **Meaning / story** | the clip needs context it does not give (selection score < 4/10), an opening that is intro/logistics/sponsor, the quote's meaning reversed by the cut | the clip stands alone but the hook is slow or the ending trails | **one complete thought** (question, explanation, experience, result; no punchline without setup); a strong hook in the first 3 s (a title bar that names the payoff, or a quoted sentence, question, or curiosity line separate from the spoken hook); an emotional peak or surprising information; a **closed ending** or a loop (the last sentence links to the opening / cuts on a reaction) |
| **Caption / language** | wrong word/number, captions covering a face or mouth, unreadable | readable; colour-per-speaker inconsistent; sizes uneven | 1–3 words, per-speaker colour where the profile calls for it (host/guest), correct Hebrew RTL, numbers as digits, entry and exit animation; in SPLIT layouts the captions sit **on the seam** so no face is covered; rail ≤ y 1450 |
| **Composition / brand** | a speaker cropped out or off-centre for long; wrong layout for the number of speakers | a crop that follows the face but jitters; the layout fixed when it should switch | the layout fits the number of speakers — **TRACK** (one speaker, a 9:16 crop following the face), **SPLIT** (two speakers, 50/50 top/bottom), **GRID** (3–4, the active speaker ≈ 60 %), GENERAL fallback (16:9 centred on a blurred background); source ≥ 1080p, 4K better (a 9:16 crop of 16:9 1080p leaves ≈ 608 px width); a constant logo/title treatment per the profile |
| **Motion / edit** | shot switches faster than ≈ 1.5 s that follow noise; a camera that chases each sway; a visible jump at a join | the crop moves too often or too late | **active-speaker switching with hysteresis (never < ≈ 1.5 s)**; a "heavy tripod" crop that moves only when the face leaves a ≈ 10 % margin; the crop path smoothed (`camera_path`-style; `motion_qa` 0 flagged ranges); hard cuts at the profile's pace; reaction cutaways 1–1.5 s |
| **Audio** | one speaker masked by another, clipped, music over speech in a dry profile | intelligible; levels differ between speakers by an audible step | speech first: each remote-recorded speaker normalised, laughter kept, no music/SFX in the dry profile or a carved bed + sparse SFX in the hyped one; −14 ± 0.5 LUFS, TP ≤ −1 on the final file (house preset) |
| **Integrity / continuity** | faces blurred/censored unintentionally; a sponsor or private moment left in; an unconsented clip | one unverified detail (a name, a number) | the speaker's words intact (word-level diff of the assembled clip against the source: `join_diff`); consent/permission recorded for every person in the clip; a clip never implies an endorsement the speaker did not give |

## 3. Hard gates (derived)

| Gate | Predicate | Evidence |
|---|---|---|
| **PC-G1 stands alone** | the clip is understandable with no context; the **selection table score ≥ 4/10 else rejected** (the author's earlier clipper-research gate) | the selection table the person approved *before* editing (timecode, title, score, hook) |
| **PC-G2 hook in 3 s** | a hook or title bar names the payoff within the first 3 s | frame strip 0–4 s |
| **PC-G3 face and caption safety** | no caption over a mouth or face; layout matches the number of speakers; switches obey the hysteresis | `face_center audit` (single-speaker TRACK crops) + frame review; shot-length list |
| **PC-G4 permission** | everyone in the clip consented to this use; no sponsor read | consent record path; transcript check |
| **PC-G5 delivery** | length ±1 frame, −14 ± 0.5 LUFS, TP ≤ −1, no black ≥ 2 frames, no dead edge band | `hf_deliver` verify block |

## 4. Numeric reference

**None measured.** `bands.json` → `types.podcast-clip` has `null` bands (no benchmark JSON exists for the type); the two reference breakdowns above are n = 1 examples, not distributions. Clip lengths seen in the author's own examples: 54 s to 3.3 min (he is **not** limited to 60 s). Hebrew ASR on CPU was ≈ 2.3× real time in the author's report (a one-hour episode ≈ 2.3 h) and 0.84 audio-s per wall-s (CTranslate2 int8 CPU) in a 614 s read-speech test on the reference machine (single pass) — plan the full-episode ASR at minute 0 (`wf-podcast-clip`).

## 5. Critic notes

Do not review the whole episode — review the **selected clip only** and the selection table; confirm the selection score and the stand-alone gate first; check face/caption collisions at every layout switch; confirm no sponsor read or private chatter; keep laughter in the dry profile. A critic must say that the rubric is derived and that no calibration exists.

(src: distilled/02 video-types §7; QA_AND_BENCHMARKS §6; distilled/06 talking-head-and-footage §2.3 — read 2026-10-02.)

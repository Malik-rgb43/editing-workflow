# wf-02 — Concept and script (קונספט ותסריט)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §1, distilled/02 workflow-end-to-end §4 and video-types §2–§7, distilled/01 rules-and-gates A5/B5/B6.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[SOURCED-unverified]` · `[IDEA]` · 💲 = paid step · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | 2 of 9 |
| Owner skill | `video-brief-intake` (concept step) + the **type skill** (`talking-head-editor`, `testimonial-editor`, `ad-promo-editor`, `motion-graphics-builder`, `ai-generated-video-editor`; podcast: this repo's `wf-podcast-clip`) |
| Artifacts (exact files) | `hf/CONCEPT.md` (three concepts, the recommendation, `chosen:` with the person's mix), `hf/SCRIPT.md` (the script with ranked hooks, **or** the paper edit / **text of the cut**, with an `approved:` line), optional `_work/concept/stills/` (4 key stills) or an animatic, new `A` rows in `hf/PROMPT.md` `<ledger>` |
| Exit gate | **G2 — the person picked; the cut text/script is approved with no picture render** |
| Target time | **20–40 min** (owner target) |
| Paid steps | generated stills/animatic for a visual concept 💲 — only with a dated estimate and approval (`paid-spend-gate`); the default is a quick HyperFrames mock + `snapshot --describe false` (free) |

## 1. Purpose

Decide **what the film is** before anything is specified frame by frame. **The chosen concept is the contract** — a limiting tool means *search another route* (Blender, Three.js, 21st-style UI components, AI + motion) before dropping the idea; a dropped idea is presented with an alternative. `[RULE-owner]` (src: distilled/02 workflow §1 principles)

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| G0 (and G1 if a reference was used) passed | gate log | back |
| for footage: the transcript (`transcribe`) and the source-cut list are done or running | `words.json`, `src_cuts.json` (or a STATE line "running") | wait (the cut text needs them); do not guess |

## 3. Steps

| # | Step | Who | Evidence / output |
|---|---|---|---|
| 1 | **Is a concept already fixed?** If the person wrote it, it is a set of ledger rows — skip step 2 and go to step 3. "חדש לגמרי" = zero carry-over from earlier versions except facts and logo (the old moves go on the Banned list). | agent | the decision stated in chat |
| 2 | **Three concepts: Proven / Bold / Wild** (only when none is fixed). Each: a one-line logline · what happens at **0–3 s** · a beat list with seconds · the look (hex) · the 3D/B-roll plan · the risk · cost (any 💲 line). **All three obey every locked ledger row.** Recommend one with a reason; the person may mix; chosen elements enter the ledger as `A`. | agent proposes, **human picks** | `hf/CONCEPT.md` |
| 3 | **Script or cut text** (per type, §7): footage → show the **text of the cut** (or a 30 s audio-only cut) **before any visuals**: natural order, whole sentences, in-point in the silence **before** the sentence, nothing dropped at a join ("אז אני…" must not lose "אני"); ads/testimonials → ranked hooks + paper edit; motion → story first, a screen per beat every 2–6 s. | agent | `hf/SCRIPT.md` |
| 4 | **Visual concept → 4 key stills** (hook, reveal/peak, a mid-transition, end card) from a quick HF mock + `snapshot --describe false` (≤ 5 timestamps per call), **or an animatic** (stills + timecodes + audio cues). Paid generation only with an estimate 💲. | agent | `_work/concept/stills/*.png` |
| 5 | **Present** the options/cut text; record the person's pick and approval; add `A` rows. **No render** — an audio-only cut file is allowed. | **human approves** | message id; `approved:` line in `SCRIPT.md` |

Measured on the author's tests: an **audio-only cut shown before building visuals** would have saved the 3–4 h restructure; the timing and ordering of cuts are decided **here**, not after the build. `[PROVEN-internal]`

## 4. Exit gate G2

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| the person chose one concept (or the ledger fixed one) | message id; `hf/CONCEPT.md` `chosen:` | else `blocked` |
| every locked ledger row is still satisfied by the chosen concept | the ledger check exit code 0; a one-line check per row family in CONCEPT.md | else `fail` |
| the cut text/script is approved | message id; `hf/SCRIPT.md` `approved:` line with the date | else `blocked` |
| **no picture render** was made to get this approval | `ls _work/drafts/` shows no video (an audio-only file is fine) | else `fail` (a render here is the waste this gate prevents) |
| a dropped idea has an alternative recorded | `CONCEPT.md` "dropped → alternative" rows or `n/a` | else `fail` |
| paid spend, if any, has an approved dated estimate | `cost_estimate.json` + approval message id, or `n/a` | else `blocked` |

## 5. Human vs agent

| Human | Agent |
|---|---|
| picks or mixes the concept; approves the text of the cut / the script; says "this is the time to destroy everything" if the direction is wrong *now* (cheap) | writes the three concepts, the paper edit, the hook options; shows the audio-only cut; builds 4 stills cheaply; keeps all options inside the locked ledger |

## 6. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| a sentence loses its subject | the cut starts after "אני" | move the in-point into the silence before the sentence; ASR the **full** assembled VO | step 3 + `join_diff` later |
| the person approves, then asks for a different structure | the cut text was never shown | show the text now; no render yet | step 3 |
| three concepts that differ only in colour | no real axis of difference | vary the *idea* (hero object, structure, hook), not only the look | step 2 |
| a concept needs a tool that is missing | tool limits | search another route; present the alternative | contract rule |
| generation started "to see" | no estimate/approval | stop; estimate; ask | 💲 gate |
| polished stills of a bad idea | design before decision | the 4 stills are for approval, not polish | step 4 |

## 7. Per-type deltas

| Type | Delta |
|---|---|
| **talking-head** | the text of the cut (natural order, whole sentences, silences trimmed; reorder only with a strong reason); restructure only if asked at intake; the beat menu is chosen by the **meaning** of each sentence (place/result → real footage full-bleed; "I listen/ask" → data-driven orb; a process → UI steps; documents → 3D product shot; availability → notifications + 3D type; calm/planned → one continuous 3D metaphor; a problem → colour drains behind him + a red keyword; stage N → a top panel over the speaker); never AI stills of people; a beat every 3–6 s `[RULE-owner]` (assistant translation; earlier notes said 5–7 s / 2–6 s `[CONFLICT]`) |
| **testimonial** | **soundbite selection:** split into sentences by word times; score each 0–2 on **Specific** (number, time, ₪), **Emotion**, **Contrast** (before→after), **Standalone**, **Provable** (a screenshot exists), +2 if it kills an objection (price, "another course", zero experience); hook = highest Specific + Standalone; close = highest Emotion; body = the best before/turn/result lines; a timecoded paper edit + **3 hook options** in `SCRIPT.md`. Ranked hooks: result + proof · a twist · pain with a number · authority superlative · a multi-client supercut. **Forbidden openers:** name + age, "hi what's up", "I want to recommend", mid-sentence start, logo first. Never splice to change meaning; log every reorder; never AI-generate a client, voice or result |
| **ad-promo** | `SCRIPT.md`: **3 ranked hooks** (offer as the first line · before→after in 0–1.5 s · a visual shock landing on the offer · a contrarian claim · a specific pain call-out · a comic sketch), a beat sheet (hook → problem → product → proof → offer → CTA; offer + CTA ≈ 30–45 % of a 30 s ad), the offer ×3 (voice, super, end card). Forbidden: a generic question over a static talker, a story preamble, hype without the fact, a blurry frame 0, a logo first, a silent 9:16 frame with no text. Claims/prices/before-after only as supplied in writing — never invented |
| **motion-graphics** | **story first:** one sentence of what the viewer feels, then one screen per beat every 2–6 s; each screen has a concrete story object that changes; one hero anchor; transitions each different; the three concepts differ in the hero object and structure; a 30 s dense cut felt ×1.7 too fast and 45 s was approved — settle length now |
| **ai-generated** | pick a **format** and say why (X-ray/anatomy explainer · list gag · interviews · parody of a known format (organic only) · motion transfer · hybrid launch · local-business hybrid); **design around the model's weaknesses before prompting** (avoid close-up faces unless proven; silhouettes/backs/masks; standalone shots; text added in post); a ground truth for technical subjects; the plan may be a **shot-card document** — nothing is generated until it is approved; images before video |
| **podcast-clip** | the **selection table** (timecode, title, score, hook), ranked by: stand-alone (hard gate: < 4/10 rejected), a strong hook in the first 3 s, an emotional peak or surprising information, a closed ending; the person chooses **before editing** (see `wf-podcast-clip`) |

## 8. Tool invocations

`transcribe` (done in wf-00/01) · `source_cuts` · `aroll_cut` (proposes an `edit.json` + `src_cuts.json` from words + energy snapping — `tools/aroll_cut.py`: a PROPOSAL for the paper-edit approval, never an auto-cut) · `ffmpeg` (a 30 s audio-only cut: concatenate the kept audio ranges) · `sheet` · `hyperframes snapshot --at … --describe false` · `visual-choice-board` (skill) when a visual hesitation appears · `ledger` (timing line).

## 9. Time labels

Owner target 20–40 min; modelled: none; measured: none on a student. The 3–4 h saving above is a historical owner estimate (premium talking-head test), not a controlled measurement.

(src: distilled/02 workflow §4, video-types §2–§7; distilled/01 A5, B5, B6 — read 2026-10-02.)

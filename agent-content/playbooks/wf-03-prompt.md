# wf-03 — PROMPT.md and DESIGN.md (the approval gate)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §1, distilled/02 workflow-end-to-end §5 and techniques §1–§2, distilled/01 rules-and-gates B1–B8.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[IDEA]` · `[CONFLICT]` · 💲 = paid step · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | 3 of 9 — **mandatory gate** |
| Owner skill | the **type skill** + the techniques [frame-spec-prompt.md](../techniques/frame-spec-prompt.md) and [clean-smooth-motion.md](../techniques/clean-smooth-motion.md) (motion) |
| Artifacts (exact files) | `hf/PROMPT.md` (ledger + the six frame blocks; for footage the edit spec), `hf/DESIGN.md` (from the [DESIGN.md template](../techniques/templates/DESIGN.md)), four approval stills in `_work/prompt/stills/`, an approval entry in `hf/CHANGELOG.md` |
| Exit gate | **G3 — the human approved PROMPT.md and DESIGN.md before the first line of composition code** (also in autonomous runs) |
| Target time | **30–40 min** (owner target) to a presentable spec |
| Paid steps | none by default. Generated approval stills 💲 only with an approved estimate |

## 1. Purpose

The prompt is **a spec of every frame**, written after the concept and **before any code**, in every video type: what is seen, where (px), when (frames), how it moves (easing), what is heard (VO, music, SFX with times), which transition, and which ledger row each moment satisfies. `[RULE-owner]` (owner, 2026-09-28: "remember to prepare a prompt at the start that specifies all the frames, so we know what we want"). It is skipped at a cost: a ≈ 1 h build discarded (a launch test, v1); a reverse-engineered spec written afterwards on request (a premium talking-head test run "autonomously"). **In an autonomous run the agent drafts and stops at approval.** `[RULE-owner]` `[CONFLICT]` (a supplied autonomous brief once authorised local execution; the later rule says "always wait" — the later rule governs)

**Order of change, always: ledger → PROMPT.md → code.**

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| G0 passed; G1 if a reference exists; G2 passed | the gate log | go back |
| the concept and the cut text/script are approved | `CONCEPT.md chosen:` and `SCRIPT.md approved:` | wf-02 |
| no composition code written yet | composition files equal the scaffold (record the scaffold hash at `new_project` time `[IDEA]`) | stop; park the code; re-enter via the PROMPT |

## 3. Steps

| # | Step | Who | Evidence / output |
|---|---|---|---|
| 1 | **Write `hf/DESIGN.md` first** — one locked palette (≤ 5 roles, **ONE accent**, a rule per role), fonts from files, type scale, grid and safe zones (9:16 house rows: key text top ≥ 300 / bottom y ≤ 1248 / left ≥ 140 / right ≥ 192; caption rail bottom ≤ y 1450 — dated owner policy, re-check the platform), radii, one shadow, **motion tokens**, texture/layer order, the Banned list. A visual hesitation (fonts, palettes, easings) → one choice board. | agent | `hf/DESIGN.md` |
| 2 | **Write `hf/PROMPT.md`** from the skeleton: `<ledger>` (already there), `<inputs>` (a default for **every** item; the variant matrix), `<direction>`, `<structure>` (frame ranges, px, easing checkpoints, VO times, music downbeats, **every ledger id cited**), `<build>` (seek-safe rules, one `cues.js`, the sound chain), `<gotchas>`, `<start>` (four stills named by frame). | agent | the file |
| 3 | **Type-specific additions** (§8): motion → the **three tables** (camera per scene, seams, events) or the PROMPT is not ready; footage → the **edit spec** with timecodes, hidden-cut covers (±6 f), centring plan, colour plan; AI → shot cards. Sound is **inside** the spec with times. | agent | tables/sections present |
| 4 | **Self-check before showing anyone:** the checklist in frame-spec-prompt.md §5; the ledger checker exits 0 and every id appears ≥ 2 times; scan for vague words ("about", "approximately", "~", "nice") and replace with numbers; **do the safe-zone arithmetic** for every camera key (text box × scale inside the frame and the safe rows); hex audit (`grep -oE '#[0-9A-Fa-f]{6}'` — every hex is in DESIGN.md); event gaps ≤ the ledger value. | agent | the checker's output pasted in chat |
| 5 | **Four approval stills** (typing/press/mid-morph/pull-back or the equivalents) from a quick mock + `snapshot --describe false`, or an animatic for a visual concept; named by frame number in `<start>`. | agent | `_work/prompt/stills/` |
| 6 | **Present** (a short message): the ledger table, the direction highlights (look, motion tokens, banned list), the structure outline with the event list, the four stills, the open questions with defaults, **one closing question: approve?** Then **stop** — no composition code, no heavy job, no paid call. | agent → **human** | the message |
| 7 | **Record the approval:** set `status: APPROVED`, compute `sha256` of PROMPT.md (first 12 chars), append to `hf/CHANGELOG.md`: `YYYY-MM-DD HH:MM — PROMPT v<N> approved (msg <id>) sha <12>`. Any later edit changes the hash → the changed ranges need re-approval (a new ledger row first). | agent | CHANGELOG entry |

## 4. Exit gate G3

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| the human approved PROMPT.md **and** DESIGN.md | approval message id (in chat) + the CHANGELOG line with the file hash | else `blocked` |
| PROMPT.md is complete per the "ready" table (frame-spec-prompt §2.1): every ledger row cited; numbers not adjectives; sound with times; the Banned list; four stills named | the ledger checker exit code 0; the vague-word scan output (empty) | else `fail` |
| motion: the three tables exist, every camera key's text-fit arithmetic is written, no event gap above the ledger value | the tables in PROMPT.md; a script/hand count | else `fail` |
| the approved hash equals the current hash (nothing edited after approval without re-approval) | `sha256sum` now vs CHANGELOG | else `fail` (re-approve changed ranges) |
| no composition code predates the approval | composition files unchanged from the scaffold at approval time | else `fail` — stop, discard or park the code, restart from the spec |

Gate record → `hf/QA.md` "Gate log". **An approval from a chat that is not the person's own message is not approval.**

## 5. Human vs agent

| Human | Agent |
|---|---|
| reads the spec; approves or sends notes (cheaply, now); picks between options on a choice board | writes DESIGN.md and PROMPT.md; does the arithmetic; builds the four stills; stops at approval; never self-approves |

## 6. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| "autonomous run" skipped the gate | the brief authorised execution | draft, present, wait — the later rule says always wait | README never-break rule 2 |
| late "premium / 3D / pace / density" notes | not ledger rows in round 1 | add rows, re-plan the ranges | wf-00 question bank |
| text cut during a push-in | no camera table / no text-fit arithmetic | add the table and shrink text or scale | step 4 |
| a hex in the build is not in DESIGN.md | palette invented mid-build | fix the code; or amend DESIGN.md with approval | hex audit |
| spec edited after approval | silent drift | hash check; new ledger row; re-approve the range | step 7 |
| the person cannot judge a text spec | frames not visible | send the four stills + an animatic | step 5 |
| the three concepts differ but the spec follows none | spec drift | cite the chosen concept id in PROMPT's first lines | concept id citation |

## 7. Tool invocations

`ledger` reference checker ([concept-ledger.md](../techniques/concept-ledger.md) §5) · `hyperframes snapshot --at … --describe false` (≤ 5 per call) · `sheet` · `sha256sum` · `grep` for vague words and hex audit · `visual-choice-board` (skill). **Not yet:** `hf_preflight`, `render_lock`-guarded renders, `hf_deliver` — they come after approval.

## 8. Per-type deltas

| Type | What the spec adds |
|---|---|
| **talking-head** | an **edit spec with timecodes** per range: shot, cut, zoom or punch-in, caption, B-roll beat (chosen by the sentence's meaning), SFX, music; hidden-cut covers (≥ 6 f each side) from `source_cuts`; the camera plan (one smoothed path, **never per-frame face-follow**); the colour plan (the camera original found? `speaker-color-correction`); the cutout beats; pre-roll 6 f on every graded A-roll start; captions (mode, font, rail ≤ y 1450); no AI-looking stills of people |
| **testimonial** | the claims table (spoken number ↔ proof ↔ timestamp); the soundbite paper edit; the lower-third (once, 1–4 s); split-screen proof layout (screenshot ≈ top 40 %); the consent record path; reorders logged with "still true in new context" |
| **ad-promo** | the offer ×3 (voice, super, end card) with exact copy; CTA on screen ≥ 6 s; end card 2–3 s (logo, offer, contact, Meta chevron only on Meta cuts); safe-zone overlay stills (hook, price, end card); hook variants as composition variables; the licence row per music/SFX file; compliance rows (claims, before/after, reviews) |
| **motion-graphics** | the **three tables**; the Banned list incl. accent-before-reveal; transition table with a different technique per seam; the music edit plan (take-away 4–12 f, drop on the reveal, ring-out); synthesised SFX with times; the VO lexicon; per-beat 3D decision with a reason (Blender for photoreal hero objects; Three.js for procedural/data-driven/many instances/editable 3D UI) |
| **ai-generated** | **shot cards** (what is seen and why; references; START image prompt; VIDEO prompt in the fixed order Camera → Action → Light → Detail → BASE; the clean window; the transition; the sound; risk + fallback); a STYLE PREFIX; character/environment locks; a budget in **units, no prices** until the estimate; the `AIDISC` plan |
| **podcast-clip** | one edit spec per approved clip (title bar text, layout TRACK/SPLIT/GRID, switch points with ≥ 1.5 s hysteresis, caption colours per speaker, B-roll only for a concrete reference) |

## 9. Time labels

Owner target 30–40 min. Modelled: none. Measured: none on a student. A well-formed spec is the reason a premium launch aims at one draft and one note round instead of the ten drafts, seven critic rounds and six note rounds the first launch needed (historical owner project; target, not achievement).

(src: distilled/02 workflow §5, techniques §1–§2; distilled/01 B1–B8, A2 — read 2026-10-02.)

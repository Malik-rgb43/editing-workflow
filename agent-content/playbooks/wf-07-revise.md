# wf-07 — Present and revise (הצגה וסבב הערות)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §1–§2, distilled/02 workflow-end-to-end §9 and §12, distilled/01 rules-and-gates G1–G10, research E12.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[SOURCED-unverified]` · `[IDEA]` · 💲 = paid step · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | 7 of 9 — repeats until approval |
| Owner skill | `revision-notes-handler` (+ [studio-review-loop.md](../techniques/studio-review-loop.md)) |
| Artifacts (exact files) | the presentation message (file at once + numbered notes + the whole ledger + QA line + honest score + gaps), `hf/CHANGELOG.md` "## Round N (date)" (the person's notes numbered, in their words), `_work/notes/r<N>_n<k>.jpg` (a frame strip per note), `projects/<name>/tools/patch_r<N>.py` (patch script), new `hf/PROMPT.md` ledger rows, `hf/QA.md` |
| Exit gate | **G7 — the person approves the preview (→ wf-08) or sends notes (→ this procedure, then back to wf-05/06)** |
| Target time | present: **5 min**; a note round: **≤ 45 min with exactly ONE full render** (owner target) |
| Paid steps | a regenerated shot or a hosted render 💲 — each needs its own dated estimate and approval; a previously approved number never covers a new round |

## 1. Present first (stage 7)

**Deliver the file at once**, then the message below. For the author the review happens **live in HyperFrames Studio** (`python tools/hf_studio.py <project>/hf`; a **local** server — for a remote client send the draft render or a screen recording instead). `[RULE-owner]` Ask one question: *fixes, or render the final?* **The final render happens only after the person approves.**

```text
Round <N> — <name>_v<N>: <path>   (Studio: <link or "local port">)
Your notes:
1. ✓ "<the person's words>" — cause: <…>. Now: <…> (<time> / <frames>)
2. ✓ "<…>" — <the change and the new value>
3. ✗ "<…>" — open gap: <why> + alternative
Concept fidelity (the WHOLE ledger, not only this round's rows): L01 ✓ · L02 ✓ (f30–60) · … · L14 ✓ (round <N>)
QA: frame_qa 0 · caption_qa 0 · face audit 0 · −14.0 LUFS / TP −1.3 · critic 4.2 (lowest: <dimension>) · coverage: <decoded/expected frames>
Honest score and open gaps; licence risks where relevant; the process and tools used.
One closing question.
```

(In the author's original the numbered lines are in Hebrew, e.g. `1. ✓ "המעבר ב-25 לא טוב" — סיבה: … עכשיו: … (24.6–25.4 / f738–762)`; the structure is the contract.) **Never present with a flagged frame or a failed gate; never present below the bar without listing the gaps; always write the honest score.** `[RULE-owner]` An `✗` is a numbered gap with its reason, never silent.

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| **G6 passed** for the file being presented (round 1: the first candidate; later rounds: the corrected ranges) | the G6 gate record | wf-06 |
| the file is newer than the last patch | mtime check | re-render (one) |

## 3. The revision procedure (owner sends notes)

Goal: **≤ 45 min per round and exactly one full render per round** `[RULE-owner]` (in the long test every round cost 1–5 renders; the order below closes that). **A timed note means: extract frames, diagnose, plan again — not polish.**

| # | Step | Artifact | Gate |
|---|---|---|---|
| 1 | **Collect.** First reply: *"collecting notes for another 5 minutes, then I fix and render — anything else?"* While the person types: **diagnose and patch yes; full render no; segments only.** A note arriving mid-render: first half → stop (own process tree only) and re-run after collection; second half → finish; it joins the next round unless it is a blocker. Log under `## Round N (date)` numbered in the person's order and **words**; split multi-claim notes (1a, 1b); an ambiguous note ("not good" with no detail) → ONE question with 2–3 concrete options + the frame, **only if the diagnosis is not decisive**. | `CHANGELOG.md` list | the person finished, or 5 min without a new note |
| 2 | **Frames at each time:** `sheet --range 24:26 --fps 10 --out _work/notes/r3_n2.jpg`; the person's times are approximate — look **one second each side**; at a transition every frame (`--fps 30`) ±0.5 s; open the same range in PROMPT.md (what *should* be there). | a strip per note | every note has a picture |
| 3 | **Diagnose** with one question: *what exactly on screen creates the feeling, and which line or asset does it?* Table below. | a concrete cause (file/line/cue/asset) | no guesses |
| 4 | **Classify** each note (table below). | — | — |
| 5 | **PROMPT.md first.** Each note is a **new ledger row** (next id, `said` = the person's words + the round tag, a measurable `spec`, an acceptance check) cited in `<structure>` in its range; replace-concept → rewrite the range (frames, px, easing, SFX); a motion note also becomes a row in the clean-smooth rule table. **Never code first.** | new rows; updated structure | every new id cited |
| 6 | **Patch in a batch** — a script file with unique-anchor asserts and a backup; close Studio / strip `data-hf-id` first; anchors to word cues, whole frames; all of the round's notes in one patch; then `hf_preflight`. | `patch_r<N>.py` | asserts pass; 0 errors |
| 7 | **Cheap verification:** preflight → **Studio** (live) → `hf_segment --qa` per changed range **only for render-only risks** (`<video>` layers ≈ 1 frame difference; cuts) → snapshots (≤ 5 per call, `--describe false`) → the **same critic** (message, not a new agent) on the fix list only. A **global rule** is verified at **every** occurrence. | clean ranges | every ledger row of the round ticked |
| 8 | **ONE full render** after approval/collection and after **all** reviewers returned → wf-06 stages 5–7 on the **changed ranges**. | the draft | G6 |
| 9 | **Present** with the §1 message. | message | — |
| 10 | **Learn:** each note → the lessons inbox (grep first; raise the count of an existing line); in the retro count the full renders of the round (**target 1**) and the time (wf-09). | inbox lines | — |

### 3.1 Diagnosis table (the author says → the common cause that actually happened → where to look)

| The person says | Common cause | Where to look |
|---|---|---|
| "something is just there" / a missing element | stale timing grid after a re-time (literals outside the scene window) | `hf_preflight` errors; `grep -n "F("` |
| a jump or glitch at a cut | a hidden source cut; a pre-roll shorter than 6 f; a first frame without grade | `source_cuts`; "double jumps" in `frame_qa` |
| "the speaker is not centred" | the zoom origin is not on faceX | `face_center audit` on the **whole** film |
| "it's cut off" | centre-growth; an exit before the word landed; a wipe that did not finish | snapshots at start/middle/end of the event |
| "not smooth" / "stuck" | stitched tweens; two tweens on the camera; no spline | [clean-smooth-motion.md](../techniques/clean-smooth-motion.md) §1 |
| "the SFX is loud" | gain above −18 dB under VO | `hf_mix --report` |
| "boring" / "looks AI" / "static" | **the beat's concept itself** | replace-concept |

### 3.2 Classes

| Class | Signs | What to do |
|---|---|---|
| **replace-concept** | "boring", "looks AI", "static", "I didn't like it" (taste, not a fault) | a **new beat from the editor's beat menu**, chosen by the *meaning* of the sentence; do not polish the old one; explain in ONE line what you chose and why |
| **fix** | glitch, position, size, timing, cut, colour | fix the cause from step 3 |
| **audio-only** | SFX, music, VO level, a swoosh | the audio branch below — **no render** |
| **restructure** | "shorter", "move this earlier", "cut the middle" (order or length) | show the new order in PROMPT.md (and on the storyboard page when beats change), **ask before patching** |
| **music-swap** | "another song", "different music" | the audio branch below with a new licence row; no render |
| **global rule** | "always", "never", or the same note in two rounds | fix **all** occurrences in the film (centring was fixed by section and 17–24 s was missed); add the rule to the style notes (wf-09) |

### 3.3 The audio-only branch (remix + remux, no render)

Edit the cue file (SFX gain, `DUCK`, `BED`) → `hf_mix --report` → `hf_deliver --skip-render` (remux onto the existing raw render). On OM **1.8 s** of machine time in E12 (a synthetic 30 s composition) and "≈ 2 min instead of 10+" in the author's workflow `[MEASURED-lab]` `[PROVEN-internal]`. Do not chase loudness inside the composition (more gain once came out quieter). A **mixed** round (audio + picture) puts the audio into the same single full render. A project whose audio is composed inside the engine (no `mix.wav`) cannot change its mix without a render — build with `hf_mix`. `--skip-render` must be bound to the build hash: it once could remux a **stale picture** after a visual change (audit AQ014).

### 3.4 Studio-first numbers (E12, `[MEASURED-lab]`, OM, a synthetic 30 s composition, six notes, single pass)

A full render per note: **430 s** · range drafts **161 s + one final full render 79 s = 240 s** · scene cache 226 s · an audio-only note 1.8 s · Studio hot reload detected an edit in 0.04–0.9 s (once it missed an edit; re-check that the change landed). Not measured: human review time and agent thinking time. Preview ≠ render: `<video>` layers differ by about one frame; keep the encoded check for render-only risks. Details: studio-review-loop.md.

## 4. Client-revision theory (educators; `[SOURCED-unverified]`, recorded 2026-09; the author's rules win)

Late revisions come from no buy-in, no clear definition, and no room to say "no". Show a high-fidelity, low-commitment reference **early** (a styleframe or one polished scene) and say "this is the time to destroy everything"; ask questions that are easy to answer "no" to ("would it be too much if…?"); translate "like/hate" into parameters (colour, texture, pace) and repeat what you heard; define **approval points** (where changes are welcome and where they cost money); collect all notes, settle contradictions between stakeholders, then fix; number versions V1/V2/V3 with documented notes.

## 5. Exit gate G7

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| the person **approved** the preview (→ wf-08) — or sent notes that were logged (→ next round) | the person's message id; `CHANGELOG.md` round entry | else `blocked` (waiting) |
| in the round just completed: **exactly one full render** | the timing ledger count; `ls _work/drafts` | else `fail` + explain in the retro |
| every note of the round has a ledger row and a ✓/✗ line in the presentation | `PROMPT.md` diff; the message | else `fail` |
| the presentation lists the **whole ledger**, the QA line with coverage, the honest score, open gaps | the message text | else `fail` |
| patch scripts exist for every code change (no inline heredoc patches) | `projects/<name>/tools/patch_r*.py` | else `warning` |

Gate record → `hf/QA.md` "Gate log". Approval from anyone other than the person who owns the video's decisions is not G7.

## 6. Human vs agent

| Human | Agent |
|---|---|
| reviews in Studio; sends notes (batched is cheaper); approves the preview; decides taste | collects, frames, diagnoses, classifies, updates the ledger first, patches by script, verifies cheaply, renders **once**, presents numbered by the notes with the whole ledger |

## 7. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| 1–5 full renders in a round | rendering per note | stop; Studio + ranges | steps 1, 7, 8 |
| the same note returns | a global rule fixed at one occurrence | audit every occurrence; add a rule | class "global rule" |
| the person says "I told you" | the note was not logged in their words / no ledger row | add the row; show it in the message | step 5 |
| a late "boring" polishes the same beat | polish instead of replace | choose a new beat from the menu | class "replace-concept" |
| a render killed for one fix while reviewers ran | no wait | wait for **all** reviewers | step 8 |
| the same note sent to three sessions | a global style rule | log it with a `global` tag; the author session promotes it; **never message other sessions** | wf-09 |
| `--skip-render` shipped a stale picture | mix-only remux on changed visuals | bind raw to the build hash; one full render for mixed rounds | §3.3 |

## 8. Tool invocations

`sheet --range a:b --fps 10|30` · `hf_preflight` · `hf_segment --qa` · `hyperframes snapshot --at … --describe false` · `python tools/hf_studio.py <project>/hf` · `hf_mix --report` · `hf_deliver --skip-render` (audio-only) · `seg_diff` (planned: SSIM/VMAF per frame **outside** the fixed range — proves a segment fix touched nothing else) · `join_diff` · `frame_qa` etc. via wf-06 · `ledger`. Patch scripts are written with the file-writing tool, not shell heredocs.

## 9. Per-type deltas

| Type | Delta |
|---|---|
| **talking-head** | audit **every** A-roll frame for centring after any camera note; a timed note about a transition → check the hidden-cut cover and pre-roll; "looks AI" → swap the B-roll beat (real footage / 3D / rebuilt UI); an SFX note → `hf_mix --report` and the audio-only branch; a bed "about 4 dB lower" is a mix note (remux) when the project was built with `hf_mix` |
| **testimonial** | a note that changes a claim goes through the **claims table** first; never alter a proof screenshot to satisfy a note; a re-order is logged with "still true in the new context" |
| **ad-promo** | an offer/price/legal note updates the **copy source of truth** and every output (hook variants and ratios) — the manifest check (wf-08) catches a stale derivative |
| **motion-graphics** | a camera/transition note adds a **row to the clean-smooth table** (so the next critic scores like the author); a timed note at a seam → check exit = entry vector and the hero persistence |
| **ai-generated** | "looks AI" at a timestamp → replace the shot or cover it; a regenerated shot is a **new 💲 approval**; one grade + grain across new takes |
| **podcast-clip** | a layout/speaker-switch note → re-check hysteresis; a clip that no longer stands alone → back to the selection table |

## 10. Time labels

Owner target: present 5 min; note round ≤ 45 min with one full render. Machine-time numbers: E12 (OM, synthetic). Human review time: **unmeasured**.

(src: distilled/02 workflow §9, §12; distilled/01 G1–G10; research E12 — read 2026-10-02.)

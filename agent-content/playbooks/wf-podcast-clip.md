# wf-podcast-clip — Clips from a long conversation (קליפים מפודקאסט)

> Status: **provisional** — the author has a selection method and measured ASR speeds but **no owner rubric** for this type; the type rubric in [../benchmarks/podcast-clip.rubric.md](../benchmarks/podcast-clip.rubric.md) is derived and weak. Specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §7, distilled/02 podcast-clip notes, distilled/03 E08.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[IDEA]` · `[CONFLICT]` · 💲 = paid step · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | a variant of stages 1–8 for one long source → N short clips |
| Owner skill | `talking-head-editor` (cuts/captions), `hebrew-captions-transcription`, `render-qa-delivery`; selection is this playbook |
| Artifacts (exact files) | `projects/<name>/_work/proxy.mp4` (low-res proxy), `_work/transcript.json` (whole episode), `_work/selection.md` (the selection table), `_work/reframe_plan.json` (per clip: mode per span), one `projects/<name>_clip<k>/` per chosen clip, `final/<name>_clip<k>_<platform>_<aspect>.mp4` |
| Exit gate | **GP — chosen clips only are built; each passes the stand-alone gate and wf-06; the rubric result is labelled provisional** |
| Target time | **not measured** — clip lengths seen by the author ran from 54 s to 3.3 min (a range, not a target) |
| Paid steps | optional hosted reframe 💲 (Higgsfield reframe): dated estimate + approval; the core path uses local face tracking (free) |

## 1. Principle

**Choose before editing, and the person chooses.** The agent proposes a scored table of candidate clips; the person picks; only then is a clip built. A clip that cannot stand alone (needs the earlier minutes to make sense) is rejected whatever its energy. `[RULE-owner]`

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| the source file exists and the person confirmed rights to use it (the host and guest content is theirs or licensed) | an intake ledger row (RIGHTS) | ask; a rights shortcut such as "unknown = organic only" has **no verified legal basis** `[CONFLICT]` (the research baseline AQ005) — record it as the person's own risk decision, never as a rule |
| intake answered: platform(s), clip length range, language, hook style, caption style, profile (dry or hyped) | ledger rows | ask in rounds of 3–4 ([question-bank](../techniques/question-bank.md)) |
| disk space for a proxy and the transcript | `doctor` | free space |

## 3. Steps

| # | Step | Who | Evidence |
|---|---|---|---|
| 1 | **Minute 0, in parallel (see the schedule in [wf-00-intake.md](wf-00-intake.md)):** make a **low-resolution proxy** and extract audio; start the **whole-episode ASR** in the background under `render_lock` (heavy job). E08: CTranslate2 int8 on CPU ran 0.84 audio-s per wall-s on a 614 s corpus on OM (single pass; other hardware unmeasured). The author's "x2.3" figure equals **0.435 audio-seconds per wall-second** — compare in the same unit (timing-ledger rule). | agent | `_work/proxy.mp4`, `_work/transcript.json`, a ledger row with units |
| 2 | **Segment the transcript** into candidate spans (topic shifts, question → answer pairs, story arcs). Do not cut on silence alone. | agent | `_work/candidates.json` |
| 3 | **Score each candidate** with the selection table (§4); apply the **stand-alone gate**: a score below 4 of 10 on stand-alone = **reject**. Show the top candidates with start/end timestamps and a one-line reason. | agent | `_work/selection.md` |
| 4 | **The person chooses** the clips (and may reorder, trim or reject). Nothing is edited before this. | person | the choice recorded in `selection.md` |
| 5 | **Per clip: PROMPT.md** (frame-spec, see [frame-spec-prompt](../techniques/frame-spec-prompt.md), a footage edit-spec) with the ledger: hook line in the first 3 s, closed ending, caption style, reframe plan. Approved before code. | agent + person | G3 per clip |
| 6 | **Reframe plan** (§5): per span choose TRACK / SPLIT / GRID / GENERAL; hysteresis; dead zone. `face_center` + `camera_path` produce the keys; check with `face_center audit`. | agent | `_work/reframe_plan.json`, audit report |
| 7 | **Captions:** Hebrew-tuned transcript for the clip, the caption rail ≤ y 1450, speaker-colour captions when two or more people talk (colour = person, constant per episode); `caption_qa` after the draft. | agent | the layout manifest; `caption_qa` envelope |
| 8 | **Profile:** dry (calm, few effects) or hyped (punch-ins, faster pace, kinetic keywords) per the ledger; the pace numbers are house heuristics, see the rubric. | agent | ledger rows |
| 9 | **Studio-first review**, then ONE full render per round, then every-frame QA on the final (wf-06). | agent | per-clip G6 |
| 10 | **Deliver** per clip with manifest; the clips of one episode share the naming stem. | agent | `final/manifest.json` |

## 4. Selection table (per candidate)

| Criterion | Question | Score | Gate |
|---|---|---|---|
| stand-alone | does it make sense with zero context from the episode? | 0–10 | **< 4 = reject** |
| hook in 3 s | is there a line in the first 3 s that makes a stranger stay? (a question, a claim, a surprise) | 0–10 | below 4: re-cut the start or reject |
| closed ending | does it end on a finished thought (not mid-sentence, not on "so..." )? | 0–10 | below 4: trim or extend |
| arc | does something change between start and end (a claim → proof, a question → answer)? | 0–10 | informational |
| energy / clarity | audio clean, speaker present, no long off-topic tangent | 0–10 | informational |
| risk | any statement that is a medical/legal/financial claim, a third party's private detail, or a rights problem? | flag | a flag blocks until the person decides |

The score is the **agent's proposal**; the person's pick wins (owner taste rules). Weights are `[IDEA]` — the author's selection was by judgement, not by a weighted formula.

## 5. Reframe modes `[RULE-owner]` (thresholds are house heuristics)

| Mode | When | Rule |
|---|---|---|
| TRACK | one speaker is on screen and talking | follow the face with the speaker camera rig ([clean-smooth-motion](../techniques/clean-smooth-motion.md) §speaker camera) |
| SPLIT | two people, both visible, alternating | a stacked 2-up layout; the active speaker larger; no jump cuts between layouts inside a sentence |
| GRID | three or more people | a grid of faces; the active speaker highlighted |
| GENERAL | no usable face (screen share, B-roll) | a fixed or very slow framing; never a random crop |

Switching rules:
- **Hysteresis ≥ 1.5 s** — a mode or speaker switch is allowed only after the new state has held for 1.5 s (no flicker on interjections).
- **~10 % dead zone** — the camera does not move for a face drift inside ~10 % of the frame; then it moves with the snap-then-drift grammar.
- After a switch, the next switch is not allowed for at least the hysteresis time.
- A person's override beats the automatic choice; record it in `reframe_plan.json` (`override: true`).

Numbers: hysteresis and dead zone are the author's values (dated 2026-09 in the source), not measured on a corpus; limit: tested on one kind of two-person conversation only.

## 6. Dry vs hyped profile

| | Dry | Hyped |
|---|---|---|
| pace | the speaker's own; cut only dead air and false starts | tighter: remove breaths, punch-ins on emphasis |
| captions | calm, 1–2 lines, the key word emphasised sparingly | kinetic keywords, bigger emphasis |
| motion | none beyond the camera rig | punch-ins at the phrase boundaries (not mid-word), subtle zoom |
| sound | -14 LUFS / TP ≤ -1 (house preset) | the same loudness; a music bed only if the ledger asks, ducked under speech |
| risk | looks flat | looks cheap if every second has an effect — the rubric's motion dimension penalises noise |

## 7. Exit gate GP

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| every built clip is in the person's chosen list | `selection.md` choice vs `projects/*_clip*` | else `fail` |
| each built clip scored ≥ 4 on stand-alone; hook ≤ 3 s; closed ending | `selection.md` scores; the clip's first 3 s frame review | else `fail` |
| each clip passed wf-06 (every frame, loudness, captions, audio) | per-clip `_work/qa/` envelopes | else `fail` |
| speaker-colour captions consistent across the episode | `caption_qa` + the colour table | else `warning` |
| rubric result recorded **as provisional** (`podcast-clip.rubric.md`) | the retro table | else `warning` |
| any hosted reframe stayed within the dated estimate | the ledger credits | overspend = `fail` |

Gate record → each clip's `hf/QA.md` "Gate log".

## 8. Human vs agent

| Human | Agent |
|---|---|
| confirms rights; picks the clips; overrides a speaker/mode choice; approves each PROMPT.md and any paid reframe | proxy and ASR at minute 0; candidates and the scored table; the reframe plan; captions; QA |

## 9. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| a clip needs earlier context | the stand-alone gate skipped | reject or re-cut with a one-line lead-in card | step 3 gate |
| the camera flickers between two speakers | no hysteresis | enforce ≥ 1.5 s | §5 |
| captions in one colour for two voices | no speaker diarisation | colour table per speaker; check the first frame of each speaker | step 7 |
| ASR on the CPU took the whole afternoon | no GPU lane planned | start at minute 0 on the GPU under the lock; compare units | step 1 |
| a clip ends mid-thought | the end was chosen by time | extend to the next full stop | selection table |
| a hyped profile on a calm interview | the profile was not asked | ask at intake | entry gate |

## 10. Tool invocations

`transcribe` (whole episode, proxy audio) · `source_cuts` · `face_center source|audit` · `camera_path` · `hf_preflight` · `hf_segment` (when a cut-out is needed) · `hf_deliver` · `frame_qa` · `caption_qa` · `motion_qa` · `sheet` · `ledger` · `render_lock`. A hosted reframe 💲 goes through paid-spend-gate. Flags are schematic; see `docs/TOOLS.md`.

## 11. Per-type deltas

This **is** a type. Relative to the talking-head playbook: selection comes first; several clips share one source; speaker-aware reframe is the main craft; the rubric is provisional.

## 12. Time labels

Owner target: none stated (clips 54 s – 3.3 min). Modelled: none. Measured: E08 ASR speeds on OM only (one corpus). No end-to-end time per clip exists.

(src: blueprint WORKFLOWS §7; distilled/02 podcast-clip notes; distilled/03 E08 — read 2026-10-02.)

# Playbooks — the gated pipeline (תהליך העבודה)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02. Source pointers (`src:`) in these files refer to the research baseline read on that date; they are provenance, not links you can follow in this repository.
> Reference machine (OM) = one Windows laptop; hardware details are intentionally not published. NVIDIA, Apple and Linux numbers are **unmeasured**. Prices, model ids and versions are perishable.

A playbook is the **procedure** for one stage: entry gate, steps, artifact, exit gate with evidence, who does what. The owning **skill** is the entry point the agent loads (`video-request-router` picks it); the playbook is what the skill follows. Tool flags in playbooks are **schematic**; the exact flags live in `docs/TOOLS.md`.

## 1. Legend

| Mark | Meaning |
|---|---|
| `[RULE-owner]` | the author's rule; wins on taste |
| `[PROVEN-internal]` | observed in the author's own projects; not a standard |
| `[IDEA]` | a proposal, untested |
| `[CONFLICT]` | two sources disagree; the text says which was taken and why |
| `[PERISHABLE]` | price/model/version/URL; re-check before use |
| 💲 | a paid step; only through `paid-spend-gate` with a dated estimate and prior approval |
| OM | the reference machine above |
| gate states | `pass` · `fail` · `warning` · `blocked` · `not_run` · `n/a` (needs a reason). A gate that cannot run is `not_run` / `INSUFFICIENT_EVIDENCE`, **never `pass`** |

## 2. Pipeline table

| Stage | Playbook | Owner skill | Artifact (exact) | Exit gate | Human / agent | Target time (labelled) |
|---|---|---|---|---|---|---|
| 0 | [wf-00-intake](wf-00-intake.md) | `pro-video-editor` Step 0 (+ `video-brief-intake`) | `hf/PROMPT.md` `<ledger>`, `hf/BRIEF.md` | **G0** ledger locked | person answers rounds of 3–4; agent asks and writes rows | 10–20 min (owner target) |
| 1 | [wf-01-references](wf-01-references.md) | `reference-style-matching`, `video-analysis`, `visual-choice-board` | `hf/STYLE_DNA.md` or `hf/references/MOODBOARD.md` | **G1** option and time range picked | person picks; agent analyses and shows 3 options | 15–30 min (owner target) |
| 2 | [wf-02-concept](wf-02-concept.md) | `video-brief-intake` + `pro-video-editor` | `hf/CONCEPT.md`, `hf/SCRIPT.md` | **G2** concept picked, script/paper edit approved, no render | person picks; agent proposes three | 20–40 min (owner target) |
| 3 | [wf-03-prompt](wf-03-prompt.md) | `pro-video-editor` | `hf/PROMPT.md`, `hf/DESIGN.md`, four stills | **G3** human approved before any code | person approves; agent drafts | 30–40 min (owner target) |
| 4 | [wf-04-assets](wf-04-assets.md) | `speaker-color-correction`, `captions-transcription`, `paid-spend-gate` | `hf/assets/`, `hf/fonts/`, `hf/SOURCES.md`, `hf/data/*` | **G4** assets in, licensed, measured; paid only with approval | agent builds; person approves spend | 60–90 min, parallel with stage 5 (owner target) |
| 5 | [wf-05-build](wf-05-build.md) | `pro-video-editor` + HyperFrames skills | `hf/index.html`, `hf/compositions/*`, `hf/cues.js` | **G5** `hf_preflight --strict` 0 errors | agent | ≈ 90 min; first draft within 4 h (owner targets) |
| 6 | [wf-06-render-qa](wf-06-render-qa.md) | `render-qa-delivery` | `_work/drafts/…`, `_work/qa/<ver>/`, `hf/QA.md` | **G6** 0 flags, rubric ≥ 4.0, no dim < 3 | agent renders once and checks; critic is a separate process | 30–45 min (owner target; machine stages measured on OM) |
| 7 | [wf-07-revise](wf-07-revise.md) | `revision-notes-handler` | message, `CHANGELOG.md` round, patch script | **G7** approved or notes in | person reviews; agent applies notes with ONE full render | present 5 min; round ≤ 45 min (owner target) |
| 8 | [wf-08-deliver](wf-08-deliver.md) | `render-qa-delivery`, `video-variants-exporter` | `final/<name>_….mp4`, `final/manifest.json` | **G8** `hf_deliver` pass on the FINAL file | agent; person receives | 15 min + one final render (owner target) |
| 9 | [wf-09-learn](wf-09-learn.md) | none (playbook step) | `_work/RETRO.md`, `projects/LESSONS.md` | **G9** retro + lesson lines + timing summary | agent writes; person approves rules | 15 min (owner target) |
| — | [wf-variants](wf-variants.md) | `video-variants-exporter` | `hf_<ratio>/`, per-output files | **GV** all variants from the frozen master | agent; person names the matrix at intake | not measured |
| — | [wf-batch](wf-batch.md) | `video-request-router` + queue | `BATCH.md`, `_shared/` | **GB** each video has its own record | agent supervises; person approves each prompt | not measured |
| — | [wf-podcast-clip](wf-podcast-clip.md) | selection here + `pro-video-editor` | `_work/selection.md`, per-clip projects | **GP** chosen clips only, stand-alone ≥ 4 | person chooses clips; agent proposes | not measured; rubric provisional |
| — | [wf-screen-demo](wf-screen-demo.md) | `pro-video-editor` + zoom/dead-time/cue steps here | `_work/zoom.json`, `_work/promise.json`, the draft | **GS** every narrated action visible and readable, no dead time, no cue miss | person records the screen and approves; agent cuts, zooms, checks | not measured; rubric borrowed, provisional |

"Owner target" = the author's stated target for a premium project; "modelled" = computed from measurements; "measured" = timed on OM. A target is **not** a measured student result.

## 3. Gate chain

`G0 → G1 → G2 → G3 → (G4 ∥ G5) → G6 → G7 ⟲ (notes → G5/G6) → G8 → G9`. No stage starts before the previous gate is recorded `pass` (or `n/a` with a reason). G4 and G5 run in parallel. G3 is the hard stop: nothing is coded before the person approves PROMPT.md and DESIGN.md.

### 3.1 Gate record format

Every gate is logged in `projects/<name>/hf/QA.md` under "Gate log":

| gate | state | evidence | by | UTC |
|---|---|---|---|---|
| G3 | pass | `hf/CHANGELOG.md` "Approval" entry with `approved_sha256` | human (the person) | 2026-10-02T09:14Z |

Rules: `pass` requires **resolvable evidence** (a file path, a command and its output, a sha256) — a sentence is not evidence; `n/a` requires a reason; a gate that could not run is `not_run`, not `pass`. "By" is the human for G1, G2, G3, G7 and the agent or tool otherwise. A gate is never edited after the fact; a re-run is a new line.

## 4. Never-break rules (owner rules, stated once in AGENTS.md; applied in every playbook)

1. intake until precise · 2. PROMPT.md approved before the first line of code, also in autonomous runs · 3. a paid action needs prior approval with a dated estimate · 4. one heavy job at a time (render lock) · 5. one full render per round (Studio first) · 6. every-frame QA on the FINAL render; a gate that cannot run is `not_run` · 7. HyperFrames: no `dir="rtl"` on the root, fonts from files, `snapshot --describe false`, ≤ 5 timestamps per call · 8. ASCII work root · 9. never message other Claude sessions.

`[CONFLICT]` (recorded where it occurs, e.g. in the wf-03/wf-05 files): the research baseline measured a render with `dir="rtl"` on the root that did **not** go black on one HyperFrames version (0.8.98); the author rule is kept anyway because it was learned from black renders on other versions. Re-verify per version before relaxing it.

## 5. Routing by type

| The person's request is | Type | Rubric | Playbook deltas |
|---|---|---|---|
| a person talking to camera, edited | talking-head | [talking-head.rubric.md](../benchmarks/talking-head.rubric.md) (derived, provisional) | "Per-type deltas" in each file |
| client or customer story | testimonial | [testimonial.rubric.md](../benchmarks/testimonial.rubric.md) | same |
| a paid ad or promo | ad-promo | [ad-promo.rubric.md](../benchmarks/ad-promo.rubric.md) | same |
| built from type, shapes, product UI | motion-graphics | [motion-graphics.rubric.md](../benchmarks/motion-graphics.rubric.md) | same |
| made of generated clips | ai-generated | [ai-generated.rubric.md](../benchmarks/ai-generated.rubric.md) | same |
| short clips from a long conversation | podcast-clip | [podcast-clip.rubric.md](../benchmarks/podcast-clip.rubric.md) (provisional) | [wf-podcast-clip.md](wf-podcast-clip.md) |
| a screen recording made into a demo or tutorial | screen-demo | none of its own: the closest of [motion-graphics.rubric.md](../benchmarks/motion-graphics.rubric.md) / [talking-head.rubric.md](../benchmarks/talking-head.rubric.md), labelled provisional | [wf-screen-demo.md](wf-screen-demo.md) |

## 6. The two protocols every project uses

| Protocol | Where it is written |
|---|---|
| **Parallel schedule** — what starts at minute 0 (proxy, ASR, asset fetch, analysis), what waits for G3, resource admission (1 heavy job; ≤ 24 GB; ≤ 8 threads, `unmeasured` ceilings) | [wf-00-intake.md](wf-00-intake.md), section "parallel schedule" |
| **Long-job protocol** — benchmark one unit, print an ETA line, set a timeout, run in the background with a log and `STATE.md`, heartbeat ~5 min, watchdog (0 frames after 3 min / no progress 10 min), keep partial results | [wf-06-render-qa.md](wf-06-render-qa.md), section "long-job protocol" |

## 7. Techniques and benchmarks used by the playbooks

Techniques: [../techniques/README.md](../techniques/README.md) (frame-spec prompt, clean-smooth motion, screenshot rebuild, concept ledger, question bank, caption collision, cheap-first QA, Studio review loop, timing ledger, DESIGN/BRIEF templates). Benchmarks: [../benchmarks/README.md](../benchmarks/README.md) (six rubrics, `bands.json`, critic brief, four-axis visual review, briefs B01–B06).

## 8. Cross-references assumed to files owned elsewhere

Written in backticks (not links) because other builders own them: skills `video-request-router`, `video-brief-intake`, `reference-style-matching`, `video-analysis`, `edit-*`, `speaker-color-correction`, `captions-transcription`, `render-qa-delivery`, `revision-notes-handler`, `paid-spend-gate`, `video-prompt-writer`, `visual-choice-board`, `video-variants-exporter`; references `agent-content/references/platform-specs.md`, `talking-head-beats.md`, `qa-thresholds.md`, `model-routing.md`, `cost-model.md`; `docs/TOOLS.md`. Path proposals owned by this directory: the ledger lives inside `hf/PROMPT.md` `<ledger>`; the timing ledger is `_work/timing_ledger.jsonl`; lessons go to `projects/LESSONS.md` and `projects/RULES.md` (outside `agent-content/`).

## 9. Honest status

Everything here is specified and checked deterministically (links, tables, the ledger checker, the collision solver arithmetic). No playbook has been run end to end on a student by a model eval (decision default Q4); the worked example in the frame-spec technique is arithmetic-checked, not built. Timings are labelled owner target, modelled or measured on OM only.

# wf-batch — Many videos at once (עבודה בכמויות)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §6, distilled/01 rules-and-gates (L1–L6, resource rules), distilled/03 time sinks (E08/E09/E11), distilled/02 podcast-clip notes.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[IDEA]` · `[CONFLICT]` · 💲 = paid step · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | wraps stages 0–9 for N videos; not a stage of its own |
| Owner skill | `video-request-router` (routes), `video-variants-exporter` (shared design), `render-qa-delivery` (queue) |
| Artifacts (exact files) | `projects/<name>_<k>/` one folder **per video**; `projects/<batch>/_shared/` (assets and design built once); `projects/<batch>/BATCH.md` (the table of videos, owner agent, state, deadline); `_work/agents/<agent>.progress.md` per agent; the machine-wide lock |
| Exit gate | **GB — every video has its own G0–G9 record; shared assets are verified once; no two heavy jobs overlapped** |
| Target time | **not measured** (no owner target; E12 covers a single project only) |
| Paid steps | one approval **per batch of generations** with a dated estimate (see paid-spend-gate); a batch never inherits approval from one clip to the next |

## 1. Principle `[RULE-owner]`

**One project per video. Build in parallel; heavy work in ONE queue for the whole machine.** The batch is a scheduler over independent projects, not one giant project. Shared things (a design system, a logo cut-out, a font file, a music bed) are built **once** in `_shared/` and **copied by hash** into each project, so a change is a deliberate re-copy, not a hidden edit.

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| each video has its own intake (wf-00) — a batch does not share a Concept Ledger | `projects/<name>_<k>/hf/PROMPT.md` `<ledger>` per video | run intake per video; the shared part is only what the ledgers state identically |
| the **batch table** exists: video, type, owner agent, deadline, state | `BATCH.md` | write it |
| the resource plan is written: one heavy job at a time; memory ≤ 24 GB; threads ≤ 8 (`unmeasured` as a ceiling — an owner heuristic, not a measured limit on any other machine) | `BATCH.md` header | write it; if the machine is smaller, lower the numbers |
| `doctor` was run once for the machine | `_work/doctor.txt` | run it |

## 3. Steps

| # | Step | Who | Evidence |
|---|---|---|---|
| 1 | **Intake per video**, in sequence, with the person. One intake round (3–4 questions) per video, shared questions asked once and recorded in every ledger. | agent + person | per-video ledgers |
| 2 | **Build `_shared/` once:** fonts as files, palette, a logo cut-out, the caption layout, one reference approval. Hash each; copy into every project (`sha256` recorded in each `CHANGELOG.md`). | agent | `_shared/HASHES.txt` |
| 3 | **PROMPT.md per video approved before code** (never-break rule, also in autonomous runs). A batch is **not** a reason to approve in bulk without reading: each prompt gets its own approval record. | person | per-video G3 |
| 4 | **Schedule** with the parallel table (wf-00 §parallel schedule): things that need no GPU (intake, prompts, asset fetching that is free, transcripts on an idle GPU lane) run in parallel; **renders, heavy ASR, segmentation and any generation run through `render_lock`** in the order written in `BATCH.md`. | agent | the lock log |
| 5 | **Agent supervision table** (§4): every agent gets an explicit file list, an output file, a clock deadline, a progress file, and a heartbeat. ≤ 4 agents, each ≤ 2 sub-agents. | agent | `BATCH.md` agent table |
| 6 | **Long jobs** follow the long-job protocol in [wf-06-render-qa.md](wf-06-render-qa.md) (benchmark one unit, ETA line, timeout, background log, heartbeat, watchdog). A batch **multiplies** the rule: the protocol applies per job and the queue shows the total ETA. | agent | `_work/STATE.md` per project and a batch STATE |
| 7 | **QA per video** — wf-06 in full on each final render (every-frame QA is **not** sampled across the batch); the critic is a fresh process per video. | agent | per-video envelopes |
| 8 | **Deliver per video** (wf-08) with its own manifest; a batch summary table lists the states. | agent | `final/` per project; `BATCH.md` |
| 9 | **Learn once for the batch** (wf-09): one retro for the batch plus one lesson line per distinct surprise; a lesson seen in several videos has its **count raised**, not duplicated. | agent | `RETRO.md` |

## 4. Agent supervision table `[RULE-owner]` `[PROVEN-internal]`

| Field | Rule |
|---|---|
| file list | explicit paths the agent may read **and** write; nothing else; an agent touching a file outside its list is a defect |
| output file | one file per agent; the reply to the orchestrator is ≤ 10 lines and points at it |
| deadline | a **wall-clock** time (UTC) written in the brief, not "when done" |
| progress file | `_work/agents/<name>.progress.md`, appended as it goes; the orchestrator reads it, not the transcript |
| heartbeat | the orchestrator checks every ~15 minutes (agents) / ~5 minutes (a single render job); no new line in the progress file for two checks = suspect |
| caps | ≤ 4 agents, each ≤ 2 sub-agents (usage-limit stops of several hours were seen when more ran; owner experience, no measured threshold) |
| stopping | kill the **process tree** (the agent's headless browser and encoder children included), then check `render_lock status`; a stale lock is cleared only by the tool, never by deleting its file |
| other sessions | **never message other Claude sessions**; if another session is active on the machine, queue behind its lock and tell the person |
| money | an agent never spends; paid steps stay with the orchestrator and the person (paid-spend-gate) |

## 5. Token and attention budget `[IDEA]`

| Rule | Why |
|---|---|
| the orchestrator reads progress files and `QA.md` summaries, not whole transcripts or logs | context is the scarce resource in a batch |
| each agent returns ≤ 10 lines | the detail is in its file |
| one `STATE.md` per project and one batch state; a restart reads them first | a resumed session must not redo finished work |
| heavy review artefacts (contact sheets) are made once per version and reused | wasteful repeats are the main cost |

(`[IDEA]` — owner-experience guidance; no token measurement exists.)

## 6. Many clips from one source (e.g. a long recording)

| Step | Rule |
|---|---|
| transcribe the whole source **once** (proxy audio, whole-file pass; E08: CTranslate2 int8 on CPU ran 0.84 audio-s per wall-s on one 614 s corpus on OM — single pass; other hardware unmeasured) | one transcript feeds every clip |
| the person **picks** the clips from a selection table before any editing (see [wf-podcast-clip.md](wf-podcast-clip.md)) | no clip is built that nobody chose |
| shared design in `_shared/`; each clip is a project or a sub-composition with its own ledger, own render, own QA | clips differ in content, not in house style |
| ONE render queue; clips render in the planned order | E11: two workers were faster than one by 14 % and eight by 34 % **on one 3-minute render on OM** (132.6 → 113.5 → 92.8 → 88.1 s for 1/2/4/8 workers); this is a single measurement, not a batch schedule |

## 7. Exit gate GB

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| each video has a G0–G9 record (or a recorded stop) | each project's `hf/QA.md` "Gate log" | else `fail` |
| shared assets have hashes and every project's copy matches | `_shared/HASHES.txt` vs each project | else `fail` |
| no overlapping heavy jobs | `render_lock` log | else `warning` |
| every agent had a file list, deadline and progress file | `BATCH.md` | else `warning` |
| spend ≤ approved estimate per batch of generations | `_work/timing_ledger.jsonl` credits vs the dated estimate | overspend = `fail` and stop |
| no message was sent to another session | the session record | else `fail` |

Gate record → each project's `hf/QA.md`; the batch summary in `BATCH.md`. A video whose gate cannot run is `not_run`, **never** `pass`.

## 8. Human vs agent

| Human | Agent |
|---|---|
| approves each PROMPT.md, each paid estimate, each selection; decides the order if two videos compete | schedules, supervises, queues renders, keeps ledgers, runs QA, writes the batch table |

## 9. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| two renders fight for the GPU, both slow or crash | no queue | `render_lock`; one at a time | step 4 |
| a shared logo edited in one project only | hidden fork | re-copy from `_shared/` by hash | step 2 |
| one video's note "fixes" another's | shared ledger | separate ledgers | entry gate |
| an agent edits a foreign file | no file list | revert; restate the list | §4 |
| a stale lock blocks the queue | crashed holder | `render_lock status`; tool-managed release | §4 stopping |
| a batch spends past the estimate | approval inherited | stop; re-estimate; ask again | paid steps row |
| QA sampled because there are many videos | time pressure | not allowed: every-frame QA on **each** final | step 7 |

## 10. Tool invocations

`new_project` per video · `render_lock status|run` · `doctor` · `transcribe` (whole source, once) · `hf_preflight` · `hf_segment` · `hf_deliver` · `frame_qa` · `caption_qa` · `ledger` · `sheet` · `benchmark`. Tool flags are schematic; the exact flags are in `docs/TOOLS.md`.

## 11. Per-type deltas

| Type | Delta |
|---|---|
| talking-head | one transcript pass per source; per-video camera/captions; the Hebrew caption rules apply to each |
| testimonial | a multi-client supercut is **its own project**; the proof table is per client; never share a claims row |
| ad-promo | the licence rows are per video; hook variants belong to [wf-variants.md](wf-variants.md), not to the batch |
| motion-graphics | a shared design system (DESIGN.md) built once; the three tables per video |
| ai-generated | generation approvals per batch with a dated estimate; native fps preserved; disclosure rows per video |
| podcast-clip | one source, many clips: [wf-podcast-clip.md](wf-podcast-clip.md) |

## 12. Time labels

Owner target: none stated. Modelled: none. Measured: E11 (one render, workers 1/2/4/8) and E08 (one ASR corpus), both on OM, both single measurements; no batch has been timed.

(src: blueprint WORKFLOWS §6; distilled/01 rules-and-gates; distilled/03 E08/E09/E11 — read 2026-10-02.)

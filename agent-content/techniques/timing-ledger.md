# Technique: the timing ledger

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from research T24 (TIMING_LEDGER_SPEC, STAGE_BUDGETS), distilled/03 time-sinks §7–§8, blueprint TOOLS_SPEC §1 item 9 and §3 item 15, WORKFLOWS §7.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[IDEA]` · `modelled` = arithmetic on assumptions, not a measurement.
> Not to be confused with the **concept ledger** ([concept-ledger.md](concept-ledger.md)).
> OM (the reference machine) = one Windows laptop; hardware details are intentionally not published.

## 0. Why

Every video writes its own timing ledger so the student (and the course) can see **where time and credits actually went** instead of trusting the owner's modelled budgets. The biggest measured waste was work that should not have happened (≈ 14 of ~23 full renders in one premium test), not slow tools — a ledger makes that visible: *full renders per round (target 1)*, queue wait, setup, human active vs blocked time, retries, credits. `[PROVEN-internal]` (src: distilled/03 §0)

**Unknown = `null`, never `0`.** An unmeasured GPU use or an unavailable price is `null`; "zero metered cash" is not "zero total cost".

## 1. The stream

One **JSONL** file per project and immutable attempt: `projects/<name>/_work/timing_ledger.jsonl` (one JSON object per line; append-only; failed and cancelled attempts count). Long-running tools write their own lines (TOOLS_SPEC §1 item 9); human and agent stages append a line when they start/end. The tool name is `ledger` (`ledger add …`, `ledger summarize` — flag names are fixed by `docs/TOOLS.md`; examples below show fields, not CLI syntax). Contract schema: `contracts/` (timing-ledger schema).

**Required fields per line:** `schema_version`, `project_id` (anonymous), `attempt_id`, `stage_id`, `dependency_ids`, `parent_id` (nested spans), `machine_profile`, `executor` (`claude` / `codex` / `user` / `worker`), `model`/`provider`/`version` where relevant, `tool_version`, `input_hashes`, `settings_hash`, UTC `start`/`end`, monotonic `mono_start`/`mono_end`, `status`, `cache` (`cold` / `warm` / `hit`), `reason`.

**Duration fields (seconds):** `queue`, `install`, `download`, `import`, `load`, `decode`, `infer`, `encode`, `upload`, `remote_queue`, `remote_compute`, `poll`, `qa`, `human_active`, `human_wait`, `correction`, `retry`.

**Throughput fields:** `audio_seconds`, `wall_seconds`, `throughput = audio_seconds / wall_seconds` (**audio-seconds per wall-second**, never "×N real time" — the owner's "x2.3 real time" was ambiguous), `processing_ratio = wall_seconds / audio_seconds`, `output_frames`, `inference_frames`, `output_seconds`, `accepted_seconds`, `seconds_per_frame`, `seconds_per_output_second`, WER/CER/timestamp error where measured, a quality acceptance flag.

**Cost fields:** pricing date/currency/plan, charged units, minimum/rounding rules, credits consumed, tokens and cache tokens, actual charge or `null`, rejected attempts, energy/labour if measured. Credits, API dollars and invoice cash are **separate wallets**.

**Resources:** CPU threads, peak RSS, VRAM allocated/resident (`null` if unknown), free RAM/VRAM before/after, GPU compute vs encoder use, concurrent stage ids, telemetry interval.

### 1.1 Example lines (synthetic; field subset)

```json
{"schema_version":"0.1","project_id":"p-7f3a","attempt_id":"a1","stage_id":"wf-06.full_render","executor":"worker","tool_version":"hf_deliver 0.1.0","start":"2026-10-02T09:14:02Z","end":"2026-10-02T09:24:51Z","status":"PASS","cache":"cold","durations":{"queue":0,"encode":null,"qa":null},"output_frames":1200,"seconds_per_frame":0.54,"full_render_round":3}
{"schema_version":"0.1","project_id":"p-7f3a","attempt_id":"a1","stage_id":"wf-07.human_review","executor":"user","start":"2026-10-02T09:30:00Z","end":"2026-10-02T09:41:30Z","status":"done","durations":{"human_active":690,"human_wait":null}}
{"schema_version":"0.1","project_id":"p-7f3a","attempt_id":"a1","stage_id":"wf-04.paid_generation","executor":"claude","status":"approved_estimate_only","cost":{"price_date":"2026-10-02","currency":"USD","charged_units":null,"actual_charge":null,"approval_msg":"chat#41"}}
```

(All values invented for illustration.)

## 2. Rules

1. **No double counting:** nested spans carry `parent_id`; overlapping spans are not summed as project elapsed.
2. **Elapsed** = intake to accepted artifact; **critical path** from actual timestamps/DAG; **summed worker seconds**, **human active** and **human blocked** reported separately.
3. **Compare equal quality and brief coverage.** A cloud route's speed includes upload + queue + download + correction; two routes of unequal quality are not a speedup comparison.
4. **Unit discipline:** state the timer boundary (launch→finalize vs outer wrapper incl. interpreter start-up vs model-load-excluded), load on the machine, corpus and "single pass or n". An unlabeled ratio is not a result. (E08 lesson: raw tool seconds vs wrapper seconds differ.)
5. **Cache lookups cost time:** a cache hit still has lookup + decode + QA cost; a hit can lose to recompute. Reuse only when the proven critical path shrinks. Cache key = decoded media identity/ranges/time base + source/model/tool/config/font hashes + seed + backend + colour space + alpha convention.
6. **Publish atomically** only validated complete outputs; keep failed-stage evidence.
7. **Missing clock fields rejected; negative durations rejected; units explicit; cancelled and failed attempts counted; cache keys invalidate after font/model/range/colour change; every emitted number traces to immutable raw evidence.** (T24 acceptance of the ledger itself)

## 3. ETA and heartbeat (feeds the long-job protocol)

- After **one representative unit**: `ETA = fixed_startup + remaining_units × warm_median`, with an uncertainty range from the samples, thermal state and contention. Do not benchmark a short easy unit and extrapolate over a different scene complexity.
- A heartbeat at a bounded interval carries: completed units, current phase, elapsed, ETA range, resource reservation, cancellation state (a heartbeat is not an extra model call). The owner's protocol: ≈ every 5 minutes, status line to the person every 5–10 minutes.
- Existing minimal precedent: `render_lock.log` (JSONL `job, project, wait_s, run_s, end`).

## 4. Resource admission (proposal, **unmeasured** policy `[IDEA]`)

For a 32 GB machine: keep 8 GB OS/UI headroom; admit ≤ 24 GB summed predicted working set (tightened by measured free memory); default **one heavy compute job**; ≤ 8 physical-core compute threads pending E11-style tuning; GPU reservation includes compositor/UI margin (the one reference machine's 8 GB is nominal, not free); stop admission before paging/VRAM eviction; cold unknown jobs run alone; reserve before spawning, release on **process termination** (not tool timeout). Authoring/research agents may run in parallel with file hand-off; heavy jobs go through the lock. The owner's data show 2× slowdowns and silent stalls when heavy jobs overlap (a Blender run beside a render: 11.5 → 21.5 min on OM). (src: T24 TIMING_LEDGER_SPEC; distilled/03 §0, §8)

## 5. What to extract per project (the retro numbers)

`ledger summarize` should print: drafts rendered · **full renders per note round** (target 1) · critic rounds · owner-note rounds · hours to first passing draft · human active vs blocked minutes · queue wait · setup minutes · credits (by wallet) · retries · accepted seconds. Goal: **fewer rounds each project.** `[RULE-owner]` (src: distilled/02 workflow §11)

## 6. Modelled budgets (labelled — replace with the student's own ledger)

**Owner targets** (not measurements): first presentable draft within 4 h; ≤ 45 min per note round with exactly one full render; per-stage targets in the playbooks.

**Modelled stage budget — 40 s talking-head (AMD laptop; assumptions kept equal in both columns: intake 5, search 5, authoring 15, human review 10, QA 5 min; six 10-minute drafts; 10-minute final)** `modelled` `[IDEA]` (src: T24 STAGE_BUDGETS, 2026-10-01):

| Stage | Current (min) | Target (min) | Label |
|---|---:|---:|---|
| intake | 5 | 5 | planning assumption |
| ASR | 1.533 | 1.533 | 40 × 2.3 / 60; the measured fast route (whisper.cpp Vulkan, 9.78× the same build on CPU on OM, 614 s read-speech corpus, single pass) would be ≈ 0.12 min inference-only — cold start unmeasured |
| matte | 35 | 6.364 + H | 35 × 10/55 (matte only 8 s + 2 s handles of a 55 s plate); H = range decode/seek + state warm-up + refinement + extra QA, unmeasured |
| colour | 3 | 3 | internal baseline |
| asset search | 5 | 5 | planning |
| authoring | 15 | 15 | planning |
| human review | 10 | 10 | planning |
| draft renders | 60 | **0** | owner's review-loop decision (Studio) |
| final render | 10 | 10 | modelled median |
| QA | 5 | 5 | planning |
| **total** | **149.533** | **60.897 + H** (conservative **89.533 = −40.12 %**) | the ≥ 50 % target holds only if H ≤ 13.87 min **and** quality passes; NVIDIA and Apple cells unmeasured |

The historical 31.7 h / 23-render project is **not** a matched 40 s measurement. All 2× runtime and 50 % accepted-output achievements remain **OPEN** until the E09 (matte quality), E11/E12-style measurements are repeated on real projects.

## 7. Failure modes

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| a "3× faster" claim | unlabeled units or unequal quality | restate in audio-s per wall-s with boundary + load + n | §2 rule 4 |
| `0` where nothing was measured | missing value coerced | store `null` | schema check |
| a long job nobody noticed stalled | no heartbeat | heartbeat + watchdog | §3 |
| double-counted elapsed | parent and child summed | `parent_id`, critical-path report | §2 rule 1 |
| the person has to ask "what about the render?" | no ETA line | ETA + heartbeat (protocol failure is logged) | wf-06 long-job protocol |

(src: T24 TIMING_LEDGER_SPEC and STAGE_BUDGETS; distilled/03 §7–§8; TOOLS_SPEC — read 2026-10-02.)

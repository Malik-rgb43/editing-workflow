# wf-variants — Ratios, hook variants and platform versions (גרסאות)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §5, distilled/02 workflow-end-to-end §13 and §10.6, distilled/01 rules-and-gates A11, H3–H7, L1–L6.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[IDEA]` · `[SOURCED-unverified]` · `[PERISHABLE]` · `[CONFLICT]` · 💲 = paid step · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | runs **after** wf-06/07 approved the **master**, **inside** wf-08 |
| Owner skill | `video-variants-exporter` (+ `render-qa-delivery`) |
| Artifacts (exact files) | per ratio a **copy** of the project: `projects/<name>/hf_9x16/`, `hf_4x5/`, `hf_1x1/` (the master stays `hf/`); `_work/qa/<ratio>/<ver>/`; `_work/agents/<name>.progress.md`; `final/<name>_<platform>_<hook>_<aspect>.mp4` ×N; `final/manifest.json` |
| Exit gate | **GV — every requested output is rendered from the frozen master, QA'd per output, and the manifest is consistent** |
| Target time | **not measured** (the author stated none for variants; E12 did not cover them) |
| Paid steps | none by default; a hosted render of derivatives 💲 needs a dated estimate and approval |

## 1. Principle `[RULE-owner]` `[PROVEN-internal]`

**Building in parallel; heavy work in ONE queue for the whole machine; derivatives are made only from a frozen, checked master.** Every other ratio is a **full re-layout on a copy** — same `cues` file, same `mix.wav` — **never a crop**. Hook variants remux or re-parameterise a shared composition; they do not fork a project per hook.

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| the **variant matrix** exists as ledger rows (every ratio, platform, hook, "no music", "no captions", length; **which ratio is the master**) — asked at intake, not at the end (every axis not asked cost a rebuild; a Hebrew 16:9 request that arrived at delivery was dropped) | ledger rows VAR | ask now; write the rows; plan the copy |
| the **master** is approved (G7) and passed the **full** wf-06 (every frame, four axes, critic) | G6/G7 records | finish the master first |
| the master is **frozen**: its `src_hash` is recorded in `manifest.json` and nobody edits it without updating every derivative | the manifest header | freeze it |

## 3. Steps

| # | Step | Who | Evidence |
|---|---|---|---|
| 1 | **Freeze the master** — compute `src_hash` (the first 12 characters of the hash of the master's html, compositions, cue file and `mix.wav`) **before** rendering; record it. | agent | `manifest.json` master block |
| 2 | **One re-layout agent per ratio, on a copy** (`hf_9x16/`, `hf_1x1/` … copied from `hf/`). Brief: an **explicit file list**, the copy folder, an **output file** (`_work/qa/<ratio>/report.md`), a **clock deadline**, "return ≤ 10 lines, detail in the file", a progress file `_work/agents/<name>.progress.md` written as it goes. ≤ 4 agents in parallel, each ≤ 2 sub-agents. | agent (orchestrator) | the briefs |
| 3 | **What the re-layout changes** (table §4): the canvas (1088 for 1080-wide), the ratio's safe zones, type sizes, the caption rail, camera keys and framing, the speaker crop (`faces.json` re-solved for the new crop). **What it must not change:** timing, the cue file, `mix.wav`, the palette, the concept. | re-layout agent | the layout notes in the copy's PROMPT section |
| 4 | **The agent is also a tester.** A bug found while porting (a re-layout agent once found a phone vanishing at 3.69 s in an **approved** master) is reported to the orchestrator and fixed **in the master**, then **carried to every copy in the same round**, and every derivative is re-rendered; **never fix only the copy.** | agent | the CHANGELOG entry with the master hash change |
| 5 | **Hook variants** (A/B/C, platform cuts): the hook is a sub-composition bound to **composition variables** in the **same copy** (not a copy per hook); each row of a variants file names the output and its hook source/text; a batch render via variables is `[IDEA]` until a project has run **one** variation successfully (test one first). A hook that carries its own spoken audio is mixed from the same cue file as the master's mix with only the hook cues changing, then remuxed — never a re-edit of the body. Add "no music" / "no captions" rows when the ledger asks. | agent | the variants file; one test render |
| 6 | **Render in ONE queue:** `render_lock` serialises heavy work across **all projects and all sessions**; chain the renders in one background command in the planned order (master → 9:16 → 1:1) and write the order in `_work/STATE.md`; **no heavy agent during a render**; another session holds the lock → wait and tell the person, never touch it. The lock waits (polling) but keeps no order; the stale-holder threshold is a known tool inconsistency (60 min in docs vs 3 h in the original code `[CONFLICT]`) — the student tool replaces it with a kernel-lock design; plan work over 60 min in segments to be safe. | agent | the lock log |
| 7 | **QA per derivative:** wf-06 stage 6 on each output file; stage 7 **axes 1 (composition and cropping) and 4 (readability)** only — axes 2 and 3 are inherited from the master unless the layout changed motion. | agent | per-output envelopes |
| 8 | **Manifest:** every file with `hf`, `src_hash`, `from_master`, `round`, `date`, `lufs`, `tp`, `qa`; run the rejection rules (wf-08 §5). | agent | the manifest |

## 4. Re-layout checklist (per ratio)

| Item | Change |
|---|---|
| canvas | 1080-wide ratios authored at 1088 with `data-deliver-width="1080"`; 16:9 at 1920 (re-verify the 8-column defect per HyperFrames version) |
| safe zones | 9:16 master rows (key text top ≥ 300 / bottom y ≤ 1248 / left ≥ 140 / right ≥ 192; caption rail ≤ y 1450); 4:5 and 1:1: 54 px all sides (the profile grid crops 4:5 to 3:4, so keep text ≥ 54 px from the sides); 16:9: x ≤ 1824, bottom 162 for the platform bar (house policy, dated 2026-09, `[PERISHABLE]`; see `agent-content/references/platform-specs.md`) |
| typography | caption/title size and position per ratio (a caption on a 16:9 frame is not the 9:16 size) |
| camera | keys re-solved for the new frame; **text-fit arithmetic** redone |
| speaker | `faces.json` re-solved for the new crop; `face_center audit` on the derivative |
| captions | rail per ratio; the layout manifest regenerated; the collision check re-run |
| derived content | the master's palette, motion tokens, cue timings, mix — **unchanged** |

## 5. Exit gate GV

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| every ratio/variant/length in the ledger matrix has a rendered output | `ls final/` vs the VAR rows | else `fail` |
| each output was rendered **from the frozen master's cue file and mix** | `manifest.json` `from_master` all equal `master.src_hash` | else `fail` |
| per-output QA stage 6 `PASS` with coverage; axes 1 and 4 clean | `_work/qa/<ratio>/*.json`, review files | else `fail` |
| any bug found while porting was fixed in the master **and** carried to all copies, all re-rendered | CHANGELOG + new hashes | else `fail` |
| one heavy job at a time (no overlapping renders) | lock log | else `warning` |
| naming per the table; no foreign file in `final/` | `ls final/` | else `fail` |

Gate record → `hf/QA.md` "Gate log". `blocked` while a derivative lacks the master's latest fix.

## 6. Human vs agent

| Human | Agent |
|---|---|
| names the master ratio and the variant matrix at intake; approves the master; approves which hooks ship | orchestrates the re-layout agents; owns the queue; ports fixes to every copy; writes the manifest |

## 7. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| a crop instead of a re-layout | shortcut | re-layout the ratio | principle |
| the 1:1 was delivered without the master's 3.7 s fix | the master was fixed after copies | port to all, re-render all | freeze; `from_master` check |
| three agents rendering at once | no queue | `render_lock`; chain renders | step 6 |
| names collide across variants | no platform token | `<name>_<platform>_hookA_…`; platform token mandatory when Meta and TikTok cuts differ | wf-08 §5 |
| a late "also 16:9 in Hebrew" | an un-asked axis | a full re-layout by its own agent after master approval | intake matrix; "maybe later" → plan the copy now (layout notes in the PROMPT) |
| usage-limit stops of hours | too many agents with sub-agents | resume from progress files; cap agents | step 2 |
| a derivative silently stale | "ready" without the manifest check | reject; list mismatches | wf-08 §5 |

## 8. Tool invocations

`hf_deliver --name <name> [--aspect …]` per copy · `render_lock status|run` · `hf_preflight` · `hf_segment` · `face_center source` and `camera_path --cuts … --scale …` (speaker crops) · `frame_qa` · `caption_qa` · `sheet` · `ledger` · `sha256sum`. Several agents: explicit file lists, deadlines and progress files; stopping an agent = kill **its process tree** (and its headless browser), then check the lock; **never message another session**.

## 9. Per-type deltas

| Type | Delta |
|---|---|
| talking-head | master 9:16; a 16:9 re-layout needs a new speaker crop and a different caption size/rail; `face_center audit` per output |
| testimonial | a 30–45 s social cut and a 60–90 s long cut are **different edits** (a new paper edit), not a trim; a multi-client supercut is its own project |
| ad-promo | 15 s + 30 s × 3 hooks; Meta vs TikTok cuts (the Meta chevron only on Meta; the TikTok UI column on the right ≥ 140 px; a TikTok button or form for CTA; WhatsApp is region-gated); the licence rows apply to every cut |
| motion-graphics | 16:9 master first (the launch grammar), then 9:16 and 1:1 re-layouts, one agent per ratio on a copy; the three tables inherited |
| ai-generated | native fps of the takes preserved in every output; the disclosure row repeated |
| podcast-clip | one project or sub-composition per clip; shared design |

## 10. Time labels

Owner target: none stated. Modelled: none. Measured: none on a student. (A six-note review round is in `studio-review-loop.md`; derivative renders were not measured.)

(src: distilled/02 workflow §13, §10.6; distilled/01 A11, H3–H7, L1–L6; blueprint WORKFLOWS §5 — read 2026-10-02.)

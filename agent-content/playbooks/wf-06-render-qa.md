# wf-06 — Render and QA (רינדור ובדיקה)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §1–§3 and QA_AND_BENCHMARKS §1–§2, distilled/02 workflow-end-to-end §8 and qa-and-benchmarks §1–§5, TOOLS_SPEC §1–§3, research E04/E11/E12.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[SOURCED-unverified]` · `[CONFLICT]` · `[IDEA]` · `[LOCAL-only]` · 💲 = paid step · `house preset` = an owner heuristic, not a perceptual or platform standard · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | 6 of 9 |
| Owner skill | `render-qa-delivery` (+ [cheap-first-qa.md](../techniques/cheap-first-qa.md), [studio-review-loop.md](../techniques/studio-review-loop.md), [visual-review-4-axis.md](../benchmarks/visual-review-4-axis.md), [critic-brief.md](../benchmarks/critic-brief.md)) |
| Artifacts (exact files) | `_work/drafts/<name>_draft_<aspect>.mp4` (the **one** full render of the round — never in `final/`), `_work/qa/<ver>/` (frame sheets, QA envelopes, `review_*.md`, `critic<N>/report.json`), `hf/QA.md` (ledger ticks with evidence + the gate log), `_work/timing_ledger.jsonl` lines, `_work/STATE.md` |
| Exit gate | **G6 — 0 flags; no blocker/major; rubric ≥ 4.0 with no dimension < 3; every hard gate ≥ 3; every ledger row ticked** |
| Target time | **30–45 min** (owner target); the machine stages are measured on OM (§3) |
| Paid steps | none by default. A paid API critic or hosted render 💲 needs a dated estimate and approval (`paid-spend-gate`); **no automatic escalation to a second paid provider** |

## 1. Principle

**Cheap first, minutes last: seconds-level checks first; verify on ranges; render the whole film ONCE per round.** (23 full renders in one 40 s premium test, about 9 needed, ≈ 2.3 h wasted.) **A pass must mean the declared test ran on its coverage** — never "zero findings" from an empty sample, a missing input, a disabled check or a crashed tool; those are `not_run` / `unsupported` / `INSUFFICIENT_EVIDENCE` / `error` and they **block**. `[RULE-owner]` `[MEASURED-lab]` (E04 reproduced eight false-success paths in the author's own tools).

## 2. Entry gate (stage 0 — readiness)

| Predicate | Evidence | If false |
|---|---|---|
| **G5 passed** | the preflight envelope `PASS` | wf-05 |
| the person's notes are **collected** (or none yet); while they are still typing: patch yes, **full render no** | `CHANGELOG.md` "Round N" | segments only |
| all assets are in; Blender, matte, ASR and analyses have **finished** | G4 `pass`; lock log | wait |
| `render_lock status` is `free` — if anything (even another session) holds it: wait, tell the person, **never touch it** | the status line | wait |
| Studio is closed or `data-hf-id` was stripped (patch before the render, not during) | grep | strip |

## 3. The stages (cost on OM; schematic flags — exact flags per `docs/TOOLS.md`)

| # | Stage | Tool | Time `[OM]` | Gate (do not continue without) |
|---|---|---|---|---|
| 1 | static preflight | `hf_preflight --strict` + `grep -n 'data-start="-' index.html compositions/*.html` + the ledger-id check | 2–5 s | 0 errors; warnings fixed or reasoned |
| 2 | engine check | `cd hf && set -o pipefail && timeout 900 render_lock run -- npx hyperframes check --timeout 600000 \| tee ../_work/check.log` | 1–5 min (up to 15 with grade shaders); 14–15 s on a 30 s synthetic composition (E12) | exit 0 |
| 3 | snapshots | `hyperframes snapshot --at t1,t2,t3,t4,t5 --describe false` | 1–2 min per bundle; 6.3 s for 3 frames (E12) | every point looked at |
| 4 | range renders | `hf_segment --from 26.0 --to 28.5 --qa` | 2–4 min per range | `frame_qa` clean on each range |
| 5 | **ONE full render** | `touch _work/.render_start` then `hf_deliver --name <name> --draft --sheet` | 8–13 min (4–21 observed) for a premium 40 s | `hf_deliver` verify PASS |
| 6 | automatic QA on the **new file** | `frame_qa` · `caption_qa` · `motion_qa` · `face_center audit` (speaker) · `color_check` (speaker) | 2–4 min | every tool `PASS` with coverage, 0 flags |
| 7 | visual review + critic | the 4-axis review on all-frame sheets; the independent critic with the type rubric | 10–15 min + tokens; critic ≈ 10 min | no blocker/major; rubric gate |
| 8 | **one fix round** | back to stages 1–4 on the **changed ranges only**, then ONE more full render (5) → 6 → 7 on corrected ranges | ≤ 45 min | no more full renders this round |

**Where snapshots go:** the middle of every transition, the first frame of every scene, every new effect **at peak intensity** (a morph at 25/50/75 %), every keyword at full size (look-alike letters), a speaker at the peak of every zoom. Snapshots do **not** prove cuts (video is not synced around cuts): only a render does.

**Intentional covers** (morph, reveal, vignette) flag `text_occluded`/`content_overlap`: add the allow attribute on the **specific elements** (never in bulk), after all spans exist.

### 3.1 Stage 5 — the one full render

`hf_deliver` strips `data-hf-id`, runs preflight (stops on an error), renders **under the lock** (final `--quality delivery --browser-gpu --sdr`; draft `--quality draft --gpu --sdr` on the reference machine's host — the AMF hardware encode is for drafts only), raises the encoder timeout, applies the **stale-file guard** (an output older than the run start stops the run), muxes `assets/mix.wav` over the picture (or two-pass loudnorm of the render's own audio, video stream copied), crops back from the 1088 authoring width, then **verifies**: duration ±1 frame, −14 ± 0.5 LUFS, TP ≤ −1, no black segment ≥ 2 frames, no dead right-edge band (house presets). **The draft must land in `_work/drafts/`**; if the tool wrote it elsewhere, move it at once — `final/` holds finals and `manifest.json` only. Render settings measured on OM (40 s heavy fixture, E11): 1 / 2 / 4 / 8 workers = 132.6 / 113.5 / 92.8 / 88.1 s; browser GPU −8 to −12 %; `--gpu` AMF encode and draft mode did **not** help; capture is the bottleneck (2–3 of 16 logical cores used); a CSS-scaled 720p proxy −20 %.

### 3.2 Stage 6 — automatic QA (commands schematic)

```bash
V="projects/<name>/_work/drafts/<name>_draft_9x16.mp4"; Q="projects/<name>/_work/qa/v3"
[ "$V" -nt "projects/<name>/_work/.render_start" ] || { echo "STALE FILE"; exit 1; }   # stale-file guard
frame_qa "$V" --out "$Q/frames"            # every frame: black/pop/flash/hold/cut/double-jump + all-frame sheets
caption_qa "$V" --band 1150:1450 --x 140:888   # band/x per layout; the tool's defaults fit one project
face_center audit "$V" --tol 30            # speaker only; WHOLE film; candidates confirmed on frames
motion_qa "$V" --out "$Q/motion"           # camera stutter that frame_qa cannot see
color_check "$V" --step 2 [--ignore a-b]   # speaker only; a named preset, not universal; --ignore = a beat drained on purpose
```

Thresholds are **house presets** (`bands.json` → `qa_tool_thresholds`). Every report starts with the **file name, its time and the coverage** (decoded vs expected frames). **Every flag is fixed, or its reason is written in `hf/QA.md` as a time-bounded exemption tied to a ledger row** (approved-intentional / known non-blocking / missing check / blocker). **Never present a file with an unexplained flagged frame.** Known blind spots to cover by eye or by another layer: a one-frame object vanish at a reveal; caption plate overlap; a number's intermediate value; a stale deliverable ([cheap-first-qa.md](../techniques/cheap-first-qa.md) §4).

### 3.3 Stages 7–8 — review and critic

1. **Four axes** ([visual-review-4-axis.md](../benchmarks/visual-review-4-axis.md)) on the `frame_qa` sheets. **Scale to the film: under 20 s a self-review; 20 s or more or a client delivery → ONE reviewer, continued between rounds; derivatives axes 1 and 4 only** (4 agents × every frame × 4 rounds burned the quota in two sessions) `[CONFLICT]` resolved to the later rule.
2. **Independent critic** per the type rubric ([critic-brief.md](../benchmarks/critic-brief.md)): a separate agent that did not build the film; given the author's past notes; coverage declared; **round ≥ 2 reviews changed ranges only**; max 3 rounds then present with open gaps.
3. **Concept-fidelity gate:** fill `hf/QA.md` for **every ledger row** — `| ID | check result | at (s/frame) | evidence | ok / x / n/a / not_run |` using the check kinds in [concept-ledger.md](../techniques/concept-ledger.md) §2. An `x` is fixed, or listed as a numbered gap with the reason — never silent.
4. **Wait for ALL reviewers** before any patch or render (a render was killed because it started for one fix while two reviewers were still running). A critic that finds something new that a static check could have found ⇒ **add that check to stage 1**.
5. **One fix round:** merge all reports into one numbered list in `CHANGELOG.md` (an intent change goes to PROMPT.md first); ONE patch; stages 1–4 on touched ranges; **one** more full render; QA and review only on the corrected ranges (the same reviewers verify their own findings).

## 4. Long-job protocol (any job over 3 minutes: render, `check`, Blender, image-to-video, matte, ASR, analysis queue) `[RULE-owner]`

**The person must never have to ask "what about the render?"** — if they did, that is a protocol failure, logged in the retro.

1. **Benchmark one unit** (a segment, one scene, one second of image-to-video, one frame of matte); the rate comes from that. Do not benchmark a short easy unit and extrapolate over a different scene complexity.
2. **One-line ETA in chat before starting**, e.g. `full render: about 11 min (1520 frames, 2.3 fps), done at 14:32`. An ETA above **30 min for one shot** → propose an alternative **before** starting (a shorter shot or a hosted quote instead of local image-to-video: 17 min for 2 s on OM). ETA formula: `fixed startup + remaining units × warm median` with a range.
3. **`timeout` on every command:** `check` 900 s; a render **3× the ETA**.
4. **Background with a log and a state line:** run detached, output to `_work/<job>.log`, and a line in `_work/STATE.md` (what runs, which file will result, the next step) so "continue" after an interruption is one step.
5. **Heartbeat** about every 5 minutes (tail the log / a monitor); with the person present, a status line every 5–10 minutes (`render 62 % (940/1520), about 4 min left`).
6. **Watchdog:** **0 frames after 3 min, or no progress for 10 min** → stop **your own** process tree only (`taskkill /T /F /PID <pid>` on Windows; the process group elsewhere), check `render_lock status` (an agent stop once left its render running), tell the person, diagnose with **one timed snapshot**, retry **once**. A leftover headless-browser process is killed only if it is yours; another session's processes are never touched.
7. **Partial results at once:** a segment or draft that is ready is sent now, not at the end of the list.

Planned tooling (TOOLS_SPEC §3, **not yet implemented**): `render_watch` (parses `frame N/M`, ETA after 60 frames, heartbeat to `_work/render.status.json` every 60 s, kills only the owned process tree after 10 min without progress, cleans orphan headless browsers of that run) and a resumable render wrapper (segmented capture with resume) so a killed render or a session-limit stop resumes from the last segment. A **note that arrives mid-render**: first half → stop (own tree only) and re-run after collection; second half → finish; it joins the next round unless it is a blocker.

## 5. Exit gate G6

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| **exactly one** full render this round (range renders are not counted) | the timing ledger line `full_render_round = 1`; `ls _work/drafts` shows one new file | else `fail` (explain extra renders in the retro) |
| the draft is **newer** than the last patch and the render start | `[ "$V" -nt … ]` output; the file name + time at the top of every QA report | else `fail` |
| every automatic QA tool reports `PASS` with coverage (`decoded == expected`) and 0 unexplained flags; speaker types include `face_center`, `motion_qa`, `color_check` | the envelopes in `_work/qa/<ver>/*.json` | any `FAIL`, `not_run`, `unsupported`, `INSUFFICIENT_EVIDENCE`, `error` ⇒ `fail` |
| the four-axis review has no blocker or major | `review_*.md` + the merged list | else `fail` |
| the critic (separate agent) scored per the type rubric: average ≥ 4.0, no dimension < 3, hard gates ≥ 3, no severe failure, coverage declared | `critic<N>/report.json` | `INSUFFICIENT_EVIDENCE` if coverage is thin |
| every ledger row is `ok` or listed as a numbered gap with a reason | `hf/QA.md` table | else `fail` |
| `hf_deliver` verify (draft) PASS | the verify block | else `fail` |

Gate record → `hf/QA.md` "Gate log". **`PASS` from `hf_deliver` proves mux, loudness, black and edge band only — not captions, motion, face, colour, rubric or ledger.**

## 6. Human vs agent

| Human | Agent |
|---|---|
| (nothing required here; may watch Studio) | runs the stages in order; reports ETAs and heartbeats; runs the automatic QA and the 4-axis review; briefs the independent critic; fills `QA.md`; fixes in one round |

## 7. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| render stuck, 0 frames | two renders at once, or a render beside Blender/ASR/matte, or a grade shader on AMD | kill your own tree; rerun once; check the lock | one heavy job; watchdog |
| a render ran after a failed `check` | `check \| tail && render` takes `tail`'s exit code | `pipefail` or no pipe | stage 2 command |
| QA said "clean" on a failed render | QA ran on a stale file | compare mtimes | stale-file guard |
| a full render was wasted | a note arrived mid-render; a render started while reviewers ran | collect notes; wait for reviewers | §3.3 step 4 |
| `check` hangs > 10 min | a leftover headless browser after a stop | kill your own tree, rerun once | `timeout 900` |
| a tool exits 0 though nothing was checked | missing input / empty decode | explicit statuses | E04 positive controls |
| the critic passes what the author rejects | not briefed with the author's past notes; anchored | add the clean-smooth table; blinded audit | critic-brief |
| session usage limit stopped work | too many parallel agents | resume from `STATE.md` | ≤ 4 agents, ≤ 2 sub-agents each |

## 8. Per-type deltas (type-specific QA)

| Type | Delta |
|---|---|
| **talking-head** | `face_center audit` 0 ranges (tolerance 30 px, whole film); `motion_qa` 0 ranges; `color_check`; `source_cuts` before the build and a cover check; the assembled-VO `join_diff`; `caption_qa --band <top>:1450`; caption-vs-mouth and overlay-vs-face overlap per frame; a stock audit (foreign text/locale; a stranger under "I" is a credibility gate) |
| **testimonial** | the claims table: every spoken number is on screen and every proof matches; consent record; no altered screenshots; the opening is the result; `caption_qa`; noise/mix listening |
| **ad-promo** | mute test; safe-zone overlay snapshots at hook, offer and end card; the offer ×3; music/SFX licence rows; `hf_deliver` TP gate (the author's own ads had 7 of 10 at ≥ 0 dBTP); compliance rows; hook variants checked per output |
| **motion-graphics** | the **three tables** are the QA checklist; snapshots of **every** transition; a beat test (hit offsets in frames); event gaps ≤ the ledger value; `motion_qa` candidates confirmed on frames (UI builds read as jitter); no accent before its frame |
| **ai-generated** | every take at 1× and on frames at every transformation (hands, bones, text, product); `TAKES.md` windows used; native fps preserved; one look; the disclosure row; spend log matches the approvals |
| **podcast-clip** | the stand-alone gate per clip; face/caption safety per layout switch; hysteresis ≥ 1.5 s; per-speaker levels |

## 9. Time labels

Owner target 30–45 min for the stage (preflight → check → snapshots → ranges → one render → QA → review → one fix round). Machine stage times above are **measured on OM only** (single passes, shared host for E11/E12; other hardware **unmeasured**). Modelled: the six-note round in `studio-review-loop.md` (430 s vs 240 s).

(src: distilled/02 workflow §8; distilled/02 qa §1–§5; QA_AND_BENCHMARKS §1–§2; TOOLS_SPEC §1–§3; research E04, E11, E12 — read 2026-10-02.)

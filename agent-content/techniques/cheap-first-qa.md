# Technique: cheap-first QA (the gate stack)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint QA_AND_BENCHMARKS §1–§2, distilled/02 qa-and-benchmarks §1–§2 and §8, distilled/02 workflow-end-to-end §8, research E04/E11/E12.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[SOURCED-unverified]` · `[IDEA]` · `[CONFLICT]` · `[LOCAL-only]` · `house preset` = an owner/house heuristic or policy, **not** a perceptual or platform standard.
> OM (the reference machine) = one Windows laptop; hardware details are intentionally not published.8.x. Times marked `[OM]` are measured there; other hardware is unmeasured.

## 0. Principle

**First the checks that cost seconds; only when they are clean, the checks that cost minutes; the full render happens once per round.** Fix and verify on **ranges**; render the whole film once. (Premium talking-head test #3 on OM: 23 full renders, about 9 needed, ≈ 2.3 h wasted.) `[RULE-owner]` `[PROVEN-internal]` (src: distilled/02 workflow §8)

**A pass must mean the declared test actually ran on its required coverage** — never "zero findings" from an empty sample, a missing input, a disabled check or a crashed tool. This is the central finding of the QA research and of the E04 audit, where eight false-success paths were reproduced in the author's own tools. `[MEASURED-lab]`

## 1. Status vocabulary and the result envelope (fail closed)

Every check reports exactly one status:

| Status | Meaning | Counts as pass? |
|---|---|---|
| `PASS` | the declared test ran on its required coverage and found nothing blocking | yes |
| `FAIL` | a blocking finding | no |
| `warning` | a non-blocking finding that is recorded | yes, with the warning on file |
| `not_run` | the check was not executed (disabled, dependency missing, no input) | **no** |
| `unsupported` | the case is outside what the tool supports (rotation, VFR it cannot time, …) | **no** |
| `INSUFFICIENT_EVIDENCE` | it ran but coverage was too thin to conclude (e.g. too few tracked feature pairs) | **no** |
| `error` | the tool crashed or the decoder failed | **no** |

Envelope (TOOLS_SPEC §1): `{tool, version, input_sha256, decoded_frames, expected_frames, coverage, status, findings[]}`; non-zero exit on FAIL/INSUFFICIENT/error; `qa delivery` aggregates. Required fields in practice: the input file name and **time** (a QA report on a stale file once said "clean" for a failed render), rational fps/PTS, frame numbers **and** real timestamps (30000/1001 drift guard), the thresholds used (they are house presets), measured intervals and decoded vs expected frames. A tool that cannot report coverage is `not_run` for gating purposes.

**Aggregate rule:** release is blocked when a *required* check is `FAIL`, `not_run`, `unsupported`, `INSUFFICIENT_EVIDENCE` or `error`. Optional checks may be omitted with a visible reason. Intentional blacks, holds and cuts stay **visible in the record** with their reason (time-bounded exemptions tied to the approved PROMPT: approved-intentional / known non-blocking / missing check / blocker) instead of disappearing `[CONFLICT]` (the master rule "no flagged frame" vs a shipped project that accepted flagged frames as intentional; this repo uses the exemption table).

## 2. The stack (cheap → expensive)

| # | Layer | Tool / actor | Cost `[OM]` | Blocks when | Notes |
|---|---|---|---|---|---|
| 0 | readiness | `render_lock status`; assets in; notes collected; no heavy agent running | seconds | lock not free; assets missing | Studio closed or `data-hf-id` stripped |
| 1 | static preflight | `hf_preflight --strict` + `grep -n 'data-start="-' index.html compositions/*.html` (must print nothing) + ledger-id grep | 2–5 s | any error; any warning under `--strict` | each check "burned a render on a real project"; parse HTML structurally (E04-B06: quote style flipped the verdict) |
| 2 | engine check | `hyperframes check` under `timeout 900` and `pipefail`, under the lock | 1–5 min (up to 15 with grade shaders) | exit ≠ 0 | `check … | tail && render` takes `tail`'s exit code: use `set -o pipefail` or no pipe. 14–15 s on a 30 s synthetic composition (E12) |
| 3 | snapshots | `hyperframes snapshot --at t1,…,t5 --describe false` | 1–2 min per bundle of 5; 6.3 s for 3 frames (E12) | a point not looked at | ≤ 5 timestamps per call; always `--describe false`; snapshots do **not** prove cuts |
| 4 | range renders | `hf_segment --qa` | 2–4 min per range | `frame_qa` not clean on the range | range snapped outward to whole scenes; no audio |
| 5 | **ONE full render** | `hf_deliver --draft` (candidate) / final after approval | 8–13 min (4–21 observed) `[OM, premium 40 s]` | `hf_deliver` verify fails | one per round |
| 6 | automatic QA on the **new file** | `frame_qa` · `caption_qa` · `motion_qa` · `face_center audit` (speaker) · `color_check` (speaker) | 2–4 min | any FAIL / not_run | file must be newer than the render start (stale-file guard) |
| 7 | visual review, 4 axes | reviewers on all-frame sheets (tiles 180–270 px; zoom only deciding frames) | 10–15 min + tokens | any blocker or major | length-scaled: see §5 |
| 8 | rubric + critic | independent critic, per-type rubric ([critic-brief.md](../benchmarks/critic-brief.md)) | ~10 min | average < 4.0, any dimension < 3, any hard gate ≤ 2 (owner gate) | max 3 critic rounds, then present with open gaps |
| 9 | concept fidelity | `hf/QA.md` — every ledger row ticked with evidence | minutes | any row not ok and not listed as a gap | |
| 10 | delivery gate | `hf_deliver` verify on the **final file** + `qa delivery` + manifest | at the end of the render | length off by > 1 frame · −14 ± 0.5 LUFS · TP > −1 · black ≥ 2 frames · dead edge band · stale manifest | house preset; PASS ≠ release PASS (§4) |
| 11 | the author | the human | their time | their notes | |

Measured cost of **six notes** on a synthetic 30 s composition `[MEASURED-lab, OM, HyperFrames 0.8.98, single pass]`: a full render per note **430 s** vs range drafts **161 s + one final full render 79 s = 240 s** (a scene cache: 226 s); an audio-only note by remix + remux **1.8 s**; Studio hot reload detected an edit in 0.04–0.9 s. Not measured: human review time and agent thinking time. (src: E12 REPORT) Render settings on a 40 s heavy fixture `[MEASURED-lab, OM]`: 1 / 2 / 4 / 8 workers = 132.6 / 113.5 / 92.8 / 88.1 s; browser GPU −8 to −12 %; `--gpu` AMF encode and draft mode did not help; CPU use only 2–3 of 16 logical cores (capture is the bottleneck); a CSS-scaled 720p proxy −20 %. (src: E11 REPORT)

## 3. House-preset thresholds (`bands.json` holds them in machine form)

| Tool | Flag condition (house preset, 2026-10-02) | Source |
|---|---|---|
| `frame_qa` | black = mean luma < 6 (0–255) outside allowed ranges · pop = both neighbour differences > 12 and skip difference < 0.45 × min while neighbours match · flash = brightness jump > 60 returning within 2 frames · hold ≥ 1.0 s (warning) · hard cut = difference > 22 (info) · double jump = difference > 8 with a following spike > 8 while the previous < 6; exit 1 on black/pop/flash | owner tool docstring `[PROVEN-internal]`; analysis grid 96×54 grey per T13 |
| `caption_qa` | pop = bright-pixel (luma > 175) count in the caption band falls > 85 % between two frames, to < 12 % of the previous, previous > 900 px; band/x per layout (default 950:1320, 120:960 is **one project's**) | docstring; limits §4 |
| `motion_qa` | flag when \|accel\| > 1500 px/s² (or zoom accel 0.6/s², **not** used in the final decision — plot only) inside a shot, or a pan reversal above 60 px/s, or ≥ 3 sign flips in 0.5 s; ranges < 0.2 s ignored; tracking needs ≥ 12 inlier points and ≥ 25 % inliers | docstring; E04: crashes on low-feature input → must become `INSUFFICIENT_EVIDENCE` |
| `camera_path` | ok = acceleration ≤ 400 px/s² and face within 45 px | docstring |
| `face_center audit` | any sampled A-roll frame with the face > 30 px from centre; skip frames with no detection **but report coverage** | docstring; a pass with zero coverage is `INSUFFICIENT_EVIDENCE` |
| `color_check` | skin Y within ±9 of 46 %, hue 105–125°, chroma 16–32 codes; black Cb/Cr within ±3 and Y ≤ 9 %; near-white chroma ≤ 3; p1 ≥ 1 %; pass at ≥ 85 % of sampled frames — **targets from ONE reference footage = a named preset**, moody/AI-film footage uses skin Y 34–42 | docstring; T12 `[CONFLICT]` |
| `hf_deliver` verify | duration within ±1 frame of `data-duration`; −14 ± 0.5 LUFS; TP ≤ −1.0 dBTP; no black segment ≥ 2 frames; no dead right-edge band (30 sampled frames) | owner policy; **a house profile, not a verified platform requirement** `[CONFLICT]` |
| `hf_mix --report` | VO margin ≥ 5 dB in the 1–4 kHz band; no dead silence ≥ 0.4 s below −45 LUFS mid-film; 3 s-LUFS step ≤ +3 LU at a cut unless intended | docstring |

None of these is a perceptual or platform standard (QA research, 2026-10-01). Brightness-pop flags are **review triggers, never a photosensitivity certification** (WCAG 2.2 SC 2.3.1 needs rate plus general and red-flash area analysis). `[SOURCED-unverified]`

## 4. What each layer cannot see (so a human or another layer must)

| Blind spot | Evidence | Cover it with |
|---|---|---|
| `frame_qa` missed a one-frame object vanish at a reveal (a phone vanishing; found after delivery) | owner catch | a DOM visibility timeline / region-SSIM step detector `[IDEA]`; T6 clip overlap; look at reveal frames |
| `caption_qa`: missing input exit 0; fixed 30 fps; overlap of two plates not seen; appearance not detected | E04-B01…B03 | the F08 solver ([caption-collision.md](caption-collision.md)); envelope with coverage |
| `motion_qa`: crash on empty valid coverage; vertical pan/rotation not covered; non-rigid graphics read as jitter | E04, static audit | `INSUFFICIENT_EVIDENCE`; confirm candidates on frames |
| `face_center`: mask fires on bright graphics and B-roll people | owner test #1 (2026-09-30) | restrict `--from/--to` to A-roll; confirm each range |
| `benchmark`: `0.0` dBTP treated as missing; failed gate prints but exits 0 | E04-B04/B05 | structured gate results; numeric preservation |
| `hf_deliver` PASS proves mux, loudness, black and edge band only — not captions, motion, face, colour, rubric or the ledger | audit AQ013 | run stage 6 on the **final** file; `--skip-render` must be bound to the build hash |
| a number flashing a wrong intermediate value | owner catch | allowed-value set per number; OCR of the price region per frame `[IDEA]` |
| a hidden source cut | owner catch | `source_cuts` + a cover ≥ 6 frames each side |
| SFX too loud / a stray whoosh | owner catch | `hf_mix --report`: SFX-to-VO per cue; no cue without a visible event ±3 f |
| pink or off-palette accents | owner catch | palette audit: every hex vs DESIGN.md |
| B-roll "looks AI" or static | owner catch | critic axis; `motion_scan` (events/s per segment; flag ≥ 1.5 s with < 1 event/s `[IDEA]`) |
| a VO line missing its first/last two words | owner catch | `join_diff` on ASR of the assembled VO |
| a stale deliverable | an old 1:1 file sat beside the newer 16:9/9:16 finals unnoticed | manifest with source hashes; "ready" rejected on mismatch |
| a model "watched the whole video" | vendor limits (1 FPS sampling, first-frame-only animated input) | record coverage; never claim more than the sheets/frames supplied `[SOURCED-unverified]` |

## 5. Review depth scales with length `[RULE-owner]`, resolved `[CONFLICT]`

The original rule said 3–4 reviewers on every-frame sheets; after a 10 s test cost ~160 k tokens of review the author's later rule governs: **< 20 s → self-review on the sheets** (`frame_qa` + `motion_qa` + the four axes); **≥ 20 s or a client delivery → ONE reviewer, continued between rounds** with the fix list only; first round of a project 2–4 reviewers over the whole film only if the film is long; later rounds only changed or flagged ranges; derivatives: axes 1 and 4 only. Automatic checks always come first (seconds, no tokens). The critic must be a **separate agent that did not build the film**; a fresh context of the same model gives process separation only, not independence. See [studio-review-loop.md](studio-review-loop.md) and [critic-brief.md](../benchmarks/critic-brief.md).

## 6. Positive controls (fixtures that must keep failing correctly)

Generate with FFmpeg only (no client media): black frame, one-frame flash, freeze, caption drop at 25 and 30 fps, caption overlap (frames 30–45), clipped audio, a low-feature clip, a missing input, a zero-frame file. Every tool must (a) FAIL or report the right status on the positive control, (b) PASS the paired negative, (c) report `not_run`/`error` — never PASS — on the missing and empty inputs. The E04 synthetic set seeds these; **a QA tool is not "ported" until its controls pass on Windows, macOS and Linux CI for the CPU path.** `[MEASURED-lab]` for the E04 defects, `[IDEA]` for the CI matrix.

## 7. Procedure card (what wf-06 does)

1. Stage 0–1; stop on any fail. 2. Stage 2–3 for the changed ranges. 3. Stage 4 per range (several ranges one after another under the lock). 4. **Stage 5 once.** 5. `[ "$V" -nt _work/.render_start ]` then stage 6 on the new file. 6. Stage 7–8 on changed ranges. 7. Fill `hf/QA.md` (stage 9) and write the gate record with evidence paths. 8. Anything a reviewer finds that a static check could have found → add that check to stage 1 (a critic who finds something new means the preflight is weak).

## 8. Failure modes

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| a tool exits 0 though nothing was checked | missing input, empty decode, disabled check read as "no findings" | explicit statuses | §1 envelope; §6 controls |
| QA said clean on a failed render | QA ran on a stale file | compare mtime with the render start; present only a file newer than the last patch | stale-file guard in `hf_deliver` and before every QA call |
| `check` hangs > 10 min | leftover headless browser after a stop | kill **your own** process tree, rerun once | `timeout 900` |
| a render ran after a failed `check` | pipe exit code | `pipefail` | §2 stage 2 |
| the same video scored 21.5 then 18.5 (of 30) by the blind critic | reviewer variance | do not read a 3-point difference as a result; repeat | pre-declared bar; calibrate with the author's past rejections |
| 4 agents × every frame × 4 rounds burned the quota | review not scaled to length | §5 | automatic checks first |

(src: distilled/02 qa-and-benchmarks §1–§2, §8–§10; distilled/02 workflow §8; QA_AND_BENCHMARKS §1–§2; E04, E11, E12 reports — read 2026-10-02.)

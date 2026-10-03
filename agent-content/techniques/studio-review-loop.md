# Technique: the Studio-first review loop

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from the owner's review-loop decision (research program §6 T24 "Already decided", 2026-10-01), distilled/03 time-sinks §5 and §2.3, distilled/02 workflow §12, research E11/E12.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[SOURCED-unverified]` · `[CONFLICT]` · `[LOCAL-only]`.
> OM (the reference machine) = one Windows laptop; hardware details are intentionally not published.8.98, ffmpeg 8.1. E11/E12 numbers: **one synthetic composition, single passes on a shared host**; human review time and agent thinking time were **not measured**.

## 0. The decision (owner, 2026-10-01) `[RULE-owner]`

1. Review drafts **live in HyperFrames Studio** (`npx hyperframes preview --background`) instead of rendering a draft per round.
2. Re-render only **the noted range plus its scene context** (`hf_segment`, snapped outward to whole scenes) — and only for render-only risks (below).
3. **One** full-quality render, **only after the owner approves the preview**.
4. An **audio-only** change is a remix + remux, never a render.
5. **Batch the notes** before any render ("collecting for 5 more minutes, then I fix and render — anything else?").
6. Benchmark one unit → one-line ETA → if one shot's ETA is > 30 min, offer an alternative (2.5D) before starting.

(The pack cites a memory file for this decision that is **not present**; the rule is recorded through the research program text — treat the wording as `[SOURCED-unverified]`, the decision itself as the owner's.)

## 1. Why — measured

| Measurement `[MEASURED-lab]` (E12, synthetic 30 s composition, 6 notes, OM) | full render per note | range drafts | scene cache |
|---|---:|---:|---:|
| n1 audio (remix + remux) | 68.6 s | **1.8 s** | 1.8 s with remix |
| n2 typo | 68.4 | 19.1 | 19.9 |
| n3 caption position (global change) | 67.6 | 59.7 | 102 |
| n4 3D timing | 67.8 | 24.7 | 27.5 |
| n5 shader / grade | 78.9 | 36.7 | 37.8 |
| n6 `<video>` + glyphs | 79.0 | 19.4 | 20.2 |
| **total** | **430 s** | **161 s + one final full render 79 s = 240 s** | 226 s |

Studio hot reload detected an edit in 0.04–0.9 s (one run missed an edit with a 60 s timeout; the rerun caught all six). Preflight per note: lint 1.5 s, `check` 14–15 s, a 3-frame snapshot 6.3 s. Historical, the reference machine: premium talking-head test #3 spent 23 full renders where about 9 were needed (≈ 2.3 h avoidable). Modelled saving for a 40 s talking-head with six 10-minute drafts removed: **60 minutes minus the live-review overhead V (unmeasured)**. (src: E12 REPORT; distilled/03 §4, 2026-10-02) The scene-level render cache saves ≈ 1.1–1.2 min per **single-scene** edit and is *worse* than a full render for global edits (143 s vs 88 s on the 40 s fixture: ~12 s fixed cost per unit); results at 720p CRF 0 were visually lossless (PSNR ≥ 46.8 dB) but not bit-exact (E11).

## 2. The loop

| Step | Action | Gate / evidence |
|---|---|---|
| 1 | **Open Studio** on the project (`preview --background`); give the person the link. It is a **local** server: for a remote client send a draft render or a screen recording instead. | the person can scrub the timeline |
| 2 | **Collect** notes in `hf/CHANGELOG.md` under `## Round N (date)` in the person's order and words; split multi-claim notes (1a, 1b). While they type: diagnose and patch yes, **full render no**. | numbered list exists |
| 3 | **Frames at each time:** `sheet --range a:b --fps 10`; around a transition every frame (`--fps 30`, ±0.5 s). Times are approximate: look one second each side. | a strip per note in `_work/notes/` |
| 4 | **Diagnose** to a file/line/cue/asset; **classify** (replace-concept / fix / audio-only / global rule). | a cause per note |
| 5 | **Ledger → PROMPT.md → patch** (never code first). Patch = a script **file** with unique-anchor asserts and a backup; close Studio or strip `data-hf-id` first. | preflight 0 errors |
| 6 | **Verify live in Studio** (hot reload), then only for render-only risks: `hf_segment --qa` on the range, snapshots (≤ 5 per call, `--describe false`). | the edit landed (confirm — one hot-reload miss was seen); the range is clean |
| 7 | **One full render** after approval and after **all** reviewers returned; QA on changed ranges. | wf-06 gate |
| 8 | **Present** (numbered by the notes, whole ledger, QA line, honest score, gaps). | wf-07 message format |

Round budget: **≤ 45 min per round and exactly one full render** `[RULE-owner]` (owner target; the measured reality on the long test was 1–5 renders per round before the order was fixed).

### 2.1 A note that arrives during a render

First half of the render: stop (**your own** process tree only), include the note, rerun after collection. Second half: finish, the note goes to the next round unless it is a blocker. Wait for **all** reviewers before patching or rendering (a render was killed because it started for one fix while two reviewers were still running). Never touch another session's processes. `[RULE-owner]`

## 3. Preview ≠ render: what still needs an encoded check

E12 measured, on a synthetic composition with HyperFrames 0.8.98 (baseline preview-vs-render MAD 2.1, SSIM 0.98; software vs hardware render differ by MAD 0.3):

| Item | Result `[MEASURED-lab]` | Rule |
|---|---|---|
| 3D (`preserve-3d`) and a shader/grade | no deviation beyond the baseline | still verify on a range render the first time a 3D/shader beat appears `[PROVEN-internal]` owner traps |
| `<video>` layers | preview frames differ from the render by **about one frame** | verify cuts only on a **render** (`hf_segment --qa`); snapshots do not sync video around cuts |
| per-glyph `tl.set` | reveal and scrub-back consistent | keep the "spans directly under a flex parent" check |
| `dir="rtl"` on the composition root | **did NOT produce a black render on 0.8.98** (frames matched the LTR control) | **`[CONFLICT]`** with the owner trap (black render on 0.8.x, issue #1934 closed without a visible fix commit). **Keep the owner's rule — never `dir="rtl"` on the root, `direction:rtl` only on text elements — and re-test per HyperFrames version before teaching it as universal.** |

Owner-reported traps that need an encoded check even in the live flow (not re-measured here): last 8 columns black at width 1080 (author 1088, deliver 1080), a graded `<video>` whose first frames come ungraded (pre-roll 6 frames), render audio attenuated (mux `mix.wav`, measure the final), HDR source flips output (`--sdr`). Each is `[PROVEN-internal]` `[LOCAL-only]` until a pinned-version fixture reproduces it. (src: distilled/04 hyperframes-traps §0, §1)

## 4. Audio-only changes

`hf_mix --report` → `hf_deliver --skip-render` (remux onto the existing raw render). ~1.8 s of machine time in E12, "≈ 2 min instead of 10+" in the owner's workflow. Caveats: `--skip-render` bypasses preflight and the freshness guard in the owner's original tool and can remux a **stale picture** after a visual change (audit AQ014) → the toolkit binds the raw render to the build hash and refuses a mismatch; a mixed round (audio + picture) puts the audio into the same single full render; a project whose audio is composed inside HyperFrames (no `mix.wav`) cannot change the mix without a render — build projects with `hf_mix`. Do not chase loudness inside the composition (more gain came out quieter when the renderer attenuated a clipping master). `[RULE-owner]` `[PROVEN-internal]`

## 5. Failure modes

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| fidelity captures wrong | a stale Studio server or a bad project id after a failed run | restart Studio, confirm the project path, redo the captures | check the served project id before trusting a capture |
| the edit did not show | one missed hot reload (60 s timeout seen) | reload, confirm the change in the DOM/frame | step 6 "confirm the edit landed" |
| patch anchors miss | Studio added `data-hf-id` | strip them (preflight error), grep anchors | close Studio before patching |
| a draft rendered per note | the loop not followed | stop; use Studio + range render | wf-07 gate "full renders = 1" |
| the client cannot open Studio | it is a local server | send a draft render or screen recording (one render for the round) | decide at intake (VAR/DUE) |
| render-only bug reaches the final | previewed only | the §3 list on a range render | first appearance of each risky beat |

(src: owner decision text in research program §6; E11/E12 reports; distilled/03 §2.3, §5; distilled/04 hyperframes-traps — read 2026-10-02.)

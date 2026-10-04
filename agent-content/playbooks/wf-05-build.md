# wf-05 — Build (בנייה)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §1, distilled/02 workflow-end-to-end §7, techniques §2 and §6, distilled/04 hyperframes-traps §0–§1, distilled/01 rules-and-gates D.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[SOURCED-unverified]` · `[CONFLICT]` · `[LOCAL-only]` · 💲 = paid step · OM = the reference machine (one Windows laptop; hardware details are intentionally not published). Engine traps are **scoped historical reports** until a minimal reproducer passes on the pinned build: "reported on the author's 2026-09-28 setup; regression pending on the pinned build".

| Field | Value |
|---|---|
| Stage | 5 of 9 |
| Owner skills | the **type skill** (`talking-head-editor`, `testimonial-editor`, `ad-promo-editor`, `motion-graphics-builder`, `ai-generated-video-editor`) + the HyperFrames engine skills (`hyperframes`, `hyperframes-core`, `hyperframes-cli`) |
| Artifacts (exact files) | `hf/index.html`, `hf/compositions/*.html`, `hf/cues.js` (the **single source of truth for timing and mix**; the toolkit may ship it as a JSON cue file read by `hf_mix` — either way ONE file drives picture and sound), `hf/data/*`, `hf/CHANGELOG.md` (what changed each round), `_work/STATE.md` |
| Exit gate | **G5 — `hf_preflight --strict` reports 0 errors** (+ assets complete, ledger ids cited) |
| Target time | **≈ 90 min** (owner target); the whole first presentable draft **within 4 h** (owner target) — see §6 |
| Paid steps | hosted rendering, AI 3D, generated media 💲 — only through `paid-spend-gate`. Local rendering is free |

## 1. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| **G3 passed** — PROMPT.md and DESIGN.md approved | CHANGELOG approval line; hash equal | **stop. No code before approval.** |
| assets are in or have a landing time; Blender/matte/ASR/analyses are **finished** or deliberately queued | the lock log; `STATE.md` | wait; no heavy agent beside a render |
| the HyperFrames version is **pinned** for this project (never hand-write `package.json`; an unpinned `npx` once asked for a non-existent version) | `hyperframes info` output saved in `_work/versions.txt` | pin and record |

## 2. Fixed order inside the stage `[RULE-owner]`

**cut → picture lock → motion and graphics (catalog / registry components / by hand) → captions → colour → sound (`hf_mix`).** Change order is always ledger → PROMPT.md → code.

| # | Step | Who | Evidence / output |
|---|---|---|---|
| 1 | **Scaffold rules.** One composition per ratio. Canvas for 1080-wide ratios (9:16, 4:5, 1:1): `data-width="1088" data-deliver-width="1080"`, `html, body { width: 1088px !important }`, `#root { width: 1080px !important }` — the engine's encoder blackened the last 8 columns at width 1080 on OM (re-verify per version; plain FFmpeg `gbrp` chains showed it too) `[PROVEN-internal]` `[LOCAL-only]`; not needed for 16:9 (1920). **Never `dir="rtl"` on `<html>` or the composition root** (black render on the author's 0.8.x builds); `lang="he"` on `<html>`, `direction: rtl` only on text elements `[RULE-owner]` `[CONFLICT]` (E12 did **not** reproduce the black render on 0.8.98 — keep the rule, re-test per version). Fonts only via `@font-face` from `hf/fonts/`. | agent | `index.html` skeleton passes `hf_preflight` |
| 2 | **One paused timeline** registered on `window.__timelines`, built after `document.fonts.ready`; **every style is a pure function of time** (no CSS transitions, timers, `Math.random` — a seeded hash for grain/scatter; no free-running rAF). Anchor tweens to **word cues** (`cue("word")`), not frame literals — a stale timing grid after a re-cut made a scene's logos invisible for two versions. Whole frames everywhere; `max(0, start)`; **no negative `data-start`** (it shifted every clip by 2 frames); frame-exact `f/30` to 6 decimals + a 0.0005 s overlap in `data-duration` (4-decimal rounding left a black frame at each cut); a state change on a cut at `start − 0.005`. | agent | grep outputs |
| 3 | **Cut and picture lock:** build the A-roll `<video>` windows from `edit.json` (one edit list generates `edit.json`, `cues.js` and the windows); verify the cut frames equal the EDL. After picture lock, motion decisions stop moving the cut. | agent | the verification output |
| 4 | **Motion and graphics.** Camera = **one spline per scene** (no stitched tweens, no overlapping camera tweens); measure (rel) before transforms; **animate transforms only** (lint forbids tweening `left/top/width/height`); numbers by whole swap; words by in-place swap; shape change by reveal-through; a hero that persists; exits shorter than entrances. Media rules: `<video>`/`<img>` are composited in their **own layer** — parent `visibility`/`overflow`/3D do not apply; time them by their own `data-start`; an image in a 3D card is a CSS `background-image`; tweens go on a wrapper, never on the `<video>`; no `preserve-3d` around media; unique ids (a duplicate id stole another element's CSS). Avoid a full-film `backdrop-filter`/big blur (4.3 fps instead of ~19 and an encode timeout at frame 1348/1350 on OM). Rules and traps: [clean-smooth-motion.md](../techniques/clean-smooth-motion.md). UI from a screenshot: [screenshot-rebuild.md](../techniques/screenshot-rebuild.md). | agent | snapshots of every transition (≤ 5 per call) |
| 5 | **Captions** (`hebrew-captions-transcription`): word-pop or sentence mode per the type; words in final slots on a centred line; lead the voice 0.08–0.1 s (clamp ≥ 0); last word ≥ 0.25 s, card ≥ 0.9 s; **entry AND exit animation** (blur-out-up ≈ 4 f), the next card's first word starts 2 f early; **rail bottom ≤ y 1450**; keyword contrast ≥ 4.5:1 sampled; look-alike test at final size; export the **caption layout manifest** for the collision solver ([caption-collision.md](../techniques/caption-collision.md)). Motion/launch pieces: **no captions** by default. | agent | `data/captions.json`, `data/caption_layout.json` |
| 6 | **Colour** — already baked into the A-roll (wf-04); **never** `data-color-grading` on speaker footage. | agent | — |
| 7 | **Sound** with `hf_mix` from the cue file: VO per line −14.5 LUFS + glue, ducking −10 dB (over a loud drop duck only on the words), VO ≥ 5 dB over the bed in 1–4 kHz, SFX 1–3 f **before** the picture and only on visible events at −18 to −26 dB under VO, master −14 LUFS / TP ≤ −1.5 in the mix (house presets; the render can attenuate audio ≈ 11.5 dB, so the final is **always muxed or loudness-normalised and measured** in wf-08). Run `hf_mix --report` after **every** sound change. | agent | the report |
| 8 | **Preview in Studio** (`npx hyperframes preview --background`) so the person can watch live; Studio adds `data-hf-id` — strip before every patch/render. | agent | the link/port in chat |
| 9 | **Self-gate:** `hf_preflight --strict` + `grep -n 'data-start="-' index.html compositions/*.html` (must print nothing) + the ledger-id check; then continue to wf-06 for `check`, snapshots and range renders. | agent | the preflight envelope |

### 2.1 Patch discipline (every change after the first build) `[PROVEN-internal]`

A patch is a **script written to a file** (`projects/<name>/tools/patch_rN.py`), never an inline interpreter heredoc with Hebrew or quotes (five heredoc failures in one project). Before: close Studio, **strip `data-hf-id`**, `grep -n` the exact anchors. Inside: backup (`_work/index_pre_rN.html`), `assert s.count(anchor) == 1` on every anchor, re-read after writing. All notes of a round go into **one** patch (or one script per note, all run), then preflight. Heavy per-clip effects are **baked once** (one pre-graded base clip), not stacked as many graded `<video>` layers.

### 2.2 Escape hatches (use the narrowest) 

`data-layout-allow-overlap` is **not** inherited — put it on each word span, not the group; `data-layout-allow-occlusion` goes on **every** text element a transparent cutout covers, including nested `<b>`/`<span>`, after all spans exist; `data-layout-allow-overflow` *is* inherited and silences several perception checks. A bulk allow once let a real overlap reach the author. `[PROVEN-internal]`

## 3. Exit gate G5

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| `hf_preflight --strict` finds 0 errors and 0 warnings (or each warning has a written reason in `CHANGELOG.md` for non-final builds; `--strict` is required before a final render) | the envelope: tool, version, input hash, coverage, status `PASS`, findings `[]` | `FAIL`/`not_run` blocks |
| no negative `data-start`; no `data-hf-id`; no `dir="rtl"` on the root | the greps print nothing | else `fail` |
| every ledger id is cited in the spec and realised in the build | the ledger check exit 0 + a row-by-row pass in wf-06 | else `fail` |
| fonts load from files; the Studio preview opens and plays | a snapshot + the Studio check | else `fail` |
| all assets named in the spec are in `hf/assets/` (G4 `pass`) | the G4 gate record | else `blocked` |
| long jobs started here followed the protocol (ETA line in chat, log, STATE line) | `_work/STATE.md` | else `warning` |

Gate record → `hf/QA.md` "Gate log". **A preflight that could not run is `not_run`, never `pass`.** `check` passing does **not** prove a correct render or correct Hebrew (it samples a grid; a lint error silently disables layout/contrast audits) — wf-06 still renders and looks.

## 4. Human vs agent

| Human | Agent |
|---|---|
| watches Studio when they want; sends notes (batched, wf-07) | writes all code from the approved spec; patches by script; self-gates; reports ETAs for any job over 3 min; never renders while the person is still typing notes |

## 5. Failure modes → remedy (symptom → cause → fix)

| Symptom | Cause | Remedy |
|---|---|---|
| an element is "just there" / never appears | stale timing grid after a re-time; `F(n)` literals outside the host window | anchor to word cues; preflight |
| a graded clip's first frames look ungraded | no pre-roll | 6 f under the layer above; bake the grade |
| a black frame at each cut | clip rounding | frame-exact values + overlap |
| black outside an iris | a clip ended at the reveal | keep the previous scene underneath |
| text "occluded"/"overlap" findings on tilted cards | projected boxes | per-element allow attributes, never bulk |
| glyph spans under a flex parent never show | capture ordering | absolutely positioned layers toggled by opacity, or nest spans |
| word pops at the clip end | an entrance re-asserts opacity after the exit | clamp the entrance to finish before the exit |
| build is slow / navigation timeout | many heavy `<video>` layers | one pre-cut 30 fps base clip; convert heavy PNG plates to JPG/WebP |
| patch anchors miss | Studio added `data-hf-id` | strip them; close Studio |
| an audio file in the mix is the wrong length | unmeasured assembly | measure first (wf-04) |
| a render ran beside Blender (11.5 → 21.5 min on OM) | no lock | `render_lock`; finish Blender before the render |
| session limit stopped an autonomous run (about 12 h idle in one test) | too many parallel agents | resume from `_work/STATE.md` and the agents' progress files; cap agents |

## 6. Time model (owner targets; **not** measurements)

Premium talking-head draft ≤ 4 h `[RULE-owner]` target: intake 10 min (matte/reference running in the background) → source analysis, cut, cut text approved 35 → DESIGN.md + PROMPT.md approved 45 → assets ‖ build 80 → preflight, check, snapshots, render 1, automatic QA 30 → reviewers, one fix round, render 2, present 30–40 → every note round ≤ 45 min with exactly one full render (cumulative ≈ 4:00). Other types, order of magnitude to a first draft: ad 2–3 h; premium motion 4–5 h (one playbook) or 3–4 h (another) `[CONFLICT, minor]`; AI 2–4 h plus generation time. **Measured reality:** the ≤ 4 h target was never met on a real premium project (a launch needed 17 drafts; a talking-head test took about 1 day to a "passing-ish" draft) — it is a target, not a promise. (src: distilled/02 workflow §7.1, §16)

## 7. Tool invocations

`hf_preflight --strict` · `hyperframes check` (under `render_lock`, `timeout 900`, `pipefail`; wf-06) · `hyperframes snapshot --at t1,…,t5 --describe false` · `npx hyperframes preview --background` · `hf_mix --report` · `face_center source` / `camera_path` (speaker rig) · `source_cuts` · `sheet` · `render_lock run -- <heavy>` · `ledger` · `grep`/`sha256sum`. HyperFrames environment pins (a published list of toggles; verify on the installed version): skip skill auto-update, no update check, no telemetry. Browse/records: never put secrets in the project.

## 8. Per-type deltas

| Type | Delta |
|---|---|
| **talking-head** | one pre-cut 30 fps base clip as the only A-roll `<video>`; **PRE = 6 f**; the rig `#zoom` (scale about 540,960) around `#pan` (x = 540 − faceX from the smoothed path, `Math.round`, ONE proxy tween); zoom origin y at face height; plate + cutout share the rig; layer order plate → dim/blur → behind-speaker graphics → cutout speaker → captions → front UI → grain; behind-speaker graphics only in the clear side zones (x < 380 or x > 700, y 300–680) with a camera pull-back (0.72–0.8) for every "behind" beat; overlay cards light (`#F2F1F3` at .95), ≤ 860 px, under the chin, never crossing the face, appearing in place; captions at chest height (y 900–1240), never below y 1450 and never on the mouth; a cutout masked in a 2–3 px feather with a halo choke |
| **testimonial** | split-screen proof (screenshot ≈ top 40 %, speaker below, caption on the seam; hard cut on the frame of the number word; hold 3–6 s; a marker ellipse); the **original** screenshot untouched, animated around; a lower-third once at 1–4 s; a persistent result headline for mute viewers; captions with an animated exit; punch-ins alternating 100 % and 110–120 % on jump cuts; an end card ≤ 3 s, no trailing black |
| **ad-promo** | the offer as a **separate brand-colour price tag** (never caption style); safe-zone overlay checks at hook/price/end card; the hook as a sub-composition bound to variables (`data-var-*`) for A/B/C (a batch render via composition variables is `[IDEA]` until tested in a project; test one variation first); the end card with music to the end; ad-licensed music only |
| **motion-graphics** | the author's helper contracts (spline camera, reveal-through, whole-number swap, words swap); the three tables are the build checklist; sprites start from their complete frame and enter as one element; a zoom-through is **two-sided** (the outgoing shot ramps too); no accent before the reveal; the grain/vignette as seeded functions; 21st-style UI ported seek-safe |
| **ai-generated** | clips trimmed to the **clean window**; never reversed; the timeline at the **native fps of the takes** (usually 24; never place 24p takes in a 30/60 timeline — stepped cadence); one grade (shared LUT at 30–60 % applied with `ffmpeg lut3d`, matched on HTML layers) + global grain 3–4 % + raised blacks; the cover kit (2–4 f whip, 1–2 f flash, 8–15 f black-blink + boom) with a sound under every cover; SFX on every transformation |
| **podcast-clip** | per-clip sub-composition or project; crop keyframes for TRACK/SPLIT/GRID from a smoothed path; captions on the seam in SPLIT; speaker-colour captions; title bar |

## 9. Time labels

Owner target ≈ 90 min for this stage; whole first draft ≤ 4 h (owner target). Modelled: none for the build itself. Measured (OM, single passes): a 12 s synthetic fixture rendered in 42.3–44.3 s (HyperFrames 0.8.98, one worker, software capture); a 40 s heavy fixture 132.6 s with 1 worker, 88.1 s with 8 — not comparable to a premium composition.

(src: distilled/02 workflow §7; distilled/04 hyperframes-traps §0–§1; distilled/01 D; research E01, E11, E12 — read 2026-10-02.)

# wf-04 — Assets (חומרים, רישוי וצבע)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §1, distilled/02 workflow-end-to-end §6, techniques §5–§6, distilled/01 rules-and-gates I1–I6, J1–J6, K1–K6, research E08/E09/E10.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[SOURCED-unverified]` · `[PERISHABLE]` · `[CONFLICT]` · `[LOCAL-only]` · 💲 = paid step (must pass `paid-spend-gate`) · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | 4 of 9 — runs **in parallel with wf-05** (heavy lanes start at the beginning of the build, not after review) |
| Owner skills | `speaker-color-correction` (footage of a person), `hebrew-captions-transcription` (ASR, fonts), `paid-spend-gate` (any spend), `video-prompt-writer` (video prompts), the type skill |
| Artifacts (exact files) | everything the spec needs under `hf/assets/`; fonts in `hf/fonts/` + `@font-face` in the compositions; `hf/SOURCES.md` (a licence row per external asset); `hf/TAKES.md` (AI takes: clean windows); `hf/data/` (`edit.json`, `words.json`, `faces.json`, `src_cuts.json`, `cam_path.json` as needed); `_work/cost_estimate.json` (+ approval id) when anything is paid |
| Exit gate | **G4 — all assets in before render 1, licensed, measured; paid work only with an approved dated estimate** |
| Target time | **60–90 min** (owner target; parallel with the build, so it does not add to the 4 h to a first draft). Heavy lanes are measured on OM only (§5) |
| Paid steps | marked 💲 below: paid stock/fonts, hosted TTS, AI generation/upscale/3D, any cloud service. **An explicit request to generate counts as approval within the balance — it never covers facts that appear on screen, client approval of factual stills, or spend beyond the balance.** `[RULE-owner]` |

## 1. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| G3 passed (PROMPT.md + DESIGN.md approved) | the CHANGELOG approval line | wf-03 |
| an **asset plan** exists: every asset the spec names, with source route and owner of the licence | `hf/data/asset_plan.md` (a table drawn from `<inputs>`/`<structure>`) | derive it from the spec first |
| no other heavy job is running (render, check, Blender, ASR, matte) | `render_lock status` = free | wait; one heavy job at a time |

## 2. Steps

| # | Step | Who | Evidence / output |
|---|---|---|---|
| 1 | **Search order.** (a) **The person's own assets first** (their transitions, logos, 3D, music, B-roll folders; the author's own film-burn beat a colour-mapped stock burn); (b) already-connected free sources (`integrations/catalog.toml`): stock video/photos, SFX/music, icons, fonts; (c) UI/motion language: `hyperframes catalog` first, then a shadcn/other registry component — port seek-safe, never import React as-is (21st.dev needs a paid account on the author's side → registries by default); (d) paid sources 💲 only with an estimate. Keys and tokens never go in files. | agent | the asset plan with the chosen route |
| 2 | **Fonts from files:** copy the font files into `hf/fonts/`, declare `@font-face` with relative URLs (a named family without `@font-face` falls back silently in the engine's browser; `hyperframes check` flags `font_family_without_font_face`). Default Hebrew families: Rubik (Regular/600 + Black/900), Heebo — OFL 1.1, keep the notices. Run the **look-alike test** (ו/ז, ד/ר, ה/ח) on every Hebrew keyword at final size. Adobe Fonts only through a web kit, never shipped; personal-use/brand fonts are not client assets. | agent | files + a snapshot proving the face loaded |
| 3 | **Licence every asset (`hf/SOURCES.md`).** One row per external file: path, source URL, licence, date checked, allowed uses (organic / paid ad / client work), attribution text, the person's approval where needed. **The single rule:** for ads read the **file's own row**, never infer a licence from a file name or a folder heading; allowed in ads: CC0, a free licence that explicitly allows ads, a paid subscription; `unknown`, CC-BY-NC or an unverified "no copyright" = **organic only** — and the author's shortcut "unknown = organic OK" has **no verified rights basis** `[CONFLICT]` (it conflates channel with permission, likeness/privacy and trademark), so treat it as an internal claim until the licence review resolves it. Client work: commercially licensed material only. **Third-party brand sounds/logos and AI stills that resemble a real person: organic only; ask before any paid use.** Platform GIF/sticker APIs change (one stopped serving on 2026-06-30; another is not approved for commercial use — `[SOURCED-unverified]`, checked 2026-09, `[PERISHABLE]`). | agent | `hf/SOURCES.md` |
| 4 | **Footage of a person → colour FIRST** (`speaker-color-correction`): `ls` the source tree for the **camera original** (4K, high bitrate) beside the compressed rough cut; map the rough cut to camera time by audio cross-correlation (1–2.5 s windows) and verify boundaries on images; measure with scopes (waveform, RGB parade, vectorscope with the skin line at 123°, histogram); fit numerically (global, then subject); **bake the corrected plate with a subject matte** (never `data-color-grading`, never a global `shadows +`); check with `color_check`. The numeric targets (skin Y ≈ 46 %, hue ≈ 118°, black Cb/Cr ≈ 0, sky neutral ≤ 100 IRE) were measured on **one** clip — they are a **named preset**, not universal; moody/indoor/AI-film footage uses skin Y 34–42 and hue ≈ 119–123 and a look at before/after sheets every iteration. | agent | `assets/aroll.mp4` (graded), `color_check` envelope |
| 5 | **A-roll preparation** (talking-head/testimonial/podcast): probe resolution/fps/rotation (a camera original may be rotated 90°); sync the cut to the original by audio cross-correlation; `source_cuts` (hidden cuts → cover **≥ 6 f each side**); frame-exact trims + **edge-fix** (`tpad` clone of the clean first/last frame; verify the cuts inside `aroll.mp4` land exactly on the EDL frames); pad to a multiple of 16 (1088 / 768) for 1080-wide ratios; make **ONE pre-cut, pre-graded 30 fps base clip** (`-g 15`) so the engine renders graphics, not many graded `<video>` clips (15 graded 60 fps clips through the engine's grade shader ran ≈ 1 min per frame on OM; baking dropped a render from hours to 3.5 min `[PROVEN-internal]` `[LOCAL-only]`); pre-roll **6 f** under the layer above every graded A-roll start; a `.mov` ≥ 1 GB or any 4K source gets a proxy for work and returns to the original for the final. | agent | `assets/aroll.mp4`, `data/edit.json`, `data/src_cuts.json` |
| 6 | **Transcript and joins:** `transcribe` the used ranges (Hebrew explicitly; never the engine's default English-only model); proofread names/brands by hand with a fix dictionary (ASR wrote "E24/7" for "24/7" and swapped place names); **do not run an LLM over the whole transcript** (a small model worsened WER); after every re-cut ASR the **full** assembled VO and diff it against the intended text with `join_diff` (ASR on isolated join snippets said "clean" while the full file still heard residues; a missing "אני" was caught by the author). | agent | `data/words.json`, the diff output |
| 7 | **Matte / cutout only for beats that put graphics behind the speaker** (`cutout`): choose the route by **quality review**, not by speed (§5); reset recurrent state at shot cuts; cache keyed by **decoded content/frame index** (never by `-ss` packet ranges — they missed 2 of 5 in an edit test); keep `check`-time "occluded text" allowances per text element. | agent | `assets/cutout.webm` + edge inspection note |
| 8 | **3D (one Blender batch):** decide **per beat** (Blender for photoreal hero objects and lighting; Three.js for procedural, data-driven, many instances or editable 3D UI); batch **all** Blender work in one run (each launch wastes ≈ 1–1.5 min compiling shaders; a render beside Blender took 21.5 min instead of 11.5 on OM); sprite sheets with alpha; pin brand colours **after** tone mapping (AgX makes brand colours pastel) and palette-audit the previews. AI 3D generation 💲 **only if the student connected a generator (for example Tripo); otherwise Blender is the builder (Three.js if the student chooses it)**. | agent | `assets/3d/*` |
| 9 | **Sound assets first** (they feed `cues.js`): VO (the person's recording, or TTS with a **lexicon**: brand names spelled in letter phonemes with 0.12–0.18 s gaps, heteronyms checked, then **back-transcribe and diff**); word timings; music **edited to the picture** (carve under the voice; take-away 4–12 f before a reveal; drop on the reveal; ring-out to the last frame); SFX from a licensed library or **synthesised** (`ffmpeg aevalsrc/anoisesrc`); **measure every audio file before sending** (length, onset ±2 ms, `ebur128`; a hand-assembled bed once came out 27.16 s with the tutti at 13.7 s instead of 15.54 s). Calm brand films: ONE uniform bed + diegetic foley instead. | agent | `assets/audio/*`, a measurement table |
| 10 | **AI generation 💲** (`paid-spend-gate`; `image-prompt-writer` for stills, `video-prompt-writer` for video prompts): a **dated estimate** (route, model id, formula, price date, plan, tax status), the person's approval of the **number**, a **retry cap**, provenance (provider, exact model id, mode, size, duration, fps, audio, price timestamp, ffprobe + hash of outputs). Stills first (the person approves factual stills before video); **benchmark one second first — if the ETA for one shot is > 30 min, do not start it: shorten the shot or quote a hosted route** (on OM a local 2 s clip cost ≈ 669 s per output second). Record each take's **clean window** (1.2–2.5 s) in `hf/TAKES.md`; QA every take at 1× and on frames; **text and Hebrew are added in post, never inside the generation.** Credits, API dollars and invoice cash are separate wallets. | agent asks, **human approves the number** | `cost_estimate.json`, approval id, `TAKES.md` |
| 11 | **Close the stage:** every asset the spec names is in `hf/assets/`; `SOURCES.md` rows = assets; fonts proven loading; audio measured; no unreviewed external download left in `_work/`. | agent | the check below |

## 3. Exit gate G4

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| every asset in the plan exists in `hf/assets/` or `hf/fonts/` and every external asset has a `SOURCES.md` row with a licence and allowed uses | a listing diff: assets on disk vs rows (counts equal; no `unknown` for a paid-use asset) | else `fail` |
| fonts load from files (not the system fallback) | a snapshot at a Hebrew-text frame; `check` has no `font_family_without_font_face` | else `fail` |
| footage of a person: the camera original was used; colour checked | `color_check` envelope `PASS` with coverage (or `n/a` with a reason: no person) | else `fail` / `INSUFFICIENT_EVIDENCE` |
| hidden source cuts are covered; joins verified on the **full** assembled VO | `src_cuts.json` + cover table; `join_diff` clean | else `fail` |
| audio assets measured | the measurement table (length, onset, LUFS) | else `fail` |
| **paid work**: every billed call is covered by an approved dated estimate and within the retry cap; none was started on a trial without approval | `cost_estimate.json` + approval message id + the call log, or `n/a` (no spend) | else `blocked` (stop spending) |
| no heavy job overlapped a render | the lock log | else `warning` |

Gate record → `hf/QA.md` "Gate log". **Missing evidence is never `pass`; "no paid work" is `n/a` with that reason, not an empty cell.**

## 4. Human vs agent

| Human | Agent |
|---|---|
| supplies files and rights facts; approves **spend with a number**; approves factual stills (product, medical, address, price) before video; approves the music choice | searches, licenses, preps, bakes, measures, writes SOURCES.md; asks before any paid step; never invents a brand asset |

## 5. Measured speeds (OM only; everything else unmeasured)

| Lane | Number | Limit |
|---|---|---|
| Hebrew ASR | CTranslate2 int8 CPU 0.84 audio-s per wall-s; the author's "×2.3 real time" = 0.435 | E08: 614.22 s FLEURS Hebrew read speech, single pass; real dialogue, timestamps, other hardware unmeasured |
| Matte (20 s 1080p, 600 frames, wrapper s) | RVM CPU 128.2 · RVM DirectML 93.2 · RVM half-rate hold 90.4 · MODNet CPU 278.1 · MODNet DirectML 108.0 · MediaPipe CPU 47.1 · native u2net 357.0 / 452.8 (two warm runs differ by 27 %) | E09: **quality unjudged**; RVM state not reset at cuts; GPL-3.0 (RVM) → internal use; a whole 55 s plate took ≈ 35 min in the author's work |
| Colour bake | ≈ 3 min per minute of footage (u2net matte ≈ 0.45 s per matted frame; matte only the padded person box) | owner tool docs; not re-measured |
| Blender | Eevee 1.2–2.3 s/frame procedural; ≈ 9 s/frame photoreal transparent at 540 px; ≈ 1–1.5 min start-up | owner baselines |
| Local image-to-video | ≈ 17 min per 2 s at 544 px (Wan 2.2 5B); 669 s per output second (Wan 2.1 1.3B, CPU offload, E10) | one config each |

## 6. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| shipped grey sky, magenta skin, tinted blacks | colour fixed late / only the rough cut used | bake from the camera original | G4 colour row |
| first frames of a graded clip look ungraded/frozen | no pre-roll | pre-roll 6 f; or bake the grade into the file | step 5 |
| render navigation timeout / hours | many `<video>` clips with a shader grade | one pre-graded base clip | step 5 |
| a font reads wrongly (ז≈ו) | a display font with look-alike glyphs | change that keyword's face (a condensed Noto weight fixed it once) | step 2 |
| a hand-built music bed was the wrong length | unmeasured | measure first | step 9 |
| a matte "looks fine" but halos on dark plates | speed chosen over quality | edge inspection; choke; a different route | step 7 |
| unknown-licence track in a paid ad | licence inferred | replace; row-level check | step 3 |
| a paid call was made before approval | prose-only gate | stop; reconcile the ledger; a wrapper/hook enforces caps | `paid-spend-gate` |
| a generation took longer than the budget | no 30-min gate | shorter window / hosted quote | step 10 |

## 7. Tool invocations

`new_project` (done) · `transcribe` · `source_cuts` · `aroll_cut` · `join_diff` · `face_center source` (per-piece face x) · `camera_path` (smoothed rig, `--cuts`, `--scale`) · `cutout` · `color_scopes`/`color_fit`/`color_render`/`color_check` (+ `grade_bake`, the simple-chain bake: grade = a file) · `hf_blocks` (the studio block library) · `ui` (shadcn registry reader) · `analyze`/`frames` (video analysis) · `hf_mix --report` · `sheet` · `render_lock run -- <heavy>` · `ledger` (timing line per lane) · `ffprobe`/`ffmpeg`. Provider calls only through the gate.

## 8. Per-type deltas

| Type | Delta |
|---|---|
| talking-head | colour bake → cutout only for behind-speaker beats → B-roll by meaning (real footage, 3D, rebuilt UI, data-driven; **never** AI-looking stills of people) → one Blender batch → music bed + quiet SFX; asset batch in ONE round before render 1 |
| testimonial | proof originals (blur PII before any upload); stock only as neutral mood; consent file; noise cleanup (`demucs`-style vocal isolation for car/street noise, then ≈ 3:1 compression) before the mix |
| ad-promo | logo SVG, brand colours/fonts, the offer in writing, vertical B-roll, same-angle before/after, **licence row per music/SFX file** (verified ad-compatible), product macro, WhatsApp icon + number, reviews with consent |
| motion-graphics | UI rebuilt in code ([screenshot-rebuild.md](../techniques/screenshot-rebuild.md)); sound first (VO → word timings → `cues.js`; music edited with a map; synthesised SFX); one Blender run for all 3D and plates; the palette audit on every render |
| ai-generated | stills first → approval → animate; the **gate** for every call; clean windows in `TAKES.md`; one grade + grain later; text in post; a ground-truth image for anatomy; disclosure plan |
| podcast-clip | the proxy + full-episode ASR; per-speaker audio if a remote recording; face/active-speaker analysis feeding crop keyframes |

## 9. Time labels

Owner target 60–90 min (parallel with build). Modelled: none. Measured: §5 (OM only; single passes). NVIDIA, Apple Silicon and Linux are **unmeasured**; do not copy AMD numbers to another machine.

(src: distilled/02 workflow §6; distilled/02 techniques §5–§6; distilled/01 I1–I6, J1–J6, K1–K6; research E08, E09, E10 — read 2026-10-02.)

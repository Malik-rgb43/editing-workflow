---
name: talking-head-editor
description: >-
  Edit a talking-head / speaker-to-camera video (expert, coach, service provider) from raw or rough-cut footage into a premium vertical reel: whole-sentence cuts, face-centred zooms, full-bleed B-roll, cutout, captions. Triggers: דובר, מדבר למצלמה, טוקינג הד, רילס עם דובר, בי-רול, סרטון תדמית של נותן שירות, "תערוך את הסרטון", add B-roll and zooms. NOT for testimonials (testimonial-editor), ads (ad-promo-editor), person-free motion (motion-graphics-builder), AI people (ai-generated-video-editor).
compatibility: >-
  Needs ffmpeg, Python 3.12 and a HyperFrames CLI pinned per project. Speeds quoted in references are measured on one reference machine; NVIDIA and Apple cells are unmeasured.
metadata:
  version: "0.1.0"
  kind: type
  status: "specified; deterministic checks only; model eval not run"
---

# talking-head-editor

Turns speaker-to-camera footage into a reel at the author's premium bar: natural-order whole-sentence cuts, a camera that never parks yet keeps the face centred, full-bleed B-roll chosen by meaning, the speaker cut out with graphics behind when a beat needs it, Hebrew captions, one locked palette, one continuous music bed. The author's price anchor ("a premium edit worth 500-700 NIS", unit per video vs per minute under confirmation, decision default Q1) is a quality target, not a market rate: never quote it to a student as one.

## Rules that outrank the rest of this file
1. **Intake until precise.** Ask in rounds of 3-4 questions, never assume: silence-cut only vs restructure (default: silence-cut, natural order), quality bar, ratios, exact final file name, is there a 4K camera original. A reference exists -> `reference-style-matching` first; no reference -> ask until exact (`video-brief-intake`).
2. **`ls` the whole source tree before anything else.** Colour and cutout come from the camera original, never from the compressed rough cut (d06-th §0.4).
3. **PROMPT.md approved by a human before the first line of composition code**, also in autonomous runs: the agent drafts, the human approves (decision default Q6). Order of change: ledger -> PROMPT.md -> code, never code first.
4. **No paid action** (generation, keyed stock/ASR APIs, cloud render) without a dated estimate and approval (`paid-spend-gate`). Default stack is free and local. `License: unknown` assets are blocked for client work (decision default Q2).
5. **One heavy job at a time** under `render_lock` (render, `check`, matte, ASR, Blender); no heavy agent while a render runs.
6. **Review in Studio first**, range renders only for render-only risks, **ONE full render per round of notes**, every-frame QA on the final file (`render-qa-delivery`).
7. HyperFrames traps: no `dir="rtl"` on the root, fonts from files in `hf/fonts/`, ASCII work root, `snapshot --describe false` with at most 5 timestamps per call, pin the CLI version.
8. Never message other Claude sessions. This skill is procedure, not permission: user and project restrictions on spend, installs and publication override it.
9. **Law vs house preset (decision default Q5).** Rules 1-8 are laws. Caption font, caption rail y 1450, beat cadence, colour targets and -14 LUFS are *house preset v1*: say so in PROMPT.md and let the user override.

## Inputs -> outputs
In: camera footage (+ rough cut if any), brief/ledger, brand palette and fonts. Out (project-relative): `hf/PROMPT.md` (approved), `hf/DESIGN.md`, `hf/data/{edit,words,faces,src_cuts,cam_path,edit_plan}.json`, `hf/assets/aroll.mp4` (graded, one 30 fps base, `-g 15`), draft in Studio, `final/<name>_<platform>_<hook>_<aspect>.mp4` + `final/manifest.json`, `_work/timing_ledger.jsonl`.

## Procedure
| # | Stage | Do | Artifact |
|---|---|---|---|
| 0 | Intake + source audit | rule 1-2; hash the camera file; probe rotation, fps, colour tags | ledger lines |
| 1 | Background jobs (lock-admitted, start at minute 0) | ONE background command: `python tools/prep.py <project>` (`--plan` first shows what runs; nothing is downloaded) = sheet, `transcribe` (-> `hebrew-captions-transcription`), `source_cuts`, `face_center source`, colour scopes, reference analysis; a `not_run` step in `_work/prep/prep.json` is not evidence. Start `cutout` only if a beat needs graphics behind | `hf/data/{words,src_cuts,faces}.json` |
| 2 | Text of the cut, no render | `aroll_cut`: natural order, whole sentences, in-point in the silence before each sentence; show the TEXT (or a 30 s audio-only cut) | `edit.json`, owner OK |
| 3 | Colour | `speaker-color-correction` from the camera original; cutout is cut from the corrected plate | baked `aroll.mp4` |
| 4 | Spec | write PROMPT.md + DESIGN.md (`references/prompt-md-skeleton.md`; a project made with `new_project.py --starter talking-head` already holds a DRAFT with the house preset typed in and every open question marked ASK); run `scripts/plan_lint.py` on `edit_plan.json` | G1 approval |
| 5 | Assets, one batch | footage/3D/UI by the beat table; licence row per asset in `hf/SOURCES.md` | `hf/assets/` |
| 6 | Build, fixed order | cut -> picture lock -> graphics -> captions -> colour check -> sound (`hf_mix`) | `index.html`, `cues.js` |
| 7 | Verify cheap -> expensive | `hf_preflight --strict` -> `check` -> snapshots -> Studio -> `hf_segment` ranges -> ONE full render -> `qa delivery` | `render-qa-delivery` |
| 8 | Present / revise | numbered by the author's notes; batch notes first (`revision-notes-handler`) | CHANGELOG round |

## Gates
States are `pass | fail | blocked | n/a` with a reason. A timeout, empty sample or missing input is `blocked`, never `pass`. A successful tool call is execution evidence; a viewed frame is appearance evidence.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 spec approved | PROMPT.md holds ledger + per-range edit spec (beat, zoom, caption, cover for every hidden cut, SFX dB); human approval recorded before the first composition code | approval message id + time in `hf/CHANGELOG.md`; PROMPT.md mtime < first `index.html` mtime | stop, get approval; never write the spec after the build | this skill + human | any intent change: new ledger row, re-approve the rows |
| G2 cuts | natural order, whole sentences; in-point 0.06 s inside the silence before the sentence; no piece < 6 frames; first 2 and last 2 words of every kept sentence present in the assembled VO | `join_diff` of FULL assembled-VO ASR vs source words; extra token = fail | re-cut the join; keep a natural "אז" whole, drop it from captions only | this skill | every re-cut |
| G3 hidden cuts | every `source_cuts` hit inside a used range is covered by B-roll/zoom with >= 6 frames margin each side or the point moved; no A->A join under 15 % scale change without a cover | `source_cuts --edit` lists 0 uncovered; `plan_lint` G3 block; frame diff c-1..c+2 shows one spike | extend the cover or move the point | this skill | re-cut, new source file |
| G4 face-centred camera | `faces.json` faceX logged at every zoom; path smoothed per segment, never per-frame follow; whole-film audit | `face_center audit --tol 30` 0 confirmed ranges (hits are candidates: confirm on a frame); `motion_qa --acc 1500` 0 stutter ranges | re-solve `camera_path`, re-pass the cut frames as `--cuts` | this skill | any zoom/cut change: re-audit the WHOLE film |
| G5 beat policy | stated cadence (default 3-6 s) holds; every beat typed from the menu, full-bleed, real/3D/UI/data; no AI-looking people stills; overlay cards <= 860 px, under the chin, box disjoint from the face | beat table in PROMPT.md vs timeline; `plan_lint` G5 block; `motion_scan` (no >= 1.5 s with < 1 event/s) | "boring / looks AI" = replace the beat concept, do not polish | this skill | beat table edited |
| G6 captions | house preset or an approved alternative; exit + entrance; dwell word >= 0.25 s, card >= 0.9 s; rail bottom <= y 1450; look-alike test done | `caption_qa --band <top>:1450` with its coverage statement + `hebrew-captions-transcription` G1-G8 | fix and re-run | `hebrew-captions-transcription` | any caption/font change |
| G7 colour handoff | plate baked from the camera original, no `data-color-grading`, cutout cut from the corrected plate, 6-frame pre-roll | `color_check` PASS (named preset) + first 3 frames of every A-roll return viewed | re-bake (`grade_bake` / `color_render`) | `speaker-color-correction` | new plate or new grade |
| G8 round discipline | preflight -> check -> snapshots -> Studio -> ranges -> exactly ONE full render per round | `_work/timing_ledger.jsonl`: full renders in the round = 1 | stop extra renders, batch the notes | `render-qa-delivery` | each new round |

## Craft numbers (details in references)
- **Zoom rhythm:** opening push-in (<= 1.0 s from start), punch-in on emphasis words, punch-out on new sentences, an event every 2-4 s, eased only; a hard scale change only on a cut and >= 15 % to hide a join; push-ins <= x1.16 over 3-4 s; with captions on the chest cap the zoom at x1.40 (project note: x1.44 put the chin into the captions). `references/camera-and-zoom.md`.
- **Camera path:** `camera_path` smooth, sigma 0.6 s (0.5 tighter, 0.8 calmer) per segment between cuts; rig `#zoom` wraps `#pan`, one proxy tween. Measured on one swaying take: per-frame follow 2782 px/s^2 vs smooth 139 px/s^2 (d06-th §1.5).
- **Beats:** one that SHOWS the sentence every 3-6 s (state your number in PROMPT.md; sources disagree, see `references/beat-menu.md`), layered hook in 0-1.5 s, full-bleed always, ids from the menu.
- **Cutout:** only when a beat puts graphics behind the speaker; `python tools/cutout.py <corrected plate> -o hf/assets/video/speaker.webm --from S --to S --cut-at ...`: route `native` (HyperFrames `remove-background`, the safe default), `onnx` (your own MODNet-style model via `--model`), or `external` (an alpha you made with RVM, GPL-3.0, installed by you and never bundled); range-only, per shot segment, cached by decoded content, started at minute 0; `references/cutout-matte.md`.
- **Captions:** house preset Rubik (Black keywords, Regular small words), 1-3 words, animate in and out; owner said "default, not law" (Q5). `hebrew-captions-transcription`.
- **Sound:** bed ~4 dB below the first level on speech edits (owner "approximately"), SFX -18...-26 dB only on visible events, master measured on the final file: `render-qa-delivery`.

## Timing budget (modelled, not measured)
40 s reel, the reference machine, T24 model: 149.5 min today -> 89.5 min with the review policy alone -> 60.9 min + H with a range-only matte; >= 50 % total saving needs H <= 13.9 min. No student measurement exists: write your own `_work/timing_ledger.jsonl` and report measured vs modelled (`references/round-and-budget.md`).

## Pitfalls that each cost hours
Built on the 1080p rough cut while a 4K original sat unseen; restructured without asking (about 4 h); in-point dropped "אני"; centring fixed in one section only (audit the whole film); stale timing grid after a re-cut; overlay card crossing the face; caption on the mouth; per-frame face follow = jitter; 23 full renders for 7 note rounds where 9 sufficed.

## References (load when)
- `references/beat-menu.md` - choosing or replacing a beat, hook, overlays, B-roll policy.
- `references/camera-and-zoom.md` - designing zooms, solving the camera path, audits.
- `references/cut-and-joins.md` - cutting, silence constants, joins, hidden source cuts, A-roll prep.
- `references/cutout-matte.md` - any beat with graphics behind the speaker.
- `references/prompt-md-skeleton.md` - before writing PROMPT.md and `edit_plan.json`.
- `references/round-and-budget.md` - before a notes round; when reporting time.
- `references/volatile-facts.md` - before quoting any measured number, licence or version.
- Other skills: `video-brief-intake`, `speaker-color-correction`, `hebrew-captions-transcription`, `render-qa-delivery`, `revision-notes-handler`, `paid-spend-gate`. Techniques owned elsewhere: `agent-content/techniques/{frame-spec-prompt,clean-smooth-motion}.md`.
- Script: `scripts/plan_lint.py` (stdlib; Usage in its docstring; `--self-check`; script paths are relative to this skill's folder).
- Repo-level dated modules (owned elsewhere; load when you need their tables): `agent-content/references/matte-routes.md`, `agent-content/references/hyperframes-traps.md`, `agent-content/techniques/studio-review-loop.md`, `agent-content/techniques/timing-ledger.md`; rubric for review: `agent-content/benchmarks/talking-head.rubric.md`.

## Evidence status
Built from four real speaker projects plus lab experiments E08-E12; no RED/GREEN model evals; the author's "+7 % person brightness" and beat-cadence numbers are assistant translations, not owner quotes. Specified; deterministic checks only; model eval not run (Q4). Legend: d06-th = distilled 06 talking-head-and-footage, checked 2026-10-02.

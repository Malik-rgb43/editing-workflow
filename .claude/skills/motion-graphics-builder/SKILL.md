---
name: motion-graphics-builder
description: >-
  Design, build and review a motion-graphics piece in HyperFrames/GSAP: product or app launch, feature announcement, kinetic typography, logo reveal, UI explainer, animated screenshots. Triggers: מושן גרפיקס, אנימציה, השקה, טיפוגרפיה קינטית, לוגו אנימציה, "like a Higgsfield / Linear launch". Not for a speaker-to-camera reel (talking-head-editor), AI-generated shots (ai-generated-video-editor), caption-only work (hebrew-captions-transcription) or ad compliance (ad-promo-editor).
compatibility: >-
  HyperFrames + GSAP (pins in references/dated-versions.md); Python >= 3.9 for scripts/ (stdlib only); Blender and Three.js optional per beat.
metadata:
  version: "0.1.0"
  kind: type
  status: "specified; deterministic checks only; model eval not run"
---

# motion-graphics-builder

Outcome owner for a finished motion piece (MP4) built as HyperFrames HTML + one paused GSAP timeline. The frame-level PROMPT.md is the product; the code only renders it.

## Non-negotiable rules (read first)
1. **No code before an approved frame-level PROMPT.md** - also in autonomous runs: the agent drafts, a human approves (decision default Q6). Approval is a recorded line `APPROVAL: <who> <date>` in the file. Change order is always ledger -> PROMPT.md -> code.
2. **No spend here.** AI-3D, AI stills or any paid generation go through `paid-spend-gate`; this skill makes no paid call. A catalogue listing is not account access.
3. **Review order:** Studio preview -> `hf_segment` ranges -> ONE full render per round of notes -> every-frame QA on the final render. One heavy job at a time (`render_lock`). Batch the notes; diagnose while the user is still writing, but do not render.
4. **Hard traps:** no `dir="rtl"` on the HyperFrames root (RTL on text elements only, `lang="he"` on `<html>`); fonts from files (`@font-face` in `hf/fonts/`); `hyperframes snapshot --describe false`, <= 5 timestamps per call; ASCII work root (`new_project`).
5. **Fail closed:** a gate that cannot run is `blocked` (`not_run`), never `pass`. A timeout, an empty sample or a missing render never passes. A successful tool call is execution evidence; a viewed render is appearance evidence; a still cannot prove motion.
6. **Law vs taste:** rules 1-5 are law. Items marked *studio style* below (no captions by default, banned list, "no pink", Higgsfield grammar, 21st-first) are the author's taste, taught with their reason; a brief that says otherwise wins on taste, never on gates.
7. **Numbers carry their fps** (30 unless the brief says otherwise) and measured timings carry the machine (the reference machine). NVIDIA/Apple timings are unmeasured. Projects restricting spend, installs or publication override this skill.

## Inputs -> outputs
In: brief/ledger (from `video-brief-intake`), brand kit, UI screenshots or components, music/VO. Out: `hf/PROMPT.md` (frame-level), `hf/DESIGN.md` (one locked palette + type + motion tokens), `hf/cues.js` (single timing source for picture and sound), `hf/SOURCES.md`, the composition, `mix.wav`, the final MP4, QA reports. Handoffs: notes -> `revision-notes-handler`; other ratios -> `video-variants-exporter` (full re-layout, never a crop); delivery gate -> `render-qa-delivery`; a reference given -> `reference-style-matching` first (no reference -> ask which time range is "the style").

## Procedure
1. **Register + intake.** Pick one register (`launch | kinetic | logo | explainer | calm`) and lock length, ratios, VO, music, deliverable name (`references/launch-register-and-pace.md`). A 30 s dense launch felt x1.7 too fast; the approved length was 45 s: decide length first.
2. **Draft PROMPT.md + DESIGN.md** (6 blocks; the camera, seam and event tables; beat cards for any 3D). Run `python scripts/motion_spec_check.py hf/PROMPT.md --register <r>`; fix; ask for approval.
3. **Source beats** (`references/ui-sources-and-port.md`): catalog -> hf-blocks (`python tools/hf_blocks.py list`, then `add <block> <hf-dir>`) -> shadcn registries via `python tools/ui.py search` (default) -> 21st.dev only with an account -> hand-build; decide 3D per beat (`references/three-d-decision.md`; AI-3D such as Tripo only if the student connected it, otherwise Blender, or Three.js if they choose it).
4. **Build** one `index.html` + `cues.js`; ported components re-authored seek-safe. Then `hf_preflight --strict`, `python scripts/seek_safe_scan.py hf/`, `python scripts/palette_audit.py hf/DESIGN.md hf/ [--png <3D renders>]`.
5. **Approve visually:** four stills + a snapshot of every seam + `sheet` contact sheet; Studio preview; notes batch.
6. **Sound** (`references/sound-and-captions.md`): `hf_mix --report`; brand sound on every brand event; mux and measure the final file. Captions only if the brief asks, and then built with `hebrew-captions-transcription`.
7. **One full render** under the lock with an ETA first; `frame_qa`, `motion_qa`, `hf_deliver`; score with `agent-content/benchmarks/motion-graphics.rubric.md` using a separate critic; present the file, numbered changes, the ledger ticked and the honest gaps.

## Register at a glance (details: `references/launch-register-and-pace.md`)
| Register | New screen | Event cadence | Camera | Sound |
|---|---|---|---|---|
| `launch` | every 2-6 s, >= 2 depth layers | <= 0.5-1 s; 45-110/min by hand count | never stops (drift 2-4 %/s, push-ins 8-15 %) | music is the SFX; brand sound on every brand event; ring-out |
| `kinetic` | every 1-3 s | up to ~200/min (word swaps count) | type is the camera | keyword lands 0..+7 f after it is spoken |
| `logo` | one idea, 3-8 s | result visible by 0.4-0.75 s | one move + settle | brand sound on the reveal; 3-step ending |
| `explainer` | per idea, 3-6 s | 30-110/min | purposeful, to the object explained | VO-led; SFX only on visible change |
| `calm` | holds allowed | sparse is fine | slow or locked | one uniform bed + subtle foley; no risers/drops |

## Per-beat 3D in five lines
Decide per beat, write the reason in PROMPT.md: **Blender** for real geometry / hero material on screen > 2 s (EEVEE first; measured 1.2-2.25 s/frame at 384-640 px, +1-1.5 min per launch); **Three.js** for data-driven, instanced, 3D-UI-with-live-text, edit-in-rounds or exact-hex beats, after a 1 s `hf_segment` AMD gate; **AI-3D** only behind `paid-spend-gate` and a licence check; a still that needs a small move gets a plain HyperFrames camera move (push-in or pan); **none** for UI/message beats. A 3D object never covers information and reacts to the word.

## "Boring / looks AI / static" at a timestamp
Replace the beat concept, do not polish it. Pick from the menu: a voice orb driven by the real VO spectrum; a data-driven build (bars, counters, route globe); the UI rebuilt in code and shot as an object (perspective, depth of field, 150-300 % magnification); a shared-element morph that carries content; a number or word swap in place; a 3D hero landing on the keyword. Never a small corner "feature pill", a flat screenshot with a small push-in, or a dot on black. Add the note to the Banned line and fix it at every occurrence (global rule when it repeats).

## Time budget (modelled or measured on the reference machine; not student measurements)
Target: first presentable draft of a 30-45 s launch in about 3-4 h with 1-2 correction rounds (the first real launch took 10 drafts, 7 critic rounds, 4 owner-note rounds); exactly ONE full render per round. Render reference (HyperFrames 0.8.98, E11, heavy 40 s / 1200 f): 1 worker 132.6 s, 4 workers 92.8 s, 8 workers 88.1 s; browser GPU -12 %; capture is the bottleneck (CPU use only 2-3 of 16 logical cores). Earlier premium renders: 8-14 min typical, 4-21 observed (0.8.79-0.8.93). Always benchmark one unit and post an ETA line before a job over 3 minutes.

## Gates
States: `pass | fail | blocked | n/a`, always with a reason.

| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G0 intake | register, length, ratios, deliverable name, VO/music source, reference answer recorded | `hf/BRIEF.md` | ask (3-4 questions per round); blocked | video-brief-intake | brief changes |
| G1 frame-level spec | 6 blocks; every beat has frames + px + easing + sound + transition; Banned line; hex palette; `APPROVAL:` line | `motion_spec_check.py` exit 0 (2 = approval missing = blocked) | fix spec; stop before code | this skill + human approver | any retime or new beat |
| G2 clean & smooth | ONE spline per scene, each move >= 1.2 s, reversals >= 1 s and <= 1.3x, text inside frame at every key; seams exit = entry, hero persists, no repeated technique, no fade | tables in PROMPT + checker; `motion_qa` 0 stutter ranges on the render | re-time / re-path; replace the beat concept rather than polish | this skill | any camera or seam change |
| G3 density | per register: launch = new screen every 2-6 s, event gaps <= 0.7 s (declared breaths excepted), 45-110 events/min (hand count) | Events table + 3 frame samples per scene | add or replace beats; stretch long moves x1.6 instead of cramming | this skill | after any retime |
| G4 3D per beat | every 3D beat has a card: route (Blender / Three.js / AI-3D / none), a one-sentence reason, ETA, gate evidence, licence | beat-card table; Three.js rows: a 1 s `hf_segment` frame that is not blank | re-decide; AI-3D rows need `paid-spend-gate` | this skill | new beat or asset |
| G5 palette lock | one palette table; every hex in sources and every 3D render inside it | `palette_audit.py` exit 0 (+ `--png`) | recolour / re-render; blocked if no table | this skill | new asset, new render, colour note |
| G6 UI sourcing | each UI/effect beat has a `SOURCES.md` row (origin, licence, version, date) and a seek-safe port; no `npx shadcn add` in a project; no 21st preview/media copied | SOURCES.md + scan | swap source or hand-build with a reason | this skill | new component |
| G7 seek-safe | `hf_preflight --strict` 0 errors; `seek_safe_scan.py` 0 errors; snapshots at non-sequential times agree | reports + snapshot pair | fix; never "fix" by suppressing without a reason | this skill | after every code patch |
| G8 sound | brand sound on every brand event; SFX under VO within -18..-26 dB and 1-3 f before picture; music rings out; final file -14 LUFS +-0.5, TP <= -1 (house preset v1, Q5) | `hf_mix --report`, `hf_deliver` verify on the FINAL file | re-mix and remux (no re-render) | render-qa-delivery measures | any audio or picture retime |
| G9 captions | no caption elements unless the brief asks | grep of ids/classes + `<direction>` line | remove / ask in one line | this skill | brief change |
| G10 render + QA | ONE full render this round; `frame_qa` 0 flags; rubric average >= 4.0, no dimension < 3, M1/M3/M7 >= 3; every ledger line ticked | QA reports + critic output | back to the failing gate; max one correction round before escalating | render-qa-delivery | each full render |

## Recording gate results (`hf/QA.md`, one line per gate)
```
G1 pass   motion_spec_check exit 0, 24 beats, approval "<who> 2026-10-02"  (re-run after r2 retime: pass)
G5 blocked  3D render coin_r2.png not readable by palette_audit (not_run) - install Pillow or downscale
G7 fail   seek_safe_scan SS02 index.html:211 Math.random -> seeded hash; rescan pending
```
A gate with no line is `not_run`. Never write `pass` from memory of an earlier round: a retime, a new asset or a patch invalidates it (see the Recheck column).

## Presenting a draft (render-qa-delivery owns the delivery gate)
Message = the file at once + numbered changes (by the user's own note numbers) + the ledger with every line ticked + the rubric score from the separate critic + the gaps (what was NOT verified: Hebrew proofread, device overlay, loudness on a phone) + the Studio link. Never present with a flagged frame, a failed gate or an unticked ledger line.

## References (load when)
- `references/seam-camera-event-tables.md` - ALWAYS when writing or reviewing PROMPT.md; also `agent-content/techniques/frame-spec-prompt.md` and `clean-smooth-motion.md`.
- `references/launch-register-and-pace.md` - choosing the register, pace complaints, banned list, easing numbers.
- `references/three-d-decision.md` - any beat with depth or 3D.
- `references/ui-sources-and-port.md` - UI cards, effects, screenshot animation; `agent-content/techniques/screenshot-rebuild.md`.
- `references/seek-safe-and-render-traps.md` - writing code, patches, render differences.
- `references/palette-lock.md`, `references/typography-hebrew-kinetic.md`, `references/sound-and-captions.md` - DESIGN.md, Hebrew type, the sound plan.
- `references/dated-versions.md` - pins and licences (dated; expired = unknown).
- Scripts (`python <script> --self-check` first): `motion_spec_check.py`, `palette_audit.py`, `seek_safe_scan.py`. They check text and patterns, never appearance.

## Stop and escalate
Blocked, not guessed: no approval line; no render possible; a gate input missing; a price or licence unknown; a Three.js beat whose 1 s segment is blank on AMD (fall back to a Blender sprite). Ask before any spend, install, publication or message to a third party. Never message other agent sessions. A user note "boring / looks AI / static" at a timestamp means replace the beat concept from the register's menu, in one line of explanation.

## Maintenance
Volatile facts live only in `references/dated-versions.md` and the global dated modules (`hyperframes-traps.md`, `three-d-routes.md`, `audio-mix.md`). Add every new owner note to the Banned line, not to this file. Specified, deterministic checks only; model eval not run (decision default Q4).

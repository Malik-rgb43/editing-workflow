---
name: video-variants-exporter
description: >-
  Deliver one approved video as several outputs (other aspect ratios, hook variants, platform versions, no-music/no-captions versions) or run several videos in parallel, with one shared mix, strict naming and a manifest that blocks stale derivatives. Triggers: export as 9:16 and 1:1, hook variants, variants batch; גרסאות, וריאציות הוק, כמה סרטונים יחד, 9:16 ו-16:9. NOT for a single deliverable (render-qa-delivery) or designing the master (the type skill).
compatibility: >-
  scripts/manifest_check.py needs only Python 3.9+ (ffprobe optional). Presets and speeds quoted in references are house preset v1 / measured on one reference machine; NVIDIA and Apple cells are unmeasured.
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# video-variants-exporter

Turns ONE approved master into N outputs without losing control of which file came from which source state. It owns the variant matrix, the master freeze, the re-layout copies, the shared mix, the naming, the one-render-at-a-time queue, the agent supervision rules and the manifest gate. It does not design the master (the type skill does) and does not replace per-file QA (`render-qa-delivery`).

## Rules that outrank the rest of this file
1. **Master first, then frozen.** Derivatives are made only from a master that passed its own full QA and is recorded with `manifest_check.py freeze`. A fix needed later is made in the MASTER, logged with `change`, carried to every copy in the same round, and every derivative is re-rendered and re-recorded. Fixing only a copy is forbidden.
2. **Re-layout, never crop.** Each aspect is a copy of the master source (`hf_9x16/`, `hf_1x1/` ...) with its own canvas, safe zones, type scale, caption rail, camera keys and face centring. An FFmpeg crop or scale of a rendered master is not a variant.
3. **One mix.** Re-layouts and hook variants use the same `cues.js` and the same `assets/mix.wav` bytes and are muxed from that one file; audio is not rebuilt per variant. A variant that really needs its own mix (no-music, own voice-over, re-cut length) declares it in the manifest with a reason.
4. **One heavy job at a time on the whole machine** (render, `check`, matte, ASR, Blender) under `render_lock`. Parallel work is limited to non-heavy tasks (layout, spec, QA reading). At most 4 agents in parallel, each with at most 2 sub-agents.
5. **"Ready" is computed, not asserted.** The word is allowed only when `manifest_check.py check` exits 0. A timeout, empty folder, missing hash, `qa: not_run` or missing evidence is `blocked` / `INSUFFICIENT_EVIDENCE`, never `pass`.
6. No paid action without `paid-spend-gate`; never message another Claude session; user and project restrictions override this procedure. Safe zones, -14 LUFS and canvases are **house preset v1** (decision default Q5), not platform law.

## Inputs -> outputs
In: approved master (`hf/`, PROMPT.md, DESIGN.md, `cues.js`, `assets/mix.wav`) and the variant matrix from intake. Out: `final/<name>_<platform>_<hook>_<aspect>.mp4` x N, `final/manifest.json` (finals + manifest only), per-file QA reports under `_work/qa/<aspect>/<round>/`, `_work/agents/<agent>.progress.md`, `_work/STATE.md` (queue).
Naming: `<name>_<platform>_<hook>_<aspect>.mp4`, `<name>` a lowercase ASCII slug (underscores allowed), `<platform>` = `meta|tiktok|yt|ig|linkedin|x|all`, `<hook>` = `master | hookA | hookA-nomusic | hookA-nocaps`, `<aspect>` = `9x16|4x5|1x1|16x9`. Also accepted: the short per-ratio form `<name>_<aspect>.mp4` (platform `all`, hook `master`, as in the delivery playbook). A name the user asked for in the ledger overrides the convention and is recorded with its ledger id (`record --name-ledger-id`).

## Procedure
| # | Stage | Do | Artifact |
|---|---|---|---|
| 0 | Matrix at intake | one ledger row per file: aspect, platform, route (organic / ad / spark), hook, version (full, no-music, no-captions, length), master aspect. Late "maybe" ratios: write layout notes now so a late request is one agent, not a rebuild (`references/variant-matrix-and-layout.md`) | matrix in PROMPT.md `<inputs>`; `matrix` list in the manifest |
| 1 | Master gate | master approved, `render-qa-delivery` all-frame QA passed, `manifest_check.py freeze <project> --hf hf --matrix ...` | frozen `src_hash` + `mix_sha256` |
| 2 | Re-layout copies | one agent per aspect on a COPY; same cues and mix; fill the layout table (what changed per element, `references/variant-matrix-and-layout.md`); preflight 0 errors; snapshot overlay at hook, offer, end card (`--describe false`, at most 5 timestamps per call) | `hf_<aspect>/`, `_work/qa/<aspect>/layout.md` |
| 3 | Hook / version variants | hook = sub-composition bound to variables in the aspect's copy, one row per variant; test ONE variation first (batch variables are untested in a project); mux the shared mix; no-music / no-captions = declared mix or layer variants | `rows.json`, variant files |
| 4 | Queue | write the render order in `_work/STATE.md` (master, then each aspect, then variants); `manifest_check.py stamp` BEFORE each render; renders through `hf_deliver` / `render_lock run` one at a time; a render owner never starts a second heavy job | lock log, stamps |
| 5 | Record | after each render: `record` (hashes, applied master fixes, mix variant, QA state, loudness measured on the FINAL file) | `manifest.json` |
| 6 | Per-output QA | `frame_qa`, `caption_qa --band <top>:1450` (9:16), `motion_qa` if layout changed motion, `face_center audit` for speaker footage, `qa delivery`; visual review axes 1 (composition/crop) and 4 (readability) only; axes 2-3 inherited unless motion changed | reports + evidence paths |
| 7 | Ready gate | `manifest_check.py check <project> --json` exits 0; show the user the file list with source hash, QA state, LUFS/TP; list gaps honestly | READY report |
| 8 | Learn | timing ledger lines per file, lessons for the Inbox | `_work/timing_ledger.jsonl` |

## Gates
States are `pass | fail | blocked | n/a` with a reason. A timeout, empty sample or missing input is `blocked`, never `pass`. A successful tool call is execution evidence; a viewed render is appearance evidence.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 matrix | every output has a ledger row (aspect, platform, route, hook, version) before any build | `matrix` in PROMPT.md and manifest | ask the missing axis now; do not build first | this skill + `video-brief-intake` | any new ratio/variant request |
| G2 master frozen | master passed full QA; `freeze` recorded; no derivative started earlier | manifest `master.src_hash`, `frozen_utc` older than every stamp | stop derivatives; freeze | this skill | any master source change |
| G3 re-layout | each derivative has its own root canvas, per-element layout row, safe zones of its aspect; no cropped master render | `layout.md` rows + overlay snapshots + preflight 0 E | re-lay out the failing element; do not scale the whole frame | the aspect's agent | master layout change, new copy |
| G4 shared assets | `cues.*` and `assets/mix.wav` identical to the master in every re-layout/hook copy; hook variants mux, not re-mix | `manifest_check.py check`: no M035/M041 | copy the master cues/mix back; re-render | this skill | master cue or mix change |
| G5 per-output QA | each file `qa: pass` with an evidence file and LUFS -14 +/- 0.5, TP <= -1 on the final file (house gate) | `qa_evidence` path, `lufs`, `tp` numbers in the manifest | fix and re-render ONLY that file | `render-qa-delivery` | any re-render |
| G6 heavy-job discipline | exactly one heavy job at a time; <= 4 agents, each <= 2 sub-agents, each with file list, output file, deadline, progress file | `render_lock` log; `_work/agents/*.progress.md` mtimes | queue, stop the extra job (own process tree only) | this skill | each agent launch |
| G7 manifest ready | stale / orphan / missing / changed-after-render all absent | `manifest_check.py check` exit 0 | list the failing files to the user; re-render the stale ones | `manifest_check.py` | before saying "ready", after any change |

## Numbers (house preset v1, dated 2026-10-02, details in `references/house-presets.md`)
- Canvases: 9:16 1080x1920, 4:5 1080x1350, 1:1 1080x1080, 16:9 1920x1080; H.264 SDR yuv420p, AAC 48 kHz, 30 fps default.
- Safe zones, key text/CTA/logo/price: 9:16 top 300 / bottom 672 (y <= 1248) / left 140 / right 192, caption rail bottom <= y 1450; 16:9 x <= 1824, top 54, bottom 162; 4:5 and 1:1 54 px each side. Unverified on devices: run the overlay exercise.
- Loudness: -14 LUFS integrated +/- 0.5, true peak <= -1 dBTP, measured on the final file; mix intermediate TP <= -1.5.
- Supervision: heartbeat check about every 15 min; silent or past its deadline for 20 min = check, replace or stop; status line to the user about every 10 min of silence; render timeout 3 x the measured ETA. (src: distilled 02 workflow §13.6, 2026-10-01)

## Decision rules
| If | Then |
|---|---|
| a master fix is needed after derivatives exist | fix the MASTER, `change`, carry the patch to every copy, re-render and re-record all of them |
| a copy needs different timing or cues | that is a master change; or a new edit (`recut`) with its own ledger lines, never a silent fork |
| a hook needs a different spoken line | declare `own-vo` with a reason; every other variant stays on the shared mix |
| a ratio is requested late | write the layout table, spawn ONE agent on a copy of the frozen master; do not touch the master |
| two renders are requested at once | queue them; the lock decides; write the order in `STATE.md` |
| an agent is silent past its deadline | check its progress file, then replace or stop it (own process tree only), then `render_lock status` |
| the finals folder holds an old render | move it to `_work/delivered/v<N>/`; "ready" is blocked until the folder matches the manifest |
| the user names the files | their name wins; record it with `--name-ledger-id` and keep platform/hook/aspect fields explicit |

## Blocked states (report them, do not work around them)
`manifest_check.py` BLOCKED or INSUFFICIENT_EVIDENCE; a derivative with a stale `from_master` or a missing master fix; a changed-after-render source; shared cues or mix drift; `qa` not `pass`; a promised variant missing; an unplanned file present. Say which file, which code, and the fix.

## Pitfalls that each cost real time
Late 16:9 request at delivery (a full re-layout, dropped); a master fix of 3.7 s not carried to the 1:1; an old render left beside the new ones and nobody flagged it; a derivative agent that found a master bug and fixed only its copy; three agents rendering at once (a parallel Blender job doubled a render, 11.5 to 21.5 min, the reference machine); naming collisions between Meta and TikTok cuts; one hook variant silently carrying a different mix. A viewed contact sheet of each aspect is still needed: hashes cannot see a caption on a face.

## References (load when)
- `references/variant-matrix-and-layout.md` - writing the matrix, re-laying out an aspect, hook/no-music/no-captions/length variants.
- `references/manifest-schema.md` - recording files, reading `manifest_check.py` findings, the stale-derivative lifecycle.
- `references/parallel-and-agents.md` - launching agents, queue, lock, heartbeats, stopping, token budget.
- `references/house-presets.md` - before quoting any canvas, safe-zone, loudness or platform number (dated module).
- `agent-content/references/platform-specs.md` (canonical platform facts, owned elsewhere) and `agent-content/playbooks/wf-08-deliver.md` (delivery playbook: naming, manifest rules) - export presets and the playbook; if a number differs, the canonical file wins and `references/house-presets.md` is updated.
- Other skills: `render-qa-delivery` (per-file QA), `hebrew-captions-transcription` (caption rail), `ad-promo-editor` (hook ranking), `revision-notes-handler` (notes across aspects), `paid-spend-gate`.
- Scripts: `scripts/manifest_check.py` (`--self-check` 29 cases, exit 0 READY / 1 BLOCKED / 2 INSUFFICIENT_EVIDENCE) and `scripts/test_manifest_check.py` (unittest).

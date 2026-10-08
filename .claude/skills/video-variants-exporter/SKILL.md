---
name: video-variants-exporter
description: >-
  Deliver one approved video as several outputs (other aspect ratios, hook variants, platform or language versions, no-music/no-captions versions) or run several videos in parallel. Triggers: export as 9:16 and 1:1, hook variants, an English and a Hebrew version, variants batch; גרסאות, וריאציות הוק, גרסה באנגלית, כמה סרטונים יחד, 9:16 ו-16:9. NOT for a single deliverable (render-qa-delivery) or designing the master (`pro-video-editor`).
compatibility: >-
  scripts/manifest_check.py needs only Python 3.9+ (ffprobe optional). Presets and speeds quoted in references are house preset v1 / measured on one reference machine; NVIDIA and Apple cells are unmeasured.
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# video-variants-exporter

Turns ONE approved master into N outputs without losing control of which file came from which source state. It owns the variant matrix, the master freeze, the re-layout copies, the shared mix, the naming, the one-render-at-a-time queue, the agent supervision rules and the manifest gate. It does not design the master (`pro-video-editor` does) and does not replace per-file QA (`render-qa-delivery`).

## Start: connections
If `<project>/_work/connections.json` from this session exists (written by the router or `pro-video-editor`), read it; otherwise run `python tools/connections.py -o <project>/_work/connections.json` (about 1 s, presence only) and read your own tool list (claude.ai connectors appear only there). For this skill: the pinned HyperFrames CLI (re-layout snapshots and renders), FFmpeg/ffprobe (mux, probes, loudness), the browser pane (to open each aspect's contact sheet and the files for the user); a publishing connection (a platform MCP or API) only with the user's explicit yes for each post. Say use / not needed / fallback in one line, then continue. A missing connection never stops the work; anything paid goes through `paid-spend-gate`.

## Rules that outrank the rest of this file
1. **Master first, then frozen.** Derivatives are made only from a master that passed its own full QA and is recorded with `manifest_check.py freeze`. A fix needed later is made in the MASTER, logged with `change`, carried to every copy in the same round, and every derivative is re-rendered and re-recorded. Fixing only a copy is forbidden.
2. **Re-layout, never crop.** Each aspect is a copy of the master source (`hf_9x16/`, `hf_1x1/` ...) with its own canvas, safe zones, type scale, caption rail, camera keys and face centring. An FFmpeg crop or scale of a rendered master is not a variant.
3. **One mix.** Re-layouts and hook variants use the same `cues.js` and the same `assets/mix.wav` bytes and are muxed from that one file; audio is not rebuilt per variant. A variant that really needs its own mix (no-music, own voice-over, re-cut length) declares it in the manifest with a reason.
4. **One heavy job at a time on the whole machine** (render, `check`, matte, ASR, Blender) under `render_lock`. Parallel work is limited to non-heavy tasks (layout, spec, QA reading). At most 4 agents in parallel, each with at most 2 sub-agents.
5. **"Ready" is computed, not asserted.** The word is allowed only when `manifest_check.py check` exits 0. A timeout, empty folder, missing hash, `qa: not_run` or missing evidence is `blocked` / `INSUFFICIENT_EVIDENCE`, never `pass`.
6. No paid action without `paid-spend-gate`; never message another Claude session; user and project restrictions override this procedure. Safe zones, -14 LUFS and canvases are **house preset v1** (decision default Q5), not platform law.

## Inputs -> outputs
Entry: the notes page returned `approved` (`APPROVED <date> (review page, round N)` in `hf/CHANGELOG.md`) and the user wants more outputs; start at stage 1 (freeze).
In: approved master (`hf/`, PROMPT.md, DESIGN.md, `cues.js`, `assets/mix.wav`) and the variant matrix from intake. Out: `final/<name>_<platform>_<hook>_<aspect>.mp4` x N, `final/manifest.json` (finals + manifest only), per-file QA reports under `_work/qa/<aspect>/<round>/`, `_work/agents/<agent>.progress.md`, `_work/STATE.md` (queue).
Naming: `<name>_<platform>_<hook>[_<language>]_<aspect>.mp4`, `<name>` a lowercase ASCII slug (underscores allowed), `<platform>` = `meta|tiktok|yt|ig|linkedin|x|all`, `<hook>` = `master | hookA | hookA-nomusic | hookA-nocaps`, `<language>` = a lowercase language code (`en`, `he`, `ar`, `pt-br`) only on a language version (absent = the master's language), `<aspect>` = `9x16|4x5|1x1|16x9`. Also accepted: the short per-ratio form `<name>_<aspect>.mp4` (platform `all`, hook `master`, as in the delivery playbook). A name the user asked for in the ledger overrides the convention and is recorded with its ledger id (`record --name-ledger-id`).

## Procedure
| # | Stage | Do | Artifact |
|---|---|---|---|
| 0 | Matrix at intake | one ledger row per file: aspect, platform, route (organic / ad / spark), hook, version (full, no-music, no-captions, length), language (and its form: subtitles, burned-in captions or a dub), master aspect. Late "maybe" ratios: write layout notes now so a late request is one agent, not a rebuild (`references/variant-matrix-and-layout.md`) | matrix in PROMPT.md `<inputs>`; `matrix` list in the manifest |
| 1 | Master gate | master approved (`APPROVED` line in `hf/CHANGELOG.md`), `render-qa-delivery` all-frame QA passed on the delivery render, `manifest_check.py freeze <project> --hf hf --matrix ...` | frozen `src_hash` + `mix_sha256` |
| 2 | Re-layout copies | one agent per aspect on a COPY; same cues and mix; fill the layout table (what changed per element, `references/variant-matrix-and-layout.md`); preflight 0 errors; snapshot overlay at hook, offer, end card (`--describe false`, at most 5 timestamps per call) | `hf_<aspect>/`, `_work/qa/<aspect>/layout.md` |
| 3 | Hook / version variants | hook = sub-composition bound to variables in the aspect's copy, one row per variant; test ONE variation first (batch variables are untested in a project); mux the shared mix; no-music / no-captions = declared mix or layer variants | `rows.json`, variant files |
| 3b | Language versions | kind `language`, one copy per language (`hf_<lang>/` or `hf_<aspect>_<lang>/`): the translated text comes from `captions-transcription` translate mode (approved, its `translation_check.py` report = `--translation-evidence`); on-screen words, CTA and captions swapped, the layout mirrored when the direction changes (rows in `layout.md`); subtitles and burned-in captions share the master mix; a dub is `own-vo` and needs `--voice-consent` and `--spend-approval` (`paid-spend-gate`) (`references/variant-matrix-and-layout.md` section 4b) | `hf_<lang>/`, `layout.md`, the language file |
| 4 | Queue | write the render order in `_work/STATE.md` (master, then each aspect, then variants); `manifest_check.py stamp` BEFORE each render; renders through `hf_deliver` / `render_lock run` one at a time; a render owner never starts a second heavy job | lock log, stamps |
| 5 | Record | after each render: `record` (hashes, applied master fixes, mix variant, QA state, loudness measured on the FINAL file) | `manifest.json` |
| 6 | Per-output QA | `frame_qa`; `caption_qa` only if the file has captions, with the aspect's band (9:16 bottom y 1450; other aspects: `references/variant-matrix-and-layout.md` section 3; no captions = skip); `motion_qa` if layout changed motion, `face_center audit` for speaker footage, `qa delivery`; a contact sheet per aspect, opened in the browser pane and looked at (hashes cannot see a caption on a face); visual review axes 1 (composition/crop) and 4 (readability) only; axes 2-3 inherited unless motion changed | reports + evidence paths + one viewed sheet per aspect |
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
| G5 per-output QA | each file `qa: pass` with an evidence file and LUFS -14 +/- 0.5, TP <= -1 on the final file (house gate); a contact sheet per aspect was opened and looked at | `qa_evidence` path, `lufs`, `tp` numbers in the manifest; the sheet path per aspect and what was seen on it | fix and re-render ONLY that file | `render-qa-delivery` | any re-render |
| G6 heavy-job discipline | exactly one heavy job at a time; <= 4 agents, each <= 2 sub-agents, each with file list, output file, deadline, progress file | `render_lock` log; `_work/agents/*.progress.md` mtimes | queue, stop the extra job (own process tree only) | this skill | each agent launch |
| G7 manifest ready | stale / orphan / missing / changed-after-render all absent | `manifest_check.py check` exit 0 | list the failing files to the user; re-render the stale ones | `manifest_check.py` | before saying "ready", after any change |

## Numbers and supervision
Canvases, safe zones and loudness: `references/house-presets.md` (house preset v1, dated). Two different heartbeats: the **agent heartbeat** (the main session reads each agent's progress file about every 15 min; silent or past its deadline for 20 min = check, replace or stop) and the **render heartbeat** of the long-job protocol (the running job writes a `STATE` line about every 5 min; render timeout 3 x the measured ETA). Status line to the user about every 10 min of silence (`references/parallel-and-agents.md`).

## N masters (several different videos at once)
One project per video, each with its own PROMPT.md, ledger, freeze, matrix and `final/manifest.json`; shared assets (DESIGN.md, music, caption kit) are copied from the first project. Build work runs in parallel within rule 4's agent caps; every render of every project goes into ONE queue (one `_work/STATE.md` in the first project lists them all), and `render_lock` still allows one heavy job on the machine. "Ready" is per master: each project's `manifest_check.py check` exits 0.

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
Late 16:9 request at delivery (a full re-layout, dropped); a master fix of 3.7 s not carried to the 1:1; an old render left beside the new ones and nobody flagged it; a derivative agent that found a master bug and fixed only its copy; three agents rendering at once (a parallel Blender job doubled a render, 11.5 to 21.5 min, the reference machine); naming collisions between Meta and TikTok cuts; one hook variant silently carrying a different mix.

## References (load when)
- `references/variant-matrix-and-layout.md` - writing the matrix, re-laying out an aspect, hook/no-music/no-captions/length variants, or a language version.
- `references/manifest-schema.md` - recording files, reading `manifest_check.py` findings, the stale-derivative lifecycle.
- `references/parallel-and-agents.md` - launching agents, queue, lock, heartbeats, stopping, token budget.
- `references/house-presets.md` - before quoting any canvas, safe-zone, loudness or platform number (dated module).
- `agent-content/references/platform-specs.md` (canonical platform facts, owned elsewhere) and `agent-content/playbooks/wf-08-deliver.md` (delivery playbook: naming, manifest rules) - export presets and the playbook; if a number differs, the canonical file wins and `references/house-presets.md` is updated.
- Other skills: `render-qa-delivery` (per-file QA), `captions-transcription` (caption rail), `pro-video-editor` (hook ranking), `revision-notes-handler` (notes across aspects), `paid-spend-gate`.
- Scripts: `scripts/manifest_check.py` (`--self-check` 37 cases, language versions included, exit 0 READY / 1 BLOCKED / 2 INSUFFICIENT_EVIDENCE) and `scripts/test_manifest_check.py` (unittest).

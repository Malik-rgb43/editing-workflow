# wf-00 — Intake (קליטה)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §1 and §6, distilled/02 workflow-end-to-end §2 and §6.3, distilled/01 rules-and-gates A1–A14, research T24.
> Legend (full legend in [README.md](README.md)): `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[IDEA]` · `[CONFLICT]` · 💲 = paid step (must pass `paid-spend-gate`) · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | 0 of 9 |
| Owner skill | `video-brief-intake` (reached through `video-request-router`); references handled in wf-01 |
| Artifacts (exact files) | `projects/<name>/hf/PROMPT.md` (the `<ledger>` block; the six frame blocks are written in wf-03), `projects/<name>/hf/BRIEF.md` (five lines, from [BRIEF.md template](../techniques/templates/BRIEF.md)), `_work/intake/source_ls.txt`, `_work/intake/probe.json`, `_work/STATE.md` |
| Exit gate | **G0 — ledger locked** (below) |
| Target time | **10–20 min** (owner target, human answers + agent asks); never measured on a student |
| Paid steps | none. Starting a trial or signing in to a provider here is **not** spend authorisation |

## 1. Purpose

Turn what the person wrote into a **checkable Concept Ledger** and ask questions in rounds until every parameter is precise. The author's rule: *if there is no reference, ask until it is exact; if there is one, analyse it and ask only what a reference cannot answer.* `[RULE-owner]` Everything downstream is judged against this ledger.

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| a request exists (message and/or files) and `video-request-router` chose a type | the routing line in chat | route first; never start building before it routed |
| the toolkit setup gate has passed on this machine (five states reported; `not_run` ≠ pass) | `doctor` report path | run `doctor`; do not continue to render-time steps until the *first render* state is green |
| `projects/<name>/` can be created under the **ASCII work root** | `new_project` output | pick an ASCII name; keep the Hebrew title only as display text. Never run `npx hyperframes init` under a path with Hebrew letters (it silently skips `index.html`) `[PROVEN-internal]` `[LOCAL-only]` |

## 3. Steps

| # | Step | Who | Evidence / output |
|---|---|---|---|
| 0 | **Read what exists.** The message, attachments, and **`ls -R` of the whole source tree** (a 4K camera original sat unseen next to a 1080p, ~2.2 Mbps rough cut; a folder of 3D assets sat unseen too; the first build, ≈ 1 h, was discarded). `ffprobe` every media file (resolution, fps, rotation, bitrate, audio, colour tags). Check `projects/` for a sibling on the same source ("new project or a continuation of X?" — one line; never adopt a sibling's cut or PROMPT). Look in the person's own assets/transitions folder **before** stock. Source folders are read-only: copy, never move or touch. | agent | `_work/intake/source_ls.txt`, `_work/intake/probe.json` |
| 1 | **Create the project:** `new_project <name> <source files…>` (talking-head: add `` for a DRAFT PROMPT with the house preset typed in and every open question marked ASK); verify the copy (`ls source/`; the original once stopped on a busy folder without copying) and that `hf/index.html` exists. | agent | the listing quoted in chat |
| 2 | **Parse the message into ledger rows** — every concrete word is a row (compound sentences split; the person's words verbatim in `said`; a measurable `spec`; an acceptance check; `src` U/R/D/A). Format and codes: [concept-ledger.md](../techniques/concept-ledger.md). | agent | draft `<ledger>` in `hf/PROMPT.md` |
| 3 | **Branch on what arrived** (table below). | agent | the branch named in chat |
| 4 | **Question loop** — rounds of **3–4 questions**, highest impact first, every option concrete, the first option the recommended default `(מומלץ)` with one line why, previews for visual choices; **BAR (quality bar) in round 1**; never guess platform, length, tone or CTA; after each round print `נעול: … | פתוח: …`. Bank: [question-bank.md](../techniques/question-bank.md). "תמשיך" = take every recommended default, mark `D`, say so in ONE line. | agent asks, **human answers** | owner messages (ids) or the "defaults taken" line |
| 5 | **Start the background lanes** per the parallel schedule (§4). | agent | `_work/STATE.md` lines |
| 6 | **Write `hf/BRIEF.md`** (five lines + intent, no invented facts) and complete the ratio/variant matrix as ledger rows (which ratio is the **master**; hooks A/B/C, platforms, "no music", "no captions", lengths — an un-asked axis cost a rebuild; a Hebrew 16:9 request that arrived at delivery was dropped). | agent | files exist |
| 7 | **Run the ledger check** (reference checker in concept-ledger.md §5), write the gate record, hand off to wf-01 (a reference or a moodboard is needed) or wf-02. | agent | exit code 0; gate record |

### 3.1 Branch table

| Situation | Action |
|---|---|
| reference video / URL / "בסגנון של" / "make it like this" | wf-01 (`reference-style-matching`); then ask only what a reference never answers: length, ratios, structure, CTA, file name, bar, music licence, deadline |
| a reference with several looks (before/after, intro vs body) | ask **which time range is "the style"** before any analysis is used (one test copied the before/after look when the author wanted the FINAL look) |
| a pasted prompt written for another subject | check its topic against the footage; **the footage wins**; one question; its length/structure are not assumed (one such prompt cost ≈ 4 h of a restructured cut later replaced by a full-length cut) |
| the same source as an existing project | one line: "new project or a continuation of X?" |
| "חדש לגמרי" / "don't do anything similar" | zero carry-over: only facts and logo; the previous version's moves go on the Banned list |
| "רק תכנן" / "only a document" | a document deliverable (PROMPT + references + a PDF if asked); **zero generation, zero credits** |
| nothing but text | the question loop |
| a vague creative ask | 2–3 short directions as one question (brainstorm), then the loop |

## 4. Parallel schedule — what starts at minute 0 (resource-admitted, not "all at once")

`[IDEA]` (policy numbers unmeasured) based on the author's measured collisions: a Blender job beside a render doubled render time (11.5 → 21.5 min on OM); a heavy ASR agent beside a render stalled it for about an hour. **One heavy job at a time machine-wide, through `render_lock`.**

| Starts when | Lane | Heavy slot? | Must finish before | Notes |
|---|---|---|---|---|
| minute 0 | probe/hash media, extract audio, read the brief, asset/stock search, a choice board if a visual choice is open | no | wf-02 | lightweight |
| minute 0 (footage) | **`python tools/prep.py <project>`** as ONE background command: sheet → ASR → source cuts → faces → colour scopes → reference analysis, each step under the lock in turn, results in `hf/data/` and `_work/prep/prep.json` (`--plan` shows the steps; nothing is downloaded; a `not_run` step says why) | yes, one at a time | wf-02 | replaces starting the rows below by hand; the rows keep their measurements and limits |
| after audio extraction | **ASR of the full source** (`transcribe`, Hebrew word-level) | yes, background | wf-02 (the cut text) | run only the used ranges if the transcript is not a deliverable. Measured on OM (E08, 614.22 s FLEURS read speech, single pass): CTranslate2 int8 CPU 0.84 audio-s per wall-s (WER 17.7 %); the author's "×2.3 real time" = 0.435 audio-s/s. VAD in front avoids hallucinated text on silence (two no-speech controls) but was **slower** than plain CT2 in the shootout. Real dialogue, timestamps and other hardware **unmeasured** |
| after the ranges are known | **speaker matte** — only for beats that put graphics behind the speaker (a matte of a whole 55 s plate took ≈ 35 min with the u2net CPU route in the author's work; start at minute 0 *only* if the intake already shows such beats) | yes | wf-05 | E09 (20 s 1080p, 600 frames, OM, wrapper seconds): RVM CPU 128.2 · RVM DirectML 93.2 · MODNet DirectML 108.0 · MediaPipe CPU 47.1 · native u2net 357–453. **No quality verdict** — a fast matte with a poor silhouette is not accepted-output time. RVM is GPL-3.0 → internal use only |
| after the 3D design is approved (wf-03) | Blender asset batch (several assets per run; each launch wastes ≈ 1–1.5 min) | yes | **render 1** | never overlapping a render |
| after the ETA, licence and capability gates | AI generation 💲 | yes (local) / no (hosted) | wf-05 | ETA > 30 min per shot → shorter shot or hosted quote (wf-04) |
| in wf-01 | reference analysis (`video-analysis`) | yes | wf-01 gate | long references queue; trim long sources first (one 42-min source blocked a queue for ~5 h) |
| after wf-02 | music search + cut to length + beat grid | light | wf-05 sound | licence row per track |
| after approval | the final render | yes | — | one per approved round |

Why not everything at minute 0: matte + Blender + browser capture + generation together exceed a 32 GB / 8-core budget; the measurements show 2× slowdowns and silent stalls when they overlap. Authoring and research agents may run in parallel with **file hand-off** (≤ 4 agents, each ≤ 2 sub-agents; explicit file list, output file, clock deadline, progress file).

## 5. Exit gate G0 — ledger locked

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| blocking dimensions are `locked` or `default`-by-"תמשיך": **FMT, LEN, TON, CTA, BAR**; footage adds **STR, COLOR**; and **FILE**; more than one output adds the **VAR matrix** | `hf/PROMPT.md` `<ledger>` with those rows; the reference checker exits 0 | any missing → `fail` |
| no reference and none requested → asked at least once | the question message id | else `fail` |
| the whole source tree was listed | `_work/intake/source_ls.txt` exists, non-empty | else `fail` |
| a person's consent/rights question was asked when a person, voice or third-party asset is involved | ledger rows RIGHTS/CONSENT or `n/a` with a reason | else `blocked` |
| the person confirmed or said "תמשיך" | owner message id or the one-line "defaults taken" message | else `blocked` |

**Gate record** → `hf/QA.md` "Gate log": `| wf-00.exit | pass | <evidence paths + message ids> | agent | <UTC> |`. **`n/a` needs a reason; a missing source listing or an empty ledger can never be `pass`.**

## 6. Human vs agent

| Human | Agent |
|---|---|
| answers the rounds; picks a default or says "תמשיך"; supplies files, logos, rights/consent facts; confirms the exact length and the CTA line | lists and probes the source; creates the project; writes rows; asks 3–4 questions per round with recommended defaults; starts lanes; never asks what `ls`/`ffprobe`/the message already answers |

## 7. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| length changed three times (30 → 51 → 45 s, ≈ 35 min of re-cutting) | derived from a multiplier | ask for an exact number; for "too fast" propose exact seconds and confirm in one line | LEN is blocking |
| three "premium" notes after spec approval (≈ 40 min rebuild) | BAR asked late | add rows, re-plan | BAR in round 1 |
| five drafts of a 43.8 s restructure (≈ 4 h) | silence-cut vs restructure never asked | ask STR; show the cut text first | STR always asked for footage |
| the wrong reference segment copied | several looks, no range pinned | pin the time range | branch table |
| a camera original unseen (v1 lost ≈ 1 h) | only the rough cut used | `ls` the tree at step 0 | step 0 |
| a "no music" copied from a reference | MUS not asked | ask MUS even when the reference has none; default = music | question bank |
| the person answers "מה שאתה חושב" five times | infrastructure/creative overload | decide, explain in one line, mark `D` | question-bank §6 |
| colour fixed late (grey sky, magenta skin shipped) | COLOR not a ledger line | add COLOR; fix before building, from the camera original | footage minimum rows |

## 8. Tool invocations (student names per TOOLS_SPEC; flags per `docs/TOOLS.md`)

`new_project` · `doctor` (setup gate, if not yet green) · `ffprobe` · `sheet` (contact sheet of a source for a quick look) · `transcribe` (background, behind the lock) · `source_cuts` (footage, after the transcript — wf-04) · `ledger` (timing ledger line for this stage) · the reference ledger checker (concept-ledger.md §5). Reference analysis through the skill `video-analysis`. Heavy commands: `render_lock run -- <cmd>`.

## 9. Per-type deltas

| Type | Add at intake |
|---|---|
| talking-head | STR and COLOR are blocking; find the camera original; BAR asked in round 1; silence-cut only is the default; start ASR (and, only if a cutout beat is already planned, the matte) in the background |
| testimonial | consent/RIGHTS first; the **result-first** structure; a claims table (spoken number ↔ proof ↔ timestamp); the proof originals; never a synthetic speaker/voice/result |
| ad-promo | the **exact offer** (number, terms, deadline), CTA channel, platforms, lengths (default 15 + 30 s, 3 hooks), claims allowed in writing, music licence; the variant matrix |
| motion-graphics | LEN exact; MOT, 3D, BROLL, CAP, MUS as rows from round 1; VO pronunciation lexicon; no captions by default; the hero object |
| ai-generated | AIDISC and a **budget ceiling + retry cap** (💲 gate); character/environment locks; format choice; no spend at intake |
| podcast-clip | the full-episode proxy + ASR at minute 0; clip count/length; profile (dry vs graphic); speaker layout; the selection table comes in `wf-podcast-clip` |

## 10. Time labels

Owner target: 10–20 min. Modelled: none. Measured: none on a student. Everything above about collisions and ASR/matte speed is `[MEASURED-lab]`/`[PROVEN-internal]` on OM only; NVIDIA, Apple Silicon and Linux are **unmeasured**.

(src: blueprint WORKFLOWS §1, §6; distilled/02 workflow §2, §6.3; distilled/01 A1–A14; distilled/03 §2.1–§2.2, §8; research E08, E09 — read 2026-10-02.)

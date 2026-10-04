# wf-08 — Deliver (מסירה)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §1, distilled/02 workflow-end-to-end §10, distilled/01 rules-and-gates H1–H7 and J1, research E01/E04/E12.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[SOURCED-unverified]` · `[PERISHABLE]` · `[CONFLICT]` · `[LOCAL-only]` · `[IDEA]` · 💲 = paid step · `house preset` = owner policy, not a verified platform requirement · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | 8 of 9 |
| Owner skills | `render-qa-delivery`; `video-variants-exporter` when more than one output |
| Artifacts (exact files) | `final/<name>_<platform>_<hook>_<aspect>.mp4` (the person's exact name wins), `final/manifest.json`, `_work/delivered/v<N>/` (previous deliveries moved here), `_work/qa/final/` (QA envelopes **on the final file**), `_work/timing_ledger.jsonl` |
| Exit gate | **G8 — `hf_deliver` PASS on the FINAL file, QA stage 6 on the final file, manifest consistent** |
| Target time | **15 min** of agent work (owner target) + the one final render (8–13 min on OM for a premium 40 s; 4–21 observed) |
| Paid steps | none by default (local render). A hosted/cloud render 💲 needs a dated estimate and approval; upload of client footage to any cloud service needs an explicit per-client decision |

## 1. Before delivery (all three, in order) `[RULE-owner]`

1. wf-06 passed on the last draft: 0 flags, no blocker/major, critic ≥ 4.0.
2. The person was shown the preview (Studio, or a draft render for a remote client) and asked: *fixes or render?*
3. **The final render happens only after approval.** Fixes go back to wf-07.

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| **G6 passed**; **G7 = the person approved** | gate records; the approval message id | wf-07 |
| the build hash recorded in `CHANGELOG.md` equals the current hash (nothing changed since approval) | `sha256` compare | re-approve or re-render the changed ranges |
| `render_lock status` free; no heavy agent running | status line | wait |
| `hf_preflight --strict` clean (`--force` only for warnings and only with a written reason in `CHANGELOG.md`) | the envelope | fix |

## 3. Steps

| # | Step | Who | Evidence / output |
|---|---|---|---|
| 1 | **Compute the source hash BEFORE rendering** (the first 12 characters of the hash of the project files the render reads): `cat hf/index.html hf/compositions/*.html hf/cues.js hf/assets/mix.wav 2>/dev/null \| sha256sum \| cut -c1-12` (pick one canonical file list and keep it in the manifest header). | agent | the hash in `STATE.md` |
| 2 | **One command for render + mux + verify:** `hf_deliver --name <name> --sheet` under the long-job protocol (ETA line, log, heartbeat, watchdog — wf-06 §4). It strips `data-hf-id`, runs preflight, renders under the lock (`--quality delivery --browser-gpu --sdr`), applies the stale-file guard, muxes `mix.wav` (or two-pass loudnorm of the render's own audio, video copied), crops from the 1088 authoring canvas, **verifies**. | agent | the verify block |
| 3 | **Run QA stage 6 on the FINAL file** (`frame_qa`, `caption_qa`, `motion_qa`, `face_center audit`, `color_check` as the type needs) and the 4-axis review **only on ranges changed since the draft**. `hf_deliver` PASS proves mux, loudness, black and edge band only. | agent | `_work/qa/final/*.json` |
| 4 | **Aspect ratios and variants** (wf-variants): each is a **re-layout** on a copy, same cues and same mix, never a crop; hook variants remux the shared mix. | agent | one row per output |
| 5 | **Name and place the files**; move the previous delivery to `_work/delivered/v<N>/`; `final/` holds **finals and `manifest.json` only** (drafts, segments, raw renders, QA live in `_work/`). | agent | `ls final/` |
| 6 | **Write `final/manifest.json`** (below) and run the consistency rules. | agent | the file |
| 7 | **Last verification** (checklist §6). | agent | quoted outputs |
| 8 | **Deliver** with a message: the file(s), the ledger ✓, the QA line with coverage, the licence risks, **AI-disclosure reminder** where applicable, the process and tools used, and (if a tool was built) its name, trigger and path. | agent | message |

## 4. The delivery gate in detail (house presets)

| Item | Value | Note |
|---|---|---|
| ratios | 9:16 1080×1920 (Reels/Stories/TikTok/Shorts) · 4:5 1080×1350 (IG/FB feed) · 1:1 1080×1080 · 16:9 1920×1080 (YouTube/web) | each ratio is designed for itself: safe zones, caption size/position, camera keys |
| fps | **30 default**; an AI-based video uses the **native fps of the takes** (usually 24); 60 only for dense motion when the source is really 60; a 60 source shown at 30 is rendered at 30 | a house default, not a universal requirement `[CONFLICT]` |
| codec | H.264, **SDR (`--sdr` always)**, yuv420p, AAC 48 kHz 320k | an HDR source (phone, AI tool) otherwise flips the output to HEVC 10-bit and platforms show washed colours |
| width | author **1088** and set `data-deliver-width="1080"` for 1080-wide ratios (9:16, 4:5, 1:1); not needed for 16:9 | the encoder blackened the last 8 columns at width 1080 on OM (verified 2026-09-28 on a plain composition; **re-verify per HyperFrames version**; the same defect appeared in plain FFmpeg `gbrp` chains) `[PROVEN-internal]` `[LOCAL-only]`; `hf_deliver` crops back to 1080 and its edge-band check fails if you forgot |
| loudness | master **−14 LUFS integrated, TP ≤ −1 dBTP, measured on the FINAL file**; the mix targets −14 LUFS with TP ≤ −1.5 (AAC headroom); gate −14 ± 0.5 | **a named studio/social profile, not a verified platform requirement**; destination profiles can differ and stay configurable. Out of range: fix the mix (lower music/SFX peaks in the cue file; a sum above 0 dBFS needs a limiter first) then `hf_deliver --skip-render`; do **not** re-render and do not chase loudness inside the composition |
| length | duration within ±1 frame of the composition's declared duration | |
| black | no segment ≥ 2 frames | intended fades/blacks are listed in the ledger as exemptions |
| edge band | no dead right-edge band (30 sampled frames) | |

### 4.1 Safe zones (house policy, dated; `[SOURCED-unverified]` `[PERISHABLE]`)

The author's table, checked 2026-09 (re-check the platform pages; the Meta placement page could not be verified on 2026-10-01; TikTok and Google publish contextual templates). Values are canvas pixels of margin where no key text, logo, price or CTA may sit. The full per-platform module is `agent-content/references/platform-specs.md` (another owner; this table is repeated only so the gate is runnable).

| Platform / ratio | Canvas | Top | Bottom | Left | Right | Logo bug |
|---|---|---|---|---|---|---|
| Meta Reels/Stories/Feed 9:16 | 1080×1920 | 270 | 672 | 65 | 65 | top 300, right 65 |
| TikTok 9:16 (In-Feed) | 1080×1920 | 150 | 480 | 60 | 140 | top 160, right 140 |
| YouTube Shorts | 1080×1920 | 288 | 672 | 48 | 192 | top 300, right 192 |
| **one 9:16 master for all platforms** | 1080×1920 | **300** | **672** | **140** | **192** | top 300, right 192 |
| IG/FB feed 4:5 | 1080×1350 | 54 | 54 | 54 | 54 | top 54, right 54 |
| 1:1 | 1080×1080 | 54 | 54 | 54 | 54 | top 54, right 54 |
| 16:9 | 1920×1080 | 54 | 162 | 96 | 96 | top 54, right 96 |

**Two zones in 9:16:** **key text** (headline, CTA, logo, price, number) — master row: top ≥ 300, **bottom y ≤ 1248**, left ≥ 140, right ≥ 192; **caption rail** — may sit lower, but its bottom edge is **never below y 1450**. A 9:16 Meta ad shown in the feed is cropped to 4:5 (285 px top and bottom), hence a logo bug at top 300, not 270. For an RTL audience keep 140 px on **both** sides (a Hebrew TikTok UI column can move to the left). 16:9: x ≤ 1824. A project may choose a stricter limit in DESIGN.md. Check with snapshots (`--at <hook>,<offer>,<endcard> --describe false`, ≤ 5 per call) with the overlay of the relevant row.

## 5. Names and the manifest

| What | Name | Where |
|---|---|---|
| a name the person asked for (ledger FILE row) | **exactly as asked — overrides everything** | `final/` |
| final per ratio | `<name>_9x16.mp4`, `_4x5`, `_1x1`, `_16x9` | `final/` |
| hook variant | `<name>_<platform>_hookA_9x16.mp4` (the platform token is mandatory when Meta and TikTok cuts differ; default 3 hooks) | `final/` |
| "without" versions | `<name>_hookA_nomusic_9x16.mp4`, `<name>_hookA_nocaps_9x16.mp4` | `final/` |
| full draft | `<name>_draft_<aspect>.mp4` | `_work/drafts/` |
| segment / raw render / QA | `seg_<from>-<to>.mp4` · `<name>_raw.mp4` · `qa/<ver>/` | `_work/` |

`<name>` = the name locked at intake; without one, a small Latin slug with underscores.

```json
{
  "project": "<name>",
  "master": {"hf": "hf", "src_hash": "3f9a1c0b7e2d", "round": "v3"},
  "files": [
    {"file": "<name>_16x9.mp4", "hf": "hf",      "src_hash": "3f9a1c0b7e2d", "from_master": "3f9a1c0b7e2d", "round": "v3", "date": "2026-10-02 14:12", "lufs": -14.0, "tp": -1.3, "qa": "pass"},
    {"file": "<name>_9x16.mp4", "hf": "hf_9x16", "src_hash": "81d0e44a92c5", "from_master": "3f9a1c0b7e2d", "round": "v3", "date": "2026-10-02 14:40", "lufs": -14.1, "tp": -1.2, "qa": "pass"}
  ]
}
```
(All values invented.) **"Ready" is rejected — list the mismatching files to the person — when:** a file's `from_master` ≠ `master.src_hash` (a derivative missed the master's last fix); the **current** hash of an hf folder differs from the recorded one (changed after rendering); `qa` is not `pass`; or `final/` holds a file not in the manifest (an old 1:1 once sat beside the newer 16:9 and 9:16 unflagged). Write the file with the file-writing tool, not an inline interpreter heredoc. A hash proves *provenance*, not correctness; stage 6 on the final still runs. `[PROVEN-internal]`

## 6. Last verification (before saying "ready")

- [ ] `hf_deliver` returned **PASS on the final file**.
- [ ] QA stage 6 ran on the **final** file; stages 7–8 on the ranges changed since the draft.
- [ ] `ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate,codec_name -of compact final/<file>.mp4` matches the brief (length, size, fps, codec).
- [ ] every ledger row is `ok` in `hf/QA.md` (or a numbered gap the person accepted).
- [ ] `manifest.json` is current and consistent; `final/` has nothing else.
- [ ] licence rows complete for everything shipped; disclosure plan stated (AI-generated realistic people/places → the platform's AI-content label must be enabled at upload).
- [ ] the verification-before-completion checklist (evidence before assertions).

## 7. Exit gate G8

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| `hf_deliver` verify PASS on the **final** file (length ±1 f, −14 ± 0.5 LUFS, TP ≤ −1, black < 2 f, no edge band) | the verify block saved in `_work/qa/final/deliver.json` | else `fail` |
| QA stage 6 on the final: every tool `PASS` with coverage | `_work/qa/final/*.json` | `not_run` etc. ⇒ `fail` |
| `qa delivery` (the aggregator, TOOLS_SPEC) reports PASS and lists `unsupported`/`blocked` counts | its envelope | else `fail` (`tools/qa_delivery.py`; if it cannot run, the table here is applied by hand) |
| the manifest is consistent (all `from_master` equal; recorded hashes equal current hashes; no foreign file) | `manifest.json` + the check output | else `fail` |
| `ffprobe` equals the brief | the quoted line | else `fail` |
| exactly one final render per output this round | the timing ledger | else `warning` |

Gate record → `hf/QA.md` "Gate log". **Mux PASS ≠ release PASS.**

## 8. Human vs agent

| Human | Agent |
|---|---|
| approves the preview and says "render the final"; accepts or rejects open gaps; owns the upload and the platform disclosure toggle | renders, verifies, names, writes the manifest, reports with evidence |

## 9. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| 8 black columns at the right edge | width not divisible by 16 | 1088 + `data-deliver-width`; `hf_deliver` edge check | §4 |
| audio ≈ 11.5 dB too quiet (−25.5 vs −14 LUFS in one draft; **not** reproduced in a later test: −14.7) | the renderer attenuated a premixed `<audio>` | always mux `mix.wav` or loudnorm the render; measure the final | `hf_deliver` step 5 `[CONFLICT]` — do not teach as universal |
| a derivative ships without the master's last fix | the master was fixed after copies were made | port the patch to **every** copy; re-render all | freeze the master; `from_master` check |
| washed colours on a platform | HDR flowed through | `--sdr`; `ffprobe` the sources | §4 |
| `final/` polluted with drafts | drafts rendered there | move to `_work/drafts/` | `final/` = finals + manifest |
| a render failed on Windows | open engine issues reported 2026-09: a disk-space gate rejecting normal renders (#4060), `spawn EBUSY` from antivirus (#4058), a transparent first frame per worker shard (#4435) | check the issue list first; `--workers 1`, `--low-memory-mode`, free disk, exclude the cache folder from the scanner | `[SOURCED-unverified]` `[PERISHABLE]` — as of 2026-09; the repo's `doctor` may supersede |
| `--skip-render` shipped a stale picture | mix-only remux bypassed freshness | bind raw render to the build hash | wf-07 §3.3 |

## 10. Tool invocations

`hf_deliver --name <name> [--draft] [--sheet] [--skip-render] [--aspect …]` · `hf_mix --report` · `frame_qa` · `caption_qa` · `motion_qa` · `face_center audit` · `color_check` · `qa delivery` (planned aggregator) · `sheet` · `ffprobe` · `sha256sum` · `render_lock status|run` · `ledger`. Variants through composition variables with `hyperframes render --batch rows.json --strict-variables --sdr` are `[IDEA]` until a project has tested one variation first.

## 11. Per-type deltas

| Type | Delta |
|---|---|
| **talking-head** | 9:16, 30 fps (a 60 fps source is down-converted), `--sdr`, 1088 canvas; `face_center audit` and `motion_qa` on the final; the name from the ledger |
| **testimonial** | a 30–45 s social cut and a 60–90 s long cut (+ an optional ad cut 15–30 s); consent and proof-match recorded in the delivery message; PII blurred in anything shared |
| **ad-promo** | 15 s + 30 s × 3 hooks (`_meta_hookA_…`, `_tiktok_hookA_…`), "no music"/"no captions" rows; TP gate (author's own ads had 7 of 10 at ≥ 0 dBTP); the licence rows and an ad-use statement for every music/SFX file; a TikTok cut has no Meta chevron; WhatsApp availability is region-gated — confirm in the ads manager |
| **motion-graphics** | 16:9 **master first**, then 9:16 and 1:1 as re-layouts (one agent per ratio on a copy); same `cues`/mix; the three tables inherited |
| **ai-generated** | native fps of the takes; disclosure reminder; the spend log reconciled with approvals; an end card with brand/CTA; no black tail |
| **podcast-clip** | one file per approved clip; naming with the episode and clip index; per-clip loudness |

## 12. Time labels

Owner target 15 min of agent work + the final render (8–13 min on OM for a premium 40 s; 4–21 observed). Modelled: none. Measured on OM: E01 (a 12 s synthetic fixture 42.3–44.3 s; frame/PCM/MP4 hashes identical across repeats within the engine); E11 (render settings). Other hardware unmeasured.

(src: distilled/02 workflow §10; distilled/01 H1–H7, J1; research E01, E04, E11, E12 — read 2026-10-02.)

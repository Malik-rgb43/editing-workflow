# Variant matrix, re-layout and variant mechanics

Load when: writing the matrix at intake, laying out another aspect, or building hook / no-music / no-captions / length variants. Sources: distilled 02 workflow §10.6 and §13 (2026-10-01), blueprint WORKFLOWS §5. Measured numbers here come from the author's projects on one Windows laptop; treat them as defaults.

## 1. The matrix (write it at intake, not at delivery)
Every axis that is not asked costs a rebuild. In one past project two structure versions were built because "silence-cut only vs reorganise" was asked late (about 4 h wasted); a 16:9 request that arrived at delivery was dropped. Ask, in one round:
1. **Ratios**, and which one is the **master** (the one the piece is designed for; the others are re-laid out from it).
2. **Variants:** hooks A/B/C (default 3 for ads), platforms with different cuts (Meta vs TikTok), `nomusic`, `nocaps`, lengths (for example 15 s + 30 s).
3. **Route per file:** organic, auction ad, Spark, other. It decides which music licence applies (a TikTok Commercial Music Library track is TikTok-only), which AI-disclosure field applies, and which safe-zone row you must satisfy (`agent-content/references/platform-specs.md`, dated).
4. **Structure:** silence-cut only vs reorganise (decided once for the master).
5. **How many different videos** and what they share (DESIGN.md, music, 3D, caption kit are built once and copied). A different video from the same source = a separate project with its own ledger.

Matrix table (one row = one file = one ledger id; copy into PROMPT.md `<inputs>`):

| File | Aspect | Platform | Route | Variant | Derived from | Source folder |
|---|---|---|---|---|---|---|
| `promo_meta_master_16x9.mp4` | 16:9 | meta | organic | master | none | `hf/` |
| `promo_meta_master_9x16.mp4` | 9:16 | meta | ad | re-layout | master | `hf_9x16/` |
| `promo_meta_hookB_9x16.mp4` | 9:16 | meta | ad | hook B | `hf_9x16/` | `hf_9x16/` (variables) |
| `promo_tiktok_hookA-nomusic_9x16.mp4` | 9:16 | tiktok | ad | hook A, own mix | `hf_9x16/` | `hf_9x16/` |

The same list goes into `manifest.json` as `matrix`, so a promised file that never arrives blocks "ready" (finding M006) and a delivered file nobody planned is flagged (M007).

## 2. Naming
`<name>_<platform>_<hook>_<aspect>.mp4`. Parsing is from the right, so `<name>` may contain underscores. `<hook>` is `master` (no hook test), `hookA`, `hookB`, ... with an optional `-nomusic` or `-nocaps` suffix (hyphen, so the file still has exactly four underscore-separated fields at the tail). A platform token is mandatory when Meta and TikTok cuts differ; use `all` when one cut serves every platform. The delivery playbook (`agent-content/playbooks/wf-08-deliver.md`) also shows the short per-ratio form `<name>_9x16.mp4` (accepted: platform `all`, hook `master`) and writes the "without" versions as `<name>_hookA_nomusic_9x16.mp4`; this skill uses the hook-token suffix `hookA-nomusic` so every file keeps the four-field shape, and a file named in the playbook style is recorded with `--name-ledger-id`. Finals folder = finals + `manifest.json` only; drafts go to `_work/drafts/`, raw renders to `_work/`, the previous delivery to `_work/delivered/v<N>/`.

## 3. Re-layout of an aspect (what changes, what must not)
A re-layout is a copy of the master source with these changed, and only these:

| Element | What is re-decided per aspect | Evidence |
|---|---|---|
| Canvas | root size = the aspect canvas (1080-wide ratios are authored at 1088 with `data-deliver-width="1080"` while the HyperFrames encoder trap is unverified for the pinned version, see `house-presets.md`) | root attributes in `index.html` |
| Safe zones | key text, CTA, logo, price, number inside the aspect's zone; caption rail bottom <= y 1450 at 9:16 | overlay snapshot at hook, offer, end card |
| Type scale | sizes re-derived for the canvas and reading distance, not scaled with the frame | layout table row |
| Captions (only if the master has captions; none = skip this row and `caption_qa`) | rail position and line width per aspect; word-pop timing unchanged. Rail per `agent-content/skills/pro-video-editor/references/safe_zone_presets.json`: 9:16 has a rail preset (bottom edge <= y 1450, x 140-888). 4:5, 1:1 and 16:9 have no rail preset: keep the rail inside the aspect's safe zone (4:5 bottom <= y 1296, x 54-1026; 1:1 bottom <= y 1026, x 54-1026; 16:9 bottom <= y 918, x 96-1824) and measure the platform UI overlay before trusting it | `caption_qa --band <top>:<bottom> --x <left>:<right>` with that aspect's numbers; the aspect's contact sheet looked at; 4-axis review axis 4 |
| Camera and framing | camera keys, punch-in scale, face centring recomputed on the new crop (`faces.json` for the new crop; zoom limits so the chin does not enter the caption zone) | `face_center audit` for speaker footage |
| B-roll framing | full-bleed re-framed by meaning (a face or a product must stay in frame), not centre-cropped | review axis 1 |
| End card | CTA and button chevron inside the zone; no trailing black | snapshot at the last second |

What must NOT change: `cues.js` / `cues.json` (timing, mix cues), `assets/mix.wav`, the words and numbers on screen, the palette and fonts in DESIGN.md. If a ratio truly needs different timing, that is a master change: fix the master and carry it everywhere.

Layout table (one per aspect, `_work/qa/<aspect>/layout.md`):

| Element id | Master box (px) | This aspect box (px) | Why it moved | Zone check |
|---|---|---|---|---|
| headline | 140,120,940,330 | 140,310,940,520 | top 300 zone | pass (overlay `snap_0.png`) |

A row with identical boxes in two different aspects is a red flag for a crop.

**Derivative QA depth (token budget):** run the automatic checks on every file; visual review only axis 1 (composition and cropping) and axis 4 (readability and safe zones); axes 2 and 3 (motion, colour/sound) are inherited from the master unless the layout changed motion. A bug found while porting (for example an element vanishing at 3.69 s) is reported to the main session, fixed in the master, and carried to every copy.

## 4. Hook variants and version variants
- **Mechanism:** one body; the hook is a sub-composition bound to variables (`data-var-text`, `data-var-src`); dimensions cannot be variables, so every aspect has its own root sharing the compositions, and the same rows run in each. Rows file: one object per output with `name`, `hook_src`, `hook_text`. Render with the pinned engine's batch mode and strict variables, then deliver each row with the shared mix. **Status: untested in a project (distilled 02 workflow §10.3, 2026-10-01): render ONE variation, verify it, then the rest.**
- **Shared mix:** the hook changes picture and text, not the music bed or the cue timing. If the hook needs a different spoken line, it is `own-vo`: declare it, give a reason, accept that the mix hash differs, and keep every other variant on the shared mix.
- **`nomusic`:** a separate premix with the bed removed (declared `mix_variant: nomusic`); captions and picture unchanged. **`nocaps`:** the caption layer off through a variable (or the clean master), mix unchanged. Deliver a timed text file (SRT) alongside where the platform supports native captions (YouTube, LinkedIn, X Media Studio per the platform module) instead of relying on burned-in text alone.
- **Length variants (15 s from a 30 s master):** these are NEW edits, not re-layouts. They get their own ledger lines and PROMPT rows, their own mix (`mix_variant: recut`, with a note), are derived from the frozen master's assets, and pass full QA as a master would.
- **Ranking and compliance of the hooks themselves** belong to `pro-video-editor` (`pro-video-editor`); this skill only guarantees the copies are consistent.

## 5. Several different videos in parallel
The procedure is the SKILL.md "N masters" branch: one project, matrix and manifest per master; one machine-wide render queue (see `parallel-and-agents.md`). Several sessions on the same source (a bake-off): never message or stop another session; report to the user only; one session owns shared rule files.

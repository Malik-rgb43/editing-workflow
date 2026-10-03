# Profile `core-cpu` (default)

> Dated 2026-10-02 · evidence state **measured, one machine** · expires 2026-12-31 or on any pin change. **unsupported ≠ missing ≠ error.**

## What it installs
The deterministic core: probes (`ffprobe`), media and QA tools, manifests and jobs, and **one** video engine — HyperFrames (research pin **0.8.98**) — rendering on the CPU with a headless browser. **No API key, no GPU, no paid call, no account** beyond the agent client. Python via `uv` (project-scoped; measured with 3.12.10), Node project-pinned (HyperFrames needs Node ≥ 22; measured with 24.14.0), FFmpeg **installed by the student following the instructions — never bundled** (measured with FFmpeg 8.1 full build).

Optional named Python groups (pyproject owned by the core agent; names assumed): `opencv`, `color`, `analysis`. They are opt-in additions to the core, not other profiles.

## Download size and where the number comes from
Sizes of the Python runtime, Node, the HyperFrames npm tree and the headless browser were **not recorded** by the research → `unmeasured`. What is recorded: the install step took 18.042 s for the HyperFrames npm tree on the reference machine (not from zero; browser reused). The installer must show real sizes and the cache location **before** downloading anything. Model downloads: none in this profile.

## Hardware
Instructor recommendation (not a measured minimum): supported 64-bit OS, modern 4-core CPU, 16 GB RAM, SSD, reliable network; more headroom with 8 cores / 32 GB. No GPU needed. Only the reference machine (one reference machine) was measured.

## Tested-on evidence
**measured** — E01: a 12 s, 360-frame, 1080×1920, 30 fps Hebrew fixture (headline with Latin "AI" and "12", Ken Burns zoom, three caption cues, 12 s music + two SFX), CPU H.264 CRF 18, software browser, one worker: HyperFrames 0.8.98 **cold 44.262 s, warm 42.292 / 42.406 s**, peak RSS ≈ 1.7 GiB, 360/360 frame hashes and PCM audio identical within the engine (cold vs warm). Cross-engine frames differ (decoded SSIM mean 0.976819 against Remotion). Cold = engine-cache-cold only. **Not tested:** macOS, Linux, NVIDIA, other AMD cards, long or 4K footage, HDR, variable frame rate.

## States
| State | When |
|---|---|
| `unsupported` | unsupported OS, or no writable ASCII work root can be created |
| `missing` | uv, Node, FFmpeg or the browser not found at the pinned version — offer the install with sizes |
| `error` | the pieces exist but the fixture render or an `ffprobe`/decode probe fails — report with evidence |
The core's final-output gates (render → decode → frame/audio checks) must all have **run**; a gate that cannot run reports `not_run`, never PASS.

## Licences
HyperFrames **Apache-2.0** (licence + NOTICE + change markers; dependencies, registry assets, fonts and hosted services are separate; no trademark endorsement). GSAP: Standard No-Charge licence (not MIT). FFmpeg: LGPL 2.1+ baseline, GPL/nonfree optional components change obligations — hence install instructions, not binaries. Remotion is **not** part of v1.0 (custom licence; decision default Q14). See `agent-content/references/licences-bom-rules.md`.

## Environment rules this profile enforces
ASCII work/cache root (`npx hyperframes init` silently skips `index.html` under Hebrew-character paths — historical report on 0.8.79, scoped); lockfiles committed; `HYPERFRAMES_SKIP_SKILLS=1`, `HYPERFRAMES_NO_UPDATE_CHECK=1`, `HYPERFRAMES_NO_TELEMETRY=1`; fonts from files; `hyperframes snapshot --describe false`. See `agent-content/references/hyperframes-traps.md`.

## Uninstall
Remove the project `.venv` and `node_modules`, run `uv cache clean`, delete the HyperFrames cache (`~/.cache/hyperframes`), the downloaded headless-browser directory and the workspace `_work/` folders. **No global change was made**, so nothing global needs undoing.

# Task evals: multi-video-variants

Status: specified, deterministic oracles only. Model eval not run (decision default Q4: no nested model runs until the owner approves). Every oracle below is a file or a script exit code, not the executor's own claim. Fixtures are synthetic: fake bytes for videos are enough for manifest tasks; real ffmpeg-generated 1-second clips are enough for QA tasks. No client media.

## T1. Stale derivative is blocked (script oracle)
- **Setup:** a project with master `hf/`, a 9:16 copy `hf_9x16/`, three recorded finals (master 16:9, 9:16 re-layout, hook B 9:16), `manifest_check.py check` currently READY. Then edit one composition file in `hf/` (a text fix at 3.7 s).
- **Oracle:** `python scripts/manifest_check.py check <project> --json` (exit code and JSON).
- **Pass:** exit 1; findings contain `M003_STALE_MASTER`; after `change --id M-001`, findings contain `M031_STALE_DERIVATIVE` and `M032_MISSING_MASTER_FIX` for every derivative; the agent does NOT say "ready"; it lists the files to re-render. After carrying the patch to the copy, re-stamping, re-rendering and `record --applied-all` for every file, exit 0.
- **Fail:** agent edits only the 9:16 copy; agent records the new hash without re-rendering; agent reports "ready" while exit is non-zero.

## T2. Aspect re-layout, not crop
- **Setup:** an approved 9:16 master of a 20 s offer video with a headline, a price badge, a caption rail and a logo. Request: "also give me 1:1 and 16:9".
- **Oracle:** the derivative folders `hf_1x1/` and `hf_16x9/`, `_work/qa/<aspect>/layout.md`, overlay snapshots at hook / offer / end card, and `manifest.json`.
- **Pass:** each derivative has its own root canvas (1:1 1080x1080, 16:9 1920x1080), the layout table lists every key element with a different box per aspect and a zone check against the house preset (1:1: 54 px each side; 16:9: x <= 1824, top 54, bottom 162); `cues.*` and `assets/mix.wav` hashes equal the master's; no file in `final/` was produced by an FFmpeg crop/scale of the master render; `check` shows no M035.
- **Fail:** identical element boxes across aspects; a centre-cropped master render delivered; a safe-zone claim with no overlay evidence (must be reported as `blocked`, not `pass`).

## T3. Hook variants share one mix
- **Setup:** an approved ad master with `assets/mix.wav`; request: "three hook variants, Meta 9:16".
- **Oracle:** `manifest.json` (+ `check`), `rows.json`, the variant files.
- **Pass:** three files named `<name>_meta_hookA_9x16.mp4`, `..._hookB_...`, `..._hookC_...`; one `mix_sha256` value across the three entries equal to the master's; only the hook segment (first seconds: text/B-roll) differs; ONE variation was rendered and verified before the batch; exactly one critic review covers the set; `check` exit 0.
- **Fail:** a re-mixed audio per variant, a variant with a different mix and no `own-vo` declaration, collisions in names, a batch rendered before one was verified.

## T4. One heavy job at a time
- **Setup:** four projects queued, each needing a full render, plus a request to "run everything in parallel".
- **Oracle:** `_work/STATE.md`, the lock log (`render_lock` jsonl), agent brief files, progress files.
- **Pass:** at no time are two heavy jobs active (lock log intervals do not overlap); the plan names the order; at most 4 agents each with <= 2 sub-agents; every agent brief has a file list, an output file, a clock-time deadline and a progress file; a silent agent (no write for 20 min in the simulated log) triggers check/replace/stop, and stopping kills only that agent's process tree and is followed by `render_lock status`.
- **Fail:** simultaneous renders, an agent without a deadline or progress file, the agent messaging another session, killing a process it does not own.

## T5. Missing evidence is never ready (script oracle)
- **Setup:** variants of T1 with each of: no `manifest.json`; `qa: not_run` on one file; `lufs: null`; an old render file left in `final/`; a promised variant missing from the folder.
- **Oracle:** exit codes and finding codes of `manifest_check.py check`.
- **Pass:** each case exits non-zero (2 for no manifest or missing numbers, 1 for the others) with M001 / M051 / M060 / M081 / M006 respectively; the agent reports each as blocked with the fix, never as pass.
- **Run it yourself:** `python scripts/manifest_check.py --self-check` (29 built-in cases) and `python -X utf8 -m unittest -v test_manifest_check` from `scripts/`.

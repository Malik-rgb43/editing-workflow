# First output - the fixture render

> Written 2026-10-02. Goal: prove on YOUR machine that install -> render -> inspection works, using owned synthetic sources (no client footage, no cost). Everything is local and free. Timing and speed numbers elsewhere in this repo come from one machine (one reference machine) and do not transfer to yours. Hebrew: [docs/he/first-output.md](../he/first-output.md). Install first with the `claude-code-setup` repository (its install guide).

Commands use the `run` launcher so they behave the same in PowerShell, CMD and bash: `python install/bootstrap.py run -- <command>` runs from the installed toolkit folder with the toolkit's own Python environment and replaces `{work_root}` with your ASCII work folder.

<!-- step: first-output-01 -->
## first-output-01 - What this proves
A bilingual (Hebrew + English) 8-second vertical sample project is generated, rendered by the engine, and checked. It contains mixed-direction hazards on purpose (a shekel sign with a thousands comma, a percent after digits, a Hebrew prefix before a Latin word, Latin words inside Hebrew lines). Passing means: FFmpeg encodes, the engine renders, fonts come from files, and the final MP4 passes every-frame checks. It does **not** prove model quality, GPU speed, or that any provider works.

<!-- step: first-output-02 -->
## first-output-02 - Check the install and the work folder
```text
python install/bootstrap.py verify
python install/bootstrap.py where
```
`installed` must be `pass`. The work root (`paths.work_root` in `toolkit.local.toml`) must be ASCII-only: `npx hyperframes init` silently skips `index.html` under a path with Hebrew letters. Do not rename your source folders; copy them into the work root instead.

<!-- step: first-output-03 -->
## first-output-03 - Generate the owned sample sources
```text
python install/bootstrap.py run -- python fixtures/generators/make_sample_project.py --out "{work_root}/sample-project"
```
Creates `projects/sample-he-en/` with `source/` (an 8 s 1080x1920 stand-in clip with a non-speech tone, an abstract B-roll clip, a music bed, a logo mark, Hebrew and English scripts, SRT captions, word-level cues, `brief.json`) and `project.json` with the Hebrew display title. Everything is produced from FFmpeg test sources by the script (src: `fixtures/generators/make_sample_project.py`, `fixtures/manifest.json`). The stand-in has no real speech, so it cannot test speech recognition.

<!-- step: first-output-04 -->
## first-output-04 - Inspect the sources
```text
python install/bootstrap.py run -- python -m core probe "{work_root}/sample-project/projects/sample-he-en/source/speaker_standin_1080x1920.mp4"
```
Expect JSON with codec `h264`, 1080x1920, 30 fps (a rational frame rate, not a rounded one), duration 8 s, and the expected frame count. A non-zero exit or `INSUFFICIENT_EVIDENCE` is a failure, not a warning.

<!-- step: first-output-05 -->
## first-output-05 - Render with the engine
Ask your agent: "make the sample project into a short vertical video with the Hebrew captions" - the `video-request-router` skill routes it. The expected path is the toolkit's gated process, nothing improvised: intake is already answered by `brief.json`; the agent drafts `PROMPT.md` and **you approve it before any code**; then project scaffolding under the ASCII work root (`new_project`), static preflight (`hf_preflight`), `hyperframes check`, range renders, ONE full render under the render lock, loudness measured on the file you ship (`hf_deliver`). Use `python install/bootstrap.py run --cwd "<project hf folder>" -- npx hyperframes ...` for engine commands. Rules the agent follows: no `dir="rtl"` on the composition root, fonts from `@font-face` files in `hf/fonts/`, `hyperframes snapshot --describe false` with at most 5 timestamps, one heavy job at a time.
Availability (checked 2026-10-02): the Phase-1 tools exist in `tools/` - `doctor`, `new_project`, `hf_preflight`, `hf_segment`, `hf_deliver`, `frame_qa`, `caption_qa`, `sheet`, `transcribe`, `render_lock`, `ledger`, `join_diff`, `qa_delivery` (each has a `Usage:` line: `python tools/<name>.py --help`). The render step itself needs Node and the HyperFrames engine; `hf_segment` and the engine-render part of `hf_deliver` were NOT run end-to-end against a live HyperFrames render in this repository (only their planning, muxing and verification parts are tested), so treat the first engine render as the real test and report any difference. Run `python tools/doctor.py smoke` first: it proves FFmpeg, Hebrew/space/emoji paths and the QA tools work on this machine without needing the engine.

<!-- step: first-output-06 -->
## first-output-06 - Inspect the result (machine + human)
* Machine: every-frame QA on the FINAL file (`frame_qa`, `caption_qa`, loudness) writes a JSON envelope `{status, decoded_frames, expected_frames, ...}`; only `PASS` with decoded = expected counts. A missing tool, timeout or empty sample is `not_run` / `INSUFFICIENT_EVIDENCE`, never a pass. Aggregate with `python tools/qa_delivery.py run <final.mp4> --captions` (it adds the human-review gate only when YOU approved the exact file: `--human-approved "<your words>"`).
* Human: play the MP4. Check: Hebrew letters are real Hebrew (not boxes), punctuation and numbers sit on the correct side in mixed lines, captions never vanish for a single frame, audio is not clipped, the last frame is not black.
Then record the facts (the installer verifies them, it does not take your word):
```text
python install/bootstrap.py mark first_render --evidence "<path to the final .mp4>"
python install/bootstrap.py mark inspection_passed --evidence "<path to the QA json>"
```

<!-- step: first-output-07 -->
## first-output-07 - Keep the timings
Write down setup, load, render, QA and review minutes (the first entry of your timing ledger; the toolkit's `ledger` module summarises them: `python install/bootstrap.py run -- python -m core ledger summarize <file>`). These are your numbers; compare them to nothing else. If a single render takes longer than expected, do not retry blindly: read `troubleshooting` (in the `claude-code-setup` repository, docs/en/troubleshooting.md).

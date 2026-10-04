# Changelog

All notable changes to the public contract of this toolkit are recorded here, newest first.
Format: [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html).
Releases are immutable: a correction is a new release.

Dates and facts here are perishable; each entry states its source where it relies on research
(src: blueprint/REPO_ARCHITECTURE.md section 10, 2026-10-02).

## [0.4.0] - 2026-10-04

### Added
- **Claude Code plugin `editing-workflow`** (`.claude-plugin/plugin.json` + `marketplace.json`, validated with `claude plugin validate`, installed and listed in an isolated config folder from a path with Hebrew letters: 17 skills, about 2.2k tokens always-on). It points at `agent-content/skills/` (no second copy). The installer now installs it by default (`--skills-via plugin`; `--skills-via copy` keeps plain folders; Codex always gets copies), records it in the manifest, verifies it, and removes it (and the marketplace entry only if it added it) on `uninstall`.
- `src/core/hf_engine.py`: one place that finds the pinned HyperFrames engine (never `npx` downloading whatever version npm serves) and refuses non-ASCII engine paths; `hf_deliver`, `hf_segment`, `new_project` (runs `init` first in an empty `hf/`) and `doctor` use it.
- Installer: the toolkit folder falls back to an ASCII folder (`C:/avc-toolkit`, `/Users/Shared/avc-toolkit`, `/var/tmp/avc-toolkit`; `AVC_ASCII_BASE` overrides) when the home path has non-ASCII letters, because `hyperframes init` silently writes nothing there (found by a live run 2026-10-03).

- The tools the skills had marked "planned" now exist (all tested on synthetic clips with real FFmpeg; none re-scored on real footage):
  - `color_fit`, `color_render`, `color_check` (+ `src/core/colour.py`): a named-parameter grade fitted toward a NAMED preset, baked as two 65^3 LUTs blended by a soft person matte, then measured for `grade_gate.py`. `color_render` forces `accurate_rnd` in the final pixel-format conversion (FFmpeg 8.1's default left the right-most columns black on a 360-wide clip) and a test checks the edge columns.
  - `cutout` (+ `src/core/matte.py`): transparent speaker video (WebM VP9 alpha or ProRes 4444) per shot segment, cached by decoded content, choked (erosion + blur), verified (size, exact frame count, non-empty alpha). Routes: `native` (HyperFrames), `onnx` (your own MODNet-style file), `external` (an alpha you made, for example with RVM).
  - `analyze` and `frames` (+ `src/core/analysis.py`, `src/core/audio_analysis.py`): produce the `analysis/<video>/` folder that `validate_analysis.py` accepts. Honest limits are written into the files: the cut detector was scored on only two hand-labelled real clips (see Changed); the sound analysis is signal-only (loudness, silences, transients, tempo/key estimates with half/double-time to be audited by the reader); no sound is named, no song identified.
  - `ui`: search and read shadcn-style registries (licence tier next to every hit, 7-day offline cache, `add-command` prints text only, 21st.dev is never queried).
  - `hf_blocks` + `hf-blocks/`: seven blocks (`voice-orb`, `task-steps`, `boarding-pass-stamp`, `notification-stack`, `film-burn`, `speaker-cutout-behind`, `caption`) each admitted by `hf_blocks.py verify` (seek-safe scan + `hyperframes check` in an empty project). The first run of the admission test rejected two blocks (text overlap, contrast, overflow); they were fixed, not waived.
- `docs/en|he/local-vs-paid.md`: what each local model replaces, the exact download source, byte size and licence (read from the hosts on 2026-10-03), and the gaps: no supported local Hebrew voice (Kokoro has no Hebrew), no local video generation.

- Speed-ups for a first edit (2026-10-04; the time each one saves is NOT measured):
  - `tools/prep.py`: one background command at minute 0. It runs, one step at a time under the lock: sheet, transcript, source cuts, faces, colour scopes and reference analysis.
    - It writes to `hf/data/` and `_work/prep/prep.json`.
    - `--plan` shows the steps first. Nothing is downloaded.
    - A step that cannot run is recorded as `not_run` with the tool's own reason; unchanged steps are cached.
  - `revision-notes-handler/scripts/notes_board.py serve <draft>`: a review page with the video, timed notes (a point, a range or a general note), frame and second stepping, and one "שלח הערות ✓" button.
    - The command exits with the numbered notes and the frame-strip times of each note, so the user pastes nothing.
    - Same guards as the choice board.
    - Tested live in a browser: seeking with range requests, a reload keeps the notes, and the send arrives.
  - `new_project.py --starter talking-head`: a DRAFT `PROMPT.md` and `BRIEF.md` with the house preset v1 defaults already typed in and every open question marked ASK.
    - The intake ledger check still fails it until those questions are answered, and approval is still required.
- `tests/unit/test_skill_scripts.py`: CI now runs every skill script's `--self-check` and `test_*.py`; before this, nothing ran them automatically.
- Student screens redesigned (2026-10-04, owner's picks: "pro editing suite", black + gold, follows the system light/dark setting, medium motion, Heebo).
  - Both screens share `scripts/ui/tokens.css` and an embedded Heebo subset (OFL-1.1, 50 KB WOFF2, the only bundled third-party file; registered in `licenses.toml` and `THIRD_PARTY_NOTICES.md`).
  - Sources: 21st.dev references (Filmstrip Scrub: timecode chip and tick ruler; AI Approval: each final action states its consequence) and the UI/UX Pro Max "Luxury/Premium Brand" palette. Still offline; no React.
  - Notes board:
    - a monitor with an SMPTE timecode chip and a seconds ruler under the timeline;
    - notes shown on the timeline (gold dots for points, champagne bands for ranges), playable range notes and in-place editing;
    - "−1 frame / +1 frame / −1 second / +1 second" buttons and NLE keys (I/O/J/L, Space);
    - a "מה הלאה?" panel with "שלח הערות (N) ✓" and a new **"מאשר, אין הערות ✓"** (the server exits with `status: approved`).
  - Choice board: decision progress ("2 / 6"), numbered tabs that turn green when answered, a gold ring and check mark on the picked card, and a bottom bar whose confirm button says what happens next.
- Hebrew fonts to choose from:
  - `visual-choice-board/references/hebrew-fonts.json`: 19 OFL Hebrew families checked on 2026-10-04 against Google Fonts' metadata and the google/fonts repository, with file sizes, styles and E03 legibility scores. Karantina is flagged: in E03 "לבזבז" read as "לבובו".
  - `scripts/hebrew_fonts.py`: `list`, `fetch` (without `--yes` it only prints the plan), and `spec` (a font decision embedding the fetched files).
  - New rule (visual-choice-board rule 8, captions, intake question bank, talking-head starter): if the user names no font, show a font board and never default silently. "You choose" means Rubik, stated as a default.

### Changed (review pass, 2026-10-03)
- Visual choice board: the export button is now **"אישור הבחירה ✓" / "Confirm my picks ✓"**. New `make_board.py serve DIR` serves the board on 127.0.0.1 and exits with the verified picks when the user confirms, so the agent gets the decision without an export or paste. Guards: a per-run token, an Origin check, a 1 MB cap and a CSP that allows no other request. The file on disk stays network-free.
- Cut detector (`src/core/analysis.py`):
  - it compares unique pictures, so pulldown and stepped (12/15 fps in 60) footage no longer counts every repeat as a cut;
  - a camera move is rejected only when the aligned residual is also small;
  - soft cuts are placed on the strongest frame;
  - scored by hand-labelled cuts on real footage on the reference machine: F1 0.69 -> 0.89 on the tuning clip, unchanged 9/9 on a held-out clip.
- Music analysis (`src/core/audio_analysis.py`):
  - tempo, beats, `cut_on_beat` and key now come only from **beat regions**: 4 s windows that agree on one tempo, with hysteresis;
  - speech-only clips report no music instead of a tempo;
  - audio is trimmed to the video span.
- `color_fit`:
  - white balance is fitted only against a declared neutral (`--neutral-roi`, black or sky patch) and is otherwise locked (`wb_locked`);
  - a skin dead-band stops it from chasing noise;
  - reported active bounds exclude parameters left at identity.
- `color_scopes`:
  - a skin region whose mean colour cannot be skin (hue outside 70-170 degrees or chroma < 5) is recorded as `skin_rejected` and counts as no person;
  - `face_roi` respects the frame aspect ratio and a 1 s gap limit.

### Fixed
- Tests no longer risk writing to `C:/` when they simulate a Hebrew home folder.
- `transcribe --model-dir` on a folder without `model.bin` now refuses (exit 2) with a clear message instead of crashing (exit 3).
- `revision-notes-handler` pointed at `sheet --range ... --fps`, which does not exist; it now uses `sheet --times`.
- `color_render` / `cutout`:
  - a VP9-alpha WebM matte is decoded with libvpx so that its alpha is read (FFmpeg reports such files as `yuv420p`);
  - `--matte-offset` refuses a matte that does not cover the pre-roll;
  - the output is capped at the exact frame count, because `alphamerge` added one frame;
  - concat lists use ASCII names;
  - the u2net first-run download (about 176 MB) is announced before it starts.

## [0.3.2] - 2026-10-03

### Removed
- fal.ai, Pixabay, Unsplash, Figma, Notion and the Adobe Express docs MCP are gone from the integrations catalogue, the install questions, the docs, the tests and the MCP reference. (Hyper3D was removed in 0.3.1.) The stock-media group is now Pexels and Iconify. Premiere / After Effects bridges stay. Rights notes about stock licences in the skills' references are kept: they are licence guidance, not offers.

## [0.3.1] - 2026-10-03

### Changed
- **Privacy:** no details of the author's computer or accounts remain in the current files. Hardware specs are replaced by "the reference machine" (OM) with the note that its details are intentionally not published; local usernames, folder names and the private research repository name were removed from tests and scan rules. (Earlier commits and tags still contain the old text.)
- 3D: AI model generation (Tripo) is used only if the student connected it; otherwise Blender builds the model (Three.js if the student chooses it). See `three-d-decision.md` section 1b.
- The offered list of services to connect is shorter: stock media = Pexels and Iconify; no fal.ai; no design-and-notes group (Figma, Notion, Adobe Express). Hyper3D was removed from the references.

## [0.3.0] - 2026-10-03

### Changed
- **Repository split revised (ADR 0005).** This repository now owns the installer (`install/bootstrap.py`), the integrations catalogue (`integrations/catalog.toml`) and sign-up links (`integrations/referrals.toml`), `INSTALL.md` and the install docs. `claude-code-setup` only prepares Claude Code (credit-saving `CLAUDE.md`, Playwright MCP, Superpowers plugin).
- `INSTALL.md` rewritten: before installing, the agent tells the student what is downloaded, what changes and which questions will be asked; **all optional MCP / CLI / API questions (Q1-Q8) live in install-09**; a new explicit HyperFrames step (install-08: browser and `doctor`) and a final report to the student (install-13).
- The installer no longer has `fetch` or a cross-repository pin: this repository is complete on its own.

### Added
- `package.json` + `package-lock.json` pin **HyperFrames 0.8.98**. Nothing of HyperFrames is stored here: `npm ci --ignore-scripts` downloads it from the official package. (Before this, the engine stage of `apply` was skipped because no `package.json` existed.)
- `docs/decisions/0005-repository-split-revised.md`.

## [0.2.1] - 2026-10-03

### Removed
- `seedance-prompting`: the phone-style UGC preset (`owner-phone-ugc`), its worked example, lint rule P08 and its eval cases. The skill keeps the cinematic preset, the vendor-short profile and custom prefixes; a casual or phone-style look now goes through `vendor-short` or the user's own prefix.

## [0.2.0] - 2026-10-03

### Added
- 11 tools, each fail-closed and tested on real FFmpeg media: `hf_mix`, `source_cuts`, `motion_qa`, `motion_scan`, `seg_diff`, `grade_bake`, `aroll_cut`, `render_watch`, `face_center` (YuNet model supplied by the student, or Haar where the OpenCV build still has it), `camera_path`, `color_scopes`.
- CI installs FFmpeg + numpy/Pillow/OpenCV and runs the media tests on Windows, macOS and Ubuntu (green 2026-10-03).

### Fixed
- `uv.lock` matched the old project name, so `uv sync --locked` failed and numpy/Pillow were not installed (found by the installer smoke test); a unit test now guards it.
- Skill-tree hash (adapter markers) is independent of operating system and line endings.
- POSIX lock treated macOS `EAGAIN` (35) as an unknown error; busy errnos are symbolic now.

## [0.1.2] - 2026-10-02
Lockfile fix. ## [0.1.1] CI-verified lock and hash fixes. ## [0.1.0] First public release (Apache-2.0).

## [Unreleased]

### Added
- Repository hygiene: `.gitignore`, `.gitattributes` (LF everywhere, binary and generated markers), `.editorconfig`.
- `LICENSE` (Apache-2.0, chosen by the author on 2026-10-02), `NOTICE`, `THIRD_PARTY_NOTICES.md`
  (generated block + hand-written section), `licenses.toml` (declared licence per path, fail-closed).
- `release-manifest.json` template (schema, support matrix with unmeasured/untested labels, hash fields filled at build time).
- Deterministic gates in `scripts/`: skill checks, secret scan, private-path/client-name scan, bill of materials with
  blocked-component gating, agent-adapter generation with package parity, SYSTEM.md / TOOLS.md generators, link and
  step-id checks, workflow policy check, dry-run release builder with update/rollback plan, and `run_all_checks.py`.
- `tests/evals/run_trigger_evals.py`: deterministic dry run of every skill's trigger evals; reports `model_eval: not_run`;
  the model lane is a stub that refuses to run without `--approved-by-owner` and a budget cap (default 60).
- GitHub Actions: deterministic CPU lane on Windows, macOS and Ubuntu with least-privilege permissions; a disabled,
  manual, approval-gated model-eval workflow. Action pins are placeholders marked `TODO pin to reviewed commit`
  (they could not be verified offline) and a release build refuses to proceed until they are real commit SHAs.

### Known limits
- No skill has been evaluated with a model (decision default Q4); only deterministic checks exist.
- CI has not run on a hosted runner yet; only the local Windows run of the unit tests is evidenced.

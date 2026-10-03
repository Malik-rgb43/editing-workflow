# Changelog

All notable changes to the public contract of this toolkit are recorded here, newest first.
Format: [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html).
Releases are immutable: a correction is a new release.

Dates and facts here are perishable; each entry states its source where it relies on research
(src: blueprint/REPO_ARCHITECTURE.md section 10, 2026-10-02).

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

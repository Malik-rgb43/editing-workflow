# editing-workflow - the editing half: skills, playbooks and tools for AI video editing

This is **repository 2 of 2**. Repository 1, `claude-code-setup`, prepares **Claude Code itself** (a credit-saving `CLAUDE.md`, the Playwright MCP, the Superpowers plugin). **This repository owns everything about editing**: the skills, playbooks and tools, the installer, the catalogue of editing MCP servers / CLIs / APIs **and all the questions about connecting them**, and the instruction to install the HyperFrames engine. The student pastes this repository's link into Claude Code or Codex and says "install this" / "תתקין את זה"; the agent follows [INSTALL.md](INSTALL.md), tells the student what is downloaded and which questions they will be asked, and installs the skills.

> No course materials here - only what the agent needs. Hebrew-first (RTL-safe captions and paths), English for implementers. Works on every computer: hardware is detected (`python tools/doctor.py recommend`), never asked; the CPU route always works ([ADR 0002](docs/decisions/0002-universal-by-default.md)).

## What is inside
| Folder | What |
|---|---|
| `agent-content/skills/` | **14 skills** - `video-request-router` (single entry), **`pro-video-editor` (the central editor: a way of thinking and a method, no per-type templates; it calls the other skills and the student's connections)**, `video-brief-intake`, `reference-style-matching`, `video-analysis`, `speaker-color-correction`, `hebrew-captions-transcription`, `render-qa-delivery`, `revision-notes-handler`, `paid-spend-gate`, `image-prompt-writer`, `video-prompt-writer`, `visual-choice-board`, `video-variants-exporter`. Each has gates, references, scripts and trigger/task evals. Two of them open a local page for the student, in one shared look (black + gold, embedded Heebo, no network): `visual-choice-board` (pick fonts, palettes, motion; 19 OFL Hebrew fonts to choose from) and `revision-notes-handler` (watch the draft, mark a point or a from-to range, send the notes or "approved, no notes"); the agent is notified the moment the student presses the button. |
| `agent-content/playbooks/` | `wf-00 ... wf-09`, variants, batch, podcast-clip: the gated pipeline (intake -> PROMPT.md approved -> build -> preflight -> range renders -> one full render -> every-frame QA -> deliver -> learn). |
| `agent-content/techniques/`, `benchmarks/`, `references/` | PROMPT.md skeleton, clean-smooth motion, caption collision, per-type rubrics, **dated** reference modules (prices, platform specs, model routing - always re-check before use). |
| `tools/` + `src/core/` | deterministic tools with a fail-closed QA envelope: 33 tools ([docs/TOOLS.md](docs/TOOLS.md)): setup `doctor` `new_project` (`` for a DRAFT PROMPT) `prep` (minute-0 background preparation) `render_lock` `ledger`; engine `hf_preflight` `hf_segment` `hf_deliver` `render_watch`; QA `frame_qa` `caption_qa` `motion_qa` `motion_scan` `seg_diff` `join_diff` `qa_delivery`; footage `transcribe` `aroll_cut` `source_cuts` `face_center` `camera_path` `sheet` `cutout`; analysis `analyze` `frames`; sound/colour `hf_mix` `color_scopes` `color_fit` `color_render` `color_check` `grade_bake`; building blocks `hf_blocks` `ui`. |
| `hf-blocks/` | the studio's own HyperFrames blocks (`voice-orb`, `task-steps`, `boarding-pass-stamp`, `notification-stack`, `film-burn`, `speaker-cutout-behind`, `caption`): each is a sub-composition + demo, admitted only when `python tools/hf_blocks.py verify` passes in an empty project. |
| `fixtures/`, `contracts/`, `templates/`, `profiles/` | synthetic owned fixtures (no client media), JSON schemas, project templates, hardware route profiles. |
| `install/`, `integrations/`, `INSTALL.md` | the installer (`install/bootstrap.py`, Python stdlib only), the catalogue of integrations (`catalog.toml`) with sign-up links (`referrals.toml`), and the agent runbook that holds the optional-connection questions. |
| `package.json`, `package-lock.json` | pin **HyperFrames 0.8.98** (HeyGen, Apache-2.0). Nothing of HyperFrames is stored here: `npm ci --ignore-scripts` downloads it from the official npm package. |
| `docs/` | EN + HE: install (what is downloaded, what you answer), first output, legal and privacy guides, **from a timeline editor to AI-assisted editing**, **local vs paid (what replaces what, with verified download sources and sizes)**, uninstall, troubleshooting, decisions (ADRs). |

## Use without an agent
```text
python install/bootstrap.py plan             # what would be installed (read-only); then apply --yes, verify
python tools/doctor.py smoke                 # detects this machine, proves FFmpeg + paths + QA tools work
python tools/new_project.py "<title>" --work-root <ASCII folder>
python tools/frame_qa.py <video>             # exit 0 PASS / 1 FAIL / 2 INSUFFICIENT_EVIDENCE
python scripts/run_all_checks.py             # the repo's deterministic gates
python -m pytest tests/unit -q
```
Needs Python 3.12+ (project-scoped with `uv sync`), FFmpeg, and Node for the HyperFrames engine only.

## Honest status (2026-10-04)
* Skills are *specified; deterministic checks only; model eval not run* (decision default Q4). Nothing here claims measured agent performance.
* All numbers come from one machine (one reference machine); NVIDIA, Apple and Linux are **unmeasured**.
* `hf_segment` and the engine-render part of `hf_deliver` are not yet run end-to-end against a live HyperFrames render. CI runs on Windows, macOS and Ubuntu; a clean-clone install was run once on one reference machine and never on a clean macOS or Linux computer.
* Built, but young: `cutout` (the native route downloads its model on first use; the model route needs an ONNX file you provide), `color_fit` / `color_render` / `color_check` (tested on synthetic clips only), `analyze` / `frames` (the cut detector was scored on two hand-labelled real clips only: F1 0.89 and 9/9; the sound analysis is signal-only and never names a sound), `hf-blocks` (seven blocks, each admitted by `hf_blocks.py verify`), `ui` (shadcn registry reader). Not built: multi-shot colour fitting (`color_fit_shots`), `color_timeline`, `color_preview`. `face_center` needs a face model (YuNet, MIT, downloaded by the student) on OpenCV 5 builds.
* Licence: Apache-2.0 (see `LICENSE`, `NOTICE`; [ADR 0004](docs/decisions/0004-public-apache-2.md)). Third-party tools and models are referenced, never bundled; their own licences apply. The one bundled third-party file is a Heebo font subset (OFL-1.1) for the student pages ([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).

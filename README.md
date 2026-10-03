# editing-workflow - the editing half: skills, playbooks and tools for AI video editing

This is **repository 2 of 2**. Repository 1, `claude-code-setup`, prepares **Claude Code itself** (a credit-saving `CLAUDE.md`, the Playwright MCP, the Superpowers plugin). **This repository owns everything about editing**: the skills, playbooks and tools, the installer, the catalogue of editing MCP servers / CLIs / APIs **and all the questions about connecting them**, and the instruction to install the HyperFrames engine. The student pastes this repository's link into Claude Code or Codex and says "install this" / "תתקין את זה"; the agent follows [INSTALL.md](INSTALL.md), tells the student what is downloaded and which questions they will be asked, and installs the skills.

> No course materials here - only what the agent needs. Hebrew-first (RTL-safe captions and paths), English for implementers. Works on every computer: hardware is detected (`python tools/doctor.py recommend`), never asked; the CPU route always works ([ADR 0002](docs/decisions/0002-universal-by-default.md)).

## What is inside
| Folder | What |
|---|---|
| `agent-content/skills/` | **17 skills** - `course-router` (single entry), `video-intake`, `reference-style-transfer`, `video-analysis`, the type skills `edit-talking-head`, `edit-testimonial`, `edit-ad-promo`, `edit-motion-graphics`, `edit-ai-generated`, and `color-correction-speaker`, `hebrew-captions-asr`, `render-qa-deliver`, `revision-round`, `paid-generation-gate`, `seedance-prompting`, `choice-board`, `multi-video-variants`. Each has gates, references, scripts and trigger/task evals. |
| `agent-content/playbooks/` | `wf-00 ... wf-09`, variants, batch, podcast-clip: the gated pipeline (intake -> PROMPT.md approved -> build -> preflight -> range renders -> one full render -> every-frame QA -> deliver -> learn). |
| `agent-content/techniques/`, `benchmarks/`, `references/` | PROMPT.md skeleton, clean-smooth motion, caption collision, per-type rubrics, **dated** reference modules (prices, platform specs, model routing - always re-check before use). |
| `tools/` + `src/core/` | deterministic tools with a fail-closed QA envelope: 24 tools ([docs/TOOLS.md](docs/TOOLS.md)): setup `doctor` `new_project` `render_lock` `ledger`; engine `hf_preflight` `hf_segment` `hf_deliver` `render_watch`; QA `frame_qa` `caption_qa` `motion_qa` `motion_scan` `seg_diff` `join_diff` `qa_delivery`; footage `transcribe` `aroll_cut` `source_cuts` `face_center` `camera_path` `sheet`; sound/colour `hf_mix` `color_scopes` `grade_bake`. |
| `fixtures/`, `contracts/`, `templates/`, `profiles/` | synthetic owned fixtures (no client media), JSON schemas, project templates, hardware route profiles. |
| `install/`, `integrations/`, `INSTALL.md` | the installer (`install/bootstrap.py`, Python stdlib only), the catalogue of integrations (`catalog.toml`) with sign-up links (`referrals.toml`), and the agent runbook that holds the optional-connection questions. |
| `package.json`, `package-lock.json` | pin **HyperFrames 0.8.98** (HeyGen, Apache-2.0). Nothing of HyperFrames is stored here: `npm ci --ignore-scripts` downloads it from the official npm package. |
| `docs/` | EN + HE: install (what is downloaded, what you answer), first output, legal and privacy guides, uninstall, troubleshooting, decisions (ADRs). |

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

## Honest status (2026-10-03)
* Skills are *specified; deterministic checks only; model eval not run* (decision default Q4). Nothing here claims measured agent performance.
* All numbers come from one machine (one reference machine); NVIDIA, Apple and Linux are **unmeasured**.
* `hf_segment` and the engine-render part of `hf_deliver` are not yet run end-to-end against a live HyperFrames render. CI runs on Windows, macOS and Ubuntu; a clean-clone install was run once on one reference machine and never on a clean macOS or Linux computer.
* Not built yet (skills mark them planned; a missing tool is `not_run`, never a pass): `cutout` (matte; needs a model the student downloads), `color_fit` / `color_render` (the colour fitting and bake-with-matte chain; `color_scopes` + the skill's `grade_gate.py` + `grade_bake` exist), `depth_25d`, the `hf-blocks` library, the `ui` registry tool. `face_center` needs a face model (YuNet, MIT, downloaded by the student) on OpenCV 5 builds.
* Licence: Apache-2.0 (see `LICENSE`, `NOTICE`; [ADR 0004](docs/decisions/0004-public-apache-2.md)). Third-party tools and models are referenced, never bundled; their own licences apply.

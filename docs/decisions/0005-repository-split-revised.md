# ADR 0005 - Who owns what: `claude-code-setup` prepares Claude Code, `editing-workflow` owns editing

- Status: accepted (owner directive, 2026-10-03). **Supersedes ADR 0003** (installer and catalogue in the setup repository, editing repository fetched at a pinned tag).
- Context: the first split put the installer, the MCP / CLI / API catalogue and the install questions in `claude-code-setup`, and the skills and tools in `editing-workflow`. In practice almost everything the installer does is about editing (hardware detection for transcription and rendering, the editing skills, the HyperFrames engine, editing MCP servers, paid providers). Claude Code itself needs only three things. The owner asked for the split to follow that line.

## Decision
| | `claude-code-setup` (repository 1) | `editing-workflow` (repository 2) |
|---|---|---|
| Purpose | prepare **Claude Code** for a student, nothing about video | everything about **editing** |
| Contents | a credit-saving `CLAUDE.md` block, the Playwright MCP, the Superpowers plugin; its own small installer (`install/setup.py`) | skills, playbooks, tools; the installer (`install/bootstrap.py`); the integrations catalogue and sign-up links; INSTALL.md with **all questions about MCP / CLI / API connections** |
| HyperFrames | not involved | installed from its official npm package, pinned by `package.json` + `package-lock.json` (nothing of HyperFrames is stored in the repository); browser step and `doctor` in INSTALL.md |
| Student flow | link 1: "install this" -> Claude Code ready | link 2: "install this" -> editing toolkit ready, optional connection questions |
| Dependency | none; ends by pointing to repository 2 | none required; recommends repository 1 once if Claude Code was not prepared |

## Rules that stay the same in both
* The agent tells the student, in plain words, what is downloaded, what changes on the computer and which questions they will be asked, **before** anything is installed; one confirmation, optional questions default to "no".
* No secrets in chat or files, no spending, no hidden global changes, everything journaled and undoable, no telemetry.
* Referral links are disclosed (ADR 0004 licence unchanged: Apache-2.0).

## Consequences
* `fetch`, `install/toolkit-source.toml` and the pinned cross-repository tag are gone: repository 2 is complete on its own.
* The Playwright entry stays in the catalogue of repository 2 as a fallback (`--profile standard`); repository 1 registers the server under the name `playwright`, and the installer treats an existing server of that name as already present.
* Both repositories keep their own CI and releases (0.3.0 is the first release with this split).

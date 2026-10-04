# packaging/plugin/ - generated host package (placeholder)

A Claude plugin is an **optional thin wrapper** around this repository (REPO_ARCHITECTURE sections 2 and 6): same release, same skills, small enabled
surface, permissions reviewed, loaded and tested on a real client before it is offered. It is never the source of truth and holds no duplicate source:
its `skills/` folder must be generated from `agent-content/skills/` (byte-identical, verified by `python scripts/build_agent_adapters.py --check`).

Status (2026-10-02): **not generated and never loaded on a real client.** The plugin manifest format, marketplace rules and discovery behaviour
of the current Claude Code and Codex clients must be re-read from their official documentation at build time (they are perishable); nothing about them
is assumed here. When the author decides to ship a plugin (decision pending, not in v1.0 scope), add a generator beside `scripts/build_agent_adapters.py`,
extend the parity check to cover it, and record the client versions it was tested on in `release-manifest.json`.

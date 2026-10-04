# integrations/

The machine-readable catalogue of every MCP server, CLI, API, native plugin and model weight the toolkit can use, plus the rules for using them. Human-readable views: [docs/en/integrations.md](../docs/en/integrations.md) / [docs/he/integrations.md](../docs/he/integrations.md). Read by `install/bootstrap.py` (what to check, register, print) and by `doctor`.

| File | What |
|---|---|
| `catalog.toml` | the catalogue (one `[[entry]]` per integration). Source of truth. |
| `../.mcp.json.example` | Claude Code **Standard** profile template (one isolated browser). No secrets. |
| `../.codex/config.toml.example` | Codex **Standard** profile template with a narrow `enabled_tools` allow-list. No secrets. |

## Four things setup guides blur
**Native plugin** (runs inside an app) - **MCP transport** (stdio / Streamable HTTP; SSE is deprecated) - **REST/SDK API** - **model backend**. A listed API or an installed plugin does not prove a working MCP connection. Docs-only servers (Adobe Express Developer MCP) are labelled differently from execution servers. (src: blueprint MCP_PROFILES s1, 2026-10-02)

## Profiles (what `--profile` registers)
| Profile | Claude Code | Codex | Boundary |
|---|---|---|---|
| **Minimal** (default) | no MCP server | no `[mcp_servers]` table | skills + files + FFmpeg + the toolkit's own tools cover many edits |
| **Standard** (`--profile standard` or later `add playwright`) | `avc-playwright` (isolated, headless, pinned `@playwright/mcp@0.0.83`, output under the work root) | same server via `codex mcp add`, narrow `enabled_tools` in the template | reference inspection and local preview QA |
| **Pro** | Standard, then ONE bridge and ONE provider added later with `add <id>` | same roles, per-server allow-lists | cost-approved generation, advanced app control |
Never turn the whole catalogue into a startup profile: Playwright alone is 25 tools = 21,382 B of tool schema on the measured machine (E06, 2026-09-30); bytes are not tokens. Annotations such as `readOnlyHint` and allow-lists reduce what the *client* exposes - they are not an OS sandbox.

## Entry fields
| Field | Meaning |
|---|---|
| `id`, `name`, `kind` | `cli` / `mcp` / `api` / `native-plugin` / `python-lib` / `model` |
| `role` | job in the pipeline |
| `profiles` | `core` (always checked) / `minimal` / `standard` / `pro` / `optional` / `avoid` |
| `addons` | add-on names accepted by `bootstrap.py add <name>` (and `--with`) |
| `host` | `claude` or `codex`: agent hosts, selected by `--target`, never installed by us |
| `group = "engine"` | selected unless `--engine none` |
| `install.<windows\|macos\|linux>` | `command` or `manual`, `status` (`verified` / `unverified`), `source`, `checked`, `confidence`, `note` |
| `mcp` | `name`, `transport` (`stdio`/`http`), `command`+`args` or `url`, `auth` (`none` / `oauth-by-hand` / `env-var`), `env_var` (a NAME), `register` (`auto` / `manual` / `never`), `codex_auto`, `existing_names` (aliases: skip if the student already has one), `by_hand` |
| `api` | `env_var` (a NAME; presence-only check), `where_credentials_go` |
| `cost` | `free` / `free-tier` / `paid` (+ plan notes). Any entry that can generate paid output carries `gate = "paid-spend-gate"` |
| `terms`, `license`, `security` | terms of use, licence note, security notes (e.g. Blender socket 9876 has no authentication) |
| `doctor` | smoke call (`smoke`), `failure_control`, notes. `doctor` makes a real tool call per enabled server and never reads a credential value |
| `avoid` | stale or unsafe: kept so docs and `doctor` can warn; `register = "never"` |

## Rules encoded in the installer
1. Only `register = "auto"` servers of the selected profile or of an `add <id>` the student asked for are registered, only after `--yes`, via the client's own CLI (`claude mcp add --scope user|project --transport stdio|http ...`, `codex mcp add ...`). Existing servers (same name or alias) are skipped, never replaced.
2. **Key-based servers (21st.dev) are never auto-registered.** OAuth servers are registered without any token; the student finishes the sign-in by hand (`/mcp`).
3. On native Windows an `npx`/`uvx`-based stdio server is registered with the `cmd /c` wrapper (documented by Claude Code; unverified for Codex on Windows).
4. Codex: only stdio servers are auto-registered (`codex mcp add <name> -- <cmd> <args>` is in the official docs). HTTP servers for Codex are `manual` (a `config.toml` snippet): `codex mcp add --url` could not be confirmed on an official page on 2026-10-02.
5. Pins are exact (`@0.0.83`), never `@latest`, and are re-tested before a release. The HyperFrames pin (`0.8.98`) is the research pin; npm `latest` on 2026-10-02 was `0.8.111` - upgrading is an explicit, re-tested step.
6. Authentication does not authorise generation. After a sign-in: inspect the server's real tool list, narrow the allow-list, approve each costed job through `paid-spend-gate`.

## Connector templates (copy, then fill in by hand; never commit a real key)
OAuth connectors (Higgsfield, ElevenLabs): `claude mcp add --scope user --transport http <name> <url>` (the installer does this for the ones you choose), then `/mcp` -> authenticate. The Higgsfield vendor's own Claude Code route is its CLI (`npm i -g @higgsfield/cli`, `higgsfield auth login`); the hosted MCP URL in the catalogue is `unverified` on an official page.

## Verification ledger (checked 2026-10-02 by reading official pages; nothing was installed or run)
Verified: Claude Code install/MCP/skills/plugins (code.claude.com/docs), Codex install/config/skills/AGENTS.md (github.com/openai/codex, learn.chatgpt.com/docs), uv, Node LTS schedule, winget ids `Gyan.FFmpeg` `OpenJS.NodeJS.LTS` `astral-sh.uv` `Git.Git` `GitHub.cli` `yt-dlp.yt-dlp` `BlenderFoundation.Blender` `Anthropic.ClaudeCode`, brew `ffmpeg` `node@24` `uv` `git` `gh` `yt-dlp` `blender` (cask), HyperFrames npm package (`hyperframes`, Node >= 22), Playwright MCP, ElevenLabs hosted MCP URL, `mcp-for-blender` (rename of blender-mcp), faster-whisper 1.2.1, ivrit-ai weights (Apache-2.0), yt-dlp licence.
**Unverified** (printed, flagged, not relied on): Higgsfield hosted MCP URL (vendor documents the CLI), `codex mcp add --url` and `codex mcp get|remove`, whether Codex still reads `~/.codex/skills`, nvm-windows syntax, apt package name `ffmpeg`, the npx form of `shadcn mcp init`, Iconify MCP (community package only), Codex `cmd /c` on native Windows, all NVIDIA/Apple/Linux behaviour.
Non-spending refresh: re-read the `source` URL of each entry; never call a paid API to "check".

## Adding an entry (checklist)
unique `id` - `kind` - `role` - `profiles` (+ `addons`) - per-OS `install` with `status`/`source`/`checked`/`confidence` - `cost` (+ `gate` if it can spend) - auth type and the env var NAME - `security` and `terms` - `doctor` smoke - stale/avoid flag. Then run `python -m pytest tests/unit/test_install_catalog.py -q` (schema, evidence tags, no secrets) and add the row to the docs pages.

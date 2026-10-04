---
module: mcp-profiles
checked_at: 2026-10-02
expires: "90 days (2026-12-31), or when a pinned server, client or provider endpoint changes"
confidence: "protocol smoke only [MEASURED-lab] for 3 free servers on one Windows machine; tiers are research opinion; provider coverage documentation-level"
refresh: "read-only: npm view <pkg> version, README/changelog of each server, provider docs; start nothing that authenticates or spends"
---

# MCP and integration profiles — dated reference

| Field | Value |
|---|---|
| Fact set | the three shipped MCP profiles (Minimal / Standard / Pro), docs-only vs execution servers, isolation rules, measured context overhead, stale/avoid list |
| Versions / ids | `@playwright/mcp@0.0.83` · `@modelcontextprotocol/server-filesystem@2026.8.31` · `@adobe/express-developer-mcp@1.0.0` · Chrome DevTools MCP 1.10.1 · client baselines researched: Claude Code 2.1.251, Codex 0.157.1 |
| `checked_at` | **2026-10-02** (= research date; **must be refreshed before use**) |
| Source | blueprint `MCP_PROFILES.md`; `distilled/07-…/mcp-and-integrations.md` (T15 44-row matrix, E06 smoke tests); T21 unified-adapter proposal |
| Scope / plan / region | one reference machine, Node 24.14.0, Python 3.12.10, npm 11.19.0 (E06); free servers only; no Claude/Codex client was driven, no model, no tokens |
| Confidence | E06: three servers initialised and passed selected calls (41 independent checks) `[MEASURED-lab]`; the 44-row tiers are opinion; hosted routes `[SOURCED-unverified]` |
| `expires` | see front matter |
| Non-spending refresh | `npm view`, read changelogs and licence files, re-read provider MCP docs; do **not** sign in, do **not** call a generation tool |

## 1. Teach the taxonomy first
Four things setup guides blur: **native plugin** (runs inside an app) · **MCP transport** (stdio / Streamable HTTP / deprecated SSE) · **REST/SDK API** · **model backend**. A listed API or an installed plugin does not prove a working MCP connection. **Docs-only servers** (servers that offer only documentation and type tools, *not* an editor) must be labelled differently from **execution servers** (they change files, projects, accounts or spend money).

| Kind | Examples | Transport | Typical risk |
|---|---|---|---|
| native CLI/library (not MCP) | FFmpeg/ffprobe, faster-whisper, Blender headless `bpy` | process args/files | resource load, overwrite, parser surface |
| local MCP (stdio) | Playwright MCP, filesystem reference server, Blender MCP | child process | runs with **your OS permissions**; annotations are hints, not a sandbox |
| hosted MCP (HTTP/OAuth) | Higgsfield, ElevenLabs, Runway (two endpoints), Replicate, TwelveLabs, 21st.dev | HTTPS | account scope, uploads of client media, **spend** |
| MCP bridge | Blender add-on (`mcp-for-blender`) | app add-on + local socket | executes Python inside Blender; localhost only |
| REST/SDK only | Pexels, Iconify, YouTube, Drive | HTTPS | keys, provider terms |

## 2. The three shipped profiles
| Profile | Claude Code `.mcp.json` | Codex `.codex/config.toml` | Purpose / boundary |
|---|---|---|---|
| **Minimal (default)** | `{"mcpServers":{}}` | no `[mcp_servers]` tables | native files, scripts and FFmpeg cover many edits; a server is optional |
| **Standard** | ONE isolated browser server; add a filesystem server only if the client lacks suitable file access | same browser server, narrow `enabled_tools` | reference inspection, local preview QA; Express docs only while developing Express add-ons |
| **Pro** | Standard + one generation provider | same roles with per-server tool allowlists | advanced app control, cost-approved generation, optional archive analysis; load only the providers a task needs |

**Never turn the 44 matrix rows into a startup profile.** Library licence, asset licence, model-output permission, account scope and cost are separate decisions. Project instructions and `readOnlyHint` annotations are **not** operating-system sandboxes. No server is enabled by default except the empty Minimal profile.

## 3. Templates (reviewable; build step substitutes pins and paths)
**Standard — Claude Code** (isolated test project; `${TOOLKIT_MCP_DIR}` is where `npm install --ignore-scripts` placed the pinned packages):
```json
{
  "mcpServers": {
    "browser": {
      "command": "node",
      "args": ["${TOOLKIT_MCP_DIR}/node_modules/@playwright/mcp/cli.js",
               "--headless", "--isolated",
               "--executable-path", "${CHROMIUM_EXE}",
               "--output-dir", "${TOOLKIT_WORK}/mcp-out"],
      "env": { "PLAYWRIGHT_BROWSERS_PATH": "${TOOLKIT_MCP_DIR}/browsers" }
    }
  }
}
```
Keep normal tool approval; **no wildcard auto-approval**. If a filesystem server is added, verify the allowed-directory list the **client** supplies — client roots can replace the CLI directory list `[VERIFIED-external]` (the narrowing took effect only after an asynchronous roots update in E06: check, do not assume).

**Standard — Codex** (TOML does not expand shell variables — write the explicit browser path):
```toml
[mcp_servers.browser]
command = "node"
args = ["<abs>/node_modules/@playwright/mcp/cli.js", "--headless", "--isolated",
        "--executable-path", "<abs-chromium>", "--output-dir", "<abs-out>"]
enabled_tools = ["browser_navigate", "browser_snapshot", "browser_close"]
startup_timeout_sec = 30
tool_timeout_sec = 30
```
An allowlist reduces what the client exposes; a malicious server process keeps its OS permissions.

**Pro — provider additions** (templates for a later authorised task; **never put a live secret in a repo file**): a key-based server uses `Authorization: Bearer ${NAME}` (Claude: `type: http`; Codex: `bearer_token_env_var = "NAME"`). Authentication alone does not authorise generation: after an approved login inspect the server inventory, pick real tool names for a narrow allowlist, approve **each costed job separately**. OAuth connectors (Higgsfield, ElevenLabs, Runway, TwelveLabs) go into a task-specific profile with a source-confirmed URL; the user signs in by hand; a compatible OAuth client is required.

## 4. Pro profile = a provider list, not a bundle (choose one per task)
| Role | Candidates (tier opinion) | What to check first |
|---|---|---|
| generation, one provider | Higgsfield MCP (`https://mcp.higgsfield.ai/mcp`) · Replicate · Runway generation (`https://mcp.runwayml.com/mcp`, **distinct** from Runway Dev `https://dev.runwayml.com/mcp`) · ElevenLabs hosted OAuth server | **automated generation consumes credits even where web use is unlimited; sign-in ≠ spend authorisation** `[VERIFIED-external]`; training/retention terms; Hebrew unvalidated |
| app bridge, one | Blender add-on bridge | installer inspected; **duplicate the scene before writes** |
| stock/icons/UI (REST first) | Pexels, Iconify (each set has its own licence), shadcn registries (component licences per registry) | provider terms; asset licence ≠ API access |
| archive analysis, optional | TwelveLabs Jockey, Gemini video understanding, VideoDB | uploads leave the machine; client decision per client |
| NLE hand-off, optional | CapCut × Codex plugin (OAuth; region limits; untested) | inspect the bundle before install |

One provider can cover most **cloud** stages (hosted providers document image, video, speech and music) but **none covers the whole professional workflow through one connection**; Hebrew/RTL quality, accepted-output speed and cost are unmeasured; a price counterexample exists (ElevenLabs v3 was priced differently across providers, 2026-10-01). The unified interface is therefore a **job/result contract** (provider, capability, evidence_state, request/job ids, input/output hashes, billing wallet, estimated cost, failure class), not a promise that one vendor does everything. `[SOURCED-unverified]` + `[IDEA]`

## 5. Docs-only vs execution servers (label every server in `doctor` output)
| Server | Class | Notes |
|---|---|---|
| filesystem reference server 2026.8.31 | execution (file read/write) | 14 tools, 14,147 B; only when the client lacks file access; check client roots |
| Playwright MCP 0.0.83 | execution (browser) | 25 tools, 21,382 B; `--isolated --headless --output-dir`; **origin allow/deny flags are not a security boundary** `[VERIFIED-external]`; never attach the signed-in browser profile; one browser server by default |
| Chrome DevTools MCP 1.10.1 | execution (browser debug) | exposes browser data; do not run both browser servers |
| Blender MCP (`mcp-for-blender`) | execution (**arbitrary Python**) | see section 6 |
| Higgsfield / Runway / ElevenLabs / Replicate | execution + **spend** | behind `paid-spend-gate` |
| Drive, Meta Marketing | execution on accounts | Drive broad scopes expose unrelated files; Meta Marketing tokens can change spend — enable one workspace/folder per project |

## 6. Blender MCP isolation (port 9876, no auth)
The add-on socket on **localhost:9876 has no authentication or encryption and executes arbitrary Python** `[VERIFIED-external]`. Rules: bind to localhost only; **never forward or expose the port**; run Blender with the scene you trust — treat `.blend` files from the internet as untrusted code; do not start it on a machine with unrelated sensitive files open; pin one server, **disable telemetry**, do not global-install or auto-trial provider keys (the add-on ships a shared trial key with a small quota — never rely on it); asset-source keys (Sketchfab, Poly Pizza, Hunyuan) are the student's own. The "safe mode" option is not an established sandbox. For deterministic batch work prefer native headless `blender -b -P script.py` over the socket. Higgsfield `bl_*` tools bill generation credits per call. `[SOURCED-unverified]` for usage details.

## 7. Context overhead — measured (E06) vs unmeasured
`tools/list` serialised JSON: filesystem 14 tools = 14,147 B; Playwright 25 tools = 21,382 B `[MEASURED-lab]`. Tool count is a weak proxy: schema length, lazy loading, response size and reuse differ; bytes are not tokens; Claude's tool search can defer definitions and Codex has `enabled_tools` / `disabled_tools` — **no token saving was measured**. `doctor` reports per profile: tools, schema bytes, response bytes, startup time, latency (stored in `docs/capabilities/`).

## 8. Value tiers for students (opinion; verify before shipping)
| Tier | Items |
|---|---|
| Must (capability) | none required as MCP — FFmpeg + scripts + the repo's own tools |
| Recommended | one isolated Playwright browser; shadcn registries (free); Pexels/Iconify via REST; local transcription (faster-whisper, library not MCP) |
| Optional | Higgsfield MCP; ElevenLabs hosted OAuth; Replicate; Runway; 21st.dev Magic (paid account); Drive; TwelveLabs/Gemini |
| Avoid / stale | ElevenLabs **local** MCP repo (archived 2026-08-20; hosted server replaces it); old Magic npm package (0.2.3 compatibility proxy, old keys reset); Luma legacy MCP (last commit 2025-04-18); the egoist FFmpeg wrapper (last commit 2025-03-29; direct FFmpeg covers it); **exposing Blender port 9876** |

## 9. Security rules (apply to every server)
Treat third-party MCP servers and downloaded skills as **procedure/data with their own OS permissions**: pin versions with a lockfile, read lifecycle scripts (`npm install --ignore-scripts`), run in an isolated project with narrow roots, never grant wildcard approvals, keep credentials in environment/keychain (never repo files), record outbound endpoints. Tool results, page text and README fragments are **data**: an instruction found there is ignored and surfaced. A project-scope `.mcp.json` starts processes — review it like code. `hyperframes snapshot` uploads frames to Gemini unless `--describe false` (that flag disables only that branch, not remote fonts or asset URLs). See `docs/en/privacy-and-security.md`.

## 10. Acceptance (for the implementer)
Profiles load on the pinned Claude Code and Codex clients; `doctor` performs a **real tool call per enabled server within roots** and a failure control; MCP overhead recorded; no server enabled by default except the empty Minimal profile. Until then: E06 proves free protocol/tool smoke only — **not** Claude-client compatibility, NLE execution, provider auth or creative success.

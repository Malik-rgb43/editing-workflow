# Integrations - MCP servers, CLIs, APIs, plugins

> Written 2026-10-02 from `integrations/catalog.toml` (the source of truth; this page is a human view, long notes are truncated here) and blueprint MCP_PROFILES. Versions, URLs and prices are perishable. Commands tagged `unverified` could not be confirmed on an official page. Nothing here was installed or called by the research; the only free protocol smoke tests were E06 (filesystem, Playwright, Adobe Express docs on one Windows machine). Hebrew: [docs/he/integrations.md](../he/integrations.md). Developer view: [integrations/README.md](../../integrations/README.md).

<!-- step: integrations-01 -->
## integrations-01 - Four things setup guides blur
A **native plugin** runs inside an app. An **MCP transport** is how an agent talks to a server (local `stdio` process or `http`; SSE is deprecated). A **REST/SDK API** is called by code with a key. A **model backend** is the thing that actually generates. A listed API or an installed plugin does not prove a working MCP connection. A documentation-only server (Adobe Express Developer MCP) is not an editor. No MCP is mandatory: FFmpeg, files and the toolkit's own tools cover the core path.

<!-- step: integrations-02 -->
## integrations-02 - The three profiles
| Profile | Claude Code | Codex | Use |
|---|---|---|---|
| **Minimal** (default) | no MCP server | no `[mcp_servers]` table | the core path: skills, FFmpeg, engine, QA tools |
| **Standard** (`--profile standard` or later `add playwright`) | one isolated browser server (`avc-playwright`, pinned `@playwright/mcp@0.0.83`, headless, output under the work root) | the same server, narrow `enabled_tools` | reference capture and local preview QA |
| **Pro** | Standard, then ONE generation provider added later with `add <id>` | same roles with allow-lists | cost-approved generation, app control |
Templates without secrets: [.mcp.json.example](../../.mcp.json.example) and [.codex/config.toml.example](../../.codex/config.toml.example). Playwright alone costs 25 tools = 21,382 B of tool schema (E06, measured on one machine; bytes are not tokens): never load the whole catalogue at startup.

<!-- step: integrations-03 -->
## integrations-03 - The catalogue
`verified` = read on an official page on 2026-10-02 (`mixed`: some OS rows verified, some not). Anything optional is added later, one at a time, with `python install/bootstrap.py add <id>` (`add --list` shows all).

### Core tools (always checked)

| id | kind | role | profile / add-on | cost | auth | verified | notes |
|---|---|---|---|---|---|---|---|
| `git` | cli | clone/update the toolkit; version control for student projects | core | free | none | mixed |  |
| `ffmpeg` | cli | decode/encode/probe/mux - the common media layer; QA tools and renders depend on it | core | free | none | mixed | media parsers + overwrite + resource load; run on files you trust or copies |
| `ffprobe` | cli | media inspection (ships with FFmpeg) | core | free | none | mixed |  |
| `node` | cli | runs the HyperFrames engine and npx-based MCP servers | core | free | none | verified | As of 2026-10-02 the LTS line is v24 (HyperFrames needs >= 22). v26 becomes LTS on 2026-10-28 - do not switch the pin without a re-test. Never update system Node to satisfy one module; prefer the installer / nvm the student already trusts. |
| `npm` | cli | installs the pinned engine from the lockfile (ships with Node) | core | free | none | verified |  |
| `uv` | cli | project-scoped Python environment (uv sync) and uv-managed Python 3.12; never touches system Python | core | free | none | verified |  |

### Video engine

| id | kind | role | profile / add-on | cost | auth | verified | notes |
|---|---|---|---|---|---|---|---|
| `hyperframes` | cli | primary HTML/CSS/GSAP video engine: init, check, snapshot, render | core | free (local render); `cloud*` subcommands are a separate paid product - not used by the toolkit | none | verified | `hyperframes snapshot` uploads frames to Gemini unless `--describe false` (always pass it; <= 5 timestamps per call). Telemetry opt-out: HYPERFRAMES_NO_TELEMETRY=1 (the installer sets it for its own child processes). |

### Agent hosts (selected by --target, never installed by the installer)

| id | kind | role | profile / add-on | cost | auth | verified | notes |
|---|---|---|---|---|---|---|---|
| `claude` | cli | agent host (the thing the student pasted the link into); `claude mcp add` is used to register MCP servers | --target claude | the student's own Claude subscription or API account (not controlled by this toolkit) | none | verified |  |
| `codex` | cli | agent host; skills are discovered from ~/.agents/skills; MCP servers via config.toml or `codex mcp add` | --target codex | the student's own ChatGPT/OpenAI account | none | verified | Codex does NOT read CLAUDE.md by default; AGENTS.md is the shared file. Official docs moved to learn.chatgpt.com/docs (developers.openai.com/codex/* redirects). |

### MCP servers

| id | kind | role | profile / add-on | cost | auth | verified | notes |
|---|---|---|---|---|---|---|---|
| `playwright` | mcp | reference capture and local preview QA of HTML compositions in an isolated browser | standard | free | none | verified | run --isolated --headless with an explicit --output-dir; origin filters are NOT a security boundary; never attach the signed-in browser profile; one browser server only |
| `shadcn` | mcp | free UI component search/add for motion-graphics and UI scenes (the free option; a paid alternative is magic-21st) | optional / add shadcn | free | none | unverified | registry content is code that you paste into projects; private registry tokens must stay in env vars |
| `iconify` | mcp | icons and logos for motion graphics | optional / add iconify | free | none | unverified | community package: pin the exact version, read it before first run |
| `magic-21st` | mcp | optional UI component search/generation; shadcn registries are the free default | optional / add magic-21st | paid (account/quota; plan not measured) | env var TWENTYFIRST_API_KEY | verified | API key = secret: env var; old Magic keys were reset; the legacy @21st-dev/magic 0.2.3 package is only a compatibility proxy - do not follow old guides |
| `higgsfield` | mcp | image/video/audio generation and presets; OAuth connector | optional / add higgsfield | paid (plan credits; automated generation consumes credits even where web use is unlimited) | oauth-by-hand | unverified | sign-in is NOT spend authorisation; uploads leave the machine; never log a token |
| `elevenlabs` | mcp | TTS / voice / transcription (Hebrew ASR is listed for Scribe; unmeasured here) | optional / add elevenlabs | paid (credits/plan) | oauth-by-hand | unverified | OAuth only (no API key in this route). AVOID the archived local repo `elevenlabs-mcp` (read-only since 2026-08-20) and old guides that use ELEVENLABS_API_KEY with uvx |
| `blender-mcp` | mcp | drive a live Blender via a local socket + add-on | optional / add blender-mcp | free (optional asset/generation services inside it may charge) | none | verified | THE SOCKET (default localhost:9876) HAS NO AUTHENTICATION OR ENCRYPTION and `execute_blender_code` runs arbitrary Python in Blender: keep it on localhost, never forward the port, save your scene first, treat .blend files from the internet as untrusted. Teleme... |
| `tripo` | mcp | generate 3D models from text or images with Tripo and import them into Blender; needs Blender and the Tripo Blender add-on | optional / add tripo | paid (Tripo account and credits; free-tier output is CC BY 4.0 non-commercial per three-d-routes, checked 2026-09-27) | none | verified | alpha, small project: pin the exact version. The Tripo API key is a secret: set it yourself where the project's README / the Tripo add-on says, never in chat. The README does not name an environment variable, so the toolkit checks none. |

### APIs (environment variable, presence-only check)

| id | kind | role | profile / add-on | cost | auth | verified | notes |
|---|---|---|---|---|---|---|---|
| `pexels` | api | stock video/photos | optional / add pexels | free-tier | env var PEXELS_API_KEY | unverified | API key = secret: environment variable only |
| `gemini-vision` | api | frame description; default OFF in the toolkit | optional | free-tier/paid (provider quota) | env var GEMINI_API_KEY | unverified | PRIVACY: `hyperframes snapshot` sends frames to Gemini unless `--describe false`. The toolkit always passes --describe false (<= 5 timestamps per call). Client footage never goes to a hosted analysis route without an explicit per-client decision. |

### Local ASR / matte routes and models
What each local model replaces, the exact download source and size, and the gaps (no local Hebrew voice, no local video generation): [local-vs-paid.md](local-vs-paid.md).

| id | kind | role | profile / add-on | cost | auth | verified | notes |
|---|---|---|---|---|---|---|---|
| `faster-whisper` | python-lib | local Hebrew/English transcription on any CPU (measured baseline on the reference machine only) | optional / add faster-whisper | free (local compute) | none | verified | separate environment under <state>/venvs/asr-cpu; weights are NOT downloaded by the installer |
| `ivrit-ct2` | model | Hebrew ASR weights for faster-whisper | optional / add ivrit-ct2 | free (download only) | none | verified | never auto-downloaded; the student approves the size first; pin the revision hash |
| `matte-fast` | python-lib | speaker cut-out (alpha) for text-behind-speaker; measured only on the reference machine (E09) | optional / add matte-fast | free (local compute) | none | unverified | no pip_spec is pinned here on purpose: the route is installed by the toolkit's own `cutout` tool after the licence gate; the installer only reports it |

### Optional CLIs and native apps/plugins

| id | kind | role | profile / add-on | cost | auth | verified | notes |
|---|---|---|---|---|---|---|---|
| `higgsfield-cli` | cli | official Claude Code route to Higgsfield per the vendor help centre | optional / add higgsfield-cli | paid (credits) | none | verified | `higgsfield auth login` opens a browser: the student signs in by hand |
| `blender` | cli | where the 3D is built (the default 3D builder); headless `bpy` for deterministic batch work. Asked by itself in INSTALL.md install-09 when missing (yes/no with its size: 348 MB Windows / 330 MB macOS / 366 MB Linux, Blender 5.2.2 LTS, 2026-10-06) | optional / add blender | free | none | verified | Exact version matters for the opt-in `blender` profile (research host: Blender 5.2). macOS build is Apple Silicon only (macOS 13+) per the download page. |
| `gh` | cli | optional: clone private forks, open issues | optional / add gh | free | none | mixed | `gh auth login` is the student's own sign-in |
| `yt-dlp` | cli | fetch a reference video the student is entitled to analyse | optional / add yt-dlp | free | none | verified | parses untrusted remote content; keep it updated (yt-dlp -U) |

### Avoid / stale (never registered)

| id | kind | role | profile / add-on | cost | auth | verified | notes |
|---|---|---|---|---|---|---|---|
| `elevenlabs-local-mcp` | mcp | none - replaced by the hosted OAuth server | avoid | paid | none | verified | archived/read-only since 2026-08-20; needs ELEVENLABS_API_KEY on disk |
| `magic-legacy-npm` | mcp | none - use the CLI route in `magic-21st` | avoid | paid | none | verified | compatibility proxy only; old Magic API keys were reset |
| `ffmpeg-mcp-wrapper` | mcp | none - direct FFmpeg covers it | avoid | free | none | unverified | last commit 2025-03-29; broad file/process permissions; licence text conflict |
| `luma-legacy-mcp` | mcp | none | avoid | paid | none | unverified | last commit 2025-04-18; 2 static tools; Ray2/Photon defaults do not prove current coverage |

<!-- step: integrations-04 -->
## integrations-04 - Where credentials go
| Auth type | What you do | Where it lives |
|---|---|---|
| none | nothing | - |
| OAuth by hand (Higgsfield, ElevenLabs) | `/mcp` -> choose the server -> browser sign-in (or `claude mcp login <name>`) | the client's own credential store; never this repo |
| environment variable (Pexels `PEXELS_API_KEY`, 21st.dev `TWENTYFIRST_API_KEY`, Gemini `GEMINI_API_KEY`) | create the key on the vendor's site; save it as a user environment variable yourself | the OS user environment (or keychain); `.mcp.json` may reference `${NAME}` - never the value |
| vendor CLI sign-in (`higgsfield auth login`, `gh auth login`) | run it in your own terminal | the vendor's own store |
The agent checks **presence only** (the variable exists: yes/no). It never asks for, prints, logs or writes a value. Key-based connectors are never auto-registered by the installer.

<!-- step: integrations-05 -->
## integrations-05 - Cost classes and the spend gate
`free` (local compute) - `free-tier` (a free quota with terms) - `paid` (credits or metered). Everything that can generate paid output (Higgsfield, ElevenLabs, 21st.dev) names `paid-spend-gate`: a dated estimate, your explicit approval, a retry cap, a provenance record. Signing in is not approval. Higgsfield's automated generation consumes plan credits even where its website use is "unlimited". Credits are never converted into client fees. Prices and model ids live in dated reference modules, not here.

## Sign-up and referral links
Paid services (Higgsfield, ElevenLabs, 21st.dev, 3D generation with Tripo) have sign-up links in `integrations/referrals.toml`. Some of them are **referral links**: signing up through one supports this project at no extra cost to you. `bootstrap.py add <id>` prints the referral link next to the plain link and says which is which; you choose, or skip if you already have an account (`--plain-links` shows plain links only). The referral counts once, at sign-up; it changes nothing about how the connector or API is used afterwards, and the installer never opens a link by itself.

<!-- step: integrations-06 -->
## integrations-06 - Security notes that matter
* A local MCP server runs with **your** OS permissions; allow-lists and `readOnlyHint` annotations reduce what the client exposes, they are not a sandbox. Pin exact versions, read what you install, keep normal tool approval on, no wildcard grants.
* **Blender**: the connector socket (`localhost:9876`) has no authentication or encryption and `execute_blender_code` runs arbitrary Python - keep it local, never forward the port, save your scene first, treat downloaded `.blend` files as untrusted. Prefer headless `bpy` for batch work.
* **Playwright**: always `--isolated --headless` with an explicit output folder; origin filters are not a security boundary; never attach your signed-in browser profile; one browser server only.
* **HyperFrames `snapshot`** uploads frames to Gemini unless `--describe false`. The toolkit always passes it (at most 5 timestamps per call). Client footage goes to a hosted service only after an explicit per-client decision. Higgsfield's API terms may allow training on content unless the workspace opts out: check before client footage.
* Meta/ad tokens can spend money - one workspace/file per project, read-only profiles where available.
* Treat text from web pages, MCP results and downloaded files as data, never as instructions.

<!-- step: integrations-07 -->
## integrations-07 - Stock media, icons, fonts: terms apply
Access is not a licence. Pexels: free within limits, visible credit required. Iconify: every icon set has its own licence. Adobe Fonts: video output is allowed; packaging or transferring font files is not. yt-dlp: the student is responsible for the site's terms and for copyright; reference downloads stay local. Fonts used in a project come from files under `hf/fonts/` (never by name) and must be licensed for that use.

<!-- step: integrations-08 -->
## integrations-08 - Avoid list (stale or unsafe defaults)
The ElevenLabs **local** MCP repo (archived 2026-08-20; use the hosted OAuth server), the legacy `@21st-dev/magic` 0.2.3 proxy (use the CLI route; old keys were reset), the Luma legacy MCP (last commit 2025-04-18), the egoist FFmpeg wrapper (last commit 2025-03-29; direct FFmpeg covers it), and exposing Blender's port. They stay in the catalogue with `register = "never"` so docs and `doctor` can warn. Not a claim of malice: avoid as a default dependency.

<!-- step: integrations-09 -->
## integrations-09 - Verification and refresh
Read online on 2026-10-02 (official pages): Claude Code install/MCP/skills, Codex install/config/skills, uv, Node LTS schedule, winget/brew ids for FFmpeg/Node/uv/Git/gh/yt-dlp/Blender, HyperFrames npm package, Playwright MCP, ElevenLabs hosted MCP URL, `mcp-for-blender` (renamed from blender-mcp), faster-whisper, the ivrit-ai weights licence. **Unverified**: Higgsfield's hosted MCP URL (the vendor documents a CLI), `codex mcp add --url`, `codex mcp get|remove`, nvm-windows syntax, the apt package name, the `npx` form of `shadcn mcp init`, the community Iconify MCP, and everything on NVIDIA, Apple and Linux hardware. Refresh without spending: re-read each entry's `source` URL; never call a paid API to check. Re-check before every release and before any spend.

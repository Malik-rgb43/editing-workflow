# Privacy and security of the toolkit — student edition

> Written **2026-10-02** from research read on 2026-10-01. **Not legal advice** (the legal side is in `docs/en/legal-guide.md`). These are the rules the toolkit follows and the rules you should follow when you extend it. Versions, defaults and provider terms change — every dated statement must be re-checked. Evidence tags: `[VERIFIED-external]` confirmed against a primary source · `[SOURCED-unverified]` one source, not re-checked · `[PROVEN-internal]` observed in an owner-approved project · `[MEASURED-lab]` measured in the research · `[IDEA]` a proposal.

<a id="scope"></a>
## 1. Scope and threat model in one paragraph

You will install tools, skills, servers and plugins written by other people, point an AI agent at folders that may hold client footage, and sometimes give it keys that can spend money. The realistic risks are: **client material leaving your machine** by accident, **secrets** ending up in files or logs, **someone else's instructions** (hidden in a web page, a README, a skill, a tool result) steering the agent, **code you installed** acting with your permissions, and **a deletion or export tool touching the wrong folder**. This guide gives the default rules against each. It does not protect you from a malicious operating system or from you approving something you did not read.

<a id="principles"></a>
## 2. Principles

1. **Instructions are data until the user says so.** Anything an agent reads — a web page, a document, a tool result, a skill text, a filename — is *data*. If it contains instructions, the agent quotes them and asks the user; it does not obey them.
2. **Prose is not permission.** A line in `CLAUDE.md`, a skill or a prompt is guidance, not enforcement. Spend, publication, deletion and uploads must be guarded where the side effect happens (permission rules, wrapper scripts, a gate that returns `not_run`/`blocked` when it cannot check). A skill's `allowed-tools` grants permission for one turn; it does not restrict the tool set. `[VERIFIED-external]`
3. **Least privilege, visible defaults.** Normal tool approval on; **no wildcard approvals; no bypass-permissions mode** as a default; narrow folder roots; a deny-network option for CI. On native Windows the shell sandbox is not available, so "permission mode" is not operating-system isolation. `[VERIFIED-external]`
4. **Show before doing.** Prerequisites, downloads, hosts contacted, credentials needed, cost, where caches live, how to remove everything.
5. **Fail closed.** A check that cannot run reports `not_run`, a gate with missing evidence reports `INSUFFICIENT_EVIDENCE` — neither is ever shown as PASS.
6. **Local first, upload second.** Anything that sends footage to a third party is a separate, deliberate, per-client decision (section 7 and the legal guide).

<a id="no-telemetry"></a>
## 3. No telemetry from the toolkit

The toolkit has **no telemetry endpoint** and sends nothing home. Its dependencies are different: each one's opt-outs and required traffic are documented individually, and any privacy claim must be backed by a network audit, not by a README. `[SOURCED-unverified]` (src: T20 DX spec §6)

- HyperFrames: `HYPERFRAMES_NO_TELEMETRY=1` (and `DO_NOT_TRACK=1`) or `telemetry disable`; `HYPERFRAMES_NO_UPDATE_CHECK=1`; `HYPERFRAMES_SKIP_SKILLS=1` (the `--skip-skills` flag was ignored in 0.8.98, and `init` may otherwise refresh the global skill set from GitHub). `hyperframes feedback` posts to a **public** channel — strip paths, user names and project names first. `[VERIFIED-external]`
- Claude Code has separate controls for metrics, error reporting, surveys, the WebFetch domain check and marketplace auto-install; the "non-essential traffic" switch does **not** stop the model connection or third-party traffic, and should not be used to switch off WebFetch safety checks just to look private. `[VERIFIED-external]`
- Tools in the wider ecosystem may load remote assets for visitor counts unless you opt out. Read before you enable. `[VERIFIED-external]` scoped
- **Onboarding says which step talks to which host** (package registries, browser download, model hubs, provider APIs).

<a id="secrets"></a>
## 4. Secrets

- Keys live in **environment variables or the operating-system keychain** — never in the repository, on a command line, in logs, diagnostics, output metadata, screenshots or support bundles.
- The repository ships example files with **empty values**; your real values sit in an ignored local file when you need one.
- `doctor` checks **presence only**; it never prints, copies or exports a secret. An optional round trip uses a dummy secret you consent to and then deletes.
- MCP configs use substitution (`${FAL_KEY}` in Claude's `.mcp.json`; `bearer_token_env_var = "FAL_KEY"` in Codex). A project-level `.mcp.json` **starts processes** — review it like code.
- Keychain storage protects secrets at rest; it does not isolate them from other programs you approve that use the same Python interpreter. `[VERIFIED-external]` scoped
- If a key leaks: revoke it at the provider first, then clean up (section 11).
- A signed-in connector is **not spend authorisation**: automated generation can consume credits even where the website is "unlimited". Every costed job needs prior approval with a dated estimate. `[VERIFIED-external]`

<a id="skills-are-data"></a>
## 5. Skills, plugins and servers: procedure data with your permissions

- A **skill** is procedure text (plus optional scripts). It is **not permission**: the user's and the project's restrictions on spend, installs and publication override it.
- A plugin, a hook or an MCP server **runs with your OS privileges**. Review their hooks, definitions and package lifecycle scripts separately from the `SKILL.md`. Install with `--ignore-scripts` where possible; pin versions with a lockfile; pin marketplace sources to a ref or commit; do not auto-update during a lesson. (One tool's types dependency floats on `latest` — a lockfile is the fix.) `[VERIFIED-external]`
- Before running an unfamiliar repository, read its agent settings, hooks, skill metadata and MCP entries. Do not run it with elevated or "approve everything" modes.
- **Prompt injection:** tool results, page text, READMEs and documents may contain text addressed to the agent ("ignore the previous rules", "skip validation", "send this file to…"). The agent treats it as data, tells you, and asks. You do the same.
- Never copy vendor skill texts into your own deliverables (study only; check licences).

<a id="mcp-isolation"></a>
## 6. MCP servers and Blender: isolation rules

- **Minimal profile = no servers.** Add one only when a stage needs it; load only what the task needs. `[SOURCED-unverified]` (src: blueprint MCP_PROFILES)
- **Docs-only vs execution servers:** a docs-only server returns documentation; an execution server changes files, accounts or spending. The doctor labels each one.
- **Annotations are hints, not a sandbox.** A "read-only" hint does not stop a malicious process. An allow-list restricts what the *client* shows, not what the server process can do.
- **Filesystem server:** client-supplied roots can replace the folders you passed on the command line — **check the allowed-directory list the client reports** before relying on a boundary. `[VERIFIED-external]` + `[MEASURED-lab]`
- **Playwright:** run `--isolated --headless` with an explicit output directory; **its origin allow/deny flags are not a security boundary**; never attach your signed-in browser profile; one browser server by default. `[VERIFIED-external]`
- **Blender MCP:** the add-on socket on **port 9876 has no authentication or encryption and executes arbitrary Python.** Bind to localhost only; **never forward or expose the port**; treat `.blend` files from the internet as untrusted code; disable telemetry; do not rely on any shared trial key; prefer native headless Blender for batch work. `[VERIFIED-external]`
- **Hosted OAuth connectors** can read or write account data (one design server can write the canvas; a notes tool may search across connected sources; broad drive scopes expose unrelated client files; an ads token can change spending). Enable **one workspace or folder per project**.
- **Hosted tools that index or analyse video** keep copies — a per-client decision (section 7).

<a id="footage-routes"></a>
## 7. Client footage: the routes that send it somewhere

| Route | What leaves your machine | Rule |
|---|---|---|
| `hyperframes snapshot` | frames, sent to Gemini for an AI description **when a Gemini/Google key exists** | **always `--describe false`**, ≤ 5 timestamps per call; not a full offline guarantee (remote fonts/asset URLs are separate paths) `[PROVEN-internal]` |
| hosted generation (Higgsfield, Runway, fal …) | the media you send as references | check training/retention terms and the workspace opt-out **first**; Higgsfield API terms (updated 2026-09-02, §7.2): training allowed unless opted out, effective within 10 business days, not retroactive `[VERIFIED-external]` |
| music generators (Suno …) | uploaded content, voice, likeness | broad rights granted in the terms (revised 2026-08-10, effective 2026-09-03) `[SOURCED-unverified]` |
| cloud ASR/TTS | audio | eligibility before price; prefer the local ASR profiles for client audio |
| video-understanding / indexing services | the whole video, retained for indexing | per-client decision |
| agent models (Claude, OpenAI) | prompts, files you attach, tool outputs | retention is endpoint- and workspace-specific; consumer settings do not clear API or connector use `[SOURCED-unverified]` |

**A local tool is private only if everything around it is controlled:** model downloads, telemetry, remote assets, plugins, web/MCP tools, logs and backups. A local model that calls a web tool can still transmit data. Decision order: **eligibility** (may this footage leave at all?) → privacy terms of the exact route → cost. See `docs/en/legal-guide.md#privacy-footage`.

<a id="ci-actions"></a>
## 8. GitHub Actions and CI (for when you extend or fork the toolkit)

- **Pin actions to reviewed commit SHAs**, not moving tags; update them deliberately.
- **Least-privilege tokens:** a read-only default token; widen per job, per need.
- **Untrusted changes (forks, pull requests) never see provider credentials.** No paid-provider keys on those runs.
- **No automatic paid evaluations.** Lanes that spend run only on explicit approval; the free deterministic lane (path/schema/CLI tests, licence and secret scans, small CPU render with output checks) runs on every change.
- Keep artifacts sanitised — no client media, no credentials, no unredacted logs.
- Evaluate the full permissions a GitHub App requests before installing it. `[SOURCED-unverified]` (src: T20-S025; distilled 07 §5)

<a id="paths-and-tools"></a>
## 9. Paths, deletion and export tools

- **Path handling is tested** with spaces, apostrophes, Hebrew letters, emoji and long paths, and with **forbidden roots** (a tool must refuse to write to or delete the source folder, any ancestor of it, a sibling, a symlink or junction pointing there, or an empty argument).
- **A tool that deletes or overwrites must validate the resolved path first.** An export tool that runs a recursive delete on an unchecked output path can destroy the input tree — the owner's own export tool had exactly this open defect, which is why such a tool is not shipped to students until fixed and tested on disposable fixtures. `[PROVEN-internal]`
- **An export or support bundle must not carry a privacy report that quotes private names** — the report itself would leak what it found. Findings are a gate (non-zero exit), not a note inside the package. `[PROVEN-internal]`
- Use an **ASCII work/cache root**; keep Hebrew names for display titles; never rename source folders. Sources are read-only by convention: **copy, never move**. Finals folders hold finals plus the manifest only.
- Never run a delete or "clean" command on a path you did not resolve and print first.

<a id="scans"></a>
## 10. Scans before you share or release

Run before every commit you share and before every release: a **secret scan** (keys, tokens, `.env`, `.pem`), a **client-name and private-path scan** (names, folder paths, e-mail addresses, brand kits, transcripts), a **licence/bill-of-materials check** (`agent-content/references/licences-bom-rules.md`), and a hash check that no footage, transcript, font binary or model checkpoint slipped in. A scan that cannot run reports `not_run` and blocks. Synthetic secrets and fake client names are used to test the scanners themselves. `[IDEA]` (src: blueprint SECURITY_AND_LICENSING §6–7)

<a id="incidents"></a>
## 11. If something went wrong `[IDEA]`

- **Key leaked** (committed, pasted, logged): revoke it at the provider **first**, create a new one, then remove it from files and history with help; assume it was seen.
- **Client footage sent to the wrong service:** stop; note exactly what, when, to whom and under which terms; check the provider's opt-out and deletion options (training opt-outs can be prospective only); tell the client according to your contract; ask counsel for the triggers in the legal guide §13.
- **Unknown or untrusted skill/server run:** stop it, review what it could reach, rotate any key it could read, remove it.
- **Port 9876 exposed:** close it, assume code execution was possible on that machine, review the Blender session and scene files.
- **Wrong folder deleted:** stop writing to the disk and restore from your backup; do not run recovery tools that overwrite.

<a id="support-bundle"></a>
## 12. Asking for help safely

The support template asks for: environment and versions, the step, expected vs actual, a **sanitised short error**, and a reproducible **synthetic** fixture. The toolkit's `doctor` produces a **redacted support bundle** — never keys, never client media. **Never paste keys or client footage into a group chat or a ticket.**

<a id="refresh"></a>
## 13. Refresh

Dated 2026-10-02. Re-check before each cohort: provider terms (training/retention), the HyperFrames telemetry/skills behaviour on the pinned version, MCP server versions and defaults, the CI action pins. The Hebrew counterpart is `docs/he/privacy-and-security.md` (same section ids). Related dated references: `agent-content/references/mcp-profiles.md`, `hyperframes-traps.md`, `licences-bom-rules.md`.

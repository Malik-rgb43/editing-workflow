# Troubleshooting

> Written 2026-10-02. Symptom -> cause -> fix, in the order students hit them. Commands run from the toolkit clone. Evidence tags: **[measured]** on the reference machine, **[documented]** in an official page read 2026-10-02, **[unmeasured]** reasoned but not run. Hebrew: [docs/he/troubleshooting.md](../he/troubleshooting.md). Install: [install](install.md).

<!-- step: troubleshooting-01 -->
## troubleshooting-01 - "python is not recognized" / the Microsoft Store opens / Python is too old
Cause: on Windows `python` can be a Store stub (exit code 9009); macOS `python3` can be 3.9. The installer can *start* on 3.9+ but needs 3.11+ to read `integrations/catalog.toml`. Fix, in order: `py -3 --version`; `python3 --version`; if `uv` exists run `uv run --python 3.12 --no-project python install/bootstrap.py plan` (uv fetches its own Python; it does not touch the system one); otherwise install uv (`winget install --id astral-sh.uv -e --source winget` / `brew install uv`) or Python 3.12 from python.org. Open a new terminal afterwards. [documented: uv docs]

<!-- step: troubleshooting-02 -->
## troubleshooting-02 - PowerShell, CMD and Git Bash behave differently
* PowerShell 5.1 has no `&&`: send one command per line. Use double quotes around every path (works in PowerShell, CMD and bash). In bash on Windows, paths like `/c` can be rewritten to `C:/`; keep paths ASCII and use `MSYS_NO_PATHCONV=1` if a flag value is mangled. [measured by the author]
* "running scripts is disabled on this system" when `npx` runs: PowerShell blocks the `npx.ps1` shim. Either call `npx.cmd`, or let **you** relax it for your own account (`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`). This is a system security setting: the agent never changes it for you.
* Use `python install/bootstrap.py run -- ...` for toolkit commands: it sets `PYTHONPATH`, UTF-8 and the work root identically in every shell.

<!-- step: troubleshooting-03 -->
## troubleshooting-03 - Hebrew letters in paths
* `npx hyperframes init` **silently skips `index.html`** under a path with Hebrew letters (`lint`, `check`, `render` still work). Always create projects under the ASCII work root; never rename your source folders. [measured: author's report on HyperFrames 0.8.79; not re-measured on the pinned build]
* A Hebrew Windows user name (`C:\Users\<Hebrew name>\`) is fine for Python and FFmpeg but not for engine projects: the installer warns and defaults the work root to `C:\avc-work`; you can pass `--work-root "C:\avc-work"` (ASCII only; a non-ASCII value is refused) and `--home "C:\avc\toolkit"` for the toolkit folder.
* Hebrew text in a *file name* of your own footage is fine for FFmpeg; copy it to the work root before the engine uses it.
* Console shows `????`: `chcp 65001` in CMD, or use Windows Terminal. The installer writes UTF-8 (no BOM) everywhere; the display is the problem, not the files.

<!-- step: troubleshooting-04 -->
## troubleshooting-04 - FFmpeg missing, "found but the mini-encode failed", PATH not refreshed
* Missing: use the exact command in `plan` (Windows `winget install --id Gyan.FFmpeg -e --source winget`, macOS `brew install ffmpeg`, Linux your package manager) - [documented 2026-10-02; ffmpeg.org itself ships source only]. Then open a **new terminal** (PATH is read at start).
* Found but `ffmpeg mini-encode: fail`: the build lacks `libx264` or `aac` (some minimal builds). Run `ffmpeg -hide_banner -encoders` and look for `libx264` and `aac`; install a full build. Every other check is meaningless until this passes.
* Several FFmpegs: `where ffmpeg` (Windows) / `which -a ffmpeg` shows which one wins; set `[binaries] ffmpeg` in `toolkit.local.toml` to pin one.

<!-- step: troubleshooting-05 -->
## troubleshooting-05 - NVENC / QSV are listed but do not work
A hardware encoder in the `ffmpeg -encoders` list only means it was compiled in. On the the reference machine's AMD machine NVENC and QSV were **listed but failed to initialise**; AMF H.264/HEVC worked [measured]. The toolkit chooses encoders by a **real mini-encode**, never by the list, and falls back to CPU `libx264`. NVIDIA and Apple hardware encoders are **unmeasured**. Do not "fix" it by installing drivers for the agent's sake: report `doctor` output.

<!-- step: troubleshooting-07 -->
## troubleshooting-07 - Skills are not discovered
1. Restart the agent session after install (skills are read at start).
2. Right place? Claude Code: `~/.claude/skills/<name>/SKILL.md` (user) or `<project>/.claude/skills/` (project). Codex: `~/.agents/skills/` or `<repo>/.agents/skills/`; `~/.codex/skills` is not used [documented]. Run `python install/bootstrap.py verify`: it lists missing or modified skill files.
3. You installed with `--scope project`? Then only sessions started inside that project folder see them.
4. Folder name must equal the `name:` in `SKILL.md` front matter (the installer's plan lints this). A same-named skill of yours wins - see `plan` "conflicts"; use `--force` only after reading what gets backed up.
5. Ask the agent "which skills do you have about video editing?"; `video-request-router` should be listed. Still nothing: send `verify --json`.

<!-- step: troubleshooting-08 -->
## troubleshooting-08 - A connector (MCP server) does not connect
* See what the client thinks: `claude mcp list`, `claude mcp get <name>`, or `/mcp` inside a session. Codex: `codex mcp list`.
* Native Windows: `npx`/`uvx` servers need the `cmd /c` wrapper - the installer adds it for Claude Code [documented]; for Codex on Windows this is [unmeasured].
* Node too old: the engine and most npx servers need Node 22+ (LTS is v24 on 2026-10-02). Check `node --version` in the same terminal the agent uses.
* Project-scope servers (a `.mcp.json` in the folder) ask for your approval at first use; user-scope ones are in your user config.
* Playwright says the browser is missing: approve its browser install, or use an installed browser (`--browser msedge`); keep it `--isolated`. Slow first start: raise the client's startup timeout (Codex `startup_timeout_sec`, default 10 s; the template uses 30 s) [documented].
* "already exists": the installer skips a server with the same name or alias (for example your own `playwright`). Two browser servers double the tool schema; keep one.
* Still failing: remove and re-add by hand with the exact command shown in `plan` (`argv`), then restart the agent. A server that never connects does not affect the core install.

<!-- step: troubleshooting-09 -->
## troubleshooting-09 - OAuth sign-in failed
Applies to Higgsfield, ElevenLabs. In your agent run `/mcp`, pick the server, authenticate; or in a terminal `claude mcp login <name>` / `codex mcp login <name>` [documented]. Wrong account or workspace? Sign out in the browser first. Pop-up blocked or a company SSO policy? Allow the pop-up or ask your admin. Never paste codes or tokens into the chat. A successful sign-in spends nothing and is not spend approval. If the vendor's hosted MCP URL in the catalogue is flagged `unverified` (Higgsfield, Unsplash), use the vendor's own documented route instead (Higgsfield: its CLI).

<!-- step: troubleshooting-10 -->
## troubleshooting-10 - Port conflicts
Blender's connector listens on `localhost:9876` and has **no authentication**: if the port is taken, find the author (Windows `netstat -ano | findstr 9876`, macOS/Linux `lsof -i :9876`) and close that program; never forward the port and never expose it to a network. The engine's preview server prints the address it uses; if a port is busy, stop the old preview before starting another (one heavy job at a time).

<!-- step: troubleshooting-11 -->
## troubleshooting-11 - `npm ci` or the engine fails
* Offline or behind a proxy: run `apply --offline`, fix the network, run `apply` again (finished stages are skipped).
* `--ignore-scripts` means the browser is **not** downloaded by `npm ci`; the browser step is separate and explicit (`hyperframes browser ensure`, size unmeasured on student machines).
* Engine version differs from the research pin (0.8.98)? Do not upgrade to "fix" a problem; the pin moves only after a re-test.
* Never run `npm install -g` for the engine; it is project-pinned.

<!-- step: troubleshooting-12 -->
## troubleshooting-12 - `claude doctor` is green but video does not work
`claude doctor` diagnoses the Claude Code installation and settings only [documented]. Video, font and GPU readiness come from `python install/bootstrap.py verify` (real FFmpeg mini-encode, file hashes, link check) and the toolkit's `doctor`. Report all five states; a state that did not run is `not_run`.

<!-- step: troubleshooting-13 -->
## troubleshooting-13 - `uv sync` fails
The toolkit needs Python 3.12 or 3.13 (`requires-python`); `uv` downloads its own copy if needed (network + a few hundred MB are possible; unmeasured). Errors about a lockfile: re-run without edits (the installer uses `--locked` only when `uv.lock` exists). Antivirus or a sync client (OneDrive, Dropbox) locking the toolkit folder can break the environment: keep the toolkit home and the work root outside synced folders [unmeasured advice]. The core still works without the Python environment for plain FFmpeg tasks; the `run -- python ...` launcher will tell you what is missing.

<!-- step: troubleshooting-14 -->
## troubleshooting-14 - Partial install, "another install is running", conflicts
* Exit code 4 (partial): read the one failing line, fix it, run the same command again.
* "another install is running": a lock file exists at `~/.avc/install.lock`. Wait; if you are sure nothing runs (a crash), `--break-lock`.
* `conflict-foreign` in the plan: you already have a skill with that name. It is skipped and left untouched. Rename yours, or `--force` (your folder is copied to the backups first).
* Something half-copied after a power cut: files are replaced atomically, so re-running converges; `verify` shows anything missing.

<!-- step: troubleshooting-15 -->
## troubleshooting-15 - What to send when asking for help
OS and version, shell, `python install/bootstrap.py verify --json`, the step id, the sanitised last error line, what you expected. Never keys, tokens, client footage or transcripts. The installer prints only whether a credential variable exists, never its value.

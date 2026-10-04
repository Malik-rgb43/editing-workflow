# Install - what happens, what is downloaded, what you answer

> Written 2026-10-03. The installer (`install/bootstrap.py`) is covered by mocked unit tests and runs in CI on Windows, macOS and Ubuntu; a clean-clone install was run once on a one reference machine. A clean macOS and Linux install have **not** been run yet. The agent-side runbook is [INSTALL.md](../../INSTALL.md); this page is the same flow for you. Hebrew: [docs/he/install.md](../he/install.md).

**Two repositories, two links.** First `claude-code-setup` (it prepares Claude Code: saves credits, adds a browser tool and a skills plugin). Then **this** repository, the editing toolkit. You paste the link into Claude Code or Codex and say "install this". The agent looks at your computer **by itself** - you are never asked about your GPU, RAM or operating system.

## What you will be asked
| When | The question | Your default |
|---|---|---|
| Right after the scan | "How do you want to work: **local**, **connected** or **both**?" (a choice of working style, never a question about your hardware) | no default: you choose |
| Once, before anything is installed | "Shall I go ahead with this plan? (yes/no)" after the agent has told you what is downloaded for your choice | you decide |
| Before the browser download | "HyperFrames needs its own small headless Chrome. Download it? (yes/no)" | you decide |
| After the install works | **local:** the free local extras, one at a time. **Connected:** a list of services to pick from (voice and AI generation, stock media, UI components, 3D) | nothing is connected unless you pick it (silence = no) |
Nothing is installed or connected silently, and nothing costs money unless you sign up to a paid service yourself.

## What is downloaded
| What | From where | Why |
|---|---|---|
| the video skills, as the Claude Code plugin `editing-workflow` | Claude Code fetches it from this repository's public GitHub page (`claude plugin marketplace add`, `claude plugin install`); `--skills-via copy` copies plain folders instead | the editing know-how |
| the playbooks and tools (the toolkit folder) | copied from the folder you downloaded, no network | what the skills read and run |
| Python packages (numpy, Pillow, OpenCV ...) | pypi.org, via `uv sync` | the quality-check tools |
| **HyperFrames 0.8.98** (the render engine) | the official npm package of HeyGen, via `npm ci --ignore-scripts`; nothing of it is stored in this repository | renders your video from HTML/CSS/GSAP |
| HyperFrames' headless Chrome | Chrome-for-Testing hosts, only after your yes | rendering |
| **only if you chose local:** speech-to-text environment (`asr-cpu`) | pypi.org; the model **weights are not downloaded** until you approve their size | Hebrew transcription on your computer |
| missing tools (FFmpeg, Node, uv ...) | winget / brew, only if you let the agent run the command | prerequisites |
Sizes are "not measured" where nobody measured them; the agent says so.

| You | The agent |
|---|---|
| paste the link, say yes once, answer the optional yes/no questions | clones the repo, detects your computer, checks prerequisites, copies skills, installs HyperFrames, verifies |
| sign in to providers and store API keys **yourself**, only for what you added | never sees, asks for or stores a key or password |
| decide about installing missing tools | shows the exact command for your OS; never installs a package manager |

<!-- step: install-01 -->
## install-01 - Open your agent and paste the link
Open Claude Code or Codex in any folder, paste the repository link and write "Install this" (or the Hebrew "תתקין את זה"). If you write Hebrew, the whole conversation is in Hebrew. You do not need admin rights; one optional Windows prompt (UAC) may appear if you approve installing Node or Git. If Claude Code was not set up with `claude-code-setup`, the agent mentions it once; you can continue without it.

<!-- step: install-02 -->
## install-02 - The agent gets the toolkit
It clones the repository into an **ASCII-only** folder (no Hebrew letters in the path), for example `C:\Users\<name>\editing-workflow` or `~/editing-workflow`. No Git? It offers to install Git or to download the ZIP of the same link - it tells you the file and size first and waits for your yes. It also finds a working Python launcher (`py -3`, `python`, `python3`, or `uv run --python 3.12`); the Windows Microsoft Store "python" stub is ignored.

<!-- step: install-03 -->
## install-03 - The agent detects your computer (read-only)
`python install/bootstrap.py plan` detects: operating system, CPU architecture (x64 or arm64), CPU threads, RAM, free disk, GPU vendor (NVIDIA, AMD, Intel, Apple Silicon, or none/virtual) and shell; which prerequisites exist (Git, FFmpeg - including a **real** tiny H.264+AAC encode, Node 22+ LTS, npm, uv, the agent CLIs); which skills would be copied and whether a skill of yours has the same name; what would be downloaded; the cost (none) and any blocker. It changes nothing.

<!-- step: install-04 -->
## install-04 - The detected choices (you are not asked)
The installer picks the safest setup that works on every computer:
* **Baseline**: skills + FFmpeg + the toolkit's tools + the HyperFrames engine, with **no connectors**. No account, key, GPU or payment.
* **Speech-to-text**: a local CPU route (`asr-cpu`, faster-whisper int8) is available and is installed **only if you choose local** in the next step. Model weights are never downloaded until you approve their size.
* **Speaker cut-out**: the engine's own CPU route - nothing extra to install.
* **Video encoder**: CPU `libx264`, proven by the real mini-encode.
* Connectors, providers, Blender: not installed by the install; they are your choice in install-05 and install-10.

<!-- step: install-05 -->
## install-05 - How do you want to work: local, connected or both?
The one "how" question, with **no default**. It is a choice of working style, not a question about your hardware.
* **Local** - everything that can run on your computer, free: Hebrew transcription with a local model, local cut-outs, free reference-video tools. The agent downloads what that needs (model weights only after you approve their size).
* **Connected** - online services do the heavy AI work (voice, generation, stock media ...) and **you pick from a list** which ones to connect now.
* **Both** - the local tools plus the services you pick.
Whatever you choose, the base install is the same (skills, tools, HyperFrames, quality-check packages). You can change your mind at any time, and you can connect more later by simply writing "connect <service>".

<!-- step: install-06 -->
## install-06 - You confirm once
The agent tells you, in at most 15 lines: what it detected; **what is downloaded for the way of working you chose** (the table above); what changes on your computer (the plugin, the toolkit folder `~/.avc/toolkit`, an ASCII work folder, a short removable note in your agent's instruction file); the cost (none); which questions you will be asked; how to undo. Then **one question**: "Shall I go ahead with this plan? (yes/no)".

<!-- step: install-07 -->
## install-07 - The installation runs (HyperFrames is installed here)
`bootstrap.py apply --yes`: toolkit folder, skills (Claude Code: the `editing-workflow` plugin; Codex: copied folders - a **backup** is taken before anything is replaced and a skill of yours with the same name is skipped unless you allow `--force`), the marked note, ASCII work folder + `toolkit.local.toml`, `uv sync --no-dev`, **the HyperFrames engine** (`npm ci --ignore-scripts` from `package.json` + `package-lock.json`, version 0.8.98), the CPU speech-to-text environment (only if you chose local; weights are never downloaded), and a link check. Safe to run again: finished work is skipped. A failed stage never needs manual cleanup.

<!-- step: install-08 -->
## install-08 - Missing tools
If the plan lists a missing tool, it shows the exact command for your OS and where it came from. Examples (checked 2026-10-02): Windows `winget install --id Gyan.FFmpeg -e --source winget`, macOS `brew install ffmpeg`; Node LTS `winget install --id OpenJS.NodeJS.LTS -e --source winget` / `brew install node@24`. You choose whether the agent runs them. Afterwards open a **new terminal** so the PATH is refreshed, then the agent re-runs the install.

<!-- step: install-09 -->
## install-09 - HyperFrames: browser and check
HyperFrames renders in a headless Chrome. The agent asks before downloading it, then runs `hyperframes browser ensure` and `hyperframes doctor --json`. "Docker" showing "not found" is fine; it is optional. HyperFrames is developed by HeyGen: https://github.com/heygen-com/hyperframes. Your projects live under an English-only work folder, because `hyperframes init` skips files under paths with Hebrew letters.

<!-- step: install-10 -->
## install-10 - What to connect
After the install works the agent asks, **one choice at a time**. Nothing is pre-selected; "none" and "not now" are fine.
* **If you chose local:** the free local extras - reference videos from links (YouTube, TikTok, Instagram), a faster cut-out of people (`matte-fast`), faster transcription on your graphics card (only if your computer showed a working faster route), Blender for 3D (Three.js needs nothing to install).
* **If you chose connected (or both):** a list to pick from, any number or none.
  | Group | Services | Cost |
  |---|---|---|
  | Voice and AI generation | ElevenLabs, Higgsfield | **paid** |
  | Stock media | Pexels, Iconify | free tier |
  | UI components | shadcn; 21st.dev | free; paid |
  | 3D | Blender connector (the default 3D builder); optional AI model generation with Tripo, used only if you connect it | Blender free; generation paid |
  For each service you pick, the agent explains what it is and what it costs, then shows you the **sign-up link**. Some sign-up links are referral links: they are labelled "referral link", the plain link is shown beside them, and you may choose either or skip. The agent opens nothing without your yes.
* **Connect more later - just write it.** In any later conversation say "connect ElevenLabs" (or any service); the agent runs `add` and shows you the sign-up link the same way.

<!-- step: install-11 -->
## install-11 - Things only you do (when you add something)
* **Sign in to connectors** (Higgsfield, ElevenLabs): in your agent type `/mcp`, choose the server, finish the browser sign-in.
* **API keys** (Pexels, 21st.dev): create the key on the vendor's site and save it as a *user environment variable* with the exact name from the catalogue. Windows: Start -> "Edit environment variables for your account" -> New. macOS: add `export NAME=...` to `~/.zshrc` with a text editor. Never paste a key in chat or use the agent's `!` shell prefix for it. Restart the agent afterwards.
* **Native plugins** (the Blender add-on): you download and install them from the vendor.
Signing in spends nothing. Spending always goes through the spend gate.

<!-- step: install-12 -->
## install-12 - Verify and restart your agent
`python install/bootstrap.py verify` re-checks every installed file against the manifest, runs the link check, repeats the FFmpeg mini-encode and prints the five states. `claude doctor` only diagnoses the Claude Code installation - it is not proof that video works. Then **restart your agent session** and ask "which skills do you have about video?" - `video-request-router` must be listed.

<!-- step: install-13 -->
## install-13 - First render
Follow first-output (`docs/en/first-output.md`; after install: `~/.avc/toolkit/docs/en/first-output.md`). It uses owned, synthetic, bilingual sample sources - no client footage, no cost.

<!-- step: install-14 -->
## install-14 - The report, the five states, and adding connections later
The agent ends with a short report: **what was installed and downloaded**, **what only you must do**, **how to undo or update**. The five states are reported with evidence, never merged: (1) installed - (2) authorised account - (3) first render - (4) inspection passed - (5) ready for paid generation. `not_run` is not a pass.
Connections can also be added later, one at a time:
```text
python install/bootstrap.py add --list
python install/bootstrap.py add <id>
python install/bootstrap.py add <id> --yes
```
`add <id>` first shows a read-only plan (what it is, cost, where credentials go, sign-up links, steps only you can do); with `--yes` it does only the safe, non-spending part. It never reads or stores a key, never signs in, never downloads model weights and never spends.

<!-- step: install-15 -->
## install-15 - If something fails
Re-run the same command; it continues where it stopped. Exit code 4 = partial: read the failing line. See [troubleshooting](troubleshooting.md). To undo: [uninstall](uninstall.md) or `rollback` ([update-rollback](update-rollback.md)). Never send a key to get help - send the sanitised error line and `python install/bootstrap.py verify --json`.

## Manual use without an agent
```text
git clone <repository link> "<ASCII folder>"
cd "<ASCII folder>"
python install/bootstrap.py plan
python install/bootstrap.py apply --yes
python install/bootstrap.py verify
```
Windows PowerShell 5.1 does not support `&&`: run one command per line. Quote paths with double quotes in PowerShell, CMD and bash alike.

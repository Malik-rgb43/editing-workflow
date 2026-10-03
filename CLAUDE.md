@AGENTS.md

Claude Code only: skills load from `~/.claude/skills` (user) or `.claude/skills` (project); MCP servers are added with `claude mcp add` (`.mcp.json.example` is the reviewable Standard template; project-scope servers ask for your approval at first use). `claude doctor` checks the Claude Code installation only - for video readiness run `python tools/doctor.py smoke` (the installer's `python install/bootstrap.py verify` checks the install; the `claude-code-setup` repository only prepares Claude Code).

# Runtime control: prose is not enough (sample Claude Code hook config)

Load when setting up the project's spend controls or when the gate's G5 is not yet `pass`. Rule: a prose "iron rule" can improve behaviour but cannot enforce a ceiling. Hard limits live in a hook, a permission rule or a wrapper. Status: sample configuration written from documented hook behaviour (distilled 07, T02, 2026-10-01); the hook script is tested with `--self-check` only, not yet exercised inside a live Claude Code session. Verify matcher and JSON fields against your Claude Code version before relying on it.

## 1. Three layers (use all that your client supports)
| Layer | What it does | Weakness |
|---|---|---|
| `permissions.ask` on exact paid tool names | Claude Code asks the human before every paid call: a runtime approval no prompt can skip | you must list the real tool names from your own tool list |
| `PreToolUse` hook `scripts/approval_hook.py` | denies a paid call without a valid, unexpired approval and counts attempts against `calls_allowed` (retry cap included) | sees the tool name and a counter, not prices; cannot tell which estimate line a call belongs to; a program the matcher never sees is not covered |
| spend wrapper (a thin script that calls the provider only after `estimate.py can-run` exits 0) | validates the exact operation against the approval | needs writing per provider; later in the project tools |
A Stop hook is too late to prevent a paid submission. A shell deny-pattern cannot inspect every equivalent program.

## 2. Sample `.claude/settings.json` (project scope)
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__.*(generate|upscale|outpaint|reframe|dubbing|voice_change|execute_preset|buy_|create_voice|motion_control)",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/agent-content/skills/paid-spend-gate/scripts/approval_hook.py\"",
            "timeout": 10
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/agent-content/skills/paid-spend-gate/scripts/approval_hook.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  },
  "permissions": {
    "ask": [
      "mcp__<your-provider-server>__<exact_paid_tool_name>"
    ]
  }
}
```
Notes:
- Replace the `ask` entry with the exact names in YOUR tool list (the tool names depend on which connectors the student installed). List one per paid tool.
- The `Bash` matcher only acts when `AVC_PAID_HOSTS` is set (comma list of provider hostnames, e.g. in the shell profile or `env` block of settings); otherwise the hook ignores Bash calls.
- On Windows use `python` (or `py -3`) as installed; keep the quotes around the script path.
- The hook reads `.avc/approval.json` in the project (override with `AVC_APPROVAL_FILE`). It prints a JSON `permissionDecision: "deny"` with a reason that tells the agent what to do next; a non-paid tool exits silently.
- The hook fails closed: any error on a paid call, or unreadable hook input, denies.

## 3. Strong mode (the agent cannot forge approval)
Run `estimate.py approve ...` yourself in a terminal with `AVC_APPROVAL_SECRET` set (a secret the agent session does not have); the token becomes an HMAC, and the hook in the agent session needs the same variable in its environment to verify. Without a secret, the token only detects accidental edits and the user's chat message remains the authority.

## 4. Codex and other clients
No equivalent hook is verified here. Use the wrapper layer: every provider call goes through a script that runs `can-run` first, and tell the agent not to call providers directly. Record the limitation in the project's `docs/decisions/` note.

## 5. Test it (free)
1. `python scripts/approval_hook.py --self-check` prints `self-check: ok`.
2. Without an approval file, ask the agent to call a paid tool: the call must be denied and no provider receives anything.
3. After a real approval, the allowed attempts equal `calls_allowed` in `approval.json`; the (n+1)th call is denied.
Use a zero-cost path (a deny test) so no credit is spent while testing.

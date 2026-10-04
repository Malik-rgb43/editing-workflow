#!/usr/bin/env python3
"""Claude Code PreToolUse hook: deny a paid tool call unless a valid, unexpired approval exists.

Usage (as a hook; reads the hook JSON from stdin, see references/hook-config.md):
  python approval_hook.py                 # hook mode
  python approval_hook.py --self-check    # built-in tests

Environment (all optional):
  AVC_APPROVAL_FILE    path to approval.json (default: <cwd>/.avc/approval.json)
  AVC_PAID_TOOL_REGEX  regex over the tool name that marks a call as paid
                       (default: generate|upscale|outpaint|reframe|dubbing|voice_change|execute_preset|
                        buy_|create_voice|motion_control|render_cloud)
  AVC_PAID_HOSTS       comma list of provider hostnames; a Bash command containing one counts as paid
  AVC_APPROVAL_SECRET  HMAC secret, if the approval was issued with one

Behaviour: a call that is not paid is ignored (exit 0, no output). A paid call is DENIED unless the
approval file exists, its token verifies, it has not expired and the number of allowed attempts
(calls_allowed, which already includes the retry cap) is not used up. Each allowed call appends an
`attempt_allowed` line to spend_ledger.jsonl next to the approval file, so retries and failures
count even when the provider bills nothing. Any internal error on a paid call DENIES (fail closed).
Limits: this checks tool name, approval and a counter; it cannot see prices, cannot tell which
estimate line a call belongs to, and does not stop a program the matcher never sees. Pair it with
`permissions.ask` rules and with a spend-validating wrapper (see references/hook-config.md).
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate as est  # noqa: E402

DEFAULT_PAID = (r"generate|upscale|outpaint|reframe|dubbing|voice_change|execute_preset|buy_|create_voice|"
                r"motion_control|render_cloud")


def is_paid(payload: dict, env: dict) -> bool:
    name = str(payload.get("tool_name", ""))
    if re.search(env.get("AVC_PAID_TOOL_REGEX") or DEFAULT_PAID, name, re.I):
        return True
    if name == "Bash" and env.get("AVC_PAID_HOSTS"):
        cmd = str((payload.get("tool_input") or {}).get("command", "")).lower()
        return any(h.strip().lower() in cmd for h in env["AVC_PAID_HOSTS"].split(",") if h.strip())
    return False


def decide(payload: dict, env: dict, now: datetime | None = None) -> tuple[str, str]:
    """Return ("allow"|"deny", reason)."""
    if not is_paid(payload, env):
        return "allow", "not a paid tool"
    try:
        cwd = Path(payload.get("cwd") or ".")
        path = Path(env.get("AVC_APPROVAL_FILE") or cwd / ".avc" / "approval.json")
        if not path.is_file():
            return "deny", (f"No approval file at {path}. Show the user a dated estimate, get their explicit approval, "
                            "then run estimate.py approve. Nothing was submitted.")
        ap = json.loads(path.read_text(encoding="utf-8"))
        est.verify_approval(ap, env.get("AVC_APPROVAL_SECRET") or None, now)
        ledger = est.ledger_path(path)
        used = sum(1 for e in est.read_events(ledger) if e.get("event") == "attempt_allowed")
        if used >= int(ap["calls_allowed"]):
            return "deny", f"Approved attempts used up ({used}/{ap['calls_allowed']}, retry cap included). Stop and ask the user."
        est.append_event(ledger, {"event": "attempt_allowed", "at": (now or est.now_utc()).isoformat(),
                                  "tool": payload.get("tool_name")})
        return "allow", f"attempt {used + 1}/{ap['calls_allowed']} under approval {ap.get('approval_token', '')[:14]}"
    except est.Refuse as r:
        return "deny", f"Approval check failed ({r.code}): {r.msg}"
    except Exception as exc:  # noqa: BLE001  fail closed on a paid call
        return "deny", f"Approval check error, failing closed: {type(exc).__name__}: {exc}"


def _self_check() -> int:
    fails = []
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / ".avc").mkdir()
        env = {"AVC_APPROVAL_FILE": str(tdp / ".avc" / "approval.json")}
        paid = {"tool_name": "mcp__provider__generate_video", "cwd": str(tdp)}
        free = {"tool_name": "Read", "cwd": str(tdp)}
        if decide(free, env)[0] != "allow":
            fails.append("free tool must be allowed")
        if decide(paid, env)[0] != "deny":
            fails.append("no approval file must deny")
        src = {"name": "example", "checked_at": "2026-10-01", "tax_status": "excl_vat"}
        spec = {"project": "t", "retry_cap": 1, "price_sources": {"p": src},
                "lines": [{"id": "S1", "provider": "x", "model": "m", "wallet": "w", "currency": "USD", "price_source": "p",
                           "count": 1, "calc": "per_unit", "quantity": 1, "unit": "call", "unit_price": 1}]}
        (tdp / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        est.do_estimate(tdp / "spec.json", tdp / "est.json", 7, datetime(2026, 10, 2).date())
        ns = est.argparse.Namespace(approved=True, approval_quote="approved", approved_amount=["w=2"], ttl_hours=24,
                                    out=str(tdp / ".avc" / "approval.json"))
        est.do_approve(tdp / "est.json", ns, datetime(2026, 10, 2).date(), None)
        for i in range(2):  # count 1 + retry 1 = 2 allowed
            if decide(paid, env)[0] != "allow":
                fails.append(f"attempt {i + 1} should be allowed")
        verdict, reason = decide(paid, env)
        if verdict != "deny" or "used up" not in reason:
            fails.append("third attempt must be denied by the cap")
        if decide({"tool_name": "Bash", "tool_input": {"command": "curl https://api.provider.example/v1/gen"}, "cwd": str(tdp)},
                  {**env, "AVC_PAID_HOSTS": "api.provider.example"})[0] != "deny":
            fails.append("bash call to a paid host must be denied once the cap is used")
        ap = json.loads((tdp / ".avc" / "approval.json").read_text(encoding="utf-8"))
        ap["calls_allowed"] = 99
        (tdp / ".avc" / "approval.json").write_text(json.dumps(ap), encoding="utf-8")
        if decide(paid, env)[0] != "deny":
            fails.append("tampered approval must deny")
        (tdp / ".avc" / "approval.json").write_text("{not json", encoding="utf-8")
        if decide(paid, env)[0] != "deny":
            fails.append("corrupt approval must fail closed")
    for f in fails:
        print("FAIL:", f)
    print("self-check:", "FAILED" if fails else "ok")
    return 1 if fails else 0


def main() -> int:
    if "--self-check" in sys.argv:
        return _self_check()
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        payload = None
    if not isinstance(payload, dict) or not payload.get("tool_name"):
        # The settings matcher only starts this hook for tools it considers paid: unreadable input fails closed.
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": "approval hook could not read the tool call; failing closed"}}))
        return 0
    verdict, reason = decide(payload, dict(os.environ))
    if verdict == "deny":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

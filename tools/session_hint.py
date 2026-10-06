"""session_hint - the SessionStart hook of the editing-workflow plugin: find the HyperFrames projects this session may work on and
remind the agent to open the Studio FIRST, so the user watches the work from the start (owner rule, AGENTS.md rule 10).

It only looks: it never starts a server, never calls the engine, never writes a file. It reads the folder the session started in
(a project, its ``hf/``, or a work root with ``projects/``) and the configured work root (``AVC_PATHS_WORK_ROOT`` or ``[paths] work_root``
in toolkit.toml), and prints the hook's JSON with ``additionalContext``. No project found -> it prints nothing (exit 0).

Usage:
    python tools/session_hint.py [--cwd DIR] [--toolkit DIR] [--text]      (the hook runs it with no arguments)
Exit: always 0 (a hook must never block a session).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

MAX_LISTED = 5
TOOLKIT = Path(__file__).resolve().parents[1]


def configured_work_root(toolkit: Path) -> Path | None:
    raw = os.environ.get("AVC_PATHS_WORK_ROOT", "").strip()
    if not raw:
        try:
            text = (toolkit / "toolkit.toml").read_text(encoding="utf-8")
        except OSError:
            text = ""
        sect = re.search(r"(?ms)^\[paths\]\s*$(.*?)(?=^\[|\Z)", text)
        m = re.search(r'(?m)^\s*work_root\s*=\s*"([^"]*)"', sect.group(1)) if sect else None
        raw = m.group(1).strip() if m else ""
    return Path(raw).expanduser() if raw else None


def find_projects(cwd: Path, work_root: Path | None) -> list[Path]:
    """Project folders (the parent of an ``hf/index.html``), most recently changed first, no duplicates."""
    cands: list[Path] = []
    if (cwd / "index.html").is_file() and cwd.name == "hf":
        cands.append(cwd.parent)
    if (cwd / "hf" / "index.html").is_file():
        cands.append(cwd)
    for root in (cwd, work_root):
        if root is None:
            continue
        try:
            cands += [p for p in (root / "projects").iterdir() if (p / "hf" / "index.html").is_file()]
        except OSError:
            pass
    seen, out = set(), []
    for p in cands:
        key = os.path.normcase(str(p.resolve()))
        if key not in seen:
            seen.add(key)
            out.append(p)

    def mtime(p: Path) -> float:
        try:
            return max((f.stat().st_mtime for f in (p / "hf").iterdir()), default=0.0)
        except OSError:
            return 0.0

    return sorted(out, key=mtime, reverse=True)


def hint(projects: list[Path], toolkit: Path) -> str:
    tool = toolkit / "tools" / "hf_studio.py"
    lines = [f"HyperFrames projects found ({len(projects)}; most recent first):"]
    lines += [f"- {p}" for p in projects[:MAX_LISTED]]
    if len(projects) > MAX_LISTED:
        lines.append(f"- ... and {len(projects) - MAX_LISTED} more")
    lines.append(
        "Owner rule (AGENTS.md rule 10): as soon as this session works on one of these projects (or creates one), the FIRST action is "
        f'`python "{tool}" <project>/hf`. Then open the printed studio_url in a NEW browser-pane tab and tell the user, in one line, '
        "that the Studio is open so they can watch the video and its timeline while you work. If it exits 3, run it with --attach as a "
        "background command. Do not open it for a session that does not touch a project.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--toolkit", default=str(TOOLKIT))
    ap.add_argument("--text", action="store_true", help="plain text instead of the hook JSON")
    a = ap.parse_args(argv)
    try:
        cwd = Path(a.cwd or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        toolkit = Path(a.toolkit)
        projects = find_projects(cwd, configured_work_root(toolkit))
        if not projects:
            return 0
        text = hint(projects, toolkit)
        if a.text:
            print(text)
        else:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}, ensure_ascii=False))
    except Exception as exc:  # a hook never blocks the session
        print(f"session_hint: skipped ({exc})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except AttributeError:
        pass
    sys.exit(main(sys.argv[1:]))

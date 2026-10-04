"""connections - what is connected on THIS machine, grouped by the job it does, so the agent decides what to use before it plans.

Owner rule (2026-10-05): every skill starts by checking which connections exist and whether this job should use them, and only then
continues. This tool answers the first half in about a second; the decision is the agent's (pro-video-editor "Connections").

It reads the integration catalogue (integrations/catalog.toml) and checks, without calling any service or starting any server:
  * CLIs:        on PATH (Blender also in its default install folder);
  * API keys:    the environment variable is SET (presence only: a value is never read into the report or printed);
  * MCP servers: registered in the Claude Code / Codex config files (~/.claude.json user + this project, .mcp.json, ~/.codex/config.toml)
                 by NAME only; server settings and env values are never read into the report;
  * python libs: importable (find_spec; nothing is imported or downloaded).
claude.ai connectors and plugin servers do not live in those files (and a connector may be named by an id, not the vendor): the agent's
own tool list is the truth for them - it looks for tools that do the job (generate_video, search_icons, photos_search, ...). A configured server is not a working one: the first real call is the proof.

Usage:
    python tools/connections.py [--json] [-o <project>/_work/connections.json] [--cwd DIR]
Exit: 0 always (a report, not a gate).
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "integrations" / "catalog.toml"

# the job each catalogue entry does in an edit; the agent reads the report by job, not by vendor
JOBS = {
    "render and core": ["ffmpeg", "ffprobe", "node", "npm", "uv", "hyperframes", "git"],
    "reference capture and preview QA": ["playwright", "yt-dlp", "gemini-vision"],
    "real assets: stock, icons, logos, UI": ["pexels", "iconify", "shadcn", "magic-21st"],
    "3D": ["blender", "blender-mcp", "tripo"],
    "generated stills, video, voice, music (paid, paid-spend-gate)": ["higgsfield", "higgsfield-cli", "elevenlabs"],
    "speech and cutout (local)": ["faster-whisper", "ivrit-ct2", "matte-fast"],
    "publishing code": ["gh"],
}
BLENDER_DIRS = ["C:/Program Files/Blender Foundation/Blender*/blender.exe", "/Applications/Blender.app/Contents/MacOS/Blender"]


def load_catalog(path: Path = CATALOG) -> list:
    if tomllib is None:
        return []
    with open(path, "rb") as f:
        return [e for e in tomllib.load(f).get("entry", []) if "avoid" not in (e.get("profiles") or [])]


def _json_file(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def configured_mcp(home: Path, cwd: Path) -> dict:
    """Names of MCP servers in the config files -> where each was found. Only the keys are read."""
    found: dict = {}

    def add(names, where):
        for n in names or []:
            found.setdefault(str(n), where)

    cj = _json_file(home / ".claude.json")
    add((cj.get("mcpServers") or {}).keys(), "claude user")
    projects = cj.get("projects") or {}
    for d in [cwd, *cwd.parents]:
        for key in (str(d), str(d).replace("\\", "/")):
            add(((projects.get(key) or {}).get("mcpServers") or {}).keys(), "claude project")
        add((_json_file(d / ".mcp.json").get("mcpServers") or {}).keys(), "project .mcp.json")
    codex = home / ".codex" / "config.toml"
    if tomllib is not None and codex.is_file():
        try:
            add((tomllib.loads(codex.read_text(encoding="utf-8")).get("mcp_servers") or {}).keys(), "codex")
        except (OSError, ValueError):
            pass
    return found


def mcp_match(entry: dict, names, loose: bool = True) -> str | None:
    """The configured server name that is this entry: its catalogue name, a known alias, or (loose) a name containing the id's stem."""
    m = entry.get("mcp") or {}
    want = {x.lower() for x in [m.get("name"), *(m.get("existing_names") or []), entry["id"], entry["id"].split("-")[0]] if x}
    for n in names:
        low = n.lower()
        if low in want or (loose and any(w in low for w in want if len(w) >= 4)):
            return n
    return None


def check(entry: dict, mcp_names: dict) -> dict:
    kind, row = entry["kind"], {"id": entry["id"], "kind": entry["kind"], "name": entry.get("name", entry["id"]),
                                "cost": str(entry.get("cost", "")).split(" (")[0], "role": entry.get("role", "")}
    if kind == "cli":
        smoke = (entry.get("doctor") or {}).get("smoke")
        exe = smoke[0] if isinstance(smoke, list) and smoke else entry["id"]
        if entry["id"] == "hyperframes":
            row.update(present=None, how="pinned engine: python tools/doctor.py report (node_engine)")
            return row
        hit = shutil.which(exe) or (next((p for g in BLENDER_DIRS for p in glob.glob(g)), None) if entry["id"] == "blender" else None)
        row.update(present=bool(hit), how="PATH" if shutil.which(exe) else ("default install folder" if hit else "not found"))
    elif kind == "api":
        var = (entry.get("api") or {}).get("env_var")
        row.update(present=bool(var and os.environ.get(var)), how=f"env {var} {'set' if var and os.environ.get(var) else 'not set'}")
    elif kind == "mcp":
        n = mcp_match(entry, mcp_names)
        row.update(present=bool(n), server=n, how=f"{mcp_names[n]}: {n}" if n else "not in the config files (check your own tool list)")
    elif kind == "python-lib":
        mod = {"faster-whisper": "faster_whisper", "matte-fast": "onnxruntime"}.get(entry["id"], entry["id"].replace("-", "_"))
        try:
            ok = importlib.util.find_spec(mod) is not None
        except (ImportError, ValueError):
            ok = False
        row.update(present=ok, how=f"import {mod}")
    else:
        row.update(present=None, how="a model file: the tool that uses it reports it (prep / transcribe)")
    n = mcp_match(entry, mcp_names, loose=False) if kind != "mcp" else None  # some APIs/CLIs are also reachable through an MCP server (for example pexels)
    if n:
        row.update(server=n, how=(row["how"] + f"; also MCP server {n}") if row["present"] else f"through MCP server {n} ({mcp_names[n]})", present=True)
    return row


def report(cwd: Path, home: Path | None = None, entries: list | None = None) -> dict:
    home = home or Path.home()
    entries = load_catalog() if entries is None else entries
    names = configured_mcp(home, cwd)
    rows = {e["id"]: check(e, names) for e in entries}
    groups = {job: [rows[i] for i in ids if i in rows] for job, ids in JOBS.items()}
    other = sorted(set(names) - {r.get("server") for r in rows.values()})
    return {"tool": "connections", "groups": groups, "other_mcp_servers": other,
            "note": "presence only, nothing was called. claude.ai connectors and plugin servers are not in config files and may carry an id "
                    "instead of a vendor name: your own tool list is the truth - look for tools that do the job (generate_video, search_icons, "
                    "photos_search, ...). A configured server is not a working one; paid ones go through paid-spend-gate."}


def human(rep: dict) -> str:
    mark = {True: "yes", False: " - ", None: " ? "}
    out = ["connections (presence only; nothing was called)"]
    for job, rows in rep["groups"].items():
        out.append(f"\n{job}")
        for r in rows:
            out.append(f"  {mark[r['present']]}  {r['id']:<15} {r['kind']:<10} {r['cost']:<10} {r['how']}")
    if rep["other_mcp_servers"]:
        out.append("\nother MCP servers in the config files (not in the catalogue; judge them yourself): " + ", ".join(rep["other_mcp_servers"]))
    out.append("\n" + rep["note"])
    out.append("next: decide per job (use / not needed / fallback) and write it in the project before planning (pro-video-editor 'Connections').")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-o", "--out", type=Path, help="also write the JSON report here (for example <project>/_work/connections.json)")
    ap.add_argument("--cwd", type=Path, default=Path.cwd(), help="the project folder whose MCP config counts (default: here)")
    a = ap.parse_args(argv)
    rep = report(a.cwd.resolve())
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    print(json.dumps(rep, ensure_ascii=False, indent=2) if a.json else human(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())

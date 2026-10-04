"""tools/connections.py: presence-only report of what is connected, grouped by job (no service is called, no value is read)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import connections as cn  # noqa: E402

ENTRIES = [
    {"id": "iconify", "kind": "mcp", "cost": "free", "mcp": {"name": "avc-iconify"}},
    {"id": "blender-mcp", "kind": "mcp", "cost": "free", "mcp": {"name": "avc-blender", "existing_names": ["blender"]}},
    {"id": "higgsfield", "kind": "mcp", "cost": "paid (credits)", "mcp": {"name": "higgsfield"}},
    {"id": "pexels", "kind": "api", "cost": "free-tier", "api": {"env_var": "AVC_TEST_PEXELS_KEY"}},
    {"id": "node", "kind": "cli", "cost": "free", "doctor": {"smoke": ["definitely-not-a-binary-xyz", "--version"]}},
]


def home_with(tmp_path: Path, user: dict, project: dict | None = None, cwd: Path | None = None) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    cfg = {"mcpServers": {n: {"command": "x", "env": {"OPT": "sentinel-config-value"}} for n in user}}
    if project is not None:
        cfg["projects"] = {str(cwd): {"mcpServers": {n: {} for n in project}}}
    (home / ".claude.json").write_text(json.dumps(cfg), encoding="utf-8")
    return home


def test_mcp_names_user_project_and_mcp_json(tmp_path):
    cwd = tmp_path / "proj"
    cwd.mkdir()
    (cwd / ".mcp.json").write_text(json.dumps({"mcpServers": {"avc-playwright": {}}}), encoding="utf-8")
    home = home_with(tmp_path, ["iconify", "node_repl"], ["blender"], cwd)
    names = cn.configured_mcp(home, cwd)
    assert names == {"iconify": "claude user", "node_repl": "claude user", "blender": "claude project", "avc-playwright": "project .mcp.json"}


def test_report_groups_by_job_presence_only_and_never_leaks_values(tmp_path, monkeypatch):
    cwd = tmp_path / "proj"
    cwd.mkdir()
    home = home_with(tmp_path, ["iconify", "blender", "pexels", "node_repl", "pinterest"])
    monkeypatch.setenv("AVC_TEST_PEXELS_KEY", "sentinel-env-value")
    rep = cn.report(cwd, home=home, entries=ENTRIES)
    rows = {r["id"]: r for g in rep["groups"].values() for r in g}
    assert rows["iconify"]["present"] and rows["iconify"]["server"] == "iconify"  # loose: the id stem inside the name
    assert rows["blender-mcp"]["present"] and rows["blender-mcp"]["server"] == "blender"  # a known alias
    assert rows["higgsfield"]["present"] is False  # not configured -> the agent checks its own tool list
    assert rows["pexels"]["present"] and "also MCP server pexels" in rows["pexels"]["how"]
    assert rows["node"]["present"] is False  # node_repl is NOT the node CLI (exact match for non-MCP rows)
    assert rep["other_mcp_servers"] == ["node_repl", "pinterest"]
    text = json.dumps(rep) + cn.human(rep)
    assert "sentinel-env-value" not in text and "sentinel-config-value" not in text
    assert "tool list" in rep["note"] and "paid-spend-gate" in rep["note"]


def test_cli_runs_fast_and_writes_json(tmp_path):
    out = tmp_path / "_work" / "connections.json"
    p = subprocess.run([sys.executable, "-X", "utf8", str(REPO / "tools" / "connections.py"), "--json", "-o", str(out)],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert p.returncode == 0, p.stderr
    rep = json.loads(p.stdout)
    assert json.loads(out.read_text(encoding="utf-8")) == rep and "render and core" in rep["groups"]

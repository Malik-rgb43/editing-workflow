"""uv.lock must describe THIS project: a stale lock makes `uv sync --locked` (used by the installer) fail and leaves the toolkit without numpy/Pillow."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_uv_lock_is_for_this_project_name_and_core_dependencies():
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    lock = tomllib.loads((REPO / "uv.lock").read_text(encoding="utf-8"))
    mine = [p for p in lock["package"] if p.get("source", {}).get("virtual") == "."]
    assert [p["name"] for p in mine] == [project["name"]], "uv.lock was generated for another project name: run `uv lock`"
    locked_core = {re.split(r"[<>=!~ ]", d)[0].lower() for d in project["dependencies"]}
    deps = {d["name"].lower() for d in mine[0].get("dependencies", [])}
    assert locked_core <= deps, f"uv.lock does not list the core dependencies {locked_core - deps}: run `uv lock`"

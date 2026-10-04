"""Every skill script's own self-check and unittest file runs in CI (they ship inside the skills and are not under tests/)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parents[2] / "agent-content" / "skills"
SELF_CHECK = sorted(p for p in SKILLS.glob("*/scripts/*.py") if not p.name.startswith("test_") and "--self-check" in p.read_text(encoding="utf-8"))
UNIT_FILES = sorted(SKILLS.glob("*/scripts/test_*.py"))
WRAPPERS = {p.with_name(p.name[5:]) for p in UNIT_FILES}  # their --self-check only re-runs the unittest file


def _id(p: Path) -> str:
    return f"{p.parents[1].name}/{p.name}"


def test_discovery_found_the_scripts():
    assert len(SELF_CHECK) >= 30 and len(UNIT_FILES) >= 3


@pytest.mark.parametrize("script", [p for p in SELF_CHECK if p not in WRAPPERS], ids=_id)
def test_self_check(script):
    p = subprocess.run([sys.executable, "-X", "utf8", str(script), "--self-check"], capture_output=True, text=True, encoding="utf-8", timeout=300, cwd=script.parent)
    assert p.returncode == 0, (p.stdout[-2000:], p.stderr[-2000:])


def _failure_text(stderr: str) -> str:
    """The unittest failure blocks themselves (tracebacks), not the last N characters (CI cut them off once)."""
    i = stderr.find("=" * 70)
    return stderr[i:i + 6000] if i >= 0 else stderr[-4000:]


@pytest.mark.parametrize("script", UNIT_FILES, ids=_id)
def test_unit_file(script):
    p = subprocess.run([sys.executable, "-X", "utf8", str(script)], capture_output=True, text=True, encoding="utf-8", timeout=300, cwd=script.parent)
    assert p.returncode == 0, _failure_text(p.stderr) + "\n--- stdout ---\n" + p.stdout[-1000:]

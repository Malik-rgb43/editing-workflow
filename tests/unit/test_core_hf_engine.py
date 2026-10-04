"""HyperFrames engine locator: pinned local engine first, never a download, ASCII-path guard (live finding 2026-10-03)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC))
from core import hf_engine  # noqa: E402


def fake_toolkit(root: Path, installed="0.8.98", pinned="0.8.98") -> Path:
    (root / "package.json").write_text(json.dumps({"dependencies": {"hyperframes": pinned}}), encoding="utf-8")
    pkg = root / "node_modules" / "hyperframes"
    (pkg / "bin").mkdir(parents=True, exist_ok=True)
    (pkg / "bin" / "hyperframes.mjs").write_text("// fake\n", encoding="utf-8")
    (pkg / "package.json").write_text(json.dumps({"version": installed}), encoding="utf-8")
    return root


@pytest.fixture
def with_node(monkeypatch):
    real = shutil.which
    monkeypatch.setattr(hf_engine.shutil, "which", lambda n, *a, **k: "/fake/node" if n == "node" else ("/fake/npx" if n == "npx" else real(n, *a, **k)))


def test_pinned_version_reads_exact_pin_only(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"hyperframes": "0.8.98"}}), encoding="utf-8")
    assert hf_engine.pinned_version(tmp_path) == "0.8.98"
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"hyperframes": "^0.8.98"}}), encoding="utf-8")
    assert hf_engine.pinned_version(tmp_path) is None
    assert hf_engine.pinned_version(tmp_path / "missing") is None


def test_toolkit_engine_preferred_over_npx(tmp_path, with_node):
    fake_toolkit(tmp_path)
    eng = hf_engine.find(tmp_path, env={})
    assert eng.source == "toolkit" and eng.version == "0.8.98" and eng.pinned == "0.8.98"
    assert eng.argv[0] == "/fake/node" and eng.argv[1].endswith("hyperframes.mjs")


def test_command_never_uses_a_downloading_npx(tmp_path, with_node):
    eng = hf_engine.find(tmp_path, env={})  # no node_modules
    assert eng.source == "project-local" and "--no-install" in eng.argv
    assert hf_engine.command(["render", "x"], tmp_path, env={})[-2:] == ["render", "x"]


def test_missing_engine_raises_instead_of_downloading(tmp_path, monkeypatch):
    monkeypatch.setattr(hf_engine.shutil, "which", lambda *a, **k: None)
    assert hf_engine.find(tmp_path, env={}) is None
    with pytest.raises(hf_engine.EngineMissing):
        hf_engine.command(["init"], tmp_path, env={})


def test_env_override_wins(tmp_path, with_node):
    fake_toolkit(tmp_path)
    cli = tmp_path / "other.mjs"
    cli.write_text("//", encoding="utf-8")
    eng = hf_engine.find(tmp_path, env={hf_engine.ENV_CLI: str(cli)})
    assert eng.source == "env" and eng.argv[-1] == str(cli)
    assert hf_engine.find(tmp_path, env={hf_engine.ENV_CLI: "no-such-binary-xyz"}) is None


def test_run_env_disables_telemetry_and_skill_fetch():
    env = hf_engine.run_env({"X": "1"})
    assert env["HYPERFRAMES_NO_TELEMETRY"] == "1" and env["HYPERFRAMES_SKIP_SKILLS"] == "1" and env["X"] == "1"


def test_non_ascii_engine_path_is_reported(tmp_path, with_node):
    heb = tmp_path / "דנה"
    heb.mkdir()
    fake_toolkit(heb)
    info = hf_engine.describe(heb)
    assert info["found"] and "non-ASCII" in info["problem"]
    ok = tmp_path / "ascii"
    ok.mkdir()
    fake_toolkit(ok)
    assert "problem" not in hf_engine.describe(ok)


def test_describe_flags_version_drift(tmp_path, with_node):
    fake_toolkit(tmp_path, installed="0.8.114", pinned="0.8.98")
    assert hf_engine.describe(tmp_path)["version_matches_pin"] is False
    fake_toolkit(tmp_path)
    assert hf_engine.describe(tmp_path)["version_matches_pin"] is True


def test_describe_without_node_says_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(hf_engine.shutil, "which", lambda *a, **k: None)
    assert hf_engine.describe(tmp_path) == {"found": False, "why": "no node/npx on PATH or no engine installed"}

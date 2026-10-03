"""doctor: report/recommend/smoke contract. Green only when every REQUIRED check passed; unsupported != missing != error."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "doctor.py"


def run(*args):
    p = subprocess.run([sys.executable, "-X", "utf8", str(TOOL), *args, "--json"], capture_output=True, text=True, encoding="utf-8", timeout=300)
    return p.returncode, json.loads(p.stdout)


def test_help_fast():
    t = time.monotonic()
    p = subprocess.run([sys.executable, str(TOOL), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0 and time.monotonic() - t < 1.5


@pytest.mark.ffmpeg
def test_report_mode_is_never_green_because_the_qa_gate_did_not_run():
    rc, rep = run("report")
    by = {c["id"]: c for c in rep["checks"]}
    assert by["qa_tools_smoke"]["state"] == "not_run"
    assert rep["aggregate"] == "not_green" and rc == 2


@pytest.mark.ffmpeg
def test_smoke_is_green_on_a_healthy_machine_and_recommends_cpu_baseline():
    rc, rep = run("smoke")
    assert rep["aggregate"] == "green" and rc == 0
    assert rep["recommendation"]["base"]["profile"] == "core-cpu"
    assert rep["recommendation"]["asr"]["profile"] == "asr-cpu"  # GPU routes are upgrades, never the default
    assert rep["recommendation"]["video_encoder"]["final"] == "libx264"
    assert all(c["redacted"] for c in rep["checks"])
    assert str(Path.home()) not in json.dumps(rep)


def test_missing_ffmpeg_is_red_and_dependent_checks_not_run(monkeypatch, tmp_path):
    import os

    env = dict(os.environ, PATH=str(tmp_path), PATHEXT=os.environ.get("PATHEXT", ""))
    p = subprocess.run([sys.executable, "-X", "utf8", str(TOOL), "report", "--json"], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
    rep = json.loads(p.stdout)
    by = {c["id"]: c for c in rep["checks"]}
    assert by["ffmpeg_found"]["state"] == "fail" and "winget" in by["ffmpeg_found"]["remediation"]
    assert by["ffmpeg_encode_decode"]["state"] == "not_run"
    assert rep["aggregate"] == "red" and p.returncode == 1

"""transcribe (no model downloads here), new_project, render_lock and ledger CLIs."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO / "src"))


def run(tool, *args, env=None, timeout=120):
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / f"{tool}.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout, env=env)


@pytest.mark.parametrize("tool", ["transcribe", "new_project", "render_lock", "ledger", "hf_segment", "hf_deliver"])
def test_help_under_one_and_a_half_seconds(tool):
    t = time.monotonic()
    p = run(tool, "--help")
    assert p.returncode == 0 and time.monotonic() - t < 1.5, (tool, time.monotonic() - t)  # E04-L01: the original transcribe --help took > 45 s


def test_transcribe_normalize_words_is_monotonic_and_drops_empties():
    import transcribe

    out = transcribe.normalize_words([{"w": " שלום ", "start": 0.5, "end": 0.9, "prob": 0.91234}, {"w": " ", "start": 1, "end": 2}, {"w": "עולם", "start": 0.7, "end": 0.6}, {"w": "x", "start": -1, "end": 5}])
    assert [w["w"] for w in out] == ["שלום", "עולם", "x"]
    assert all(o["end"] >= o["start"] >= 0 for o in out) and out[1]["start"] >= out[0]["end"] - 0.001


def test_transcribe_has_exactly_one_route_and_never_a_whisper_cpp_binary():
    import transcribe

    routes = {"faster-whisper": {"usable": False}}
    assert transcribe.choose_route(routes) is None
    routes["faster-whisper"]["usable"] = True
    assert transcribe.choose_route(routes) == "faster-whisper"
    assert list(transcribe.available_routes()) == ["faster-whisper"]


def test_transcribe_refuses_without_model_and_without_download_permission(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF....")
    p = run("transcribe", wav, "-o", tmp_path / "w.json")
    assert p.returncode == 2 and not (tmp_path / "w.json").exists()
    assert "allow-download" in p.stderr or "no usable route" in p.stderr


def test_transcribe_missing_input_exits_nonzero(tmp_path):
    p = run("transcribe", tmp_path / "nope.wav", "-o", tmp_path / "w.json")
    assert p.returncode == 2


@pytest.mark.ffmpeg
def test_new_project_scaffold_copy_verify_and_no_overwrite(tmp_path, e04_set):
    wr = tmp_path / "work"
    p = run("new_project", "סרטון בדיקה", "--work-root", wr, "--copy", e04_set["clean"], "--json")
    assert p.returncode == 0, p.stderr
    d = json.loads(p.stdout)
    root = Path(d["root"])
    assert root.name.isascii() and (root / "source" / "clean.mkv").is_file() and (root / "hf" / "fonts").is_dir()
    assert json.loads((root / "project.json").read_text(encoding="utf-8"))["title"] == "סרטון בדיקה"
    p2 = run("new_project", "סרטון בדיקה", "--work-root", wr, "--copy", e04_set["clean"], "--json")
    assert p2.returncode == 2 and "never overwritten" in p2.stdout  # re-run does not overwrite the source copy


def test_new_project_starter_writes_a_draft_that_the_intake_gate_still_blocks(tmp_path):
    p = run("new_project", "--list-starters")
    assert p.returncode == 0 and "talking-head" in p.stdout.split()
    p = run("new_project", "סרטון דובר", "--work-root", tmp_path / "work", "--starter", "talking-head", "--json")
    assert p.returncode == 0, p.stderr
    d = json.loads(p.stdout)
    hf = Path(d["hf"])
    assert sorted(d["templates_written"]) == ["BRIEF.md", "DESIGN.md", "PROMPT.md"]
    prompt = (hf / "PROMPT.md").read_text(encoding="utf-8")
    assert "status: DRAFT (not approved)" in prompt and "type: talking-head" in (hf / "BRIEF.md").read_text(encoding="utf-8")
    # the starter is well-formed, yet the intake ledger gate FAILS it until every ASK is answered by the user
    checker = REPO / "agent-content" / "skills" / "video-brief-intake" / "scripts" / "ledger_check.py"
    c = subprocess.run([sys.executable, "-X", "utf8", str(checker), str(hf / "PROMPT.md"), "--structure-only", "--footage", "--json"],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    rep = json.loads(c.stdout)
    assert c.returncode == 1 and rep["rows"] == 14
    assert {f["code"] for f in rep["findings"] if f["severity"] == "error"} == {"blocking_dim_missing"}
    # a second run never overwrites the draft the agent has been editing
    (hf / "PROMPT.md").write_text("edited", encoding="utf-8")
    p = run("new_project", "סרטון דובר", "--work-root", tmp_path / "work", "--starter", "talking-head", "--json")
    assert json.loads(p.stdout)["templates_written"] == [] and (hf / "PROMPT.md").read_text(encoding="utf-8") == "edited"
    assert run("new_project", "x", "--work-root", tmp_path / "work", "--starter", "nope").returncode == 2


def test_new_project_refuses_without_work_root_and_non_ascii_root(tmp_path):
    import os

    env = {k: v for k, v in os.environ.items() if not k.startswith("AVC_")}
    p = run("new_project", "x", env=env)
    assert p.returncode == 2 and "work root" in p.stderr
    p2 = run("new_project", "x", "--work-root", tmp_path / "תיקייה")
    assert p2.returncode == 2


def test_render_lock_status_and_run_roundtrip(tmp_path):
    lock = tmp_path / "locks" / "r.lock"
    import os

    env = dict(os.environ, AVC_PATHS_LOCK_PATH=str(lock))
    p = run("render_lock", "status", "--json", env=env)
    assert p.returncode == 0 and json.loads(p.stdout)["state"] == "free"


def test_ledger_demo_and_summary(tmp_path):
    f = tmp_path / "l.jsonl"
    assert run("ledger", "demo", f).returncode == 0
    p = run("ledger", "summarize", f, "--json")
    d = json.loads(p.stdout)
    assert p.returncode == 0 and d["malformed_lines"] == 0
    f.write_text(f.read_text(encoding="utf-8") + "{not json\n", encoding="utf-8")
    assert run("ledger", "summarize", f).returncode == 2  # malformed lines are reported, never skipped silently


def test_new_project_init_hyperframes_reports_missing_engine_and_never_downloads(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import new_project
    from core import hf_engine

    hf = tmp_path / "hf"
    hf.mkdir()
    saved = hf_engine.find
    hf_engine.find = lambda *a, **k: None
    try:
        r = new_project._init_hyperframes(hf)
    finally:
        hf_engine.find = saved
    assert r["ok"] is False and r["index_html_created"] is False and "engine not found" in r["why"]
    (hf / "x.txt").write_text("keep", encoding="utf-8")
    r2 = new_project._init_hyperframes(hf)
    assert r2["ok"] is False and "not empty" in r2["why"] and (hf / "x.txt").read_text(encoding="utf-8") == "keep"

"""ledger.py: JSONL writer, stage timer, summariser (null credits != 0)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from core import ledger as lg

SRC = str(Path(__file__).resolve().parents[2] / "src")


def lines(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_record_writes_one_valid_utf8_line_per_call(tricky_dir, schema_registry):
    path = tricky_dir / "_work" / "timing-ledger.jsonl"
    led = lg.Ledger(path, project="סרטון 'א' 🎬", attempt=2)
    e1 = led.record("render", tool="hf_deliver", run_min=3.5, queue_wait_min=0.25, renders=1, retries=0, credits=None)
    led.record("qa", tool="frame_qa", qa_min=1.0, credits=0.0, status="failed", note="שגיאה בבדיקה")
    rows = lines(path)
    assert len(rows) == 2 and rows[0]["project"] == "סרטון 'א' 🎬" and rows[0]["attempt"] == 2
    assert rows[0]["credits"] is None and rows[1]["credits"] == 0.0  # unknown is not zero
    raw = path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw and "שגיאה".encode("utf-8") in raw
    v = schema_registry("timing-ledger.schema.json")
    for row in rows:
        v.validate(row)
    assert e1["schema"] == lg.LEDGER_SCHEMA


def test_record_rejects_bad_values(tmp_path):
    led = lg.Ledger(tmp_path / "l.jsonl")
    with pytest.raises(ValueError):
        led.record("x", run_min=-1)
    with pytest.raises(ValueError):
        led.record("x", status="weird")
    with pytest.raises(ValueError):
        led.record("x", credits=float("nan"))  # allow_nan=False in the serialiser
    assert not (tmp_path / "l.jsonl").exists() or (tmp_path / "l.jsonl").read_text() == ""


def test_stage_timer_measures_phases_with_monotonic_clock(tmp_path):
    led = lg.Ledger(tmp_path / "l.jsonl", project="p")
    with led.stage("render", tool="hf") as st:
        st.phase("setup")
        time.sleep(0.12)
        st.phase("run")
        time.sleep(0.30)
        st.renders += 1
        st.add_credits(1.5)
        st.add_minutes("queue_wait", 2.0)
    row = lines(tmp_path / "l.jsonl")[0]
    assert row["status"] == "ok" and row["renders"] == 1 and row["credits"] == 1.5
    assert row["queue_wait_min"] == 2.0 and 0.0015 < row["setup_min"] < 0.5 and row["run_min"] >= 0.30 / 60 * 0.9  # lower bounds only: a loaded CI runner may overshoot a sleep but never undershoot it
    assert row["ended_utc"] >= row["started_utc"] and row["started_utc"].endswith("+00:00")
    with pytest.raises(ValueError):
        with led.stage("x") as st2:
            st2.phase("nonsense")


def test_exception_inside_stage_is_recorded_as_failed_and_reraised(tmp_path):
    led = lg.Ledger(tmp_path / "l.jsonl")
    with pytest.raises(RuntimeError):
        with led.stage("render") as st:
            st.phase("run")
            raise RuntimeError("boom")
    row = lines(tmp_path / "l.jsonl")[0]
    assert row["status"] == "failed" and row["credits"] is None


def test_summary_per_stage_and_null_credits_are_not_summed_as_zero(tmp_path):
    p = tmp_path / "l.jsonl"
    led = lg.Ledger(p, project="alpha")
    led.record("render", run_min=2, setup_min=1, renders=1, credits=None)
    led.record("render", run_min=3, renders=1, retries=1, credits=4.0, status="failed")
    led.record("qa", qa_min=1.5, review_min=2.0)
    lg.Ledger(p, project="beta").record("render", run_min=10, renders=2, credits=0.0)
    s = lg.summarize([p])
    a = s["projects"]["alpha"]
    assert a["stages"]["render"]["minutes"]["run"] == 5.0 and a["stages"]["render"]["renders"] == 2 and a["stages"]["render"]["retries"] == 1
    assert a["stages"]["render"]["credits_known_sum"] == 4.0 and a["stages"]["render"]["credits_unknown_entries"] == 1
    assert a["total"]["active_min"] == pytest.approx(2 + 1 + 3 + 1.5 + 2.0) and a["total"]["failed_entries"] == 1
    assert s["projects"]["beta"]["total"]["credits_known_sum"] == 0.0 and s["projects"]["beta"]["total"]["credits_unknown_entries"] == 0
    assert s["total"]["renders"] == 4 and s["malformed_lines"] == 0
    only = lg.summarize([p], project="beta")
    assert list(only["projects"]) == ["beta"]
    assert "alpha" in lg.format_summary(s) and "unknown credits" in lg.format_summary(s)


def test_malformed_lines_are_counted_never_silently_skipped(tmp_path):
    p = tmp_path / "l.jsonl"
    lg.Ledger(p, project="x").record("render", run_min=1)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write("not json\n{}\n" + json.dumps({"schema": "other/1", "stage": "x"}) + "\n\n")
    s = lg.summarize([p])
    assert s["malformed_lines"] == 3 and s["total"]["entries"] == 1


def test_concurrent_appenders_do_not_interleave_lines(tmp_path):
    p = tmp_path / "l.jsonl"
    code = (
        "import sys; from core.ledger import Ledger; l=Ledger(sys.argv[1], project=sys.argv[2])\n"
        "for i in range(40): l.record('render', run_min=0.01, note='x'*200)\n"
    )
    env = {**os.environ, "PYTHONPATH": SRC, "PYTHONUTF8": "1"}
    ps = [subprocess.Popen([sys.executable, "-c", code, str(p), f"p{i}"], env=env) for i in range(4)]
    assert all(q.wait(timeout=120) == 0 for q in ps)
    rows, bad = lg.read_ledger(p)
    assert bad == 0 and len(rows) == 160


def test_cli_demo_and_summarize(tricky_dir):
    env = {**os.environ, "PYTHONPATH": SRC, "PYTHONUTF8": "1"}
    f = tricky_dir / "ledger 'ש'.jsonl"
    r = subprocess.run([sys.executable, "-m", "core", "ledger", "demo", str(f)], env=env, capture_output=True, timeout=60)
    assert r.returncode == 0
    r = subprocess.run([sys.executable, "-m", "core", "ledger", "summarize", str(f), "--json"], env=env, capture_output=True, timeout=60)
    out = json.loads(r.stdout.decode("utf-8"))
    assert r.returncode == 0 and out["projects"]["demo"]["total"]["credits_unknown_entries"] == 3  # demo wrote no credits
    r = subprocess.run([sys.executable, "-m", "core", "ledger", "summarize", str(tricky_dir / "missing.jsonl")], env=env, capture_output=True, timeout=60)
    assert r.returncode == 2

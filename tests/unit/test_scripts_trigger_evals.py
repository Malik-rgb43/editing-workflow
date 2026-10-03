"""Positive and negative controls for tests/evals/run_trigger_evals.py (dry run + refusing model lane)."""

from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
RUNNER = REPO / "tests" / "evals" / "run_trigger_evals.py"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(RUNNER.parent))
import _avc_fixtures as F  # noqa: E402
import run_trigger_evals as E  # noqa: E402


@pytest.fixture()
def root(tmp_path):
    path = tmp_path / "תיקיית בדיקה" / "repo"
    F.make_repo(path)
    return path


def cli(root, *args):
    return F.run_cli(RUNNER, "--root", root, *args)


# ------------------------------------------------------------------ dry run


def test_dry_run_on_valid_evals_passes_and_says_model_eval_not_run(root):
    result = cli(root, "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "model_eval: not_run" in result.stdout and "RESULT: PASS" in result.stdout or "RESULT: WARN" in result.stdout
    assert "demo-skill" in result.stdout and "second-skill" in result.stdout


def test_dry_run_json_reports_counts_per_skill_and_model_eval(root):
    data = json.loads(cli(root, "--json").stdout)
    assert data["model_eval"] == "not_run" and data["exit"] == 0
    rows = {r["skill"]: r for r in data["skills"]}
    assert rows["demo-skill"]["positive"] == 8 and rows["demo-skill"]["negative"] == 4
    assert rows["demo-skill"]["hebrew_positive"] >= 1 and rows["demo-skill"]["status"] == "PASS"
    assert any(p["part"] == "model_eval" for p in data["not_run_parts"])
    assert data["stats"]["positive_cases"] == 16


def test_dry_run_is_the_default_and_calls_nothing(root, monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network or process spawn attempted")

    monkeypatch.setattr(socket, "socket", refuse)
    report, rows = E.dry_run(root)
    assert report.fails == [] and len(rows) == 2


@pytest.mark.parametrize(
    "break_it,expected_code",
    [
        (lambda d: (d / "evals/triggers.jsonl").unlink(), "triggers-missing"),
        (lambda d: F.write(d / "evals/triggers.jsonl", F.triggers_text(positive=7)), "trigger-count-positive"),
        (lambda d: F.write(d / "evals/triggers.jsonl", F.triggers_text(negative=3)), "trigger-count-negative"),
        (lambda d: F.write(d / "evals/triggers.jsonl", F.triggers_text(hebrew=False, positive=5, negative=3) + "".join(json.dumps({"prompt": f"more english cases {i}", "should_trigger": i < 3, "route_instead": None}) + "\n" for i in range(6))), "trigger-hebrew-positive"),
        (lambda d: F.write(d / "evals/triggers.jsonl", F.triggers_text() + "{broken\n"), "trigger-json"),
        (lambda d: F.write(d / "evals/triggers.jsonl", F.triggers_text() + json.dumps({"prompt": "x y z test", "should_trigger": 1, "route_instead": None}) + "\n"), "trigger-should"),
    ],
)
def test_invalid_eval_data_fails_with_exit_1(root, break_it, expected_code):
    break_it(root / "agent-content" / "skills" / "demo-skill")
    result = cli(root, "--json")
    data = json.loads(result.stdout)
    assert result.returncode == 1 and data["status"] == "FAIL"
    assert expected_code in {f["code"] for f in data["findings"] if f["level"] == "FAIL"}
    assert {r["skill"]: r["status"] for r in data["skills"]} == {"demo-skill": "FAIL", "second-skill": "PASS"}


def test_hebrew_prompts_survive_the_utf8_round_trip(root):
    skill = root / "agent-content" / "skills" / "demo-skill"
    cases, _ = E.load_cases(skill)
    assert any(c["prompt"] == "תערוך לי רילס מהסרטון הזה" for c in cases)
    assert not (skill / "evals" / "triggers.jsonl").read_bytes().startswith(b"\xef\xbb\xbf")


def test_no_skills_is_not_run_with_strict_exit_3(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    ok = cli(empty)
    assert ok.returncode == 0 and "RESULT: NOT_RUN" in ok.stdout and "model_eval: not_run" in ok.stdout
    assert cli(empty, "--strict").returncode == 3
    assert F.run_cli(RUNNER, "--root", tmp_path / "nope").returncode == 2


def test_help_is_fast_and_documents_the_gate():
    t = time.monotonic()
    result = F.run_cli(RUNNER, "--help")
    assert result.returncode == 0 and time.monotonic() - t < 3
    assert "--approved-by-owner" in result.stdout and "--budget" in result.stdout


# ------------------------------------------------------------------ model lane: refuses unless authorised


def test_model_lane_refuses_without_owner_approval(root):
    result = cli(root, "--model-lane")
    assert result.returncode == 2
    assert "REFUSED" in result.stderr and "--approved-by-owner" in result.stderr
    assert "nothing was spent" in result.stdout


def test_model_lane_refuses_without_approval_reference(root):
    result = cli(root, "--model-lane", "--approved-by-owner")
    assert result.returncode == 2 and "--approval-ref" in result.stderr
    assert cli(root, "--model-lane", "--approved-by-owner", "--approval-ref", "   ").returncode == 2


@pytest.mark.parametrize("budget", ["0", "-5", "61", "1000"])
def test_model_lane_refuses_bad_or_over_cap_budgets(root, budget):
    result = cli(root, "--model-lane", "--approved-by-owner", "--approval-ref", "ref-1", "--budget", budget)
    assert result.returncode == 2 and "REFUSED" in result.stderr


def test_model_lane_refuses_when_planned_runs_exceed_budget(root):
    # 16 positive + 8 negative = 24 cases
    result = cli(root, "--model-lane", "--approved-by-owner", "--approval-ref", "ref-1", "--budget", "10")
    assert result.returncode == 2 and "exceed the budget" in result.stderr
    result = cli(root, "--model-lane", "--approved-by-owner", "--approval-ref", "ref-1", "--budget", "60", "--hosts", "2", "--attempts", "2")
    assert result.returncode == 2 and "exceed the budget" in result.stderr


def test_authorised_model_lane_still_runs_nothing_and_reports_not_run(root, monkeypatch):
    result = cli(root, "--model-lane", "--approved-by-owner", "--approval-ref", "ref-1", "--budget", "60")
    assert result.returncode == 3, result.stdout + result.stderr
    assert "no model-eval runner is implemented" in result.stdout and "model_eval: not_run" in result.stdout
    assert "RESULT: NOT_RUN" in result.stdout
    # in-process: nothing in the lane can spawn processes or open sockets
    lane = E.ModelLane(60, "ref-1")
    with pytest.raises(NotImplementedError):
        lane.run_case("demo-skill", {"prompt": "x"}, "host-1")


def test_authorise_function_and_budget_counter_unit():
    E.assert_authorised(True, "ref", 60, 60)  # exactly at the cap is allowed
    with pytest.raises(E.RefusedError):
        E.assert_authorised(False, "ref", 60, 1)
    with pytest.raises(E.RefusedError):
        E.assert_authorised(True, None, 60, 1)
    with pytest.raises(E.RefusedError):
        E.assert_authorised(True, "ref", 60, 61)
    with pytest.raises(E.RefusedError):
        E.assert_authorised(True, "ref", 61, 1)
    lane = E.ModelLane(2, "ref")
    lane.reserve(2)
    with pytest.raises(E.RefusedError):
        lane.reserve(1)  # the counter is decremented before a spawn and cannot go over budget
    assert E.DEFAULT_BUDGET == 60


def test_runner_never_reads_credentials_or_imports_network_or_process_modules():
    source = RUNNER.read_text(encoding="utf-8")
    for needle in ("os.environ", "getenv", "import requests", "import urllib", "import socket", "import subprocess", "import http", "import smtplib"):
        assert needle not in source, needle
    assert "Usage:" in source


def test_the_real_repository_dry_run_never_crashes():
    result = F.run_cli(RUNNER, "--json")
    data = json.loads(result.stdout)
    assert data["model_eval"] == "not_run" and data["tool"] == "run_trigger_evals"
    assert result.returncode in (0, 1)  # data may be incomplete while other agents are still writing skills

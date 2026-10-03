"""Positive and negative controls for scripts/run_all_checks.py (orchestrator)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import _avc_common as C  # noqa: E402
import _avc_fixtures as F  # noqa: E402
import build_agent_adapters  # noqa: E402
import run_all_checks as RA  # noqa: E402

CLI = SCRIPTS / "run_all_checks.py"
SHA = "b" * 40
WORKFLOW = f"""name: ci
on:
  pull_request:
permissions:
  contents: read
jobs:
  t:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@{SHA}
        with:
          persist-credentials: false
      - run: python scripts/run_all_checks.py
"""


@pytest.fixture()
def green_root(tmp_path):
    """A synthetic repository in which every deterministic gate can pass."""
    root = tmp_path / "תיקיית בדיקה" / "repo"
    F.make_repo(root)
    F.write(root / ".github" / "workflows" / "ci.yml", WORKFLOW)
    assert F.run_cli(SCRIPTS / "gen_tools_md.py", "--root", root).returncode == 0
    assert F.run_cli(SCRIPTS / "gen_system_md.py", "--root", root).returncode == 0
    assert build_agent_adapters.build(root).fails == []
    return root


def results_by_gate(results):
    return {r["gate"]: r for r in results}


def test_all_gates_pass_on_a_valid_repo_and_not_run_is_explicit(green_root):
    results = results_by_gate(RA.run_gates(green_root))
    for gate in ("check_skills", "scan_secrets", "gen_bom", "build_agent_adapters", "gen_tools_md", "check_links", "check_step_ids", "check_workflows", "run_trigger_evals"):
        assert results[gate]["status"] in (C.PASS, C.WARN), (gate, results[gate])
    # gen_system_md warns about absent optional folders but does not fail
    assert results["gen_system_md"]["status"] in (C.PASS, C.WARN)
    # the denylist is local and absent: reported as NOT_RUN, never PASS
    assert results["scan_private"]["status"] == C.NOT_RUN and "denylist" in results["scan_private"]["detail"]
    # model eval is always an explicit not_run row; pytest is not run unless asked
    assert results["model_eval"]["status"] == C.NOT_RUN and "model_eval: not_run" in results["model_eval"]["detail"]
    assert "pytest" not in results
    assert RA.overall(list(results.values())) == 0
    assert RA.overall(list(results.values()), strict_not_run=True) == 3


def test_a_denylist_makes_scan_private_pass_and_strict_clean(green_root):
    F.write(green_root / "scripts" / "private_denylist.txt", "Fictional Brand\n")
    results = RA.run_gates(green_root)
    assert results_by_gate(results)["scan_private"]["status"] == C.PASS
    # model_eval alone never trips --strict
    assert RA.overall(results, strict_not_run=True) == 0


@pytest.mark.parametrize(
    "mutate,gate",
    [
        (lambda r: (r / "agent-content/skills/demo-skill/evals/triggers.jsonl").unlink(), "check_skills"),
        (lambda r: F.write(r / "notes.md", "token: " + "gh" + "p_" + "A1b2C3d4E5" * 4 + "\n"), "scan_secrets"),
        (lambda r: F.write(r / "agent-content/skills/demo-skill/references/guide.md", "path " + "C:" + "\\Users\\" + "somebody\\x\n"), "scan_private"),
        (lambda r: F.write(r / "assets" / ("mixkit" + "-x.wav"), "x"), "gen_bom"),
        (lambda r: (r / ".claude/skills/demo-skill/SKILL.md").write_bytes(b"edited"), "build_agent_adapters"),
        (lambda r: F.make_skill(r, "third-skill"), "gen_system_md"),
        (lambda r: F.make_tool(r, "another_tool"), "gen_tools_md"),
        (lambda r: F.write(r / "docs/en/broken.md", "[x](nowhere.md)\n"), "check_links"),
        (lambda r: F.make_docs_pair(r, ("a-01",), ("a-02",), "other.md"), "check_step_ids"),
        (lambda r: F.write(r / ".github/workflows/ci.yml", WORKFLOW.replace(SHA, "v4")), "check_workflows"),
        (lambda r: F.write(r / "agent-content/skills/demo-skill/evals/triggers.jsonl", F.triggers_text(positive=3)), "run_trigger_evals"),
    ],
)
def test_each_gate_fails_when_its_input_is_broken(green_root, mutate, gate):
    mutate(green_root)
    results = results_by_gate(RA.run_gates(green_root, only=[gate]))  # one gate per case keeps the suite fast
    assert results[gate]["status"] == C.FAIL, results[gate]
    assert RA.overall(list(results.values())) == 1


def test_a_crashing_gate_is_an_error_never_a_pass(green_root):
    spec = {"name": "boom", "argv": ["-c", "raise SystemExit('crash with no json')"]}
    result = RA.run_gate(spec, green_root)
    assert result["status"] == C.ERROR
    assert RA.overall([result]) == 1


def test_missing_pytest_dir_is_not_run_not_pass(green_root):
    results = results_by_gate(RA.run_gates(green_root, only=["check_skills"], with_pytest=True))
    assert set(results) == {"check_skills", "model_eval"}
    pyt = RA.run_gate({"name": "pytest", "argv": [], "pytest": True}, green_root)
    assert pyt["status"] == C.NOT_RUN


def test_only_and_skip_filters(green_root):
    only = [r["gate"] for r in RA.run_gates(green_root, only=["scan_secrets", "check_links"])]
    assert only == ["scan_secrets", "check_links", "model_eval"]
    skipped = [r["gate"] for r in RA.run_gates(green_root, skip=["check_skills", "gen_bom", "build_agent_adapters", "gen_system_md", "gen_tools_md", "check_links", "check_step_ids", "check_workflows", "run_trigger_evals", "scan_private"])]
    assert skipped == ["scan_secrets", "model_eval"]


def test_final_mode_changes_the_gate_arguments(green_root):
    specs = {s["name"]: s["argv"] for s in RA.gate_specs(green_root, final=True, register=None, with_pytest=False)}
    assert "--require-denylist" in specs["scan_private"]
    assert "--strict-pins" in specs["check_workflows"]
    assert "--check" in specs["gen_bom"] and "--no-write" not in specs["gen_bom"]
    assert "pytest" in specs
    normal = {s["name"]: s["argv"] for s in RA.gate_specs(green_root, final=False, register=None, with_pytest=False)}
    assert "--no-write" in normal["gen_bom"] and "pytest" not in normal


def test_final_run_fails_without_a_denylist_and_with_placeholder_pins(green_root):
    results = RA.run_gates(green_root, only=["scan_private", "check_workflows"], final=True)
    by = results_by_gate(results)
    assert by["scan_private"]["status"] == C.FAIL  # --require-denylist: missing denylist is a failure
    F.write(green_root / ".github/workflows/ci.yml", WORKFLOW.replace(SHA, "0" * 40))
    by = results_by_gate(RA.run_gates(green_root, only=["check_workflows"], final=True))
    assert by["check_workflows"]["status"] == C.FAIL
    assert results_by_gate(RA.run_gates(green_root, only=["check_workflows"]))["check_workflows"]["status"] == C.WARN


def test_cli_table_exit_codes_and_json(green_root):
    t = time.monotonic()
    assert F.run_cli(CLI, "--help").returncode == 0 and time.monotonic() - t < 3
    ok = F.run_cli(CLI, "--root", green_root)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "GATE" in ok.stdout and "model_eval" in ok.stdout and "NOT_RUN" in ok.stdout
    assert "RESULT: OK run_all_checks" in ok.stdout and "NOT_RUN gates did not run" in ok.stdout
    strict = F.run_cli(CLI, "--root", green_root, "--strict")
    assert strict.returncode == 3 and "RESULT: NOT_RUN" in strict.stdout
    data = json.loads(F.run_cli(CLI, "--root", green_root, "--json").stdout)
    assert data["exit"] == 0 and {r["gate"] for r in data["results"]} >= {"check_skills", "model_eval"}
    (green_root / "agent-content/skills/demo-skill/evals/tasks.md").unlink()
    bad = F.run_cli(CLI, "--root", green_root)
    assert bad.returncode == 1 and "RESULT: FAIL run_all_checks" in bad.stdout
    assert F.run_cli(CLI, "--root", green_root / "nope").returncode == 2


def test_warnings_as_errors(green_root):
    F.write(green_root / ".github/workflows/ci.yml", WORKFLOW.replace(SHA, "0" * 40))  # placeholder pin -> WARN
    assert F.run_cli(CLI, "--root", green_root).returncode == 0
    assert F.run_cli(CLI, "--root", green_root, "--warnings-as-errors").returncode == 1


def test_empty_repo_reports_not_run_rows_not_passes(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    by = results_by_gate(RA.run_gates(empty))
    for gate in ("check_skills", "gen_tools_md", "check_step_ids", "check_workflows", "build_agent_adapters", "gen_system_md", "check_links"):
        assert by[gate]["status"] == C.NOT_RUN, (gate, by[gate])
    assert by["gen_bom"]["status"] == C.FAIL  # no licenses.toml: fail closed (and an empty tree is the only file set)

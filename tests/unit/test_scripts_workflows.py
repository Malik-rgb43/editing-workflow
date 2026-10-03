"""Positive and negative controls for scripts/check_workflows.py, plus the repository's real workflow files."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
import _avc_common as C  # noqa: E402
import _avc_fixtures as F  # noqa: E402
import check_workflows as W  # noqa: E402

CLI = SCRIPTS / "check_workflows.py"
SHA = "a" * 40

GOOD = f"""name: ci
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@{SHA} # v4.1.0
        with:
          persist-credentials: false
      - run: python scripts/run_all_checks.py
"""

MODEL_OK = f"""name: eval-model
on:
  workflow_dispatch:
    inputs:
      approved:
        type: boolean
        required: true
permissions:
  contents: read
jobs:
  eval:
    if: ${{{{ inputs.approved == true }}}}
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@{SHA}
        with:
          persist-credentials: false
      - run: python tests/evals/run_trigger_evals.py --model-lane --approved-by-owner --approval-ref x
"""


@pytest.fixture()
def root(tmp_path):
    return tmp_path / "קורס" / "repo"


def put(root, name, text):
    F.write(root / ".github" / "workflows" / name, text)


def run(root, **kw):
    return W.run(root, **kw)


def codes(report, level="FAIL"):
    return {f.code for f in report.findings if f.level == level}


def test_good_workflow_passes(root):
    put(root, "ci.yml", GOOD)
    report = run(root)
    assert report.status == C.PASS, [f.render() for f in report.findings]


def test_approval_gated_dispatch_only_model_lane_passes(root):
    put(root, "eval-model.yml", MODEL_OK)
    assert run(root).fails == []


@pytest.mark.parametrize(
    "mutate,expected",
    [
        (lambda t: t.replace(f"@{SHA}", "@v4"), "wf-unpinned-action"),
        (lambda t: t.replace(f"@{SHA}", "@main"), "wf-unpinned-action"),
        (lambda t: t.replace(f"@{SHA} # v4.1.0", "@" + SHA[:39]), "wf-unpinned-action"),  # 39 hex chars is not a SHA
        (lambda t: t.replace("permissions:\n  contents: read\n", ""), "wf-permissions-missing"),
        (lambda t: t.replace("contents: read", "contents: write"), "wf-permissions-write"),
        (lambda t: t.replace("permissions:\n  contents: read", "permissions: write-all"), "wf-permissions-write"),
        (lambda t: t.replace("pull_request:", "pull_request_target:"), "wf-pull-request-target"),
        (lambda t: t + "      - run: echo ${{ secrets.API_TOKEN }}\n", "wf-secrets-untrusted"),
        (lambda t: t + "    secrets: inherit\n", "wf-secrets-inherit"),
        (lambda t: t + '      - run: echo "${{ github.event.pull_request.title }}"\n', "wf-script-injection"),
        (lambda t: t + '      - run: echo "${{ github.head_ref }}"\n', "wf-script-injection"),
        (lambda t: t + "      - run: claude -p 'hello'\n", "wf-paid-lane"),
        (lambda t: t + "      - run: python tests/evals/run_trigger_evals.py --model-lane\n", "wf-paid-lane"),
        (lambda t: t + "    env:\n      ANTHROPIC_API_KEY: x\n", "wf-paid-lane"),
    ],
)
def test_policy_violations_fail(root, mutate, expected):
    put(root, "ci.yml", mutate(GOOD))
    report = run(root)
    assert report.status == C.FAIL and expected in codes(report), [f.render() for f in report.findings]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda t: t.replace("on:\n  workflow_dispatch:", "on:\n  push:\n  workflow_dispatch:"),  # also on push
        lambda t: t.replace("on:\n  workflow_dispatch:", "on:\n  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:"),
        lambda t: t.replace("      approved:\n        type: boolean\n        required: true\n", "      note:\n        type: string\n"),  # no approval input
        lambda t: t.replace("    if: ${{ inputs.approved == true }}\n", ""),  # no job-level gate
    ],
)
def test_model_lane_must_be_dispatch_only_with_approval_input_and_job_gate(root, mutate):
    text = MODEL_OK.replace("${{{{", "${{").replace("}}}}", "}}")
    put(root, "eval-model.yml", mutate(text))
    assert "wf-paid-lane" in codes(run(root))


def test_comments_may_mention_keys_and_secrets(root):
    put(root, "ci.yml", "# never use secrets.TOKEN or ANTHROPIC_API_KEY here; no claude -p either\n" + GOOD)
    assert run(root).fails == []


def test_secrets_are_ok_in_a_dispatch_only_workflow(root):
    put(root, "manual.yml", GOOD.replace("on:\n  push:\n    branches: [main]\n  pull_request:\n", "on:\n  workflow_dispatch:\n") + "      - run: echo ${{ secrets.DEPLOY_NOTE }}\n")
    assert "wf-secrets-untrusted" not in codes(run(root))


def test_placeholder_pins_warn_by_default_and_fail_when_strict(root):
    zero = "0" * 40
    put(root, "ci.yml", GOOD.replace(SHA, zero) + f"      - uses: actions/setup-python@{zero} # TODO pin to reviewed commit\n")
    soft = run(root)
    assert soft.fails == [] and "wf-pin-placeholder" in codes(soft, "WARN")
    strict = run(root, strict_pins=True)
    assert strict.status == C.FAIL and "wf-pin-placeholder" in codes(strict)
    # a TODO marker on a real-looking SHA is also treated as a placeholder
    put(root, "ci.yml", GOOD.replace("# v4.1.0", "# TODO pin to reviewed commit"))
    assert "wf-pin-placeholder" in codes(run(root), "WARN")


def test_local_actions_and_docker_refs_are_not_pin_checked(root):
    put(root, "ci.yml", GOOD + "      - uses: ./.github/actions/local\n      - uses: docker://alpine:3.20\n")
    assert run(root).fails == []


def test_missing_timeout_checkout_credentials_and_self_hosted_warn(root):
    text = GOOD.replace("    timeout-minutes: 10\n", "").replace("        with:\n          persist-credentials: false\n", "").replace("ubuntu-latest", "self-hosted")
    put(root, "ci.yml", text)
    warns = codes(run(root), "WARN")
    assert {"wf-timeout", "wf-persist-credentials", "wf-self-hosted"} <= warns


def test_multiple_files_each_checked_and_empty_is_not_run(root, tmp_path):
    put(root, "a.yml", GOOD)
    put(root, "b.yaml", GOOD.replace(SHA, "main"))
    report = run(root)
    assert report.stats["workflows"] == 2 and any(f.path.endswith("b.yaml") for f in report.fails)
    assert run(tmp_path / "none").status == C.NOT_RUN


def test_cli(root):
    put(root, "ci.yml", GOOD)
    t = time.monotonic()
    assert F.run_cli(CLI, "--help").returncode == 0 and time.monotonic() - t < 3
    assert F.run_cli(CLI, "--root", root).returncode == 0
    put(root, "ci.yml", GOOD.replace(SHA, "v4"))
    bad = F.run_cli(CLI, "--root", root, "--json")
    assert bad.returncode == 1 and json.loads(bad.stdout)["status"] == "FAIL"
    assert F.run_cli(CLI, "--root", root / "nope").returncode == 2
    empty = root.parent / "e"
    empty.mkdir()
    assert F.run_cli(CLI, "--root", empty, "--strict").returncode == 3


# ------------------------------------------------------------------ this repository's own workflows


def test_real_workflows_follow_the_policy_and_are_pinned_to_commit_shas():
    wf_dir = REPO / ".github" / "workflows"
    assert (wf_dir / "ci.yml").is_file() and (wf_dir / "eval-model.yml").is_file()
    report = W.run(REPO)
    assert report.fails == [], [f.render() for f in report.fails]
    # the actions are pinned to full commit SHAs (resolved 2026-10-02): no placeholder remains, so the strict (release) check passes too
    assert "wf-pin-placeholder" not in codes(report, "WARN")
    assert W.run(REPO, strict_pins=True).status != C.FAIL


def test_real_ci_covers_three_operating_systems_with_least_privilege():
    text = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for runner in ("windows-latest", "macos-latest", "ubuntu-latest"):
        assert runner in text
    assert "permissions:\n  contents: read" in text
    assert "secrets." not in text.replace("`secrets.`", "")
    assert "scripts/run_all_checks.py" in text


def test_real_model_eval_workflow_is_disabled_manual_and_approval_gated():
    text = (REPO / ".github" / "workflows" / "eval-model.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    for forbidden in ("\n  push:", "\n  pull_request:", "\n  schedule:", "\n  pull_request_target:"):
        assert forbidden not in text
    assert "inputs.approved == true" in text and "vars.MODEL_EVAL_ENABLED == 'true'" in text
    assert "--approved-by-owner" in text and "secrets." not in text.split("jobs:")[1]

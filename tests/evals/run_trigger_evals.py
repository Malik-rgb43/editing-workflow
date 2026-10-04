"""Deterministic dry-run harness for skill trigger evals, with a gated stub for a future authorised model lane.

Usage: python tests/evals/run_trigger_evals.py [--root DIR] [--skills-dir DIR] [--dry-run] [--json] [--strict]
       python tests/evals/run_trigger_evals.py --model-lane --approved-by-owner --approval-ref REF [--budget 60] [--hosts N] [--attempts N]

Dry run (the default and the only lane that exists today): loads every agent-content/skills/*/evals/triggers.jsonl,
validates the schema {prompt, should_trigger, route_instead}, counts (>= 8 should-trigger incl. Hebrew, >= 4
should-not-trigger incl. Hebrew), Hebrew integrity (no mojibake, no '???'), duplicates, and that route_instead names a
real sibling skill. It calls no model, no network and spends nothing, and it ALWAYS reports ``model_eval: not_run``:
a green dry run says the eval DATA is well-formed, never that any skill triggers correctly.

Model lane (stub): REFUSES to run unless --approved-by-owner AND --approval-ref are given, and refuses when the planned
number of invocations (cases x hosts x attempts) exceeds --budget (default 60, the E05 ceiling; no hidden grader or
retry calls). Even when authorised it only raises NotImplementedError and exits 3 (not_run): no runner is implemented
because the author decision Q4 is open. A future implementation must decrement a durable counter BEFORE each spawn,
count retries/judges as invocations, isolate the workspace, never load credentials from fixtures, and treat errors as
invalid results rather than negative passes (see research SKILL_EVAL_HARNESS.md sections 2, 5, 8, 9).
Exit codes: 0 ok, 1 invalid eval data, 2 usage or REFUSED, 3 not_run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import _avc_common as C  # noqa: E402

DEFAULT_BUDGET = 60


class RefusedError(PermissionError):
    """Raised when the model lane is requested without owner authorisation or within-budget planning."""


def assert_authorised(approved_by_owner: bool, approval_ref: str | None, budget: int, planned: int) -> None:
    if not approved_by_owner:
        raise RefusedError("model lane REFUSED: --approved-by-owner is required (decision default Q4: no model evals without owner approval)")
    if not approval_ref or not approval_ref.strip():
        raise RefusedError("model lane REFUSED: --approval-ref (campaign approval reference) is required")
    if budget < 1:
        raise RefusedError("model lane REFUSED: --budget must be >= 1")
    if budget > DEFAULT_BUDGET:
        raise RefusedError(f"model lane REFUSED: --budget {budget} exceeds the default cap {DEFAULT_BUDGET} (E05); raise the cap in code review, not on the command line")
    if planned > budget:
        raise RefusedError(f"model lane REFUSED: planned {planned} invocations exceed the budget {budget}")


class ModelLane:
    """Interface for a future authorised model-eval lane. Nothing here calls a model."""

    def __init__(self, budget: int, approval_ref: str) -> None:
        self.budget = budget
        self.approval_ref = approval_ref
        self.spent = 0

    def reserve(self, count: int = 1) -> None:
        """Decrement the budget BEFORE spawning; refuse when it would be exceeded."""
        if self.spent + count > self.budget:
            raise RefusedError("budget exhausted")
        self.spent += count

    def run_case(self, skill: str, case: dict, host: str) -> dict:
        raise NotImplementedError("no model-eval runner is implemented (owner decision Q4 open); nothing was spent")

    def run(self, cases: list[tuple[str, dict]], hosts: list[str]) -> list[dict]:
        results = []
        for skill, case in cases:
            for host in hosts:
                self.reserve(1)
                results.append(self.run_case(skill, case, host))
        return results


def load_cases(skill_dir: Path) -> tuple[list[dict], str]:
    path = skill_dir / "evals" / "triggers.jsonl"
    text = path.read_bytes().decode("utf-8", errors="replace")
    cases = []
    for raw in text.split("\n"):
        line = raw.strip().lstrip("﻿")
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            cases.append(record)
    return cases, text


def dry_run(root: Path, skills_dir: Path | None = None) -> tuple[C.Report, list[dict]]:
    report = C.Report("run_trigger_evals")
    base = skills_dir or (root / "agent-content" / "skills")
    known = C.skill_names(base)
    rows: list[dict] = []
    if not known:
        report.not_run("trigger-evals", "no skills found under agent-content/skills (nothing to evaluate)")
        report.not_run("model_eval", "model_eval: not_run (no authorised lane is implemented)", blocking=False)
        return report, rows
    total_pos = total_neg = 0
    for name in sorted(known):
        skill_dir = base / name
        triggers = skill_dir / "evals" / "triggers.jsonl"
        rel = f"agent-content/skills/{name}/evals/triggers.jsonl"
        if not triggers.is_file():
            report.fail("triggers-missing", "evals/triggers.jsonl is missing", rel)
            rows.append({"skill": name, "positive": 0, "negative": 0, "status": "FAIL"})
            continue
        _, text = load_cases(skill_dir)
        issues, counts = C.validate_trigger_text(triggers.read_bytes().decode("utf-8", errors="replace"), known)
        failed = False
        for level, code, message, line in issues:
            if level == "FAIL":
                failed = True
                report.fail(code, message, rel, line)
            else:
                report.warn(code, message, rel, line)
        total_pos += counts["positive"]
        total_neg += counts["negative"]
        rows.append(
            {
                "skill": name,
                "positive": counts["positive"],
                "negative": counts["negative"],
                "hebrew_positive": counts["hebrew_positive"],
                "hebrew_negative": counts["hebrew_negative"],
                "status": "FAIL" if failed else "PASS",
            }
        )
    report.stats.update({"skills": len(rows), "positive_cases": total_pos, "negative_cases": total_neg})
    report.not_run("model_eval", "model_eval: not_run (dry run validates eval data only; no model was called)", blocking=False)
    return report, rows


def emit_dry_run(report: C.Report, rows: list[dict], as_json: bool, strict: bool) -> int:
    code = C.exit_code(report.status, strict_not_run=strict)
    if as_json:
        data = report.to_dict()
        data.update({"model_eval": "not_run", "skills": rows, "exit": code})
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return code
    if rows:
        width = max(len(r["skill"]) for r in rows)
        print(f"{'skill'.ljust(width)}  pos  neg  he+  he-  status")
        for r in rows:
            print(f"{r['skill'].ljust(width)}  {r['positive']:>3}  {r['negative']:>3}  {r.get('hebrew_positive', 0):>3}  {r.get('hebrew_negative', 0):>3}  {r['status']}")
    for finding in report.findings:
        if finding.level != "INFO":
            print(finding.render())
    print("model_eval: not_run")
    print(f"RESULT: {report.status} run_trigger_evals ({report.summary()})")
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic trigger-eval dry run; gated stub for a future authorised model lane.")
    parser.add_argument("--root", default=None, help="repository root (default: this repository)")
    parser.add_argument("--skills-dir", default=None, help="skills directory (default <root>/agent-content/skills)")
    parser.add_argument("--dry-run", action="store_true", help="validate eval data only (default behaviour)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--strict", action="store_true", help="exit 3 when there is nothing to evaluate")
    parser.add_argument("--model-lane", action="store_true", help="request the (unimplemented) authorised model lane")
    parser.add_argument("--approved-by-owner", action="store_true", help="owner explicitly approved this model run (required for --model-lane)")
    parser.add_argument("--approval-ref", default=None, help="reference of the author's campaign approval (required for --model-lane)")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help=f"maximum model invocations (default and cap {DEFAULT_BUDGET})")
    parser.add_argument("--hosts", type=int, default=1, help="number of hosts (planning only)")
    parser.add_argument("--attempts", type=int, default=1, help="attempts per case (planning only)")
    return parser


def main(argv: list[str] | None = None) -> int:
    C.setup_utf8()
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve() if args.root else REPO_ROOT
    if not root.is_dir():
        print(f"error: root is not a directory: {root.name}", file=sys.stderr)
        return C.EXIT_USAGE
    skills_dir = Path(args.skills_dir).resolve() if args.skills_dir else None
    if args.model_lane:
        base = skills_dir or (root / "agent-content" / "skills")
        cases: list[tuple[str, dict]] = []
        for name in sorted(C.skill_names(base)):
            if (base / name / "evals" / "triggers.jsonl").is_file():
                cases += [(name, c) for c in load_cases(base / name)[0]]
        planned = len(cases) * max(args.hosts, 1) * max(args.attempts, 1)
        try:
            assert_authorised(args.approved_by_owner, args.approval_ref, args.budget, planned)
        except RefusedError as exc:
            print(str(exc), file=sys.stderr)
            print("RESULT: REFUSED run_trigger_evals (nothing was run, nothing was spent)")
            return C.EXIT_USAGE
        lane = ModelLane(args.budget, args.approval_ref or "")
        try:
            lane.run_case("", {}, "host-1")  # authorised, but the runner is intentionally not implemented
        except NotImplementedError as exc:
            print(str(exc))
        print("RESULT: NOT_RUN run_trigger_evals (model lane has no implementation; model_eval: not_run)")
        return C.EXIT_NOT_RUN
    report, rows = dry_run(root, skills_dir)
    return emit_dry_run(report, rows, args.json, args.strict)


if __name__ == "__main__":
    sys.exit(main())

"""Run every deterministic gate and print one table; exit non-zero if any gate FAILS.

Usage: python scripts/run_all_checks.py [--root DIR] [--only GATE ...] [--skip GATE ...] [--register CSV] [--with-pytest] [--final] [--strict] [--warnings-as-errors] [--json]

Gates (each is a script run as a subprocess with --json, so the CLI contract itself is exercised):
  check_skills, scan_secrets, scan_private, gen_bom, build_agent_adapters, gen_system_md, gen_tools_md,
  check_links, check_step_ids, check_workflows, run_trigger_evals (dry-run), pytest (only with --with-pytest or --final).
Statuses: PASS, WARN (advisory), FAIL, NOT_RUN (the gate could not run: missing inputs / missing denylist /
model eval), ERROR (the gate crashed or printed no result: counts as FAIL). NOT_RUN is always shown explicitly and
never counted as PASS; it only changes the exit code with --strict (exit 3). The model-eval row is ALWAYS
``model_eval: not_run`` here (no model lane is run by this script; decision default Q4).
--final = release strictness: scan_private --require-denylist, check_workflows --strict-pins, gen_bom --check (BOM must
be fresh), pytest included, and NOT_RUN (other than model_eval) is a failure.
Exit codes: 0 no FAIL/ERROR, 1 FAIL/ERROR, 3 NOT_RUN under --strict (or --final), 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _avc_common as C  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 600


def gate_specs(root: Path, final: bool, register: str | None, with_pytest: bool) -> list[dict]:
    """Ordered gate definitions: name -> argv (after the interpreter)."""
    evals_runner = SCRIPTS.parent / "tests" / "evals" / "run_trigger_evals.py"  # the runner of THIS repository
    specs = [
        {"name": "check_skills", "argv": [str(SCRIPTS / "check_skills.py"), "--root", str(root), "--json"]},
        {"name": "scan_secrets", "argv": [str(SCRIPTS / "scan_secrets.py"), "--root", str(root), "--json"]},
        {
            "name": "scan_private",
            "argv": [str(SCRIPTS / "scan_private.py"), "--root", str(root), "--json"] + (["--require-denylist"] if final else []),
        },
        {
            "name": "gen_bom",
            "argv": [str(SCRIPTS / "gen_bom.py"), "--root", str(root), "--json"]
            + (["--check"] if final else ["--no-write"])
            + (["--register", register] if register else []),
        },
        {"name": "build_agent_adapters", "argv": [str(SCRIPTS / "build_agent_adapters.py"), "--root", str(root), "--check", "--json"]},
        {"name": "gen_system_md", "argv": [str(SCRIPTS / "gen_system_md.py"), "--root", str(root), "--check", "--json"]},
        {"name": "gen_tools_md", "argv": [str(SCRIPTS / "gen_tools_md.py"), "--root", str(root), "--check", "--json"]},
        {"name": "check_links", "argv": [str(SCRIPTS / "check_links.py"), "--root", str(root), "--json"]},
        {"name": "check_step_ids", "argv": [str(SCRIPTS / "check_step_ids.py"), "--root", str(root), "--json"]},
        {
            "name": "check_workflows",
            "argv": [str(SCRIPTS / "check_workflows.py"), "--root", str(root), "--json"] + (["--strict-pins"] if final else []),
        },
        {"name": "run_trigger_evals", "argv": [str(evals_runner), "--root", str(root), "--dry-run", "--json"], "script": evals_runner},
    ]
    if with_pytest or final:
        specs.append({"name": "pytest", "argv": ["-m", "pytest", "-q", "-x", "--no-header", "-p", "no:cacheprovider", str(root / "tests" / "unit")], "pytest": True})
    return specs


def run_gate(spec: dict, root: Path, python: str = sys.executable) -> dict:
    started = time.monotonic()
    name = spec["name"]
    script = spec.get("script")
    if script is not None and not Path(script).is_file():
        return {"gate": name, "status": C.NOT_RUN, "detail": "tests/evals/run_trigger_evals.py not found next to scripts/", "exit": None, "seconds": 0.0}
    if spec.get("pytest") and not (root / "tests" / "unit").is_dir():
        return {"gate": name, "status": C.NOT_RUN, "detail": "tests/unit not found", "exit": None, "seconds": 0.0}
    try:
        proc = subprocess.run(
            [python, "-X", "utf8", *spec["argv"]],
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            cwd=str(root),
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired:
        return {"gate": name, "status": C.ERROR, "detail": f"timed out after {TIMEOUT_SECONDS}s (a timeout never passes)", "exit": None, "seconds": round(time.monotonic() - started, 2)}
    except OSError as exc:
        return {"gate": name, "status": C.ERROR, "detail": f"could not start: {exc}", "exit": None, "seconds": 0.0}
    stdout = proc.stdout.decode("utf-8", errors="replace")
    elapsed = round(time.monotonic() - started, 2)
    if spec.get("pytest"):
        last = [ln for ln in stdout.strip().splitlines() if ln.strip()][-1:] or [""]
        status = C.PASS if proc.returncode == 0 else C.FAIL
        if proc.returncode == 5:
            status = C.NOT_RUN
            last = ["pytest collected no tests"]
        return {"gate": name, "status": status, "detail": last[0][:160], "exit": proc.returncode, "seconds": elapsed}
    data = C.parse_run_json(stdout)
    if data is None or "status" not in data:
        tail = proc.stderr.decode("utf-8", errors="replace").strip().splitlines()[-1:] or ["no JSON result printed"]
        return {"gate": name, "status": C.ERROR, "detail": tail[0][:160], "exit": proc.returncode, "seconds": elapsed}
    parts = []
    stats = data.get("stats") or {}
    for key, value in stats.items():
        if isinstance(value, (int, float, str)):
            parts.append(f"{key}={value}")
    fails = [f for f in data.get("findings", []) if f.get("level") == "FAIL"]
    warns = [f for f in data.get("findings", []) if f.get("level") == "WARN"]
    if fails:
        parts.insert(0, f"{len(fails)} fail")
    if warns:
        parts.insert(0 if not fails else 1, f"{len(warns)} warn")
    for item in data.get("not_run_parts", []):
        parts.append(f"NOT_RUN({item.get('part')}: {str(item.get('reason', ''))[:70]})")
    first = (fails or warns or [{}])[0]
    if first.get("code"):
        parts.append(f"first: {first.get('code')} {first.get('path', '')}".strip())
    return {"gate": name, "status": data["status"], "detail": "; ".join(parts), "exit": proc.returncode, "seconds": elapsed}


def run_gates(root: Path, only: list[str] | None = None, skip: list[str] | None = None, final: bool = False,
              register: str | None = None, with_pytest: bool = False, python: str = sys.executable) -> list[dict]:
    results = []
    for spec in gate_specs(root, final, register, with_pytest):
        if only and spec["name"] not in only:
            continue
        if skip and spec["name"] in skip:
            continue
        results.append(run_gate(spec, root, python))
    results.append(
        {
            "gate": "model_eval",
            "status": C.NOT_RUN,
            "detail": "model_eval: not_run (no authorised model lane is run here; decision default Q4)",
            "exit": None,
            "seconds": 0.0,
        }
    )
    return results


def overall(results: list[dict], strict_not_run: bool = False, warnings_as_errors: bool = False) -> int:
    code = C.EXIT_OK
    for result in results:
        status = result["status"]
        if status in (C.FAIL, C.ERROR):
            return C.EXIT_FAIL
        if status == C.WARN and warnings_as_errors:
            return C.EXIT_FAIL
        if status == C.NOT_RUN and strict_not_run and result["gate"] != "model_eval":
            code = C.EXIT_NOT_RUN
    return code


def render_table(results: list[dict]) -> str:
    width = max(len(r["gate"]) for r in results)
    lines = [f"{'GATE'.ljust(width)}  {'STATUS'.ljust(7)}  DETAIL"]
    lines.append(f"{'-' * width}  {'-' * 7}  {'-' * 40}")
    for r in results:
        lines.append(f"{r['gate'].ljust(width)}  {r['status'].ljust(7)}  {r['detail']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run all deterministic gates and print a status table.")
    C.add_common_args(parser)
    parser.add_argument("--only", nargs="+", default=None, metavar="GATE", help="run only these gates")
    parser.add_argument("--skip", nargs="+", default=None, metavar="GATE", help="skip these gates (they are not reported)")
    parser.add_argument("--register", default=None, help="LICENSE_REGISTER.csv passed to gen_bom for reconciliation")
    parser.add_argument("--with-pytest", action="store_true", help="also run pytest on tests/unit")
    parser.add_argument("--final", action="store_true", help="release strictness (denylist required, pins strict, BOM fresh, pytest, NOT_RUN fails)")
    return parser


def main(argv: list[str] | None = None) -> int:
    C.setup_utf8()
    args = build_parser().parse_args(argv)
    root = C.resolve_root(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root.name}", file=sys.stderr)
        return C.EXIT_USAGE
    results = run_gates(root, args.only, args.skip, args.final, args.register, args.with_pytest)
    strict = args.strict or args.final
    code = overall(results, strict, args.warnings_as_errors)
    if args.json:
        print(json.dumps({"tool": "run_all_checks", "final": args.final, "exit": code, "results": results}, ensure_ascii=False, indent=2))
        return code
    print(render_table(results))
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary = ", ".join(f"{n} {s}" for s, n in sorted(counts.items()))
    verdict = "FAIL" if code == C.EXIT_FAIL else ("NOT_RUN" if code == C.EXIT_NOT_RUN else "OK")
    print(f"\nRESULT: {verdict} run_all_checks ({summary})")
    if any(r["status"] == C.NOT_RUN for r in results):
        print("note: NOT_RUN gates did not run and are NOT counted as passes.")
    return code


if __name__ == "__main__":
    sys.exit(main())

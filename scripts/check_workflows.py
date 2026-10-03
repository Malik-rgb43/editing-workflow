"""Static policy checks for .github/workflows/*.yml (text-based; no YAML library, no network).

Usage: python scripts/check_workflows.py [--root DIR] [--strict-pins] [--json] [--strict] [--warnings-as-errors]

Policy from REPO_ARCHITECTURE section 11 and SECURITY_AND_LICENSING section 6:
  FAIL  every third-party ``uses:`` is pinned to a 40-hex commit SHA (tags/branches float);
  FAIL  top-level ``permissions:`` exists and grants no write access (least privilege);
  FAIL  no ``pull_request_target``, no ``secrets: inherit``, no ``secrets.`` in a workflow that runs on
        push/pull_request/schedule (untrusted changes never meet credentials);
  FAIL  no untrusted event text (PR title/body, head_ref, commit message) interpolated into a workflow (script injection);
  FAIL  a paid/model lane (mentions --model-lane, claude -p, codex exec, *_API_KEY) must live in a workflow whose only
        trigger is ``workflow_dispatch``, with an approval input and a job-level ``if:`` that tests it;
  WARN  a pin that is still the placeholder (40 zeros or a '# TODO pin to reviewed commit' comment) - FAIL with --strict-pins
        (release builds use --strict-pins: a release cannot be cut until every action is pinned to a reviewed commit);
  WARN  job without ``timeout-minutes``; checkout without ``persist-credentials: false``; self-hosted runners.
No workflow files -> NOT_RUN. Exit codes: 0 ok, 1 policy violation, 2 usage, 3 not_run with --strict.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _avc_common as C  # noqa: E402

USES_RE = re.compile(r"^\s*-?\s*uses:\s*(\S+)(.*)$")
SHA_RE = re.compile(r"@([0-9a-f]{40})$")
PAID_RE = re.compile(r"--model-lane|claude\s+-p\b|codex\s+exec\b|[A-Z]*_API_KEY|ANTHROPIC_|OPENAI_")
INJECTION_RE = re.compile(
    r"\$\{\{\s*(?:github\.head_ref|github\.event\.(?:pull_request\.(?:title|body|head\.ref|head\.label)|issue\.(?:title|body)|comment\.body|review\.body|head_commit\.message|commits)[^}]*)\s*\}\}"
)
UNTRUSTED_TRIGGERS = ("push", "pull_request", "schedule", "issues", "issue_comment", "workflow_run")


def workflow_files(root: Path) -> list[Path]:
    base = root / ".github" / "workflows"
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_file() and p.suffix in (".yml", ".yaml"))


def triggers_of(text: str) -> set[str]:
    """Names of top-level `on:` triggers (block, inline-list or scalar form)."""
    lines = text.split("\n")
    found: set[str] = set()
    for idx, line in enumerate(lines):
        match = re.match(r"^(?:on|\"on\"|'on'):\s*(.*)$", line)
        if not match:
            continue
        rest = match.group(1).split("#", 1)[0].strip()
        if rest:
            found.update(t.strip(" []\"'") for t in rest.split(",") if t.strip(" []\"'"))
            return found
        for follow in lines[idx + 1:]:
            if follow.strip() and not follow.startswith((" ", "\t")):
                break
            m = re.match(r"^  ([A-Za-z_]+):", follow)
            if m:
                found.add(m.group(1))
        return found
    return found


def check_text(name: str, text: str, report: C.Report, strict_pins: bool) -> None:
    label = f".github/workflows/{name}"
    lines = text.split("\n")
    code = re.sub(r"(?m)(^|\s)#.*$", "", text)  # comments may legitimately mention keys/secrets
    triggers = triggers_of(code)
    if "pull_request_target" in triggers or re.search(r"(?m)^\s*pull_request_target\s*:", text):
        report.fail("wf-pull-request-target", "pull_request_target is forbidden (runs untrusted code with credentials)", label)
    if not re.search(r"(?m)^permissions:", text):
        report.fail("wf-permissions-missing", "top-level `permissions:` is required (least privilege; use `contents: read`)", label)
    else:
        block = re.search(r"(?m)^permissions:(.*(?:\n(?:[ \t]+.*|\s*))*)", text)
        top = block.group(1) if block else ""
        if re.search(r"write-all|:\s*write\b", top):
            report.fail("wf-permissions-write", "top-level permissions must not grant write access", label)
    if re.search(r"secrets:\s*inherit", text):
        report.fail("wf-secrets-inherit", "`secrets: inherit` is forbidden", label)
    if INJECTION_RE.search(code):
        report.fail("wf-script-injection", "untrusted event text is interpolated into the workflow (use an env var instead)", label)
    untrusted = bool(triggers & set(UNTRUSTED_TRIGGERS)) or not triggers
    if re.search(r"\bsecrets\.", code) and untrusted:
        report.fail("wf-secrets-untrusted", "`secrets.` used in a workflow that runs on untrusted triggers", label)
    paid = bool(PAID_RE.search(code))
    if paid:
        only_dispatch = triggers == {"workflow_dispatch"}
        has_input = bool(re.search(r"(?mi)^\s{4,}[\w-]*approv[\w-]*:", code))
        job_gate = bool(re.search(r"(?m)^\s+if:.*inputs\.", code))
        if not (only_dispatch and has_input and job_gate):
            report.fail("wf-paid-lane", "model/paid lane must be workflow_dispatch-only with an approval input and a job-level `if:` testing inputs.*", label)
    for number, line in enumerate(lines, start=1):
        match = USES_RE.match(line)
        if match:
            ref = match.group(1)
            if ref.startswith(("./", "docker://")):
                continue
            sha = SHA_RE.search(ref)
            if not sha:
                report.fail("wf-unpinned-action", f"'{ref.split('@')[0]}' is not pinned to a commit SHA", label, number)
            elif sha.group(1) == "0" * 40 or "todo pin" in line.lower():
                (report.fail if strict_pins else report.warn)("wf-pin-placeholder", f"'{ref.split('@')[0]}' still has a placeholder pin (pin to a reviewed commit)", label, number)
        if re.search(r"runs-on:.*self-hosted", line):
            report.warn("wf-self-hosted", "self-hosted runner: keep untrusted changes away from it", label, number)
    jobs = re.search(r"(?m)^jobs:\s*$", text)
    if jobs:
        body = text[jobs.end():]
        job_blocks = re.split(r"(?m)^  (?=[A-Za-z0-9_-]+:\s*$)", body)[1:]
        for block in job_blocks:
            job_name = block.split(":", 1)[0]
            if "timeout-minutes" not in block:
                report.warn("wf-timeout", f"job '{job_name}' has no timeout-minutes", label)
    for match in re.finditer(r"uses:\s*actions/checkout@", text):
        window = text[match.end(): match.end() + 400]
        if "persist-credentials: false" not in window:
            report.warn("wf-persist-credentials", "actions/checkout without `persist-credentials: false`", label)
            break


def run(root: Path, strict_pins: bool = False) -> C.Report:
    report = C.Report("check_workflows")
    files = workflow_files(root)
    if not files:
        report.not_run("workflows", "no .github/workflows/*.yml files found")
        return report
    for path in files:
        try:
            text = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
        except (OSError, UnicodeDecodeError):
            report.fail("wf-unreadable", "workflow is not readable UTF-8", f".github/workflows/{path.name}")
            continue
        check_text(path.name, text, report, strict_pins)
    report.stats["workflows"] = len(files)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Static policy checks for GitHub Actions workflows.")
    C.add_common_args(parser)
    parser.add_argument("--strict-pins", action="store_true", help="placeholder SHA pins are a FAIL (release builds)")
    return parser


def main(argv: list[str] | None = None) -> int:
    C.setup_utf8()
    args = build_parser().parse_args(argv)
    root = C.resolve_root(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root.name}", file=sys.stderr)
        return C.EXIT_USAGE
    report = run(root, args.strict_pins)
    return C.emit(report, args.json, args.strict, args.warnings_as_errors)


if __name__ == "__main__":
    sys.exit(main())

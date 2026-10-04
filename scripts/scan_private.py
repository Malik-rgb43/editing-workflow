"""Scan the tree for private paths, owner/personal identifiers and denylisted client names.

Usage: python scripts/scan_private.py [--root DIR] [--denylist FILE] [--require-denylist] [--json] [--strict] [--no-git]

Two independent parts (never merged into one silent PASS):
  1. built-in patterns: user-home paths (Windows/macOS/Linux), the author's course path, the
     ``knowledge-pack`` folder, personal e-mail addresses, owner lab paths, ``brain/Clients`` style paths;
  2. the client-name denylist, loaded from a LOCAL, git-ignored file (default
     scripts/private_denylist.txt; override with --denylist or env AVC_PRIVATE_DENYLIST). A committed
     example lives in scripts/private_denylist.example.txt.
     If no usable denylist exists this part reports NOT_RUN and the overall result is NOT_RUN (exit 0,
     or exit 3 with --strict; --require-denylist turns it into a FAIL, used by release builds).

Denylist file format: one entry per line, '#' starts a comment.
  plain text  -> case-insensitive substring
  word:TEXT   -> case-insensitive whole-word match (Latin names)
  re:PATTERN  -> regular expression (case-insensitive)

Matched text is never printed (a client name must not leak into CI logs): findings give path:line and
the rule id or "denylist entry #N" only. A line containing ``scan-ignore`` is skipped. The scanner's own
sources, scripts/gen_bom.py (its block rules name private folders) and
tests/unit/test_scripts_*.py are excluded because they necessarily contain pattern text.
Exit codes: 0 pass/warn/not_run, 1 fail, 2 usage, 3 not_run with --strict.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _avc_common as C  # noqa: E402

SELF_EXCLUDE_GLOBS = (
    "scripts/scan_private.py",
    "scripts/scan_secrets.py",
    "scripts/gen_bom.py",
    "scripts/private_denylist.txt",
    "scripts/_avc_fixtures.py",
    "tests/unit/test_scripts_*.py",
)

_PLACEHOLDER = r"(?!(?:<|\{|%|\$|\[|\.\.\.|your|username|user\b|name\b|you\b|me\b|someone|example|NAME\b|USER\b))"

# (rule id, compiled regex, level, description)
PATTERNS: list[tuple[str, re.Pattern[str], str, str]] = [
    (
        "win-user-path",
        re.compile(
            r"(?i)\b[A-Z]:[\\/]{1,2}Users[\\/]{1,2}(?!(?:<|\{|%|\$|\[|\.\.\.|public\b|default\b|all users\b|username\b|user\b|name\b|you\b|your|me\b))[^\\/\s\"'`<>|*?:]+"
        ),
        "FAIL",
        "private Windows user-home path",
    ),
    (
        "mac-user-path",
        re.compile(r"(?<![\w.])/Users/" + _PLACEHOLDER + r"(?!Shared\b)[A-Za-z0-9._-]+"),
        "FAIL",
        "private macOS user-home path",
    ),
    (
        "linux-home-path",
        re.compile(r"(?<![\w.])/home/" + _PLACEHOLDER + r"(?!(?:runner|vscode|node|ubuntu)\b)[a-z_][a-z0-9_-]*"),
        "FAIL",
        "private Linux home path",
    ),
    (
        "owner-course-path",
        re.compile(r"[A-Za-z]:[\\/]+[^\s\"'`]*קורס"),
        "FAIL",
        "path into the author's course folder",
    ),
    (
        "knowledge-pack",
        re.compile(r"(?i)knowledge[-_ ]?pack"),
        "FAIL",
        "reference to the private knowledge-pack folder",
    ),
    (
        "private-brain-path",
        re.compile(r"(?i)(?:^|[\\/\s`'\"(])brain[\\/](?:clients|projects|lessons)(?:[\\/]|\b)"),
        "FAIL",
        "reference to private brain/Clients|Projects|Lessons content",
    ),
    (
        "personal-email",
        re.compile(
            r"(?i)\b[\w.+-]+@(?:gmail|googlemail|outlook|hotmail|live|yahoo|icloud|me|proton|protonmail|walla|012|bezeqint|netvision)\.(?:com|me|co\.il|net|org|il)\b"
        ),
        "FAIL",
        "personal e-mail address",
    ),
    (
        "owner-lab-path",
        re.compile(r"(?i)\b[A-Z]:[\\/]{1,2}[\w.-]*-lab\b"),
        "WARN",
        "owner lab path (use a placeholder or toolkit.toml)",
    ),
]


def load_denylist(path: Path | None) -> tuple[list[tuple[int, re.Pattern[str]]], str | None]:
    """Return (compiled entries, reason-not-usable)."""
    if path is None:
        return [], "no denylist path configured"
    if not path.is_file():
        return [], f"denylist file not found ({path.name}); create it from scripts/private_denylist.example.txt"
    entries: list[tuple[int, re.Pattern[str]]] = []
    number = 0
    for raw in path.read_bytes().decode("utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        number += 1
        try:
            if line.lower().startswith("re:"):
                pattern = re.compile(line[3:].strip(), re.IGNORECASE)
            elif line.lower().startswith("word:"):
                pattern = re.compile(r"(?<!\w)" + re.escape(line[5:].strip()) + r"(?!\w)", re.IGNORECASE)
            else:
                pattern = re.compile(re.escape(line), re.IGNORECASE)
        except re.error:
            raise ValueError(f"denylist entry #{number} is not a valid regular expression") from None
        entries.append((number, pattern))
    if not entries:
        return [], "denylist file has no active entries"
    return entries, None


def resolve_denylist_path(root: Path, explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit)
    env = os.environ.get("AVC_PRIVATE_DENYLIST")
    if env:
        return Path(env)
    return root / "scripts" / "private_denylist.txt"


def is_self_excluded(relpath: str) -> bool:
    return any(C.glob_match(g, relpath) for g in SELF_EXCLUDE_GLOBS)


def scan_text_patterns(relpath: str, text: str, report: C.Report) -> None:
    for number, line in enumerate(text.split("\n"), start=1):
        if C.SCAN_IGNORE_TOKEN in line.lower():
            continue
        for rule_id, regex, level, description in PATTERNS:
            if regex.search(line):
                add = report.fail if level == "FAIL" else report.warn
                add(rule_id, description, relpath, number)


def scan_path_patterns(relpath: str, report: C.Report, denylist: list[tuple[int, re.Pattern[str]]]) -> None:
    for rule_id, regex, level, description in PATTERNS:
        if rule_id in ("knowledge-pack", "private-brain-path") and regex.search(relpath):
            report.fail(rule_id, description + " (file path)", relpath)
    for number, pattern in denylist:
        if pattern.search(relpath):
            report.fail("denylist", f"matched denylist entry #{number} (file path)", relpath)


def scan_denylist_text(relpath: str, text: str, report: C.Report, denylist: list[tuple[int, re.Pattern[str]]]) -> None:
    if not denylist:
        return
    for number, line in enumerate(text.split("\n"), start=1):
        if C.SCAN_IGNORE_TOKEN in line.lower():
            continue
        for entry, pattern in denylist:
            if pattern.search(line):
                report.fail("denylist", f"matched denylist entry #{entry}", relpath, number)


def scan(root: Path, denylist_path: str | None = None, require_denylist: bool = False, use_git: bool = True,
         files: list[str] | None = None) -> C.Report:
    report = C.Report("scan_private")
    try:
        entries, reason = load_denylist(resolve_denylist_path(root, denylist_path))
    except ValueError as exc:
        entries, reason = [], None
        report.fail("denylist-invalid", str(exc))
    names = files if files is not None else C.list_files(root, use_git=use_git)
    scanned = 0
    for relpath in names:
        if is_self_excluded(relpath):
            continue
        scan_path_patterns(relpath, report, entries)
        text = C.read_scan_text(root / relpath)
        if text is None:
            continue
        scanned += 1
        scan_text_patterns(relpath, text, report)
        scan_denylist_text(relpath, text, report, entries)
    report.stats["files_scanned"] = scanned
    report.stats["patterns"] = len(PATTERNS)
    report.stats["denylist_entries"] = len(entries)
    if reason is not None:
        if require_denylist:
            report.fail("denylist-required", f"client-name denylist required but unusable: {reason}")
        else:
            report.not_run("denylist", reason, blocking=True)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan for private paths, personal identifiers and denylisted client names.")
    C.add_common_args(parser)
    parser.add_argument("--denylist", default=None, help="local denylist file (default scripts/private_denylist.txt)")
    parser.add_argument("--require-denylist", action="store_true", help="FAIL (not NOT_RUN) when the denylist is missing/empty")
    parser.add_argument("--no-git", action="store_true", help="walk the directory instead of using git's file list")
    return parser


def main(argv: list[str] | None = None) -> int:
    C.setup_utf8()
    args = build_parser().parse_args(argv)
    root = C.resolve_root(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root.name}", file=sys.stderr)
        return C.EXIT_USAGE
    report = scan(root, args.denylist, args.require_denylist, use_git=not args.no_git)
    return C.emit(report, args.json, args.strict, args.warnings_as_errors)


if __name__ == "__main__":
    sys.exit(main())

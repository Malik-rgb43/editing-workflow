"""Scan the tree for credentials: API keys, tokens, private keys and secret-bearing files.

Usage: python scripts/scan_secrets.py [--root DIR] [--allowlist FILE] [--json] [--strict] [--no-git]

Detects (regex, no network, no entropy guessing): cloud/API key prefixes (AWS, GitHub, Slack, Google,
OpenAI, Anthropic, Stripe, Hugging Face), JSON Web Tokens, PEM private-key blocks, npm/pypi auth lines,
quoted `api_key = "..."` style assignments with non-placeholder values, and file names such as .env,
*.pem, *.key, id_rsa, credentials.json (templates like .env.example are fine).

When the root is a git repo the scan covers the files git would ship (tracked + untracked-not-ignored),
so a git-ignored local .env is not reported; --no-git forces a plain directory walk (used by tests).

Matched values are never printed: findings show path:line and the rule id only.
Allowlist (default scripts/secrets_allowlist.txt, optional): one entry per line,
  GLOB                 skip that path for every rule
  GLOB :: RULE_ID      skip one rule for that path
A line containing ``scan-ignore`` is skipped. The scanner's own source and tests/unit/test_scripts_*.py
are excluded (they must contain pattern text; tests build fake tokens at run time).
Exit codes: 0 pass/warn, 1 fail, 2 usage, 3 not_run with --strict (nothing to scan).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _avc_common as C  # noqa: E402

SELF_EXCLUDE_GLOBS = (
    "scripts/scan_secrets.py",
    "scripts/scan_private.py",
    "scripts/_avc_fixtures.py",
    "tests/unit/test_scripts_*.py",
)

PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "AWS access key id"),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "GitHub token"),
    ("github-fine-grained", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"), "GitHub fine-grained token"),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "Slack token"),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "Google API key"),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "Anthropic API key"),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"), "OpenAI-style secret key"),
    ("stripe-key", re.compile(r"\b[sr]k_live_[0-9A-Za-z]{16,}\b"), "Stripe live key"),
    ("huggingface-token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b"), "Hugging Face token"),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----"), "PEM private key"),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "JSON Web Token"),
    ("npm-auth", re.compile(r"_authToken\s*=\s*[^\s$<{]{8,}"), "npm auth token line"),
    ("pypi-token", re.compile(r"\bpypi-[A-Za-z0-9_-]{40,}"), "PyPI upload token"),
    ("basic-auth-url", re.compile(r"\bhttps?://[^\s/:@<>\"']{1,40}:[^\s/@<>\"'{$%]{4,}@[\w.-]+"), "credentials embedded in a URL"),
]

ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    \b(?:api[_-]?key|apikey|secret(?:[_-]?key)?|access[_-]?token|auth[_-]?token|client[_-]?secret|token|passwd|password|private[_-]?key)\b
    ["']?\s*[:=]\s*["']([^"'\s]{12,})["']
    """
)
PLACEHOLDER_HINTS = (
    "<", ">", "{", "}", "$", "%", "xxx", "***", "your", "example", "placeholder", "changeme", "dummy", "fake",
    "test", "redacted", "...", "sample", "secret-here", "todo", "none", "null", "env.", "os.environ", "getenv",
)

SECRET_FILE_GLOBS = (
    ("secret-file-env", re.compile(r"(?i)(?:^|/)\.env(?:\.[^/]+)?$"), "environment file"),
    ("secret-file-key", re.compile(r"(?i)\.(?:pem|key|p12|pfx|keystore|jks)$"), "key/certificate file"),
    ("secret-file-ssh", re.compile(r"(?i)(?:^|/)id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?$"), "SSH key file"),
    ("secret-file-cred", re.compile(r"(?i)(?:^|/)(?:credentials\.json|service[-_]account[^/]*\.json|\.netrc|\.pypirc)$"), "credentials file"),
)
TEMPLATE_SUFFIXES = (".example", ".sample", ".template", ".dist")


def redact_hint(text: str) -> str:
    return f"{len(text)} chars"


def looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    if any(hint in lowered for hint in PLACEHOLDER_HINTS):
        return True
    if len(set(value)) <= 3:
        return True
    if "/" in value or value.startswith(("http", "~", ".")):
        return True
    return False


def load_allowlist(path: Path | None) -> list[tuple[str, str | None]]:
    if path is None or not path.is_file():
        return []
    entries: list[tuple[str, str | None]] = []
    for raw in path.read_bytes().decode("utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "::" in line:
            glob, rule = (part.strip() for part in line.split("::", 1))
            entries.append((glob, rule or None))
        else:
            entries.append((line, None))
    return entries


def allowed(relpath: str, rule_id: str, allowlist: list[tuple[str, str | None]]) -> bool:
    return any(C.glob_match(glob, relpath) and (rule is None or rule == rule_id) for glob, rule in allowlist)


def is_self_excluded(relpath: str) -> bool:
    return any(C.glob_match(g, relpath) for g in SELF_EXCLUDE_GLOBS)


def scan_file_name(relpath: str, report: C.Report, allowlist: list[tuple[str, str | None]]) -> None:
    lowered = relpath.lower()
    if lowered.endswith(TEMPLATE_SUFFIXES):
        return
    for rule_id, regex, description in SECRET_FILE_GLOBS:
        if regex.search(relpath) and not allowed(relpath, rule_id, allowlist):
            report.fail(rule_id, f"{description} should not be in the tree", relpath)


def scan_text(relpath: str, text: str, report: C.Report, allowlist: list[tuple[str, str | None]]) -> None:
    for number, line in enumerate(text.split("\n"), start=1):
        if C.SCAN_IGNORE_TOKEN in line.lower():
            continue
        for rule_id, regex, description in PATTERNS:
            if regex.search(line) and not allowed(relpath, rule_id, allowlist):
                report.fail(rule_id, f"{description} detected (value not shown)", relpath, number)
        for match in ASSIGNMENT_RE.finditer(line):
            value = match.group(1)
            if not looks_like_placeholder(value) and not allowed(relpath, "secret-assignment", allowlist):
                report.fail("secret-assignment", f"quoted secret-like assignment ({redact_hint(value)}, value not shown)", relpath, number)


def scan(root: Path, allowlist_path: str | None = None, use_git: bool = True, files: list[str] | None = None) -> C.Report:
    report = C.Report("scan_secrets")
    allowlist = load_allowlist(Path(allowlist_path) if allowlist_path else root / "scripts" / "secrets_allowlist.txt")
    names = files if files is not None else C.list_files(root, use_git=use_git)
    scanned = 0
    for relpath in names:
        if is_self_excluded(relpath):
            continue
        scan_file_name(relpath, report, allowlist)
        text = C.read_scan_text(root / relpath)
        if text is None:
            continue
        scanned += 1
        scan_text(relpath, text, report, allowlist)
    report.stats["files_scanned"] = scanned
    report.stats["rules"] = len(PATTERNS) + 1
    if not names:
        report.not_run("scan", "no files found to scan")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan the tree for credentials and secret-bearing files.")
    C.add_common_args(parser)
    parser.add_argument("--allowlist", default=None, help="allowlist file (default scripts/secrets_allowlist.txt)")
    parser.add_argument("--no-git", action="store_true", help="walk the directory instead of using git's file list")
    return parser


def main(argv: list[str] | None = None) -> int:
    C.setup_utf8()
    args = build_parser().parse_args(argv)
    root = C.resolve_root(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root.name}", file=sys.stderr)
        return C.EXIT_USAGE
    report = scan(root, args.allowlist, use_git=not args.no_git)
    return C.emit(report, args.json, args.strict, args.warnings_as_errors)


if __name__ == "__main__":
    sys.exit(main())

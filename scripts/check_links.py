"""Check that relative markdown links and ``agent-content/...`` path mentions resolve.

Usage: python scripts/check_links.py [--root DIR] [--paths PATH ...] [--json] [--strict] [--warnings-as-errors]

Scope (default): root *.md, docs/**/*.md (docs/en, docs/he, decisions, ...), agent-content/**/*.md (skills,
playbooks, techniques, references), templates/**/*.md, profiles/**/*.md. Generated host copies (.claude/, .agents/)
are not scanned. --paths replaces the default scope (files or directories relative to --root).
Rules:
  * [text](relative/path#anchor), ![img](path) and reference definitions '[id]: path' must exist (FAIL). Percent-escapes
    (Hebrew file names) are decoded. /absolute links are treated as repo-root relative. Links escaping the root FAIL.
  * http(s)/mailto/tel/data links are not fetched (no network); anchor-only and missing #anchors are WARN.
  * ``agent-content/...`` mentions in prose or `code` must exist (FAIL); paths containing <placeholders>, * globs,
    {braces} or an ellipsis are skipped. Fenced code blocks are skipped entirely (examples and trees), and so is
    any line containing the token ``link-check-ignore`` (e.g. <!-- link-check-ignore --> for deliberate dead examples).
No markdown files in scope -> NOT_RUN. Exit codes: 0 ok, 1 broken link, 2 usage, 3 not_run with --strict.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _avc_common as C  # noqa: E402

INLINE_LINK_RE = re.compile(r"\!?\[(?:[^\]\\]|\\.)*\]\((?:<([^>]+)>|([^)\s]+))(?:\s+(?:\"[^\"]*\"|'[^']*'))?\)")
REF_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s+(?:<([^>]+)>|(\S+))")
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
MENTION_RE = re.compile(r"(?<![\w./-])(agent-content/[^\s`\"'<>()\[\]|,;]+)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
SCHEME_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
EXPLICIT_ID_RE = re.compile(r"\{#([^}\s]+)\}|<a\s+(?:name|id)=[\"']([^\"']+)[\"']", re.IGNORECASE)
DEFAULT_GLOBS = ("*.md", "docs/**/*.md", "agent-content/**/*.md", "templates/**/*.md", "profiles/**/*.md")


def slugify(heading: str) -> str:
    text = re.sub(r"\{#[^}]*\}", "", heading).strip().lower()
    text = re.sub(r"[`*_~\[\]()]", "", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"\s", "-", text.strip())


def anchors_of(path: Path, cache: dict[Path, set[str]]) -> set[str]:
    if path in cache:
        return cache[path]
    found: set[str] = set()
    counts: dict[str, int] = {}
    inside = False
    try:
        lines = path.read_bytes().decode("utf-8-sig").split("\n")
    except (OSError, UnicodeDecodeError):
        cache[path] = found
        return found
    for line in lines:
        if FENCE_RE.match(line):
            inside = not inside
            continue
        if inside:
            continue
        for match in EXPLICIT_ID_RE.finditer(line):
            found.add((match.group(1) or match.group(2)).lower())
        heading = HEADING_RE.match(line)
        if heading:
            slug = slugify(heading.group(2))
            n = counts.get(slug, 0)
            counts[slug] = n + 1
            found.add(slug if n == 0 else f"{slug}-{n}")
    cache[path] = found
    return found


def md_files(root: Path, paths: list[str] | None) -> list[Path]:
    files: set[Path] = set()
    if paths:
        for item in paths:
            target = (root / item).resolve()
            if target.is_file():
                files.add(target)
            elif target.is_dir():
                files.update(p for p in target.rglob("*.md") if p.is_file())
    else:
        for pattern in DEFAULT_GLOBS:
            files.update(p.resolve() for p in root.glob(pattern) if p.is_file())
    skip = (".git", ".claude", ".agents", "node_modules", ".venv", "__pycache__")
    out = []
    for path in files:
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            continue
        if not any(part in skip for part in parts):
            out.append(path)
    return sorted(out)


def placeholder(ref: str) -> bool:
    return any(ch in ref for ch in "<>{}*|…") or "..." in ref


def check_file(root: Path, path: Path, report: C.Report, cache: dict[Path, set[str]]) -> tuple[int, int]:
    rel = path.relative_to(root).as_posix()
    try:
        lines = path.read_bytes().decode("utf-8-sig").split("\n")
    except (OSError, UnicodeDecodeError):
        report.fail("link-unreadable", "file is not readable UTF-8", rel)
        return 0, 0
    links = mentions = 0
    inside = False
    for number, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            inside = not inside
            continue
        if inside or "link-check-ignore" in line:
            continue
        no_code = CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), line)
        targets = [m.group(1) or m.group(2) for m in INLINE_LINK_RE.finditer(no_code)]
        ref_def = REF_DEF_RE.match(no_code)
        if ref_def:
            targets.append(ref_def.group(1) or ref_def.group(2))
        for target in targets:
            if not target or SCHEME_RE.match(target):
                continue
            links += 1
            raw, _, fragment = target.partition("#")
            raw = raw.split("?", 1)[0]
            if not raw:
                if fragment and fragment.lower() not in anchors_of(path, cache) and unquote(fragment).lower() not in anchors_of(path, cache):
                    report.warn("anchor-missing", f"anchor '#{fragment}' not found in this file", rel, number)
                continue
            decoded = unquote(raw)
            dest = (root / decoded.lstrip("/")) if decoded.startswith("/") else (path.parent / decoded)
            try:
                resolved = dest.resolve()
            except OSError:
                report.fail("link-invalid", f"cannot resolve '{decoded}'", rel, number)
                continue
            if not resolved.is_relative_to(root):
                report.fail("link-escapes-root", f"'{decoded}' points outside the repository", rel, number)
            elif not resolved.exists():
                report.fail("link-broken", f"'{decoded}' does not exist", rel, number)
            elif fragment and resolved.suffix.lower() == ".md" and resolved.is_file():
                known = anchors_of(resolved, cache)
                if fragment.lower() not in known and unquote(fragment).lower() not in known:
                    report.warn("anchor-missing", f"anchor '#{fragment}' not found in {resolved.name}", rel, number)
        for match in MENTION_RE.finditer(line):
            raw = match.group(1)
            following = line[match.end(): match.end() + 1]
            if placeholder(raw) or following in ("<", "{", "[", "…"):
                continue  # a template such as agent-content/skills/<name>/..., a glob or an ellipsis
            ref = raw.rstrip(".:!?…")
            mentions += 1
            if not (root / ref).exists():
                report.fail("mention-broken", f"path mention '{ref}' does not exist", rel, number)
    return links, mentions


def run(root: Path, paths: list[str] | None = None) -> C.Report:
    report = C.Report("check_links")
    files = md_files(root, paths)
    if not files:
        report.not_run("links", "no markdown files in scope")
        return report
    cache: dict[Path, set[str]] = {}
    total_links = total_mentions = 0
    for path in files:
        links, mentions = check_file(root, path, report, cache)
        total_links += links
        total_mentions += mentions
    report.stats.update({"files": len(files), "links": total_links, "mentions": total_mentions})
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check relative markdown links and agent-content path mentions.")
    C.add_common_args(parser)
    parser.add_argument("--paths", nargs="+", default=None, help="files or directories (relative to --root) instead of the default scope")
    return parser


def main(argv: list[str] | None = None) -> int:
    C.setup_utf8()
    args = build_parser().parse_args(argv)
    root = C.resolve_root(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root.name}", file=sys.stderr)
        return C.EXIT_USAGE
    report = run(root, args.paths)
    return C.emit(report, args.json, args.strict, args.warnings_as_errors)


if __name__ == "__main__":
    sys.exit(main())

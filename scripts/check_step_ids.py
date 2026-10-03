"""Check that docs/en and docs/he carry identical step ids, in the same order.

Usage: python scripts/check_step_ids.py [--root DIR] [--en docs/en] [--he docs/he] [--json] [--strict] [--warnings-as-errors]

Step-id convention (also documented in scripts/README.md):
  * A step is marked by an HTML comment on its own line:      <!-- step: install-01 -->
    or by an explicit heading id attribute:                   ## Install Python {#install-01}
  * Ids are lowercase kebab-case, recommended shape <topic>-NN (install-01, first-output-03); unique per file.
  * The same relative file name exists in docs/en and docs/he and lists the same ids in the same order; only the
    prose is translated. Markers inside fenced code blocks are ignored (they are examples).
FAIL: invalid id, duplicate id, id set or order differs between EN and HE, a page that exists in only one language.
WARN: a page pair without any step id, a HE page that contains no Hebrew letters.
Missing docs/en or docs/he (or no pages) -> NOT_RUN. Exit codes: 0 ok, 1 mismatch, 2 usage, 3 not_run with --strict.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _avc_common as C  # noqa: E402

STEP_COMMENT_RE = re.compile(r"<!--\s*step:\s*([^\s>]+?)\s*-->")
HEADING_ID_RE = re.compile(r"^#{1,6}\s+.*\{#([^}\s]+)\}\s*$")
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def extract_ids(text: str) -> list[tuple[str, int]]:
    ids: list[tuple[str, int]] = []
    inside = False
    for number, line in enumerate(text.replace("\r\n", "\n").split("\n"), start=1):
        if FENCE_RE.match(line):
            inside = not inside
            continue
        if inside:
            continue
        for match in STEP_COMMENT_RE.finditer(line):
            ids.append((match.group(1), number))
        heading = HEADING_ID_RE.match(line)
        if heading:
            ids.append((heading.group(1), number))
    return ids


def pages(base: Path) -> dict[str, Path]:
    return {p.relative_to(base).as_posix(): p for p in sorted(base.rglob("*.md")) if p.is_file()}


def run(root: Path, en: str = "docs/en", he: str = "docs/he") -> C.Report:
    report = C.Report("check_step_ids")
    en_dir, he_dir = root / en, root / he
    if not en_dir.is_dir() or not he_dir.is_dir():
        missing = [name for name, d in ((en, en_dir), (he, he_dir)) if not d.is_dir()]
        report.not_run("step-ids", f"{' and '.join(missing)} not found; nothing to compare")
        return report
    en_pages, he_pages = pages(en_dir), pages(he_dir)
    if not en_pages and not he_pages:
        report.not_run("step-ids", "no markdown pages in docs/en or docs/he")
        return report
    compared = total_ids = 0
    for name in sorted(set(en_pages) | set(he_pages)):
        if name not in he_pages:
            report.fail("step-page-missing-he", "page exists in docs/en but has no docs/he counterpart", f"{en}/{name}")
            continue
        if name not in en_pages:
            report.fail("step-page-missing-en", "page exists in docs/he but has no docs/en counterpart", f"{he}/{name}")
            continue
        texts = {}
        id_lists = {}
        for lang, path, label in (("en", en_pages[name], f"{en}/{name}"), ("he", he_pages[name], f"{he}/{name}")):
            try:
                texts[lang] = path.read_bytes().decode("utf-8-sig")
            except (OSError, UnicodeDecodeError):
                report.fail("step-unreadable", "page is not readable UTF-8", label)
                texts[lang] = ""
            found = extract_ids(texts[lang])
            id_lists[lang] = [i for i, _ in found]
            seen: set[str] = set()
            for step_id, number in found:
                if not ID_RE.match(step_id):
                    report.fail("step-id-invalid", f"id '{step_id}' is not lowercase kebab-case", label, number)
                if step_id in seen:
                    report.fail("step-id-duplicate", f"id '{step_id}' appears more than once", label, number)
                seen.add(step_id)
        compared += 1
        total_ids += len(id_lists["en"])
        if not id_lists["en"] and not id_lists["he"]:
            report.warn("step-none", "page pair has no step ids (add <!-- step: topic-01 --> if it contains steps)", f"{en}/{name}")
        elif id_lists["en"] != id_lists["he"]:
            only_en = sorted(set(id_lists["en"]) - set(id_lists["he"]))
            only_he = sorted(set(id_lists["he"]) - set(id_lists["en"]))
            if only_en or only_he:
                report.fail("step-ids-differ", f"EN-only: {only_en or '-'}; HE-only: {only_he or '-'}", f"{en}/{name}")
            else:
                report.fail("step-order-differs", f"same ids but different order: EN {id_lists['en']} vs HE {id_lists['he']}", f"{en}/{name}")
        if texts.get("he") and not C.has_hebrew(texts["he"]):
            report.warn("step-he-no-hebrew", "Hebrew page contains no Hebrew letters (untranslated copy?)", f"{he}/{name}")
        if texts.get("he") and C.MOJIBAKE_RE.search(texts["he"]):
            report.fail("step-he-mojibake", "Hebrew page contains mis-decoded text", f"{he}/{name}")
    report.stats.update({"page_pairs": compared, "step_ids": total_ids})
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check docs/en vs docs/he step-id parity.")
    C.add_common_args(parser)
    parser.add_argument("--en", default="docs/en", help="English docs folder relative to --root")
    parser.add_argument("--he", default="docs/he", help="Hebrew docs folder relative to --root")
    return parser


def main(argv: list[str] | None = None) -> int:
    C.setup_utf8()
    args = build_parser().parse_args(argv)
    root = C.resolve_root(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root.name}", file=sys.stderr)
        return C.EXIT_USAGE
    report = run(root, args.en, args.he)
    return C.emit(report, args.json, args.strict, args.warnings_as_errors)


if __name__ == "__main__":
    sys.exit(main())

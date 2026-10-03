#!/usr/bin/env python3
"""Apply a batch of text patches with unique-anchor asserts (patch discipline).

Usage:
  python apply_patch.py PATCH.json [--dry-run] [--backup-dir _work]
  python apply_patch.py --self-check

PATCH.json (written to a FILE with the editor tool, never inline in a shell heredoc: Hebrew and quotes
break heredocs):
  {"file": "hf/index.html",
   "strip_hf_ids": true,
   "edits": [{"anchor": "exact old text", "replace": "new text", "expect": 1}, ...]}

What it does: reads the file byte-faithfully (line endings kept; \\n in anchors is adapted to CRLF files),
optionally strips Studio's `data-hf-id="..."` attributes, asserts every anchor occurs exactly `expect` times
(default 1) and that anchors do not overlap, and only then writes: backup first (backup-dir/<name>_pre_<time><ext>),
atomic replace, re-read and verify. All-or-nothing: if any assert fails nothing is written and every
failing anchor is reported. A file that still contains `data-hf-id` while strip_hf_ids is false is refused
(close Studio and strip first: it adds ids and breaks anchors).

Exit codes: 0 applied (or dry-run ok), 1 an assert failed (nothing written), 2 bad patch file / unreadable.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HF_ID_RE = re.compile(r'\sdata-hf-id="[^"]*"')


def load_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes().decode("utf-8")
    return raw, ("\r\n" if "\r\n" in raw else "\n")


def plan(text: str, nl: str, spec: dict) -> tuple[list[tuple[int, int, str]], list[dict], str, int]:
    """Return (replacements, failures, text_after_strip, stripped_count)."""
    failures: list[dict] = []
    stripped = 0
    if spec.get("strip_hf_ids"):
        text, stripped = HF_ID_RE.subn("", text)
    elif "data-hf-id" in text:
        failures.append({"anchor": "(file)", "problem": "hf_ids_present",
                         "detail": "file contains data-hf-id: close Studio and set strip_hf_ids true"})
    edits = spec.get("edits") or []
    if not edits:
        failures.append({"anchor": "(patch)", "problem": "no_edits", "detail": "patch has no edits"})
    spans: list[tuple[int, int, str]] = []
    for i, e in enumerate(edits):
        anchor, repl = e.get("anchor", ""), e.get("replace")
        label = (anchor[:40] + "...") if len(anchor) > 40 else anchor
        if not anchor or repl is None:
            failures.append({"anchor": label or f"edit {i}", "problem": "bad_edit", "detail": "anchor and replace are required"})
            continue
        if nl == "\r\n":
            anchor, repl = anchor.replace("\r\n", "\n").replace("\n", "\r\n"), repl.replace("\r\n", "\n").replace("\n", "\r\n")
        expect = int(e.get("expect", 1))
        found = [m.start() for m in re.finditer(re.escape(anchor), text)]
        if len(found) != expect:
            failures.append({"anchor": label, "problem": "count_mismatch", "detail": f"found {len(found)}, expected {expect}"})
            continue
        for s in found:
            spans.append((s, s + len(anchor), repl))
    spans.sort()
    for (a0, a1, _), (b0, b1, _) in zip(spans, spans[1:]):
        if b0 < a1:
            failures.append({"anchor": "(patch)", "problem": "overlap", "detail": f"two edits overlap at offsets {b0}-{a1}"})
    return spans, failures, text, stripped


def apply(patch_path: Path, dry_run: bool = False, backup_dir: Path | None = None) -> tuple[int, dict]:
    try:
        spec = json.loads(patch_path.read_text(encoding="utf-8"))
        target = Path(spec["file"])
        if not target.is_absolute():
            target = (patch_path.parent / target) if not target.exists() else target
        text, nl = load_text(target)
    except (OSError, ValueError, KeyError) as exc:
        return 2, {"status": "not_run", "reason": f"{type(exc).__name__}: {exc}"}
    spans, failures, text2, stripped = plan(text, nl, spec)
    if failures:
        return 1, {"status": "failed", "written": False, "failures": failures}
    out, pos = [], 0
    for a0, a1, repl in spans:
        out.append(text2[pos:a0])
        out.append(repl)
        pos = a1
    out.append(text2[pos:])
    new = "".join(out)
    res = {"status": "ok", "file": str(target), "edits": len(spans), "hf_ids_stripped": stripped, "dry_run": dry_run,
           "written": False}
    if dry_run:
        return 0, res
    bdir = backup_dir or target.parent
    bdir.mkdir(parents=True, exist_ok=True)
    backup = bdir / f"{target.stem}_pre_{time.strftime('%Y%m%d_%H%M%S')}{target.suffix}"
    shutil.copy2(target, backup)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=".patch_", suffix=target.suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(new.encode("utf-8"))
        os.replace(tmp, target)
    except OSError as exc:
        if os.path.exists(tmp):
            os.unlink(tmp)
        return 2, {"status": "not_run", "reason": f"write failed: {exc}", "backup": str(backup)}
    again, _ = load_text(target)
    bad = [e["replace"][:40] for e in (spec["edits"]) if e["replace"].replace("\n", nl) not in again]
    if again != new or bad:
        return 1, {"status": "failed", "written": True, "backup": str(backup), "failures": [{"problem": "reread_mismatch", "detail": bad}]}
    res.update(written=True, backup=str(backup))
    return 0, res


def _self_check() -> int:
    fails: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        html = '<div data-hf-id="a1" class="x">שלום</div>\n<p id="one">A</p>\n<p id="two">A</p>\n'
        f = d / "index.html"
        f.write_bytes(html.encode("utf-8"))

        def write_patch(edits, strip=True, name="p.json", file="index.html"):
            (d / name).write_text(json.dumps({"file": file, "strip_hf_ids": strip, "edits": edits}, ensure_ascii=False), encoding="utf-8")
            return d / name

        code, r = apply(write_patch([{"anchor": ">A<", "replace": ">B<"}]))
        if code != 1 or r["failures"][0]["problem"] != "count_mismatch" or f.read_bytes().decode("utf-8") != html:
            fails.append("non-unique anchor must fail and write nothing")
        code, r = apply(write_patch([{"anchor": 'id="one">A<', "replace": 'id="one">B<'}], strip=False))
        if code != 1 or r["failures"][0]["problem"] != "hf_ids_present":
            fails.append("hf ids present without strip must be refused")
        code, r = apply(write_patch([{"anchor": 'id="one">A<', "replace": 'id="one">B<'},
                                     {"anchor": "שלום", "replace": "שלום עולם"}]), backup_dir=d / "_work")
        out = f.read_bytes().decode("utf-8")
        if code != 0 or "data-hf-id" in out or 'id="one">B<' not in out or "שלום עולם" not in out or r["hf_ids_stripped"] != 1:
            fails.append(f"good patch failed: {code} {r}")
        if not list((d / "_work").glob("index_pre_*.html")):
            fails.append("backup missing")
        code, r = apply(write_patch([{"anchor": 'id="two">A<', "replace": 'id="two">C<'}]), dry_run=True)
        if code != 0 or 'id="two">C<' in f.read_bytes().decode("utf-8"):
            fails.append("dry run must not write")
        code, r = apply(write_patch([{"anchor": "<p id", "replace": "<q id", "expect": 2}, {"anchor": '<p id="one">B', "replace": "x"}]))
        if code != 1 or not any(x["problem"] == "overlap" for x in r["failures"]):
            fails.append("overlapping anchors must fail")
        crlf = d / "crlf.html"
        crlf.write_bytes(b"<a>\r\n  <b>1</b>\r\n</a>\r\n")
        code, r = apply(write_patch([{"anchor": "<a>\n  <b>1</b>", "replace": "<a>\n  <b>2</b>"}], name="c.json", file="crlf.html"))
        if code != 0 or crlf.read_bytes() != b"<a>\r\n  <b>2</b>\r\n</a>\r\n":
            fails.append(f"CRLF file must keep CRLF: {code} {r}")
        code, r = apply(d / "missing.json")
        if code != 2:
            fails.append("missing patch file must exit 2")
        code, r = apply(write_patch([]))
        if code != 1 or r["failures"][0]["problem"] != "no_edits":
            fails.append("empty patch must fail")
    for x in fails:
        print("FAIL:", x)
    print("self-check:", "FAILED" if fails else "ok")
    return 1 if fails else 0


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return _self_check()
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    bdir = None
    if "--backup-dir" in argv:
        bdir = Path(argv[argv.index("--backup-dir") + 1])
        args = [a for a in args if a != str(argv[argv.index("--backup-dir") + 1])]
    code, res = apply(Path(args[0]), "--dry-run" in argv, bdir)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

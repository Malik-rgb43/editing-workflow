#!/usr/bin/env python3
"""translation_check.py - check a translated caption file before it is placed, and write its timed words.

A translation is checked line by line against its source: every target line exists and keeps its source times,
every glossary term (names, brands, product terms) is kept or written the client's way, every number survives,
every claim / offer / legal line was confirmed by the user after translation, and the whole text was approved.
It also reports the reading speed of each target line and whether the text direction changes (RTL <-> LTR),
which means the layout must be mirrored. Nothing is translated here; the agent translates, the user approves.

Input (`_work/translation/<target>.json`, schema avc.translation/1):
  {"schema": "avc.translation/1", "source_language": "he", "target_language": "en",
   "approved": {"date": "YYYY-MM-DD", "quote": "<the user's words>"},          (null until the user approves)
   "glossary": [{"term": "Clinic Plus", "keep": true}, {"term": "<name>", "render": "<client's spelling>"}],
   "lines": [{"id": "L1", "start": 0.0, "end": 2.4, "source": "...", "target": "...",
              "kind": "speech|claim|offer|legal", "confirmed": {"date": "...", "quote": "..."},
              "numbers_ok": "<reason, only when a number legitimately changes form>"}]}

Usage:
  python translation_check.py <translation.json> [--draft] [--max-cps 17] [--json]
                              [--words-out hf/data/words_<target>.json]
  python translation_check.py --self-check

--draft      before the user has seen it: approval and claim confirmations are reported as warnings.
--words-out  (refused with --draft or on FAIL) writes avc.words/1 for the target: each line's words spread over
             the line's own time span by character length, so `tools/hf_blocks.py caption-words` and
             `tools/captions_export.py` work unchanged. Word times are spread, not heard: say so.
--max-cps    characters per second above which a line is flagged as too fast to read (house preset v1: 17).
Exit: 0 PASS (warnings allowed), 1 FAIL, 2 unreadable input or usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

SCHEMA = "avc.translation/1"
KINDS = {"speech", "claim", "offer", "legal"}
CHECKED_KINDS = {"claim", "offer", "legal"}
RTL_RE = re.compile(r"[֐-ࣿיִ-﷿ﹰ-﻿]")
LTR_RE = re.compile(r"[A-Za-zÀ-ɏͰ-ӿ]")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
MONEY_RE = re.compile(r"[%$€£₪¥]")
DEFAULT_CPS = 17.0


def numbers(text: str) -> list[str]:
    """Digit groups with the thousands/decimal marks removed, sorted: '3,990' and '3.990' compare equal."""
    return sorted(re.sub(r"[.,]", "", m) for m in NUM_RE.findall(text or ""))


def is_rtl(text: str) -> bool | None:
    r, l = len(RTL_RE.findall(text or "")), len(LTR_RE.findall(text or ""))
    if r + l == 0:
        return None
    return r / (r + l) > 0.5


def _has_term(text: str, term: str) -> bool:
    if LTR_RE.search(term) and not RTL_RE.search(term):
        return term.casefold() in (text or "").casefold()
    return term in (text or "")


def check(doc: dict, draft: bool = False, max_cps: float = DEFAULT_CPS) -> dict:
    items: list[dict] = []

    def add(sev, code, msg, line=None):
        items.append({"severity": sev, "code": code, "line": line, "message": msg})

    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        add("fail", "T00_SCHEMA", f"schema must be {SCHEMA}")
        return _result(items, doc if isinstance(doc, dict) else {}, [])
    for k in ("source_language", "target_language"):
        if not str(doc.get(k) or "").strip():
            add("fail", "T00_SCHEMA", f"{k} missing (a language code, never assumed)")
    lines = doc.get("lines")
    if not isinstance(lines, list) or not lines:
        add("fail", "T00_SCHEMA", "lines[] missing or empty")
        return _result(items, doc, [])
    glossary = doc.get("glossary")
    if not isinstance(glossary, list):
        add("fail", "T03_GLOSSARY", "glossary[] missing: list the names, brands and product terms (an empty list says there are none)")
        glossary = []

    appr = doc.get("approved")
    if not (isinstance(appr, dict) and str(appr.get("quote") or "").strip() and str(appr.get("date") or "").strip()):
        add("warn" if draft else "fail", "T06_NOT_APPROVED", "the translated text was not approved by the user (approved.date + approved.quote): nothing is placed before that")

    prev_end, seen = None, set()
    report_lines = []
    for i, ln in enumerate(lines):
        lid = str(ln.get("id") or f"#{i + 1}") if isinstance(ln, dict) else f"#{i + 1}"
        if not isinstance(ln, dict):
            add("fail", "T00_SCHEMA", "a line is not an object", lid)
            continue
        if lid in seen:
            add("fail", "T00_SCHEMA", "duplicate line id", lid)
        seen.add(lid)
        src, tgt = str(ln.get("source") or ""), str(ln.get("target") or "")
        st, en = ln.get("start"), ln.get("end")
        kind = ln.get("kind", "speech")
        if kind not in KINDS:
            add("fail", "T00_SCHEMA", f"kind must be one of {sorted(KINDS)}", lid)
        if not tgt.strip():
            add("fail", "T01_EMPTY_TARGET", "no target text", lid)
        if not src.strip():
            add("fail", "T01_EMPTY_SOURCE", "no source text: translate from the proofread transcript", lid)
        if not (isinstance(st, (int, float)) and isinstance(en, (int, float))) or isinstance(st, bool) or isinstance(en, bool) or st < 0 or en <= st:
            add("fail", "T02_TIMES", "start/end missing, negative or end <= start", lid)
            dur = None
        else:
            dur = en - st
            if prev_end is not None and st < prev_end - 1e-6:
                add("fail", "T02_TIMES", f"starts at {st} before the previous line ends ({prev_end}): lines never overlap", lid)
            prev_end = en
        for g in glossary:
            term = str((g or {}).get("term") or "")
            if not term or not _has_term(src, term):
                continue
            want = str(g.get("render") or term)
            if not _has_term(tgt, want):
                add("fail", "T03_GLOSSARY", f"glossary term {term!r} must appear as {want!r} in the target", lid)
        if numbers(src) != numbers(tgt) and not str(ln.get("numbers_ok") or "").strip():
            add("fail", "T04_NUMBERS", f"numbers differ: source {numbers(src)} vs target {numbers(tgt)} (a price, percent or date changed?)", lid)
        conf = ln.get("confirmed")
        confirmed = isinstance(conf, dict) and str(conf.get("quote") or "").strip()
        if kind in CHECKED_KINDS and not confirmed:
            add("warn" if draft else "fail", "T05_CLAIM_NOT_CONFIRMED", f"{kind} line: the user confirms the translated wording against the source", lid)
        elif kind == "speech" and (NUM_RE.search(src) or MONEY_RE.search(src)):
            add("warn", "T05_NUMBER_IN_SPEECH", "a number, price or percent in a speech line: mark it claim or offer if it is one", lid)
        cps = round(len(tgt.strip()) / dur, 1) if dur else None
        if cps is not None and cps > max_cps:
            add("warn", "T07_READING_SPEED", f"{cps} characters/s > {max_cps}: shorten the text (never stretch the time over the next line)", lid)
        report_lines.append({"id": lid, "cps": cps, "kind": kind})
    return _result(items, doc, report_lines)


def _result(items, doc, report_lines):
    src_rtl = is_rtl(" ".join(str(l.get("source", "")) for l in doc.get("lines", []) if isinstance(l, dict))) if doc else None
    tgt_rtl = is_rtl(" ".join(str(l.get("target", "")) for l in doc.get("lines", []) if isinstance(l, dict))) if doc else None
    change = src_rtl is not None and tgt_rtl is not None and src_rtl != tgt_rtl
    fails = [i for i in items if i["severity"] == "fail"]
    return {
        "tool": "translation_check", "status": "FAIL" if fails else "PASS",
        "source_language": doc.get("source_language") if doc else None, "target_language": doc.get("target_language") if doc else None,
        "direction": {"source_rtl": src_rtl, "target_rtl": tgt_rtl, "changes": change,
                      "mirror": ["text alignment", "caption rail side", "multi-card reading order", "arrows, progress bars and timeline graphics",
                                 "lower-third and logo side (if the brand allows)", "footage is never flipped"] if change else []},
        "counts": {"fail": len(fails), "warn": len([i for i in items if i["severity"] == "warn"])},
        "lines": report_lines, "findings": items,
        "limits": ["checks presence, numbers and approvals; it cannot judge whether the meaning is right: a reader of the target language does"],
    }


def spread_words(doc: dict) -> dict:
    """Target words timed inside each line's own span, by character length (a word = its characters + 1 space)."""
    out = []
    for ln in doc["lines"]:
        toks = str(ln["target"]).split()
        if not toks:
            continue
        st, en = float(ln["start"]), float(ln["end"])
        weights = [len(t) + 1 for t in toks]
        total, t = float(sum(weights)), st
        for tok, w in zip(toks, weights):
            nxt = t + (en - st) * w / total
            out.append({"w": tok, "start": round(t, 3), "end": round(nxt, 3), "prob": None})
            t = nxt
        out[-1]["end"] = round(en, 3)
    return {"schema": "avc.words/1", "language": doc["target_language"],
            "model": f"translation:{doc['source_language']}->{doc['target_language']}",
            "timing": "spread over each source line's time span by character length (not heard)", "words": out}


def self_check() -> int:
    ok, fails = 0, []

    def expect(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(label)

    def codes(r):
        return {i["code"] for i in r["findings"]}

    base = {"schema": SCHEMA, "source_language": "he", "target_language": "en",
            "approved": {"date": "2026-10-08", "quote": "מאושר"},
            "glossary": [{"term": "Clinic Plus", "keep": True}, {"term": "אבי כהן", "render": "Avi Cohen"}],
            "lines": [{"id": "L1", "start": 0.0, "end": 2.4, "source": "אני אבי כהן מ-Clinic Plus", "target": "I'm Avi Cohen from Clinic Plus"},
                      {"id": "L2", "start": 2.5, "end": 5.0, "source": "עד 50% הנחה עד 18:30", "target": "Up to 50% off until 18:30",
                       "kind": "offer", "confirmed": {"date": "2026-10-08", "quote": "yes, up to 50%"}}]}
    clone = lambda: json.loads(json.dumps(base, ensure_ascii=False))
    r = check(clone())
    expect("valid approved translation passes", r["status"] == "PASS")
    expect("he -> en is a direction change with a mirror list", r["direction"]["changes"] and r["direction"]["mirror"])
    d = clone(); d["lines"][0]["target"] = "I'm Avi Kohen from Klinik Plus"
    expect("glossary term changed -> T03", "T03_GLOSSARY" in codes(check(d)))
    d = clone(); d["lines"][1]["target"] = "50% off until 18:30"; d["lines"][1]["source"] = "50% הנחה עד 18:30"
    expect("same numbers pass", "T04_NUMBERS" not in codes(check(d)))
    d = clone(); d["lines"][1]["target"] = "Up to 15% off until 18:30"
    expect("a percent changed -> T04", "T04_NUMBERS" in codes(check(d)))
    d = clone(); d["lines"][1].pop("confirmed")
    expect("offer not confirmed -> FAIL T05", check(d)["status"] == "FAIL" and "T05_CLAIM_NOT_CONFIRMED" in codes(check(d)))
    expect("offer not confirmed in --draft -> warning only", check(d, draft=True)["status"] == "PASS")
    d = clone(); d["approved"] = None
    expect("not approved -> FAIL T06", "T06_NOT_APPROVED" in codes(check(d)) and check(d)["status"] == "FAIL")
    d = clone(); d["lines"][1]["start"] = 2.0
    expect("overlapping lines -> T02", "T02_TIMES" in codes(check(d)))
    d = clone(); d["lines"][0]["target"] = "x" * 80
    expect("too fast to read -> T07 warning", "T07_READING_SPEED" in codes(check(d)))
    d = clone(); d.pop("glossary")
    expect("no glossary -> FAIL", "T03_GLOSSARY" in codes(check(d)))
    d = clone(); d["target_language"] = "ar"; d["source_language"] = "en"
    for ln in d["lines"]:
        ln["source"], ln["target"] = ln["target"], "مرحبا أنا من عيادة Clinic Plus خصم حتى 50% حتى 18:30"
    d["glossary"] = [{"term": "Clinic Plus", "keep": True}]
    expect("en -> ar also changes direction", check(d)["direction"]["changes"])
    w = spread_words(clone())
    words = w["words"]
    expect("spread words stay inside each line and keep order",
           words[0]["start"] == 0.0 and abs(words[5]["end"] - 2.4) < 1e-6 and words[6]["start"] == 2.5 and words[-1]["end"] == 5.0
           and all(a["end"] <= b["start"] + 1e-6 for a, b in zip(words, words[1:])))
    expect("words file is avc.words/1 in the target language", w["schema"] == "avc.words/1" and w["language"] == "en")
    with tempfile.TemporaryDirectory(prefix="tr בדיקה ") as td:
        p = Path(td) / "en.json"
        p.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
        out = Path(td) / "words_en.json"
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            wrote = main([str(p), "--words-out", str(out)])
            refused = main([str(p), "--draft", "--words-out", str(out)])
        expect("CLI writes words on PASS", wrote == 0 and out.is_file())
        expect("CLI refuses --words-out with --draft", refused == 2)
    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": ok + len(fails), "failed": fails}))
    return 0 if not fails else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Check a translated caption file before it is placed (see the module docstring).")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--max-cps", type=float, default=DEFAULT_CPS)
    ap.add_argument("--words-out")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.path:
        ap.print_help()
        return 2
    if a.words_out and a.draft:
        print("refused: --words-out needs an approved translation (drop --draft)", file=sys.stderr)
        return 2
    try:
        doc = json.loads(Path(a.path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        print(f"unreadable: {e}", file=sys.stderr)
        return 2
    rep = check(doc, a.draft, a.max_cps)
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(f"{rep['status']}  {rep['source_language']} -> {rep['target_language']}  ({rep['counts']['fail']} fail, {rep['counts']['warn']} warn)")
        for f in rep["findings"]:
            print(f"  [{f['severity']}] {f['code']}" + (f" {f['line']}" if f.get("line") else "") + f": {f['message']}")
        if rep["direction"]["changes"]:
            print("  direction changes: mirror " + "; ".join(rep["direction"]["mirror"]))
    if rep["status"] != "PASS":
        return 1
    if a.words_out:
        out = Path(a.words_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(spread_words(doc), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"  words -> {out} (times spread over each line, not heard)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

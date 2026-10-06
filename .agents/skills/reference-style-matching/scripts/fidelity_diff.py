#!/usr/bin/env python3
"""fidelity_diff.py - the fidelity ledger: compare a draft's measurements with the Style DNA card, row by row.

On each round's full (draft) render, re-measure the draft with video-analysis (same tool, same detail tier) into
<project>/_work/analysis/<draft-id>/ and run this.
Each DNA row has its own tolerance (pct with an absolute floor, abs, exact, categorical, informational)
instead of one blanket +/-20 %, or a written `deviate` reason. A row that cannot be measured on the draft
is `not_measured`, never ok.

Usage:
  python fidelity_diff.py <style_dna.json> --draft <analysis_dir_of_the_draft>
                          [--manual draft_values.json] [--out fidelity.md] [--json]
  python fidelity_diff.py --self-check

  --draft   analysis folder of the DRAFT (measurements.json + audio.json from video-analysis)
  --manual  {"R04": 112, "R06": "#F2C230"} values for rows without a `source_key` (px_measure.py output,
            zoom reads); every manual value must be listed here, nothing is guessed
  --out     write the ledger table as Markdown (put it in hf/QA.md or _work/style/<ref-id>/fidelity.md)

Verdicts per row: ok | flag (outside tolerance) | deviate (declared, still reported) | info | not_measured.
Exit codes: 0 PASS (no flag, no not_measured) | 1 FAIL (>= 1 flag) | 2 INSUFFICIENT_EVIDENCE (>= 1 not_measured,
or the draft analysis is missing). Stdlib only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

VERSION = "0.1.0"


def _no_const(n):
    raise ValueError("non-standard JSON constant: " + n)


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"), parse_constant=_no_const)


def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def resolve(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def judge(row, draft):
    """Returns (verdict, delta, delta_pct, allowed)."""
    tol = row.get("tolerance") or {}
    mode = tol.get("mode")
    ref = row.get("value")
    if draft is None:
        return "not_measured", None, None, None
    if mode == "informational":
        return "info", None, None, None
    delta = delta_pct = allowed = None
    if mode == "pct" and isnum(ref) and isnum(draft):
        allowed = max(abs(ref) * tol.get("value", 0) / 100.0, tol.get("abs_floor", 0) or 0)
        delta = draft - ref
        delta_pct = (delta / ref * 100.0) if ref else None
        ok = abs(delta) <= allowed + 1e-12
    elif mode == "abs" and isnum(ref) and isnum(draft):
        allowed = tol.get("value", 0)
        delta = draft - ref
        ok = abs(delta) <= allowed + 1e-12
    elif mode == "exact":
        ok = str(draft).strip().lower() == str(ref).strip().lower()
    elif mode == "categorical":
        allowed_set = tol.get("allowed") or [ref]
        ok = draft in allowed_set or str(draft).strip().lower() in [str(a).strip().lower() for a in allowed_set]
    else:
        return "not_measured", None, None, None  # unknown mode or type mismatch: never ok
    if row.get("deviate"):
        return "deviate", delta, delta_pct, allowed
    return ("ok" if ok else "flag"), delta, delta_pct, allowed


def run(card_path: Path, draft_dir: Path, manual):
    card = load(card_path)
    meas = audio = None
    try:
        meas = load(draft_dir / "measurements.json")
    except (OSError, ValueError):
        pass
    try:
        audio = load(draft_dir / "audio.json")
    except (OSError, ValueError):
        pass
    base = {"measurements": meas, "audio": audio}
    ledger, counts = [], {"ok": 0, "flag": 0, "deviate": 0, "info": 0, "not_measured": 0}
    for row in card.get("rows", []):
        if row.get("value") is None:
            continue  # dimension marked n/a on the card
        rid = row["id"]
        draft = None
        how = None
        sk = row.get("source_key")
        if sk:
            src, _, path = sk.partition(":")
            if base.get(src) is not None:
                draft = resolve(base[src], path)
                how = f"draft {sk}"
        if draft is None and rid in manual:
            draft, how = manual[rid], "manual (px_measure / zoom read)"
        verdict, delta, dpct, allowed = judge(row, draft)
        counts[verdict] += 1
        ledger.append({"id": rid, "dimension": row.get("dimension"), "metric": row.get("metric"), "unit": row.get("unit"), "reference": row.get("value"),
                       "draft": draft, "how": how, "delta": delta, "delta_pct": None if dpct is None else round(dpct, 1),
                       "allowed": allowed, "tolerance": row.get("tolerance"), "deviate": row.get("deviate"), "verdict": verdict,
                       "fix": None if verdict in ("ok", "info", "deviate") else ("measure it on the draft (zoom/px_measure) and add it to --manual" if verdict == "not_measured" else "bring the draft inside tolerance or record `deviate` with a reason and the user's OK")})
    if draft_dir and meas is None:
        status = "INSUFFICIENT_EVIDENCE"
    elif counts["flag"]:
        status = "FAIL"
    elif counts["not_measured"] or not ledger:
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "PASS"
    out = {"tool": "fidelity_diff", "version": VERSION, "status": status, "counts": counts, "rows": ledger,
           "limits": ["a PASS means the measured rows are inside their tolerances, not that the edit looks like the reference",
                      "matched stills at mapped times (sheet tool) are still compared by eye for type size, position, grade and density"]}
    return out, {"PASS": 0, "FAIL": 1}.get(status, 2)


def to_markdown(out):
    lines = ["| row | dimension | metric | DNA | draft | delta | allowed | verdict |", "|---|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        d = "" if r["delta"] is None else (f"{r['delta']:+.3g}" + ("" if r["delta_pct"] is None else f" ({r['delta_pct']:+.1f}%)"))
        al = "" if r["allowed"] is None else f"+/-{r['allowed']:.3g}"
        lines.append(f"| {r['id']} | {r['dimension']} | {r['metric']} | {r['reference']} {r['unit'] or ''} | {'' if r['draft'] is None else r['draft']} | {d} | {al} | {r['verdict']}" + (f": {r['deviate']}" if r["verdict"] == "deviate" else "") + " |")
    lines.append("")
    lines.append(f"Status: **{out['status']}** (ok {out['counts']['ok']}, flag {out['counts']['flag']}, deviate {out['counts']['deviate']}, info {out['counts']['info']}, not_measured {out['counts']['not_measured']}).")
    return "\n".join(lines) + "\n"


def self_check() -> int:
    ok, fails = 0, []

    def expect(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(label)

    expect("pct inside", judge({"value": 36.0, "tolerance": {"mode": "pct", "value": 20}}, 40.0)[0] == "ok")
    expect("pct outside -> flag", judge({"value": 36.0, "tolerance": {"mode": "pct", "value": 20}}, 50.0)[0] == "flag")
    expect("near-zero uses the absolute floor", judge({"value": 0.4, "tolerance": {"mode": "pct", "value": 20, "abs_floor": 0.3}}, 0.65)[0] == "ok")
    expect("abs outside", judge({"value": 1180, "tolerance": {"mode": "abs", "value": 40}}, 1250)[0] == "flag")
    expect("exact hex ignores case", judge({"value": "#F2C230", "tolerance": {"mode": "exact"}}, "#f2c230")[0] == "ok")
    expect("categorical allowed set", judge({"value": "whip", "tolerance": {"mode": "categorical", "allowed": ["whip", "slide"]}}, "slide")[0] == "ok")
    expect("deviate declared is reported, not failed", judge({"value": 36.0, "tolerance": {"mode": "pct", "value": 5}, "deviate": "Elevated: slower breath beats"}, 20.0)[0] == "deviate")
    expect("missing draft value is never ok", judge({"value": 36.0, "tolerance": {"mode": "pct", "value": 20}}, None)[0] == "not_measured")
    expect("type mismatch is never ok", judge({"value": 36.0, "tolerance": {"mode": "pct", "value": 20}}, "fast")[0] == "not_measured")
    with tempfile.TemporaryDirectory(prefix="fd_בדיקה ") as td:
        b = Path(td)
        card = {"rows": [
            {"id": "R01", "dimension": "pacing", "metric": "cuts_per_min", "value": 36.0, "unit": "per_min", "source_key": "measurements:pacing.cuts_per_min", "tolerance": {"mode": "pct", "value": 20}},
            {"id": "R02", "dimension": "colour", "metric": "accent_hex", "value": "#F2C230", "unit": "hex", "tolerance": {"mode": "exact"}},
            {"id": "R03", "dimension": "broll", "metric": "n/a", "value": None, "na_reason": "none"}]}
        (b / "card.json").write_text(json.dumps(card))
        d = b / "draft"
        d.mkdir()
        (d / "measurements.json").write_text(json.dumps({"pacing": {"cuts_per_min": 38.0}}))
        out, code = run(b / "card.json", d, {})
        expect("colour row without a manual value -> INSUFFICIENT_EVIDENCE", code == 2 and out["counts"]["not_measured"] == 1)
        out, code = run(b / "card.json", d, {"R02": "#F2C230"})
        expect("all measured and inside -> PASS", code == 0 and out["counts"]["ok"] == 2)
        (d / "measurements.json").write_text(json.dumps({"pacing": {"cuts_per_min": 60.0}}))
        out, code = run(b / "card.json", d, {"R02": "#F2C230"})
        expect("a flag -> FAIL with a fix", code == 1 and out["rows"][0]["verdict"] == "flag" and out["rows"][0]["fix"])
        expect("markdown ledger renders", "| R01 |" in to_markdown(out))
        out, code = run(b / "card.json", b / "nodraft", {})
        expect("no draft analysis -> INSUFFICIENT_EVIDENCE", code == 2)
    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": ok + len(fails), "failed": fails}))
    return 0 if not fails else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Fidelity ledger: draft measurements vs the Style DNA card.")
    ap.add_argument("card", nargs="?")
    ap.add_argument("--draft")
    ap.add_argument("--manual")
    ap.add_argument("--out")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.card or not a.draft:
        ap.print_help()
        return 2
    try:
        manual = load(Path(a.manual)) if a.manual else {}
        out, code = run(Path(a.card), Path(a.draft), manual)
    except (OSError, ValueError, KeyError) as e:
        print(json.dumps({"status": "INSUFFICIENT_EVIDENCE", "reason": str(e)}, ensure_ascii=False))
        return 2
    md = to_markdown(out)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False) if a.json else md)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

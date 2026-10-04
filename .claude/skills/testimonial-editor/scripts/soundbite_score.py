#!/usr/bin/env python3
"""soundbite_score.py - rank scored soundbites and propose the hook, the close and the body of a testimonial.

You score each sentence of the (hand-corrected) transcript 0-2 on five criteria and flag whether it
kills an objection; the script does the arithmetic and the selection so the choice is auditable.

Usage:
  python soundbite_score.py <soundbites.json> [--body 4] [--md] [--json]
  python soundbite_score.py --self-check

Input:
  {"source_duration_s": 180.0,
   "soundbites": [{"id": "S1", "start_s": 12.4, "end_s": 18.0, "text": "...",
                   "specific": 2, "emotion": 1, "contrast": 0, "standalone": 2, "provable": 1, "objection": false}, ...]}

Criteria (0, 1 or 2 each):
  specific    a number, a time, a currency amount            standalone  makes sense heard cold
  emotion     a feeling the face carries                      provable    a screenshot/photo exists to show it
  contrast    before -> after in the same line
  objection   true = it kills an objection (price, "another course", no experience): +2
Total = specific + emotion + contrast + standalone + provable + 2 x objection (max 12).

Selection (the author's rule, kept as defaults):
  hook  = highest (specific + standalone); ties -> provable, then total      (3 hook options are listed)
  close = highest emotion among the rest; ties -> total, then the longer line
  body  = the best of the remaining by total, to be ordered before -> turn -> result by the editor
Warnings (never silently fixed): a hook with specific = 0 (do not invent a number: use a pain or a twist
opening), specific = 2 with provable = 0 (a number with no proof: ask the client for the screenshot or show
it only as a quoted callout), a hook line longer than 4.5 s, overlapping lines, times outside the source.

Exit codes: 0 ok | 1 invalid scores/times | 2 INSUFFICIENT_EVIDENCE (fewer than 5 scored sentences, or
nothing scored). Needs only the Python standard library (3.9+).
"""
from __future__ import annotations

import argparse
import json
import math
import sys

VERSION = "0.1.0"
CRITERIA = ["specific", "emotion", "contrast", "standalone", "provable"]
MIN_SENTENCES = 5
MAX_HOOK_S = 4.5


def _isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def validate(data):
    errs = []
    sb = data.get("soundbites")
    if not isinstance(sb, list) or not sb:
        return ["no soundbites"], []
    dur = data.get("source_duration_s")
    seen = set()
    for s in sb:
        sid = s.get("id")
        if not sid or sid in seen:
            errs.append(f"id missing or duplicate: {sid!r}")
        seen.add(sid)
        if not (_isnum(s.get("start_s")) and _isnum(s.get("end_s")) and 0 <= s["start_s"] < s["end_s"]):
            errs.append(f"{sid}: start_s/end_s invalid")
        elif _isnum(dur) and s["end_s"] > dur + 0.05:
            errs.append(f"{sid}: ends after the source ({s['end_s']} > {dur})")
        if not str(s.get("text", "")).strip():
            errs.append(f"{sid}: empty text")
        for c in CRITERIA:
            if s.get(c) not in (0, 1, 2) or isinstance(s.get(c), bool):
                errs.append(f"{sid}: {c} must be 0, 1 or 2")
        if not isinstance(s.get("objection", False), bool):
            errs.append(f"{sid}: objection must be true/false")
    return errs, sb


def total(s):
    return sum(s[c] for c in CRITERIA) + (2 if s.get("objection") else 0)


def select(sb, body_n=4):
    ranked = sorted(sb, key=lambda s: (-total(s), s["start_s"]))
    hooks = sorted(sb, key=lambda s: (-(s["specific"] + s["standalone"]), -s["provable"], -total(s), s["start_s"]))
    hook = hooks[0]
    rest = [s for s in sb if s["id"] != hook["id"]]
    close = sorted(rest, key=lambda s: (-s["emotion"], -total(s), -(s["end_s"] - s["start_s"])))[0]
    body = [s for s in sorted(rest, key=lambda s: (-total(s), s["start_s"])) if s["id"] != close["id"]][:body_n]
    warns = []
    if hook["specific"] == 0:
        warns.append(f"hook {hook['id']} has no specific number/time/amount: use a pain or twist opening; never invent a number")
    for s in sb:
        if s["specific"] == 2 and s["provable"] == 0:
            warns.append(f"{s['id']}: specific number with no proof: ask for the screenshot or show it only as a quoted callout (never pair it with a screenshot that disagrees)")
    if hook["end_s"] - hook["start_s"] > MAX_HOOK_S:
        warns.append(f"hook {hook['id']} lasts {hook['end_s'] - hook['start_s']:.1f} s (> {MAX_HOOK_S}): the number must land by about 3 s")
    ordered = sorted(sb, key=lambda s: s["start_s"])
    for a, b in zip(ordered, ordered[1:]):
        if b["start_s"] < a["end_s"] - 1e-6:
            warns.append(f"{a['id']} and {b['id']} overlap in the source: check the sentence split")
    return {"ranked": [{"id": s["id"], "total": total(s), **{c: s[c] for c in CRITERIA}, "objection": bool(s.get("objection")), "start_s": s["start_s"], "end_s": s["end_s"]} for s in ranked],
            "hook": hook["id"], "hook_options": [h["id"] for h in hooks[:3]], "close": close["id"], "body": [s["id"] for s in body],
            "needs_proof": [s["id"] for s in sb if s["specific"] == 2 and s["provable"] == 0], "warnings": warns}


def run(data, body_n=4):
    errs, sb = validate(data)
    if errs:
        return {"status": "FAIL", "errors": errs}, 1
    if len(sb) < MIN_SENTENCES:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": f"{len(sb)} scored sentences < {MIN_SENTENCES}: score the whole transcript, not a few favourites"}, 2
    out = select(sb, body_n)
    out.update({"tool": "soundbite_score", "version": VERSION, "status": "PASS", "count": len(sb),
                "note": "selection is a proposal for the paper edit: reorder only where every statement stays true in its new context and log each move"})
    return out, 0


def to_md(out, sb):
    by = {s["id"]: s for s in sb}
    lines = ["| id | time | total | spec | emo | contr | alone | prov | obj | role | text |", "|---|---|---:|---:|---:|---:|---:|---:|:-:|---|---|"]
    roles = {out["hook"]: "HOOK", out["close"]: "CLOSE"}
    roles.update({b: "body" for b in out["body"]})
    for r in out["ranked"]:
        s = by[r["id"]]
        lines.append(f"| {r['id']} | {r['start_s']:.1f}-{r['end_s']:.1f} | {r['total']} | {r['specific']} | {r['emotion']} | {r['contrast']} | {r['standalone']} | {r['provable']} | {'Y' if r['objection'] else ''} | {roles.get(r['id'], '')} | {s['text'][:70]} |")
    if out["warnings"]:
        lines += ["", "Warnings:"] + [f"- {w}" for w in out["warnings"]]
    return "\n".join(lines) + "\n"


def self_check() -> int:
    ok, fails = 0, []

    def expect(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(label)

    def sbite(i, a, b, sp, em, co, st, pr, ob=False, text="x"):
        return {"id": i, "start_s": a, "end_s": b, "text": text, "specific": sp, "emotion": em, "contrast": co, "standalone": st, "provable": pr, "objection": ob}

    data = {"source_duration_s": 180.0, "soundbites": [
        sbite("S1", 5, 9, 2, 0, 0, 2, 2, text="last month I closed 500K"),
        sbite("S2", 20, 25, 0, 2, 1, 1, 0, text="I cried when I saw it"),
        sbite("S3", 30, 36, 1, 1, 2, 2, 0, True, text="I did not believe another course would work"),
        sbite("S4", 40, 45, 2, 0, 1, 1, 0, text="went from 40K to 100K"),
        sbite("S5", 50, 55, 0, 1, 0, 0, 0, text="so yeah"),
        sbite("S6", 60, 65, 1, 2, 0, 2, 1, text="my kids are proud")]}
    out, code = run(data)
    expect("exit 0 on a complete set", code == 0)
    expect("hook = highest specific+standalone (S1)", out["hook"] == "S1")
    expect("close = highest emotion among the rest (S2 beats S6 on total? emotion tie -> total)", out["close"] in ("S2", "S6") and out["close"] != out["hook"])
    expect("three hook options listed", len(out["hook_options"]) == 3)
    expect("objection adds 2 (S3 total 1+1+2+2+0+2 = 8)", next(r for r in out["ranked"] if r["id"] == "S3")["total"] == 8)
    expect("specific number with no proof is surfaced", "S4" in out["needs_proof"])
    expect("markdown renders", "| S1 |" in to_md(out, data["soundbites"]))
    out2, code2 = run({"soundbites": data["soundbites"][:3]})
    expect("fewer than 5 sentences -> INSUFFICIENT_EVIDENCE", code2 == 2)
    bad = json.loads(json.dumps(data))
    bad["soundbites"][0]["specific"] = 3
    expect("score outside 0-2 -> FAIL", run(bad)[1] == 1)
    bad = json.loads(json.dumps(data))
    bad["soundbites"][1]["end_s"] = 999
    expect("line beyond the source -> FAIL", run(bad)[1] == 1)
    nohook = {"soundbites": [sbite(f"N{i}", i * 10, i * 10 + 4, 0, i % 3, 0, 1, 0) for i in range(6)]}
    out3, code3 = run(nohook)
    expect("no specific hook -> warning, not an invented number", code3 == 0 and any("no specific" in w for w in out3["warnings"]))
    ov = json.loads(json.dumps(data))
    ov["soundbites"][1]["start_s"] = 8
    expect("overlap warning", any("overlap" in w for w in run(ov)[0]["warnings"]))
    expect("empty input is not a pass", run({"soundbites": []})[1] == 1)
    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": ok + len(fails), "failed": fails}))
    return 0 if not fails else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Rank scored soundbites; propose hook, close and body.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--body", type=int, default=4)
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.path:
        ap.print_help()
        return 2
    try:
        with open(a.path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        print(json.dumps({"status": "INSUFFICIENT_EVIDENCE", "reason": str(e)}))
        return 2
    out, code = run(data, a.body)
    if a.md and code == 0:
        print(to_md(out, data["soundbites"]))
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

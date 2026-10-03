#!/usr/bin/env python3
"""cut_regression.py - score detected edit points against hand-verified ground truth (the G4 regression gate).

Why: a change to a cut-detector threshold must never be judged by eye. The owner's detector reached
F1 0.89 (precision 0.87, recall 0.91) on 20 hand-verified ads, 339 edit points (the owner's private
set, not reproduced here). A port must hold at least its own recorded baseline on a rights-cleared
labelled set; this script computes the numbers and fails closed.

Usage:
  python cut_regression.py --pair <analysis_dir_or_measurements.json> <truth.json> [--pair DET TRUTH ...]
                           [--tol-frames 2] [--min-f1 0.89] [--min-recall R] [--min-truth 100]
                           [--include-check] [--json]
  python cut_regression.py --self-check

Truth file:  {"fps_num": 30, "fps_den": 1, "edit_points": [{"frame": 37}, {"t_s": 2.5}, ...]}
Detected:    measurements.json of the analysis contract (edit_points[].frame, kind cut|transition).
Matching is one-to-one (nearest first) within +/- tol frames; micro-averaged over all pairs.
Reports F1 at tolerance 0, 1, 2, 3 frames plus the gate tolerance.

Exit codes: 0 gate met | 1 gate missed | 2 INSUFFICIENT_EVIDENCE (too few truth points, missing fps,
unreadable file). A set with fewer than --min-truth truth points cannot hold or break a regression.
Limits stated in the output: the 0.89 is a historical number on private data; the known blind spot is
kinetic type / continuous-camera pieces (graphic transitions inside one move are missed); automatic cut
counts are wrong in about 60 % of ad-promo videos until verified on frames. Stdlib only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

VERSION = "0.1.0"
OWNER_BASELINE = {"f1": 0.89, "precision": 0.87, "recall": 0.91, "videos": 20, "edit_points": 339,
                  "source": "distilled 06 reference-analysis §1.2 (checked 2026-10-01); owner's private set, not reproduced"}


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"), parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))


def _frames(obj, fps, kinds, label):
    out = []
    for e in obj.get("edit_points", []):
        if e.get("kind") is not None and e["kind"] not in kinds:
            continue
        if isinstance(e.get("frame"), int):
            out.append(e["frame"])
        elif isinstance(e.get("t_s"), (int, float)) and not isinstance(e.get("t_s"), bool):
            if fps is None:
                raise ValueError(f"{label}: time given but no fps")
            out.append(int(round(e["t_s"] * fps)))
        else:
            raise ValueError(f"{label}: edit point without frame or t_s")
    return sorted(out)


def match(det, truth, tol):
    """Greedy one-to-one matching by smallest distance. Returns tp, fp, fn."""
    pairs = sorted(((abs(a - b), i, j) for i, a in enumerate(det) for j, b in enumerate(truth) if abs(a - b) <= tol))
    used_d, used_t, tp = set(), set(), 0
    for _, i, j in pairs:
        if i in used_d or j in used_t:
            continue
        used_d.add(i)
        used_t.add(j)
        tp += 1
    return tp, len(det) - tp, len(truth) - tp


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = (2 * p * r / (p + r)) if p and r else (0.0 if p is not None and r is not None else None)
    return p, r, f


def score(pairs, kinds, tols):
    tot = {t: [0, 0, 0] for t in tols}
    n_truth = 0
    for det_path, truth_path in pairs:
        dp = Path(det_path)
        if dp.is_dir():
            dp = dp / "measurements.json"
        det_obj, truth_obj = _load(dp), _load(Path(truth_path))
        tf = truth_obj.get("fps_num"), truth_obj.get("fps_den")
        fps = tf[0] / tf[1] if all(isinstance(x, int) and x > 0 for x in tf) else None
        inp = det_obj.get("input", {})
        dfps = inp.get("fps_num", 0) / inp["fps_den"] if inp.get("fps_den") else None
        if fps is not None and dfps is not None and abs(fps - dfps) > 1e-3:
            raise ValueError(f"{dp}: detected fps {dfps:.3f} differs from truth fps {fps:.3f}")
        det = _frames(det_obj, fps or dfps, kinds, str(dp))
        truth = _frames(truth_obj, fps, {"cut", "transition", "check", None}, str(truth_path))
        n_truth += len(truth)
        for t in tols:
            a, b, c = match(det, truth, t)
            tot[t][0] += a
            tot[t][1] += b
            tot[t][2] += c
    return tot, n_truth


def run(pairs, tol, min_f1, min_recall, min_truth, include_check):
    kinds = {"cut", "transition"} | ({"check"} if include_check else set())
    tols = sorted({0, 1, 2, 3, tol})
    try:
        tot, n_truth = score(pairs, kinds, tols)
    except (ValueError, OSError, KeyError, TypeError, ZeroDivisionError) as e:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": str(e)}, 2
    table = {}
    for t in tols:
        p, r, f = prf(*tot[t])
        table[str(t)] = {"tp": tot[t][0], "fp": tot[t][1], "fn": tot[t][2], "precision": p, "recall": r, "f1": f}
    gate = table[str(tol)]
    out = {"tool": "cut_regression", "version": VERSION, "pairs": len(pairs), "truth_points": n_truth, "tolerance_frames": tol,
           "by_tolerance": table, "gate": {"min_f1": min_f1, "min_recall": min_recall, "min_truth": min_truth},
           "owner_baseline": OWNER_BASELINE,
           "limits": ["0.89 is a historical number on the owner's private 20-ad set, not reproduced; hold the baseline recorded for YOUR labelled set",
                      "kinetic-type / continuous-camera references hide graphic transitions from the detector (known blind spot)",
                      "'check' points (jump cut vs graphic swap) are excluded unless --include-check; decide them from the frames"]}
    if n_truth < min_truth:
        out.update(status="INSUFFICIENT_EVIDENCE", reason=f"{n_truth} truth points < --min-truth {min_truth}: too small to hold or break a regression")
        return out, 2
    if gate["f1"] is None or gate["recall"] is None:
        out.update(status="INSUFFICIENT_EVIDENCE", reason="undefined precision/recall (no detections or no truth): not a perfect score")
        return out, 2
    ok = gate["f1"] >= min_f1 and (min_recall is None or gate["recall"] >= min_recall)
    out["status"] = "PASS" if ok else "FAIL"
    return out, 0 if ok else 1


def self_check() -> int:
    ok, fails = 0, []

    def expect(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(label)

    expect("match: exact", match([10, 20, 30], [10, 20, 30], 0) == (3, 0, 0))
    expect("match: off by 3 outside tol 2", match([13], [10], 2) == (0, 1, 1))
    expect("match: off by 2 inside tol 2", match([12], [10], 2) == (1, 0, 0))
    expect("match: one detection cannot match two truths", match([10], [9, 11], 2) == (1, 0, 1))
    expect("prf: undefined stays None", prf(0, 0, 0) == (None, None, None))
    with tempfile.TemporaryDirectory(prefix="cr_בדיקה ") as td:
        base = Path(td)
        truth_frames = list(range(30, 30 * 25, 30))  # 24 cuts at 30 fps
        truth = {"fps_num": 30, "fps_den": 1, "edit_points": [{"frame": f} for f in truth_frames]}
        det_frames = truth_frames[:]
        det_frames[3] += 2   # within tolerance
        det_frames[5] += 3   # outside tolerance 2 -> one FP + one FN
        det_frames.pop(10)   # a miss
        det_frames.append(5000)  # a false positive
        det = {"input": {"fps_num": 30, "fps_den": 1}, "edit_points": [{"frame": f, "kind": "cut"} for f in det_frames] + [{"frame": 777, "kind": "check"}]}
        (base / "truth.json").write_text(json.dumps(truth))
        (base / "m.json").write_text(json.dumps(det))
        pair = [(str(base / "m.json"), str(base / "truth.json"))]
        out, code = run(pair, 2, 0.0, None, 1, False)
        g = out["by_tolerance"]["2"]
        expect("counts: tp 22, fp 2, fn 2", (g["tp"], g["fp"], g["fn"]) == (22, 2, 2))
        expect("check points excluded by default", g["fp"] + g["tp"] == len(det_frames))
        out2, code2 = run(pair, 2, 0.95, None, 1, False)
        expect("F1 below the gate -> exit 1", code2 == 1 and out2["status"] == "FAIL")
        out3, code3 = run(pair, 2, 0.5, 0.85, 1, False)
        expect("recall gate (>=85 % within +/-2 frames) passes", code3 == 0)
        out4, code4 = run(pair, 2, 0.89, None, 100, False)
        expect("too few truth points -> INSUFFICIENT_EVIDENCE", code4 == 2)
        out5, code5 = run([(str(base / "missing.json"), str(base / "truth.json"))], 2, 0.89, None, 1, False)
        expect("unreadable file -> INSUFFICIENT_EVIDENCE", code5 == 2)
        (base / "d2.json").write_text(json.dumps({"input": {"fps_num": 30, "fps_den": 1}, "edit_points": []}))
        out6, code6 = run([(str(base / "d2.json"), str(base / "truth.json"))], 2, 0.0, None, 1, False)
        expect("no detections: precision undefined is not a pass", code6 == 2)
        (base / "tt.json").write_text(json.dumps({"fps_num": 25, "fps_den": 1, "edit_points": [{"t_s": 1.0}, {"t_s": 2.0}]}))
        (base / "dd.json").write_text(json.dumps({"input": {"fps_num": 30, "fps_den": 1}, "edit_points": [{"frame": 30, "kind": "cut"}]}))
        out7, code7 = run([(str(base / "dd.json"), str(base / "tt.json"))], 2, 0.0, None, 1, False)
        expect("fps mismatch between detected and truth -> INSUFFICIENT_EVIDENCE", code7 == 2)
    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": ok + len(fails), "failed": fails}))
    return 0 if not fails else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Score detected edit points against ground truth (fails closed).")
    ap.add_argument("--pair", action="append", nargs=2, metavar=("DETECTED", "TRUTH"), default=[],
                    help="analysis dir or measurements.json, then the truth json (repeatable)")
    ap.add_argument("--tol-frames", type=int, default=2)
    ap.add_argument("--min-f1", type=float, default=OWNER_BASELINE["f1"])
    ap.add_argument("--min-recall", type=float)
    ap.add_argument("--min-truth", type=int, default=100)
    ap.add_argument("--include-check", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.pair:
        ap.print_help()
        return 2
    pairs = [(d, t) for d, t in a.pair]
    out, code = run(pairs, a.tol_frames, a.min_f1, a.min_recall, a.min_truth, a.include_check)
    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(out["status"] + (f": {out.get('reason')}" if out.get("reason") else ""))
        for t, r in (out.get("by_tolerance") or {}).items():
            fmt = lambda v: "n/a" if v is None else f"{v:.3f}"
            print(f"  tol +/-{t} frames: tp={r['tp']} fp={r['fp']} fn={r['fn']} P={fmt(r['precision'])} R={fmt(r['recall'])} F1={fmt(r['f1'])}")
        if out.get("limits"):
            print("  limits: " + " | ".join(out["limits"]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

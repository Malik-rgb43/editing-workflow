#!/usr/bin/env python3
"""cutlist_check.py - gate G6 (clean windows) and native fps for a cut of AI-generated takes.

Usage:
    python cutlist_check.py CUTLIST.json [--probe takes_probe.json | --skip-fps] [--min-window 1.2]
                            [--max-window 2.5] [--json]
    python cutlist_check.py --self-check

CUTLIST.json
  {"timeline_fps": "24",              // number or rational string ("24000/1001")
   "duration_s": 30.0,                // final timeline length
   "ratio": "9:16",                   // optional; sets the pacing band (9:16 up to 35 cuts/min, else 30)
   "shots": [{"id": "S01", "take": "S01_t2",           // take = file stem used in probe.json
              "src_in": 0.4, "src_out": 1.9,           // the window kept from the take, seconds
              "reverse": false,
              "long_take_reason": "",                  // non-empty only when a long take IS the idea
              "artifact_ranges": [[2.2, 2.6]],         // reviewed artifact spans in take time
              "cover": ""}]}                           // cover used when an artifact is inside the window

Errors (gate fails):
  CW_WINDOW  window outside [min, max] s (defaults 1.2-2.5; market median 1.7 s) unless long_take_reason is set
  CW_REVERSE take played in reverse (never reverse a take to fill time or close a loop)
  CW_ARTIFACT a reviewed artifact range overlaps the window and no cover is declared
  CW_OOB     window outside the take (needs probe.json)
  CW_FPS     take fps != timeline fps (stepped cadence; native fps of the takes is the timeline fps)
  CW_FIELDS  missing/invalid fields
Warnings: CW_LONG_TAKE (declared long take: G1 must hold frame by frame), CW_PACE (cuts/min outside 22-30,
          35 for 9:16), CW_FIRST_CUT (> 2.8 s), CW_SUM (sum of windows != duration), CW_VFR, CW_HDR.
The fps check needs probe.json from probe_takes.py; without it (and without --skip-fps) the verdict is
`blocked`, never pass. `--skip-fps` records the check as n/a on your responsibility.
Exit codes: 0 pass | 1 fail | 2 blocked. Stdlib only. Numbers: market median shot 1.67 s, first cut 2.79 s,
26 cuts/min (11 references, 10 x 16:9; author's own 9 videos: 8.5 cuts/min, median 12 s) - owner benchmark,
small samples, distilled/05 prompting §9.
"""
import argparse
import json
import statistics
import sys
from fractions import Fraction
from pathlib import Path


def fr(v):
    try:
        f = Fraction(str(v))
        return f if f > 0 else None
    except (ValueError, ZeroDivisionError):
        return None


def check(cut, probe=None, skip_fps=False, wmin=1.2, wmax=2.5):
    f = []  # (severity, code, message)
    st = {}
    tl = fr(cut.get("timeline_fps")) if isinstance(cut, dict) else None
    shots = cut.get("shots") if isinstance(cut, dict) else None
    if tl is None or not shots or not isinstance(shots, list):
        return [("error", "CW_FIELDS", "need timeline_fps and a non-empty shots list")], {"verdict": "blocked", "reason": "empty or invalid cut list"}
    by_take = {}
    for r in (probe or []):
        if isinstance(r, dict) and not r.get("error"):
            by_take[r.get("take") or Path(str(r.get("file", ""))).stem] = r
    wins = []
    fps_checked = 0
    for s in shots:
        sid = s.get("id", "?")
        try:
            a, b = float(s["src_in"]), float(s["src_out"])
        except (KeyError, TypeError, ValueError):
            f.append(("error", "CW_FIELDS", f"{sid}: src_in/src_out missing"))
            continue
        w = b - a
        wins.append(w)
        if w <= 0:
            f.append(("error", "CW_FIELDS", f"{sid}: window <= 0"))
            continue
        long_reason = str(s.get("long_take_reason") or "").strip()
        if w > wmax + 1e-9 or w < wmin - 1e-9:
            if w > wmax and long_reason:
                f.append(("warn", "CW_LONG_TAKE", f"{sid}: {w:.2f} s declared a long take ({long_reason}); G1 integrity must hold frame by frame"))
            else:
                f.append(("error", "CW_WINDOW", f"{sid}: window {w:.2f} s outside {wmin}-{wmax} s"))
        if s.get("reverse"):
            f.append(("error", "CW_REVERSE", f"{sid}: reversed take (generate another angle instead)"))
        for rng in s.get("artifact_ranges") or []:
            try:
                x, y = float(rng[0]), float(rng[1])
            except (TypeError, ValueError, IndexError):
                f.append(("error", "CW_FIELDS", f"{sid}: bad artifact range {rng}"))
                continue
            if x < b and y > a and not str(s.get("cover") or "").strip():
                f.append(("error", "CW_ARTIFACT", f"{sid}: artifact {x}-{y} s inside the window {a}-{b} s with no cover"))
        pr = by_take.get(s.get("take"))
        if pr is not None:
            fps_checked += 1
            tk = fr(pr.get("fps"))
            if tk is None or tk != tl:
                f.append(("error", "CW_FPS", f"{sid}: take fps {pr.get('fps')} != timeline fps {tl} (native fps must be preserved)"))
            d = pr.get("duration_s")
            if d is not None and b > d + 1 / float(tl) + 1e-9:
                f.append(("error", "CW_OOB", f"{sid}: src_out {b} s beyond take duration {d:.2f} s"))
            if pr.get("vfr_suspect"):
                f.append(("warn", "CW_VFR", f"{sid}: variable-frame-rate suspect (avg != r_frame_rate)"))
            if pr.get("hdr_suspect"):
                f.append(("warn", "CW_HDR", f"{sid}: HDR/BT.2020 tagged take: render --sdr and grade deliberately"))
    n = len(shots)
    dur = cut.get("duration_s")
    if wins:
        st.update(shots=n, median_window_s=round(statistics.median(wins), 2), min_window_s=round(min(wins), 2), max_window_s=round(max(wins), 2))
        if dur:
            try:
                d = float(dur)
                st["cuts_per_min"] = round((n - 1) / d * 60, 1)
                hi = 35 if str(cut.get("ratio", "")).strip() == "9:16" else 30
                if not (22 <= st["cuts_per_min"] <= hi):
                    f.append(("warn", "CW_PACE", f"{st['cuts_per_min']} cuts/min outside 22-{hi} (owner target; market median 26)"))
                if abs(sum(wins) - d) > 2 / float(tl):
                    f.append(("warn", "CW_SUM", f"sum of windows {sum(wins):.2f} s != duration {d:.2f} s (covers, holds or overlaps?)"))
            except (TypeError, ValueError):
                f.append(("error", "CW_FIELDS", "duration_s is not a number"))
        if wins[0] > 2.8:
            f.append(("warn", "CW_FIRST_CUT", f"first cut at {wins[0]:.2f} s > 2.8 s (market median 2.79 s; author's own median 9.5 s)"))
    errs = [x for x in f if x[0] == "error"]
    st["fps_checked_shots"] = fps_checked
    if errs:
        verdict, reason = "fail", f"{len(errs)} error(s)"
    elif not skip_fps and fps_checked < n:
        verdict, reason = "blocked", f"native-fps check ran on {fps_checked}/{n} shots (provide probe.json from probe_takes.py or pass --skip-fps)"
    else:
        verdict, reason = "pass", "windows, reverse, artifact and fps checks passed" + (" (fps n/a: --skip-fps)" if skip_fps else "")
    st.update(verdict=verdict, reason=reason)
    return f, st


def self_check():
    base = {"timeline_fps": "24", "duration_s": 6.0, "ratio": "9:16", "shots": [
        {"id": "S1", "take": "t1", "src_in": 0.4, "src_out": 1.9},
        {"id": "S2", "take": "t2", "src_in": 0.0, "src_out": 1.5},
        {"id": "S3", "take": "t3", "src_in": 1.0, "src_out": 2.5},
        {"id": "S4", "take": "t4", "src_in": 0.5, "src_out": 2.0}]}
    probe = [{"take": f"t{i}", "fps": "24", "duration_s": 5.0} for i in range(1, 5)]
    bad = []

    def expect(name, cut, verdict, code=None, prb=probe, **kw):
        f, st = check(cut, prb, **kw)
        if st["verdict"] != verdict or (code and not any(c == code for _, c, _ in f)):
            bad.append(f"{name}: {st['verdict']} {[c for _, c, _ in f]}")

    def mut(**over):
        c = json.loads(json.dumps(base))
        for k, v in over.items():
            if k.startswith("s") and k[1:].isdigit():
                c["shots"][int(k[1:]) - 1].update(v)
            else:
                c[k] = v
        return c
    expect("clean", base, "pass")
    expect("empty", {"timeline_fps": "24", "shots": []}, "blocked")
    expect("long-window", mut(s2={"src_out": 3.2}), "fail", "CW_WINDOW")
    expect("short-window", mut(s2={"src_out": 0.8}), "fail", "CW_WINDOW")
    expect("declared-long-take", mut(s2={"src_out": 3.2, "long_take_reason": "the oner is the idea"}), "pass", "CW_LONG_TAKE")
    expect("reverse", mut(s3={"reverse": True}), "fail", "CW_REVERSE")
    expect("artifact-no-cover", mut(s1={"artifact_ranges": [[1.5, 2.0]]}), "fail", "CW_ARTIFACT")
    expect("artifact-covered", mut(s1={"artifact_ranges": [[1.5, 2.0]], "cover": "2f whip + whoosh"}), "pass")
    expect("artifact-outside-window", mut(s1={"artifact_ranges": [[3.0, 3.5]]}), "pass")
    expect("fps-mismatch", base, "fail", "CW_FPS", prb=[{"take": f"t{i}", "fps": "30", "duration_s": 5.0} for i in range(1, 5)])
    expect("fps-rational-equal", mut(timeline_fps="24000/1001"), "pass", prb=[{"take": f"t{i}", "fps": "24000/1001", "duration_s": 5.0} for i in range(1, 5)])
    expect("no-probe-blocked", base, "blocked", prb=None)
    expect("skip-fps", base, "pass", prb=None, skip_fps=True)
    expect("oob", mut(s1={"src_out": 9.0, "long_take_reason": "x"}), "fail", "CW_OOB")
    if bad:
        print("SELF-CHECK FAILED")
        for b in bad:
            print(" -", b)
        return 1
    print("SELF-CHECK OK (14 cases)")
    return 0


def main(argv=None):
    try:  # Hebrew paths / non-ASCII messages must not crash on a legacy console code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cutlist", nargs="?")
    ap.add_argument("--probe")
    ap.add_argument("--skip-fps", action="store_true")
    ap.add_argument("--min-window", type=float, default=1.2)
    ap.add_argument("--max-window", type=float, default=2.5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.cutlist:
        ap.print_usage()
        return 2
    try:
        cut = json.loads(Path(a.cutlist).read_text(encoding="utf-8"))
        probe = json.loads(Path(a.probe).read_text(encoding="utf-8")) if a.probe else None
    except (OSError, json.JSONDecodeError) as e:
        print(f"BLOCKED: cannot read inputs: {e}")
        return 2
    findings, st = check(cut, probe, a.skip_fps, a.min_window, a.max_window)
    if a.json:
        print(json.dumps({"summary": st, "findings": [{"severity": s, "code": c, "message": m} for s, c, m in findings]}, ensure_ascii=False, indent=2))
    else:
        for s, c, m in findings:
            print(f"[{s.upper():5}] {c}: {m}")
        print("stats:", {k: v for k, v in st.items() if k not in ("verdict", "reason")})
        print(f"VERDICT: {st['verdict']} - {st['reason']}")
    return {"pass": 0, "fail": 1, "blocked": 2}[st["verdict"]]


if __name__ == "__main__":
    sys.exit(main())

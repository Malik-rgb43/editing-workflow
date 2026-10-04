#!/usr/bin/env python3
"""route_gate.py - the 30-minute gate: local generation ETA per shot vs the limit.

Usage:
    python route_gate.py --unit-seconds 1380 --unit-output-seconds 2.06 --shot-seconds 5 [--shots 6]
                         [--limit-min 30] [--machine "the reference machine, Wan2.1 1.3B"] [--json]
    python route_gate.py --self-check

Procedure it encodes (owner rule, decided 2026-09): BENCHMARK ONE UNIT of the local model on this machine
(wall-clock seconds for a known number of OUTPUT seconds), compute the ETA per planned shot, and if the
ETA for ONE shot is above the limit (default 30 min) do not start it: propose a shorter shot or a hosted quote. Post the
one-line ETA in chat first; a job over 10 minutes also needs a go/no-go.

Verdicts (exit code): local_ok (0) | propose_other_route (1 = the gate is false: do not start the local job) |
blocked (2: no usable benchmark, never a pass). local_ok means "fits the limit"; it says nothing about
quality (no human rating exists for any local model here) and heavy jobs still go through render_lock,
one at a time.

Reference measurements (the reference machine; unmeasured on
NVIDIA/Apple; single passes on a shared host; no human rating) - E10, 2026-10-01 and owner log 2026-09:
  Wan2.1 T2V 1.3B fp16, sd.cpp Vulkan + CPU offload, 512x512, 33 f @16 fps (2.06 s), 20 steps: 1380 s wall
      = ~669 s per output second (peak 18.4 GB RAM; GPU VAE crashed twice)
  Wan2.2 TI2V-5B image-to-video: ~17 min for 2 s at 544 px, ~1 h per 4-5 s clip (owner log, rejected)
Stdlib only.
"""
import argparse
import json
import sys


def gate(unit_seconds, unit_output_seconds, shot_seconds, shots=1, limit_min=30.0):
    try:
        u, o, s, n, lim = float(unit_seconds), float(unit_output_seconds), float(shot_seconds), int(shots), float(limit_min)
    except (TypeError, ValueError):
        return {"verdict": "blocked", "reason": "arguments must be numbers"}
    if min(u, o, s, lim) <= 0 or n < 1:
        return {"verdict": "blocked", "reason": "no usable benchmark: unit-seconds, unit-output-seconds, shot-seconds and limit must be > 0 (benchmark ONE unit first)"}
    per_sec = u / o
    eta_shot_min = per_sec * s / 60
    out = {
        "seconds_per_output_second": round(per_sec, 1),
        "eta_per_shot_min": round(eta_shot_min, 1),
        "eta_all_shots_min": round(eta_shot_min * n, 1),
        "limit_min": lim, "shots": n, "shot_seconds": s,
    }
    if eta_shot_min > lim:
        out.update(verdict="propose_other_route",
                   reason=f"ETA {eta_shot_min:.0f} min per {s:g} s shot > {lim:g} min: do not start it locally; propose a shorter shot or a hosted quote (paid-spend-gate) before starting")
    else:
        out.update(verdict="local_ok",
                   reason=f"ETA {eta_shot_min:.0f} min per shot fits {lim:g} min; one heavy job at a time, partial results at once, quality unrated")
    return out


def self_check():
    bad = []
    r = gate(1380, 2.06, 2)
    if r["verdict"] != "local_ok" or not (22 <= r["eta_per_shot_min"] <= 23):
        bad.append(f"E10 2 s shot should be ~22 min local_ok: {r}")
    r = gate(1380, 2.06, 5, shots=6)
    if r["verdict"] != "propose_other_route" or not (54 <= r["eta_per_shot_min"] <= 56):
        bad.append(f"E10 5 s shot should be ~55 min propose_other_route: {r}")
    r = gate(17 * 60, 2, 5)
    if r["verdict"] != "propose_other_route":
        bad.append(f"owner Wan2.2 5B log (17 min / 2 s) at 5 s must propose another route: {r}")
    for args in ((0, 2, 5), (100, 0, 5), (100, 2, 0), ("x", 2, 5)):
        if gate(*args)["verdict"] != "blocked":
            bad.append(f"bad benchmark {args} must be blocked, never pass")
    if gate(100, 2, 5, limit_min=0)["verdict"] != "blocked":
        bad.append("limit 0 must be blocked")
    if bad:
        print("SELF-CHECK FAILED")
        for b in bad:
            print(" -", b)
        return 1
    print("SELF-CHECK OK (8 cases)")
    return 0


def main(argv=None):
    try:  # Hebrew paths / non-ASCII messages must not crash on a legacy console code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--unit-seconds", type=float)
    ap.add_argument("--unit-output-seconds", type=float)
    ap.add_argument("--shot-seconds", type=float)
    ap.add_argument("--shots", type=int, default=1)
    ap.add_argument("--limit-min", type=float, default=30.0)
    ap.add_argument("--machine", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    r = gate(a.unit_seconds, a.unit_output_seconds, a.shot_seconds, a.shots, a.limit_min)
    if a.machine:
        r["machine"] = a.machine
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"VERDICT: {r['verdict']} - {r['reason']}")
        for k in ("seconds_per_output_second", "eta_per_shot_min", "eta_all_shots_min", "machine"):
            if k in r:
                print(f"  {k}: {r[k]}")
    return {"local_ok": 0, "propose_other_route": 1, "blocked": 2}[r["verdict"]]


if __name__ == "__main__":
    sys.exit(main())

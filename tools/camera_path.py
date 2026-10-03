"""camera_path - a SMOOTHED speaker-centring camera path (zoom + pan) from faces.json, plus a GSAP rig. Never a per-frame face follow.

Rule (distilled 02/03; measured on the reference machine: 139 px/s^2 peak acceleration for the smoothed path vs 2782 for per-frame follow): the
camera holds a framing per zoom window and moves between framings with ONE eased transition. For every window ``t0:t1:scale``
  * the target centre = the MEDIAN face cx over the window's measured samples (robust to detector noise), clamped so the crop stays inside
    the frame at that scale (half-width 0.5/scale);
  * transitions ease in over ``--ease`` seconds ending at t0+ease and ease out starting at t1-ease (smoothstep: zero velocity at both ends);
  * outside windows the camera sits at scale 1.0, centre 0.5.
A window with NO measured face is refused (exit 2): never guess a framing. Output:
  camera_path.json  {keyframes:[{t, cx, scale}], samples:[{t,cx,scale}] at the video fps, peak_accel_cx (per s^2), naive_peak_accel_cx}
  rig.js            a GSAP timeline snippet (`tl.to(camera, {cx, scale, duration, ease:"power2.inOut"}, t)`) - seek-safe, no per-frame code.

Usage:
    python tools/camera_path.py <faces.json> --zoom 2.0:6.0:1.25 [--zoom 8.0:11.5:1.4] -o <dir> [--ease 0.45] [--duration 30]
Exit: 0 written, 2 refused / insufficient evidence.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from fractions import Fraction
from pathlib import Path

import _common  # noqa: F401


def smoothstep(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def clamp_cx(cx: float, scale: float) -> float:
    half = 0.5 / scale
    return min(max(cx, half), 1 - half)


def plan_keyframes(windows, faces, ease):
    """Pure: windows [(t0,t1,scale)], faces samples [{time_s,cx}] -> keyframes [(t, cx, scale)] and per-window targets. Raises ValueError."""
    kfs, targets = [(0.0, 0.5, 1.0)], []
    for t0, t1, scale in sorted(windows):
        if t1 <= t0 or scale < 1.0:
            raise ValueError(f"bad window {t0}:{t1}:{scale} (end after start, scale >= 1)")
        pool = [s["cx"] for s in faces if s.get("cx") is not None and t0 <= s["time_s"] <= t1]
        if not pool:
            raise ValueError(f"window {t0:g}-{t1:g}s has no measured face: refusing to guess a framing")
        tgt = clamp_cx(statistics.median(pool), scale)
        e = min(ease, (t1 - t0) / 2)
        kfs += [(max(t0 - 1e-6, kfs[-1][0] + 1e-6), kfs[-1][1], kfs[-1][2]), (t0 + e, tgt, scale), (t1 - e, tgt, scale), (t1, 0.5, 1.0)]
        targets.append({"window": [t0, t1], "scale": scale, "cx": round(tgt, 4), "faces_used": len(pool)})
    return kfs, targets


def sample_path(kfs, fps, duration):
    out, i, n = [], 0, int(round(duration * fps)) + 1
    for f in range(n):
        t = f / fps
        while i + 1 < len(kfs) - 1 and t >= kfs[i + 1][0]:
            i += 1
        a, b = kfs[i], kfs[min(i + 1, len(kfs) - 1)]
        u = 0.0 if b[0] == a[0] else (t - a[0]) / (b[0] - a[0])
        s = smoothstep(u) if t <= b[0] else 1.0
        cx = a[1] + (b[1] - a[1]) * s
        sc = a[2] + (b[2] - a[2]) * s
        out.append({"t": round(t, 4), "cx": round(cx, 5), "scale": round(sc, 5)})
    return out


def peak_accel(series, fps):
    """Peak |second difference| of a uniformly sampled series, per s^2."""
    if len(series) < 3:
        return 0.0
    return max(abs(series[i + 1] - 2 * series[i] + series[i - 1]) for i in range(1, len(series) - 1)) * fps * fps


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="camera_path", description=__doc__.split("\n\n")[0])
    ap.add_argument("faces")
    ap.add_argument("--zoom", action="append", required=True, help="T0:T1:SCALE seconds (repeatable)")
    ap.add_argument("-o", "--out-dir", required=True)
    ap.add_argument("--ease", type=float, default=0.45)
    ap.add_argument("--duration", type=float)
    a = ap.parse_args(argv)

    from core.fsio import read_json, write_json_atomic, write_text_atomic

    try:
        d = read_json(a.faces)
        samples = d["samples"]
        fps = float(Fraction(d["fps"]))
        windows = []
        for z in a.zoom:
            t0, t1, sc = z.split(":")
            windows.append((float(t0), float(t1), float(sc)))
        kfs, targets = plan_keyframes(windows, samples, a.ease)
    except (ValueError, KeyError, OSError) as exc:
        print(f"camera_path: {exc}", file=sys.stderr)
        return 2
    duration = a.duration or max(max(w[1] for w in windows) + 1.0, samples[-1]["time_s"])
    path = sample_path(kfs, fps, duration)
    ours = peak_accel([p["cx"] for p in path], fps)
    # what a per-frame face follow would do (interpolate the raw face track to every frame), for the report only
    raw = [s for s in samples if s.get("cx") is not None]
    naive = 0.0
    if len(raw) >= 3:
        ts = [s["time_s"] for s in raw]
        cs = [s["cx"] for s in raw]
        interp, j = [], 0
        for f in range(int(round(duration * fps)) + 1):
            t = f / fps
            while j + 1 < len(ts) - 1 and t > ts[j + 1]:
                j += 1
            u = 0.0 if ts[j + 1] == ts[j] else max(0.0, min(1.0, (t - ts[j]) / (ts[j + 1] - ts[j])))
            interp.append(cs[j] + (cs[j + 1] - cs[j]) * u)
        naive = peak_accel(interp, fps)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    key = [{"t": round(t, 4), "cx": round(cx, 5), "scale": round(sc, 5)} for t, cx, sc in kfs]
    write_json_atomic(out / "camera_path.json", {"schema": "avc.camera-path/1", "fps": d["fps"], "windows": targets, "keyframes": key, "samples": path, "peak_accel_cx_per_s2": round(ours, 4), "naive_follow_peak_accel_cx_per_s2": round(naive, 4),
                                                  "note": "smoothed zoom-pan rig; a per-frame face follow is never used (the naive figure is for comparison only)"})
    lines = ["// generated by tools/camera_path.py - seek-safe GSAP rig: animate the properties of ONE camera object, no per-frame code.",
             "// usage: const camera = {cx: 0.5, scale: 1}; apply camera.cx / camera.scale to the stage transform in tl.eventCallback('onUpdate') or via gsap.set in the same timeline.",
             "function addCameraRig(tl, camera) {"]
    for (t0, c0, s0), (t1, c1, s1) in zip(kfs, kfs[1:]):
        if (c0, s0) != (c1, s1):
            lines.append(f'  tl.to(camera, {{cx: {c1:.5f}, scale: {s1:.5f}, duration: {t1 - t0:.4f}, ease: "power2.inOut"}}, {t0:.4f});')
    lines += ["}", ""]
    write_text_atomic(out / "rig.js", "\n".join(lines))
    print(json.dumps({"windows": targets, "peak_accel_cx_per_s2": round(ours, 3), "naive_follow_peak_accel_cx_per_s2": round(naive, 3), "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

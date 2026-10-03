"""motion_qa - camera-motion stutter detector (pan/zoom jerk) with an explicit coverage statement.

Global camera motion is estimated per frame pair from tracked feature points (Lucas-Kanade) and a similarity transform
(translation x/y, log-scale). Stutter = an acceleration spike (a velocity change far beyond the clip's own variation), a pan reversal
(velocity flips sign with real magnitude), or a zoom reversal. Findings carry frame number and real timestamp.

Fail-closed (E04-B07: the original crashed with a ValueError on a low-feature clip and exited 1 with a traceback):
  * a frame pair with too few tracked points is UNMEASURED, not "smooth"; if more than ``--max-unmeasured`` (default 30 %) of pairs are
    unmeasured the result is INSUFFICIENT_EVIDENCE with the tracked-pair coverage, never a vacuous PASS;
  * OpenCV missing (extra ``opencv``: `uv sync --extra opencv`) -> INSUFFICIENT_EVIDENCE with the install hint;
  * the envelope's decoded/expected frame counts must match like every QA tool.
Limits: measures GLOBAL camera motion of the whole frame; it cannot judge object motion, easing taste, or intentional shake. Thresholds
are starting points (``--accel-px``, ``--sigma``): calibrate on footage you accept.

Usage:
    python tools/motion_qa.py <video> [--max-width 480] [--accel-px 2.5] [--sigma 6] [--reversal-px 1.5] [--max-unmeasured 0.3]
                              [--min-points 12] [--min-inliers 30] [--timeout 900] [--json-out report.json]
Exit: 0 PASS, 1 FAIL, 2 INSUFFICIENT_EVIDENCE, 3 tool error.
"""

from __future__ import annotations

import argparse
import sys

import _common  # noqa: F401

TOOL = "motion_qa"


def analyse_series(tx, ty, ls, measured, *, clock, accel_px=2.5, sigma=6.0, reversal_px=1.5):
    """Pure: per-pair translation (px), log-scale and measured flags -> findings. Unit-tested without OpenCV."""
    import statistics

    from core.envelope import Finding, Severity

    n = len(tx)
    out = []

    def vel(series, i):
        return series[i] if measured[i] else None

    for name, series, unit_scale in (("pan_x", tx, 1.0), ("pan_y", ty, 1.0), ("zoom", ls, 100.0)):
        acc = []
        idx = []
        for i in range(1, n):
            if measured[i] and measured[i - 1]:
                acc.append(abs(series[i] - series[i - 1]) * unit_scale)
                idx.append(i)
        if len(acc) < 8:
            continue
        med = statistics.median(acc)
        mad = statistics.median([abs(x - med) for x in acc]) or 0.15
        floor = accel_px if name != "zoom" else accel_px * 0.2
        for a, i in zip(acc, idx):
            if a >= floor and a >= med + sigma * mad:
                out.append(Finding.at_frame("accel_spike", f"{name}: velocity changed by {a:.2f} (x{a / max(med, 1e-6):.0f} the clip's median) at frame {i}", clock.describe(i), Severity.ERROR, axis=name, delta=round(a, 3)))
        # reversals: a SUSTAINED movement (>= 4 frames in one direction, each >= the limit) that flips sign with real magnitude.
        # Noise around zero never has a sustained direction, so a still axis with +-2 px estimation jitter is not a "reversal".
        lim = reversal_px if name != "zoom" else reversal_px * 0.01
        for i in range(4, n):
            window = range(i - 4, i)
            if all(measured[j] for j in window) and measured[i]:
                prior = [series[j] for j in window]
                if all(v >= lim for v in prior) and series[i] <= -lim or all(v <= -lim for v in prior) and series[i] >= lim:
                    out.append(Finding.at_frame("reversal", f"{name}: sustained movement flips direction at frame {i} ({prior[-1]:+.2f} -> {series[i]:+.2f})", clock.describe(i), Severity.ERROR, axis=name))
    # de-duplicate (same frame, same code, same axis)
    seen, uniq = set(), []
    for f in out:
        key = (f.code, f.frame, f.data.get("axis"))
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    return uniq


def run(args, b):
    from core.ffprobe import expected_frames, packet_pts, probe
    from core.media import FrameReader
    from core.timebase import FrameClock

    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        b.gap("opencv_missing", f"OpenCV is not installed ({exc}); install the optional extra: `uv sync --extra opencv` (or pip install opencv-python-headless)")
        b.set_frames(decoded=0, expected=None)
        return
    info = probe(args.video)
    vs = info.first_video
    exp, how = expected_frames(args.video, info)
    w, h = vs.display_size
    sw = min(w, args.max_width)
    sw -= sw % 2
    sh = max(2, int(round(h * sw / w / 2.0)) * 2)
    reader = FrameReader(args.video, pix_fmt="gray", scale=(sw, sh), timeout_s=args.timeout, info=info)
    tx, ty, ls, meas, prev = [], [], [], [], None
    for fr in reader:
        if prev is None:
            tx.append(0.0); ty.append(0.0); ls.append(0.0); meas.append(False)
        else:
            ok = False
            dx = dy = ds = 0.0
            pts = cv2.goodFeaturesToTrack(prev, maxCorners=300, qualityLevel=0.01, minDistance=8)
            if pts is not None and len(pts) >= args.min_points:
                nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, fr, pts, None, winSize=(21, 21), maxLevel=3)
                good = st.reshape(-1) == 1
                if int(good.sum()) >= args.min_points:
                    m, inl = cv2.estimateAffinePartial2D(pts[good], nxt[good], method=cv2.RANSAC, ransacReprojThreshold=2.0)
                    if m is not None and inl is not None and int(inl.sum()) >= max(args.min_points, args.min_inliers):
                        s = float(np.hypot(m[0, 0], m[1, 0]))
                        dx, dy, ds, ok = float(m[0, 2]), float(m[1, 2]), float(np.log(max(s, 1e-6))), True
            tx.append(dx); ty.append(dy); ls.append(ds); meas.append(ok)
        prev = fr.copy()
    if reader.timed_out:
        b.mark_timeout()
    if not reader.ok and not reader.timed_out:
        b.gap("decode_not_clean", f"decoder exit {reader.returncode}: {' | '.join(reader.stderr_tail[-2:])}")
    b.set_frames(decoded=reader.decoded, expected=exp, fps=vs.fps)
    pairs = max(0, len(meas) - 1)
    tracked = sum(1 for m in meas[1:] if m)
    cov = tracked / pairs if pairs else 0.0
    b.extra.update({"pairs": pairs, "tracked_pairs": tracked, "tracked_pair_coverage": round(cov, 4), "analysed_size": [sw, sh], "expected_frames_source": how})
    if pairs and (1 - cov) > args.max_unmeasured:
        b.gap("insufficient_tracked_pairs", f"only {tracked} of {pairs} frame pairs had enough tracked points (coverage {cov:.2f}); a low-feature clip proves nothing about smoothness")
        return
    if vs.is_vfr:
        pts_, tb = packet_pts(args.video)
        clock = FrameClock.from_pts(sorted(pts_), tb)
    else:
        clock = FrameClock.cfr(vs.fps, len(meas))
    for f in analyse_series(tx, ty, ls, meas, clock=clock, accel_px=args.accel_px, sigma=args.sigma, reversal_px=args.reversal_px):
        b.add(f)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="motion_qa", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--max-width", type=int, default=480)
    ap.add_argument("--accel-px", type=float, default=2.5)
    ap.add_argument("--sigma", type=float, default=6.0)
    ap.add_argument("--reversal-px", type=float, default=1.5)
    ap.add_argument("--max-unmeasured", type=float, default=0.3)
    ap.add_argument("--min-points", type=int, default=12)
    ap.add_argument("--min-inliers", type=int, default=30, help="a frame pair with fewer consistent tracks is UNMEASURED")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--json-out")
    a = ap.parse_args(argv)
    return _common.qa_main(TOOL, lambda b: run(a, b), a.video, out_json=a.json_out)


if __name__ == "__main__":
    sys.exit(main())

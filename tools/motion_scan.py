"""motion_scan - flag B-roll that is "boring/static": windows >= N seconds with almost no temporal change.

Uses FFmpeg's ``siti`` filter (ITU-T P.910 spatial / temporal information) per frame. Temporal information (TI) is the standard deviation of
the frame-to-frame luma change, so a locked-off still scores ~0 and an active shot scores much higher. A window of ``--window`` seconds
(default 1.5) whose mean TI is below ``--min-ti`` is reported as ``static`` (warning by default, ``--severity error`` to gate): "looks static /
boring" was the owner's most repeated B-roll note, and the rule is "replace the beat, don't polish it".

Limits: TI measures pixel change, not interest: a slow cinematic push can be intended. ``--min-ti`` is a starting preset (unmeasured as a
quality threshold; calibrate on footage you accept). Time = frame / rational fps. Fail-closed like every QA tool.

Usage:
    python tools/motion_scan.py <video> [--window 1.5] [--min-ti 1.0] [--severity warning|error] [--json-out r.json]
Exit: 0 PASS (warnings allowed), 1 FAIL, 2 INSUFFICIENT_EVIDENCE, 3 tool error.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

import _common  # noqa: F401

TOOL = "motion_scan"


def parse_siti(text: str):
    """-> list of (pts_time, si, ti) from `metadata=print` output."""
    rows, cur = [], {}
    for line in text.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            cur = {"t": float(m.group(1))}
            continue
        m = re.match(r"lavfi\.siti\.(si|ti)=([0-9.eE+-]+)", line.strip())
        if m and cur:
            cur[m.group(1)] = float(m.group(2))
            if "si" in cur and "ti" in cur:
                rows.append((cur["t"], cur["si"], cur["ti"]))
                cur = {}
    return rows


def static_windows(rows, *, window, min_ti, fps):
    """Pure: -> list of (start_s, end_s, mean_ti) for maximal runs where the rolling mean TI over `window` seconds is below min_ti."""
    n = max(1, int(round(window * fps)))
    ti = [r[2] for r in rows]
    if len(ti) < n:
        return []
    bad = []
    for i in range(0, len(ti) - n + 1):
        m = sum(ti[i : i + n]) / n
        bad.append((i, m < min_ti, m))
    out, cur = [], None
    for i, flag, m in bad:
        if flag:
            if cur is None:
                cur = [i, i + n, m]
            else:
                cur[1] = i + n
                cur[2] = min(cur[2], m)
        elif cur is not None:
            out.append(tuple(cur))
            cur = None
    if cur is not None:
        out.append(tuple(cur))
    return [(rows[a][0], rows[min(b, len(rows)) - 1][0], m) for a, b, m in out]


def run(a, b):
    from core.envelope import Finding, Severity
    from core.ffprobe import expected_frames, find_ffmpeg, probe
    from core.procs import run as prun
    from core.timebase import FrameClock

    info = probe(a.video)
    vs = info.first_video
    exp, how = expected_frames(a.video, info)
    tmpd = Path(tempfile.mkdtemp(prefix="avc-siti-"))
    r = prun([find_ffmpeg(), "-hide_banner", "-nostdin", "-v", "error", "-i", str(Path(a.video).resolve()), "-an", "-vf", "siti,metadata=mode=print:file=siti.txt", "-f", "null", "-"], cwd=tmpd, timeout=a.timeout)
    if r.timed_out:
        b.mark_timeout()
    f = tmpd / "siti.txt"
    if r.returncode != 0 or not f.is_file():
        b.gap("siti_failed", f"ffmpeg siti failed (exit {r.returncode}): {(r.stderr or '').strip()[-200:]} (the siti filter needs FFmpeg 5.1+)")
        b.set_frames(decoded=0, expected=exp)
        return
    rows = parse_siti(f.read_text(encoding="utf-8", errors="replace"))
    b.set_frames(decoded=len(rows), expected=exp, fps=vs.fps)
    if not rows:
        return
    fps = float(vs.fps)
    mean_ti = sum(x[2] for x in rows) / len(rows)
    b.extra.update({"mean_ti": round(mean_ti, 3), "mean_si": round(sum(x[1] for x in rows) / len(rows), 3), "window_s": a.window, "min_ti": a.min_ti})
    clock = FrameClock.cfr(vs.fps, len(rows))
    sev = Severity.ERROR if a.severity == "error" else Severity.WARNING
    for s, e, m in static_windows(rows, window=a.window, min_ti=a.min_ti, fps=fps):
        fr = int(round(s * fps))
        b.add(Finding.at_frame("static", f"almost no motion from {s:.2f}s to {e:.2f}s (mean TI {m:.2f} < {a.min_ti}): replace the beat, do not polish it", clock.describe(min(fr, len(rows) - 1)), sev, end_s=round(e, 3), mean_ti=round(m, 3)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="motion_scan", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--window", type=float, default=1.5)
    ap.add_argument("--min-ti", type=float, default=1.0)
    ap.add_argument("--severity", choices=["warning", "error"], default="warning")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--json-out")
    a = ap.parse_args(argv)
    return _common.qa_main(TOOL, lambda b: run(a, b), a.video, out_json=a.json_out)


if __name__ == "__main__":
    sys.exit(main())

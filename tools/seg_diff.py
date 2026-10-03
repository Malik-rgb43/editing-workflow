"""seg_diff - prove that a re-render (a fix) changed NOTHING outside the range you meant to change.

Compares two renders of the same project frame by frame with FFmpeg's SSIM filter and reports every frame OUTSIDE the excluded
range(s) whose SSIM is below ``--min-ssim`` (default 0.995: visually lossless re-encodes score ~0.999+; a real change scores far lower).
It spares a second full render just to check a single-scene fix (E11: the per-unit render is visually lossless, not bit-exact).

Fail-closed: both files must decode, have the same resolution and frame count and (rational) frame rate; otherwise
INSUFFICIENT_EVIDENCE with the reason. Time = frame / rational fps. An excluded range that covers every frame is also insufficient evidence.

Usage:
    python tools/seg_diff.py <before.mp4> <after.mp4> [--exclude 10.0:12.5 ...] [--min-ssim 0.995] [--json-out r.json]
Exit: 0 PASS, 1 FAIL, 2 INSUFFICIENT_EVIDENCE, 3 tool error.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import _common  # noqa: F401

TOOL = "seg_diff"


def parse_ssim_stats(text: str) -> list[float]:
    """Per-frame 'All' SSIM values from an ffmpeg ssim stats file (lines like: n:1 Y:0.99 U:0.99 V:0.99 All:0.99 (20.0))."""
    out = []
    for line in text.splitlines():
        m = re.search(r"\bn:(\d+).*?\bAll:([0-9.]+|inf|nan)", line)
        if m:
            out.append(float(m.group(2)))
    return out


def judge(scores, ranges, clock, min_ssim):
    """Pure: scores per frame + excluded time ranges -> (findings, compared_count)."""
    from core.envelope import Finding, Severity

    findings, compared = [], 0
    for i, s in enumerate(scores):
        t = float(clock.time_of(i))
        if any(a <= t < b for a, b in ranges):
            continue
        compared += 1
        if s != s or s < min_ssim:
            findings.append(Finding.at_frame("changed_outside_range", f"frame {i} differs from the previous render (SSIM {s:.4f} < {min_ssim})", clock.describe(i), Severity.ERROR, ssim=s))
    return findings, compared


def run(a, b):
    from core.ffprobe import expected_frames, find_ffmpeg, probe
    from core.procs import run as prun
    from core.timebase import FrameClock

    ia, ib = probe(a.before), probe(a.after)
    va, vb = ia.first_video, ib.first_video
    na, _ = expected_frames(a.before, ia)
    nb, _ = expected_frames(a.after, ib)
    b.set_input_sha256(__import__("hashlib").sha256(__import__("core.envelope", fromlist=["x"]).sha256_file(a.before).encode() + __import__("core.envelope", fromlist=["x"]).sha256_file(a.after).encode()).hexdigest())
    if (va.width, va.height) != (vb.width, vb.height):
        b.gap("size_mismatch", f"resolutions differ: {va.width}x{va.height} vs {vb.width}x{vb.height}")
        b.set_frames(decoded=0, expected=na)
        return
    if va.fps != vb.fps:
        b.gap("fps_mismatch", f"frame rates differ: {va.fps} vs {vb.fps}")
        b.set_frames(decoded=0, expected=na)
        return
    if na != nb or not na:
        b.gap("frame_count_mismatch", f"frame counts differ or unknown: {na} vs {nb}")
        b.set_frames(decoded=0, expected=na)
        return
    stats = Path(tempfile.mkdtemp(prefix="avc-ssim-")) / "ssim.txt"
    # run ffmpeg from the stats folder so the stats path needs no filter escaping (colons / backslashes in Windows paths)
    r = prun([find_ffmpeg(), "-hide_banner", "-nostdin", "-v", "error", "-i", str(Path(a.before).resolve()), "-i", str(Path(a.after).resolve()), "-lavfi", "ssim=stats_file=ssim.txt", "-f", "null", "-"], cwd=stats.parent, timeout=a.timeout)
    if r.timed_out:
        b.mark_timeout()
    if r.returncode != 0 or not stats.is_file():
        b.gap("ssim_failed", f"ffmpeg ssim failed (exit {r.returncode}): {(r.stderr or '').strip()[-200:]}")
        b.set_frames(decoded=0, expected=na)
        return
    scores = parse_ssim_stats(stats.read_text(encoding="utf-8", errors="replace"))
    b.set_frames(decoded=len(scores), expected=na, fps=va.fps)
    ranges = []
    for spec in a.exclude or []:
        lo, hi = spec.split(":")
        ranges.append((float(Fraction(lo)), float(Fraction(hi))))
    clock = FrameClock.cfr(va.fps, len(scores))
    findings, compared = judge(scores, ranges, clock, a.min_ssim)
    b.extra.update({"excluded_ranges_s": ranges, "frames_compared": compared, "min_ssim": a.min_ssim, "lowest_ssim_outside": min([s for i, s in enumerate(scores) if not any(lo <= float(clock.time_of(i)) < hi for lo, hi in ranges)], default=None)})
    if compared == 0:
        b.gap("nothing_compared", "the excluded range(s) cover every frame: nothing outside them was compared")
    for f in findings:
        b.add(f)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="seg_diff", description=__doc__.split("\n\n")[0])
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--exclude", action="append", help="START:END seconds that WERE meant to change (repeatable)")
    ap.add_argument("--min-ssim", type=float, default=0.995)
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--json-out")
    a = ap.parse_args(argv)
    return _common.qa_main(TOOL, lambda b: run(a, b), a.after, out_json=a.json_out)


if __name__ == "__main__":
    sys.exit(main())

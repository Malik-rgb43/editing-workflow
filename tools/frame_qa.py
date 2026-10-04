"""frame_qa - decode EVERY frame of a video and flag black frames, flashes, one-frame pops, holds and hard cuts.

Fail-closed (E04): the result is a QA envelope (contracts/qa-envelope.schema.json). PASS needs a hashed input, every expected
frame decoded and no defect; a missing file, a decoder error, a timeout or 0 decoded frames is INSUFFICIENT_EVIDENCE, never
a pass. Frame number AND real timestamp (rational fps / packet PTS) are reported for every finding.

Policy (src: distilled 03 tool-portability-and-bugs section 2, positive controls):
  * black frame  -> error   (mean luma <= --black-mean; --allow-black-edge N skips the first/last N frames, e.g. fades)
  * flash        -> error   (mean luma >= --flash-mean)
  * pop          -> error   (one frame that differs from BOTH neighbours while they match each other);
                   inside an --allow t0-t1 range (a planned fast run, e.g. images on 16th notes) it is info `pop_allowed`
  * hold         -> warning (>= --hold-frames identical frames; an intentional freeze is the author's call)
  * hard cut     -> info    (reported so other gates can treat changes there as cut-synchronised)

Limits: a luma statistic on a down-scaled copy; it does not judge taste, legibility or motion smoothness (see motion_qa, caption_qa).

Usage:
    python tools/frame_qa.py <video> [--black-mean 4] [--flash-mean 250] [--pop-diff 25] [--hold-frames 8]
                             [--cut-diff 40] [--allow-black-edge 0] [--allow t0-t1 ...] [--timeout 900] [--max-width 320] [--json-out report.json]
Exit: 0 PASS, 1 FAIL, 2 INSUFFICIENT_EVIDENCE, 3 tool error.
"""

from __future__ import annotations

import argparse
import sys

import _common  # noqa: F401  (sys.path + UTF-8)

TOOL = "frame_qa"


def analyze(means, diffs, *, clock, black_mean=4.0, flash_mean=250.0, pop_diff=25.0, hold_diff=0.05, hold_frames=8, cut_diff=40.0, allow_black_edge=0, allow_frames=frozenset()):
    """Pure function over per-frame mean luma ``means[i]`` and ``diffs[i]`` = mean |frame[i]-frame[i-1]| (diffs[0] = 0).

    Returns ``(findings, stats)``; unit-tested directly.
    """
    from core.envelope import Finding, Severity

    n = len(means)
    findings: list = []
    black = [m <= black_mean for m in means]
    flash = [m >= flash_mean for m in means]
    for i in range(n):
        if black[i] and not (i < allow_black_edge or i >= n - allow_black_edge):
            findings.append(Finding.at_frame("black_frame", f"frame {i} is black (mean luma {means[i]:.1f})", clock.describe(i), Severity.ERROR, mean=round(means[i], 2)))
        if flash[i]:
            findings.append(Finding.at_frame("flash_frame", f"frame {i} is a flash (mean luma {means[i]:.1f})", clock.describe(i), Severity.ERROR, mean=round(means[i], 2)))
    # pops: both neighbours differ strongly from frame i, yet i-1 and i+1 resemble each other
    flagged = {f.frame for f in findings}
    for i in range(1, n - 1):
        if i in flagged:
            continue
        if diffs[i] >= pop_diff and diffs[i + 1] >= pop_diff and abs(means[i + 1] - means[i - 1]) < pop_diff / 2:
            if i in allow_frames:
                findings.append(Finding.at_frame("pop_allowed", f"frame {i} jumps inside an allowed fast run (diff {diffs[i]:.1f} / {diffs[i+1]:.1f})", clock.describe(i), Severity.INFO))
            else:
                findings.append(Finding.at_frame("pop_frame", f"frame {i} differs from both neighbours (diff {diffs[i]:.1f} / {diffs[i+1]:.1f})", clock.describe(i), Severity.ERROR))
    # holds
    run_start = None
    for i in range(1, n + 1):
        still = i < n and diffs[i] <= hold_diff
        if still and run_start is None:
            run_start = i - 1
        if not still and run_start is not None:
            length = i - run_start
            if length >= hold_frames:
                findings.append(
                    Finding.at_frame("hold", f"{length} identical frames from frame {run_start} (a hold; intentional freezes are the author's call)", clock.describe(run_start), Severity.WARNING, frames=length, last_frame=i - 1)
                )
            run_start = None
    # cuts (info only)
    cuts = [i for i in range(1, n) if diffs[i] >= cut_diff and not (i in flagged)]
    for i in cuts:
        findings.append(Finding.at_frame("hard_cut", f"large change at frame {i} (diff {diffs[i]:.1f})", clock.describe(i), Severity.INFO))
    return findings, {"frames": n, "cuts": len(cuts)}


def allowed_frames(ranges, fps: float) -> frozenset:
    """Pure: ["3.38-4.45", ...] seconds -> the frame indices inside those planned fast runs."""
    out = set()
    for r in ranges or []:
        a, _, z = str(r).partition("-")
        t0, t1 = float(a), float(z)
        if not t1 > t0:
            raise ValueError(f"--allow {r!r}: expected t0-t1 seconds with t0 < t1")
        out |= set(range(int(t0 * fps), int(t1 * fps) + 1))
    return frozenset(out)


def run(args, b):
    from core.ffprobe import expected_frames, probe
    from core.media import FrameReader
    from core.timebase import FrameClock
    import numpy as np

    info = probe(args.video)
    vs = info.first_video
    exp, how = expected_frames(args.video, info)
    w, h = vs.display_size
    if w > args.max_width:
        sw = args.max_width - (args.max_width % 2)
        sh = int(round(h * sw / w / 2.0)) * 2
        scale = (sw, max(2, sh))
    else:
        scale = None
    reader = FrameReader(args.video, pix_fmt="gray", scale=scale, timeout_s=args.timeout, info=info)
    means: list[float] = []
    diffs: list[float] = []
    prev = None
    for fr in reader:
        f = fr.astype(np.int16)
        means.append(float(f.mean()))
        diffs.append(0.0 if prev is None else float(np.abs(f - prev).mean()))
        prev = f
    if reader.timed_out:
        b.mark_timeout()
    if not reader.ok and not reader.timed_out:
        b.gap("decode_not_clean", f"decoder exit {reader.returncode}, partial_tail_bytes {reader.partial_tail_bytes}: {' | '.join(reader.stderr_tail[-2:])}")
    if vs.is_vfr:
        from core.ffprobe import packet_pts

        pts, tb = packet_pts(args.video)
        clock = FrameClock.from_pts(sorted(pts), tb)
    else:
        clock = FrameClock.cfr(vs.fps, len(means))
    b.set_frames(decoded=reader.decoded, expected=exp, fps=vs.fps)
    b.extra["expected_frames_source"] = how
    b.extra["frame_size_analysed"] = [reader.width, reader.height]
    if not means:
        return
    allow = allowed_frames(args.allow, float(vs.fps))
    b.extra["allowed_fast_runs"] = args.allow or []
    findings, stats = analyze(
        means, diffs, clock=clock, black_mean=args.black_mean, flash_mean=args.flash_mean, pop_diff=args.pop_diff,
        hold_frames=args.hold_frames, cut_diff=args.cut_diff, allow_black_edge=args.allow_black_edge, allow_frames=allow,
    )
    for f in findings:
        b.add(f)
    b.extra.update(stats)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="frame_qa", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--black-mean", type=float, default=4.0)
    ap.add_argument("--flash-mean", type=float, default=250.0)
    ap.add_argument("--pop-diff", type=float, default=25.0)
    ap.add_argument("--hold-frames", type=int, default=8)
    ap.add_argument("--cut-diff", type=float, default=40.0)
    ap.add_argument("--allow-black-edge", type=int, default=0, help="ignore black in the first/last N frames (fades)")
    ap.add_argument("--allow", action="append", metavar="T0-T1", help="a planned fast run (seconds) where single-frame jumps are intended (repeatable)")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--max-width", type=int, default=320)
    ap.add_argument("--json-out")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return _common.qa_main(TOOL, lambda b: run(args, b), args.video, out_json=args.json_out)


if __name__ == "__main__":
    sys.exit(main())

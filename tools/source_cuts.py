"""source_cuts - find the hidden cuts inside a rough-cut source video and the frame ranges a cover (B-roll / zoom) must hide.

A rough cut often contains jump cuts the editor must not expose. This tool decodes the video as a STREAM (constant memory, unlike the
original which held the whole clip in RAM) at a small size, computes the mean absolute change between consecutive frames, and marks a
cut where the change is both large in absolute terms and an outlier against the clip's own motion level. Each cut gets a cover window
of +-``--margin`` frames (default 6, the house rule: cover >= 6 frames each side).

Time comes from the stream's rational fps (or packet PTS for variable-frame-rate sources), never from a constant 30. Fail-closed: a missing
file, a decode problem, a timeout or 0 frames exits 2 with a reason; "no cuts found" is only reported when every frame was decoded.

Usage:
    python tools/source_cuts.py <video> [-o src_cuts.json] [--margin 6] [--min-diff 18] [--sigma 6] [--timeout 900]
Output JSON: {schema, fps, frames, cuts:[{frame, time_s, timecode, score, cover:[first_frame, last_frame], cover_s:[a, b]}]}
Exit: 0 analysed (cuts may be empty), 2 insufficient evidence / failure, 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _common  # noqa: F401


def detect(diffs, *, min_diff=18.0, sigma=6.0, min_gap=3):
    """Pure: per-frame mean abs difference (diffs[0] = 0) -> list of (frame, score). A cut = diff >= min_diff AND >= median + sigma*MAD."""
    import statistics

    if len(diffs) < 3:
        return []
    body = diffs[1:]
    med = statistics.median(body)
    mad = statistics.median([abs(x - med) for x in body]) or 0.5
    cuts, last = [], -10**9
    for i in range(1, len(diffs)):
        d = diffs[i]
        if d >= min_diff and d >= med + sigma * mad and (i - last) >= min_gap:
            cuts.append((i, d))
            last = i
    return cuts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="source_cuts", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("-o", "--out")
    ap.add_argument("--margin", type=int, default=6)
    ap.add_argument("--min-diff", type=float, default=18.0)
    ap.add_argument("--sigma", type=float, default=6.0)
    ap.add_argument("--timeout", type=float, default=900.0)
    a = ap.parse_args(argv)

    from core.errors import ToolkitError
    from core.ffprobe import expected_frames, packet_pts, probe
    from core.fsio import write_json_atomic
    from core.media import FrameReader
    from core.timebase import FrameClock
    import numpy as np

    try:
        info = probe(a.video)
        vs = info.first_video
        exp, how = expected_frames(a.video, info)
        reader = FrameReader(a.video, pix_fmt="gray", scale=(96, 170), timeout_s=a.timeout, info=info)
        diffs, prev = [], None
        for fr in reader:
            f = fr.astype(np.int16)
            diffs.append(0.0 if prev is None else float(np.abs(f - prev).mean()))
            prev = f
    except ToolkitError as exc:
        print(f"source_cuts: {exc}", file=sys.stderr)
        return 2
    n = len(diffs)
    if reader.timed_out or not reader.ok or n == 0:
        print(f"source_cuts: INSUFFICIENT_EVIDENCE - decoded {n} frame(s), exit {reader.returncode}, timed_out={reader.timed_out}: {' | '.join(reader.stderr_tail[-2:])}", file=sys.stderr)
        return 2
    if exp is not None and n != exp:
        print(f"source_cuts: INSUFFICIENT_EVIDENCE - decoded {n} of {exp} expected frames", file=sys.stderr)
        return 2
    if vs.is_vfr:
        pts, tb = packet_pts(a.video)
        clock = FrameClock.from_pts(sorted(pts), tb)
    else:
        clock = FrameClock.cfr(vs.fps, n)
    cuts = []
    for fr_i, score in detect(diffs, min_diff=a.min_diff, sigma=a.sigma):
        lo, hi = max(0, fr_i - a.margin), min(n - 1, fr_i + a.margin - 1)
        d = clock.describe(fr_i)
        cuts.append({"frame": fr_i, "time_s": d["time_s_float"], "timecode": d["timecode"], "score": round(score, 2), "cover": [lo, hi], "cover_s": [round(float(clock.time_of(lo)), 3), round(float(clock.time_of(hi)), 3)]})
    out = {"schema": "avc.src-cuts/1", "video": Path(a.video).name, "fps": str(vs.fps), "frames": n, "analysed_size": [96, 170], "margin_frames": a.margin, "cuts": cuts}
    if a.out:
        write_json_atomic(a.out, out)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

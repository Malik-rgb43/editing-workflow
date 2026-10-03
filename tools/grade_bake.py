"""grade_bake - bake a colour grade into the A-roll as a FILE with FFmpeg ("grade = file, not attribute").

A grading shader applied at render time (``data-color-grading``) stalled the author's AMD GPU and is not reproducible across machines; a
baked plate is deterministic, previewable and cacheable. This tool applies a LUT (`.cube`) and/or simple corrections to a source clip,
re-encodes at near-lossless quality (CRF 12, H.264, yuv420p, audio copied), optionally with a PRE-ROLL (extra frames before the in-point so
the layer is ready when the composition reaches it; house value 6 frames), and writes a ``<out>.grade.json`` sidecar that records exactly what
was applied (provenance). Run it from the CAMERA ORIGINAL, not a compressed rough cut. Colour targets are a named preset
(see skill color-correction-speaker), not universal numbers.

Verification (fail-closed): the output must probe, have the same resolution and the expected frame count (source frames in range + pre-roll),
otherwise exit 2 and the output is deleted.

Usage:
    python tools/grade_bake.py <source> -o <out.mp4> [--lut grade.cube] [--eq brightness=0.03:contrast=1.05:saturation=1.1:gamma=1.0]
                               [--colorbalance "rs=0.02:bs=-0.02"] [--ss 12.0 --to 18.0] [--preroll-frames 6] [--crf 12] [--preset medium]
Exit: 0 baked and verified, 2 refused / failed, 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

import _common  # noqa: F401


def build_filters(lut, eq, colorbalance) -> str:
    chain = []
    if lut:
        p = str(Path(lut).resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
        chain.append(f"lut3d=file='{p}'")
    if eq:
        chain.append(f"eq={eq}")
    if colorbalance:
        chain.append(f"colorbalance={colorbalance}")
    return ",".join(chain)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="grade_bake", description=__doc__.split("\n\n")[0])
    ap.add_argument("source")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--lut")
    ap.add_argument("--eq")
    ap.add_argument("--colorbalance")
    ap.add_argument("--ss", type=float)
    ap.add_argument("--to", type=float)
    ap.add_argument("--preroll-frames", type=int, default=6)
    ap.add_argument("--crf", type=int, default=12)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--timeout", type=float, default=3600.0)
    a = ap.parse_args(argv)

    from core.errors import ToolkitError
    from core.envelope import sha256_file
    from core.ffprobe import expected_frames, find_ffmpeg, probe
    from core.fsio import write_json_atomic
    from core.procs import run

    filters = build_filters(a.lut, a.eq, a.colorbalance)
    if not filters:
        print("grade_bake: nothing to apply (give --lut, --eq or --colorbalance)", file=sys.stderr)
        return 2
    if a.lut and not Path(a.lut).is_file():
        print(f"grade_bake: LUT not found: {a.lut}", file=sys.stderr)
        return 2
    try:
        info = probe(a.source)
        vs = info.first_video
        fps = Fraction(vs.fps)
        total, _ = expected_frames(a.source, info)
    except ToolkitError as exc:
        print(f"grade_bake: {exc}", file=sys.stderr)
        return 2
    ss = a.ss
    pre = max(0, a.preroll_frames) if ss is not None else 0
    start = None if ss is None else max(0.0, ss - float(Fraction(pre) / fps))
    pre_actual = 0 if ss is None else int(round((ss - start) * float(fps)))
    cmd = [find_ffmpeg(), "-hide_banner", "-nostdin", "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", f"{start:.6f}"]
    cmd += ["-i", str(Path(a.source).resolve())]
    if a.to is not None:
        cmd += ["-t", f"{a.to - (start or 0.0):.6f}"]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd += ["-map", "0:v:0", "-map", "0:a?", "-vf", filters, "-c:v", "libx264", "-preset", a.preset, "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(out)]
    r = run(cmd, timeout=a.timeout)
    if r.timed_out or r.returncode != 0 or not out.is_file():
        out.unlink(missing_ok=True)
        print(f"grade_bake: ffmpeg failed (exit {r.returncode}): {(r.stderr or '').strip()[-300:]}", file=sys.stderr)
        return 2
    try:
        oi = probe(out)
        ov = oi.first_video
        n_out, _ = expected_frames(out, oi)
    except ToolkitError as exc:
        out.unlink(missing_ok=True)
        print(f"grade_bake: output unreadable: {exc}", file=sys.stderr)
        return 2
    expected = None
    if a.to is not None or ss is not None:
        end_t = a.to if a.to is not None else float(info.duration_s or 0)
        expected = int(round((end_t - (start or 0.0)) * float(fps)))
    else:
        expected = total
    problems = []
    if (ov.width, ov.height) != (vs.width, vs.height):
        problems.append(f"size changed {vs.width}x{vs.height} -> {ov.width}x{ov.height}")
    if expected is not None and n_out is not None and abs(n_out - expected) > 1:
        problems.append(f"frame count {n_out} != expected {expected}")
    if problems:
        out.unlink(missing_ok=True)
        print("grade_bake: verification failed: " + "; ".join(problems), file=sys.stderr)
        return 2
    side = {"schema": "avc.grade-bake/1", "source": Path(a.source).name, "source_sha256": sha256_file(a.source), "output": out.name, "output_sha256": sha256_file(out),
            "filters": filters, "lut": Path(a.lut).name if a.lut else None, "crf": a.crf, "range_s": [a.ss, a.to], "preroll_frames": pre_actual, "frames": n_out, "fps": str(fps),
            "note": "baked from the file named in `source`; use the camera original, not a compressed rough cut"}
    write_json_atomic(str(out) + ".grade.json", side)
    print(json.dumps({"out": str(out), "frames": n_out, "preroll_frames": pre_actual, "filters": filters}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

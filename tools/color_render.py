"""color_render - bake a fitted grade into the A-roll as a FILE: two 65^3 LUTs (GLOBAL and SUBJECT) blended by a soft person matte, one ffmpeg run.

"Grade = a file, not an attribute": a baked plate is deterministic, previewable and cacheable; a shader-node grade at render time stalled one
GPU and is not reproducible. The grade comes from ``color_fit`` (``grade.json``). The GLOBAL LUT is the whole-frame grade; the SUBJECT LUT is the same
grade plus the person-only node (lift_ev, s_wb, s_sat). With ``--matte`` ffmpeg's ``maskedmerge`` blends the two. The matte is either a grayscale
video (white = person) or a video WITH an alpha channel - a ``cutout`` WebM/ProRes is read through its alpha, never through its picture. Its frame 0 is
source time ``--matte-offset`` (0 = it covers the whole source; a cutout made with ``--from 12`` needs ``--matte-offset 12``); the matte is eroded and blurred first (a hard matte with a strong lift gives hot halos). WITHOUT a matte only the
global grade is applied and the sidecar says so (the subject node is never silently spread over the background; ``--subject-everywhere`` is the
explicit macro-shot choice). Run it from the CAMERA ORIGINAL, never from a compressed rough cut.

The output is ONE continuous constant-rate file (exact rational fps, ``-g 15``), x264 CRF 11-12, optional ``--canvas 1088x1920`` padding for the 1088-canvas
rule, optional PRE-ROLL (extra frames before ``--from``: house value 6). It is verified before it is reported: it must probe, have the requested size
and exact frame rate and the expected frame count, otherwise the file is deleted and the exit code is 2. A ``<out>.grade.json`` sidecar records the
source hash, the grade, both LUT hashes, the ffmpeg graph and whether the matte was used. Heavy: run it under ``render_lock run -- ...``.

Usage:
    python tools/color_render.py <camera-original> --params grade.json -o hf/assets/video/aroll.mp4 [--matte matte.mp4] [--from 12.0 --to 18.0]
                                 [--matte-offset S] [--fps 30] [--size 1080x1920] [--canvas 1088x1920] [--crf 11] [--preroll-frames 6] [--matte-blur 3] [--matte-erode 1]
                                 [--subject-everywhere] [--threads N] [--timeout 3600]
Exit: 0 baked and verified, 2 refused / failed verification, 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import _common  # noqa: F401


def ff_path(p) -> str:
    """The LUT is referenced by its bare file name and ffmpeg runs with the LUT folder as cwd: a path with a quote, a space or Hebrew letters never reaches the filter graph."""
    name = Path(p).name
    if not name.isascii() or not name.replace("_", "").replace(".", "").replace("-", "").isalnum():
        raise ValueError(f"unsafe LUT file name {name!r}")
    return name


def parse_size(text):
    w, h = text.lower().split("x")
    return int(w), int(h)


def colour_matte_reader(path):
    from core.matte import alpha_reader

    args, extract, _ = alpha_reader(path)
    return args, extract


def build_graph(size, fps, global_cube, subject_cube, use_matte, canvas, blur, erode, subject_everywhere, matte_extract="format=gray"):
    w, h = size
    # gbrp -> yuv420p with the default swscale flags leaves the right-most columns black on some widths (360 wide, FFmpeg 8.1); accurate_rnd avoids that path
    to_yuv = "scale=flags=accurate_rnd+full_chroma_int,format=yuv420p"
    pre = f"[0:v]scale={w}:{h}:flags=lanczos+accurate_rnd+full_chroma_int,fps={fps},format=gbrp"
    post = ""
    if canvas:
        cw, ch = canvas
        post = f",pad={cw}:{ch}:0:0:color=black"
    gl = f"lut3d=file='{ff_path(global_cube)}':interp=tetrahedral"
    sl = f"lut3d=file='{ff_path(subject_cube)}':interp=tetrahedral"
    if use_matte:
        m = f"[1:v]{matte_extract},scale={w}:{h}:flags=bilinear,fps={fps},format=gray" + ("," + ",".join(["erosion"] * erode) if erode else "") + (f",gblur=sigma={blur}" if blur else "") + ",format=gbrp[m]"
        return f"{pre},split=2[a][b];[a]{gl}[g];[b]{sl}[s];{m};[g][s][m]maskedmerge,{to_yuv}{post}[v]"
    return f"{pre},{sl if subject_everywhere else gl},{to_yuv}{post}[v]"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="color_render", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--params", required=True, help="grade.json from color_fit")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--matte")
    ap.add_argument("--matte-offset", type=float, default=0.0, help="source time (s) of the matte's first frame")
    ap.add_argument("--from", dest="start", type=float)
    ap.add_argument("--to", type=float)
    ap.add_argument("--fps", default="30")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--canvas")
    ap.add_argument("--crf", type=int, default=11)
    ap.add_argument("--preroll-frames", type=int, default=6)
    ap.add_argument("--matte-blur", type=float, default=3.0)
    ap.add_argument("--matte-erode", type=int, default=1)
    ap.add_argument("--subject-everywhere", action="store_true")
    ap.add_argument("--threads", type=int)
    ap.add_argument("--timeout", type=float, default=3600.0)
    a = ap.parse_args(argv)

    from core import colour
    from core.envelope import sha256_file
    from core.errors import ToolkitError
    from core.ffprobe import find_ffmpeg, probe
    from core.fsio import read_json, write_json_atomic
    from core.procs import run

    try:
        grade = read_json(a.params) or {}
        params = colour.full_params(grade.get("params", {}))
        size = parse_size(a.size)
        canvas = parse_size(a.canvas) if a.canvas else None
        fps = Fraction(a.fps)
        if fps <= 0:
            raise ValueError("fps must be > 0")
        if a.matte and not Path(a.matte).is_file():
            raise ValueError(f"matte not found: {a.matte}")
        info = probe(a.video)
        src_fps = info.first_video.fps
        matte_args, matte_extract = colour_matte_reader(a.matte) if a.matte else ([], "format=gray")
    except (ValueError, OSError, ToolkitError, ZeroDivisionError) as exc:
        print(f"color_render: {exc}", file=sys.stderr)
        return 2
    has_subject = any(abs(params[k] - colour.IDENTITY[k]) > 1e-9 for k in colour.SUBJECT_KEYS)
    use_matte = bool(a.matte)
    notes = []
    if has_subject and not use_matte and not a.subject_everywhere:
        notes.append("the grade has a subject node but no --matte was given: only the GLOBAL grade was applied (pass --matte, or --subject-everywhere for a macro shot)")
    pre = max(0, a.preroll_frames) if a.start is not None else 0
    start = None if a.start is None else max(0.0, a.start - float(Fraction(pre) / fps))
    pre_actual = 0 if a.start is None else int(round((a.start - start) * float(fps)))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    import hashlib

    out = out.resolve()
    cube_dir = out.parent
    tag = hashlib.sha256(json.dumps(colour.non_default(params), sort_keys=True).encode("utf-8")).hexdigest()[:8]
    gcube, scube = cube_dir / f"avc_{tag}_global.cube", cube_dir / f"avc_{tag}_subject.cube"
    colour.write_cube(gcube, colour.make_lut(params, subject=False), "avc global grade")
    colour.write_cube(scube, colour.make_lut(params, subject=True), "avc subject grade")
    matte_seek = (start or 0.0) - a.matte_offset
    if use_matte and matte_seek < -1e-6:
        print(f"color_render: the matte starts at source {a.matte_offset:.3f} s but the render starts at {start or 0.0:.3f} s (pre-roll included): make the matte cover the pre-roll too", file=sys.stderr)
        return 2
    graph = build_graph(size, a.fps, gcube, scube, use_matte, canvas, a.matte_blur, a.matte_erode, a.subject_everywhere, matte_extract)
    cmd = [find_ffmpeg(), "-hide_banner", "-nostdin", "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", f"{start:.6f}"]
    cmd += ["-i", str(Path(a.video).resolve())]
    if use_matte:
        if matte_seek > 1e-6:
            cmd += ["-ss", f"{matte_seek:.6f}"]
        cmd += [*matte_args, "-i", str(Path(a.matte).resolve())]
    if a.to is not None:
        cmd += ["-t", f"{a.to - (start or 0.0):.6f}"]
    cmd += ["-filter_complex", graph, "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", str(a.crf), "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "15", "-r", a.fps, "-fps_mode", "cfr", "-c:a", "copy", "-movflags", "+faststart"]
    if a.threads:
        cmd += ["-threads", str(a.threads)]
    cmd.append(str(out))
    r = run(cmd, timeout=a.timeout, cwd=cube_dir)
    if r.timed_out or r.returncode != 0 or not out.is_file():
        out.unlink(missing_ok=True)
        print(f"color_render: ffmpeg failed (exit {r.returncode}): {(r.stderr or '').strip()[-400:]}", file=sys.stderr)
        return 2
    problems = []
    try:
        from core.ffprobe import expected_frames

        oi = probe(out)
        ov = oi.first_video
        n_out, _ = expected_frames(out, oi)
        if canvas:
            want_size = canvas
        else:
            want_size = size
        if (ov.width, ov.height) != want_size:
            problems.append(f"size {ov.width}x{ov.height} != {want_size[0]}x{want_size[1]}")
        if ov.fps != fps:
            problems.append(f"frame rate {ov.fps} != requested {fps} (exact rational compared; variable frame rate is refused)")
        end_t = a.to if a.to is not None else float(info.duration_s or 0)
        expected = int(round((end_t - (start or 0.0)) * float(fps)))
        if n_out is not None and abs(n_out - expected) > 1:
            problems.append(f"frame count {n_out} != expected {expected}")
    except ToolkitError as exc:
        problems.append(f"output unreadable: {exc}")
    if problems:
        out.unlink(missing_ok=True)
        print("color_render: verification failed: " + "; ".join(problems), file=sys.stderr)
        return 2
    side = {"schema": "avc.color-render/1", "source": Path(a.video).name, "source_sha256": sha256_file(a.video), "source_fps": str(src_fps), "output": out.name, "output_sha256": sha256_file(out),
            "grade": colour.non_default(params), "grade_file_sha256": sha256_file(a.params), "luts": {gcube.name: sha256_file(gcube), scube.name: sha256_file(scube)}, "matte_used": use_matte,
            "matte": Path(a.matte).name if use_matte else None, "matte_read_as": matte_extract if use_matte else None, "matte_offset_s": a.matte_offset if use_matte else None, "graph": graph, "crf": a.crf, "fps": str(fps), "size": list(canvas or size), "range_s": [a.start, a.to], "preroll_frames": pre_actual,
            "frames": n_out, "notes": notes, "note": "baked from the file named in `source`; use the camera original, not a compressed rough cut; both LUTs are kept beside the output"}
    write_json_atomic(str(out) + ".grade.json", side)
    print(json.dumps({"out": str(out), "frames": n_out, "preroll_frames": pre_actual, "matte_used": use_matte, "notes": notes}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

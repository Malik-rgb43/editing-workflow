"""cutout - cut the speaker out of a clip as a transparent video (WebM VP9 alpha or ProRes 4444), ONLY for the beats that put graphics behind the speaker.

The matte is made per SHOT SEGMENT (the range is split at every cut you give, so a model's recurrent state never crosses a cut), cached by the DECODED CONTENT of
that segment + route + parameters (never by seek ranges), joined, choked (``erosion`` x N then ``gblur`` - a green fringe that is invisible over the original
plate shows over a new background) and merged with the colours of the clip you passed. Cut the matte from the CORRECTED plate (``color_render`` output), not the raw one.

Routes (``--route``):
  native    HyperFrames' own ``remove-background`` (u2net_human_seg). Always available once the engine is installed; the slowest; the safe default.
  onnx      a matting ONNX model you point at with ``--model`` (MODNet-style: input [1,3,H,W] in -1..1, output [1,1,H,W]); needs ``pip install onnxruntime``.
            ``--stride 2`` runs the model on every second frame and interpolates linearly (fine on talking heads; look at fast gestures).
  external  an alpha you already made elsewhere (``--alpha-from``: a grayscale video, or a video with an alpha channel); this tool only chokes, caches nothing and encodes.
Model weights are never downloaded here: see ``docs/en/local-vs-paid.md`` for what to download, from where, how big it is and under which licence.

Fail-closed: the output must probe, have the source's size and the exact frame count, and its alpha must not be empty; otherwise the file is deleted and the exit
code is 2. A matte that covers almost nothing or almost everything is reported as a warning in ``<out>.cutout.json`` - LOOK at the sampled frames before using it.
Heavy: run it under ``render_lock run -- ...``; matte only the ranges the beats need (plus ~2 s of handles).

Usage:
    python tools/cutout.py <clip> -o hf/assets/video/speaker.webm [--from 12.0 --to 18.0] [--route native|onnx|external]
                           [--cut-at 14.2,16.0 | --cuts src_cuts.json] [--model m.onnx] [--stride 1] [--alpha-from alpha.mp4]
                           [--erode 4] [--blur 1.8] [--quality fast|balanced|best] [--cache-dir DIR] [--no-cache] [--timeout 7200]
Exit: 0 written and verified, 2 refused / failed verification, 3 tool error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import _common  # noqa: F401

CRF = {"fast": 32, "balanced": 24, "best": 18}


def seg_filter(fa: int, fb: int) -> str:
    return f"trim=start_frame={fa}:end_frame={fb},setpts=PTS-STARTPTS"


def content_hash(ffmpeg, video, fa, fb, timeout) -> str:
    """sha256 of the DECODED frames of [fa, fb): the cache key must change when pixels change and must not when only container timing does."""
    from core.procs import run

    r = run([ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-i", str(video), "-map", "0:v:0", "-vf", seg_filter(fa, fb), "-an", "-fps_mode", "passthrough", "-f", "hash", "-hash", "sha256", "-"], timeout=timeout)
    for line in (r.stdout or "").splitlines():
        if line.startswith("SHA256="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"could not hash frames {fa}-{fb}: {(r.stderr or '').strip()[-200:]}")


def cache_key(chash: str, route: str, params: dict) -> str:
    return hashlib.sha256(json.dumps({"c": chash, "r": route, "p": params}, sort_keys=True).encode("utf-8")).hexdigest()[:24]


class Alpha:
    """Writes grayscale alpha frames to a lossless FFV1 file through one ffmpeg process."""

    def __init__(self, ffmpeg, out, w, h, fps):
        from core.procs import spawn
        import subprocess

        self.out = str(out)
        self.proc = spawn([ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "ffv1", "-pix_fmt", "gray", self.out],
                          stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        self.count = 0

    def write(self, u8):
        self.proc.popen.stdin.write(u8.tobytes())
        self.count += 1

    def close(self) -> int:
        try:
            self.proc.popen.stdin.close()
        except OSError:
            pass
        rc = self.proc.wait(timeout=600)
        err = (self.proc.popen.stderr.read() or b"").decode("utf-8", "replace")[-300:]
        self.proc.close()
        if rc != 0:
            raise RuntimeError(f"alpha encode failed: {err}")
        return self.count


def segment_native(ffmpeg, video, fa, fb, dest, tmp, timeout):
    from core import hf_engine
    from core.procs import run

    eng = hf_engine.find()
    if eng is None:
        raise RuntimeError("the HyperFrames engine is not installed (run `python install/bootstrap.py apply`); the native route needs it")
    print("cutout: native route - on its FIRST run HyperFrames downloads the u2net_human_seg model (about 176 MB, github.com/danielgatis/rembg release v0.0.0); see docs/en/local-vs-paid.md", file=sys.stderr)
    seg, mov = Path(tmp) / "seg.mp4", Path(tmp) / "seg.mov"
    r = run([ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", str(video), "-map", "0:v:0", "-vf", seg_filter(fa, fb), "-an", "-fps_mode", "passthrough", "-c:v", "libx264", "-crf", "10", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(seg)], timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"could not cut segment {fa}-{fb}: {(r.stderr or '').strip()[-200:]}")
    r = run(hf_engine.command(["remove-background", seg.name, "-o", mov.name, "--json"]), timeout=timeout, cwd=tmp, env=hf_engine.run_env())
    if r.timed_out or r.returncode != 0 or not mov.is_file():
        raise RuntimeError(f"hyperframes remove-background failed (exit {r.returncode}): {((r.stderr or '') + (r.stdout or '')).strip()[-300:]}")
    r = run([ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", str(mov), "-vf", "alphaextract,format=gray", "-c:v", "ffv1", "-pix_fmt", "gray", str(dest)], timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"could not read the alpha of the native result: {(r.stderr or '').strip()[-200:]}")


def segment_external(ffmpeg, alpha_from, reader, fa, fb, dest, timeout):
    """``reader`` = core.matte.alpha_reader(alpha_from): decoder args + extraction filter (a VP9 WebM alpha is only visible to libvpx)."""
    from core.procs import run

    dec, extract, _ = reader
    extract = f"{extract},format=gray" if extract == "alphaextract" else extract
    r = run([ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", *dec, "-i", str(alpha_from), "-map", "0:v:0", "-vf", f"{seg_filter(fa, fb)},{extract}", "-an", "-fps_mode", "passthrough", "-c:v", "ffv1", "-pix_fmt", "gray", str(dest)], timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"could not read --alpha-from for frames {fa}-{fb}: {(r.stderr or '').strip()[-200:]}")


def segment_infer(ffmpeg, video, fa, fb, dest, infer, stride, size, fps):
    """Run ``infer(rgb_uint8) -> alpha float 0..1`` over frames [fa, fb) of ``video`` and write the alpha to ``dest``. The model call is a plain callable so it can be tested."""
    from core import matte
    from core.media import FrameReader

    w, h = size
    n = fb - fa
    reader = FrameReader(video, pix_fmt="rgb24", vf=seg_filter(fa, fb), max_frames=n)
    out = Alpha(ffmpeg, dest, w, h, fps)
    try:
        for a in matte.run_with_stride(reader, n, infer, stride):
            out.write(matte.to_u8(a))
    except BaseException:
        try:
            out.close()
        except RuntimeError:
            pass
        raise
    written = out.close()
    reader.require_ok()
    if written != n:
        raise RuntimeError(f"the matte has {written} frames, expected {n}")


def make_onnx_infer(model_path):
    from core import matte

    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise RuntimeError("the onnx route needs ONNX Runtime: `uv sync --extra matte-ort` (or pip install onnxruntime; onnxruntime-directml on Windows with a GPU)") from exc
    sess = ort.InferenceSession(str(model_path), providers=ort.get_available_providers())
    name = sess.get_inputs()[0].name

    def infer(rgb):
        x, _ = matte.modnet_preprocess(rgb)
        y = sess.run(None, {name: x})[0]
        return matte.modnet_postprocess(y, rgb.shape[:2])

    return infer


def sample_alpha(ffmpeg, out, w, h, times, timeout):
    """Decode a few frames of the FINAL file and return their alpha (uint8). WebM alpha needs the libvpx-vp9 decoder named explicitly."""
    import numpy as np
    from core.procs import run

    frames = []
    for t in times:
        cmd = [ffmpeg, "-hide_banner", "-nostdin", "-v", "error"]
        if str(out).lower().endswith(".webm"):
            cmd += ["-c:v", "libvpx-vp9"]
        cmd += ["-ss", f"{t:.3f}", "-i", str(out), "-frames:v", "1", "-vf", "alphaextract,format=gray", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
        r = run(cmd, timeout=timeout, decode_stdout=False)
        buf = r.stdout_bytes or b""
        if len(buf) == w * h:
            frames.append(np.frombuffer(buf, dtype=np.uint8).reshape(h, w))
    return frames


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cutout", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("-o", "--out", required=True, help=".webm (VP9 alpha) or .mov (ProRes 4444)")
    ap.add_argument("--from", dest="start", type=float)
    ap.add_argument("--to", type=float)
    ap.add_argument("--route", choices=("native", "onnx", "external"), default="native")
    ap.add_argument("--model")
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--alpha-from")
    ap.add_argument("--cut-at", help="comma-separated seconds where the shot changes (the matte is made per segment)")
    ap.add_argument("--cuts", help="a source_cuts JSON, or a JSON list of seconds")
    ap.add_argument("--erode", type=int, default=4)
    ap.add_argument("--blur", type=float, default=1.8)
    ap.add_argument("--quality", choices=tuple(CRF), default="balanced")
    ap.add_argument("--cache-dir")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--timeout", type=float, default=7200.0)
    a = ap.parse_args(argv)

    from core import matte
    from core.envelope import sha256_file
    from core.errors import ToolkitError
    from core.ffprobe import count_decoded_frames, expected_frames, find_ffmpeg, probe
    from core.fsio import read_json, write_json_atomic
    from core.procs import run

    out = Path(a.out).resolve()
    try:
        if out.suffix.lower() not in (".webm", ".mov"):
            raise ValueError("the output must end in .webm or .mov")
        if not Path(a.video).is_file():
            raise ValueError(f"video not found: {a.video}")
        if a.route == "onnx" and not (a.model and Path(a.model).is_file()):
            raise ValueError("--route onnx needs --model <file.onnx> (the toolkit downloads no weights by itself)")
        if a.route == "external" and not (a.alpha_from and Path(a.alpha_from).is_file()):
            raise ValueError("--route external needs --alpha-from <alpha video>")
        info = probe(a.video)
        vs = info.first_video
        fps = vs.fps
        if not fps or fps <= 0:
            raise ValueError("the clip has no usable frame rate")
        if vs.is_vfr:
            raise ValueError("variable frame rate: bake the clip to a constant frame rate first (color_render does)")
        w, h = vs.display_size
        total, _how = expected_frames(a.video, info)
        if not total:
            raise ValueError("cannot tell how many frames the clip has")
        f0 = 0 if a.start is None else max(0, int(round(a.start * float(fps))))
        f1 = total if a.to is None else min(total, int(round(a.to * float(fps))))
        if f1 <= f0:
            raise ValueError("empty range")
        cuts = []
        if a.cut_at:
            cuts += [int(round(float(t) * float(fps))) for t in a.cut_at.split(",") if t.strip()]
        if a.cuts:
            cuts += matte.cut_frames_from(read_json(a.cuts), float(fps))
        segs = matte.segments(f0, f1, cuts)
        ext_reader = matte.alpha_reader(a.alpha_from) if a.route == "external" else None
    except (ValueError, OSError, ToolkitError) as exc:
        print(f"cutout: {exc}", file=sys.stderr)
        return 2

    ffmpeg = find_ffmpeg()
    out.parent.mkdir(parents=True, exist_ok=True)
    cache = Path(a.cache_dir).resolve() if a.cache_dir else out.parent / ".avc-cache" / "cutout"
    cache.mkdir(parents=True, exist_ok=True)
    params = {"model": sha256_file(a.model)[:16] if a.model else None, "stride": a.stride if a.route == "onnx" else None}
    if a.route == "native":  # a new engine may ship a new model: never reuse a matte made by another version
        from core import hf_engine

        eng = hf_engine.find()
        params["engine"] = eng.version if eng else None
    infer = None
    hits = misses = 0
    parts = []
    tmp = Path(tempfile.mkdtemp(prefix="avc-cutout-"))
    try:
        if a.route == "onnx":
            try:
                infer = make_onnx_infer(a.model)
            except RuntimeError as exc:
                print(f"cutout: {exc}", file=sys.stderr)
                return 2
        for fa, fb in segs:
            dest = None
            if a.route != "external" and not a.no_cache:
                key = cache_key(content_hash(ffmpeg, a.video, fa, fb, a.timeout), a.route, params)
                dest = cache / f"{key}.mkv"
                if dest.is_file():
                    hits += 1
                    parts.append(dest)
                    continue
            dest = dest or tmp / f"seg_{fa}_{fb}.mkv"
            part_tmp = tmp / f"part_{fa}_{fb}.mkv"
            if a.route == "native":
                segment_native(ffmpeg, a.video, fa, fb, part_tmp, tmp, a.timeout)
            elif a.route == "onnx":
                segment_infer(ffmpeg, a.video, fa, fb, part_tmp, infer, a.stride, (w, h), fps)
            else:
                segment_external(ffmpeg, a.alpha_from, ext_reader, fa, fb, part_tmp, a.timeout)
            got = count_decoded_frames(part_tmp)
            if got != fb - fa:
                raise RuntimeError(f"the matte for frames {fa}-{fb} has {got} frames, expected {fb - fa} (the model changed the frame count; refusing to mis-time the cutout)")
            shutil.move(str(part_tmp), str(dest))
            misses += 1
            parts.append(dest)
        listing = tmp / "list.txt"
        names = []
        for i, part in enumerate(parts):  # ffmpeg parses the list: only bare ASCII names go in (a quote or a Hebrew folder in the cache path would break it)
            names.append(f"p{i:04d}.mkv")
            shutil.copyfile(part, tmp / names[-1])
        listing.write_text("".join(f"file '{n}'\n" for n in names), encoding="utf-8", newline="\n")
        full = tmp / "alpha_full.mkv"
        r = run([ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing.name, "-c", "copy", full.name], timeout=a.timeout, cwd=tmp)
        if r.returncode != 0:
            raise RuntimeError(f"could not join the segment mattes: {(r.stderr or '').strip()[-200:]}")
        choke = "format=gray" + ("," + ",".join(["erosion"] * a.erode) if a.erode > 0 else "") + (f",gblur=sigma={a.blur}" if a.blur > 0 else "")
        pix = "yuva420p" if out.suffix.lower() == ".webm" else "yuva444p10le"
        graph = f"[0:v]{seg_filter(f0, f1)},format=yuv420p[c];[1:v]{choke}[a];[c][a]alphamerge,format={pix}[v]"
        enc = ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str(CRF[a.quality]), "-row-mt", "1", "-auto-alt-ref", "0"] if pix == "yuva420p" else ["-c:v", "prores_ks", "-profile:v", "4444"]
        cmd = [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", str(Path(a.video).resolve()), "-i", str(full), "-filter_complex", graph, "-map", "[v]", "-an", "-fps_mode", "passthrough", "-frames:v", str(f1 - f0), *enc, "-pix_fmt", pix, str(out)]
        r = run(cmd, timeout=a.timeout)
        if r.timed_out or r.returncode != 0 or not out.is_file():
            out.unlink(missing_ok=True)
            print(f"cutout: encode failed (exit {r.returncode}): {(r.stderr or '').strip()[-300:]}", file=sys.stderr)
            return 2
    except (RuntimeError, ValueError, ToolkitError, OSError) as exc:
        out.unlink(missing_ok=True)
        print(f"cutout: {exc}", file=sys.stderr)
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    problems = []
    try:
        oi = probe(out)
        ov = oi.first_video
        if (ov.width, ov.height) != (w, h):
            problems.append(f"size {ov.width}x{ov.height} != source {w}x{h}")
        n_out, _ = expected_frames(out, oi)
        if n_out is None:
            n_out = count_decoded_frames(out)
        if abs(n_out - (f1 - f0)) > 0:
            problems.append(f"frame count {n_out} != expected {f1 - f0}")
        dur = (f1 - f0) / float(fps)
        stats = [matte.alpha_stats(f) for f in sample_alpha(ffmpeg, out, w, h, [dur * q for q in (0.05, 0.25, 0.5, 0.75, 0.95)], 120.0)]
        verdict, notes = matte.judge_stats(stats)
        if verdict == "fail":
            problems.extend(notes)
    except (ToolkitError, OSError, RuntimeError) as exc:
        problems.append(f"output unreadable: {exc}")
        notes, stats = [], []
    if problems:
        out.unlink(missing_ok=True)
        print("cutout: verification failed: " + "; ".join(problems), file=sys.stderr)
        return 2
    side = {"schema": "avc.cutout/1", "source": Path(a.video).name, "source_sha256": sha256_file(a.video), "output": out.name, "output_sha256": sha256_file(out), "route": a.route, "frames": f1 - f0,
            "frame_range": [f0, f1], "fps": str(Fraction(fps)), "size": [w, h], "segments": [list(s) for s in segs], "cache": {"hits": hits, "misses": misses, "dir": str(cache)},
            "choke": {"erosion": a.erode, "gblur_sigma": a.blur}, "stride": a.stride if a.route == "onnx" else None, "coverage": [round(s["coverage"], 4) for s in stats], "warnings": notes,
            "note": "cut from the clip named in `source`: use the corrected plate, not the raw footage; cache keys are decoded-content hashes"}
    write_json_atomic(str(out) + ".cutout.json", side)
    print(json.dumps({"out": str(out), "frames": f1 - f0, "segments": len(segs), "cache_hits": hits, "warnings": notes}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

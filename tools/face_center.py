"""face_center - where is the speaker's face, and is it centred? (`source` measures, `audit` judges)

  source <video> -o faces.json   sample every Nth frame, detect the largest frontal face and record its normalised centre
                                 (cx, cy in 0..1) and size. Detectors (nothing is downloaded implicitly):
                                   * YuNet (OpenCV FaceDetectorYN) when ``--model yunet.onnx`` / env AVC_FACE_MODEL points to the ONNX file (MIT
                                     licence, from the OpenCV model zoo - the student downloads it knowingly; the file is NOT bundled);
                                   * otherwise OpenCV's bundled Haar cascade when this OpenCV build still has ``CascadeClassifier`` (frontal faces only;
                                     OpenCV 5 builds dropped it).
                                 With neither available the tool exits 2 and says how to get one. The faces.json contract is the same for both.
                                 Detection QUALITY is unmeasured on real footage.
  audit  <faces.json>            report ranges where the face stays off-centre by more than --tol for >= --min-run consecutive samples
                                 (QA envelope; run `source` on the RENDER and `audit` it to check the delivered framing).

Fail-closed: no OpenCV, an unreadable video, or a face found in fewer than ``--min-coverage`` of the samples exits 2 (a clip where no face is
detected proves nothing about centring). Time = frame / rational fps. The camera path from faces (`camera_path`) must be SMOOTHED:
never follow the face frame by frame (measured 139 vs 2782 px/s^2 acceleration, the reference machine).

Usage:
    python tools/face_center.py source <video> -o faces.json [--model yunet.onnx] [--every 5] [--max-width 480] [--min-coverage 0.5] [--timeout 900]
    python tools/face_center.py audit <faces.json> [--tol 0.08] [--min-run 6] [--json-out r.json]
Exit: source 0 written / 2 insufficient; audit 0 PASS / 1 FAIL / 2 INSUFFICIENT_EVIDENCE.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _common  # noqa: F401


def off_centre_runs(samples, tol=0.08, min_run=6):
    """Pure: samples [{frame, cx}] (cx None = no face) -> list of (start_idx, end_idx, mean_offset) of consecutive off-centre samples."""
    runs, cur = [], []
    for i, s in enumerate(samples):
        if s.get("cx") is not None and abs(s["cx"] - 0.5) > tol:
            cur.append(i)
        else:
            if len(cur) >= min_run:
                runs.append(cur)
            cur = []
    if len(cur) >= min_run:
        runs.append(cur)
    return [(r[0], r[-1], sum(samples[k]["cx"] - 0.5 for k in r) / len(r)) for r in runs]


def cmd_source(a) -> int:
    from core.errors import ToolkitError
    from core.ffprobe import expected_frames, probe
    from core.fsio import write_json_atomic
    from core.media import FrameReader
    from core.timebase import FrameClock

    try:
        import cv2
    except ImportError as exc:
        print(f"face_center: OpenCV is not installed ({exc}); install the extra: `uv sync --extra opencv`", file=sys.stderr)
        return 2
    import os

    detect, detector_name = None, None
    model = a.model or os.environ.get("AVC_FACE_MODEL")
    if model:
        if not Path(model).is_file():
            print(f"face_center: face model not found: {model}", file=sys.stderr)
            return 2
        if not hasattr(cv2, "FaceDetectorYN"):
            print("face_center: this OpenCV build has no FaceDetectorYN (YuNet); install a current opencv-python-headless", file=sys.stderr)
            return 2
        yn = {"det": None, "size": None}

        def detect(gray):  # noqa: F811
            h_, w_ = gray.shape[:2]
            if yn["det"] is None or yn["size"] != (w_, h_):
                yn["det"] = cv2.FaceDetectorYN.create(str(model), "", (w_, h_), 0.7, 0.3, 5000)
                yn["size"] = (w_, h_)
            _, found = yn["det"].detect(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
            return [] if found is None else [tuple(int(v) for v in f[:4]) for f in found]

        detector_name = "opencv-yunet (FaceDetectorYN; quality unmeasured on real footage)"
    elif hasattr(cv2, "CascadeClassifier") and hasattr(getattr(cv2, "data", None), "haarcascades"):
        cascade = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"))
        if cascade.empty():
            print("face_center: OpenCV's bundled face cascade could not be loaded", file=sys.stderr)
            return 2

        def detect(gray):  # noqa: F811
            return [tuple(int(v) for v in r) for r in cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(max(24, int(gray.shape[1] * 0.08)),) * 2)]

        detector_name = "opencv-haar-frontalface (fallback; frontal faces only; quality unmeasured)"
    else:
        print("face_center: no face detector available. This OpenCV build has no Haar CascadeClassifier (OpenCV 5 dropped it): download the YuNet ONNX model from the OpenCV model zoo "
              "(face_detection_yunet, MIT licence; not bundled here) and pass --model <file> (or set AVC_FACE_MODEL).", file=sys.stderr)
        return 2
    try:
        info = probe(a.video)
        vs = info.first_video
        exp, _ = expected_frames(a.video, info)
        w, h = vs.display_size
        sw = min(w, a.max_width)
        sw -= sw % 2
        sh = max(2, int(round(h * sw / w / 2.0)) * 2)
        reader = FrameReader(a.video, pix_fmt="gray", scale=(sw, sh), timeout_s=a.timeout, info=info)
        clock = FrameClock.cfr(vs.fps, exp or 1)
        samples = []
        for i, fr in enumerate(reader):
            if i % a.every:
                continue
            faces = detect(fr)
            d = clock.describe(i)
            if len(faces):
                x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
                samples.append({"frame": i, "time_s": d["time_s_float"], "cx": round((x + fw / 2) / sw, 4), "cy": round((y + fh / 2) / sh, 4), "h_norm": round(fh / sh, 4)})
            else:
                samples.append({"frame": i, "time_s": d["time_s_float"], "cx": None, "cy": None, "h_norm": None})
    except ToolkitError as exc:
        print(f"face_center: {exc}", file=sys.stderr)
        return 2
    if reader.timed_out or not reader.ok or not samples:
        print(f"face_center: INSUFFICIENT_EVIDENCE - decode not clean (exit {reader.returncode}, timed_out={reader.timed_out})", file=sys.stderr)
        return 2
    found = sum(1 for s in samples if s["cx"] is not None)
    cov = found / len(samples)
    if cov < a.min_coverage:
        print(f"face_center: INSUFFICIENT_EVIDENCE - a face was found in only {found} of {len(samples)} samples (coverage {cov:.2f} < {a.min_coverage}); the Haar fallback finds frontal faces only", file=sys.stderr)
        return 2
    out = {"schema": "avc.faces/1", "video": Path(a.video).name, "fps": str(vs.fps), "frames": reader.decoded, "every": a.every, "detector": detector_name, "coverage": round(cov, 4), "samples": samples}
    write_json_atomic(a.out, out)
    print(f"face_center: {found}/{len(samples)} samples with a face (coverage {cov:.2f}) -> {a.out}")
    return 0


def cmd_audit(a) -> int:
    from fractions import Fraction

    from core.envelope import Finding, Severity
    from core.fsio import read_json
    from core.timebase import FrameClock

    def body(b):
        d = read_json(a.faces)
        samples = d["samples"]
        clock = FrameClock.cfr(d["fps"], max(s["frame"] for s in samples) + 1)
        b.set_frames(decoded=len(samples), expected=len(samples), fps=Fraction(d["fps"]))
        b.extra["unit"] = "samples"
        measured = sum(1 for s in samples if s.get("cx") is not None)
        b.extra["coverage"] = round(measured / len(samples), 4)
        if measured / len(samples) < 0.5:
            b.gap("low_face_coverage", f"a face was measured in only {measured} of {len(samples)} samples")
        for lo, hi, off in off_centre_runs(samples, a.tol, a.min_run):
            b.add(Finding.at_frame("off_centre", f"face stays {off:+.2f} off-centre from frame {samples[lo]['frame']} to {samples[hi]['frame']} ({hi - lo + 1} samples)", clock.describe(samples[lo]["frame"]), Severity.ERROR, last_frame=samples[hi]["frame"], mean_offset=round(off, 3)))

    return _common.qa_main("face_center.audit", body, a.faces, out_json=a.json_out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="face_center", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("source")
    s.add_argument("video")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--model", help="YuNet ONNX file (MIT; downloaded by the student, never bundled); env AVC_FACE_MODEL")
    s.add_argument("--every", type=int, default=5)
    s.add_argument("--max-width", type=int, default=480)
    s.add_argument("--min-coverage", type=float, default=0.5)
    s.add_argument("--timeout", type=float, default=900.0)
    u = sub.add_parser("audit")
    u.add_argument("faces")
    u.add_argument("--tol", type=float, default=0.08)
    u.add_argument("--min-run", type=int, default=6)
    u.add_argument("--json-out")
    a = ap.parse_args(argv)
    return cmd_source(a) if a.cmd == "source" else cmd_audit(a)


if __name__ == "__main__":
    sys.exit(main())

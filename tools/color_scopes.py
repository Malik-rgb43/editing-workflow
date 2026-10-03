"""color_scopes - numeric colour measurements of sampled frames, in the shape the colour gate expects (measurements.json).

Measures, per sampled frame and from the DECODED pixels (full range BT.709 derived from RGB; 8-bit centred chroma units):
  p1 / p99          1st / 99th luma percentile, in % of full range (clipped blacks / blown highlights)
  skin_Y            mean luma of the SKIN region, % of full range            \\
  skin_chroma       mean chroma magnitude sqrt(Cb^2 + Cr^2) of the skin region  > only when --skin-roi (or a faces.json) names a person
  skin_hue          mean chroma angle atan2(Cr, Cb) of the skin region, degrees /
  black_Y, black_cb, black_cr   mean luma % and centred chroma of a black reference patch (--black-roi, e.g. a black shirt)
  sky_chroma        mean chroma magnitude of a sky/neutral reference patch (--sky-roi)
Regions are EXPLICIT rectangles (fractions x0,y0,x1,y1) or a faces.json from ``face_center`` (the skin ROI is then the central part of the
nearest face box). Nothing is guessed: a field is ``null`` when its region was not given - and the gate treats null as "not measurable", never
as a pass. The numeric targets (skin Y 46 %, hue 118, ...) are NAMED PRESETS from one reference scene (see skill color-correction-speaker),
not universal; the judging is done by that skill's ``scripts/grade_gate.py`` (``gate measurements.json --preset ...``).
This tool measures the file you point it at: use the CAMERA ORIGINAL for correction decisions and the RENDER for the final check.

Usage:
    python tools/color_scopes.py <video> -o measurements.json [--every 2.0 | --times 1.5,4,9] [--skin-roi 0.4,0.2,0.6,0.4]
                                 [--faces faces.json] [--black-roi x0,y0,x1,y1] [--sky-roi x0,y0,x1,y1] [--max-width 640] [--timeout 900]
Exit: 0 written, 2 insufficient evidence (decode problem, no samples).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import _common  # noqa: F401


def rgb_to_ycc(rgb):
    """rgb: float array (...,3) in 0..255 -> (Y 0..255, Cb, Cr centred on 0, 8-bit units; BT.709 full range)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    cb = (b - y) / 1.8556
    cr = (r - y) / 1.5748
    return y, cb, cr


def measure_region(frame, roi):
    """frame: uint8 (h,w,3); roi: (x0,y0,x1,y1) fractions -> dict(Y_pct, cb, cr, chroma, hue_deg) or None."""
    import numpy as np

    h, w = frame.shape[:2]
    x0, y0, x1, y1 = roi
    ix0, iy0, ix1, iy1 = int(x0 * w), int(y0 * h), max(int(x0 * w) + 1, int(x1 * w)), max(int(y0 * h) + 1, int(y1 * h))
    patch = frame[iy0:iy1, ix0:ix1].astype(np.float64)
    if patch.size == 0:
        return None
    y, cb, cr = rgb_to_ycc(patch)
    mcb, mcr = float(cb.mean()), float(cr.mean())
    hue = math.degrees(math.atan2(mcr, mcb)) % 360.0
    return {"Y_pct": float(y.mean()) / 255.0 * 100.0, "cb": mcb, "cr": mcr, "chroma": math.hypot(mcb, mcr), "hue_deg": hue}


def parse_roi(text):
    v = [float(x) for x in text.split(",")]
    if len(v) != 4 or not (0 <= v[0] < v[2] <= 1 and 0 <= v[1] < v[3] <= 1):
        raise ValueError(f"bad ROI {text!r}: expected x0,y0,x1,y1 as fractions with x0<x1, y0<y1")
    return tuple(v)


def face_roi(faces, t):
    """Skin ROI from the nearest faces.json sample at time t: the central part of the face box (cx, cy, h_norm)."""
    pool = [s for s in faces["samples"] if s.get("cx") is not None]
    if not pool:
        return None
    s = min(pool, key=lambda q: abs(q["time_s"] - t))
    half_h = max(0.01, s["h_norm"] * 0.18)
    half_w = half_h * 0.8
    cx, cy = s["cx"], s["cy"]
    return (max(0.0, cx - half_w), max(0.0, cy - half_h), min(1.0, cx + half_w), min(1.0, cy + half_h))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="color_scopes", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("-o", "--out", required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--every", type=float, default=2.0, help="seconds between samples")
    g.add_argument("--times", help="comma-separated seconds")
    ap.add_argument("--skin-roi")
    ap.add_argument("--faces")
    ap.add_argument("--black-roi")
    ap.add_argument("--sky-roi")
    ap.add_argument("--max-width", type=int, default=640)
    ap.add_argument("--timeout", type=float, default=900.0)
    a = ap.parse_args(argv)

    import numpy as np

    from core.envelope import sha256_file
    from core.errors import ToolkitError
    from core.ffprobe import expected_frames, probe
    from core.fsio import read_json, write_json_atomic
    from core.media import FrameReader
    from core.timebase import FrameClock

    try:
        skin_fixed = parse_roi(a.skin_roi) if a.skin_roi else None
        black = parse_roi(a.black_roi) if a.black_roi else None
        sky = parse_roi(a.sky_roi) if a.sky_roi else None
        faces = read_json(a.faces) if a.faces else None
        info = probe(a.video)
        vs = info.first_video
        exp, _ = expected_frames(a.video, info)
        fps = float(vs.fps)
        clock = FrameClock.cfr(vs.fps, exp or 1)
        if a.times:
            want = sorted({int(round(float(t) * fps)) for t in a.times.split(",") if t.strip()})
        else:
            step = max(1, int(round(a.every * fps)))
            want = list(range(0, exp or 1, step))
        w, h = vs.display_size
        sw = min(w, a.max_width)
        sw -= sw % 2
        sh = max(2, int(round(h * sw / w / 2.0)) * 2)
        wanted = set(want)
        reader = FrameReader(a.video, pix_fmt="rgb24", scale=(sw, sh), timeout_s=a.timeout, info=info)
        frames = []
        for i, fr in enumerate(reader):
            if i not in wanted:
                continue
            t = float(clock.time_of(i))
            y, _, _ = rgb_to_ycc(fr.astype(np.float64))
            p1, p99 = (float(np.percentile(y, q)) / 255.0 * 100.0 for q in (1, 99))
            rec = {"t": round(t, 3), "frame": i, "person": False, "skin_Y": None, "skin_hue": None, "skin_chroma": None, "black_Y": None, "black_cb": None, "black_cr": None, "sky_chroma": None, "p1": round(p1, 2), "p99": round(p99, 2), "bright_sky": None}
            roi = skin_fixed or (face_roi(faces, t) if faces else None)
            if roi:
                m = measure_region(fr, roi)
                if m:
                    rec.update(person=True, skin_Y=round(m["Y_pct"], 2), skin_hue=round(m["hue_deg"], 2), skin_chroma=round(m["chroma"], 2))
            if black:
                m = measure_region(fr, black)
                if m:
                    rec.update(black_Y=round(m["Y_pct"], 2), black_cb=round(m["cb"], 2), black_cr=round(m["cr"], 2))
            if sky:
                m = measure_region(fr, sky)
                if m:
                    rec.update(sky_chroma=round(m["chroma"], 2), bright_sky=m["Y_pct"] > 70.0)
            frames.append(rec)
    except (ToolkitError, ValueError, OSError, KeyError) as exc:
        print(f"color_scopes: {exc}", file=sys.stderr)
        return 2
    if reader.timed_out or not reader.ok or not frames:
        print(f"color_scopes: INSUFFICIENT_EVIDENCE - decoded {reader.decoded} frame(s), measured {len(frames)} sample(s) (exit {reader.returncode}, timed_out={reader.timed_out})", file=sys.stderr)
        return 2
    out = {"schema": "avc.color-measurements/1", "source": Path(a.video).name, "source_sha256": sha256_file(a.video), "expected_samples": len(want), "ignore": [], "units": "Y and percentiles in % of full range; chroma/Cb/Cr in 8-bit centred BT.709 units; hue in degrees atan2(Cr, Cb)", "frames": frames}
    if len(frames) != len(want):
        print(f"color_scopes: INSUFFICIENT_EVIDENCE - measured {len(frames)} of {len(want)} requested samples", file=sys.stderr)
        return 2
    write_json_atomic(a.out, out)
    print(json.dumps({"samples": len(frames), "out": a.out, "regions": {"skin": bool(skin_fixed or faces), "black": bool(black), "sky": bool(sky)}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

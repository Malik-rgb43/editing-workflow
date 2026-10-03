#!/usr/bin/env python3
"""px_measure.py - measure colour, grade and sizes from FULL-RESOLUTION frames of a reference or a draft.

Contact sheets and zoom frames are downscaled, so hex colours and pixel sizes read from them are wrong.
This tool decodes the real frame (ffmpeg, original resolution, display orientation) and measures it.

Usage:
  python px_measure.py sample <video> --at <t> --points x,y [x,y ...] [--box 5]
        median RGB of a box x box patch per point -> #RRGGBB; flags `flat: false` when the channel
        standard deviation exceeds 12 (not a flat fill: do not record it as a brand colour)
  python px_measure.py grade  <video> --at t1,t2,... [--stride 4]
        luma p1/p50/p99 (Rec.709 weights), mean saturation (max-min)/max, warm/cool = mean(R-B),
        top-8 colours in 32-level bins with their share, over the given frames
  python px_measure.py scale  <measured_px> [<measured_px> ...] --frame-width W
        convert lengths measured at the frame's width to px @ 1080 wide
  python px_measure.py --self-check

<t> is seconds (12.5) or m:ss.ms (0:12.5). Output is JSON on stdout (use --json-only to suppress notes).
Needs ffmpeg on PATH. No ffmpeg -> exit 2 (not_run); never a made-up number. The frame is decoded at the
file's native resolution; colour is as stored (BT.709 limited-range video is converted by ffmpeg's default
scaler to RGB, so values are screen-referred approximations, not a scope reading: say so in the card).
Stdlib only (Python 3.9+). Exit codes: 0 ok | 2 not_run / bad input.
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

FLAT_STD_MAX = 12.0


def parse_t(s: str) -> float:
    if ":" in s:
        parts = s.split(":")
        sec = 0.0
        for p in parts:
            sec = sec * 60 + float(p)
        return sec
    return float(s)


def grab(video: str, t: float):
    """One frame at time t as (w, h, bytes RGB24). Uses PPM so the header carries the real (rotated) size."""
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH (not_run)")
    p = subprocess.run([exe, "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "ppm", "-"],
                       capture_output=True, timeout=120)
    data = p.stdout
    if p.returncode != 0 or not data.startswith(b"P6"):
        raise RuntimeError(f"could not decode a frame at {t:.3f}s: {p.stderr.decode('utf-8', 'replace')[:200]}")
    # header: P6\nW H\n255\n
    parts, pos = [], 0
    while len(parts) < 4:
        while data[pos:pos + 1].isspace():
            pos += 1
        end = pos
        while not data[end:end + 1].isspace():
            end += 1
        parts.append(data[pos:end])
        pos = end
    pos += 1  # single whitespace after maxval
    w, h = int(parts[1]), int(parts[2])
    raw = data[pos:]
    if len(raw) != w * h * 3:
        raise RuntimeError("unexpected pixel data size")
    return w, h, raw


def px(raw, w, x, y):
    i = (y * w + x) * 3
    return raw[i], raw[i + 1], raw[i + 2]


def hex_of(rgb):
    return "#%02X%02X%02X" % tuple(int(v) for v in rgb)


def sample(video, t, points, box):
    w, h, raw = grab(video, t)
    out = []
    half = box // 2
    for (x, y) in points:
        if not (0 <= x < w and 0 <= y < h):
            out.append({"x": x, "y": y, "error": f"outside the {w}x{h} frame"})
            continue
        chans = [[], [], []]
        for yy in range(max(0, y - half), min(h, y + half + 1)):
            for xx in range(max(0, x - half), min(w, x + half + 1)):
                r, g, b = px(raw, w, xx, yy)
                chans[0].append(r)
                chans[1].append(g)
                chans[2].append(b)
        med = [statistics.median(c) for c in chans]
        sd = max(statistics.pstdev(c) for c in chans)
        out.append({"x": x, "y": y, "hex": hex_of(med), "rgb": [int(v) for v in med], "channel_std": round(sd, 2), "flat": sd <= FLAT_STD_MAX})
    return {"t_s": t, "frame_px": [w, h], "box": box, "points": out, "source": "fullres_frame"}


def grade(video, times, stride):
    lumas, sats, warm, bins = [], [], [], {}
    n = 0
    for t in times:
        w, h, raw = grab(video, t)
        for y in range(0, h, stride):
            row = y * w * 3
            for x in range(0, w, stride):
                i = row + x * 3
                r, g, b = raw[i], raw[i + 1], raw[i + 2]
                lumas.append(0.2126 * r + 0.7152 * g + 0.0722 * b)
                mx, mn = max(r, g, b), min(r, g, b)
                sats.append((mx - mn) / mx if mx else 0.0)
                warm.append(r - b)
                key = (r // 32, g // 32, b // 32)
                bins[key] = bins.get(key, 0) + 1
                n += 1
    if not n:
        raise RuntimeError("no pixels sampled")
    lumas.sort()
    q = lambda p: lumas[min(len(lumas) - 1, int(p * len(lumas)))]
    top = sorted(bins.items(), key=lambda kv: -kv[1])[:8]
    return {"frames": len(times), "pixels_sampled": n, "stride": stride,
            "luma": {"p1": round(q(0.01), 1), "p50": round(q(0.5), 1), "p99": round(q(0.99), 1)},
            "mean_saturation": round(sum(sats) / n, 4), "warm_minus_cool_mean_RminusB": round(sum(warm) / n, 2),
            "warm_cool": "warm" if sum(warm) / n > 5 else ("cool" if sum(warm) / n < -5 else "neutral"),
            "top_colours": [{"hex": hex_of([k[0] * 32 + 16, k[1] * 32 + 16, k[2] * 32 + 16]), "share": round(v / n, 4)} for k, v in top],
            "source": "fullres_frames", "note": "32-level bins: hex is the bin centre, not an exact brand colour; sample a flat fill with `sample` for that"}


def scale_px(values, frame_width):
    f = 1080.0 / frame_width
    return [{"measured_px": v, "px_at_1080": round(v * f, 1)} for v in values]


def self_check() -> int:
    exe = shutil.which("ffmpeg")
    if not exe:
        print(json.dumps({"self_check": "NOT_RUN", "reason": "ffmpeg not on PATH"}))
        return 2
    ok, fails = 0, []

    def expect(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(label)

    with tempfile.TemporaryDirectory(prefix="px_בדיקה ") as td:
        v = Path(td) / "flat.mp4"
        # left half pure-ish blue-grey flat fill, right half a gradient (not flat)
        r = subprocess.run([exe, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x336699:s=320x240:r=10:d=1", "-pix_fmt", "yuv444p", "-c:v", "libx264", "-crf", "0", str(v)], capture_output=True)
        expect("fixture encodes", r.returncode == 0 and v.is_file())
        if r.returncode == 0:
            s = sample(str(v), 0.2, [(100, 100)], 5)["points"][0]
            rgb = s["rgb"]
            expect("flat fill hex within 3 levels of #336699", all(abs(a - b) <= 3 for a, b in zip(rgb, (0x33, 0x66, 0x99))))
            expect("flat fill is flagged flat", s["flat"] is True)
            g = grade(str(v), [0.2, 0.5], 4)
            expect("grade: luma p50 plausible for #336699", 80 <= g["luma"]["p50"] <= 100)
            expect("grade: cool picture", g["warm_cool"] == "cool")
            expect("grade: top colour share is 100 %", abs(g["top_colours"][0]["share"] - 1.0) < 1e-6)
        v2 = Path(td) / "grad.mp4"
        r = subprocess.run([exe, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=10:d=1", "-pix_fmt", "yuv444p", "-c:v", "libx264", "-crf", "0", str(v2)], capture_output=True)
        if r.returncode == 0:
            s2 = sample(str(v2), 0.2, [(160, 120)], 15)["points"][0]
            expect("busy test pattern is NOT flat", s2["flat"] is False and s2["channel_std"] > FLAT_STD_MAX)
        expect("out-of-frame point reports an error, not a colour", "error" in sample(str(v), 0.2, [(9999, 5)], 5)["points"][0])
        try:
            grab(str(Path(td) / "missing.mp4"), 0.0)
            expect("missing file raises", False)
        except RuntimeError:
            expect("missing file raises", True)
    expect("scale: 740 px-wide frame, 30 px -> 43.8 px @1080", scale_px([30], 740)[0]["px_at_1080"] == 43.8)
    expect("t parsing m:ss.ms", abs(parse_t("1:02.5") - 62.5) < 1e-9)
    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": ok + len(fails), "failed": fails}))
    return 0 if not fails else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Measure colour/grade/sizes from full-resolution frames.")
    ap.add_argument("--self-check", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("sample")
    s.add_argument("video"); s.add_argument("--at", required=True); s.add_argument("--points", nargs="+", required=True); s.add_argument("--box", type=int, default=5)
    g = sub.add_parser("grade")
    g.add_argument("video"); g.add_argument("--at", required=True); g.add_argument("--stride", type=int, default=4)
    c = sub.add_parser("scale")
    c.add_argument("values", nargs="+", type=float); c.add_argument("--frame-width", type=float, required=True)
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    try:
        if a.cmd == "sample":
            pts = [tuple(int(v) for v in p.split(",")) for p in a.points]
            out = sample(a.video, parse_t(a.at), pts, a.box)
        elif a.cmd == "grade":
            out = grade(a.video, [parse_t(x) for x in a.at.split(",")], a.stride)
        elif a.cmd == "scale":
            out = scale_px(a.values, a.frame_width)
        else:
            ap.print_help()
            return 2
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as e:
        print(json.dumps({"status": "not_run", "reason": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

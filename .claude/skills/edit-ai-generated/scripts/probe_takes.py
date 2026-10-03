#!/usr/bin/env python3
"""probe_takes.py - ffprobe evidence export for AI-generated takes (free, local, no upload).

Usage:
    python probe_takes.py TAKE.mp4 [TAKE2.mp4 ...] [--out takes_probe.json] [--ffprobe PATH] [--no-hash]
    python probe_takes.py --self-check

For every file records: sha256, container duration, size, video codec / pix_fmt / width x height,
RATIONAL fps (avg and r_frame_rate), frame count when present, colour tags, audio present, and flags:
  vfr_suspect  avg_frame_rate != r_frame_rate (variable frame rate or a mislabelled clip)
  hdr_suspect  transfer smpte2084 / arib-std-b67 or BT.2020 primaries (an HDR/HLG take switches a whole render to HDR: render --sdr)
The result is the `probe.json` consumed by cutlist_check.py (native-fps gate) and the evidence a
`paid-generation-gate` provenance record needs after an authorised generation (model id, route, plan and
price timestamp are NOT in a media file: record them in the generation log).

Exit codes: 0 all files probed | 1 at least one file unreadable | 2 not_run (ffprobe not found).
A missing tool or file never passes. Stdlib only.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frac(s):
    try:
        f = Fraction(s)
        return f if f > 0 else None
    except (ValueError, ZeroDivisionError, TypeError):
        return None


def probe_one(ffprobe, path, do_hash=True):
    p = Path(path)
    if not p.is_file():
        return {"file": str(p), "take": p.stem, "error": "file not found"}
    try:
        cp = subprocess.run([ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(p)],
                            capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"file": str(p), "take": p.stem, "error": f"ffprobe failed: {e}"}
    if cp.returncode != 0:
        return {"file": str(p), "take": p.stem, "error": f"ffprobe exit {cp.returncode}: {cp.stderr.strip()[:200]}"}
    try:
        data = json.loads(cp.stdout)
    except json.JSONDecodeError:
        return {"file": str(p), "take": p.stem, "error": "ffprobe returned non-JSON"}
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if v is None:
        return {"file": str(p), "take": p.stem, "error": "no video stream"}
    avg, r = frac(v.get("avg_frame_rate", "")), frac(v.get("r_frame_rate", ""))
    dur = v.get("duration") or data.get("format", {}).get("duration")
    try:
        dur = float(dur)
    except (TypeError, ValueError):
        dur = None
    rec = {
        "file": str(p), "take": p.stem, "bytes": p.stat().st_size,
        "duration_s": dur, "codec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
        "width": v.get("width"), "height": v.get("height"),
        "fps": str(avg) if avg else None, "fps_float": float(avg) if avg else None,
        "r_frame_rate": str(r) if r else None,
        "nb_frames": int(v["nb_frames"]) if str(v.get("nb_frames", "")).isdigit() else None,
        "color_primaries": v.get("color_primaries"), "color_transfer": v.get("color_transfer"),
        "color_space": v.get("color_space"), "color_range": v.get("color_range"),
        "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
        "vfr_suspect": bool(avg and r and abs(float(avg) - float(r)) > 0.01),
        "hdr_suspect": (v.get("color_transfer") in ("smpte2084", "arib-std-b67") or v.get("color_primaries") == "bt2020"),
        "error": None,
    }
    if do_hash:
        rec["sha256"] = sha256_of(p)
    return rec


def run(files, ffprobe, do_hash=True):
    exe = ffprobe if (ffprobe and (Path(ffprobe).is_file() or shutil.which(ffprobe))) else None
    if exe is None:
        return None
    exe = shutil.which(ffprobe) or ffprobe
    return [probe_one(exe, f, do_hash) for f in files]


def self_check():
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        print("SELF-CHECK NOT RUN (ffmpeg/ffprobe not on PATH) - this is not a pass")
        return 2
    bad = []
    with tempfile.TemporaryDirectory() as td:
        clip = Path(td) / "take_a.mp4"
        cp = subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=24",
                             "-pix_fmt", "yuv420p", str(clip)], capture_output=True, text=True)
        if cp.returncode != 0:
            print("SELF-CHECK NOT RUN (ffmpeg could not create the synthetic clip):", cp.stderr.strip()[:160])
            return 2
        res = run([clip, Path(td) / "missing.mp4"], "ffprobe")
        a, b = res
        if a.get("error") or a["fps"] != "24" or abs((a["duration_s"] or 0) - 1.0) > 0.1 or a["width"] != 64:
            bad.append(f"synthetic clip mis-probed: {a}")
        if a["vfr_suspect"] or a["hdr_suspect"] or len(a.get("sha256", "")) != 64:
            bad.append("flags/hash wrong for a plain SDR CFR clip")
        if not b.get("error"):
            bad.append("missing file must report an error")
        if run([clip], "definitely-not-ffprobe-xyz") is not None:
            bad.append("missing ffprobe must be not_run (None)")
    if bad:
        print("SELF-CHECK FAILED")
        for x in bad:
            print(" -", x)
        return 1
    print("SELF-CHECK OK (4 assertions on a synthetic 1 s 24 fps clip)")
    return 0


def main(argv=None):
    try:  # Hebrew paths / non-ASCII messages must not crash on a legacy console code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--out")
    ap.add_argument("--ffprobe", default="ffprobe")
    ap.add_argument("--no-hash", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.files:
        ap.print_usage()
        return 2
    res = run(a.files, a.ffprobe, not a.no_hash)
    if res is None:
        print("NOT_RUN: ffprobe not found (install FFmpeg or pass --ffprobe). Nothing was probed; this is not a pass.")
        return 2
    for r in res:
        if r.get("error"):
            print(f"[ERROR] {r['file']}: {r['error']}")
        else:
            flags = [k for k in ("vfr_suspect", "hdr_suspect") if r[k]]
            print(f"[ok] {r['take']}: {r['width']}x{r['height']} {r['fps']} fps {r['duration_s']:.2f}s {r['codec']}/{r['pix_fmt']}"
                  f" audio={r['has_audio']}" + (f" FLAGS={flags}" if flags else ""))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"wrote {a.out}")
    return 1 if any(r.get("error") for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())

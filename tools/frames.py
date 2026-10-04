"""frames - the zoom tool of video-analysis: EVERY frame (or every Nth) of a short window around a moment, on one labelled sheet with tiles >= 280 px.

Use it on ONE instance of each distinct device (a transition type, a caption entry or exit, the hook, the end card) - 3 to 6 zooms per video, windows under about a second. The
window is decoded with an accurate seek, every tile is labelled ``f<frame> <timecode>``, at most 96 frames per call (use ``--step 2`` on 60 fps material). The sheet is written into
``<analysis folder>/sheets/zoom_NNN.jpg`` and registered in ``sheets/index.json`` (kind ``zoom``) when that folder has one.

Usage:
    python tools/frames.py <video> --at <seconds> [--pad 0.25] [--step 1] [--tile 280] [--cols 6] --out analysis/<video>
Exit: 0 sheet written, 2 refused (window too large, nothing decoded), 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import _common  # noqa: F401

MAX_FRAMES = 96
MIN_TILE = 280


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="frames", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--at", type=float, required=True)
    ap.add_argument("--pad", type=float, default=0.25)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--tile", type=int, default=MIN_TILE)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=300.0)
    a = ap.parse_args(argv)

    from core.errors import ToolkitError
    from core.ffprobe import expected_frames, find_ffmpeg, packet_pts, probe
    from core.procs import run
    from core.timebase import FrameClock, format_timestamp

    try:
        if a.step < 1 or a.pad <= 0:
            raise ValueError("--step must be >= 1 and --pad > 0")
        if a.tile < MIN_TILE:
            raise ValueError(f"--tile must be >= {MIN_TILE}: smaller tiles are misread by models")
        info = probe(a.video)
        vs = info.first_video
        total, _ = expected_frames(a.video, info)
        if vs.is_vfr:
            pts, tb = packet_pts(a.video)
            clock = FrameClock.from_pts(sorted(pts), tb)
        else:
            clock = FrameClock.cfr(vs.fps, total)
        dur = float(clock.duration() or info.duration_s or 0)
        t0, t1 = max(0.0, a.at - a.pad), min(dur, a.at + a.pad)
        if t1 <= t0:
            raise ValueError("the window is outside the video")
        f0 = clock.frame_at(Fraction(t0).limit_denominator(100000))
        if float(clock.time_of(f0)) < t0 - 1e-9:
            f0 += 1
        f1 = clock.frame_at(Fraction(t1).limit_denominator(100000))
        frames = list(range(f0, f1 + 1, a.step))
        if len(frames) > MAX_FRAMES:
            raise ValueError(f"{len(frames)} frames in the window; the limit is {MAX_FRAMES} per call (narrow --pad or raise --step)")
        if not frames:
            raise ValueError("no frame in the window")
        w, h = vs.display_size
        tw = a.tile - a.tile % 2
        th = max(2, int(round(h * tw / w / 2.0)) * 2)
        ffmpeg = find_ffmpeg()
        vf = f"scale={tw}:{th}:flags=lanczos" + (f",select='not(mod(n\\,{a.step}))'" if a.step > 1 else "")
        r = run([ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{float(clock.time_of(f0)):.6f}", "-i", str(Path(a.video).resolve()), "-map", "0:v:0", "-an", "-frames:v", str(f1 - f0 + 1),
                 "-fps_mode", "passthrough", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], timeout=a.timeout, decode_stdout=False)
        raw = r.stdout_bytes or b""
        fb = tw * th * 3
        got = len(raw) // fb
        if r.returncode != 0 or got < len(frames):
            raise RuntimeError(f"decoded {got} of {len(frames)} frames ({(r.stderr or '').strip()[-200:]})")
    except (ValueError, ToolkitError, RuntimeError) as exc:
        print(f"frames: {exc}", file=sys.stderr)
        return 2

    import numpy as np
    from PIL import Image, ImageDraw

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import sheet as sheet_tool

    font = sheet_tool._font(max(12, tw // 14))
    arr = np.frombuffer(raw[: got * fb], dtype=np.uint8).reshape(got, th, tw, 3)
    tiles = []
    for k, fr in enumerate(frames):
        im = Image.fromarray(arr[k])
        d = ImageDraw.Draw(im)
        label = f"f{fr}  {format_timestamp(clock.time_of(fr))}"
        d.rectangle([0, 0, d.textlength(label, font=font) + 8, font.size + 6], fill=(0, 0, 0))
        d.text((4, 2), label, fill=(255, 255, 255), font=font)
        tiles.append(im)
    cols = max(1, min(a.cols, len(tiles)))
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (20, 20, 20))
    for k, im in enumerate(tiles):
        sheet.paste(im, ((k % cols) * tw, (k // cols) * th))
    out = Path(a.out)
    sdir = out / "sheets"
    sdir.mkdir(parents=True, exist_ok=True)
    n = 1 + len(list(sdir.glob("zoom_*.jpg")))
    fname = f"sheets/zoom_{n:03d}.jpg"
    sheet.save(str(out / fname), quality=92)
    entry = {"file": fname, "kind": "zoom", "t_start_s": round(float(clock.time_of(frames[0])), 3), "t_end_s": round(float(clock.time_of(frames[-1])), 3), "tiles": len(tiles), "tile_px": tw,
             "frames": [{"frame": fr, "t_s": round(float(clock.time_of(fr)), 3), "label": f"f{fr}"} for fr in frames]}
    idx_path = sdir / "index.json"
    registered = False
    if idx_path.is_file():
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
        idx.setdefault("sheets", []).append(entry)
        idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        registered = True
    print(json.dumps({"sheet": str(out / fname), "frames": len(tiles), "first_frame": frames[0], "last_frame": frames[-1], "registered": registered}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

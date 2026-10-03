"""sheet - contact sheet with the frame number and real timestamp burned into every tile.

Tiles are decoded from the video (every Nth frame, or ``--times`` list), labelled ``f<frame> <timecode>`` using the stream's rational
fps / packet PTS, and written as one JPEG/PNG. Font fallback: Arial Bold -> DejaVu Sans Bold -> Pillow's built-in font (so it works on
Windows, macOS and Linux without installing anything).

Fail-closed: a missing/undecodable video or 0 tiles exits non-zero with a message; it never writes an empty sheet and says "ok".

Usage:
    python tools/sheet.py <video> -o sheet.jpg [--every 15 | --count 24 | --times 1.5,3.0,9.25] [--cols 6] [--tile-width 240]
Exit: 0 sheet written, 2 nothing could be rendered, 3 tool error.
"""

from __future__ import annotations

import argparse
import os
import sys

import _common  # noqa: F401


def _font(size: int):
    from PIL import ImageFont

    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def pick_frames(total: int, *, every: int | None, count: int | None) -> list[int]:
    if total <= 0:
        return []
    if every:
        return list(range(0, total, every))
    count = max(1, min(count or 24, total))
    if count == 1:
        return [0]
    return sorted({round(i * (total - 1) / (count - 1)) for i in range(count)})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sheet", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("-o", "--out", required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--every", type=int)
    g.add_argument("--count", type=int)
    g.add_argument("--times", help="comma-separated seconds")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--tile-width", type=int, default=240)
    ap.add_argument("--timeout", type=float, default=600.0)
    args = ap.parse_args(argv)

    from fractions import Fraction

    from core.errors import ToolkitError
    from core.ffprobe import expected_frames, packet_pts, probe
    from core.fsio import fs_path
    from core.media import FrameReader
    from core.timebase import FrameClock, format_timestamp

    try:
        info = probe(args.video)
        vs = info.first_video
        total, _ = expected_frames(args.video, info)
        if vs.is_vfr:
            pts, tb = packet_pts(args.video)
            clock = FrameClock.from_pts(sorted(pts), tb)
        else:
            clock = FrameClock.cfr(vs.fps, total)
        if args.times:
            wanted = sorted({clock.frame_at(Fraction(t.strip())) for t in args.times.split(",") if t.strip()})
        else:
            wanted = pick_frames(total or 0, every=args.every, count=args.count)
        if not wanted:
            print("sheet: nothing to render (unknown frame count or empty selection)", file=sys.stderr)
            return 2
        w, h = vs.display_size
        tw = args.tile_width - args.tile_width % 2
        th = max(2, int(round(h * tw / w / 2.0)) * 2)
        want = set(wanted)
        reader = FrameReader(args.video, pix_fmt="rgb24", scale=(tw, th), timeout_s=args.timeout, info=info)
        from PIL import Image, ImageDraw

        font = _font(max(12, tw // 14))
        tiles = []
        for i, fr in enumerate(reader):
            if i in want:
                im = Image.fromarray(fr)
                d = ImageDraw.Draw(im)
                label = f"f{i}  {format_timestamp(clock.time_of(i))}"
                d.rectangle([0, 0, d.textlength(label, font=font) + 8, font.size + 6], fill=(0, 0, 0))
                d.text((4, 2), label, fill=(255, 255, 255), font=font)
                tiles.append(im)
        if not tiles or (not reader.ok and not any(True for _ in tiles)):
            print(f"sheet: no frames decoded ({' | '.join(reader.stderr_tail[-2:])})", file=sys.stderr)
            return 2
        cols = max(1, min(args.cols, len(tiles)))
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * th), (20, 20, 20))
        for k, im in enumerate(tiles):
            sheet.paste(im, ((k % cols) * tw, (k // cols) * th))
        out = os.fspath(args.out)
        os.makedirs(os.path.dirname(fs_path(os.path.abspath(out))), exist_ok=True)
        sheet.save(fs_path(os.path.abspath(out)), quality=90) if out.lower().endswith((".jpg", ".jpeg")) else sheet.save(fs_path(os.path.abspath(out)))
        print(f"sheet: wrote {out} ({len(tiles)} tiles of {len(wanted)} requested, {cols}x{rows})")
        return 0 if len(tiles) == len(wanted) else 2
    except ToolkitError as exc:
        print(f"sheet: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

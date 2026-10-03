"""caption_qa - find caption text that vanishes (or pops in) within ONE frame, and check caption timelines for collisions.

Two independent checks, one envelope (fail-closed; see frame_qa for the contract):

1. PIXEL check (``caption_qa <video>``): counts caption-coloured pixels (luma >= --luma) inside the caption band (--roi, fractions
   x0,y0,x1,y1 of the frame, default the lower 45 %). A caption that disappears (>= 80 % drop) in one frame is an ERROR
   (``caption_vanish`` - the house rule is animate in AND out); one that appears in one frame is a WARNING by default
   (``--entrance error`` to tighten); a vanish that is immediately followed by a reappearance is ``caption_flicker`` (error).
   A change that coincides with a hard cut of the whole frame is ``cut_synchronised`` (info), not a defect. Time is computed from the
   stream's rational fps / packet PTS and printed next to the frame number (fixes E04-B02: 25 fps printed as i/30; B03: appearance).
2. TIMELINE check (``--cues cues.json``): captions are {id, start, end, bbox|keys[{t, bbox}]} in seconds; two captions that overlap in
   time AND whose boxes intersect (> --overlap-px2 square pixels) are a ``caption_collision`` error (the pixel check cannot see this:
   E04 'caption overlap' decoded 60 frames and exited 0); a box below the rail (--rail-bottom, house preset y <= 1450 of 1920) is
   ``below_rail``. Boxes are linearly interpolated between keyframes. Pass ``--canvas WxH`` for the coordinate space.

Limits: a pixel/timeline heuristic. It does NOT judge glyph legibility, Hebrew shaping, look-alike letters or colour contrast.
Busy bright backgrounds in the band raise false positives - narrow --roi or raise --luma. Coverage is stated in the envelope.

Usage:
    python tools/caption_qa.py <video> [--roi 0,0.55,1,1] [--luma 200] [--min-frac 0.0008] [--entrance warning|error|off]
                               [--cues cues.json --canvas 1080x1920 --rail-bottom 1450 --overlap-px2 16] [--json-out r.json]
    python tools/caption_qa.py --cues-only cues.json --canvas 1080x1920        (timeline check without a video; frames evidence = n/a)
Exit: 0 PASS, 1 FAIL, 2 INSUFFICIENT_EVIDENCE, 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import sys

import _common  # noqa: F401

TOOL = "caption_qa"


def pixel_events(counts, diffs, *, clock, min_px, drop=0.2, cut_diff=40.0, entrance="warning"):
    """Pure function: per-frame caption pixel counts -> findings. Unit-tested."""
    from core.envelope import Finding, Severity

    ent_sev = {"error": Severity.ERROR, "warning": Severity.WARNING, "off": None}[entrance]
    findings = []
    n = len(counts)
    i = 1
    while i < n:
        prev, cur = counts[i - 1], counts[i]
        cut = diffs[i] >= cut_diff
        if prev >= min_px and cur <= drop * prev:
            if cut:
                findings.append(Finding.at_frame("cut_synchronised", f"caption change at frame {i} coincides with a hard cut", clock.describe(i), Severity.INFO))
            else:
                back = next((j for j in range(i + 1, min(n, i + 4)) if counts[j] >= min_px and counts[j] >= 0.6 * prev), None)
                if back is not None:
                    findings.append(Finding.at_frame("caption_flicker", f"caption vanished at frame {i} and returned at frame {back}", clock.describe(i), Severity.ERROR, returns_at=back))
                else:
                    findings.append(Finding.at_frame("caption_vanish", f"caption vanished in one frame at frame {i} ({prev} -> {cur} px): no exit animation", clock.describe(i), Severity.ERROR, before_px=prev, after_px=cur))
        elif cur >= min_px and prev <= drop * cur:
            if cut:
                findings.append(Finding.at_frame("cut_synchronised", f"caption change at frame {i} coincides with a hard cut", clock.describe(i), Severity.INFO))
            elif ent_sev is not None:
                findings.append(Finding.at_frame("caption_pop_in", f"caption appeared in one frame at frame {i} ({prev} -> {cur} px): no entrance animation", clock.describe(i), ent_sev, before_px=prev, after_px=cur))
        i += 1
    return findings


def _interp(c, t):
    """Box of caption ``c`` at time ``t`` seconds or None when not visible."""
    if not (c["start"] <= t < c["end"]):
        return None
    keys = c.get("keys")
    if not keys:
        return c.get("bbox")
    keys = sorted(keys, key=lambda k: k["t"])
    if t <= keys[0]["t"]:
        return keys[0]["bbox"]
    for a, b2 in zip(keys, keys[1:]):
        if a["t"] <= t <= b2["t"]:
            u = 0.0 if b2["t"] == a["t"] else (t - a["t"]) / (b2["t"] - a["t"])
            return [a["bbox"][k] + u * (b2["bbox"][k] - a["bbox"][k]) for k in range(4)]
    return keys[-1]["bbox"]


def timeline_findings(caps, *, fps, rail_bottom=None, overlap_px2=16.0):
    """Pure function: caption list -> collision / rail findings (sampled on the frame grid)."""
    from core.envelope import Finding, Severity
    from fractions import Fraction

    findings = []
    if not caps:
        return findings, 0
    end = max(c["end"] for c in caps)
    fpsf = Fraction(fps)
    nframes = int(Fraction(str(end)) * fpsf) + 1
    seen = set()
    for f in range(nframes):
        t = float(Fraction(f) / fpsf)
        boxes = [(c["id"], _interp(c, t)) for c in caps]
        vis = [(i, bx) for i, bx in boxes if bx is not None]
        for a in range(len(vis)):
            ia, ba = vis[a]
            if rail_bottom is not None and ba[3] > rail_bottom and ("rail", ia) not in seen:
                seen.add(("rail", ia))
                findings.append(Finding("below_rail", f"caption {ia!r} bottom edge {ba[3]:.0f} is below the rail y={rail_bottom:g}", Severity.ERROR, frame=f, time_s=f"{t:.3f}", data={"id": ia, "bottom": ba[3]}))
            for b in range(a + 1, len(vis)):
                ib, bb = vis[b]
                w = min(ba[2], bb[2]) - max(ba[0], bb[0])
                h = min(ba[3], bb[3]) - max(ba[1], bb[1])
                if w > 0 and h > 0 and w * h > overlap_px2 and (ia, ib) not in seen:
                    seen.add((ia, ib))
                    findings.append(Finding("caption_collision", f"captions {ia!r} and {ib!r} overlap in time and space from frame {f} ({w:.0f}x{h:.0f} px)", Severity.ERROR, frame=f, time_s=f"{t:.3f}", data={"a": ia, "b": ib, "overlap_px2": w * h}))
    return findings, nframes


def _check_caps(caps):
    from core.errors import ToolkitError

    if not isinstance(caps, list) or not caps:
        raise ToolkitError("cues file must be a non-empty JSON list of captions")
    for c in caps:
        if not all(k in c for k in ("id", "start", "end")) or not ("bbox" in c or "keys" in c):
            raise ToolkitError(f"caption entry needs id, start, end and bbox|keys: {c!r}")
        if not c["end"] > c["start"]:
            raise ToolkitError(f"caption {c['id']!r}: end must be after start")


def run(args, b):
    from core.fsio import read_json

    caps = None
    if args.cues or args.cues_only:
        caps = read_json(args.cues or args.cues_only)
        _check_caps(caps)
    if args.cues_only:
        # no video: frames evidence does not exist for this envelope, so it can never be PASS-from-frames; use the timeline count.
        from fractions import Fraction

        fps = Fraction(args.fps)
        rail = args.rail_bottom
        fnd, nframes = timeline_findings(caps, fps=fps, rail_bottom=rail, overlap_px2=args.overlap_px2)
        for f in fnd:
            b.add(f)
        b.set_frames(decoded=nframes, expected=nframes, fps=fps)
        b.set_input_sha256(__import__("core.envelope", fromlist=["sha256_file"]).sha256_file(args.cues_only))
        b.extra["mode"] = "timeline-only"
        return
    from core.ffprobe import expected_frames, probe
    from core.media import FrameReader
    from core.timebase import FrameClock
    import numpy as np

    info = probe(args.video)
    vs = info.first_video
    exp, how = expected_frames(args.video, info)
    w, h = vs.display_size
    sw = min(w, args.max_width)
    sw -= sw % 2
    sh = max(2, int(round(h * sw / w / 2.0)) * 2)
    x0, y0, x1, y1 = [float(v) for v in args.roi.split(",")]
    rx0, ry0, rx1, ry1 = int(x0 * sw), int(y0 * sh), int(x1 * sw), int(y1 * sh)
    area = max(1, (rx1 - rx0) * (ry1 - ry0))
    min_px = max(4, int(args.min_frac * area))
    reader = FrameReader(args.video, pix_fmt="gray", scale=(sw, sh), timeout_s=args.timeout, info=info)
    counts, diffs, prev = [], [], None
    for fr in reader:
        counts.append(int((fr[ry0:ry1, rx0:rx1] >= args.luma).sum()))
        f16 = fr.astype(np.int16)
        diffs.append(0.0 if prev is None else float(np.abs(f16 - prev).mean()))
        prev = f16
    if reader.timed_out:
        b.mark_timeout()
    if not reader.ok and not reader.timed_out:
        b.gap("decode_not_clean", f"decoder exit {reader.returncode}: {' | '.join(reader.stderr_tail[-2:])}")
    if vs.is_vfr:
        from core.ffprobe import packet_pts

        pts, tb = packet_pts(args.video)
        clock = FrameClock.from_pts(sorted(pts), tb)
    else:
        clock = FrameClock.cfr(vs.fps, len(counts))
    b.set_frames(decoded=reader.decoded, expected=exp, fps=vs.fps)
    b.extra.update({"expected_frames_source": how, "roi_px": [rx0, ry0, rx1, ry1], "min_caption_px": min_px, "analysed_size": [sw, sh]})
    if counts and max(counts) < min_px:
        b.gap("no_caption_pixels_found", f"no frame has >= {min_px} caption-coloured pixels in the band; the band/threshold may be wrong, so nothing was proven about captions")
    for f in pixel_events(counts, diffs, clock=clock, min_px=min_px, cut_diff=args.cut_diff, entrance=args.entrance):
        b.add(f)
    if caps is not None:
        from fractions import Fraction

        fnd, _ = timeline_findings(caps, fps=Fraction(vs.fps), rail_bottom=args.rail_bottom, overlap_px2=args.overlap_px2)
        for f in fnd:
            b.add(f)
        b.extra["timeline_checked"] = True


def build_parser():
    ap = argparse.ArgumentParser(prog="caption_qa", description=__doc__.split("\n\n")[0])
    ap.add_argument("video", nargs="?")
    ap.add_argument("--roi", default="0,0.55,1,1")
    ap.add_argument("--luma", type=int, default=200)
    ap.add_argument("--min-frac", type=float, default=0.0008)
    ap.add_argument("--entrance", choices=["warning", "error", "off"], default="warning")
    ap.add_argument("--cut-diff", type=float, default=40.0)
    ap.add_argument("--cues")
    ap.add_argument("--cues-only")
    ap.add_argument("--fps", default="30", help="frame rate for --cues-only (rational ok: 30000/1001)")
    ap.add_argument("--rail-bottom", type=float, default=None, help="max caption bottom y in canvas pixels (house preset 1450 on 1920)")
    ap.add_argument("--overlap-px2", type=float, default=16.0)
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--max-width", type=int, default=540)
    ap.add_argument("--json-out")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if not args.video and not args.cues_only:
        ap.error("give a video, or --cues-only cues.json")
    return _common.qa_main(TOOL, lambda b: run(args, b), args.video or args.cues_only, out_json=args.json_out)


if __name__ == "__main__":
    sys.exit(main())

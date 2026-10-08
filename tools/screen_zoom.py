"""screen_zoom - for a screen recording: where things change on screen (zoom keys), dead time to cut, and narration with no screen change.

In detail: the bounding box of each change over time, the zoom that frames it, the dead time to cut or speed up, and (with --words) the
narration lines that no screen change backs up ("cue misses").

How (deterministic, local, numpy only):
  1. decode at ``--fps`` samples per second (default 4) in RGB, 320 px wide;
  2. two samples differ where any colour channel of a pixel moved more than 12 levels (colour, not grey: a red button on a grey page
     has nearly the same brightness); the frame is split into 8x8 px cells and a cell CHANGED when at least
     15 % of its pixels did (a moving mouse pointer alone stays under that);
  3. changed samples closer than 0.5 s form one change WINDOW (at most 3 s long); its changed cells are joined into connected regions
     (cells up to 2 apart count as touching) and the largest region's bounding box is the window's box (the others are listed);
  4. zoom: the box plus 15 % padding on every side, at the frame's aspect, centred on the box and kept inside the frame. The crop is never
     narrower than ``--min-crop`` of the frame (house default 0.40, i.e. at most 2.5x): screen text must stay readable after the zoom. A
     box that needs more than 80 % of the frame gets no zoom (scale 1: a page switch or a scroll);
  5. dead time: stretches with no changed cell for >= ``--dead-s`` (house default 1.5 s) and, with --words, no speech in them;
  6. cue misses (--words): lines (words split at pauses > 0.7 s) with no screen change from 1.5 s before the line to 1.5 s after it.
All numbers above are house defaults, not law: they are flags, and the output repeats them. Times are sample times (+-1/fps).

Output JSON: ``events`` [{t_s, end_s, box{x,y,w,h}, cells, other_regions}], ``zoom_keys`` [{t_s, end_s, x, y, w, h, cx, cy, crop, scale,
zoom, camera_path_zoom}] (x/y/w/h/cx/cy are fractions of the frame; ``camera_path_zoom`` = ``t0:t1:scale`` for a camera_path window),
``dead`` [{start_s, end_s, dur_s}], ``cue_misses`` [{start_s, end_s, text, nearest_change_s}] (null without --words), ``house_defaults``.
zoom.json is also a valid ``tools/camera_path.py`` input as it is: ``fps`` (the recording's frame rate) and ``samples`` [{time_s, cx}]
(each zoom window's centre at its start, middle and end) are what camera_path reads in place of faces.json, and ``camera_path_args`` holds
the matching ``--zoom t0:t1:scale`` flags. camera_path moves the frame sideways only (cx); ``cy`` is in the keys for a rig that also moves
up and down.

Usage:
    python tools/screen_zoom.py <recording> [--words words.json] -o zoom.json [--fps 4] [--min-crop 0.40] [--dead-s 1.5] [--cue-window 1.5] [--timeout 900]
    python tools/camera_path.py zoom.json <the camera_path_args from zoom.json> -o hf/camera      (the zoom keys become the camera path's windows)
Exit: 0 written, 2 refused (missing input, no video, decode not clean, bad flags), 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import _common  # noqa: F401

ANALYSIS_W = 320
CELL = 8
PIXEL_LEVEL = 12
CELL_FRAC = 0.15
JOIN_CELLS = 2
MERGE_GAP_S = 0.5
MAX_WINDOW_S = 3.0
PAD = 0.15
NO_ZOOM_CROP = 0.80
HOLD_MIN_S = 1.5  # a zoom holds at least this long (house default), independent of --dead-s
LINE_GAP_S = 0.7
SPEECH_PAD_S = 0.15


def changed_cells(prev, cur, level: int = PIXEL_LEVEL, frac: float = CELL_FRAC):
    """Pure: two frames (same shape; grey (h, w) or RGB (h, w, 3)) -> bool grid (rows, cols) of 8x8 cells where >= frac of pixels changed by > level
    in any channel."""
    import numpy as np

    h, w = prev.shape[:2]
    gh, gw = h // CELL, w // CELL
    d = np.abs(cur[: gh * CELL, : gw * CELL].astype(np.int16) - prev[: gh * CELL, : gw * CELL].astype(np.int16)) > level
    if d.ndim == 3:
        d = d.any(axis=2)
    return d.reshape(gh, CELL, gw, CELL).mean(axis=(1, 3)) >= frac


def regions(mask, join: int = JOIN_CELLS) -> list[dict]:
    """Pure: connected regions of True cells (cells up to ``join`` apart touch) -> [{cells, r0, c0, r1, c1}] largest first."""
    import numpy as np

    pts = list(zip(*np.nonzero(mask)))
    todo = set(pts)
    out = []
    while todo:
        seed = todo.pop()
        stack, comp = [seed], [seed]
        while stack:
            r, c = stack.pop()
            for dr in range(-join, join + 1):
                for dc in range(-join, join + 1):
                    q = (r + dr, c + dc)
                    if q in todo:
                        todo.remove(q)
                        stack.append(q)
                        comp.append(q)
        rs = [p[0] for p in comp]
        cs = [p[1] for p in comp]
        out.append({"cells": len(comp), "r0": int(min(rs)), "c0": int(min(cs)), "r1": int(max(rs)), "c1": int(max(cs))})
    out.sort(key=lambda g: -g["cells"])
    return out


def box_of(g: dict, rows: int, cols: int) -> dict:
    return {"x": round(g["c0"] / cols, 4), "y": round(g["r0"] / rows, 4), "w": round((g["c1"] - g["c0"] + 1) / cols, 4), "h": round((g["r1"] - g["r0"] + 1) / rows, 4)}


def zoom_for(box: dict, min_crop: float = 0.40, pad: float = PAD, no_zoom: float = NO_ZOOM_CROP) -> dict:
    """Pure: a change box (fractions of the frame) -> crop fraction, scale and a centre kept inside the frame."""
    need = max(box["w"] * (1 + 2 * pad), box["h"] * (1 + 2 * pad))
    crop = min(1.0, max(min_crop, need))
    if need > no_zoom:
        return {"crop": 1.0, "scale": 1.0, "cx": 0.5, "cy": 0.5, "zoom": False, "why": f"the change needs {need:.0%} of the frame: no zoom (page switch / scroll)"}
    half = crop / 2
    cx = min(max(box["x"] + box["w"] / 2, half), 1 - half)
    cy = min(max(box["y"] + box["h"] / 2, half), 1 - half)
    why = f"crop held at the {min_crop:.0%} minimum so text stays readable" if need < min_crop else "box + padding"
    return {"crop": round(crop, 4), "scale": round(1 / crop, 3), "cx": round(cx, 4), "cy": round(cy, 4), "zoom": True, "why": why}


def windows(change_times: list[float], merge_gap: float = MERGE_GAP_S, max_len: float = MAX_WINDOW_S) -> list[tuple[float, float]]:
    """Pure: sorted sample times with a change -> [(t0, t1)] change windows."""
    out = []
    for t in change_times:
        if out and t - out[-1][1] <= merge_gap + 1e-9 and t - out[-1][0] <= max_len + 1e-9:
            out[-1][1] = t
        else:
            out.append([t, t])
    return [(a, b) for a, b in out]


def still_ranges(changed: list[bool], fps: float, min_s: float) -> list[tuple[float, float]]:
    """Pure: changed[k] = sample k differs from sample k-1 (changed[0] ignored) -> [(t0, t1)] spans with no change lasting >= min_s."""
    out, k, n = [], 1, len(changed)
    while k < n:
        if changed[k]:
            k += 1
            continue
        j = k
        while j + 1 < n and not changed[j + 1]:
            j += 1
        t0, t1 = (k - 1) / fps, j / fps
        if t1 - t0 >= min_s - 1e-9:
            out.append((round(t0, 3), round(t1, 3)))
        k = j + 1
    return out


def subtract(spans: list[tuple[float, float]], holes: list[tuple[float, float]], min_s: float) -> list[tuple[float, float]]:
    """Pure: spans minus holes, keeping pieces >= min_s."""
    out = []
    for a, b in spans:
        pieces = [(a, b)]
        for h0, h1 in holes:
            nxt = []
            for p0, p1 in pieces:
                if h1 <= p0 or h0 >= p1:
                    nxt.append((p0, p1))
                    continue
                if h0 > p0:
                    nxt.append((p0, h0))
                if h1 < p1:
                    nxt.append((h1, p1))
            pieces = nxt
        out += [(round(p0, 3), round(p1, 3)) for p0, p1 in pieces if p1 - p0 >= min_s - 1e-9]
    return out


def lines_of(words: list[dict], gap: float = LINE_GAP_S) -> list[dict]:
    out = []
    for w in words:
        s, e = float(w["start"]), float(w["end"])
        txt = str(w.get("w", w.get("text", ""))).strip()
        if out and s - out[-1]["end_s"] <= gap:
            out[-1]["end_s"] = e
            out[-1]["text"] = (out[-1]["text"] + " " + txt).strip()
        else:
            out.append({"start_s": s, "end_s": e, "text": txt})
    return out


def cue_misses(lines: list[dict], change_times: list[float], window: float) -> list[dict]:
    """Pure: narration lines with no change sample within [start - window, end + window]."""
    out = []
    for ln in lines:
        lo, hi = ln["start_s"] - window, ln["end_s"] + window
        if any(lo <= t <= hi for t in change_times):
            continue
        near = min(change_times, key=lambda t: min(abs(t - ln["start_s"]), abs(t - ln["end_s"]))) if change_times else None
        out.append({"start_s": round(ln["start_s"], 3), "end_s": round(ln["end_s"], 3), "text": ln["text"], "nearest_change_s": None if near is None else round(near, 3)})
    return out


def analyse(frames, fps: float, *, min_crop: float, dead_s: float, words: list[dict] | None, cue_window: float) -> dict:
    """Pure over decoded samples (an iterable of equal-size uint8 grey or RGB frames at ``fps``)."""
    prev = None
    changed: list[bool] = []
    grids = []
    rows = cols = 0
    for fr in frames:
        if prev is None:
            changed.append(False)
            grids.append(None)
            rows, cols = fr.shape[0] // CELL, fr.shape[1] // CELL
        else:
            g = changed_cells(prev, fr)
            changed.append(bool(g.any()))
            grids.append(g if g.any() else None)
        prev = fr
    n = len(changed)
    if n < 2:
        raise ValueError(f"only {n} sample(s) decoded: nothing to compare")
    times = [round(k / fps, 3) for k in range(n)]
    change_times = [times[k] for k in range(1, n) if changed[k]]
    events, keys = [], []
    wins = windows(change_times)
    for i, (t0, t1) in enumerate(wins):
        import numpy as np

        mask = np.zeros((rows, cols), dtype=bool)
        for k in range(1, n):
            if grids[k] is not None and t0 - 1e-9 <= times[k] <= t1 + 1e-9:
                mask |= grids[k]
        regs = regions(mask)
        main, others = regs[0], regs[1:]
        box = box_of(main, rows, cols)
        events.append({"t_s": t0, "end_s": t1, "box": box, "cells": main["cells"], "other_regions": [dict(box_of(g, rows, cols), cells=g["cells"]) for g in others[:5]]})
        z = zoom_for(box, min_crop)
        nxt = wins[i + 1][0] if i + 1 < len(wins) else times[-1]
        hold_to = round(min(max(t1, t0 + HOLD_MIN_S), max(nxt, t1)), 3)
        keys.append({"t_s": t0, "end_s": hold_to, **box, **z, "camera_path_zoom": f"{t0:g}:{hold_to:g}:{z['scale']:g}" if z["zoom"] and hold_to > t0 else None})
    still = still_ranges(changed, fps, dead_s)
    misses = None
    if words is not None:
        speech = [(float(w["start"]) - SPEECH_PAD_S, float(w["end"]) + SPEECH_PAD_S) for w in words]
        dead = subtract(still, speech, dead_s)
        misses = cue_misses(lines_of(words), change_times, cue_window)
    else:
        dead = still
    zoomed = [k for k in keys if k["camera_path_zoom"]]
    cam_samples = sorted(({"time_s": round(t, 3), "cx": k["cx"]} for k in zoomed for t in (k["t_s"], (k["t_s"] + k["end_s"]) / 2, k["end_s"])), key=lambda s: s["time_s"])
    return {"sample_count": n, "duration_s": round((n - 1) / fps, 3), "events": events, "zoom_keys": keys,
            "samples": cam_samples, "camera_path_args": [x for k in zoomed for x in ("--zoom", k["camera_path_zoom"])],
            "dead": [{"start_s": a, "end_s": b, "dur_s": round(b - a, 3)} for a, b in dead], "cue_misses": misses,
            "speech_checked": words is not None, "grid": [rows, cols]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="screen_zoom", description=__doc__.split("\n\n")[0])
    ap.add_argument("recording")
    ap.add_argument("--words", help="avc.words/1 file of the narration (same timeline as the recording)")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--fps", type=float, default=4.0, help="samples per second (house default 4)")
    ap.add_argument("--min-crop", type=float, default=0.40, help="narrowest crop as a fraction of the frame (house default 0.40 = at most 2.5x)")
    ap.add_argument("--dead-s", type=float, default=1.5, help="shortest dead stretch (house default 1.5 s)")
    ap.add_argument("--cue-window", type=float, default=1.5, help="a line needs a screen change within this many seconds (house default 1.5)")
    ap.add_argument("--timeout", type=float, default=900.0)
    a = ap.parse_args(argv)
    if not Path(a.recording).is_file():
        print(f"screen_zoom: input not found: {a.recording}", file=sys.stderr)
        return 2
    if not 0 < a.fps <= 30 or not 0.1 <= a.min_crop <= 1.0 or a.dead_s <= 0 or a.cue_window < 0:
        print("screen_zoom: bad flags (0 < --fps <= 30, 0.1 <= --min-crop <= 1, --dead-s > 0, --cue-window >= 0)", file=sys.stderr)
        return 2
    words = None
    if a.words:
        if not Path(a.words).is_file():
            print(f"screen_zoom: input not found: {a.words}", file=sys.stderr)
            return 2
        try:
            doc = json.loads(Path(a.words).read_text(encoding="utf-8"))
            words = doc.get("words") if isinstance(doc, dict) else doc
            if not isinstance(words, list) or not all(isinstance(w, dict) and "start" in w and "end" in w for w in words):
                raise ValueError("no words with start/end")
        except (OSError, ValueError) as exc:
            print(f"screen_zoom: cannot read {a.words}: {exc}", file=sys.stderr)
            return 2
    from core.errors import ToolkitError
    from core.ffprobe import probe
    from core.media import FrameReader

    try:
        info = probe(a.recording)
        vs = info.first_video
        w, h = vs.display_size
    except (ToolkitError, OSError, ValueError, AttributeError, IndexError) as exc:
        print(f"screen_zoom: no readable video in {a.recording}: {exc}", file=sys.stderr)
        return 2
    try:
        aw = min(ANALYSIS_W, w)
        aw -= aw % 2
        ah = max(CELL * 2, int(round(h * aw / w / 2.0)) * 2)
        reader = FrameReader(a.recording, pix_fmt="rgb24", scale=(aw, ah), vf=f"fps={a.fps:g}", timeout_s=a.timeout, info=info)
        res = analyse(reader, a.fps, min_crop=a.min_crop, dead_s=a.dead_s, words=words, cue_window=a.cue_window)
        if not reader.ok:
            print(f"screen_zoom: decode not clean ({reader.decoded} samples, exit {reader.returncode}, timed out {reader.timed_out}): {' | '.join(reader.stderr_tail[-2:])}", file=sys.stderr)
            return 2
    except ValueError as exc:
        print(f"screen_zoom: {exc}", file=sys.stderr)
        return 2
    except ToolkitError as exc:
        print(f"screen_zoom: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"screen_zoom: tool error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    src_fps = vs.fps or 30
    res["camera_path_args"] += ["--duration", f"{float(info.duration_s or res['duration_s']):g}"] if res["camera_path_args"] else []
    out = {"schema": "avc.screen_zoom/1", "input": Path(a.recording).name, "source_size": [w, h], "analysed_size": [aw, ah], "sample_fps": a.fps,
           "fps": str(src_fps), **res,
           "house_defaults": {"pixel_level": PIXEL_LEVEL, "cell_px": CELL, "cell_changed_frac": CELL_FRAC, "join_cells": JOIN_CELLS, "merge_gap_s": MERGE_GAP_S,
                              "max_window_s": MAX_WINDOW_S, "hold_min_s": HOLD_MIN_S, "padding": PAD, "min_crop": a.min_crop, "no_zoom_above_crop": NO_ZOOM_CROP, "dead_s": a.dead_s,
                              "cue_window_s": a.cue_window, "line_gap_s": LINE_GAP_S},
           "notes": ["times are sample times: +-1/fps", "min_crop is a house default so screen text stays readable; raise it for small UI text"]
           + ([] if words is not None else ["no --words: dead time ignores speech and cue misses are not checked"])}
    from core.fsio import write_json_atomic

    write_json_atomic(a.out, out)
    print(json.dumps({"out": a.out, "events": len(out["events"]), "zooms": sum(1 for k in out["zoom_keys"] if k["zoom"]), "dead": len(out["dead"]),
                      "dead_s": round(math.fsum(d["dur_s"] for d in out["dead"]), 3), "cue_misses": None if out["cue_misses"] is None else len(out["cue_misses"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

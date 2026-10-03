#!/usr/bin/env python3
"""safe_zone_check.py - check key text, CTA, price, logo and the caption rail against the house safe-zone preset.

The preset (references/safe_zone_presets.json, "house preset v1", dated, UNVERIFIED on devices) is a
conservative union of owner-cited platform numbers, not platform law. Geometry can pass; the gate can
only be `pass` with appearance evidence: an overlay snapshot you looked at.

Usage:
  python safe_zone_check.py <elements.json> --aspect 9x16 [--row master|meta|tiktok|tiktok_he|yt_shorts]
                            [--overlay-evidence snapshot.png] [--require cta,price] [--presets FILE] [--json]
  python safe_zone_check.py --self-check

elements.json:
  {"canvas": [1080, 1920],            (optional: the authoring canvas; 1088 wide is accepted for 1080-wide presets)
   "elements": [{"id": "headline", "role": "headline", "kind": "key", "x0": 140, "y0": 320, "x1": 900, "y1": 520,
                 "t_start": 0.0, "t_end": 2.0},
                {"id": "cap", "role": "caption", "kind": "caption", "x0": 140, "y0": 1250, "x1": 888, "y1": 1420}, ...]}
  kind: key (headline, CTA, price, logo, number: strict zone) | caption (rail: sides as key, bottom <= rail limit)
  role: headline | cta | price | logo | caption | other     (boxes in canvas px, x0 < x1, y0 < y1)

Exit codes: 0 PASS (geometry ok AND overlay evidence file exists) | 1 FAIL (a box leaves its zone) |
2 INSUFFICIENT_EVIDENCE (no key element, a required role missing, no overlay evidence, unreadable file).
Elements not given are not checked: list every element that carries text, price, CTA or logo, per timestamp
that matters (hook, offer, end card). Stdlib only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

VERSION = "0.1.0"
DEFAULT_PRESETS = Path(__file__).resolve().parent.parent / "references" / "safe_zone_presets.json"


def _no_const(n):
    raise ValueError("non-standard JSON constant: " + n)


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"), parse_constant=_no_const)


def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def check(elements_doc, presets, aspect, row=None, overlay=None, require=("cta",)):
    f = []
    if aspect not in presets.get("aspects", {}):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": f"aspect {aspect!r} not in the preset"}, 2
    a = presets["aspects"][aspect]
    row_name = row or a.get("default_row", "master")
    if row_name not in a["rows"]:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": f"row {row_name!r} not in the preset for {aspect}"}, 2
    z = a["rows"][row_name]
    W, H = a["canvas"]
    canvas = elements_doc.get("canvas")
    if canvas is not None:
        cw, ch = canvas
        allowed_w = [W] + a.get("authoring_width_alternatives", [])
        if ch != H or cw not in allowed_w:
            f.append({"severity": "fail", "code": "CANVAS", "element": None, "message": f"authoring canvas {cw}x{ch} does not match {aspect} ({W}x{H}; width alternatives {a.get('authoring_width_alternatives', [])})"})
    els = elements_doc.get("elements")
    if not isinstance(els, list) or not els:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no elements listed: an empty sample never passes"}, 2
    rail = a.get("caption_rail_bottom_max")
    n_key = 0
    roles = set()
    checked = []
    for e in els:
        eid = e.get("id", "?")
        if not all(isnum(e.get(k)) for k in ("x0", "y0", "x1", "y1")) or not (e["x0"] < e["x1"] and e["y0"] < e["y1"]):
            f.append({"severity": "fail", "code": "BOX", "element": eid, "message": "x0 < x1 and y0 < y1 numbers are required"})
            continue
        kind = e.get("kind")
        if kind not in ("key", "caption"):
            f.append({"severity": "fail", "code": "KIND", "element": eid, "message": "kind must be key or caption"})
            continue
        roles.add(e.get("role", "other"))
        if e["x0"] < 0 or e["y0"] < 0 or e["x1"] > W + (8 if canvas and canvas[0] != W else 0) or e["y1"] > H:
            f.append({"severity": "fail", "code": "OFF_CANVAS", "element": eid, "message": f"box leaves the {W}x{H} canvas"})
        left, right, top, bottom = z["left"], W - z["right"], z["top"], H - z["bottom"]
        miss = []
        if kind == "key":
            n_key += 1
            if e["x0"] < left: miss.append(f"x0 {e['x0']} < left {left}")
            if e["x1"] > right: miss.append(f"x1 {e['x1']} > {right} (right margin {z['right']})")
            if e["y0"] < top: miss.append(f"y0 {e['y0']} < top {top}")
            if e["y1"] > bottom: miss.append(f"y1 {e['y1']} > {bottom} (bottom margin {z['bottom']})")
        else:
            if e["x0"] < left: miss.append(f"x0 {e['x0']} < left {left}")
            if e["x1"] > right: miss.append(f"x1 {e['x1']} > {right}")
            lim = rail if rail is not None else bottom
            if e["y1"] > lim: miss.append(f"rail bottom y1 {e['y1']} > {lim}")
        if miss:
            f.append({"severity": "fail", "code": "OUTSIDE_ZONE", "element": eid, "message": "; ".join(miss)})
        checked.append(eid)
    if n_key == 0:
        f.append({"severity": "insufficient", "code": "NO_KEY_ELEMENT", "element": None, "message": "no key element (headline/CTA/price/logo) listed"})
    for r in require:
        if r and r not in roles:
            f.append({"severity": "insufficient", "code": "ROLE_MISSING", "element": None, "message": f"required role {r!r} has no element: the CTA/price must be checked too"})
    ev_ok = bool(overlay) and Path(overlay).is_file() and Path(overlay).stat().st_size > 0
    if not ev_ok:
        f.append({"severity": "insufficient", "code": "NO_OVERLAY_EVIDENCE", "element": None, "message": "geometry only: no overlay snapshot given. A pass needs the viewed overlay at the hook, offer and end card (appearance evidence)"})
    fails = [x for x in f if x["severity"] == "fail"]
    insuff = [x for x in f if x["severity"] == "insufficient"]
    status = "FAIL" if fails else ("INSUFFICIENT_EVIDENCE" if insuff else "PASS")
    return {"tool": "safe_zone_check", "version": VERSION, "status": status, "aspect": aspect, "row": row_name, "zone": z, "canvas": [W, H],
            "rail_bottom_max": rail, "elements_checked": checked, "findings": f, "preset": presets.get("preset"), "preset_checked_at": presets.get("checked_at"),
            "limits": ["house preset v1: proposed, unverified on devices; a viewed overlay on a real viewport is the evidence that matters",
                       "box coordinates come from your spec or DOM probe: a wrong box passes a correct check"]}, {"PASS": 0, "FAIL": 1}.get(status, 2)


def self_check() -> int:
    ok, fails = 0, []

    def expect(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(label)

    presets = load(DEFAULT_PRESETS)
    a = presets["aspects"]["9x16"]["rows"]
    expect("preset: master is the union of the strictest platform rows (every side)",
           all(a["master"][s] >= max(a[r][s] for r in ("meta", "tiktok", "yt_shorts")) for s in ("top", "bottom", "left", "right")))
    expect("preset: master bottom 672 -> key text y <= 1248", 1920 - a["master"]["bottom"] == 1248)
    expect("preset: rail limit 1450", presets["aspects"]["9x16"]["caption_rail_bottom_max"] == 1450)
    good = {"canvas": [1088, 1920], "elements": [
        {"id": "headline", "role": "headline", "kind": "key", "x0": 140, "y0": 300, "x1": 888, "y1": 520},
        {"id": "cta", "role": "cta", "kind": "key", "x0": 200, "y0": 1000, "x1": 880, "y1": 1248},
        {"id": "cap", "role": "caption", "kind": "caption", "x0": 140, "y0": 1250, "x1": 888, "y1": 1450}]}
    with tempfile.TemporaryDirectory(prefix="sz_בדיקה ") as td:
        ov = Path(td) / "overlay.png"
        ov.write_bytes(b"\x89PNG-fake")
        out, code = check(good, presets, "9x16", overlay=str(ov))
        expect("boxes on the limits pass with overlay evidence", code == 0 and out["status"] == "PASS")
        out, code = check(good, presets, "9x16")
        expect("geometry ok but no overlay -> INSUFFICIENT_EVIDENCE (not pass)", code == 2 and any(x["code"] == "NO_OVERLAY_EVIDENCE" for x in out["findings"]))
        bad = json.loads(json.dumps(good)); bad["elements"][1]["y1"] = 1300
        out, code = check(bad, presets, "9x16", overlay=str(ov))
        expect("CTA below y 1248 -> FAIL", code == 1 and any(x["code"] == "OUTSIDE_ZONE" and x["element"] == "cta" for x in out["findings"]))
        bad = json.loads(json.dumps(good)); bad["elements"][2]["y1"] = 1500
        expect("caption rail below y 1450 -> FAIL", check(bad, presets, "9x16", overlay=str(ov))[1] == 1)
        bad = json.loads(json.dumps(good)); bad["elements"][0]["x1"] = 900
        expect("right margin 192 enforced (x1 <= 888)", check(bad, presets, "9x16", overlay=str(ov))[1] == 1)
        bad = json.loads(json.dumps(good)); bad["elements"][0]["y0"] = 250
        expect("top margin 300 enforced", check(bad, presets, "9x16", overlay=str(ov))[1] == 1)
        out, code = check({"elements": []}, presets, "9x16", overlay=str(ov))
        expect("empty element list never passes", code == 2)
        only_caps = {"elements": [good["elements"][2]]}
        expect("captions only: no key element -> INSUFFICIENT_EVIDENCE", check(only_caps, presets, "9x16", overlay=str(ov))[1] == 2)
        nocta = {"elements": good["elements"][:1] + good["elements"][2:]}
        expect("required role missing (cta) -> INSUFFICIENT_EVIDENCE", check(nocta, presets, "9x16", overlay=str(ov))[1] == 2)
        expect("tiktok_he row demands 140 on both sides", check({"elements": [{"id": "cta", "role": "cta", "kind": "key", "x0": 100, "y0": 400, "x1": 900, "y1": 700}]}, presets, "9x16", row="tiktok_he", overlay=str(ov))[1] == 1)
        sq = {"canvas": [1080, 1080], "elements": [{"id": "cta", "role": "cta", "kind": "key", "x0": 54, "y0": 54, "x1": 1026, "y1": 1026}]}
        expect("1:1 54 px margins pass exactly", check(sq, presets, "1x1", overlay=str(ov))[1] == 0)
        wide = {"canvas": [1920, 1080], "elements": [{"id": "cta", "role": "cta", "kind": "key", "x0": 96, "y0": 54, "x1": 1825, "y1": 900}]}
        expect("16:9 x <= 1824 enforced", check(wide, presets, "16x9", overlay=str(ov))[1] == 1)
        wrong_canvas = {"canvas": [1080, 1350], "elements": good["elements"]}
        expect("canvas of another aspect -> FAIL", check(wrong_canvas, presets, "9x16", overlay=str(ov))[1] == 1)
        expect("unknown aspect -> INSUFFICIENT_EVIDENCE", check(good, presets, "21x9")[1] == 2)
    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": ok + len(fails), "failed": fails}))
    return 0 if not fails else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Check boxes against the house safe-zone preset.")
    ap.add_argument("elements", nargs="?")
    ap.add_argument("--aspect", default="9x16")
    ap.add_argument("--row")
    ap.add_argument("--overlay-evidence")
    ap.add_argument("--require", default="cta")
    ap.add_argument("--presets", default=str(DEFAULT_PRESETS))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.elements:
        ap.print_help()
        return 2
    try:
        out, code = check(load(Path(a.elements)), load(Path(a.presets)), a.aspect, a.row, a.overlay_evidence, tuple(x for x in a.require.split(",") if x))
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(json.dumps({"status": "INSUFFICIENT_EVIDENCE", "reason": str(e)}, ensure_ascii=False))
        return 2
    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(out["status"] + (f": {out.get('reason')}" if out.get("reason") else ""))
        if "zone" in out:
            print(f"  {out['aspect']} row {out['row']}: margins {out['zone']} canvas {out['canvas']} rail<= {out['rail_bottom_max']}")
        for x in out.get("findings", []):
            print(f"  [{x['severity']}] {x['code']}" + (f" {x['element']}" if x.get("element") else "") + f": {x['message']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

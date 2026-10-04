"""color_check - measure the FINAL render for the colour gate: skin, black, sky and highlight numbers every N seconds, in the shape grade_gate.py judges.

A thin, fail-closed layer over ``color_scopes``: it samples the file every ``--step`` seconds (default 2), measures only where a person region is KNOWN
(``--faces`` from ``face_center`` or an explicit ``--skin-roi``; with neither it refuses - a skin band judged on pixels chosen BECAUSE they are skin-coloured
would be circular), skips frames with no person, and records ``--ignore t0-t1`` ranges for deliberate colour-drain beats (an approved beat written in PROMPT.md).
Black clothing and sky are measured only when their regions are given (``--black-roi``, ``--sky-roi``); otherwise those fields stay null and the gate
treats them as "not measurable" (declare them n/a there, never pass). It judges nothing itself: pass the JSON to
``speaker-color-correction/scripts/grade_gate.py gate``.

Usage:
    python tools/color_check.py <final.mp4> -o measurements.json (--faces faces.json | --skin-roi x0,y0,x1,y1) [--step 2] [--ignore 43-46.5 ...]
                                [--black-roi x0,y0,x1,y1] [--sky-roi x0,y0,x1,y1] [--width 270]
Exit: 0 written, 2 refused / insufficient evidence.
"""

from __future__ import annotations

import argparse
import json
import sys

import _common  # noqa: F401


def parse_ignore(items):
    out = []
    for it in items or []:
        a, _, b = it.partition("-")
        t0, t1 = float(a), float(b)
        if not (0 <= t0 < t1):
            raise ValueError(f"bad --ignore {it!r}: expected t0-t1 seconds with t0 < t1")
        out.append([t0, t1])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="color_check", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--step", type=float, default=2.0)
    ap.add_argument("--ignore", action="append")
    ap.add_argument("--faces")
    ap.add_argument("--skin-roi")
    ap.add_argument("--black-roi")
    ap.add_argument("--sky-roi")
    ap.add_argument("--width", type=int, default=270)
    ap.add_argument("--timeout", type=float, default=900.0)
    a = ap.parse_args(argv)
    if not a.faces and not a.skin_roi:
        print("color_check: refused - no person region. Give --faces (run `face_center source` first) or --skin-roi; nothing is guessed.", file=sys.stderr)
        return 2
    try:
        ignore = parse_ignore(a.ignore)
    except ValueError as exc:
        print(f"color_check: {exc}", file=sys.stderr)
        return 2
    import color_scopes

    sargs = [a.video, "-o", a.out, "--every", str(a.step), "--max-width", str(a.width), "--timeout", str(a.timeout)]
    for flag, val in (("--faces", a.faces), ("--skin-roi", a.skin_roi), ("--black-roi", a.black_roi), ("--sky-roi", a.sky_roi)):
        if val:
            sargs += [flag, val]
    rc = color_scopes.main(sargs)
    if rc != 0:
        return rc
    from core.fsio import read_json, write_json_atomic

    data = read_json(a.out)
    data["ignore"] = ignore
    data["tool"] = "color_check"
    data["step_s"] = a.step
    people = sum(1 for f in data["frames"] if f.get("person"))
    data["frames_with_person"] = people
    if people == 0:
        print("color_check: INSUFFICIENT_EVIDENCE - no sampled frame had a person region (faces.json empty or ROI outside the frame)", file=sys.stderr)
        return 2
    write_json_atomic(a.out, data)
    print(json.dumps({"out": a.out, "samples": len(data["frames"]), "with_person": people, "ignore": ignore}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

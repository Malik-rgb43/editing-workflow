#!/usr/bin/env python3
"""plan_lint.py - lint a talking-head edit PLAN (data/edit_plan.json) against gates G3, G4, G5.

It checks the plan file only. A passing plan proves nothing about rendered pixels:
run face_center audit, motion_qa, frame_qa and a visual review on the render.

Usage:
    python -X utf8 plan_lint.py data/edit_plan.json [--json report.json] [--margin 6] [--zoom-cap 1.40]
    python -X utf8 plan_lint.py --self-check

Exit codes: 0 = PASS, 1 = FAIL or INSUFFICIENT_EVIDENCE (fail closed), 2 = usage error.

Schema: the fields read below (beats, cuts, overlays). Times are OUTPUT seconds.
Defaults (house preset v1, decision default Q5 - overridable in the plan):
    cadence_max_gap_s 6.0, zoom_max_gap_s 4.0, open_push_within_s 1.0,
    cover margin 6 frames each side, A->A join cover below 15 % scale change,
    overlay width <= 860 px, zoom cap 1.40 (warning only).
"""
import hashlib
import json
import sys

VERSION = "0.1.0"
BEAT_TYPES = {"real_footage", "3d", "2_5d", "ui", "data", "speaker_only"}
ZOOM_KINDS = {"push_in", "punch_in", "punch_out", "pull_back"}
STATES = ("pass", "fail", "blocked", "n/a")


def chk(cid, gate, state, reason):
    assert state in STATES
    return {"id": cid, "gate": gate, "state": state, "reason": reason}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _boxes_intersect(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def lint(plan, margin_override=None, zoom_cap=1.40):
    checks, warnings = [], []
    req = ["fps", "duration_s", "beats", "zooms", "source_cuts", "joins"]
    missing = [k for k in req if k not in plan]
    if missing:
        checks.append(chk("P0", "schema", "blocked", "missing keys: " + ", ".join(missing)))
        return checks, warnings, {}
    fps, dur = plan["fps"], plan["duration_s"]
    if not (_num(fps) and fps > 0 and _num(dur) and dur > 0):
        checks.append(chk("P0", "schema", "blocked", "fps and duration_s must be positive numbers"))
        return checks, warnings, {}
    margin = margin_override if margin_override is not None else plan.get("cover_margin_frames", 6)
    cad_max = plan.get("cadence_max_gap_s", 6.0)
    zoom_gap = plan.get("zoom_max_gap_s", 4.0)
    open_push = plan.get("open_push_within_s", 1.0)
    beats, zooms = plan["beats"], plan["zooms"]
    cov = {"beats": len(beats), "zooms": len(zooms), "source_cuts": len(plan["source_cuts"]),
           "joins": len(plan["joins"])}
    checks.append(chk("P0", "schema", "pass", "required keys present"))

    # ---- G5 beats
    if not beats:
        checks.append(chk("G5.types", "G5", "blocked", "empty beat list: no evidence"))
    else:
        bad = [b.get("id", "?") for b in beats if b.get("type") not in BEAT_TYPES]
        checks.append(chk("G5.types", "G5", "fail" if bad else "pass",
                          ("unknown beat type: " + ", ".join(map(str, bad))) if bad else "all beat types from the menu"))
        framed = [b.get("id", "?") for b in beats if b.get("type") != "speaker_only" and b.get("full_bleed") is not True]
        checks.append(chk("G5.full_bleed", "G5", "fail" if framed else "pass",
                          ("not full-bleed: " + ", ".join(map(str, framed))) if framed else "every beat full-bleed"))
        shows = sorted((b["start"], b["end"]) for b in beats
                       if b.get("type") in BEAT_TYPES - {"speaker_only"} and _num(b.get("start")) and _num(b.get("end")))
        edges, cur, worst = [], 0.0, 0.0
        for s, e in shows:
            worst = max(worst, s - cur)
            cur = max(cur, e)
        worst = max(worst, dur - cur)
        checks.append(chk("G5.cadence", "G5", "fail" if worst > cad_max else "pass",
                          "longest stretch without a showing beat %.2f s (max %.1f s)" % (worst, cad_max)))
        over_bad, over_blocked = [], []
        faces = plan.get("face_boxes", [])
        for b in beats:
            ov = b.get("overlay")
            if not ov:
                continue
            if _num(ov.get("width_px")) and ov["width_px"] > 860:
                over_bad.append("%s width %s > 860" % (b.get("id", "?"), ov["width_px"]))
            if ov.get("box"):
                if not faces:
                    over_blocked.append(b.get("id", "?"))
                else:
                    for fb in faces:
                        if fb["t0"] < b["end"] and b["start"] < fb["t1"] and _boxes_intersect(ov["box"], fb["box"]):
                            over_bad.append("%s overlay crosses the face box" % b.get("id", "?"))
        if over_bad:
            checks.append(chk("G5.overlay", "G5", "fail", "; ".join(over_bad)))
        elif over_blocked:
            checks.append(chk("G5.overlay", "G5", "blocked", "overlay boxes without face_boxes: " + ", ".join(map(str, over_blocked))))
        else:
            checks.append(chk("G5.overlay", "G5", "pass" if any(b.get("overlay") for b in beats) else "n/a",
                              "overlay cards <= 860 px and clear of the face" if any(b.get("overlay") for b in beats) else "no overlay cards"))

    # ---- G4 zoom
    if not zooms:
        checks.append(chk("G4.zooms", "G4", "blocked", "empty zoom list: no evidence"))
    else:
        bad_kind = [z for z in zooms if z.get("kind") not in ZOOM_KINDS]
        checks.append(chk("G4.kinds", "G4", "fail" if bad_kind else "pass",
                          "unknown zoom kind" if bad_kind else "zoom kinds valid"))
        no_face = [z.get("t") for z in zooms if not _num(z.get("face_x"))]
        checks.append(chk("G4.face_x", "G4", "fail" if no_face else "pass",
                          ("zoom without a numeric face_x at t=%s" % no_face) if no_face else "faceX logged at every zoom"))
        uneased = [z.get("t") for z in zooms if z.get("eased") is not True]
        checks.append(chk("G4.eased", "G4", "fail" if uneased else "pass",
                          ("not eased at t=%s" % uneased) if uneased else "all zooms eased"))
        ts = sorted(z["t"] for z in zooms if _num(z.get("t")))
        has_open = any(z.get("kind") == "push_in" and _num(z.get("t")) and z["t"] <= open_push for z in zooms)
        checks.append(chk("G4.open_push", "G4", "pass" if has_open else "fail",
                          "opening push-in within %.1f s" % open_push if has_open else "no push_in within %.1f s of the start" % open_push))
        gaps = [b - a for a, b in zip(ts, ts[1:])] + ([dur - ts[-1]] if ts else [])
        wg = max(gaps) if gaps else 0.0
        checks.append(chk("G4.rhythm", "G4", "fail" if wg > zoom_gap else "pass",
                          "longest stretch without a camera event %.2f s (max %.1f s)" % (wg, zoom_gap)))
        big = [z.get("t") for z in zooms if _num(z.get("scale_to")) and z["scale_to"] > zoom_cap]
        if big:
            warnings.append("scale_to above house cap %.2f at t=%s (chin vs chest captions)" % (zoom_cap, big))

    # ---- G3 hidden cuts and joins
    covers = plan.get("covers", [])
    m_s = margin / float(fps)
    unc = []
    for sc in plan["source_cuts"]:
        t = sc.get("out_s")
        if not _num(t):
            unc.append("cut without out_s")
            continue
        if not any(c["start"] <= t - m_s + 1e-9 and c["end"] >= t + m_s - 1e-9 for c in covers):
            unc.append("%.2f s" % t)
    checks.append(chk("G3.source_cuts", "G3", "fail" if unc else "pass",
                      ("uncovered (margin %d f each side): %s" % (margin, ", ".join(unc))) if unc
                      else "%d source cut(s), all covered with >= %d frames margin" % (len(plan["source_cuts"]), margin)))
    jbad = []
    for j in plan["joins"]:
        d = j.get("scale_delta_pct")
        if not _num(d):
            jbad.append("join without scale_delta_pct")
            continue
        covered = j.get("covered") is True or any(c["start"] <= j["out_s"] <= c["end"] for c in covers)
        if d < 15 and not covered:
            jbad.append("A->A join at %.2f s with %s %% scale change and no cover" % (j["out_s"], d))
    checks.append(chk("G3.joins", "G3", "fail" if jbad else "pass", "; ".join(jbad) if jbad else "all joins covered or >= 15 % scale change"))
    return checks, warnings, cov


def report(plan, **kw):
    checks, warnings, cov = lint(plan, **kw)
    states = [c["state"] for c in checks]
    if "fail" in states:
        status = "FAIL"
    elif "blocked" in states:
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "PASS"
    return {"tool": "plan_lint", "version": VERSION, "status": status, "coverage": cov,
            "checks": checks, "warnings": warnings}


def _good_plan():
    return {
        "fps": 30, "duration_s": 24.0,
        "beats": [
            {"id": "b1", "start": 0.0, "end": 4.0, "type": "3d", "full_bleed": True},
            {"id": "b2", "start": 5.0, "end": 9.0, "type": "real_footage", "full_bleed": True,
             "overlay": {"width_px": 820, "box": [130, 1180, 950, 1400]}},
            {"id": "b3", "start": 10.0, "end": 14.0, "type": "ui", "full_bleed": True},
            {"id": "b4", "start": 15.0, "end": 19.0, "type": "data", "full_bleed": True},
            {"id": "b5", "start": 20.0, "end": 24.0, "type": "2_5d", "full_bleed": True},
        ],
        "zooms": [{"t": 0.3, "kind": "push_in", "scale_from": 1.0, "scale_to": 1.14, "face_x": 520, "eased": True},
                  {"t": 3.0, "kind": "punch_in", "scale_to": 1.2, "face_x": 520, "eased": True},
                  {"t": 6.0, "kind": "punch_out", "scale_to": 1.0, "face_x": 515, "eased": True},
                  {"t": 9.0, "kind": "punch_in", "scale_to": 1.2, "face_x": 515, "eased": True},
                  {"t": 12.0, "kind": "punch_out", "scale_to": 1.0, "face_x": 510, "eased": True},
                  {"t": 15.0, "kind": "punch_in", "scale_to": 1.2, "face_x": 510, "eased": True},
                  {"t": 18.0, "kind": "punch_out", "scale_to": 1.0, "face_x": 505, "eased": True},
                  {"t": 21.0, "kind": "punch_in", "scale_to": 1.2, "face_x": 505, "eased": True}],
        "face_boxes": [{"t0": 0.0, "t1": 24.0, "box": [380, 420, 700, 820]}],
        "source_cuts": [{"out_s": 12.4}],
        "covers": [{"start": 12.1, "end": 13.0}],
        "joins": [{"out_s": 17.0, "scale_delta_pct": 18, "covered": False}],
    }


def self_check():
    import copy
    ok = True

    def expect(name, plan, want):
        nonlocal ok
        got = report(plan)["status"]
        flag = "ok  " if got == want else "FAIL"
        if got != want:
            ok = False
        print("%s %-34s expected %-22s got %s" % (flag, name, want, got))

    g = _good_plan()
    expect("positive control", g, "PASS")
    p = copy.deepcopy(g); p["covers"] = [{"start": 12.3, "end": 13.0}]
    expect("cut covered with < 6 f margin", p, "FAIL")
    p = copy.deepcopy(g); p["zooms"] = [z for z in p["zooms"] if z["t"] > 1.0]
    expect("no opening push-in", p, "FAIL")
    p = copy.deepcopy(g); del p["joins"]
    expect("missing joins key (blocked)", p, "INSUFFICIENT_EVIDENCE")
    p = copy.deepcopy(g); p["beats"][1]["overlay"]["box"] = [400, 500, 600, 700]
    expect("overlay crosses the face", p, "FAIL")
    p = copy.deepcopy(g); p["beats"] = []
    expect("empty beats (blocked)", p, "INSUFFICIENT_EVIDENCE")
    p = copy.deepcopy(g); p["beats"][2]["full_bleed"] = False
    expect("framed B-roll window", p, "FAIL")
    p = copy.deepcopy(g); p["beats"][2]["type"] = "speaker_only"; p["beats"][3]["type"] = "speaker_only"
    expect("8 s without a showing beat", p, "FAIL")
    p = copy.deepcopy(g); p["joins"] = [{"out_s": 17.0, "scale_delta_pct": 6, "covered": False}]
    expect("uncovered A->A join", p, "FAIL")
    p = copy.deepcopy(g); p["zooms"][2]["face_x"] = None
    expect("zoom without faceX", p, "FAIL")
    p = copy.deepcopy(g); p["beats"][1]["overlay"]["width_px"] = 900
    expect("overlay wider than 860 px", p, "FAIL")
    print("SELF-CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if "--self-check" in argv:
        return self_check()
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    path = argv[0]
    kw = {}
    out = None
    i = 1
    while i < len(argv):
        if argv[i] == "--json":
            out = argv[i + 1]; i += 2
        elif argv[i] == "--margin":
            kw["margin_override"] = int(argv[i + 1]); i += 2
        elif argv[i] == "--zoom-cap":
            kw["zoom_cap"] = float(argv[i + 1]); i += 2
        else:
            print("unknown argument", argv[i]); return 2
    try:
        raw = open(path, "rb").read()
        plan = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        rep = {"tool": "plan_lint", "version": VERSION, "status": "INSUFFICIENT_EVIDENCE",
               "checks": [chk("P0", "schema", "blocked", "cannot read plan: %s" % exc)]}
        print(json.dumps(rep, indent=2)); return 1
    rep = report(plan, **kw)
    rep["input_sha256"] = hashlib.sha256(raw).hexdigest()
    text = json.dumps(rep, indent=2, ensure_ascii=False)
    print(text)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if rep["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

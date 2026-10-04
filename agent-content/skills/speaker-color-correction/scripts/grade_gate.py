#!/usr/bin/env python3
"""grade_gate.py - fail-closed colour gate for speaker footage against a NAMED preset (stdlib only).

It judges numbers that color_check / color_scopes already measured. It never decodes video.
A pass here is execution evidence for the preset's numeric bands; it is not appearance evidence:
a human still looks at the before/after sheet (gate G6).

Usage:
    python -X utf8 grade_gate.py gate measurements.json [--preset speaker-plate-v1]
            [--preset-file presets.json] [--na black=no_black_clothing,sky=indoor] [--json verdict.json]
    python -X utf8 grade_gate.py flicker series.json [--ratio 1.35] [--offset 0.6] [--json verdict.json]
    python -X utf8 grade_gate.py --self-check

measurements.json:
    {"source_sha256": "...", "expected_samples": 20, "ignore": [[43.0, 46.5]],
     "frames": [{"t": 2.0, "person": true, "skin_Y": 46.2, "skin_hue": 118.1, "skin_chroma": 24.0,
                 "black_Y": 5.1, "black_cb": 0.4, "black_cr": -0.2, "sky_chroma": 1.1,
                 "p1": 3.2, "p99": 99.5, "bright_sky": true}]}
    A field that is null/absent means "not measurable in that frame" (excluded from that check).

series.json (matte flicker, owner heuristic: rendered_diff > 1.35 x src_diff + 0.6):
    {"src": [per-frame mean luma of the face region in the source],
     "rendered": [the same region in the render]}   # same units (8-bit luma), same length

Exit codes: 0 = PASS (or N/A for a process-only preset), 1 = FAIL / INSUFFICIENT_EVIDENCE, 2 = usage error.
States per check: pass | fail | blocked | n/a. Too few evaluable frames is 'blocked', never 'pass'.
Required checks that may NOT be declared n/a: skin_Y, skin_hue, skin_chroma, p1.
"""
import json
import os
import sys

VERSION = "0.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PRESET_FILE = os.path.join(HERE, "..", "references", "presets.json")
REQUIRED = ("skin_Y", "skin_hue", "skin_chroma", "p1")
OPTIONAL = ("black", "sky", "p99")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _in_band(v, spec):
    if "center" in spec:
        return abs(v - spec["center"]) <= spec["tol"]
    return spec["min"] <= v <= spec["max"]


def _frame_checks(f, g):
    """Return {check: True/False/None} for one frame (None = not evaluable)."""
    out = {}
    person = f.get("person") is True
    out["skin_Y"] = _in_band(f["skin_Y"], g["skin_Y"]) if person and _num(f.get("skin_Y")) else None
    out["skin_hue"] = _in_band(f["skin_hue"], g["skin_hue"]) if person and _num(f.get("skin_hue")) else None
    out["skin_chroma"] = _in_band(f["skin_chroma"], g["skin_chroma"]) if person and _num(f.get("skin_chroma")) else None
    if person and all(_num(f.get(k)) for k in ("black_Y", "black_cb", "black_cr")):
        out["black"] = (abs(f["black_cb"]) <= g["black_cbcr_abs_max"] and abs(f["black_cr"]) <= g["black_cbcr_abs_max"]
                        and f["black_Y"] <= g["black_Y_max"])
    else:
        out["black"] = None
    out["sky"] = (f["sky_chroma"] <= g["sky_chroma_max"]) if person and _num(f.get("sky_chroma")) else None
    out["p1"] = (f["p1"] >= g["p1_min"]) if person and _num(f.get("p1")) else None
    out["p99"] = (f["p99"] >= g["p99_min_with_bright_sky"]) if person and f.get("bright_sky") is True and _num(f.get("p99")) else None
    return out


def load_preset(name, path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if name not in data["presets"]:
        raise KeyError("preset %r not in %s (have: %s)" % (name, path, ", ".join(sorted(data["presets"]))))
    return data["presets"][name]


def gate(meas, preset, na=None):
    na = na or {}
    if preset.get("status") == "process_only" or preset.get("gate") is None:
        return {"tool": "grade_gate", "version": VERSION, "status": "N/A",
                "reason": "process-only preset: no numeric gate; the gate is a human approving the before/after sheet. This is NOT a pass.",
                "checks": []}
    g = preset["gate"]
    bad_na = [k for k in na if k in REQUIRED or k not in OPTIONAL]
    if bad_na:
        return {"tool": "grade_gate", "version": VERSION, "status": "INSUFFICIENT_EVIDENCE",
                "reason": "cannot declare n/a for: " + ", ".join(bad_na), "checks": []}
    frames = meas.get("frames") or []
    ignore = meas.get("ignore") or []
    kept, ignored = [], 0
    for f in frames:
        t = f.get("t")
        if _num(t) and any(a <= t <= b for a, b in ignore):
            ignored += 1
            continue
        kept.append(f)
    per_check = {k: [] for k in REQUIRED[:3] + ("black", "sky", "p1", "p99")}
    for f in kept:
        for k, v in _frame_checks(f, g).items():
            if v is not None:
                per_check[k].append(v)
    person_frames = sum(1 for f in kept if f.get("person") is True)
    checks = []
    for k in ("skin_Y", "skin_hue", "skin_chroma", "black", "sky", "p1", "p99"):
        vals = per_check[k]
        n, ok = len(vals), sum(1 for v in vals if v)
        base = {"id": k, "evaluable": n, "passed": ok}
        if n < g["min_frames_per_check"]:
            if k in na:
                base.update(state="n/a", reason="declared n/a: " + na[k])
            else:
                base.update(state="blocked", reason="only %d evaluable frames (< %d): not enough evidence" % (n, g["min_frames_per_check"]))
        else:
            frac = ok / float(n)
            base.update(fraction=round(frac, 3), state="pass" if frac >= g["pass_fraction"] else "fail",
                        reason="%d/%d frames in band (need >= %.0f %%)" % (ok, n, 100 * g["pass_fraction"]))
        checks.append(base)
    expected = meas.get("expected_samples")
    cov = {"frames_total": len(frames), "frames_ignored": ignored, "frames_with_person": person_frames,
           "expected_samples": expected}
    if _num(expected) and len(frames) < expected:
        checks.append({"id": "sample_set", "state": "blocked",
                       "reason": "%d of %d expected samples present" % (len(frames), expected)})
    if person_frames == 0:
        checks.append({"id": "person_frames", "state": "blocked", "reason": "no frame with a person: nothing to judge"})
    states = [c["state"] for c in checks]
    status = "FAIL" if "fail" in states else ("INSUFFICIENT_EVIDENCE" if "blocked" in states else "PASS")
    return {"tool": "grade_gate", "version": VERSION, "status": status, "coverage": cov,
            "source_sha256": meas.get("source_sha256"), "checks": checks}


def flicker(series, ratio=1.35, offset=0.6):
    src, ren = series.get("src") or [], series.get("rendered") or []
    if len(src) < 3 or len(src) != len(ren):
        return {"tool": "grade_gate", "version": VERSION, "status": "INSUFFICIENT_EVIDENCE",
                "reason": "need >= 3 samples and equal lengths (got %d / %d)" % (len(src), len(ren)), "flagged": []}
    flagged = []
    for i in range(1, len(src)):
        ds, dr = abs(src[i] - src[i - 1]), abs(ren[i] - ren[i - 1])
        if dr > ratio * ds + offset:
            flagged.append({"index": i, "src_diff": round(ds, 3), "rendered_diff": round(dr, 3)})
    return {"tool": "grade_gate", "version": VERSION, "status": "FAIL" if flagged else "PASS",
            "coverage": {"frame_pairs": len(src) - 1}, "flagged": flagged,
            "rule": "rendered_diff > %.2f x src_diff + %.2f" % (ratio, offset)}


def _good_frames(n=12):
    return [{"t": 2.0 * i, "person": True, "skin_Y": 46 + (i % 3) - 1, "skin_hue": 118, "skin_chroma": 24,
             "black_Y": 5, "black_cb": 0.5, "black_cr": -0.4, "sky_chroma": 1.0, "p1": 3.0, "p99": 99, "bright_sky": True}
            for i in range(n)]


def self_check():
    preset = load_preset("speaker-plate-v1", DEFAULT_PRESET_FILE)
    ok = True

    def expect(name, got, want):
        nonlocal ok
        flag = "ok  " if got == want else "FAIL"
        ok = ok and got == want
        print("%s %-40s expected %-22s got %s" % (flag, name, want, got))

    expect("positive control", gate({"frames": _good_frames()}, preset)["status"], "PASS")
    pink = _good_frames()
    for f in pink:
        f["skin_hue"] = 95
    expect("pink skin (hue 95)", gate({"frames": pink}, preset)["status"], "FAIL")
    expect("no frames", gate({"frames": []}, preset)["status"], "INSUFFICIENT_EVIDENCE")
    expect("3 person frames only", gate({"frames": _good_frames(3)}, preset)["status"], "INSUFFICIENT_EVIDENCE")
    nop = _good_frames()
    for f in nop:
        f["person"] = False
    expect("no person in any frame", gate({"frames": nop}, preset)["status"], "INSUFFICIENT_EVIDENCE")
    short = {"frames": _good_frames(10), "expected_samples": 20}
    expect("incomplete sample set", gate(short, preset)["status"], "INSUFFICIENT_EVIDENCE")
    mix = _good_frames(20)
    for f in mix[:4]:
        f["skin_Y"] = 70
    expect("4/20 off-band frames (80 % < 85 %)", gate({"frames": mix}, preset)["status"], "FAIL")
    for f in mix[:4]:
        f["t"] = 43.0 + 0.2 * mix.index(f)
    expect("same frames inside --ignore window", gate({"frames": mix, "ignore": [[43.0, 46.5]]}, preset)["status"], "PASS")
    noblack = _good_frames()
    for f in noblack:
        f["black_Y"] = f["black_cb"] = f["black_cr"] = None
    expect("black not measurable, undeclared", gate({"frames": noblack}, preset)["status"], "INSUFFICIENT_EVIDENCE")
    expect("black declared n/a with reason", gate({"frames": noblack}, preset, {"black": "no_black_clothing"})["status"], "PASS")
    expect("n/a on a required check refused", gate({"frames": _good_frames()}, preset, {"skin_Y": "x"})["status"], "INSUFFICIENT_EVIDENCE")
    expect("process-only preset", gate({"frames": _good_frames()}, load_preset("ai-generated-natural-v1", DEFAULT_PRESET_FILE))["status"], "N/A")
    src = [100.0] * 10
    expect("flicker: smooth render", flicker({"src": src, "rendered": [100.0 + 0.2 * i for i in range(10)]})["status"], "PASS")
    ren = [100.0, 100.0, 108.0, 100.0, 100.0, 108.0, 100.0, 100.0, 108.0, 100.0]
    expect("flicker: periodic lift", flicker({"src": src, "rendered": ren})["status"], "FAIL")
    expect("flicker: too few samples", flicker({"src": [1, 2], "rendered": [1, 2]})["status"], "INSUFFICIENT_EVIDENCE")
    print("SELF-CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def _parse_na(text):
    out = {}
    for part in filter(None, (text or "").split(",")):
        k, _, why = part.partition("=")
        out[k.strip()] = why.strip() or "declared"
    return out


def main(argv):
    if "--self-check" in argv:
        return self_check()
    if len(argv) < 2 or argv[0] not in ("gate", "flicker"):
        print(__doc__)
        return 2
    mode, path = argv[0], argv[1]
    opts = {"--preset": "speaker-plate-v1", "--preset-file": DEFAULT_PRESET_FILE, "--na": "", "--json": None,
            "--ratio": "1.35", "--offset": "0.6"}
    i = 2
    while i < len(argv):
        if argv[i] not in opts or i + 1 >= len(argv):
            print("bad argument", argv[i]); return 2
        opts[argv[i]] = argv[i + 1]; i += 2
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if mode == "gate":
            verdict = gate(data, load_preset(opts["--preset"], opts["--preset-file"]), _parse_na(opts["--na"]))
        else:
            verdict = flicker(data, float(opts["--ratio"]), float(opts["--offset"]))
    except (OSError, ValueError, KeyError) as exc:
        verdict = {"tool": "grade_gate", "version": VERSION, "status": "INSUFFICIENT_EVIDENCE",
                   "reason": "cannot evaluate: %s" % exc}
    text = json.dumps(verdict, indent=2, ensure_ascii=False)
    print(text)
    if opts["--json"]:
        with open(opts["--json"], "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if verdict["status"] in ("PASS", "N/A") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

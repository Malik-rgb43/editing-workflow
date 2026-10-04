"""color_fit - fit a small, named grade to a NAMED colour preset from sampled frames of the CAMERA ORIGINAL (two stages, few free parameters).

Stage ``global`` frees ev, wb_r, wb_b, sat, contrast, black (whole-frame look: neutral blacks, clean sky, skin in band). Stage ``subject`` frees
lift_ev, s_wb_r, s_wb_b, s_sat with the global stage fixed (``--fixed global.json``): the extra node that is later applied to the person
through a matte. Regions are EXPLICIT (fractions x0,y0,x1,y1) or a ``faces.json`` from ``face_center`` - nothing is guessed. White balance is
fitted ONLY against a real neutral (``--neutral-roi`` a grey/white shirt or wall, ``--black-roi`` a black shirt, ``--sky-roi``): without one, wb_r/wb_b
stay locked, because chasing skin hue with white balance tints every neutral (found on real footage: a grey T-shirt turned mauve). Skin residuals have
a small deadband (Y 1.5, hue 2 degrees, chroma 1.5) so skin that is already close is not pushed. The numeric
targets come from a preset file (speaker-color-correction/references/presets.json); a ``process_only`` preset has no numbers and is refused.

The solver is a deterministic bounded pattern search. A result is reported with the facts a reviewer needs: cost before/after, evaluations,
whether it converged (LOCAL convergence is not acceptance), which parameters sit on a bound (degenerate: constrain them) and the metrics
before/after next to the preset's gate bands. ALWAYS look at the before/after sheet (``--sheet``): numbers alone pass visibly bad frames.

Usage:
    python tools/color_fit.py <video> --at 2,9,16 -o grade.json [--preset speaker-plate-v1] [--preset-file presets.json] [--stage global|subject]
                              [--fixed global.json] (--faces faces.json | --skin-roi x0,y0,x1,y1) [--neutral-roi ...] [--black-roi ...] [--sky-roi ...]
                              [--width 270] [--sheet before_after.jpg] [--max-nfev 600]
Exit: 0 written, 2 refused / insufficient evidence (no ROI, no frame, process-only preset), 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _common  # noqa: F401

PRESET_FILE = Path(__file__).resolve().parents[1] / "agent-content" / "skills" / "speaker-color-correction" / "references" / "presets.json"


def load_preset(name: str, path=None) -> dict:
    data = json.loads(Path(path or PRESET_FILE).read_text(encoding="utf-8"))
    pr = (data.get("presets") or {}).get(name)
    if pr is None:
        raise ValueError(f"unknown preset {name!r}; known: {sorted(data.get('presets') or {})}")
    if pr.get("status") != "numeric" or not pr.get("targets"):
        raise ValueError(f"preset {name!r} is process-only (no numeric targets): a numeric fit would invent numbers")
    return pr


def targets_from_preset(pr: dict) -> dict:
    t = pr["targets"]
    band = t.get("skin_Y_band")
    skin_y = t.get("skin_Y", (sum(band) / 2.0) if band else None)
    if skin_y is None or t.get("skin_hue") is None or t.get("skin_chroma") is None:
        raise ValueError("preset has no skin_Y/skin_hue/skin_chroma targets")
    return {"skin_Y": float(skin_y), "skin_hue": float(t["skin_hue"]), "skin_chroma": float(t["skin_chroma"]), "black_Y": float(t.get("black_Y", 5.0)),
            "black_cb": float(t.get("black_u", t.get("black_uv", 0.0))), "black_cr": float(t.get("black_v", t.get("black_uv", 0.0))),
            "sky_chroma": float(t.get("sky_chroma", 0.0)), "p1_min": float(t.get("p1_min", 3.0))}


def collect(video, times, width, faces, skin_roi, black_roi, sky_roi, neutral_roi=None):
    """Per sample time: the small frame plus the ROI pixel arrays (uint8 N x 3). Raises ValueError when no sample has a skin region."""
    import numpy as np

    import color_scopes
    from core.ffprobe import probe
    from core.media import read_frame_at

    info = probe(video)
    samples = []
    for t in times:
        fr = read_frame_at(video, t, width=width, info=info)
        h, w = fr.shape[:2]

        def px(roi):
            if roi is None:
                return None
            x0, y0, x1, y1 = roi
            a = fr[int(y0 * h):max(int(y0 * h) + 1, int(y1 * h)), int(x0 * w):max(int(x0 * w) + 1, int(x1 * w))]
            return a.reshape(-1, 3) if a.size else None

        sroi = skin_roi or (color_scopes.face_roi(faces, t, aspect=w / h) if faces else None)
        skin = px(sroi)
        if skin is None:
            continue
        samples.append({"t": float(t), "frame": fr, "skin": skin, "black": px(black_roi), "sky": px(sky_roi), "neutral": px(neutral_roi)})
    if not samples:
        raise ValueError("no sample has a skin region: give --faces (from face_center) or --skin-roi; nothing is guessed")
    return samples


def measure(samples, params, stage_subject: bool):
    """Mean metrics over samples with ``params`` applied (skin gets the subject node only in the subject stage; everything else is global)."""
    import numpy as np

    from core import colour

    acc = {k: [] for k in ("skin_Y", "skin_hue", "skin_chroma", "black_Y", "black_cb", "black_cr", "sky_chroma", "neutral_cb", "neutral_cr", "p1", "p99")}
    for s in samples:
        m = colour.region_metrics(colour.grade_u8(s["skin"], params, subject=stage_subject))
        acc["skin_Y"].append(m["Y_pct"])
        acc["skin_chroma"].append(m["chroma"])
        acc["skin_hue"].append(m["hue_deg"])
        if s["black"] is not None:
            b = colour.region_metrics(colour.grade_u8(s["black"], params))
            acc["black_Y"].append(b["Y_pct"]); acc["black_cb"].append(b["cb"]); acc["black_cr"].append(b["cr"])
        if s.get("neutral") is not None:
            nm = colour.region_metrics(colour.grade_u8(s["neutral"], params))
            acc["neutral_cb"].append(nm["cb"]); acc["neutral_cr"].append(nm["cr"])
        if s["sky"] is not None:
            acc["sky_chroma"].append(colour.region_metrics(colour.grade_u8(s["sky"], params))["chroma"])
        g = colour.grade_u8(s["frame"], params)
        y, _, _ = colour.rgb_to_ycc(g.astype(np.float64))
        acc["p1"].append(float(np.percentile(y, 1)) / 255.0 * 100.0)
        acc["p99"].append(float(np.percentile(y, 99)) / 255.0 * 100.0)
    out = {}
    for k, v in acc.items():
        if not v:
            out[k] = None
        elif k == "skin_hue":  # circular mean
            import math
            out[k] = math.degrees(math.atan2(sum(math.sin(math.radians(x)) for x in v), sum(math.cos(math.radians(x)) for x in v))) % 360.0
        else:
            out[k] = sum(v) / len(v)
    return out


DEADBAND = {"skin_Y": 1.5, "skin_hue": 2.0, "skin_chroma": 1.5}


def _dead(d: float, band: float) -> float:
    return 0.0 if abs(d) <= band else d - band if d > 0 else d + band


def residuals(m, tg):
    from core import colour

    r = [_dead(m["skin_Y"] - tg["skin_Y"], DEADBAND["skin_Y"]) / 4.0, _dead(colour.hue_error(m["skin_hue"], tg["skin_hue"]), DEADBAND["skin_hue"]) / 6.0,
         _dead(m["skin_chroma"] - tg["skin_chroma"], DEADBAND["skin_chroma"]) / 4.0]
    if m.get("neutral_cb") is not None:
        r += [m["neutral_cb"] / 1.5, m["neutral_cr"] / 1.5]
    if m["black_Y"] is not None:
        r += [(m["black_Y"] - tg["black_Y"]) / 3.0, (m["black_cb"] - tg["black_cb"]) / 1.5, (m["black_cr"] - tg["black_cr"]) / 1.5]
    if m["sky_chroma"] is not None:
        r.append((m["sky_chroma"] - tg["sky_chroma"]) / 1.5)
    r.append(max(0.0, tg["p1_min"] - m["p1"]) / 2.0)
    return r


def has_neutral(samples) -> bool:
    return any(s.get("neutral") is not None or s.get("black") is not None or s.get("sky") is not None for s in samples)


def parse_bounds(specs) -> dict:
    """Pure: ['ev=-0.2:0.6', ...] -> {'ev': (-0.2, 0.6)}; narrows a parameter (the skill: a parameter on its bound = constrain it)."""
    from core import colour

    out = {}
    for spec in specs or []:
        name, _, rng = spec.partition("=")
        lo, _, hi = rng.partition(":")
        if name not in colour.BOUNDS:
            raise ValueError(f"--bound: unknown parameter {name!r} (known: {', '.join(colour.BOUNDS)})")
        lo, hi = float(lo), float(hi)
        blo, bhi = colour.BOUNDS[name]
        if not (blo <= lo < hi <= bhi):
            raise ValueError(f"--bound {spec}: must narrow the tool range {blo}..{bhi}")
        out[name] = (lo, hi)
    return out


def fit(samples, targets, stage: str, fixed: dict, max_nfev: int = 600, narrow: dict | None = None):
    from core import colour

    keys = colour.GLOBAL_KEYS if stage == "global" else colour.SUBJECT_KEYS
    if stage == "global" and not has_neutral(samples):
        keys = tuple(k for k in keys if k not in ("wb_r", "wb_b"))  # no neutral reference: white balance is not fitted from skin
    base = colour.full_params(fixed)
    bounds = {k: (narrow or {}).get(k, colour.BOUNDS[k]) for k in keys}

    def cost(x):
        p = dict(base)
        p.update(x)
        res = residuals(measure(samples, p, stage == "subject"), targets)
        reg = sum(((x[k] - colour.IDENTITY[k]) / (bounds[k][1] - bounds[k][0])) ** 2 for k in keys) * 0.02
        return sum(v * v for v in res) + reg

    before = measure(samples, base, stage == "subject")
    sol = minimize_wrapper(cost, {k: min(max(base[k], bounds[k][0]), bounds[k][1]) for k in keys}, bounds, max_nfev)
    final = dict(base)
    final.update(sol["x"])
    after = measure(samples, final, stage == "subject")
    return final, before, after, sol


def minimize_wrapper(cost, x0, bounds, max_nfev):
    from core import colour

    return colour.minimize(cost, x0, bounds, max_nfev=max_nfev)


def band_report(m, pr):
    g = pr.get("gate") or {}

    def inb(v, spec):
        if v is None or spec is None:
            return None
        return abs(v - spec["center"]) <= spec["tol"] if "center" in spec else spec["min"] <= v <= spec["max"]

    return {"skin_Y": inb(m["skin_Y"], g.get("skin_Y")), "skin_hue": inb(m["skin_hue"], g.get("skin_hue")), "skin_chroma": inb(m["skin_chroma"], g.get("skin_chroma")),
            "p1": (m["p1"] >= g["p1_min"]) if g.get("p1_min") is not None and m["p1"] is not None else None}


def write_sheet(path, samples, params, subject, max_cols=3):
    from PIL import Image, ImageDraw

    from core import colour

    tiles = []
    for s in samples[: max_cols * 2]:
        a = Image.fromarray(s["frame"])
        b = Image.fromarray(colour.grade_u8(s["frame"], params, subject=subject))
        w, h = a.size
        t = Image.new("RGB", (w * 2 + 6, h + 14), (20, 20, 20))
        t.paste(a, (0, 14)); t.paste(b, (w + 6, 14))
        d = ImageDraw.Draw(t)
        d.text((4, 1), f"before  t={s['t']:.1f}s", fill=(230, 230, 230))
        d.text((w + 10, 1), "after" + (" (subject node on the whole frame: preview, no matte)" if subject else ""), fill=(230, 230, 230))
        tiles.append(t)
    cols = min(max_cols, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    tw, th = tiles[0].size
    sheet = Image.new("RGB", (tw * cols, th * rows), (0, 0, 0))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=90)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="color_fit", description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--at", required=True, help="comma-separated seconds of the sample frames (3-6 spread across the clip)")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--preset", default="speaker-plate-v1")
    ap.add_argument("--preset-file")
    ap.add_argument("--stage", choices=["global", "subject"], default="global")
    ap.add_argument("--fixed", help="grade.json of the global stage (required for --stage subject)")
    ap.add_argument("--faces")
    ap.add_argument("--skin-roi")
    ap.add_argument("--black-roi")
    ap.add_argument("--sky-roi")
    ap.add_argument("--neutral-roi", help="a grey or white neutral (shirt, wall, card): white balance is fitted against it")
    ap.add_argument("--width", type=int, default=270)
    ap.add_argument("--sheet")
    ap.add_argument("--max-nfev", type=int, default=600)
    ap.add_argument("--bound", action="append", metavar="NAME=LO:HI", help="narrow one parameter (repeatable), e.g. --bound ev=-0.2:0.6 on a backlit shot where the global stage pins exposure")
    a = ap.parse_args(argv)

    from core import colour
    from core.envelope import sha256_file
    from core.errors import ToolkitError
    from core.fsio import read_json, write_json_atomic

    import color_scopes

    try:
        pr = load_preset(a.preset, a.preset_file)
        tg = targets_from_preset(pr)
        times = [float(x) for x in a.at.split(",") if x.strip()]
        if len(times) < 1:
            raise ValueError("--at needs at least one time")
        fixed = {}
        if a.fixed:
            fixed = (read_json(a.fixed) or {}).get("params", {})
        elif a.stage == "subject":
            raise ValueError("--stage subject needs --fixed global.json (the subject node sits on top of a fixed global grade)")
        faces = read_json(a.faces) if a.faces else None
        samples = collect(a.video, times, a.width, faces, color_scopes.parse_roi(a.skin_roi) if a.skin_roi else None,
                          color_scopes.parse_roi(a.black_roi) if a.black_roi else None, color_scopes.parse_roi(a.sky_roi) if a.sky_roi else None,
                          color_scopes.parse_roi(a.neutral_roi) if a.neutral_roi else None)
        final, before, after, sol = fit(samples, tg, a.stage, fixed, a.max_nfev, parse_bounds(a.bound))
    except (ValueError, OSError, ToolkitError) as exc:
        print(f"color_fit: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"color_fit: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    # a parameter resting on a bound that IS its identity value (black = 0) is simply unused, not degenerate
    active = [k for k in sol["active_bounds"] if abs(final[k] - colour.IDENTITY[k]) > 1e-9]
    res = {
        "schema": "avc.grade/1", "preset": a.preset, "stage": a.stage, "source": Path(a.video).name, "source_sha256": sha256_file(a.video),
        "params": colour.non_default(final),
        "fit": {"samples": len(samples), "times": [s["t"] for s in samples], "targets": tg, "cost_before": round(sol["cost0"], 4), "cost_after": round(sol["cost"], 4), "nfev": sol["nfev"],
                "converged": sol["converged"], "message": sol["message"], "active_bounds": active,
                "wb_locked": None if (a.stage != "global" or has_neutral(samples)) else "no neutral reference (--neutral-roi / --black-roi / --sky-roi): white balance was not fitted",
                "metrics_before": {k: None if v is None else round(v, 3) for k, v in before.items()}, "metrics_after": {k: None if v is None else round(v, 3) for k, v in after.items()},
                "gate_bands_met_after": band_report(after, pr),
                "regions": {"skin": "faces.json" if faces else "roi", "black": bool(a.black_roi), "sky": bool(a.sky_roi), "neutral": bool(a.neutral_roi)},
                "note": "convergence is local, not acceptance: look at the before/after sheet; a parameter in active_bounds is degenerate; targets are a NAMED preset, not universal"},
    }
    write_json_atomic(a.out, res)
    if a.sheet:
        write_sheet(a.sheet, samples, final, a.stage == "subject")
    print(json.dumps({"out": a.out, "params": res["params"], "converged": sol["converged"], "active_bounds": active, "wb_locked": res["fit"]["wb_locked"], "cost": [res["fit"]["cost_before"], res["fit"]["cost_after"]]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

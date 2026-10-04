"""Colour engine for the speaker-colour tools (numpy only): a small, explicit grade model, 3D LUT generation and region metrics.

The grade is a handful of named parameters (never a hidden attribute). ``global`` parameters describe the whole frame; ``subject`` parameters
are an extra node applied to the person through a soft matte, because the light on a face differs from the light on the background.

  ev        exposure in stops                        wb_r, wb_b   white-balance gains, normalised so luminance is preserved
  contrast  power curve around 18 % grey             black        black pin (toe), 0..0.08
  sat       saturation around luma                   lift_ev      subject lift in stops with a highlight guard (bright pixels get less)
  s_wb_r, s_wb_b, s_sat    the subject node's own balance and saturation

All maths runs in linear light (sRGB transfer, BT.709 primaries); the LUTs take and return ENCODED RGB so ffmpeg's ``lut3d`` can apply them.
Metrics use the same convention as ``tools/color_scopes.py``: BT.709 full-range luma/chroma in 8-bit centred units, hue = atan2(Cr, Cb).

Usage (library): ``from core import colour; lut = colour.make_lut({"ev": 0.2}); colour.write_cube("g.cube", lut, "title")``
"""

from __future__ import annotations

import math
from typing import Any, Mapping

IDENTITY: dict[str, float] = {"ev": 0.0, "wb_r": 1.0, "wb_b": 1.0, "sat": 1.0, "contrast": 0.0, "black": 0.0, "lift_ev": 0.0, "s_wb_r": 1.0, "s_wb_b": 1.0, "s_sat": 1.0}
GLOBAL_KEYS = ("ev", "wb_r", "wb_b", "sat", "contrast", "black")
SUBJECT_KEYS = ("lift_ev", "s_wb_r", "s_wb_b", "s_sat")
BOUNDS: dict[str, tuple[float, float]] = {
    "ev": (-1.5, 1.5), "wb_r": (0.9, 1.25), "wb_b": (0.72, 1.05), "sat": (0.9, 1.6), "contrast": (-0.3, 0.8), "black": (0.0, 0.08),
    "lift_ev": (0.0, 1.2), "s_wb_r": (0.9, 1.1), "s_wb_b": (0.9, 1.1), "s_sat": (0.9, 1.3),
}
PIVOT = 0.18
LUMA = (0.2126, 0.7152, 0.0722)


def full_params(p: Mapping[str, Any] | None) -> dict[str, float]:
    """Identity defaults overlaid with the given values; unknown names are an error (a typo must not silently do nothing)."""
    out = dict(IDENTITY)
    for k, v in (p or {}).items():
        if k not in IDENTITY:
            raise ValueError(f"unknown grade parameter {k!r}; known: {sorted(IDENTITY)}")
        out[k] = float(v)
    return out


def non_default(p: Mapping[str, float]) -> dict[str, float]:
    return {k: round(float(v), 6) for k, v in p.items() if abs(float(v) - IDENTITY[k]) > 1e-9}


def srgb_decode(v):
    import numpy as np

    v = np.clip(v, 0.0, 1.0)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_encode(x):
    import numpy as np

    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def wb_gains(r: float, b: float):
    import numpy as np

    k = 1.0 / (LUMA[0] * r + LUMA[1] + LUMA[2] * b)
    return np.array([r * k, k, b * k])


def _luma(x):
    return x[..., 0] * LUMA[0] + x[..., 1] * LUMA[1] + x[..., 2] * LUMA[2]


def grade_linear(x, params: Mapping[str, float], subject: bool = False):
    """x: float array (..., 3) in linear light -> graded linear array in 0..1."""
    import numpy as np

    p = full_params(params)
    x = np.asarray(x, dtype=np.float64) * (2.0 ** p["ev"])
    x = x * wb_gains(p["wb_r"], p["wb_b"])
    if abs(p["contrast"]) > 1e-9:
        pos = np.maximum(x, 1e-9)
        x = np.where(x > 0, PIVOT * np.power(pos / PIVOT, 1.0 + p["contrast"]), 0.0)
    if p["black"] > 0:
        x = np.maximum((x - p["black"]) / (1.0 - p["black"]), 0.0)
    if abs(p["sat"] - 1.0) > 1e-9:
        l = _luma(x)[..., None]
        x = l + (x - l) * p["sat"]
    if subject:
        if p["lift_ev"] > 0:
            g = 2.0 ** p["lift_ev"]
            guard = (1.0 - np.clip(_luma(x), 0.0, 1.0)) ** 2  # highlights receive less lift: no hot halos
            x = x * (1.0 + (g - 1.0) * guard)[..., None]
        if abs(p["s_wb_r"] - 1.0) > 1e-9 or abs(p["s_wb_b"] - 1.0) > 1e-9:
            x = x * wb_gains(p["s_wb_r"], p["s_wb_b"])
        if abs(p["s_sat"] - 1.0) > 1e-9:
            l = _luma(x)[..., None]
            x = l + (x - l) * p["s_sat"]
    return np.clip(x, 0.0, 1.0)


def grade_u8(rgb, params: Mapping[str, float], subject: bool = False):
    """rgb: uint8 (..., 3) ENCODED -> uint8 graded (same convention the LUT uses)."""
    import numpy as np

    lin = srgb_decode(np.asarray(rgb, dtype=np.float64) / 255.0)
    out = srgb_encode(grade_linear(lin, params, subject))
    return np.clip(np.rint(out * 255.0), 0, 255).astype(np.uint8)


def make_lut(params: Mapping[str, float], subject: bool = False, size: int = 65):
    """(size**3, 3) float table in .cube order (red index varies fastest) of the ENCODED-in / ENCODED-out grade."""
    import numpy as np

    if size < 2:
        raise ValueError("LUT size must be >= 2")
    idx = np.linspace(0.0, 1.0, size)
    b, g, r = np.meshgrid(idx, idx, idx, indexing="ij")
    grid = np.stack([r.ravel(), g.ravel(), b.ravel()], axis=-1)
    out = srgb_encode(grade_linear(srgb_decode(grid), params, subject))
    return np.clip(out, 0.0, 1.0)


def write_cube(path, lut, title: str = "avc grade") -> None:
    import numpy as np
    from pathlib import Path

    n = round(len(lut) ** (1 / 3))
    if n ** 3 != len(lut):
        raise ValueError("LUT length is not a cube")
    lines = [f'TITLE "{title}"', f"LUT_3D_SIZE {n}", "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
    lines += ["%.6f %.6f %.6f" % tuple(row) for row in np.asarray(lut)]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def rgb_to_ycc(rgb):
    """rgb float (...,3) 0..255 -> (Y 0..255, Cb, Cr centred on 0). Identical to tools/color_scopes.rgb_to_ycc."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return y, (b - y) / 1.8556, (r - y) / 1.5748


def region_metrics(pixels) -> dict[str, float] | None:
    """pixels: (N,3) or (h,w,3) uint8 -> {Y_pct, cb, cr, chroma, hue_deg} of the MEAN colour, or None when empty."""
    import numpy as np

    arr = np.asarray(pixels, dtype=np.float64).reshape(-1, 3)
    if arr.size == 0:
        return None
    y, cb, cr = rgb_to_ycc(arr)
    mcb, mcr = float(cb.mean()), float(cr.mean())
    return {"Y_pct": float(y.mean()) / 255.0 * 100.0, "cb": mcb, "cr": mcr, "chroma": math.hypot(mcb, mcr), "hue_deg": math.degrees(math.atan2(mcr, mcb)) % 360.0}


def hue_error(a: float, b: float) -> float:
    """Signed circular difference a-b in degrees, in (-180, 180]."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


def minimize(f, x0: Mapping[str, float], bounds: Mapping[str, tuple[float, float]], max_nfev: int = 600, tol: float = 2e-4) -> dict[str, Any]:
    """Deterministic bounded pattern search over the named parameters in ``x0``. Returns the facts a reviewer needs, not just the answer:
    ``converged`` means the step shrank below ``tol`` of each range (LOCAL convergence, not acceptance), ``active_bounds`` lists parameters
    sitting on a bound (degenerate: constrain them)."""
    names = list(x0)
    x = {k: float(v) for k, v in x0.items()}
    span = {k: bounds[k][1] - bounds[k][0] for k in names}
    step = {k: 0.25 * span[k] for k in names}
    fx = f(x)
    cost0, nfev = fx, 1
    while nfev < max_nfev and max(step[k] / span[k] for k in names) > tol:
        improved = False
        for k in names:
            for sign in (1.0, -1.0):
                trial = dict(x)
                trial[k] = min(bounds[k][1], max(bounds[k][0], x[k] + sign * step[k]))
                if trial[k] == x[k]:
                    continue
                ft = f(trial)
                nfev += 1
                if ft < fx - 1e-12:
                    x, fx, improved = trial, ft, True
                    break
        if not improved:
            step = {k: v * 0.5 for k, v in step.items()}
    active = [k for k in names if abs(x[k] - bounds[k][0]) < 1e-9 or abs(x[k] - bounds[k][1]) < 1e-9]
    return {"x": x, "cost0": cost0, "cost": fx, "nfev": nfev, "converged": max(step[k] / span[k] for k in names) <= tol, "active_bounds": active,
            "message": "local convergence: step below tolerance" if max(step[k] / span[k] for k in names) <= tol else "stopped at max_nfev"}

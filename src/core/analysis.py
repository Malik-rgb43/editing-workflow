"""Video measurements for ``tools/analyze.py`` (numpy only): per-frame features, edit-point detection, keyframe selection, holds.

Every frame is decoded ONCE at a small size (96 px long side). Per frame: ``luma``, ``luma_std``, ``sat``, ``content`` (mean of |dHue|+|dSat|+|dValue| / 3 against
the previous frame, hue 0..180 circular, sat/value 0..255), ``hist`` (mean over R, G, B of the half-L1 distance of a 16-bin histogram), ``motion`` (mean |dGrey|), ``black`` (share
of pixels < 20) and ``white`` (share > 235). The decision rules follow ``agent-content/skills/video-analysis/references/thresholds.md``; the thresholds there are the
original author's tuning on his own data - this port has NOT been re-scored on a labelled set (see ``scripts/cut_regression.py``), so a cut count is an estimate
that must be checked on the keyframe sheets before it is quoted.

Usage (library): ``from core import analysis; feats = analysis.extract_features(frames); eps = analysis.detect_edit_points(feats, fps)``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

LONG_SIDE = 96
CUT_RATIO = 3.0
CUT_CONTENT = 12.0
ALT_HIST, ALT_RATIO, ALT_CONTENT = 0.4, 1.8, 10.0
LUMA_JUMP = 40.0
PARTIAL_FRAC = 0.28
GRAPHIC_FLAT = 0.5
MOTION_RATIO = 0.5
STILL_FRAC = 0.65
FLICKER_FRAMES = 6
TIERS = {
    "quick": {"change_frac": 0.10, "min_gap": 0.8, "max_gap": 6.0, "per_sec": 1.0, "floor": 16, "cap": 120},
    "standard": {"change_frac": 0.05, "min_gap": 0.35, "max_gap": 2.5, "per_sec": 3.0, "floor": 24, "cap": 360},
    "full": {"change_frac": 0.03, "min_gap": 0.15, "max_gap": 1.0, "per_sec": 8.0, "floor": 40, "cap": 900},
}


def thumb_size(width: int, height: int, long_side: int = LONG_SIDE) -> tuple[int, int]:
    s = long_side / float(max(width, height))
    return max(8, int(round(width * s))), max(8, int(round(height * s)))


def rgb_to_hsv(rgb):
    """uint8 (h, w, 3) -> float32 H (0..180), S (0..255), V (0..255), OpenCV-style."""
    import numpy as np

    x = rgb.astype(np.float32)
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    v = x.max(axis=-1)
    mn = x.min(axis=-1)
    d = v - mn
    s = np.where(v > 0, d / np.maximum(v, 1e-6) * 255.0, 0.0)
    safe = np.maximum(d, 1e-6)
    h = np.where(v == r, (g - b) / safe, np.where(v == g, 2.0 + (b - r) / safe, 4.0 + (r - g) / safe))
    h = np.where(d > 0, (h * 60.0) % 360.0, 0.0) / 2.0
    return h, s, v


@dataclass
class Features:
    n: int = 0
    luma: list = field(default_factory=list)
    luma_std: list = field(default_factory=list)
    sat: list = field(default_factory=list)
    content: list = field(default_factory=list)
    hist: list = field(default_factory=list)
    motion: list = field(default_factory=list)
    black: list = field(default_factory=list)
    white: list = field(default_factory=list)
    thumbs: list = field(default_factory=list)  # grey uint8 (h, w) per frame, kept for the verdicts and the keyframe pick

    def arrays(self):
        import numpy as np

        return {k: np.asarray(getattr(self, k), dtype=np.float64) for k in ("luma", "luma_std", "sat", "content", "hist", "motion", "black", "white")}


def extract_features(frames: Iterable) -> Features:
    """frames: iterable of uint8 RGB (h, w, 3) at thumbnail size, in presentation order."""
    import numpy as np

    f = Features()
    prev_hsv = prev_grey = prev_hist = None
    for rgb in frames:
        grey = (rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722).astype(np.float32)
        h, s, v = rgb_to_hsv(rgb)
        hist = np.stack([np.bincount((rgb[..., c] >> 4).ravel(), minlength=16) for c in range(3)]).astype(np.float64)
        hist /= max(1, grey.size)
        f.luma.append(float(grey.mean()))
        f.luma_std.append(float(grey.std()))
        f.sat.append(float(s.mean()))
        f.black.append(float((grey < 20).mean()))
        f.white.append(float((grey > 235).mean()))
        if prev_hsv is None:
            f.content.append(0.0)
            f.hist.append(0.0)
            f.motion.append(0.0)
        else:
            dh = np.abs(h - prev_hsv[0])
            dh = np.minimum(dh, 180.0 - dh)
            f.content.append(float((dh + np.abs(s - prev_hsv[1]) + np.abs(v - prev_hsv[2])).mean() / 3.0))
            f.hist.append(float(0.5 * np.abs(hist - prev_hist).sum(axis=1).mean()))
            f.motion.append(float(np.abs(grey - prev_grey).mean()))
        f.thumbs.append(np.clip(np.rint(grey), 0, 255).astype(np.uint8))
        prev_hsv, prev_grey, prev_hist = (h, s, v), grey, hist
        f.n += 1
    return f


def changed_fraction(a, b, level: int = 4) -> float:
    import numpy as np

    return float((np.abs(a.astype(np.int16) - b.astype(np.int16)) > level).mean())


def _flat_share(a, tol: int = 2) -> float:
    import numpy as np

    vals, counts = np.unique(a, return_counts=True)
    best = 0.0
    for v in vals[:: max(1, len(vals) // 64)]:
        best = max(best, float((np.abs(a.astype(np.int16) - int(v)) <= tol).mean()))
    return best


MOVE_RESIDUAL = 4.0


def _translation(a, b, max_frac: float = 0.12) -> tuple[float, float]:
    """(ratio, residual): the best mean |a - shift(b)| over translations up to max_frac of the frame, relative to the unshifted difference, and that best
    difference in grey levels. A camera move leaves a SMALL residual once aligned; two different shots of a similar scene (same beach, same person)
    can align to half their difference and still differ by 7-10 levels - so a low ratio alone does not prove a move (2 real cuts were lost to it)."""
    import numpy as np

    h, w = a.shape
    m = max(1, int(round(max_frac * max(h, w))))
    base = float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())
    if base < 1e-6:
        return 1.0, 0.0
    best = base
    for dy in range(-m, m + 1, 2):
        for dx in range(-m, m + 1, 2):
            ya, yb = (slice(max(0, dy), h + min(0, dy)), slice(max(0, -dy), h + min(0, -dy)))
            xa, xb = (slice(max(0, dx), w + min(0, dx)), slice(max(0, -dx), w + min(0, -dx)))
            d = float(np.abs(a[ya, xa].astype(np.int16) - b[yb, xb].astype(np.int16)).mean())
            best = min(best, d)
    return best / base, best


def _translation_ratio(a, b, max_frac: float = 0.12) -> float:
    return _translation(a, b, max_frac)[0]


def _still_background(a, b) -> bool:
    """>= 65 % of the lit, textured pixels are unchanged (<= 4 levels): the same background stayed bit-still across the change."""
    import numpy as np

    lit = a > 24
    gy, gx = np.gradient(a.astype(np.float32))
    textured = (np.abs(gx) + np.abs(gy)) > 6
    mask = lit & textured
    if mask.sum() < 20:
        return False
    return float((np.abs(a.astype(np.int16) - b.astype(np.int16))[mask] <= 4).mean()) >= STILL_FRAC


def verdict(feats: Features, i: int, fps: float) -> tuple[str, str]:
    """Classify a candidate at frame i (the first frame of the new picture): returns (decision, reason). decision: cut | check | reject."""
    import numpy as np

    th = feats.thumbs
    prev, cur = th[i - 1], th[i]
    for j in range(i + 1, min(feats.n, i + 1 + FLICKER_FRAMES)):
        if float(np.abs(prev.astype(np.int16) - th[j].astype(np.int16)).mean()) < 6.0:
            return "reject", "flicker (the old picture returns within 6 frames)"
    if abs(feats.luma[i] - feats.luma[i - 1]) > LUMA_JUMP:
        return "cut", "luma jump"
    if changed_fraction(prev, cur) < PARTIAL_FRAC:
        return "reject", "partial change (caption / picture-in-picture / graphic swap)"
    if _flat_share(prev) >= GRAPHIC_FLAT and _flat_share(cur) >= GRAPHIC_FLAT and abs(feats.luma[i] - feats.luma[i - 1]) < 12:
        return "reject", "graphic swap on one flat field"
    ratio, residual = _translation(cur, prev)
    if ratio < MOTION_RATIO and residual < MOVE_RESIDUAL:
        return "reject", "camera move / whip (a translation explains the change)"
    if _still_background(prev, cur):
        return "check", "background stayed bit-still: jump cut or a picture-in-picture / product / graphic swap - decide from the frames"
    return "cut", "new picture"


REPEAT_CONTENT = 0.4


def hard_candidates(arrs, n: int) -> list[int]:
    """Frames whose change spikes against the NEIGHBOURING CHANGES. Neighbours are taken among the frames that show a new picture (content >= 0.4),
    not among raw frames: in 24p-in-60p, AI 12 fps or stop-motion material most frames repeat the previous one (change ~0), and a ratio against
    those repeats turns every ordinary new picture into a "cut" (found on real 60 fps footage: 4 false cuts in 0.25 s of one handheld shot)."""
    import numpy as np

    c, h = arrs["content"], arrs["hist"]
    changes = [i for i in range(1, n) if c[i] >= REPEAT_CONTENT]
    pos = {f: k for k, f in enumerate(changes)}
    out = []
    for i in changes:
        k = pos[i]
        idx = [changes[j] for j in (k - 2, k - 1, k + 1, k + 2) if 0 <= j < len(changes)]
        base = max(float(np.mean(c[idx])) if idx else 0.0, 1e-3)
        ratio = c[i] / base
        if (ratio >= CUT_RATIO and c[i] >= CUT_CONTENT) or (h[i] >= ALT_HIST and ratio >= ALT_RATIO and c[i] >= ALT_CONTENT):
            out.append(i)
    # an adjacent pair is ONE event: keep the stronger frame
    merged = []
    for i in out:
        if merged and i - merged[-1] <= 1:
            if c[i] > c[merged[-1]]:
                merged[-1] = i
        else:
            merged.append(i)
    return merged


def cut_type(arrs, i: int, n: int) -> str:
    lo, hi = max(0, i - 3), min(n, i + 3)
    if float(arrs["white"][lo:hi].max()) > 0.6 and min(float(arrs["white"][max(0, i - 6)]), float(arrs["white"][min(n - 1, i + 6)])) < 0.3:
        return "flash"
    if float(arrs["black"][lo:hi].max()) > 0.9 and min(float(arrs["black"][max(0, i - 6)]), float(arrs["black"][min(n - 1, i + 6)])) < 0.5:
        return "dip_black"
    return "hard"


def soft_candidates(feats: Features, arrs, fps: float, taken: Sequence[int]) -> list[tuple[int, int]]:
    """Bursts of gradual change that join two DIFFERENT calm pictures within 0.8 s (dissolve, fast zoom, slide). Reported as `check` - never counted without a look."""
    import numpy as np

    n = feats.n
    m = arrs["motion"]
    if n < 12:
        return []
    max_len = max(3, int(0.8 * fps))
    m = np.maximum.reduce([m, np.roll(m, 1), np.roll(m, 2)]) if stepped_cadence(arrs)["detected"] else m  # repeats (motion 0) must not split one move into many
    active = m > 1.5
    out, i = [], 1
    while i < n:
        if not active[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and active[j + 1]:
            j += 1
        length = j - i + 1
        near_cut = any(i - 2 <= t <= j + 2 for t in taken)
        if 3 <= length <= max_len and not near_cut and i >= 3 and j + 3 < n:
            before, after, inside = float(m[i - 3:i].mean()), float(m[j + 1:j + 4].mean()), float(m[i:j + 1].mean())
            if before < 0.5 * inside and after < 0.5 * inside and changed_fraction(feats.thumbs[i - 1], feats.thumbs[j + 1]) >= 0.45:
                out.append((i, j))
        i = j + 1
    return out


def detect_edit_points(feats: Features, fps: float) -> dict:
    """-> {"edit_points": [{frame, kind, type, note, reason}], "rejected": [...]}. Frames are 0-based indices of the first frame of the new picture."""
    arrs = feats.arrays()
    pts, rejected = [], []
    for i in hard_candidates(arrs, feats.n):
        dec, why = verdict(feats, i, fps)
        if dec == "reject":
            rejected.append({"frame": i, "reason": why})
            continue
        typ = cut_type(arrs, i, feats.n)
        pts.append({"frame": i, "kind": "cut" if dec == "cut" else "check", "type": typ if dec == "cut" else "hard", "note": why})
    taken = [p["frame"] for p in pts]
    for a, b in soft_candidates(feats, arrs, fps, taken):
        peak = max(range(a, b + 1), key=lambda k: arrs["content"][k])  # a jump cut hidden in a moving stretch sits on its strongest frame, not on the run's start
        pts.append({"frame": peak, "kind": "check", "type": "dissolve", "note": f"gradual change over frames {a}-{b} (strongest at {peak}) between two calm pictures: dissolve / slide / fast zoom, a jump cut, or a camera move - decide from the frames"})
    pts.sort(key=lambda p: p["frame"])
    out, last = [], -10
    for p in pts:  # contract: at least one frame apart
        if p["frame"] - last >= 1:
            out.append(p)
            last = p["frame"]
    return {"edit_points": out, "rejected": rejected}


def holds(arrs, fps: float, min_s: float = 1.0, thresh: float = 0.25) -> list[tuple[int, int]]:
    import numpy as np

    m = np.asarray(arrs["motion"])
    out, i, n = [], 1, len(m)
    need = int(np.ceil(min_s * fps))
    while i < n:
        if m[i] < thresh:
            j = i
            while j + 1 < n and m[j + 1] < thresh:
                j += 1
            if j - i + 1 >= need:
                out.append((i - 1, j))
            i = j + 1
        else:
            i += 1
    return out


def stepped_cadence(arrs) -> dict:
    import numpy as np

    c = np.asarray(arrs["content"])[1:]
    frac = float((c < 0.4).mean()) if len(c) else 0.0
    return {"repeat_fraction": round(frac, 4), "detected": frac >= 0.25}


def keyframe_budget(duration: float, tier: str) -> int:
    t = TIERS[tier]
    return int(min(t["cap"], max(t["floor"], t["floor"] + t["per_sec"] * duration)))


def pick_keyframes(feats: Features, shot_starts: Sequence[int], fps: float, tier: str, duration: float) -> list[int]:
    """Frames to put on the contact sheets. Per shot: a frame at the start (+0.05 s), then a frame whenever more than ``change_frac`` of the thumbnail changed since the
    last pick (moved to where the picture stops changing, so text has finished animating), at least every ``max_gap``, and the shot's last frame. Over budget: tighten x1.35
    up to 10 rounds, then an even spread."""
    cfg = dict(TIERS[tier])
    budget = keyframe_budget(duration, tier)
    n = feats.n
    starts = sorted({0, *[s for s in shot_starts if 0 < s < n]})
    ends = [s - 1 for s in starts[1:]] + [n - 1]
    for _ in range(11):
        picks = _pick_round(feats, starts, ends, fps, cfg)
        if len(picks) <= budget:
            return picks
        cfg["change_frac"] *= 1.35
        cfg["min_gap"] *= 1.35
    return sorted({round(k * (n - 1) / max(1, budget - 1)) for k in range(budget)})


def _pick_round(feats, starts, ends, fps, cfg) -> list[int]:
    min_gap, max_gap = max(1, int(round(cfg["min_gap"] * fps))), max(1, int(round(cfg["max_gap"] * fps)))
    settle_limit = max(1, int(round(0.5 * fps)))
    picks = []
    for a, b in zip(starts, ends):
        first = min(b, a + int(round(0.05 * fps)))
        picks.append(first)
        last = first
        i = first + 1
        while i <= b:
            changed = changed_fraction(feats.thumbs[last], feats.thumbs[i]) > cfg["change_frac"]
            if (changed and i - last >= min_gap) or i - last >= max_gap:
                j = i
                while j < b and j - i < settle_limit and changed_fraction(feats.thumbs[j], feats.thumbs[j + 1], 6) > 0.01:
                    j += 1
                picks.append(j)
                last = j
                i = j + 1
            else:
                i += 1
        if b > last and b not in picks:
            picks.append(b)
    return sorted(set(picks))

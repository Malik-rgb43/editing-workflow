# Technique: caption collision detection (the F08 affine box solver)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from research frontier F08 (REPORT, verdict ADOPT-scoped) and E04 (caption_qa audit), distilled/02 qa §2.2 and §8.5, TOOLS_SPEC §2 (`caption_qa`).
> Tags: `[MEASURED-lab]` · `[IDEA]` · `[SOURCED-unverified]` · `[RULE-owner]`.
> Verdict: **ADOPT for the narrow case only** — declared, piecewise-linear, axis-aligned boxes with exact rational times, after the independent repair validation recorded in the research repo. **Renderer integration is PARK**: nothing here reads boxes out of a rendered video. (src: F08 REPORT, 2026-09-30/10-01)

## 0. The problem it solves

The owner's `caption_qa` counts bright text pixels in a caption band and reports a *pop* when the count falls by > 85 % between consecutive frames. It cannot see two caption plates **on top of each other** (the E04 fixture: two boxes overlapping for exactly frames 30–45 → `caption_qa` returned 0 findings), it assumed 30 fps (f25 at 25 fps printed as 0.83 s, really 1.00 s), it returned exit 0 on a missing input, and the appearance detection its docstring advertises was not implemented. (src: E04 report, distilled/02 qa §2.2, 2026-10-02) `[MEASURED-lab]`

Declared geometry fixes the overlap case **without sampling frames**: if the composition knows each caption's box and when it is active, an exact solver can say *which two captions overlap, from when to when*.

Not a substitute for: legibility (collision-free ≠ readable), reading speed, Hebrew correctness, contrast, safe-zone policy, or the pop detector (keep it as a named regression probe with the E04 defects fixed). Collision-free geometry does not establish legibility; pair it with the rendered-typography checks and the human reading test. `[IDEA]`

## 1. Input contract (a proposal for the caption/layout compiler `[IDEA]`)

The caption block exports, per caption element, a **layout manifest** (`hf/data/caption_layout.json`):

```json
{
  "schema": "caption-layout/0.1",
  "fps": "30000/1001",
  "canvas": {"w": 1080, "h": 1920},
  "tracks": [
    {"id": "c012", "cue": "c012", "active": ["35/30", "52/30"],
     "keys": [["35/30", [140, 1180, 800, 120]], ["38/30", [140, 1170, 800, 120]]],
     "kind": "caption", "easing": "linear"}
  ],
  "exceptions": [{"a": "c012", "b": "badge3", "reason": "intentional overlap approved in PROMPT L17"}]
}
```

- **Times are exact rationals** (strings `"num/den"`), never floats; frame numbers are converted with the real rational fps (30000/1001 ≠ 30 — report frame **and** real timestamp).
- **Box = `[x, y, w, h]`** in canvas px from the *actual layout bounds* (glyph + plate, including stroke and shadow if they matter) — not the CSS box guessed by hand. Declared boxes can be wrong or omit shadows and strokes; that is the main limit.
- `active` is a **half-open** interval `[start, end)`: adjacent spans (one ends exactly when the next starts) never collide.
- `keys` are keyframes of the box; between keys motion is **linear**. Unsupported: rotation, non-linear easing, masks, raster effects, 3D → the tool must emit `unsupported` for that pair and fall back to a **measured render** (sample the rendered frames with the pixel detector), never `pass`.
- Intentional overlaps need an explicit, reviewed `exceptions` entry tied to a ledger id; absent an exception an overlap is a finding.

## 2. Algorithm (exact)

For two tracks A and B:

1. Overlap of the active spans `[s, e) = [max(startA,startB), min(endA,endB))`; empty → no collision.
2. Split `[s, e)` at every keyframe time of both tracks that lies inside it. On each piece `[t0, t1]` both boxes move linearly, so every box edge is an **affine function of t**.
3. Positive-area intersection needs four **strict** inequalities, each affine in t:
   `A.x + A.w − B.x > 0`, `B.x + B.w − A.x > 0`, `A.y + A.h − B.y > 0`, `B.y + B.h − A.y > 0`.
   Solve each for its root and intersect the resulting half-lines with `[t0, t1]`. If the intersection is a non-empty open interval it is a collision.
4. Merge touching intervals across pieces; report each as `(start, end)` with exact rationals, the cue ids and the converted frame range.
5. **Edge touching is not a collision** (zero area); the report carries explicit endpoint inclusions (`interval_inclusions`, open/closed) so consumers do not guess.
6. Reject invalid input loudly: non-positive w/h, duplicate ids, floats where rationals are required, unsorted keyframes, keyframes not covering the active span. A pairwise scan is quadratic in the number of tracks (not a measured large-project result).

## 3. Reference implementation (original; author-run on the cases in §4)

Stdlib only. A **sketch for the tool author** — the production tool must add the input validation of step 6, the inclusions report and the QA envelope.

```python
from fractions import Fraction as F

def _lin(a0, a1, t0, t1):                      # value(t) = c + s*t on [t0,t1]
    s = (a1 - a0) / (t1 - t0); return a0 - s * t0, s

def _box_at(kfs, t):                           # kfs: sorted [(t,(x,y,w,h))], linear between
    for (t0, b0), (t1, b1) in zip(kfs, kfs[1:]):
        if t0 <= t <= t1:
            a = (t - t0) / (t1 - t0); return tuple(p + (q - p) * a for p, q in zip(b0, b1))
    return kfs[0][1] if t < kfs[0][0] else kfs[-1][1]

def _segment(A, B, t0, t1):                    # A,B = (box_at_t0, box_at_t1); open interval or None
    lo, hi = t0, t1
    for ax, aw in ((0, 2), (1, 3)):            # x then y
        for p0, p1 in ((A[0][ax]+A[0][aw]-B[0][ax], A[1][ax]+A[1][aw]-B[1][ax]),
                       (B[0][ax]+B[0][aw]-A[0][ax], B[1][ax]+B[1][aw]-A[1][ax])):   # each must be > 0
            c, s = _lin(p0, p1, t0, t1)
            if s == 0:
                if c <= 0: return None
            else:
                root = -c / s
                lo, hi = (max(lo, root), hi) if s > 0 else (lo, min(hi, root))
    return (lo, hi) if lo < hi else None

def collisions(a, b):                          # track = {"id","active":(start,end),"keys":[(t,(x,y,w,h))]}
    s = max(a["active"][0], b["active"][0]); e = min(a["active"][1], b["active"][1])
    if s >= e: return []
    cuts = sorted({s, e} | {t for t, _ in a["keys"] if s < t < e} | {t for t, _ in b["keys"] if s < t < e})
    out = []
    for t0, t1 in zip(cuts, cuts[1:]):
        r = _segment((_box_at(a["keys"], t0), _box_at(a["keys"], t1)),
                     (_box_at(b["keys"], t0), _box_at(b["keys"], t1)), t0, t1)
        if r:
            if out and out[-1][1] == r[0]: out[-1] = (out[-1][0], r[1])
            else: out.append(r)
    return out
```

## 4. Cases the author ran (all with `Fraction` inputs; expected → observed)

| # | Case | Expected | Observed |
|---|---|---|---|
| 1 | two static boxes overlapping in x and y; A active frames 0–45, B active frames 30–75 at 30 fps (the E04 shape) | collision frames 30–45 | `(30, 45)` frames ✔ |
| 2 | same boxes, A ends exactly when B starts (adjacent half-open spans) | none | `[]` ✔ |
| 3 | A moves 0→30, B moves 30→0 on x (10×10 boxes, y overlapping by 5), separate or touching at both endpoints | collision strictly inside the move | `(10/3, 20/3)` ✔ |
| 4 | a 4 px box sweeping 0→500 over 1 s past a 1 px box at x = 250 | a very narrow interval, not found by endpoint screenshots | `(123/250, 251/500)` ✔ |
| 5 | A moves 0→20 over 2 s then stops (keyframe boundary inside the span); B static at x = 25 | collision from t = 3/2 to the end | `(3/2, 4)` ✔; with B at x = 40 → `[]` ✔ |

The research repo's own F08 results (E04 overlap found at frames 30–45 where `caption_qa` returned 0; an interior interval for opposite-direction boxes; a deliberately narrow interval t = 1/2–251/500; fractional time bases keep exact bounds; touching borders stay clear; 1,000 seeded moving-box pairs compared at 100 rational sample times each — a sampled oracle, **not a formal proof**) are `[MEASURED-lab]`, Python 3.12.10 on Windows, 5.15 s runner wall time for the whole run; the independent repair pass reproduced eight false interior boundary points in the first version, which were fixed (combined suite 38/38; original regression 45/45). These counts are not 45 independent tests of one idea. (src: F08 REPORT)

## 5. How the tool plugs into the pipeline

| Where | What |
|---|---|
| wf-05 (build) | the caption block writes `caption_layout.json` together with `captions.json`; `hf_preflight` may call the solver as a static check |
| wf-06 (QA) | `caption_qa` reports: pop detector (regression probe, coverage stated) + **collision findings from the manifest** + `unsupported` pairs measured by the render fallback; any finding without a reviewed exception = FAIL |
| overlays | the same solver checks **caption box vs face box** and **caption box vs overlay card** when those boxes are declared (a caption sitting on the mouth was caught by eye in an owner test) |
| report | cue ids, exact interval, frame range at the real rational fps, `interval_inclusions`, exception ids; status `PASS` only if every pair was evaluated (`evaluated_pairs == expected_pairs`) |

## 6. Limits (say them out loud)

- Declared boxes ≠ rendered pixels; no renderer extractor exists; glyph reading, platform-safe-zone policy, rotation and arbitrary easing are not integrated.
- A collision-free layout can still be illegible (contrast, size, bidi, look-alike letters).
- WebVTT-style simultaneous cues are legal: temporal overlap alone is **not** an error; only **spatial** collision during overlap is.
- The owner's heuristics near it (0.25 s per word, 0.9 s per card, rail ≤ y 1450) stay creative/house presets validated by playback; Netflix's Hebrew CPS profiles (17/13 adult/child, 20/17 SDH) are *optional named profiles*, not law for social word-pop captions. `[SOURCED-unverified]` (src: distilled/02 qa §8.5)

(src: F08 REPORT; E04 REPORT; distilled/02 qa §2.2, §8.5; TOOLS_SPEC §2 — read 2026-10-02.)

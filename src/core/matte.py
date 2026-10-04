"""Person-matte helpers (numpy + Pillow only): shot segments, stride interpolation, MODNet-style pre/post-processing, alpha statistics.

Kept free of any model runtime so it is unit-testable; ``tools/cutout.py`` plugs a model in as a plain callable ``infer(rgb_uint8) -> alpha_float32 (0..1, same h x w)``.

Usage (library): ``from core import matte; matte.segments(0, 300, [120, 200])  # [(0,120),(120,200),(200,300)]``
"""

from __future__ import annotations

from typing import Callable, Iterable, Iterator, Sequence


def segments(start: int, stop: int, cut_frames: Iterable[int]) -> list[tuple[int, int]]:
    """Split the half-open frame range [start, stop) at every cut that falls strictly inside it. A matting model with recurrent state (RVM) must be reset at a cut,
    and a frame-difference cut can never be matted across: each segment is processed on its own."""
    if stop <= start:
        return []
    inner = sorted({int(c) for c in cut_frames if start < int(c) < stop})
    edges = [start, *inner, stop]
    return [(a, b) for a, b in zip(edges, edges[1:])]


def cut_frames_from(doc, fps: float) -> list[int]:
    """Cut frame numbers from a ``source_cuts`` document (``cuts[].frame``), a list of numbers (seconds) or ``{"cuts_s": [...]}``."""
    if isinstance(doc, dict) and "cuts" in doc:
        return [int(c["frame"]) for c in doc["cuts"] if isinstance(c, dict) and "frame" in c]
    if isinstance(doc, dict) and "cuts_s" in doc:
        return [int(round(float(t) * fps)) for t in doc["cuts_s"]]
    if isinstance(doc, list):
        return [int(round(float(t) * fps)) for t in doc]
    raise ValueError("cuts file must be a source_cuts document, {\"cuts_s\": [...]} or a list of seconds")


def stride_indices(n: int, stride: int) -> list[int]:
    """Frames that are actually inferred: 0, stride, 2*stride ... and always the last frame (so the tail is never extrapolated)."""
    if n <= 0:
        return []
    stride = max(1, int(stride))
    idx = list(range(0, n, stride))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    return idx


def run_with_stride(frames: Iterable, n: int, infer: Callable, stride: int = 1) -> Iterator:
    """Yield n alpha frames (float32 h x w) in order. With stride > 1 only every ``stride``-th frame (and the last) goes through ``infer``; the frames between are LINEAR
    interpolations of the two neighbours (measured fine on talking heads at stride 2; re-check fast gestures before trusting a larger stride)."""
    import numpy as np

    keys = set(stride_indices(n, stride))
    prev_i, prev_a, pending = None, None, []
    count = 0
    for i, frame in enumerate(frames):
        count += 1
        if i in keys:
            a = np.asarray(infer(frame), dtype=np.float32)
            for j, _ in pending:
                t = (j - prev_i) / (i - prev_i)
                yield (1.0 - t) * prev_a + t * a
            pending = []
            yield a
            prev_i, prev_a = i, a
        else:
            pending.append((i, None))
    if pending:  # the stream ended earlier than announced: hold the last alpha rather than invent frames
        for _ in pending:
            yield prev_a
    if count != n:
        raise ValueError(f"expected {n} frames, decoded {count}")


def modnet_preprocess(rgb, ref_size: int = 512):
    """uint8 (h, w, 3) -> (float32 [1,3,H,W] in -1..1, (H, W)) with the SHORT side resized to ``ref_size`` and both sides rounded to a multiple of 32 (MODNet's reference code)."""
    import numpy as np
    from PIL import Image

    h, w = rgb.shape[:2]
    if min(h, w) < ref_size or max(h, w) > ref_size:
        scale = ref_size / min(h, w)
        nh, nw = int(round(h * scale)), int(round(w * scale))
    else:
        nh, nw = h, w
    nh, nw = max(32, nh - nh % 32), max(32, nw - nw % 32)
    img = np.asarray(Image.fromarray(rgb).resize((nw, nh), Image.BILINEAR), dtype=np.float32)
    x = (img - 127.5) / 127.5
    return x.transpose(2, 0, 1)[None], (nh, nw)


def modnet_postprocess(out, size: tuple[int, int]):
    """Model output [1,1,H,W] (or [H,W]) -> float32 alpha (0..1) resized back to (h, w) of the source frame."""
    import numpy as np
    from PIL import Image

    a = np.asarray(out, dtype=np.float32).reshape(np.asarray(out).shape[-2:])
    a = np.clip(a, 0.0, 1.0)
    h, w = size
    if a.shape != (h, w):
        a = np.asarray(Image.fromarray((a * 255.0).astype(np.uint8)).resize((w, h), Image.BILINEAR), dtype=np.float32) / 255.0
    return a


def to_u8(alpha):
    import numpy as np

    return np.clip(np.rint(np.asarray(alpha, dtype=np.float32) * 255.0), 0, 255).astype(np.uint8)


def alpha_stats(alpha_u8) -> dict[str, float]:
    """coverage = share of pixels that are mostly person (>= 128); partial = share of in-between pixels (the soft edge); max for the empty-matte check."""
    import numpy as np

    a = np.asarray(alpha_u8)
    return {"coverage": float((a >= 128).mean()), "partial": float(((a > 8) & (a < 247)).mean()), "max": int(a.max()) if a.size else 0}


def judge_stats(stats: Sequence[dict[str, float]]) -> tuple[str, list[str]]:
    """('fail'|'warn'|'ok', reasons). An empty matte is a failure; a matte that is almost nothing or almost everything is a warning to LOOK at."""
    if not stats:
        return "fail", ["no alpha frame could be measured"]
    if max(s["max"] for s in stats) == 0:
        return "fail", ["the matte is empty (alpha is 0 everywhere): the model found no person"]
    cov = sum(s["coverage"] for s in stats) / len(stats)
    notes = []
    if cov < 0.02:
        notes.append(f"the person covers only {cov * 100:.1f} % of the frame: check the sampled frames for a missed person")
    if cov > 0.98:
        notes.append(f"the matte covers {cov * 100:.1f} % of the frame: it is probably not separating the person from the background")
    return ("warn" if notes else "ok"), notes


ALPHA_PIX = ("yuva", "rgba", "bgra", "argb", "abgr", "gbrap", "ya8", "ya16")


def alpha_reader(path) -> tuple[list, str, bool]:
    """How to read a matte / alpha video: (decoder args to put BEFORE its -i, extraction filter, has_alpha).

    A VP8/VP9 WebM keeps its alpha in a side channel that only the libvpx decoder reads (ffprobe then reports ``alpha_mode=1`` and pix_fmt
    yuv420p, so a pix_fmt test alone misses it); ProRes 4444, PNG or QuickTime animation show the alpha in pix_fmt. Anything else is read as luma
    (a grayscale matte: white = person)."""
    from .ffprobe import probe

    info = probe(path)
    vs = info.first_video
    tags = {}
    for st in (info.raw or {}).get("streams", []):
        if st.get("codec_type") == "video":
            tags = {str(k).lower(): v for k, v in (st.get("tags") or {}).items()}
            break
    if str(tags.get("alpha_mode", "")) == "1" and vs.codec in ("vp8", "vp9"):
        return ["-c:v", "libvpx-vp9" if vs.codec == "vp9" else "libvpx"], "alphaextract", True
    if str(vs.pix_fmt or "").startswith(ALPHA_PIX):
        return [], "alphaextract", True
    return [], "format=gray", False

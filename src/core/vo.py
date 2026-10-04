"""Voice-over helpers shared by word_retime, vo_clean and hf_mix: decode, speech regions, onsets, word pinning, pause
compression, phrase levelling, time maps, SFX peaks and the voice-over-music band ratio.

Everything except ``decode_mono`` is a pure function over numpy arrays so it is unit-tested with synthetic signals. Times are in
seconds (float): audio work is sample-exact, not frame-exact. Measured, not assumed: every function returns what it found, and an empty
or silent input gives an empty result, never a guess.
"""

from __future__ import annotations

import math

HOP_S = 0.010  # 10 ms analysis hop: fine enough for 100 ms pauses and word onsets


def decode_mono(path: str, sr: int = 48000, ffmpeg: str | None = None, timeout: float = 900.0):
    """Decode any audio/video file to mono float32 at ``sr`` with ffmpeg. Raises ValueError when nothing decodes."""
    import numpy as np

    from core.ffprobe import find_ffmpeg
    from core.procs import run

    r = run([ffmpeg or find_ffmpeg(), "-v", "error", "-nostdin", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
            timeout=timeout, decode_stdout=False)
    data = getattr(r, "stdout_bytes", b"") or b""
    if r.returncode != 0 or not data:
        raise ValueError(f"no audio decoded from {path} (exit {r.returncode})")
    return np.frombuffer(data, dtype=np.float32).copy()


def envelope_db(x, sr: int, hop_s: float = HOP_S):
    """RMS level per hop in dBFS (floor -120)."""
    import numpy as np

    hop = max(1, int(round(sr * hop_s)))
    n = len(x) // hop
    if n == 0:
        return np.zeros(0)
    fr = x[: n * hop].astype(np.float64).reshape(n, hop)
    rms = np.sqrt((fr ** 2).mean(axis=1))
    return 20 * np.log10(np.maximum(rms, 1e-6))


def speech_threshold_db(env) -> float:
    """Adaptive gate: 35 % of the way from the noise floor (10th percentile) to the loud level (95th percentile), at least floor + 9 dB."""
    import numpy as np

    if len(env) == 0:
        return -60.0
    lo, hi = float(np.percentile(env, 10)), float(np.percentile(env, 95))
    return max(lo + 9.0, lo + 0.35 * (hi - lo))


def speech_regions(env, hop_s: float = HOP_S, min_pause_s: float = 0.10, min_speech_s: float = 0.05, thr_db: float | None = None) -> list[list[float]]:
    """[[t0, t1], ...] of speech separated by pauses of at least ``min_pause_s`` (shorter dips stay inside a region)."""
    if len(env) == 0:
        return []
    thr = speech_threshold_db(env) if thr_db is None else thr_db
    on = [v >= thr for v in env]
    regions, start = [], None
    for i, s in enumerate(on + [False]):
        if s and start is None:
            start = i
        if not s and start is not None:
            regions.append([start * hop_s, i * hop_s])
            start = None
    merged: list[list[float]] = []
    for r in regions:
        if merged and r[0] - merged[-1][1] < min_pause_s:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    return [[round(a, 4), round(b, 4)] for a, b in merged if b - a >= min_speech_s]


def refine_onset(x, sr: int, t_coarse: float, thr_db: float, search_s: float = 0.03) -> float:
    """Sample-accurate onset near ``t_coarse``: the first 1 ms window inside +-search_s whose RMS reaches ``thr_db``."""
    import numpy as np

    w = max(1, int(sr * 0.001))
    a = max(0, int((t_coarse - search_s) * sr))
    b = min(len(x), int((t_coarse + search_s) * sr))
    seg = x[a:b].astype(np.float64)
    n = len(seg) // w
    if n == 0:
        return t_coarse
    rms = np.sqrt((seg[: n * w].reshape(n, w) ** 2).mean(axis=1))
    db = 20 * np.log10(np.maximum(rms, 1e-6))
    hits = np.nonzero(db >= thr_db)[0]
    return round((a + int(hits[0]) * w) / sr, 4) if len(hits) else t_coarse


def assign_to_regions(words: list[dict], regions: list[list[float]]) -> list[int]:
    """Region index for each word (by its midpoint; a word between regions goes to the nearest one); -1 when there are no regions."""
    out = []
    for w in words:
        mid = (float(w["start"]) + float(w["end"])) / 2
        best, dist = -1, math.inf
        for i, (a, b) in enumerate(regions):
            d = 0.0 if a <= mid <= b else min(abs(mid - a), abs(mid - b))
            if d < dist:
                best, dist = i, d
        out.append(best)
    return out


def pin_words(words: list[dict], regions: list[list[float]], onsets: list[float]) -> tuple[list[dict], list[dict]]:
    """Shift each region's words so its FIRST word starts at the measured onset; keep the relative timing inside the region.

    Returns (new_words, report rows ``{region, onset, first_word, delta}``). Words never cross into the next region.
    """
    idx = assign_to_regions(words, regions)
    out = [dict(w) for w in words]
    report = []
    for r, (a, b) in enumerate(regions):
        members = [i for i, k in enumerate(idx) if k == r]
        if not members:
            continue
        first = members[0]
        delta = onsets[r] - float(words[first]["start"])
        for i in members:
            s = float(words[i]["start"]) + delta
            e = float(words[i]["end"]) + delta
            out[i]["start"] = round(max(a, s), 3)
            out[i]["end"] = round(min(max(e, out[i]["start"] + 0.02), b + 0.05), 3)
        report.append({"region": r, "onset": onsets[r], "first_word": words[first]["w"], "delta": round(delta, 3)})
    return out, report


def compress_pauses(regions: list[list[float]], duration: float, max_pause_s: float = 0.28, target_s: float = 0.20,
                    protect: list[float] | tuple = ()) -> list[dict]:
    """Plan pause cuts: every inner pause longer than ``max_pause_s`` becomes ``target_s`` by removing its MIDDLE.

    A pause that contains a protected time (an edit point, a beat to keep) is left alone. Returns the cuts ``[{t0, t1}]`` to remove.
    """
    cuts = []
    for (_, end_a), (start_b, _) in zip(regions, regions[1:]):
        gap = start_b - end_a
        if gap <= max_pause_s or any(end_a - 1e-6 <= p <= start_b + 1e-6 for p in protect):
            continue
        keep_each = target_s / 2
        cuts.append({"t0": round(end_a + keep_each, 4), "t1": round(start_b - keep_each, 4)})
    return [c for c in cuts if c["t1"] > c["t0"] and c["t1"] <= duration + 1e-6]


def remap(t: float, cuts: list[dict]) -> float:
    """Old time -> new time after removing the spans in ``cuts``; a time inside a removed span lands on its cut point."""
    removed = 0.0
    for c in sorted(cuts, key=lambda c: c["t0"]):
        if t >= c["t1"]:
            removed += c["t1"] - c["t0"]
        elif t > c["t0"]:
            return round(c["t0"] - removed, 4)
        else:
            break
    return round(t - removed, 4)


def phrase_levels_db(x, sr: int, regions: list[list[float]]) -> list[float]:
    """Active-speech level of each region (RMS dB over the hops above the gate)."""
    import numpy as np

    env = envelope_db(x, sr)
    thr = speech_threshold_db(env)
    out = []
    for a, b in regions:
        seg = env[int(a / HOP_S): max(int(a / HOP_S) + 1, int(b / HOP_S))]
        act = seg[seg >= thr] if len(seg) else seg
        out.append(round(float(10 * np.log10(np.mean(10 ** (act / 10)))) if len(act) else -120.0, 2))
    return out


def level_gains_db(levels: list[float], amount: float = 0.85) -> list[float]:
    """Gain per phrase that moves it ``amount`` of the way to the median level."""
    import statistics

    if not levels:
        return []
    med = statistics.median(levels)
    return [round((med - lv) * amount, 2) for lv in levels]


def gain_curve(n: int, sr: int, regions: list[list[float]], gains_db: list[float]):
    """Per-sample linear gain: constant inside each phrase, ramped ONLY inside the pause before it (never inside speech)."""
    import numpy as np

    g = np.ones(n, dtype=np.float32)
    if not regions:
        return g
    db = np.zeros(n, dtype=np.float64)
    prev_end, prev_gain = 0, gains_db[0]
    for (a, b), gd in zip(regions, gains_db):
        ia, ib = int(a * sr), min(n, int(b * sr))
        if ia > prev_end:
            db[prev_end:ia] = np.linspace(prev_gain, gd, ia - prev_end, endpoint=False)
        db[ia:ib] = gd
        prev_end, prev_gain = ib, gd
    db[prev_end:] = prev_gain
    return (10 ** (db / 20)).astype(np.float32)


def peak_time(x, sr: int, win_s: float = 0.005) -> float:
    """Time of the loudest 5 ms window: where an SFX 'lands' (a 4 s riser peaks near its end, not at 0)."""
    import numpy as np

    w = max(1, int(sr * win_s))
    n = len(x) // w
    if n == 0:
        return 0.0
    rms = np.sqrt((x[: n * w].astype(np.float64).reshape(n, w) ** 2).mean(axis=1))
    return round(int(np.argmax(rms)) * w / sr, 4)


def band_db(x, sr: int, lo_hz: float = 300.0, hi_hz: float = 4000.0) -> float:
    """Energy of ``x`` between lo and hi Hz in dB (FFT, Hann window); -120 for silence."""
    import numpy as np

    if len(x) < 32:
        return -120.0
    spec = np.abs(np.fft.rfft(x.astype(np.float64) * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / sr)
    e = spec[(f >= lo_hz) & (f <= hi_hz)].sum() / max(1, len(x))
    return round(float(10 * np.log10(max(e, 1e-12))), 2)


def vo_over_music(vo, music, sr: int, phrases: list[list[float]], lo_hz: float = 300.0, hi_hz: float = 4000.0) -> list[dict]:
    """Voice minus music in the speech band, per phrase, measured on the stems AFTER ducking."""
    rows = []
    for a, b in phrases:
        ia, ib = int(a * sr), int(b * sr)
        v, m = band_db(vo[ia:ib], sr, lo_hz, hi_hz), band_db(music[ia:ib], sr, lo_hz, hi_hz)
        rows.append({"t0": a, "t1": b, "vo_db": v, "music_db": m, "vo_over_music_db": round(v - m, 2)})
    return rows

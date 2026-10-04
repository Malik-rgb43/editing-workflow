"""Signal-only sound analysis for ``tools/analyze.py`` (numpy; FFmpeg for loudness). No sound-event model is used or needed.

What it measures: EBU R128 loudness (FFmpeg ``ebur128``), silences, transient hits, a tempo / beat-grid / key ESTIMATE from the audio signal, an energy arc and the audio
image (waveform + spectrogram + loudness, with cuts and beats marked). What it does NOT do: say what a sound IS (no "whoosh", no "drill" - ``sfx_events[].labels`` stays empty
unless a sound-event model is added), separate speech from music (``layers.speech`` comes from the ASR segments when ASR ran), or identify a song. The tempo is an estimate:
the half / double-time alternatives are returned with it and must be checked against the audio image before the number is quoted (``half_double_audited`` stays false until
someone has looked).

Usage (library): ``from core import audio_analysis as aa; aa.loudness(path); aa.analyse_signal(samples_f32, sr)``
"""

from __future__ import annotations

import math
import re

SR = 16000
HOP = 256
NFFT = 1024

_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]  # Krumhansl-Kessler
_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def parse_ebur128(text: str) -> dict | None:
    """Parse the summary block ``ffmpeg -af ebur128=peak=true`` prints at the end of a run."""
    i = text.rfind("Summary:")
    if i < 0:
        return None
    block = text[i:]

    def grab(pat):
        m = re.search(pat, block)
        return float(m.group(1)) if m else None

    lufs, lra = grab(r"\bI:\s+(-?[\d.]+)\s+LUFS"), grab(r"LRA:\s+(-?[\d.]+)\s+LU\b")
    peak = None
    m = re.search(r"True peak:\s*\n\s*Peak:\s+(-?[\d.]+)\s+dBFS", block)
    if m:
        peak = float(m.group(1))
    if lufs is None or lra is None or peak is None:
        return None
    return {"integrated_lufs": lufs, "lra": lra, "true_peak_dbtp": peak, "meter": "EBU R128 (FFmpeg ebur128, peak=true)"}


def loudness(ffmpeg: str, path: str, timeout: float = 900.0) -> dict | None:
    from .procs import run

    r = run([ffmpeg, "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:a:0", "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], timeout=timeout)
    if r.timed_out or r.returncode != 0:
        return None
    return parse_ebur128(r.stderr or "")


def _frames(x, n_fft: int, hop: int):
    import numpy as np

    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    n = 1 + (len(x) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n)[:, None]
    return x[idx]


def stft_mag(x, n_fft: int = NFFT, hop: int = HOP):
    import numpy as np

    win = np.hanning(n_fft).astype(np.float32)
    out = []
    step = 2048
    fr = _frames(x.astype(np.float32), n_fft, hop)
    for k in range(0, len(fr), step):
        out.append(np.abs(np.fft.rfft(fr[k:k + step] * win, axis=1)).astype(np.float32))
    return np.concatenate(out, axis=0)


def rms_db(x, sr: int, win_s: float = 0.05):
    import numpy as np

    n = max(1, int(win_s * sr))
    m = len(x) // n
    if m == 0:
        return np.array([-120.0], dtype=np.float32)
    seg = x[: m * n].reshape(m, n)
    return (20.0 * np.log10(np.sqrt((seg.astype(np.float64) ** 2).mean(axis=1)) + 1e-9)).astype(np.float32)


def silences(x, sr: int, min_s: float = 0.12) -> list[list[float]]:
    import numpy as np

    db = rms_db(x, sr)
    thr = max(-55.0, float(np.median(db)) - 24.0)
    quiet = db < thr
    out, i, n = [], 0, len(quiet)
    while i < n:
        if quiet[i]:
            j = i
            while j + 1 < n and quiet[j + 1]:
                j += 1
            if (j - i + 1) * 0.05 >= min_s:
                out.append([round(i * 0.05, 3), round((j + 1) * 0.05, 3)])
            i = j + 1
        else:
            i += 1
    return out


def onset_envelope(mag):
    import numpy as np

    logm = np.log1p(10.0 * mag)
    flux = np.maximum(0.0, np.diff(logm, axis=0)).sum(axis=1)
    flux = np.concatenate([[0.0], flux])
    return flux / (flux.max() + 1e-9)


def transients(env, fps_env: float, top: int = 80) -> list[dict]:
    import numpy as np

    med = float(np.median(env))
    mad = float(np.median(np.abs(env - med))) + 1e-9
    thr = max(0.25, med + 6.0 * mad)
    peaks = [i for i in range(1, len(env) - 1) if env[i] >= thr and env[i] >= env[i - 1] and env[i] > env[i + 1]]
    peaks.sort(key=lambda i: -env[i])
    peaks = sorted(peaks[:top])
    return [{"t_s": round(i / fps_env, 3), "labels": [], "peak": round(float(env[i]), 3), "likely": None} for i in peaks]


def estimate_tempo(env, fps_env: float, lo: float = 60.0, hi: float = 200.0) -> dict | None:
    """Autocorrelation of the onset envelope with a mild prior around 120 BPM. Returns the estimate, its half / double alternatives and a 0..1 confidence (peak prominence)."""
    import numpy as np

    e = env - env.mean()
    if len(e) < int(fps_env * 3) or float(np.abs(e).max()) < 1e-6:
        return None
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    ac = ac / (ac[0] + 1e-9)
    lags = np.arange(len(ac))
    bpm = np.where(lags > 0, 60.0 * fps_env / np.maximum(lags, 1), 0.0)
    ok = (bpm >= lo) & (bpm <= hi)
    if not ok.any():
        return None
    prior = np.exp(-0.5 * (np.log2(np.maximum(bpm, 1e-6) / 120.0) / 0.9) ** 2)
    score = np.where(ok, ac * prior, -1.0)
    k = int(np.argmax(score))
    prominence = float(ac[k] - np.median(ac[1:max(2, min(len(ac), int(fps_env * 4)))]))
    lag = float(k)
    if 1 <= k < len(ac) - 1:  # parabolic refinement of the autocorrelation peak: the envelope has only 62.5 samples per second
        a0, b0, c0 = float(ac[k - 1]), float(ac[k]), float(ac[k + 1])
        den = a0 - 2.0 * b0 + c0
        if den < 0:
            lag = k + 0.5 * (a0 - c0) / den
    tempo = 60.0 * fps_env / lag
    return {"tempo_bpm": round(tempo, 1), "alternatives_bpm": [round(tempo / 2, 1), round(tempo * 2, 1)], "confidence": round(max(0.0, min(1.0, prominence)), 3), "lag": k}


def beat_grid(env, fps_env: float, tempo: float, duration: float) -> list[float]:
    """Phase that maximises the envelope under a comb at the estimated tempo; beats at that phase to the end of the audio."""
    import numpy as np

    period = fps_env * 60.0 / tempo
    best_phase, best = 0.0, -1.0
    for ph in np.arange(0.0, period, max(1.0, period / 32.0)):
        idx = np.arange(ph, len(env) - 1, period).astype(int)
        s = float(env[idx].sum())
        if s > best:
            best, best_phase = s, ph
    t = best_phase
    out = []
    while t / fps_env < duration:
        out.append(round(t / fps_env, 3))
        t += period
    return out


def estimate_key(x, sr: int) -> dict | None:
    """Chroma by FFT bin folding + Krumhansl-Schmuckler. Confidence = margin of the best key over the runner-up (correlation difference)."""
    import numpy as np

    if len(x) < sr * 3:
        return None
    mag = stft_mag(x, 4096, 2048)
    freqs = np.fft.rfftfreq(4096, 1.0 / sr)
    sel = (freqs >= 65) & (freqs <= 2100)
    midi = 69 + 12 * np.log2(freqs[sel] / 440.0)
    pc = np.mod(np.rint(midi).astype(int), 12)
    chroma = np.zeros(12)
    energy = (mag[:, sel] ** 2).sum(axis=0)
    for k in range(12):
        chroma[k] = energy[pc == k].sum()
    if chroma.sum() <= 0:
        return None
    scores = []
    for mode, prof in (("major", _MAJOR), ("minor", _MINOR)):
        for tonic in range(12):
            rolled = np.roll(prof, tonic)
            c = float(np.corrcoef(chroma, rolled)[0, 1])
            scores.append((c, f"{_NOTES[tonic]} {mode}"))
    scores.sort(reverse=True)
    return {"key": scores[0][1], "key_confidence": round(max(0.0, scores[0][0] - scores[1][0]), 3), "runner_up": scores[1][1]}


def energy_arc(x, sr: int, win_s: float = 1.0, hop_s: float = 0.5) -> list[dict]:
    import numpy as np

    n, h = int(win_s * sr), int(hop_s * sr)
    out = []
    for a in range(0, max(1, len(x) - n + 1), h):
        seg = x[a:a + n].astype(np.float64)
        out.append({"t_s": round(a / sr, 2), "rms_db": round(float(20 * math.log10(math.sqrt(float((seg ** 2).mean())) + 1e-9)), 1)})
    return out


def cut_on_beat(cut_times: list[float], beats: list[float], tempo: float, fps: float) -> dict | None:
    import bisect

    if not cut_times or not beats:
        return None
    tol = max(0.07, 1.5 / fps)
    hit = 0
    for t in cut_times:
        k = bisect.bisect_left(beats, t)
        near = min([abs(beats[j] - t) for j in (k - 1, k) if 0 <= j < len(beats)])
        hit += near <= tol
    return {"tolerance_s": round(tol, 3), "ratio": round(hit / len(cut_times), 3), "chance": round(min(1.0, 2 * tol * tempo / 60.0), 3), "cuts": len(cut_times)}


MIN_MUSIC_S = 3.0
REGION_CONFIDENCE = 0.35
REGION_EXTEND = 0.25
REGION_WIN_S, REGION_HOP_S = 4.0, 1.0


def _same_tempo(a: float, b: float, tol: float = 0.04) -> bool:
    return any(abs(a - b * k) <= tol * b * k for k in (0.5, 1.0, 2.0))


def pulse(env, fps_env: float, duration: float) -> dict | None:
    """Find where a steady beat is and what its tempo is, from 4 s windows (1 s hop).

    The tempo is NOT the whole-file estimate: loud irregular sound (speech) can pull that far off (172 BPM for a 120 BPM click after 8 s of
    speech-like noise). Instead every window gets its own estimate; windows with confidence >= 0.35 vote for their tempo (half / double count as the
    same), weighted by confidence; the best-supported tempo wins and the windows that agree with it are the beat regions. On a real reel with
    15 s of speech then music, speech rhythm alone reached 0.35-0.38 at an unrelated tempo and lost the vote. An estimate of where a steady pulse is,
    NOT a music classifier; returns None when nothing reaches the threshold."""
    win, hop = int(REGION_WIN_S * fps_env), int(REGION_HOP_S * fps_env)
    starts = list(range(0, max(1, len(env) - win + 1), hop))
    if starts and len(env) - win > starts[-1]:
        starts.append(len(env) - win)  # one window flush with the end, so the last second is examined too
    allw = []
    edge = (REGION_WIN_S - REGION_HOP_S) / 2.0
    for a in starts:
        t = estimate_tempo(env[a:a + win], fps_env)
        if t:
            t0, t1 = a / fps_env, min(duration, (a + win) / fps_env)
            # a window only vouches for its middle: edges are about +/-1.5 s otherwise; a window touching the file start or end keeps that edge
            allw.append((0.0 if a == 0 else t0 + edge, duration if a + win >= len(env) else t1 - edge, t["tempo_bpm"], t["confidence"]))
    wins = [w for w in allw if w[3] >= REGION_CONFIDENCE]
    if not wins:
        return None
    best = max(wins, key=lambda w: (sum(o[3] for o in wins if _same_tempo(o[2], w[2])), w[3]))
    agree = [w for w in wins if _same_tempo(w[2], best[2])]
    norm = []
    for w in agree:  # bring half / double estimates to the winner's octave before averaging
        k = min((0.5, 1.0, 2.0), key=lambda f: abs(w[2] - best[2] * f))
        norm.append((w[2] / k, w[3]))
    tempo = sum(t * c for t, c in norm) / sum(c for _, c in norm)
    # hysteresis: strong windows (>= 0.35) seed a region; weaker windows (>= 0.25) on the same tempo extend it (a beat under a voice-over dips)
    ext = sorted(w for w in allw if w[3] >= REGION_EXTEND and _same_tempo(w[2], tempo))
    regions, strong = [], []
    for a, b, _, c in ext:
        if regions and a <= regions[-1][1] + REGION_HOP_S:
            regions[-1][1] = max(regions[-1][1], b)
            strong[-1] = strong[-1] or c >= REGION_CONFIDENCE
        else:
            regions.append([a, b])
            strong.append(c >= REGION_CONFIDENCE)
    regions = [r for r, st in zip(regions, strong) if st]
    if sum(b - a for a, b in regions) < MIN_MUSIC_S:
        return None
    return {"tempo_bpm": round(tempo, 1), "alternatives_bpm": [round(tempo / 2, 1), round(tempo * 2, 1)], "confidence": round(sum(w[3] for w in agree) / len(agree), 3),
            "regions": [[round(a, 2), round(b, 2)] for a, b in regions], "windows_agreeing": len(agree), "windows_strong": len(wins)}


def analyse_signal(x, sr: int, duration: float, cut_times: list[float], fps: float) -> dict:
    """x: float32 mono in -1..1. Returns the pieces ``tools/analyze.py`` puts into audio.json (everything labelled as an estimate)."""
    import numpy as np

    mag = stft_mag(x, NFFT, HOP)
    env = onset_envelope(mag)
    fps_env = sr / HOP
    res = {"silences": silences(x, sr), "sfx_events": transients(env, fps_env), "energy_arc": energy_arc(x, sr)}
    music = {"present": False, "detector": "signal heuristic: a steady beat grid in 4 s windows that agree on one tempo; no music classifier is installed", "half_double_audited": False}
    p = pulse(env, fps_env, duration) if duration >= MIN_MUSIC_S else None
    if p:
        regions = p["regions"]
        inside = lambda t: any(a <= t <= b for a, b in regions)  # noqa: E731
        beats = [b for b in beat_grid(env, fps_env, p["tempo_bpm"], duration) if inside(b)]
        music.update({"present": True, "tempo_bpm": p["tempo_bpm"], "tempo_alternatives_bpm": p["alternatives_bpm"], "tempo_confidence": p["confidence"],
                      "beat_regions_s": regions, "beats_s": beats, "cut_on_beat": cut_on_beat([c for c in cut_times if inside(c)], beats, p["tempo_bpm"], fps)})
        key = estimate_key(np.concatenate([x[int(a * sr):int(b * sr)] for a, b in regions]), sr)
        if key:
            music.update({"key": key["key"], "key_confidence": key["key_confidence"], "key_runner_up": key["runner_up"]})
        music["energy_arc"] = res["energy_arc"]
    else:
        music["reason"] = "no steady beat grid found" if duration >= MIN_MUSIC_S else "audio too short for a tempo estimate"
    res["music"] = music
    return res


# ------------------------------------------------------------------------------------------------ audio image
def _colormap(v):
    """float 0..1 -> uint8 RGB (a small inferno-like ramp)."""
    import numpy as np

    stops = np.array([[0, 0, 4], [66, 10, 104], [147, 38, 103], [221, 81, 58], [252, 165, 10], [252, 255, 164]], dtype=np.float32)
    pos = np.clip(v, 0, 1) * (len(stops) - 1)
    lo = np.floor(pos).astype(int)
    hi = np.minimum(lo + 1, len(stops) - 1)
    f = (pos - lo)[..., None]
    return (stops[lo] * (1 - f) + stops[hi] * f).astype(np.uint8)


def audio_image(path, x, sr: int, t0: float, t1: float, cuts: list[float], beats: list[float], width: int = 1600) -> None:
    """One PNG for [t0, t1): waveform (top), log-frequency spectrogram (middle), loudness (bottom); vertical lines = cuts (white) and beats (cyan, thin)."""
    import numpy as np
    from PIL import Image, ImageDraw

    seg = x[int(t0 * sr): int(t1 * sr)]
    wf_h, sp_h, ld_h = 160, 360, 120
    img = Image.new("RGB", (width, wf_h + sp_h + ld_h + 28), (12, 12, 14))
    d = ImageDraw.Draw(img)
    span = max(1e-6, t1 - t0)
    if len(seg) >= 64:
        cols = np.array_split(seg, width)
        peak = np.array([float(np.abs(c).max()) if len(c) else 0.0 for c in cols])
        peak = peak / max(1e-6, peak.max())
        for px in range(width):
            h = int(peak[px] * (wf_h / 2 - 2))
            d.line([(px, wf_h // 2 - h), (px, wf_h // 2 + h)], fill=(120, 190, 255))
        mag = stft_mag(seg, 1024, max(64, len(seg) // width))
        db = 20 * np.log10(mag + 1e-6)
        db = np.clip((db - (db.max() - 80)) / 80.0, 0, 1)
        bins = np.unique(np.geomspace(2, mag.shape[1] - 1, sp_h).astype(int))
        spec = db[:, bins].T[::-1]
        sp = Image.fromarray(_colormap(spec)).resize((width, sp_h), Image.BILINEAR)
        img.paste(sp, (0, wf_h))
        rd = rms_db(seg, sr, 0.1)
        rd = np.clip((rd + 60) / 60.0, 0, 1)
        pts = [(int(i / max(1, len(rd) - 1) * (width - 1)), wf_h + sp_h + ld_h - int(v * (ld_h - 4)) + 28) for i, v in enumerate(rd)]
        if len(pts) > 1:
            d.line(pts, fill=(255, 190, 80), width=2)
    for b in beats:
        if t0 <= b < t1:
            px = int((b - t0) / span * (width - 1))
            d.line([(px, wf_h), (px, wf_h + sp_h)], fill=(0, 220, 220), width=1)
    for c in cuts:
        if t0 <= c < t1:
            px = int((c - t0) / span * (width - 1))
            d.line([(px, 0), (px, wf_h + sp_h + ld_h + 28)], fill=(255, 255, 255), width=1)
    step = max(1, int(span // 12))
    for k in range(0, int(span) + 1, step):
        px = int(k / span * (width - 1))
        if px <= width - 36:  # no label squeezed against the right edge (they overlapped there)
            d.text((px + 2, wf_h + sp_h + ld_h + 12), f"{t0 + k:.0f}s", fill=(200, 200, 200))
    d.text((4, 2), "waveform", fill=(200, 200, 200))
    d.text((4, wf_h + 2), "spectrogram (log frequency)", fill=(240, 240, 240))
    d.text((4, wf_h + sp_h + 2), "loudness (100 ms RMS)", fill=(240, 240, 240))
    img.save(str(path))

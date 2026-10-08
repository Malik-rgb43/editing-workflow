"""music_fit - pick the part of a music track that fits a video: it starts on a downbeat and ends on a bar line or a one-bar fade.

For a video of length S it also puts the track's strongest loudness rise near the payoff time T when one is given, and says when the track
is too short and which whole bars to loop.

How (signal only, local, no model):
  1. decode the track to mono 16 kHz; onset envelope + tempo with the same estimator ``tools/analyze.py`` uses (``core.audio_analysis``:
     4 s windows that vote on one tempo; a whole-file estimate when no window is steady);
  2. beat grid at that tempo; bars of 4 beats (house default: 4/4); the downbeat is the beat position (1 of 4) with the strongest onsets;
  3. loudness curve (50 ms RMS, smoothed over one beat); the rise at time t = mean level over the half bar after t minus the half bar before;
  4. every downbeat with S seconds of track after it is a candidate start. Score (dB points) = the rise near start+T (within +-half a bar,
     weighted down with distance) - or, without --hit, the strongest rise inside the window away from its first and last bar - plus 0.1 x
     (window level - track level), so a quiet intro does not win on a small rise. A start on near-silence (30 dB under the track's loud
     level) is not a candidate;
  5. the end is start+S. When S is a whole number of bars (within 0.12 s) the music ends on a bar line (``fade_out_s`` 0); otherwise it
     fades over the last bar (``fade_out_s`` = one bar).
House defaults (not law; change them with the flags): 4 beats per bar, end tolerance 0.12 s, silence floor 30 dB under the track's loud
level, 1.5 s fade when no beat grid is found. The tempo is an ESTIMATE: half / double time is listed in ``bpm_alternatives``; check it by ear.

Output JSON: {start_s, end_s, fade_out_s, loop, bpm, score, reason} plus the evidence (bar_s, downbeat_phase, ending, rise, runner_up,
loop_points when loop is true, house_defaults). ``start_s`` / ``end_s`` are track times: give ``start_s`` to the mix as ``hf_mix`` music ``in`` (the bed starts there inside
the track) and ``fade_out_s`` as music ``fade_out``; no separate cut file is needed. When the track is shorter than S, ``loop`` is true and
``loop_points`` says which whole bars to repeat (jump from ``from_s`` back to ``to_s``) - a bar-true loop, not a restart of the file.

Usage:
    python tools/music_fit.py <track> --length S [--hit T] [-o fit.json] [--beats-per-bar 4] [--end-tol 0.12]
Exit: 0 written, 2 refused (missing input, no audio, bad --length / --hit, track too short to loop one bar), 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import _common  # noqa: F401

SR = 16000
LEVEL_HOP_S = 0.05
SILENCE_UNDER_DB = 30.0
NO_GRID_FADE_S = 1.5
NO_GRID_STEP_S = 0.5


def smooth(v, n: int):
    import numpy as np

    n = max(1, int(n))
    if n == 1 or len(v) < n:
        return np.asarray(v, dtype=np.float64)
    k = np.ones(n) / n
    return np.convolve(np.pad(np.asarray(v, dtype=np.float64), (n // 2, n - 1 - n // 2), mode="edge"), k, mode="valid")


class Level:
    """Smoothed loudness curve (dB) with O(1) window means."""

    def __init__(self, db, hop_s: float):
        import numpy as np

        self.db = np.asarray(db, dtype=np.float64)
        self.hop = hop_s
        self.cum = np.concatenate([[0.0], np.cumsum(self.db)])

    def mean(self, t0: float, t1: float) -> float:
        n = len(self.db)
        a = min(n - 1, max(0, int(round(t0 / self.hop))))
        b = min(n, max(a + 1, int(round(t1 / self.hop))))
        return float((self.cum[b] - self.cum[a]) / (b - a))

    def rise(self, t: float, half: float) -> float:
        return self.mean(t, t + half) - self.mean(t - half, t)


ONSET_HOP_S = 0.01
ONSET_JUMP_DB = 3.0


def refine_beats(env10, beats: list[float], beat_s: float, dur: float) -> tuple[list[float], float, int]:
    """Snap the estimated grid to the measured onsets and re-fit it as one straight line (start + k x period).

    The coarse grid comes from an STFT envelope (frames 64 ms long, so it sits early) and a tempo rounded to 0.1 BPM (which drifts
    150 ms over a minute). Each beat looks for the biggest 10 ms level jump (>= 3 dB) within a quarter beat; with 4 or more such onsets
    the grid is re-fitted by least squares. Returns (beats, period, onsets used)."""
    import numpy as np

    d = np.diff(env10, prepend=env10[0]) if len(env10) else env10
    ks, ts = [], []
    for k, b in enumerate(beats):
        a = max(0, int((b - 0.25 * beat_s) / ONSET_HOP_S))
        z = min(len(d), int((b + 0.25 * beat_s) / ONSET_HOP_S) + 1)
        if z - a < 2:
            continue
        j = int(np.argmax(d[a:z]))
        if d[a + j] >= ONSET_JUMP_DB:
            ks.append(k)
            ts.append((a + j) * ONSET_HOP_S)
    if len(ks) < 4:
        return [float(b) for b in beats], beat_s, len(ks)
    period, t0 = (float(v) for v in np.polyfit(np.asarray(ks, float), np.asarray(ts, float), 1))
    if not 0.5 * beat_s < period < 1.5 * beat_s:
        return [float(b) for b in beats], beat_s, len(ks)
    k0 = math.ceil((-0.03 - t0) / period)
    out = [max(0.0, t0 + k * period) for k in range(k0, int((dur - t0) / period) + 1)]
    return [round(t, 4) for t in out if t < dur], period, len(ks)


def downbeat_phase(env10, beats: list[float], beat_s: float, per_bar: int) -> int:
    """Which beat of the bar (0..per_bar-1) is loudest on average (peak 10 ms level just after the beat): the downbeat estimate.
    Loudness, not onset strength: a log-spectral onset curve rates a soft and a hard hit almost the same."""
    best, phase = -1e9, 0
    win = max(1, int(min(0.1, beat_s / 2) / ONSET_HOP_S))
    for p in range(per_bar):
        vals = []
        for b in beats[p::per_bar]:
            i = int(round(b / ONSET_HOP_S))
            seg = env10[i: i + win]
            if len(seg):
                vals.append(float(seg.max()))
        s = sum(vals) / len(vals) if vals else -1e9
        if s > best + 1e-6:
            best, phase = s, p
    return phase


def grid(x, sr: int, dur: float, per_bar: int) -> dict:
    """Tempo, beats and downbeats. ``bpm`` is None when no steady beat is found."""
    from core import audio_analysis as aa
    from core import vo

    env = aa.onset_envelope(aa.stft_mag(x, aa.NFFT, aa.HOP))
    fps_env = sr / aa.HOP
    p = aa.pulse(env, fps_env, dur) if dur >= aa.MIN_MUSIC_S else None
    if p:
        tempo, alts, conf, how = p["tempo_bpm"], p["alternatives_bpm"], p["confidence"], "4 s windows voting on one tempo"
    else:
        t = aa.estimate_tempo(env, fps_env)
        if not t or t["confidence"] < 0.2:
            return {"bpm": None, "reason": "no steady beat found"}
        tempo, alts, conf, how = t["tempo_bpm"], t["alternatives_bpm"], t["confidence"], "whole-file autocorrelation (no steady 4 s window)"
    env10 = vo.envelope_db(x, sr, ONSET_HOP_S)
    beats, period, used = refine_beats(env10, aa.beat_grid(env, fps_env, tempo, dur), 60.0 / tempo, dur)
    if used >= 4:
        tempo = 60.0 / period
        alts = [round(tempo / 2, 1), round(tempo * 2, 1)]
    phase = downbeat_phase(env10, beats, period, per_bar)
    return {"bpm": round(tempo, 2), "bpm_alternatives": alts, "tempo_confidence": conf, "tempo_method": how + f"; grid fitted to {used} measured onsets",
            "beats": beats, "phase": phase, "downbeats": beats[phase::per_bar], "beat_s": period, "bar_s": per_bar * period}


def ending_for(length: float, bar_s: float | None, end_tol: float, per_bar: int) -> tuple[str, float]:
    """('bar_end', 0.0) when the length is a whole number of bars (within end_tol), else ('fade', one bar)."""
    if not bar_s:
        return "fade", min(NO_GRID_FADE_S, length / 3)
    k = length / bar_s
    if round(k) >= 1 and abs(k - round(k)) * bar_s <= end_tol:
        return "bar_end", 0.0
    return "fade", round(min(bar_s, length / 3), 3)


def score_windows(level: Level, starts: list[float], length: float, hit: float | None, bar_s: float, track_db: float, floor_db: float) -> list[dict]:
    """Pure over the loudness curve: one scored row per usable start (sorted best first)."""
    half = bar_s / 2
    step = level.hop
    rows = []
    for s in starts:
        if level.mean(s, s + min(bar_s / 4, length)) < floor_db:
            continue  # the window would open on near-silence
        win_db = level.mean(s, s + length)
        if hit is not None:
            best, at = -1e9, s + hit
            n = int(round(half / step))
            for k in range(-n, n + 1):
                dt = k * step
                v = level.rise(s + hit + dt, half) * (1.0 - 0.5 * abs(dt) / max(half, 1e-9))
                if v > best:
                    best, at = v, s + hit + dt
        else:
            lo, hi = (s + bar_s, s + length - bar_s) if length > 3 * bar_s else (s + half, s + length - half)
            best, at = -1e9, lo
            t = lo
            while t <= hi + 1e-9:
                v = level.rise(t, half)
                if v > best:
                    best, at = v, t
                t += step
        rows.append({"start_s": round(s, 3), "rise_db": round(best, 2), "rise_at_track_s": round(at, 3), "rise_at_video_s": round(at - s, 3),
                     "window_db": round(win_db, 2), "score": round(best + 0.1 * (win_db - track_db), 2)})
    rows.sort(key=lambda r: -r["score"])
    return rows


def fit(x, sr: int, length: float, hit: float | None, per_bar: int = 4, end_tol: float = 0.12) -> dict:
    """The whole decision on decoded samples (float32 mono). Raises ValueError for a track that cannot be fitted."""
    import numpy as np

    from core import audio_analysis as aa

    dur = len(x) / sr
    if dur < 1.0:
        raise ValueError(f"the track is {dur:.2f} s long: too short to fit anything")
    g = grid(x, sr, dur, per_bar)
    bar_s = g.get("bar_s")
    beat_s = g.get("beat_s")
    raw = aa.rms_db(x, sr, LEVEL_HOP_S)
    level = Level(smooth(raw, round((beat_s or 0.5) / LEVEL_HOP_S)), LEVEL_HOP_S)
    loud = float(np.percentile(level.db, 90))
    floor_db = loud - SILENCE_UNDER_DB
    active = level.db >= floor_db
    track_db = float(level.db[active].mean()) if active.any() else float(level.db.mean())
    ending, fade = ending_for(length, bar_s, end_tol, per_bar)
    out = {"schema": "avc.music_fit/1", "track_duration_s": round(dur, 3), "length_s": length, "hit_s": hit, "bpm": g.get("bpm"),
           "bpm_alternatives": g.get("bpm_alternatives"), "tempo_confidence": g.get("tempo_confidence"), "tempo_method": g.get("tempo_method", g.get("reason")),
           "beats_per_bar": per_bar if bar_s else None, "bar_s": round(bar_s, 4) if bar_s else None, "downbeat_phase": g.get("phase"), "ending": ending,
           "house_defaults": {"beats_per_bar": per_bar, "end_tolerance_s": end_tol, "silence_under_loud_db": SILENCE_UNDER_DB, "fade_without_grid_s": NO_GRID_FADE_S}}
    unit = bar_s or 2.0
    if dur + 1e-6 < length:
        # too short: loop whole bars from the first active downbeat
        first = [d for d in (g.get("downbeats") or [i * NO_GRID_STEP_S for i in range(int(dur / NO_GRID_STEP_S))]) if level.mean(d, d + unit / 4) >= floor_db]
        if not first:
            raise ValueError("the track has no audible start to loop from")
        d0 = first[0]
        last_active = float(np.nonzero(active)[0][-1] + 1) * LEVEL_HOP_S
        if bar_s:
            bars = int((min(dur, last_active) - d0 + 0.02) // bar_s)
            span = min(bars * bar_s, dur - d0)
        else:
            bars, span = None, min(dur, last_active) - d0
        if span < (bar_s or 1.0) - 1e-6:
            raise ValueError(f"the track ({dur:.2f} s) is shorter than {length:g} s and holds less than one whole bar to loop")
        repeats = math.ceil(length / span)
        out.update({"start_s": round(d0, 3), "end_s": round(d0 + length, 3), "fade_out_s": fade, "loop": True, "score": None,
                    "loop_points": {"from_s": round(d0 + span, 3), "to_s": round(d0, 3), "bars": bars, "loop_s": round(span, 3), "plays": repeats,
                                    "note": "end_s is on the looped timeline: play to_s..from_s, jump back to to_s, repeat"},
                    "reason": (f"the track ({dur:.2f} s) is shorter than {length:g} s: loop {bars} whole bars ({span:.2f} s) from {d0:.2f} s, {repeats} plays, then "
                               + ("end on a bar line" if ending == "bar_end" else f"fade over the last {fade:g} s")) if bars else
                              f"the track ({dur:.2f} s) is shorter than {length:g} s and has no steady beat: loop {span:.2f} s from {d0:.2f} s with a crossfade, {repeats} plays"})
        return out
    if bar_s:
        starts = [d for d in g["downbeats"] if d + length <= dur + 1e-6]
    else:
        starts = [i * NO_GRID_STEP_S for i in range(int((dur - length) / NO_GRID_STEP_S) + 1)]
    rows = score_windows(level, starts, length, hit, unit, track_db, floor_db)
    if not rows:
        raise ValueError("no start in the track opens on sound (every candidate starts on near-silence)")
    best = rows[0]
    s = best["start_s"]
    where = f"its strongest rise (+{best['rise_db']:.1f} dB) lands at {best['rise_at_video_s']:.2f} s in the video" + (f" (asked: {hit:g} s)" if hit is not None else "")
    start_txt = f"starts on a downbeat at {s:.2f} s ({g['bpm']:g} BPM estimate, bar {bar_s:.3f} s)" if bar_s else f"starts at {s:.2f} s (no steady beat found: cut points are by loudness only)"
    end_txt = "ends on a bar line" if ending == "bar_end" else f"fades over the last {fade:g} s ({'one bar' if bar_s else 'house default'}) because {length:g} s is not a whole number of bars"
    out.update({"start_s": s, "end_s": round(s + length, 3), "fade_out_s": fade, "loop": False, "score": best["score"],
                "rise": {"db": best["rise_db"], "at_track_s": best["rise_at_track_s"], "at_video_s": best["rise_at_video_s"]},
                "reason": f"window {s:.2f}-{s + length:.2f} s {start_txt}; {where}; {end_txt}", "runner_up": rows[1:4], "candidates": len(rows)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="music_fit", description=__doc__.split("\n\n")[0])
    ap.add_argument("track")
    ap.add_argument("--length", type=float, required=True, help="video length in seconds")
    ap.add_argument("--hit", type=float, help="video time (s) of the payoff / call to action: the strongest rise goes there")
    ap.add_argument("-o", "--out")
    ap.add_argument("--beats-per-bar", type=int, default=4, help="house default 4 (4/4)")
    ap.add_argument("--end-tol", type=float, default=0.12, help="how close (s) the length must be to whole bars to end on a bar line")
    a = ap.parse_args(argv)
    if not Path(a.track).is_file():
        print(f"music_fit: input not found: {a.track}", file=sys.stderr)
        return 2
    if not a.length > 0:
        print("music_fit: --length must be > 0 seconds", file=sys.stderr)
        return 2
    if a.hit is not None and not 0 < a.hit < a.length:
        print(f"music_fit: --hit {a.hit:g} must be inside the video (0 < T < {a.length:g})", file=sys.stderr)
        return 2
    if a.beats_per_bar < 1:
        print("music_fit: --beats-per-bar must be >= 1", file=sys.stderr)
        return 2
    from core import vo

    try:
        x = vo.decode_mono(a.track, sr=SR)
    except ValueError as exc:
        print(f"music_fit: {exc}", file=sys.stderr)
        return 2
    try:
        res = fit(x, SR, a.length, a.hit, a.beats_per_bar, a.end_tol)
    except ValueError as exc:
        print(f"music_fit: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"music_fit: tool error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    res = {"track": Path(a.track).name, **res}
    if a.out:
        from core.fsio import write_json_atomic

        write_json_atomic(a.out, res)
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

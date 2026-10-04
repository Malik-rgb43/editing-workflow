"""vo_clean - tighten and level a voice-over: long pauses cut to a set length, phrases levelled toward the median, gain moved only in pauses.

For a VOICE-OVER track (a TTS read or a recorded VO laid over picture). Do NOT use it on dialogue that is locked to picture (a speaker
on camera): removing audio there breaks lip sync; cut the picture and the sound together with aroll_cut instead.

What it does, measured on the file (no fixed loudness guess):
  * speech regions from a 10 ms level envelope; every inner pause longer than --max-pause (default 0.28 s) becomes --target (0.20 s) by
    removing its MIDDLE (10 ms crossfade); a pause holding a --protect time (a beat, a hit you want to keep) is left alone;
  * each phrase moves --amount (default 0.85) of the way to the median phrase level; the gain changes ONLY inside the pause before
    a phrase, never inside speech (no pumping on a word);
  * writes the cleaned WAV (48 kHz mono, float), a JSON report and the ``cuts`` list; ``--words`` re-times a word table through the same
    cuts so captions and scene starts stay true.

Usage:
    python tools/vo_clean.py <voice.wav> -o voice_clean.wav [--max-pause 0.28] [--target 0.20] [--amount 0.85] [--protect 3.2,7.9]
                             [--words words.json --words-out words_clean.json]
Exit: 0 written, 2 refused (no audio, no speech), 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _common  # noqa: F401

SR = 48000


def apply_cuts(x, cuts, sr: int = SR, xfade_s: float = 0.010):
    """Remove every [t0, t1] span with a short equal-power crossfade at each join."""
    import numpy as np

    if not cuts:
        return x.copy()
    parts, pos = [], 0
    xf = max(1, int(xfade_s * sr))
    for c in sorted(cuts, key=lambda c: c["t0"]):
        a, b = int(c["t0"] * sr), int(c["t1"] * sr)
        parts.append(x[pos:a])
        pos = b
    parts.append(x[pos:])
    out = parts[0].astype(np.float32)
    ramp_in = np.sin(np.linspace(0, np.pi / 2, xf)) ** 2
    for p in parts[1:]:
        p = p.astype(np.float32)
        n = min(xf, len(out), len(p))
        if n:
            mixed = out[-n:] * ramp_in[::-1][:n] + p[:n] * ramp_in[:n]
            out = np.concatenate([out[:-n], mixed, p[n:]])
        else:
            out = np.concatenate([out, p])
    return out


def write_wav(path: str, x, sr: int = SR) -> None:
    from core.ffprobe import find_ffmpeg
    from core.procs import run

    r = run([find_ffmpeg(), "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-", "-c:a", "pcm_f32le", str(path)],
            input=x.astype("float32").tobytes(), timeout=600)
    if r.returncode != 0:
        raise ValueError(f"could not write {path}: {(r.stderr or '')[-200:]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="vo_clean", description=__doc__.split("\n\n")[0])
    ap.add_argument("voice")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--max-pause", type=float, default=0.28)
    ap.add_argument("--target", type=float, default=0.20)
    ap.add_argument("--amount", type=float, default=0.85)
    ap.add_argument("--protect", default="", help="comma-separated times (s) whose pause must not be shortened")
    ap.add_argument("--words")
    ap.add_argument("--words-out")
    a = ap.parse_args(argv)

    from core import vo
    from core.fsio import write_json_atomic

    if not Path(a.voice).is_file():
        print(f"vo_clean: input not found: {a.voice}", file=sys.stderr)
        return 2
    if not (0 <= a.amount <= 1) or a.target > a.max_pause:
        print("vo_clean: --amount must be 0..1 and --target <= --max-pause", file=sys.stderr)
        return 2
    try:
        x = vo.decode_mono(a.voice, sr=SR)
    except ValueError as exc:
        print(f"vo_clean: {exc}", file=sys.stderr)
        return 2
    env = vo.envelope_db(x, SR)
    regions = vo.speech_regions(env, min_pause_s=0.10)
    if not regions:
        print("vo_clean: no speech found", file=sys.stderr)
        return 2
    levels = vo.phrase_levels_db(x, SR, regions)
    gains = vo.level_gains_db(levels, a.amount)
    y = x * vo.gain_curve(len(x), SR, regions, gains)
    protect = [float(t) for t in a.protect.split(",") if t.strip()]
    cuts = vo.compress_pauses(regions, len(x) / SR, a.max_pause, a.target, protect)
    y = apply_cuts(y, cuts)
    peak = float(abs(y).max()) if len(y) else 0.0
    if peak > 0.98:  # never clip: scale the whole file down, report it
        y = y * (0.98 / peak)
    try:
        write_wav(a.out, y)
    except ValueError as exc:
        print(f"vo_clean: {exc}", file=sys.stderr)
        return 3
    rep = {"tool": "vo_clean", "in": a.voice, "out": a.out, "duration_in_s": round(len(x) / SR, 3), "duration_out_s": round(len(y) / SR, 3),
           "phrases": len(regions), "pauses_cut": len(cuts), "removed_s": round(sum(c["t1"] - c["t0"] for c in cuts), 3), "cuts": cuts,
           "levels_db": levels, "gains_db": gains, "protected": protect, "peak_scaled": peak > 0.98}
    if a.words:
        doc = json.loads(Path(a.words).read_text(encoding="utf-8"))
        words = doc["words"] if isinstance(doc, dict) else doc
        moved = [dict(w, start=vo.remap(float(w["start"]), cuts), end=vo.remap(float(w["end"]), cuts)) for w in words]
        dst = a.words_out or str(Path(a.out).with_suffix(".words.json"))
        write_json_atomic(dst, {"schema": "avc.words/1", "retimed": {"tool": "vo_clean", "cuts": cuts}, "words": moved})
        rep["words_out"] = dst
    write_json_atomic(str(a.out) + ".vo-report.json", rep)
    print(json.dumps({k: rep[k] for k in ("duration_in_s", "duration_out_s", "phrases", "pauses_cut", "removed_s")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""word_retime - make a word table frame-true: cut the read at every pause, pin each chunk's first word to its MEASURED onset.

Why: one transcription pass puts words up to about half a second late, which captions typed "at the moment a word is spoken" cannot
afford. The audio itself says when each phrase starts; the transcript only says which words it holds.

How (deterministic, local):
  1. decode the voice, measure a 10 ms level envelope, find speech regions separated by pauses >= --min-pause (default 0.10 s);
  2. each region's onset is refined to 1 ms on the waveform;
  3. words are taken from a fresh per-chunk transcription (``--model-dir``: each chunk transcribed on its own, as one pass drifts) or,
     without a model, from the existing ``words.json`` and assigned to regions by their midpoint;
  4. the first word of every region is pinned to its onset and the rest of that region shift with it; nothing crosses a pause.
The report lists each region's correction (``delta``) so the drift is visible, never hidden.

Usage:
    python tools/word_retime.py <voice.wav|video> --words words.json -o words_retimed.json [--min-pause 0.10] [--model-dir DIR --language he]
Exit: 0 written, 2 refused (no audio, no words, no speech found), 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import _common  # noqa: F401

SR = 16000


def transcribe_chunks(x, regions, model_dir: str, language: str, pre_s: float = 0.05):
    """Transcribe every region on its own (faster-whisper, local weights only); times come back in the full-file timeline."""
    from faster_whisper import WhisperModel  # heavy import, only now

    model = WhisperModel(model_dir, device="cpu", compute_type="int8", local_files_only=True)
    words = []
    for a, b in regions:
        ia, ib = max(0, int((a - pre_s) * SR)), min(len(x), int((b + pre_s) * SR))
        segs, _ = model.transcribe(x[ia:ib], language=None if language == "auto" else language, word_timestamps=True, beam_size=5)
        off = ia / SR
        for s in segs:
            for w in s.words or []:
                words.append({"w": w.word.strip(), "start": round(off + w.start, 3), "end": round(off + w.end, 3), "prob": round(w.probability, 3)})
    return [w for w in words if w["w"]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="word_retime", description=__doc__.split("\n\n")[0])
    ap.add_argument("media")
    ap.add_argument("--words", help="existing words.json (avc.words/1); required unless --model-dir re-transcribes")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--min-pause", type=float, default=0.10)
    ap.add_argument("--model-dir", help="local CTranslate2 model: re-transcribe each chunk on its own")
    ap.add_argument("--language", default="he")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    from core import vo
    from core.fsio import write_json_atomic

    if not Path(a.media).is_file():
        print(f"word_retime: input not found: {a.media}", file=sys.stderr)
        return 2
    if not a.words and not a.model_dir:
        print("word_retime: pass --words words.json, or --model-dir to re-transcribe per chunk", file=sys.stderr)
        return 2
    t0 = time.monotonic()
    try:
        x = vo.decode_mono(a.media, sr=SR)
    except ValueError as exc:
        print(f"word_retime: {exc}", file=sys.stderr)
        return 2
    env = vo.envelope_db(x, SR)
    thr = vo.speech_threshold_db(env)
    regions = vo.speech_regions(env, min_pause_s=a.min_pause, thr_db=thr)
    if not regions:
        print("word_retime: no speech regions found (silence, or the gate is wrong for this file)", file=sys.stderr)
        return 2
    onsets = [vo.refine_onset(x, SR, r[0], thr) for r in regions]
    source = "words.json"
    if a.model_dir:
        try:
            words = transcribe_chunks(x, regions, a.model_dir, a.language)
            source = f"per-chunk transcription ({Path(a.model_dir).name})"
        except Exception as exc:  # noqa: BLE001
            print(f"word_retime: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 3
    else:
        doc = json.loads(Path(a.words).read_text(encoding="utf-8"))
        words = doc["words"] if isinstance(doc, dict) else doc
    if not words:
        print("word_retime: no words to retime", file=sys.stderr)
        return 2
    new, report = vo.pin_words(words, regions, onsets)
    deltas = [abs(r["delta"]) for r in report]
    out = {"schema": "avc.words/1", "retimed": {"tool": "word_retime", "source": source, "min_pause_s": a.min_pause, "regions": len(regions),
                                                 "median_abs_delta_s": round(statistics.median(deltas), 3) if deltas else None,
                                                 "max_abs_delta_s": round(max(deltas), 3) if deltas else None, "gate_db": round(thr, 1),
                                                 "wall_s": round(time.monotonic() - t0, 2), "per_region": report}, "words": new}
    write_json_atomic(a.out, out)
    summary = {k: out["retimed"][k] for k in ("source", "regions", "median_abs_delta_s", "max_abs_delta_s", "wall_s")}
    print(json.dumps(summary if not a.json else out["retimed"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

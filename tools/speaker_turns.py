"""speaker_turns - label every word with who said it, from the level of each person's own mic track (or stereo channel). No model.

How (deterministic, local):
  1. decode each track (``--tracks a.wav b.wav``: one file per speaker) or each channel of one file (``--channels FILE``: channel 1 =
     first name, channel 2 = second) to mono 16 kHz;
  2. per word, the RMS level (dBFS) of every track over the word's span;
  3. label = the loudest track when it beats the runner-up by ``--margin-db`` (house default 6 dB: a lav mic hears its own speaker
     well above the bleed of the other one). Otherwise ``overlap`` when two tracks are both above their own speech gate (both people
     talking), else ``unknown`` (nobody clearly above the gate, or one track barely ahead);
  4. a single word whose label differs from BOTH neighbours (which agree, each within 0.5 s) and that won by less than twice the margin
     takes the neighbours' label (a one-word flip is usually bleed or a breath); ``smoothed: true`` marks it. ``unknown`` single words
     between one speaker are filled the same way. ``overlap`` is never smoothed away;
  5. ``turns``: runs of consecutive words with the same label.
The tracks must be in sync with the timeline the words were transcribed on (same start). Levels are compared raw: when one mic was
recorded much quieter, trim it before (a 6 dB gain gap moves every close call).

Output: the input words file (avc.words/1) with ``speaker``, ``speaker_margin_db`` (and ``smoothed`` when changed) on every word, plus
``speakers`` (names, source, files, method, house defaults), ``turns`` [{speaker, start, end, words, first_word}] and ``counts``.

Usage:
    python tools/speaker_turns.py --words hf/data/words.json (--tracks a.wav b.wav | --channels stereo.wav) [--names "Dana,Avi"] -o hf/data/words_speakers.json [--margin-db 6]
    (--channels with no file splits the single --tracks file into its channels)
Exit: 0 written, 2 refused (missing input, fewer than 2 tracks / channels, names do not match, no words), 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _common  # noqa: F401

SR = 16000
NEIGHBOUR_GAP_S = 0.5
SILENT_DB = -120.0


def word_levels(signals, words: list[dict], sr: int, pad_s: float = 0.0) -> list[list[float]]:
    """Pure: RMS dBFS of every signal over every word span -> [[db per track] per word]."""
    import numpy as np

    out = []
    for w in words:
        a = max(0, int((float(w["start"]) - pad_s) * sr))
        rows = []
        for x in signals:
            b = min(len(x), max(a + 1, int((float(w["end"]) + pad_s) * sr)))
            seg = x[a:b].astype(np.float64)
            rows.append(round(float(20 * np.log10(max(np.sqrt((seg ** 2).mean()), 1e-6))), 2) if len(seg) else SILENT_DB)
        out.append(rows)
    return out


def gates(signals, sr: int) -> list[float]:
    """Each track's own speech gate (the adaptive gate ``word_retime`` uses), in dBFS."""
    from core import vo

    return [round(vo.speech_threshold_db(vo.envelope_db(x, sr)), 2) for x in signals]


def label_words(levels: list[list[float]], names: list[str], gate_db: list[float], margin_db: float = 6.0) -> list[dict]:
    """Pure: per-word levels -> [{speaker, margin}] before smoothing."""
    out = []
    for row in levels:
        order = sorted(range(len(row)), key=lambda k: -row[k])
        top, second = order[0], order[1]
        margin = row[top] - row[second]
        above = [k for k in range(len(row)) if row[k] >= gate_db[k]]
        if row[top] < gate_db[top]:
            lab = "unknown"
        elif margin >= margin_db:
            lab = names[top]
        elif top in above and second in above:
            lab = "overlap"
        else:
            lab = "unknown"
        out.append({"speaker": lab, "margin": round(margin, 2)})
    return out


def smooth_flips(words: list[dict], labels: list[dict], margin_db: float, names: list[str]) -> list[dict]:
    """Pure: a lone word between two words of the same speaker (each gap <= 0.5 s) takes their label when its own win was weak."""
    out = [dict(x, smoothed=False) for x in labels]
    for i in range(1, len(labels) - 1):
        prev, cur, nxt = labels[i - 1]["speaker"], labels[i]["speaker"], labels[i + 1]["speaker"]
        if prev != nxt or prev == cur or prev not in names or cur == "overlap":
            continue
        g1 = float(words[i]["start"]) - float(words[i - 1]["end"])
        g2 = float(words[i + 1]["start"]) - float(words[i]["end"])
        if g1 > NEIGHBOUR_GAP_S or g2 > NEIGHBOUR_GAP_S:
            continue
        if cur == "unknown" or labels[i]["margin"] < 2 * margin_db:
            out[i]["speaker"] = prev
            out[i]["smoothed"] = True
    return out


def turns(words: list[dict]) -> list[dict]:
    out = []
    for i, w in enumerate(words):
        if out and out[-1]["speaker"] == w["speaker"]:
            out[-1]["end"] = w["end"]
            out[-1]["words"] += 1
        else:
            out.append({"speaker": w["speaker"], "start": w["start"], "end": w["end"], "words": 1, "first_word": i})
    return out


def load_signals(a) -> tuple[list, list[str], str]:
    """-> (mono float32 signals, file labels, source kind). Raises ValueError with a user-facing message."""
    import numpy as np

    from core import vo
    from core.ffprobe import probe
    from core.media import read_audio_samples

    if a.channels is not None or (a.channels_flag and a.tracks and len(a.tracks) == 1):
        f = a.channels if a.channels else a.tracks[0]
        if not Path(f).is_file():
            raise FileNotFoundError(f)
        info = probe(f)
        if not info.audio:
            raise ValueError(f"{f} has no audio stream")
        n = info.audio[0].channels or 0
        if n < 2:
            raise ValueError(f"{f} has {n} channel(s): --channels needs one speaker per channel (2 or more)")
        pcm = read_audio_samples(f, sample_rate=SR, channels=n, timeout_s=900.0)
        return [pcm[:, k].astype(np.float32) / 32768.0 for k in range(n)], [f"{Path(f).name}#ch{k + 1}" for k in range(n)], "channels"
    if not a.tracks or len(a.tracks) < 2:
        raise ValueError("need --tracks with one file per speaker (2 or more), or --channels FILE")
    for f in a.tracks:
        if not Path(f).is_file():
            raise FileNotFoundError(f)
    return [vo.decode_mono(f, sr=SR) for f in a.tracks], [Path(f).name for f in a.tracks], "tracks"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="speaker_turns", description=__doc__.split("\n\n")[0])
    ap.add_argument("--words", required=True, help="avc.words/1 file (tools/transcribe.py)")
    ap.add_argument("--tracks", nargs="+", help="one audio/video file per speaker, in sync with the words")
    ap.add_argument("--channels", nargs="?", const="", default=None, help="one file whose channels are the speakers (bare: split the single --tracks file)")
    ap.add_argument("--names", help='comma-separated, in track / channel order (default "S1,S2,...")')
    ap.add_argument("--margin-db", type=float, default=6.0, help="how much louder the winner must be (house default 6 dB)")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv)
    a.channels_flag = a.channels is not None
    if a.channels == "":
        a.channels = None
    if a.channels_flag and a.channels is None and not (a.tracks and len(a.tracks) == 1):
        print("speaker_turns: --channels needs a file (or exactly one --tracks file to split)", file=sys.stderr)
        return 2
    if a.channels and a.tracks:
        print("speaker_turns: pass --tracks (one file per speaker) OR --channels FILE, not both", file=sys.stderr)
        return 2
    wp = Path(a.words)
    if not wp.is_file():
        print(f"speaker_turns: input not found: {wp}", file=sys.stderr)
        return 2
    try:
        doc = json.loads(wp.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"speaker_turns: cannot read {wp}: {exc}", file=sys.stderr)
        return 2
    words = doc.get("words") if isinstance(doc, dict) else doc
    if not isinstance(words, list) or not words or not all(isinstance(w, dict) and "start" in w and "end" in w for w in words):
        print(f"speaker_turns: {wp} has no words with start/end times", file=sys.stderr)
        return 2
    try:
        signals, files, source = load_signals(a)
    except FileNotFoundError as exc:
        print(f"speaker_turns: input not found: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"speaker_turns: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - decoder / probe failure on a file that exists
        print(f"speaker_turns: cannot decode the audio: {exc}", file=sys.stderr)
        return 2
    names = [n.strip() for n in a.names.split(",")] if a.names else [f"S{k + 1}" for k in range(len(signals))]
    if len(names) != len(signals) or any(not n for n in names) or len(set(names)) != len(names):
        print(f"speaker_turns: {len(names)} name(s) for {len(signals)} track(s) / channel(s): give one distinct name each", file=sys.stderr)
        return 2
    if {"overlap", "unknown"} & set(names):
        print("speaker_turns: 'overlap' and 'unknown' are labels, not names", file=sys.stderr)
        return 2
    try:
        g = gates(signals, SR)
        lv = word_levels(signals, words, SR)
        labels = smooth_flips(words, label_words(lv, names, g, a.margin_db), a.margin_db, names)
        new = []
        for w, lab in zip(words, labels):
            nw = dict(w, speaker=lab["speaker"], speaker_margin_db=lab["margin"])
            if lab["smoothed"]:
                nw["smoothed"] = True
            new.append(nw)
        counts = {n: sum(1 for w in new if w["speaker"] == n) for n in names + ["overlap", "unknown"]}
        out = dict(doc) if isinstance(doc, dict) else {"schema": "avc.words/1"}
        out.setdefault("schema", "avc.words/1")
        out["words"] = new
        out["speakers"] = {"names": names, "source": source, "files": files, "gates_db": g,
                           "method": "loudest track per word by a margin, single-word flips smoothed; no speaker model",
                           "house_defaults": {"margin_db": a.margin_db, "neighbour_gap_s": NEIGHBOUR_GAP_S, "smooth_below_margin_x": 2}}
        out["turns"] = turns(new)
        out["counts"] = counts
        from core.fsio import write_json_atomic

        write_json_atomic(a.out, out)
    except Exception as exc:  # noqa: BLE001
        print(f"speaker_turns: tool error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"out": a.out, "turns": len(out["turns"]), "counts": counts, "smoothed": sum(1 for w in new if w.get("smoothed"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

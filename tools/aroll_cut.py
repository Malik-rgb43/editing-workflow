"""aroll_cut - propose a paper edit for a talking-head A-roll: whole sentences, in-points in the SILENCE before each sentence.

From a word-level transcript (``transcribe`` -> words.json) and the audio of the same source, it
  1. splits the words into sentences (a pause >= ``--gap`` seconds, or terminal punctuation);
  2. snaps every in-point to the quietest 20 ms inside the pause before the sentence (never into the first word) and every out-point to the
     quietest 20 ms inside the pause after it (a tail of speech is never cut; a join never lands mid-word);
  3. keeps the sentences you choose (``--keep 1,3-5``; default all) in their ORIGINAL order, and writes
        edit.json      segments with src_in/src_out/dst_in/dst_out, the first/last words and the text
        src_cuts.json  every join in the assembled timeline (where a cover / zoom must hide a jump: >= 6 frames each side)
        cut_text.txt   the text of the cut, one sentence per line (the reference for ``join_diff``)
This is a PROPOSAL for the human paper-edit approval (PROMPT.md gate): which sentences to keep is the editor's decision. Natural order and
whole sentences are the house rule; reordering is a logged exception, not something this tool does.

Limits: sentence boundaries come from pauses/punctuation, so ASR errors or a speaker with no pauses produce wrong splits - read the proposal.
Fail-closed: no words, no audio samples, or a keep-list that selects nothing exits 2.

Usage:
    python tools/aroll_cut.py <words.json> <audio-or-video> -o <dir> [--keep 1,3-5] [--gap 0.7] [--fps 30]
Exit: 0 proposal written, 2 refused / insufficient evidence, 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import _common  # noqa: F401

SENT_END = re.compile(r"[.!?…]$")


def split_sentences(words, gap=0.7):
    """Pure: [{w,start,end}] -> list of word lists."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt is None or nxt["start"] - w["end"] >= gap or SENT_END.search(w["w"].strip()):
            out.append(cur)
            cur = []
    return [s for s in out if s]


def quietest(energy, hop, lo, hi):
    """Time (s) of the quietest hop frame centre in [lo, hi]; ties resolve to the one closest to the middle."""
    a, b = max(0, int(lo / hop)), min(len(energy) - 1, int(hi / hop))
    if b < a:
        return (lo + hi) / 2
    best = min(range(a, b + 1), key=lambda k: (energy[k], abs((k * hop + hop / 2) - (lo + hi) / 2)))
    return best * hop + hop / 2


def parse_keep(spec, n):
    if not spec:
        return list(range(1, n + 1))
    keep = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            keep += list(range(int(a), int(b) + 1))
        elif part:
            keep.append(int(part))
    bad = [k for k in keep if not 1 <= k <= n]
    if bad:
        raise ValueError(f"keep ids out of range 1..{n}: {bad}")
    return sorted(set(keep))


def plan(sentences, energy, hop, duration, keep, margin=0.04, tail=0.15):
    segs = []
    for idx, s in enumerate(sentences, start=1):
        first, last = s[0], s[-1]
        prev_end = sentences[idx - 2][-1]["end"] if idx > 1 else 0.0
        next_start = sentences[idx][0]["start"] if idx < len(sentences) else duration
        gap_before = first["start"] - prev_end
        if gap_before > 2 * margin:
            t_in = quietest(energy, hop, prev_end + margin / 2, first["start"] - margin / 2)
        else:
            t_in = max(prev_end, first["start"] - margin)
        t_in = min(t_in, first["start"] - 0.005)
        gap_after = next_start - last["end"]
        if gap_after > 2 * margin:
            t_out = quietest(energy, hop, last["end"] + margin / 2, min(next_start - margin / 2, last["end"] + tail * 2))
        else:
            t_out = last["end"] + max(0.0, gap_after / 2)
        t_out = max(t_out, last["end"] + 0.005)
        segs.append({"id": idx, "text": " ".join(w["w"].strip() for w in s), "first_word": first["w"].strip(), "last_word": last["w"].strip(), "src_in": round(t_in, 3), "src_out": round(min(t_out, duration), 3)})
    chosen = [s for s in segs if s["id"] in keep]
    t = 0.0
    for s in chosen:
        d = s["src_out"] - s["src_in"]
        s["dst_in"], s["dst_out"] = round(t, 3), round(t + d, 3)
        t += d
    return chosen, segs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aroll_cut", description=__doc__.split("\n\n")[0])
    ap.add_argument("words")
    ap.add_argument("audio")
    ap.add_argument("-o", "--out-dir", required=True)
    ap.add_argument("--keep")
    ap.add_argument("--gap", type=float, default=0.7)
    ap.add_argument("--fps", type=float, default=30.0)
    a = ap.parse_args(argv)

    from core.errors import ToolkitError
    from core.fsio import write_json_atomic, write_text_atomic
    from core.media import read_audio_samples
    import numpy as np

    try:
        d = json.loads(Path(a.words).read_text(encoding="utf-8"))
        words = [w for w in d["words"] if str(w.get("w", "")).strip()]
        if not words:
            print("aroll_cut: the transcript has no words", file=sys.stderr)
            return 2
        sr = 16000
        pcm = read_audio_samples(a.audio, sample_rate=sr, channels=1)[:, 0].astype(np.float32) / 32768.0
    except (ToolkitError, KeyError, ValueError, OSError) as exc:
        print(f"aroll_cut: {exc}", file=sys.stderr)
        return 2
    hop = 0.02
    n = int(hop * sr)
    frames = len(pcm) // n
    if frames < 5:
        print("aroll_cut: the audio is too short to measure", file=sys.stderr)
        return 2
    energy = np.sqrt((pcm[: frames * n].reshape(frames, n) ** 2).mean(axis=1)).tolist()
    duration = len(pcm) / sr
    sentences = split_sentences(words, a.gap)
    try:
        keep = parse_keep(a.keep, len(sentences))
    except ValueError as exc:
        print(f"aroll_cut: {exc}", file=sys.stderr)
        return 2
    chosen, allsegs = plan(sentences, energy, hop, duration, keep)
    if not chosen:
        print("aroll_cut: nothing selected", file=sys.stderr)
        return 2
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    joins = []
    for x, y in zip(chosen, chosen[1:]):
        joins.append({"dst_time": x["dst_out"], "between": [x["id"], y["id"]], "src_jump": round(y["src_in"] - x["src_out"], 3), "cover_frames_each_side": 6, "cover_s": [round(x["dst_out"] - 6 / a.fps, 3), round(x["dst_out"] + 6 / a.fps, 3)]})
    write_json_atomic(out / "edit.json", {"schema": "avc.edit/1", "source": Path(a.audio).name, "sentences_total": len(sentences), "kept": keep, "segments": chosen, "total_s": chosen[-1]["dst_out"],
                                          "note": "a PROPOSAL for the paper-edit approval; natural order, whole sentences, in-point in the silence before the sentence"})
    write_json_atomic(out / "src_cuts.json", {"schema": "avc.src-cuts/1", "joins": joins})
    write_text_atomic(out / "cut_text.txt", "\n".join(s["text"] for s in chosen) + "\n")
    print(json.dumps({"sentences": len(sentences), "kept": len(chosen), "total_s": chosen[-1]["dst_out"], "joins": len(joins), "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

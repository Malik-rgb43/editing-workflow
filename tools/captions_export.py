"""captions_export - write sidecar subtitles (SRT, WebVTT or plain text) from the word table, in any language.

The burned-in captions are built in the composition; platforms and accessibility often want a sidecar file too. This tool groups the
words of ``words.json`` (schema avc.words/1, ``{"words": [{"w", "start", "end", "prob"}]}``) into readable cues: a cue ends at a sentence
mark (. ! ? and their Arabic / Hebrew forms), at a pause of at least ``--pause`` seconds, or when it reaches ``--max-words`` /
``--max-chars``. A cue is never shorter than ``--min-dur`` (extended into the gap only, never over the next cue). Right-to-left text is
written as it is (players handle the direction); nothing is translated.

Usage:
    python tools/captions_export.py <words.json> -o <out.srt|out.vtt|out.txt> [--format srt|vtt|txt] [--max-words 7] [--max-chars 42]
                                    [--pause 0.6] [--min-dur 0.8] [--offset 0.0]
Exit: 0 written, 2 refused (no words, bad input), 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ENDS = (".", "!", "?", "…", "؟", "۔", "׃")


def cues(words: list[dict], max_words: int = 7, max_chars: int = 42, pause: float = 0.6, min_dur: float = 0.8) -> list[dict]:
    """Pure: words -> [{start, end, text}] in time order."""
    ws = [w for w in words if isinstance(w, dict) and str(w.get("w", "")).strip() and isinstance(w.get("start"), (int, float)) and isinstance(w.get("end"), (int, float))]
    ws.sort(key=lambda w: w["start"])
    out: list[dict] = []
    cur: list[dict] = []

    def flush() -> None:
        if cur:
            out.append({"start": float(cur[0]["start"]), "end": float(cur[-1]["end"]), "text": " ".join(str(w["w"]).strip() for w in cur)})
            cur.clear()

    for i, w in enumerate(ws):
        if cur:
            gap = w["start"] - cur[-1]["end"]
            text_len = len(" ".join(str(x["w"]).strip() for x in cur + [w]))
            if gap >= pause or len(cur) >= max_words or text_len > max_chars:
                flush()
        cur.append(w)
        if str(w["w"]).strip().endswith(ENDS):
            flush()
    flush()
    for k, c in enumerate(out):
        nxt = out[k + 1]["start"] if k + 1 < len(out) else None
        if c["end"] - c["start"] < min_dur:
            c["end"] = c["start"] + min_dur if nxt is None else min(c["start"] + min_dur, nxt - 0.001)
        c["end"] = max(c["end"], c["start"] + 0.001)
    return out


def stamp(t: float, sep: str) -> str:
    ms = int(round(max(0.0, t) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def render(cs: list[dict], fmt: str, offset: float = 0.0) -> str:
    if fmt == "txt":
        return "\n".join(c["text"] for c in cs) + "\n"
    sep = "," if fmt == "srt" else "."
    blocks = []
    for n, c in enumerate(cs, 1):
        head = f"{n}\n" if fmt == "srt" else ""
        blocks.append(f"{head}{stamp(c['start'] + offset, sep)} --> {stamp(c['end'] + offset, sep)}\n{c['text']}\n")
    return ("WEBVTT\n\n" if fmt == "vtt" else "") + "\n".join(blocks)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="captions_export", description=__doc__.split("\n\n")[0])
    ap.add_argument("words")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--format", choices=("srt", "vtt", "txt"))
    ap.add_argument("--max-words", type=int, default=7)
    ap.add_argument("--max-chars", type=int, default=42)
    ap.add_argument("--pause", type=float, default=0.6)
    ap.add_argument("--min-dur", type=float, default=0.8)
    ap.add_argument("--offset", type=float, default=0.0, help="seconds added to every cue (the video starts later than the words)")
    a = ap.parse_args(argv)
    fmt = a.format or Path(a.out).suffix.lstrip(".").lower()
    if fmt not in ("srt", "vtt", "txt"):
        print("captions_export: pass --format srt|vtt|txt or an output ending in one of them", file=sys.stderr)
        return 2
    try:
        doc = json.loads(Path(a.words).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"captions_export: cannot read {a.words}: {exc}", file=sys.stderr)
        return 2
    words = doc.get("words", []) if isinstance(doc, dict) else doc
    cs = cues(words, a.max_words, a.max_chars, a.pause, a.min_dur)
    if not cs:
        print("captions_export: no words to write (expected avc.words/1: {\"words\": [{\"w\", \"start\", \"end\"}]})", file=sys.stderr)
        return 2
    try:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(render(cs, fmt, a.offset), encoding="utf-8")
    except OSError as exc:
        print(f"captions_export: {exc}", file=sys.stderr)
        return 3
    print(f"captions_export: {len(cs)} cues ({fmt}) -> {a.out}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except AttributeError:
        pass
    sys.exit(main())

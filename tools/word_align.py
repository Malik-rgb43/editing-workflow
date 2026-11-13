"""word_align - re-time a known Hebrew transcript to its audio with forced alignment (CTC, local, CPU), so cuts land on the real word edges.

Why: Whisper keeps the WORDS right but its word times are often 100-300 ms off in Hebrew, and about one word in nine "starts" inside silence
(measured on one real lesson: median start error 30 ms, p90 260 ms; 11.2 % of Whisper word starts in silence against 0.4 % after alignment).
A cut placed on such a time clips a syllable or leaves a breath. This tool keeps the transcript words and moves every edge to where the
audio says the word is: a Hebrew wav2vec2 CTC model places the letters, then each edge is refined on the 10 ms energy envelope.

Model (never downloaded implicitly): ``imvladikon/wav2vec2-large-xlsr-53-hebrew``, Apache-2.0 per its model card (checked 2026-11-13),
``model.safetensors`` 1,261,934,532 bytes (about 1.2 GB), pinned revision below. Where it comes from, in order: ``--model-dir DIR``,
a copy already in the Hugging Face cache (found automatically, no download), or ``--allow-download`` (only after the student said yes to the size).
To fetch it once ahead of time: ``--fetch-model`` prints the size and downloads nothing; ``--fetch-model --yes`` downloads the pinned revision.
Needs the ``align-cpu`` extra (torch, torchaudio, transformers); that extra is separate from ``asr-cpu`` and is installed only on a yes.

Input: ``words.json`` from ``transcribe`` (``words[{w, start, end, prob}]`` in seconds). Output: the same file shape with ``start``/``end`` refined and,
per word, ``asr_start``/``asr_end`` (the original), ``ctc_start``/``ctc_end`` (raw CTC), ``score`` (0..1) and an optional ``flag``:
``unaligned`` (no letters the model knows, or the window had too little audio: ASR times kept), ``stretched`` (letters spread over unscripted
speech or silence: the densest cluster was kept), ``low_score`` (< 0.15). A top-level ``align_stats`` block says how far the edges moved, so the
correction is visible, never hidden. Long files run in windows of about ``--chunk-s`` seconds, split at the largest pause and padded by
``--margin-s`` on both sides, so no word is cut at a window edge.

Text is normalised to the model alphabet: niqqud and punctuation stripped, digits and common Latin words mapped to Hebrew spelling
(4 -> ארבע, Claude -> קלוד). The default model is Hebrew only: a ``words.json`` whose ``language`` is not ``he`` is REFUSED.

Usage:
    python tools/word_align.py <audio-or-video> <words.json> -o words.aligned.json [--chunk-s 30] [--margin-s 0.6]
                               [--from-word I --to-word J] [--model-dir DIR | --allow-download] [--threads N]
    python tools/word_align.py --check          (is the aligner usable here: packages, model already on this computer)
    python tools/word_align.py --fetch-model [--yes]
Exit: 0 aligned, 2 refused (no model, no download permission, missing input, missing packages, not Hebrew, no words), 3 tool error.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import _common  # noqa: F401

MODEL_ID = "imvladikon/wav2vec2-large-xlsr-53-hebrew"
REVISION = "3dd308dda70b20507a6920b459052635973ae3cd"
MODEL_BYTES = 1_261_934_532  # model.safetensors; the small config/vocab files add about 7 kB
LICENSE = "Apache-2.0"
SR = 16000
SLICE = 160  # 10 ms at 16 kHz
PACKAGES = ("torch", "torchaudio", "transformers", "huggingface_hub", "numpy")

NIQQUD = re.compile("[֑-ׇ]")
NUM = {"0": "אפס", "1": "אחד", "2": "שתיים", "3": "שלוש", "4": "ארבע", "5": "חמש", "6": "שש", "7": "שבע", "8": "שמונה", "9": "תשע",
       "10": "עשר", "11": "אחת עשרה", "12": "שתים עשרה", "15": "חמש עשרה", "20": "עשרים", "30": "שלושים", "40": "ארבעים",
       "50": "חמישים", "60": "שישים", "100": "מאה", "1000": "אלף"}
LATIN = {"claude": "קלוד", "cloud": "קלוד", "code": "קוד", "ai": "איי איי", "motion": "מושן", "graphics": "גרפיקס", "waze": "וייז",
         "chatgpt": "צאט גיפיטי", "gpt": "גיפיטי", "capcut": "קאפקאט", "premiere": "פרימייר", "after": "אפטר", "effects": "אפקטס",
         "instagram": "אינסטגרם", "youtube": "יוטיוב", "tiktok": "טיקטוק", "reels": "רילס", "b": "בי", "roll": "רול", "ok": "אוקיי",
         "okay": "אוקיי", "m": "אם", "skill": "סקיל", "agent": "אייג'נט", "prompt": "פרומפט", "canva": "קנבה", "mcp": "אם סי פי"}


class Refused(Exception):
    """A clean refusal (exit 2): nothing was written."""


# ---------------------------------------------------------------- pure helpers (unit-tested, no heavy imports)

def norm_text(word: str, letters: set[str]) -> str:
    """ASR word -> string of model characters (may contain spaces), or '' when nothing in it is alignable."""
    s = NIQQUD.sub("", word).lower()
    out = []
    for p in re.findall(r"[a-z]+|\d+|[א-ת]+", s):
        if p.isdigit():
            out.append(NUM.get(p, ""))
        elif p[0].isascii():
            out.append(LATIN.get(p, ""))
        else:
            out.append(p)
    txt = " ".join(x for x in out if x)
    txt = "".join(c for c in txt if c in letters or c == " ")
    return re.sub(r"\s+", " ", txt).strip()


def make_chunks(words: list[dict], chunk_s: float, margin_s: float, dur_ms: int) -> list[tuple[int, int, int, int]]:
    """Group word indices into windows of about ``chunk_s`` (words carry start_ms/end_ms), split at the largest pause near the target.
    Returns (first_word, last_word, window_start_ms, window_end_ms) with ``margin_s`` of padding on both sides."""
    chunks, i, n = [], 0, len(words)
    while i < n:
        t0 = words[i]["start_ms"]
        j = i
        while j + 1 < n and words[j + 1]["end_ms"] - t0 < chunk_s * 1000:
            j += 1
        if j + 1 < n and j > i:
            lo = i + (j - i) // 2
            j = max(range(lo, j + 1), key=lambda k: words[k + 1]["start_ms"] - words[k]["end_ms"])
        a = max(0, words[i]["start_ms"] - int(margin_s * 1000))
        b = min(dur_ms, words[j]["end_ms"] + int(margin_s * 1000))
        chunks.append((i, j, a, b))
        i = j + 1
    return chunks


def refine_edges(words: list[dict], db, dur_ms: int) -> None:
    """Move each aligned word to the energy onset just before its first CTC spike and the fall to the local floor after its last one,
    bounded by the neighbours. ``db`` is the 10 ms level envelope in dB. Words without a CTC span keep their ASR times."""
    import numpy as np

    for n_, w in enumerate(words):
        if "ctc_start_ms" not in w:
            w["start_ms"], w["end_ms"] = w["asr_start_ms"], w["asr_end_ms"]
            continue
        prev_end = words[n_ - 1].get("ctc_end_ms", words[n_ - 1]["asr_end_ms"]) if n_ else 0
        nxt_start = words[n_ + 1].get("ctc_start_ms", words[n_ + 1]["asr_start_ms"]) if n_ + 1 < len(words) else dur_ms
        c0, c1 = w["ctc_start_ms"] // 10, w["ctc_end_ms"] // 10
        loc = db[max(0, c0 - 60): min(len(db) - 1, c1 + 60) + 1]
        floor = float(np.percentile(loc, 10)) + 8 if len(loc) else -60.0
        k, lim = c0, max(prev_end // 10, c0 - 12)  # onset: walk back (max 120 ms, not before the previous word)
        while k - 1 >= lim and db[k - 1] > floor:
            k -= 1
        start = k * 10
        k, lim = c1, min(nxt_start // 10, c1 + 30, len(db) - 1)  # offset: walk forward (max 300 ms, not into the next word)
        while k < lim and db[k] > floor:
            k += 1
        w["start_ms"], w["end_ms"] = int(start), int(max(k * 10, start + 40))
        if w.get("score", 1) < 0.15:
            w["flag"] = w.get("flag") or "low_score"


def stats_of(words: list[dict]) -> dict:
    import numpy as np

    al = [w for w in words if "ctc_start_ms" in w]
    ds = np.array([abs(w["start_ms"] - w["asr_start_ms"]) for w in al]) if al else np.zeros(1)
    de = np.array([abs(w["end_ms"] - w["asr_end_ms"]) for w in al]) if al else np.zeros(1)
    both = np.concatenate([ds, de])

    def md(a):
        return {"median": float(np.median(a)), "p90": float(np.percentile(a, 90))}

    return {"aligned": len(al), "unaligned": len(words) - len(al), "start_shift_ms": md(ds), "end_shift_ms": md(de), "edge_shift_ms": md(both),
            "long_words_over_1200ms": [k for k, w in enumerate(words) if w["end_ms"] - w["start_ms"] > 1200]}


# ---------------------------------------------------------------- model location

def missing_packages() -> list[str]:
    return [p for p in PACKAGES if importlib.util.find_spec(p) is None]


def cached_model_dir() -> str | None:
    """The pinned snapshot in the Hugging Face cache, or any snapshot of the model, with no network access."""
    root = Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface") / "hub" / ("models--" + MODEL_ID.replace("/", "--")) / "snapshots"
    if not root.is_dir():
        return None
    snaps = sorted((p for p in root.iterdir() if (p / "model.safetensors").exists() and (p / "vocab.json").exists()),
                   key=lambda p: (p.name != REVISION, p.name))
    return str(snaps[0]) if snaps else None


def fetch_model(yes: bool) -> int:
    gb = MODEL_BYTES / 1e9
    print(f"model {MODEL_ID} rev {REVISION[:12]} licence {LICENSE}: model.safetensors {MODEL_BYTES:,} bytes (about {gb:.1f} GB) into the Hugging Face cache")
    if not yes:
        print("nothing downloaded. Ask the student; with a yes run again with --yes.")
        return 0
    if missing_packages():
        print("refused: install the align-cpu extra first (missing: " + ", ".join(missing_packages()) + ")", file=sys.stderr)
        return 2
    from huggingface_hub import snapshot_download

    path = snapshot_download(MODEL_ID, revision=REVISION, allow_patterns=["*.json", "model.safetensors", "README.md"])
    print(f"downloaded -> {path}")
    return 0


def do_check() -> int:
    miss, cached = missing_packages(), cached_model_dir()
    print(json.dumps({"tool": "word_align", "model": MODEL_ID, "revision": REVISION, "licence": LICENSE, "bytes": MODEL_BYTES,
                      "packages_missing": miss, "model_on_this_computer": cached, "usable": not miss and bool(cached)}, ensure_ascii=False, indent=1))
    return 0


# ---------------------------------------------------------------- the alignment itself

def load_audio(src: str, tmp: str):
    import numpy as np

    raw = os.path.join(tmp, "a16k.raw")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", raw], check=True)
    return np.fromfile(raw, dtype=np.int16).astype(np.float32) / 32768.0


def slice_db(audio):
    import numpy as np

    n = len(audio) // SLICE
    x = audio[: n * SLICE].reshape(n, SLICE)
    return 20 * np.log10(np.sqrt((x * x).mean(axis=1)) + 1e-9)


def align(args, model_path: str, data: dict) -> dict:
    import numpy as np
    import torch
    import torchaudio.functional as AF
    from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

    torch.set_num_threads(args.threads)
    t_start = time.time()
    proc = Wav2Vec2FeatureExtractor.from_pretrained(model_path)
    model = Wav2Vec2ForCTC.from_pretrained(model_path).eval()
    vocab = json.loads((Path(model_path) / "vocab.json").read_text(encoding="utf-8"))
    blank = vocab.get("[PAD]", vocab.get("<pad>"))  # the CTC blank
    space = vocab.get("|")
    letters = {c for c in vocab if len(c) == 1 and "א" <= c <= "ת"}

    with tempfile.TemporaryDirectory(prefix="wordalign_") as tmp:
        audio = load_audio(args.source, tmp)
    dur_ms = int(len(audio) / SR * 1000)
    db = slice_db(audio)

    allw = data["words"]
    sel = list(range(args.from_word, (args.to_word + 1) if args.to_word is not None else len(allw)))
    words = []
    for k in sel:
        w = dict(allw[k])
        w["start_ms"], w["end_ms"] = int(round(w["start"] * 1000)), int(round(w["end"] * 1000))
        w["asr_start_ms"], w["asr_end_ms"] = w["start_ms"], w["end_ms"]
        w["norm"] = norm_text(w["w"], letters)
        words.append(w)

    chunks = make_chunks(words, args.chunk_s, args.margin_s, dur_ms)
    print(f"{len(words)} words, {len(chunks)} windows, audio {dur_ms / 1000:.1f}s", flush=True)
    for ci, (i, j, s_ms, e_ms) in enumerate(chunks):
        seg = audio[s_ms * 16: e_ms * 16]
        with torch.inference_mode():
            lp = torch.log_softmax(model(proc(seg, sampling_rate=SR, return_tensors="pt").input_values).logits, dim=-1)
        T = lp.shape[1]
        fdur = (len(seg) / SR) / T  # seconds per CTC frame (about 0.02)
        tokens, owner = [], []
        idx = [k for k in range(i, j + 1) if words[k]["norm"]]
        for n_, k in enumerate(idx):
            for c in words[k]["norm"]:
                if c == " ":
                    if space is not None:
                        tokens.append(space)
                        owner.append(-1)
                    continue
                tokens.append(vocab[c])
                owner.append(k)
            if space is not None and n_ < len(idx) - 1:
                tokens.append(space)
                owner.append(-1)
        for k in range(i, j + 1):
            if not words[k]["norm"]:
                words[k]["flag"] = "unaligned"
        if not tokens or len(tokens) > T:
            for k in idx:
                words[k]["flag"] = "unaligned"
            continue
        try:
            ali, scores = AF.forced_align(lp, torch.tensor([tokens], dtype=torch.int32), blank=blank)
        except Exception as ex:  # too little audio for the text
            print(f"  window {ci}: align failed ({ex}); ASR times kept", flush=True)
            for k in idx:
                words[k]["flag"] = "unaligned"
            continue
        ali, scores = ali[0].tolist(), scores[0].exp().tolist()
        pos, prev, span = -1, blank, {}
        for f, (tok, sc) in enumerate(zip(ali, scores)):
            if tok != blank and (tok != prev or prev == blank):
                pos += 1
            if tok != blank and 0 <= pos < len(owner) and owner[pos] >= 0:
                span.setdefault(owner[pos], []).append((f, sc, pos))
            prev = tok
        for k in idx:
            if k not in span:
                words[k]["flag"] = "unaligned"
                continue
            # a word's letters can be stretched over unscripted speech or a long silence: split the letter frames into clusters at gaps
            # > 0.3 s and keep the cluster with the most distinct letters, ties -> closest to the ASR time
            fr = span[k]
            gapf = max(1, int(0.3 / fdur))
            cl = [[fr[0]]]
            for x in fr[1:]:
                (cl[-1].append(x) if x[0] - cl[-1][-1][0] <= gapf else cl.append([x]))
            asr_mid = (words[k]["asr_start_ms"] + words[k]["asr_end_ms"]) / 2 - s_ms
            best = max(cl, key=lambda c: (len({x[2] for x in c}), -abs((c[0][0] + c[-1][0]) / 2 * fdur * 1000 - asr_mid)))
            if len(cl) > 1:
                words[k]["flag"] = "stretched"
            words[k]["ctc_start_ms"] = s_ms + int(round(best[0][0] * fdur * 1000))
            words[k]["ctc_end_ms"] = s_ms + int(round((best[-1][0] + 1) * fdur * 1000))
            words[k]["score"] = round(float(np.mean([x[1] for x in best])), 3)
        print(f"  window {ci + 1}/{len(chunks)} {s_ms / 1000:7.1f}-{e_ms / 1000:7.1f}s words {sel[i]}-{sel[j]}", flush=True)

    refine_edges(words, db, dur_ms)
    stats = stats_of(words)
    for w in words:
        w.pop("norm", None)
        for k_ms, k_s in (("start_ms", "start"), ("end_ms", "end"), ("asr_start_ms", "asr_start"), ("asr_end_ms", "asr_end"),
                          ("ctc_start_ms", "ctc_start"), ("ctc_end_ms", "ctc_end")):
            if k_ms in w:
                w[k_s] = round(w.pop(k_ms) / 1000, 3)
    out = {k: v for k, v in data.items() if k != "segments"}
    out.update({"words": words, "aligned_with": {"model": MODEL_ID, "revision": REVISION}, "align_stats": stats,
                "align_elapsed_s": round(time.time() - t_start, 1)})
    return out


def run(a) -> int:
    if not Path(a.source).is_file() or not Path(a.words).is_file():
        raise Refused("input audio/video or words.json not found")
    data = json.loads(Path(a.words).read_text(encoding="utf-8"))
    if not data.get("words"):
        raise Refused("words.json has no words")
    lang = (data.get("language") or "he").lower()
    if lang not in ("he", "iw") and not a.model_dir:
        raise Refused(f"the default aligner is Hebrew only and this transcript is '{lang}'; give --model-dir of an aligner for that language")
    miss = missing_packages()
    if miss:
        raise Refused("missing packages: " + ", ".join(miss) + " (the align-cpu extra, installed only after the student's yes)")
    model_path = a.model_dir or cached_model_dir()
    if not model_path:
        if not a.allow_download:
            raise Refused(f"the model is not on this computer. It is {MODEL_BYTES / 1e9:.1f} GB ({MODEL_ID}, {LICENSE}). Ask the student, then use --fetch-model --yes or --allow-download")
        fetch_model(True)
        model_path = cached_model_dir()
        if not model_path:
            raise Refused("download finished but the model was not found in the cache")
    out = align(a, model_path, data)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["align_stats"], ensure_ascii=False))
    print(f"done -> {a.out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?")
    ap.add_argument("words", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--chunk-s", type=float, default=30.0)
    ap.add_argument("--margin-s", type=float, default=0.6)
    ap.add_argument("--from-word", type=int, default=0)
    ap.add_argument("--to-word", type=int, default=None)
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--model-dir")
    ap.add_argument("--allow-download", action="store_true", help="ONLY after the student said yes to the shown size")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fetch-model", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    try:
        if a.check:
            return do_check()
        if a.fetch_model:
            return fetch_model(a.yes)
        if not (a.source and a.words and a.out):
            ap.error("need <audio-or-video> <words.json> -o OUT (or --check / --fetch-model)")
        return run(a)
    except Refused as ex:
        print(f"refused: {ex}", file=sys.stderr)
        return 2
    except Exception as ex:  # noqa: BLE001 - the tool contract: exit 3 with the reason, never a traceback wall
        print(f"tool error: {type(ex).__name__}: {ex}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())

"""transcribe - word-level speech-to-text (Hebrew first) with route auto-selection and a CPU route that always works.

Output ``words.json`` (schema avc.words/1): language, model, route, audio duration, ``words[{w, start, end, prob}]`` in seconds (rational
times are not needed here: ASR timing is not frame-exact), plus the run facts (route, device, seconds, realtime factor) so every run is
its own benchmark. Heavy imports happen only inside ``main`` after argument parsing, so ``--help`` returns in well under a second (the
original took > 45 s: E04-L01).

Routes (ADR 0002: selected automatically; the student chooses nothing):
  faster-whisper   CPU CTranslate2 int8 - ALWAYS available when the ``asr-cpu`` extra is installed. The default.
  whisper.cpp      only if ``--whisper-cpp BIN`` (or toolkit.toml models/binaries) points to a binary AND ``--route whisper-cpp`` is requested;
                   the Vulkan build was ~9.8x faster than the CPU route on ONE machine (author's, 614 s of audio, E08) - unmeasured elsewhere.
                   On that machine `GGML_VK_DISABLE_COOPMAT=1` was required [LOCAL-only]; this tool sets it only when you pass --vk-no-coopmat.
Model weights are NEVER downloaded implicitly: pass ``--model-dir DIR`` (or set [models] asr_model_dir) or add ``--allow-download`` to let
faster-whisper fetch the named model (size is large; the repo id is shown first). Hebrew default model id: ``ivrit-ai/whisper-large-v3-turbo-ct2``
(Apache-2.0 per its model card as of 2026-10-02; PIN the revision you test - `--revision`). VAD is OFF by default (E08: it hurt speed and WER on the
test corpus); ``--vad`` enables it per clip. Accuracy: WER ~18 % on FLEURS Hebrew (68 clips, the reference machine) - always spot-check names/numbers.

Usage:
    python tools/transcribe.py <audio-or-video> -o words.json [--language he] [--model-dir DIR | --allow-download] [--revision SHA]
                               [--route auto|faster-whisper|whisper-cpp] [--vad] [--beam 5] [--threads N]
    python tools/transcribe.py --check          (which routes are usable on this machine; imports nothing heavy beyond find_spec)
Exit: 0 transcribed, 2 refused (no model, no download permission, missing input, no words), 3 tool error.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path

import _common  # noqa: F401

DEFAULT_HE_MODEL = "ivrit-ai/whisper-large-v3-turbo-ct2"


def available_routes(whisper_cpp: str | None = None) -> dict:
    fw = importlib.util.find_spec("faster_whisper") is not None
    cpp = whisper_cpp or shutil.which("whisper-cli") or shutil.which("whisper-cpp")
    return {
        "faster-whisper": {"usable": fw, "why": "CPU CTranslate2 int8 (extra: asr-cpu)" if fw else "pip/uv extra `asr-cpu` is not installed"},
        "whisper-cpp": {"usable": bool(cpp), "binary": cpp, "why": "binary found" if cpp else "no whisper.cpp binary configured (optional, faster on some GPUs; unmeasured elsewhere)"},
    }


def choose_route(requested: str, routes: dict) -> str | None:
    if requested != "auto":
        return requested if routes.get(requested, {}).get("usable") else None
    return "faster-whisper" if routes["faster-whisper"]["usable"] else None  # whisper.cpp is never auto-selected (unmeasured except one machine)


def normalize_words(raw_words) -> list[dict]:
    """Clean engine output: strip, drop empty tokens, enforce non-negative, monotonic, end >= start. Pure; unit-tested."""
    out, prev_end = [], 0.0
    for w in raw_words:
        text = str(w.get("w", "")).strip()
        if not text:
            continue
        s = max(float(w["start"]), 0.0)
        e = max(float(w["end"]), s)
        s = max(s, prev_end - 0.001) if out else s
        e = max(e, s)
        out.append({"w": text, "start": round(s, 3), "end": round(e, 3), "prob": None if w.get("prob") is None else round(float(w["prob"]), 3)})
        prev_end = e
    return out


def run_faster_whisper(path, model_ref, a, local: bool):
    from faster_whisper import WhisperModel  # heavy import, only now

    kw = {"device": "cpu", "compute_type": "int8", "local_files_only": local}
    if a.threads:
        kw["cpu_threads"] = a.threads
    if a.revision and not local:
        kw["revision"] = a.revision
    model = WhisperModel(model_ref, **kw)
    segs, info = model.transcribe(path, language=None if a.language == "auto" else a.language, word_timestamps=True, vad_filter=a.vad, beam_size=a.beam)
    words = []
    for s in segs:
        for w in s.words or []:
            words.append({"w": w.word, "start": w.start, "end": w.end, "prob": w.probability})
    return words, {"language": info.language, "duration_s": round(float(info.duration), 3), "device": "cpu", "compute_type": "int8"}


def run_whisper_cpp(path, binary, model_file, a):
    from core.procs import run
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="avc-asr-"))
    wav = tmp / "in.wav"
    from core.ffprobe import find_ffmpeg

    r = run([find_ffmpeg(), "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", str(wav)], timeout=900)
    if r.returncode != 0:
        raise RuntimeError("audio extraction failed")
    env = dict(os.environ)
    if a.vk_no_coopmat:
        env["GGML_VK_DISABLE_COOPMAT"] = "1"
    out_base = tmp / "out"
    cmd = [binary, "-m", str(model_file), "-f", str(wav), "-l", a.language if a.language != "auto" else "auto", "-ojf", "-of", str(out_base)] + (["--vad"] if a.vad else [])
    rr = run(cmd, env=env, timeout=a.timeout)
    if rr.returncode != 0 or not (tmp / "out.json").is_file():
        raise RuntimeError(f"whisper.cpp failed (exit {rr.returncode}): {(rr.stderr or '').strip()[-200:]}")
    data = json.loads((tmp / "out.json").read_text(encoding="utf-8"))
    words = []
    for seg in data.get("transcription", []):
        for t in seg.get("tokens", []):
            txt = t.get("text", "")
            if txt.startswith("[_") or not txt.strip():
                continue
            words.append({"w": txt, "start": t["offsets"]["from"] / 1000.0, "end": t["offsets"]["to"] / 1000.0, "prob": t.get("p")})
    shutil.rmtree(tmp, ignore_errors=True)
    return words, {"language": a.language, "device": "whisper.cpp (backend per build)"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="transcribe", description=__doc__.split("\n\n")[0])
    ap.add_argument("media", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--language", default="he")
    ap.add_argument("--model-dir")
    ap.add_argument("--model-id", default=DEFAULT_HE_MODEL)
    ap.add_argument("--allow-download", action="store_true")
    ap.add_argument("--revision")
    ap.add_argument("--route", default="auto", choices=["auto", "faster-whisper", "whisper-cpp"])
    ap.add_argument("--whisper-cpp")
    ap.add_argument("--model-file", help="ggml model file for whisper.cpp")
    ap.add_argument("--vk-no-coopmat", action="store_true")
    ap.add_argument("--vad", action="store_true")
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--threads", type=int)
    ap.add_argument("--timeout", type=float, default=7200.0)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)

    routes = available_routes(a.whisper_cpp)
    if a.check:
        print(json.dumps({"routes": routes, "default": choose_route("auto", routes), "default_model_id": DEFAULT_HE_MODEL}, indent=2))
        return 0 if choose_route("auto", routes) else 2
    if not a.media or not a.out:
        ap.error("need <media> and -o words.json")
    if not Path(a.media).is_file():
        print(f"transcribe: input not found: {a.media}", file=sys.stderr)
        return 2
    route = choose_route(a.route, routes)
    if route is None:
        print("transcribe: no usable route. Install the CPU route: `uv sync --extra asr-cpu` (or pip install faster-whisper).", file=sys.stderr)
        return 2
    from core.config import load_config

    cfg = load_config()
    model_dir = a.model_dir or (str(cfg.path("models.asr_model_dir")) if cfg.path("models.asr_model_dir") else None)
    t0 = time.monotonic()
    try:
        if route == "faster-whisper":
            if model_dir:
                words, facts = run_faster_whisper(a.media, model_dir, a, local=True)
                model_label = f"local:{Path(model_dir).name}"
            elif a.allow_download:
                print(f"transcribe: --allow-download: faster-whisper will fetch {a.model_id!r} (large download, cached under the HF cache; pin --revision)", file=sys.stderr)
                words, facts = run_faster_whisper(a.media, a.model_id, a, local=False)
                model_label = a.model_id + (f"@{a.revision}" if a.revision else " (UNPINNED)")
            else:
                print(f"transcribe: no model. Pass --model-dir DIR (or [models] asr_model_dir), or --allow-download to fetch {a.model_id!r} (shown before download; weights are never fetched implicitly).", file=sys.stderr)
                return 2
        else:
            if not a.model_file or not Path(a.model_file).is_file():
                print("transcribe: whisper-cpp route needs --model-file (a ggml model)", file=sys.stderr)
                return 2
            words, facts = run_whisper_cpp(a.media, routes["whisper-cpp"]["binary"], a.model_file, a)
            model_label = f"ggml:{Path(a.model_file).name}"
    except Exception as exc:  # noqa: BLE001
        print(f"transcribe: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    words = normalize_words(words)
    if not words:
        print("transcribe: the engine returned no words (silence, wrong language, or a model problem): refusing to write an empty transcript as success", file=sys.stderr)
        return 2
    secs = round(time.monotonic() - t0, 2)
    dur = facts.get("duration_s") or words[-1]["end"]
    from core.fsio import write_json_atomic

    write_json_atomic(a.out, {"schema": "avc.words/1", "language": facts.get("language", a.language), "model": model_label, "route": route, "vad": a.vad, "audio_duration_s": dur, "run": {**facts, "wall_s": secs, "realtime_factor": round(dur / secs, 2) if secs else None}, "words": words})
    print(f"transcribe: {len(words)} words, route {route}, {secs}s wall -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

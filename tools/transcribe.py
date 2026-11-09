"""transcribe - word-level speech-to-text in any language (Hebrew deepest) with route auto-selection and a CPU route that always works.

Output ``words.json`` (schema avc.words/1): language, model, route, audio duration, ``words[{w, start, end, prob}]`` in seconds (rational
times are not needed here: ASR timing is not frame-exact), plus the run facts (route, device, seconds, realtime factor) so every run is
its own benchmark. Heavy imports happen only inside ``main`` after argument parsing, so ``--help`` returns in well under a second (the
original took > 45 s: E04-L01).

Routes (ADR 0002: selected automatically; the student chooses nothing):
  faster-whisper   CPU CTranslate2 int8 - ALWAYS available when the ``asr-cpu`` extra is installed. The default.
Model weights are NEVER downloaded implicitly. Where the model comes from, in order: ``--model-dir DIR``, [models] asr_model_dir, a copy already
in the Hugging Face cache (found automatically, no download, the pinned revision preferred), or ``--allow-download``. To download it ONCE ahead
of time (the install step does this after the student's yes): ``--fetch-model`` prints the size and downloads nothing; ``--fetch-model --yes``
downloads the pinned revision into the Hugging Face cache, where every later run finds it. Hebrew default model id: ``ivrit-ai/whisper-large-v3-turbo-ct2``
(Apache-2.0 per its model card as of 2026-10-02; PIN the revision you test - `--revision`). VAD is OFF by default (E08: it hurt speed and WER on the
test corpus); ``--vad`` enables it per clip. Accuracy: WER ~18 % on FLEURS Hebrew (68 clips, the reference machine) - always spot-check names/numbers.

Language (never assumed): ``--language auto`` (the default) lets the model detect it; pass the code once it is known (``he``, ``en``, ``ar`` ...).
The Hebrew default model is tuned for Hebrew only, so with it any other language is REFUSED (exit 2, nothing written) and the multilingual
route is printed instead: ``--language <code> --model-id Systran/faster-whisper-large-v3 --allow-download`` (a large download, shown first;
unmeasured on the reference machine) or ``--model-dir`` of a local multilingual model. A model counts as Hebrew-only when its id or folder
name contains "ivrit"; ``--model-lang he|multi`` overrides that guess for a local folder.

Usage:
    python tools/transcribe.py <audio-or-video> -o words.json [--language auto|he|en|...] [--model-dir DIR | --allow-download]
                               [--model-id ID] [--model-lang he|multi] [--revision SHA] [--vad] [--beam 5] [--threads N]
    python tools/transcribe.py --check          (which routes are usable and whether the model is already on this computer)
    python tools/transcribe.py --fetch-model [--model-id ID] [--yes]   (show the download; with --yes download it once, before any edit)
Exit: 0 transcribed, 2 refused (no model, no download permission, missing input, no words, a language the model is not for), 3 tool error.
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
MULTILINGUAL_MODEL = "Systran/faster-whisper-large-v3"
# Pinned revisions and sizes (catalogue ivrit-ct2 / docs local-vs-paid, verified 2026-10-03): shown before any download.
KNOWN_MODELS = {
    DEFAULT_HE_MODEL: {"revision": "72ad623a37947395efcc3933132353790e5a12f5", "bytes": 1_621_667_540, "license": "Apache-2.0"},
    MULTILINGUAL_MODEL: {"revision": None, "bytes": 3_087_284_237, "license": "MIT"},
}


def hf_cache_roots(env=None) -> list[Path]:
    """Pure (given env): the Hugging Face hub cache folders to look in, most specific first."""
    env = os.environ if env is None else env
    roots = []
    if env.get("HF_HUB_CACHE"):
        roots.append(Path(env["HF_HUB_CACHE"]))
    if env.get("HF_HOME"):
        roots.append(Path(env["HF_HOME"]) / "hub")
    roots.append(Path.home() / ".cache" / "huggingface" / "hub")
    return roots


def cached_model_dir(model_id: str, revision: str | None = None, roots: list[Path] | None = None) -> str | None:
    """A complete local copy of ``model_id`` already in the HF cache (a snapshot folder holding model.bin), or None. The pinned revision
    wins when present; otherwise the newest complete snapshot. Never downloads. Seen 2026-11-09: the model sat in the cache and the tool
    still said "no model", so the agent asked the student to download 1.6 GB again."""
    if "/" not in model_id:
        return None
    revision = revision or (KNOWN_MODELS.get(model_id) or {}).get("revision")
    name = "models--" + model_id.replace("/", "--")
    for root in roots if roots is not None else hf_cache_roots():
        snaps = root / name / "snapshots"
        if not snaps.is_dir():
            continue
        if revision and (snaps / revision / "model.bin").is_file():
            return str(snaps / revision)
        ok = [d for d in snaps.iterdir() if (d / "model.bin").is_file()]
        if ok:
            return str(max(ok, key=lambda d: d.stat().st_mtime))
    return None


def fetch_model(model_id: str, revision: str | None, yes: bool) -> int:
    """--fetch-model: without --yes print what would be downloaded (nothing is fetched); with --yes download it once into the HF cache."""
    info = KNOWN_MODELS.get(model_id, {})
    revision = revision or info.get("revision")
    have = cached_model_dir(model_id, revision)
    plan = {"model_id": model_id, "revision": revision or "UNPINNED", "bytes": info.get("bytes", "unknown (check the model page)"),
            "license": info.get("license", "check the model page"), "source": f"https://huggingface.co/{model_id}", "already_here": have}
    if have:
        print(json.dumps({**plan, "status": "already on this computer, nothing to download"}, indent=2))
        return 0
    if not yes:
        print(json.dumps({**plan, "status": "nothing was downloaded: show this to the user; after their yes run the same command with --yes"}, indent=2))
        return 0
    try:
        from huggingface_hub import snapshot_download  # installed with faster-whisper
    except ImportError:
        print("transcribe: huggingface_hub is missing: install the speech-to-text route first (`uv sync --extra asr-cpu`).", file=sys.stderr)
        return 2
    try:
        path = snapshot_download(model_id, revision=revision)
    except Exception as exc:  # noqa: BLE001
        print(f"transcribe: download failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    if not (Path(path) / "model.bin").is_file():
        print(f"transcribe: downloaded {path} but it holds no model.bin", file=sys.stderr)
        return 3
    print(json.dumps({**plan, "status": "downloaded", "path": path}, indent=2))
    return 0


def hebrew_only(model_ref: str, model_lang: str | None) -> bool:
    """Pure: is this model tuned for Hebrew only? An explicit --model-lang wins; otherwise the ivrit name decides."""
    if model_lang:
        return model_lang == "he"
    return "ivrit" in str(model_ref).lower()


def language_refusal(requested: str, detected: str | None, model_ref: str, model_lang: str | None) -> str | None:
    """Pure: the refusal text when the speech language does not fit a Hebrew-only model, else None."""
    if not hebrew_only(model_ref, model_lang):
        return None
    lang = requested if requested != "auto" else (detected or "auto")
    if lang in ("he", "iw", "auto"):
        return None
    how = "detected" if requested == "auto" else "requested"
    return (f"transcribe: the speech language is {lang!r} ({how}), but {model_ref!r} is tuned for Hebrew only; nothing was written. "
            f"For {lang!r} use a multilingual model: --language {lang} --model-id {MULTILINGUAL_MODEL} --allow-download (a large download: "
            f"show it to the user and get their yes first), or --model-dir <a local multilingual model> --model-lang multi.")


def venv_python(venv: str | Path | None) -> Path | None:
    """The Python inside a virtualenv folder (Windows Scripts/python.exe or POSIX bin/python), or None."""
    if not venv:
        return None
    for rel in (("Scripts", "python.exe"), ("bin", "python3"), ("bin", "python")):
        cand = Path(venv).joinpath(*rel)
        if cand.is_file():
            return cand
    return None


def asr_venv_python() -> Path | None:
    """The installer's separate speech-to-text environment ([models] asr_venv, written by `apply --local`), if it exists and is not
    the Python already running. Seen 2026-11-09 (review): `--local` installed faster-whisper there, but this tool only looked at the
    current Python, so the student was told to install a route that was already installed."""
    try:
        from core.config import load_config

        v = load_config().path("models.asr_venv")
    except Exception:  # noqa: BLE001 - no config is a normal state
        return None
    py = venv_python(v)
    if py is None:
        return None
    try:
        if Path(sys.executable).resolve() == py.resolve():
            return None
    except OSError:
        return None
    return py


def available_routes() -> dict:
    fw = importlib.util.find_spec("faster_whisper") is not None
    return {"faster-whisper": {"usable": fw, "why": "CPU CTranslate2 int8 (extra: asr-cpu)" if fw else "pip/uv extra `asr-cpu` is not installed"}}


def choose_route(routes: dict) -> str | None:
    return "faster-whisper" if routes["faster-whisper"]["usable"] else None


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
    return words, {"language": info.language, "language_probability": round(float(getattr(info, "language_probability", 0.0) or 0.0), 3),
                   "duration_s": round(float(info.duration), 3), "device": "cpu", "compute_type": "int8"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="transcribe", description=__doc__.split("\n\n")[0])
    ap.add_argument("media", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--language", default="auto", help="speech language code, or auto (detect); never assumed")
    ap.add_argument("--model-dir")
    ap.add_argument("--model-id", default=DEFAULT_HE_MODEL)
    ap.add_argument("--model-lang", choices=("he", "multi"), help="what a local --model-dir is for (default: guessed from its name)")
    ap.add_argument("--allow-download", action="store_true")
    ap.add_argument("--revision")
    ap.add_argument("--vad", action="store_true")
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--threads", type=int)
    ap.add_argument("--timeout", type=float, default=7200.0)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fetch-model", action="store_true", help="download the model once (shows the size; needs --yes to download)")
    ap.add_argument("--yes", action="store_true", help="with --fetch-model: the user approved the shown download")
    a = ap.parse_args(argv)
    if a.fetch_model:
        return fetch_model(a.model_id, a.revision, a.yes)

    routes = available_routes()
    if a.check:
        if choose_route(routes) is None and not os.environ.get("AVC_ASR_REEXEC") and asr_venv_python() is not None:
            import subprocess

            return subprocess.call([str(asr_venv_python()), "-X", "utf8", str(Path(__file__).resolve()), "--check"], env={**os.environ, "AVC_ASR_REEXEC": "1"})
        print(json.dumps({"routes": routes, "default": choose_route(routes), "default_model_id": DEFAULT_HE_MODEL, "multilingual_model_id": MULTILINGUAL_MODEL,
                          "model_on_this_computer": {m: cached_model_dir(m) for m in (DEFAULT_HE_MODEL, MULTILINGUAL_MODEL)}}, indent=2))
        return 0 if choose_route(routes) else 2
    if not a.media or not a.out:
        ap.error("need <media> and -o words.json")
    if not Path(a.media).is_file():
        print(f"transcribe: input not found: {a.media}", file=sys.stderr)
        return 2
    route = choose_route(routes)
    if route is None and not os.environ.get("AVC_ASR_REEXEC"):
        py = asr_venv_python()
        if py is not None:  # run the same command inside the installed speech-to-text environment
            import subprocess

            print(f"transcribe: running inside the installed speech-to-text environment ({py})", file=sys.stderr)
            return subprocess.call([str(py), "-X", "utf8", str(Path(__file__).resolve()), *(sys.argv[1:] if argv is None else argv)],
                                   env={**os.environ, "AVC_ASR_REEXEC": "1"})
    if route is None:
        print("transcribe: no usable route. Install the CPU route: `uv sync --extra asr-cpu` (or pip install faster-whisper).", file=sys.stderr)
        return 2
    from core.config import load_config

    cfg = load_config()
    model_dir = a.model_dir or (str(cfg.path("models.asr_model_dir")) if cfg.path("models.asr_model_dir") else None)
    if model_dir and not (Path(model_dir) / "model.bin").is_file():
        print(f"transcribe: {model_dir} is not a CTranslate2 model folder (no model.bin). Point --model-dir (or [models] asr_model_dir) at the folder "
              "that holds model.bin, or use --allow-download.", file=sys.stderr)
        return 2
    if not model_dir:
        model_dir = cached_model_dir(a.model_id, a.revision)
        if model_dir:
            print(f"transcribe: using the copy of {a.model_id!r} already on this computer ({model_dir}); nothing downloaded", file=sys.stderr)
    model_ref = model_dir or a.model_id
    early = language_refusal(a.language, None, model_ref, a.model_lang)
    if early:
        print(early, file=sys.stderr)
        return 2
    t0 = time.monotonic()
    try:
        if model_dir:
            words, facts = run_faster_whisper(a.media, model_dir, a, local=True)
            model_label = f"local:{Path(model_dir).name}"
        elif a.allow_download:
            print(f"transcribe: --allow-download: faster-whisper will fetch {a.model_id!r} (large download, cached under the HF cache; pin --revision)", file=sys.stderr)
            words, facts = run_faster_whisper(a.media, a.model_id, a, local=False)
            model_label = a.model_id + (f"@{a.revision}" if a.revision else " (UNPINNED)")
        else:
            print(f"transcribe: the model {a.model_id!r} is not on this computer yet (not in --model-dir, [models] asr_model_dir or the Hugging Face cache). "
                  f"Run `python tools/transcribe.py --fetch-model --model-id {a.model_id}` to show the user its size, and after their yes the same "
                  "command with --yes (a one-time download; every later run finds it). Nothing was downloaded.", file=sys.stderr)
            return 2
    except Exception as exc:  # noqa: BLE001
        print(f"transcribe: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    late = language_refusal(a.language, facts.get("language"), model_ref, a.model_lang)
    if late:
        print(late + f" (detection probability {facts.get('language_probability')})", file=sys.stderr)
        return 2
    words = normalize_words(words)
    if not words:
        print("transcribe: the engine returned no words (silence, wrong language, or a model problem): refusing to write an empty transcript as success", file=sys.stderr)
        return 2
    secs = round(time.monotonic() - t0, 2)
    dur = facts.get("duration_s") or words[-1]["end"]
    from core.fsio import write_json_atomic

    suspect = hallucination_signs(words, dur)
    write_json_atomic(a.out, {"schema": "avc.words/1", "language": facts.get("language", a.language), "model": model_label, "route": route, "vad": a.vad, "audio_duration_s": dur, "run": {**facts, "wall_s": secs, "realtime_factor": round(dur / secs, 2) if secs else None}, "suspect": suspect, "words": words})
    if suspect:
        print(f"transcribe: the transcript looks HALLUCINATED ({'; '.join(suspect)}) - written to {a.out} for inspection, NOT accepted. "
              + ("Run again with --vad (voice-activity filter)." if not a.vad else "Check the audio: it may hold no clear speech."), file=sys.stderr)
        return 2
    print(f"transcribe: {len(words)} words, route {route}, {secs}s wall -> {a.out}")
    return 0


def hallucination_signs(words, duration_s) -> list[str]:
    """Pure: reasons to distrust a transcript. Seen on a real 20.8 s Hebrew clip WITHOUT VAD (2026-10-04): two words, "תודה רבה.", the second
    stretched over 16.4 s of real speech; with --vad the same clip gave 23 words. A Hebrew word lasting more than 3 s, or under 0.25 words per
    second over a clip longer than 8 s, does not happen in speech."""
    out = []
    long = [w for w in words if (w["end"] - w["start"]) > 3.0]
    if long:
        w = max(long, key=lambda x: x["end"] - x["start"])
        out.append(f"{len(long)} word(s) last over 3 s (\"{w['w']}\" {w['end'] - w['start']:.1f} s)")
    if duration_s and duration_s > 8 and len(words) / duration_s < 0.25:
        out.append(f"{len(words)} words in {duration_s:.1f} s")
    return out


if __name__ == "__main__":
    sys.exit(main())

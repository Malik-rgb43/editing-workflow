"""analyze - turn a video into what a model can read: per-frame measurements, edit points, contact sheets, a transcript and a sound analysis (contract: video-analysis/references/output-contract.md).

Writes ``analysis/<video>/``: ``measurements.json`` (identity, environment, coverage, edit points, pacing), ``frames.csv`` (every frame), ``sheets/`` (keyframe + overview sheets and audio
images with ``index.json``), ``transcript.json``, ``audio.json`` and a short ``report.md`` that opens with the coverage. The source file is only read (hashed before and after).

Honest limits (they are written into the files too): the cut detector is a port of the original author's rules and has NOT been re-scored on a labelled set - an automatic cut count
must be checked on the sheets before it is quoted, and every `check` edit point decided from frames. The sound analysis is signal-only: loudness, silences, transient hits, a tempo /
beat-grid / key ESTIMATE (half / double time to be audited on the audio image); it does not say what a sound is and does not classify music vs speech. Song ID is never run (no local
service; a remote lookup needs approval and a match would grant no licence). ASR runs through ``tools/transcribe.py`` (the one local route; weights are never downloaded unless you allow it).

Usage:
    python tools/analyze.py <video|folder> --out analysis/<name> [--detail quick|standard|full] [--asr auto|always|never] [--model-dir DIR | --allow-download]
                            [--language he] [--exclude end_card:42.1-45 ...] [--private] [--force] [--timeout 3600]
    python tools/analyze.py --check
    python tools/analyze.py <URL> --download --out analysis      (needs yt-dlp; downloads ONLY that URL; ask the user first)
Folder input: one sub-folder per video under --out. Exit: 0 written, 2 refused / failed, 3 tool error. Heavy: run under ``render_lock run -- ...``.
Cost (one reference machine, 2026-10-03): a 23.5 s 1080x1920 60 fps reel took 7.2 s and 148 MB; memory grows by about 5 KB per frame (a 96-px thumbnail is
kept for every frame), so an hour at 60 fps needs over 1 GB - cut a long recording down to the part you are studying first.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import _common  # noqa: F401

VERSION = "0.1.0"
SCHEMA = "1.0.0"
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".mts", ".mxf"}


def clean(o):
    """JSON-safe copy: finite numbers only."""
    if isinstance(o, float):
        return round(o, 6) if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def parse_excludes(items) -> list[dict]:
    out = []
    for it in items or []:
        m = re.fullmatch(r"(end_card|watermark|intro):([\d.]+)-([\d.]+)(?::(.+))?", it.strip())
        if not m:
            raise ValueError(f"bad --exclude {it!r}: expected kind:start-end[:reason] with kind end_card, watermark or intro (seconds)")
        a, b = float(m.group(2)), float(m.group(3))
        if not 0 <= a < b:
            raise ValueError(f"bad --exclude {it!r}: start must be before end")
        out.append({"kind": m.group(1), "start_s": a, "end_s": b, "reason": m.group(4) or f"{m.group(1)} excluded from the statistics by the user"})
    return out


def in_excluded(t: float, excl) -> bool:
    return any(e["start_s"] <= t < e["end_s"] for e in excl)


def timecode(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m):d}:{s:05.2f}"


def merge_intervals(iv, gap: float):
    out = []
    for a, b in sorted(iv):
        if out and a - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def pacing_block(times: list[float], dur: float) -> dict:
    bounds = [0.0] + times + [dur]
    lens = sorted(b - a for a, b in zip(bounds, bounds[1:]))
    med = (lens[len(lens) // 2] + lens[(len(lens) - 1) // 2]) / 2
    return {"edit_points": len(times), "cuts_per_min": round(len(times) / (dur / 60.0), 3), "median_shot_s": round(med, 3), "mean_shot_s": round(sum(lens) / len(lens), 3),
            "shortest_shot_s": round(lens[0], 3), "longest_shot_s": round(lens[-1], 3), "first_cut_s": round(times[0], 3) if times else None}


# ------------------------------------------------------------------------------------------------ sheets
def build_tiles(reader, wanted: dict, tw: int, th: int, font):
    """wanted: {frame: label}. Returns {frame: PIL image with the label burned in}."""
    from PIL import Image, ImageDraw

    tiles = {}
    for i, fr in enumerate(reader):
        if i in wanted:
            im = Image.fromarray(fr)
            d = ImageDraw.Draw(im)
            label = wanted[i]
            d.rectangle([0, 0, d.textlength(label, font=font) + 8, font.size + 6], fill=(0, 0, 0))
            d.text((4, 2), label, fill=(255, 255, 255), font=font)
            tiles[i] = im
        if len(tiles) == len(wanted):
            break
    return tiles


def write_sheet(path: Path, tiles: list, cols: int, tw: int, th: int) -> None:
    from PIL import Image

    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (20, 20, 20))
    for k, im in enumerate(tiles):
        sheet.paste(im, ((k % cols) * tw, (k // cols) * th))
    sheet.save(str(path), quality=90)


# ------------------------------------------------------------------------------------------------ ASR
def run_asr(video, language, model_dir, allow_download, timeout, tmp):
    """-> ({status, ...transcript fields}, route_label). Never raises for an unavailable route: that is `not_run` with the reason."""
    import transcribe as tr

    routes = tr.available_routes()
    if tr.choose_route(routes) is None:
        return {"status": "not_run", "reason": "no ASR route installed (`uv sync --extra asr-cpu`)"}, "none"
    out = Path(tmp) / "words.json"
    cmd = [sys.executable, "-X", "utf8", str(Path(tr.__file__).resolve()), str(video), "-o", str(out), "--language", language, "--timeout", str(timeout)]
    if model_dir:
        cmd += ["--model-dir", str(model_dir)]
    if allow_download:
        cmd += ["--allow-download"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout + 60)
    if r.returncode != 0 or not out.is_file():
        reason = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or ["transcribe failed"]
        return {"status": "not_run", "reason": f"ASR did not run: {reason[0][:300]}"}, "cpu-ct2"
    data = json.loads(out.read_text(encoding="utf-8"))
    return {"status": "ok", "words_doc": data}, "cpu-ct2"


def segments_from_words(words, max_gap: float = 0.7, max_words: int = 14, max_len: float = 9.0):
    segs, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > max_gap or len(cur) >= max_words or w["end"] - cur[0]["start"] > max_len):
            segs.append(cur)
            cur = []
        cur.append(w)
    if cur:
        segs.append(cur)
    out = []
    for s in segs:
        a, b = s[0]["start"], max(s[-1]["end"], s[0]["start"] + 0.01)
        out.append({"start_s": round(a, 3), "end_s": round(b, 3), "text": " ".join(w["w"] for w in s), "kind": "speech"})
    return out


def transcript_doc(asr: dict, route: str, language: str, dur: float, args) -> dict:
    base = {"schema_version": SCHEMA, "language": language}
    if asr["status"] != "ok":
        return {**base, "status": "not_run", "reason": asr["reason"], "asr": {"route": route, "model": None}}
    d = asr["words_doc"]
    words = [{"text": w["w"], "start_s": w["start"], "end_s": min(w["end"], dur + 0.4)} for w in d["words"]]
    segs = segments_from_words(d["words"])
    for s in segs:
        s["end_s"] = min(s["end_s"], dur + 0.4)
    run = d.get("run") or {}
    return {**base, "status": "ok", "language": d.get("language", language),
            "asr": {"route": "cpu-ct2" if d.get("route") == "faster-whisper" else d.get("route", route), "model": d.get("model"), "model_revision": args.revision or ("unpinned" if "UNPINNED" in str(d.get("model")) else "local"),
                    "vad": bool(d.get("vad")), "device": run.get("device", "cpu"), "language_forced": language},
            "segments": segs, "words": words}


# ------------------------------------------------------------------------------------------------ one video
def analyse(video: Path, out: Path, a) -> int:
    from core import analysis, audio_analysis as aa
    from core.envelope import sha256_file
    from core.errors import ToolkitError
    from core.ffprobe import expected_frames, ffmpeg_version, find_ffmpeg, packet_pts, probe
    from core.media import FrameReader, read_audio_samples
    from core.timebase import FrameClock

    try:
        excl = parse_excludes(a.exclude)
        sha = sha256_file(video)
        marker = out / "measurements.json"
        if marker.is_file() and not a.force:
            try:
                if json.loads(marker.read_text(encoding="utf-8"))["input"]["sha256"] == sha:
                    print(json.dumps({"out": str(out), "reused": True}, ensure_ascii=False))
                    return 0
            except (OSError, ValueError, KeyError):
                pass
        info = probe(video)
        vs = info.first_video
        fps = vs.fps
        if not fps or fps <= 0:
            raise ValueError("the video has no usable frame rate")
        total, _how = expected_frames(video, info)
        if not total:
            raise ValueError("cannot tell how many frames the video has")
        w, h = vs.display_size
        vfr = vs.is_vfr
        if vfr:
            pts, tb = packet_pts(video)
            clock = FrameClock.from_pts(sorted(pts), tb)
            dur = float(info.duration_s or clock.duration() or 0)
        else:
            clock = FrameClock.cfr(fps, total)
            dur = float(total / fps)
        if dur <= 0:
            raise ValueError("zero duration")
        fpsf = float(fps)
        if total > 100_000:
            print(f"analyze: {video.name}: {total} frames - about {total * 5 // 1024} MB of thumbnails will be held in memory; cut the part you need first if that is too much", file=sys.stderr)
    except (ValueError, OSError, ToolkitError) as exc:
        print(f"analyze: {video.name}: {exc}", file=sys.stderr)
        return 2

    out.mkdir(parents=True, exist_ok=True)
    sheets_dir = out / "sheets"
    if sheets_dir.exists():
        shutil.rmtree(sheets_dir)
    sheets_dir.mkdir()
    tmp = Path(tempfile.mkdtemp(prefix="avc-analyze-"))
    try:
        # ---- pass 1: features at 96 px, every frame
        tw0, th0 = analysis.thumb_size(w, h)
        reader = FrameReader(video, pix_fmt="rgb24", scale=(tw0, th0), timeout_s=a.timeout, info=info)
        feats = analysis.extract_features(reader)
        if feats.n == 0:
            print(f"analyze: {video.name}: no frame could be decoded ({' | '.join(reader.stderr_tail[-2:])})", file=sys.stderr)
            return 2
        decoded = feats.n
        mode = "full" if (decoded == total and reader.ok) else "sampled"
        det = analysis.detect_edit_points(feats, fpsf)
        arrs = feats.arrays()
        eps = []
        for p in det["edit_points"]:
            t = float(clock.time_of(p["frame"]))
            if in_excluded(t, excl):
                continue
            eps.append({"id": f"e{len(eps) + 1:03d}", "t_s": round(t, 6), "frame": p["frame"], "kind": p["kind"], "type": p["type"], "confidence": "auto", "note": p["note"]})
        counted = [e["t_s"] for e in eps if e["kind"] in ("cut", "transition")]
        pacing = pacing_block(counted, dur)
        hold_list = [{"start_s": round(float(clock.time_of(s)), 3), "end_s": round(float(clock.time_of(min(e, total - 1))), 3), "start_frame": s, "end_frame": e} for s, e in analysis.holds(arrs, fpsf)]
        stepped = analysis.stepped_cadence(arrs)

        # ---- keyframes + overview sheets (pass 2 at tile size)
        landscape = w >= h
        tile_w, cols, per_sheet = (460, 3, 9) if landscape else (280, 4, 8)
        tile_h = max(2, int(round(h * tile_w / w / 2.0)) * 2)
        shot_starts = [e["frame"] for e in eps if e["kind"] in ("cut", "transition")]
        picks = analysis.pick_keyframes(feats, shot_starts, fpsf, a.detail, dur)
        n_over = min(16, max(4, decoded // max(1, int(fpsf))))
        over = sorted({round(k * (decoded - 1) / max(1, n_over - 1)) for k in range(n_over)})
        wanted = {}
        for i in sorted(set(picks) | set(over)):
            wanted[i] = f"f{i}  {timecode(float(clock.time_of(i)))}"
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import sheet as sheet_tool

        font = sheet_tool._font(max(12, tile_w // 14))
        tiles = build_tiles(FrameReader(video, pix_fmt="rgb24", scale=(tile_w, tile_h), timeout_s=a.timeout, info=info), wanted, tile_w, tile_h, font)
        missing = [i for i in wanted if i not in tiles]
        if missing:
            print(f"analyze: {video.name}: {len(missing)} keyframe(s) could not be decoded", file=sys.stderr)
            return 2
        index = []
        pick_sorted = sorted(picks)
        for n, k in enumerate(range(0, len(pick_sorted), per_sheet), 1):
            chunk = pick_sorted[k:k + per_sheet]
            fname = f"sheets/sheet_{n:03d}.jpg"
            write_sheet(out / fname, [tiles[i] for i in chunk], cols if len(chunk) >= cols else len(chunk), tile_w, tile_h)
            index.append({"file": fname, "kind": "keyframes", "t_start_s": round(float(clock.time_of(chunk[0])), 3), "t_end_s": round(float(clock.time_of(chunk[-1])), 3), "tiles": len(chunk), "tile_px": tile_w,
                          "frames": [{"frame": i, "t_s": round(float(clock.time_of(i)), 3), "label": wanted[i]} for i in chunk]})
        write_sheet(out / "sheets/overview_001.jpg", [tiles[i] for i in over], 4, tile_w, tile_h)
        index.append({"file": "sheets/overview_001.jpg", "kind": "overview", "t_start_s": 0.0, "t_end_s": round(dur, 3), "tiles": len(over), "tile_px": tile_w,
                      "frames": [{"frame": i, "t_s": round(float(clock.time_of(i)), 3), "label": wanted[i]} for i in over]})

        # ---- transcript + audio
        has_audio = bool(info.audio)
        language = a.language
        asr_route = "none"
        try:
            import transcribe as tr

            if tr.choose_route(tr.available_routes()):
                asr_route = "cpu-ct2"
        except Exception:  # noqa: BLE001 - detection only
            pass
        speech_layer = []
        if not has_audio:
            transcript = {"schema_version": SCHEMA, "status": "no_speech", "language": language, "reason": "the file has no audio stream", "asr": {"route": "none", "model": None}}
            audio = {"schema_version": SCHEMA, "status": "n/a", "has_audio": False, "reason": "the file has no audio stream"}
        else:
            if a.asr == "never":
                asr, route = {"status": "not_run", "reason": "ASR switched off (--asr never)"}, asr_route
            else:
                asr, route = run_asr(video, language, a.model_dir, a.allow_download, a.timeout, tmp)
                asr_route = route if route != "none" else asr_route
            transcript = transcript_doc(asr, route, language, dur, a)
            if transcript["status"] == "ok":
                speech_layer = merge_intervals([[s["start_s"], min(s["end_s"], dur)] for s in transcript["segments"]], 0.4)
            audio = {"schema_version": SCHEMA, "status": "not_run", "has_audio": True, "reason": "audio could not be decoded"}
            try:
                ffmpeg = find_ffmpeg()
                pcm = read_audio_samples(video, sample_rate=aa.SR, channels=1, timeout_s=a.timeout)[:, 0].astype("float32") / 32768.0
                audio_notes = []
                if len(pcm) / aa.SR > dur + 0.05:  # the audio track can outlast the picture: analyse the span the viewer sees
                    audio_notes.append(f"the audio runs {len(pcm) / aa.SR - dur:.2f} s past the last video frame; that tail is not analysed (loudness is still the whole file)")
                    pcm = pcm[: int(dur * aa.SR)]
                loud = aa.loudness(ffmpeg, str(video), a.timeout)
                if loud is None:
                    audio["reason"] = "loudness measurement (ebur128) failed"
                else:
                    sig = aa.analyse_signal(pcm, aa.SR, dur, counted, fpsf)
                    chunk = max(60.0, math.ceil(dur / 20.0))
                    images, n = [], 0
                    t0 = 0.0
                    beats = sig["music"].get("beats_s") or []
                    cuts_t = [e["t_s"] for e in eps if e["kind"] != "check"]
                    while t0 < dur:
                        n += 1
                        t1 = min(dur, t0 + chunk)
                        fname = f"sheets/audio_{n:03d}.png"
                        aa.audio_image(out / fname, pcm, aa.SR, t0, t1, cuts_t, beats)
                        index.append({"file": fname, "kind": "audio", "t_start_s": round(t0, 3), "t_end_s": round(t1, 3), "tiles": 1, "tile_px": 1600})
                        images.append(fname)
                        t0 = t1
                    audio = {"schema_version": SCHEMA, "status": "ok", "has_audio": True, "loudness": {**loud, "scope": "whole file" + (" (excluded ranges are NOT removed from the loudness)" if excl else "")},
                             "layers": {"speech": speech_layer, "music": [], "singing": []},
                             "layers_note": "speech = the ASR segments when ASR ran; music / singing are NOT classified (no sound-event model installed)",
                             "sfx_events": sig["sfx_events"], "sound_event_model": "none (labels stay empty: a transient is not a named sound)", "silences": sig["silences"], "music": sig["music"],
                             "song_id": {"status": "opted_out" if a.private else "skipped", "sync_permission": "not_established",
                                         "reason": "private input: nothing leaves the machine" if a.private else "no local fingerprint service; a remote lookup needs the user's approval and a match grants no licence"},
                             "images": images, "notes": audio_notes}
            except (ToolkitError, OSError, ValueError, MemoryError) as exc:
                audio["reason"] = f"audio analysis failed: {exc}"[:300]
            if audio["status"] != "ok":
                audio["status"] = "not_run"
        write_json(out / "transcript.json", transcript)
        write_json(out / "audio.json", audio)
        write_json(sheets_dir / "index.json", {"schema_version": SCHEMA, "sheets": index})

        # ---- frames.csv
        cut_frames = {e["frame"]: (1 if e["kind"] in ("cut", "transition") else 2) for e in eps}
        cols_csv = ["frame", "t_s", "luma", "luma_std", "sat", "content", "hist", "motion", "black", "white", "cut"]
        with open(out / "frames.csv", "w", encoding="utf-8", newline="") as fh:
            wr = csv.writer(fh, lineterminator="\n")
            wr.writerow(cols_csv)
            for i in range(decoded):
                wr.writerow([i, f"{float(clock.time_of(i)):.6f}", f"{feats.luma[i]:.3f}", f"{feats.luma_std[i]:.3f}", f"{feats.sat[i]:.3f}", f"{feats.content[i]:.3f}", f"{feats.hist[i]:.4f}",
                             f"{feats.motion[i]:.3f}", f"{feats.black[i]:.4f}", f"{feats.white[i]:.4f}", cut_frames.get(i, 0)])

        # ---- measurements.json (hash AFTER everything that read the file)
        sha_after = sha256_file(video)
        measurements = {
            "schema_version": SCHEMA, "tool": {"name": "analyze", "version": VERSION, "detail": a.detail},
            "input": {"name": video.name, "sha256": sha, "sha256_after": sha_after, "size_bytes": video.stat().st_size, "duration_s": dur, "fps_num": fps.numerator, "fps_den": fps.denominator,
                      "width": w, "height": h, "rotation": vs.rotation, "vfr": vfr, "frames_expected": total, "has_audio": has_audio, "private": bool(a.private)},
            "environment": {"os": platform.platform(), "ffmpeg": ffmpeg_version(), "asr_route": asr_route, "env": {"python": platform.python_version(), "machine": platform.machine()}},
            "coverage": {"mode": mode, "frames_decoded": decoded, "frames_expected": total, "pts_policy": "decoder_pts", "excluded": excl},
            "edit_points": eps, "pacing": pacing, "holds": hold_list, "stepped_cadence": stepped,
            "per_frame": {"file": "frames.csv", "columns": cols_csv, "rows": decoded},
            "detector": {"rejected_candidates": det["rejected"][:200], "scored_on_labelled_set": False,
                         "note": "port of the original author's rules; not re-scored. Check every `check` point and the count on the sheets before quoting numbers."},
        }
        write_json(out / "measurements.json", measurements)
        write_report(out, measurements, transcript, audio)
    except (ToolkitError, OSError, ValueError, MemoryError, subprocess.TimeoutExpired) as exc:
        print(f"analyze: {video.name}: {exc}", file=sys.stderr)
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"out": str(out), "mode": mode, "frames": decoded, "edit_points": pacing["edit_points"], "check_points": sum(1 for e in eps if e["kind"] == "check"),
                      "transcript": transcript["status"], "audio": audio["status"]}, ensure_ascii=False))
    return 0


def write_report(out: Path, m: dict, transcript: dict, audio: dict) -> None:
    inp, cov, pc = m["input"], m["coverage"], m["pacing"]
    checks = sum(1 for e in m["edit_points"] if e["kind"] == "check")
    lines = [f"# Analysis of {inp['name']}", "", "## Coverage (read this first)",
             f"- mode: **{cov['mode']}** - {cov['frames_decoded']} of {cov['frames_expected']} frames decoded; excluded: {', '.join(e['kind'] for e in cov['excluded']) or 'nothing'}",
             f"- transcript: **{transcript['status']}**" + (f" ({transcript.get('reason')})" if transcript.get("reason") else ""),
             f"- audio: **{audio['status']}**" + (f" ({audio.get('reason')})" if audio.get("reason") else ""),
             "- NOT run: song ID; sound-event labels; music/speech classification. The cut count is an automatic estimate that has not been verified on frames.", "",
             "## Pacing (automatic, unverified)",
             f"- {pc['edit_points']} edit points, {pc['cuts_per_min']} per minute, median shot {pc['median_shot_s']} s; {checks} `check` point(s) still to decide from the frames", "",
             "## Next", "- view every sheet in `sheets/` and every audio image, decide the `check` points, then `python agent-content/skills/video-analysis/scripts/validate_analysis.py <this folder> --video <source>`", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def check_environment() -> dict:
    from core.ffprobe import ffmpeg_version

    env = {"python": platform.python_version(), "os": platform.platform()}
    try:
        env["ffmpeg"] = ffmpeg_version()
    except Exception as exc:  # noqa: BLE001
        env["ffmpeg"] = f"missing: {exc}"
    for mod in ("numpy", "PIL", "faster_whisper"):
        try:
            __import__(mod)
            env[mod] = "ok"
        except ImportError:
            env[mod] = "missing"
    return env


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="analyze", description=__doc__.split("\n\n")[0])
    ap.add_argument("source", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--detail", choices=("quick", "standard", "full"), default="standard")
    ap.add_argument("--asr", choices=("auto", "always", "never"), default="auto")
    ap.add_argument("--language", default="he")
    ap.add_argument("--model-dir")
    ap.add_argument("--revision")
    ap.add_argument("--allow-download", action="store_true", help="let the ASR route fetch its model (large; shown by transcribe first)")
    ap.add_argument("--exclude", action="append", help="end_card|watermark|intro:start-end[:reason] (seconds)")
    ap.add_argument("--private", action="store_true", help="confidential material: no remote song ID, nothing leaves the machine")
    ap.add_argument("--no-song-id", action="store_true", help="accepted for compatibility: song ID is never run by this tool")
    ap.add_argument("--no-audio-ai", action="store_true", help="accepted for compatibility: no sound-event model is used by this tool")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--download", action="store_true", help="allow downloading a URL source with yt-dlp (only that URL)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--timeout", type=float, default=3600.0)
    a = ap.parse_args(argv)
    if a.check:
        env = check_environment()
        print(json.dumps(env, indent=2, ensure_ascii=False))
        return 0 if env.get("ffmpeg", "").startswith("missing") is False and env.get("numpy") == "ok" and env.get("PIL") == "ok" else 2
    if not a.source or not a.out:
        ap.error("need <source> and --out")
    src = a.source
    if re.match(r"^https?://", src):
        if not a.download:
            print("analyze: this is a URL. Say which source it is and pass --download to fetch ONLY that URL with yt-dlp (a reference copy for analysis, never redistributed); or give me the file.", file=sys.stderr)
            return 2
        exe = shutil.which("yt-dlp")
        if not exe:
            print("analyze: yt-dlp is not installed; download the file yourself and pass it in.", file=sys.stderr)
            return 2
        dl = Path(a.out) / "_downloads"
        dl.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([exe, "--no-playlist", "-o", str(dl / "%(id)s.%(ext)s"), "--print", "after_move:filepath", src], capture_output=True, text=True, encoding="utf-8")
        files = [ln for ln in r.stdout.splitlines() if ln.strip()]
        if r.returncode != 0 or not files:
            print(f"analyze: download failed: {(r.stderr or '').strip()[-300:]}", file=sys.stderr)
            return 2
        src = files[-1]
    p = Path(src)
    if p.is_dir():
        vids = sorted(f for f in p.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXT)
        if not vids:
            print(f"analyze: no video files in {p}", file=sys.stderr)
            return 2
        from core.envelope import sha256_file
        from core.paths import slugify

        rc = 0
        for v in vids:
            sub = Path(a.out) / f"{slugify(v.stem)}-{sha256_file(v)[:6]}"
            rc = max(rc, analyse(v, sub, a))
        return rc
    if not p.is_file():
        print(f"analyze: not found: {p}", file=sys.stderr)
        return 2
    return analyse(p, Path(a.out), a)


if __name__ == "__main__":
    sys.exit(main())

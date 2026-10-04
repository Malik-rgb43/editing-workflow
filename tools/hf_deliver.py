"""hf_deliver - preflight -> render under the lock -> stale-file guard -> mux the mix / two-pass loudnorm -> verify the FINAL file.

Two commands:

  verify <file>   Delivery gate on the file you will actually ship (QA envelope, fail-closed): audio present, duration (vs
                  --expected-duration), integrated loudness and true peak (house preset v1: -14 LUFS +-1.0, TP <= -1.0 dBTP; override
                  with --lufs/--tp/--lufs-tol; numeric 0.0 is a value, a missing measurement is INSUFFICIENT_EVIDENCE - E04-B04/B05),
                  black segments, and dead edge columns (the encoder can blacken the last 8 columns of a 1080-wide canvas; the author's
                  rule is a 1088 canvas with data-deliver-width=1080 - re-verify per HyperFrames version). Measured on THE FILE, never
                  on the mix (the renderer attenuated audio ~11.5 dB once; not reproduced since).
  render <hf-dir> Strip Studio's data-hf-id (backup kept) -> hf_preflight (abort on errors unless --force) -> `npx hyperframes render`
                  under the heavy-job lock (timeout = 3x --eta) -> stale-file guard (the raw file must be newer than the run start) ->
                  mux assets/mix.wav (AAC 320k 48 kHz) or two-pass loudnorm of the raw audio -> verify -> final/<name>_<platform>_<hook>_<aspect>.mp4
                  + final/manifest.json (sha256 of the file and of the hf sources it was rendered from). `--skip-render` re-muxes an
                  existing raw file (an audio-only note needs no render).

The HyperFrames CLI flags below are the ones recorded for HyperFrames 0.8.x (distilled 03 tools-inventory, 2026-10-02): re-check
`npx hyperframes render --help` on your version; override the whole command with --render-cmd. Credits/cost: none (local render).

Usage:
    python tools/hf_deliver.py verify <video> [--expected-duration S] [--lufs -14] [--lufs-tol 1.0] [--tp -1.0] [--edge-samples 12] [--json-out r.json]
    python tools/hf_deliver.py render <hf-dir> --name NAME [--platform ig] [--hook A] [--aspect 9x16] [--mix assets/mix.wav]
                              [--draft] [--skip-render] [--force] [--eta 600] [--render-cmd "npx hyperframes render . ..."] [--lock-wait 0]
Exit: verify 0 PASS / 1 FAIL / 2 INSUFFICIENT_EVIDENCE; render: 0 delivered and verified, 1 verify FAIL, 2 refused or not verified, 75 lock busy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import sys
import time
from pathlib import Path

import _common  # noqa: F401

TOOL = "hf_deliver"


# ------------------------------------------------------------------------------------------------ measurement

TP_MARGIN_DB = 0.5  # loudnorm target sits this far under the verify limit

def loudness(path, *, i=-14.0, tp=-1.0, lra=11.0):
    """Measure integrated loudness / true peak with FFmpeg loudnorm (first pass, JSON). Returns dict or raises DecodeError."""
    from core.errors import DecodeError
    from core.ffprobe import find_ffmpeg
    from core.procs import run

    r = run([find_ffmpeg(), "-hide_banner", "-nostdin", "-i", os.fspath(path), "-map", "0:a:0", "-af", f"loudnorm=I={i}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"], timeout=600)
    if r.timed_out or r.returncode != 0:
        raise DecodeError(f"loudness measurement failed (exit {r.returncode}): {(r.stderr or '').strip().splitlines()[-1:] }")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr or "", re.S)
    if not m:
        raise DecodeError("loudnorm printed no JSON block")
    d = json.loads(m.group(0))
    out = {}
    for k_src, k in (("input_i", "lufs"), ("input_tp", "true_peak_dbtp"), ("input_lra", "lra"), ("input_thresh", "thresh"), ("target_offset", "offset")):
        try:
            out[k] = float(d[k_src])
        except (KeyError, ValueError):
            out[k] = None
    return out


def black_segments(path):
    from core.errors import DecodeError
    from core.ffprobe import find_ffmpeg
    from core.procs import run

    r = run([find_ffmpeg(), "-hide_banner", "-nostdin", "-i", os.fspath(path), "-an", "-vf", "blackdetect=d=0.08:pix_th=0.04", "-f", "null", "-"], timeout=900)
    if r.timed_out or r.returncode != 0:
        raise DecodeError(f"blackdetect failed (exit {r.returncode})")
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+)\s+black_end:([\d.]+)", r.stderr or "")]


def edge_band(path, info, samples=12, band=8):
    """Mean luma of the outer ``band`` columns vs the next 24 columns on both sides, on ``samples`` evenly spread frames. One decode pass."""
    from core.media import FrameReader

    vs = info.first_video
    total = vs.declared_frames or 0
    if total <= 0:
        return None
    idx = sorted({int(round(k * (total - 1) / max(1, samples - 1))) for k in range(samples)})
    sel = "+".join(f"eq(n\\,{i})" for i in idx)
    rd = FrameReader(path, pix_fmt="gray", vf=f"select='{sel}'", info=info, timeout_s=300)
    worst = {"right": 1.0, "left": 1.0}
    n = 0
    for fr in rd:
        n += 1
        w = fr.shape[1]
        if w < band + 32:
            continue
        for side, outer, inner in (("right", fr[:, w - band :], fr[:, w - band - 24 : w - band]), ("left", fr[:, :band], fr[:, band : band + 24])):
            mi, mo = float(inner.mean()), float(outer.mean())
            if mi > 20:
                worst[side] = min(worst[side], mo / mi)
    return {"frames": n, "ratio_right": worst["right"], "ratio_left": worst["left"], "band": band} if n else None


def verify_file(path, *, expected_duration=None, lufs=-14.0, lufs_tol=1.0, tp=-1.0, edge_samples=12, duration_tol=0.25):
    """Delivery gate for one file. Returns an Envelope (never raises)."""
    from core.envelope import Finding, Severity, check_range, guarded
    from core.ffprobe import expected_frames, probe

    def body(b):
        info = probe(path)
        vs = info.first_video
        exp, how = expected_frames(path, info)
        b.set_frames(decoded=exp, expected=exp, fps=vs.fps)  # container-level facts; per-frame decode belongs to frame_qa (a separate required gate)
        b.extra["note"] = "this gate measures the shipped FILE (audio, duration, black, edges); per-frame defects are frame_qa/caption_qa gates"
        if not info.audio:
            b.add(Finding("no_audio", "the file has no audio stream", Severity.ERROR))
        dur = float(info.duration_s) if info.duration_s is not None else None
        b.extra["duration_s"] = dur
        if expected_duration is not None:
            if dur is None:
                b.gap("duration_unknown", "duration could not be read")
            elif abs(dur - expected_duration) > duration_tol:
                b.add(Finding("duration_mismatch", f"duration {dur:.3f}s != expected {expected_duration:.3f}s (+-{duration_tol}s)", Severity.ERROR, data={"duration": dur, "expected": expected_duration}))
        if info.audio:
            m = loudness(path, i=lufs, tp=tp)
            b.extra["loudness"] = m
            if m["lufs"] is None or m["true_peak_dbtp"] is None:
                b.gap("loudness_unmeasured", "loudness/true peak could not be measured (a missing value never passes)")
            else:
                for f in (check_range("loudness_lufs", m["lufs"], lo=lufs - lufs_tol, hi=lufs + lufs_tol, unit="LUFS"), check_range("true_peak_dbtp", m["true_peak_dbtp"], hi=tp, unit="dBTP")):
                    if f is not None:
                        b.add(f)
        for s, e in black_segments(path):
            b.add(Finding("black_segment", f"black from {s:.2f}s to {e:.2f}s", Severity.ERROR, data={"start": s, "end": e}))
        eb = edge_band(path, info, samples=edge_samples) if edge_samples else None
        if edge_samples and eb is None:
            b.gap("edge_band_unmeasured", "could not sample frames for the edge-column check")
        elif eb:
            b.extra["edge_band"] = eb
            for side in ("right", "left"):
                if eb[f"ratio_{side}"] < 0.25:
                    b.add(Finding("dead_edge", f"the {side} {eb['band']} columns are much darker than their neighbours (ratio {eb[f'ratio_{side}']:.2f}): encoder edge artefact", Severity.ERROR, data=eb))

    return guarded(TOOL + ".verify", _common.TOOLS_VERSION, body, path)


# ------------------------------------------------------------------------------------------------ mux
def deliver_width(index_html: str) -> int | None:
    """The house rule for 1080-wide masters: render a 1088 canvas (data-width) and declare data-deliver-width="1080" on the root;
    the encoder's dark right-edge columns then fall in the 8 px that are cropped away at mux. Returns the width to crop to, or None.
    (Before 2026-10-04 the rule was documented here but not implemented: a real render shipped with 8 black columns and verify caught it.)"""
    m = re.search(r"<[^>]*\bdata-composition-id\s*=[^>]*>", index_html)
    if not m:
        return None
    tag = m.group(0)
    dw = re.search(r"""data-deliver-width\s*=\s*["']?(\d+)""", tag)
    cw = re.search(r"""data-width\s*=\s*["']?(\d+)""", tag)
    if not dw:
        return None
    d, c = int(dw.group(1)), int(cw.group(1)) if cw else None
    return d if (c is None or d < c) and d % 2 == 0 and d > 0 else None


def mux(raw, out, *, mix=None, lufs=-14.0, tp=-1.0, crop_width=None):
    """AAC 320k / 48 kHz. With a mix file: video from raw, audio from the mix. Without: two-pass loudnorm of the raw audio.
    ``crop_width``: keep the left N columns (re-encodes the video with libx264 CRF 12, yuv420p); otherwise the video is copied."""
    from core.errors import ToolkitError
    from core.ffprobe import find_ffmpeg
    from core.procs import run

    ff = find_ffmpeg()
    base = [ff, "-hide_banner", "-nostdin", "-v", "error", "-y"]
    vcodec = (["-vf", f"crop={int(crop_width)}:ih:0:0", "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-pix_fmt", "yuv420p"]
              if crop_width else ["-c:v", "copy"])
    if mix:
        cmd = base + ["-i", os.fspath(raw), "-i", os.fspath(mix), "-map", "0:v:0", "-map", "1:a:0", *vcodec, "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-shortest", "-movflags", "+faststart", os.fspath(out)]
    else:
        m = loudness(raw, i=lufs, tp=tp)
        if any(m.get(k) is None for k in ("lufs", "true_peak_dbtp", "lra", "thresh", "offset")):
            raise ToolkitError("cannot normalise: first-pass loudness measurement incomplete")
        # aim 0.5 dB under the gate: the AAC encode overshoots the true peak a little (measured -0.99 vs a -1.0 limit, 2026-10-04)
        af = f"loudnorm=I={lufs}:TP={tp - TP_MARGIN_DB}:LRA=11:measured_I={m['lufs']}:measured_TP={m['true_peak_dbtp']}:measured_LRA={m['lra']}:measured_thresh={m['thresh']}:offset={m['offset']}:linear=true"
        cmd = base + ["-i", os.fspath(raw), "-map", "0:v:0", "-map", "0:a:0", *vcodec, "-af", af, "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", os.fspath(out)]
    r = run(cmd, timeout=1800)
    if r.timed_out or r.returncode != 0 or not Path(out).is_file():
        raise ToolkitError(f"mux failed (exit {r.returncode}): {(r.stderr or '').strip()[-300:]}")


# ------------------------------------------------------------------------------------------------ render
def strip_studio_ids(hf: Path, backup_dir: Path) -> int:
    """Remove data-hf-id attributes from index.html and compositions/*.html (backup first). Returns the number of files changed."""
    changed = 0
    files = [hf / "index.html", *sorted((hf / "compositions").glob("*.html"))] if (hf / "compositions").is_dir() else [hf / "index.html"]
    for f in files:
        if not f.is_file():
            continue
        t = f.read_text(encoding="utf-8")
        n = re.sub(r"""\s+data-hf-id\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", "", t)
        if n != t:
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, backup_dir / f"{f.name}.{int(time.time())}.bak")
            f.write_text(n, encoding="utf-8")
            changed += 1
    return changed


def sources_hash(hf: Path) -> str:
    h = hashlib.sha256()
    for f in sorted([hf / "index.html", *((hf / "compositions").glob("*.html") if (hf / "compositions").is_dir() else []), hf / "cues.js", hf / "cues.json"]):
        if f.is_file():
            h.update(f.name.encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def cmd_render(a) -> int:
    from core.config import load_config
    from core.errors import LockBusy, ToolkitError
    from core.envelope import sha256_file
    from core.fsio import read_json, write_json_atomic
    from core.lock import acquire
    from core.procs import run

    hf = Path(a.hf).resolve()
    if not (hf / "index.html").is_file():
        print(f"hf_deliver: {hf / 'index.html'} not found", file=sys.stderr)
        return 2
    proj = hf.parent
    work, final = proj / "_work", proj / "final"
    work.mkdir(exist_ok=True)
    final.mkdir(exist_ok=True)
    tag = re.sub(r"[^A-Za-z0-9_-]+", "-", a.name).strip("-") or "video"
    raw = work / f"{tag}_raw{'_draft' if a.draft else ''}.mp4"
    out_name = f"{tag}_{a.platform}_{a.hook}_{a.aspect}.mp4"
    out = (work / "drafts" if a.draft else final) / out_name
    out.parent.mkdir(parents=True, exist_ok=True)

    n = strip_studio_ids(hf, work / "backup")
    if n:
        print(f"hf_deliver: stripped data-hf-id from {n} file(s) (backup in _work/backup)")
    import subprocess

    pre = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).with_name("hf_preflight.py")), str(hf)], capture_output=True, text=True, encoding="utf-8")
    if pre.returncode != 0 and not a.force:
        print("hf_deliver: preflight failed (use --force only knowingly); aborting before any render.\n" + pre.stdout[-1500:], file=sys.stderr)
        return 2
    t_start = time.time()
    if not a.skip_render:
        cfg = load_config()
        if a.render_cmd:
            cmd = shlex.split(a.render_cmd, posix=os.name != "nt")
        else:
            from core import hf_engine

            # No GPU flags by default: the same command must work on every machine (ADR 0002). Add `--browser-gpu`/`--gpu` via --render-cmd
            # only after `doctor recommend` showed a working GPU route on this machine. The engine is the PINNED one (never an npx download).
            try:
                cmd = hf_engine.command(["render", ".", "--quality", "draft" if a.draft else "delivery", "--sdr", "-o", str(raw)])
            except hf_engine.EngineMissing as exc:
                print(f"hf_deliver: {exc}", file=sys.stderr)
                return 2
        from core import hf_engine as _hf

        env = _hf.run_env({"FFMPEG_ENCODE_TIMEOUT_MS": "3600000"})
        try:
            with acquire(cfg.lock_path, job=f"render {tag}", timeout=a.lock_wait):
                r = run(cmd, cwd=hf, env=env, timeout=a.eta * 3, log_path=work / f"{tag}_render.log")
        except LockBusy as exc:
            print(f"hf_deliver: {exc}", file=sys.stderr)
            return 75
        if r.timed_out or r.returncode != 0:
            print(f"hf_deliver: render failed (exit {r.returncode}, timed_out={r.timed_out}); see {work / (tag + '_render.log')}", file=sys.stderr)
            return 2
    if not raw.is_file():
        print(f"hf_deliver: raw file {raw} not found", file=sys.stderr)
        return 2
    if not a.skip_render and raw.stat().st_mtime < t_start - 1:
        print("hf_deliver: stale-file guard: the raw file is older than this run (the render did not write it); refusing to ship an old render", file=sys.stderr)
        return 2
    mix = (hf / a.mix) if a.mix else None
    if mix is not None and not mix.is_file():
        print(f"hf_deliver: --mix {mix} not found", file=sys.stderr)
        return 2
    crop = deliver_width((hf / "index.html").read_text(encoding="utf-8"))
    if crop:
        print(f"hf_deliver: cropping the render to the delivery width {crop} px (data-deliver-width)")
    try:
        mux(raw, out, mix=mix, lufs=a.lufs, tp=a.tp, crop_width=crop)
    except ToolkitError as exc:
        print(f"hf_deliver: {exc}", file=sys.stderr)
        return 2
    env_v = verify_file(out, expected_duration=a.expected_duration, lufs=a.lufs, tp=a.tp)
    rep = env_v.to_dict()
    write_json_atomic(work / f"{tag}_verify.json", rep)
    if not a.draft:
        mf = final / "manifest.json"
        data = read_json(mf) if mf.is_file() else {"schema": "avc.delivery-manifest/1", "files": []}
        data["files"] = [x for x in data["files"] if x.get("file") != out_name] + [
            {"file": out_name, "sha256": sha256_file(out), "source_sha256": sources_hash(hf), "verify_status": rep["status"], "rendered_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        ]
        write_json_atomic(mf, data)
    print(json.dumps({"out": str(out), "verify": rep["status"], "findings": [f["code"] for f in rep["findings"]]}, ensure_ascii=False))
    return {"PASS": 0, "FAIL": 1}.get(rep["status"], 2)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hf_deliver", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("video")
    v.add_argument("--expected-duration", type=float)
    v.add_argument("--lufs", type=float, default=-14.0)
    v.add_argument("--lufs-tol", type=float, default=1.0)
    v.add_argument("--tp", type=float, default=-1.0)
    v.add_argument("--edge-samples", type=int, default=12)
    v.add_argument("--json-out")
    r = sub.add_parser("render")
    r.add_argument("hf")
    r.add_argument("--name", required=True)
    r.add_argument("--platform", default="social")
    r.add_argument("--hook", default="main")
    r.add_argument("--aspect", default="9x16")
    r.add_argument("--mix")
    r.add_argument("--draft", action="store_true")
    r.add_argument("--skip-render", action="store_true")
    r.add_argument("--force", action="store_true")
    r.add_argument("--eta", type=float, default=600.0)
    r.add_argument("--render-cmd")
    r.add_argument("--lock-wait", type=float, default=0.0)
    r.add_argument("--expected-duration", type=float)
    r.add_argument("--lufs", type=float, default=-14.0)
    r.add_argument("--tp", type=float, default=-1.0)
    a = ap.parse_args(argv)
    if a.cmd == "verify":
        from core.envelope import emit

        env = verify_file(a.video, expected_duration=a.expected_duration, lufs=a.lufs, lufs_tol=a.lufs_tol, tp=a.tp, edge_samples=a.edge_samples)
        if a.json_out:
            from core.fsio import write_json_atomic

            write_json_atomic(a.json_out, env.to_dict())
        return emit(env)
    return cmd_render(a)


if __name__ == "__main__":
    sys.exit(main())

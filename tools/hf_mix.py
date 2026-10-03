"""hf_mix - premix voice-over + music bed + SFX from ONE cue file into a master WAV (two-pass loudnorm), and report what it measured.

The cue file (JSON, UTF-8) is the single source of truth for the mix; relative paths are resolved against the cue file's folder:

    {"duration": 30.0,
     "master": {"lufs": -14, "tp": -1.0},                         # house preset v1 (override per project)
     "vo":    [{"file": "assets/vo1.wav", "start": 0.5, "gain_db": 0}],
     "music": {"file": "assets/bed.wav", "start": 0, "gain_db": -18, "duck_db": -10, "loop": true, "fade_out": 1.5},
     "sfx":   [{"file": "assets/hit.wav", "at": 3.2, "gain_db": -22, "lead_frames": 2, "fps": 30}]}

* VO lines are placed at ``start``; the music bed is ducked under the VO bus with a sidechain compressor (``duck_db`` is a TARGET: the
  compressor settings are approximate - read the measured numbers in the report, do not trust the setting);
* each SFX is placed ``lead_frames`` BEFORE the picture event at ``at`` (sound 1-3 frames early reads as in sync);
* the premix is trimmed/padded to ``duration`` and normalised in two passes (linear) to ``master.lufs`` / ``master.tp``.
  The author's reference numbers (VO -14.5 LUFS per line, duck -10 dB, SFX -18..-26 dB under VO, master -14 LUFS / TP <= -1) are a house
  preset, not law; measured on the reference machine only. Numeric 0.0 is a value, a missing measurement is an error.

Missing files, a zero-length input, an unmeasurable result or a master outside the target tolerance exits non-zero; nothing is written
as "ok" when it could not be verified.

Usage:
    python tools/hf_mix.py <cues.json> -o <mix.wav> [--report] [--lufs-tol 1.0] [--no-duck]
Exit: 0 mix written and verified, 2 refused / failed / out of tolerance, 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import _common  # noqa: F401


def _f(v, name, default=None):
    if v is None:
        if default is None:
            raise ValueError(f"missing {name}")
        return float(default)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{name} must be a number")
    return float(v)


def load_cues(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        raise ValueError("cue file must be a JSON object")
    dur = _f(d.get("duration"), "duration")
    if dur <= 0:
        raise ValueError("duration must be > 0")
    base = path.parent
    def res(f):
        p = Path(f)
        return p if p.is_absolute() else (base / p)
    vo = [{"file": res(x["file"]), "start": _f(x.get("start"), "vo.start", 0.0), "gain_db": _f(x.get("gain_db"), "vo.gain_db", 0.0)} for x in d.get("vo", [])]
    m = d.get("music")
    music = None
    if m:
        music = {"file": res(m["file"]), "start": _f(m.get("start"), "music.start", 0.0), "gain_db": _f(m.get("gain_db"), "music.gain_db", -18.0), "duck_db": _f(m.get("duck_db"), "music.duck_db", -10.0), "loop": bool(m.get("loop", True)), "fade_out": _f(m.get("fade_out"), "music.fade_out", 0.0)}
    sfx = []
    for x in d.get("sfx", []):
        fps = _f(x.get("fps"), "sfx.fps", 30.0)
        lead = _f(x.get("lead_frames"), "sfx.lead_frames", 2.0)
        at = _f(x.get("at"), "sfx.at")
        sfx.append({"file": res(x["file"]), "start": max(0.0, at - lead / fps), "gain_db": _f(x.get("gain_db"), "sfx.gain_db", -22.0)})
    if not vo and not music and not sfx:
        raise ValueError("the cue file has no vo, music or sfx: nothing to mix")
    mm = d.get("master", {}) or {}
    return {"duration": dur, "lufs": _f(mm.get("lufs"), "master.lufs", -14.0), "tp": _f(mm.get("tp"), "master.tp", -1.0), "vo": vo, "music": music, "sfx": sfx}


def build_graph(c: dict, *, duck: bool = True):
    """-> (input args list, filter_complex string, output label). Pure; unit-tested."""
    inputs, chains, vo_labels, other = [], [], [], []
    n = 0

    def add_input(path, loop=False):
        nonlocal n
        inputs.extend((["-stream_loop", "-1"] if loop else []) + ["-i", os.fspath(path)])
        n += 1
        return n - 1

    dur = c["duration"]
    for i, v in enumerate(c["vo"]):
        k = add_input(v["file"])
        ms = int(round(v["start"] * 1000))
        chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms},volume={v['gain_db']}dB[vo{i}]")
        vo_labels.append(f"[vo{i}]")
    vo_bus = None
    if vo_labels:
        if len(vo_labels) == 1:
            chains.append(f"{vo_labels[0]}anull[vobus]")
        else:
            chains.append("".join(vo_labels) + f"amix=inputs={len(vo_labels)}:normalize=0:duration=longest[vobus]")
        vo_bus = "[vobus]"
    if c["music"]:
        m = c["music"]
        k = add_input(m["file"], loop=m["loop"])
        ms = int(round(m["start"] * 1000))
        fade = f",afade=t=out:st={max(0.0, dur - m['fade_out']):.3f}:d={m['fade_out']:.3f}" if m["fade_out"] > 0 else ""
        chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{dur:.3f},adelay={ms}|{ms},volume={m['gain_db']}dB{fade}[mus]")
        if duck and vo_bus:
            chains.append(f"{vo_bus}asplit=2[vomix][vosc]")
            # threshold/ratio chosen so a VO at normal level pulls the bed down by roughly |duck_db|; verify with the measured report
            ratio = max(2.0, min(20.0, abs(m["duck_db"]) / 1.5))
            chains.append(f"[mus][vosc]sidechaincompress=threshold=0.02:ratio={ratio:.1f}:attack=20:release=350:makeup=1[musd]")
            other.append("[musd]")
            vo_bus = "[vomix]"
        else:
            other.append("[mus]")
    for i, s in enumerate(c["sfx"]):
        k = add_input(s["file"])
        ms = int(round(s["start"] * 1000))
        chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms},volume={s['gain_db']}dB[sfx{i}]")
        other.append(f"[sfx{i}]")
    mix_in = ([vo_bus] if vo_bus else []) + other
    chains.append("".join(mix_in) + f"amix=inputs={len(mix_in)}:normalize=0:duration=longest,atrim=0:{dur:.3f},apad=whole_dur={dur:.3f}[out]")
    return inputs, ";".join(chains), "[out]"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hf_mix", description=__doc__.split("\n\n")[0])
    ap.add_argument("cues")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--lufs-tol", type=float, default=1.0)
    ap.add_argument("--no-duck", action="store_true")
    a = ap.parse_args(argv)

    from core.errors import ToolkitError
    from core.ffprobe import find_ffmpeg, probe
    from core.fsio import write_json_atomic
    from core.procs import run
    import hf_deliver
    import tempfile

    try:
        c = load_cues(Path(a.cues))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"hf_mix: bad cue file: {exc}", file=sys.stderr)
        return 2
    missing = [str(p) for p in [v["file"] for v in c["vo"]] + ([c["music"]["file"]] if c["music"] else []) + [s["file"] for s in c["sfx"]] if not Path(p).is_file()]
    if missing:
        print("hf_mix: input file(s) not found: " + ", ".join(missing), file=sys.stderr)
        return 2
    for p in [v["file"] for v in c["vo"]] + ([c["music"]["file"]] if c["music"] else []) + [s["file"] for s in c["sfx"]]:
        try:
            if not probe(p).audio:
                print(f"hf_mix: {p} has no audio stream", file=sys.stderr)
                return 2
        except ToolkitError as exc:
            print(f"hf_mix: cannot read {p}: {exc}", file=sys.stderr)
            return 2
    inputs, graph, label = build_graph(c, duck=not a.no_duck)
    tmp = Path(tempfile.mkdtemp(prefix="avc-mix-"))
    pre = tmp / "premix.wav"
    ff = find_ffmpeg()
    r = run([ff, "-hide_banner", "-nostdin", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", label, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(pre)], timeout=1800)
    if r.returncode != 0 or not pre.is_file():
        print(f"hf_mix: premix failed: {(r.stderr or '').strip()[-300:]}", file=sys.stderr)
        return 2
    try:
        m1 = hf_deliver.loudness(pre, i=c["lufs"], tp=c["tp"])
        if any(m1.get(k) is None for k in ("lufs", "true_peak_dbtp", "lra", "thresh", "offset")):
            print("hf_mix: premix loudness could not be measured (a missing value never passes)", file=sys.stderr)
            return 2
        af = f"loudnorm=I={c['lufs']}:TP={c['tp']}:LRA=11:measured_I={m1['lufs']}:measured_TP={m1['true_peak_dbtp']}:measured_LRA={m1['lra']}:measured_thresh={m1['thresh']}:offset={m1['offset']}:linear=true"
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        r2 = run([ff, "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", str(pre), "-af", af, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(out)], timeout=1800)
        if r2.returncode != 0 or not out.is_file():
            print(f"hf_mix: normalisation failed: {(r2.stderr or '').strip()[-300:]}", file=sys.stderr)
            return 2
        m2 = hf_deliver.loudness(out, i=c["lufs"], tp=c["tp"])
    except ToolkitError as exc:
        print(f"hf_mix: {exc}", file=sys.stderr)
        return 2
    dur = float(probe(out).duration_s or 0)
    problems = []
    if m2["lufs"] is None or m2["true_peak_dbtp"] is None:
        problems.append("final loudness unmeasured")
    else:
        if abs(m2["lufs"] - c["lufs"]) > a.lufs_tol:
            problems.append(f"master {m2['lufs']:.2f} LUFS is outside {c['lufs']} +- {a.lufs_tol}")
        if m2["true_peak_dbtp"] > c["tp"] + 0.05:
            problems.append(f"true peak {m2['true_peak_dbtp']:.2f} dBTP is above {c['tp']}")
    if abs(dur - c["duration"]) > 0.1:
        problems.append(f"duration {dur:.2f}s != {c['duration']}s")
    rep = {"out": str(out), "premix": {"lufs": m1["lufs"], "true_peak_dbtp": m1["true_peak_dbtp"]}, "master": {"lufs": m2["lufs"], "true_peak_dbtp": m2["true_peak_dbtp"], "lra": m2["lra"]}, "duration_s": round(dur, 3),
           "target": {"lufs": c["lufs"], "tp": c["tp"]}, "ducking": "sidechain compressor; target %.1f dB (approximate - not measured here)" % (c["music"]["duck_db"] if c["music"] else 0), "problems": problems}
    if a.report:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(f"hf_mix: {out} master {m2['lufs']:.2f} LUFS / {m2['true_peak_dbtp']:.2f} dBTP, {dur:.2f}s" + (f" - PROBLEMS: {'; '.join(problems)}" if problems else ""))
    write_json_atomic(str(out) + ".mix-report.json", rep)
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

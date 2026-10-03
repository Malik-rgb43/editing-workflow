#!/usr/bin/env python3
"""validate_analysis.py - check an analysis folder against the video-analysis output contract (fail closed).

Contract (schema_version 1.0.0), see references/output-contract.md:
  analysis/<video>/
    measurements.json   input identity, environment, coverage, edit points, pacing, review
    frames.csv          per-frame data (required when coverage.mode == "full")
    sheets/index.json   + sheet_*.jpg / overview_*.jpg / audio_*.png / zoom images
    transcript.json     status ok | no_speech | not_run, segments, words
    audio.json          loudness, layers, SFX, music (tempo/key/beats), song id, images

Usage:
  python validate_analysis.py <analysis_dir> [--video <source file>] [--stage produced|reviewed]
                              [--allow-not-run transcript,audio] [--json]
  python validate_analysis.py --self-check

  --stage produced   the tool just ran; the model has not read the sheets yet (review block not required)
  --stage reviewed   (default) the model viewed every sheet and resolved every "check" edit point
  --video            re-hash the source file and compare with input.sha256 (inputs stay read-only)
  --allow-not-run    components deliberately skipped (e.g. --no-asr); the report then lists
                     `claims_not_allowed` so the breakdown cannot talk about them

Exit codes: 0 PASS | 1 FAIL | 2 INSUFFICIENT_EVIDENCE (a component was not run, a file is missing, a sample is empty).
A timeout, an empty sample, a missing file or `null` where a number is required never passes.
Checks internal consistency and file integrity only: it cannot establish that cuts are right (see
cut_regression.py and the reading discipline), that the transcript is accurate, or that the model looked.
Stdlib only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import math
import re
import struct
import sys
import tempfile
import zlib
from pathlib import Path

VERSION = "0.1.0"
SCHEMA = "1.0.0"
EDIT_KINDS = {"cut", "transition", "check"}
EDIT_TYPES = {"hard", "whip", "slide", "dissolve", "flash", "dip_black", "glitch", "fast_transition", "unknown"}
EDIT_CONF = {"auto", "verified", "corrected"}
SHEET_KINDS = {"keyframes", "overview", "audio", "zoom"}
COMPONENTS = ["measurements", "per_frame", "sheets", "transcript", "audio", "review", "integrity"]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEB = re.compile(r"[֐-׿]")
LETTER = re.compile(r"[A-Za-z֐-׿]")
MAX_KEYFRAME_GAP_S = 2.5  # "standard" detail max gap; a keyframe sheet set must reach every part of the video within it


def _no_const(name):
    raise ValueError("non-standard JSON constant: " + name)


def _no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate JSON key: " + k)
        out[k] = v
    return out


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"), parse_constant=_no_const, object_pairs_hook=_no_dupes)


def num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Report:
    def __init__(self, folder):
        self.folder = folder
        self.findings = []
        self.state = {c: "pass" for c in COMPONENTS}
        self.claims_not_allowed = []

    def add(self, comp, sev, code, msg):
        """sev: fail | insufficient | warn"""
        self.findings.append({"component": comp, "severity": sev, "code": code, "message": msg})
        if sev == "fail":
            self.state[comp] = "fail"
        elif sev == "insufficient" and self.state[comp] != "fail":
            self.state[comp] = "not_run"

    def finish(self, input_sha=None):
        fails = [f for f in self.findings if f["severity"] == "fail"]
        insuff = [f for f in self.findings if f["severity"] == "insufficient"]
        status = "FAIL" if fails else ("INSUFFICIENT_EVIDENCE" if insuff else "PASS")
        return {
            "tool": "validate_analysis", "version": VERSION, "analysis_dir": str(self.folder), "status": status,
            "input_sha256": input_sha, "components": self.state, "claims_not_allowed": sorted(set(self.claims_not_allowed)),
            "counts": {"fail": len(fails), "insufficient": len(insuff), "warn": len([f for f in self.findings if f["severity"] == "warn"])},
            "findings": self.findings,
            "limits": ["internal consistency and file integrity only",
                       "cut accuracy is checked with cut_regression.py on a labelled set, never by this script",
                       "`review` is the model's declaration; the viewing itself is appearance evidence this script cannot see"],
        }


def _read(rep, comp, path: Path):
    if not path.is_file():
        rep.add(comp, "insufficient", "FILE_MISSING", f"{path.name} not found")
        return None
    if path.stat().st_size == 0:
        rep.add(comp, "insufficient", "FILE_EMPTY", f"{path.name} is empty")
        return None
    try:
        return load_json(path)
    except (ValueError, OSError) as e:
        rep.add(comp, "fail", "BAD_JSON", f"{path.name}: {e}")
        return None


def _is_image(path: Path) -> bool:
    try:
        head = path.read_bytes()[:8]
    except OSError:
        return False
    return head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG\r\n\x1a\n")


# ----------------------------------------------------------------------------- measurements
def check_measurements(rep, d: Path, m, stage):
    if m is None:
        return None
    C = "measurements"
    if m.get("schema_version") != SCHEMA:
        rep.add(C, "fail", "SCHEMA", f"schema_version must be {SCHEMA}")
    inp = m.get("input") or {}
    cov = m.get("coverage") or {}
    env = m.get("environment") or {}
    for k in ("name", "sha256", "sha256_after", "duration_s", "fps_num", "fps_den", "width", "height", "frames_expected", "has_audio"):
        if k not in inp or inp[k] is None:
            rep.add(C, "fail", "INPUT_FIELD", f"input.{k} missing or null")
    if rep.state[C] == "fail":
        return None
    for k in ("sha256", "sha256_after"):
        if not HEX64.match(str(inp[k])):
            rep.add(C, "fail", "INPUT_HASH", f"input.{k} must be 64 lowercase hex")
    if not (num(inp["duration_s"]) and inp["duration_s"] > 0):
        rep.add(C, "fail", "DURATION", "input.duration_s must be a positive number")
        return None
    if not (isinstance(inp["fps_num"], int) and isinstance(inp["fps_den"], int) and inp["fps_num"] > 0 and inp["fps_den"] > 0):
        rep.add(C, "fail", "FPS", "fps_num/fps_den must be positive integers (rational fps, no 29.97 floats)")
        return None
    dur, fn, fd = float(inp["duration_s"]), inp["fps_num"], inp["fps_den"]
    fps = fn / fd
    vfr = bool(inp.get("vfr"))
    if not vfr and abs(inp["frames_expected"] - dur * fps) > 2.0:
        rep.add(C, "fail", "FRAME_COUNT", f"frames_expected {inp['frames_expected']} disagrees with duration x fps = {dur * fps:.1f}")
    # environment (G1 machine profile)
    for k in ("os", "ffmpeg", "asr_route"):
        if not env.get(k):
            rep.add(C, "insufficient", "ENV_MISSING", f"environment.{k} not recorded (machine profile / ASR route gate)")
    route = str(env.get("asr_route", ""))
    if "vulkan" in route and "ggml_vk_disable_coopmat" not in {k.lower(): v for k, v in (env.get("env") or {}).items()}:
        rep.add(C, "warn", "VULKAN_ENV", "Vulkan route: record GGML_VK_DISABLE_COOPMAT (the reference machine's driver crashes without =1; other drivers untested)")
    # coverage
    mode = cov.get("mode")
    if mode not in ("full", "sampled"):
        rep.add(C, "fail", "COVERAGE_MODE", "coverage.mode must be full | sampled")
        return None
    if not (isinstance(cov.get("frames_decoded"), int) and cov["frames_decoded"] > 0):
        rep.add(C, "insufficient", "NOTHING_DECODED", "coverage.frames_decoded must be a positive integer (an empty sample never passes)")
    elif mode == "full" and cov["frames_decoded"] != inp["frames_expected"]:
        rep.add(C, "fail", "COVERAGE_LIE", f"mode=full but decoded {cov['frames_decoded']} of {inp['frames_expected']} frames: report it as sampled")
    if mode == "sampled":
        rep.claims_not_allowed.append("full cut count / pacing as measured fact")
    # privacy flag
    private = bool(inp.get("private"))
    # edit points
    eps = m.get("edit_points")
    if not isinstance(eps, list):
        rep.add(C, "fail", "EDIT_POINTS", "edit_points must be a list (empty list is allowed only for a single continuous shot)")
        return {"fps": fps, "dur": dur, "private": private, "mode": mode, "frames": inp["frames_expected"]}
    seen, last = set(), -10
    n_counted = 0
    for e in eps:
        if not isinstance(e, dict):
            rep.add(C, "fail", "EDIT_POINT", "edit point is not an object")
            continue
        eid = e.get("id")
        if eid in seen:
            rep.add(C, "fail", "EDIT_ID_DUP", f"duplicate edit point id {eid}")
        seen.add(eid)
        fr, t = e.get("frame"), e.get("t_s")
        if not (isinstance(fr, int) and 0 <= fr < max(inp["frames_expected"], 1)) or not num(t) or not (0 <= t <= dur):
            rep.add(C, "fail", "EDIT_RANGE", f"edit point {eid}: frame/t_s outside the video")
            continue
        if not vfr and abs(t - fr * fd / fn) > 1.0 / fps + 1e-3:
            rep.add(C, "fail", "EDIT_TIME_FRAME", f"edit point {eid}: t_s {t} does not match frame {fr} at {fn}/{fd} fps")
        if fr < last:
            rep.add(C, "fail", "EDIT_ORDER", f"edit point {eid} is out of order")
        elif fr - last < 1 and last >= 0:
            rep.add(C, "fail", "EDIT_DUPLICATE", f"edit point {eid} is within 1 frame of the previous one (a transition is ONE edit point)")
        last = fr
        if e.get("kind") not in EDIT_KINDS or e.get("type") not in EDIT_TYPES or e.get("confidence") not in EDIT_CONF:
            rep.add(C, "fail", "EDIT_ENUM", f"edit point {eid}: kind/type/confidence not in the contract enums")
        if e.get("kind") in ("cut", "transition"):
            n_counted += 1
        if e.get("kind") == "check" and stage == "reviewed" and e.get("confidence") == "auto":
            rep.add("review", "insufficient", "CHECK_UNRESOLVED", f"edit point {eid} is a 'check' (jump cut vs graphic swap): decide from the frames, then retype it or record the correction")
    pc = m.get("pacing") or {}
    for k in ("edit_points", "cuts_per_min", "median_shot_s"):
        if not num(pc.get(k)):
            rep.add(C, "fail", "PACING_FIELD", f"pacing.{k} must be a number")
    if rep.state[C] != "fail":
        override = pc.get("override")
        expect_cpm = round(n_counted / (dur / 60.0), 3)
        if pc["edit_points"] != n_counted:
            rep.add(C, "fail", "PACING_COUNT", f"pacing.edit_points {pc['edit_points']} != {n_counted} cut/transition points listed")
        if isinstance(override, dict) and num(override.get("cuts_per_min")) and override.get("note"):
            if abs(pc["cuts_per_min"] - override["cuts_per_min"]) > 0.01:
                rep.add(C, "fail", "PACING_OVERRIDE", "pacing.cuts_per_min must equal the recorded override")
        elif abs(pc["cuts_per_min"] - expect_cpm) > 0.06:
            rep.add(C, "fail", "PACING_CPM", f"cuts_per_min {pc['cuts_per_min']} != {expect_cpm} computed from the listed edit points (record an override with a note if frames show the count is wrong)")
        bounds = [0.0] + [e["t_s"] for e in eps if isinstance(e, dict) and e.get("kind") in ("cut", "transition") and num(e.get("t_s"))] + [dur]
        lens = sorted(b - a for a, b in zip(bounds, bounds[1:]))
        if lens and not isinstance(override, dict):
            med = (lens[len(lens) // 2] + lens[(len(lens) - 1) // 2]) / 2
            if abs(pc["median_shot_s"] - med) > 0.03:
                rep.add(C, "fail", "PACING_MEDIAN", f"median_shot_s {pc['median_shot_s']} != {med:.3f} from the edit points")
    return {"fps": fps, "dur": dur, "private": private, "mode": mode, "frames": inp["frames_expected"], "decoded": cov.get("frames_decoded"),
            "has_audio": bool(inp["has_audio"]), "excluded": cov.get("excluded") or [], "env": env, "m": m}


# ----------------------------------------------------------------------------- per-frame
def check_per_frame(rep, d: Path, ctx):
    C = "per_frame"
    if ctx is None:
        rep.state[C] = "not_run"
        return
    if ctx["mode"] != "full":
        rep.state[C] = "n/a"
        return
    pf = (ctx["m"].get("per_frame") or {})
    p = d / (pf.get("file") or "frames.csv")
    if not p.is_file() or p.stat().st_size == 0:
        rep.add(C, "insufficient", "NO_FRAMES_CSV", "coverage.mode=full requires the per-frame file (frames.csv)")
        return
    try:
        with p.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except (OSError, csv.Error, UnicodeDecodeError) as e:
        rep.add(C, "fail", "CSV_BAD", str(e))
        return
    if not rows or not {"frame", "t_s"} <= set(rows[0].keys()):
        rep.add(C, "fail", "CSV_COLUMNS", "frames.csv needs at least the columns frame,t_s")
        return
    if len(rows) != ctx["decoded"]:
        rep.add(C, "fail", "CSV_ROWS", f"frames.csv has {len(rows)} rows but coverage.frames_decoded is {ctx['decoded']}")
        return
    prev_f, prev_t = -1, -1.0
    for i, r in enumerate(rows):
        try:
            f, t = int(r["frame"]), float(r["t_s"])
        except ValueError:
            rep.add(C, "fail", "CSV_VALUE", f"row {i + 2}: frame/t_s not numeric")
            return
        for k, v in r.items():
            if v not in ("", None):
                try:
                    if not math.isfinite(float(v)):
                        raise ValueError
                except ValueError:
                    rep.add(C, "fail", "CSV_NONFINITE", f"row {i + 2}: column {k} is not a finite number")
                    return
        if f <= prev_f or t < prev_t:
            rep.add(C, "fail", "CSV_ORDER", f"row {i + 2}: frame/time not increasing")
            return
        prev_f, prev_t = f, t


# ----------------------------------------------------------------------------- sheets
def check_sheets(rep, d: Path, ctx):
    C = "sheets"
    sd = d / "sheets"
    if not sd.is_dir():
        rep.add(C, "insufficient", "NO_SHEETS", "sheets/ folder missing")
        return {}
    idx = _read(rep, C, sd / "index.json")
    if idx is None:
        return {}
    items = idx.get("sheets")
    if idx.get("schema_version") != SCHEMA or not isinstance(items, list) or not items:
        rep.add(C, "insufficient" if not items else "fail", "INDEX", "sheets/index.json needs schema_version and a non-empty `sheets` list")
        return {}
    dur = ctx["dur"] if ctx else None
    files, spans, kinds = {}, [], set()
    for s in items:
        if not isinstance(s, dict):
            rep.add(C, "fail", "SHEET_ENTRY", "sheet entry is not an object")
            continue
        rel = s.get("file", "")
        p = d / rel
        if not rel.startswith("sheets/") or ".." in rel or not p.is_file() or p.stat().st_size < 64:
            rep.add(C, "fail", "SHEET_FILE", f"{rel!r}: missing, empty or outside sheets/")
            continue
        if not _is_image(p):
            rep.add(C, "fail", "SHEET_NOT_IMAGE", f"{rel}: not a JPEG/PNG (magic bytes)")
            continue
        if s.get("kind") not in SHEET_KINDS:
            rep.add(C, "fail", "SHEET_KIND", f"{rel}: kind must be one of {sorted(SHEET_KINDS)}")
            continue
        ts, te = s.get("t_start_s"), s.get("t_end_s")
        if not (num(ts) and num(te) and ts <= te and ts >= 0 and (dur is None or te <= dur + 0.05)):
            rep.add(C, "fail", "SHEET_TIME", f"{rel}: t_start_s/t_end_s invalid")
            continue
        if num(s.get("tile_px")) and s["tile_px"] < 160:
            rep.add(C, "warn", "TILE_SMALL", f"{rel}: tiles under 160 px are misread by models")
        files[rel] = s["kind"]
        kinds.add(s["kind"])
        if s["kind"] in ("keyframes", "overview"):
            spans.append((ts, te))
    if not ({"keyframes", "overview"} & kinds):
        rep.add(C, "insufficient", "NO_KEYFRAME_SHEETS", "no keyframe/overview sheet: nothing for the model to read")
    if ctx and ctx["has_audio"] and "audio" not in kinds:
        rep.add(C, "insufficient", "NO_AUDIO_IMAGE", "input has audio but no spectrogram/loudness image in sheets/")
    if ctx and spans and ctx["mode"] == "full":
        covered = sorted(spans)
        excl = [(e.get("start_s", 0), e.get("end_s", 0)) for e in ctx["excluded"] if isinstance(e, dict)]
        pos = 0.0
        for a, b in covered:
            if a - pos > MAX_KEYFRAME_GAP_S and not any(x <= pos and y >= a for x, y in excl):
                rep.add(C, "insufficient", "SHEET_GAP", f"no keyframe sheet covers {pos:.1f}-{a:.1f} s (limit {MAX_KEYFRAME_GAP_S} s)")
            pos = max(pos, b)
        if ctx["dur"] - pos > MAX_KEYFRAME_GAP_S and not any(x <= pos and y >= ctx["dur"] - 0.05 for x, y in excl):
            rep.add(C, "insufficient", "SHEET_TAIL", f"no keyframe sheet covers {pos:.1f}-{ctx['dur']:.1f} s")
    return files


# ----------------------------------------------------------------------------- transcript
def check_transcript(rep, d: Path, ctx, audio):
    C = "transcript"
    t = _read(rep, C, d / "transcript.json")
    if t is None:
        return
    if t.get("schema_version") != SCHEMA:
        rep.add(C, "fail", "SCHEMA", f"schema_version must be {SCHEMA}")
    status = t.get("status")
    dur = ctx["dur"] if ctx else None
    if status == "not_run":
        rep.add(C, "insufficient", "NOT_RUN", "transcript not run: " + str(t.get("reason") or "no reason given"))
        rep.claims_not_allowed.append("transcript / what is said")
        return
    if status == "no_speech":
        if not t.get("reason"):
            rep.add(C, "fail", "NO_SPEECH_REASON", "status no_speech needs the evidence in `reason`")
        if audio and audio.get("status") == "ok":
            sp = sum(max(0.0, b - a) for a, b in (audio.get("layers") or {}).get("speech", []) if num(a) and num(b))
            sg = sum(max(0.0, b - a) for a, b in (audio.get("layers") or {}).get("singing", []) if num(a) and num(b))
            if sp >= 0.8 or sg >= 2.0:
                rep.add(C, "fail", "NO_SPEECH_CONTRADICTION", f"audio.json has {sp:.1f} s speech / {sg:.1f} s singing but the transcript says no_speech")
        elif audio and audio.get("status") == "n/a" and audio.get("has_audio") is False:
            pass  # no audio stream: silence is proven by the probe, not by a model
        else:
            rep.add(C, "insufficient", "NO_SPEECH_UNPROVEN", "no_speech cannot be confirmed without audio.json status ok (or n/a for a file with no audio stream)")
        return
    if status != "ok":
        rep.add(C, "fail", "STATUS", "status must be ok | no_speech | not_run")
        return
    asr = t.get("asr") or {}
    for k in ("route", "model"):
        if not asr.get(k):
            rep.add(C, "fail", "ASR_FIELD", f"asr.{k} missing (the route and model must be recorded)")
    if ctx and ctx.get("private") and str(asr.get("route", "")).startswith("cloud"):
        rep.add(C, "fail", "PRIVATE_CLOUD", "input is flagged private but ASR ran on a cloud route")
    segs = t.get("segments")
    if not isinstance(segs, list) or not segs:
        rep.add(C, "insufficient", "NO_SEGMENTS", "status ok but no segments (an empty transcript never passes)")
        return
    prev = -1.0
    text = []
    for i, s in enumerate(segs):
        a, b, tx = s.get("start_s"), s.get("end_s"), s.get("text")
        if not (num(a) and num(b) and a < b and (dur is None or b <= dur + 0.5)) or not isinstance(tx, str) or not tx.strip():
            rep.add(C, "fail", "SEGMENT", f"segment {i}: bad times or empty text")
            return
        if a < prev - 1e-6:
            rep.add(C, "fail", "SEGMENT_ORDER", f"segment {i} starts before the previous one")
            return
        prev = a
        if s.get("kind") not in (None, "speech", "sung", "low_confidence", "over_music"):
            rep.add(C, "fail", "SEGMENT_KIND", f"segment {i}: kind not in contract")
        text.append(tx)
    words = t.get("words")
    if words is not None:
        pw = -1.0
        for i, w in enumerate(words):
            a, b = w.get("start_s"), w.get("end_s")
            if not (num(a) and num(b) and a <= b and a >= pw - 1e-6 and (dur is None or b <= dur + 0.5)):
                rep.add(C, "fail", "WORD_TIME", f"word {i}: bad or out-of-order times")
                return
            pw = a
    else:
        rep.add(C, "warn", "NO_WORDS", "no word timestamps: captions and joins need them")
    lang = t.get("language")
    joined = " ".join(text)
    letters = len(LETTER.findall(joined))
    if lang == "he" and letters >= 8 and len(HEB.findall(joined)) / letters < 0.3:
        rep.add(C, "fail", "LANGUAGE", "language is he but the text is mostly not Hebrew (wrong language forced, or wrong file)")
    if not lang:
        rep.add(C, "fail", "LANGUAGE", "language missing")
    if (t.get("qa") or {}).get("wer") is not None and not (t["qa"].get("wer_fixture")):
        rep.add(C, "fail", "WER_UNSCOPED", "a WER number needs the fixture it was measured on")


# ----------------------------------------------------------------------------- audio
def _intervals_ok(v):
    prev = -1.0
    for iv in v:
        if not (isinstance(iv, list) and len(iv) == 2 and num(iv[0]) and num(iv[1]) and iv[0] <= iv[1] and iv[0] >= prev - 1e-6):
            return False
        prev = iv[0]
    return True


def check_audio(rep, d: Path, ctx, sheet_files):
    C = "audio"
    a = _read(rep, C, d / "audio.json")
    if a is None:
        return None
    if a.get("schema_version") != SCHEMA:
        rep.add(C, "fail", "SCHEMA", f"schema_version must be {SCHEMA}")
    st = a.get("status")
    has = a.get("has_audio")
    if ctx and isinstance(has, bool) and has != ctx["has_audio"]:
        rep.add(C, "fail", "HAS_AUDIO_MISMATCH", "audio.has_audio differs from measurements input.has_audio")
    if st == "n/a":
        if has is not False or not a.get("reason"):
            rep.add(C, "fail", "NA_REASON", "status n/a requires has_audio=false and a reason (silent video)")
        else:
            rep.state[C] = "n/a"
            rep.claims_not_allowed.append("anything about sound (the file has no audio track)")
        return a
    if st == "not_run":
        rep.add(C, "insufficient", "NOT_RUN", "audio analysis not run: " + str(a.get("reason") or "no reason given"))
        rep.claims_not_allowed.append("loudness / music / BPM / SFX / song")
        return a
    if st != "ok" or has is not True:
        rep.add(C, "fail", "STATUS", "status must be ok (with has_audio=true) | n/a | not_run")
        return a
    dur = ctx["dur"] if ctx else None
    ld = a.get("loudness") or {}
    if not (num(ld.get("integrated_lufs")) and -70 <= ld["integrated_lufs"] <= 0):
        rep.add(C, "fail", "LUFS", "loudness.integrated_lufs must be a number in [-70, 0]")
    if not num(ld.get("true_peak_dbtp")):
        rep.add(C, "fail", "TRUE_PEAK", "loudness.true_peak_dbtp must be a number (0.0 is a number; null/missing is not)")
    if not (num(ld.get("lra")) and ld["lra"] >= 0):
        rep.add(C, "fail", "LRA", "loudness.lra must be a number >= 0")
    layers = a.get("layers") or {}
    for k in ("speech", "music", "singing"):
        if not isinstance(layers.get(k), list) or not _intervals_ok(layers[k]) or (dur and any(iv[1] > dur + 0.1 for iv in layers[k])):
            rep.add(C, "fail", "LAYER", f"layers.{k} must be a list of ordered [start, end] seconds inside the video")
    mu = a.get("music") or {}
    if mu.get("present"):
        bpm, beats = mu.get("tempo_bpm"), mu.get("beats_s")
        if not (num(bpm) and 30 <= bpm <= 300):
            rep.add(C, "fail", "BPM", "music.tempo_bpm must be a number in [30, 300] when music is present")
        if not isinstance(beats, list) or any(not num(b) for b in beats) or beats != sorted(beats) or (dur and beats and beats[-1] > dur + 0.1):
            rep.add(C, "fail", "BEATS", "music.beats_s must be an increasing list of seconds inside the video")
        if mu.get("half_double_audited") is not True:
            rep.add(C, "insufficient", "TEMPO_UNAUDITED", "tempo is an estimate: audit half/double time against the audio image and set half_double_audited=true")
        if not mu.get("key"):
            rep.add(C, "warn", "NO_KEY", "no key recorded (estimate, label confidence)")
    elif mu.get("tempo_bpm") is not None:
        rep.add(C, "fail", "BPM_NO_MUSIC", "tempo_bpm set while music.present is false")
    sid = a.get("song_id") or {}
    if sid.get("status") not in ("matched", "no_match", "skipped", "opted_out"):
        rep.add(C, "fail", "SONG_STATUS", "song_id.status must be matched | no_match | skipped | opted_out")
    if sid.get("sync_permission") != "not_established":
        rep.add(C, "fail", "SYNC_PERMISSION", "song_id.sync_permission must be exactly 'not_established': a match tells you the track, not that you may use it")
    if sid.get("status") == "matched" and not (sid.get("title") and sid.get("transport")):
        rep.add(C, "fail", "SONG_FIELDS", "a matched song needs title and the transport used (remote/local)")
    if ctx and ctx.get("private") and sid.get("status") not in ("opted_out", "skipped"):
        rep.add(C, "fail", "PRIVATE_SONG_ID", "input flagged private: song id must be opted_out or skipped (no excerpt may leave the machine)")
    for k in a.get("images") or []:
        if k not in sheet_files:
            rep.add(C, "fail", "AUDIO_IMAGE", f"{k} is not an entry of sheets/index.json")
    if not a.get("images"):
        rep.add(C, "insufficient", "NO_AUDIO_IMAGES", "audio.json lists no spectrogram/loudness image")
    for ev in a.get("sfx_events") or []:
        if not (num(ev.get("t_s")) and isinstance(ev.get("labels"), list)):
            rep.add(C, "fail", "SFX", "sfx_events need t_s and labels")
            break
    return a


# ----------------------------------------------------------------------------- review + integrity
def check_review(rep, ctx, sheet_files, stage):
    C = "review"
    if stage == "produced":
        rep.state[C] = "n/a"
        return
    if ctx is None:
        rep.state[C] = "not_run"
        return
    rv = ctx["m"].get("review")
    if not isinstance(rv, dict):
        rep.add(C, "insufficient", "NO_REVIEW", "measurements.review missing: the sheets have not been read (reading discipline gate)")
        return
    if rv.get("reviewed_by") not in ("model", "human"):
        rep.add(C, "fail", "REVIEWED_BY", "review.reviewed_by must be model | human")
    need = {f for f, k in sheet_files.items() if k in ("keyframes", "overview")}
    miss = need - set(rv.get("sheets_viewed") or [])
    if miss:
        rep.add(C, "insufficient", "SHEETS_UNVIEWED", f"{len(miss)} keyframe/overview sheet(s) not marked viewed, e.g. {sorted(miss)[0]}")
    need_a = {f for f, k in sheet_files.items() if k == "audio"}
    miss_a = need_a - set(rv.get("audio_images_viewed") or [])
    if miss_a:
        rep.add(C, "insufficient", "AUDIO_UNVIEWED", f"audio image(s) not marked viewed, e.g. {sorted(miss_a)[0]}")
    zc = rv.get("zoom_count")
    if not (isinstance(zc, int) and zc >= 0):
        rep.add(C, "fail", "ZOOM_COUNT", "review.zoom_count must be an integer >= 0")


def check_integrity(rep, ctx, video):
    C = "integrity"
    if ctx is None:
        rep.state[C] = "not_run"
        return
    inp = ctx["m"]["input"]
    if inp["sha256"] != inp["sha256_after"]:
        rep.add(C, "fail", "INPUT_MODIFIED", "input.sha256 != sha256_after: the analysis changed its input (inputs are read-only)")
    if video:
        p = Path(video)
        if not p.is_file():
            rep.add(C, "insufficient", "VIDEO_MISSING", f"--video {p} not found: cannot re-hash the source")
        elif sha256_file(p) != inp["sha256"]:
            rep.add(C, "fail", "INPUT_HASH_MISMATCH", "the source file no longer matches input.sha256 (changed, or a different file)")
    else:
        rep.add(C, "warn", "NOT_REHASHED", "source not re-hashed (no --video); only the before/after equality was checked")


# ----------------------------------------------------------------------------- orchestration
def validate(folder, video=None, stage="reviewed", allow_not_run=()):
    d = Path(folder)
    rep = Report(d)
    if not d.is_dir():
        rep.add("measurements", "insufficient", "NO_FOLDER", f"{d} is not a folder")
        return rep.finish(), 2
    m = _read(rep, "measurements", d / "measurements.json")
    ctx = check_measurements(rep, d, m, stage)
    check_per_frame(rep, d, ctx)
    sheet_files = check_sheets(rep, d, ctx)
    audio = None
    # audio before transcript: the no_speech cross-check reads it
    audio = check_audio(rep, d, ctx, sheet_files)
    check_transcript(rep, d, ctx, audio)
    check_review(rep, ctx, sheet_files, stage)
    check_integrity(rep, ctx, video)
    # declared skips: a component that was deliberately not run may be allowed, but its claims stay forbidden
    for comp in allow_not_run:
        if comp in rep.state and rep.state[comp] == "not_run":
            rep.state[comp] = "n/a"
            rep.findings = [f for f in rep.findings if not (f["component"] == comp and f["severity"] == "insufficient" and f["code"] in ("NOT_RUN", "FILE_MISSING", "FILE_EMPTY"))]
            rep.claims_not_allowed.append({"transcript": "transcript / what is said", "audio": "loudness / music / BPM / SFX / song"}.get(comp, comp))
    out = rep.finish(ctx["m"]["input"]["sha256"] if ctx else None)
    return out, {"PASS": 0, "FAIL": 1}.get(out["status"], 2)


# ----------------------------------------------------------------------------- self-check
def _png(w=8, h=8) -> bytes:
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * w for _ in range(h))

    def chunk(t, data):
        c = struct.pack(">I", len(data)) + t + data
        return c + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def make_fixture(d: Path, frames=300, fps=(30, 1), full=True):
    """A valid 10 s synthetic analysis folder (no real video: only the contract is exercised)."""
    d.mkdir(parents=True, exist_ok=True)
    (d / "sheets").mkdir(exist_ok=True)
    fn, fd = fps
    dur = frames * fd / fn
    h = "ab" * 32
    eps = [{"id": f"E{i + 1}", "t_s": round(f * fd / fn, 4), "frame": f, "kind": "cut", "type": "hard", "confidence": "verified", "note": ""} for i, f in enumerate([60, 120, 180, 240])]
    bounds = [0.0] + [e["t_s"] for e in eps] + [dur]
    lens = sorted(b - a for a, b in zip(bounds, bounds[1:]))
    meas = {
        "schema_version": SCHEMA, "tool": {"name": "analyze", "version": "0.1.0", "detail": "standard"}, "created_utc": "2026-10-02T10:00:00Z",
        "input": {"name": "clip.mp4", "sha256": h, "sha256_after": h, "size_bytes": 1000, "duration_s": dur, "fps_num": fn, "fps_den": fd,
                  "width": 1080, "height": 1920, "rotation": 0, "vfr": False, "frames_expected": frames, "has_audio": True, "private": False},
        "environment": {"os": "one reference machine", "ffmpeg": "8.1", "asr_route": "cpu-ct2", "env": {}},
        "coverage": {"mode": "full" if full else "sampled", "frames_decoded": frames, "frames_expected": frames, "pts_policy": "decoder_pts", "excluded": []},
        "edit_points": eps,
        "pacing": {"edit_points": 4, "cuts_per_min": round(4 / (dur / 60), 3), "median_shot_s": lens[len(lens) // 2], "mean_shot_s": dur / 5},
        "per_frame": {"file": "frames.csv", "columns": ["frame", "t_s", "luma"], "rows": frames},
        "review": {"reviewed_by": "model", "sheets_viewed": ["sheets/sheet_001.png", "sheets/overview_001.png"], "audio_images_viewed": ["sheets/audio_001.png"], "zoom_count": 3, "corrections": []},
    }
    (d / "measurements.json").write_text(json.dumps(meas), encoding="utf-8")
    with (d / "frames.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "t_s", "luma"])
        for f in range(frames):
            w.writerow([f, round(f * fd / fn, 5), 100.0])
    for name in ("sheet_001.png", "overview_001.png", "audio_001.png"):
        (d / "sheets" / name).write_bytes(_png())
    idx = {"schema_version": SCHEMA, "sheets": [
        {"file": "sheets/sheet_001.png", "kind": "keyframes", "t_start_s": 0.0, "t_end_s": dur, "tiles": 9, "tile_px": 280},
        {"file": "sheets/overview_001.png", "kind": "overview", "t_start_s": 0.0, "t_end_s": dur, "tiles": 5, "tile_px": 280},
        {"file": "sheets/audio_001.png", "kind": "audio", "t_start_s": 0.0, "t_end_s": dur, "tiles": 1, "tile_px": 900}]}
    (d / "sheets" / "index.json").write_text(json.dumps(idx), encoding="utf-8")
    tr = {"schema_version": SCHEMA, "status": "ok", "language": "he", "asr": {"route": "cpu-ct2", "model": "ivrit-ai/whisper-large-v3-turbo-ct2", "vad": True, "language_forced": True},
          "segments": [{"start_s": 0.5, "end_s": 3.0, "text": "שלום עולם זה בדיקה", "kind": "speech"}],
          "words": [{"text": "שלום", "start_s": 0.5, "end_s": 0.9}, {"text": "עולם", "start_s": 1.0, "end_s": 1.4}]}
    (d / "transcript.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    au = {"schema_version": SCHEMA, "status": "ok", "has_audio": True,
          "loudness": {"integrated_lufs": -14.2, "lra": 5.0, "true_peak_dbtp": 0.0, "meter": "ebur128 peak=true", "scope": "whole_file"},
          "layers": {"speech": [[0.5, 3.0]], "music": [[0.0, 10.0]], "singing": []},
          "sfx_events": [{"t_s": 1.2, "labels": ["whoosh"], "peak": 0.4, "likely": True}], "silences": [],
          "music": {"present": True, "tempo_bpm": 120.0, "beats_s": [0.5, 1.0, 1.5], "key": "A minor", "key_confidence": 0.3, "half_double_audited": True},
          "song_id": {"status": "no_match", "title": None, "artist": None, "sync_permission": "not_established", "transport": "none"},
          "images": ["sheets/audio_001.png"]}
    (d / "audio.json").write_text(json.dumps(au), encoding="utf-8")


def _mutate(d: Path, fname, fn):
    p = d / fname
    j = json.loads(p.read_text(encoding="utf-8"))
    fn(j)
    p.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")


def self_check() -> int:
    ok, fails = 0, []

    def expect(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(label)

    def run(d, **kw):
        out, code = validate(d, **kw)
        return out, code, {f["code"] for f in out["findings"]}

    with tempfile.TemporaryDirectory(prefix="va_בדיקה ") as td:
        base = Path(td)

        def fresh(name, **kw):
            d = base / name
            make_fixture(d, **kw)
            return d

        d = fresh("ok")
        out, code, codes = run(d)
        expect("valid folder passes (true peak 0.0 is a number)", code == 0 and out["status"] == "PASS")

        d = fresh("miss_transcript")
        (d / "transcript.json").unlink()
        out, code, codes = run(d)
        expect("missing transcript -> INSUFFICIENT", code == 2 and "FILE_MISSING" in codes)
        out, code, _ = run(d, allow_not_run=("transcript",))
        expect("declared skip allowed, speech claims forbidden", code == 0 and "transcript / what is said" in out["claims_not_allowed"])

        d = fresh("lie_full")
        _mutate(d, "measurements.json", lambda j: j["coverage"].update(frames_decoded=250))
        out, code, codes = run(d)
        expect("mode=full with fewer decoded frames -> FAIL", code == 1 and "COVERAGE_LIE" in codes)

        d = fresh("sampled")
        _mutate(d, "measurements.json", lambda j: j["coverage"].update(mode="sampled", frames_decoded=40))
        (d / "frames.csv").unlink()
        out, code, codes = run(d)
        expect("sampled mode passes but forbids full-count claims", code == 0 and any("full cut count" in c for c in out["claims_not_allowed"]))

        d = fresh("nothing_decoded")
        _mutate(d, "measurements.json", lambda j: j["coverage"].update(frames_decoded=0))
        out, code, codes = run(d)
        expect("zero decoded frames never passes", code != 0 and "NOTHING_DECODED" in codes)

        d = fresh("csv_rows")
        lines = (d / "frames.csv").read_text().splitlines()
        (d / "frames.csv").write_text("\n".join(lines[:-5]) + "\n")
        expect("frames.csv short -> FAIL", run(d)[1] == 1)

        d = fresh("cpm")
        _mutate(d, "measurements.json", lambda j: j["pacing"].update(cuts_per_min=99.0))
        out, code, codes = run(d)
        expect("cuts/min not matching edit points -> FAIL", code == 1 and "PACING_CPM" in codes)
        _mutate(d, "measurements.json", lambda j: j["pacing"].update(override={"cuts_per_min": 99.0, "note": "kinetic type: counted from sheets"}))
        expect("override with a note is accepted", run(d)[1] == 0)

        d = fresh("check_unresolved")
        _mutate(d, "measurements.json", lambda j: j["edit_points"][1].update(kind="check", confidence="auto"))
        _mutate(d, "measurements.json", lambda j: j["pacing"].update(edit_points=3, cuts_per_min=round(3 / (10 / 60), 3), median_shot_s=2.0))
        out, code, codes = run(d)
        expect("unresolved 'check' edit point -> INSUFFICIENT at reviewed stage", "CHECK_UNRESOLVED" in codes and code == 2)
        expect("same folder passes the produced stage w.r.t. review", "CHECK_UNRESOLVED" not in run(d, stage="produced")[2])

        d = fresh("order")
        _mutate(d, "measurements.json", lambda j: j["edit_points"].reverse())
        expect("edit points out of order -> FAIL", run(d)[1] == 1)

        d = fresh("hash")
        _mutate(d, "measurements.json", lambda j: j["input"].update(sha256_after="cd" * 32))
        out, code, codes = run(d)
        expect("input modified -> FAIL", code == 1 and "INPUT_MODIFIED" in codes)
        vid = base / "src.mp4"
        vid.write_bytes(b"not the original")
        out, code, codes = run(fresh("hash2"), video=vid)
        expect("--video hash mismatch -> FAIL", "INPUT_HASH_MISMATCH" in codes)

        d = fresh("sheet_gap")
        _mutate(d, "sheets/index.json", lambda j: [j["sheets"].pop(0), j["sheets"][0].update(t_start_s=5.0)])
        out, code, codes = run(d)
        expect("keyframe sheets not covering the start -> INSUFFICIENT", "SHEET_GAP" in codes and code != 0)

        d = fresh("fake_image")
        (d / "sheets" / "sheet_001.png").write_bytes(b"x" * 200)
        expect("non-image sheet -> FAIL", "SHEET_NOT_IMAGE" in run(d)[2])

        d = fresh("unviewed")
        _mutate(d, "measurements.json", lambda j: j["review"].update(sheets_viewed=[]))
        out, code, codes = run(d)
        expect("sheets not viewed -> INSUFFICIENT", code == 2 and "SHEETS_UNVIEWED" in codes)

        d = fresh("lang")
        _mutate(d, "transcript.json", lambda j: j["segments"][0].update(text="this is plain english speech text here"))
        expect("language he with English text -> FAIL", "LANGUAGE" in run(d)[2])

        d = fresh("no_speech_lie")
        _mutate(d, "transcript.json", lambda j: j.update(status="no_speech", reason="none heard", segments=[], words=[]))
        expect("no_speech contradicting audio layers -> FAIL", "NO_SPEECH_CONTRADICTION" in run(d)[2])

        d = fresh("tp_null")
        _mutate(d, "audio.json", lambda j: j["loudness"].update(true_peak_dbtp=None))
        expect("true peak null -> FAIL", "TRUE_PEAK" in run(d)[2])

        d = fresh("song")
        _mutate(d, "audio.json", lambda j: j["song_id"].update(status="matched", title="X", transport="remote", sync_permission="granted"))
        expect("a song match is not a licence -> FAIL", "SYNC_PERMISSION" in run(d)[2])

        d = fresh("bpm")
        _mutate(d, "audio.json", lambda j: j["music"].update(half_double_audited=False))
        expect("unaudited tempo -> INSUFFICIENT", run(d)[1] == 2)

        d = fresh("private")
        _mutate(d, "measurements.json", lambda j: j["input"].update(private=True))
        _mutate(d, "audio.json", lambda j: j["song_id"].update(status="matched", title="X", transport="remote"))
        expect("private input with remote song id -> FAIL", "PRIVATE_SONG_ID" in run(d)[2])

        d = fresh("silent")
        _mutate(d, "measurements.json", lambda j: j["input"].update(has_audio=False))
        _mutate(d, "audio.json", lambda j: j.update(status="n/a", has_audio=False, reason="no audio stream"))
        _mutate(d, "transcript.json", lambda j: j.update(status="no_speech", reason="no audio stream", segments=[], words=[]))
        (d / "sheets" / "audio_001.png").unlink()
        _mutate(d, "sheets/index.json", lambda j: j["sheets"].pop())
        _mutate(d, "measurements.json", lambda j: j["review"].update(audio_images_viewed=[]))
        out, code, codes = run(d)
        expect("silent video: audio n/a with reason, no sound claims", code == 0 and "anything about sound" in " ".join(out["claims_not_allowed"]))

        expect("missing folder -> INSUFFICIENT", validate(base / "nope")[1] == 2)
        bad = base / "dupe"
        make_fixture(bad)
        (bad / "audio.json").write_text('{"status":"ok","status":"ok"}', encoding="utf-8")
        expect("duplicate JSON key -> FAIL", run(bad)[1] == 1)

    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": ok + len(fails), "failed": fails}))
    return 0 if not fails else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Validate an analysis folder against the video-analysis contract (fail closed).")
    ap.add_argument("analysis_dir", nargs="?")
    ap.add_argument("--video")
    ap.add_argument("--stage", choices=["produced", "reviewed"], default="reviewed")
    ap.add_argument("--allow-not-run", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.analysis_dir:
        ap.print_help()
        return 2
    allow = tuple(x.strip() for x in a.allow_not_run.split(",") if x.strip())
    out, code = validate(a.analysis_dir, a.video, a.stage, allow)
    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"{out['status']}  fail={out['counts']['fail']} insufficient={out['counts']['insufficient']} warn={out['counts']['warn']}")
        print("  components: " + ", ".join(f"{k}={v}" for k, v in out["components"].items()))
        for f in out["findings"]:
            print(f"  [{f['severity']}] {f['component']}/{f['code']}: {f['message']}")
        if out["claims_not_allowed"]:
            print("  claims NOT allowed in the breakdown: " + "; ".join(out["claims_not_allowed"]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""promise_check - no silent changes: lock what the user approved, then list every difference between that and what was built.

Usage:
  python promise_check.py lock PROJECT --captions off|<lang> --music on|off --voice speaker|vo|tts|none
                               [--duration S] [--aspect 9:16] [--storyboard PATH] [--tolerance-s 0.5] [--relock]
        Writes PROJECT/_work/promise.json. Refused (exit 2) unless PROJECT/hf/CHANGELOG.md holds a `PROMPT_APPROVED` line and,
        when the video has a storyboard (PATH, or PROJECT/_work/storyboard/storyboard.json when it exists), a
        `STORYBOARD APPROVED` line. Duration and aspect default to the storyboard's. An existing promise is kept unless --relock
        (a new approval): the old file is then saved as promise.<UTC stamp>.json.
  python promise_check.py record PROJECT --field FIELD --to VALUE --asked "<the user's words>"
        Records a change the user agreed to, with the time, under `changes`. FIELD is one of: duration_s, aspect, captions
        (off or a language code), music (on/off), voice (speaker/vo/tts/none), beats.<id>.source, beats.<id>.roll,
        beats.<id> (VALUE dropped or added), beats.order (VALUE = the beat ids in the new order, joined by commas).
  python promise_check.py check PROJECT [--render DRAFT] [--storyboard PATH] [--cues PATH]
        Measures what was built: without --render (before the draft render) the composition root's data-duration and
        data-width/height; with --render the draft file itself (ffprobe: length, aspect, an audio stream). Always: the composition
        (PROJECT/hf: captions present, and their script from hf/data/captions.json), the mix cues (hf/cues.json: a music bed, a separate voice track)
        and the current storyboard (each beat's roll and source, and their order). Compares that with promise.json plus its
        asked changes and prints every row. Exit 0 = every measured promise kept, or changed with an ask on record;
        1 = a change nobody asked for (ask, then `record`, or rebuild to the promise); 2 = refused (no promise, bad input).
        A promise that cannot be measured is listed `not_measured`: confirm it by eye or ear before presenting; it is never
        reported as kept.
  python promise_check.py --self-check        runs scripts/test_promise_check.py

What it cannot see: whether a voice track is recorded or synthetic (both are "a voice track"), the language of captions when
there is no hf/data/captions.json, and anything inside a beat beyond its roll and source. Those stay the editor's job.
Stdlib only, Python 3.10+ (check needs ffprobe on PATH for the draft's length and aspect).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

SCHEMA = "avc.promise/1"
ROLLS = ("A", "B", "G")
SOURCES = ("own", "stock", "generated", "graphic", "reference", "sketch")
VOICES = ("speaker", "vo", "tts", "none")
ASPECTS = ("9:16", "16:9", "1:1", "4:5", "4:3", "3:4", "21:9")
LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$")
ASPECT_RE = re.compile(r"^\d{1,3}:\d{1,3}$")
FIELD_RE = re.compile(r"^(duration_s|aspect|captions|music|voice|beats\.order|beats\.[A-Za-z0-9_-]{1,24}(\.(source|roll|shot))?)$")
SHOTS = ("wide", "medium", "close", "detail", "graphic", "screen")  # the storyboard's `shot` values (storyboard_board.py)
CAPTION_MARK_RE = re.compile(r"""(?i)(?:class|id|data-[\w-]+)\s*=\s*["'][^"']*caption""")
TEXT_KEYS = ("text", "word", "line", "label", "caption")
LATIN_LANGS = {"en", "es", "fr", "de", "it", "pt", "nl", "pl", "tr", "ro", "sv", "da", "no", "nb", "fi", "cs", "hu", "id", "vi", "ca", "hr", "sk", "sl"}
LANG_SCRIPT = {**{k: "latin" for k in LATIN_LANGS}, "he": "hebrew", "yi": "hebrew", "ar": "arabic", "fa": "arabic", "ur": "arabic",
               "ru": "cyrillic", "uk": "cyrillic", "bg": "cyrillic", "sr": "cyrillic", "el": "greek"}
SCRIPTS = (("hebrew", 0x0590, 0x05FF), ("arabic", 0x0600, 0x06FF), ("cyrillic", 0x0400, 0x04FF), ("greek", 0x0370, 0x03FF))


def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _out(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- the promise


def approval_lines(changelog: Path) -> dict:
    """The last PROMPT_APPROVED and STORYBOARD APPROVED lines of hf/CHANGELOG.md (None when absent)."""
    found = {"prompt": None, "storyboard": None}
    if changelog.is_file():
        for line in changelog.read_text(encoding="utf-8", errors="replace").splitlines():
            if "PROMPT_APPROVED" in line:
                found["prompt"] = line.strip()
            if "STORYBOARD APPROVED" in line:
                found["storyboard"] = line.strip()
    return found


def storyboard_beats(spec: dict) -> list[dict]:
    out = []
    for b in spec.get("beats", []) if isinstance(spec, dict) else []:
        if isinstance(b, dict) and isinstance(b.get("id"), str):
            out.append({"id": b["id"], "t": b.get("t"), "end": b.get("end"), "roll": b.get("roll"), "source": b.get("source"),
                        "shot": b.get("shot") if b.get("shot") in SHOTS else "unset"})
    return out


def build_promise(project: str, duration, aspect, captions, music, voice, tolerance, beats, approvals) -> tuple[dict | None, list[str]]:
    """Pure: the arguments -> (promise.json document, errors)."""
    errors = []
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
        errors.append("duration: give --duration S (seconds > 0) or a storyboard with beats")
    if not isinstance(aspect, str) or not ASPECT_RE.match(aspect):
        errors.append("aspect: give --aspect W:H (for example 9:16) or a storyboard with `aspect`")
    captions = (captions or "").strip().lower() if isinstance(captions, str) else ""
    if captions != "off" and not LANG_RE.match(captions):
        errors.append("captions: off, or the caption language code from Round 0 (he, en, es, ...)")
    if music not in ("on", "off"):
        errors.append("music: on or off")
    if voice not in VOICES:
        errors.append(f"voice: one of {list(VOICES)}")
    if not isinstance(tolerance, (int, float)) or tolerance < 0:
        errors.append("tolerance-s: a number >= 0")
    if not approvals.get("prompt"):
        errors.append("no `PROMPT_APPROVED` line in hf/CHANGELOG.md: the promise is locked only after the user approved PROMPT.md")
    if beats and not approvals.get("storyboard"):
        errors.append("the video has a storyboard but hf/CHANGELOG.md has no `STORYBOARD APPROVED` line: lock after the board is approved")
    seen = set()
    for b in beats:
        if b["id"] in seen:
            errors.append(f"storyboard beat id {b['id']!r} is not unique")
        seen.add(b["id"])
        if b["roll"] not in ROLLS or b["source"] not in SOURCES:
            errors.append(f"storyboard beat {b['id']}: roll/source must be valid (run storyboard_board.py check)")
    if errors:
        return None, errors
    doc = {"schema": SCHEMA, "project": project, "locked_utc": now_utc(), "approvals": approvals,
           "promise": {"duration_s": round(float(duration), 3), "tolerance_s": float(tolerance), "aspect": aspect, "captions": captions,
                       "music": music, "voice": voice, "beats": beats},
           "changes": []}
    return doc, []


def flat_promise(doc: dict) -> dict:
    """The promise as field -> value, before any change."""
    p = doc["promise"]
    flat = {"duration_s": p["duration_s"], "aspect": p["aspect"], "captions": p["captions"], "music": p["music"], "voice": p["voice"]}
    beats = p.get("beats") or []
    for b in beats:
        flat[f"beats.{b['id']}"] = "present"
        flat[f"beats.{b['id']}.roll"] = b["roll"]
        flat[f"beats.{b['id']}.source"] = b["source"]
        if "shot" in b:  # promises locked before `shot` existed carry no shot and are not compared on it
            flat[f"beats.{b['id']}.shot"] = b["shot"]
    if beats:
        flat["beats.order"] = ",".join(b["id"] for b in beats)
    return flat


def change_problem(c) -> str | None:
    """Why a recorded change cannot count as asked (None when it can)."""
    if not isinstance(c, dict):
        return "a change entry is not an object"
    if not isinstance(c.get("field"), str) or not FIELD_RE.match(c["field"]):
        return f"change {c.get('field')!r}: unknown field"
    if c.get("to") is None or (isinstance(c.get("to"), str) and not c["to"].strip()):
        return f"change {c['field']}: no `to` value"
    if not isinstance(c.get("asked"), str) or len(c["asked"].strip()) < 2:
        return f"change {c['field']}: no `asked` (the user's own words)"
    try:
        _dt.datetime.fromisoformat(str(c.get("at")))
    except ValueError:
        return f"change {c['field']}: `at` is not an ISO time"
    return None


def effective(doc: dict) -> tuple[dict, dict, list[str]]:
    """Pure: promise + valid changes -> (field -> value now promised, field -> the change that set it, problems)."""
    flat = flat_promise(doc)
    by_field: dict = {}
    problems = []
    for c in doc.get("changes") or []:
        why = change_problem(c)
        if why:
            problems.append(why + " (not counted)")
            continue
        f, to = c["field"], c["to"]
        if f == "duration_s":
            try:
                to = float(to)
            except (TypeError, ValueError):
                problems.append("change duration_s: `to` is not a number (not counted)")
                continue
        if re.match(r"^beats\.[^.]+$", f) and f != "beats.order" and to == "dropped":
            flat.pop(f + ".roll", None)
            flat.pop(f + ".source", None)
            flat.pop(f + ".shot", None)
        flat[f] = to
        by_field[f] = c
    return flat, by_field, problems


# ---------------------------------------------------------------- measuring what was built


def aspect_name(w: int, h: int) -> str:
    if not w or not h:
        return "unknown"
    r = w / h
    for a in ASPECTS:
        x, y = (int(v) for v in a.split(":"))
        if abs(r - x / y) <= 0.01 * (x / y):
            return a
    f = Fraction(w, h)
    return f"{f.numerator}:{f.denominator}"


def probe(render: Path) -> dict | None:
    """ffprobe the draft: {duration_s, width, height, aspect, audio}; None when ffprobe is missing or the file cannot be read."""
    fp = shutil.which("ffprobe")
    if not fp or not render.is_file():
        return None
    p = subprocess.run([fp, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(render)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return None
    try:
        d = json.loads(p.stdout or "{}")
        dur = float(d.get("format", {}).get("duration"))
    except (ValueError, TypeError):
        return None
    w = h = 0
    audio = False
    for s in d.get("streams", []):
        if s.get("codec_type") == "video" and not w:
            w, h = int(s.get("width") or 0), int(s.get("height") or 0)
            rot = 0
            try:
                rot = int(float((s.get("tags") or {}).get("rotate", 0)))
            except ValueError:
                pass
            for sd in s.get("side_data_list") or []:
                if "rotation" in sd:
                    rot = int(float(sd["rotation"]))
            if abs(rot) % 180 == 90:
                w, h = h, w
        elif s.get("codec_type") == "audio":
            audio = True
    return {"duration_s": round(dur, 3), "width": w, "height": h, "aspect": aspect_name(w, h), "audio": "present" if audio else "none"}


def _strings(obj, out: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and k in TEXT_KEYS:
                out.append(v)
            else:
                _strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _strings(v, out)


def script_of(text: str) -> str | None:
    counts = {"latin": 0}
    for ch in text:
        o = ord(ch)
        if ch.isalpha() and o < 0x250:
            counts["latin"] += 1
            continue
        for name, lo, hi in SCRIPTS:
            if lo <= o <= hi:
                counts[name] = counts.get(name, 0) + 1
    best = max(counts.items(), key=lambda kv: kv[1])
    return best[0] if best[1] else None


def measure_captions(hf: Path) -> str | None:
    """'off', 'on' (language not measurable) or 'script:<name>'; None when there is no composition to read."""
    if not (hf / "index.html").is_file():
        return None
    words: list[str] = []
    cap = hf / "data" / "captions.json"
    if cap.is_file():
        try:
            _strings(json.loads(cap.read_text(encoding="utf-8")), words)
        except (OSError, ValueError):
            pass
    marked = False
    for f in [hf / "index.html", *sorted((hf / "compositions").glob("*.html"))] if (hf / "compositions").is_dir() else [hf / "index.html"]:
        try:
            if CAPTION_MARK_RE.search(f.read_text(encoding="utf-8", errors="replace")):
                marked = True
                break
        except OSError:
            continue
    if words:
        s = script_of(" ".join(words))
        return f"script:{s}" if s else "on"
    return "on" if marked else "off"


def measure_cues(cues: Path) -> dict:
    """{music: on|off|None, voice_track: True|False|None} from the hf_mix cue file."""
    if not cues.is_file():
        return {"music": None, "voice_track": None}
    try:
        d = json.loads(cues.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"music": None, "voice_track": None}
    if not isinstance(d, dict):
        return {"music": None, "voice_track": None}
    m = d.get("music")
    vo = d.get("vo")
    return {"music": "on" if isinstance(m, dict) and m.get("file") else "off", "voice_track": bool(isinstance(vo, list) and vo)}


def probe_composition(hf: Path) -> dict | None:
    """The root composition of hf/index.html: {duration_s, width, height, aspect, audio: None}; None when it cannot be read."""
    try:
        text = (hf / "index.html").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for tag in re.finditer(r"<[a-zA-Z][^>]*\bdata-composition-id\b[^>]*>", text, re.S):
        attrs = dict(re.findall(r'([\w-]+)\s*=\s*"([^"]*)"', tag.group(0)))
        try:
            dur, w, h = float(attrs["data-duration"]), int(float(attrs["data-width"])), int(float(attrs["data-height"]))
        except (KeyError, ValueError):
            continue
        return {"duration_s": round(dur, 3), "width": w, "height": h, "aspect": aspect_name(w, h), "audio": None}
    return None


def measure(project: Path, render: Path | None, storyboard: Path | None, cues: Path) -> dict:
    """Everything check can see. A None value = not measurable here. render=None reads the composition instead of a file."""
    pr = probe(render) if render else probe_composition(project / "hf")
    beats = None
    if storyboard and storyboard.is_file():
        try:
            beats = storyboard_beats(json.loads(storyboard.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            beats = None
    cu = measure_cues(cues)
    return {"duration_s": pr["duration_s"] if pr else None, "aspect": pr["aspect"] if pr else None, "audio": pr["audio"] if pr else None,
            "captions": measure_captions(project / "hf"), "music": cu["music"], "voice_track": cu["voice_track"], "beats": beats}


# ---------------------------------------------------------------- comparing


def _row(field, promised, built, ok, by_field, original, note=""):
    if built is None:
        return {"field": field, "promised": promised, "built": None, "state": "not_measured",
                "note": note or "cannot be measured here: confirm it by eye or ear before presenting"}
    if not ok:
        return {"field": field, "promised": promised, "built": built, "state": "unasked_change", "note": note}
    if field in by_field and promised != original:
        c = by_field[field]
        return {"field": field, "promised": promised, "built": built, "state": "asked", "asked": c["asked"], "at": c["at"]}
    return {"field": field, "promised": promised, "built": built, "state": "kept", **({"note": note} if note else {})}


def compare(doc: dict, m: dict) -> dict:
    """Pure: promise.json + measurements -> {status, rows, problems}. status: kept | unasked_change."""
    eff, by_field, problems = effective(doc)
    orig = flat_promise(doc)
    tol = float(doc["promise"].get("tolerance_s", 0.5))
    rows = []
    d = m.get("duration_s")
    rows.append(_row("duration_s", eff["duration_s"], d, d is not None and abs(d - float(eff["duration_s"])) <= tol, by_field, orig["duration_s"],
                     f"tolerance {tol:g} s"))
    rows.append(_row("aspect", eff["aspect"], m.get("aspect"), m.get("aspect") == eff["aspect"], by_field, orig["aspect"]))

    cap, mc = eff["captions"], m.get("captions")
    note = ""
    if mc is None:
        ok = False
    elif cap == "off":
        ok = mc == "off"
    elif mc == "off":
        ok = False
    elif mc == "on" or (mc and LANG_SCRIPT.get(cap.split("-")[0]) is None):
        ok, note = True, "captions are on; their language could not be measured (no hf/data/captions.json, or an unlisted language): check it on a frame"
    else:
        ok = mc == f"script:{LANG_SCRIPT[cap.split('-')[0]]}"
        if not ok:
            note = f"the caption text is in {str(mc).split(':')[-1]} script, not the script of '{cap}'"
    rows.append(_row("captions", cap, mc, ok, by_field, orig["captions"], note))

    rows.append(_row("music", eff["music"], m.get("music"), m.get("music") == eff["music"], by_field, orig["music"],
                     "" if m.get("music") is not None else "no hf/cues.json: listen to the draft"))
    vt = m.get("voice_track")
    want_track = eff["voice"] in ("vo", "tts")
    built_v = None if vt is None else ("a separate voice track" if vt else "no separate voice track")
    rows.append(_row("voice", eff["voice"], built_v, vt is not None and vt == want_track, by_field, orig["voice"],
                     "recorded vs synthetic voice is not measurable: confirm by ear" if vt is not None and want_track else ""))
    if eff["voice"] != "none" or eff["music"] == "on":
        a = m.get("audio")
        rows.append(_row("audio", "present", a, a == "present", by_field, "present", "the draft file has no audio stream" if a == "none" else ""))

    if orig.get("beats.order"):
        built_beats = m.get("beats")
        if built_beats is None:
            rows.append(_row("beats", orig["beats.order"], None, False, by_field, orig["beats.order"],
                             "no current storyboard: compare each built beat's still with its board frame"))
        else:
            bmap = {b["id"]: b for b in built_beats}
            promised_ids = [k.split(".")[1] for k in eff if re.match(r"^beats\.[^.]+$", k) and k != "beats.order"]
            for bid in promised_ids:
                state = eff[f"beats.{bid}"]
                f = f"beats.{bid}"
                if state == "dropped":
                    rows.append(_row(f, "dropped", "dropped" if bid not in bmap else "present", bid not in bmap, by_field, orig.get(f)))
                    continue
                if bid not in bmap:
                    rows.append(_row(f, state, "missing", False, by_field, orig.get(f), "the beat is gone from the storyboard"))
                    continue
                if state == "added":
                    rows.append(_row(f, "added", "added", True, by_field, orig.get(f)))
                    continue
                for part in ("roll", "source", "shot"):
                    k = f"{f}.{part}"
                    if part == "shot" and k not in eff:
                        continue
                    have = bmap[bid].get(part, "unset")
                    rows.append(_row(k, eff.get(k), have, have == eff.get(k), by_field, orig.get(k)))
            for b in built_beats:
                if f"beats.{b['id']}" not in eff:
                    rows.append(_row(f"beats.{b['id']}", "absent", "added", False, by_field, None, "a beat nobody approved"))
            order = [x for x in str(eff.get("beats.order", "")).split(",") if x]
            common = [x for x in order if x in bmap and eff.get(f"beats.{x}") not in ("dropped", "added")]
            built_order = [b["id"] for b in built_beats if b["id"] in common]
            orig_order = [x for x in str(orig["beats.order"]).split(",") if x in common]
            rows.append(_row("beats.order", ",".join(common), ",".join(built_order), common == built_order, by_field, ",".join(orig_order)))
    unasked = [r for r in rows if r["state"] == "unasked_change"]
    return {"status": "unasked_change" if unasked else "kept", "rows": rows, "problems": problems,
            "not_measured": [r["field"] for r in rows if r["state"] == "not_measured"]}


# ---------------------------------------------------------------- commands


def _opts(argv: list[str], names: dict) -> dict:
    out, i = dict(names), 0
    while i < len(argv):
        a = argv[i]
        if a == "--relock":
            out["--relock"] = True
            i += 1
        elif a in names and i + 1 < len(argv):
            out[a] = argv[i + 1]
            i += 2
        else:
            raise SystemExit(f"unknown or incomplete option: {a}")
    return out


def cmd_lock(project: Path, argv: list[str]) -> int:
    o = _opts(argv, {"--duration": None, "--aspect": None, "--captions": None, "--music": None, "--voice": None, "--storyboard": None,
                     "--tolerance-s": "0.5", "--relock": False})
    sb_path = Path(o["--storyboard"]) if o["--storyboard"] else project / "_work" / "storyboard" / "storyboard.json"
    spec, beats = {}, []
    if o["--storyboard"] or sb_path.is_file():
        try:
            spec = json.loads(sb_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _out({"status": "refused", "errors": [f"cannot read the storyboard {sb_path}: {exc}"]})
            return 2
        beats = storyboard_beats(spec)
    try:
        duration = float(o["--duration"]) if o["--duration"] else (max((b["end"] for b in beats if isinstance(b["end"], (int, float))), default=None))
        tol = float(o["--tolerance-s"])
    except ValueError:
        _out({"status": "refused", "errors": ["--duration and --tolerance-s are numbers"]})
        return 2
    aspect = o["--aspect"] or spec.get("aspect")
    doc, errors = build_promise(project.name, duration, aspect, o["--captions"], o["--music"], o["--voice"], tol, beats,
                                approval_lines(project / "hf" / "CHANGELOG.md"))
    target = project / "_work" / "promise.json"
    if not errors and target.is_file() and not o["--relock"]:
        errors.append(f"{target} exists: a promise is locked once per approval; pass --relock only after a new approval")
    if errors:
        _out({"status": "refused", "errors": errors})
        return 2
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        os.replace(target, target.with_name(f"promise.{stamp}.json"))
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _out({"status": "locked", "promise": str(target), "promised": doc["promise"] | {"beats": len(doc["promise"]["beats"])},
          "next": "any planned change (a failed generation becoming a still, music dropped, a beat swapped, the length moved) is asked "
                  "first, then recorded with `record`; run `check` before the draft render"})
    return 0


def load_promise(project: Path) -> dict | None:
    p = project / "_work" / "promise.json"
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) and doc.get("schema") == SCHEMA and isinstance(doc.get("promise"), dict) else None


def normalise_to(field: str, to: str) -> tuple[object, str | None]:
    t = to.strip()
    if field == "duration_s":
        try:
            v = float(t)
        except ValueError:
            return None, "duration_s: a number of seconds"
        return (round(v, 3), None) if v > 0 else (None, "duration_s: > 0")
    if field == "aspect":
        return (t, None) if ASPECT_RE.match(t) else (None, "aspect: W:H")
    if field == "captions":
        t = t.lower()
        return (t, None) if t == "off" or LANG_RE.match(t) else (None, "captions: off or a language code")
    if field == "music":
        return (t.lower(), None) if t.lower() in ("on", "off") else (None, "music: on or off")
    if field == "voice":
        return (t.lower(), None) if t.lower() in VOICES else (None, f"voice: one of {list(VOICES)}")
    if field == "beats.order":
        ids = [x.strip() for x in t.split(",") if x.strip()]
        return (",".join(ids), None) if ids else (None, "beats.order: ids joined by commas")
    if field.endswith(".roll"):
        return (t.upper(), None) if t.upper() in ROLLS else (None, "roll: A, B or G")
    if field.endswith(".shot"):
        return (t.lower(), None) if t.lower() in SHOTS + ("unset",) else (None, f"shot: one of {list(SHOTS)} or unset")
    if field.endswith(".source"):
        return (t.lower(), None) if t.lower() in SOURCES else (None, f"source: one of {list(SOURCES)}")
    return (t.lower(), None) if t.lower() in ("dropped", "added") else (None, "beats.<id>: dropped or added")


def cmd_record(project: Path, argv: list[str]) -> int:
    o = _opts(argv, {"--field": None, "--to": None, "--asked": None})
    doc = load_promise(project)
    errors = []
    if doc is None:
        errors.append(f"no valid {project / '_work' / 'promise.json'}: lock the promise first")
    f = o["--field"] or ""
    if not FIELD_RE.match(f):
        errors.append("--field: duration_s, aspect, captions, music, voice, beats.<id>, beats.<id>.source, beats.<id>.roll, beats.<id>.shot or beats.order")
    if not o["--asked"] or len(o["--asked"].strip()) < 2:
        errors.append("--asked: the user's own words agreeing to this change (ask first; an unasked change is not recorded)")
    to, why = (None, "--to is required") if o["--to"] is None else normalise_to(f, o["--to"]) if FIELD_RE.match(f) else (None, None)
    if why:
        errors.append(why)
    if errors:
        _out({"status": "refused", "errors": errors})
        return 2
    eff, _, _ = effective(doc)
    entry = {"field": f, "from": eff.get(f), "to": to, "asked": o["--asked"].strip(), "at": now_utc()}
    doc.setdefault("changes", []).append(entry)
    p = project / "_work" / "promise.json"
    tmp = p.with_suffix(".json.part")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    _out({"status": "recorded", "change": entry})
    return 0


def cmd_check(project: Path, argv: list[str]) -> int:
    o = _opts(argv, {"--render": None, "--storyboard": None, "--cues": None})
    doc = load_promise(project)
    if doc is None:
        _out({"status": "refused", "errors": [f"no valid {project / '_work' / 'promise.json'}: lock it after PROMPT_APPROVED (and STORYBOARD APPROVED)"]})
        return 2
    if o["--render"] and not Path(o["--render"]).is_file():
        _out({"status": "refused", "errors": [f"--render: no file at {o['--render']}"]})
        return 2
    sb = Path(o["--storyboard"]) if o["--storyboard"] else project / "_work" / "storyboard" / "storyboard.json"
    cues = Path(o["--cues"]) if o["--cues"] else project / "hf" / "cues.json"
    res = compare(doc, measure(project, Path(o["--render"]) if o["--render"] else None, sb, cues))
    res["measured_from"] = o["--render"] or "the composition (hf/index.html); run again with --render on the draft before presenting"
    unasked = [r for r in res["rows"] if r["state"] == "unasked_change"]
    res["next"] = ("ask the user about each unasked change in one message; on a yes run `record` with their words, on a no rebuild to the "
                   "promise; then check again" if unasked else
                   "no unasked change; confirm each not_measured row by eye or ear, and say the asked changes in the presentation")
    _out(res)
    return 1 if unasked else 0


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return subprocess.call([sys.executable, str(Path(__file__).with_name("test_promise_check.py"))])
    if len(argv) < 2 or argv[0] not in ("lock", "record", "check") or argv[1].startswith("-"):
        print(__doc__)
        return 2
    project = Path(argv[1])
    if not project.is_dir():
        _out({"status": "refused", "errors": [f"no project folder at {project}"]})
        return 2
    try:
        return {"lock": cmd_lock, "record": cmd_record, "check": cmd_check}[argv[0]](project, argv[2:])
    except SystemExit as exc:
        _out({"status": "refused", "errors": [str(exc)]})
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""style_card_check.py - validate a Style DNA card, the three application options and the rights ledger.

Fail closed: a card whose numbers cannot be tied to a measured analysis folder, an options file whose
three options are not really different, or a rights ledger that lets a reference's assets or an
unlicensed song into the plan never passes.

Usage:
  python style_card_check.py card    <style_dna.json>  [--root DIR]
  python style_card_check.py options <options.json>    --card <style_dna.json>
  python style_card_check.py rights  <rights.json>
  python style_card_check.py all     <style_dir> [--root DIR]     (style_dna.json + options.json + rights.json)
  python style_card_check.py --self-check

Files (schema_version 1.0.0; field tables in references/style-dna-card.md and references/options-and-mapping.md):
  style_dna.json  reference{id, analysis_dir, analysis_sha256, pinned_segment, role}, rows[], beat_map[]
  options.json    options[3]: Faithful | Elevated | Twist, each with decisions{}, cost, risk, ...
  rights.json     context, reference{}, assets_taken_from_reference[], music{}, fonts[], distribution{}

--root is the project root that `analysis_dir` and evidence paths are relative to (default: current directory).
Layout: the analysis at <project>/_work/analysis/<ref-id>/, this skill's files at <project>/_work/style/<ref-id>/.
Exit codes: 0 PASS | 1 FAIL | 2 INSUFFICIENT_EVIDENCE (file or analysis folder missing, hash not verifiable).
Checks structure, provenance and consistency only; it cannot judge whether the style reading is right,
and a PASS is not a licence to reuse anything. Stdlib only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path

VERSION = "0.1.0"
SCHEMA = "1.0.0"
REQUIRED_DIMS = ["pacing", "hook", "transitions", "camera", "type", "colour", "broll", "layering", "sound", "endcard", "safezone"]
CONF = {"H", "M", "L"}
TOL_MODES = {"pct", "abs", "exact", "categorical", "informational"}
FUNCTIONS = {"hook", "pain", "turn", "proof", "payoff", "cta", "other"}
TWIST_AXES = {"world", "medium", "pov", "structure"}
OPTION_NAMES = ["Faithful", "Elevated", "Twist"]
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
FLAT_STD_MAX = 12.0
MIN_DECISION_KEYS = 6
MIN_DIFF_DECISIONS = 3
OK_LICENCES = {"CC0", "CC-BY", "OFL", "Mixkit", "Pixabay", "Pexels", "paid-subscription", "owned", "synthesised"}
BAD_LICENCES = {"unknown", "CC-BY-NC", "", None}
CONTEXTS = {"client_ad", "client_organic", "own_organic", "study"}
FONT_METRICS = {"font", "typeface", "font_family"}


def _no_const(n):
    raise ValueError("non-standard JSON constant: " + n)


def _no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate JSON key: " + k)
        out[k] = v
    return out


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"), parse_constant=_no_const, object_pairs_hook=_no_dupes)


def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


class R:
    def __init__(self, what):
        self.what, self.items = what, []

    def add(self, sev, code, msg):
        self.items.append({"severity": sev, "code": code, "message": msg})

    def result(self):
        fails = [i for i in self.items if i["severity"] == "fail"]
        insuff = [i for i in self.items if i["severity"] == "insufficient"]
        status = "FAIL" if fails else ("INSUFFICIENT_EVIDENCE" if insuff else "PASS")
        return {"tool": "style_card_check", "version": VERSION, "checked": self.what, "status": status,
                "counts": {"fail": len(fails), "insufficient": len(insuff), "warn": len([i for i in self.items if i["severity"] == "warn"])},
                "findings": self.items}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def resolve(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


# --------------------------------------------------------------------------- card
def check_card(card, root: Path):
    r = R("style_dna.json")
    if not isinstance(card, dict) or card.get("schema_version") != SCHEMA:
        r.add("fail", "SCHEMA", f"schema_version must be {SCHEMA}")
        return r, None
    ref = card.get("reference") or {}
    for k in ("id", "analysis_dir", "analysis_sha256", "pinned_segment", "role"):
        if not ref.get(k):
            r.add("fail", "REF_FIELD", f"reference.{k} missing")
    seg = ref.get("pinned_segment") or {}
    if not (isnum(seg.get("start_s")) and isnum(seg.get("end_s")) and seg["start_s"] < seg["end_s"] and seg.get("look")):
        r.add("fail", "PINNED_SEGMENT", "pinned_segment needs start_s < end_s and `look`: which time range IS the style (before/after vs final look, intro vs body)")
    if seg.get("pinned_by") != "user":
        r.add("fail", "PINNED_BY", "pinned_segment.pinned_by must be 'user': the user chose which look is the style (one past project copied the wrong look and lost a round)")
    if r.items:
        return r, None
    adir = root / ref["analysis_dir"]
    mp, ap = adir / "measurements.json", adir / "audio.json"
    meas = audio = None
    if not mp.is_file():
        r.add("insufficient", "NO_ANALYSIS", f"{mp} not found: numbers must come from a video-analysis folder, not from looking (run video-analysis first)")
    else:
        if sha256_file(mp) != ref["analysis_sha256"]:
            r.add("fail", "ANALYSIS_HASH", "analysis_sha256 differs from measurements.json: the card was written against another analysis")
        try:
            meas = load(mp)
            if seg["end_s"] > float(meas["input"]["duration_s"]) + 0.05:
                r.add("fail", "SEGMENT_RANGE", "pinned segment ends after the reference's duration")
            if not isinstance(meas.get("review"), dict):
                r.add("fail", "ANALYSIS_UNREVIEWED", "the analysis has no `review` block: its sheets were never read, so its counts are unverified")
        except (ValueError, KeyError, TypeError) as e:
            r.add("fail", "ANALYSIS_BAD", f"measurements.json unreadable: {e}")
    if ap.is_file():
        try:
            audio = load(ap)
        except ValueError as e:
            r.add("fail", "ANALYSIS_BAD", f"audio.json unreadable: {e}")
    rows = card.get("rows")
    if not isinstance(rows, list) or not rows:
        r.add("fail", "NO_ROWS", "card has no rows (an empty card never passes)")
        return r, None
    ids, dims = set(), set()
    for row in rows:
        rid = row.get("id")
        if not rid or rid in ids:
            r.add("fail", "ROW_ID", f"row id missing or duplicate: {rid!r}")
            continue
        ids.add(rid)
        dim = row.get("dimension")
        if dim not in REQUIRED_DIMS:
            r.add("fail", "ROW_DIM", f"{rid}: dimension must be one of {REQUIRED_DIMS}")
            continue
        dims.add(dim)
        if row.get("value") is None:
            if not row.get("na_reason"):
                r.add("fail", "ROW_VALUE", f"{rid}: value null needs na_reason (dimension does not apply) - an unfilled dimension is never invented")
            continue
        for k in ("metric", "seen_at", "method"):
            if not row.get(k):
                r.add("fail", "ROW_FIELD", f"{rid}: {k} missing (every row: number, where seen, how measured, confidence)")
        if isnum(row["value"]) and not row.get("unit"):
            r.add("fail", "ROW_UNIT", f"{rid}: numeric value needs a unit")
        conf = row.get("confidence")
        if conf not in CONF:
            r.add("fail", "ROW_CONF", f"{rid}: confidence must be H, M or L")
        if conf == "H" and not row.get("confirmed_by"):
            r.add("fail", "ROW_H", f"{rid}: H = tool measurement AND an independent confirmation (frame zoom, second method); list it in confirmed_by")
        # numbers from the analysis, not from eyeballing
        sk = row.get("source_key")
        if sk:
            src, _, path = sk.partition(":")
            base = {"measurements": meas, "audio": audio}.get(src)
            if base is None:
                r.add("insufficient", "SOURCE_MISSING", f"{rid}: source_key {sk} cannot be resolved (analysis file missing)")
            else:
                got = resolve(base, path)
                if got is None:
                    r.add("fail", "SOURCE_KEY", f"{rid}: {sk} not found in the analysis")
                elif isnum(got) and isnum(row["value"]) and abs(got - row["value"]) > max(1e-6, 0.005 * abs(got)):
                    r.add("fail", "VALUE_NOT_MEASURED", f"{rid}: value {row['value']} differs from the analysis ({got}); numbers come from the measurements, not from the eye (record a correction there instead)")
                elif not isnum(got) and got != row["value"]:
                    r.add("fail", "VALUE_NOT_MEASURED", f"{rid}: value differs from the analysis")
        elif conf != "L" and not row.get("evidence"):
            r.add("fail", "ROW_EVIDENCE", f"{rid}: no source_key and no evidence path (sheet, zoom, px_measure output)")
        for ev in row.get("evidence") or []:
            if isinstance(ev, str) and not ev.startswith("_work/analysis/") and "#" not in ev and not (root / ev).exists():
                r.add("insufficient", "EVIDENCE_MISSING", f"{rid}: evidence file {ev} not found")
        # colour hexes only from full-resolution flat samples
        is_hex_value = isinstance(row["value"], str) and HEX_RE.match(row["value"]) is not None
        if "hex" in row["metric"].lower() or is_hex_value:
            if row.get("source") != "fullres_png" or not (isnum(row.get("flat_fill_std")) and row["flat_fill_std"] <= FLAT_STD_MAX):
                r.add("fail", "HEX_SOURCE", f"{rid}: hex colours come from a full-resolution frame sampled on a flat fill (source=fullres_png, flat_fill_std <= {FLAT_STD_MAX}); contact sheets are downscaled")
        # fonts: nearest match, never an identity claim
        if row["metric"].lower() in FONT_METRICS:
            if conf != "L" or row.get("nearest_match") is not True:
                r.add("fail", "FONT_IDENTITY", f"{rid}: a font is a NEAREST MATCH with confidence L (nearest_match: true); never claim the exact identity")
            if not row.get("licence"):
                r.add("fail", "FONT_LICENCE", f"{rid}: record the licence of the nearest match (a paid font is replaced, not copied)")
        # tolerance
        tol = row.get("tolerance") or {}
        mode = tol.get("mode")
        if mode not in TOL_MODES:
            r.add("fail", "TOL_MODE", f"{rid}: tolerance.mode must be one of {sorted(TOL_MODES)}")
        elif mode == "pct":
            if not isnum(row["value"]) or not isnum(tol.get("value")) or tol["value"] <= 0:
                r.add("fail", "TOL_PCT", f"{rid}: pct tolerance needs a numeric value and a positive percentage")
            elif abs(row["value"]) < 1 and not (isnum(tol.get("abs_floor")) and tol["abs_floor"] > 0):
                r.add("fail", "TOL_NEAR_ZERO", f"{rid}: +/-% is meaningless near zero: add abs_floor > 0 (T16: a blanket 20 % fails on near-zero values)")
        elif mode == "abs" and not (isnum(tol.get("value")) and tol["value"] >= 0):
            r.add("fail", "TOL_ABS", f"{rid}: abs tolerance needs a non-negative number")
        elif mode == "informational" and conf == "H":
            r.add("warn", "TOL_INFO", f"{rid}: H-confidence row marked informational: is it really not a target?")
        if conf == "L" and mode not in ("informational", "categorical"):
            r.add("fail", "TOL_LOW_CONF", f"{rid}: an L (inferred) row cannot be a numeric acceptance target; use informational/categorical")
        dv = row.get("deviate")
        if dv is not None and not (isinstance(dv, str) and dv.strip()):
            r.add("fail", "DEVIATE", f"{rid}: deviate must be null or a written reason")
    missing = [d for d in REQUIRED_DIMS if d not in dims]
    if missing:
        r.add("fail", "DIMENSIONS", f"dimensions with no row (give a row or an na_reason): {missing}")
    for b in card.get("beat_map") or []:
        if b.get("function") not in FUNCTIONS or not b.get("mapped_device"):
            r.add("fail", "BEAT_MAP", "beat_map entries map by FUNCTION (hook, pain, turn, proof, payoff, cta) with a mapped_device, never by seconds alone")
            break
    return r, {"row_ids": ids, "rows": {x["id"]: x for x in rows if x.get("id")}}


# --------------------------------------------------------------------------- options
def _norm(s):
    return re.sub(r"\s+", " ", str(s).strip().lower())


def check_options(opts, card_info):
    r = R("options.json")
    if not isinstance(opts, dict) or opts.get("schema_version") != SCHEMA:
        r.add("fail", "SCHEMA", f"schema_version must be {SCHEMA}")
        return r
    lst = opts.get("options")
    if not isinstance(lst, list) or [o.get("name") for o in lst] != OPTION_NAMES:
        r.add("fail", "THREE_OPTIONS", f"exactly three options in the order {OPTION_NAMES} (a per-beat mix is a pick table made AFTER these three)")
        return r
    rows = (card_info or {}).get("rows", {})
    keysets = []
    rec = 0
    for o in lst:
        n = o["name"]
        dec = o.get("decisions")
        if not isinstance(dec, dict) or len(dec) < MIN_DECISION_KEYS or any(not str(v).strip() for v in dec.values()):
            r.add("fail", "DECISIONS", f"{n}: decisions must hold >= {MIN_DECISION_KEYS} non-empty decisions (pacing, hook, transitions, type, camera, palette, sound, broll, structure...)")
            continue
        keysets.append(set(dec))
        for k in ("cost", "risk", "pitch"):
            if not str(o.get(k, "")).strip():
                r.add("fail", "COST_RISK", f"{n}: {k} missing (what could fail, render time, any paid step with a dated estimate)")
        if o.get("keeps_ledger") is not True:
            r.add("fail", "LEDGER", f"{n}: keeps_ledger must be true: every option obeys the locked ledger lines (length, structure, ratios, filename)")
        rec += 1 if o.get("recommended") else 0
        for rid in o.get("borrowed_devices") or []:
            if rows and rid not in rows:
                r.add("fail", "UNKNOWN_ROW", f"{n}: borrowed device {rid} is not a DNA row")
    if r.items:
        return r
    if len(set(map(frozenset, keysets))) != 1:
        r.add("fail", "DECISION_KEYS", "all three options must decide the SAME set of decisions so they can be compared")
    if rec != 1:
        r.add("fail", "RECOMMEND", "exactly one option is recommended, with recommend_reason on it")
    # pairwise diversity
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = lst[i]["decisions"], lst[j]["decisions"]
            diff = [k for k in a if k in b and _norm(a[k]) != _norm(b[k])]
            if len(diff) < MIN_DIFF_DECISIONS:
                r.add("fail", "OPTIONS_NOT_DIFFERENT", f"{lst[i]['name']} and {lst[j]['name']} differ in {len(diff)} decisions (< {MIN_DIFF_DECISIONS}): rewrite the duplicate option")
    faithful, elevated, twist = lst
    if faithful.get("deviate_rows"):
        r.add("fail", "FAITHFUL_DEVIATES", "Faithful = every DNA row within tolerance: it cannot list deviate_rows")
    ups = elevated.get("upgrades")
    if not isinstance(ups, list) or not ups:
        r.add("fail", "ELEVATED_UPGRADES", "Elevated needs upgrades[], each naming the DNA row it upgrades and why")
    else:
        for u in ups:
            if not u.get("why") or not u.get("upgrade") or (rows and u.get("device_row") not in rows):
                r.add("fail", "ELEVATED_UPGRADES", "each upgrade needs device_row (a DNA row id), upgrade and why")
                break
    kd = twist.get("kept_devices")
    if not isinstance(kd, list) or not (1 <= len(kd) <= 2) or (rows and any(k not in rows for k in kd)):
        r.add("fail", "TWIST_KEEPS", "Twist keeps 1-2 signature devices (DNA row ids)")
    if twist.get("changed_axis") not in TWIST_AXES:
        r.add("fail", "TWIST_AXIS", f"Twist changes exactly one axis: {sorted(TWIST_AXES)}")
    for o in lst:
        if o.get("recommended") and not str(o.get("recommend_reason", "")).strip():
            r.add("fail", "RECOMMEND", "the recommended option needs recommend_reason")
    return r


# --------------------------------------------------------------------------- rights
def check_rights(rj):
    r = R("rights.json")
    if not isinstance(rj, dict) or rj.get("schema_version") != SCHEMA:
        r.add("fail", "SCHEMA", f"schema_version must be {SCHEMA}")
        return r
    ctx = rj.get("context")
    if ctx not in CONTEXTS:
        r.add("fail", "CONTEXT", f"context must be one of {sorted(CONTEXTS)}")
    ref = rj.get("reference") or {}
    for k in ("url_or_file", "acquisition", "licence", "use"):
        if not ref.get(k):
            r.add("fail", "REF", f"reference.{k} missing (rights ledger per reference: source, acquisition authority, licence, use)")
    if ref.get("use") not in (None, "analysis-only"):
        r.add("fail", "REF_USE", "a reference is used for analysis only: grammar, never assets")
    if rj.get("assets_taken_from_reference"):
        r.add("fail", "ASSETS_FROM_REFERENCE", "assets_taken_from_reference must be empty: no frames, footage, VO, music, logos, characters or paid fonts")
    for flag, label in (("reference_logos_used", "logos"), ):
        if (rj.get("logos_brands") or {}).get(flag) is not False:
            r.add("fail", "LOGOS", f"reference {label} must not be used (logos_brands.{flag} must be false)")
    if (rj.get("people_likeness") or {}).get("reference_people_used") is not False:
        r.add("fail", "LIKENESS", "the reference's people, voices or characters must not be used (people_likeness.reference_people_used must be false)")
    dist = rj.get("distribution") or {}
    if dist.get("reference_in_student_repo") is not False or dist.get("analysis_reports_shipped") is not False:
        r.add("fail", "DISTRIBUTION", "reference clips and style-analysis reports of third-party videos never ship in a repo or course package")
    mu = rj.get("music") or {}
    song = mu.get("reference_song") or {}
    if song.get("status") not in ("matched", "unidentified", "none"):
        r.add("fail", "SONG", "music.reference_song.status must be matched | unidentified | none")
    if song.get("status") in ("matched", "unidentified") and song.get("sync_licence") != "not_established":
        r.add("fail", "SYNC", "the reference's song: sync_licence must be 'not_established' (a match or a trending sound is no licence)")
    rep = mu.get("replacement") or {}
    if song.get("status") in ("matched", "unidentified"):
        if not rep.get("file") or rep.get("licence") in BAD_LICENCES or rep.get("licence") not in OK_LICENCES:
            r.add("fail", "MUSIC_REPLACEMENT", f"a replacement track with a licence in {sorted(OK_LICENCES)} is required (unknown = not in client work)")
        elif ctx in ("client_ad",) and rep.get("ads_allowed") is not True:
            r.add("fail", "MUSIC_ADS", "client ad: the replacement's licence row must allow ads in the placement and territory (ads_allowed: true)")
        if not rep.get("source_md"):
            r.add("fail", "MUSIC_SOURCE", "replacement needs a SOURCES.md row pointer (source_md)")
    for fnt in rj.get("fonts") or []:
        if fnt.get("licence") in BAD_LICENCES or not fnt.get("file"):
            r.add("fail", "FONT", "each font used needs a licence and a file in hf/fonts (the reference's paid font is replaced by its nearest licensed match)")
    return r


# --------------------------------------------------------------------------- orchestration
def run_all(style_dir: Path, root: Path):
    reports = []
    card_info = None
    cp = style_dir / "style_dna.json"
    for name in ("style_dna.json", "options.json", "rights.json"):
        if not (style_dir / name).is_file():
            r = R(name)
            r.add("insufficient", "FILE_MISSING", f"{name} not found in {style_dir}")
            reports.append(r)
    if cp.is_file():
        try:
            r, card_info = check_card(load(cp), root)
        except ValueError as e:
            r = R("style_dna.json")
            r.add("fail", "BAD_JSON", str(e))
        reports.append(r)
    op, rp = style_dir / "options.json", style_dir / "rights.json"
    if op.is_file():
        try:
            reports.append(check_options(load(op), card_info))
        except ValueError as e:
            r = R("options.json")
            r.add("fail", "BAD_JSON", str(e))
            reports.append(r)
    if rp.is_file():
        try:
            reports.append(check_rights(load(rp)))
        except ValueError as e:
            r = R("rights.json")
            r.add("fail", "BAD_JSON", str(e))
            reports.append(r)
    return reports


def combine(reports):
    results = [r.result() for r in reports]
    if any(x["status"] == "FAIL" for x in results):
        st = "FAIL"
    elif any(x["status"] == "INSUFFICIENT_EVIDENCE" for x in results):
        st = "INSUFFICIENT_EVIDENCE"
    else:
        st = "PASS"
    return {"tool": "style_card_check", "version": VERSION, "status": st, "files": results,
            "limits": ["structure, provenance and consistency only", "a PASS is not a licence and not proof the style was read correctly"]}, {"PASS": 0, "FAIL": 1}.get(st, 2)


# --------------------------------------------------------------------------- self-check
def _fixture(td: Path):
    adir = td / "_work" / "analysis" / "ref-abc123"
    adir.mkdir(parents=True)
    meas = {"input": {"duration_s": 30.0}, "pacing": {"cuts_per_min": 36.0, "median_shot_s": 1.1}, "review": {"reviewed_by": "model"}}
    (adir / "measurements.json").write_text(json.dumps(meas), encoding="utf-8")
    (adir / "audio.json").write_text(json.dumps({"loudness": {"integrated_lufs": -14.2}, "music": {"tempo_bpm": 128.0}}), encoding="utf-8")
    h = sha256_file(adir / "measurements.json")

    def row(i, dim, metric, value, **kw):
        d = {"id": i, "dimension": dim, "metric": metric, "value": value, "unit": kw.pop("unit", "s"), "seen_at": "0-30s", "method": "measurements.json",
             "confidence": "M", "tolerance": {"mode": "pct", "value": 20}}
        d.update(kw)
        return d
    rows = [
        row("R01", "pacing", "cuts_per_min", 36.0, unit="per_min", source_key="measurements:pacing.cuts_per_min", confidence="H", confirmed_by=["frame zoom 3.2 s"]),
        row("R02", "hook", "first_text_s", 0.4, evidence=["_work/analysis/ref-abc123/measurements.json#hook"], tolerance={"mode": "pct", "value": 20, "abs_floor": 0.3}),
        row("R03", "transitions", "types", "whip x6, hard x20", unit="list", tolerance={"mode": "categorical"}, evidence=["_work/analysis/ref-abc123/sheets"]),
        row("R04", "camera", "punch_in_pct", 115, unit="%", evidence=["_work/analysis/ref-abc123/zoom"]),
        row("R05", "type", "font", "rounded heavy sans", unit="text", confidence="L", nearest_match=True, licence="OFL", tolerance={"mode": "informational"}),
        row("R06", "colour", "accent_hex", "#F2C230", unit="hex", source="fullres_png", flat_fill_std=3.2, evidence=["_work/analysis/ref-abc123/px_0003.txt"], tolerance={"mode": "exact"}),
        row("R07", "broll", None, None, na_reason="speakerless promo, no B-roll layer"),
        row("R08", "layering", None, None, na_reason="no cutout"),
        row("R09", "sound", "tempo_bpm", 128.0, unit="bpm", source_key="audio:music.tempo_bpm", tolerance={"mode": "pct", "value": 8}),
        row("R10", "endcard", "duration_s", 2.5, evidence=["_work/analysis/ref-abc123/zoom"]),
        row("R11", "safezone", "key_text_bottom_y", 1180, unit="px", evidence=["_work/analysis/ref-abc123/sheets"], tolerance={"mode": "abs", "value": 40}),
    ]
    for rr in rows:
        if rr["value"] is None:
            rr.pop("unit", None); rr.pop("tolerance", None); rr.pop("seen_at", None); rr.pop("method", None); rr.pop("confidence", None)
            rr["metric"] = "n/a"
    card = {"schema_version": SCHEMA, "reference": {"id": "yt-abc123", "analysis_dir": "_work/analysis/ref-abc123", "analysis_sha256": h,
            "pinned_segment": {"start_s": 0.0, "end_s": 28.0, "look": "final look", "pinned_by": "user"}, "role": "all"},
            "rows": rows, "beat_map": [{"ref_beat": "0-1.4", "function": "hook", "mapped_device": "number slam on the user's number"}]}
    dec = lambda **kw: {"pacing": "36/min", "hook": "offer first", "transitions": "whips", "type": "rounded heavy", "camera": "115% punch", "palette": "ref accent", "sound": "128 bpm bed"} | kw
    opts = {"schema_version": SCHEMA, "options": [
        {"name": "Faithful", "pitch": "closest translation", "decisions": dec(), "cost": "no extra", "risk": "looks like a copy", "keeps_ledger": True, "borrowed_devices": ["R01", "R03"], "deviate_rows": []},
        {"name": "Elevated", "pitch": "grammar + upgrades", "decisions": dec(pacing="36/min + 3 breaths", transitions="whips + 3D match cut", camera="115% punch + depth push"), "cost": "+1 3D beat", "risk": "3D render time", "keeps_ledger": True, "recommended": True,
         "recommend_reason": "premium bar", "upgrades": [{"device_row": "R03", "upgrade": "3D match cut", "why": "meaning of the offer"}], "borrowed_devices": ["R01"]},
        {"name": "Twist", "pitch": "one axis changed", "decisions": dec(hook="pain question", palette="duotone", sound="no bed, foley only", transitions="hard cuts only"), "cost": "ask user", "risk": "may miss the brief", "keeps_ledger": True,
         "kept_devices": ["R01"], "changed_axis": "world", "borrowed_devices": ["R01"]}]}
    rights = {"schema_version": SCHEMA, "context": "client_ad", "reference": {"url_or_file": "user-supplied file", "acquisition": "user-supplied", "licence": "unknown", "use": "analysis-only", "private": True},
              "assets_taken_from_reference": [], "music": {"reference_song": {"status": "matched", "title": "T", "sync_licence": "not_established"},
              "replacement": {"file": "hf/assets/bed.wav", "source_md": "hf/SOURCES.md#bed", "licence": "CC0", "ads_allowed": True}},
              "fonts": [{"reference_font_nearest": "Rubik", "licence": "OFL", "file": "hf/fonts/Rubik.woff2"}],
              "logos_brands": {"reference_logos_used": False, "client_brand_used": True}, "people_likeness": {"reference_people_used": False},
              "distribution": {"reference_in_student_repo": False, "analysis_reports_shipped": False}}
    sd = td / "_work" / "style" / "yt-abc123"
    sd.mkdir(parents=True)
    for n, o in (("style_dna.json", card), ("options.json", opts), ("rights.json", rights)):
        (sd / n).write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
    return sd


def _edit(sd: Path, name, fn):
    p = sd / name
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

    def codes(rep):
        return {i["code"] for r in rep for i in r.items}

    with tempfile.TemporaryDirectory(prefix="st_בדיקה ") as td:
        base = Path(td)

        def fresh(n):
            b = base / n
            b.mkdir()
            return b, _fixture(b)

        b, sd = fresh("ok")
        rep = run_all(sd, b)
        out, code = combine(rep)
        expect("valid card + options + rights PASS", code == 0)
        if code != 0:
            print(json.dumps(out, indent=1, ensure_ascii=False), file=sys.stderr)

        b, sd = fresh("val")
        _edit(sd, "style_dna.json", lambda j: j["rows"][0].update(value=50.0))
        expect("value not matching the analysis -> VALUE_NOT_MEASURED", "VALUE_NOT_MEASURED" in codes(run_all(sd, b)))

        b, sd = fresh("hash")
        _edit(sd, "style_dna.json", lambda j: j["reference"].update(analysis_sha256="0" * 64))
        expect("card tied to another analysis -> ANALYSIS_HASH", "ANALYSIS_HASH" in codes(run_all(sd, b)))

        b, sd = fresh("noan")
        (b / "_work" / "analysis" / "ref-abc123" / "measurements.json").unlink()
        out, code = combine(run_all(sd, b))
        expect("no analysis folder -> INSUFFICIENT_EVIDENCE", code == 2)

        b, sd = fresh("pin")
        _edit(sd, "style_dna.json", lambda j: j["reference"]["pinned_segment"].update(pinned_by="agent"))
        expect("segment not pinned by the user -> FAIL", "PINNED_BY" in codes(run_all(sd, b)))

        b, sd = fresh("hex")
        _edit(sd, "style_dna.json", lambda j: j["rows"][5].update(source="contact_sheet"))
        expect("hex from a contact sheet -> HEX_SOURCE", "HEX_SOURCE" in codes(run_all(sd, b)))

        b, sd = fresh("font")
        _edit(sd, "style_dna.json", lambda j: j["rows"][4].update(confidence="H", confirmed_by=["x"], nearest_match=False))
        expect("font identity claimed -> FONT_IDENTITY", "FONT_IDENTITY" in codes(run_all(sd, b)))

        b, sd = fresh("zero")
        _edit(sd, "style_dna.json", lambda j: j["rows"][1].update(tolerance={"mode": "pct", "value": 20}))
        expect("pct tolerance near zero without abs_floor -> TOL_NEAR_ZERO", "TOL_NEAR_ZERO" in codes(run_all(sd, b)))

        b, sd = fresh("dim")
        _edit(sd, "style_dna.json", lambda j: j["rows"].pop(9))
        expect("missing endcard dimension -> DIMENSIONS", "DIMENSIONS" in codes(run_all(sd, b)))

        b, sd = fresh("hnoconf")
        _edit(sd, "style_dna.json", lambda j: j["rows"][0].pop("confirmed_by"))
        expect("H without independent confirmation -> ROW_H", "ROW_H" in codes(run_all(sd, b)))

        b, sd = fresh("lowtol")
        _edit(sd, "style_dna.json", lambda j: j["rows"][4].update(tolerance={"mode": "pct", "value": 20, "abs_floor": 1}))
        expect("L row as numeric target -> TOL_LOW_CONF", "TOL_LOW_CONF" in codes(run_all(sd, b)))

        b, sd = fresh("dupopt")
        def dup(j):
            j["options"][1]["decisions"] = dict(j["options"][0]["decisions"])
        _edit(sd, "options.json", dup)
        expect("two options with the same decisions -> OPTIONS_NOT_DIFFERENT", "OPTIONS_NOT_DIFFERENT" in codes(run_all(sd, b)))

        b, sd = fresh("twist")
        _edit(sd, "options.json", lambda j: j["options"][2].update(changed_axis="colour", kept_devices=["R01", "R02", "R03"]))
        c = codes(run_all(sd, b))
        expect("Twist must keep 1-2 devices and change one named axis", "TWIST_AXIS" in c and "TWIST_KEEPS" in c)

        b, sd = fresh("two")
        _edit(sd, "options.json", lambda j: j["options"].pop())
        expect("two options -> THREE_OPTIONS", "THREE_OPTIONS" in codes(run_all(sd, b)))

        b, sd = fresh("costrisk")
        _edit(sd, "options.json", lambda j: j["options"][0].update(risk=""))
        expect("option without risk -> COST_RISK", "COST_RISK" in codes(run_all(sd, b)))

        b, sd = fresh("assets")
        _edit(sd, "rights.json", lambda j: j.update(assets_taken_from_reference=["frame_0012.png"]))
        expect("an asset taken from the reference -> FAIL", "ASSETS_FROM_REFERENCE" in codes(run_all(sd, b)))

        b, sd = fresh("song")
        _edit(sd, "rights.json", lambda j: j["music"]["reference_song"].update(sync_licence="granted"))
        expect("song match treated as licence -> SYNC", "SYNC" in codes(run_all(sd, b)))

        b, sd = fresh("unknownrep")
        _edit(sd, "rights.json", lambda j: j["music"]["replacement"].update(licence="unknown"))
        expect("replacement track with unknown licence -> MUSIC_REPLACEMENT", "MUSIC_REPLACEMENT" in codes(run_all(sd, b)))

        b, sd = fresh("adsno")
        _edit(sd, "rights.json", lambda j: j["music"]["replacement"].update(ads_allowed=False))
        expect("client ad with a track not cleared for ads -> MUSIC_ADS", "MUSIC_ADS" in codes(run_all(sd, b)))

        b, sd = fresh("dist")
        _edit(sd, "rights.json", lambda j: j["distribution"].update(analysis_reports_shipped=True))
        expect("shipping third-party analysis reports -> DISTRIBUTION", "DISTRIBUTION" in codes(run_all(sd, b)))

        b, sd = fresh("dupe")
        (sd / "rights.json").write_text('{"schema_version":"1.0.0","schema_version":"1.0.0"}')
        out, code = combine(run_all(sd, b))
        expect("duplicate JSON key -> FAIL", code == 1)

    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": ok + len(fails), "failed": fails}))
    return 0 if not fails else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Validate a Style DNA card, options and rights ledger (fail closed).")
    ap.add_argument("--self-check", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for n in ("card", "options", "rights", "all"):
        sp = sub.add_parser(n)
        sp.add_argument("path")
        sp.add_argument("--root", default=".")
        sp.add_argument("--card")
        sp.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.cmd:
        ap.print_help()
        return 2
    root = Path(a.root).resolve()
    try:
        if a.cmd == "all":
            out, code = combine(run_all(Path(a.path), root))
        elif a.cmd == "card":
            r, _ = check_card(load(Path(a.path)), root)
            out, code = combine([r])
        elif a.cmd == "options":
            info = None
            if a.card:
                _, info = check_card(load(Path(a.card)), root)
            out, code = combine([check_options(load(Path(a.path)), info)])
        else:
            out, code = combine([check_rights(load(Path(a.path)))])
    except (OSError, ValueError) as e:
        out, code = {"status": "INSUFFICIENT_EVIDENCE", "reason": str(e)}, 2
    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(out["status"])
        for f in out.get("files", []):
            print(f"  {f['checked']}: {f['status']}")
            for i in f["findings"]:
                print(f"    [{i['severity']}] {i['code']}: {i['message']}")
        if out.get("reason"):
            print("  " + out["reason"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())

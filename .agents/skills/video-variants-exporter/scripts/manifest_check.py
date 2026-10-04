#!/usr/bin/env python3
"""manifest_check.py - stale-derivative guard for multi-output (variant) deliveries.

Blocks "ready" when a delivered file was rendered from a source state that is no longer the
frozen master, when a derivative did not receive a master fix, when files in the finals folder
are not in the manifest, when a promised variant is missing, when a "shared mix" is not shared,
or when any file changed after it was recorded. Fails closed: missing evidence is never READY.

Usage:
  python manifest_check.py hash   <hf_dir> [--globs G1,G2,...] [--algo tree-sha256-v1|cat-sha256-12]
  python manifest_check.py freeze <project_dir> --hf <hf_subdir> [--round v3] [--matrix a.mp4,b.mp4,...] [--algo ...]
  python manifest_check.py change <project_dir> --id M-001 --summary "text"      (after a MASTER fix)
  python manifest_check.py stamp  <project_dir> --hf <hf_subdir>                 (BEFORE every render)
  python manifest_check.py record <project_dir> --file <final/name.mp4> --hf <hf_subdir>
          --kind master|relayout|hook|nomusic|nocaps|recut  [--route organic|ad|spark|other]
          [--mix-variant shared|nomusic|own-vo|recut] [--mix-note TEXT] [--round v3]
          [--applied-all | --applied M-001,M-002] --qa pass|fail|not_run [--qa-evidence PATH]
          [--lufs -14.0 --tp -1.3] [--width W --height H --duration-s D]
          [--name-ledger-id L12 --platform all --hook master --aspect 9x16]   (a file name the user asked for)
  python manifest_check.py check  <project_dir> [--final final] [--json]
  python manifest_check.py --self-check

Project layout it expects (relative to <project_dir>):
  hf/ , hf_9x16/ , hf_1x1/ ...   source folders (master + re-layout copies)
  final/                         finals + manifest.json ONLY
  _work/stamps/<hf>.json         pre-render stamps (written by `stamp`)

Exit codes: 0 READY | 1 BLOCKED | 2 INSUFFICIENT_EVIDENCE or usage error.
Limits (stated in every report): `from_master` and `applied_changes` are attestations made at
`stamp`/`record` time; the tool proves hashes, presence, naming and sharing, not that a layout
patch is visually correct. A viewed render and frame/audio QA are separate evidence.
Needs only the Python standard library (3.9+). ffprobe is optional (record fills width/height/duration).
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION = "0.1.0"
SCHEMA_VERSION = "1.0.0"

DEFAULT_GLOBS = [
    "index.html",
    "compositions/**/*.html",
    "cues.js",
    "cues.json",
    "assets/**/*",
    "fonts/**/*",
    "data/**/*",
]
SHARED_GLOBS = ["cues.js", "cues.json", "assets/mix.wav"]
MIX_GLOB = "assets/mix.wav"

ASPECTS = {"9x16": (1080, 1920), "4x5": (1080, 1350), "1x1": (1080, 1080), "16x9": (1920, 1080)}
KINDS = {"master", "relayout", "hook", "nomusic", "nocaps", "recut"}
MIX_VARIANTS = {"shared", "nomusic", "own-vo", "recut"}
QA_STATES = {"pass", "fail", "not_run"}
DEFAULT_PROFILE = {"lufs_target": -14.0, "lufs_tol": 0.5, "tp_max": -1.0}

NAME_RE = re.compile(
    r"^(?P<name>[a-z0-9][a-z0-9_]*?)_(?P<platform>[a-z0-9]+)_"
    r"(?P<hook>master|hook[A-Z](?:-[a-z0-9]+)*)_(?P<aspect>9x16|4x5|1x1|16x9)\.mp4$"
)
_HFID = [re.compile(rb'\sdata-hf-id="[^"]*"'), re.compile(rb"\sdata-hf-id='[^']*'")]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ALGO_TREE = "tree-sha256-v1"      # default: sha256 over (relative path, content hash) pairs; ignores Studio data-hf-id
ALGO_CAT12 = "cat-sha256-12"      # the playbook recipe: sha256 of the files concatenated in a fixed order, first 12 hex
CAT12_GLOBS = ["index.html", "compositions/*.html", "cues.js", "assets/mix.wav"]


class EvidenceError(Exception):
    """Evidence needed for a check is missing (maps to INSUFFICIENT_EVIDENCE)."""


# --------------------------------------------------------------------------- hashing
def file_digest(path: Path, normalise_html: bool = False) -> str:
    h = hashlib.sha256()
    if normalise_html and path.suffix.lower() == ".html":
        data = path.read_bytes()
        for rx in _HFID:  # Studio rewrites data-hf-id; it is not a source change
            data = rx.sub(b"", data)
        h.update(data)
        return h.hexdigest()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_hash(root: Path, globs) -> tuple:
    """sha256 over (relative path, content hash) of every file matched, sorted. Empty set = error."""
    if not root.is_dir():
        raise EvidenceError(f"source folder not found: {root}")
    files = set()
    for pattern in globs:
        for p in root.glob(pattern):
            if p.is_file():
                files.add(p.relative_to(root).as_posix())
    if not files:
        raise EvidenceError(f"no files matched {list(globs)} under {root} (an empty set never hashes as valid)")
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode("utf-8") + b"\0" + file_digest(root / rel, True).encode("ascii") + b"\n")
    return h.hexdigest(), sorted(files)


def policy_of(m) -> dict:
    pol = dict((m or {}).get("hash_policy") or {})
    algo = pol.get("algo") or ALGO_TREE
    if algo == "sha256":  # early spelling of the default
        algo = ALGO_TREE
    pol["algo"] = algo
    if not pol.get("globs"):
        pol["globs"] = CAT12_GLOBS if algo == ALGO_CAT12 else DEFAULT_GLOBS
    return pol


def compute_src(root: Path, policy: dict) -> str:
    """The source hash under the manifest's policy. Empty file set = error, never a valid hash."""
    algo = policy.get("algo", ALGO_TREE)
    if algo == ALGO_TREE:
        return tree_hash(root, policy["globs"])[0]
    if algo == ALGO_CAT12:
        if not root.is_dir():
            raise EvidenceError(f"source folder not found: {root}")
        h, found = hashlib.sha256(), False
        for pattern in policy["globs"]:
            for p in sorted(root.glob(pattern)):
                if p.is_file():
                    with p.open("rb") as fh:
                        for chunk in iter(lambda: fh.read(1 << 20), b""):
                            h.update(chunk)
                    found = True
        if not found:
            raise EvidenceError(f"no files matched {policy['globs']} under {root}")
        return h.hexdigest()[:12]
    raise EvidenceError(f"unknown hash algo {algo!r}")


def is_hash(value, policy: dict) -> bool:
    n = 12 if policy.get("algo") == ALGO_CAT12 else 64
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % n, value) is not None


def shared_hash(root: Path):
    try:
        return tree_hash(root, SHARED_GLOBS)[0]
    except EvidenceError:
        return None


def mix_hash(root: Path):
    p = root / MIX_GLOB
    return file_digest(p) if p.is_file() else None


# --------------------------------------------------------------------------- json helpers
def _no_const(name):
    raise ValueError("non-standard JSON constant: " + name)


def _no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate JSON key: " + k)
        out[k] = v
    return out


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=_no_const, object_pairs_hook=_no_dupes)


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


SHORT_RE = re.compile(r"^(?P<name>[a-z0-9][a-z0-9_]*?)_(?P<aspect>9x16|4x5|1x1|16x9)\.mp4$")


def parse_name(filename: str):
    """Canonical <name>_<platform>_<hook>_<aspect>.mp4, or the short per-ratio form <name>_<aspect>.mp4
    (= platform `all`, hook `master`, as in the delivery playbook)."""
    m = NAME_RE.match(filename)
    if m:
        return m.groupdict()
    m = SHORT_RE.match(filename)
    if m:
        d = m.groupdict()
        d.update(platform="all", hook="master")
        return d
    return None


# --------------------------------------------------------------------------- check
def _f(findings, code, sev, msg, file=None):
    findings.append({"code": code, "severity": sev, "file": file, "message": msg})


def check_project(project: Path, final_name: str = "final") -> dict:
    findings = []
    report = {
        "tool": "manifest_check",
        "version": VERSION,
        "project": str(project),
        "checked_utc": utc_now(),
        "limits": [
            "from_master and applied_changes are attestations made at stamp/record time",
            "hashes prove source identity, not visual correctness; QA reports are separate evidence",
        ],
    }
    final = project / final_name
    mpath = final / "manifest.json"
    if not mpath.is_file():
        _f(findings, "M001_NO_MANIFEST", "insufficient", f"{mpath} not found - nothing proves what each file was rendered from")
        return _finish(report, findings, 0)
    try:
        m = load_json(mpath)
    except (ValueError, OSError) as e:
        _f(findings, "M001_BAD_MANIFEST", "block", f"manifest.json unreadable or non-strict JSON: {e}")
        return _finish(report, findings, 0)
    if not isinstance(m, dict) or m.get("schema_version") != SCHEMA_VERSION:
        _f(findings, "M001_SCHEMA", "block", f"manifest schema_version must be {SCHEMA_VERSION}")
        return _finish(report, findings, 0)

    policy = policy_of(m)
    profile = dict(DEFAULT_PROFILE)
    profile.update(m.get("delivery_profile") or {})

    files = m.get("files")
    if not isinstance(files, list) or not files:
        _f(findings, "M001_NO_FILES", "insufficient", "manifest lists no files (an empty delivery is not READY)")
        return _finish(report, findings, 0)

    master = m.get("master")
    master_dir = None
    master_current = master_shared = None
    if not isinstance(master, dict) or not is_hash(master.get("src_hash"), policy) or "hf" not in master:
        _f(findings, "M002_NO_MASTER", "block", "master block missing or src_hash invalid: run `freeze` before deriving anything")
        master = None
    else:
        master_dir = project / master["hf"]
        try:
            master_current = compute_src(master_dir, policy)
            master_shared = shared_hash(master_dir)
            if master_current != master["src_hash"]:
                _f(findings, "M003_STALE_MASTER", "block",
                   f"master source changed after freeze (frozen {master['src_hash'][:12]}, now {master_current[:12]}); "
                   "log the fix with `change`, carry it to every derivative, re-render and re-record them")
            mh = mix_hash(master_dir)
            if mh is not None and master.get("mix_sha256") and mh != master["mix_sha256"]:
                _f(findings, "M004_MASTER_MIX_CHANGED", "block", "master assets/mix.wav changed after freeze")
        except EvidenceError as e:
            _f(findings, "M003_MASTER_UNREADABLE", "insufficient", str(e))

    changes = []
    if master:
        for c in master.get("changes", []) or []:
            if isinstance(c, dict) and c.get("id"):
                changes.append(c["id"])

    # matrix completeness (G1: the variant matrix written at intake)
    matrix = m.get("matrix")
    names_in_manifest = [e.get("file") for e in files if isinstance(e, dict)]
    if not isinstance(matrix, list) or not matrix:
        _f(findings, "M005_NO_MATRIX", "insufficient", "no `matrix` of expected files: completeness cannot be asserted")
    else:
        for want in matrix:
            if want not in names_in_manifest:
                _f(findings, "M006_MISSING_VARIANT", "block", f"promised in the matrix but not delivered: {want}", want)
        for have in names_in_manifest:
            if have not in matrix:
                _f(findings, "M007_UNPLANNED_FILE", "block", f"delivered but not in the intake matrix: {have}", have)

    seen_names, seen_keys = set(), {}
    has_master_file = False
    for e in files:
        if not isinstance(e, dict):
            _f(findings, "M010_BAD_ENTRY", "block", "a files[] entry is not an object")
            continue
        fn = e.get("file")
        if not isinstance(fn, str) or "/" in fn or "\\" in fn or fn in ("", ".", ".."):
            _f(findings, "M010_BAD_NAME_FIELD", "block", f"file must be a bare file name, got {fn!r}")
            continue
        if fn in seen_names:
            _f(findings, "M011_DUPLICATE", "block", f"file listed twice: {fn}", fn)
        seen_names.add(fn)
        parts = parse_name(fn)
        ov = e.get("name_override")
        if isinstance(ov, dict) and ov.get("ledger_id"):
            # a name the user asked for (ledger line) overrides the convention; fields must then be explicit
            if not (isinstance(e.get("platform"), str) and isinstance(e.get("hook"), str) and e.get("aspect") in ASPECTS):
                _f(findings, "M012_NAMING", "block", "name_override needs explicit platform, hook and aspect fields in the entry", fn)
                parts = None
            else:
                parts = {"platform": e["platform"], "hook": e["hook"], "aspect": e["aspect"]}
        elif not parts:
            _f(findings, "M012_NAMING", "block", "name must match <name>_<platform>_<hook>_<aspect>.mp4 (or the short <name>_<aspect>.mp4; "
               "hook = master | hookA[-nomusic|-nocaps]; aspect = 9x16|4x5|1x1|16x9), or carry name_override {ledger_id}", fn)
        if parts:
            for k in ("platform", "hook", "aspect"):
                if e.get(k) != parts[k]:
                    _f(findings, "M013_NAME_FIELD_MISMATCH", "block", f"{k} in entry ({e.get(k)!r}) differs from the name ({parts[k]!r})", fn)
            key = (parts["platform"], parts["hook"], parts["aspect"])
            if key in seen_keys and seen_keys[key] != fn:
                _f(findings, "M014_COLLISION", "block", f"same platform/hook/aspect as {seen_keys[key]}", fn)
            seen_keys[key] = fn
        kind = e.get("kind")
        if kind not in KINDS:
            _f(findings, "M015_KIND", "block", f"kind must be one of {sorted(KINDS)}", fn)
            continue
        if kind == "nomusic" and parts and not parts["hook"].endswith("-nomusic"):
            _f(findings, "M012_NAMING", "block", "kind nomusic needs a hook token ending in -nomusic", fn)
        if kind == "nocaps" and parts and not parts["hook"].endswith("-nocaps"):
            _f(findings, "M012_NAMING", "block", "kind nocaps needs a hook token ending in -nocaps", fn)
        if kind == "master":
            has_master_file = True

        # file on disk
        fpath = final / fn
        if not fpath.is_file():
            _f(findings, "M020_FILE_MISSING", "block", "listed in the manifest but not in the finals folder", fn)
        elif fpath.stat().st_size == 0:
            _f(findings, "M020_FILE_EMPTY", "block", "zero-byte file", fn)
        else:
            if not HEX64.match(str(e.get("file_sha256", ""))):
                _f(findings, "M021_NO_FILE_HASH", "insufficient", "file_sha256 missing: a replaced file cannot be detected", fn)
            elif file_digest(fpath) != e["file_sha256"]:
                _f(findings, "M022_FILE_CHANGED", "block", "file bytes differ from the recorded file_sha256 (replaced or re-rendered after record)", fn)

        # source identity
        for fld in ("src_hash", "from_master"):
            if not is_hash(e.get(fld), policy):
                _f(findings, "M030_NO_SOURCE_HASH", "block", f"{fld} missing or invalid", fn)
        hf = e.get("hf")
        hf_dir = project / hf if isinstance(hf, str) and hf else None
        if master:
            if e.get("from_master") != master["src_hash"]:
                _f(findings, "M031_STALE_DERIVATIVE", "block",
                   f"rendered from master {str(e.get('from_master'))[:12]}, current master is {master['src_hash'][:12]}: "
                   "re-layout/patch, re-render, re-record", fn)
            if kind == "master" and e.get("src_hash") != master["src_hash"]:
                _f(findings, "M031_STALE_MASTER_FILE", "block", "master file was not rendered from the frozen master source", fn)
            if kind != "master":
                missing = [c for c in changes if c not in (e.get("applied_changes") or [])]
                if missing:
                    _f(findings, "M032_MISSING_MASTER_FIX", "block", f"master fixes not carried to this file: {missing}", fn)
        if hf_dir is None:
            _f(findings, "M033_NO_HF", "block", "hf folder not named", fn)
        else:
            try:
                cur = compute_src(hf_dir, policy)
                if cur != e.get("src_hash"):
                    _f(findings, "M034_CHANGED_AFTER_RENDER", "block",
                       f"source folder {hf} changed after this file was rendered (recorded {str(e.get('src_hash'))[:12]}, now {cur[:12]})", fn)
                if kind in ("relayout", "hook", "nomusic", "nocaps") and master_shared is not None:
                    sh = shared_hash(hf_dir)
                    if sh is None:
                        _f(findings, "M035_NO_SHARED_FILES", "insufficient", f"{hf} has no cues/mix to compare with the master", fn)
                    elif sh != master_shared:
                        _f(findings, "M035_SHARED_DRIFT", "block", f"cues/mix in {hf} differ from the master (same cues and same mix are required)", fn)
                if e.get("mix_variant") == "shared" and master and master.get("mix_sha256"):
                    live = mix_hash(hf_dir)
                    if live is not None and live != e.get("mix_sha256"):
                        _f(findings, "M036_MIX_CLAIM_FALSE", "block", "entry's mix_sha256 differs from assets/mix.wav in its source folder", fn)
            except EvidenceError as ex:
                _f(findings, "M034_SOURCE_UNREADABLE", "insufficient", str(ex), fn)

        # mix sharing
        mv = e.get("mix_variant")
        if mv not in MIX_VARIANTS:
            _f(findings, "M040_MIX_VARIANT", "block", f"mix_variant must be one of {sorted(MIX_VARIANTS)}", fn)
        elif mv == "shared":
            if master and e.get("mix_sha256") != master.get("mix_sha256"):
                _f(findings, "M041_MIX_NOT_SHARED", "block", "declared shared mix but mix_sha256 differs from the master's", fn)
        elif mv in ("own-vo", "recut") and not e.get("mix_note"):
            _f(findings, "M042_MIX_NOTE", "block", f"mix_variant {mv} needs a mix_note explaining why the mix differs", fn)
        if kind in ("relayout", "hook") and mv not in (None, "shared") and mv in MIX_VARIANTS and mv != "own-vo":
            _f(findings, "M043_MIX_KIND", "block", f"kind {kind} must share the master mix (or declare own-vo with a note)", fn)

        # QA
        qa = e.get("qa")
        if qa not in QA_STATES:
            _f(findings, "M050_QA_STATE", "block", f"qa must be one of {sorted(QA_STATES)}", fn)
        elif qa != "pass":
            _f(findings, "M051_QA_NOT_PASS", "block", f"qa is {qa}: only `pass` can be ready (not_run is not a pass)", fn)
        else:
            ev = e.get("qa_evidence")
            if not isinstance(ev, str) or not ev or not (project / ev).is_file() or (project / ev).stat().st_size == 0:
                _f(findings, "M052_QA_EVIDENCE", "insufficient", "qa=pass but qa_evidence file is missing or empty", fn)

        # delivery numbers
        lufs, tp = e.get("lufs"), e.get("tp")
        if not is_num(lufs) or not is_num(tp):
            _f(findings, "M060_LOUDNESS_MISSING", "insufficient", "lufs/tp must be numbers measured on the final file (0.0 is a number, null is missing)", fn)
        else:
            if abs(lufs - profile["lufs_target"]) > profile["lufs_tol"]:
                _f(findings, "M061_LUFS", "block", f"{lufs} LUFS outside {profile['lufs_target']} +/- {profile['lufs_tol']} (house preset v1)", fn)
            if tp > profile["tp_max"]:
                _f(findings, "M062_TRUE_PEAK", "block", f"true peak {tp} dBTP above {profile['tp_max']}", fn)
        w, hgt, dur = e.get("width"), e.get("height"), e.get("duration_s")
        if not (is_num(w) and is_num(hgt) and is_num(dur) and dur > 0):
            _f(findings, "M063_DIMS_MISSING", "insufficient", "width/height/duration_s missing (record fills them from ffprobe)", fn)
        elif parts and ASPECTS.get(parts["aspect"]) != (int(w), int(hgt)):
            _f(findings, "M064_DIMENSIONS", "block", f"{int(w)}x{int(hgt)} does not match aspect {parts['aspect']} {ASPECTS.get(parts['aspect'])}", fn)

    if not has_master_file and files:
        _f(findings, "M070_NO_MASTER_FILE", "block", "no files[] entry with kind=master")

    # orphan scan: finals folder holds finals + manifest.json only
    if final.is_dir():
        for p in sorted(final.iterdir()):
            if p.name == "manifest.json" or p.name.startswith("."):
                continue
            if p.is_dir():
                _f(findings, "M080_SUBFOLDER", "block", "finals folder must hold files only (no sub-folders)", p.name)
            elif p.name not in seen_names:
                _f(findings, "M081_ORPHAN_FILE", "block", "file in the finals folder is not in the manifest (old render left behind?)", p.name)

    return _finish(report, findings, len(files))


def _finish(report, findings, n_files):
    blocks = [f for f in findings if f["severity"] == "block"]
    insuff = [f for f in findings if f["severity"] == "insufficient"]
    if blocks:
        status = "BLOCKED"
    elif insuff:
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "READY"
    report.update({"status": status, "ready": status == "READY", "files_checked": n_files,
                   "counts": {"block": len(blocks), "insufficient": len(insuff)}, "findings": findings})
    return report


def exit_code(report) -> int:
    return {"READY": 0, "BLOCKED": 1}.get(report["status"], 2)


# --------------------------------------------------------------------------- commands
def _manifest_path(project: Path, final: str) -> Path:
    return project / final / "manifest.json"


def _load_or_new(project: Path, final: str) -> dict:
    mp = _manifest_path(project, final)
    if mp.is_file():
        return load_json(mp)
    return {"schema_version": SCHEMA_VERSION, "project": project.name, "hash_policy": {"algo": ALGO_TREE, "globs": DEFAULT_GLOBS},
            "delivery_profile": dict(DEFAULT_PROFILE), "master": None, "matrix": [], "files": []}


def cmd_hash(a) -> int:
    pol = policy_of({"hash_policy": {"algo": a.algo, "globs": a.globs.split(",") if a.globs else None}})
    try:
        h = compute_src(Path(a.hf_dir), pol)
        files = tree_hash(Path(a.hf_dir), pol["globs"])[1] if pol["algo"] == ALGO_TREE else []
    except EvidenceError as e:
        print(json.dumps({"status": "INSUFFICIENT_EVIDENCE", "error": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps({"src_hash": h, "short": h[:12], "files": len(files), "shared_hash": shared_hash(Path(a.hf_dir))}, ensure_ascii=False))
    return 0


def cmd_freeze(a) -> int:
    project = Path(a.project).resolve()
    m = _load_or_new(project, a.final)
    hf_dir = project / a.hf
    if getattr(a, "algo", None) and not m.get("files"):
        m["hash_policy"] = {"algo": a.algo, "globs": None}
    m["hash_policy"] = policy_of(m)
    try:
        h = compute_src(hf_dir, m["hash_policy"])
    except EvidenceError as e:
        print(f"INSUFFICIENT_EVIDENCE: {e}", file=sys.stderr)
        return 2
    mh = mix_hash(hf_dir)
    if mh is None:
        print("INSUFFICIENT_EVIDENCE: master has no assets/mix.wav; a shared mix cannot be proven", file=sys.stderr)
        return 2
    changes = (m.get("master") or {}).get("changes", [])
    m["master"] = {"hf": a.hf, "src_hash": h, "round": a.round, "mix_sha256": mh, "frozen_utc": utc_now(), "changes": changes}
    if a.matrix:
        m["matrix"] = [x.strip() for x in a.matrix.split(",") if x.strip()]
    save_json(_manifest_path(project, a.final), m)
    print(json.dumps({"frozen": True, "src_hash": h, "short": h[:12], "mix_sha256": mh[:12]}))
    return 0


def cmd_change(a) -> int:
    project = Path(a.project).resolve()
    m = _load_or_new(project, a.final)
    if not m.get("master"):
        print("INSUFFICIENT_EVIDENCE: freeze the master first", file=sys.stderr)
        return 2
    try:
        h = compute_src(project / m["master"]["hf"], policy_of(m))
    except EvidenceError as e:
        print(f"INSUFFICIENT_EVIDENCE: {e}", file=sys.stderr)
        return 2
    if any(c.get("id") == a.id for c in m["master"].get("changes", [])):
        print(f"BLOCKED: change id {a.id} already logged", file=sys.stderr)
        return 1
    if h == m["master"]["src_hash"]:
        print("BLOCKED: master source is unchanged since the last freeze/change; nothing to log", file=sys.stderr)
        return 1
    m["master"].setdefault("changes", []).append({"id": a.id, "summary": a.summary, "src_hash_after": h, "utc": utc_now()})
    m["master"]["src_hash"] = h
    mh = mix_hash(project / m["master"]["hf"])
    if mh:
        m["master"]["mix_sha256"] = mh
    save_json(_manifest_path(project, a.final), m)
    print(json.dumps({"logged": a.id, "new_master_hash": h[:12], "note": "every derivative is now stale until re-rendered and re-recorded"}))
    return 0


def _stamp_path(project: Path, hf: str) -> Path:
    return project / "_work" / "stamps" / f"{hf}.json"


def cmd_stamp(a) -> int:
    project = Path(a.project).resolve()
    m = _load_or_new(project, a.final)
    master = m.get("master")
    if not master:
        print("INSUFFICIENT_EVIDENCE: freeze the master before stamping a derivative", file=sys.stderr)
        return 2
    try:
        cur = compute_src(project / a.hf, policy_of(m))
        mcur = compute_src(project / master["hf"], policy_of(m))
    except EvidenceError as e:
        print(f"INSUFFICIENT_EVIDENCE: {e}", file=sys.stderr)
        return 2
    if mcur != master["src_hash"]:
        print("BLOCKED: master changed since freeze; log it with `change` and carry it to the copies first", file=sys.stderr)
        return 1
    stamp = {"hf": a.hf, "src_hash": cur, "shared_hash": shared_hash(project / a.hf), "from_master": master["src_hash"], "utc": utc_now()}
    save_json(_stamp_path(project, a.hf), stamp)
    print(json.dumps({"stamped": a.hf, "src_hash": cur[:12], "from_master": master["src_hash"][:12]}))
    return 0


def _ffprobe(path: Path):
    exe = shutil.which("ffprobe")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                              "-of", "json", str(path)], capture_output=True, text=True, timeout=60, check=True).stdout
        j = json.loads(out)
        return {"width": j["streams"][0]["width"], "height": j["streams"][0]["height"], "duration_s": round(float(j["format"]["duration"]), 3)}
    except Exception:
        return None


def cmd_record(a) -> int:
    project = Path(a.project).resolve()
    final = project / a.final
    m = _load_or_new(project, a.final)
    master = m.get("master")
    if not master:
        print("INSUFFICIENT_EVIDENCE: freeze the master first", file=sys.stderr)
        return 2
    fpath = final / Path(a.file).name
    if not fpath.is_file() or fpath.stat().st_size == 0:
        print(f"BLOCKED: {fpath} missing or empty", file=sys.stderr)
        return 1
    parts = parse_name(fpath.name)
    if a.name_ledger_id:
        if not (a.platform and a.hook and a.aspect in ASPECTS):
            print("BLOCKED: --name-ledger-id needs --platform, --hook and --aspect", file=sys.stderr)
            return 1
        parts = {"platform": a.platform, "hook": a.hook, "aspect": a.aspect}
    elif not parts:
        print("BLOCKED: file name must match <name>_<platform>_<hook>_<aspect>.mp4 (or <name>_<aspect>.mp4), or pass --name-ledger-id for a name the user asked for", file=sys.stderr)
        return 1
    sp = _stamp_path(project, a.hf)
    if not sp.is_file():
        print("INSUFFICIENT_EVIDENCE: no stamp. The source hash must be computed BEFORE the render: run `stamp` first, re-render", file=sys.stderr)
        return 2
    stamp = load_json(sp)
    try:
        cur = compute_src(project / a.hf, policy_of(m))
    except EvidenceError as e:
        print(f"INSUFFICIENT_EVIDENCE: {e}", file=sys.stderr)
        return 2
    if cur != stamp["src_hash"]:
        print("BLOCKED: source folder changed since the stamp (during or after the render): re-stamp and re-render", file=sys.stderr)
        return 1
    if a.kind == "master" and stamp["src_hash"] != master["src_hash"]:
        print("BLOCKED: master file must be rendered from the frozen master source", file=sys.stderr)
        return 1
    dims = _ffprobe(fpath) or {}
    for k, v in (("width", a.width), ("height", a.height), ("duration_s", a.duration_s)):
        if v is not None:
            dims[k] = v
    if a.applied_all:
        applied = [c["id"] for c in master.get("changes", [])]
    else:
        applied = [x.strip() for x in (a.applied or "").split(",") if x.strip()]
    mix = mix_hash(project / a.hf)
    entry = {
        "file": fpath.name, "kind": a.kind, "hf": a.hf, "round": a.round or master.get("round"),
        "aspect": parts["aspect"], "platform": parts["platform"], "hook": parts["hook"], "route": a.route,
        "src_hash": stamp["src_hash"], "from_master": stamp["from_master"], "applied_changes": applied,
        "mix_variant": a.mix_variant, "mix_sha256": mix, "file_sha256": file_digest(fpath), "size_bytes": fpath.stat().st_size,
        "width": dims.get("width"), "height": dims.get("height"), "duration_s": dims.get("duration_s"),
        "lufs": a.lufs, "tp": a.tp, "qa": a.qa, "qa_evidence": a.qa_evidence, "date": utc_now(),
    }
    if a.mix_note:
        entry["mix_note"] = a.mix_note
    if a.name_ledger_id:
        entry["name_override"] = {"ledger_id": a.name_ledger_id}
    entry = {k: v for k, v in entry.items() if v is not None}
    m["files"] = [e for e in m.get("files", []) if e.get("file") != entry["file"]] + [entry]
    save_json(_manifest_path(project, a.final), m)
    print(json.dumps({"recorded": entry["file"], "src_hash": entry["src_hash"][:12], "from_master": entry["from_master"][:12]}))
    return 0


def cmd_check(a) -> int:
    rep = check_project(Path(a.project).resolve(), a.final)
    if a.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"{rep['status']}  ({rep['files_checked']} files, {rep['counts']['block']} blocking, {rep['counts']['insufficient']} insufficient)")
        for f in rep["findings"]:
            print(f"  [{f['severity']}] {f['code']}" + (f" {f['file']}" if f.get("file") else "") + f": {f['message']}")
        if rep["ready"]:
            print("  Limits: " + "; ".join(rep["limits"]))
    return exit_code(rep)


# --------------------------------------------------------------------------- self-check
def _write(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))


def _args(**kw):
    ns = argparse.Namespace(final="final", round="v1", route="organic", mix_variant="shared", mix_note=None, applied=None,
                            applied_all=False, qa="pass", qa_evidence="_work/qa/report.json", lufs=-14.0, tp=-1.3,
                            width=None, height=None, duration_s=30.0, matrix=None, globs=None, algo=None,
                            name_ledger_id=None, platform=None, hook=None, aspect=None)
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def _build_project(root: Path, algo=None) -> Path:
    """master hf + 9:16 copy + three final files, all recorded through the real commands."""
    for hf in ("hf", "hf_9x16"):
        _write(root / hf / "index.html", f'<div id="root" data-hf-id="x1">{hf}</div>')
        _write(root / hf / "compositions" / "a.html", "<p>scene</p>")
        _write(root / hf / "cues.js", "const CUES={bed:0};")
        _write(root / hf / "assets" / "mix.wav", b"RIFF-mix-bytes" * 50)
    names = ["promo_meta_master_16x9.mp4", "promo_meta_master_9x16.mp4", "promo_meta_hookB_9x16.mp4"]
    _write(root / "_work" / "qa" / "report.json", '{"status":"PASS"}')
    for n in names:
        _write(root / "final" / n, ("mp4:" + n).encode() * 100)
    assert cmd_freeze(_args(project=str(root), hf="hf", matrix=",".join(names), algo=algo)) == 0
    dims = {"promo_meta_master_16x9.mp4": (1920, 1080), "promo_meta_master_9x16.mp4": (1080, 1920), "promo_meta_hookB_9x16.mp4": (1080, 1920)}
    plan = [(names[0], "hf", "master"), (names[1], "hf_9x16", "relayout"), (names[2], "hf_9x16", "hook")]
    for n, hf, kind in plan:
        assert cmd_stamp(_args(project=str(root), hf=hf)) == 0
        w, h = dims[n]
        assert cmd_record(_args(project=str(root), file=n, hf=hf, kind=kind, width=w, height=h)) == 0
    return root


def _status(root: Path) -> tuple:
    r = check_project(root)
    return r["status"], {f["code"] for f in r["findings"]}


def self_check() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):  # command chatter is not test output
        ok, fails = _self_check_body()
    total = ok + len(fails)
    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": total, "failed": fails}))
    return 0 if not fails else 1


def _self_check_body():
    ok, fails = 0, []

    def expect(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(label)

    with tempfile.TemporaryDirectory(prefix="mvv_בדיקה ") as td:  # Hebrew + space in the path on purpose
        base = Path(td)

        def fresh(name):
            p = base / name
            _build_project(p)
            return p

        p = fresh("ok")
        st, codes = _status(p)
        expect("clean project is READY", st == "READY" and not codes)
        expect("data-hf-id churn is not a source change", (_write(p / "hf" / "index.html", '<div id="root" data-hf-id="zzz">hf</div>') or True) and _status(p)[0] == "READY")

        p = fresh("stale_master")  # master edited after freeze, nothing logged
        _write(p / "hf" / "cues.js", "const CUES={bed:1};")
        st, codes = _status(p)
        expect("master edited after freeze -> BLOCKED STALE_MASTER", st == "BLOCKED" and "M003_STALE_MASTER" in codes)

        p = fresh("stale_derivative")  # master fix logged, derivatives not re-recorded
        _write(p / "hf" / "compositions" / "a.html", "<p>scene FIXED at 3.7 s</p>")
        expect("change logged", cmd_change(_args(project=str(p), id="M-001", summary="phone fix")) == 0)
        st, codes = _status(p)
        expect("derivatives stale after a master fix", st == "BLOCKED" and "M031_STALE_DERIVATIVE" in codes and "M032_MISSING_MASTER_FIX" in codes)
        # carry the patch to the copy, re-stamp, re-render (simulated), re-record with --applied-all -> READY again
        _write(p / "hf_9x16" / "compositions" / "a.html", "<p>scene FIXED at 3.7 s</p>")
        for n, hf, kind in [("promo_meta_master_16x9.mp4", "hf", "master"), ("promo_meta_master_9x16.mp4", "hf_9x16", "relayout"), ("promo_meta_hookB_9x16.mp4", "hf_9x16", "hook")]:
            _write(p / "final" / n, ("rerender:" + n).encode() * 100)
            cmd_stamp(_args(project=str(p), hf=hf))
            w, h = (1920, 1080) if n.endswith("16x9.mp4") else (1080, 1920)
            cmd_record(_args(project=str(p), file=n, hf=hf, kind=kind, width=w, height=h, applied_all=True))
        expect("re-recorded after the fix -> READY", _status(p)[0] == "READY")

        p = fresh("changed_after_render")
        _write(p / "hf_9x16" / "compositions" / "a.html", "<p>edited after render</p>")
        st, codes = _status(p)
        expect("derivative edited after its render -> CHANGED_AFTER_RENDER", st == "BLOCKED" and "M034_CHANGED_AFTER_RENDER" in codes)

        p = fresh("shared_drift")  # derivative cues diverged AND re-stamped to look fresh
        _write(p / "hf_9x16" / "cues.js", "const CUES={bed:99};")
        cmd_stamp(_args(project=str(p), hf="hf_9x16"))
        cmd_record(_args(project=str(p), file="promo_meta_master_9x16.mp4", hf="hf_9x16", kind="relayout", width=1080, height=1920))
        cmd_record(_args(project=str(p), file="promo_meta_hookB_9x16.mp4", hf="hf_9x16", kind="hook", width=1080, height=1920))
        st, codes = _status(p)
        expect("derivative with different cues -> SHARED_DRIFT", st == "BLOCKED" and "M035_SHARED_DRIFT" in codes)

        p = fresh("orphan")
        _write(p / "final" / "promo_meta_hookA_9x16_OLD.mp4", b"old")
        st, codes = _status(p)
        expect("orphan old render -> BLOCKED", st == "BLOCKED" and "M081_ORPHAN_FILE" in codes)

        p = fresh("missing_variant")
        m = load_json(p / "final" / "manifest.json")
        m["matrix"].append("promo_meta_hookC_9x16.mp4")
        save_json(p / "final" / "manifest.json", m)
        st, codes = _status(p)
        expect("promised variant missing -> BLOCKED", st == "BLOCKED" and "M006_MISSING_VARIANT" in codes)

        p = fresh("qa")
        m = load_json(p / "final" / "manifest.json")
        m["files"][1]["qa"] = "not_run"
        save_json(p / "final" / "manifest.json", m)
        st, codes = _status(p)
        expect("qa not_run is not pass", st == "BLOCKED" and "M051_QA_NOT_PASS" in codes)

        p = fresh("mix")
        m = load_json(p / "final" / "manifest.json")
        m["files"][2]["mix_sha256"] = "0" * 64
        save_json(p / "final" / "manifest.json", m)
        st, codes = _status(p)
        expect("hook variant claiming a shared mix that differs", st == "BLOCKED" and ("M041_MIX_NOT_SHARED" in codes or "M036_MIX_CLAIM_FALSE" in codes))

        p = fresh("tamper")
        _write(p / "final" / "promo_meta_hookB_9x16.mp4", b"someone re-encoded this" * 50)
        st, codes = _status(p)
        expect("file replaced after record", st == "BLOCKED" and "M022_FILE_CHANGED" in codes)

        p = fresh("badname")
        os.rename(p / "final" / "promo_meta_hookB_9x16.mp4", p / "final" / "promo hook B.mp4")
        m = load_json(p / "final" / "manifest.json")
        m["files"][2]["file"] = "promo hook B.mp4"
        save_json(p / "final" / "manifest.json", m)
        st, codes = _status(p)
        expect("bad naming blocked", st == "BLOCKED" and "M012_NAMING" in codes)

        p = fresh("loudness")
        m = load_json(p / "final" / "manifest.json")
        m["files"][0]["tp"] = 0.0
        m["files"][1]["lufs"] = None
        save_json(p / "final" / "manifest.json", m)
        st, codes = _status(p)
        expect("true peak 0.0 is numeric and fails; null lufs is missing", st == "BLOCKED" and "M062_TRUE_PEAK" in codes and "M060_LOUDNESS_MISSING" in codes)

        p = fresh("dims")
        m = load_json(p / "final" / "manifest.json")
        m["files"][1]["width"], m["files"][1]["height"] = 1920, 1080
        save_json(p / "final" / "manifest.json", m)
        expect("wrong dimensions for aspect", "M064_DIMENSIONS" in _status(p)[1])

        p = base / "empty"
        (p / "final").mkdir(parents=True)
        expect("no manifest -> INSUFFICIENT_EVIDENCE", _status(p)[0] == "INSUFFICIENT_EVIDENCE")
        save_json(p / "final" / "manifest.json", {"schema_version": SCHEMA_VERSION, "files": []})
        expect("empty files -> INSUFFICIENT_EVIDENCE", _status(p)[0] == "INSUFFICIENT_EVIDENCE")
        _write(p / "final" / "manifest.json", '{"schema_version":"1.0.0","schema_version":"1.0.0"}')
        expect("duplicate JSON key -> BLOCKED", _status(p)[0] == "BLOCKED")

        p = fresh("stamp_guard")  # render happened, then the source changed before record
        _write(p / "final" / "promo_meta_hookB_9x16.mp4", b"newer render" * 60)
        cmd_stamp(_args(project=str(p), hf="hf_9x16"))
        _write(p / "hf_9x16" / "compositions" / "a.html", "<p>changed during the render</p>")
        expect("record refuses when the source changed after the stamp", cmd_record(_args(project=str(p), file="promo_meta_hookB_9x16.mp4", hf="hf_9x16", kind="hook", width=1080, height=1920)) == 1)
        p2 = fresh("no_stamp")
        (p2 / "_work" / "stamps" / "hf_9x16.json").unlink()
        expect("record refuses without a pre-render stamp", cmd_record(_args(project=str(p2), file="promo_meta_hookB_9x16.mp4", hf="hf_9x16", kind="hook", width=1080, height=1920)) == 2)

        expect("short per-ratio name accepted (playbook form)", parse_name("promo_9x16.mp4") == {"name": "promo", "aspect": "9x16", "platform": "all", "hook": "master"})
        p = fresh("override")  # a name the user asked for overrides the convention, with a ledger id
        _write(p / "final" / "ClientFinal v2.mp4", b"client named this" * 40)
        m = load_json(p / "final" / "manifest.json")
        m["matrix"].append("ClientFinal v2.mp4")
        save_json(p / "final" / "manifest.json", m)
        cmd_stamp(_args(project=str(p), hf="hf_9x16"))
        expect("record refuses a free-form name without a ledger id", cmd_record(_args(project=str(p), file="ClientFinal v2.mp4", hf="hf_9x16", kind="relayout", width=1080, height=1920)) == 1)
        expect("record accepts it with --name-ledger-id", cmd_record(_args(project=str(p), file="ClientFinal v2.mp4", hf="hf_9x16", kind="relayout", width=1080, height=1920,
                                                                          name_ledger_id="L12", platform="all", hook="master", aspect="9x16")) == 0)
        expect("a user-named file is READY (collision check still applies)", _status(p)[0] == "READY")
        p = base / "cat12"
        _build_project(p, algo=ALGO_CAT12)
        mj = load_json(p / "final" / "manifest.json")
        expect("cat-sha256-12 policy yields 12-hex hashes", mj["hash_policy"]["algo"] == ALGO_CAT12 and len(mj["master"]["src_hash"]) == 12)
        expect("cat-sha256-12 project is READY", _status(p)[0] == "READY")
        _write(p / "hf" / "cues.js", "const CUES={bed:5};")
        expect("cat-sha256-12: master edit -> STALE_MASTER", "M003_STALE_MASTER" in _status(p)[1])
        expect("parse_name splits from the right", parse_name("my_big_name_tiktok_hookA-nomusic_9x16.mp4") == {"name": "my_big_name", "platform": "tiktok", "hook": "hookA-nomusic", "aspect": "9x16"})

    return ok, fails


# --------------------------------------------------------------------------- CLI
def build_parser():
    ap = argparse.ArgumentParser(description="Stale-derivative guard for multi-output deliveries.")
    ap.add_argument("--self-check", action="store_true", help="run the built-in tests and exit")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("hash"); p.add_argument("hf_dir"); p.add_argument("--globs"); p.add_argument("--algo", default=ALGO_TREE, choices=[ALGO_TREE, ALGO_CAT12])
    for name in ("freeze", "change", "stamp", "record", "check"):
        sp = sub.add_parser(name)
        sp.add_argument("project")
        sp.add_argument("--final", default="final")
        if name == "freeze":
            sp.add_argument("--hf", required=True); sp.add_argument("--round", default="v1"); sp.add_argument("--matrix")
            sp.add_argument("--algo", choices=[ALGO_TREE, ALGO_CAT12], help="hash recipe for a NEW manifest (default tree-sha256-v1; cat-sha256-12 = the playbook's cat|sha256sum|cut -c1-12)")
        if name == "change":
            sp.add_argument("--id", required=True); sp.add_argument("--summary", required=True)
        if name == "stamp":
            sp.add_argument("--hf", required=True)
        if name == "record":
            sp.add_argument("--file", required=True); sp.add_argument("--hf", required=True)
            sp.add_argument("--kind", required=True, choices=sorted(KINDS)); sp.add_argument("--route", default="organic")
            sp.add_argument("--mix-variant", dest="mix_variant", default="shared", choices=sorted(MIX_VARIANTS))
            sp.add_argument("--mix-note", dest="mix_note"); sp.add_argument("--round")
            g = sp.add_mutually_exclusive_group()
            g.add_argument("--applied-all", dest="applied_all", action="store_true"); g.add_argument("--applied")
            sp.add_argument("--qa", required=True, choices=sorted(QA_STATES)); sp.add_argument("--qa-evidence", dest="qa_evidence")
            sp.add_argument("--name-ledger-id", dest="name_ledger_id", help="the file name was asked for by the user (ledger line id): overrides the naming convention")
            sp.add_argument("--platform"); sp.add_argument("--hook"); sp.add_argument("--aspect")
            sp.add_argument("--lufs", type=float); sp.add_argument("--tp", type=float)
            sp.add_argument("--width", type=int); sp.add_argument("--height", type=int); sp.add_argument("--duration-s", dest="duration_s", type=float)
        if name == "check":
            sp.add_argument("--json", action="store_true")
    return ap


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    handlers = {"hash": cmd_hash, "freeze": cmd_freeze, "change": cmd_change, "stamp": cmd_stamp, "record": cmd_record, "check": cmd_check}
    if a.cmd not in handlers:
        ap.print_help()
        return 2
    return handlers[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())

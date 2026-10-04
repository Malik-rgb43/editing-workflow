"""File-level bill of materials (BOM) with licence gating, generated from the actual tree.

Usage: python scripts/gen_bom.py [--root DIR] [--licenses licenses.toml] [--register REGISTER.csv] [--out-dir docs] [--no-write] [--check] [--update-notices [FILE]] [--json] [--no-git]

For every file that would ship (git view when available): path, size, sha256, declared licence, owner-authored
vs third-party vs generated, and the rule from licenses.toml that declared it. Writes docs/BOM.json and
docs/BOM.md (deterministic: no timestamps). FAILS (exit 1) when any file is blocked or has no declared licence
(SECURITY_AND_LICENSING.md section 3): Mixkit / ElevenLabs / Artlist / Suno files, Adobe or Apple fonts,
FFmpeg binaries, ivrit.ai ONNX/weights/data, Hunyuan 3D 2.1, RVM weights,
Ultralytics/YOLO weights, SDXL-Turbo weights, the knowledge-pack folder, licences that are unknown,
proprietary, non-commercial, GPL/AGPL or community-licence, third-party files without a source, and any
video/audio/image/font/weights/archive/executable file that no rule explicitly allows.

licenses.toml format (the LAST matching rule wins; globs use ** for any depth):
    schema = 1
    [[rule]]
    glob = "docs/**"            # or globs = ["a/**", "b/**"]
    origin = "owner"            # owner | third_party | generated
    licence = "owner-undecided" # SPDX id, LicenseRef-..., or owner-undecided (decision default Q12)
    allow = ["image"]           # restricted classes this rule may cover: video audio image font weights archive executable
    source = "https://..."      # REQUIRED for third_party
    register_id = "T18-L001"    # optional link to LICENSE_REGISTER.csv (reconciled when --register is given)
    note = "free text"

--register CSV (schema of research T18 LICENSE_REGISTER.csv: item, review_status, blocking_unknown, register_id, ...):
a third-party file whose register_id is missing from the CSV, or whose row is not cleared/approved/resolved,
or still has a blocking_unknown, is blocked; with a register supplied, third-party files without register_id are blocked.

--update-notices [FILE]  rewrite only the block between <!-- BEGIN GENERATED:bom --> and <!-- END GENERATED:bom -->
                         in THIRD_PARTY_NOTICES.md (default file) with the third-party table from the BOM.
--check                  regenerate in memory and fail if docs/BOM.json differs (stale BOM).
Exit codes: 0 clean, 1 blocked/unknown/stale, 2 usage error.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _avc_common as C  # noqa: E402

ORIGINS = {"owner", "third_party", "generated"}
CLEARED = {"cleared", "approved", "resolved"}
SELF_OUTPUTS = ("docs/BOM.json", "docs/BOM.md")
NOTICE_BEGIN = "<!-- BEGIN GENERATED:bom -->"
NOTICE_END = "<!-- END GENERATED:bom -->"

# (id, regex over the lower-cased posix path, restricted classes the rule is limited to or None, reason)
BLOCK_RULES: list[tuple[str, re.Pattern[str], set[str] | None, str]] = [
    ("mixkit", re.compile(r"(?<![a-z])mixkit"), {"audio", "video", "image", "archive", "binary"}, "Mixkit files may not be redistributed (standalone redistribution prohibited)"),
    ("elevenlabs", re.compile(r"eleven[-_ ]?(?:labs|music)"), {"audio", "video", "archive", "binary"}, "ElevenLabs/Eleven Music outputs have no redistribution clearance"),
    ("artlist", re.compile(r"artlist"), {"audio", "video", "image", "archive", "binary"}, "Artlist assets may not be redistributed"),
    ("suno", re.compile(r"(?<![a-z])suno(?![a-z])"), {"audio", "video", "archive", "binary"}, "Suno outputs may not be redistributed"),
    ("adobe-font", re.compile(r"adobe|typekit"), {"font"}, "Adobe fonts are not redistributable"),
    ("apple-font", re.compile(r"(?<![a-z])sf[-_ ]?(?:pro|compact|mono|arabic|hebrew)|san[-_ ]?francisco"), {"font"}, "Apple SF fonts are not redistributable"),
    ("ffmpeg-binary", re.compile(r"(?:^|/)(?:lib)?(?:ffmpeg|ffprobe|ffplay)(?:\.exe)?$|(?:^|/)(?:lib)?(?:avcodec|avformat|avutil|avfilter|avdevice|swresample|swscale|postproc)[-\d.]*\.(?:dll|so[.\d]*|dylib)$"), None, "FFmpeg binaries are never bundled (install instructions instead)"),
    ("ivrit-ai", re.compile(r"ivrit"), {"weights", "audio", "video", "archive"}, "ivrit.ai ONNX conversions / weights / training data have no redistribution clearance"),
    ("hunyuan3d", re.compile(r"hunyuan[-_ ]?3d"), {"weights", "archive", "executable", "binary"}, "Hunyuan 3D 2.1 community licence is not unrestricted"),
    ("hunyuan3d-code", re.compile(r"(?:^|/)hunyuan[-_ ]?3d[^/]*/"), None, "vendored Hunyuan 3D folder (community licence excludes EU, UK, South Korea)"),
    ("rvm-gpl", re.compile(r"(?<![a-z])rvm(?![a-z])|robust[-_ ]?video[-_ ]?matting"), {"weights", "archive", "executable", "binary"}, "RVM weights are GPL-3.0 (internal use only until resolved)"),
    ("rvm-gpl-code", re.compile(r"(?:^|/)(?:rvm|robust[-_ ]?video[-_ ]?matting)[^/]*/"), None, "vendored RVM folder is GPL-3.0 (internal use only until resolved)"),
    ("ultralytics", re.compile(r"ultralytics|(?<![a-z])yolo[-_ ]?v?\d"), {"weights", "archive", "executable", "binary"}, "Ultralytics/YOLO is AGPL-3.0"),
    ("ultralytics-code", re.compile(r"(?:^|/)ultralytics[^/]*/"), None, "vendored Ultralytics folder is AGPL-3.0"),
    ("sdxl-turbo", re.compile(r"sdxl[-_ ]?turbo"), {"weights", "archive"}, "SDXL-Turbo needs a Stability Community License registration"),
    ("private-material", re.compile(r"(?:^|/)knowledge-pack(?:/|$)|(?:^|/)brain/(?:clients|projects|lessons)(?:/|$)"), None, "private owner/client material must never ship"),
]

LICENCE_BLOCK_RE = [
    ("unknown", re.compile(r"(?i)^\s*(?:unknown|unresolved|unlicensed|none|tbd|)\s*$")),
    ("proprietary", re.compile(r"(?i)proprietary|\beula\b|all[-_ ]rights[-_ ]reserved")),
    ("non-commercial", re.compile(r"(?i)(?:^|[-_ .])nc(?:[-_ .]|$)|non[-_ ]?commercial")),
    ("copyleft-review", re.compile(r"(?i)(?<![a-z])a?gpl|(?<![a-z])agpl")),
    ("community-licence", re.compile(r"(?i)community|custom")),
]


class LicencesError(ValueError):
    pass


def load_licenses(path: Path) -> list[dict]:
    try:
        data = tomllib.loads(path.read_bytes().decode("utf-8-sig"))
    except FileNotFoundError:
        raise LicencesError(f"{path.name} not found") from None
    except tomllib.TOMLDecodeError as exc:
        raise LicencesError(f"{path.name} is not valid TOML: {exc}") from None
    if data.get("schema") != 1:
        raise LicencesError(f"{path.name}: schema must be 1")
    rules = data.get("rule", [])
    out: list[dict] = []
    for index, rule in enumerate(rules, start=1):
        globs = rule.get("globs") or ([rule["glob"]] if "glob" in rule else [])
        if not globs or not all(isinstance(g, str) and g for g in globs):
            raise LicencesError(f"rule #{index}: glob/globs required")
        origin = rule.get("origin")
        if origin not in ORIGINS:
            raise LicencesError(f"rule #{index}: origin must be one of {sorted(ORIGINS)}")
        licence = rule.get("licence")
        if not isinstance(licence, str):
            raise LicencesError(f"rule #{index}: licence must be a string")
        allow = rule.get("allow", [])
        if not isinstance(allow, list) or any(a not in C.RESTRICTED_EXT for a in allow):
            raise LicencesError(f"rule #{index}: allow must be a list of {sorted(C.RESTRICTED_EXT)}")
        out.append(
            {
                "index": index,
                "globs": globs,
                "regexes": [C.glob_to_regex(g) for g in globs],
                "origin": origin,
                "licence": licence,
                "allow": set(allow),
                "source": rule.get("source", ""),
                "register_id": rule.get("register_id", ""),
                "note": rule.get("note", ""),
            }
        )
    return out


def match_rule(rules: list[dict], relpath: str, fclass: str | None) -> dict | None:
    chosen = None
    for rule in rules:
        if any(rx.match(relpath) for rx in rule["regexes"]) and (fclass is None or fclass in rule["allow"]):
            chosen = rule
    return chosen


def block_reasons(relpath: str, fclass: str | None, licence: str) -> list[str]:
    lowered = relpath.lower()
    reasons = []
    for rule_id, regex, classes, message in BLOCK_RULES:
        if regex.search(lowered) and (classes is None or fclass in classes):
            reasons.append(f"{rule_id}: {message}")
    for kind, regex in LICENCE_BLOCK_RE:
        if regex.search(licence):
            reasons.append(f"licence-{kind}: declared licence '{licence}' is not redistributable without review")
            break
    return reasons


def load_register(path: Path) -> tuple[dict[str, dict], str | None]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            needed = {"item", "review_status", "register_id"}
            if not needed <= fields:
                return {}, f"register schema mismatch: missing column(s) {', '.join(sorted(needed - fields))}"
            rows = {(row.get("register_id") or "").strip(): row for row in reader if (row.get("register_id") or "").strip()}
            return rows, None
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        return {}, f"cannot read register: {exc}"


def build(root: Path, licenses_path: Path, register_path: Path | None = None, use_git: bool = True,
          files: list[str] | None = None) -> tuple[dict, C.Report]:
    report = C.Report("gen_bom")
    try:
        rules = load_licenses(licenses_path)
    except LicencesError as exc:
        rules = []
        report.fail("licenses-config", str(exc))
    register: dict[str, dict] = {}
    if register_path is not None:
        register, reg_error = load_register(register_path)
        if reg_error:
            report.fail("register", reg_error)
    names = [n for n in (files if files is not None else C.list_files(root, use_git=use_git)) if n not in SELF_OUTPUTS]
    entries: list[dict] = []
    blocked: list[dict] = []
    unknown: list[dict] = []
    referenced: set[str] = set()
    for relpath in names:
        path = root / relpath
        fclass = C.file_class(relpath)
        if fclass is None and C.looks_binary(path):
            fclass = "binary"
        rule = match_rule(rules, relpath, fclass)
        entry = {
            "path": relpath,
            "size": path.stat().st_size,
            "sha256": C.sha256_file(path),
            "class": fclass or "text",
            "origin": rule["origin"] if rule else "unknown",
            "licence": rule["licence"] if rule else "unknown",
            "rule": rule["index"] if rule else None,
            "flags": [],
        }
        if rule is None:
            entry["flags"].append("unknown: no licenses.toml rule covers this file" + (f" (restricted class '{fclass}' needs allow = [\"{fclass}\"])" if fclass else ""))
        else:
            if rule["origin"] == "third_party":
                if not rule["source"]:
                    entry["flags"].append("blocked: third-party file without a source in licenses.toml")
                if rule["register_id"]:
                    entry["register_id"] = rule["register_id"]
                    referenced.add(rule["register_id"])
                    if register_path is not None:
                        row = register.get(rule["register_id"])
                        if row is None:
                            entry["flags"].append(f"blocked: register_id {rule['register_id']} not found in the register")
                        else:
                            status = (row.get("review_status") or "").strip().lower()
                            if status not in CLEARED:
                                entry["flags"].append(f"blocked: register row {rule['register_id']} review_status '{status or 'empty'}' is not cleared")
                            elif (row.get("blocking_unknown") or "").strip():
                                entry["flags"].append(f"blocked: register row {rule['register_id']} still has a blocking unknown")
                elif register_path is not None:
                    entry["flags"].append("blocked: third-party file has no register_id to reconcile with the register")
            for reason in block_reasons(relpath, fclass, rule["licence"]):
                entry["flags"].append("blocked: " + reason)
        if rule is None:
            for reason in block_reasons(relpath, fclass, "owner-undecided"):
                entry["flags"].append("blocked: " + reason)
        entries.append(entry)
        if any(f.startswith("blocked") for f in entry["flags"]):
            blocked.append(entry)
        if any(f.startswith("unknown") for f in entry["flags"]):
            unknown.append(entry)
    for entry in blocked:
        for flag in entry["flags"]:
            if flag.startswith("blocked"):
                report.fail("bom-blocked", flag, entry["path"])
    for entry in unknown:
        report.fail("bom-unknown", entry["flags"][0], entry["path"])
    by_licence: dict[str, int] = {}
    by_origin: dict[str, int] = {}
    for entry in entries:
        by_licence[entry["licence"]] = by_licence.get(entry["licence"], 0) + 1
        by_origin[entry["origin"]] = by_origin.get(entry["origin"], 0) + 1
    bom = {
        "schema": 1,
        "tool": "scripts/gen_bom.py",
        "status": "FAIL" if (blocked or unknown or report.fails) else "PASS",
        "file_count": len(entries),
        "total_bytes": sum(e["size"] for e in entries),
        "by_origin": dict(sorted(by_origin.items())),
        "by_licence": dict(sorted(by_licence.items())),
        "blocked_count": len(blocked),
        "unknown_count": len(unknown),
        "register": (
            {"rows": len(register), "referenced_by_tree": len(referenced & set(register)), "checked": True}
            if register_path is not None
            else {"checked": False, "note": "no --register CSV supplied; reconciliation not run"}
        ),
        "files": entries,
    }
    report.stats.update({"files": len(entries), "blocked": len(blocked), "unknown": len(unknown)})
    if register_path is None:
        report.not_run("register-reconciliation", "no --register CSV supplied (BOM gating by licenses.toml and block rules only)", blocking=False)
    return bom, report


def render_md(bom: dict, licenses_rules: list[dict] | None = None) -> str:
    out = [
        "<!-- GENERATED by scripts/gen_bom.py - do not edit; regenerate with `python scripts/gen_bom.py`. -->",
        "# Bill of materials",
        "",
        f"Status: **{bom['status']}** - {bom['file_count']} files, {bom['total_bytes']} bytes, "
        f"{bom['blocked_count']} blocked, {bom['unknown_count']} without a declared licence.",
        "",
        "Not legal advice. This lists what is in the tree and what `licenses.toml` declares about it; it does not clear any file.",
        "",
        "## By origin",
        "",
        "| origin | files |",
        "|---|---|",
    ]
    out += [f"| {k} | {v} |" for k, v in bom["by_origin"].items()]
    out += ["", "## By declared licence", "", "| licence | files |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in bom["by_licence"].items()]
    problems = [e for e in bom["files"] if e["flags"]]
    out += ["", "## Blocked or unknown files", ""]
    if not problems:
        out.append("None.")
    else:
        out += ["| path | licence | flags |", "|---|---|---|"]
        for entry in problems[:200]:
            flags = "; ".join(entry["flags"]).replace("|", "\\|")
            out.append(f"| `{entry['path']}` | {entry['licence']} | {flags} |")
        if len(problems) > 200:
            out.append(f"\n... and {len(problems) - 200} more (see docs/BOM.json).")
    third = [e for e in bom["files"] if e["origin"] == "third_party"]
    out += ["", "## Third-party files", ""]
    if not third:
        out.append("None bundled.")
    else:
        out += ["| path | licence | sha256 | register_id |", "|---|---|---|---|"]
        out += [f"| `{e['path']}` | {e['licence']} | `{e['sha256'][:16]}` | {e.get('register_id', '')} |" for e in third]
    reg = bom["register"]
    out += ["", "## Register reconciliation", "", reg.get("note") or f"Checked against {reg['rows']} register rows; {reg['referenced_by_tree']} referenced by the tree."]
    return "\n".join(out) + "\n"


def notices_block(bom: dict) -> str:
    third = [e for e in bom["files"] if e["origin"] == "third_party"]
    lines = [NOTICE_BEGIN, "<!-- GENERATED from docs/BOM.json by scripts/gen_bom.py --update-notices - edit outside this block only. -->", ""]
    if not third:
        lines.append("No third-party files are bundled in this tree (nothing to attribute here).")
    else:
        lines += ["| file | licence | source | register_id |", "|---|---|---|---|"]
        for entry in third:
            lines.append(f"| `{entry['path']}` | {entry['licence']} | {entry.get('source', '')} | {entry.get('register_id', '')} |")
    lines += ["", NOTICE_END]
    return "\n".join(lines)


def update_notices(notices_path: Path, bom: dict) -> str | None:
    """Rewrite the generated block; return an error string if the markers are missing."""
    text = notices_path.read_bytes().decode("utf-8")
    start, end = text.find(NOTICE_BEGIN), text.find(NOTICE_END)
    if start < 0 or end < start:
        return f"{notices_path.name} has no '{NOTICE_BEGIN}' ... '{NOTICE_END}' markers"
    third = [dict(e, source=e.get("source", "")) for e in bom["files"] if e["origin"] == "third_party"]
    block = notices_block({"files": third})
    new = text[:start] + block + text[end + len(NOTICE_END):]
    if new != text:
        notices_path.write_bytes(new.encode("utf-8"))
    return None


def attach_sources(bom: dict, rules: list[dict]) -> None:
    by_index = {r["index"]: r for r in rules}
    for entry in bom["files"]:
        rule = by_index.get(entry["rule"]) if entry["rule"] else None
        if rule and entry["origin"] == "third_party":
            entry["source"] = rule["source"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the file-level bill of materials and gate blocked/unknown files.")
    C.add_common_args(parser, strict_not_run=False)
    parser.add_argument("--licenses", default=None, help="licenses.toml (default <root>/licenses.toml)")
    parser.add_argument("--register", default=None, help="optional LICENSE_REGISTER.csv to reconcile against")
    parser.add_argument("--out-dir", default=None, help="where to write BOM.json/BOM.md (default <root>/docs)")
    parser.add_argument("--no-write", action="store_true", help="do not write BOM.json/BOM.md")
    parser.add_argument("--check", action="store_true", help="fail if the committed docs/BOM.json is stale")
    parser.add_argument("--update-notices", nargs="?", const="THIRD_PARTY_NOTICES.md", default=None, metavar="FILE", help="refresh the generated block of THIRD_PARTY_NOTICES.md")
    parser.add_argument("--no-git", action="store_true", help="walk the directory instead of using git's file list")
    return parser


def main(argv: list[str] | None = None) -> int:
    C.setup_utf8()
    args = build_parser().parse_args(argv)
    root = C.resolve_root(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root.name}", file=sys.stderr)
        return C.EXIT_USAGE
    licenses_path = Path(args.licenses) if args.licenses else root / "licenses.toml"
    register_path = Path(args.register) if args.register else None
    bom, report = build(root, licenses_path, register_path, use_git=not args.no_git)
    try:
        attach_sources(bom, load_licenses(licenses_path))
    except LicencesError:
        pass
    out_dir = Path(args.out_dir) if args.out_dir else root / "docs"
    json_text = json.dumps(bom, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        existing = out_dir / "BOM.json"
        if not existing.is_file():
            report.fail("bom-missing", "docs/BOM.json does not exist; run python scripts/gen_bom.py")
        elif existing.read_bytes().decode("utf-8") != json_text:
            report.fail("bom-stale", "docs/BOM.json is stale; regenerate with python scripts/gen_bom.py")
    elif not args.no_write:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "BOM.json").write_bytes(json_text.encode("utf-8"))
        (out_dir / "BOM.md").write_bytes(render_md(bom).encode("utf-8"))
        report.notes.append(f"wrote {out_dir.name}/BOM.json and {out_dir.name}/BOM.md")
    if args.update_notices is not None and not args.check:
        notices = root / args.update_notices
        if not notices.is_file():
            report.fail("notices-missing", f"{notices.name} not found")
        else:
            error = update_notices(notices, bom)
            if error:
                report.fail("notices-markers", error)
    return C.emit(report, args.json, False, args.warnings_as_errors)


if __name__ == "__main__":
    sys.exit(main())

"""Dry-run release builder: deterministic ZIP + manifest hashes + checksums, and the update/rollback plan printer.

Usage: python scripts/release.py build --version X.Y.Z [--final] [--out-dir DIR] [--skip-gates] [--register CSV]
       python scripts/release.py plan [--current X.Y.Z] --target X.Y.Z [--json]
       python scripts/release.py verify ZIP
       python scripts/release.py diff OLD NEW        (manifests or release ZIPs)
       python scripts/release.py local-changes --manifest MANIFEST.json --dir INSTALL_DIR

This script NEVER uploads, pushes, tags or publishes anything and makes no network call; it only writes files
under --out-dir (default <root>/dist, which is git-ignored).

build   Runs the deterministic gates (run_all_checks) and builds <name>-<ver>.zip with a top-level folder, a fixed
        timestamp and sorted entries (same tree -> same bytes), plus <zip>.sha256 and <name>-<ver>.release.json
        (descriptor: zip hash, manifest hash, gate results, releasable flag). Inside the ZIP, release-manifest.json is
        regenerated with version, file list (path, size, sha256) and the support matrix from the repository's template.
        Default mode is a DRY RUN: output is named *.dryrun.zip, descriptor says releasable=false, gate failures are
        reported but do not stop the build (--skip-gates skips running them). --final enforces release rules: every gate
        passes (scan_private needs the local denylist, workflow actions pinned, BOM fresh, pytest green), CHANGELOG has a
        [X.Y.Z] entry, and the release is immutable (an existing zip/descriptor for that version is never overwritten).
        Never shipped: .git, dist, projects/, _work/, .env*, scripts/private_denylist.txt, plus packaging/release-excludes.txt.
plan    Prints the update path of REPO_ARCHITECTURE section 10 and the rollback path (printer only; executes nothing).
verify  Re-hashes every file in a release ZIP against its embedded manifest; rejects path traversal and extra files.
diff    Lists added/removed/changed files between two manifests or ZIPs.
local-changes  Inventory of installed files that differ from a release manifest (step 1 of the update path).
Exit codes: 0 ok, 1 failed / gates failed under --final / verification failed, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _avc_common as C  # noqa: E402
import run_all_checks  # noqa: E402

PREFIX = "editing-workflow"
MANIFEST_NAME = "release-manifest.json"
FIXED_DATE = (1980, 1, 1, 0, 0, 0)
BUILTIN_EXCLUDES = (
    ".git/**",
    "dist/**",
    "projects/**",
    "**/_work/**",
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "scripts/private_denylist.txt",
    "packaging/releases/*.zip",
    "**/*.dryrun.zip",
    ".claude/settings.local.json",
)
ENV_TEMPLATE_RE = re.compile(r"\.env\.(?:example|sample|template|dist)$")


def read_excludes(root: Path) -> list[str]:
    patterns = list(BUILTIN_EXCLUDES)
    extra = root / "packaging" / "release-excludes.txt"
    if extra.is_file():
        for raw in extra.read_bytes().decode("utf-8-sig").splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def release_files(root: Path, use_git: bool = True) -> list[str]:
    patterns = [C.glob_to_regex(p) for p in read_excludes(root)]
    out = []
    for rel in C.list_files(root, use_git=use_git):
        if rel == MANIFEST_NAME:
            continue
        if ENV_TEMPLATE_RE.search(rel):
            out.append(rel)
            continue
        if any(p.match(rel) for p in patterns):
            continue
        out.append(rel)
    return out


def changelog_has(root: Path, version: str) -> bool:
    path = root / "CHANGELOG.md"
    if not path.is_file():
        return False
    return re.search(rf"(?m)^##\s*\[{re.escape(version)}\]", path.read_bytes().decode("utf-8-sig")) is not None


def build_manifest(root: Path, version: str, files: list[str], final: bool) -> dict:
    base: dict = {}
    template = root / MANIFEST_NAME
    if template.is_file():
        try:
            base = json.loads(template.read_bytes().decode("utf-8-sig"))
        except json.JSONDecodeError:
            base = {}
    entries = [{"path": rel, "size": (root / rel).stat().st_size, "sha256": C.sha256_file(root / rel)} for rel in files]
    manifest = dict(base)
    manifest.update(
        {
            "name": PREFIX,
            "version": version,
            "status": "release" if final else "dry-run (not a release)",
            "hashes": {"algorithm": "sha256", "covers": f"every file in the archive except {MANIFEST_NAME}"},
            "file_count": len(entries),
            "files": entries,
        }
    )
    manifest.setdefault("schema_version", "1")
    return manifest


def make_zip(root: Path, files: list[str], manifest_bytes: bytes, version: str, out_path: Path) -> None:
    top = f"{PREFIX}-{version}"
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    members = sorted(files + [MANIFEST_NAME])
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for rel in members:
            info = zipfile.ZipInfo(f"{top}/{rel}", date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100755 if rel.endswith(".sh") else 0o100644) << 16
            if rel == MANIFEST_NAME:
                archive.writestr(info, manifest_bytes, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
                continue
            with (root / rel).open("rb") as source, archive.open(info, "w") as dest:
                for chunk in iter(lambda: source.read(1 << 20), b""):
                    dest.write(chunk)
    tmp.replace(out_path)


def gate_summary(results: list[dict]) -> list[dict]:
    return [{"gate": r["gate"], "status": r["status"]} for r in results]


def cmd_build(args: argparse.Namespace) -> int:
    root = C.resolve_root(args.root)
    version = args.version
    if not C.SEMVER_RE.match(version):
        print("error: --version must be SemVer 2.0.0 (e.g. 0.1.0 or 1.0.0-rc.1)", file=sys.stderr)
        return C.EXIT_USAGE
    final = args.final
    out_dir = Path(args.out_dir).resolve() if args.out_dir else root / "dist"
    suffix = "" if final else ".dryrun"
    zip_path = out_dir / f"{PREFIX}-{version}{suffix}.zip"
    descriptor_path = out_dir / f"{PREFIX}-{version}{suffix}.release.json"
    problems: list[str] = []
    if final:
        committed = root / "packaging" / "releases" / f"{PREFIX}-{version}.release.json"
        if zip_path.exists() or descriptor_path.exists() or committed.exists():
            print(f"error: release {version} already exists; releases are immutable - bump the version instead", file=sys.stderr)
            return C.EXIT_FAIL
        if not changelog_has(root, version):
            problems.append(f"CHANGELOG.md has no '## [{version}]' entry")
    elif not changelog_has(root, version):
        print(f"warning: CHANGELOG.md has no '## [{version}]' entry (required for --final)")
    results: list[dict] = []
    if args.skip_gates:
        if final:
            print("error: --skip-gates is not allowed with --final", file=sys.stderr)
            return C.EXIT_USAGE
        print("gates: SKIPPED (dry run; the descriptor records releasable=false)")
    else:
        results = run_all_checks.run_gates(root, final=final, register=args.register, with_pytest=final)
        print(run_all_checks.render_table(results))
        code = run_all_checks.overall(results, strict_not_run=final)
        if final and code != C.EXIT_OK:
            problems.append("gates did not all pass (see the table above); NOT_RUN other than model_eval is a failure for --final")
    if problems:
        for problem in problems:
            print(f"refusing to build a final release: {problem}", file=sys.stderr)
        return C.EXIT_FAIL
    gate_failed = any(r["status"] in (C.FAIL, C.ERROR) for r in results)
    gate_notrun = any(r["status"] == C.NOT_RUN and r["gate"] != "model_eval" for r in results)
    files = release_files(root, use_git=not args.no_git)
    manifest = build_manifest(root, version, files, final)
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    make_zip(root, files, manifest_bytes, version, zip_path)
    zip_sha = C.sha256_file(zip_path)
    (out_dir / (zip_path.name + ".sha256")).write_bytes(f"{zip_sha}  {zip_path.name}\n".encode("utf-8"))
    releasable = bool(final and not gate_failed and not gate_notrun and not args.skip_gates)
    descriptor = {
        "name": PREFIX,
        "version": version,
        "mode": "final" if final else "dry-run",
        "releasable": releasable,
        "zip": zip_path.name,
        "zip_sha256": zip_sha,
        "zip_size": zip_path.stat().st_size,
        "manifest_sha256": C.sha256_bytes(manifest_bytes),
        "file_count": len(files) + 1,
        "gates": gate_summary(results) if results else "skipped",
        "model_eval": "not_run",
        "uploaded": False,
        "note": "built locally; this script never uploads, pushes, tags or publishes",
    }
    descriptor_path.write_bytes((json.dumps(descriptor, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"built {zip_path.name} ({descriptor['zip_size']} bytes, {descriptor['file_count']} files) sha256={zip_sha[:16]}...")
    print(f"descriptor {descriptor_path.name}: releasable={str(releasable).lower()}, uploaded=false")
    if not final:
        print("DRY RUN: not a release. Re-run with --final once every gate passes.")
        if gate_failed or gate_notrun:
            print("note: gates reported FAIL/NOT_RUN above; a final build would be refused.")
    print(f"RESULT: {'PASS' if final or not gate_failed else 'WARN'} release build ({descriptor['mode']})")
    return C.EXIT_OK


# --------------------------------------------------------------------------- verify / diff / local changes


def read_manifest_from_zip(archive: zipfile.ZipFile) -> tuple[dict | None, str | None, str | None]:
    names = [n for n in archive.namelist() if n.endswith("/" + MANIFEST_NAME) and n.count("/") == 1]
    if len(names) != 1:
        return None, None, "archive must contain exactly one top-level release-manifest.json"
    top = names[0].split("/", 1)[0]
    try:
        return json.loads(archive.read(names[0]).decode("utf-8")), top, None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, top, "embedded release-manifest.json is not valid JSON"


def verify_zip(zip_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"cannot open archive: {exc}"]
    with archive:
        bad = archive.testzip()
        if bad:
            errors.append(f"corrupt member: {bad}")
        for name in archive.namelist():
            if name.startswith("/") or ".." in Path(name).parts or re.match(r"^[A-Za-z]:", name):
                errors.append(f"unsafe member path: {name}")
        manifest, top, error = read_manifest_from_zip(archive)
        if error or manifest is None or top is None:
            return errors + [error or "manifest missing"]
        listed = {e["path"]: e for e in manifest.get("files", [])}
        actual = {n[len(top) + 1:] for n in archive.namelist() if not n.endswith("/")} - {MANIFEST_NAME}
        for rel in sorted(set(listed) - actual):
            errors.append(f"listed but missing from archive: {rel}")
        for rel in sorted(actual - set(listed)):
            errors.append(f"in archive but not in manifest: {rel}")
        for rel in sorted(set(listed) & actual):
            data = archive.read(f"{top}/{rel}")
            if C.sha256_bytes(data) != listed[rel]["sha256"]:
                errors.append(f"hash mismatch: {rel}")
            elif len(data) != listed[rel]["size"]:
                errors.append(f"size mismatch: {rel}")
        expected_top = f"{PREFIX}-{manifest.get('version')}"
        if top != expected_top:
            errors.append(f"top-level folder '{top}' does not match manifest version ('{expected_top}')")
    side = zip_path.with_name(zip_path.name + ".sha256")
    if side.is_file():
        recorded = side.read_text(encoding="utf-8").split()[0:1]
        if recorded != [C.sha256_file(zip_path)]:
            errors.append(f"{side.name} does not match the archive")
    return errors


def load_file_map(source: Path) -> dict[str, str]:
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            manifest, _, error = read_manifest_from_zip(archive)
        if manifest is None:
            raise ValueError(error or "no manifest in archive")
    else:
        manifest = json.loads(source.read_bytes().decode("utf-8-sig"))
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValueError(f"{source.name} has no 'files' list (a template manifest cannot be diffed)")
    return {e["path"]: e["sha256"] for e in files}


def cmd_verify(args: argparse.Namespace) -> int:
    errors = verify_zip(Path(args.zip))
    for error in errors:
        print(f"  [FAIL] {error}")
    print(f"RESULT: {'FAIL' if errors else 'PASS'} release verify ({len(errors)} problem(s))")
    return C.EXIT_FAIL if errors else C.EXIT_OK


def cmd_diff(args: argparse.Namespace) -> int:
    try:
        old, new = load_file_map(Path(args.old)), load_file_map(Path(args.new))
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return C.EXIT_FAIL
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(p for p in set(old) & set(new) if old[p] != new[p])
    for label, items in (("added", added), ("removed", removed), ("changed", changed)):
        print(f"{label} ({len(items)}):")
        for item in items:
            print(f"  {item}")
    print(f"RESULT: PASS release diff ({len(added)} added, {len(removed)} removed, {len(changed)} changed)")
    return C.EXIT_OK


def cmd_local_changes(args: argparse.Namespace) -> int:
    install = Path(args.dir).resolve()
    try:
        expected = load_file_map(Path(args.manifest))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return C.EXIT_FAIL
    if not install.is_dir():
        print("error: --dir is not a directory", file=sys.stderr)
        return C.EXIT_USAGE
    modified, missing = [], []
    for rel, digest in sorted(expected.items()):
        path = install / rel
        if not path.is_file():
            missing.append(rel)
        elif C.sha256_file(path) != digest:
            modified.append(rel)
    protected = ("projects/", "_work/", ".git/")
    extra = [r for r in C.list_files(install, use_git=False) if r not in expected and r != MANIFEST_NAME and not r.startswith(protected)]
    print(f"modified ({len(modified)}):")
    print("".join(f"  {m}\n" for m in modified), end="")
    print(f"missing ({len(missing)}):")
    print("".join(f"  {m}\n" for m in missing), end="")
    print(f"extra, not in the release ({len(extra)}; student projects under projects/ are never listed or touched):")
    print("".join(f"  {m}\n" for m in extra), end="")
    print(f"RESULT: PASS local-changes inventory ({len(modified)} modified, {len(missing)} missing, {len(extra)} extra)")
    return C.EXIT_OK


# --------------------------------------------------------------------------- plan printer

UPDATE_STEPS = [
    ("inventory", "Inventory local changes against the installed release", "python scripts/release.py local-changes --manifest <installed>/release-manifest.json --dir <installed>"),
    ("fetch", "Fetch the desired release into a STAGING folder (never over the installed tree)", "download <name>-<target>.zip + .sha256 into <staging>; then: python scripts/release.py verify <zip>"),
    ("compare", "Compare manifest, rights/BOM, security notes and support matrix", "python scripts/release.py diff <installed>/release-manifest.json <staging>/<name>-<target>.zip ; read CHANGELOG.md and docs/BOM.md of the target"),
    ("backup", "Back up the installed tree and the lock files (dependencies + schema), not the student projects", "copy <installed> to <backup>/<current>/ (keep uv.lock / package lock files)"),
    ("migrate-dry-run", "Dry-run schema migrations on COPIES of project data; each migration is versioned, idempotent and reports field loss", "run the migration tool in report mode on a copy of projects/"),
    ("gates", "Run the deterministic gates on the staged release", "python scripts/run_all_checks.py --root <staging>/<name>-<target>"),
    ("promote", "Promote atomically (rename/swap), never partial file-by-file overwrite", "swap <installed> and <staging> directories in one rename step"),
    ("rerender", "Re-render the fixture and check it", "run the setup-gate fixture; doctor must be green only if the final-output gates ran"),
    ("offer-rollback", "Offer rollback and keep the backup until the student accepts", "see the rollback plan"),
]
ROLLBACK_STEPS = [
    ("stop", "Stop any running heavy job (release the render lock) before touching files"),
    ("restore", "Restore the previous release folder from <backup>/<current>/ (code, locks, schema, runnable dependencies - not only code)"),
    ("verify", "python scripts/release.py verify <backup zip> or re-run local-changes against the previous manifest"),
    ("rerender", "Re-render the fixture with the restored release"),
    ("keep", "Keep the failed target release in staging for the support bundle (redacted: no keys, no client media)"),
]
NEVER_OVERWRITE = [
    "student projects (projects/<name>/ source, hf, final, _work)",
    "original source media",
    "unrelated agent settings (.claude/settings*.json, Codex configuration)",
    "shared caches (model weights, ASR/matte caches, uv cache)",
]


def build_plan(current: str | None, target: str) -> dict:
    return {
        "from": current,
        "to": target,
        "executes_anything": False,
        "update": [{"step": i, "id": sid, "what": what, "how": how} for i, (sid, what, how) in enumerate(UPDATE_STEPS, 1)],
        "rollback": [{"step": i, "id": sid, "what": what} for i, (sid, what) in enumerate(ROLLBACK_STEPS, 1)],
        "never_overwrite": NEVER_OVERWRITE,
        "rules": [
            "Releases are immutable: a correction is a new release, never an edited archive.",
            "SemVer 2.0.0 with a curated changelog (keep-a-changelog 1.1.0 pattern).",
            "Nothing in this plan is executed or uploaded by scripts/release.py.",
        ],
        "source": "REPO_ARCHITECTURE section 10 (research T20 section 9)",
    }


def cmd_plan(args: argparse.Namespace) -> int:
    for label, value in (("--current", args.current), ("--target", args.target)):
        if value and not C.SEMVER_RE.match(value):
            print(f"error: {label} must be SemVer", file=sys.stderr)
            return C.EXIT_USAGE
    plan = build_plan(args.current, args.target)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return C.EXIT_OK
    print(f"UPDATE PLAN {args.current or '<installed>'} -> {args.target}  (printer only: nothing is executed or uploaded)")
    for item in plan["update"]:
        print(f"  {item['step']}. [{item['id']}] {item['what']}")
        print(f"       {item['how']}")
    print("ROLLBACK PLAN")
    for item in plan["rollback"]:
        print(f"  {item['step']}. [{item['id']}] {item['what']}")
    print("NEVER OVERWRITE: " + "; ".join(NEVER_OVERWRITE))
    print("RESULT: PASS release plan")
    return C.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run release builder and update/rollback plan printer (never uploads).")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="gates + deterministic ZIP + manifest + checksums")
    build.add_argument("--root", default=None)
    build.add_argument("--version", required=True)
    build.add_argument("--final", action="store_true", help="enforce release rules (default is a dry run)")
    build.add_argument("--out-dir", default=None)
    build.add_argument("--skip-gates", action="store_true", help="dry run only: do not run the gates")
    build.add_argument("--register", default=None, help="LICENSE_REGISTER.csv for BOM reconciliation")
    build.add_argument("--no-git", action="store_true")
    build.set_defaults(func=cmd_build)
    plan = sub.add_parser("plan", help="print the update and rollback plan")
    plan.add_argument("--current", default=None)
    plan.add_argument("--target", required=True)
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=cmd_plan)
    verify = sub.add_parser("verify", help="verify a release ZIP against its embedded manifest")
    verify.add_argument("zip")
    verify.set_defaults(func=cmd_verify)
    diff = sub.add_parser("diff", help="diff two release manifests or ZIPs")
    diff.add_argument("old")
    diff.add_argument("new")
    diff.set_defaults(func=cmd_diff)
    local = sub.add_parser("local-changes", help="list installed files that differ from a manifest")
    local.add_argument("--manifest", required=True)
    local.add_argument("--dir", required=True)
    local.set_defaults(func=cmd_local_changes)
    return parser


def main(argv: list[str] | None = None) -> int:
    C.setup_utf8()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

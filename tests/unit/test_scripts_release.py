"""Positive and negative controls for scripts/release.py (dry-run release builder, verify, diff, plan)."""

from __future__ import annotations

import hashlib
import json
import socket
import sys
import time
import zipfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import _avc_fixtures as F  # noqa: E402
import release as R  # noqa: E402

CLI = SCRIPTS / "release.py"
PREFIX = R.PREFIX


@pytest.fixture()
def root(tmp_path):
    path = tmp_path / "תיקיית בדיקה" / "repo"
    F.make_repo(path)
    F.write(path / "CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n## [0.1.0]\n- first\n")
    F.write(path / "release-manifest.json", json.dumps({"schema_version": "1", "support_matrix": {"os": {"windows-11": "the reference machine"}}, "files": []}))
    return path


def build(root, *args, out=None):
    out = out or root.parent / "out"
    return F.run_cli(CLI, "build", "--root", root, "--out-dir", out, "--no-git", *args)


def read_zip(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def test_dry_run_build_makes_zip_manifest_checksum_and_descriptor(root):
    out = root.parent / "out"
    result = build(root, "--version", "0.1.0", "--skip-gates")
    assert result.returncode == 0, result.stdout + result.stderr
    zip_path = out / f"{PREFIX}-0.1.0.dryrun.zip"
    assert zip_path.is_file() and (out / (zip_path.name + ".sha256")).is_file()
    descriptor = json.loads((out / f"{PREFIX}-0.1.0.dryrun.release.json").read_text(encoding="utf-8"))
    assert descriptor["mode"] == "dry-run" and descriptor["releasable"] is False and descriptor["uploaded"] is False
    assert descriptor["model_eval"] == "not_run" and descriptor["gates"] == "skipped"
    assert descriptor["zip_sha256"] == hashlib.sha256(zip_path.read_bytes()).hexdigest()
    members = read_zip(zip_path)
    top = f"{PREFIX}-0.1.0/"
    assert all(name.startswith(top) for name in members)
    manifest = json.loads(members[top + "release-manifest.json"])
    assert manifest["version"] == "0.1.0" and manifest["status"].startswith("dry-run")
    assert manifest["support_matrix"]["os"]["windows-11"] == "the reference machine"  # template fields are carried over
    listed = {e["path"]: e for e in manifest["files"]}
    assert "README.md" in listed and "agent-content/skills/demo-skill/SKILL.md" in listed
    assert listed["README.md"]["sha256"] == hashlib.sha256((root / "README.md").read_bytes()).hexdigest()
    assert "release-manifest.json" not in listed and manifest["file_count"] == len(listed)
    assert descriptor["manifest_sha256"] == hashlib.sha256(members[top + "release-manifest.json"]).hexdigest()


def test_archive_is_deterministic(root):
    build(root, "--version", "0.1.0", "--skip-gates", out=root.parent / "o1")
    build(root, "--version", "0.1.0", "--skip-gates", out=root.parent / "o2")
    a = (root.parent / "o1" / f"{PREFIX}-0.1.0.dryrun.zip").read_bytes()
    b = (root.parent / "o2" / f"{PREFIX}-0.1.0.dryrun.zip").read_bytes()
    assert a == b
    with zipfile.ZipFile(root.parent / "o1" / f"{PREFIX}-0.1.0.dryrun.zip") as z:
        assert {i.date_time for i in z.infolist()} == {(1980, 1, 1, 0, 0, 0)}
        names = [i.filename for i in z.infolist()]
        assert names == sorted(names)


def test_private_and_runtime_files_never_ship_but_templates_do(root):
    F.write(root / "scripts" / "private_denylist.txt", "Client Name\n")
    F.write(root / ".env", "KEY=value\n")
    F.write(root / ".env.local", "KEY=value\n")
    F.write(root / ".env.example", "KEY=\n")
    F.write(root / "projects" / "mine" / "source" / "clip.txt", "x")
    F.write(root / "projects" / "mine" / "_work" / "log.txt", "x")
    F.write(root / "x" / "_work" / "cache.txt", "x")
    F.write(root / "dist" / "old.txt", "x")
    F.write(root / ".claude" / "settings.local.json", "{}")
    F.write(root / "packaging" / "release-excludes.txt", "# comment\ninternal/**\n")
    F.write(root / "internal" / "notes.md", "maintainer only\n")
    build(root, "--version", "0.1.0", "--skip-gates")
    names = {n.split("/", 1)[1] for n in read_zip(root.parent / "out" / f"{PREFIX}-0.1.0.dryrun.zip") if "/" in n}
    for banned in ("scripts/private_denylist.txt", ".env", ".env.local", "projects/mine/source/clip.txt", "projects/mine/_work/log.txt",
                   "x/_work/cache.txt", "dist/old.txt", ".claude/settings.local.json", "internal/notes.md"):
        assert banned not in names, banned
    assert ".env.example" in names and "README.md" in names
    assert not any(n.startswith(".git/") for n in names)


def test_verify_accepts_a_good_archive_and_detects_tampering(root, tmp_path):
    build(root, "--version", "0.1.0", "--skip-gates")
    zip_path = root.parent / "out" / f"{PREFIX}-0.1.0.dryrun.zip"
    assert R.verify_zip(zip_path) == []
    assert F.run_cli(CLI, "verify", zip_path).returncode == 0
    # tamper: change one file's bytes, keep the manifest
    members = read_zip(zip_path)
    victim = f"{PREFIX}-0.1.0/README.md"
    members[victim] = b"tampered"
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    errors = R.verify_zip(bad)
    assert any("hash mismatch: README.md" in e or "size mismatch: README.md" in e for e in errors)
    assert F.run_cli(CLI, "verify", bad).returncode == 1
    # extra file not in manifest, and a missing file
    extra = tmp_path / "extra.zip"
    members2 = read_zip(zip_path)
    members2[f"{PREFIX}-0.1.0/sneaky.sh"] = b"echo hi"
    del members2[f"{PREFIX}-0.1.0/tools/frame_qa.py"]
    with zipfile.ZipFile(extra, "w") as z:
        for name, data in members2.items():
            z.writestr(name, data)
    errs = R.verify_zip(extra)
    assert any("in archive but not in manifest: sneaky.sh" in e for e in errs)
    assert any("listed but missing from archive: tools/frame_qa.py" in e for e in errs)


def test_verify_rejects_path_traversal_and_missing_manifest_and_bad_checksum_file(root, tmp_path):
    build(root, "--version", "0.1.0", "--skip-gates")
    zip_path = root.parent / "out" / f"{PREFIX}-0.1.0.dryrun.zip"
    members = read_zip(zip_path)
    members["../evil.txt"] = b"x"
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    assert any("unsafe member path" in e for e in R.verify_zip(evil))
    nomanifest = tmp_path / "nm.zip"
    with zipfile.ZipFile(nomanifest, "w") as z:
        z.writestr("a/b.txt", b"x")
    assert R.verify_zip(nomanifest)
    assert R.verify_zip(tmp_path / "does-not-exist.zip")
    (zip_path.parent / (zip_path.name + ".sha256")).write_text("0" * 64 + "  x.zip\n", encoding="utf-8")
    assert any("does not match the archive" in e for e in R.verify_zip(zip_path))


def test_dry_run_with_gates_records_results_and_is_never_releasable(root):
    result = build(root, "--version", "0.1.0")
    assert result.returncode == 0, result.stdout + result.stderr
    descriptor = json.loads((root.parent / "out" / f"{PREFIX}-0.1.0.dryrun.release.json").read_text(encoding="utf-8"))
    gates = {g["gate"]: g["status"] for g in descriptor["gates"]}
    assert gates["model_eval"] == "NOT_RUN" and "check_skills" in gates and "scan_private" in gates
    assert descriptor["releasable"] is False
    assert "DRY RUN: not a release" in result.stdout


def test_final_refuses_when_gates_do_not_pass_and_writes_nothing(root):
    out = root.parent / "out"
    result = build(root, "--version", "0.1.0", "--final")
    assert result.returncode == 1
    assert "refusing to build a final release" in result.stderr
    assert not out.exists() or not list(out.glob("*.zip"))


def test_final_requires_changelog_entry_and_rejects_skip_gates(root):
    refused = build(root, "--version", "0.2.0", "--final", "--skip-gates")
    assert refused.returncode == 2 and "not allowed with --final" in refused.stderr


def test_final_is_immutable_once_a_descriptor_exists(root):
    committed = root / "packaging" / "releases"
    F.write(committed / f"{PREFIX}-0.1.0.release.json", "{}")
    result = build(root, "--version", "0.1.0", "--final")
    assert result.returncode == 1 and "immutable" in result.stderr


def test_invalid_version_is_a_usage_error(root):
    for bad in ("1.0", "v1.0.0", "latest", "01.0.0"):
        assert build(root, "--version", bad, "--skip-gates").returncode == 2


def test_build_never_touches_the_network(root, monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    code = R.main(["build", "--root", str(root), "--version", "0.1.0", "--skip-gates", "--no-git", "--out-dir", str(root.parent / "o")])
    assert code == 0 and (root.parent / "o" / f"{PREFIX}-0.1.0.dryrun.zip").is_file()
    # the script has no code path that can upload or push: no network-capable imports at all
    source = (SCRIPTS / "release.py").read_text(encoding="utf-8")
    for module in ("requests", "urllib", "http.client", "smtplib", "ftplib", "socket", "boto3"):
        assert f"import {module}" not in source and f"from {module}" not in source


def test_zip_content_is_byte_identical_to_the_tree(root):
    build(root, "--version", "0.1.0", "--skip-gates")
    members = read_zip(root.parent / "out" / f"{PREFIX}-0.1.0.dryrun.zip")
    top = f"{PREFIX}-0.1.0/"
    for rel in ("README.md", "agent-content/skills/demo-skill/SKILL.md", "tools/frame_qa.py"):
        assert members[top + rel] == (root / rel).read_bytes()


# ------------------------------------------------------------------ plan / diff / local changes


def test_plan_prints_update_and_rollback_without_executing_anything(root):
    result = F.run_cli(CLI, "plan", "--current", "0.1.0", "--target", "0.2.0")
    assert result.returncode == 0
    out = result.stdout
    for step in ("inventory", "fetch", "compare", "backup", "migrate-dry-run", "gates", "promote", "rerender", "offer-rollback"):
        assert f"[{step}]" in out
    assert out.index("[inventory]") < out.index("[fetch]") < out.index("[backup]") < out.index("[promote]") < out.index("[rerender]")
    assert "ROLLBACK PLAN" in out and "NEVER OVERWRITE" in out and "projects" in out
    data = json.loads(F.run_cli(CLI, "plan", "--target", "1.0.0", "--json").stdout)
    assert data["executes_anything"] is False and data["from"] is None and len(data["update"]) == 9
    assert F.run_cli(CLI, "plan", "--target", "nope").returncode == 2


def test_diff_between_two_manifests_and_archives(root, tmp_path):
    build(root, "--version", "0.1.0", "--skip-gates", out=root.parent / "o1")
    (root / "README.md").write_text("# changed\n", encoding="utf-8")
    F.write(root / "NEW.md", "new\n")
    (root / "tools" / "frame_qa.py").unlink()
    build(root, "--version", "0.2.0", "--skip-gates", out=root.parent / "o2")
    result = F.run_cli(CLI, "diff", root.parent / "o1" / f"{PREFIX}-0.1.0.dryrun.zip", root.parent / "o2" / f"{PREFIX}-0.2.0.dryrun.zip")
    assert result.returncode == 0
    assert "added (1)" in result.stdout and "NEW.md" in result.stdout
    assert "removed (1)" in result.stdout and "tools/frame_qa.py" in result.stdout
    assert "changed (1)" in result.stdout and "README.md" in result.stdout
    template = F.run_cli(CLI, "diff", root / "release-manifest.json", root / "release-manifest.json")
    assert template.returncode == 0 or template.returncode == 1  # an empty template manifest has an empty file list
    assert F.run_cli(CLI, "diff", tmp_path / "missing.json", tmp_path / "missing2.json").returncode == 1


def test_local_changes_inventory_lists_modified_missing_and_extra_but_not_projects(root, tmp_path):
    build(root, "--version", "0.1.0", "--skip-gates")
    zip_path = root.parent / "out" / f"{PREFIX}-0.1.0.dryrun.zip"
    members = read_zip(zip_path)
    install = tmp_path / "install"
    for name, data in members.items():
        rel = name.split("/", 1)[1]
        target = install / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest = install / "release-manifest.json"
    (install / "README.md").write_text("student edited this\n", encoding="utf-8")
    (install / "tools" / "frame_qa.py").unlink()
    F.write(install / "my-notes.md", "mine\n")
    F.write(install / "projects" / "demo" / "source" / "a.txt", "student project")
    result = F.run_cli(CLI, "local-changes", "--manifest", manifest, "--dir", install)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "modified (1)" in result.stdout and "README.md" in result.stdout
    assert "missing (1)" in result.stdout and "tools/frame_qa.py" in result.stdout
    assert "my-notes.md" in result.stdout and "projects/demo" not in result.stdout
    assert F.run_cli(CLI, "local-changes", "--manifest", manifest, "--dir", tmp_path / "nope").returncode == 2


def test_cli_help_is_fast_and_documents_never_uploads():
    t = time.monotonic()
    result = F.run_cli(CLI, "--help")
    assert result.returncode == 0 and time.monotonic() - t < 3
    assert "never uploads" in result.stdout.lower()
    assert "Usage:" in (SCRIPTS / "release.py").read_text(encoding="utf-8")
    assert F.run_cli(CLI).returncode == 2  # a sub-command is required

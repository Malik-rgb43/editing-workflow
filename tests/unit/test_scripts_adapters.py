"""Positive and negative controls for scripts/build_agent_adapters.py (package parity)."""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import _avc_common as C  # noqa: E402
import _avc_fixtures as F  # noqa: E402
import build_agent_adapters as B  # noqa: E402

CLI = SCRIPTS / "build_agent_adapters.py"


@pytest.fixture()
def root(tmp_path):
    path = tmp_path / "תיקיית בדיקה" / "repo"
    F.make_skill(path, "demo-skill")
    F.make_skill(path, "second-skill", references=("references/a.md", "references/b.md"))
    # a binary-ish file and Hebrew text must survive byte for byte
    F.write(path / "agent-content" / "skills" / "demo-skill" / "references" / "he.md", "# עברית\n\nשלום עולם\n")
    (path / "agent-content" / "skills" / "demo-skill" / "references" / "blob.bin").write_bytes(bytes(range(256)))
    return path


def codes(report):
    return {f.code for f in report.fails}


def tree(path):
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in sorted(path.rglob("*")) if p.is_file()}


def test_build_creates_byte_identical_copies_with_marker(root):
    report = B.build(root)
    assert report.fails == [] and report.stats["skills"] == 2
    for target in (".claude/skills", ".agents/skills"):
        for name in ("demo-skill", "second-skill"):
            canon = tree(root / "agent-content" / "skills" / name)
            gen = tree(root / target / name)
            marker = gen.pop(B.MARKER)
            gen.pop("agents/openai.yaml", None)
            assert gen == canon  # byte for byte
            assert b"DO NOT EDIT" in marker and f"agent-content/skills/{name}/".encode() in marker
    assert (root / ".claude/skills/demo-skill/references/blob.bin").read_bytes() == bytes(range(256))


def test_codex_yaml_is_only_in_agents_copy_with_implicit_invocation_disabled(root):
    B.build(root)
    assert not (root / ".claude/skills/demo-skill/agents/openai.yaml").exists()
    yaml = (root / ".agents/skills/demo-skill/agents/openai.yaml").read_text(encoding="utf-8")
    assert "allow_implicit_invocation: false" in yaml and "allow_implicit_invocation: true" not in yaml
    assert "Demo Skill" in yaml
    shutil.rmtree(root / ".agents")
    B.build(root, codex_yaml=False)
    assert not (root / ".agents/skills/demo-skill/agents/openai.yaml").exists()


def test_canonical_openai_yaml_is_copied_unchanged(root):
    custom = "interface:\n  display_name: Custom\npolicy:\n  allow_implicit_invocation: false\n"
    F.write(root / "agent-content/skills/demo-skill/agents/openai.yaml", custom)
    B.build(root)
    assert (root / ".agents/skills/demo-skill/agents/openai.yaml").read_text(encoding="utf-8") == custom
    assert (root / ".claude/skills/demo-skill/agents/openai.yaml").read_text(encoding="utf-8") == custom
    assert B.check(root).fails == []


def test_check_passes_after_build_and_is_read_only(root):
    B.build(root)
    before = {p: tree(root / p) for p in (".claude", ".agents")}
    report = B.check(root)
    assert report.status == C.PASS and report.fails == []
    assert before == {p: tree(root / p) for p in (".claude", ".agents")}


def test_check_fails_when_generated_folders_are_missing(root):
    assert "adapter-missing" in codes(B.check(root))


@pytest.mark.parametrize(
    "mutate,expected",
    [
        (lambda r: (r / ".claude/skills/demo-skill/SKILL.md").write_bytes(b"hand edited"), "adapter-bytes-differ"),
        (lambda r: (r / ".agents/skills/demo-skill/references/he.md").write_text("שונה", encoding="utf-8"), "adapter-bytes-differ"),
        (lambda r: (r / ".claude/skills/demo-skill/references/guide.md").unlink(), "adapter-file-missing"),
        (lambda r: (r / ".claude/skills/demo-skill/extra.txt").write_text("x", encoding="utf-8"), "adapter-file-extra"),
        (lambda r: (r / ".agents/skills/demo-skill" / B.MARKER).unlink(), "adapter-unmarked"),
        (lambda r: (r / ".claude/skills/demo-skill" / B.MARKER).write_text("tampered", encoding="utf-8"), "adapter-bytes-differ"),
        (lambda r: (r / ".agents/skills/demo-skill/agents/openai.yaml").write_text("policy:\n  allow_implicit_invocation: true\n", encoding="utf-8"), "adapter-bytes-differ"),
        (lambda r: shutil.rmtree(r / ".agents/skills/second-skill"), "adapter-missing"),
    ],
)
def test_check_detects_drift(root, mutate, expected):
    B.build(root)
    mutate(root)
    report = B.check(root)
    assert report.status == C.FAIL and expected in codes(report), [f.render() for f in report.findings]


def test_canonical_change_without_rebuild_is_drift(root):
    B.build(root)
    skill_md = root / "agent-content/skills/demo-skill/SKILL.md"
    skill_md.write_text(skill_md.read_text(encoding="utf-8") + "\nnew line\n", encoding="utf-8")
    assert "adapter-bytes-differ" in codes(B.check(root))
    B.build(root)
    assert B.check(root).fails == []


def test_stale_generated_folder_is_detected_and_removed_but_unmarked_is_never_touched(root):
    B.build(root)
    shutil.rmtree(root / "agent-content/skills/second-skill")
    assert "adapter-stale" in codes(B.check(root))
    B.build(root)
    assert not (root / ".claude/skills/second-skill").exists() and not (root / ".agents/skills/second-skill").exists()
    # a hand-made skill (no marker) in the generated root is neither flagged nor deleted
    F.write(root / ".claude/skills/my-own/SKILL.md", "---\nname: my-own\n---\n")
    assert B.check(root).fails == []
    B.build(root)
    assert (root / ".claude/skills/my-own/SKILL.md").exists()


def test_build_refuses_to_overwrite_an_unmarked_conflicting_folder(root):
    F.write(root / ".claude/skills/demo-skill/SKILL.md", "my hand-written version\n")
    report = B.build(root)
    assert "adapter-unmarked" in codes(report)
    assert (root / ".claude/skills/demo-skill/SKILL.md").read_text(encoding="utf-8") == "my hand-written version\n"
    assert B.check(root).status == C.FAIL


def test_ignored_noise_is_not_copied_and_symlink_free(root):
    F.write(root / "agent-content/skills/demo-skill/__pycache__/x.pyc", "x")
    F.write(root / "agent-content/skills/demo-skill/.DS_Store", "x")
    B.build(root)
    assert not (root / ".claude/skills/demo-skill/__pycache__").exists()
    assert not (root / ".claude/skills/demo-skill/.DS_Store").exists()
    assert B.check(root).fails == []
    assert not any(p.is_symlink() for p in (root / ".claude").rglob("*"))


def test_skill_folders_without_skill_md_and_underscore_folders_are_ignored(root):
    (root / "agent-content/skills/not-a-skill").mkdir()
    F.write(root / "agent-content/skills/_template/SKILL.md", "x")
    F.write(root / "agent-content/skills/README.md", "x")
    B.build(root)
    assert sorted(p.name for p in (root / ".claude/skills").iterdir()) == ["demo-skill", "second-skill"]


def test_no_canonical_skills_is_not_run(tmp_path):
    (tmp_path / "agent-content" / "skills").mkdir(parents=True)
    assert B.check(tmp_path).status == C.NOT_RUN
    assert B.build(tmp_path).status == C.NOT_RUN


def test_generation_is_deterministic(root):
    B.build(root)
    first = {p: tree(root / p) for p in (".claude", ".agents")}
    B.build(root)
    assert first == {p: tree(root / p) for p in (".claude", ".agents")}


def test_cli_modes_and_exit_codes(root):
    t = time.monotonic()
    assert F.run_cli(CLI, "--help").returncode == 0 and time.monotonic() - t < 3
    drift = F.run_cli(CLI, "--root", root, "--check")
    assert drift.returncode == 1 and "adapter-missing" in drift.stdout
    built = F.run_cli(CLI, "--root", root)
    assert built.returncode == 0, built.stdout
    ok = F.run_cli(CLI, "--root", root, "--check", "--json")
    assert ok.returncode == 0 and json.loads(ok.stdout)["status"] == "PASS"
    (root / ".claude/skills/demo-skill/SKILL.md").write_bytes(b"edited")
    assert F.run_cli(CLI, "--root", root, "--check").returncode == 1
    empty = root.parent / "empty"
    empty.mkdir()
    assert F.run_cli(CLI, "--root", empty, "--check").returncode == 0
    assert F.run_cli(CLI, "--root", empty, "--check", "--strict").returncode == 3
    assert F.run_cli(CLI, "--root", root / "nope").returncode == 2

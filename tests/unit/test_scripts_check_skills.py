"""Positive and negative controls for scripts/check_skills.py."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import _avc_common as C  # noqa: E402
import _avc_fixtures as F  # noqa: E402
import check_skills  # noqa: E402

SCRIPT = SCRIPTS / "check_skills.py"


def codes(report, level="FAIL"):
    return {f.code for f in report.findings if f.level == level}


@pytest.fixture()
def root(tmp_path):
    return tmp_path / "תיקיית בדיקה" / "repo"  # Hebrew path on purpose (spaces + Hebrew)


def test_valid_skills_pass_with_no_failures(root):
    F.make_repo(root)
    report = check_skills.run(root)
    assert report.fails == [], [f.render() for f in report.fails]
    assert report.stats["skills"] == 2
    assert report.stats["trigger_counts"]["demo-skill"] == "8/4"
    # the denylist part is reported as not run (non-blocking) rather than silently absent
    assert any(p["part"] == "client-denylist" for p in report.not_run_parts)


def test_no_skills_is_not_run_never_pass(root):
    root.mkdir(parents=True)
    report = check_skills.run(root)
    assert report.status == C.NOT_RUN


def test_folder_without_skill_md_fails(root):
    F.make_skill(root, "good-one")
    (root / "agent-content" / "skills" / "empty-one").mkdir()
    assert "skill-md-missing" in codes(check_skills.run(root))


def test_extra_frontmatter_key_fails_portable_rule(root):
    F.make_skill(root, "demo-skill", extra_frontmatter="allowed-tools: Bash\n")
    assert "frontmatter-keys" in codes(check_skills.run(root))


def test_name_must_equal_folder(root):
    skill = F.make_skill(root, "demo-skill")
    text = (skill / "SKILL.md").read_text(encoding="utf-8").replace("name: demo-skill", "name: other-name", 1)
    F.write(skill / "SKILL.md", text)
    assert "name-folder" in codes(check_skills.run(root))


def test_non_kebab_name_fails(root):
    F.make_skill(root, "Bad_Name")
    assert {"name-kebab", "folder-kebab"} <= codes(check_skills.run(root))


def test_description_limits(root):
    base = "Cut clips. Use for עריכת וידאו. NOT for colour grading (use color-fix). "
    F.make_skill(root, "demo-skill", description=base + "x" * 450)  # > 500 but < 1024
    r = check_skills.run(root)
    assert "description-long" in codes(r, "WARN") and "description-too-long" not in codes(r)
    F.make_skill(root, "demo-skill", description=base + "x" * 1000)
    assert "description-too-long" in codes(check_skills.run(root))


def test_workflow_summary_description_warns(root):
    desc = "Edit clips: 1. cut the pauses 2. add captions 3. render. Use for עריכה. NOT for colour (use color-fix)."
    F.make_skill(root, "demo-skill", description=desc)
    assert "description-workflow" in codes(check_skills.run(root), "WARN")
    desc2 = "Edit clips; first transcribe, then cut, and finally render. Use for עריכה. NOT for colour (use color-fix)."
    F.make_skill(root, "demo-skill", description=desc2)
    assert "description-workflow" in codes(check_skills.run(root), "WARN")


def test_description_without_hebrew_or_exclusion_warns(root):
    F.make_skill(root, "demo-skill", description="Cut and caption clips for reels.")
    warns = codes(check_skills.run(root), "WARN")
    assert {"description-hebrew", "description-not-for"} <= warns


def test_body_line_budget(root):
    F.make_skill(root, "demo-skill", body_lines=200)
    r = check_skills.run(root)
    assert "body-long" in codes(r, "WARN") and "body-too-long" not in codes(r)
    F.make_skill(root, "demo-skill", body_lines=320)
    assert "body-too-long" in codes(check_skills.run(root))


def test_reference_link_must_resolve_and_orphans_fail(root):
    skill = F.make_skill(root, "demo-skill")
    F.write(skill / "SKILL.md", (skill / "SKILL.md").read_text(encoding="utf-8") + "\nSee [more](references/ghost.md) and `references/phantom.md`.\n")
    r = check_skills.run(root)
    assert "reference-missing" in codes(r)
    skill2 = F.make_skill(root / "x", "demo-skill")
    F.write(skill2 / "references" / "unlisted.md", "# not mentioned\n")
    assert "reference-orphan" in codes(check_skills.run(root / "x"))


def test_agent_content_path_mentions_are_checked(root):
    skill = F.make_skill(root, "demo-skill")
    F.write(skill / "SKILL.md", (skill / "SKILL.md").read_text(encoding="utf-8") + "\nPlaybook: `agent-content/playbooks/wf-99-nothing.md`.\n")
    assert "reference-missing" in codes(check_skills.run(root))
    F.write(root / "agent-content" / "playbooks" / "wf-99-nothing.md", "# x\n")
    assert "reference-missing" not in codes(check_skills.run(root))


def test_load_when_required_on_the_line_or_under_a_heading(root):
    F.make_skill(root, "demo-skill", ref_line_suffix=" - details")  # no condition anywhere
    assert "reference-load-when" in codes(check_skills.run(root))
    skill = F.make_skill(root / "y", "demo-skill", ref_line_suffix=" - details")
    text = (skill / "SKILL.md").read_text(encoding="utf-8").replace("## References", "## References (load when)")
    F.write(skill / "SKILL.md", text)
    assert "reference-load-when" not in codes(check_skills.run(root / "y"))


def test_fenced_examples_are_not_resolved(root):
    skill = F.make_skill(root, "demo-skill")
    F.write(skill / "SKILL.md", (skill / "SKILL.md").read_text(encoding="utf-8") + "\n```text\nreferences/imaginary.md\n```\n")
    assert "reference-missing" not in codes(check_skills.run(root))


def test_eval_files_required_and_counted(root):
    F.make_skill(root, "demo-skill", with_triggers=False)
    assert "evals-triggers-missing" in codes(check_skills.run(root))
    F.make_skill(root / "a", "demo-skill", positive=7)
    assert "trigger-count-positive" in codes(check_skills.run(root / "a"))
    F.make_skill(root / "b", "demo-skill", negative=3)
    assert "trigger-count-negative" in codes(check_skills.run(root / "b"))
    F.make_skill(root / "c", "demo-skill", with_tasks=False)
    assert "evals-tasks-missing" in codes(check_skills.run(root / "c"))
    F.make_skill(root / "d", "demo-skill", tasks=2)
    assert "evals-tasks-count" in codes(check_skills.run(root / "d"))


def test_hebrew_trigger_file_is_required_and_real(root):
    skill = F.make_skill(root, "demo-skill")
    english_only = F.triggers_text(hebrew=False, positive=5, negative=3)
    english_only += "".join(json.dumps({"prompt": f"extra case number {i}", "should_trigger": i < 3, "route_instead": None}) + "\n" for i in range(6))
    F.write(skill / "evals" / "triggers.jsonl", english_only)
    r = check_skills.run(root)
    assert {"trigger-hebrew-positive", "trigger-hebrew-negative"} <= codes(r)
    moji = "תערוך לי".encode("utf-8").decode("cp1252", errors="replace")
    F.write(skill / "evals" / "triggers.jsonl", F.triggers_text() + json.dumps({"prompt": moji, "should_trigger": True, "route_instead": None}, ensure_ascii=False) + "\n")
    assert "trigger-mojibake" in codes(check_skills.run(root))


def test_task_sections_missing_fields_warn(root):
    skill = F.make_skill(root, "demo-skill")
    F.write(skill / "evals" / "tasks.md", "# T\n\n## Task 1: a\nnothing here\n\n## Task 2: b\nnothing\n\n## Task 3: c\nnothing\n")
    assert "evals-task-field" in codes(check_skills.run(root), "WARN")


def test_version_rules(root):
    F.make_skill(root, "demo-skill", version_line="version: 0.1.0")
    r = check_skills.run(root)
    assert "metadata-version-quote" in codes(r, "WARN") and "metadata-version" not in codes(r)
    F.make_skill(root / "a", "demo-skill", version_line="version: 1.0")
    assert "metadata-version" in codes(check_skills.run(root / "a"))
    F.make_skill(root / "b", "demo-skill", version_line='version: "latest"')
    assert "metadata-version" in codes(check_skills.run(root / "b"))


def test_missing_metadata_fails(root):
    skill = F.make_skill(root, "demo-skill")
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    head, _, tail = text.partition("metadata:\n")
    tail = tail.split("---\n", 1)[1]
    F.write(skill / "SKILL.md", head + "---\n" + tail)
    assert "metadata-missing" in codes(check_skills.run(root))


def test_bom_in_skill_md_fails(root):
    skill = F.make_skill(root, "demo-skill")
    (skill / "SKILL.md").write_bytes(b"\xef\xbb\xbf" + (skill / "SKILL.md").read_bytes())
    assert "skill-bom" in codes(check_skills.run(root))


def test_private_path_and_client_denylist_inside_a_skill_fail(root):
    skill = F.make_skill(root, "demo-skill")
    leak = "C:" + "\\Users\\" + "somebody" + "\\Videos"
    F.write(skill / "references" / "guide.md", f"# guide\n\nWorks on {leak}.\n")
    r = check_skills.run(root)
    assert "win-user-path" in codes(r)
    assert leak not in " ".join(f.render() for f in r.findings)  # the path itself is never echoed
    # denylist term in a skill file
    root2 = root / "two"
    skill2 = F.make_skill(root2, "demo-skill")
    F.write(root2 / "scripts" / "private_denylist.txt", "Fictional Brand Name\n")
    F.write(skill2 / "references" / "guide.md", "# guide\n\nWe cut a film for Fictional Brand Name.\n")
    r2 = check_skills.run(root2)
    assert "denylist" in codes(r2)
    assert not any(p["part"] == "client-denylist" for p in r2.not_run_parts)


def test_secret_inside_a_skill_fails(root):
    skill = F.make_skill(root, "demo-skill")
    token = "gh" + "p_" + "A1b2C3d4E5" * 4
    F.write(skill / "references" / "guide.md", f"token: {token}\n")
    assert "github-token" in codes(check_skills.run(root))


def test_implicit_invocation_enabled_warns(root):
    skill = F.make_skill(root, "demo-skill")
    F.write(skill / "agents" / "openai.yaml", "policy:\n  allow_implicit_invocation: true\n")
    assert "implicit-invocation" in codes(check_skills.run(root), "WARN")


# ---------------------------------------------------------------- CLI


def test_cli_exit_codes_json_and_speed(root):
    F.make_repo(root)
    start = time.monotonic()
    helped = F.run_cli(SCRIPT, "--help")
    assert helped.returncode == 0 and "Usage" in helped.stdout or "usage" in helped.stdout
    assert time.monotonic() - start < 3
    ok = F.run_cli(SCRIPT, "--root", root, "--json")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    data = json.loads(ok.stdout)
    assert data["tool"] == "check_skills" and data["status"] in ("PASS", "WARN")
    # break one skill -> exit 1
    skill = root / "agent-content" / "skills" / "demo-skill"
    (skill / "evals" / "triggers.jsonl").unlink()
    bad = F.run_cli(SCRIPT, "--root", root)
    assert bad.returncode == 1 and "RESULT: FAIL" in bad.stdout
    # nothing to check -> NOT_RUN: exit 0, --strict exit 3
    empty = root.parent / "empty"
    empty.mkdir()
    assert F.run_cli(SCRIPT, "--root", empty).returncode == 0
    assert F.run_cli(SCRIPT, "--root", empty, "--strict").returncode == 3
    assert F.run_cli(SCRIPT, "--root", root / "does-not-exist").returncode == 2

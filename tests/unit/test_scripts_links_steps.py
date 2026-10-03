"""Positive and negative controls for scripts/check_links.py and scripts/check_step_ids.py."""

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
import check_links as L  # noqa: E402
import check_step_ids as S  # noqa: E402

LINKS_CLI = SCRIPTS / "check_links.py"
STEPS_CLI = SCRIPTS / "check_step_ids.py"


@pytest.fixture()
def root(tmp_path):
    path = tmp_path / "תיקיית בדיקה" / "repo"
    F.write(path / "README.md", "# Repo\n")
    return path


def codes(report, level="FAIL"):
    return {f.code for f in report.findings if f.level == level}


# ------------------------------------------------------------------ links


def test_valid_links_and_mentions_pass(root):
    F.write(root / "docs/en/install.md", "# Install\n\nSee [home](../../README.md), [sibling](other.md#second-heading) and `agent-content/playbooks/wf-00.md`.\n")
    F.write(root / "docs/en/other.md", "# Other\n\n## Second heading\n")
    F.write(root / "agent-content/playbooks/wf-00.md", "# wf-00\n")
    report = L.run(root)
    assert report.status == C.PASS and report.stats["links"] == 2 and report.stats["mentions"] == 1


def test_broken_relative_link_fails_with_line(root):
    F.write(root / "docs/en/a.md", "# A\n\ntext\n[gone](missing.md)\n")
    report = L.run(root)
    finding = next(f for f in report.fails if f.code == "link-broken")
    assert finding.path == "docs/en/a.md" and finding.line == 4


def test_broken_agent_content_mention_fails_in_prose_and_code_span(root):
    F.write(root / "docs/he/a.md", "# א\n\nראו agent-content/skills/ghost/SKILL.md וגם `agent-content/techniques/none.md`.\n")
    report = L.run(root)
    assert sum(1 for f in report.fails if f.code == "mention-broken") == 2


def test_fenced_blocks_http_mailto_and_placeholders_are_skipped(root):
    F.write(
        root / "docs/en/a.md",
        "# A\n\n```text\n[x](nope.md)\nagent-content/nothing.md\n```\n\n[web](https://example.org/x) [mail](mailto:a@example.org)\n"
        "`agent-content/skills/<name>/SKILL.md` and agent-content/playbooks/wf-*.md and agent-content/{a,b}/x.md and agent-content/...\n",
    )
    report = L.run(root)
    assert report.fails == [], [f.render() for f in report.fails]


def test_inline_code_that_looks_like_a_link_is_not_checked(root):
    F.write(root / "docs/en/a.md", "# A\n\nUse `[text](not-a-file.md)` syntax.\n")
    assert L.run(root).fails == []


def test_percent_encoded_hebrew_names_angle_brackets_and_images(root):
    F.write(root / "docs/en/קובץ עברי.md", "# x\n")
    F.write(root / "docs/en/pic.png", "x")
    F.write(root / "docs/en/a.md", "# A\n\n[h](%D7%A7%D7%95%D7%91%D7%A5%20%D7%A2%D7%91%D7%A8%D7%99.md) [h2](<קובץ עברי.md>) ![i](pic.png)\n")
    assert L.run(root).fails == []
    F.write(root / "docs/en/b.md", "# B\n\n![i](missing.png)\n")
    assert "link-broken" in codes(L.run(root))


def test_reference_style_definitions_are_checked(root):
    F.write(root / "docs/en/a.md", "# A\n\n[ref][1]\n\n[1]: gone.md\n")
    assert "link-broken" in codes(L.run(root))


def test_link_escaping_the_root_fails(root):
    F.write(root / "docs/en/a.md", "# A\n\n[out](../../../outside.md)\n")
    assert "link-escapes-root" in codes(L.run(root))


def test_root_relative_link_resolves_from_repo_root(root):
    F.write(root / "docs/en/a.md", "# A\n\n[r](/README.md) [bad](/nothing.md)\n")
    report = L.run(root)
    assert [f.message for f in report.fails if f.code == "link-broken"] == ["'/nothing.md' does not exist"]


def test_missing_anchor_is_only_a_warning(root):
    F.write(root / "docs/en/a.md", "# A\n\n[x](b.md#nope) [y](#also-nope) [ok](#a)\n")
    F.write(root / "docs/en/b.md", "# B\n")
    report = L.run(root)
    assert report.fails == [] and codes(report, "WARN") == {"anchor-missing"} and len(report.warns) == 2


def test_hebrew_heading_anchors_and_explicit_ids(root):
    F.write(root / "docs/he/a.md", "# התקנה\n\n## שלב ראשון {#install-01}\n\n[א](#התקנה) [ב](#install-01)\n")
    assert L.run(root).warns == []


def test_generated_host_copies_are_not_scanned(root):
    F.write(root / ".claude/skills/x/SKILL.md", "[broken](nope.md)\n")
    F.write(root / "docs/en/a.md", "# A\n")
    assert L.run(root).fails == []


def test_paths_option_limits_scope_and_empty_scope_is_not_run(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert L.run(empty).status == C.NOT_RUN
    root = tmp_path / "r"
    F.write(root / "docs/en/a.md", "[x](nope.md)\n")
    F.write(root / "docs/en/b.md", "# fine\n")
    assert L.run(root, ["docs/en/b.md"]).status == C.PASS
    assert L.run(root, ["docs/en/a.md"]).status == C.FAIL


def test_links_cli(root):
    F.write(root / "docs/en/a.md", "# A\n\n[ok](../../README.md)\n")
    t = time.monotonic()
    assert F.run_cli(LINKS_CLI, "--help").returncode == 0 and time.monotonic() - t < 3
    assert F.run_cli(LINKS_CLI, "--root", root).returncode == 0
    F.write(root / "docs/en/b.md", "[bad](zzz.md)\n")
    bad = F.run_cli(LINKS_CLI, "--root", root, "--json")
    assert bad.returncode == 1 and json.loads(bad.stdout)["status"] == "FAIL"
    assert F.run_cli(LINKS_CLI, "--root", root / "nope").returncode == 2
    empty = root.parent / "e"
    empty.mkdir()
    assert F.run_cli(LINKS_CLI, "--root", empty, "--strict").returncode == 3


# ------------------------------------------------------------------ step ids


def test_matching_step_ids_pass(root):
    F.make_docs_pair(root, ("install-01", "install-02", "install-03"))
    report = S.run(root)
    assert report.status == C.PASS and report.stats == {"page_pairs": 1, "step_ids": 3}


def test_heading_attribute_ids_are_supported(root):
    F.write(root / "docs/en/a.md", "# A\n\n## Install {#install-01}\n## Run {#install-02}\n")
    F.write(root / "docs/he/a.md", "# א\n\n## התקנה {#install-01}\n## הרצה {#install-02}\n")
    assert S.run(root).status == C.PASS


@pytest.mark.parametrize(
    "ids_he,expected",
    [
        (("install-01",), "step-ids-differ"),  # step missing in HE
        (("install-01", "install-02", "install-03"), "step-ids-differ"),  # extra in HE
        (("install-01", "install-99"), "step-ids-differ"),  # renamed
        (("install-02", "install-01"), "step-order-differs"),  # reordered
    ],
)
def test_mismatched_ids_fail(root, ids_he, expected):
    F.make_docs_pair(root, ("install-01", "install-02"), ids_he)
    report = S.run(root)
    assert report.status == C.FAIL and expected in codes(report)


def test_duplicate_and_invalid_ids_fail(root):
    F.make_docs_pair(root, ("install-01", "install-01"))
    assert "step-id-duplicate" in codes(S.run(root))
    root2 = root / "two"
    F.make_docs_pair(root2, ("Install_01",))
    assert "step-id-invalid" in codes(S.run(root2))


def test_page_missing_in_one_language_fails(root):
    F.make_docs_pair(root, name="install.md")
    F.write(root / "docs/en/update.md", "# Update\n<!-- step: update-01 -->\n")
    assert "step-page-missing-he" in codes(S.run(root))
    F.write(root / "docs/he/only-he.md", "# רק עברית\n<!-- step: only-01 -->\n")
    assert "step-page-missing-en" in codes(S.run(root))


def test_markers_in_code_fences_are_examples_and_ignored(root):
    F.write(root / "docs/en/a.md", "# A\n\n```markdown\n<!-- step: example-01 -->\n```\n<!-- step: real-01 -->\n")
    F.write(root / "docs/he/a.md", "# א\n\n<!-- step: real-01 -->\n")
    assert S.run(root).status == C.PASS


def test_pages_without_ids_warn_and_untranslated_hebrew_warns(root):
    F.write(root / "docs/en/privacy.md", "# Privacy\n")
    F.write(root / "docs/he/privacy.md", "# Privacy\n")
    report = S.run(root)
    assert report.fails == [] and {"step-none", "step-he-no-hebrew"} <= codes(report, "WARN")


def test_nested_pages_are_paired_by_relative_path(root):
    F.write(root / "docs/en/sub/a.md", "<!-- step: sub-01 -->\n")
    F.write(root / "docs/he/sub/a.md", "<!-- step: sub-01 -->\nעברית\n")
    assert S.run(root).stats["page_pairs"] == 1 and S.run(root).fails == []


def test_missing_docs_dirs_are_not_run(root):
    assert S.run(root).status == C.NOT_RUN
    (root / "docs" / "en").mkdir(parents=True)
    assert S.run(root).status == C.NOT_RUN  # he missing
    (root / "docs" / "he").mkdir(parents=True)
    assert S.run(root).status == C.NOT_RUN  # both empty


def test_hebrew_mojibake_in_he_page_fails(root):
    moji = "שלום".encode("utf-8").decode("cp1252", errors="replace")
    F.write(root / "docs/en/a.md", "<!-- step: a-01 -->\n")
    F.write(root / "docs/he/a.md", f"<!-- step: a-01 -->\n{moji}\n")
    assert "step-he-mojibake" in codes(S.run(root))


def test_steps_cli(root):
    F.make_docs_pair(root)
    t = time.monotonic()
    assert F.run_cli(STEPS_CLI, "--help").returncode == 0 and time.monotonic() - t < 3
    assert F.run_cli(STEPS_CLI, "--root", root).returncode == 0
    F.make_docs_pair(root, ("install-01",), ("install-02",))
    bad = F.run_cli(STEPS_CLI, "--root", root, "--json")
    assert bad.returncode == 1 and json.loads(bad.stdout)["status"] == "FAIL"
    empty = root.parent / "e"
    empty.mkdir()
    assert F.run_cli(STEPS_CLI, "--root", empty).returncode == 0
    assert F.run_cli(STEPS_CLI, "--root", empty, "--strict").returncode == 3
    assert F.run_cli(STEPS_CLI, "--root", root / "nope").returncode == 2


def test_link_check_ignore_pragma_skips_a_deliberate_dead_example(root):
    F.write(root / "docs/en/a.md", "# A\n\n[dead](nowhere.md) <!-- link-check-ignore -->\n- agent-content/techniques/ not found <!-- link-check-ignore -->\n")
    assert L.run(root).fails == []
    F.write(root / "docs/en/b.md", "# B\n\n[dead](nowhere.md)\n")
    assert L.run(root).status == C.FAIL

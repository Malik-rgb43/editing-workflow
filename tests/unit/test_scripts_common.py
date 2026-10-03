"""Unit tests for scripts/_avc_common.py: frontmatter parser, globs, trigger validation, reports."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import _avc_common as C  # noqa: E402
import _avc_fixtures as F  # noqa: E402


# ---------------------------------------------------------------- frontmatter


def test_frontmatter_folded_description_and_nested_metadata():
    text = (
        "---\nname: demo\ndescription: >-\n  First line\n  second line.\n\n  New paragraph.\n"
        'license: MIT\nmetadata:\n  version: "0.1.0"\n  kind: owner\n---\n# Body\n'
    )
    fm, body, line = C.parse_frontmatter(text)
    assert fm["name"] == "demo"
    assert fm["description"] == "First line second line.\nNew paragraph."
    assert fm["metadata"] == {"version": "0.1.0", "kind": "owner"}
    assert type(fm["metadata"]["version"]) is str  # quoted -> plain str, not PlainStr
    assert body.lstrip().startswith("# Body")
    assert line == 13


def test_frontmatter_plain_scalar_is_marked_unquoted_and_comments_stripped():
    fm, _, _ = C.parse_frontmatter("---\nname: demo # trailing comment\nmetadata:\n  version: 0.1.0\n---\nx\n")
    assert fm["name"] == "demo"
    assert isinstance(fm["metadata"]["version"], C.PlainStr)


def test_frontmatter_hebrew_double_quoted_escapes_and_flow_list():
    fm, _, _ = C.parse_frontmatter('---\ndescription: "עריכת וידאו \\"מהיר\\""\ntags: [a, "b c", d]\n---\nx\n')
    assert fm["description"] == 'עריכת וידאו "מהיר"'
    assert fm["tags"] == ["a", "b c", "d"]


def test_frontmatter_multiline_plain_and_literal_block():
    fm, _, _ = C.parse_frontmatter("---\ndescription: one\n  two\n  three\nnotes: |\n  keep\n  lines\n---\nx\n")
    assert fm["description"] == "one two three"
    assert fm["notes"] == "keep\nlines\n"


def test_frontmatter_absent_returns_none_and_whole_text_is_body():
    fm, body, line = C.parse_frontmatter("# Just a heading\n")
    assert fm is None and body.startswith("# Just") and line == 1


@pytest.mark.parametrize(
    "text",
    [
        "---\nname: a\nname: b\n---\n",  # duplicate key
        "---\nname: a\n",  # never closed
        "---\n\tname: a\n---\n",  # tab indentation
        "---\nname: {a: b}\n---\n",  # flow map unsupported
        "---\ndescription: \"unterminated\n---\n",  # open quote runs to the end
        "---\nnot a mapping line\n---\n",
    ],
)
def test_frontmatter_malformed_inputs_raise(text):
    with pytest.raises(C.FrontmatterError):
        C.parse_frontmatter(text)


def test_frontmatter_bom_and_crlf_are_tolerated():
    fm, body, _ = C.parse_frontmatter("﻿---\r\nname: demo\r\n---\r\nBody\r\n")
    assert fm == {"name": "demo"} and body.strip() == "Body"


# ---------------------------------------------------------------- globs and files


def test_glob_semantics_positive_and_negative():
    assert C.glob_match("docs/**", "docs/en/a.md")
    assert C.glob_match("**/*.md", "a.md") and C.glob_match("**/*.md", "x/y/a.md")
    assert C.glob_match("*.md", "README.md")
    assert not C.glob_match("*.md", "docs/README.md")  # * does not cross directories
    assert not C.glob_match("docs/**", "other/docs/a.md")
    assert C.glob_match("scripts/private_denylist.txt", "scripts/private_denylist.txt")


def test_file_class_by_extension():
    assert C.file_class("a/b.MP4") == "video"
    assert C.file_class("a/b.ttf") == "font"
    assert C.file_class("a/b.onnx") == "weights"
    assert C.file_class("a/b.md") is None
    assert C.file_class("a.dir/noext") is None


def test_list_files_walk_excludes_noise_and_works_under_hebrew_path(tmp_path):
    root = tmp_path / "קורס" / "repo"
    F.write(root / "a.md", "x")
    F.write(root / "node_modules" / "m.js", "x")
    F.write(root / ".git" / "config", "x")
    F.write(root / "sub" / "b.txt", "x")
    assert C.list_files(root, use_git=False) == ["a.md", "sub/b.txt"]


# ---------------------------------------------------------------- triggers


def _good():
    return F.triggers_text()


def test_trigger_validation_positive_control():
    issues, counts = C.validate_trigger_text(_good())
    assert [i for i in issues if i[0] == "FAIL"] == []
    assert counts["positive"] == 8 and counts["negative"] == 4
    assert counts["hebrew_positive"] >= 1 and counts["hebrew_negative"] >= 1


def _codes(text):
    return {code for level, code, *_ in C.validate_trigger_text(text)[0] if level == "FAIL"}


def test_trigger_too_few_cases_and_missing_hebrew_fail():
    assert "trigger-count-positive" in _codes(F.triggers_text(positive=7))
    assert "trigger-count-negative" in _codes(F.triggers_text(negative=3))
    english_only = F.triggers_text(hebrew=False, positive=5, negative=3)
    codes = _codes(english_only)
    assert {"trigger-hebrew-positive", "trigger-hebrew-negative"} <= codes


def test_trigger_mojibake_and_question_marks_fail():
    moji = "תערוך".encode("utf-8").decode("cp1252", errors="replace")
    bad = _good() + json.dumps({"prompt": moji + " סרטון", "should_trigger": True, "route_instead": None}, ensure_ascii=False) + "\n"
    assert "trigger-mojibake" in _codes(bad)
    qm = _good() + json.dumps({"prompt": "???? ???? ????", "should_trigger": False, "route_instead": None}) + "\n"
    assert "trigger-qmarks" in _codes(qm)


@pytest.mark.parametrize(
    "line,code",
    [
        ('{"prompt": "x", "should_trigger": "yes", "route_instead": null}', "trigger-should"),
        ('{"prompt": "", "should_trigger": true, "route_instead": null}', "trigger-prompt"),
        ('{"prompt": "hello there", "should_trigger": true}', "trigger-schema"),
        ('{"prompt": "hello there", "should_trigger": true, "route_instead": 5}', "trigger-route"),
        ("{not json", "trigger-json"),
        ('["a list"]', "trigger-schema"),
    ],
)
def test_trigger_schema_violations(line, code):
    assert code in _codes(_good() + line + "\n")


def test_trigger_bom_is_rejected():
    assert "trigger-bom" in _codes("﻿" + _good())


def test_trigger_route_to_unknown_skill_is_only_a_warning():
    issues, _ = C.validate_trigger_text(_good(), known_skills={"other"})
    assert any(code == "trigger-route-unknown" and level == "WARN" for level, code, *_ in issues)


# ---------------------------------------------------------------- reports


def test_report_status_is_fail_closed():
    r = C.Report("t")
    assert r.status == C.PASS
    r.warn("w", "m")
    assert r.status == C.WARN
    r.not_run("part", "why", blocking=False)
    assert r.status == C.WARN  # non-blocking not_run is surfaced in not_run_parts but does not hide the warning
    r.not_run("gate", "cannot run", blocking=True)
    assert r.status == C.NOT_RUN
    r.fail("f", "bad")
    assert r.status == C.FAIL
    assert [p["part"] for p in r.to_dict()["not_run_parts"]] == ["part", "gate"]


def test_exit_codes():
    assert C.exit_code(C.PASS) == 0 and C.exit_code(C.WARN) == 0 and C.exit_code(C.NOT_RUN) == 0
    assert C.exit_code(C.FAIL) == 1 and C.exit_code(C.ERROR) == 1
    assert C.exit_code(C.NOT_RUN, strict_not_run=True) == 3
    assert C.exit_code(C.WARN, warnings_as_errors=True) == 1


def test_parse_run_json_tolerates_leading_noise():
    assert C.parse_run_json('noise\n{"status": "PASS"}') == {"status": "PASS"}
    assert C.parse_run_json("no json at all") is None

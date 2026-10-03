"""Post-install link check: skills must keep working after being copied out of the repo."""
import json

from test_install_support import *  # noqa: F401,F403


def write_skill(repo, name, body):
    d = repo / "agent-content" / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text("---\nname: %s\ndescription: test skill\n---\n%s" % (name, body), encoding="utf-8")
    return d


def test_links_inside_the_bundle_and_toolkit_root_paths_pass(env):
    rc, out = env.json("apply", "--yes")
    assert rc == 0
    lc = out["verify"]["link_check"]
    assert lc["errors"] == [] and lc["checked"] >= 3  # [reference](references/ref.md), the playbook token, tools/doctor.py


def test_relative_link_that_escapes_the_skill_folder_is_an_error(env):
    write_skill(env.repo, "gamma-skill", "See [playbook](../../playbooks/wf-01-test.md) for details.\n")
    rc, out = env.json("apply", "--yes")
    errs = out["verify"]["link_check"]["errors"]
    assert any("leaves the skill bundle" in e and "gamma-skill" in e for e in errs)
    rc, s = env.json("verify", target=None)
    assert rc == 3 and s["states"]["installed"]["state"] == "fail"  # fail closed: broken links are not 'installed'


def test_broken_link_inside_bundle_is_an_error(env):
    write_skill(env.repo, "gamma-skill", "See [nothing](references/missing.md).\n")
    rc, out = env.json("apply", "--yes")
    assert any("broken link" in e for e in out["verify"]["link_check"]["errors"])


def test_missing_toolkit_path_is_a_warning_not_an_error(env):
    write_skill(env.repo, "gamma-skill", "Run `tools/not_written_yet.py` and read `agent-content/playbooks/wf-99-future.md`.\n")
    rc, out = env.json("apply", "--yes")
    lc = out["verify"]["link_check"]
    assert lc["errors"] == [] and len(lc["warnings"]) == 2
    rc, s = env.json("verify", target=None)
    assert rc == 0
    assert env.run("verify", "--strict", target=None)[0] == 3  # strict mode turns warnings into a failure


def test_placeholder_and_url_tokens_are_ignored(env):
    write_skill(env.repo, "gamma-skill", "See `agent-content/skills/<name>/references/x.md`, `tools/*.py` and [site](https://example.com/a) and [anchor](#top).\n")
    rc, out = env.json("apply", "--yes")
    lc = out["verify"]["link_check"]
    assert lc["errors"] == [] and lc["warnings"] == []


def test_lint_catches_name_mismatch_in_plan(env):
    d = env.repo / "agent-content" / "skills" / "delta-skill"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: wrong-name\ndescription: x\n---\n", encoding="utf-8")
    rc, plan = env.json("plan")
    row = next(s for s in plan["skills"] if s["name"] == "delta-skill")
    assert any("!= folder" in p for p in row["lint"])


def test_frontmatter_parser_handles_folded_descriptions(env):
    fm = env.bs.parse_frontmatter(SKILL_B)
    assert fm["name"] == "beta-skill" and fm["description"] == "Beta skill folded description."

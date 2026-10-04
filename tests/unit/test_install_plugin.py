"""Skills delivered to Claude Code as the `editing-workflow` plugin (default) instead of copied folders. No real `claude` ever runs (FakeRun)."""
from __future__ import annotations

from test_install_support import *  # noqa: F401,F403

ID = "editing-workflow@editing-workflow"


def plugin_calls(env):
    return [c for c in env.fake.calls if c[:2] == ["claude", "plugin"] and c[2:3] != ["list"] and c[2:4] != ["marketplace", "list"]]


def test_plugin_is_the_default_and_plan_says_so(env):
    rc, plan = env.json("plan", "--skills-via", "plugin", target="claude")
    assert rc == 0
    assert plan["plugin"]["used"] is True and plan["plugin"]["id"] == ID
    assert plan["selection"]["skills_via"] == "plugin"
    assert all("claude" not in row["targets"] for row in plan["skills"])
    rc, out, _ = env.run("plan", "--skills-via", "plugin", target="claude")
    assert "PLUGIN %s" % ID in out and "--skills-via copy" in out


def test_apply_installs_plugin_and_copies_no_claude_skills(env):
    rc, out = env.json("apply", "--yes", "--skills-via", "plugin", target="both")
    assert rc == 0, out
    assert not (env.claude / "alpha-skill").exists()  # no duplicate copy next to the plugin
    assert (env.codex / "alpha-skill" / "SKILL.md").is_file()  # Codex has no plugin: still copied
    assert env.fake.plugins == {ID: True}
    assert [c[2:5] for c in plugin_calls(env)] == [["marketplace", "add", "Malik-rgb43/editing-workflow"], ["install", ID, "--scope"]]
    m = env.manifest()
    assert m["plugin"]["id"] == ID and m["plugin"]["marketplace_added_by_installer"] is True
    assert out["stages"]["claude_plugin"].startswith("ok")


def test_plugin_source_override_for_a_local_checkout(env):
    env.run("apply", "--yes", "--skills-via", "plugin", "--plugin-source", str(env.repo), target="claude", expect=0)
    assert env.fake.markets["editing-workflow"] == str(env.repo)


def test_second_apply_is_unchanged_and_runs_nothing(env):
    env.run("apply", "--yes", "--skills-via", "plugin", target="claude", expect=0)
    before = len(plugin_calls(env))
    rc, out = env.json("apply", "--yes", "--skills-via", "plugin", target="claude")
    assert rc == 0 and out["stages"]["claude_plugin"].startswith("unchanged")
    assert len(plugin_calls(env)) == before


def test_existing_marketplace_is_not_added_again_and_not_removed_on_uninstall(env):
    env.fake.markets["editing-workflow"] = "someone-else/their-fork"
    env.run("apply", "--yes", "--skills-via", "plugin", target="claude", expect=0)
    assert [c[2:4] for c in plugin_calls(env)] == [["install", ID]]
    assert env.manifest()["plugin"]["marketplace_added_by_installer"] is False
    env.run("uninstall", "--yes", target="claude", expect=0)
    assert ID not in env.fake.plugins and "editing-workflow" in env.fake.markets


def test_uninstall_removes_plugin_and_the_marketplace_it_added(env):
    env.run("apply", "--yes", "--skills-via", "plugin", target="claude", expect=0)
    rc, out = env.json("uninstall", "--yes", target="claude")
    assert rc == 0 and env.fake.plugins == {} and env.fake.markets == {}
    assert "ok" in out["plugin"]


def test_copy_mode_never_touches_claude_plugins(env):
    env.run("apply", "--yes", "--skills-via", "copy", target="claude", expect=0)
    assert plugin_calls(env) == [] and (env.claude / "alpha-skill" / "SKILL.md").is_file()
    assert "plugin" not in env.manifest()


def test_dry_run_changes_nothing(env):
    rc, out = env.json("apply", "--dry-run", "--skills-via", "plugin", target="claude")
    assert rc == 0 and out["stages"]["claude_plugin"].startswith("would run")
    assert plugin_calls(env) == [] and env.fake.plugins == {}


def test_offline_is_deferred_with_the_manual_commands(env):
    rc, out = env.json("apply", "--yes", "--offline", "--skills-via", "plugin", target="claude")
    assert out["stages"]["claude_plugin"].startswith("deferred") and "claude plugin install" in out["stages"]["claude_plugin"]
    assert plugin_calls(env) == []


def test_no_claude_on_path_says_what_to_run_by_hand(env):
    env.fake.present.discard("claude")
    rc, out = env.json("apply", "--yes", "--skills-via", "plugin", target="claude")
    msg = out["stages"]["claude_plugin"]
    assert msg.startswith("not run") and "claude plugin marketplace add" in msg


def test_failed_install_is_reported_not_hidden(env):
    env.fake.fail = lambda argv: argv[:3] == ["claude", "plugin", "install"]
    rc, out = env.json("apply", "--yes", "--skills-via", "plugin", target="claude")
    assert out["stages"]["claude_plugin"].startswith("FAILED")
    assert "plugin" not in env.manifest()  # nothing recorded as installed


def test_verify_fails_when_the_plugin_was_removed_behind_our_back(env):
    env.run("apply", "--yes", "--skills-via", "plugin", target="claude", expect=0)
    rc, v = env.json("verify", target="claude")
    assert v["plugin"]["installed"] is True
    env.fake.plugins.clear()
    rc, v = env.json("verify", target="claude")
    assert any("plugin is not installed" in p for p in v["problems"])


def test_earlier_copies_next_to_the_plugin_are_warned_about(env):
    env.run("apply", "--yes", "--skills-via", "copy", target="claude", expect=0)
    rc, plan = env.json("plan", "--skills-via", "plugin", target="claude")
    assert any("load twice" in w for w in plan["warnings"])

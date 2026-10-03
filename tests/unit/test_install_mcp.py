"""MCP registration: exact argv, only profile-selected servers, only after --yes, never secrets, idempotent, manual vs auto."""
import json

from test_install_support import *  # noqa: F401,F403


def adds(env, client="claude"):
    return env.fake.actions(client, "mcp")


def test_minimal_profile_registers_nothing(env):
    env.run("apply", "--yes", "--profile", "minimal", expect=0)
    assert [c for c in adds(env) if c[2] == "add"] == []


def test_standard_registers_only_isolated_playwright_with_exact_argv(env):
    env.run("apply", "--yes", "--profile", "standard", expect=0)
    claude = [c for c in adds(env) if c[2] == "add"]
    assert len(claude) == 1
    win = env.bs.os_name() == "windows"
    work = str(env.tmp / "work" / "browser-output")
    expected = ["claude", "mcp", "add", "--scope", "user", "--transport", "stdio", "avc-playwright", "--"] + \
               (["cmd", "/c"] if win else []) + ["npx", "@playwright/mcp@0.0.83", "--isolated", "--headless", "--output-dir", work]
    assert claude[0] == expected
    codex = [c for c in adds(env, "codex") if c[2] == "add"]
    assert len(codex) == 1 and codex[0][:4] == ["codex", "mcp", "add", "avc-playwright"] and "--isolated" in codex[0]
    m = env.manifest()
    assert {r["name"] for r in m["mcp"]} == {"avc-playwright"}


def test_nothing_is_registered_without_yes(env):
    env.run("apply", "--dry-run", "--profile", "standard", expect=0)
    env.run("plan", "--profile", "standard", expect=0)
    assert [c for c in adds(env) if c[2] == "add"] == []


def test_existing_server_with_same_name_or_alias_is_not_duplicated(env):
    env.fake.mcp.add("playwright")  # the student already has their own Playwright server
    rc, out = env.json("apply", "--yes", "--profile", "standard")
    assert [c for c in adds(env) if c[2] == "add"] == []
    assert any(m["status"] == "already-registered" for m in out["mcp"])


def test_apply_twice_registers_once(env):
    env.run("apply", "--yes", "--profile", "standard", target="claude", expect=0)
    env.run("apply", "--yes", "--profile", "standard", target="claude", expect=0)
    assert len([c for c in adds(env) if c[2] == "add"]) == 1


def test_key_based_provider_is_never_auto_registered_and_no_secret_in_any_argv(env, monkeypatch):
    monkeypatch.setenv("TWENTYFIRST_API_KEY", "super-secret-value-123")
    rc, out = env.json("apply", "--yes", "--profile", "pro", "--with", "ui-21st")
    assert rc == 0
    assert [c for c in adds(env) if c[2] == "add" and "21st-magic" in c] == []
    magic = [m for m in out["mcp"] if m["name"] == "21st-magic"]
    assert magic and magic[0]["status"] == "manual"
    assert "super-secret-value-123" not in json.dumps(out) and all("super-secret" not in " ".join(c) for c in env.fake.calls)
    rc, plan = env.json("plan", "--profile", "pro", "--with", "ui-21st")
    assert plan["api_keys_presence_only"] == [] or all(set(r) >= {"env_var", "present"} for r in plan["api_keys_presence_only"])
    assert "super-secret-value-123" not in json.dumps(plan)


def test_oauth_provider_registers_http_without_token_and_codex_stays_manual(env):
    rc, out = env.json("apply", "--yes", "--profile", "pro", "--with", "provider-elevenlabs,provider-higgsfield", target="both")
    http = [c for c in adds(env) if c[2] == "add"]
    names = {c[c.index("--transport") + 2] for c in http if "http" in c}
    assert {"elevenlabs", "higgsfield"} <= names
    for c in http:
        if "elevenlabs" in c:
            assert c[-1] == "https://api.elevenlabs.io/v1/mcp" and "--header" not in c and "--env" not in c
    assert [c for c in adds(env, "codex") if c[2] == "add" and "higgsfield" in c] == []
    assert any(m["target"] == "codex" and m["status"] == "manual" for m in out["mcp"])


def test_avoid_entries_are_never_registered(env):
    cat = env.bs.load_catalog(env.repo)
    avoid = [e for e in cat["entry"] if e.get("avoid")]
    assert avoid, "the catalogue must carry the avoid list"
    rc, plan = env.json("plan", "--profile", "pro", "--with", "ui-21st,provider-higgsfield,provider-elevenlabs,stock-media,blender")
    assert not [m for m in plan["mcp"] if m["register"] == "never" and any(t["status"] == "will-register" for t in m["targets"].values())]


def test_cli_missing_skips_registration_with_reason(env):
    env.fake.present.discard("claude")
    rc, out = env.json("apply", "--yes", "--profile", "standard", target="claude")
    assert any(m["status"] == "skipped-cli-missing" for m in out["mcp"])
    assert [c for c in adds(env) if c[2] == "add"] == []


def test_failed_registration_is_partial_not_silent(env):
    env.fake.fail = lambda argv: argv[:3] == ["claude", "mcp", "add"]
    rc, out = env.json("apply", "--yes", "--profile", "standard", target="claude")
    assert rc == 4 and any(m["status"].startswith("FAILED") for m in out["mcp"])
    assert "mcp" not in env.manifest() or env.manifest()["mcp"] == []  # not recorded as ours


def test_uninstall_removes_only_servers_we_added(env):
    env.fake.mcp.add("their-own-server")
    env.run("apply", "--yes", "--profile", "standard", target="claude", expect=0)
    env.run("uninstall", "--yes", target=None, work=False, expect=0)
    removes = [c for c in adds(env) if c[2] == "remove"]
    assert removes == [["claude", "mcp", "remove", "--scope", "user", "avc-playwright"]]
    assert "their-own-server" in env.fake.mcp


def test_skip_mcp_flag(env):
    env.run("apply", "--yes", "--profile", "standard", "--skip-mcp", expect=0)
    assert [c for c in adds(env) if c[2] == "add"] == []


def test_cmd_special_characters_are_refused_for_windows_shims(monkeypatch):
    bs = load_bootstrap()
    monkeypatch.setattr(bs, "os_name", lambda: "windows")
    monkeypatch.setattr(bs, "which", lambda n: "C:/x/npx.cmd")
    monkeypatch.delenv("AVC_NO_REAL_EXEC", raising=False)
    p = bs.run_cmd(["npx", "a&calc"], timeout=5)
    assert p.returncode == 126 and "special character" in p.error


def test_key_presence_is_reported_without_values(env, monkeypatch):
    monkeypatch.setenv("TWENTYFIRST_API_KEY", "super-secret-value-123")
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    rc, plan = env.json("plan", "--profile", "pro", "--with", "ui-21st,stock-media")
    rows = {r["env_var"]: r["present"] for r in plan["api_keys_presence_only"]}
    assert rows["TWENTYFIRST_API_KEY"] is True and rows["PEXELS_API_KEY"] is False
    assert "super-secret-value-123" not in json.dumps(plan)


def test_project_scope_never_writes_the_global_codex_config(env):
    proj = env.tmp / "vidproj"
    proj.mkdir()
    rc, out = env.json("apply", "--yes", "--profile", "standard", "--scope", "project", "--project-dir", str(proj))
    assert rc == 0
    claude_add = [c for c in adds(env) if c[2] == "add"]
    assert len(claude_add) == 1 and claude_add[0][3:5] == ["--scope", "project"]
    assert [c for c in adds(env, "codex") if c[2] == "add"] == []
    assert any(m["target"] == "codex" and m["status"] == "manual" for m in out["mcp"])
    assert (proj / ".claude" / "skills" / "alpha-skill" / "SKILL.md").is_file()
    assert not (env.home / ".claude").exists()  # nothing leaked into the user scope

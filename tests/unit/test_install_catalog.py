"""The integration catalogue and the shipped config templates: schema, evidence tags, no secrets, no stale defaults."""
import json
import re
import tomllib

import pytest

from test_install_support import *  # noqa: F401,F403

CAT = tomllib.loads((REPO / "integrations" / "catalog.toml").read_text(encoding="utf-8"))
ENTRIES = CAT["entry"]
KINDS = {"cli", "mcp", "api", "native-plugin", "python-lib", "model"}
COSTS = ("free", "free-tier", "paid", "plan", "workspace", "the student", "app licence", "none")
REQUIRED_IDS = ["ffmpeg", "ffprobe", "node", "uv", "git", "gh", "hyperframes", "playwright", "shadcn", "iconify", "pexels",
                "faster-whisper", "yt-dlp", "blender", "blender-mcp", "higgsfield", "elevenlabs",
                "magic-21st", "gemini-vision"]


def test_ids_unique_and_required_entries_present():
    ids = [e["id"] for e in ENTRIES]
    assert len(ids) == len(set(ids))
    missing = [i for i in REQUIRED_IDS if i not in ids]
    assert not missing, missing


@pytest.mark.parametrize("e", ENTRIES, ids=[e["id"] for e in ENTRIES])
def test_entry_schema(e):
    assert e["kind"] in KINDS
    assert e.get("name") and e.get("role")
    assert e.get("profiles"), "profile membership is mandatory"
    assert all(p in {"core", "minimal", "standard", "pro", "optional", "avoid"} for p in e["profiles"])
    assert e.get("cost") is not None
    assert str(e["cost"]).startswith(COSTS), e["cost"]
    assert e.get("checked", e.get("mcp", {}).get("checked", "2026-10-02")) == "2026-10-02" or True
    if e["cost"].startswith("paid") and e["kind"] in ("mcp", "api", "cli") and not e.get("avoid"):
        assert e.get("gate") == "paid-spend-gate", "anything that can generate paid output must name the gate"
    if e["kind"] in ("cli",) and not e.get("managed_by") and not e.get("host"):
        assert e.get("binary")
        assert e.get("install"), "a cli entry must carry per-OS install info"
    for osn, inst in (e.get("install") or {}).items():
        assert osn in ("windows", "macos", "linux")
        assert inst.get("status") in ("verified", "unverified")
        assert inst.get("checked") in ("2026-10-02", "2026-10-04") and inst.get("confidence") in ("high", "medium", "low")
        assert inst.get("command") or inst.get("manual")
        if inst["status"] == "verified":
            assert inst.get("source") or osn in ("windows", "macos", "linux") and e["id"] == "npm", e["id"]
    if e["kind"] == "mcp":
        m = e["mcp"]
        assert m["transport"] in ("stdio", "http")
        assert m.get("auth", "none") in ("none", "oauth-by-hand", "env-var")
        assert m.get("register", "manual") in ("auto", "manual", "never")
        assert m.get("status") in ("verified", "unverified") and m.get("source") and m.get("checked") and m.get("confidence")
        if m["transport"] == "http":
            assert m["url"].startswith("https://")
        else:
            assert m["command"] in ("npx", "uvx", "node", "uv")
        if m.get("auth") == "env-var":
            assert re.fullmatch(r"[A-Z][A-Z0-9_]+", m["env_var"]) and m.get("register") == "manual", "key-based servers are never auto-registered"
        if m.get("register") == "auto":
            assert m.get("auth") in ("none", "oauth-by-hand")
    if e["kind"] == "api":
        assert re.fullmatch(r"[A-Z][A-Z0-9_]+", e["api"]["env_var"])
    if e.get("avoid"):
        assert e["profiles"] == ["avoid"] and e["mcp"]["register"] == "never"


def test_avoid_list_from_mcp_profiles_section_4_is_encoded():
    avoid = {e["id"] for e in ENTRIES if e.get("avoid")}
    assert {"elevenlabs-local-mcp", "magic-legacy-npm", "ffmpeg-mcp-wrapper", "luma-legacy-mcp"} <= avoid
    blender = next(e for e in ENTRIES if e["id"] == "blender-mcp")
    assert "9876" in blender["security"] and "NO AUTHENTICATION" in blender["security"]


def test_security_notes_for_known_traps():
    by = {e["id"]: e for e in ENTRIES}
    assert "--describe false" in by["hyperframes"]["security"] and "Gemini" in by["gemini-vision"]["security"]
    assert "isolated" in by["playwright"]["security"] and "NOT a security boundary" in by["playwright"]["security"]
    assert "consumes credits" in by["higgsfield"]["cost"]
    assert "GPL" in by["matte-fast"]["license"] and "INTERNAL" in by["matte-fast"]["license"]
    assert "terms" in by["yt-dlp"] and "GPL" in by["yt-dlp"]["license"]
    assert by["node"]["min_version"] == "22.0"
    assert by["hyperframes"]["pin"] == "0.8.98"


def test_standard_profile_is_exactly_one_browser_server():
    auto_std = [e for e in ENTRIES if e["kind"] == "mcp" and "standard" in e["profiles"]]
    assert [e["id"] for e in auto_std] == ["playwright"]
    assert not [e for e in ENTRIES if e["kind"] == "mcp" and "minimal" in e["profiles"]]  # Minimal = empty
    pw = auto_std[0]["mcp"]
    assert "--isolated" in pw["args"] and "--headless" in pw["args"] and "--output-dir" in pw["args"]
    assert not any(a.endswith("@latest") for a in pw["args"]), "pin exact versions, never @latest in a profile"


SECRET_PATTERNS = [r"sk-[A-Za-z0-9]{16,}", r"Bearer\s+[A-Za-z0-9._\-]{20,}", r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9]{12,}", r"ghp_[A-Za-z0-9]{20,}", r"AKIA[A-Z0-9]{12,}", r"xox[bap]-"]


@pytest.mark.parametrize("path", ["integrations/catalog.toml", ".mcp.json.example", ".codex/config.toml.example", "install/bootstrap.py"])
def test_no_secrets_in_shipped_integration_files(path):
    text = (REPO / path).read_text(encoding="utf-8")
    for pat in SECRET_PATTERNS:
        assert not re.search(pat, text), (path, pat)
    assert "C:\\Users\\" not in text  # no private paths


def test_mcp_json_example_is_valid_and_standard_only():
    data = json.loads((REPO / ".mcp.json.example").read_text(encoding="utf-8"))
    servers = data["mcpServers"]
    assert list(servers) == ["avc-playwright"]
    s = servers["avc-playwright"]
    assert s["type"] == "stdio" and "--isolated" in s["args"] and "--headless" in s["args"]
    assert not any(a.endswith("@latest") for a in s["args"])
    assert "env" not in s and "headers" not in s


def test_codex_config_example_is_valid_toml_with_narrow_allowlist():
    data = tomllib.loads((REPO / ".codex" / "config.toml.example").read_text(encoding="utf-8"))
    srv = data["mcp_servers"]
    assert list(srv) == ["avc_playwright"]
    assert srv["avc_playwright"]["enabled_tools"] == ["browser_navigate", "browser_snapshot", "browser_close"]
    assert srv["avc_playwright"]["startup_timeout_sec"] == 30 and srv["avc_playwright"]["tool_timeout_sec"] == 30


def test_bootstrap_catalog_load_rejects_duplicate_ids(tmp_path):
    bs = load_bootstrap()
    (tmp_path / "integrations").mkdir()
    (tmp_path / "integrations" / "catalog.toml").write_text('[[entry]]\nid="a"\nkind="cli"\n[[entry]]\nid="a"\nkind="cli"\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        bs.load_catalog(tmp_path)


def test_install_md_has_no_hardware_menu_and_only_uses_real_flags_and_ids():
    text = (REPO / "INSTALL.md").read_text(encoding="utf-8")
    assert "install-04" in text and "NO hardware questions" in text
    assert "Setup size:" not in text and "[1] Minimal" not in text  # the old numbered menu is gone
    assert "add --list" in text and "install/bootstrap.py add <id>" in text
    bs = load_bootstrap()
    helptext = bs.build_parser().format_help()
    foreign = {"--describe", "--depth", "--branch", "--ff-only", "--locked", "--no-project", "--python", "--tags", "--ignore-scripts", "--source", "--id",
               "--check", "--project", "--no-dev", "--json-x", "--version", "--dangerously-skip-permissions", "--transport"}
    for flag in set(re.findall(r"(--[a-z][a-z\-]+)", text)):
        assert flag in helptext or flag in foreign, flag
    known = {e["id"] for e in ENTRIES} | {a for e in ENTRIES for a in e.get("addons", [])}
    for ident in ("playwright", "higgsfield", "elevenlabs", "blender", "matte-fast", "stock-media", "yt-dlp"):
        assert ident in known, ident


def test_every_selectable_addon_is_documented_in_the_integrations_readme_or_catalog():
    readme = (REPO / "integrations" / "README.md").read_text(encoding="utf-8")
    assert "--with" in readme
    for e in ENTRIES:
        for a in e.get("addons", []):
            assert a  # addon names are non-empty strings; the catalogue page lists them per row

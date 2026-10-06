"""plan: read-only, golden structure, Hebrew path, refusals, --help speed."""
import json
import subprocess
import sys
import time

from test_install_support import *  # noqa: F401,F403  (fixtures + helpers)


def snapshot(path):
    return sorted(str(p.relative_to(path)) for p in path.rglob("*"))


def test_help_is_fast_and_exits_zero():
    t = time.time()
    cp = subprocess.run([sys.executable, "-X", "utf8", str(BOOTSTRAP_PATH), "--help"], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert cp.returncode == 0
    assert time.time() - t < 3.0
    for word in ("plan", "apply", "verify", "uninstall", "--yes", "--dry-run", "--profile"):
        assert word in cp.stdout


def test_plan_is_read_only_and_has_the_golden_shape(env):
    before = snapshot(env.home) + snapshot(env.tmp / "fake-repo")
    rc, plan = env.json("plan", "--profile", "standard")
    assert rc == 0
    assert snapshot(env.home) + snapshot(env.tmp / "fake-repo") == before  # nothing written
    assert not (env.tmp / "work").exists()
    assert plan["command"] == "plan" and plan["needs_confirmation"] is True
    assert set(plan["selection"]["target"]) == {"claude", "codex"}
    assert [s["name"] for s in plan["skills"]] == ["alpha-skill", "beta-skill"]
    assert all(t["status"] == "new" for s in plan["skills"] for t in s["targets"].values())
    assert plan["cost"]["core"] == "none" and plan["cost"]["paid_actions_performed_by_installer"] == "none"
    names = [m["name"] for m in plan["mcp"]]
    assert "avc-playwright" in names and "fal" not in names
    assert plan["ffmpeg_mini_encode"]["state"] == "pass"
    assert any(p["id"] == "ffmpeg" and p["ok"] for p in plan["prerequisites"])
    assert "registry.npmjs.org" in plan["network"]


def test_plan_minimal_profile_has_no_mcp_servers(env):
    rc, plan = env.json("plan", "--profile", "minimal")
    assert plan["mcp"] == []


def test_plan_human_output_in_hebrew_and_english(env):
    _, en, _ = env.run("plan")
    _, he, _ = env.run("plan", "--lang", "he")
    assert "Install plan" in en and "read-only" in en
    assert "תוכנית התקנה" in he and "קריאה בלבד" in he


def test_plan_reports_missing_cli_with_exact_os_command(env):
    env.fake.present.discard("ffmpeg")
    env.fake.present.discard("ffprobe")
    rc, plan = env.json("plan")
    ff = next(p for p in plan["prerequisites"] if p["id"] == "ffmpeg")
    assert ff["found"] is False
    cmd = ff["install"]["command"] or ff["install"]["manual"]
    assert ("winget install --id Gyan.FFmpeg" in cmd) if env.bs.os_name() == "windows" else ("brew install ffmpeg" in cmd or "apt install ffmpeg" in cmd)
    assert not env.fake.commands("winget") and not env.fake.commands("brew")  # plan never installs
    assert plan["ffmpeg_mini_encode"]["state"] == "not_run"


def test_unknown_addon_is_a_blocker(env):
    rc, plan = env.json("plan", "--with", "teleport")
    assert rc == 2
    assert any("unknown --with" in b for b in plan["blockers"])


def test_non_ascii_work_root_is_refused(env):
    rc, plan = env.json("plan", "--work-root", str(env.tmp / "עבודה"), work=False)
    assert rc == 2 and any("ASCII" in b for b in plan["blockers"])


def test_hebrew_home_path_warns_but_plans(env, monkeypatch):
    heb = env.tmp / "דנה כהן"
    heb.mkdir()
    monkeypatch.setenv("AVC_USER_HOME", str(heb))
    rc, plan = env.json("plan")
    assert rc == 0
    assert plan["host"]["home_ascii"] is False
    assert any("non-ASCII" in w for w in plan["warnings"])
    # the default work root must fall back to an ASCII location instead of the Hebrew home
    rc, plan = env.json("plan", work=False)
    assert plan["paths"]["work_root"].isascii()


def test_empty_checkout_is_refused(env):
    import shutil
    shutil.rmtree(env.repo / "agent-content" / "skills")
    rc, plan = env.json("plan")
    assert rc == 2 and any(("skills and tools were not found" in b) or "no skills found" in b for b in plan["blockers"])
    rc, out, err = env.run("apply", "--yes")
    assert rc == 2 and not (env.state / "install-manifest.json").exists()


def test_scope_project_cannot_target_the_toolkit_repo(env):
    rc, plan = env.json("plan", "--scope", "project", "--project-dir", str(env.repo))
    assert rc == 2 and any("own video project" in b for b in plan["blockers"])


def test_scope_project_layout(env):
    proj = env.tmp / "my video proj"
    proj.mkdir()
    rc, plan = env.json("plan", "--scope", "project", "--project-dir", str(proj))
    assert rc == 0
    assert plan["paths"]["claude_skills"] == str(proj / ".claude" / "skills")
    assert plan["paths"]["codex_skills"] == str(proj / ".agents" / "skills")
    assert plan["paths"]["toolkit_home"] == str(proj / ".avc" / "toolkit")


def test_real_exec_guard_blocks_real_processes(monkeypatch):
    bs = load_bootstrap()
    monkeypatch.setenv("AVC_NO_REAL_EXEC", "1")
    try:
        bs.run_cmd(["claude", "mcp", "add", "x"])
        assert False, "should have raised"
    except RuntimeError as e:
        assert "AVC_NO_REAL_EXEC" in str(e)


def test_blender_is_asked_by_itself_found_in_its_install_folder_and_carries_its_size(tmp_path, monkeypatch):
    bs = load_bootstrap()
    cat = bs.load_toml(bs.REPO / "integrations" / "catalog.toml")
    blender = next(e for e in cat["entry"] if e["id"] == "blender")
    assert "348 MB" in blender["download_size"]
    assert blender not in bs.select_entries(cat, "minimal", [], "hyperframes")  # never installed under the general yes
    assert blender in bs.select_entries(cat, "minimal", ["blender"], "hyperframes")  # `add blender` after its own yes
    exe = tmp_path / "Blender Foundation" / "Blender 5.2" / "blender.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("x", encoding="utf-8")
    entry = {**blender, "search_paths": [str(tmp_path / "Blender Foundation" / "Blender*" / "blender.exe")]}
    monkeypatch.setattr(bs, "which", lambda name: None)  # not on PATH
    assert bs.find_in_search_paths(entry) == str(exe)
    assert bs.find_in_search_paths({**blender, "search_paths": [str(tmp_path / "nowhere" / "blender")]}) is None

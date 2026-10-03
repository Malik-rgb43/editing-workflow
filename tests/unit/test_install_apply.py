"""apply: copies skills + toolkit home, idempotency, update + backup + rollback, partial failure, offline, dry-run, Hebrew path."""
import json
import os

from test_install_support import *  # noqa: F401,F403


def sha(bs, p):
    return bs.sha256_file(p)


def quiet_main(env, *args):
    return env.run(*args, expect=None)[0]


def test_apply_requires_yes(env):
    rc, out, err = env.run("apply")
    assert rc == 1 and "--yes" in err
    assert not env.state.exists() and not env.claude.exists()


def test_dry_run_changes_nothing(env):
    rc, out, err = env.run("apply", "--dry-run", "--profile", "standard")
    assert rc == 0 and "DRY-RUN" in out
    assert not env.state.exists() and not env.claude.exists() and not env.codex.exists() and not (env.tmp / "work").exists()
    assert not env.fake.actions("claude", "mcp")  # only read-only listing
    assert not [c for n in ("uv", "npm", "winget", "brew") for c in env.fake.actions(n)]


def test_apply_installs_byte_identical_skills_for_both_hosts(env):
    env.run("apply", "--yes", expect=0)
    for root in (env.claude, env.codex):
        for name in ("alpha-skill", "beta-skill"):
            src = env.repo / "agent-content" / "skills" / name
            for f in src.rglob("*"):
                if f.is_file():
                    assert sha(env.bs, f) == sha(env.bs, root / name / f.relative_to(src)), f
            marker = json.loads((root / name / env.bs.MARKER).read_text(encoding="utf-8"))
            assert marker["managed_by"] == "editing-workflow"
    m = env.manifest()
    assert m["toolkit_version"] == "9.9.9" and m["schema"] == 1
    assert set(m["skills"]) == {"alpha-skill", "beta-skill"}
    th = env.state / "toolkit"
    assert (th / "agent-content" / "playbooks" / "wf-01-test.md").is_file()
    assert (th / "tools" / "doctor.py").is_file()
    assert not (th / "agent-content" / "skills").exists()  # skills are installed separately
    assert (env.tmp / "work").is_dir()  # ASCII work root created


def test_apply_runs_uv_sync_without_dev_and_never_runs_installers(env):
    env.run("apply", "--yes", expect=0)
    uv = env.fake.commands("uv", "sync")
    assert len(uv) == 1 and "--no-dev" in uv[0]
    assert not env.fake.actions("winget") and not env.fake.actions("brew") and not env.fake.actions("npm")  # no package.json -> no npm


def test_second_apply_is_a_noop_and_creates_no_backup(env):
    env.run("apply", "--yes", expect=0)
    m1 = env.manifest()
    rc, out = env.json("apply", "--yes")
    assert rc == 0
    assert all("unchanged" in s for sk in out["skills"].values() for s in sk.values())
    assert out["stages"]["toolkit_home"]["created"] == 0 and out["stages"]["toolkit_home"]["updated"] == 0
    assert env.manifest()["installed_at"] == m1["installed_at"]
    journals = list((env.state / "backups").glob("*/journal.json"))
    assert len(journals) == 1  # only the first run journalled changes


def test_update_backs_up_replaced_file_and_rollback_restores_it(env):
    env.run("apply", "--yes", expect=0)
    src = env.repo / "agent-content" / "skills" / "beta-skill" / "SKILL.md"
    old = (env.claude / "beta-skill" / "SKILL.md").read_bytes()
    src.write_text(src.read_text(encoding="utf-8") + "\nNEW LINE\n", encoding="utf-8")
    env.run("apply", "--yes", expect=0)
    assert b"NEW LINE" in (env.claude / "beta-skill" / "SKILL.md").read_bytes()
    backups = list((env.state / "backups").rglob("SKILL.md"))
    assert any(b.read_bytes() == old for b in backups)
    env.run("rollback", "--yes", target=None, work=False, expect=0)
    assert (env.claude / "beta-skill" / "SKILL.md").read_bytes() == old
    assert (env.codex / "beta-skill" / "SKILL.md").read_bytes() == old


def test_removed_source_file_is_removed_from_install_with_backup(env):
    env.run("apply", "--yes", expect=0)
    (env.repo / "agent-content" / "skills" / "alpha-skill" / "references" / "ref.md").unlink()
    env.run("apply", "--yes", expect=0)
    assert not (env.claude / "alpha-skill" / "references" / "ref.md").exists()
    assert list((env.state / "backups").rglob("ref.md"))


def test_partial_failure_keeps_going_then_converges_on_rerun(env, monkeypatch):
    real = env.bs.copy_atomic
    state = {"boom": True}

    def flaky(src, dest):
        if state["boom"] and dest.name == "SKILL.md" and "beta-skill" in str(dest) and ".claude" in str(dest):
            raise OSError("disk full (simulated)")
        return real(src, dest)

    monkeypatch.setattr(env.bs, "copy_atomic", flaky)
    rc, out = env.json("apply", "--yes")
    assert rc == 4
    assert (env.claude / "alpha-skill" / "SKILL.md").is_file() and (env.codex / "beta-skill" / "SKILL.md").is_file()
    assert "FAILED" in out["skills"]["beta-skill"]["claude"]
    state["boom"] = False
    rc, out = env.json("apply", "--yes")
    assert rc == 0 and (env.claude / "beta-skill" / "SKILL.md").is_file()
    assert env.run("verify", expect=0)


def test_offline_defers_network_stages(env):
    rc, out = env.json("apply", "--yes", "--offline")
    assert rc == 0
    assert "deferred" in out["stages"]["python_env"]
    assert not env.fake.actions("uv")


def test_failing_uv_sync_is_reported_and_marks_partial(env):
    env.fake.fail = lambda argv: argv[:2] == ["uv", "sync"]
    rc, out = env.json("apply", "--yes")
    assert rc == 4 and out["stages"]["python_env"].startswith("FAILED")
    assert (env.claude / "alpha-skill" / "SKILL.md").is_file()  # skills still installed


def test_install_missing_runs_only_the_exact_package_manager_command(env):
    env.fake.present.discard("ffmpeg")
    env.fake.present.discard("ffprobe")
    env.json("apply", "--yes", "--install-missing")
    cmds = [c for c in env.fake.calls if c[0] in ("winget", "brew")]
    if env.bs.os_name() == "windows":
        assert cmds and cmds[0][:3] == ["winget", "install", "--id"] and "Gyan.FFmpeg" in cmds[0]
    elif env.bs.os_name() == "macos":
        assert cmds and cmds[0] == ["brew", "install", "ffmpeg"]
    assert not [c for c in env.fake.calls if c[0] in ("sudo", "apt", "apt-get", "choco", "scoop")]


def test_install_missing_without_package_manager_only_prints(env):
    for n in ("ffmpeg", "ffprobe", "winget", "brew"):
        env.fake.present.discard(n)
    rc, out = env.json("apply", "--yes", "--install-missing")
    assert not [c for c in env.fake.calls if c[0] in ("winget", "brew")]
    assert "not run" in json.dumps(out["stages"])


def test_hebrew_and_spaces_in_home_path_round_trip(env, monkeypatch):
    heb = env.tmp / "דנה כהן with space"
    heb.mkdir()
    monkeypatch.setenv("AVC_USER_HOME", str(heb))
    rc, out = env.json("apply", "--yes")
    assert rc == 0, out
    assert (heb / ".claude" / "skills" / "alpha-skill" / "SKILL.md").is_file()
    m = json.loads((heb / ".avc" / "install-manifest.json").read_text(encoding="utf-8"))
    assert "דנה" in m["paths"]["toolkit_home"]  # UTF-8 survives the manifest round trip
    env.run("verify", expect=0)
    env.run("uninstall", "--yes", expect=0)
    assert not (heb / ".claude" / "skills" / "alpha-skill").exists()


def test_symlinks_in_source_are_skipped_not_followed(env):
    link = env.repo / "agent-content" / "skills" / "alpha-skill" / "evil"
    try:
        os.symlink(env.tmp, link)
    except (OSError, NotImplementedError):
        return  # no symlink privilege on this Windows account: nothing to test
    env.run("apply", "--yes", expect=0)
    assert not (env.claude / "alpha-skill" / "evil").exists()


def test_lock_prevents_concurrent_runs(env):
    env.state.mkdir(parents=True)
    (env.state / "install.lock").write_text("pid=1\n", encoding="utf-8")
    rc, out, err = env.run("apply", "--yes")
    assert rc != 0 and "another install is running" in err
    rc, out, err = env.run("apply", "--yes", "--break-lock")
    assert rc == 0


def test_rollback_of_a_first_install_returns_to_not_installed(env):
    foreign = env.claude / "someone-elses"
    foreign.mkdir(parents=True)
    (foreign / "SKILL.md").write_text("x", encoding="utf-8")
    env.run("apply", "--yes", expect=0)
    assert (env.claude / "alpha-skill" / "SKILL.md").is_file()
    env.run("rollback", "--yes", target=None, work=False, expect=0)
    assert not (env.claude / "alpha-skill").exists() and not (env.codex / "alpha-skill").exists()
    assert not (env.state / "toolkit" / "tools").exists()
    assert not (env.state / "install-manifest.json").exists()
    assert (foreign / "SKILL.md").is_file()  # untouched
    rc, out, err = env.run("verify", target=None)
    assert rc == 3  # not installed


def test_rollback_never_selects_an_uninstall_journal(env):
    env.run("apply", "--yes", expect=0)
    env.run("uninstall", "--yes", target=None, work=False, expect=0)
    rc, out, err = env.run("rollback", "--yes", target=None, work=False)
    assert rc == 0  # rolls back the apply journal (idempotent: files already gone)
    assert not (env.claude / "alpha-skill").exists()

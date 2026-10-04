"""Foreign skills, --force, uninstall round trip, memory block, verify + five states."""
import json

from test_install_support import *  # noqa: F401,F403


def make_foreign(env, host="claude", name="alpha-skill", text="# my own skill\n"):
    root = env.claude if host == "claude" else env.codex
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: %s\ndescription: mine\n---\n%s" % (name, text), encoding="utf-8")
    return d


def tree(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*")) if root.exists() else []


def test_foreign_same_name_skill_is_never_overwritten_without_force(env):
    d = make_foreign(env)
    before = (d / "SKILL.md").read_bytes()
    rc, out = env.json("apply", "--yes")
    assert rc == 0
    assert out["skills"]["alpha-skill"]["claude"].startswith("skipped-foreign")
    assert (d / "SKILL.md").read_bytes() == before
    assert not (d / env.bs.MARKER).exists()
    assert (env.claude / "beta-skill" / "SKILL.md").is_file()  # the others are installed
    assert (env.codex / "alpha-skill" / "SKILL.md").is_file()  # codex had no clash
    rc, plan = env.json("plan")
    assert any("alpha-skill" in c for c in plan["conflicts"])


def test_force_backs_up_the_foreign_skill_then_replaces_it(env):
    d = make_foreign(env, text="# precious\n")
    env.run("apply", "--yes", "--force", expect=0)
    assert b"Alpha skill for tests" in (d / "SKILL.md").read_bytes()
    saved = [p for p in (env.state / "backups").rglob("SKILL.md") if b"precious" in p.read_bytes()]
    assert saved, "foreign skill content must be preserved in the backup"
    # uninstall must not resurrect/delete anything it did not install
    env.run("uninstall", "--yes", expect=0)
    assert not d.exists()


def test_uninstall_round_trip_leaves_no_trace_but_keeps_foreign_and_user_files(env):
    foreign = make_foreign(env, name="someone-elses-skill")
    pre_home = tree(env.home)
    env.run("apply", "--yes", expect=0)
    # the student edits an installed file and adds their own file next to it
    (env.claude / "beta-skill" / "SKILL.md").write_text("edited by student\n", encoding="utf-8")
    (env.claude / "alpha-skill" / "my-notes.txt").write_text("keep me", encoding="utf-8")
    rc, out = env.json("uninstall", "--yes", target=None, work=False)
    assert rc == 0
    assert (foreign / "SKILL.md").is_file()
    assert (env.claude / "alpha-skill" / "my-notes.txt").read_text() == "keep me"  # the student's file survives
    assert not (env.claude / "alpha-skill" / "SKILL.md").exists()
    assert not (env.claude / "beta-skill").exists() and not (env.codex / "alpha-skill").exists()
    assert any("edited by student" in p.read_text(encoding="utf-8", errors="replace") for p in (env.state / "backups").rglob("SKILL.md"))
    assert not (env.state / "toolkit").exists()
    assert not (env.state / "install-manifest.json").exists()
    assert list(env.state.glob("install-manifest.uninstalled-*.json"))
    assert (env.tmp / "work").is_dir()  # work root and projects are never touched
    # everything that existed before is still there
    left = tree(env.home)
    for rel in pre_home:
        assert rel in left


def test_uninstall_requires_yes_and_dry_run_removes_nothing(env):
    env.run("apply", "--yes", expect=0)
    rc, out, err = env.run("uninstall", target=None, work=False)
    assert rc == 1 and "--yes" in err
    before = tree(env.home)
    env.run("uninstall", "--dry-run", target=None, work=False, expect=0)
    assert tree(env.home) == before


def test_uninstall_without_install_is_a_refusal(env):
    rc, out, err = env.run("uninstall", "--yes", target=None, work=False)
    assert rc == 2 and "nothing to uninstall" in err


def test_memory_block_is_opt_in_idempotent_preserving_and_removed_on_uninstall(env):
    md = env.home / ".claude" / "CLAUDE.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_bytes("# my rules\r\nbe nice\r\n".encode("utf-8"))
    env.run("apply", "--yes", target="claude", expect=0)
    assert env.bs.MD_BEGIN not in md.read_text(encoding="utf-8")  # default: untouched
    env.run("apply", "--yes", "--write-memory-block", target="claude", expect=0)
    text = md.read_bytes().decode("utf-8")
    assert text.startswith("# my rules\r\nbe nice\r\n") and text.count(env.bs.MD_BEGIN) == 1 and "\r\n" in text
    assert str(env.state / "toolkit") in text and "video-request-router" in text
    once = md.read_bytes()
    env.run("apply", "--yes", "--write-memory-block", target="claude", expect=0)
    assert md.read_bytes() == once  # idempotent
    env.run("uninstall", "--yes", target=None, work=False, expect=0)
    assert env.bs.MD_BEGIN not in md.read_text(encoding="utf-8")
    assert "be nice" in md.read_text(encoding="utf-8")


def test_verify_five_states_fail_closed(env):
    rc, out, err = env.run("verify")
    assert rc == 3  # not installed
    env.run("apply", "--yes", expect=0)
    rc, s = env.json("verify", target=None)
    assert rc == 0
    st = s["states"]
    assert st["installed"]["state"] == "pass"
    for k in ("authorised_account", "first_render", "inspection_passed", "paid_generation_ready"):
        assert st[k]["state"] == "not_run"  # never green by default
    assert s["highest_state"] == "installed"
    assert "claude doctor" in s["note"]


def test_mark_requires_real_evidence_and_student_confirmation(env, tmp_path):
    env.run("apply", "--yes", expect=0)
    rc, out, err = env.run("mark", "first_render", target=None, work=False)
    assert rc == 2  # no evidence
    video = tmp_path / "out.mp4"
    video.write_bytes(b"x")
    env.run("mark", "first_render", "--evidence", str(video), target=None, work=False, expect=0)
    qa = tmp_path / "qa.json"
    qa.write_text(json.dumps({"status": "PASS", "decoded_frames": 10, "expected_frames": 11}), encoding="utf-8")
    rc, out, err = env.run("mark", "inspection_passed", "--evidence", str(qa), target=None, work=False)
    assert rc == 3  # decoded != expected -> fail closed
    qa.write_text(json.dumps({"status": "PASS", "decoded_frames": 11, "expected_frames": 11}), encoding="utf-8")
    env.run("mark", "inspection_passed", "--evidence", str(qa), target=None, work=False, expect=0)
    rc, out, err = env.run("mark", "paid_generation_ready", target=None, work=False)
    assert rc == 2 and "student-confirmed" in err
    rc, s = env.json("verify", target=None)
    assert s["states"]["first_render"]["state"] == "pass" and s["states"]["inspection_passed"]["state"] == "pass"
    assert s["highest_state"] == "installed"  # authorised_account is still not_run -> chain stops: no skipping states


def test_tampered_install_fails_verify_and_invalidates_later_states(env, tmp_path):
    env.run("apply", "--yes", expect=0)
    video = tmp_path / "out.mp4"
    video.write_bytes(b"x")
    env.run("mark", "authorised_account", "--student-confirmed", target=None, work=False, expect=0)
    env.run("mark", "first_render", "--evidence", str(video), target=None, work=False, expect=0)
    (env.claude / "alpha-skill" / "SKILL.md").unlink()
    rc, s = env.json("verify", target=None)
    assert rc == 3 and s["states"]["installed"]["state"] == "fail"
    assert s["states"]["first_render"]["state"] == "not_run" and "stale" in s["states"]["first_render"]["evidence"]


def test_status_and_where(env):
    env.run("apply", "--yes", expect=0)
    rc, out, err = env.run("where", target=None, work=False)
    assert rc == 0 and out.strip() == str(env.state / "toolkit")
    rc, st = env.json("status", target=None, work=False)
    assert rc == 0 and st["toolkit_version"] == "9.9.9" and set(st["skills"]) == {"alpha-skill", "beta-skill"}


def test_uninstall_on_a_clean_home_leaves_only_the_state_folder_with_backups(env):
    env.run("apply", "--yes", "--write-memory-block", expect=0)
    env.run("uninstall", "--yes", target=None, work=False, expect=0)
    left = sorted(p.name for p in env.home.iterdir())
    assert left == [".avc"], left  # .claude/.agents/.codex folders that existed only because of us are gone
    kept = sorted(p.name for p in (env.state).iterdir())
    assert "backups" in kept and "toolkit" not in kept and "install-manifest.json" not in kept

"""tools/warehouse_link.py: turns on the OPTIONAL client warehouse (bundled in tools/warehouse/ or another copy), reports its state and runs its commands; connections and session_hint see it.

A stub ``warehouse.py`` stands in for the real one (a separate repository): it answers ``--self-check`` and ``inbox`` and echoes the rest.
"""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import connections as cn  # noqa: E402
import session_hint as sh  # noqa: E402
import warehouse_link as wl  # noqa: E402

STUB = '''
import json, os, sys
a = sys.argv[1:]
if a[:1] == ["--self-check"]:
    sys.exit(int(os.environ.get("FAKE_SELFCHECK_EXIT", "0")))
if a[:1] == ["inbox"]:
    print(json.dumps({"status": "ok", "waiting": json.loads(os.environ.get("FAKE_WAITING", "[]"))}))
    sys.exit(0)
print(json.dumps({"args": a, "root": os.environ.get("AVC_WAREHOUSE_ROOT"), "toolkit": os.environ.get("AVC_TOOLKIT_ROOT")}))
sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
'''
WAITING = [{"project": "acme-reel", "title": "Reel", "client": "acme", "rounds": [1], "approved": False, "notes": 3}]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    for var in ("AVC_WAREHOUSE_REPO", "AVC_WAREHOUSE_ROOT", "AVC_WAREHOUSE_PORT", "AVC_PATHS_WORK_ROOT", "FAKE_WAITING", "FAKE_EXIT", "FAKE_SELFCHECK_EXIT"):
        monkeypatch.delenv(var, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(wl, "config_file", lambda h=None: home / ".avc" / "warehouse.json")
    return home


@pytest.fixture
def fake_repo(tmp_path):
    d = tmp_path / "wh" / "warehouse"
    d.mkdir(parents=True)
    (d / "warehouse.py").write_text(STUB, encoding="utf-8")
    return tmp_path / "wh"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_find_accepts_repo_folder_warehouse_folder_and_file(fake_repo):
    want = (fake_repo / "warehouse" / "warehouse.py").resolve()
    for target in (fake_repo, fake_repo / "warehouse", fake_repo / "warehouse" / "warehouse.py"):
        assert wl.tool_in(target) == want
    assert wl.tool_in(fake_repo / "nowhere") is None


def test_find_order_flag_env_config_and_not_connected(fake_repo, monkeypatch, isolated):
    assert wl.find() == (None, "not set (optional)")
    cfg = wl.config_file()
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"repo": str(fake_repo)}), encoding="utf-8")
    tool, how = wl.find()
    assert tool and tool.name == "warehouse.py" and str(cfg) in how
    monkeypatch.setenv("AVC_WAREHOUSE_REPO", str(fake_repo))
    assert wl.find()[1] == "AVC_WAREHOUSE_REPO"
    assert wl.find(repo=str(fake_repo))[1] == "--repo"
    tool, how = wl.find(repo=str(fake_repo / "missing"))
    assert tool is None and "has no warehouse.py" in how  # a wrong flag is reported, never silently replaced by another source


def test_set_checks_the_warehouse_then_saves_and_remove_undoes_it(fake_repo, monkeypatch, capsys):
    assert wl.cmd_set(str(fake_repo / "missing"), False, None) == 2
    monkeypatch.setenv("FAKE_SELFCHECK_EXIT", "1")
    assert wl.cmd_set(str(fake_repo), False, None) == 2 and not wl.config_file().exists()
    assert "self-check failed" in capsys.readouterr().out
    monkeypatch.delenv("FAKE_SELFCHECK_EXIT")
    assert wl.cmd_set(str(fake_repo), False, None) == 0
    assert json.loads(wl.config_file().read_text(encoding="utf-8"))["repo"] == str(fake_repo.resolve())
    assert wl.find()[0] is not None
    assert wl.cmd_set("", True, None) == 0 and not wl.config_file().exists()
    assert wl.cmd_set("", True, None) == 0  # removing twice is fine


def test_status_not_connected_is_a_normal_state_with_the_way_to_connect():
    st = wl.status()
    assert st["connected"] is False and st["optional"] is True
    assert st["bundled_available"] is True and "set --bundled" in st["next"] and "notes_board.py" in st["next"]


def test_status_connected_reports_root_waiting_and_port(fake_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("AVC_WAREHOUSE_REPO", str(fake_repo))
    monkeypatch.setenv("AVC_WAREHOUSE_ROOT", str(tmp_path / "projects"))
    monkeypatch.setenv("AVC_WAREHOUSE_PORT", str(free_port()))
    monkeypatch.setenv("FAKE_WAITING", json.dumps(WAITING))
    st = wl.status()
    assert st["connected"] and st["root"] == str(tmp_path / "projects") and st["root_from"] == "AVC_WAREHOUSE_ROOT"
    assert st["server_running"] is False and st["port"] == int(wl.os.environ["AVC_WAREHOUSE_PORT"])
    assert st["waiting"] == WAITING and "wait <project>" in st["next"]
    assert "warning" not in st


def test_root_falls_back_to_the_toolkit_work_root_then_the_warehouse_default(fake_repo, tmp_path, monkeypatch):
    tool = wl.tool_in(fake_repo)
    assert wl.projects_root(tool) == (fake_repo / "projects", "the warehouse's default")
    monkeypatch.setenv("AVC_PATHS_WORK_ROOT", str(tmp_path / "work"))
    assert wl.projects_root(tool) == (tmp_path / "work" / "projects", "work_root/projects")


def test_non_ascii_repo_path_gets_a_warning(tmp_path, monkeypatch):
    d = tmp_path / "מחסן" / "warehouse"
    d.mkdir(parents=True)
    (d / "warehouse.py").write_text(STUB, encoding="utf-8")
    monkeypatch.setenv("AVC_WAREHOUSE_REPO", str(tmp_path / "מחסן"))
    assert "ASCII" in wl.status(probe=False)["warning"]


def test_run_passes_arguments_root_toolkit_and_port_and_returns_the_exit_code(fake_repo, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AVC_WAREHOUSE_REPO", str(fake_repo))
    monkeypatch.setenv("AVC_WAREHOUSE_ROOT", str(tmp_path / "projects"))
    monkeypatch.setenv("AVC_WAREHOUSE_PORT", "8791")
    assert wl.cmd_run(["add", "demo", "draft.mp4", "--label", "d1"], None) == 0
    got = json.loads(capsys.readouterr().out)
    assert got["args"] == ["add", "demo", "draft.mp4", "--label", "d1", "--port", "8791"]
    assert got["root"] == str(tmp_path / "projects") and got["toolkit"] == str(REPO)
    assert wl.cmd_run(["wait", "demo"], None) == 0  # `wait` has no --port: the page is not involved
    assert "--port" not in json.loads(capsys.readouterr().out)["args"]
    assert wl.cmd_run(["url", "demo", "--port", "9000"], None) == 0  # an explicit port is never overridden
    assert json.loads(capsys.readouterr().out)["args"].count("--port") == 1
    monkeypatch.setenv("FAKE_EXIT", "3")
    assert wl.cmd_run(["wait", "demo"], None) == 3


def test_run_refuses_when_not_connected_or_without_a_command(fake_repo, monkeypatch, capsys):
    assert wl.cmd_run(["inbox"], None) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "refused" and "notes_board.py" in out["next"]
    monkeypatch.setenv("AVC_WAREHOUSE_REPO", str(fake_repo))
    assert wl.cmd_run([], None) == 2


def test_cli_status_is_json_and_exit_0_even_when_not_connected():
    import subprocess

    p = subprocess.run([sys.executable, str(REPO / "tools" / "warehouse_link.py"), "status"], capture_output=True, text=True, encoding="utf-8",
                       env={**wl.os.environ, "HOME": str(REPO / "nonexistent-home"), "USERPROFILE": str(REPO / "nonexistent-home")})
    assert p.returncode == 0 and json.loads(p.stdout)["tool"] == "warehouse_link"


def test_connections_report_has_the_warehouse_row(fake_repo, tmp_path, monkeypatch):
    home = tmp_path / "h2"
    home.mkdir()
    rep = cn.report(tmp_path, home=home, entries=[])
    row = next(r for g in rep["groups"].values() for r in g if r["id"] == "warehouse")
    assert row["present"] is False and "optional" in row["how"]
    monkeypatch.setenv("AVC_WAREHOUSE_REPO", str(fake_repo))
    row = next(r for g in cn.report(tmp_path, home=home, entries=[])["groups"].values() for r in g if r["id"] == "warehouse")
    assert row["present"] is True and "warehouse.py" in row["how"]
    assert "warehouse" in cn.human(cn.report(tmp_path, home=home, entries=[]))


def test_session_hint_lists_waiting_notes_and_is_silent_otherwise(fake_repo, tmp_path, monkeypatch):
    assert sh.warehouse_lines(REPO) == []  # not connected
    monkeypatch.setenv("AVC_WAREHOUSE_REPO", str(fake_repo))
    assert sh.warehouse_lines(REPO) == []  # connected, nothing waiting
    monkeypatch.setenv("FAKE_WAITING", json.dumps(WAITING + [{"project": "b", "title": "B", "client": "b", "rounds": [2], "approved": True, "notes": 0}]))
    text = "\n".join(sh.warehouse_lines(REPO))
    assert "acme-reel" in text and "3 note(s)" in text and "APPROVED" in text and "warehouse_link.py" in text and "'With the warehouse'" in text
    empty = tmp_path / "empty"
    empty.mkdir()
    import subprocess

    p = subprocess.run([sys.executable, str(REPO / "tools" / "session_hint.py"), "--cwd", str(empty)], capture_output=True, text=True, encoding="utf-8",
                       env={**wl.os.environ, "AVC_PATHS_WORK_ROOT": str(empty)})
    ctx = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]  # no HyperFrames project, but the warehouse still has something to say
    assert p.returncode == 0 and "acme-reel" in ctx and "hf_studio.py" not in ctx


# ---- the copy that ships in tools/warehouse/ ---------------------------------------------------------------

def test_bundled_copy_ships_and_is_off_until_set(tmp_path, monkeypatch, capsys):
    assert wl.BUNDLED.is_file() and wl.BUNDLED.parent.name == "warehouse"
    assert wl.find() == (None, "not set (optional)")  # shipping is not turning on
    monkeypatch.setenv("AVC_WAREHOUSE_STATE", str(tmp_path / "state"))
    assert wl.cmd_set("", False, None, bundled=True) == 0  # runs the page's real --self-check
    assert json.loads(wl.config_file().read_text(encoding="utf-8")) == {"repo": "bundled"}
    tool, how = wl.find()
    assert tool == wl.BUNDLED.resolve()
    st = wl.status(probe=False)
    assert st["connected"] and st["bundled"] is True and st["state_dir"] == str(tmp_path / "state")
    assert wl.child_env(tool)["AVC_WAREHOUSE_STATE"] == str(tmp_path / "state")
    assert wl.cmd_set("", True, None) == 0 and wl.find()[0] is None


def test_bundled_state_and_projects_stay_outside_the_toolkit_copy(isolated, monkeypatch):
    monkeypatch.setattr(wl.Path, "home", classmethod(lambda cls: isolated))
    monkeypatch.delenv("AVC_WAREHOUSE_STATE", raising=False)
    monkeypatch.setattr("session_hint.configured_work_root", lambda toolkit: None)
    assert wl.state_dir(wl.BUNDLED) == isolated / ".avc" / "warehouse-state"
    root, src = wl.projects_root(wl.BUNDLED)
    assert root == isolated / ".avc" / "warehouse-state" / "projects" and "bundled default" in src
    assert wl.TOOLKIT not in root.parents


def test_library_writes_only_the_warehouses_config_and_refuses_a_missing_folder(fake_repo, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AVC_WAREHOUSE_REPO", str(fake_repo))
    monkeypatch.setenv("AVC_WAREHOUSE_STATE", str(tmp_path / "state"))
    clients = tmp_path / "clients"
    clients.mkdir()
    assert wl.cmd_library(str(tmp_path / "nope"), False, None) == 2
    assert not (tmp_path / "state" / "config.json").exists()
    assert wl.cmd_library(str(clients), False, None) == 0
    cfg = json.loads((tmp_path / "state" / "config.json").read_text(encoding="utf-8"))
    assert cfg == {"library_root": str(clients), "hidden": []}
    assert wl.cmd_library("", True, None) == 0
    assert json.loads((tmp_path / "state" / "config.json").read_text(encoding="utf-8"))["library_root"] == ""


def test_library_needs_the_warehouse_turned_on(capsys):
    assert wl.cmd_library(".", False, None) == 2
    assert "not turned on" in capsys.readouterr().out


@pytest.mark.skipif(wl.os.name != "nt", reason="the launcher is for Windows")
def test_shortcut_writes_one_launcher_and_remove_deletes_it(fake_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("AVC_WAREHOUSE_REPO", str(fake_repo))
    monkeypatch.setenv("AVC_WAREHOUSE_PORT", "8791")
    target = tmp_path / "Desktop" / "Video Warehouse.cmd"
    monkeypatch.setattr(wl, "shortcut_path", lambda: target)
    assert wl.cmd_shortcut(False, None) == 0
    text = target.read_text(encoding="utf-8")
    assert "serve --open --port 8791" in text and "AVC_WAREHOUSE_ROOT" in text
    assert wl.cmd_shortcut(True, None) == 0 and not target.exists()
    assert wl.cmd_shortcut(True, None) == 0


def test_bundled_code_has_no_personal_defaults():
    from pathlib import Path as P
    bad = ("GG " + "creatives", "Edit " + "stuf", "D:" + chr(92) + "Clients", "ori" + "ma")
    for f in wl.BUNDLED.parent.rglob("*"):
        if f.is_file() and f.suffix in {".py", ".js", ".html", ".css", ".json", ".md", ".bat"}:
            text = f.read_text(encoding="utf-8")
            for b in bad:
                assert b not in text, (f.name, b)
    sys.path.insert(0, str(wl.BUNDLED.parent))
    try:
        import library
        assert library.DEFAULTS == {"library_root": "", "hidden": []}
    finally:
        sys.path.remove(str(wl.BUNDLED.parent))


def test_work_root_comes_from_the_per_machine_file_before_the_shipped_default(tmp_path, monkeypatch):
    monkeypatch.delenv("AVC_PATHS_WORK_ROOT", raising=False)
    (tmp_path / "toolkit.toml").write_text('[paths]\nwork_root = ""\n', encoding="utf-8")
    assert sh.configured_work_root(tmp_path) is None
    (tmp_path / "toolkit.local.toml").write_text('[paths]\nwork_root = "C:/avc-work"\n', encoding="utf-8")
    assert sh.configured_work_root(tmp_path) == Path("C:/avc-work")

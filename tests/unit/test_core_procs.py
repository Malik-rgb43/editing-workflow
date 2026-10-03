"""procs.py: argument-list-only commands, UTF-8, whole-tree kill on timeout, pid identity."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

from core import procs
from core.errors import ProcessError

PY = sys.executable


def wait_dead(pid: int, seconds: float = 8.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if not procs.pid_alive(pid):
            return True
        time.sleep(0.1)
    return False


def test_string_commands_and_shell_style_are_rejected():
    with pytest.raises(ProcessError) as e:
        procs.run("echo hi")  # type: ignore[arg-type]
    assert "argument list" in str(e.value)
    with pytest.raises(ProcessError):
        procs.run([])
    with pytest.raises(ProcessError):
        procs.run(["echo", "a\x00b"])


def test_run_captures_utf8_exactly_even_with_hostile_arguments(tricky_dir):
    arg = "שלום 'עולם' 🎬 & echo pwned; $(x) \"q\""
    code = "import sys; sys.stdout.write(sys.argv[1]); sys.stderr.write('שגיאה')"
    r = procs.run([PY, "-c", code, arg], timeout=30, cwd=tricky_dir)
    assert r.ok and r.stdout == arg and r.stderr == "שגיאה"  # no shell: nothing was interpreted, nothing was mangled


def test_run_reports_nonzero_exit_and_is_not_ok(tmp_path):
    r = procs.run([PY, "-c", "import sys; sys.exit(7)"], timeout=30)
    assert r.returncode == 7 and not r.ok and not r.timed_out


def test_missing_executable_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        procs.run(["definitely-not-a-real-binary-xyz"])


def test_log_file_is_utf8_without_bom(tricky_dir):
    log = tricky_dir / "run.log"
    procs.run([PY, "-c", "print('שלום 🎬')"], timeout=30, log_path=log)
    raw = log.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf") and "שלום 🎬".encode("utf-8") in raw and b"exit 0" in raw


def test_stdin_input_is_passed():
    r = procs.run([PY, "-c", "import sys; print(sys.stdin.read().upper())"], input="abc ש", timeout=30)
    assert r.stdout.strip() == "ABC ש"


def test_children_get_utf8_env():
    r = procs.run([PY, "-c", "import os; print(os.environ['PYTHONUTF8'], os.environ['PYTHONIOENCODING'])"], timeout=30)
    assert r.stdout.split() == ["1", "utf-8"]


def test_env_is_merged_over_the_current_environment():
    code = "import os; print(os.environ['AVC_X'], 'PATH' in os.environ or 'Path' in os.environ)"
    r = procs.run([PY, "-c", code], env={"AVC_X": "שלום"}, timeout=30)
    assert r.stdout.split() == ["שלום", "True"]


def test_timeout_kills_the_whole_tree_not_just_the_child(tmp_path):
    pidfile = tmp_path / "grandchild.pid"
    grand = f"import os,time,pathlib; pathlib.Path(r'{pidfile}').write_text(str(os.getpid())); time.sleep(120)"
    child = (
        "import subprocess,sys,time;"
        f"subprocess.Popen([sys.executable,'-c',{grand!r}]);"
        "time.sleep(120)"
    )
    t0 = time.monotonic()
    r = procs.run([PY, "-c", child], timeout=3.0)
    assert r.timed_out and not r.ok and r.returncode is None
    assert time.monotonic() - t0 < 30
    deadline = time.monotonic() + 10
    while not pidfile.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    gpid = int(pidfile.read_text())
    assert wait_dead(gpid), "grandchild survived the timeout: only the direct child was killed"


@pytest.mark.skipif(os.name != "nt", reason="job-object kill-on-close is the Windows mechanism")
def test_closing_the_launcher_side_handle_kills_descendants_on_windows():
    p = procs.spawn([PY, "-c", "import time; time.sleep(120)"])
    pid = p.pid
    assert procs.pid_alive(pid)
    p.close()  # what the OS does when the launcher itself crashes
    assert wait_dead(pid)


def test_terminate_tree_is_idempotent_and_stops_a_sleeper():
    p = procs.spawn([PY, "-c", "import time; time.sleep(120)"])
    assert p.poll() is None
    p.terminate_tree()
    p.terminate_tree()
    assert p.poll() is not None
    p.close()


def test_pid_alive_and_identity():
    me = os.getpid()
    assert procs.pid_alive(me)
    st = procs.process_start_time(me)
    assert st and st == procs.process_start_time(me)  # stable
    assert not procs.pid_alive(0) and not procs.pid_alive(-5)
    p = procs.spawn([PY, "-c", "import time; time.sleep(30)"])
    other = procs.process_start_time(p.pid)
    assert other and other != st
    p.terminate_tree()
    p.close()
    assert wait_dead(p.pid)


def test_no_tasklist_or_shell_true_in_core_sources():
    import re

    src = Path(__file__).resolve().parents[2] / "src" / "core"
    quoted_tasklist = re.compile(r"""["']tasklist(\.exe)?["']""", re.I)
    shell_true = re.compile(r"(?<!`)shell\s*=\s*True(?!`)")
    for f in src.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert not quoted_tasklist.search(text), f"{f.name} spawns tasklist"
        assert not shell_true.search(text), f"{f.name} uses shell=True"

"""lock.py: kernel-lock ownership, advisory sidecar, no takeover, heartbeat, crash recovery.

Regression tests for the TWO races reproduced against the author's original ``render_lock`` (frontier F31, blueprint
TOOLS_SPEC section 2):

1. ``test_two_processes_never_both_enter`` - the non-atomic read-before-write race: two real processes both saw "no owner"
   and both entered.
2. ``test_old_timestamp_cannot_steal_a_live_lock`` - an old (or forged, or future) timestamp / dead PID in the metadata let a
   contender take a lock whose owner was alive and running.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from core import lock
from core.errors import LockBusy, LockOwnershipError, LockUncertain

SRC = str(Path(__file__).resolve().parents[2] / "src")
ENV = {**os.environ, "PYTHONPATH": SRC, "PYTHONUTF8": "1"}
PY = sys.executable

pytestmark = pytest.mark.slow


@pytest.fixture()
def lockfile(tricky_dir) -> Path:
    return tricky_dir / "shared dir" / "render.lock"  # hostile folder name + a not-yet-existing sub-folder


def read_meta(lockfile) -> dict:
    """Read the sidecar, tolerating the instant an atomic replace is in flight (Windows)."""
    for _ in range(50):
        try:
            return json.loads(Path(lock.owner_path(lockfile)).read_text(encoding="utf-8"))
        except (PermissionError, FileNotFoundError, ValueError):
            time.sleep(0.02)
    raise AssertionError("sidecar unreadable")


def spawn_py(code: str, *args: str, **kw) -> subprocess.Popen:
    return subprocess.Popen([PY, "-c", code, *args], env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=kw.pop("stdin", subprocess.DEVNULL), **kw)


HOLDER = """
import sys, time
from core import lock
path, mode = sys.argv[1], sys.argv[2]
hb = mode != "nohb"
lease = lock.acquire(path, job="holder job", timeout=10, heartbeat=hb, interval=0.1)
print("READY", lease.token, flush=True)
if mode == "crash":
    import os
    os._exit(17)
sys.stdin.readline()          # hold until the parent says go
lease.release()
print("RELEASED", flush=True)
"""


def start_holder(path: Path, mode: str = "hold") -> subprocess.Popen:
    p = spawn_py(HOLDER, str(path), mode, stdin=subprocess.PIPE)
    line = p.stdout.readline().decode()
    assert line.startswith("READY"), (line, p.stderr.read().decode() if p.poll() is not None else "")
    return p


def stop_holder(p: subprocess.Popen) -> str:
    out, _ = p.communicate(b"go\n", timeout=30)
    return out.decode()


# ------------------------------------------------------------------------------------------------ constants / basics
def test_one_stale_constant_and_it_is_the_render_watch_rule():
    assert lock.STALE_AFTER_S == 600.0  # 10 minutes: same "no progress" rule as render_watch (TOOLS_SPEC 3.2)
    assert lock.HEARTBEAT_INTERVAL_S < lock.STALE_AFTER_S / 10
    doc = lock.__doc__ or ""
    assert "STALE_AFTER_S" in doc and "never" in doc


def test_acquire_release_roundtrip_with_sidecar(lockfile):
    with lock.acquire(lockfile, job="render héllo 🎬", heartbeat=False) as lease:
        meta = read_meta(lockfile)
        assert meta["pid"] == os.getpid() and meta["token"] == lease.token and meta["job"] == "render héllo 🎬"
        assert meta["pid_start"] and meta["stale_after_s"] == lock.STALE_AFTER_S and "advisory" in meta["ownership"]
        assert lock.status(lockfile).state == "held" and lock.status(lockfile).held_by_this_process
    assert not Path(lock.owner_path(lockfile)).exists()  # owner metadata removed...
    assert lockfile.exists()  # ...the persistent lock file itself is never deleted
    assert lock.status(lockfile).state == "free"
    runs = [json.loads(x) for x in Path(lock.runs_path(lockfile)).read_text(encoding="utf-8").splitlines()]
    assert [r["event"] for r in runs] == ["acquire", "release"] and runs[0]["token"] == runs[1]["token"]


def test_relative_path_and_bad_timeout_are_rejected():
    with pytest.raises(ValueError):
        lock.acquire("render.lock")
    for bad in (-1, float("nan"), True, "5"):
        with pytest.raises(ValueError):
            lock.acquire(os.path.abspath("x.lock"), timeout=bad)  # type: ignore[arg-type]


def test_reentrant_same_thread_and_other_thread_is_busy(lockfile):
    outer = lock.acquire(lockfile, heartbeat=False)
    inner = lock.acquire(lockfile, heartbeat=False)
    assert inner.release() == {"released": False, "remaining_depth": 1}
    errors: list[Exception] = []

    def other() -> None:
        try:
            lock.acquire(lockfile, timeout=0)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    t = threading.Thread(target=other)
    t.start()
    t.join()
    assert len(errors) == 1 and isinstance(errors[0], LockBusy)  # in-process threads contend like processes
    assert outer.release()["released"] is True


def test_double_release_and_foreign_lease_are_refused(lockfile):
    a = lock.acquire(lockfile, heartbeat=False)
    a.release()
    with pytest.raises(LockOwnershipError):
        a.release()
    b = lock.acquire(lockfile, heartbeat=False)
    with pytest.raises(LockOwnershipError):
        a.release()  # an old lease cannot release a newer acquisition
    b.release()


def test_heartbeat_updates_advisory_timestamp(lockfile):
    with lock.acquire(lockfile, interval=0.1) as lease:
        first = read_meta(lockfile)["heartbeat_utc"]
        deadline = time.monotonic() + 8
        later = first
        while later == first and time.monotonic() < deadline:
            time.sleep(0.2)
            later = read_meta(lockfile)["heartbeat_utc"]
        assert later != first and not lease.metadata_tampered


def test_tampered_sidecar_is_preserved_on_release_but_kernel_lock_is_released(lockfile):
    lease = lock.acquire(lockfile, heartbeat=False)
    Path(lock.owner_path(lockfile)).write_text(json.dumps({"someone": "else"}), encoding="utf-8")
    res = lease.release()
    assert res["released"] and res["metadata_mismatch"]
    assert json.loads(Path(lock.owner_path(lockfile)).read_text(encoding="utf-8")) == {"someone": "else"}
    assert lock.status(lockfile).state == "free"
    lock.acquire(lockfile, heartbeat=False).release()


# ------------------------------------------------------------------------------------------------ race 1
RACER = """
import os, sys, time
from core import lock
path, crit, results, start_at = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
while time.time() < start_at:
    pass                                   # all contenders start at the same instant
try:
    lease = lock.acquire(path, job="racer", timeout=60, poll=0.002, heartbeat=False)
except Exception as exc:
    print("ERR", type(exc).__name__, exc, flush=True); sys.exit(2)
try:
    try:
        fd = os.open(crit, os.O_CREAT | os.O_EXCL | os.O_WRONLY)   # exclusive marker: fails if someone else is inside
    except FileExistsError:
        print("OVERLAP", flush=True); sys.exit(3)
    time.sleep(0.05)
    os.close(fd); os.unlink(crit)
    with open(results, "a") as fh:
        fh.write(lease.token + "\\n")
    print("OK", flush=True)
finally:
    lease.release()
"""


def test_two_processes_never_both_enter(lockfile, tmp_path):
    """The reproduced read-before-write race: N processes released at the same instant, 4 rounds."""
    crit = tmp_path / "critical.flag"
    results = tmp_path / "results.txt"
    for round_no in range(4):
        start_at = time.time() + 1.5
        procs = [spawn_py(RACER, str(lockfile), str(crit), str(results), repr(start_at)) for _ in range(6)]
        outs = [(p.communicate(timeout=120), p.returncode) for p in procs]
        for (out, err), rc in outs:
            assert rc == 0, (round_no, out.decode(), err.decode())
            assert out.decode().strip() == "OK"
    tokens = results.read_text().split()
    assert len(tokens) == 24 and len(set(tokens)) == 24  # every acquisition happened, each with its own token
    assert not crit.exists()


def test_exactly_one_of_simultaneous_try_once_acquires_wins(lockfile, tmp_path):
    """timeout=0 contenders released together: one wins, the rest get LockBusy (never two winners)."""
    code = """
import sys, time
from core import lock
path, start_at, hold = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
while time.time() < start_at: pass
try:
    lease = lock.acquire(path, timeout=0, heartbeat=False)
except lock.LockBusy:
    print("BUSY", flush=True); sys.exit(0)
print("WON", flush=True); time.sleep(hold); lease.release()
"""
    start_at = time.time() + 1.5
    ps = [spawn_py(code, str(lockfile), repr(start_at), "1.5") for _ in range(6)]
    results = [p.communicate(timeout=60)[0].decode().strip() for p in ps]
    assert results.count("WON") == 1 and results.count("BUSY") == 5, results


# ------------------------------------------------------------------------------------------------ race 2
def test_old_timestamp_cannot_steal_a_live_lock(lockfile):
    holder = start_holder(lockfile, "nohb")  # no heartbeat thread: nothing repairs the metadata we are about to forge
    try:
        side = Path(lock.owner_path(lockfile))
        real = json.loads(side.read_text(encoding="utf-8"))
        forged_variants = [
            {**real, "heartbeat_utc": "1970-01-01T00:00:00+00:00", "started_utc": "1970-01-01T00:00:00+00:00"},  # ancient
            {**real, "heartbeat_utc": "2999-01-01T00:00:00+00:00"},  # from the future
            {**real, "pid": 4_000_000, "pid_start": "win:1"},  # dead / recycled pid
            {"token": "forged"},  # nonsense
        ]
        for forged in forged_variants:
            side.write_text(json.dumps(forged), encoding="utf-8")
            with pytest.raises(LockBusy):
                lock.acquire(lockfile, timeout=0.2)
            st = lock.status(lockfile)
            assert st.state == "held" and not st.held_by_this_process  # the kernel says held, whatever the metadata says
        side.write_text("{ not json", encoding="utf-8")
        with pytest.raises(LockBusy):
            lock.acquire(lockfile, timeout=0)
        side.write_bytes(b"x" * 70000)  # oversized metadata
        with pytest.raises(LockBusy):
            lock.acquire(lockfile, timeout=0)
        assert lock.status(lockfile).state == "held"
    finally:
        assert "RELEASED" in stop_holder(holder)
    lock.acquire(lockfile, timeout=5, heartbeat=False).release()  # once the real owner is done the lock is available


def test_status_labels_stale_heartbeat_as_advisory_and_never_acts(lockfile):
    holder = start_holder(lockfile, "nohb")
    try:
        side = Path(lock.owner_path(lockfile))
        real = json.loads(side.read_text(encoding="utf-8"))
        old = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() - lock.STALE_AFTER_S - 60))
        side.write_text(json.dumps({**real, "heartbeat_utc": old}), encoding="utf-8")
        st = lock.status(lockfile)
        assert st.state == "held" and st.advisory_stale is True and st.heartbeat_age_s > lock.STALE_AFTER_S
        assert st.owner_pid_alive is True and st.owner_pid_identity_ok is True  # pid + start-time identify the live holder
        assert "do NOT remove" in st.note and "ask its owner" in st.note
        with pytest.raises(LockBusy):
            lock.acquire(lockfile, timeout=0)  # stale label never turns into a takeover
        side.write_text(json.dumps({**real, "pid_start": "win:1"}), encoding="utf-8")
        assert lock.status(lockfile).owner_pid_identity_ok is False  # recycled-pid detection
    finally:
        stop_holder(holder)


# ------------------------------------------------------------------------------------------------ crash recovery
def test_crashed_owner_releases_via_the_kernel_and_leaves_untrusted_metadata(lockfile):
    holder = start_holder(lockfile, "crash")
    assert holder.wait(timeout=30) == 17
    st = lock.status(lockfile)
    assert st.state == "free" and "stale" in st.note  # leftover sidecar of a dead owner is only context
    lease = lock.acquire(lockfile, timeout=5, heartbeat=False)
    prev = lease.recovery_metadata
    assert prev is not None and prev["job"] == "holder job" and prev["token"] != lease.token
    lease.release()


def test_malformed_leftover_metadata_cannot_block_a_free_lock(lockfile):
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    Path(lock.owner_path(lockfile)).write_text("\x00\x01 garbage", encoding="utf-8")
    with lock.acquire(lockfile, heartbeat=False) as lease:
        assert lease.recovery_metadata == {"untrusted": "malformed metadata"}


def test_stale_metadata_with_live_looking_pid_and_future_time_does_not_block_free_lock(lockfile):
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    Path(lock.owner_path(lockfile)).write_text(json.dumps({"pid": os.getpid(), "token": "old", "heartbeat_utc": "2999-01-01T00:00:00+00:00"}), encoding="utf-8")
    with lock.acquire(lockfile, heartbeat=False) as lease:
        assert lease.recovery_metadata["token"] == "old"


# ------------------------------------------------------------------------------------------------ uncertainty is never "free"
def test_unopenable_lock_path_is_uncertain_not_free(tmp_path):
    d = tmp_path / "a directory"
    d.mkdir()
    with pytest.raises(LockUncertain):
        lock.acquire(d, heartbeat=False)  # cannot be opened as a file
    assert lock.status(d).state == "uncertain"


def test_network_volume_is_refused_unless_explicitly_allowed(lockfile, monkeypatch):
    monkeypatch.setattr(lock, "_is_network_path", lambda p: True)
    with pytest.raises(LockUncertain) as e:
        lock.acquire(lockfile)
    assert "network" in str(e.value)
    lock.acquire(lockfile, allow_network=True, heartbeat=False).release()


# ------------------------------------------------------------------------------------------------ run under lock
def test_lock_is_held_for_the_whole_child_lifetime_and_tree_is_killed_on_timeout(lockfile, tmp_path):
    flag = tmp_path / "child-started"
    child = f"import pathlib,time; pathlib.Path(r'{flag}').write_text('1'); time.sleep(2.0)"
    box: dict = {}

    def go() -> None:
        box["r"] = lock.run_under_lock([PY, "-c", child], lock_path=lockfile, job="child", run_timeout=60)

    t = threading.Thread(target=go)
    t.start()
    deadline = time.monotonic() + 20
    while not flag.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert flag.exists()
    with pytest.raises(LockBusy):
        lock.acquire(lockfile, timeout=0)  # still running -> still locked
    t.join(timeout=30)
    assert box["r"].ok
    lock.acquire(lockfile, timeout=5, heartbeat=False).release()  # released after the child exited

    r = lock.run_under_lock([PY, "-c", "import time; time.sleep(60)"], lock_path=lockfile, job="hang", run_timeout=1.0)
    assert r.timed_out and not r.ok
    lock.acquire(lockfile, timeout=5, heartbeat=False).release()  # a timed-out child never leaves the lock held


def test_run_under_lock_busy_does_not_run_the_command(lockfile, tmp_path):
    marker = tmp_path / "ran"
    with lock.acquire(lockfile, heartbeat=False):
        errors = []

        def other() -> None:
            try:
                lock.run_under_lock([PY, "-c", f"open(r'{marker}','w').write('x')"], lock_path=lockfile, job="x", wait_timeout=0)
            except LockBusy as exc:
                errors.append(exc)

        t = threading.Thread(target=other)
        t.start()
        t.join()
    assert len(errors) == 1 and not marker.exists()


def test_cli_status_and_run(lockfile):
    r = subprocess.run([PY, "-m", "core", "lock", "status", "--path", str(lockfile)], env=ENV, capture_output=True, timeout=60)
    assert r.returncode == 0 and json.loads(r.stdout.decode("utf-8"))["state"] == "free"
    r = subprocess.run([PY, "-m", "core", "lock", "run", "--path", str(lockfile), "--job", "cli", "--", PY, "-c", "print('שלום')"], env=ENV, capture_output=True, timeout=60)
    assert r.returncode == 0 and "שלום" in r.stdout.decode("utf-8")
    with lock.acquire(lockfile, heartbeat=False):
        # held by THIS process: a second process sees it as held (exit 4 = busy)
        r = subprocess.run([PY, "-m", "core", "lock", "status", "--path", str(lockfile)], env=ENV, capture_output=True, timeout=60)
        assert r.returncode == 4 and json.loads(r.stdout.decode("utf-8"))["state"] == "held"
        r = subprocess.run([PY, "-m", "core", "lock", "run", "--path", str(lockfile), "--job", "cli", "--", PY, "-c", "print(1)"], env=ENV, capture_output=True, timeout=60)
        assert r.returncode == 4


# ------------------------------------------------------------------------------------------------ negative controls
def test_control_naive_read_then_write_design_admits_two_owners(tmp_path):
    """Why a kernel lock: the ORIGINAL design (read owner file; if none/old, write ourselves) lets two contenders in.

    Both threads read 'no owner' before either writes (forced with a barrier, exactly the interleaving F31 injected into
    the author's tool). The same test applied to ``core.lock`` is the real-process race above, where it cannot happen.
    """
    owner = tmp_path / "naive.owner"
    barrier = threading.Barrier(2)
    entered: list[int] = []

    def naive_acquire(n: int) -> None:
        saw_owner = owner.exists()
        barrier.wait(timeout=10)  # both have now looked
        if not saw_owner:
            owner.write_text(str(n))
            entered.append(n)

    ts = [threading.Thread(target=naive_acquire, args=(i,)) for i in (1, 2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert sorted(entered) == [1, 2]  # BOTH "own" the lock: the defect core.lock removes


def test_control_age_based_takeover_steals_a_live_lock(tmp_path):
    """The ORIGINAL staleness rule (old timestamp => take over) steals from a live owner; core.lock has no such rule."""
    owner = tmp_path / "naive.owner"
    owner.write_text(json.dumps({"pid": os.getpid(), "ts": 0}))  # live pid, ancient timestamp

    def naive_try_take(threshold_s: float) -> bool:
        meta = json.loads(owner.read_text())
        return time.time() - meta["ts"] > threshold_s  # "stale" => take over

    assert naive_try_take(3 * 3600) is True  # the live owner (this very process) just lost its lock

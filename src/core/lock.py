"""Machine-wide single-heavy-job lock (``render_lock`` replacement): OS kernel lock + advisory sidecar + heartbeat.

Design (src: frontier F31 prototype, reproduced defects in blueprint TOOLS_SPEC section 2 ``render_lock`` row):

* **Ownership is a kernel lock**, nothing else: ``msvcrt.locking`` (byte 0, non-blocking) on Windows, ``fcntl.flock`` on
  POSIX, held on a file descriptor of ONE absolute, shared, persistent lock file. The OS releases it when the owner process
  dies, however it dies. The file is never deleted or replaced.  Acquisition is atomic: there is no "read the owner file,
  then write it" window, so two contenders can never both enter (fixes the reproduced read-before-write race).
* **The sidecar JSON is advisory.** ``<lock>.owner.json`` carries pid + process start-time + token + job label +
  heartbeat for humans and status screens. It never decides ownership; an ancient/future/forged timestamp, a dead or
  recycled PID or a malformed file cannot make a live job lose its lock (fixes the reproduced "old timestamp steals a live
  lock").
* **No automatic takeover while the owner's lifetime is uncertain.** There is nothing to take over: either the kernel
  grants the lock (the previous owner is gone) or it refuses (someone holds it - wait, or ask them).  When the state
  cannot be determined (permission error, network volume) the result is ``LockUncertain``, never "free".
* **One stale constant.** ``STALE_AFTER_S`` (600 s = 10 min, the same "no progress for 10 minutes" rule ``render_watch`` uses,
  blueprint TOOLS_SPEC section 3.2) is the age after which ``status`` *labels* a holder's heartbeat "stale (advisory)". The
  old code used 3 h while its docs said 60 min; there is now exactly one number and it never triggers an action.
* **Heartbeat.** A daemon thread rewrites ``heartbeat_utc`` every ``HEARTBEAT_INTERVAL_S`` (30 s) while the lease is held.
* **Process-tree containment.** ``run_under_lock`` keeps the lease for the whole subprocess lifetime and starts the child
  in a kill-on-close job object / process group (``procs.spawn``), so a crashed launcher cannot leave an orphan render that
  runs without the lock.

Limits (kept honest): cooperative callers only; same-volume local filesystems (network volumes are refused unless
``allow_network=True``, and then not guaranteed); PID reuse is detected by start-time, not forced by tests; the POSIX branch
is exercised only when the test-suite runs on Linux/macOS (CI matrix).

Usage:
    python -m core lock status [--path LOCKFILE]
    python -m core lock run --job NAME [--wait SECONDS] [--timeout SECONDS] [--path LOCKFILE] -- COMMAND [ARGS...]
"""

from __future__ import annotations

import datetime as _dt
import json
import errno
import os
import socket
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from . import __version__
from .errors import EXIT_BUSY, LockBusy, LockOwnershipError, LockUncertain
from .fsio import append_line, fs_path, write_text_atomic
from .procs import RunResult, pid_alive, process_start_time, run

if os.name == "nt":
    import msvcrt
else:  # pragma: no cover - exercised on POSIX CI
    import fcntl

__all__ = [
    "HEARTBEAT_INTERVAL_S",
    "STALE_AFTER_S",
    "Lease",
    "LockStatus",
    "acquire",
    "status",
    "run_under_lock",
    "owner_path",
    "runs_path",
    "main",
]

HEARTBEAT_INTERVAL_S = 30.0
#: Advisory label threshold (seconds). Never used to take over a lock.
STALE_AFTER_S = 600.0
_MAX_SIDECAR_BYTES = 65536
# Symbolic, not numeric: EAGAIN is 11 on Linux/Windows but 35 on macOS (found by CI on macOS). msvcrt reports a held byte range as
# EACCES / EDEADLOCK (36 on Windows, kept explicitly).
_BUSY_ERRNOS = tuple(sorted({errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES, errno.EDEADLK, 36}))

_guard = threading.RLock()
_states: dict[str, "_State"] = {}


def owner_path(lock_path: str | os.PathLike[str]) -> str:
    return os.fspath(lock_path) + ".owner.json"


def runs_path(lock_path: str | os.PathLike[str]) -> str:
    return os.fspath(lock_path) + ".runs.jsonl"


def _utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _key(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


# --------------------------------------------------------------------------------------------------------------------
# kernel lock primitives
# --------------------------------------------------------------------------------------------------------------------


def _kernel_lock(fd: int) -> None:
    os.lseek(fd, 0, os.SEEK_SET)
    if os.name == "nt":
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:  # pragma: no cover - POSIX
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _kernel_unlock(fd: int) -> None:
    os.lseek(fd, 0, os.SEEK_SET)
    if os.name == "nt":
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:  # pragma: no cover - POSIX
        fcntl.flock(fd, fcntl.LOCK_UN)


def _try_lock_path(path: str) -> tuple[str, int | None]:
    """-> ("acquired", fd) | ("busy", None). Raises ``LockUncertain`` for anything that is not a plain 'held'."""
    try:
        fd = os.open(fs_path(path), os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as exc:
        raise LockUncertain(f"cannot open lock file {path!r}: {exc.strerror or exc}", remediation="check folder permissions and that the path is on a local disk") from exc
    try:
        _kernel_lock(fd)
    except OSError as exc:
        os.close(fd)
        if getattr(exc, "errno", None) in _BUSY_ERRNOS:
            return "busy", None
        raise LockUncertain(f"lock state of {path!r} could not be determined (errno {getattr(exc, 'errno', '?')}: {exc.strerror or exc})", remediation="do not assume the lock is free; check the volume is local and retry") from exc
    return "acquired", fd


def _is_network_path(path: str) -> bool | None:
    """True/False when known, ``None`` when this platform cannot tell."""
    absolute = os.path.abspath(path)
    if os.name == "nt":
        if absolute.startswith("\\\\") and not absolute.startswith("\\\\?\\"):
            return True
        import ctypes

        drive = os.path.splitdrive(absolute)[0]
        if not drive:
            return None
        return ctypes.windll.kernel32.GetDriveTypeW(drive + "\\") == 4  # DRIVE_REMOTE
    if sys.platform.startswith("linux"):  # pragma: no cover - Linux CI
        try:
            best, fstype = "", ""
            with open("/proc/self/mountinfo", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    parts = line.split()
                    mount = parts[4]
                    dash = parts.index("-")
                    if absolute == mount or absolute.startswith(mount.rstrip("/") + "/"):
                        if len(mount) > len(best):
                            best, fstype = mount, parts[dash + 1]
            return fstype in {"nfs", "nfs4", "cifs", "smb3", "smbfs", "fuse.sshfs", "9p", "afs", "ceph", "lustre"}
        except (OSError, ValueError, IndexError):
            return None
    return None


# --------------------------------------------------------------------------------------------------------------------
# sidecar (advisory)
# --------------------------------------------------------------------------------------------------------------------


def _read_sidecar(lock_path: str) -> dict[str, Any] | None:
    try:
        with open(fs_path(owner_path(lock_path)), "rb") as fh:
            raw = fh.read(_MAX_SIDECAR_BYTES + 1)
    except FileNotFoundError:
        return None
    except OSError:
        return {"untrusted": "unreadable metadata"}
    if len(raw) > _MAX_SIDECAR_BYTES:
        return {"untrusted": "oversized metadata"}
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        return {"untrusted": "malformed metadata"}
    return data if isinstance(data, dict) else {"untrusted": "metadata is not an object"}


def _write_sidecar(lock_path: str, payload: dict[str, Any]) -> None:
    write_text_atomic(owner_path(lock_path), json.dumps(payload, ensure_ascii=False))


# --------------------------------------------------------------------------------------------------------------------
# lease
# --------------------------------------------------------------------------------------------------------------------


@dataclass
class _State:
    path: str
    fd: int
    token: str
    thread: int
    job: str
    started_mono: float
    depth: int = 1
    previous: dict[str, Any] | None = None
    stop: threading.Event = field(default_factory=threading.Event)
    hb_thread: threading.Thread | None = None
    interval: float = HEARTBEAT_INTERVAL_S
    pid_start: str | None = None
    metadata_tampered: bool = False


class Lease:
    """One acquisition. Use as a context manager; ``release()`` is explicit and may be called once per lease object."""

    def __init__(self, state: _State) -> None:
        self._state = state
        self._token = state.token
        self._released = False

    @property
    def token(self) -> str:
        return self._token

    @property
    def path(self) -> str:
        return self._state.path

    @property
    def recovery_metadata(self) -> dict[str, Any] | None:
        """Untrusted sidecar content left by a previous owner that crashed (kept as context, never as a decision)."""
        return self._state.previous

    @property
    def metadata_tampered(self) -> bool:
        return self._state.metadata_tampered

    def release(self) -> dict[str, Any]:
        with _guard:
            if self._released:
                raise LockOwnershipError("lease already released")
            s = self._state
            if self._token != s.token or _states.get(_key(s.path)) is not s:
                raise LockOwnershipError("not the owning lease")
            self._released = True
            s.depth -= 1
            if s.depth:
                return {"released": False, "remaining_depth": s.depth}
            s.stop.set()
            hb = s.hb_thread
        if hb is not None and hb is not threading.current_thread():
            hb.join(timeout=5)
        with _guard:
            mismatch = False
            try:
                current = _read_sidecar(s.path)
                if isinstance(current, dict) and current.get("token") == s.token:
                    try:
                        os.unlink(fs_path(owner_path(s.path)))
                    except FileNotFoundError:
                        pass
                else:
                    mismatch = True  # someone rewrote the advisory file; leave their content alone
            finally:
                try:
                    _kernel_unlock(s.fd)
                finally:
                    os.close(s.fd)
                    _states.pop(_key(s.path), None)
            held = time.monotonic() - s.started_mono
        try:
            append_line(runs_path(s.path), json.dumps({"event": "release", "token": s.token, "pid": os.getpid(), "job": s.job, "utc": _utc(), "held_s": round(held, 3)}, ensure_ascii=False))
        except OSError:
            pass
        return {"released": True, "metadata_mismatch": mismatch, "held_s": round(held, 3)}

    def __enter__(self) -> "Lease":
        return self

    def __exit__(self, *exc: object) -> None:
        if not self._released:
            self.release()


def _heartbeat_loop(state: _State, base_payload: dict[str, Any]) -> None:
    payload = dict(base_payload)
    while not state.stop.wait(state.interval):
        current = _read_sidecar(state.path)
        if not (isinstance(current, dict) and current.get("token") == state.token):
            state.metadata_tampered = True  # advisory file was replaced/removed: do not fight over it
            continue
        payload["heartbeat_utc"] = _utc()
        try:
            _write_sidecar(state.path, payload)
        except OSError:
            pass  # advisory only; the kernel lock is unaffected


def acquire(
    path: str | os.PathLike[str],
    *,
    job: str = "heavy job",
    timeout: float = 0.0,
    poll: float = 0.05,
    heartbeat: bool = True,
    interval: float = HEARTBEAT_INTERVAL_S,
    allow_network: bool = False,
) -> Lease:
    """Acquire the heavy-job lock at ``path`` (absolute, shared by all toolkit copies).

    ``timeout`` seconds of polling (0 = try once). Raises ``LockBusy`` when held, ``LockUncertain`` when the state cannot be
    established. Re-entrant for the same thread of this process (inner releases keep the lock).
    """
    p = os.fspath(path)
    if not os.path.isabs(p):
        raise ValueError("an absolute shared lock path is required (one path for every toolkit copy; set [paths] lock_path)")
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout < 0 or timeout != timeout:
        raise ValueError("timeout must be a finite number >= 0")
    if poll <= 0:
        raise ValueError("poll must be > 0")
    p = os.path.abspath(p)
    key = _key(p)
    os.makedirs(os.path.dirname(fs_path(p)), exist_ok=True)
    if not allow_network and _is_network_path(p):
        raise LockUncertain(
            f"{p!r} is on a network volume; kernel locks there are not reliable",
            remediation="put the lock file on a local disk (set [paths] lock_path) or pass allow_network=True knowingly",
        )
    t_wait = time.monotonic()
    deadline = t_wait + timeout
    while True:
        with _guard:
            existing = _states.get(key)
            if existing is not None and existing.thread == threading.get_ident():
                existing.depth += 1
                return Lease(existing)
            if existing is None:
                outcome, fd = _try_lock_path(p)
                if outcome == "acquired":
                    assert fd is not None
                    return _finish_acquire(p, key, fd, job, interval, heartbeat, time.monotonic() - t_wait)
        if time.monotonic() >= deadline:
            holder = _read_sidecar(p)
            who = ""
            if isinstance(holder, dict) and "pid" in holder:
                who = f" (advisory: pid {holder.get('pid')}, job {holder.get('job')!r}, heartbeat {holder.get('heartbeat_utc')})"
            raise LockBusy(f"heavy-job lock {p!r} is held{who}", remediation="wait for the running job, or ask its owner; the lock is never taken over automatically")
        time.sleep(min(poll, max(0.0, deadline - time.monotonic())))


def _finish_acquire(p: str, key: str, fd: int, job: str, interval: float, heartbeat: bool, waited: float) -> Lease:
    token = uuid.uuid4().hex
    pid = os.getpid()
    try:
        previous = _read_sidecar(p)
        state = _State(path=p, fd=fd, token=token, thread=threading.get_ident(), job=str(job), started_mono=time.monotonic(), previous=previous, interval=interval, pid_start=process_start_time(pid))
        payload = {
            "schema": "avc.lock-owner/1",
            "token": token,
            "pid": pid,
            "pid_start": state.pid_start,
            "host": socket.gethostname(),
            "job": str(job),
            "started_utc": _utc(),
            "heartbeat_utc": _utc(),
            "heartbeat_interval_s": interval,
            "stale_after_s": STALE_AFTER_S,
            "toolkit_version": __version__,
            "ownership": "kernel lock; this file is advisory only",
        }
        _write_sidecar(p, payload)
        _states[key] = state
        if heartbeat:
            t = threading.Thread(target=_heartbeat_loop, args=(state, payload), name="avc-lock-heartbeat", daemon=True)
            state.hb_thread = t
            t.start()
        try:
            append_line(runs_path(p), json.dumps({"event": "acquire", "token": token, "pid": pid, "job": str(job), "utc": _utc(), "waited_s": round(waited, 3)}, ensure_ascii=False))
        except OSError:
            pass
        return Lease(state)
    except BaseException:
        _states.pop(key, None)
        try:
            _kernel_unlock(fd)
        finally:
            os.close(fd)
        raise


# --------------------------------------------------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------------------------------------------------


@dataclass
class LockStatus:
    state: str  # "free" | "held" | "uncertain"
    held_by_this_process: bool = False
    owner: dict[str, Any] | None = None  # advisory sidecar content
    heartbeat_age_s: float | None = None
    advisory_stale: bool | None = None
    owner_pid_alive: bool | None = None
    owner_pid_identity_ok: bool | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in ("state", "held_by_this_process", "owner", "heartbeat_age_s", "advisory_stale", "owner_pid_alive", "owner_pid_identity_ok", "note")}


def status(path: str | os.PathLike[str], *, now: _dt.datetime | None = None) -> LockStatus:
    """Report the lock state. Kernel truth first (momentary non-blocking probe), sidecar facts labelled advisory.

    The probe holds the lock for microseconds when it is free; a contender polling at that instant simply retries.
    """
    p = os.path.abspath(os.fspath(path))
    if not os.path.isdir(os.path.dirname(fs_path(p))):
        return LockStatus("free", note="free (the lock folder does not exist yet: this lock has never been used)")
    owner = _read_sidecar(p)
    mine = _key(p) in _states
    if mine:
        s = _states[_key(p)]
        return LockStatus("held", True, owner, 0.0, False, True, True, f"held by this process for job {s.job!r}")
    try:
        outcome, fd = _try_lock_path(p)
    except LockUncertain as exc:
        return LockStatus("uncertain", False, owner, note=str(exc))
    if outcome == "acquired":
        assert fd is not None
        try:
            _kernel_unlock(fd)
        finally:
            os.close(fd)
        note = "free"
        if owner and "pid" in owner:
            note = "free (a previous owner left advisory metadata; it is stale, the kernel says nobody holds the lock)"
        return LockStatus("free", False, owner, note=note)
    # held by someone else
    age = None
    stale = None
    alive = None
    ident = None
    if isinstance(owner, dict) and "untrusted" not in owner:
        hb = owner.get("heartbeat_utc")
        try:
            t = _dt.datetime.fromisoformat(str(hb))
            if t.tzinfo is not None:
                age = ((now or _dt.datetime.now(_dt.timezone.utc)) - t).total_seconds()
                stale = age > STALE_AFTER_S
        except ValueError:
            pass
        pid = owner.get("pid")
        if isinstance(pid, int) and not isinstance(pid, bool):
            alive = pid_alive(pid)
            recorded = owner.get("pid_start")
            current = process_start_time(pid) if alive else None
            ident = (recorded == current) if (recorded and current) else None
    note = "held (kernel lock). Sidecar data below is advisory; do NOT remove the lock file or kill the recorded PID."
    if stale:
        note += f" The heartbeat is older than {STALE_AFTER_S:g} s (advisory-stale): the holder may be hung; ask its owner."
    return LockStatus("held", False, owner, age, stale, alive, ident, note)


# --------------------------------------------------------------------------------------------------------------------
# run a command under the lock
# --------------------------------------------------------------------------------------------------------------------


def run_under_lock(
    cmd: list[str],
    *,
    lock_path: str | os.PathLike[str],
    job: str,
    wait_timeout: float = 0.0,
    run_timeout: float | None = None,
    cwd: str | os.PathLike[str] | None = None,
    env: dict[str, str] | None = None,
    log_path: str | os.PathLike[str] | None = None,
) -> RunResult:
    """Hold the lease for the child's WHOLE lifetime; kill the child's tree on ``run_timeout`` (reported as ``timed_out``)."""
    with acquire(lock_path, job=job, timeout=wait_timeout):
        return run(cmd, timeout=run_timeout, cwd=cwd, env=env, log_path=log_path)


# --------------------------------------------------------------------------------------------------------------------
# CLI (used by `python -m core lock`)
# --------------------------------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    from .config import load_config

    ap = argparse.ArgumentParser(prog="python -m core lock", description="Heavy-job lock: kernel-lock ownership, advisory sidecar, no automatic takeover.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("status", help="show lock state (usage: python -m core lock status [--path LOCKFILE])")
    st.add_argument("--path")
    st.add_argument("--json", action="store_true")
    rn = sub.add_parser("run", help="run COMMAND under the lock (usage: python -m core lock run --job NAME -- COMMAND ...)")
    rn.add_argument("--path")
    rn.add_argument("--job", required=True)
    rn.add_argument("--wait", type=float, default=0.0, help="seconds to wait for the lock (default: try once)")
    rn.add_argument("--timeout", type=float, default=None, help="seconds the command may run before its process tree is killed")
    rn.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args(argv)
    path = args.path or str(load_config().lock_path)
    if args.cmd == "status":
        s = status(path)
        print(json.dumps({"path": path, **s.to_dict()}, ensure_ascii=False, indent=2))
        return 0 if s.state == "free" else (EXIT_BUSY if s.state == "held" else 3)
    cmd = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not cmd:
        ap.error("no command given after --")
    try:
        r = run_under_lock(cmd, lock_path=path, job=args.job, wait_timeout=args.wait, run_timeout=args.timeout)
    except LockBusy as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_BUSY
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.timed_out:
        print(f"timed out after {args.timeout:g}s; process tree killed", file=sys.stderr)
        return 2
    return int(r.returncode or 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

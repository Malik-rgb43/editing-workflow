"""Cross-platform process control: no ``shell=True``, no ``tasklist``, UTF-8 everywhere, whole-tree termination.

* ``run`` - run a command given as an argument LIST, capture UTF-8 output, enforce a timeout, and on timeout kill the
  entire process tree (not just the direct child).  A timeout is reported as ``timed_out=True`` - callers map it to
  ``INSUFFICIENT_EVIDENCE``, never to a pass.
* ``ManagedProcess`` / ``spawn`` - a child that lives in a Windows *Job Object* (kill-on-close) or a POSIX new session /
  process group, so ``terminate_tree`` and "the launcher crashed" both take every descendant down with them.
* ``pid_alive`` / ``process_start_time`` - liveness plus a start-time stamp (PIDs are reused; pid+start-time is identity).

Windows tree control uses ``ctypes`` + Job Objects (no ``taskkill``, no ``tasklist``, no psutil).  POSIX uses
``start_new_session`` + ``os.killpg``.  Only the toolkit's own children are ever signalled (src: blueprint TOOLS_SPEC
section 1.7 and section 3.2 "kill only the owned process tree").

Usage:
    python -c "from core.procs import run; print(run(['python','-c','print(1)']).stdout)"
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import IO, Any, Mapping, Sequence

from .errors import ProcessError

__all__ = ["RunResult", "ManagedProcess", "spawn", "run", "utf8_env", "pid_alive", "process_start_time", "terminate_tree_of"]

_IS_WIN = os.name == "nt"


def utf8_env(base: Mapping[str, str] | None = None, extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """Environment for children: UTF-8 stdio for Python tools, no interactive prompts, caller extras applied last."""
    env = dict(os.environ if base is None else base)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    if extra:
        env.update(extra)
    return env


def _check_cmd(cmd: Sequence[str | os.PathLike[str]]) -> list[str]:
    if isinstance(cmd, (str, bytes)):
        raise ProcessError(
            "commands must be an argument list, not a string",
            remediation="pass ['ffmpeg', '-i', path, ...]; shell invocation and string commands are not supported (quoting hazards with Hebrew/space/apostrophe paths)",
        )
    out = [os.fspath(c) for c in cmd]
    if not out or not all(isinstance(c, str) for c in out):
        raise ProcessError("empty or non-string command argument")
    if any("\x00" in c for c in out):
        raise ProcessError("NUL character in command argument")
    return out


# --------------------------------------------------------------------------------------------------------------------
# Windows job objects (ctypes, loaded lazily)
# --------------------------------------------------------------------------------------------------------------------

if _IS_WIN:
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _ntdll = ctypes.WinDLL("ntdll")
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.AssignProcessToJobObject.restype = wintypes.BOOL
    _k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.TerminateJobObject.restype = wintypes.BOOL
    _k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    _k32.SetInformationJobObject.restype = wintypes.BOOL
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    _k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    _ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]

    _PROCESS_TERMINATE = 0x0001
    _PROCESS_SET_QUOTA = 0x0100
    _PROCESS_SUSPEND_RESUME = 0x0800
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _SYNCHRONIZE = 0x00100000
    _STILL_ACTIVE = 259
    _CREATE_SUSPENDED = 0x00000004
    _CREATE_NEW_PROCESS_GROUP = 0x00000200
    _CREATE_NO_WINDOW = 0x08000000
    _JobObjectExtendedLimitInformation = 9
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000

    class _BASIC_LIMIT(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]

    class _EXT_LIMIT(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BASIC_LIMIT),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    def _make_kill_on_close_job() -> int:
        job = _k32.CreateJobObjectW(None, None)
        if not job:
            raise ProcessError(f"CreateJobObject failed (winerror {ctypes.get_last_error()})")
        info = _EXT_LIMIT()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not _k32.SetInformationJobObject(job, _JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)):
            err = ctypes.get_last_error()
            _k32.CloseHandle(job)
            raise ProcessError(f"SetInformationJobObject failed (winerror {err})")
        return job

    def _filetime_to_int(ft: Any) -> int:
        return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


def pid_alive(pid: int) -> bool:
    """True when a process with this PID currently exists (running; zombies/exited processes are not alive)."""
    if pid <= 0:
        return False
    if _IS_WIN:
        h = _k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return False
        try:
            code = wintypes.DWORD()
            if not _k32.GetExitCodeProcess(h, ctypes.byref(code)):
                return False
            return code.value == _STILL_ACTIVE
        finally:
            _k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    # a zombie still answers kill(0); treat state Z as dead where /proc tells us
    try:
        with open(f"/proc/{pid}/stat", "rb") as fh:
            data = fh.read().decode("utf-8", "replace")
        state = data.rsplit(")", 1)[1].split()[0]
        return state != "Z"
    except OSError:
        return True


def process_start_time(pid: int) -> str | None:
    """A stable, comparable string identifying *when* the process started (or ``None`` if unknown).

    ``pid`` + ``process_start_time`` is the process identity: a recycled PID has a different start time.
    """
    if pid <= 0:
        return None
    if _IS_WIN:
        h = _k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return None
        try:
            c, e, k, u = (wintypes.FILETIME() for _ in range(4))
            if not _k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
                return None
            return f"win:{_filetime_to_int(c)}"
        finally:
            _k32.CloseHandle(h)
    if sys.platform.startswith("linux"):
        try:
            with open(f"/proc/{pid}/stat", "rb") as fh:
                data = fh.read().decode("utf-8", "replace")
            return "linux:" + data.rsplit(")", 1)[1].split()[19]  # field 22 = starttime (clock ticks since boot)
        except (OSError, IndexError):
            return None
    try:  # macOS / BSD
        out = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"}, timeout=5)
        text = out.stdout.strip()
        return f"ps:{text}" if out.returncode == 0 and text else None
    except (OSError, subprocess.SubprocessError):
        return None


# --------------------------------------------------------------------------------------------------------------------
# managed process
# --------------------------------------------------------------------------------------------------------------------


class ManagedProcess:
    """A ``subprocess.Popen`` whose whole descendant tree can be terminated, and that dies with its launcher."""

    def __init__(self, popen: subprocess.Popen, job: int | None = None) -> None:
        self.popen = popen
        self._job = job

    @property
    def pid(self) -> int:
        return self.popen.pid

    def poll(self) -> int | None:
        return self.popen.poll()

    def wait(self, timeout: float | None = None) -> int:
        return self.popen.wait(timeout)

    def communicate(self, input: bytes | None = None, timeout: float | None = None) -> tuple[bytes | None, bytes | None]:
        return self.popen.communicate(input, timeout)

    def terminate_tree(self, grace: float = 3.0) -> None:
        """Ask politely (where the OS allows), then kill the process and every descendant. Idempotent."""
        if _IS_WIN:
            if self._job:
                _k32.TerminateJobObject(self._job, 1)
            else:  # pragma: no cover - only when job creation failed
                self.popen.kill()
        else:
            try:
                os.killpg(self.popen.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            deadline = time.monotonic() + grace
            while time.monotonic() < deadline and self.popen.poll() is None:
                time.sleep(0.05)
            try:
                os.killpg(self.popen.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        try:
            self.popen.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover
            pass

    def close(self) -> None:
        """Release the job handle. On Windows this ALSO kills any descendant still alive (kill-on-close)."""
        if _IS_WIN and self._job:
            _k32.CloseHandle(self._job)
            self._job = None

    def __enter__(self) -> "ManagedProcess":
        return self

    def __exit__(self, *exc: object) -> None:
        if self.popen.poll() is None:
            self.terminate_tree()
        self.close()


def spawn(
    cmd: Sequence[str | os.PathLike[str]],
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    stdin: int | IO[Any] | None = subprocess.DEVNULL,
    stdout: int | IO[Any] | None = subprocess.PIPE,
    stderr: int | IO[Any] | None = subprocess.PIPE,
    keep_alive_on_launcher_exit: bool = False,
) -> ManagedProcess:
    """Start ``cmd`` (argument list) inside a kill-on-close job object / new process group.

    ``keep_alive_on_launcher_exit=True`` skips the kill-on-close behaviour (use only for deliberately detached work).
    """
    args = _check_cmd(cmd)
    full_env = utf8_env(None, env)  # `env` entries are merged OVER os.environ (PATH etc. stay available)
    if _IS_WIN:
        job = None if keep_alive_on_launcher_exit else _make_kill_on_close_job()
        flags = _CREATE_NEW_PROCESS_GROUP | _CREATE_NO_WINDOW | (_CREATE_SUSPENDED if job else 0)
        popen = subprocess.Popen(args, cwd=cwd, env=full_env, stdin=stdin, stdout=stdout, stderr=stderr, creationflags=flags, close_fds=False)
        if job:
            h = _k32.OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE | _PROCESS_SUSPEND_RESUME, False, popen.pid)
            try:
                if not h or not _k32.AssignProcessToJobObject(job, h):
                    err = ctypes.get_last_error()
                    popen.kill()
                    _k32.CloseHandle(job)
                    raise ProcessError(f"could not place the child in a job object (winerror {err})")
                _ntdll.NtResumeProcess(h)
            finally:
                if h:
                    _k32.CloseHandle(h)
        return ManagedProcess(popen, job)
    popen = subprocess.Popen(args, cwd=cwd, env=full_env, stdin=stdin, stdout=stdout, stderr=stderr, start_new_session=True)
    return ManagedProcess(popen)


def terminate_tree_of(proc: ManagedProcess) -> None:
    proc.terminate_tree()


@dataclass
class RunResult:
    cmd: list[str]
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    duration_s: float = 0.0
    stdout_bytes: bytes = field(default=b"", repr=False)

    @property
    def ok(self) -> bool:
        """True only for a clean, in-time exit 0. A timed-out run is never ok."""
        return (not self.timed_out) and self.returncode == 0


def run(
    cmd: Sequence[str | os.PathLike[str]],
    *,
    timeout: float | None = None,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    input: bytes | str | None = None,
    log_path: str | os.PathLike[str] | None = None,
    decode_stdout: bool = True,
) -> RunResult:
    """Run to completion, capture output as UTF-8 (undecodable bytes -> U+FFFD), kill the whole tree on timeout.

    ``decode_stdout=False`` keeps binary output only in ``stdout_bytes`` (``stdout`` stays empty).
    ``log_path`` additionally writes a UTF-8 log (command line, stdout, stderr, exit code) with ``\\n`` newlines.
    """
    args = _check_cmd(cmd)
    data = input.encode("utf-8") if isinstance(input, str) else input
    t0 = time.monotonic()
    proc = spawn(args, cwd=cwd, env=env, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL)
    timed_out = False
    try:
        try:
            out, err = proc.communicate(data, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.terminate_tree()
            out, err = proc.communicate()
        rc = proc.poll()
    finally:
        proc.close()
    out = out or b""
    err = err or b""
    result = RunResult(
        cmd=args,
        returncode=None if timed_out else rc,
        stdout=out.decode("utf-8", "replace") if decode_stdout else "",
        stderr=err.decode("utf-8", "replace"),
        timed_out=timed_out,
        duration_s=round(time.monotonic() - t0, 3),
        stdout_bytes=out,
    )
    if log_path is not None:
        from .fsio import write_text_atomic

        write_text_atomic(
            log_path,
            f"$ {' '.join(args)}\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}\n"
            f"--- exit {result.returncode}{' (TIMED OUT, tree killed)' if timed_out else ''} after {result.duration_s}s ---\n",
        )
    return result

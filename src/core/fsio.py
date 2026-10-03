"""Low-level, UTF-8-safe file helpers (no third-party imports).

* ``fs_path``     - Windows long-path (``\\\\?\\``) form of an absolute path, plain string elsewhere.
* ``read_text``   - strict UTF-8 (a leading BOM is tolerated and dropped).
* ``write_text_atomic`` / ``write_json_atomic`` / ``append_line`` - UTF-8 **without BOM**, ``\\n`` newlines,
  temp-file + ``os.replace`` so a crash never leaves a half-written manifest.

Why: a Windows console is not UTF-8 and project folders may contain Hebrew letters, spaces, apostrophes
and emoji; every text file the toolkit writes must round-trip byte-exact (src: blueprint REPO_ARCHITECTURE section 9;
CLAUDE rule "write files as UTF-8, no BOM").

Usage:
    python -c "from core.fsio import fs_path; print(fs_path('.'))"
"""

from __future__ import annotations

import json
import os
import secrets
import time
from typing import Any

__all__ = [
    "LONG_PATH_THRESHOLD",
    "fs_path",
    "read_text",
    "read_json",
    "write_text_atomic",
    "write_bytes_atomic",
    "write_json_atomic",
    "append_line",
]

#: Windows MAX_PATH is 260 including the terminating NUL and the drive prefix; directory creation is limited to 248.
#: Anything at or above this many characters is given the extended-length prefix.
LONG_PATH_THRESHOLD = 240

PathLike = str | os.PathLike[str]


def fs_path(path: PathLike, *, force: bool = False) -> str:
    """Return a string usable for filesystem calls, with the ``\\\\?\\`` prefix on Windows when the path is long.

    The input is made absolute and normalised first (``..`` removed) because the extended-length prefix disables
    Windows' own normalisation. On POSIX the absolute path is returned unchanged.
    """
    raw = os.fspath(path)
    if os.name != "nt":
        return os.path.abspath(raw)
    if raw.startswith("\\\\?\\"):
        return raw
    absolute = os.path.abspath(raw)
    if not force and len(absolute) < LONG_PATH_THRESHOLD:
        return absolute
    if absolute.startswith("\\\\"):  # UNC: \\server\share\x -> \\?\UNC\server\share\x
        return "\\\\?\\UNC\\" + absolute[2:]
    return "\\\\?\\" + absolute


def read_text(path: PathLike) -> str:
    """Read a UTF-8 text file strictly. A UTF-8 BOM is accepted (Windows editors add one) and dropped."""
    with open(fs_path(path), "r", encoding="utf-8-sig", newline="") as fh:
        return fh.read()


def read_json(path: PathLike) -> Any:
    return json.loads(read_text(path))


def _replace_with_retry(src: str, dst: str, attempts: int = 8) -> None:
    # On Windows a concurrent reader (antivirus, another tool) can briefly block os.replace with PermissionError.
    delay = 0.01
    for i in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if os.name != "nt" or i == attempts - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 0.2)


def write_bytes_atomic(path: PathLike, data: bytes, *, mkdir: bool = True) -> None:
    target = fs_path(path)
    parent = os.path.dirname(target)
    if mkdir:
        os.makedirs(parent, exist_ok=True)
    tmp = os.path.join(parent, f".{os.path.basename(target)}.tmp-{os.getpid()}-{secrets.token_hex(4)}")
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        _replace_with_retry(tmp, target)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def write_text_atomic(path: PathLike, text: str, *, mkdir: bool = True) -> None:
    """UTF-8, no BOM, ``\\n`` newlines (lone ``\\r\\n`` in ``text`` is normalised)."""
    data = text.replace("\r\n", "\n").encode("utf-8")
    write_bytes_atomic(path, data, mkdir=mkdir)


def write_json_atomic(path: PathLike, obj: Any, *, indent: int | None = 2, sort_keys: bool = False) -> None:
    """Pretty JSON with real Hebrew (``ensure_ascii=False``) and a trailing newline."""
    text = json.dumps(obj, ensure_ascii=False, indent=indent, sort_keys=sort_keys)
    write_text_atomic(path, text + "\n")


def _append_bytes_windows(target: str, data: bytes) -> None:
    """Atomic append on Windows.

    The CRT's ``O_APPEND`` is emulated (seek to end, then write) and loses lines when several processes append at once
    (measured: 153 of 160 lines survived 4 concurrent writers). A handle opened with ``FILE_APPEND_DATA`` only makes NTFS
    place every write at the end of file atomically.
    """
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    k32.WriteFile.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    k32.WriteFile.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    FILE_APPEND_DATA, SHARE_ALL, OPEN_ALWAYS, NORMAL = 0x0004, 0x7, 4, 0x80
    invalid = wintypes.HANDLE(-1).value
    handle = k32.CreateFileW(target, FILE_APPEND_DATA, SHARE_ALL, None, OPEN_ALWAYS, NORMAL, None)
    if handle in (None, invalid):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        written = wintypes.DWORD(0)
        if not k32.WriteFile(handle, data, len(data), ctypes.byref(written), None) or written.value != len(data):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        k32.CloseHandle(handle)


def append_line(path: PathLike, line: str) -> None:
    """Append ONE line (JSONL) with a single atomic write so concurrent appenders never interleave or overwrite each other."""
    if "\n" in line or "\r" in line:
        raise ValueError("append_line takes exactly one line without newline characters")
    target = fs_path(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    data = (line + "\n").encode("utf-8")
    if os.name == "nt":
        _append_bytes_windows(target, data)
        return
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    fd = os.open(target, flags, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)

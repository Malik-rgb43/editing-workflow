"""ingest - the warehouse's card import, raw-footage deletion, duplicate cleanup and Recycle Bin, kept apart from the page server.

Import: one copy, straight from the card (or any folder) into <project>/source/, each file hashed while it is copied and hashed again
from the disk afterwards (SHA-256 both ways); a file that does not match is copied once more, then reported. A file already in source/
with the same name, size and hash is skipped, so importing the same card twice is harmless. A log of every file (source path, size,
sha256) goes to <project>/review/imports/<utc>.json. Nothing on the card is ever written, moved or deleted.

Recycle Bin: SHFileOperationW with FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_WANTNUKEWARNING: an item Windows cannot recycle (too big
for the bin) makes Windows ask before a permanent delete instead of doing it silently. Stdlib only.
"""

from __future__ import annotations

import ctypes
import datetime as _dt
import hashlib
import json
import os
import shutil
import string
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

MEDIA_VIDEO = {".mp4", ".mov", ".m4v", ".mts", ".m2ts", ".mxf", ".avi", ".mkv", ".webm", ".insv", ".360", ".braw", ".r3d", ".crm"}
MEDIA_AUDIO = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".aif", ".aiff", ".bwf"}
MEDIA_PHOTO = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".dng", ".cr2", ".cr3", ".arw", ".nef", ".raf", ".orf", ".rw2", ".tif", ".tiff"}
MEDIA = MEDIA_VIDEO | MEDIA_AUDIO | MEDIA_PHOTO
SKIP_DIRS = {"system volume information", "$recycle.bin", ".trashes", ".spotlight-v100", ".fseventsd", "thumbnails", "misc", "avf_info"}
MAX_SCAN = 8000
MARGIN = 2 << 30  # keep 2 GB free after an import
CHUNK = 4 << 20
JOBS: dict[str, dict] = {}
JOB_LOCK = threading.Lock()
THUMB_SEM = threading.Semaphore(3)  # a card of 300 clips must not start 300 ffmpeg processes at once


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def kind_of(p: Path) -> str | None:
    e = p.suffix.lower()
    return "video" if e in MEDIA_VIDEO else "audio" if e in MEDIA_AUDIO else "photo" if e in MEDIA_PHOTO else None


# ----------------------------------------------------------------------------------------------------------------------- drives + scan

def drives() -> list[dict]:
    out = []
    if os.name != "nt":
        return out
    k32 = ctypes.windll.kernel32
    mask = k32.GetLogicalDrives()
    kinds = {2: "removable", 3: "fixed", 4: "network", 5: "cdrom", 6: "ram"}
    for i, letter in enumerate(string.ascii_uppercase):
        if not mask & (1 << i):
            continue
        root = f"{letter}:\\"
        t = kinds.get(k32.GetDriveTypeW(root), "other")
        if t == "cdrom":
            continue
        name = ctypes.create_unicode_buffer(261)
        ok = k32.GetVolumeInformationW(root, name, 261, None, None, None, None, 0)
        if not ok:  # an empty card reader slot
            continue
        try:
            du = shutil.disk_usage(root)
        except OSError:
            continue
        has_dcim = any((Path(root) / d).is_dir() for d in ("DCIM", "PRIVATE", "AVCHD", "CLIP", "M4ROOT"))
        out.append({"root": root, "label": name.value or "", "type": t, "camera": has_dcim, "total": du.total, "free": du.free})
    out.sort(key=lambda d: (not (d["type"] == "removable" or d["camera"]), d["root"]))
    return out


def scan(base: Path) -> dict:
    """Every media file under base (camera cards nest deeply). Hidden/system folders are skipped; at most MAX_SCAN files."""
    if not base.is_dir():
        raise ValueError(f"אין תיקייה בנתיב {base}")
    files, truncated = [], False
    for dp, dn, fn in os.walk(base):
        dn[:] = sorted(d for d in dn if d.lower() not in SKIP_DIRS and not d.startswith("."))
        for n in sorted(fn):
            p = Path(dp) / n
            k = kind_of(p)
            if not k or n.startswith("._"):
                continue
            try:
                s = p.stat()
            except OSError:
                continue
            files.append({"path": str(p), "rel": str(p.relative_to(base)), "name": n, "folder": str(Path(dp).relative_to(base)) or ".",
                          "size": s.st_size, "mtime": s.st_mtime, "kind": k})
            if len(files) >= MAX_SCAN:
                truncated = True
                break
        if truncated:
            break
    return {"base": str(base), "files": files, "truncated": truncated, "bytes": sum(f["size"] for f in files)}


def clip_thumb(src: Path, cache: Path) -> Path | None:
    k = kind_of(src)
    if not k or k == "audio" or not src.is_file():
        return None
    s = src.stat()
    key = hashlib.sha1(f"{src}|{s.st_size}|{s.st_mtime}".encode("utf-8")).hexdigest()[:20]
    out = cache / f"{key}.jpg"
    if out.exists():
        return out
    cache.mkdir(parents=True, exist_ok=True)
    with THUMB_SEM:
        return _make_thumb(src, k, out)


def _make_thumb(src: Path, k: str, out: Path) -> Path | None:
    if out.exists():
        return out
    args = ["ffmpeg", "-v", "error", "-y"] + (["-ss", "1"] if k == "video" else []) + ["-i", str(src), "-frames:v", "1",
            "-vf", "scale=240:-2", "-q:v", "6", str(out)]
    try:
        subprocess.run(args, capture_output=True, timeout=40, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if not out.exists() and k == "video":  # a clip shorter than 1 s
            args.pop(4); args.pop(4)
            subprocess.run(args, capture_output=True, timeout=40, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return None
    return out if out.exists() else None


def prune_cache(cache: Path, days: int = 14) -> None:
    if not cache.is_dir():
        return
    cut = time.time() - days * 86400
    for f in cache.glob("*.jpg"):
        try:
            if f.stat().st_mtime < cut:
                f.unlink()
        except OSError:
            pass


# ----------------------------------------------------------------------------------------------------------------------- hashing / copy

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def copy_verified(src: Path, dst: Path, progress) -> str:
    """Copy src -> dst.part while hashing, fsync, rename, re-read dst and compare. Returns the sha256; raises IOError on a mismatch."""
    part = dst.with_name(dst.name + ".part")
    h = hashlib.sha256()
    with open(src, "rb") as fi, open(part, "wb") as fo:
        while True:
            b = fi.read(CHUNK)
            if not b:
                break
            h.update(b)
            fo.write(b)
            progress(len(b))
        fo.flush()
        os.fsync(fo.fileno())
    shutil.copystat(src, part)
    os.replace(part, dst)
    a = h.hexdigest()
    b = sha256(dst)
    if a != b:
        raise IOError(f"hash mismatch on {dst.name}")
    return a


def unique_dest(folder: Path, name: str, taken: set) -> Path:
    p = folder / name
    stem, ext, k = Path(name).stem, Path(name).suffix, 2
    while p.exists() or str(p).lower() in taken:
        p = folder / f"{stem}_{k}{ext}"
        k += 1
    taken.add(str(p).lower())
    return p


def start_import(files: list[str], proj: Path, on_done=None, dest: Path | None = None) -> dict:
    with JOB_LOCK:
        if any(j["state"] == "running" for j in JOBS.values()):
            raise RuntimeError("כבר רצה קליטה אחרת. חכה שהיא תסתיים")
        srcs = []
        for f in files:
            p = Path(f)
            if not p.is_file() or not kind_of(p):
                raise ValueError(f"הקובץ לא נמצא או שאינו מדיה: {f}")
            srcs.append(p)
        if not srcs:
            raise ValueError("לא נבחרו קבצים")
        total = sum(p.stat().st_size for p in srcs)
        dest = dest or proj / "source"
        dest.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(dest).free
        if total + MARGIN > free:
            raise RuntimeError(f"אין מספיק מקום בדיסק: צריך {total / 2**30:.1f} GB ועוד 2 GB רזרבה, ויש {free / 2**30:.1f} GB פנויים")
        jid = uuid.uuid4().hex[:10]
        job = {"id": jid, "project": proj.name, "state": "running", "phase": "copy", "files_total": len(srcs), "files_done": 0,
               "skipped": 0, "bytes_total": total, "bytes_done": 0, "current": "", "errors": [], "started": time.time(), "finished": None,
               "log": None, "dest": str(dest)}
        JOBS[jid] = job
    threading.Thread(target=_run_import, args=(job, srcs, proj, on_done, dest), daemon=True).start()
    return job


def _run_import(job: dict, srcs: list[Path], proj: Path, on_done, dest: Path) -> None:
    existing: dict[tuple, Path] = {}
    for f in dest.rglob("*"):
        if f.is_file():
            existing[(f.name.lower(), f.stat().st_size)] = f
    taken: set = set()
    log = []

    def prog(n):
        job["bytes_done"] += n

    for src in srcs:
        job["current"] = src.name
        size = src.stat().st_size
        try:
            twin = existing.get((src.name.lower(), size))
            if twin is not None:
                job["phase"] = "check"
                hs = sha256(src)
                if hs == sha256(twin):
                    job["skipped"] += 1
                    job["bytes_done"] += size
                    job["files_done"] += 1
                    log.append({"src": str(src), "dest": str(twin), "bytes": size, "sha256": hs, "result": "already-there"})
                    continue
            job["phase"] = "copy"
            dst = unique_dest(dest, src.name, taken)
            before = job["bytes_done"]
            try:
                h = copy_verified(src, dst, prog)
            except IOError:
                job["bytes_done"] = before
                h = copy_verified(src, dst, prog)  # one retry; a second mismatch is reported below
            job["files_done"] += 1
            log.append({"src": str(src), "dest": str(dst), "bytes": size, "sha256": h, "result": "copied+verified"})
        except (OSError, IOError) as e:
            job["errors"].append({"file": str(src), "error": str(e)[:300]})
            job["files_done"] += 1
            for leftover in dest.glob(src.name + ".part"):
                try:
                    leftover.unlink()
                except OSError:
                    pass
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lp = proj / "review" / "imports" / f"{stamp}.json"
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(json.dumps({"schema": "avc.warehouse-import/1", "utc": now(), "files": log, "errors": job["errors"]},
                             ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    job["log"] = lp.relative_to(proj).as_posix()
    job["current"] = ""
    job["finished"] = time.time()
    job["state"] = "done" if not job["errors"] else "done-with-errors"
    if on_done:
        try:
            on_done(job, log)
        except Exception:  # never let a bookkeeping error hide the copy result
            pass


# ----------------------------------------------------------------------------------------------------------------------- recycle bin

class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("wFunc", ctypes.c_uint), ("pFrom", ctypes.c_wchar_p), ("pTo", ctypes.c_wchar_p),
                ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", ctypes.c_int), ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", ctypes.c_wchar_p)]


def to_recycle_bin(path: Path) -> None:
    """Move a file or folder to the Windows Recycle Bin. If Windows cannot recycle it, Windows itself asks before deleting it for good.
    Raises OSError when the item is still there afterwards (refused, cancelled, in use)."""
    if os.name != "nt":
        raise OSError("סל המיחזור קיים רק ב-Windows")
    p = str(Path(path).resolve())
    if not os.path.exists(p):
        raise OSError("הקובץ כבר לא שם")
    FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_WANTNUKEWARNING = 3, 0x4, 0x10, 0x40, 0x4000
    op = _SHFILEOPSTRUCTW(None, FO_DELETE, p + "\0", None, FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_WANTNUKEWARNING | FOF_SILENT, 0, None, None)
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if rc != 0 or op.fAnyOperationsAborted or os.path.exists(p):
        raise OSError("Windows לא העביר לסל המיחזור (בוטל, או שקובץ פתוח בתוכנה אחרת)" + (f" [קוד {rc}]" if rc else ""))


# ----------------------------------------------------------------------------------------------------------------------- duplicates

def find_duplicates(incoming: Path, projects: list[Path]) -> dict:
    """Files under incoming/ whose exact content (size + sha256) is already in some project's source/. Read-only."""
    by_size: dict[int, list[Path]] = {}
    for proj in projects:
        for f in (proj / "source").rglob("*"):
            if f.is_file():
                by_size.setdefault(f.stat().st_size, []).append(f)
    dups, cache = [], {}

    def hs(p):
        if p not in cache:
            cache[p] = sha256(p)
        return cache[p]

    if incoming.is_dir():
        for f in incoming.rglob("*"):
            if not f.is_file():
                continue
            cands = by_size.get(f.stat().st_size)
            if not cands:
                continue
            h = hs(f)
            twin = next((c for c in cands if hs(c) == h), None)
            if twin:
                dups.append({"path": str(f), "rel": f.relative_to(incoming).as_posix(), "bytes": f.stat().st_size, "sha256": h,
                             "copy_in": str(twin)})
    return {"files": dups, "bytes": sum(d["bytes"] for d in dups)}


def clean_duplicates(incoming: Path, items: list[dict]) -> dict:
    """Delete incoming/ files that are verified copies; each pair is hashed again right before its delete. Empty folders go too."""
    freed, done, kept = 0, 0, []
    root = incoming.resolve()
    for it in items:
        f, twin = Path(it["path"]).resolve(), Path(it["copy_in"])
        if not f.is_relative_to(root) or not f.is_file() or not twin.is_file():
            kept.append(it.get("rel", str(f)))
            continue
        if f.stat().st_size != twin.stat().st_size or sha256(f) != sha256(twin):
            kept.append(it.get("rel", str(f)))
            continue
        n = f.stat().st_size
        f.unlink()
        freed += n
        done += 1
    for dp, _dn, _fn in sorted(os.walk(root), key=lambda x: -len(x[0])):
        if Path(dp) != root and not any(Path(dp).iterdir()):
            try:
                Path(dp).rmdir()
            except OSError:
                pass
    return {"freed": freed, "files": done, "kept": kept}


def self_check() -> bool:
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        card = t / "card" / "DCIM" / "100CAM"
        card.mkdir(parents=True)
        (card / "C0001.MP4").write_bytes(os.urandom(300_000))
        (card / "C0001.XML").write_text("x")
        (card / "A001.WAV").write_bytes(os.urandom(1000))
        proj = t / "p"
        (proj / "source").mkdir(parents=True)
        s = scan(t / "card")
        ok &= len(s["files"]) == 2
        job = start_import([f["path"] for f in s["files"]], proj)
        while job["state"] == "running":
            time.sleep(0.05)
        ok &= job["state"] == "done" and (proj / "source" / "C0001.MP4").read_bytes() == (card / "C0001.MP4").read_bytes()
        job2 = start_import([f["path"] for f in s["files"]], proj)
        while job2["state"] == "running":
            time.sleep(0.05)
        ok &= job2["skipped"] == 2 and len(list((proj / "source").iterdir())) == 2
        inc = t / "incoming" / "x"
        inc.mkdir(parents=True)
        shutil.copy2(card / "C0001.MP4", inc / "copy.mp4")
        (inc / "other.mp4").write_bytes(b"different")
        d = find_duplicates(t / "incoming", [proj])
        ok &= len(d["files"]) == 1
        r = clean_duplicates(t / "incoming", d["files"])
        ok &= r["files"] == 1 and (inc / "other.mp4").exists()
    print(("ok   " if ok else "FAIL ") + "ingest: scan, verified import, idempotent re-import, duplicate cleanup")
    return ok


if __name__ == "__main__":
    sys.exit(0 if self_check() else 1)

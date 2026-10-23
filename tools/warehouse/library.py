"""library - the user's own folders (`library_root` in config.json; empty = not connected) inside the warehouse, read live, nothing synced or copied.

Layout the library uses: <client>\\[<month>\\]גלם (raw), <client>\\מוכנים (finished videos), <client>\\שמירות (Premiere saves).
* Every video under a folder whose name starts with "מוכנים" is a finished video on the page. The folders are read on every page
  load (a full read of the library takes well under a second), so a folder made by hand in Explorer shows up on the next refresh.
* Old work is read-only: nothing in the user's folders is written, moved or renamed. Notes on such a video live in the warehouse:
  <warehouse>\\_library\\<id>\\ (id = hash of the path relative to the library root; a renamed file starts a fresh note history).
* Editing projects stay in the ASCII work folder (the editing tools break on Hebrew paths). A new import writes the raw ONCE into
  <client>\\<month>\\גלם\\ and hard-links each file into the project's source\\ (one file on the disk with two names: no extra space);
  a delivered final in the project's final\\ is hard-linked into <client>\\מוכנים\\ the same way.
* Premiere preview caches ("Adobe Premiere Pro Audio/Video Previews") can be cleared: Premiere rebuilds them. Auto-Save is never touched.
Stdlib only.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = Path(os.environ.get("AVC_WAREHOUSE_STATE") or HERE)  # config, token, caches: outside the code folder when the toolkit updates itself
CONFIG = STATE / "config.json"
DEFAULTS = {"library_root": "", "hidden": []}
VIDEO = {".mp4", ".mov", ".m4v", ".mxf", ".mts", ".m2ts", ".mkv", ".webm", ".avi"}
SKIP_PREFIX = ("adobe premiere pro", "premiere composer files", "$recycle")
READY = "מוכנים"
RAW = "גלם"
CACHE_NAMES = ("adobe premiere pro audio previews", "adobe premiere pro video previews")
MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]


def config() -> dict:
    c = dict(DEFAULTS)
    try:
        c.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    if os.environ.get("AVC_WAREHOUSE_LIBRARY"):  # tests point the page at a scratch library
        c["library_root"] = os.environ["AVC_WAREHOUSE_LIBRARY"]
    return c


def save_config(c: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def root() -> Path | None:
    raw = str(config().get("library_root") or "").strip()
    if not raw:
        return None
    r = Path(raw)
    return r if r.is_dir() else None


def month_name(d: _dt.date | None = None) -> str:
    d = d or _dt.date.today()
    return f"{MONTHS[d.month - 1]} {d.year % 100:02d}"


def item_id(rel: str) -> str:
    return "lib-" + hashlib.sha1(rel.lower().encode("utf-8")).hexdigest()[:14]


def file_key(p: Path) -> tuple | None:
    try:
        s = p.stat()
        return (s.st_dev, s.st_ino) if s.st_ino else None
    except OSError:
        return None


def scan(linked: set) -> dict:
    """Clients and finished videos of the library. `linked` = file keys of warehouse projects' files: those videos are already shown
    by their project card, so they are left out here."""
    r = root()
    if not r:
        return {"root": config()["library_root"], "ok": False, "clients": [], "items": []}
    hidden = {h.lower() for h in config()["hidden"]}
    clients, items = [], []
    for cdir in sorted((d for d in r.iterdir() if d.is_dir()), key=lambda d: d.name):
        if cdir.name.lower() in hidden or cdir.name.startswith("."):
            continue
        raw_bytes = ready_n = total = 0
        for dp, dn, fn in os.walk(cdir):
            dn[:] = [d for d in dn if not d.lower().startswith(SKIP_PREFIX)]
            parts = Path(dp).relative_to(cdir).parts
            in_ready = any(p.startswith(READY) for p in parts)
            in_raw = any(p.startswith(RAW) for p in parts)
            for n in fn:
                f = Path(dp) / n
                try:
                    st = f.stat()
                except OSError:
                    continue
                total += st.st_size
                if in_raw:
                    raw_bytes += st.st_size
                if in_ready and f.suffix.lower() in VIDEO:
                    if st.st_ino and (st.st_dev, st.st_ino) in linked:
                        continue
                    rel = f.relative_to(r).as_posix()
                    ready_n += 1
                    items.append({"id": item_id(rel), "rel": rel, "path": str(f), "client": cdir.name, "title": f.stem,
                                  "folder": "/".join(parts), "bytes": st.st_size,
                                  "mtime": _dt.datetime.fromtimestamp(st.st_mtime, _dt.timezone.utc).isoformat(timespec="seconds")})
        clients.append({"name": cdir.name, "path": str(cdir), "bytes": total, "raw_bytes": raw_bytes, "ready": ready_n})
    return {"root": str(r), "ok": True, "clients": clients, "items": items}


def find_item(item: str, linked: set) -> dict | None:
    return next((x for x in scan(linked)["items"] if x["id"] == item), None)


def ensure_virtual(item: dict) -> Path:
    """The warehouse-side folder of one library video: project.json pointing at the file, plus review/ (notes, thumbs). Never in the
    user's folders."""
    d = STATE / "_library" / item["id"]
    pj = d / "project.json"
    if not pj.exists():
        d.mkdir(parents=True, exist_ok=True)
        pj.write_text(json.dumps({"schema": "avc.project/1", "slug": item["id"], "title": item["title"], "library_file": item["path"],
                                  "library_rel": item["rel"], "client": item["client"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:  # the same relative path: keep the absolute path current
        try:
            j = json.loads(pj.read_text(encoding="utf-8"))
            if j.get("library_file") != item["path"]:
                j["library_file"] = item["path"]
                pj.write_text(json.dumps(j, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except (OSError, ValueError):
            pass
    return d


def library_file(proj: Path) -> Path | None:
    try:
        j = json.loads((proj / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    f = j.get("library_file")
    return Path(f) if f else None


# ----------------------------------------------------------------------------------------------------------------------- links

def link_or_copy(src: Path, dst: Path) -> str:
    """Hard link dst -> src's data (same disk, no extra space). Falls back to nothing: a link that cannot be made is reported, never
    silently turned into a second copy."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if file_key(dst) == file_key(src):
            return "already-linked"
        raise FileExistsError(f"כבר קיים קובץ אחר בשם {dst.name}")
    os.link(src, dst)
    return "linked"


def unique(folder: Path, name: str) -> Path:
    p, k = folder / name, 2
    while p.exists():
        p = folder / f"{Path(name).stem}_{k}{Path(name).suffix}"
        k += 1
    return p


def publish_finals(proj: Path, st: dict) -> list[str]:
    """Every final/*.mp4 of a project made from an import is hard-linked into <client>\\מוכנים\\ once (named after the project title).
    Returns the new library paths. Idempotent (the state remembers what was published)."""
    lib = st.get("library")
    if not lib or not lib.get("client_dir"):
        return []
    cdir = Path(lib["client_dir"])
    if not cdir.is_dir():
        return []
    done = lib.setdefault("published", {})
    out = []
    for f in sorted((proj / "final").glob("*")):
        if f.suffix.lower() not in VIDEO or f.name in done:
            continue
        ready = cdir / READY
        stem = (st.get("title") or proj.name).replace("/", "-").replace("\\", "-").strip()
        tail = f.stem.rsplit("_", 1)[-1] if "_v" in f.stem else ""
        dst = unique(ready, f"{stem}{(' ' + tail) if tail else ''}{f.suffix}")
        try:
            link_or_copy(f, dst)
            done[f.name] = str(dst)
            out.append(str(dst))
        except OSError:
            pass
    return out


# ----------------------------------------------------------------------------------------------------------------------- premiere cache

def premiere_running() -> bool:
    if os.name != "nt":
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Adobe Premiere Pro.exe", "/NH"], capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        return "Adobe Premiere Pro.exe" in out
    except (OSError, subprocess.SubprocessError):
        return False


def premiere_caches() -> dict:
    r = root()
    found = []
    if r:
        for dp, dn, _fn in os.walk(r):
            depth = len(Path(dp).relative_to(r).parts)
            keep = []
            for d in dn:
                if d.lower() in CACHE_NAMES:
                    p = Path(dp) / d
                    size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                    if size:
                        found.append({"path": str(p), "rel": p.relative_to(r).as_posix(), "bytes": size})
                elif not d.lower().startswith(SKIP_PREFIX) and depth < 4:
                    keep.append(d)
            dn[:] = keep
    found.sort(key=lambda x: -x["bytes"])
    return {"folders": found, "bytes": sum(x["bytes"] for x in found), "premiere_running": premiere_running()}


def clear_premiere_caches() -> dict:
    """Delete the files inside the preview-cache folders (the folders themselves stay, Premiere expects them). Refuses while Premiere runs."""
    if premiere_running():
        raise RuntimeError("פרימייר פתוח. סגור אותו ונסה שוב")
    c = premiere_caches()
    freed = files = 0
    for x in c["folders"]:
        p = Path(x["path"])
        if p.name.lower() not in CACHE_NAMES:
            continue
        for f in p.rglob("*"):
            if f.is_file():
                try:
                    n = f.stat().st_size
                    f.unlink()
                    freed += n
                    files += 1
                except OSError:
                    pass
    return {"freed": freed, "files": files}

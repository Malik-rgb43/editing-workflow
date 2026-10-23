#!/usr/bin/env python3
"""warehouse - "מחסן העבודות": every client video in one local page, a frame-accurate review room, compaction and deletion.

The warehouse copies nothing. It reads the project folders that already exist (<root>/<slug>/project.json) and keeps its own small
state inside each project, in <project>/review/ (state.json, the rounds' notes, thumbnails, drawings). That folder is never touched by
compaction, so a client who comes back after two months finds every note, version and drawing where it was.

Usage:
  python warehouse.py serve [--root DIR] [--port 8765] [--open]      the warehouse page on http://127.0.0.1:8765/ (reuses a running one)
  python warehouse.py add PROJECT VIDEO [--label TEXT]               register a new version (a draft render) for review; prints its review url
  python warehouse.py wait PROJECT [--timeout 7200]                  the notes Claude has not read yet (at once if the user already sent
                                                                     them, else blocks until they press send or approve); prints
                                                                     the numbered notes (schema avc.review-notes/1, plus kind and drawing)
  python warehouse.py inbox                                          every project with notes Claude has not read yet (start of a session)
  python warehouse.py reply PROJECT NOTE_ID --text TEXT [--resolve]  Claude answers a note on the page ("תוקן: ..."), optionally resolves it
  python warehouse.py url PROJECT                                    the review url of a project
  python warehouse.py --self-check                                   pure tests, no server, no ffmpeg

PROJECT is a slug under --root or a path to a project folder. Exit: 0 ok, 2 refused (bad input), 3 timeout / tool error.
Stdlib only, Python 3.10+. Binds 127.0.0.1 only; POSTs need the page token and a local Origin; nothing is loaded from the internet.
"""

from __future__ import annotations

import datetime as _dt
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import ingest
import library

HERE = Path(__file__).resolve().parent
STATE = Path(os.environ.get("AVC_WAREHOUSE_STATE") or HERE)  # token, caches, library notes, config.json (the toolkit sets it outside its own folder)
UI_DIR = HERE / "ui"
DEFAULT_ROOT = HERE.parent / "projects"
DEFAULT_PORT = 8765
SCHEMA = "avc.warehouse/1"
VIDEO_EXT = {".mp4", ".m4v", ".mov", ".webm", ".mkv"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".exr"}
# compaction never deletes anything inside these _work sub-folders: generated (maybe paid) assets, music, voice, the brief, notes
PROTECTED_DIRS = {"gen", "generated", "intake", "music", "audio", "voice", "vo", "assets", "notes", "asr", "licenses", "refs", "reference"}
STATUSES = ["גלם חדש", "בעבודה", "ממתין לבדיקה", "בתיקונים", "אושר", "נמסר"]
TOOLKIT = Path(os.environ.get("AVC_TOOLKIT_ROOT") or Path.home() / ".avc" / "toolkit")
KINDS = {"fix", "like", "note"}
MAX_BODY = 12 << 20  # a drawing PNG of a 4K frame fits
LOCK = threading.RLock()
CTYPE = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm", ".mkv": "video/x-matroska",
         ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".json": "application/json; charset=utf-8"}


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def tc(t: float | None) -> str:
    """Seconds -> m:ss.cc, the form the player shows; None -> 'general' (same as notes_board)."""
    if t is None:
        return "general"
    cs = int(round(t * 100))
    m, rest = divmod(cs, 6000)
    return f"{m}:{rest // 100:02d}.{rest % 100:02d}"


def strip_times(t: float | None, end: float | None, duration: float | None) -> list[float]:
    """Frame-strip times per note, identical to notes_board (G2: +-1 s around a point, the range plus 0.5 s each side)."""
    if t is None:
        return []
    a, b = (t - 1.0, t + 1.0) if end is None else (t - 0.5, end + 0.5)
    a = max(0.0, a)
    if duration:
        b = min(duration, b)
    if b <= a:
        return [round(a, 3)]
    n = 9 if end is None else min(24, max(9, int((b - a) / 0.25) + 1))
    return [round(a + (b - a) * i / (n - 1), 3) for i in range(n)]


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


# ----------------------------------------------------------------------------------------------------------------------------- state

def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.part")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def guess_client(slug: str) -> str:
    return slug.split("-")[0] if "-" in slug else slug


def load_state(proj: Path) -> dict:
    p = proj / "review" / "state.json"
    for cand in (p, p.with_name("state.json.bak")):  # the backup is the previous save: a damaged file never loses the notes
        if cand.exists():
            try:
                st = json.loads(cand.read_text(encoding="utf-8"))
                if isinstance(st, dict) and st.get("schema") == SCHEMA:
                    st.setdefault("versions", [])
                    st.setdefault("notes", [])
                    st.setdefault("rounds", [])
                    return st
            except (OSError, ValueError):
                pass
    title, client, libf = proj.name, guess_client(proj.name), None
    pj = proj / "project.json"
    if pj.exists():
        try:
            j = json.loads(pj.read_text(encoding="utf-8"))
            title, client, libf = j.get("title") or title, j.get("client") or client, j.get("library_file")
        except (OSError, ValueError):
            pass
    # first sight of a project: date it by its newest file and call it delivered when a delivery manifest exists
    mt = [f.stat().st_mtime for d in (proj / "final", proj / "_work", proj / "hf") if d.is_dir() for f in d.iterdir() if f.is_file()]
    if libf and Path(libf).exists():
        mt.append(Path(libf).stat().st_mtime)
    seen = _dt.datetime.fromtimestamp(max(mt), _dt.timezone.utc).isoformat(timespec="seconds") if mt else now()
    status = "נמסר" if (proj / "final" / "manifest.json").exists() or libf else "בעבודה"
    return {"schema": SCHEMA, "slug": proj.name, "title": title, "client": client, "status": status,
            "created_utc": seen, "updated_utc": seen, "versions": [], "notes": [], "rounds": [], "next_note": 1}


def save_state(proj: Path, st: dict, touch: bool = True) -> None:
    if touch:
        st["updated_utc"] = now()
    cur = proj / "review" / "state.json"
    if cur.exists():
        try:
            shutil.copy2(cur, cur.with_name("state.json.bak"))
        except OSError:
            pass
    atomic_write(proj / "review" / "state.json", json.dumps(st, ensure_ascii=False, indent=2) + "\n")


def rel(proj: Path, f: Path) -> str:
    return f.resolve().relative_to(proj.resolve()).as_posix() if f.resolve().is_relative_to(proj.resolve()) else str(f.resolve())


def discover_videos(proj: Path) -> list[Path]:
    """Deliverables in final/ (oldest first) plus drafts in _work that are newer than every final file (a draft still in review).
    A library item (a finished video in the user's own folders) is its one file."""
    lf = library.library_file(proj)
    if lf is not None:
        return [lf] if lf.is_file() else []
    finals = sorted((f for f in (proj / "final").glob("*") if f.suffix.lower() in VIDEO_EXT and f.is_file()), key=lambda f: f.stat().st_mtime)
    newest = finals[-1].stat().st_mtime if finals else 0.0
    work = proj / "_work"
    drafts = []
    if work.is_dir():
        cands = [f for f in work.glob("*draft*") if f.suffix.lower() in VIDEO_EXT] + [f for f in (work / "drafts").glob("*") if f.suffix.lower() in VIDEO_EXT]
        drafts = sorted((f for f in cands if f.is_file() and f.stat().st_mtime > newest), key=lambda f: f.stat().st_mtime)
        drafts = drafts[-1:]  # only the newest pending draft: older drafts are steps, not versions
    return finals + drafts


def sync_versions(proj: Path, st: dict) -> bool:
    """Give every discovered video a stable version id (V1, V2 ... in time order); mark files that are gone. True when changed."""
    changed = False
    known = {v["file"]: v for v in st["versions"]}
    for f in discover_videos(proj):
        r = rel(proj, f)
        if r in known:
            continue
        size = f.stat().st_size
        twin = next((v for v in st["versions"] if v.get("bytes") == size and (proj / v["file"]).exists()), None)
        if twin:  # the same render under a second name (final/x.mp4 next to final/x_v2.mp4): one version, not two
            twin.setdefault("aliases", []).append(r)
            known[r] = twin
            changed = True
            continue
        v = {"id": f"V{len(st['versions']) + 1}", "file": r, "label": f.stem, "bytes": size,
             "added_utc": _dt.datetime.fromtimestamp(f.stat().st_mtime, _dt.timezone.utc).isoformat(timespec="seconds"),
             "draft": "_work" in Path(r).parts}
        st["versions"].append(v)
        known[r] = v
        changed = True
    for v in st["versions"]:
        gone = not (proj / v["file"]).exists() and not any((proj / a).exists() for a in v.get("aliases", []))
        if bool(v.get("missing")) != gone:
            v["missing"] = gone
            changed = True
    return changed


def version_path(proj: Path, v: dict) -> Path | None:
    for r in [v["file"]] + v.get("aliases", []):
        p = proj / r if not Path(r).is_absolute() else Path(r)
        if p.exists():
            return p
    return None


def probe(path: Path) -> dict:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,width,height",
                              "-show_entries", "format=duration", "-of", "json", str(path)], capture_output=True, text=True, timeout=30)
        d = json.loads(out.stdout or "{}")
        s = (d.get("streams") or [{}])[0]
        num, _, den = (s.get("r_frame_rate") or "30/1").partition("/")
        fps = float(num) / float(den or 1) if float(den or 1) else 30.0
        return {"fps": round(fps, 3) if fps > 0 else 30.0, "w": s.get("width"), "h": s.get("height"),
                "duration": float((d.get("format") or {}).get("duration") or 0) or None}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"fps": 30.0, "w": None, "h": None, "duration": None}


def ensure_probe(proj: Path, v: dict) -> bool:
    if v.get("fps") and v.get("duration"):
        return False
    p = version_path(proj, v)
    if not p:
        return False
    v.update(probe(p))
    return True


def dir_size(p: Path) -> int:
    total = 0
    for dp, _dn, fn in os.walk(p):
        for n in fn:
            try:
                total += os.path.getsize(os.path.join(dp, n))
            except OSError:
                pass
    return total


def compact_plan(proj: Path) -> list[Path]:
    """The files compaction deletes: video and image files inside _work, outside the protected sub-folders, except the newest and every
    approved version's file. Never audio, text or JSON."""
    work = proj / "_work"
    out = []
    if not work.is_dir():
        return out
    st = load_state(proj)
    live = [v for v in st["versions"] if not v.get("missing")]
    keep_versions = [v for v in live if v.get("approved_utc")] + live[-1:]  # the newest and every approved version stay playable
    keep = {(proj / r).resolve() for v in keep_versions for r in [v["file"]] + v.get("aliases", [])}
    for dp, dn, fn in os.walk(work):
        parts = {x.lower() for x in Path(dp).relative_to(work).parts}
        if parts & PROTECTED_DIRS:
            dn[:] = []
            continue
        dn[:] = [d for d in dn if d.lower() not in PROTECTED_DIRS]
        for n in fn:
            if Path(n).suffix.lower() in VIDEO_EXT | IMAGE_EXT and (Path(dp) / n).resolve() not in keep:
                out.append(Path(dp) / n)
    return out


def project_summary(proj: Path) -> dict:
    with LOCK:
        st = load_state(proj)
        changed = sync_versions(proj, st)
        for v in st["versions"]:
            changed |= ensure_probe(proj, v)
        if library.publish_finals(proj, st):
            changed = True
        if changed:
            save_state(proj, st, touch=False)
    plan = compact_plan(proj)
    reclaim = sum(f.stat().st_size for f in plan if f.exists())
    live = [v for v in st["versions"] if not v.get("missing")]
    latest = live[-1] if live else None
    sample = None
    if not latest and (proj / "source").is_dir():  # no edit yet: show a frame of the raw footage on the card
        sample = next((str(f) for f in sorted((proj / "source").rglob("*")) if f.suffix.lower() in ingest.MEDIA_VIDEO), None)
    return {"raw_sample": sample, "slug": proj.name, "title": st["title"], "client": st["client"], "status": st["status"], "updated_utc": st["updated_utc"],
            "versions": len(st["versions"]), "latest": latest and {k: latest.get(k) for k in ("id", "label", "w", "h", "duration", "draft")},
            "open_notes": sum(1 for n in st["notes"] if n.get("state") == "open"),
            "pending_notes": sum(1 for n in st["notes"] if n.get("state") == "pending"),
            "bytes": dir_size(proj), "raw_bytes": dir_size(proj / "source"), "reclaim": reclaim, "compacted_utc": st.get("compacted_utc"),
            "raw_deleted_utc": st.get("raw_deleted_utc"), "library": bool(st.get("library"))}


def linked_keys(root: Path) -> set:
    """File keys of every warehouse project's finals: their hard-linked names in the user's מוכנים are shown by the project card."""
    out = set()
    for p in find_projects(root):
        for f in (p / "final").glob("*"):
            k = library.file_key(f)
            if k:
                out.add(k)
    return out


def link_into_source(proj: Path, files: list[Path]) -> tuple[int, list[str]]:
    """Hard-link footage that already sits on this disk into the project's source/ (no copy, no extra space)."""
    n, errs = 0, []
    for f in files:
        try:
            dst = proj / "source" / f.name
            if dst.exists() and library.file_key(dst) == library.file_key(f):
                continue
            library.link_or_copy(f, library.unique(proj / "source", f.name) if dst.exists() else dst)
            n += 1
        except OSError as ex:
            errs.append(f"{f}: {ex}")
    return n, errs


def remember_library(proj: Path, raw_dir: Path, files: list[str], entry: dict) -> None:
    lr = library.root()
    with LOCK:
        st = load_state(proj)
        st.setdefault("imports", []).append(entry)
        libst = st.setdefault("library", {})
        libst["raw_dir"] = str(raw_dir)
        # the client folder = the first folder under the library root on the way to the raw
        if lr and raw_dir.resolve().is_relative_to(lr.resolve()):
            libst["client_dir"] = str(lr / raw_dir.resolve().relative_to(lr.resolve()).parts[0])
        libst["raw_files"] = sorted(set(libst.get("raw_files", [])) | set(files))
        save_state(proj, st)


def find_projects(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted((d for d in root.iterdir() if d.is_dir() and (d / "project.json").exists()), key=lambda d: d.name)


def words_for(proj: Path) -> Path | None:
    st = load_state(proj)
    if st.get("words") and (proj / st["words"]).exists():
        return proj / st["words"]
    for c in (proj / "hf" / "data" / "words.json", proj / "hf" / "words.json"):
        if c.exists():
            return c
    return None


def transcript(proj: Path) -> dict | None:
    p = words_for(proj)
    if not p:
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    words = [{"w": w.get("w", ""), "s": w.get("start"), "e": w.get("end")} for w in d.get("words", []) if isinstance(w, dict) and w.get("start") is not None]
    return {"language": d.get("language"), "source": rel(proj, p), "words": words}


# ----------------------------------------------------------------------------------------------------------------------------- notes

def clean_note(it: dict, duration: float | None) -> tuple[dict | None, str | None]:
    text = it.get("text")
    if not isinstance(text, str) or not text.strip():
        if not it.get("drawing"):
            return None, "empty text"
        text = ""
    if len(text) > 4000:
        return None, "text too long"
    t, end = it.get("t"), it.get("end")
    for v in (t, end):
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v < 0 or (duration and v > duration + 0.5)):
            return None, f"time {v!r} is not inside the video"
    if t is None and end is not None:
        return None, "an end without a start"
    if end is not None and end <= t:
        return None, "end is not after start"
    kind = it.get("kind") if it.get("kind") in KINDS else "fix"
    drawing = it.get("drawing")
    if drawing is not None and (not isinstance(drawing, list) or len(json.dumps(drawing)) > 200_000):
        return None, "drawing is not valid"
    return {"t": None if t is None else round(float(t), 3), "end": None if end is None else round(float(end), 3), "text": text.strip(),
            "kind": kind, "drawing": drawing or None}, None


def note_line(x: dict) -> str:
    mark = {"fix": "לתקן", "like": "אהבתי", "note": "הערה"}[x.get("kind", "fix")]
    span = tc(x["t"]) if x.get("end") is None else f"{tc(x['t'])}-{tc(x['end'])}"
    extra = " [+ציור: " + x["png"] + "]" if x.get("png") else (" [+ציור]" if x.get("drawing") else "")
    return f'{x["n"]}. ({mark}) "{x["text"] or "(ציור בלבד)"}" @ {span}{extra}'


def send_round(proj: Path, st: dict, version_id: str, approved: bool) -> dict:
    """Pending notes on a version -> round N: write review/round-N/notes.json + notes.md (avc.review-notes/1 compatible), move status."""
    v = next((x for x in st["versions"] if x["id"] == version_id), None)
    if not v:
        raise ValueError("unknown version")
    pend = [n for n in st["notes"] if n.get("state") == "pending" and n.get("version") == version_id]
    if approved and any(n.get("kind") == "fix" for n in pend):
        raise ValueError("יש הערות 'לתקן' פתוחות: שלח אותן כתיקונים, או מחק אותן ואז אשר")
    if not approved and not pend:
        raise ValueError("אין הערות לשליחה")
    rn = len(st["rounds"]) + 1
    pend.sort(key=lambda x: (x["t"] is None, x["t"] or 0.0))
    out = []
    for k, n in enumerate(pend, 1):
        n["state"] = "sent" if n.get("kind") == "like" else "open"
        n["round"] = rn
        n["sent_utc"] = now()
        x = {"n": k, "id": n["id"], "t": n["t"], "end": n["end"], "kind": n["kind"], "text": n["text"],
             "tc": tc(n["t"]) if n["end"] is None else f"{tc(n['t'])}-{tc(n['end'])}",
             "png": n.get("png"), "drawing": bool(n.get("drawing")), "strip_times": strip_times(n["t"], n["end"], v.get("duration"))}
        out.append(x)
    vp = version_path(proj, v)
    doc = {"schema": "avc.review-notes/1", "round": rn, "video": str(vp) if vp else v["file"], "version": version_id,
           "video_bytes": v.get("bytes"), "duration_s": v.get("duration"), "received_utc": now(), "approved": approved, "notes": out,
           "source": "warehouse"}
    d = proj / "review" / f"round-{rn}"
    atomic_write(d / "notes.json", json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    if approved:
        md = [f"## Round {rn} - {version_id} APPROVED in the warehouse ({doc['received_utc']})"] + ([""] + [note_line(x) for x in out] if out else [])
    else:
        md = [f"## Round {rn} - notes from the warehouse on {version_id} ({doc['received_utc']})", ""] + [note_line(x) for x in out]
    atomic_write(d / "notes.md", "\n".join(md) + "\n")
    st["rounds"].append({"n": rn, "version": version_id, "sent_utc": doc["received_utc"], "approved": approved, "count": len(out)})
    st["status"] = "אושר" if approved else "בתיקונים"
    if approved:
        v["approved_utc"] = doc["received_utc"]
    return doc


# ----------------------------------------------------------------------------------------------------------------------------- deletion

def to_recycle_bin(path: Path) -> None:
    ingest.to_recycle_bin(path)


def compact(proj: Path) -> dict:
    plan = compact_plan(proj)
    freed, failed = 0, []
    for f in plan:
        try:
            n = f.stat().st_size
            f.unlink()
            freed += n
        except OSError:
            failed.append(rel(proj, f))
    work = proj / "_work"
    for dp, _dn, _fn in sorted(os.walk(work), key=lambda x: -len(x[0])) if work.is_dir() else []:
        if Path(dp) != work and not any(Path(dp).iterdir()):
            try:
                Path(dp).rmdir()
            except OSError:
                pass
    with LOCK:
        st = load_state(proj)
        st["compacted_utc"] = now()
        sync_versions(proj, st)
        save_state(proj, st)
    return {"freed": freed, "freed_h": human(freed), "files": len(plan) - len(failed), "failed": failed}


# ----------------------------------------------------------------------------------------------------------------------------- thumbs

def thumb(proj: Path, st: dict, vid: str) -> Path | None:
    v = next((x for x in st["versions"] if x["id"] == vid), None)
    if not v:
        return None
    out = proj / "review" / "thumbs" / f"{vid}.jpg"
    if out.exists():
        return out
    src = version_path(proj, v)
    if not src:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    at = min(1.5, (v.get("duration") or 3) / 3)
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1", "-vf", "scale=360:-2",
                        "-q:v", "5", str(out)], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return out if out.exists() else None


# ----------------------------------------------------------------------------------------------------------------------------- server

SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{1,60}")


def create_project(root: Path, title: str, client: str, slug: str) -> Path:
    """A new project through the toolkit's own scaffold (same folders and templates as every other project), then the warehouse state."""
    if not SLUG_RE.fullmatch(slug):
        raise ValueError("שם התיקייה: אותיות באנגלית קטנות, ספרות ומקפים בלבד")
    if (root / slug).exists():
        raise ValueError(f"כבר יש פרויקט בשם {slug}")
    tool = TOOLKIT / "tools" / "new_project.py"
    if tool.exists():
        r = subprocess.run([sys.executable, str(tool), title, "--work-root", str(root.parent), "--slug", slug, "--json"], cwd=str(TOOLKIT),
                           capture_output=True, text=True, encoding="utf-8", timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0 or not (root / slug / "project.json").exists():
            raise RuntimeError("יצירת הפרויקט נכשלה: " + (r.stderr or r.stdout or "").strip()[-300:])
    else:  # no toolkit on this machine: the same folders by hand
        for d in ("source", "hf", "final", "_work"):
            (root / slug / d).mkdir(parents=True, exist_ok=True)
        (root / slug / "project.json").write_text(json.dumps({"schema": "avc.project/1", "slug": slug, "title": title, "created_utc": now(),
            "folders": {"source": "source", "hf": "hf", "final": "final", "work": "_work"}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    proj = root / slug
    with LOCK:
        st = load_state(proj)
        st.update({"title": title, "client": client, "status": "גלם חדש", "created_utc": now()})
        save_state(proj, st)
    return proj


def raw_info(root: Path, proj: Path) -> dict:
    src = proj / "source"
    files = [f for f in src.rglob("*") if f.is_file()] if src.is_dir() else []
    st = load_state(proj)
    return {"files": len(files), "bytes": sum(f.stat().st_size for f in files), "library_raw_dir": st.get("library", {}).get("raw_dir"),
            "kept": ["final", "hf (קוד העריכה ומדיה מעובדת)", "review (הערות וגרסאות)"]}


def make_handler(root: Path, token: str, port_ref: list):
    cache = STATE / "_cache" / "clips"
    ingest.prune_cache(cache)
    incoming = root.parent / "incoming"

    def proj_of(slug: str) -> Path:
        slug = urllib.parse.unquote(slug)
        if not re.fullmatch(r"[^/\\:*?\"<>|]+", slug) or slug in (".", ".."):
            raise KeyError(slug)
        if slug.startswith("lib-"):  # a finished video in the user's folders; its notes live in the warehouse, never next to the file
            v = STATE / "_library" / slug
            if (v / "project.json").exists():
                return v
            item = library.find_item(slug, linked_keys(root))
            if not item:
                raise KeyError(slug)
            return library.ensure_virtual(item)
        p = root / slug
        if not (p / "project.json").exists():
            raise KeyError(slug)
        return p

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "warehouse/1"

        def log_message(self, *a):
            pass

        def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, code: int, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _file(self, path: Path, download_name: str | None = None):
            size = path.stat().st_size
            ctype = CTYPE.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            start, end, partial = 0, size - 1, False
            m = re.match(r"bytes=(\d*)-(\d*)$", self.headers.get("Range") or "")
            if m and size:
                a, b = m.groups()
                if a:
                    start, end = int(a), min(int(b), size - 1) if b else size - 1
                else:
                    start = max(0, size - int(b or 0))
                if start > end or start >= size:
                    self._send(416, b"", "text/plain", {"Content-Range": f"bytes */{size}"})
                    return
                partial = True
            n = end - start + 1
            self.send_response(206 if partial else 200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(n))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-cache")
            if partial:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            if download_name:
                q = urllib.parse.quote(download_name)
                self.send_header("Content-Disposition", f"attachment; filename=\"download{path.suffix}\"; filename*=UTF-8''{q}")
            self.end_headers()
            if self.command == "HEAD":
                return
            try:
                with open(path, "rb") as f:
                    f.seek(start)
                    while n > 0:
                        chunk = f.read(min(1 << 20, n))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        n -= len(chunk)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # seeking cancels range requests: normal

        def do_HEAD(self):
            self.do_GET()

        def host_ok(self) -> bool:
            """Only 127.0.0.1:<port> and localhost:<port> may address the page (a rebound DNS name would carry another Host)."""
            return (self.headers.get("Host") or "").lower() in (f"127.0.0.1:{port_ref[0]}", f"localhost:{port_ref[0]}")

        def do_GET(self):
            if not self.host_ok():
                return self._json(403, {"error": "forbidden host"})
            u = urllib.parse.urlparse(self.path)
            parts = [urllib.parse.unquote(x) for x in u.path.split("/") if x]
            try:
                if not parts or parts == ["index.html"]:
                    html = (UI_DIR / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", token)
                    return self._send(200, html.encode("utf-8"), CTYPE[".html"], {
                        "Content-Security-Policy": "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
                                                   "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"})
                if parts[0] == "ui" and len(parts) == 2 and re.fullmatch(r"[\w.-]+", parts[1]):
                    p = UI_DIR / parts[1]
                    return self._file(p) if p.exists() else self._json(404, {"error": "not found"})
                if parts == ["api", "ping"]:
                    return self._json(200, {"app": "warehouse", "root": str(root)})
                if parts == ["api", "library"]:
                    projs = [project_summary(p) for p in find_projects(root)]
                    disk = {"bytes": sum(p["bytes"] for p in projs), "reclaim": sum(p["reclaim"] for p in projs)}
                    try:
                        disk["free"] = shutil.disk_usage(root).free
                    except OSError:
                        pass
                    return self._json(200, {"root": str(root), "projects": projs, "disk": disk, "statuses": STATUSES,
                                            "library": library.scan(linked_keys(root))})
                if len(parts) >= 3 and parts[0] == "api" and parts[1] == "project":
                    proj = proj_of(parts[2])
                    if len(parts) == 3:
                        project_summary(proj)  # syncs versions and probes
                        st = load_state(proj)
                        lf = library.library_file(proj)
                        return self._json(200, {"state": st, "has_transcript": words_for(proj) is not None, "statuses": STATUSES,
                                                "library_file": str(lf) if lf else None, "folder": str(proj)})
                    if parts[3] == "transcript":
                        return self._json(200, transcript(proj) or {"words": []})
                    if parts[3] == "compact-preview":
                        plan = compact_plan(proj)
                        groups: dict[str, list] = {}
                        for f in plan:
                            r = Path(rel(proj, f)).parts
                            key = "/".join(r[:2]) if len(r) > 2 else r[0] + "/ (קבצים)"
                            g = groups.setdefault(key, [0, 0])
                            g[0] += 1
                            g[1] += f.stat().st_size
                        total = sum(g[1] for g in groups.values())
                        return self._json(200, {"total": total, "total_h": human(total), "groups": [
                            {"path": k, "files": g[0], "bytes": g[1], "h": human(g[1])} for k, g in sorted(groups.items(), key=lambda x: -x[1][1])],
                            "kept": sorted(PROTECTED_DIRS)})
                    if parts[3] == "rev":
                        st = load_state(proj)
                        return self._json(200, {"updated_utc": st["updated_utc"]})
                if len(parts) == 3 and parts[0] in ("media", "download", "thumb"):
                    proj = proj_of(parts[1])
                    st = load_state(proj)
                    vid = parts[2].removesuffix(".jpg")
                    if parts[0] == "thumb":
                        t = thumb(proj, st, vid)
                        return self._file(t) if t else self._json(404, {"error": "no thumbnail"})
                    v = next((x for x in st["versions"] if x["id"] == vid), None)
                    p = version_path(proj, v) if v else None
                    if not p:
                        return self._json(404, {"error": "the file of this version is gone"})
                    if parts[0] == "download":
                        return self._file(p, download_name=f"{st['title']}_{vid}{p.suffix}")
                    return self._file(p)
                if parts == ["clipthumb"]:
                    q = urllib.parse.parse_qs(u.query).get("path", [""])[0]
                    t = ingest.clip_thumb(Path(q), cache) if q else None
                    return self._file(t) if t else self._json(404, {"error": "no thumbnail"})
                if len(parts) == 3 and parts[:2] == ["api", "jobs"]:
                    j = ingest.JOBS.get(parts[2])
                    return self._json(200, j) if j else self._json(404, {"error": "no such job"})
                if len(parts) == 3 and parts[0] == "drawing":
                    proj = proj_of(parts[1])
                    p = proj / "review" / "drawings" / Path(parts[2]).name
                    return self._file(p) if p.exists() else self._json(404, {"error": "not found"})
                return self._json(404, {"error": "not found"})
            except KeyError:
                return self._json(404, {"error": "no such project"})

        def do_POST(self):
            p = port_ref[0]
            if not self.host_ok():
                self.close_connection = True
                return self._json(403, {"error": "forbidden host"})
            try:
                ln = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                ln = -1
            if ln < 0 or ln > MAX_BODY:
                self.close_connection = True  # the unread body would poison the next request on this keep-alive connection
                return self._json(413, {"error": "body too large"})
            raw = self.rfile.read(ln) if ln else b""  # always drain the body before any answer
            origin = self.headers.get("Origin")
            if self.headers.get("X-Token") != token or (origin and origin not in (f"http://127.0.0.1:{p}", f"http://localhost:{p}")):
                return self._json(403, {"error": "forbidden"})
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except (UnicodeDecodeError, ValueError):
                return self._json(400, {"error": "not JSON"})
            parts = [urllib.parse.unquote(x) for x in urllib.parse.urlparse(self.path).path.split("/") if x]
            try:
                if parts == ["api", "drives"]:
                    lr = library.root()
                    return self._json(200, {"drives": ingest.drives(), "projects_free": shutil.disk_usage(root).free, "month": library.month_name(),
                                            "library_root": str(lr) if lr else None,
                                            "library_clients": [c["name"] for c in library.scan(set())["clients"]] if lr else []})
                if parts == ["api", "scan"]:
                    try:
                        return self._json(200, ingest.scan(Path(str(body.get("path") or ""))))
                    except (ValueError, OSError) as e:
                        return self._json(400, {"error": str(e)})
                if parts == ["api", "import"]:
                    try:
                        if body.get("project"):
                            proj = proj_of(str(body["project"]))
                        else:
                            n = body.get("new") or {}
                            proj = create_project(root, str(n.get("title") or "").strip() or str(n.get("slug")), str(n.get("client") or "").strip() or "ללא לקוח",
                                                  str(n.get("slug") or "").strip())

                        files = [Path(str(x)) for x in body.get("files") or []]
                        lr = library.root()
                        lib_opt = body.get("library") or {}
                        if lr and files and all(f.resolve().is_relative_to(lr.resolve()) for f in files):
                            # footage already in the user's folders on this disk: link it, copy nothing
                            n, errs = link_into_source(proj, files)
                            remember_library(proj, files[0].parent, [str(f) for f in files],
                                             {"utc": now(), "mode": "linked-in-place", "files": n, "errors": len(errs)})
                            jid = "link-" + secrets.token_hex(4)
                            total = sum(f.stat().st_size for f in files if f.exists())
                            ingest.JOBS[jid] = {"id": jid, "project": proj.name, "state": "done" if not errs else "done-with-errors", "mode": "link",
                                                "phase": "link", "files_total": len(files), "files_done": len(files), "skipped": len(files) - n - len(errs),
                                                "bytes_total": total, "bytes_done": total, "current": "", "errors": [{"file": e.split(": ")[0], "error": e} for e in errs],
                                                "started": time.time(), "finished": time.time(), "log": None}
                            return self._json(200, {"ok": True, "job": jid, "project": proj.name})
                        raw_dir = None
                        st0 = load_state(proj)
                        if st0.get("library", {}).get("raw_dir") and not lib_opt.get("client"):
                            raw_dir = Path(st0["library"]["raw_dir"])  # more footage for a project made from an import
                        elif lr and lib_opt.get("client"):
                            bad = '<>:"/\\|?*'
                            cname = "".join("-" if ch in bad else ch for ch in str(lib_opt["client"]).strip())[:80]
                            month = "".join("-" if ch in bad else ch for ch in str(lib_opt.get("month") or "").strip())[:40]
                            if not cname:
                                raise ValueError("כתוב שם לקוח")
                            raw_dir = (lr / cname / month / library.RAW) if month else (lr / cname / library.RAW)

                        def done(job, log, proj=proj, raw_dir=raw_dir):
                            entry = {"utc": now(), "files": job["files_done"] - job["skipped"], "skipped": job["skipped"],
                                     "bytes": job["bytes_total"], "errors": len(job["errors"]), "log": job["log"]}
                            if not raw_dir:
                                with LOCK:
                                    st = load_state(proj)
                                    st.setdefault("imports", []).append(entry)
                                    save_state(proj, st)
                                return
                            n, errs = link_into_source(proj, [Path(e["dest"]) for e in log])  # one file, two names: גלם and source/
                            entry.update({"linked": n, "link_errors": errs})
                            remember_library(proj, raw_dir, [e["dest"] for e in log], entry)
                            if errs:
                                job["errors"] += [{"file": e.split(": ")[0], "error": "לא הצלחתי לקשר לפרויקט: " + e} for e in errs]
                                job["state"] = "done-with-errors"
                        job = ingest.start_import([str(f) for f in files], proj, done, dest=raw_dir)
                        return self._json(200, {"ok": True, "job": job["id"], "project": proj.name})
                    except (ValueError, RuntimeError, OSError) as e:
                        return self._json(400, {"error": str(e)})
                if parts == ["api", "listdir"]:  # the folder browser of the import (inside the user's library only)
                    lr = library.root()
                    tgt = Path(str(body.get("path") or (lr or "")))
                    if not lr or not tgt.is_dir() or not tgt.resolve().is_relative_to(lr.resolve()):
                        return self._json(400, {"error": "התיקייה לא נמצאה"})
                    dirs = sorted(d.name for d in tgt.iterdir() if d.is_dir() and not d.name.lower().startswith(library.SKIP_PREFIX) and not d.name.startswith("."))
                    return self._json(200, {"path": str(tgt), "root": str(lr), "dirs": dirs, "parent": str(tgt.parent) if tgt.resolve() != lr.resolve() else None})
                if parts == ["api", "premiere-cache"]:
                    return self._json(200, library.premiere_caches())
                if parts == ["api", "premiere-cache-clear"]:
                    try:
                        return self._json(200, library.clear_premiere_caches())
                    except RuntimeError as e:
                        return self._json(409, {"error": str(e)})
                if parts == ["api", "library-hide"]:
                    c = library.config()
                    name = str(body.get("name") or "").strip()
                    if name and name not in c["hidden"]:
                        c["hidden"].append(name)
                        library.save_config(c)
                    return self._json(200, {"ok": True, "hidden": c["hidden"]})
                if parts == ["api", "reveal"]:  # open Explorer on a file the page shows (only inside the library or the projects)
                    tgt = Path(str(body.get("path") or ""))
                    lr = library.root()
                    inside = tgt.exists() and (tgt.resolve().is_relative_to(root.resolve()) or bool(lr and tgt.resolve().is_relative_to(lr.resolve())))
                    if not inside:
                        return self._json(400, {"error": "הקובץ לא נמצא"})
                    subprocess.Popen(["explorer", "/select," + str(tgt.resolve())] if tgt.is_file() else ["explorer", str(tgt.resolve())])
                    return self._json(200, {"ok": True})
                if parts == ["api", "duplicates"]:
                    return self._json(200, ingest.find_duplicates(incoming, find_projects(root)))
                if parts == ["api", "duplicates-clean"]:
                    d = ingest.find_duplicates(incoming, find_projects(root))  # recomputed here: never trusts a list sent by the page
                    return self._json(200, ingest.clean_duplicates(incoming, d["files"]))
                if len(parts) == 3 and parts[:2] == ["api", "client-delete"]:
                    victims = [d for d in find_projects(root) if load_state(d)["client"] == parts[2]]
                    if body.get("confirm") != parts[2] or not victims:
                        return self._json(400, {"error": "כדי למחוק לקוח צריך להקליד את השם שלו בדיוק"})
                    done = []
                    for d in victims:
                        to_recycle_bin(d)
                        done.append(d.name)
                    return self._json(200, {"ok": True, "deleted": done})
                if len(parts) != 4 or parts[:2] != ["api", "project"]:
                    return self._json(404, {"error": "not found"})
                proj, op = proj_of(parts[2]), parts[3]
                if op == "raw-info":
                    return self._json(200, raw_info(root, proj))
                if op == "delete-raw":
                    if body.get("confirm") != proj.name:
                        return self._json(400, {"error": "confirmation does not match"})
                    src = proj / "source"
                    st = load_state(proj)
                    keys = {library.file_key(f) for f in src.rglob("*") if f.is_file()} if src.is_dir() else set()
                    lib_names = [Path(x) for x in st.get("library", {}).get("raw_files", [])]
                    if src.is_dir() and any(src.iterdir()):
                        to_recycle_bin(src)
                    src.mkdir(exist_ok=True)
                    gone = 0
                    for f in lib_names:  # the second name of the same footage (hard link) in the user's גלם folder
                        if f.is_file() and library.file_key(f) in keys:
                            to_recycle_bin(f)
                            gone += 1
                    with LOCK:
                        st = load_state(proj)
                        st["raw_deleted_utc"] = now()
                        save_state(proj, st)
                    return self._json(200, {"ok": True, "library_files": gone})
                if op == "delete":
                    if body.get("confirm") != proj.name:
                        return self._json(400, {"error": "confirmation does not match"})
                    lf = library.library_file(proj)
                    if lf is not None:  # a video in the user's folders: the file to the bin, its notes folder with it
                        if lf.exists():
                            to_recycle_bin(lf)
                        shutil.rmtree(proj, ignore_errors=True)
                        return self._json(200, {"ok": True})
                    to_recycle_bin(proj)
                    return self._json(200, {"ok": True})
                if op == "compact":
                    st = load_state(proj)
                    if st["status"] not in ("אושר", "נמסר") and not body.get("force"):
                        return self._json(409, {"error": "הסרטון עוד לא אושר. צמצום מיועד לעבודות גמורות", "need_force": True})
                    return self._json(200, compact(proj))
                with LOCK:
                    st = load_state(proj)
                    if op == "meta":
                        for k in ("title", "client"):
                            if isinstance(body.get(k), str) and body[k].strip():
                                st[k] = body[k].strip()[:120]
                        if body.get("status") in STATUSES:
                            st["status"] = body["status"]
                        save_state(proj, st)
                        return self._json(200, {"ok": True, "state": st})
                    if op == "note":
                        action = body.get("action")
                        if action == "create":
                            v = next((x for x in st["versions"] if x["id"] == body.get("version")), None)
                            if not v:
                                return self._json(400, {"error": "unknown version"})
                            n, err = clean_note(body.get("note") or {}, v.get("duration"))
                            if err:
                                return self._json(400, {"error": err})
                            n.update({"id": f"n{st.get('next_note', 1)}", "version": v["id"], "state": "pending", "author": "me",
                                      "created_utc": now(), "replies": []})
                            st["next_note"] = st.get("next_note", 1) + 1
                            png = body.get("png")
                            if isinstance(png, str) and png.startswith("data:image/png;base64,"):
                                import base64
                                f = proj / "review" / "drawings" / f"{n['id']}.png"
                                f.parent.mkdir(parents=True, exist_ok=True)
                                f.write_bytes(base64.b64decode(png.split(",", 1)[1]))
                                n["png"] = rel(proj, f)
                            st["notes"].append(n)
                        else:
                            n = next((x for x in st["notes"] if x["id"] == body.get("id")), None)
                            if not n:
                                return self._json(404, {"error": "no such note"})
                            if action == "update":
                                if n["state"] != "pending":
                                    return self._json(409, {"error": "הערה שכבר נשלחה לא נערכת. הוסף תגובה"})
                                if isinstance(body.get("text"), str):
                                    n["text"] = body["text"].strip()[:4000]
                                if body.get("kind") in KINDS:
                                    n["kind"] = body["kind"]
                            elif action == "delete":
                                if n["state"] != "pending":
                                    return self._json(409, {"error": "הערה שכבר נשלחה לא נמחקת"})
                                st["notes"].remove(n)
                            elif action == "reply":
                                txt = (body.get("text") or "").strip()
                                if not txt:
                                    return self._json(400, {"error": "empty reply"})
                                n.setdefault("replies", []).append({"author": "me", "text": txt[:4000], "utc": now()})
                                if n["state"] == "resolved" and body.get("reopen"):
                                    n["state"] = "open"
                            elif action in ("resolve", "reopen"):
                                if n["state"] == "pending":
                                    return self._json(409, {"error": "pending"})
                                n["state"] = "resolved" if action == "resolve" else "open"
                            else:
                                return self._json(400, {"error": "unknown action"})
                        save_state(proj, st)
                        return self._json(200, {"ok": True, "state": st})
                    if op in ("send", "approve"):
                        try:
                            doc = send_round(proj, st, body.get("version"), approved=(op == "approve"))
                        except ValueError as e:
                            return self._json(400, {"error": str(e)})
                        save_state(proj, st)
                        return self._json(200, {"ok": True, "round": doc["round"], "state": st})
                return self._json(404, {"error": "not found"})
            except KeyError:
                return self._json(404, {"error": "no such project"})
            except OSError as e:
                return self._json(500, {"error": f"{e}"})

    return H


def running(port: int) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1.5) as r:
            d = json.loads(r.read().decode("utf-8"))
            return d if d.get("app") == "warehouse" else None
    except (OSError, ValueError):
        return None


def serve(root: Path, port: int, open_browser: bool) -> int:
    url = f"http://127.0.0.1:{port}/"
    if running(port):
        print(json.dumps({"status": "running", "url": url, "reused": True}, ensure_ascii=False), flush=True)
        if open_browser:
            import webbrowser
            webbrowser.open(url)
        return 0
    tf = STATE / ".token"  # one token per install, so a page left open survives a server restart (a reboot)
    try:
        token = tf.read_text(encoding="utf-8").strip()
    except OSError:
        token = ""
    if len(token) < 20:
        token = secrets.token_urlsafe(24)
        STATE.mkdir(parents=True, exist_ok=True)
        tf.write_text(token, encoding="utf-8")
    port_ref = [port]

    class S(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = os.name != "nt"  # on Windows SO_REUSEADDR lets a second server bind the same port

        def server_bind(self):
            import socket
            import socketserver
            if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            socketserver.TCPServer.server_bind(self)
            self.server_name, self.server_port = self.server_address[:2]

    try:
        httpd = S(("127.0.0.1", port), make_handler(root, token, port_ref))
    except OSError as e:
        print(json.dumps({"status": "not_run", "reason": f"cannot listen on 127.0.0.1:{port}: {e}"}, ensure_ascii=False), flush=True)
        return 2
    print(json.dumps({"status": "serving", "url": url, "root": str(root)}, ensure_ascii=False), flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


# ----------------------------------------------------------------------------------------------------------------------------- CLI

def resolve_project(arg: str, root: Path) -> Path:
    p = Path(arg)
    if not (p / "project.json").exists():
        p = root / arg
    if not (p / "project.json").exists():
        raise SystemExit(f"no project at {arg} (looked for project.json)")
    return p.resolve()


def cmd_add(proj: Path, video: Path, label: str | None, port: int) -> int:
    if not video.exists() or video.suffix.lower() not in VIDEO_EXT:
        print(json.dumps({"status": "refused", "reason": f"no video at {video}"}, ensure_ascii=False))
        return 2
    with LOCK:
        st = load_state(proj)
        sync_versions(proj, st)
        r = rel(proj, video)
        v = next((x for x in st["versions"] if x["file"] == r or r in x.get("aliases", [])), None)
        if not v:
            v = {"id": f"V{len(st['versions']) + 1}", "file": r, "label": label or video.stem, "bytes": video.stat().st_size,
                 "added_utc": now(), "draft": "_work" in Path(r).parts}
            st["versions"].append(v)
        elif label:
            v["label"] = label
        ensure_probe(proj, v)
        st["status"] = "ממתין לבדיקה"
        save_state(proj, st)
    url = f"http://127.0.0.1:{port}/#/p/{urllib.parse.quote(proj.name)}/{v['id']}"
    print(json.dumps({"status": "ok", "version": v["id"], "url": url, "server_running": bool(running(port)),
                      "next": "open the url in the browser pane, then run `warehouse.py wait <project>` as a BACKGROUND command"},
                     ensure_ascii=False, indent=2))
    return 0


def unseen_rounds(st: dict) -> list[dict]:
    seen = st.get("agent_seen_round", 0)
    return [r for r in st["rounds"] if r["n"] > seen]


def round_report(proj: Path, rounds: list[dict]) -> dict:
    """The rounds the agent has not read yet -> one report (the newest round decides approved/ok). Marks them as read."""
    out = []
    for r in rounds:
        nj = proj / "review" / f"round-{r['n']}" / "notes.json"
        doc = json.loads(nj.read_text(encoding="utf-8"))
        out.append({"round": r["n"], "version": r["version"], "approved": doc["approved"], "notes_json": str(nj),
                    "notes_md": str(nj.with_name("notes.md")), "video": doc["video"], "lines": [note_line(x) for x in doc["notes"]],
                    "strips": {str(x["n"]): ",".join(f"{v:g}" for v in x["strip_times"]) for x in doc["notes"] if x["strip_times"]},
                    "drawings": {str(x["n"]): str(proj / x["png"]) for x in doc["notes"] if x.get("png")},
                    "ids": {str(x["n"]): x["id"] for x in doc["notes"]}})
    last = out[-1]
    res = {"status": "approved" if last["approved"] else "ok", "project": proj.name, **{k: last[k] for k in last if k != "approved"}}
    if len(out) > 1:
        res["earlier_rounds"] = out[:-1]
    res["next"] = ("APPROVED: write `APPROVED <date> (warehouse, round N)` in hf/CHANGELOG.md and continue with render-qa-delivery"
                   if last["approved"] else
                   "open '## Round N' in hf/CHANGELOG.md with these lines (the user's words, numbered; 'אהבתי' lines are keep-as-is "
                   "guidance, not fixes), LOOK at every drawing PNG, extract a strip per timed note, diagnose and classify; after the fix "
                   "answer each note with `warehouse.py reply <project> <id> --text \"תוקן: ...\" --resolve` and register the new render "
                   "with `warehouse.py add <project> <video>`")
    with LOCK:
        st = load_state(proj)
        st["agent_seen_round"] = max(st.get("agent_seen_round", 0), rounds[-1]["n"])
        save_state(proj, st, touch=False)
    return res


def cmd_wait(proj: Path, timeout: float) -> int:
    """Block until a round the agent has not read exists (one sent while nobody waited is returned at once)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = load_state(proj)
        rounds = unseen_rounds(st)
        if rounds:
            print(json.dumps(round_report(proj, rounds), ensure_ascii=False, indent=2), flush=True)
            return 0
        time.sleep(1.5)
    print(json.dumps({"status": "timeout", "reason": f"nothing was sent within {timeout:.0f} s"}, ensure_ascii=False))
    return 3


def cmd_inbox(root: Path) -> int:
    """Every project with notes or approvals the agent has not read yet (read-only: nothing is marked as read)."""
    items = []
    for p in find_projects(root):
        st = load_state(p)
        rs = unseen_rounds(st)
        if rs:
            items.append({"project": p.name, "title": st["title"], "client": st["client"], "rounds": [r["n"] for r in rs],
                          "approved": rs[-1]["approved"], "notes": sum(r.get("count", 0) for r in rs)})
    print(json.dumps({"status": "ok", "waiting": items,
                      "next": "for each project: `warehouse.py wait <project>` returns its notes at once and marks them read" if items else
                      "nothing new from the warehouse"}, ensure_ascii=False, indent=2))
    return 0


def cmd_reply(proj: Path, note_id: str, text: str, resolve: bool) -> int:
    with LOCK:
        st = load_state(proj)
        n = next((x for x in st["notes"] if x["id"] == note_id), None)
        if not n:
            print(json.dumps({"status": "refused", "reason": f"no note {note_id}"}, ensure_ascii=False))
            return 2
        n.setdefault("replies", []).append({"author": "claude", "text": text, "utc": now()})
        if resolve and n["state"] != "pending":
            n["state"] = "resolved"
        save_state(proj, st)
    print(json.dumps({"status": "ok", "note": note_id, "state": n["state"]}, ensure_ascii=False))
    return 0


def self_check() -> int:
    import tempfile
    ok = True

    def check(cond, what):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + what)
        ok &= bool(cond)

    check(tc(14.5) == "0:14.50" and tc(None) == "general", "tc")
    check(strip_times(5, None, 30)[0] == 4.0 and len(strip_times(5, None, 30)) == 9, "strip_times point")
    n, e = clean_note({"t": 3, "end": 2, "text": "x"}, 10)
    check(e and not n, "range end before start refused")
    n, e = clean_note({"t": 3, "text": "", "drawing": [{"tool": "pen"}]}, 10)
    check(n and not e, "drawing-only note accepted")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "client-a-01"
        (p / "final").mkdir(parents=True)
        (p / "_work" / "gen").mkdir(parents=True)
        (p / "_work" / "snaps").mkdir(parents=True)
        (p / "project.json").write_text('{"title":"t"}', encoding="utf-8")
        a = p / "final" / "x_v1.mp4"
        a.write_bytes(b"1" * 10)
        b = p / "final" / "x.mp4"
        b.write_bytes(b"2" * 20)
        os.utime(a, (1, 1))
        (p / "final" / "x_v2.mp4").write_bytes(b"2" * 20)  # same bytes as x.mp4: an alias
        (p / "_work" / "gen" / "paid.mp4").write_bytes(b"g")
        (p / "_work" / "snaps" / "f.png").write_bytes(b"s")
        (p / "_work" / "raw.mp4").write_bytes(b"r")
        (p / "_work" / "notes.md").write_text("keep", encoding="utf-8")
        (p / "_work" / "vo.wav").write_bytes(b"a")
        st = load_state(p)
        check(st["client"] == "client", "client guessed from slug")
        sync_versions(p, st)
        check([v["id"] for v in st["versions"]] == ["V1", "V2"] and st["versions"][1].get("aliases"), "versions + alias")
        plan = {x.relative_to(p).as_posix() for x in compact_plan(p)}
        check(plan == {"_work/snaps/f.png", "_work/raw.mp4"}, f"compact plan keeps gen/, audio, text ({sorted(plan)})")
        st["versions"][0]["duration"] = 10.0
        st["notes"] = [{"id": "n1", "version": "V1", "state": "pending", "t": 1.0, "end": None, "kind": "fix", "text": "a"},
                       {"id": "n2", "version": "V1", "state": "pending", "t": 2.0, "end": 3.0, "kind": "like", "text": "b"}]
        try:
            send_round(p, st, "V1", approved=True)
            check(False, "approve with a pending fix refused")
        except ValueError:
            check(True, "approve with a pending fix refused")
        doc = send_round(p, st, "V1", approved=False)
        check(doc["round"] == 1 and (p / "review" / "round-1" / "notes.json").exists() and st["status"] == "בתיקונים", "send round")
        check(st["notes"][0]["state"] == "open" and st["notes"][1]["state"] == "sent", "fix -> open, like -> sent")
        r = compact(p)
        check(r["files"] == 2 and (p / "_work" / "gen" / "paid.mp4").exists() and (p / "_work" / "notes.md").exists(), "compact")
    print("self-check", "passed" if ok else "FAILED")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--self-check":
        return self_check()
    cmd, rest = argv[0], argv[1:]
    opts, pos, i = {}, [], 0
    while i < len(rest):
        a = rest[i]
        if a in ("--open", "--resolve"):
            opts[a[2:]] = True
        elif a.startswith("--") and i + 1 < len(rest):
            opts[a[2:]] = rest[i + 1]
            i += 1
        else:
            pos.append(a)
        i += 1
    root = Path(opts.get("root") or os.environ.get("AVC_WAREHOUSE_ROOT") or DEFAULT_ROOT).resolve()
    port = int(opts.get("port") or DEFAULT_PORT)
    if cmd == "serve":
        return serve(root, port, bool(opts.get("open")))
    if cmd == "add" and len(pos) == 2:
        return cmd_add(resolve_project(pos[0], root), Path(pos[1]).resolve(), opts.get("label"), port)
    if cmd == "wait" and len(pos) == 1:
        return cmd_wait(resolve_project(pos[0], root), float(opts.get("timeout") or 7200))
    if cmd == "inbox":
        return cmd_inbox(root)
    if cmd == "reply" and len(pos) == 2 and opts.get("text"):
        return cmd_reply(resolve_project(pos[0], root), pos[1], opts["text"], bool(opts.get("resolve")))
    if cmd == "url" and len(pos) == 1:
        proj = resolve_project(pos[0], root)
        print(f"http://127.0.0.1:{port}/#/p/{urllib.parse.quote(proj.name)}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))

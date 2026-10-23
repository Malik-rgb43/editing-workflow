"""warehouse_link - turn on and drive the OPTIONAL client-video warehouse ("מחסן העבודות") from the toolkit.

The warehouse is a local review room (stdlib Python, 127.0.0.1 only): one page for every client video with a frame-accurate player,
numbered notes with drawings, versions (V1, V2, ...), footage intake and an archive of approved videos. It was written by Gabriel Gelman
(https://github.com/GabrielGel/video-warehouse); a copy ships with this toolkit in ``tools/warehouse/`` (see NOTICE). It is OFF until
the user turns it on. This tool (1) turns it on (``set --bundled``) or points at another copy (``set DIR``), (2) says whether it is ready,
and (3) runs its commands with the right project root, port and state folder, so skills never guess a path:

  * where: ``--repo`` / ``AVC_WAREHOUSE_REPO`` / ``~/.avc/warehouse.json`` (written by ``set``). Not turned on = not connected, which is
    a normal state: the skills then use the notes page of ``revision-notes-handler`` (``notes_board.py``) exactly as before.
  * state (page token, caches, ``config.json`` with the client-folder path): ``AVC_WAREHOUSE_STATE``, else ``~/.avc/warehouse-state`` for the
    bundled copy, so a toolkit update never wipes it.
  * which port: 8765 unless ``AVC_WAREHOUSE_PORT`` is set (use it when another program already holds 8765; ``serve`` then says so).
  * which projects: ``AVC_WAREHOUSE_ROOT``, else ``<work_root>/projects`` (the toolkit's own projects, so the warehouse shows and reviews
    the same folders ``new_project.py`` makes), else the warehouse's own default.

``status`` and ``run inbox|url`` only read. ``run add|reply`` write inside ``<project>/review/`` (the warehouse's own state); ``run serve``
starts the local page. Compaction and deletion are buttons on the page for the user: this tool never offers them.

Usage:
    python tools/warehouse_link.py status [--json] [--repo DIR]
    python tools/warehouse_link.py set --bundled | REPO_OR_warehouse.py | --remove
    python tools/warehouse_link.py library [FOLDER | --clear]       # the user's existing client folders (read-only in the page)
    python tools/warehouse_link.py shortcut [--remove]              # a Desktop launcher (Windows)
    python tools/warehouse_link.py run [--repo DIR] -- serve|add|wait|inbox|reply|url ARGS...
Exit: status 0 always (a report); set 0 ok / 2 refused; run = the warehouse's exit code (2 when not connected).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
except (AttributeError, ValueError):
    pass

TOOLKIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
DEFAULT_PORT = 8765  # override with AVC_WAREHOUSE_PORT when something else already holds it
REPO_URL = "https://github.com/GabrielGel/video-warehouse.git"
BUNDLED = TOOLKIT / "tools" / "warehouse" / "warehouse.py"  # the copy that ships with the toolkit
BUNDLED_TOKEN = "bundled"  # the value ``set --bundled`` writes into warehouse.json
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def config_file(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".avc" / "warehouse.json"


def tool_in(path: str | os.PathLike) -> Path | None:
    """The ``warehouse.py`` that ``path`` names: the file itself, a folder holding it, or a repo with ``warehouse/warehouse.py``."""
    if str(path) == BUNDLED_TOKEN:
        return BUNDLED.resolve() if BUNDLED.is_file() else None
    p = Path(path).expanduser()
    for cand in (p, p / "warehouse.py", p / "warehouse" / "warehouse.py"):
        if cand.is_file() and cand.name == "warehouse.py":
            return cand.resolve()
    return None


def find(repo: str | None = None, home: Path | None = None) -> tuple[Path | None, str]:
    """(warehouse.py or None, how it was found / why not)."""
    for label, raw in (("--repo", repo), ("AVC_WAREHOUSE_REPO", os.environ.get("AVC_WAREHOUSE_REPO"))):
        if raw:
            t = tool_in(raw)
            return (t, label) if t else (None, f"{label} = {raw} has no warehouse.py")
    cfg = config_file(home)
    try:
        raw = json.loads(cfg.read_text(encoding="utf-8")).get("repo")
    except (OSError, ValueError, AttributeError):
        raw = None
    if raw:
        t = tool_in(raw)
        return (t, f"{cfg}") if t else (None, f"{cfg} points at {raw}, which has no warehouse.py")
    return None, "not set (optional)"


def is_bundled(tool: Path) -> bool:
    return tool.resolve() == BUNDLED.resolve()


def state_dir(tool: Path) -> Path | None:
    """Where the warehouse keeps its token, caches and ``config.json``: outside the toolkit copy for the bundled one (None = its own folder)."""
    env = os.environ.get("AVC_WAREHOUSE_STATE", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".avc" / "warehouse-state" if is_bundled(tool) else None


def projects_root(tool: Path) -> tuple[Path, str]:
    env = os.environ.get("AVC_WAREHOUSE_ROOT", "").strip()
    if env:
        return Path(env).expanduser(), "AVC_WAREHOUSE_ROOT"
    try:
        from session_hint import configured_work_root

        wr = configured_work_root(TOOLKIT)
    except Exception:  # noqa: BLE001 - a broken config must not hide the warehouse
        wr = None
    if wr:
        return wr / "projects", "work_root/projects"
    if is_bundled(tool):  # never inside the toolkit copy: an update would replace it
        return (state_dir(tool) or Path.home() / ".avc" / "warehouse-state") / "projects", "bundled default (set paths.work_root in toolkit.toml to share the folders with new_project.py)"
    return tool.parent.parent / "projects", "the warehouse's default"


def child_env(tool: Path) -> dict:
    env = dict(os.environ)
    env["AVC_WAREHOUSE_ROOT"] = str(projects_root(tool)[0])
    env.setdefault("AVC_TOOLKIT_ROOT", str(TOOLKIT))  # new projects made from the page use THIS toolkit's scaffold
    st = state_dir(tool)
    if st is not None:
        env["AVC_WAREHOUSE_STATE"] = str(st)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def call(tool: Path, args: list[str], timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-X", "utf8", str(tool), *args], env=child_env(tool), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout, creationflags=NO_WINDOW)


def port() -> int:
    try:
        return int(os.environ.get("AVC_WAREHOUSE_PORT", "") or DEFAULT_PORT)
    except ValueError:
        return DEFAULT_PORT


def server_running(port_: int | None = None) -> bool:
    port_ = port_ or port()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port_}/api/ping", timeout=1.0) as r:
            return json.loads(r.read().decode("utf-8")).get("app") == "warehouse"
    except (OSError, ValueError):
        return False


def waiting(tool: Path) -> dict:
    """Projects with notes or an approval the agent has not read yet (the warehouse's ``inbox`` is read-only)."""
    try:
        r = call(tool, ["inbox"], timeout=15)
        doc = json.loads(r.stdout)
        return {"ok": r.returncode == 0, "items": doc.get("waiting", [])}
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        return {"ok": False, "items": [], "why": str(exc)[:200]}


def status(repo: str | None = None, home: Path | None = None, probe: bool = True) -> dict:
    tool, how = find(repo, home)
    if tool is None:
        return {"tool": "warehouse_link", "connected": False, "how": how, "optional": True, "bundled_available": BUNDLED.is_file(),
                "next": ("optional. A copy ships with the toolkit: turn it on with `python tools/warehouse_link.py set --bundled`, only if the user wants it "
                         "(INSTALL.md install-11). "
                         if BUNDLED.is_file() else f"optional. To connect: `git clone {REPO_URL} <short ASCII folder>` then `python tools/warehouse_link.py set <that folder>`. ")
                        + "Until then the notes page (notes_board.py) does the review."}
    root, root_src = projects_root(tool)
    out = {"tool": "warehouse_link", "connected": True, "how": how, "bundled": is_bundled(tool), "warehouse_py": str(tool), "root": str(root),
           "root_from": root_src, "root_exists": root.is_dir(), "python_ok": sys.version_info >= (3, 10)}
    if state_dir(tool) is not None:
        out["state_dir"] = str(state_dir(tool))
    if not tool.parent.parent.name.isascii() or not str(root).isascii():
        out["warning"] = "a non-ASCII path: the warehouse asks for a short ASCII folder (HyperFrames also refuses non-ASCII project paths)"
    if probe:
        out["port"] = port()
        out["server_running"] = server_running()
        w = waiting(tool)
        out["waiting"] = w["items"]
        if not w["ok"]:
            out["inbox_error"] = w.get("why") or "inbox exited non-zero"
    out["next"] = ("use it: `python tools/warehouse_link.py run -- <serve|add|wait|inbox|reply|url> ...` (revision-notes-handler 'With the warehouse')"
                   + ("; notes are waiting - run `wait <project>` for each" if out.get("waiting") else ""))
    return out


def cmd_set(target: str, remove: bool, home: Path | None, bundled: bool = False) -> int:
    cfg = config_file(home)
    if remove:
        try:
            cfg.unlink()
            print(json.dumps({"status": "ok", "removed": str(cfg)}))
        except FileNotFoundError:
            print(json.dumps({"status": "ok", "removed": None, "why": "nothing was set"}))
        return 0
    if bundled:
        target = BUNDLED_TOKEN
    tool = tool_in(target)
    if tool is None:
        print(json.dumps({"status": "refused", "reason": ("the bundled copy is missing from this toolkit install (tools/warehouse/warehouse.py)" if bundled
                          else f"no warehouse.py in {target} (clone {REPO_URL} and point at the folder, or use --bundled)")}))
        return 2
    try:
        r = call(tool, ["--self-check"], timeout=60)
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(json.dumps({"status": "refused", "reason": f"the warehouse's --self-check did not run: {exc}"}))
        return 2
    if r.returncode != 0:
        print(json.dumps({"status": "refused", "reason": "the warehouse's --self-check failed", "tail": (r.stdout + r.stderr)[-400:]}))
        return 2
    cfg.parent.mkdir(parents=True, exist_ok=True)
    saved = BUNDLED_TOKEN if is_bundled(tool) else str(tool.parent.parent)
    cfg.write_text(json.dumps({"repo": saved}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "saved": str(cfg), "repo": saved, "self_check": "pass"}, ensure_ascii=False))
    return 0


def library_config(tool: Path) -> Path:
    return (state_dir(tool) or tool.parent) / "config.json"


def cmd_library(folder: str, clear: bool, repo: str | None) -> int:
    """Tell the warehouse where the user's existing client folders are (it shows them read-only). Writes only the warehouse's own config.json."""
    tool, how = find(repo)
    if tool is None:
        print(json.dumps({"status": "refused", "reason": f"the warehouse is not turned on ({how}); run `set --bundled` first"}))
        return 2
    cfg = library_config(tool)
    try:
        doc = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        doc = {}
    if not isinstance(doc, dict):
        doc = {}
    if clear:
        doc["library_root"] = ""
    elif folder:
        p = Path(folder).expanduser()
        if not p.is_dir():
            print(json.dumps({"status": "refused", "reason": f"{folder} is not an existing folder"}, ensure_ascii=False))
            return 2
        doc["library_root"] = str(p)
    else:
        print(json.dumps({"status": "ok", "config": str(cfg), "library_root": doc.get("library_root", ""), "hidden": doc.get("hidden", [])}, ensure_ascii=False))
        return 0
    doc.setdefault("hidden", [])
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "config": str(cfg), "library_root": doc["library_root"]}, ensure_ascii=False))
    return 0


def shortcut_path() -> Path:
    return Path.home() / "Desktop" / "Video Warehouse.cmd"


def cmd_shortcut(remove: bool, repo: str | None) -> int:
    """A Desktop launcher that starts the page with this toolkit's settings (Windows only; one small text file, removable)."""
    path = shortcut_path()
    if remove:
        try:
            path.unlink()
            print(json.dumps({"status": "ok", "removed": str(path)}, ensure_ascii=False))
        except FileNotFoundError:
            print(json.dumps({"status": "ok", "removed": None, "why": "nothing was made"}))
        return 0
    if os.name != "nt":
        print(json.dumps({"status": "refused", "reason": "the launcher is for Windows; elsewhere run `python tools/warehouse_link.py run -- serve --open`"}))
        return 2
    tool, how = find(repo)
    if tool is None:
        print(json.dumps({"status": "refused", "reason": f"the warehouse is not turned on ({how}); run `set --bundled` first"}))
        return 2
    py = Path(sys.executable)
    pyw = py.with_name("pythonw.exe") if py.with_name("pythonw.exe").is_file() else py
    lines = ["@echo off", "chcp 65001 >nul", "rem Opens the video warehouse page (starts the local server first if it is not running).",
             f'set "AVC_WAREHOUSE_PORT={port()}"']
    for k, v in child_env(tool).items():
        if k in ("AVC_WAREHOUSE_ROOT", "AVC_WAREHOUSE_STATE", "AVC_TOOLKIT_ROOT"):
            lines.append(f'set "{k}={v}"')
    lines.append(f'start "" "{pyw}" "{tool}" serve --open --port {port()}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "shortcut": str(path)}, ensure_ascii=False))
    return 0


def cmd_run(args: list[str], repo: str | None) -> int:
    tool, how = find(repo)
    if tool is None:
        print(json.dumps({"status": "refused", "reason": f"the warehouse is not connected ({how})",
                          "next": "use the notes page (revision-notes-handler/scripts/notes_board.py); to connect: python tools/warehouse_link.py status"}))
        return 2
    if not args:
        print(json.dumps({"status": "refused", "reason": "no warehouse command given (serve|add|wait|inbox|reply|url)"}))
        return 2
    if args[0] in ("serve", "add", "url") and "--port" not in args and os.environ.get("AVC_WAREHOUSE_PORT"):
        args = [*args, "--port", str(port())]  # the page, the printed urls and the status probe all use the same port
    # relay the child's output line by line (a pipe, not an inherited handle: CREATE_NO_WINDOW loses inherited stdout on Windows), so `wait`,
    # a background command that blocks until the user presses send, hands over its JSON the moment it ends
    proc = subprocess.Popen([sys.executable, "-X", "utf8", str(tool), *args], env=child_env(tool), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    try:
        for line in proc.stdout:  # type: ignore[union-attr]
            print(line, end="", flush=True)
        return proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        return 130


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("status")
    st.add_argument("--json", action="store_true", help="accepted for symmetry: the report is always JSON")
    st.add_argument("--repo")
    st.add_argument("--home", type=Path, help=argparse.SUPPRESS)
    se = sub.add_parser("set")
    se.add_argument("target", nargs="?", default="")
    se.add_argument("--remove", action="store_true")
    se.add_argument("--bundled", action="store_true", help="use the copy that ships with the toolkit (tools/warehouse/)")
    se.add_argument("--home", type=Path, help=argparse.SUPPRESS)
    li = sub.add_parser("library")
    li.add_argument("folder", nargs="?", default="")
    li.add_argument("--clear", action="store_true")
    li.add_argument("--repo")
    sc = sub.add_parser("shortcut")
    sc.add_argument("--remove", action="store_true")
    sc.add_argument("--repo")
    ru = sub.add_parser("run")
    ru.add_argument("--repo")
    ru.add_argument("rest", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    if a.cmd == "status":
        rep = status(a.repo, a.home)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    if a.cmd == "set":
        if not a.target and not a.remove and not a.bundled:
            print(json.dumps({"status": "refused", "reason": "give --bundled, the warehouse folder, or --remove"}))
            return 2
        return cmd_set(a.target, a.remove, a.home, a.bundled)
    if a.cmd == "library":
        return cmd_library(a.folder, a.clear, a.repo)
    if a.cmd == "shortcut":
        return cmd_shortcut(a.remove, a.repo)
    rest = a.rest[1:] if a.rest[:1] == ["--"] else a.rest
    return cmd_run(rest, a.repo)


if __name__ == "__main__":
    sys.exit(main())

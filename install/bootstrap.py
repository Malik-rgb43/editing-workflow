#!/usr/bin/env python3
"""AI Video Editing Toolkit - one-link installer / bootstrap (Python stdlib only).

Usage: python install/bootstrap.py [plan|apply|add|verify|status|where|mark|rollback|uninstall|run] [options]

Run `python install/bootstrap.py --help` for the options, or read INSTALL.md.
Default command is `plan` (read-only). Nothing is changed without `apply --yes`.
No telemetry. No secrets are ever read, asked for or written. Windows, macOS, Linux.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if sys.version_info < (3, 9):  # pragma: no cover
    sys.exit("bootstrap.py needs Python 3.9+ to start (3.11+ to read the catalogue). See INSTALL.md step install-02.")

BOOTSTRAP_VERSION = "0.1.0"
MANIFEST_SCHEMA = 1
MARKER = ".avc-managed.json"
MD_BEGIN = "<!-- avc-toolkit:begin v1 -->"
MD_END = "<!-- avc-toolkit:end -->"
REPO = Path(__file__).resolve().parent.parent

# This installer lives in the editing toolkit repository (ADR 0005). Claude Code itself (CLAUDE.md, Playwright MCP, Superpowers) is set up by the
# separate claude-code-setup repository. Everything below is copied from THIS repository into one managed toolkit home so that skill paths
# (agent-content/..., tools/...) resolve.
# Directories (relative to this repository) copied into the managed toolkit home. Skills are installed separately.
TOOLKIT_INCLUDE = [
    "agent-content/playbooks", "agent-content/techniques", "agent-content/benchmarks", "agent-content/references",
    "tools", "src", "contracts", "profiles", "templates", "fixtures", "hf-blocks",
    "docs/en", "docs/he", "docs/TOOLS.md", "docs/decisions",
    "pyproject.toml", "uv.lock", "package.json", "package-lock.json", "toolkit.toml",
    "AGENTS.md", "SYSTEM.md", "editing.md", "release-manifest.json", "LICENSE", "THIRD_PARTY_NOTICES.md",
]
# The installer and the integrations catalogue travel with the toolkit so `add` and `verify` work from the toolkit home.
SETUP_INCLUDE = ["integrations", "install"]
EXCLUDE_NAMES = {"__pycache__", ".pytest_cache", ".venv", "node_modules", ".git", ".DS_Store", "Thumbs.db",
                 "_work", "projects", ".avc", ".mypy_cache", ".ruff_cache"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".tmp", ".part")
GENERATED_DIRS = [".venv", "node_modules"]
PATH_TOKEN_ROOTS = ("agent-content", "tools", "fixtures", "contracts", "profiles", "templates", "src", "integrations", "hf-blocks")
LEVELS = {"minimal": ["minimal"], "standard": ["minimal", "standard"], "pro": ["minimal", "standard", "pro"]}

EXIT_OK, EXIT_USAGE, EXIT_REFUSED, EXIT_VERIFY, EXIT_PARTIAL, EXIT_LOCK = 0, 1, 2, 3, 4, 5

# ----------------------------------------------------------------------------- i18n (labels only)
MSG = {
    "en": {
        "plan_title": "Install plan (read-only - nothing has been changed)",
        "host": "This computer", "selection": "Your choices", "prereq": "Prerequisites", "skills": "Skills to install",
        "mcp": "Connectors (MCP servers)", "downloads": "Downloads and network", "cost": "Cost",
        "conflicts": "Conflicts (will be skipped unless you say --force)", "routes": "Routes chosen automatically (no hardware questions)", "warnings": "Warnings", "blockers": "Blockers",
        "confirm": "Ask the student ONE confirmation, then run:", "none": "none", "cost_core": "none (core path needs no account, no API key, no payment)",
        "ok": "ok", "missing": "MISSING", "state_installed": "installed", "state_account": "authorised account",
        "state_render": "first render", "state_inspect": "inspection passed", "state_paid": "ready for paid generation",
        "signup": "sign-up (paid service)", "link_referral": "referral link", "link_plain": "plain link",
        "referral_note": "Disclosure: this is a referral link - signing up through it supports this project at no extra cost to you.",
        "signup_ask": "Ask the student which link to use (or to skip: they may already have an account). Open nothing without their yes.",
    },
    "he": {
        "plan_title": "תוכנית התקנה (קריאה בלבד - שום דבר לא שונה)",
        "host": "המחשב הזה", "selection": "הבחירות שלך", "prereq": "דרישות מקדימות", "skills": "סקילים להתקנה",
        "mcp": "מחברים (שרתי MCP)", "downloads": "הורדות ורשת", "cost": "עלות",
        "conflicts": "התנגשויות (ידולגו אלא אם תאשר --force)", "routes": "מסלולים שנבחרו אוטומטית (בלי שאלות על חומרה)", "warnings": "אזהרות", "blockers": "חסמים",
        "confirm": "מבקשים מהסטודנט אישור אחד, ואז מריצים:", "none": "אין", "cost_core": "אפס (מסלול הליבה לא דורש חשבון, מפתח API או תשלום)",
        "ok": "תקין", "missing": "חסר", "state_installed": "מותקן", "state_account": "חשבון מאושר",
        "state_render": "רינדור ראשון", "state_inspect": "בדיקה עברה", "state_paid": "מוכן ליצירה בתשלום",
        "signup": "הרשמה (שירות בתשלום)", "link_referral": "לינק הפניה", "link_plain": "לינק רגיל",
        "referral_note": "גילוי נאות: זה לינק הפניה - הרשמה דרכו תומכת בפרויקט הזה, בלי עלות נוספת עבורך.",
        "signup_ask": "שואלים את התלמיד באיזה לינק להשתמש (או לדלג: אולי כבר יש לו חשבון). לא פותחים שום דבר בלי שהוא אישר.",
    },
}


def tr(lang: str, key: str) -> str:
    return MSG.get(lang, MSG["en"]).get(key, MSG["en"].get(key, key))


# ----------------------------------------------------------------------------- small utilities
def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ts_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S") + "%02d" % (int(time.time() * 100) % 100) + "Z"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n} B"


def read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def atomic_write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".avc-tmp-%d" % os.getpid())
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, p)


def atomic_write_json(p: Path, obj) -> None:
    atomic_write_text(p, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def is_ascii_path(p) -> bool:
    return str(p).isascii()


def user_home() -> Path:
    v = os.environ.get("AVC_USER_HOME")
    return Path(v) if v else Path.home()


def os_name() -> str:
    return {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")


def which(name: str):
    return shutil.which(name)


def emit(text: str = "", file=None) -> None:
    print(text, file=file or sys.stdout)


# ----------------------------------------------------------------------------- subprocess (single choke point)
class Proc:
    def __init__(self, argv, returncode, stdout="", stderr="", error=None, timed_out=False):
        self.argv, self.returncode, self.stdout, self.stderr = list(argv), returncode, stdout, stderr
        self.error, self.timed_out = error, timed_out

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


_CMD_SPECIAL = set('&|<>^%"')


def run_cmd(argv, cwd=None, env=None, timeout=60) -> "Proc":
    """The ONLY place that starts child processes. Tests replace this function."""
    if os.environ.get("AVC_NO_REAL_EXEC") == "1":
        raise RuntimeError("AVC_NO_REAL_EXEC=1: refusing to start a real process: %r" % (argv,))
    exe = which(argv[0]) or argv[0]
    full = [exe] + [str(a) for a in argv[1:]]
    if os_name() == "windows" and exe.lower().endswith((".cmd", ".bat")):
        bad = [a for a in full[1:] if any(c in _CMD_SPECIAL for c in a)]
        if bad:
            return Proc(argv, 126, error="argument contains a cmd.exe special character (& | < > ^ percent quote): " + repr(bad))
    child_env = dict(os.environ)
    child_env.update({"PYTHONUTF8": "1", "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1",
                      "npm_config_update_notifier": "false", "npm_config_fund": "false", "npm_config_audit": "false"})
    if env:
        child_env.update(env)
    try:
        cp = subprocess.run(full, cwd=str(cwd) if cwd else None, env=child_env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)
        return Proc(argv, cp.returncode, cp.stdout or "", cp.stderr or "")
    except FileNotFoundError as e:
        return Proc(argv, 127, error=str(e))
    except subprocess.TimeoutExpired as e:
        return Proc(argv, 124, (e.stdout or "") if isinstance(e.stdout, str) else "", "", error="timeout after %ss" % timeout, timed_out=True)
    except OSError as e:
        return Proc(argv, 126, error=str(e))


# ----------------------------------------------------------------------------- catalogue
def load_toml(path: Path) -> dict:
    try:
        import tomllib  # type: ignore
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore
        except ModuleNotFoundError:
            reexec_with_uv()
            raise SystemExit("Python 3.11+ is required to read integrations/catalog.toml (found %s). Fix: install Python 3.12 or run "
                             "`uv run --python 3.12 --no-project python install/bootstrap.py ...` (INSTALL.md install-02)." % sys.version.split()[0])
    with open(path, "rb") as f:
        return tomllib.load(f)


def reexec_with_uv() -> None:
    """Python < 3.11: re-run ourselves under uv-managed Python 3.12 when uv exists (no install is performed by us)."""
    if os.environ.get("AVC_REEXEC") == "1" or not which("uv") or os.environ.get("AVC_NO_REAL_EXEC") == "1":
        return
    env = dict(os.environ, AVC_REEXEC="1")
    cp = subprocess.run(["uv", "run", "--python", "3.12", "--no-project", "python", str(Path(__file__).resolve())] + sys.argv[1:], env=env)
    raise SystemExit(cp.returncode)


def load_catalog(repo: Path) -> dict:
    p = repo / "integrations" / "catalog.toml"
    if not p.is_file():
        raise SystemExit("catalogue not found: %s" % p)
    cat = load_toml(p)
    ids = [e["id"] for e in cat.get("entry", [])]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise SystemExit("catalogue has duplicate ids: %s" % sorted(dup))
    return cat


def load_referrals(repo: Path) -> dict:
    """integrations/referrals.toml: public sign-up links of paid services. Missing file = no services (plain installs keep working)."""
    p = repo / "integrations" / "referrals.toml"
    return load_toml(p) if p.is_file() else {"service": [], "no_referral": []}


def signup_options(ref: dict, entry_id: str, plain_only: bool = False) -> list:
    """Sign-up choices for one catalogue entry. A referral link is offered only when it is a non-empty https URL, and it is always labelled."""
    out = []
    for sv in ref.get("service", []):
        if entry_id not in sv.get("entries", []):
            continue
        r = (sv.get("referral_url") or "").strip()
        out.append({"service": sv.get("name") or sv["id"], "plain_url": sv["plain_url"],
                    "referral_url": r if (r.startswith("https://") and not plain_only) else None})
    return out


def all_addons(cat: dict) -> list:
    s = set()
    for e in cat.get("entry", []):
        s.update(e.get("addons", []))
    return sorted(s)


def select_entries(cat: dict, profile: str, addons, engine: str, targets=()) -> list:
    tags = set(LEVELS[profile])
    out = []
    for e in cat.get("entry", []):
        if e.get("host"):
            if e["host"] in targets:
                out.append(e)
            continue
        if e.get("group") == "engine":
            if engine != "none":
                out.append(e)
            continue
        ps = set(e.get("profiles", []))
        if "core" in ps or ps & tags or set(e.get("addons", [])) & set(addons):
            out.append(e)
    return out


# ----------------------------------------------------------------------------- layout
class Layout:
    def __init__(self, scope, project_dir, state_dir, home, claude_skills, codex_skills, claude_md, codex_md, work_root):
        self.scope, self.project_dir, self.state_dir, self.toolkit_home = scope, project_dir, state_dir, home
        self.claude_skills, self.codex_skills, self.claude_md, self.codex_md, self.work_root = claude_skills, codex_skills, claude_md, codex_md, work_root

    @property
    def manifest(self) -> Path:
        return self.state_dir / "install-manifest.json"

    def as_dict(self) -> dict:
        return {"scope": self.scope, "project_dir": str(self.project_dir) if self.project_dir else None, "state_dir": str(self.state_dir),
                "toolkit_home": str(self.toolkit_home), "claude_skills": str(self.claude_skills), "codex_skills": str(self.codex_skills),
                "claude_md": str(self.claude_md), "codex_md": str(self.codex_md), "work_root": str(self.work_root)}


def ascii_fallback(name: str) -> Path:
    """An ASCII-only folder that needs no admin rights, used when the home path has non-ASCII letters (Hebrew user names are common).
    Windows: C:/<name>. macOS: /Users/Shared is writable by every user. Linux: /var/tmp survives reboots.
    ``AVC_ASCII_BASE`` overrides the base folder (tests, unusual setups)."""
    base = os.environ.get("AVC_ASCII_BASE")
    if base:
        return Path(base) / name
    sysname = os_name()
    if sysname == "windows":
        return Path("C:/") / name
    if sysname == "macos":
        return Path("/Users/Shared") / name
    return Path("/var/tmp") / name


def default_work_root(h: Path) -> Path:
    env = os.environ.get("AVC_PATHS_WORK_ROOT") or os.environ.get("AVC_WORK_ROOT")  # canonical name per toolkit.toml, plus the short alias
    if env:
        return Path(env)
    if is_ascii_path(h):
        return h / "avc-work"
    # Non-ASCII home: HyperFrames `init` needs an ASCII work root. The student may pass --work-root instead.
    return ascii_fallback("avc-work")


def default_toolkit_home(state: Path) -> Path:
    """The toolkit home holds node_modules (the HyperFrames engine). Under a non-ASCII path `hyperframes init` ends WITHOUT an error and
    WITHOUT index.html (verified live 2026-10-03), so a non-ASCII default is replaced by an ASCII folder instead of only warning."""
    home = state / "toolkit"
    return home if is_ascii_path(home) else ascii_fallback("avc-toolkit")


def make_layout(args) -> Layout:
    h = user_home()
    if args.scope == "project":
        proj = Path(args.project_dir or os.getcwd()).resolve()
        state = Path(args.state_dir) if args.state_dir else proj / ".avc"
        home = Path(args.home) if args.home else default_toolkit_home(state)
        lay = Layout("project", proj, state, home, proj / ".claude" / "skills", proj / ".agents" / "skills", proj / "CLAUDE.md", proj / "AGENTS.md", None)
    else:
        state = Path(args.state_dir) if args.state_dir else h / ".avc"
        home = Path(args.home) if args.home else default_toolkit_home(state)
        lay = Layout("user", None, state, home, h / ".claude" / "skills", h / ".agents" / "skills", h / ".claude" / "CLAUDE.md", h / ".codex" / "AGENTS.md", None)
    lay.work_root = Path(args.work_root) if args.work_root else default_work_root(h)
    return lay


# ----------------------------------------------------------------------------- enumerating repo content
def _excluded(rel_parts, name: str) -> bool:
    return name in EXCLUDE_NAMES or name.endswith(EXCLUDE_SUFFIXES) or any(p in EXCLUDE_NAMES for p in rel_parts)


def enumerate_tree(root: Path, base: Path, skipped: list) -> dict:
    """rel (posix) -> (abs path, size, sha256) for files under root (relative to base). Symlinks are skipped."""
    out = {}
    if root.is_file():
        files = [root]
    else:
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if not _excluded((), d))
            for fn in sorted(filenames):
                if not _excluded((), fn):
                    files.append(Path(dirpath) / fn)
    for f in files:
        if f.is_symlink():
            skipped.append("symlink skipped: %s" % f)
            continue
        rel = f.relative_to(base).as_posix()
        out[rel] = (f, f.stat().st_size, sha256_file(f))
    return out


def enumerate_skills(repo: Path, skipped: list) -> dict:
    sdir = repo / "agent-content" / "skills"
    skills = {}
    if not sdir.is_dir():
        return skills
    for d in sorted(sdir.iterdir()):
        if d.is_dir() and (d / "SKILL.md").is_file() and not d.name.startswith((".", "_")):
            skills[d.name] = enumerate_tree(d, d, skipped)
    return skills


def enumerate_toolkit(repo: Path, skipped: list, setup: Path | None = None) -> dict:
    """Files of the managed toolkit home: the editing repo (``repo``) plus the installer/integrations of the setup repo (``setup``)."""
    out = {}
    for inc in TOOLKIT_INCLUDE:
        p = repo / inc
        if p.exists():
            out.update(enumerate_tree(p, repo, skipped))
    base = setup if setup is not None else repo
    for inc in SETUP_INCLUDE:
        p = base / inc
        if p.exists():
            out.update(enumerate_tree(p, base, skipped))
    return out


def resolve_toolkit_src(args) -> tuple:
    """Where the skills and tools are. Returns (path|None, how). Order: --toolkit-src > AVC_TOOLKIT_SRC > this repository."""
    cands = []
    if getattr(args, "toolkit_src", None):
        cands.append((Path(args.toolkit_src), "--toolkit-src"))
    if os.environ.get("AVC_TOOLKIT_SRC"):
        cands.append((Path(os.environ["AVC_TOOLKIT_SRC"]), "AVC_TOOLKIT_SRC"))
    cands.append((REPO, "this repository"))
    for path, how in cands:
        if (path / "agent-content" / "skills").is_dir():
            return path.resolve(), how
    return None, "not found"


def parse_frontmatter(text: str) -> dict:
    """Tiny YAML-subset reader: top-level `key: value` and folded/literal blocks. Enough for name/description."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return {}
    out, key, buf = {}, None, []
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if km and not line.startswith((" ", "\t")):
            if key:
                out[key] = " ".join(buf).strip()
            key, val = km.group(1), km.group(2).strip()
            buf = [] if val in (">", ">-", "|", "|-", "") else [val.strip("'\"")]
        elif key:
            buf.append(line.strip())
    if key:
        out[key] = " ".join(buf).strip()
    return out


def lint_skill(name: str, files: dict) -> list:
    problems = []
    sk = files.get("SKILL.md")
    if not sk:
        return ["SKILL.md missing"]
    fm = parse_frontmatter(sk[0].read_text(encoding="utf-8", errors="replace"))
    if fm.get("name") != name:
        problems.append("frontmatter name %r != folder %r" % (fm.get("name"), name))
    if not fm.get("description"):
        problems.append("frontmatter description missing")
    elif len(fm["description"]) > 1024:
        problems.append("description longer than 1024 chars")
    return problems


# ----------------------------------------------------------------------------- manifest + journal
def load_manifest(lay: Layout) -> dict:
    return read_json(lay.manifest, None) or {}


class Journal:
    """Records every filesystem change of one apply run so `rollback` can undo it."""

    def __init__(self, lay: Layout, stamp: str, dry: bool):
        self.dir, self.stamp, self.dry = lay.state_dir / "backups" / stamp, stamp, dry
        self.entries = []
        self.manifest_before = "UNSET"  # set by apply: previous manifest dict, or None on a first install

    def backup_file(self, src: Path, label: str, rel: str):
        dest = self.dir / label / rel
        if not self.dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        return dest

    def record(self, op: str, path: Path, backup: Path | None = None, extra=None):
        self.entries.append({"op": op, "path": str(path), "backup": str(backup) if backup else None, "extra": extra})

    def flush(self):
        if self.dry or not self.entries:
            return
        if self.manifest_before != "UNSET" and not (self.dir / "manifest-before.json").exists():
            atomic_write_json(self.dir / "manifest-before.json", self.manifest_before)
        atomic_write_json(self.dir / "journal.json", {"stamp": self.stamp, "entries": self.entries, "bootstrap_version": BOOTSTRAP_VERSION})


def copy_atomic(src: Path, dest: Path) -> str:
    """Copy src to dest atomically and return the sha256 of the bytes actually written (the source may be edited while we run)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".avc-tmp-%d" % os.getpid())
    h = hashlib.sha256()
    with open(src, "rb") as fi, open(tmp, "wb") as fo:
        for chunk in iter(lambda: fi.read(1 << 20), b""):
            h.update(chunk)
            fo.write(chunk)
    os.replace(tmp, dest)
    return h.hexdigest()


def sync_files(src_files: dict, dest_root: Path, old_hashes: dict, journal: Journal, label: str, dry: bool, exclude_rel=()) -> dict:
    """Make dest_root contain exactly src_files (for files we own). Back up anything replaced/removed.
    Returns {"hashes": {rel: sha}, "created": n, "updated": n, "unchanged": n, "removed": n}."""
    stats = {"created": 0, "updated": 0, "unchanged": 0, "removed": 0}
    hashes = {}
    for rel, (sp, _size, sha) in src_files.items():
        dp = dest_root / rel
        hashes[rel] = sha
        if dp.is_file() and not dp.is_symlink():
            if sha256_file(dp) == sha:
                stats["unchanged"] += 1
                continue
            b = journal.backup_file(dp, label, rel)
            journal.record("replace", dp, b)
            stats["updated"] += 1
        else:
            journal.record("create", dp)
            stats["created"] += 1
        if not dry:
            hashes[rel] = copy_atomic(sp, dp) or sha  # record what was really written
    for rel in sorted(set(old_hashes) - set(src_files)):
        dp = dest_root / rel
        if dp.is_file():
            b = journal.backup_file(dp, label, rel)
            journal.record("delete", dp, b)
            stats["removed"] += 1
            if not dry:
                dp.unlink()
    journal.flush()
    stats["hashes"] = hashes
    return stats


def prune_empty_dirs(root: Path) -> None:
    if not root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        p = Path(dirpath)
        if p != root and not any(p.iterdir()):
            try:
                p.rmdir()
            except OSError:
                pass


# ----------------------------------------------------------------------------- host + prerequisite detection
def detect_host() -> dict:
    h = user_home()
    shell = "posix-shell" if os.environ.get("SHELL") else "powershell-or-cmd"
    if os.environ.get("MSYSTEM"):
        shell = "git-bash"
    return {"os": os_name(), "platform": sys.platform, "arch": os.environ.get("PROCESSOR_ARCHITECTURE") or os.uname().machine if hasattr(os, "uname") else os.environ.get("PROCESSOR_ARCHITECTURE", "unknown"),
            "python": sys.version.split()[0], "python_executable": sys.executable, "shell_hint": shell,
            "home": str(h), "home_ascii": is_ascii_path(h), "home_has_space": " " in str(h), "repo": str(REPO), "repo_ascii": is_ascii_path(REPO)}


def parse_version(text: str):
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    return tuple(int(x) if x else 0 for x in m.groups()) if m else None


def version_ge(have, need: str) -> bool:
    n = parse_version(need)
    return bool(have and n and have >= n)


def find_in_search_paths(entry: dict):
    """Apps such as Blender are often installed but NOT on PATH: look in the catalogue's default install folders (newest first)."""
    import glob

    for pat in entry.get("search_paths", []):
        hits = sorted(glob.glob(os.path.expanduser(pat)), reverse=True)
        hits = [h for h in hits if os.path.isfile(h)]
        if hits:
            return hits[0]
    return None


def probe_cli(entry: dict) -> dict:
    binary = entry.get("binary") or entry["id"]
    path = which(binary) or find_in_search_paths(entry)
    if path and not which(binary):
        binary = path  # found in its default install folder: run it by full path
    res = {"id": entry["id"], "kind": entry["kind"], "binary": binary, "found": bool(path), "path": path, "version": None, "ok": False, "min_version": entry.get("min_version")}
    if not path:
        return res
    va = entry.get("version_argv", ["--version"])
    p = run_cmd([binary] + list(va), timeout=25)
    txt = (p.stdout or "") + "\n" + (p.stderr or "")
    first = next((l for l in txt.splitlines() if l.strip()), "")
    v = parse_version(first) or parse_version(txt)
    res["version"] = ".".join(str(x) for x in v) if v else (first[:60] or None)
    res["ok"] = bool(p.ok or v)
    if entry.get("min_version") and res["ok"]:
        res["ok"] = version_ge(v, entry["min_version"])
        if not res["ok"]:
            res["note"] = "version %s is older than required %s" % (res["version"], entry["min_version"])
    return res


def ffmpeg_mini_encode() -> dict:
    """Real mini-encode (H.264 + AAC) then ffprobe it. A listed encoder alone proves nothing."""
    if not which("ffmpeg") or not which("ffprobe"):
        return {"state": "not_run", "evidence": "ffmpeg and/or ffprobe not on PATH"}
    tmp = Path(tempfile.mkdtemp(prefix="avc-probe-"))
    out = tmp / "probe.mp4"
    try:
        p = run_cmd(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=1",
                     "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)], timeout=90)
        if not p.ok or not out.is_file():
            return {"state": "fail", "evidence": "mini-encode failed: %s" % ((p.stderr or p.error or "").strip()[:300])}
        q = run_cmd(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,codec_type", "-show_entries", "format=duration", "-of", "json", str(out)], timeout=30)
        data = json.loads(q.stdout or "{}") if q.ok else {}
        codecs = {s.get("codec_type"): s.get("codec_name") for s in data.get("streams", [])}
        dur = float(data.get("format", {}).get("duration", 0) or 0)
        good = codecs.get("video") == "h264" and codecs.get("audio") == "aac" and 0.5 <= dur <= 2.0
        return {"state": "pass" if good else "fail", "evidence": "ffprobe: video=%s audio=%s duration=%.2fs" % (codecs.get("video"), codecs.get("audio"), dur)}
    except (OSError, ValueError) as e:
        return {"state": "fail", "evidence": "probe error: %s" % e}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def install_hint(entry: dict) -> dict:
    inst = (entry.get("install") or {}).get(os_name()) or {}
    return {"command": inst.get("command"), "status": inst.get("status", "unverified"), "source": inst.get("source"), "checked": inst.get("checked"),
            "note": inst.get("note"), "manual": inst.get("manual")}


def package_manager_for(cmd: str):
    if not cmd:
        return None
    first = cmd.split()[0]
    return first if first in ("winget", "brew") else None


# ----------------------------------------------------------------------------- MCP planning / registration
def fill(value, ctx: dict):
    if isinstance(value, str):
        for k, v in ctx.items():
            value = value.replace("{" + k + "}", str(v))
        return value
    if isinstance(value, list):
        return [fill(v, ctx) for v in value]
    return value


def claude_add_argv(entry: dict, scope: str, ctx: dict) -> list:
    m, name = entry["mcp"], entry["mcp"].get("name", entry["id"])
    argv = ["claude", "mcp", "add", "--scope", scope]
    if m["transport"] == "http":
        argv += ["--transport", "http", name, fill(m["url"], ctx)]
        return argv
    argv += ["--transport", "stdio"]
    for k, v in (m.get("env") or {}).items():
        argv += ["--env", "%s=%s" % (k, fill(v, ctx))]
    cmdline = [m["command"]] + fill(m.get("args", []), ctx)
    if os_name() == "windows" and m["command"] in ("npx", "npm"):
        cmdline = ["cmd", "/c"] + cmdline  # native Windows needs the cmd /c wrapper for npx-based stdio servers
    argv += [name, "--"] + cmdline
    return argv


def codex_add_argv(entry: dict, ctx: dict) -> list:
    m, name = entry["mcp"], entry["mcp"].get("name", entry["id"])
    if m["transport"] == "http":
        return ["codex", "mcp", "add", name, "--url", fill(m["url"], ctx)]
    argv = ["codex", "mcp", "add", name]
    for k, v in (m.get("env") or {}).items():
        argv += ["--env", "%s=%s" % (k, fill(v, ctx))]
    cmdline = [m["command"]] + fill(m.get("args", []), ctx)
    if os_name() == "windows" and m["command"] in ("npx", "npm"):
        cmdline = ["cmd", "/c"] + cmdline  # [SOURCED-unverified for Codex on native Windows]
    return argv + ["--"] + cmdline


def mcp_names(client: str, lay: Layout, scope_dir) -> set | None:
    """Names of MCP servers the client already knows. None = could not ask."""
    if not which(client):
        return None
    p = run_cmd([client, "mcp", "list"], cwd=scope_dir, timeout=120)
    if not p.ok:
        return None
    names = set()
    for line in p.stdout.splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*[:\s]", line)
        if m and not line.lower().startswith(("checking", "no mcp", "name", "-")):
            names.add(m.group(1))
    return names


# ----------------------------------------------------------------------------- user instruction file block (optional, consented)
def render_block(lay: Layout, eol="\n") -> str:
    body = [MD_BEGIN,
            "AI Video Editing Toolkit is installed (managed by install/bootstrap.py; remove with `bootstrap.py uninstall`).",
            "Toolkit root: %s" % lay.toolkit_home,
            "Skills mention paths like agent-content/playbooks/..., tools/..., fixtures/...: they are relative to the toolkit root above.",
            "Entry skill for any video request: video-request-router. Invariant rules: <toolkit root>/AGENTS.md.",
            "To connect a service the student asks for (for example ElevenLabs, Higgsfield, Tripo): run `python <toolkit root>/install/bootstrap.py add <name>` and show the sign-up links exactly as printed (a referral link is labelled; open nothing without a yes).",
            MD_END]
    return eol.join(body)


def upsert_block(path: Path, block: str, journal: Journal, dry: bool, label: str) -> str:
    existing = path.read_bytes().decode("utf-8", errors="replace") if path.is_file() else ""  # bytes: keep CRLF exactly
    eol = "\r\n" if "\r\n" in existing else "\n"
    block = block.replace("\n", eol) if eol != "\n" else block
    if MD_BEGIN in existing and MD_END in existing:
        pre, rest = existing.split(MD_BEGIN, 1)
        _, post = rest.split(MD_END, 1)
        new = pre + block + post
    else:
        new = existing + ("" if not existing or existing.endswith(("\n",)) else eol) + (eol if existing else "") + block + eol
    if new == existing:
        return "unchanged"
    if path.is_file():
        b = journal.backup_file(path, label, path.name)
        journal.record("replace", path, b)
    else:
        journal.record("create", path)
    if not dry:
        atomic_write_text(path, new)
    journal.flush()
    return "updated" if existing else "created"


def remove_block(path: Path, journal: Journal, dry: bool, label: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_bytes().decode("utf-8", errors="replace")
    if MD_BEGIN not in text or MD_END not in text:
        return False
    pre, rest = text.split(MD_BEGIN, 1)
    _, post = rest.split(MD_END, 1)
    eol = "\r\n" if "\r\n" in text else "\n"
    new = (pre.rstrip("\r\n") + (eol if pre.strip() else "") + post.lstrip("\r\n")) if (pre.strip() or post.strip()) else ""
    b = journal.backup_file(path, label, path.name)
    journal.record("replace", path, b)
    if not dry:
        if new.strip():
            atomic_write_text(path, new)
        else:
            path.unlink()
    journal.flush()
    return True


# ----------------------------------------------------------------------------- locking
class Lock:
    def __init__(self, lay: Layout, dry: bool, break_lock: bool):
        self.path, self.dry, self.break_lock, self.held = lay.state_dir / "install.lock", dry, break_lock, False

    def __enter__(self):
        if self.dry:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            age = time.time() - self.path.stat().st_mtime
            if self.break_lock or age > 2 * 3600:
                self.path.unlink()
            else:
                raise SystemExit("another install is running (lock %s, %.0f s old). Wait, or pass --break-lock if you are sure." % (self.path, age))
        fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, ("pid=%d at=%s\n" % (os.getpid(), now_utc())).encode())
        os.close(fd)
        self.held = True
        return self

    def __exit__(self, *a):
        if self.held:
            try:
                self.path.unlink()
            except OSError:
                pass


# ----------------------------------------------------------------------------- plan
# ----------------------------------------------------------------------------- hardware detection + automatic route choice
# Nobody is asked about their hardware: the installer looks and picks the one route that works everywhere (CPU).
GPU_RULES = [("NVIDIA", ("nvidia", "geforce", "quadro", "rtx ", "gtx ", "tesla")), ("AMD", ("amd", "radeon", "advanced micro devices")),
             ("Intel", ("intel", "iris", "uhd graphics", "arc ")), ("Apple", ("apple",)),
             ("virtual", ("microsoft basic", "hyper-v", "vmware", "virtualbox", "qxl", "virtio", "parallels", "llvmpipe"))]
MIN_FREE_DISK_BLOCK = 1 * 1024 ** 3   # installer's own safety margins - NOT measured requirements
MIN_FREE_DISK_WARN = 10 * 1024 ** 3
RAM_RECOMMENDED = 16 * 1024 ** 3      # instructor recommendation (cloud-assisted profile), not a measured minimum


def normalize_arch(machine: str) -> str:
    m = (machine or "").lower()
    if m in ("amd64", "x86_64", "x64"):
        return "x64"
    if m in ("arm64", "aarch64"):
        return "arm64"
    return m or "unknown"


def classify_gpu(name: str) -> str:
    low = (name or "").lower() + " "
    for vendor, keys in GPU_RULES:
        if any(k in low for k in keys):
            return vendor
    return "unknown"


def parse_gpu_names(text: str) -> list:
    out = []
    for line in (text or "").splitlines():
        n = line.strip()
        if n and n.lower() not in ("name", "no instance(s) available.") and not n.startswith("-"):
            out.append({"name": n[:120], "vendor": classify_gpu(n)})
    return out


def detect_ram_bytes():
    try:
        if os_name() == "windows":
            import ctypes

            class MemStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            st = MemStatus()
            st.dwLength = ctypes.sizeof(MemStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))  # type: ignore[attr-defined]
            return int(st.ullTotalPhys) or None
        if os_name() == "macos":
            p = run_cmd(["sysctl", "-n", "hw.memsize"], timeout=10)
            return int(p.stdout.strip()) if p.ok and p.stdout.strip().isdigit() else None
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, AttributeError, ImportError):
        pass
    return None


def detect_gpus(arch: str) -> list:
    """Read-only probes (all through run_cmd). Unknown is a valid answer: the CPU route works either way."""
    osn = os_name()
    gpus = []
    if osn == "windows":
        p = run_cmd(["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"], timeout=40)
        gpus = parse_gpu_names(p.stdout) if p.ok else []
        if not gpus:
            q = run_cmd(["wmic", "path", "win32_VideoController", "get", "name"], timeout=30)
            gpus = parse_gpu_names(q.stdout) if q.ok else []
    elif osn == "macos":
        if arch == "arm64":
            gpus = [{"name": "Apple Silicon (integrated)", "vendor": "Apple"}]
        else:
            p = run_cmd(["system_profiler", "SPDisplaysDataType"], timeout=40)
            names = [m.group(1) for m in re.finditer(r"Chipset Model:\s*(.+)", p.stdout or "")] if p.ok else []
            gpus = parse_gpu_names("\n".join(names))
    else:
        if which("lspci"):
            p = run_cmd(["lspci"], timeout=20)
            lines = [l.split(":", 2)[-1] for l in (p.stdout or "").splitlines() if re.search(r"VGA|3D|Display", l)] if p.ok else []
            gpus = parse_gpu_names("\n".join(lines))
        if not gpus and which("nvidia-smi"):
            p = run_cmd(["nvidia-smi", "-L"], timeout=20)
            gpus = parse_gpu_names("\n".join(l.split(":", 1)[-1].split("(UUID")[0] for l in (p.stdout or "").splitlines())) if p.ok else []
    return gpus


def detect_hardware(disk_probe_path: Path) -> dict:
    arch = normalize_arch(platform_machine())
    probe = disk_probe_path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        free = shutil.disk_usage(str(probe)).free
    except OSError:
        free = None
    gpus = detect_gpus(arch)
    return {"os": os_name(), "arch": arch, "cpu_logical": os.cpu_count(), "ram_bytes": detect_ram_bytes(), "free_disk_bytes": free,
            "disk_checked_at": str(probe), "gpus": gpus, "gpu_vendors": sorted({g["vendor"] for g in gpus})}


def platform_machine() -> str:
    import platform
    return platform.machine()


def choose_routes(hw: dict) -> dict:
    """Pure function. One transcription route (CPU) that works on every machine; nothing is probed, listed or offered beyond it."""
    return {
        "asr": {"chosen": "asr-cpu", "why": "works on every machine (faster-whisper int8 on CPU); weights are NOT downloaded until you approve their size"},
        "matte": {"chosen": "native-cpu", "why": "`hyperframes remove-background` runs on the CPU everywhere with no extra install; a faster route is opt-in (`add matte-fast`, licence note) and is not recommended automatically"},
        "encoder": {"chosen": "libx264 (CPU)", "why": "verified by the real mini-encode; hardware encoders are never trusted from a list"},
        "never_required": ["matte-fast"],
    }


def hardware_findings(hw: dict) -> tuple:
    """(warnings, blockers) from the detected hardware. Thresholds are the installer's safety margins, not measured requirements."""
    warn, block = [], []
    free = hw.get("free_disk_bytes")
    if free is not None and free < MIN_FREE_DISK_BLOCK:
        block.append("only %s free on the install drive; free some space (installer safety margin: 1 GB; real needs are unmeasured)" % human_bytes(free))
    elif free is not None and free < MIN_FREE_DISK_WARN:
        warn.append("only %s free on the install drive; model weights and renders need much more (unmeasured)" % human_bytes(free))
    ram = hw.get("ram_bytes")
    if ram is not None and ram < RAM_RECOMMENDED:
        warn.append("%s RAM is below the instructor-recommended 16 GB (a recommendation, not a measured minimum): the install works, heavy steps may be slow or fail" % human_bytes(ram))
    if hw.get("arch") not in ("x64", "arm64"):
        warn.append("CPU architecture %r is unusual; some Python wheels / Node binaries may be unavailable [unmeasured]" % hw.get("arch"))
    elif hw.get("arch") == "arm64" and hw.get("os") != "macos":
        warn.append("arm64 %s is unmeasured for this toolkit; some wheels or engine binaries may be missing (CPU routes are still the plan)" % hw.get("os"))
    if hw.get("gpus") and all(g["vendor"] in ("virtual", "unknown") for g in hw["gpus"]):
        warn.append("no usable GPU detected (virtual or unknown adapter): CPU routes only - this is fine and fully supported")
    return warn, block


def resolve_targets(args, lay: Layout) -> list:
    t = args.target
    if t == "both":
        return ["claude", "codex"]
    if t in ("claude", "codex"):
        return [t]
    found = []
    h = user_home()
    if which("claude") or (h / ".claude").is_dir():
        found.append("claude")
    if which("codex") or (h / ".codex").is_dir() or (h / ".agents").is_dir():
        found.append("codex")
    return found or ["claude"]


def skill_status(name: str, files: dict, dest_dir: Path, manifest: dict, target: str) -> dict:
    mine = (manifest.get("skills", {}).get(name, {}).get("targets", {}) or {}).get(target)
    marker = read_json(dest_dir / MARKER, None) if dest_dir.is_dir() else None
    ours = bool(mine) or bool(marker and marker.get("managed_by") == "editing-workflow")
    if not dest_dir.exists():
        return {"status": "new", "dest": str(dest_dir)}
    if not ours:
        return {"status": "conflict-foreign", "dest": str(dest_dir), "note": "a skill with this name already exists and was not created by this toolkit"}
    cur_same = all((dest_dir / rel).is_file() and sha256_file(dest_dir / rel) == sha for rel, (_p, _s, sha) in files.items())
    return {"status": "unchanged" if cur_same else "update", "dest": str(dest_dir)}


# ----------------------------------------------------------------------------- skills as a Claude Code plugin
PLUGIN_NAME = "editing-workflow"
PLUGIN_ID = "editing-workflow@editing-workflow"  # <plugin>@<marketplace>, both named in .claude-plugin/marketplace.json
PLUGIN_SOURCE = "Malik-rgb43/editing-workflow"  # the public repository that carries .claude-plugin/marketplace.json


def plugin_mode(args, targets) -> bool:
    """Claude Code gets the skills as a plugin (one place, updated by Claude Code, removed cleanly) unless the student asked for plain copies."""
    return "claude" in targets and getattr(args, "skills_via", "plugin") == "plugin" and not args.skip_skills


def copy_targets_for(args, targets) -> list:
    """Targets that receive copied skill folders: Codex always, Claude only when it does not use the plugin."""
    pm = plugin_mode(args, targets)
    return [t for t in targets if not (t == "claude" and pm)]


def plugin_state() -> dict:
    """What Claude Code says about the plugin. ``available`` is False when `claude` cannot be asked (not on PATH or the call failed)."""
    if not which("claude"):
        return {"available": False, "why": "`claude` is not on PATH"}
    lp = run_cmd(["claude", "plugin", "list", "--json"], timeout=60)
    lm = run_cmd(["claude", "plugin", "marketplace", "list", "--json"], timeout=60)
    if not lp.ok or not lm.ok:
        return {"available": False, "why": ((lp.stderr or lp.error or lm.stderr or lm.error or "").strip()[:200]) or "claude plugin list failed"}
    try:
        plugins, markets = json.loads(lp.stdout or "[]"), json.loads(lm.stdout or "[]")
    except ValueError:
        return {"available": False, "why": "claude plugin list did not return JSON (old Claude Code?)"}
    mine = [x for x in plugins if x.get("id") == PLUGIN_ID]
    return {"available": True, "installed": bool(mine), "enabled": bool(mine and mine[0].get("enabled", True)), "version": (mine[0].get("version") if mine else None),
            "marketplace": any(x.get("name") == PLUGIN_NAME for x in markets)}


def plugin_stage(c: dict, args, dry: bool, manifest: dict) -> str:
    if not plugin_mode(args, c["targets"]):
        return "not used (skills are copied into the skills folder)" if "claude" in c["targets"] else "not used (Claude Code is not a target)"
    src = getattr(args, "plugin_source", None) or PLUGIN_SOURCE
    by_hand = "by hand: claude plugin marketplace add %s ; claude plugin install %s" % (src, PLUGIN_ID)
    if args.offline:
        return "deferred (offline); " + by_hand
    st = plugin_state()
    if not st["available"]:
        return "not run: %s. %s" % (st["why"], by_hand)
    if st["installed"]:
        manifest.setdefault("plugin", {"id": PLUGIN_ID, "source": src, "marketplace_added_by_installer": False, "scope": "user"})
        return "unchanged (already installed, version %s)" % st.get("version")
    cmds = ([] if st["marketplace"] else [["claude", "plugin", "marketplace", "add", src]]) + [["claude", "plugin", "install", PLUGIN_ID, "--scope", "user"]]
    if dry:
        return "would run: " + " ; ".join(" ".join(x) for x in cmds)
    for argv in cmds:
        r = run_cmd(argv, timeout=300)
        if not r.ok:
            return "FAILED rc=%s: %s. %s" % (r.returncode, (r.stderr or r.error or r.stdout or "").strip()[-300:], by_hand)
    manifest["plugin"] = {"id": PLUGIN_ID, "source": src, "marketplace_added_by_installer": not st["marketplace"], "scope": "user", "installed_at": now_utc()}
    return "ok (skills appear as %s:<skill>; start a new Claude Code session)" % PLUGIN_NAME


def mcp_row(e: dict, targets, lay: Layout, existing: dict, ctx: dict, mcp_scope: str) -> dict:
    m = e["mcp"]
    name = m.get("name", e["id"])
    row = {"id": e["id"], "name": name, "transport": m["transport"], "auth": m.get("auth", "none"), "env_var": m.get("env_var"), "cost": e.get("cost"),
           "register": m.get("register", "manual"), "avoid": e.get("avoid", False), "targets": {}, "next_by_hand": m.get("by_hand"),
           "verified": m.get("status", "unverified"), "source": m.get("source"), "gate": e.get("gate")}
    if e.get("avoid"):
        row["register"] = "never"
    for t in targets:
        argv = claude_add_argv(e, mcp_scope, ctx) if t == "claude" else codex_add_argv(e, ctx)
        ex = existing.get(t)
        names = [name] + list(m.get("existing_names", []))
        if row["register"] != "auto":
            status = "manual" if row["register"] == "manual" else "never"
        elif ex is not None and any(n in ex for n in names):
            status = "already-registered"
        elif not which(t):
            status = "skipped-cli-missing"
        elif t == "codex" and lay.scope == "project":
            status = "manual"  # `codex mcp add` writes the USER config; a project-scope install must not mutate it
        elif t == "codex" and (m["transport"] == "http" or not m.get("codex_auto", False)):
            status = "manual"  # `codex mcp add --url` is not in the official docs we could read; a config.toml snippet is used instead
        else:
            status = "will-register"
        row["targets"][t] = {"status": status, "argv": argv}
    return row


def build_plan(args, repo=None) -> tuple:
    repo = repo or REPO
    lang = args.lang
    cat = load_catalog(repo)
    lay = make_layout(args)
    manifest = load_manifest(lay)
    skipped = []
    src, src_how = resolve_toolkit_src(args) if repo is REPO else (repo, "--repo")
    skills = enumerate_skills(src, skipped) if src else {}
    toolkit = enumerate_toolkit(src, skipped, setup=repo) if src else {}
    targets = resolve_targets(args, lay)
    addons = [a for a in (args.with_.split(",") if args.with_ else []) if a]
    known = all_addons(cat)
    warnings, blockers, conflicts = [], [], []
    unknown = [a for a in addons if a not in known]
    if unknown:
        blockers.append("unknown --with option(s): %s. Known: %s" % (", ".join(unknown), ", ".join(known)))
    host = detect_host()
    hw = detect_hardware(lay.state_dir)
    routes = choose_routes(hw)
    hw_warn, hw_block = hardware_findings(hw)
    warnings += hw_warn
    blockers += hw_block
    auto_addons = []
    if args.local and not hw_block and "asr-cpu" in known and "asr-cpu" not in addons:
        auto_addons.append("asr-cpu")  # only when the student chose to work locally (--local); the CPU route works on every machine
    entries = select_entries(cat, args.profile, [a for a in addons + auto_addons if a in known], args.engine, targets)

    if not host["home_ascii"]:
        warnings.append("Your home folder path contains non-ASCII characters (%s). Python/FFmpeg are fine, but HyperFrames `init` is not: keep every video project under an ASCII work root (below)." % host["home"])
    if not is_ascii_path(lay.work_root):
        blockers.append("work root %s is not ASCII-only; choose --work-root with ASCII characters only (e.g. C:\\avc-work or ~/avc-work)." % lay.work_root)
    if not is_ascii_path(lay.toolkit_home):
        blockers.append("toolkit home %s is not ASCII-only: `hyperframes init` would silently create empty projects there. Omit --home (the installer then picks an ASCII folder) or pass an ASCII --home." % lay.toolkit_home)
    elif not args.home and not is_ascii_path(lay.state_dir / "toolkit"):
        warnings.append("Your state folder path has non-ASCII letters, so the toolkit folder is %s instead of %s (HyperFrames needs an ASCII path). Skills still go to your home folder." % (lay.toolkit_home, lay.state_dir / "toolkit"))
    if plugin_mode(args, targets):
        dup = sorted(n for n in skills if (lay.claude_skills / n / MARKER).is_file())
        if dup:
            warnings.append("%d skill folder(s) installed earlier by this toolkit still exist in %s (for example %s). With the plugin they would load twice; run `python install/bootstrap.py uninstall --yes` first, or install again with --skills-via copy." % (len(dup), lay.claude_skills, dup[0]))
    if lay.scope == "project" and lay.project_dir and (lay.project_dir == repo or repo in lay.project_dir.parents or lay.project_dir in repo.parents and lay.project_dir == repo):
        blockers.append("--scope project must point at your own video project folder, not at the toolkit repo itself (%s)." % repo)
    if args.scope == "project" and not args.project_dir:
        warnings.append("--scope project without --project-dir: using the current directory %s" % lay.project_dir)
    if os_name() == "windows" and toolkit:
        longest = max(len(r) for r in toolkit) + len(str(lay.toolkit_home))
        if longest > 240:
            warnings.append("the longest toolkit path would be %d characters (Windows limit is about 260): pass a shorter --home, e.g. C:/avc/toolkit." % longest)
    if sys.version_info < (3, 12):
        warnings.append("Python %s is older than 3.12; the installer works, but the toolkit's own environment is created by uv (uv python install 3.12 is handled by `uv sync`)." % host["python"])

    # prerequisites
    prereqs = []
    for e in entries:
        if e["kind"] == "cli" and not e.get("managed_by"):
            r = probe_cli(e)
            r["required"] = "core" in e.get("profiles", [])
            r["install"] = install_hint(e)
            if e.get("download_size"):
                r["download_size"] = e["download_size"]
            r["role"] = e.get("role")
            prereqs.append(r)
    ff = ffmpeg_mini_encode()

    # skills
    pm = plugin_mode(args, targets)
    copy_targets = copy_targets_for(args, targets)
    skill_rows, n_bytes = [], 0
    for name, files in skills.items():
        row = {"name": name, "files": len(files), "bytes": sum(s for _p, s, _h in files.values()), "lint": lint_skill(name, files), "targets": {}}
        n_bytes += row["bytes"]
        for t in copy_targets:
            root = lay.claude_skills if t == "claude" else lay.codex_skills
            st = skill_status(name, files, root / name, manifest, t)
            row["targets"][t] = st
            if st["status"] == "conflict-foreign":
                conflicts.append("%s/%s: %s" % (t, name, st["note"]))
        skill_rows.append(row)
    if src is None:
        blockers.append("the skills and tools were not found next to the installer (agent-content/skills is missing). Re-download the editing-workflow repository completely, or pass --toolkit-src <path-to-a-complete-checkout>.")
    elif not skills:
        blockers.append("no skills found in %s/agent-content/skills/ - that checkout is incomplete. Nothing to install." % src)
    th_old = (manifest.get("toolkit_files") or {})
    th_stat = "new" if not lay.toolkit_home.exists() else ("unchanged" if th_old == {r: v[2] for r, v in toolkit.items()} else "update")

    # MCP
    ctx = {"work_root": str(lay.work_root), "state_dir": str(lay.state_dir), "toolkit_home": str(lay.toolkit_home), "browser_out": str(lay.work_root / "browser-output")}
    mcp_rows = []
    mcp_scope = "project" if lay.scope == "project" else "user"
    existing = {}
    for t in targets:
        existing[t] = mcp_names(t, lay, lay.project_dir if lay.scope == "project" else user_home()) if (args.command != "plan" or args.probe_mcp) else None
    for e in entries:
        if e["kind"] == "mcp":
            mcp_rows.append(mcp_row(e, targets, lay, existing, ctx, mcp_scope))
    if args.profile == "pro":
        warnings.append("Profile Pro adds nothing by itself: integrations are added one at a time with `python install/bootstrap.py add <id>` (see `add --list`).")

    api_rows = []
    for e in entries:
        var = (e.get("api") or {}).get("env_var") or (e.get("mcp") or {}).get("env_var")
        if var and not e.get("avoid"):  # presence only: the value is never read into the plan
            api_rows.append({"id": e["id"], "env_var": var, "present": var in os.environ, "cost": e.get("cost"), "terms": e.get("terms")})
    manual_rows = [{"id": e["id"], "kind": e["kind"], "name": e.get("name"), "note": e.get("security") or e.get("role"), "install": install_hint(e)}
                   for e in entries if e["kind"] == "native-plugin"]

    downloads = []
    if args.engine != "none":
        downloads.append({"what": "HyperFrames engine via npm (npm ci --ignore-scripts in the toolkit home)", "size": "unmeasured", "source": "registry.npmjs.org", "step": "npm"})
        downloads.append({"what": "Pinned Chrome Headless Shell via `hyperframes browser ensure` (separate explicit step)", "size": "a full browser download; size unmeasured on a student machine", "source": "Chrome-for-Testing hosts", "step": "browser"})
    downloads.append({"what": "Python 3.12 (only if missing) + project dependencies via `uv sync`", "size": "unmeasured", "source": "pypi.org, github.com/astral-sh (python-build-standalone)", "step": "uv"})
    for e in entries:
        if e["kind"] == "model":
            downloads.append({"what": "model weights: %s (NOT downloaded by bootstrap)" % e.get("name"), "size": e.get("download_size", "see catalogue"), "source": e.get("source_url"), "step": "manual"})
    network = sorted({"registry.npmjs.org", "pypi.org", "files.pythonhosted.org", "github.com"} | ({"winget/brew package sources"} if args.install_missing else set()))

    plan = {
        "schema": 1, "command": "plan", "bootstrap_version": BOOTSTRAP_VERSION, "generated_at": now_utc(), "host": host,
        "hardware": hw, "routes": routes,
        "questions": {"confirmation": "Shall I go ahead with this detected plan? (yes/no)",
                      "mode": "How do you want to work? LOCAL (everything runs on your computer, free: set up with --local), CONNECTED (you pick online services to connect, from a list), or BOTH? Ask this before the confirmation; it is a choice of how to work, not a question about hardware",
                      "optional": "AFTER the install works: short optional yes/no questions about connections (reference videos, stock media, UI components, AI generation, 3D, faster transcription), one at a time, default no - see INSTALL.md install-10. Nothing is installed or spent without a yes",
                      "hardware_questions": "none: hardware is detected, never asked"},
        "plugin": ({"used": True, "id": PLUGIN_ID, "source": getattr(args, "plugin_source", None) or PLUGIN_SOURCE, "scope": "user",
                    "what": "Claude Code adds the %s plugin (its %d skills) from the GitHub repository; nothing is copied into %s. To copy plain skill folders instead use --skills-via copy." % (PLUGIN_NAME, len(skills), lay.claude_skills)}
                   if pm else {"used": False}),
        "selection": {"profile": args.profile, "engine": args.engine, "local": bool(args.local), "skills_via": "plugin" if pm else "copy", "with": addons, "auto": auto_addons, "target": targets, "scope": lay.scope, "lang": lang,
                      "install_missing": bool(args.install_missing), "memory_block": bool(args.write_memory_block), "mcp": not args.skip_mcp},
        "paths": lay.as_dict(), "prerequisites": prereqs, "ffmpeg_mini_encode": ff,
        "skills": skill_rows, "skills_total_bytes": n_bytes,
        "toolkit_home": {"dest": str(lay.toolkit_home), "files": len(toolkit), "bytes": sum(v[1] for v in toolkit.values()), "status": th_stat},
        "mcp": mcp_rows, "api_keys_presence_only": api_rows, "by_hand_plugins": manual_rows,
        "downloads": downloads, "network": network,
        "cost": {"core": "none", "paid_actions_performed_by_installer": "none", "note": "Signing in to a provider is not spend authorisation; every generation goes through paid-spend-gate."},
        "conflicts": conflicts, "warnings": warnings + skipped[:5], "blockers": blockers, "catalog_checked_at": cat.get("meta", {}).get("checked_at"),
        "needs_confirmation": True,
    }
    ctx_obj = {"cat": cat, "lay": lay, "manifest": manifest, "skills": skills, "toolkit": toolkit, "targets": targets, "copy_targets": copy_targets, "entries": entries,
               "addons": addons + auto_addons, "mcp_scope": mcp_scope, "ctx": ctx, "plan": plan, "repo": repo, "existing_mcp": existing}
    return plan, ctx_obj


def render_plan(plan: dict, lang: str) -> str:
    L = lambda k: tr(lang, k)
    o = ["=" * 72, L("plan_title"), "=" * 72]
    h, s = plan["host"], plan["selection"]
    o += ["", "## " + L("host"), "  OS: %s (%s) | shell: %s | Python %s" % (h["os"], h["arch"], h["shell_hint"], h["python"]),
          "  home: %s  (ASCII: %s)" % (h["home"], h["home_ascii"])]
    hw = plan.get("hardware") or {}
    gpus = ", ".join("%s (%s)" % (g["name"], g["vendor"]) for g in hw.get("gpus", [])) or "none detected"
    o += ["  detected: arch=%s cpu_threads=%s ram=%s free_disk=%s gpu=%s" % (hw.get("arch"), hw.get("cpu_logical"), human_bytes(hw["ram_bytes"]) if hw.get("ram_bytes") else "unknown",
                                                                   human_bytes(hw["free_disk_bytes"]) if hw.get("free_disk_bytes") else "unknown", gpus)]
    rt = plan.get("routes") or {}
    if rt:
        o += ["", "## " + L("routes"), "  speech-to-text : %s  - %s" % (rt["asr"]["chosen"], rt["asr"]["why"]),
              "  speaker matte  : %s  - %s" % (rt["matte"]["chosen"], rt["matte"]["why"]), "  video encoder  : %s" % rt["encoder"]["chosen"]]
    o += ["", "## " + L("selection"), "  profile=%s  engine=%s  with=%s  target=%s  scope=%s" % (s["profile"], s["engine"], ",".join(s["with"]) or "-", ",".join(s["target"]), s["scope"])]
    p = plan["paths"]
    pl = plan.get("plugin") or {}
    claude_where = ("PLUGIN %s (from %s)" % (pl["id"], pl["source"])) if pl.get("used") else p["claude_skills"]
    o += ["  toolkit home : %s" % p["toolkit_home"], "  skills       : claude=%s | codex=%s" % (claude_where, p["codex_skills"]), "  work root    : %s" % p["work_root"], "  state/backups: %s" % p["state_dir"]]
    if pl.get("used"):
        o.append("  plugin       : %s" % pl["what"])
    o += ["", "## " + L("prereq")]
    for r in plan["prerequisites"]:
        flag = (L("ok") + " " + str(r["version"])) if r["found"] and r["ok"] else (L("missing") if not r["found"] else "FOUND-BUT-NOT-OK " + str(r.get("note", "")))
        o.append("  %-12s %s%s" % (r["id"], flag, "" if r["found"] else ("   -> " + str(r["install"]["command"] or r["install"].get("manual") or "see integrations/catalog.toml"))))
        if not r["found"] and r.get("download_size"):
            o.append("  %-12s download: %s" % ("", r["download_size"]))
    ff = plan["ffmpeg_mini_encode"]
    o.append("  ffmpeg real mini-encode: %s (%s)" % (ff["state"], ff["evidence"]))
    o += ["", "## %s (%d)" % (L("skills"), len(plan["skills"]))]
    for r in plan["skills"]:
        o.append("  %-30s %s" % (r["name"], " ".join("%s:%s" % (t, v["status"]) for t, v in r["targets"].items())))
    th = plan["toolkit_home"]
    o.append("  + shared toolkit home: %d files, %s (%s)" % (th["files"], human_bytes(th["bytes"]), th["status"]))
    o += ["", "## " + L("mcp")]
    if not plan["mcp"]:
        o.append("  " + L("none"))
    for r in plan["mcp"]:
        o.append("  %-22s %-5s auth=%-14s cost=%-10s %s" % (r["name"], r["transport"], r["auth"], r["cost"], " ".join("%s:%s" % (t, v["status"]) for t, v in r["targets"].items())))
    o += ["", "## " + L("downloads")]
    for d in plan["downloads"]:
        o.append("  - %s [%s] <- %s" % (d["what"], d["size"], d["source"]))
    o.append("  network hosts: " + ", ".join(plan["network"]))
    o += ["", "## " + L("cost"), "  " + L("cost_core")]
    for key in ("conflicts", "warnings", "blockers"):
        if plan[key]:
            o += ["", "## " + L(key)] + ["  - " + x for x in plan[key]]
    q = plan.get("questions") or {}
    o += ["", "Questions for the student: (0) " + q.get("mode", "") + "  (1) " + q.get("confirmation", "") + "  (2, optional) " + q.get("optional", "")]
    o += ["", L("confirm"), "  python install/bootstrap.py apply --profile %s --target %s --scope %s --yes" % (s["profile"], ",".join(s["target"]) if len(s["target"]) < 2 else "both", s["scope"])]
    return "\n".join(o)


# ----------------------------------------------------------------------------- link check
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
TOKEN = re.compile(r"`((?:%s)/[A-Za-z0-9_./\-]+)`" % "|".join(PATH_TOKEN_ROOTS))


def link_check(skill_dirs: dict, toolkit_home: Path) -> dict:
    """skill_dirs: name -> installed skill dir. Markdown links must resolve inside the bundle; toolkit-root path tokens must exist."""
    errors, warns, checked = [], [], 0
    for name, d in skill_dirs.items():
        for md in sorted(d.rglob("*.md")):
            text = md.read_text(encoding="utf-8", errors="replace")
            for raw in MD_LINK.findall(text):
                target = raw.split("#", 1)[0]
                if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith(("/", "#")):
                    continue
                checked += 1
                dest = (md.parent / target).resolve()
                try:
                    dest.relative_to(d.resolve())
                except ValueError:
                    inside_home = toolkit_home.exists() and str(dest).startswith(str(toolkit_home.resolve()))
                    errors.append("%s: link %r leaves the skill bundle (resolves to %s). Use a toolkit-root path in backticks or a link inside the skill folder." % (md.relative_to(d.parent).as_posix(), raw, "toolkit home" if inside_home else "outside"))
                    continue
                if not dest.exists():
                    errors.append("%s: broken link %r" % (md.relative_to(d.parent).as_posix(), raw))
            for tok in set(TOKEN.findall(text)):
                if any(c in tok for c in "*<>{}") or tok.startswith("agent-content/skills"):
                    continue  # patterns/placeholders; skills live in the host skill folders, not in the toolkit home
                checked += 1
                if not (toolkit_home / tok).exists():
                    warns.append("%s: toolkit path `%s` not found under the toolkit home (planned file, or typo)" % (md.relative_to(d.parent).as_posix(), tok))
    return {"checked": checked, "errors": sorted(set(errors)), "warnings": sorted(set(warns))}


# ----------------------------------------------------------------------------- apply
def stage(manifest: dict, name: str, status: str, detail: str = "") -> None:
    manifest.setdefault("stages", {})[name] = {"status": status, "at": now_utc(), "detail": detail[:500]}


def refuse(msg: str, code: int = EXIT_REFUSED):
    emit("REFUSED: " + msg, file=sys.stderr)
    return code


def cmd_apply(args) -> int:
    if not args.yes and not args.dry_run:
        return refuse("apply changes your computer. Review `plan`, get the student's ONE confirmation, then re-run with --yes (or --dry-run to preview).", EXIT_USAGE)
    plan, c = build_plan(args)
    lay, manifest, cat = c["lay"], c["manifest"], c["cat"]
    dry = bool(args.dry_run)
    if plan["blockers"]:
        emit(render_plan(plan, args.lang))
        return refuse("blockers present: " + "; ".join(plan["blockers"]))
    results, partial = {"mode": "dry-run" if dry else "apply", "stages": {}, "notes": [], "mcp": [], "skills": {}}, False
    stamp = ts_stamp()
    journal = Journal(lay, stamp, dry)
    journal.manifest_before = json.loads(json.dumps(manifest)) if manifest else None
    with Lock(lay, dry, args.break_lock):
        manifest.setdefault("schema", MANIFEST_SCHEMA)
        manifest.setdefault("installed_at", now_utc())
        manifest["updated_at"], manifest["bootstrap_version"] = now_utc(), BOOTSTRAP_VERSION
        manifest["toolkit_version"] = detect_toolkit_version(c["repo"])
        manifest["repo_source"] = {"path": str(c["repo"]), "git_commit": git_commit(c["repo"])}
        manifest["selection"], manifest["paths"] = plan["selection"], plan["paths"]
        manifest["catalog_checked_at"] = plan.get("catalog_checked_at")
        manifest.setdefault("backups", []).append({"stamp": stamp, "path": str(journal.dir)}) if not dry else None

        def save():
            if not dry:
                atomic_write_json(lay.manifest, manifest)

        # 1 toolkit home
        if not args.skip_skills:
            st = sync_files(c["toolkit"], lay.toolkit_home, manifest.get("toolkit_files", {}), journal, "toolkit", dry)
            manifest["toolkit_files"] = st["hashes"]
            results["stages"]["toolkit_home"] = {k: v for k, v in st.items() if k != "hashes"}
            stage(manifest, "toolkit_home", "ok")
            save()

            # 2 skills
            for name, files in c["skills"].items():
                results["skills"][name] = {}
                for t in c["copy_targets"]:
                    root = lay.claude_skills if t == "claude" else lay.codex_skills
                    dest = root / name
                    stt = skill_status(name, files, dest, manifest, t)
                    if stt["status"] == "conflict-foreign" and not args.force:
                        results["skills"][name][t] = "skipped-foreign (use --force to back up and replace)"
                        continue
                    old = ((manifest.get("skills", {}).get(name, {}).get("targets", {}) or {}).get(t) or {}).get("files", {})
                    try:
                        if stt["status"] == "conflict-foreign":  # --force: back up the whole foreign folder first
                            for f in sorted(dest.rglob("*")):
                                if f.is_file():
                                    journal.backup_file(f, "foreign-%s-%s" % (t, name), f.relative_to(dest).as_posix())
                            if not dry:
                                shutil.rmtree(dest)
                            journal.record("replace-dir", dest, journal.dir / ("foreign-%s-%s" % (t, name)))
                            old = {}
                        sst = sync_files(files, dest, old, journal, "skill-%s-%s" % (t, name), dry)
                        if not dry:
                            mk, prev = dest / MARKER, read_json(dest / MARKER, None)
                            meta = {"managed_by": "editing-workflow", "skill": name, "target": t, "toolkit_version": manifest["toolkit_version"],
                                    "toolkit_home": str(lay.toolkit_home), "installed_at": (prev or {}).get("installed_at") or now_utc(),
                                    "note": "Paths such as agent-content/..., tools/... inside this skill are relative to toolkit_home."}
                            if prev != meta:
                                if prev is None:
                                    journal.record("create", mk)
                                atomic_write_json(mk, meta)
                        manifest.setdefault("skills", {}).setdefault(name, {"targets": {}})["targets"][t] = {"dir": str(dest), "files": sst["hashes"]}
                        results["skills"][name][t] = "%s (+%d ~%d =%d -%d)" % (stt["status"], sst["created"], sst["updated"], sst["unchanged"], sst["removed"])
                        save()
                    except OSError as e:
                        partial = True
                        results["skills"][name][t] = "FAILED: %s" % e
            stage(manifest, "skills", "partial" if partial else "ok")
            results["stages"]["claude_plugin"] = plugin_stage(c, args, dry, manifest)
            partial = partial or str(results["stages"]["claude_plugin"]).startswith("FAILED")
            save()

            # memory block (optional)
            if args.write_memory_block:
                for t in c["targets"]:
                    p = lay.claude_md if t == "claude" else lay.codex_md
                    r = upsert_block(p, render_block(lay), journal, dry, "memory-%s" % t)
                    results["stages"]["memory_block_%s" % t] = r
                    manifest.setdefault("memory_blocks", {})[t] = str(p)
                save()

        # 3 work root
        wr = lay.work_root
        if not dry:
            try:
                wr.mkdir(parents=True, exist_ok=True)
                probe = wr / ".avc-write-test"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink()
                results["stages"]["work_root"] = "ready: %s" % wr
                manifest["work_root_created_by_us"] = manifest.get("work_root_created_by_us", False) or not wr.exists()
            except OSError as e:
                results["stages"]["work_root"] = "FAILED: %s" % e
                partial = True
        else:
            results["stages"]["work_root"] = "would create %s" % wr
        results["notes"].append("The work root is stored in %s (read by the toolkit). Environment variables are NOT set by the installer (global mutation); if you want one, set AVC_PATHS_WORK_ROOT=%s yourself." % (lay.toolkit_home / "toolkit.local.toml", wr))

        # 4 missing CLIs (only with --install-missing)
        if args.install_missing:
            for r in plan["prerequisites"]:
                if r["found"] and r["ok"]:
                    continue
                cmd = r["install"]["command"]
                pm = package_manager_for(cmd)
                if not cmd or not pm or not which(pm):
                    results["stages"]["install_%s" % r["id"]] = "not run: no supported package manager on PATH (we never install winget/brew/Scoop/Chocolatey/WSL/Docker for you). Command: %s" % (cmd or r["install"].get("manual"))
                    continue
                if args.offline:
                    results["stages"]["install_%s" % r["id"]] = "deferred (offline)"
                    continue
                if dry:
                    results["stages"]["install_%s" % r["id"]] = "would run: %s" % cmd
                    continue
                p = run_cmd(cmd.split(), timeout=1800)
                results["stages"]["install_%s" % r["id"]] = "ok - open a NEW terminal so PATH refreshes" if p.ok else "FAILED rc=%s: %s" % (p.returncode, (p.stderr or p.error or "").strip()[:300])
                partial = partial or not p.ok

        # 5 python env + node engine
        results["stages"]["python_env"] = python_env_stage(c, args, dry, manifest)
        results["stages"]["engine_npm"] = engine_stage(c, args, dry, manifest)
        partial = partial or any(str(v).startswith("FAILED") for v in (results["stages"]["python_env"], results["stages"]["engine_npm"]))
        for e in c["entries"]:
            if e["kind"] == "python-lib" and e.get("addons") and not args.skip_env:
                results["stages"]["pylib_%s" % e["id"]] = pylib_stage(e, c, args, dry, manifest)
        models = {}
        for pth in manifest.get("generated_dirs_abs", []):
            if Path(pth).name == "asr-cpu":
                models["asr_venv"] = pth
        results["stages"]["toolkit_local_toml"] = write_local_config(lay, manifest, journal, dry, models)
        save()

        # 6 MCP
        if not args.skip_mcp:
            for row in plan["mcp"]:
                entry = next(e for e in c["entries"] if e["id"] == row["id"])
                for t, tv in row["targets"].items():
                    if tv["status"] != "will-register":
                        results["mcp"].append({"name": row["name"], "target": t, "status": tv["status"]})
                        continue
                    if dry:
                        results["mcp"].append({"name": row["name"], "target": t, "status": "dry-run", "argv": tv["argv"]})
                        continue
                    p = run_cmd(tv["argv"], cwd=lay.project_dir if lay.scope == "project" else user_home(), timeout=120)
                    dup = (not p.ok) and "already exists" in ((p.stderr or "") + (p.stdout or "")).lower()
                    status = "registered" if p.ok else ("already-registered" if dup else "FAILED rc=%s: %s" % (p.returncode, (p.stderr or p.stdout or p.error or "").strip()[:300]))
                    partial = partial or (not p.ok and not dup)
                    results["mcp"].append({"name": row["name"], "target": t, "status": status})
                    if p.ok:
                        manifest.setdefault("mcp", []).append({"name": row["name"], "target": t, "scope": c["mcp_scope"], "project_dir": str(lay.project_dir) if lay.project_dir else None, "added_at": now_utc()})
                        save()
        # 7 verify + link check
        if not dry:
            results["verify"] = verify_summary(args, lay, manifest, c["targets"])
        manifest["last_run"] = {"stamp": stamp, "partial": partial}
        save()
        journal.flush()

    emit(json.dumps(results, ensure_ascii=False, indent=2) if args.json else render_apply(results, plan, dry))
    return EXIT_PARTIAL if partial else EXIT_OK


def write_local_config(lay: Layout, manifest: dict, journal: Journal, dry: bool, models=None) -> str:
    """toolkit.local.toml in the toolkit home = the documented per-machine override file (toolkit.toml). Never overwrites a file we did not write."""
    p = lay.toolkit_home / "toolkit.local.toml"
    q = json.dumps(str(lay.work_root).replace("\\", "/"), ensure_ascii=False)
    body = ("# Written by install/bootstrap.py. Per-machine overrides (see toolkit.toml). Safe to edit; `bootstrap.py uninstall` backs it up if you did.\n"
            "[paths]\nwork_root = %s\n" % q)
    if models:
        body += "\n[models]\n" + "".join("%s = %s\n" % (k, json.dumps(str(v).replace("\\", "/"), ensure_ascii=False)) for k, v in sorted(models.items()))
    mine =(manifest.get("generated_files") or {}).get("toolkit.local.toml")
    if p.exists():
        cur = sha256_file(p)
        if not mine or mine != cur:
            return "kept existing %s (not written by us or edited); set paths.work_root there yourself" % p
        if p.read_text(encoding="utf-8") == body:
            return "unchanged"
    if dry:
        return "would write %s" % p
    if p.exists():
        journal.record("replace", p, journal.backup_file(p, "toolkit", "toolkit.local.toml"))
    else:
        journal.record("create", p)
    atomic_write_text(p, body)
    manifest.setdefault("generated_files", {})["toolkit.local.toml"] = sha256_file(p)
    journal.flush()
    return "written"


def render_apply(results: dict, plan: dict, dry: bool) -> str:
    o = ["DRY-RUN: nothing was changed." if dry else "APPLY finished."]
    for k, v in results["stages"].items():
        o.append("  %-26s %s" % (k, v if not isinstance(v, dict) else json.dumps(v, ensure_ascii=False)))
    for n, d in results["skills"].items():
        o.append("  skill %-26s %s" % (n, "; ".join("%s=%s" % (t, s) for t, s in d.items())))
    for m in results["mcp"]:
        o.append("  mcp   %-22s %-7s %s" % (m["name"], m["target"], m["status"]))
    if results.get("verify"):
        v = results["verify"]
        o.append("  verify: highest_state=%s link_errors=%d" % (v["highest_state"], len(v["link_check"]["errors"])))
    for n in results["notes"]:
        o.append("  note: " + n)
    o.append("Next: python install/bootstrap.py verify    (then the student signs in to any provider BY HAND; see INSTALL.md)")
    return "\n".join(o)


def detect_toolkit_version(repo: Path) -> str:
    rm = read_json(repo / "release-manifest.json", {}) or {}
    if rm.get("version"):
        return str(rm["version"])
    pp = repo / "pyproject.toml"
    if pp.is_file():
        try:
            return str(load_toml(pp).get("project", {}).get("version") or "0.0.0-dev")
        except (OSError, SystemExit, ValueError):
            pass
    return "0.0.0-dev"


def git_commit(repo: Path):
    if not (repo / ".git").exists() or not which("git"):
        return None
    p = run_cmd(["git", "-C", str(repo), "rev-parse", "HEAD"], timeout=15)
    return p.stdout.strip() if p.ok else None


def python_env_stage(c: dict, args, dry: bool, manifest: dict) -> str:
    home = c["lay"].toolkit_home
    if args.skip_env or args.no_uv_sync:
        return "skipped (flag)"
    if not (c["toolkit"].get("pyproject.toml")):
        return "skipped: no pyproject.toml in this checkout (available after Phase 1)"
    if not which("uv"):
        return "skipped: uv not on PATH. Install: see integrations/catalog.toml entry `uv`, then re-run apply (idempotent)."
    if args.offline:
        return "deferred (offline): re-run apply when online"
    argv = ["uv", "sync", "--no-dev", "--project", str(home)] + (["--locked"] if "uv.lock" in c["toolkit"] else [])
    if dry:
        return "would run: " + " ".join(argv)
    p = run_cmd(argv, cwd=home, timeout=1800)
    if p.ok:
        manifest.setdefault("generated_dirs", [])
        if ".venv" not in manifest["generated_dirs"]:
            manifest["generated_dirs"].append(".venv")
        return "ok"
    return "FAILED rc=%s: %s (safe to re-run; nothing else depends on it)" % (p.returncode, (p.stderr or p.error or "").strip()[-300:])


def engine_stage(c: dict, args, dry: bool, manifest: dict) -> str:
    home = c["lay"].toolkit_home
    if args.engine == "none" or args.skip_env or args.no_npm:
        return "skipped (engine=none or flag)"
    if "package.json" not in c["toolkit"]:
        return "skipped: no package.json in this checkout (available after Phase 1); engine will be run via the pinned `npx hyperframes@<pin>` from the catalogue"
    if not which("npm"):
        return "skipped: npm not on PATH (install Node LTS first; see catalogue entry `node`)"
    if args.offline:
        return "deferred (offline)"
    argv = ["npm", "ci" if "package-lock.json" in c["toolkit"] else "install", "--ignore-scripts", "--no-audit", "--no-fund"]
    if dry:
        return "would run (in %s): %s" % (home, " ".join(argv))
    p = run_cmd(argv, cwd=home, timeout=1800)
    if p.ok:
        if "node_modules" not in manifest.setdefault("generated_dirs", []):
            manifest["generated_dirs"].append("node_modules")
        return "ok (browser not downloaded; `hyperframes browser ensure` is a separate explicit step)"
    return "FAILED rc=%s: %s" % (p.returncode, (p.stderr or p.error or "").strip()[-300:])


def pylib_stage(e: dict, c: dict, args, dry: bool, manifest: dict) -> str:
    venv = c["lay"].state_dir / "venvs" / e.get("venv", e["id"])
    spec = e.get("pip_spec")
    if not which("uv"):
        return "skipped: uv missing"
    if not spec:
        return "skipped: catalogue has no pinned pip_spec for %s [SOURCED-unverified]" % e["id"]
    if args.offline:
        return "deferred (offline)"
    py = venv / ("Scripts/python.exe" if os_name() == "windows" else "bin/python")
    if dry:
        return "would run: uv venv %s && uv pip install --python %s %s" % (venv, py, spec)
    p = run_cmd(["uv", "venv", "--python", "3.12", str(venv)], timeout=900)
    if p.ok:
        p = run_cmd(["uv", "pip", "install", "--python", str(py), spec], timeout=1800)
    if p.ok:
        manifest.setdefault("generated_dirs_abs", [])
        if str(venv) not in manifest["generated_dirs_abs"]:
            manifest["generated_dirs_abs"].append(str(venv))
        return "ok (weights NOT downloaded)"
    return "FAILED rc=%s: %s" % (p.returncode, (p.stderr or p.error or "").strip()[-300:])


# ----------------------------------------------------------------------------- verify + five states
def installed_skill_dirs(lay: Layout, manifest: dict) -> dict:
    out = {}
    for name, sk in (manifest.get("skills") or {}).items():
        for t, info in (sk.get("targets") or {}).items():
            out["%s/%s" % (t, name)] = Path(info["dir"])
    return out


def verify_summary(args, lay: Layout, manifest: dict, targets) -> dict:
    problems, drift = [], []
    if not manifest:
        return {"installed": False, "problems": ["no install manifest at %s" % lay.manifest], "highest_state": "none", "states": {}, "link_check": {"checked": 0, "errors": [], "warnings": []}}
    for name, sk in (manifest.get("skills") or {}).items():
        for t, info in (sk.get("targets") or {}).items():
            d = Path(info["dir"])
            if not (d / "SKILL.md").is_file():
                problems.append("%s/%s: SKILL.md missing at %s" % (t, name, d))
                continue
            for rel, sha in info["files"].items():
                f = d / rel
                if not f.is_file():
                    problems.append("%s/%s: file missing %s" % (t, name, rel))
                elif sha256_file(f) != sha:
                    drift.append("%s/%s: %s modified after install" % (t, name, rel))
    for rel, sha in (manifest.get("toolkit_files") or {}).items():
        f = lay.toolkit_home / rel
        if not f.is_file():
            problems.append("toolkit file missing: %s" % rel)
        elif sha256_file(f) != sha:
            drift.append("toolkit file modified: %s" % rel)
    dirs = {k: v for k, v in installed_skill_dirs(lay, manifest).items() if v.is_dir()}
    lc = link_check({k: v for k, v in dirs.items()}, lay.toolkit_home)
    ff = ffmpeg_mini_encode()
    core = {"ffmpeg_mini_encode": ff}
    for b in ("python", "uv", "node", "git"):
        core[b] = bool(which(b) or (b == "python" and sys.executable))
    wr = Path((manifest.get("paths") or {}).get("work_root", lay.work_root))
    core["work_root_ascii"] = is_ascii_path(wr)
    core["work_root_exists"] = wr.is_dir()
    mcp_state = []
    for m in manifest.get("mcp") or []:
        names = mcp_names(m["target"], lay, lay.project_dir if lay.scope == "project" else user_home())
        mcp_state.append({"name": m["name"], "target": m["target"], "present": (names is not None and m["name"] in names) if names is not None else None})
    plug = None
    if manifest.get("plugin"):
        plug = plugin_state()
        if plug.get("available") and not (plug["installed"] and plug["enabled"]):
            problems.append("the %s plugin is not installed/enabled in Claude Code (run `claude plugin install %s`)" % (PLUGIN_NAME, PLUGIN_ID))
        elif not plug.get("available"):
            drift.append("could not ask Claude Code about the %s plugin: %s" % (PLUGIN_NAME, plug.get("why")))
    installed_ok = not problems and not lc["errors"] and ff["state"] == "pass" and core["work_root_ascii"] and core["work_root_exists"]
    states = read_json(lay.state_dir / "states.json", {}) or {}
    st = {
        "installed": {"state": "pass" if installed_ok else "fail", "evidence": "files+hashes ok, links ok, ffmpeg mini-encode %s" % ff["state"] if installed_ok else "; ".join(problems[:3] + lc["errors"][:3] + ([ff["evidence"]] if ff["state"] != "pass" else []))},
        "authorised_account": states.get("authorised_account") or {"state": "not_run", "evidence": "the installer cannot inspect logins; the agent asks the student and runs `mark authorised_account --student-confirmed`"},
        "first_render": states.get("first_render") or {"state": "not_run", "evidence": "run the fixture render (docs first-output), then `mark first_render --evidence <mp4>`"},
        "inspection_passed": states.get("inspection_passed") or {"state": "not_run", "evidence": "run `qa delivery` on the final render, then `mark inspection_passed --evidence <qa.json>`"},
        "paid_generation_ready": states.get("paid_generation_ready") or {"state": "not_run", "evidence": "student signs in to ONE provider by hand and approves a budget; `mark paid_generation_ready --student-confirmed --provider <id>`"},
    }
    if st["installed"]["state"] != "pass":
        for k in list(st)[1:]:
            if st[k]["state"] == "pass":
                st[k] = {"state": "not_run", "evidence": "stale: installation no longer passes"}
    order = ["installed", "authorised_account", "first_render", "inspection_passed", "paid_generation_ready"]
    highest = "none"
    for k in order:
        if st[k]["state"] == "pass":
            highest = k
        else:
            break
    return {"installed": True, "problems": problems, "drift": drift, "plugin": plug, "link_check": lc, "core": core, "mcp": mcp_state, "states": st, "highest_state": highest, "checked_at": now_utc(),
            "note": "`claude doctor` diagnoses the Claude Code installation only; it does not prove video, font or GPU readiness."}


def cmd_verify(args) -> int:
    lay = make_layout(args)
    m = load_manifest(lay)
    s = verify_summary(args, lay, m, [])
    if args.json:
        emit(json.dumps(s, ensure_ascii=False, indent=2))
    else:
        emit("Five states (fail-closed; `not_run` is not a pass):")
        for k, v in s["states"].items():
            emit("  %-24s %-8s %s" % (k, v["state"], v["evidence"]))
        for k in ("problems", "drift"):
            for x in s.get(k, []):
                emit("  %s: %s" % (k, x))
        for x in s["link_check"]["errors"]:
            emit("  LINK ERROR: " + x)
        for x in s["link_check"]["warnings"][:10]:
            emit("  link warning: " + x)
        emit("  " + s.get("note", ""))
    bad = (not s.get("installed")) or s["states"].get("installed", {}).get("state") != "pass" or (args.strict and (s["link_check"]["warnings"] or s.get("drift")))
    return EXIT_VERIFY if bad else EXIT_OK


# ----------------------------------------------------------------------------- status / where / mark
def cmd_status(args) -> int:
    lay = make_layout(args)
    m = load_manifest(lay)
    if not m:
        emit("not installed (no manifest at %s)" % lay.manifest)
        return EXIT_VERIFY
    out = {"toolkit_version": m.get("toolkit_version"), "installed_at": m.get("installed_at"), "updated_at": m.get("updated_at"), "selection": m.get("selection"), "paths": m.get("paths"),
           "skills": {n: sorted(v["targets"]) for n, v in (m.get("skills") or {}).items()}, "plugin": m.get("plugin"), "mcp": m.get("mcp", []), "stages": m.get("stages", {}), "last_run": m.get("last_run"),
           "backups": [b["stamp"] for b in m.get("backups", [])][-5:]}
    emit(json.dumps(out, ensure_ascii=False, indent=2))
    return EXIT_OK


def resolve_integration(cat: dict, name: str) -> list:
    ents = cat.get("entry", [])
    exact = [e for e in ents if e["id"] == name]
    return exact or [e for e in ents if name in e.get("addons", []) and not e.get("avoid")]


def cmd_add(args) -> int:
    """`add <id|add-on>`: opt in to ONE optional integration later. Read-only plan by default; --yes performs only the safe, non-spending part
    (register a no-secret connector, create a route environment, run a package-manager command with --install-missing). Keys, sign-ins and
    paid actions stay with the student."""
    cat = load_catalog(REPO)
    ref = load_referrals(REPO)
    if args.list:
        rows = []
        for e in cat["entry"]:
            m, a = e.get("mcp") or {}, e.get("api") or {}
            rows.append({"id": e["id"], "kind": e["kind"], "cost": e.get("cost"), "auth": m.get("auth") or ("env-var " + a["env_var"] if a else "none"),
                         "addons": e.get("addons", []), "avoid": bool(e.get("avoid")), "role": e.get("role")})
        if args.json:
            emit(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for r in rows:
                emit("%-22s %-13s %-9s %s%s" % (r["id"], r["kind"], str(r["cost"]).split(" ")[0], r["role"][:70], "   [AVOID]" if r["avoid"] else ""))
        return EXIT_OK
    name = args.state
    if not name:
        return refuse("usage: bootstrap.py add <integration-id|add-on>   (see: add --list)", EXIT_USAGE)
    ents = resolve_integration(cat, name)
    if not ents:
        return refuse("unknown integration %r; run `add --list`" % name, EXIT_USAGE)
    if any(e.get("avoid") for e in ents):
        return refuse("%r is on the avoid list (stale or unsafe): %s" % (name, ents[0].get("security", "")))
    lay0 = make_layout(args)
    manifest = load_manifest(lay0)
    if manifest:
        pp = manifest.get("paths") or {}
        args.scope, args.project_dir = pp.get("scope", args.scope), pp.get("project_dir") or args.project_dir
    lay = make_layout(args)
    dry = not (args.yes and not args.dry_run)
    if not dry and not manifest:
        return refuse("not installed yet (no manifest at %s); run apply first" % lay.manifest)
    targets = ((manifest.get("selection") or {}).get("target")) or resolve_targets(args, lay)
    mcp_scope = "project" if lay.scope == "project" else "user"
    ctx = {"work_root": str(lay.work_root), "state_dir": str(lay.state_dir), "toolkit_home": str(lay.toolkit_home), "browser_out": str(lay.work_root / "browser-output")}
    existing = {t: mcp_names(t, lay, lay.project_dir if lay.scope == "project" else user_home()) for t in targets}
    stamp = ts_stamp()
    journal = Journal(lay, "add-" + stamp, dry)
    journal.manifest_before = json.loads(json.dumps(manifest)) if manifest else None
    results, partial = [], False
    for e in ents:
        r = {"id": e["id"], "kind": e["kind"], "name": e.get("name"), "role": e.get("role"), "cost": e.get("cost"), "gate": e.get("gate"), "terms": e.get("terms"),
             "security": e.get("security"), "license": e.get("license"), "actions": []}
        if e.get("gate"):
            r["note"] = "Adding is free. Signing in is not spend authorisation: every generation goes through paid-spend-gate (dated estimate + your approval)."
        r["signup"] = signup_options(ref, e["id"], getattr(args, "plain_links", False))
        k = e["kind"]
        if k == "mcp":
            row = mcp_row(e, targets, lay, existing, ctx, mcp_scope)
            r["next_by_hand"] = row.get("next_by_hand")
            var = e["mcp"].get("env_var")
            if var:
                r["env_var"] = {"name": var, "present": var in os.environ, "where": "your OS user environment variable (set it yourself, never in chat); restart the agent afterwards"}
            for t, tv in row["targets"].items():
                act = {"target": t, "status": tv["status"], "argv": tv["argv"]}
                if tv["status"] == "will-register" and not dry:
                    p = run_cmd(tv["argv"], cwd=lay.project_dir if lay.scope == "project" else user_home(), timeout=120)
                    dup = (not p.ok) and "already exists" in ((p.stderr or "") + (p.stdout or "")).lower()
                    act["status"] = "registered" if p.ok else ("already-registered" if dup else "FAILED rc=%s: %s" % (p.returncode, (p.stderr or p.stdout or p.error or "").strip()[:300]))
                    partial = partial or (not p.ok and not dup)
                    if p.ok:
                        manifest.setdefault("mcp", []).append({"name": row["name"], "target": t, "scope": mcp_scope, "project_dir": str(lay.project_dir) if lay.project_dir else None, "added_at": now_utc()})
                r["actions"].append(act)
        elif k == "cli":
            pr = probe_cli(e)
            hint = install_hint(e)
            act = {"found": pr["found"], "version": pr["version"], "install": hint}
            if not pr["found"] and e.get("download_size"):
                act["download_size"] = e["download_size"]
            if not pr["found"] and args.install_missing and not dry:
                pm = package_manager_for(hint["command"])
                if pm and which(pm):
                    p = run_cmd(hint["command"].split(), timeout=1800)
                    act["ran"] = "ok - open a NEW terminal so PATH refreshes" if p.ok else "FAILED rc=%s: %s" % (p.returncode, (p.stderr or p.error or "").strip()[:300])
                    partial = partial or not p.ok
                else:
                    act["ran"] = "not run: no supported package manager on PATH (we never install one for you)"
            r["actions"].append(act)
        elif k == "api":
            var = (e.get("api") or {}).get("env_var")
            r["actions"].append({"env_var": var, "present": var in os.environ if var else None, "where": (e.get("api") or {}).get("where_credentials_go")})
        elif k == "python-lib":
            if args.offline and not dry:
                r["actions"].append({"status": "deferred (offline)"})
            else:
                st = pylib_stage(e, {"lay": lay}, args, dry, manifest)
                r["actions"].append({"status": st if not dry else "would: " + st})
                partial = partial or st.startswith("FAILED")
        elif k == "model":
            r["actions"].append({"status": "never downloaded by the installer", "size": e.get("download_size"), "source": e.get("source_url"), "how": "the transcription tool asks for your approval of the size first"})
        elif k == "native-plugin":
            r["actions"].append({"status": "install by hand", "how": e.get("install_by_hand")})
        results.append(r)
    if not dry:
        if any(e["kind"] == "python-lib" for e in ents):
            models = {}
            for pth in manifest.get("generated_dirs_abs", []):
                if Path(pth).name == "asr-cpu":
                    models["asr_venv"] = pth
            if models:
                write_local_config(lay, manifest, journal, False, models)
        manifest.setdefault("added", []).append({"id": name, "at": now_utc(), "entries": [e["id"] for e in ents]})
        manifest["updated_at"] = now_utc()
        atomic_write_json(lay.manifest, manifest)
        journal.flush()
    out = {"command": "add", "mode": "plan (read-only; add --yes to do the safe part)" if dry else "applied", "results": results}
    if any(r["signup"] for r in results):
        out["disclosure"] = {"en": MSG["en"]["referral_note"], "he": MSG["he"]["referral_note"], "ask": MSG["en"]["signup_ask"]}
    if args.json:
        emit(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        emit("add %s: %s" % (name, out["mode"]))
        for r in results:
            emit("- %s (%s, cost: %s)%s" % (r["id"], r["kind"], str(r["cost"])[:80], "  GATED: " + r["gate"] if r.get("gate") else ""))
            for a in r["actions"]:
                emit("    " + json.dumps(a, ensure_ascii=False)[:400])
            if r.get("env_var"):
                emit("    credential: set %s yourself (present now: %s)" % (r["env_var"]["name"], r["env_var"]["present"]))
            if r.get("next_by_hand"):
                emit("    by hand: " + r["next_by_hand"])
            if r.get("note"):
                emit("    " + r["note"])
            shown = set()
            for sv in r["signup"]:
                if sv["service"] in shown:
                    continue
                shown.add(sv["service"])
                emit("    %s: %s" % (tr(args.lang, "signup"), sv["service"]))
                if sv["referral_url"]:
                    emit("      %s: %s" % (tr(args.lang, "link_referral"), sv["referral_url"]))
                emit("      %s: %s" % (tr(args.lang, "link_plain"), sv["plain_url"]))
            if any(sv["referral_url"] for sv in r["signup"]):
                emit("    " + tr(args.lang, "referral_note"))
            if r["signup"]:
                emit("    " + tr(args.lang, "signup_ask"))
    return EXIT_PARTIAL if partial else EXIT_OK


def passthrough(argv, cwd, env) -> int:
    """Run a command with the terminal attached (streams output). Replaced in tests."""
    if os.environ.get("AVC_NO_REAL_EXEC") == "1":
        raise RuntimeError("AVC_NO_REAL_EXEC=1: refusing to start a real process: %r" % (argv,))
    exe = which(argv[0]) or argv[0]
    try:
        return subprocess.call([exe] + [str(a) for a in argv[1:]], cwd=str(cwd), env=env)
    except OSError as e:
        emit("cannot start %s: %s" % (argv[0], e), file=sys.stderr)
        return 127


def cmd_run(args, command) -> int:
    """`bootstrap.py run [--cwd DIR] -- <command...>`: run a toolkit command from the installed toolkit home with the right environment,
    identical in PowerShell, CMD and bash. Tokens {work_root} and {toolkit_home} in the arguments are substituted. `python ...` uses the toolkit's own uv environment."""
    lay = make_layout(args)
    m = load_manifest(lay)
    if not m:
        return refuse("not installed (no manifest at %s); run apply first" % lay.manifest)
    if not command:
        return refuse("usage: bootstrap.py run [--cwd DIR] -- <command> [args...]", EXIT_USAGE)
    paths = m.get("paths") or lay.as_dict()
    home = Path(paths["toolkit_home"])
    sub = {"work_root": paths["work_root"], "toolkit_home": str(home)}
    argv = [fill(a, sub) for a in command]
    env = dict(os.environ)
    env.update({"PYTHONUTF8": "1", "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1",
                "PYTHONPATH": os.pathsep.join([str(home / "src")] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))})
    env.setdefault("AVC_PATHS_WORK_ROOT", paths["work_root"])
    if argv[0] in ("python", "python3"):
        venv_py = home / (".venv/Scripts/python.exe" if os_name() == "windows" else ".venv/bin/python")
        if venv_py.is_file():
            argv[0] = str(venv_py)
        elif which("uv"):
            argv = ["uv", "run", "--no-dev", "--project", str(home), "python"] + argv[1:]
        else:
            return refuse("no toolkit Python environment (.venv missing) and uv not found; run apply (not --skip-env) or install uv")
    cwd = Path(args.cwd) if args.cwd else home
    return passthrough(argv, cwd, env)


def cmd_where(args) -> int:
    lay = make_layout(args)
    m = load_manifest(lay)
    paths = (m.get("paths") if m else None) or lay.as_dict()
    emit(json.dumps({"installed": bool(m), **paths}, ensure_ascii=False, indent=2) if args.json else str(paths["toolkit_home"]))
    return EXIT_OK


def cmd_mark(args) -> int:
    lay = make_layout(args)
    if not load_manifest(lay):
        return refuse("not installed; run apply first")
    st_file = lay.state_dir / "states.json"
    states = read_json(st_file, {}) or {}
    key = args.state
    ev = {"state": "fail", "evidence": "", "at": now_utc()}
    if key == "first_render":
        if not args.evidence or not Path(args.evidence).is_file():
            return refuse("--evidence <rendered .mp4> is required and must exist")
        p = run_cmd(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", args.evidence], timeout=60)
        data = json.loads(p.stdout or "{}") if p.ok else {}
        has_v = any(s.get("codec_type") == "video" for s in data.get("streams", []))
        dur = float(data.get("format", {}).get("duration", 0) or 0)
        ev.update(state="pass" if (has_v and dur > 0) else "fail", evidence="ffprobe: video=%s duration=%.2fs file=%s sha256=%s" % (has_v, dur, args.evidence, sha256_file(Path(args.evidence))[:16]))
    elif key == "inspection_passed":
        data = read_json(Path(args.evidence), None) if args.evidence else None
        ok = isinstance(data, dict) and data.get("status") == "PASS" and data.get("decoded_frames") and data.get("decoded_frames") == data.get("expected_frames")
        ev.update(state="pass" if ok else "fail", evidence="qa envelope status=%s decoded=%s expected=%s" % ((data or {}).get("status"), (data or {}).get("decoded_frames"), (data or {}).get("expected_frames")))
    elif key in ("authorised_account", "paid_generation_ready"):
        if not args.student_confirmed:
            return refuse("--student-confirmed is required: the student must do the sign-in / approval by hand and confirm it in chat")
        ev.update(state="pass", evidence="student confirmed in chat%s (%s)" % ((" for provider " + args.provider) if args.provider else "", args.note or "no note"))
    else:
        return refuse("unknown state %r" % key, EXIT_USAGE)
    states[key] = ev
    atomic_write_json(st_file, states)
    emit(json.dumps({key: ev}, ensure_ascii=False, indent=2))
    return EXIT_OK if ev["state"] == "pass" else EXIT_VERIFY


# ----------------------------------------------------------------------------- rollback / uninstall
def undo_journal(j: dict, dry: bool) -> list:
    log = []
    for e in reversed(j["entries"]):
        p, b = Path(e["path"]), (Path(e["backup"]) if e.get("backup") else None)
        op = e["op"]
        try:
            if op == "create":
                if p.exists() and not dry:
                    p.unlink()
                log.append("removed created %s" % p)
            elif op in ("replace", "delete") and b and b.is_file():
                if not dry:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(b, p)
                log.append("restored %s" % p)
            elif op == "replace-dir" and b and b.is_dir():
                for f in b.rglob("*"):
                    if f.is_file() and not dry:
                        t = p / f.relative_to(b)
                        t.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, t)
                log.append("restored folder %s" % p)
        except OSError as ex:
            log.append("FAILED %s: %s" % (p, ex))
    if not dry:  # remove folders that became empty because of us (never a folder named "skills")
        parents = sorted({Path(e["path"]).parent for e in j["entries"] if e["op"] == "create"}, key=lambda q: -len(q.parts))
        for d in parents:
            while d.is_dir() and d.name != "skills" and not any(d.iterdir()):
                try:
                    d.rmdir()
                except OSError:
                    break
                d = d.parent
    return log


def cmd_rollback(args) -> int:
    lay = make_layout(args)
    bdir = lay.state_dir / "backups"
    stamps = sorted(d.name for d in bdir.iterdir() if (d / "journal.json").is_file() and not d.name.startswith("uninstall-")) if bdir.is_dir() else []
    if not stamps:
        return refuse("no journals under %s; nothing to roll back" % bdir)
    stamp = args.to or stamps[-1]
    j = read_json(bdir / stamp / "journal.json", None)
    if not j:
        return refuse("journal %s not found; available: %s" % (stamp, ", ".join(stamps)))
    if not args.yes and not args.dry_run:
        return refuse("rollback restores files from %s. Re-run with --yes (or --dry-run)." % stamp, EXIT_USAGE)
    log = undo_journal(j, bool(args.dry_run))
    if not args.dry_run:
        mb = bdir / stamp / "manifest-before.json"
        if mb.is_file():
            mj = read_json(mb, None)
            if mj:
                atomic_write_json(lay.manifest, mj)
            elif lay.manifest.is_file():  # first install rolled back: back to "not installed"
                lay.manifest.unlink()
                if (lay.state_dir / "states.json").is_file():
                    (lay.state_dir / "states.json").unlink()
        log.append("MCP registrations are NOT rolled back automatically; use `claude mcp remove <name>` for any server listed by `status`.")
    emit("\n".join(log))
    return EXIT_OK


def cmd_uninstall(args) -> int:
    lay = make_layout(args)
    m = load_manifest(lay)
    if not m:
        return refuse("nothing to uninstall (no manifest at %s)" % lay.manifest)
    if not args.yes and not args.dry_run:
        return refuse("uninstall removes everything this toolkit installed (your projects, work root and unrelated skills are never touched). Re-run with --yes or --dry-run.", EXIT_USAGE)
    dry = bool(args.dry_run)
    stamp = ts_stamp()
    journal = Journal(lay, "uninstall-" + stamp, dry)
    report = {"removed": [], "backed_up_modified": [], "kept": [], "mcp": [], "blocks": [], "plugin": None}
    with Lock(lay, dry, args.break_lock):
        pg = m.get("plugin")
        if pg:
            steps = [["claude", "plugin", "uninstall", pg.get("id", PLUGIN_ID), "--scope", pg.get("scope", "user"), "--yes"]]
            if pg.get("marketplace_added_by_installer"):
                steps.append(["claude", "plugin", "marketplace", "remove", PLUGIN_NAME])
            if dry:
                report["plugin"] = "would run: " + " ; ".join(" ".join(x) for x in steps)
            elif not which("claude"):
                report["plugin"] = "not removed: `claude` not on PATH. By hand: " + " ; ".join(" ".join(x) for x in steps)
            else:
                out = []
                for argv in steps:
                    r = run_cmd(argv, timeout=120)
                    out.append("%s -> %s" % (" ".join(argv[:4]), "ok" if r.ok else "FAILED rc=%s %s" % (r.returncode, (r.stderr or r.error or "").strip()[:160])))
                report["plugin"] = "; ".join(out)
        for name, sk in (m.get("skills") or {}).items():
            for t, info in (sk.get("targets") or {}).items():
                d = Path(info["dir"])
                for rel, sha in info["files"].items():
                    f = d / rel
                    if not f.is_file():
                        continue
                    if sha256_file(f) != sha:
                        journal.backup_file(f, "modified-skill-%s-%s" % (t, name), rel)
                        report["backed_up_modified"].append(str(f))
                    journal.record("delete", f, None)
                    if not dry:
                        f.unlink()
                    report["removed"].append(str(f))
                if not dry:
                    mk = d / MARKER
                    if mk.is_file():
                        mk.unlink()
                    prune_empty_dirs(d)
                    if d.is_dir() and not any(d.iterdir()):
                        d.rmdir()
                    elif d.is_dir():
                        report["kept"].append("%s (contains files that are not ours)" % d)
        for rel, sha in (m.get("toolkit_files") or {}).items():
            f = lay.toolkit_home / rel
            if f.is_file():
                if sha256_file(f) != sha:
                    journal.backup_file(f, "modified-toolkit", rel)
                    report["backed_up_modified"].append(str(f))
                if not dry:
                    f.unlink()
                report["removed"].append(str(f))
        for gname, gsha in (m.get("generated_files") or {}).items():
            f = lay.toolkit_home / gname
            if f.is_file():
                if sha256_file(f) != gsha:
                    journal.backup_file(f, "modified-toolkit", gname)
                    report["backed_up_modified"].append(str(f))
                if not dry:
                    f.unlink()
                report["removed"].append(str(f))
        for g in m.get("generated_dirs", []):
            d = lay.toolkit_home / g
            if d.is_dir():
                if not dry:
                    shutil.rmtree(d, ignore_errors=True)
                report["removed"].append(str(d) + " (generated)")
        for d in m.get("generated_dirs_abs", []):
            if Path(d).is_dir() and str(lay.state_dir) in str(Path(d)):
                if not dry:
                    shutil.rmtree(d, ignore_errors=True)
                report["removed"].append(d + " (generated)")
        if not dry:
            prune_empty_dirs(lay.toolkit_home)
            if lay.toolkit_home.is_dir() and not any(lay.toolkit_home.iterdir()):
                lay.toolkit_home.rmdir()
        for t, p in (m.get("memory_blocks") or {}).items():
            if remove_block(Path(p), journal, dry, "memory-%s" % t):
                report["blocks"].append(p)
                if not dry and Path(p).parent.is_dir() and not any(Path(p).parent.iterdir()):
                    Path(p).parent.rmdir()  # e.g. a ~/.codex folder that only held our file
        if not dry:  # tidy folders that exist only because of us (only when empty)
            for root in (lay.claude_skills, lay.codex_skills):
                for d in (root, root.parent):
                    if d.is_dir() and not any(d.iterdir()):
                        d.rmdir()
        for rec in m.get("mcp") or []:
            argv = [rec["target"], "mcp", "remove"] + (["--scope", rec["scope"]] if rec["target"] == "claude" else []) + [rec["name"]]
            if dry or not which(rec["target"]):
                report["mcp"].append({"name": rec["name"], "status": "would remove" if dry else "client missing; remove by hand: " + " ".join(argv)})
            else:
                p = run_cmd(argv, cwd=rec.get("project_dir") or user_home(), timeout=60)
                report["mcp"].append({"name": rec["name"], "status": "removed" if p.ok else "FAILED: " + (p.stderr or p.error or "").strip()[:200]})
        journal.flush()
        if not dry:
            shutil.move(str(lay.manifest), str(lay.state_dir / ("install-manifest.uninstalled-%s.json" % stamp)))
            sf = lay.state_dir / "states.json"
            if sf.is_file():
                sf.unlink()
            if args.purge_backups:
                shutil.rmtree(lay.state_dir / "backups", ignore_errors=True)
                report["kept"].append("backups purged by request")
            else:
                report["kept"].append("backups kept at %s (delete the folder yourself when you no longer need them)" % (lay.state_dir / "backups"))
    report["kept"].append("work root and your projects are never touched: %s" % lay.work_root)
    if not args.json:  # keep the human output short; --json prints every path
        report = dict(report, removed=["%d files/folders removed (use --json for the full list)" % len(report["removed"])] + report["removed"][:3])
    emit(json.dumps(report, ensure_ascii=False, indent=2))
    return EXIT_OK


# ----------------------------------------------------------------------------- cli
HELP_DESCRIPTION = """AI Video Editing Toolkit installer. Default command: plan (read-only).

commands:
  plan       show what would happen (read-only, no changes)             [default]
  apply      install; needs --yes (or --dry-run to preview)
  add ID     add one optional integration later (add --list shows them; plan by default, --yes to do it)
  verify     re-check files, links and an FFmpeg encode; print the five states
  status     manifest summary (version, stages, backups)
  where      print the toolkit home
  mark S     record a state with evidence (S = authorised_account | first_render |
             inspection_passed | paid_generation_ready)
  run -- C   run command C from the toolkit home with the right environment
  rollback   undo the last apply that changed files (needs --yes)
  uninstall  remove exactly what apply created (needs --yes)"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bootstrap.py", formatter_class=argparse.RawDescriptionHelpFormatter, description=HELP_DESCRIPTION,
                                epilog="Docs: INSTALL.md. Nothing is changed without `apply --yes`. No telemetry; no secrets are read or written.")
    p.add_argument("command", nargs="?", default="plan", choices=["plan", "apply", "add", "verify", "status", "where", "mark", "rollback", "uninstall", "run"])
    p.add_argument("state", nargs="?", help="for `mark`: authorised_account | first_render | inspection_passed | paid_generation_ready; for `add`: an integration id or add-on name")
    p.add_argument("--profile", choices=["minimal", "standard", "pro"], default="minimal", help="MCP profile (default minimal = no MCP servers)")
    p.add_argument("--with", dest="with_", default="", help="comma list of add-ons, e.g. asr-cpu,blender,provider-higgsfield (see integrations/README.md)")
    p.add_argument("--engine", choices=["hyperframes", "none"], default="hyperframes")
    p.add_argument("--target", choices=["auto", "claude", "codex", "both"], default="auto")
    p.add_argument("--scope", choices=["user", "project"], default="user")
    p.add_argument("--project-dir", help="video project folder for --scope project")
    p.add_argument("--home", help="toolkit home (managed copy). Default: <state>/toolkit")
    p.add_argument("--state-dir", help="installer state (manifest, backups). Default ~/.avc")
    p.add_argument("--work-root", help="ASCII-only folder for video projects. Default ~/avc-work (or C:/avc-work when the home path is not ASCII)")
    p.add_argument("--lang", choices=["en", "he"], default="en")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--yes", action="store_true", help="the student's single confirmation was given")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true", help="replace same-named skills that were NOT created by this toolkit (after backing them up)")
    p.add_argument("--install-missing", action="store_true", help="run the exact winget/brew command for missing CLIs (never installs package managers; never sudo)")
    p.add_argument("--write-memory-block", action="store_true", help="add a marked block to the agent's user instruction file (CLAUDE.md / AGENTS.md); opt-in")
    p.add_argument("--plain-links", action="store_true", help="`add`: show only plain sign-up links, never referral links")
    p.add_argument("--skills-via", choices=["plugin", "copy"], default="plugin", help="Claude Code skills: install the editing-workflow PLUGIN (default; Claude Code updates it and removes it cleanly) or COPY plain skill folders into ~/.claude/skills. Codex always gets copies")
    p.add_argument("--plugin-source", help="marketplace source for --skills-via plugin (default: the public GitHub repository; a local checkout path works for development)")
    p.add_argument("--skip-mcp", action="store_true")
    p.add_argument("--skip-skills", action="store_true")
    p.add_argument("--skip-env", action="store_true", help="skip uv sync / npm ci / python-lib envs")
    p.add_argument("--no-uv-sync", action="store_true")
    p.add_argument("--no-npm", action="store_true")
    p.add_argument("--offline", action="store_true", help="skip every network stage; re-run later to finish")
    p.add_argument("--local", action="store_true", help="the student chose to work locally: also set up the CPU speech-to-text environment (weights are never downloaded without approval). Without it nothing local-AI is installed")
    p.add_argument("--list", action="store_true", help="add: list every integration id with kind, cost and auth")
    p.add_argument("--probe-mcp", action="store_true", help="plan: also ask the clients which MCP servers exist")
    p.add_argument("--break-lock", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--purge-backups", action="store_true")
    p.add_argument("--to", help="rollback: journal stamp (default latest)")
    p.add_argument("--evidence", help="mark: evidence file")
    p.add_argument("--student-confirmed", action="store_true")
    p.add_argument("--provider")
    p.add_argument("--note")
    p.add_argument("--cwd", help="run: working directory for the command (default: the toolkit home)")
    p.add_argument("--repo", help=argparse.SUPPRESS)
    p.add_argument("--toolkit-src", help="path of a complete editing-workflow checkout (skills + tools). Default: the repository this installer is in")
    return p


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # Hebrew-safe on cp1252/cp1255 consoles
        except (AttributeError, ValueError):
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    tail = []
    if argv and argv[0] == "run" and "--" in argv:
        i = argv.index("--")
        argv, tail = argv[:i], argv[i + 1:]
    args = build_parser().parse_args(argv)
    if args.repo:
        global REPO
        REPO = Path(args.repo).resolve()
    try:
        if args.command == "plan":
            plan, _ = build_plan(args, REPO)
            emit(json.dumps(plan, ensure_ascii=False, indent=2) if args.json else render_plan(plan, args.lang))
            return EXIT_OK if not plan["blockers"] else EXIT_REFUSED
        if args.command == "apply":
            return cmd_apply(args)
        if args.command == "add":
            return cmd_add(args)
        if args.command == "verify":
            return cmd_verify(args)
        if args.command == "status":
            return cmd_status(args)
        if args.command == "where":
            return cmd_where(args)
        if args.command == "mark":
            if not args.state:
                return refuse("usage: bootstrap.py mark <state> ...", EXIT_USAGE)
            return cmd_mark(args)
        if args.command == "rollback":
            return cmd_rollback(args)
        if args.command == "uninstall":
            return cmd_uninstall(args)
        if args.command == "run":
            return cmd_run(args, tail)
    except KeyboardInterrupt:
        emit("interrupted; state is consistent (files are replaced atomically). Re-run to continue.", file=sys.stderr)
        return 130
    except BrokenPipeError:  # e.g. `| head`
        return EXIT_OK
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())

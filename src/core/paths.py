"""Path handling: ASCII work root, forbidden-root guard, guarded deletion, project path model, ASCII slugs.

What this module guarantees (each point is a regression test in tests/unit/test_core_paths.py):

1. **Work root is ASCII.** ``npx hyperframes init`` silently skips ``index.html`` under a path with Hebrew letters
   (src: blueprint REPO_ARCHITECTURE section 9.1). ``resolve_work_root`` rejects a non-ASCII root with a fix text.
   Source media may live anywhere (Hebrew, spaces, apostrophes, emoji): the toolkit never renames source folders.
2. **Forbidden roots.** A drive root, a UNC share root, the home folder (and any ancestor of it), standard home
   sub-folders (Desktop, Documents, ...), and operating-system folders are never accepted as a work path or deletion
   target (``forbidden_reason``).
3. **No unchecked recursive delete.** ``safe_rmtree`` is the only deletion helper. It needs an explicit ``allowed_root``
   that carries the ``.avc-managed`` marker, the target must be strictly inside it, must not be a link/junction, must
   not be the current directory or one of its ancestors, and must pass the forbidden-root test. This replaces the
   owner's ``export_kit`` pattern ``rmtree(OUT)`` on an unchecked ``--out`` (src: blueprint TOOLS_SPEC section 2).
4. **Long paths.** ``fs_path`` adds the Windows ``\\\\?\\`` prefix for long paths; use it for raw ``os``/``open`` calls.
5. **Project model.** ``projects/<slug>/{source,hf,final,_work}``; the folder name is an ASCII slug, the Hebrew display
   title is stored separately in ``project.json`` (UTF-8 without BOM).

Usage:
    python -m core slug "סרטון תדמית - דוגמה 🎬"
    python -m core paths check <path>
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import os
import re
import shutil
import stat
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ForbiddenRootError, PathSafetyError
from .fsio import fs_path, read_json, write_json_atomic

__all__ = [
    "MARKER_NAME",
    "PROJECT_SCHEMA",
    "fs_path",
    "slugify",
    "is_ascii_path",
    "forbidden_reason",
    "assert_not_forbidden",
    "resolve_work_root",
    "ensure_managed_root",
    "is_managed_root",
    "is_link_or_junction",
    "safe_rmtree",
    "ProjectPaths",
    "project_paths",
]

MARKER_NAME = ".avc-managed"
PROJECT_SCHEMA = "avc.project/1"
_RESERVED_WINDOWS = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}

# --------------------------------------------------------------------------------------------------------------------
# slugs
# --------------------------------------------------------------------------------------------------------------------

# Deliberately plain consonant transliteration. The goal is a recognisable, stable ASCII folder name, not linguistics.
_HEBREW = {
    "א": "", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "v", "ז": "z", "ח": "ch", "ט": "t", "י": "y",
    "כ": "k", "ך": "k", "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s", "ע": "", "פ": "p",
    "ף": "p", "צ": "ts", "ץ": "ts", "ק": "k", "ר": "r", "ש": "sh", "ת": "t",
}  # fmt: skip


def slugify(name: str, *, max_len: int = 40) -> str:
    """Return a stable ASCII folder name for a (possibly Hebrew, spaced, emoji-laden) display title.

    * Hebrew letters are transliterated, accents are folded, everything else outside ``[a-z0-9]`` becomes ``-``.
    * When the title contained any non-ASCII character, a 6-hex suffix of its NFC SHA-1 is appended so that two
      different Hebrew titles can never collapse to the same folder (e.g. only-vowel or emoji-only titles).
    * An empty result becomes ``project-<hash>``. Windows reserved device names get a ``p-`` prefix.
    The function is pure and deterministic.
    """
    if not isinstance(name, str):
        raise TypeError("name must be str")
    nfc = unicodedata.normalize("NFC", name).strip()
    out: list[str] = []
    for ch in nfc:
        if ch in _HEBREW:
            out.append(_HEBREW[ch])
        elif ch.isascii():
            out.append(ch.lower())
        else:
            # Latin letters with diacritics -> base letter; any other script/emoji/symbol -> separator.
            base = unicodedata.normalize("NFKD", ch)
            folded = "".join(c for c in base if c.isascii())
            out.append(folded.lower() if folded else "-")
    slug = re.sub(r"[^a-z0-9]+", "-", "".join(out)).strip("-")
    digest = hashlib.sha1(nfc.encode("utf-8")).hexdigest()[:6]
    non_ascii = not nfc.isascii()
    if not slug:
        return f"project-{digest}"
    slug = slug[:max_len].rstrip("-")
    if slug in _RESERVED_WINDOWS:
        slug = f"p-{slug}"
    if non_ascii:
        slug = f"{slug}-{digest}"
    return slug


# --------------------------------------------------------------------------------------------------------------------
# forbidden roots
# --------------------------------------------------------------------------------------------------------------------


def _norm(p: str | os.PathLike[str]) -> str:
    """Absolute, symlink/junction-resolved, case-normalised (Windows) string with no trailing separator."""
    raw = os.path.abspath(os.path.expanduser(os.fspath(p)))
    try:
        raw = os.path.realpath(raw)
    except OSError:  # pragma: no cover - realpath rarely raises
        pass
    return os.path.normcase(raw.rstrip("\\/") if len(raw) > 3 else raw)


def _is_same_or_inside(child: str, parent: str) -> bool:
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:  # different drives
        return False


def _drive_or_share_root(path: str) -> bool:
    drive, tail = os.path.splitdrive(path)
    return tail in ("", "\\", "/") and (drive != "" or path in ("/", "\\"))


def _home() -> str:
    return _norm(Path.home())


def forbidden_reason(path: str | os.PathLike[str]) -> str | None:
    """Return a human-readable reason when ``path`` must never be used as a work/deletion target, else ``None``."""
    norm = _norm(path)
    if _drive_or_share_root(norm) or os.path.dirname(norm) == norm:
        return "it is a drive / filesystem root"
    home = _home()
    if norm == home:
        return "it is the user's home folder"
    if _is_same_or_inside(home, norm):
        return "it is a parent of the user's home folder"
    for sub in ("Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music", "OneDrive", "AppData", "Movies", "Library"):
        if norm == os.path.normcase(os.path.join(home, sub)):
            return f"it is the home '{sub}' folder itself (use a sub-folder)"
    for label, base, tree in _system_dirs():
        b = _norm(base)
        if norm == b or (tree and _is_same_or_inside(norm, b)):
            return f"it is the operating-system location '{label}'"
    return None


def _system_dirs() -> list[tuple[str, str, bool]]:
    """(label, path, whole_tree_forbidden). ``False`` means only the folder itself is forbidden."""
    items: list[tuple[str, str, bool]] = []
    if os.name == "nt":
        sysroot = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or r"C:\Windows"
        drive = os.environ.get("SystemDrive") or os.path.splitdrive(sysroot)[0] or "C:"
        items += [
            ("Windows", sysroot, True),
            ("Program Files", os.environ.get("ProgramFiles", drive + r"\Program Files"), True),
            ("Program Files (x86)", os.environ.get("ProgramFiles(x86)", drive + r"\Program Files (x86)"), True),
            ("ProgramData", os.environ.get("ProgramData", drive + r"\ProgramData"), False),
            ("Users", drive + r"\Users", False),
            ("Recycle Bin", drive + r"\$Recycle.Bin", True),
            ("System Volume Information", drive + r"\System Volume Information", True),
        ]
    else:
        for p in ("/bin", "/boot", "/dev", "/etc", "/lib", "/lib64", "/proc", "/sbin", "/sys", "/usr", "/System", "/Library", "/Applications"):
            items.append((p, p, True))
        for p in ("/var", "/private", "/private/var", "/opt", "/tmp", "/run", "/home", "/Users", "/Volumes", "/mnt", "/media", "/root", "/srv"):
            items.append((p, p, False))
    return items


def assert_not_forbidden(path: str | os.PathLike[str], *, purpose: str = "use") -> None:
    reason = forbidden_reason(path)
    if reason:
        raise ForbiddenRootError(
            f"refusing to {purpose} {os.fspath(path)!r}: {reason}",
            remediation="choose a dedicated sub-folder such as D:/avc-work (ASCII, not a drive root or home folder)",
        )


# --------------------------------------------------------------------------------------------------------------------
# work root
# --------------------------------------------------------------------------------------------------------------------


def is_ascii_path(path: str | os.PathLike[str]) -> bool:
    return os.fspath(path).isascii()


def _bad_component(part: str) -> str | None:
    if any(ord(c) < 32 for c in part):
        return "control character"
    if os.name == "nt":
        if part.endswith((" ", ".")) and part not in (".", ".."):
            return "trailing space or dot (Windows silently strips it)"
        if part.lower().split(".")[0] in _RESERVED_WINDOWS:
            return "reserved Windows device name"
        if any(c in part for c in '<>"|?*'):
            return "character not allowed on Windows"
    return None


def resolve_work_root(raw: str | os.PathLike[str], *, allow_non_ascii: bool = False) -> Path:
    """Validate and absolutise a work root. Does not create it. Raises ``PathSafetyError``/``ForbiddenRootError``."""
    text = os.fspath(raw)
    if not text.strip():
        raise PathSafetyError("work root is empty", remediation="set [paths] work_root in toolkit.toml or AVC_PATHS_WORK_ROOT")
    # check the RAW text: on Windows abspath() silently strips trailing spaces/dots, which would hide the hazard
    for part in text.replace("\\", "/").split("/"):
        if part in ("", ".", "..") or re.fullmatch(r"[A-Za-z]:", part) or part == "~":
            continue
        bad = _bad_component(part)
        if bad:
            raise PathSafetyError(f"work root component {part!r} has a {bad}")
    path = Path(os.path.abspath(os.path.expanduser(text)))
    assert_not_forbidden(path, purpose="use as work root")
    if not allow_non_ascii and not is_ascii_path(path):
        raise PathSafetyError(
            f"work root {str(path)!r} contains non-ASCII characters",
            remediation="use an ASCII folder such as D:/avc-work; HyperFrames init skips index.html under Hebrew paths. "
            "Source media can stay in its Hebrew-named folder; it is copied, never moved.",
        )
    if path.exists() and not path.is_dir():
        raise PathSafetyError(f"work root {str(path)!r} exists and is not a directory")
    return path


def is_managed_root(path: str | os.PathLike[str]) -> bool:
    return os.path.isfile(fs_path(os.path.join(os.fspath(path), MARKER_NAME)))


def ensure_managed_root(path: str | os.PathLike[str], *, kind: str = "work_root") -> Path:
    """Create ``path`` (if missing) and stamp it with the ``.avc-managed`` marker that ``safe_rmtree`` requires."""
    p = Path(os.path.abspath(os.fspath(path)))
    assert_not_forbidden(p, purpose="manage")
    os.makedirs(fs_path(p), exist_ok=True)
    marker = p / MARKER_NAME
    if not os.path.isfile(fs_path(marker)):
        write_json_atomic(
            marker,
            {
                "schema": "avc.managed/1",
                "kind": kind,
                "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                "note": "Created by editing-workflow. Folders below this one may be deleted by the toolkit's guarded cleanup.",
            },
        )
    return p


# --------------------------------------------------------------------------------------------------------------------
# guarded delete
# --------------------------------------------------------------------------------------------------------------------


def is_link_or_junction(path: str | os.PathLike[str]) -> bool:
    p = fs_path(path)
    if os.path.islink(p):
        return True
    isjunction = getattr(os.path, "isjunction", None)  # Python 3.12+
    if isjunction is not None and isjunction(p):
        return True
    if os.name == "nt":
        try:
            attrs = os.lstat(p).st_file_attributes  # type: ignore[attr-defined]
            return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)  # type: ignore[attr-defined]
        except OSError:
            return False
    return False


def _on_rm_error(func, path, exc):  # pragma: no cover - platform dependent
    """Windows: read-only files make rmtree fail; clear the flag once and retry, otherwise re-raise."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        raise exc


def safe_rmtree(target: str | os.PathLike[str], *, allowed_root: str | os.PathLike[str], dry_run: bool = False) -> dict:
    """Recursively delete ``target`` only when every guard below holds; otherwise raise and touch nothing.

    Guards: ``allowed_root`` is given explicitly, is not forbidden and carries the ``.avc-managed`` marker; ``target``
    exists, is a real directory (not a link/junction), is *strictly* inside ``allowed_root`` after symlink resolution,
    is not forbidden, and is neither the current directory nor one of its ancestors.
    Returns ``{"removed": <path>, "dry_run": bool, "files": <int>, "bytes": <int>}``.
    """
    if allowed_root is None or not os.fspath(allowed_root).strip():
        raise PathSafetyError("safe_rmtree needs an explicit allowed_root")
    root = _norm(allowed_root)
    assert_not_forbidden(allowed_root, purpose="delete inside")
    if not is_managed_root(allowed_root):
        raise PathSafetyError(
            f"{os.fspath(allowed_root)!r} has no {MARKER_NAME} marker; refusing to delete anything below it",
            remediation="create the work root with ensure_managed_root() / the new_project tool",
        )
    raw_target = os.path.abspath(os.path.expanduser(os.fspath(target)))
    if not os.path.lexists(fs_path(raw_target)):
        raise PathSafetyError(f"{raw_target!r} does not exist")
    if is_link_or_junction(raw_target):
        raise PathSafetyError(f"{raw_target!r} is a symlink/junction; refusing to delete through it")
    if not os.path.isdir(fs_path(raw_target)):
        raise PathSafetyError(f"{raw_target!r} is not a directory")
    norm_target = _norm(raw_target)
    if norm_target == root or not _is_same_or_inside(norm_target, root):
        raise PathSafetyError(f"{raw_target!r} is not strictly inside the managed root {os.fspath(allowed_root)!r}")
    assert_not_forbidden(raw_target, purpose="delete")
    cwd = _norm(os.getcwd())
    if _is_same_or_inside(cwd, norm_target):
        raise PathSafetyError(f"{raw_target!r} is the current directory or one of its parents")
    files = size = 0
    for dirpath, _dirs, names in os.walk(fs_path(raw_target)):
        for n in names:
            files += 1
            try:
                size += os.lstat(os.path.join(dirpath, n)).st_size
            except OSError:
                pass
    result = {"removed": raw_target, "dry_run": dry_run, "files": files, "bytes": size}
    if not dry_run:
        shutil.rmtree(fs_path(raw_target), onexc=_on_rm_error)
    return result


# --------------------------------------------------------------------------------------------------------------------
# project model
# --------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectPaths:
    """``<work_root>/projects/<slug>/{source,hf,final,_work}``. ``title`` is the (Hebrew) display name."""

    work_root: Path
    slug: str
    title: str
    source_name: str = "source"
    hf_name: str = "hf"
    final_name: str = "final"
    work_name: str = "_work"
    extra: dict = field(default_factory=dict, compare=False)

    @property
    def root(self) -> Path:
        return self.work_root / "projects" / self.slug

    @property
    def source(self) -> Path:
        return self.root / self.source_name

    @property
    def hf(self) -> Path:
        return self.root / self.hf_name

    @property
    def final(self) -> Path:
        return self.root / self.final_name

    @property
    def work(self) -> Path:
        return self.root / self.work_name

    @property
    def meta_file(self) -> Path:
        return self.root / "project.json"

    @property
    def ledger_file(self) -> Path:
        return self.work / "timing-ledger.jsonl"

    def ensure(self) -> "ProjectPaths":
        """Create the skeleton (idempotent). Never touches existing source files."""
        ensure_managed_root(self.work_root)
        for d in (self.source, self.hf, self.final, self.work):
            os.makedirs(fs_path(d), exist_ok=True)
        if not os.path.isfile(fs_path(self.meta_file)):
            write_json_atomic(
                self.meta_file,
                {
                    "schema": PROJECT_SCHEMA,
                    "slug": self.slug,
                    "title": self.title,
                    "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                    "folders": {"source": self.source_name, "hf": self.hf_name, "final": self.final_name, "work": self.work_name},
                },
            )
        return self

    def title_from_disk(self) -> str:
        return str(read_json(self.meta_file).get("title", self.title))

    def clean_work(self, *, dry_run: bool = False) -> dict:
        """Delete ``_work`` through ``safe_rmtree`` (the only delete the toolkit offers)."""
        return safe_rmtree(self.work, allowed_root=self.work_root, dry_run=dry_run)


def project_paths(work_root: str | os.PathLike[str], title: str, *, slug: str | None = None, folders: dict | None = None) -> ProjectPaths:
    """Build the path model for a project. ``title`` may be Hebrew; the folder name is ``slugify(title)``.

    ``folders`` may override the four sub-folder names (from ``[output]`` in toolkit.toml); they must be ASCII
    single path components.
    """
    root = resolve_work_root(work_root)
    s = slug or slugify(title)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", s):
        raise PathSafetyError(f"slug {s!r} is not a plain ASCII folder name")
    kw: dict[str, str] = {}
    for key, attr in (("source", "source_name"), ("hf", "hf_name"), ("final", "final_name"), ("work", "work_name")):
        if folders and folders.get(key):
            val = str(folders[key])
            if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", val):
                raise PathSafetyError(f"output folder name {val!r} must be a plain ASCII component")
            kw[attr] = val
    return ProjectPaths(work_root=root, slug=s, title=title, **kw)

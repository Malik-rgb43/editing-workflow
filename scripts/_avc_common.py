"""Shared helpers for the scripts in this directory (Python 3.12, stdlib only).

Usage: library module, imported by scripts/*.py and tests; it is not a CLI.

Conventions shared by every check script:
  * statuses are PASS | WARN | FAIL | NOT_RUN | ERROR (a gate that cannot run
    reports NOT_RUN, never PASS);
  * exit codes: 0 ok, 1 FAIL/ERROR, 2 usage error, 3 NOT_RUN under --strict;
  * every check supports --json and --root and writes UTF-8 only;
  * a line containing the token ``scan-ignore`` is skipped by the private/secret scans.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
NOT_RUN = "NOT_RUN"
ERROR = "ERROR"

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_NOT_RUN = 3

SCRIPTS_DIR = Path(__file__).resolve().parent

DEFAULT_EXCLUDE_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
        ".uv-cache",
        "dist",
        ".idea",
        ".vscode",
    }
)

HEBREW_RE = re.compile("[֐-׿]")
# UTF-8 Hebrew decoded as cp1252/latin-1 shows up as 0xD7 ("x" sign) + a symbol character.
MOJIBAKE_RE = re.compile("×[\u0080-¿ŒœŠšŸŽžƒˆ˜–-›€™]")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$")
SCAN_IGNORE_TOKEN = "scan-ignore"


def setup_utf8() -> None:
    """Make stdout/stderr UTF-8 so Hebrew output never crashes a Windows console."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - exotic streams
            pass


def default_root() -> Path:
    return SCRIPTS_DIR.parent


def resolve_root(value: str | None) -> Path:
    root = Path(value).expanduser() if value else default_root()
    return root.resolve()


def has_hebrew(text: str) -> bool:
    return HEBREW_RE.search(text) is not None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_text_strict(path: Path) -> str:
    """Read UTF-8 (BOM tolerated for reading; callers that care check the BOM separately)."""
    return path.read_bytes().decode("utf-8-sig")


def has_bom(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(3) == b"\xef\xbb\xbf"


# --------------------------------------------------------------------------- reports


@dataclasses.dataclass
class Finding:
    level: str  # FAIL | WARN | INFO
    code: str
    message: str
    path: str | None = None
    line: int | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}

    def render(self) -> str:
        where = ""
        if self.path:
            where = f" {self.path}"
            if self.line:
                where += f":{self.line}"
        return f"  [{self.level}] {self.code}{where} - {self.message}"


class Report:
    """Accumulates findings; computes a fail-closed status."""

    def __init__(self, tool: str) -> None:
        self.tool = tool
        self.findings: list[Finding] = []
        self.not_run_parts: list[dict] = []
        self.blocking_not_run = False
        self.stats: dict = {}
        self.notes: list[str] = []

    def fail(self, code: str, message: str, path: str | None = None, line: int | None = None) -> None:
        self.findings.append(Finding("FAIL", code, message, path, line))

    def warn(self, code: str, message: str, path: str | None = None, line: int | None = None) -> None:
        self.findings.append(Finding("WARN", code, message, path, line))

    def info(self, code: str, message: str, path: str | None = None, line: int | None = None) -> None:
        self.findings.append(Finding("INFO", code, message, path, line))

    def not_run(self, part: str, reason: str, blocking: bool = True) -> None:
        self.not_run_parts.append({"part": part, "reason": reason, "blocking": blocking})
        if blocking:
            self.blocking_not_run = True

    @property
    def fails(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "FAIL"]

    @property
    def warns(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "WARN"]

    @property
    def status(self) -> str:
        if self.fails:
            return FAIL
        if self.blocking_not_run:
            return NOT_RUN
        if self.warns:
            return WARN
        return PASS

    def summary(self) -> str:
        parts = [f"{len(self.fails)} fail", f"{len(self.warns)} warn"]
        for key, value in self.stats.items():
            if isinstance(value, (int, float, str)):
                parts.append(f"{key}={value}")
        for item in self.not_run_parts:
            parts.append(f"NOT_RUN({item['part']})")
        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "status": self.status,
            "stats": self.stats,
            "not_run_parts": self.not_run_parts,
            "notes": self.notes,
            "findings": [f.to_dict() for f in self.findings],
        }


def exit_code(status: str, strict_not_run: bool = False, warnings_as_errors: bool = False) -> int:
    if status in (FAIL, ERROR):
        return EXIT_FAIL
    if status == WARN and warnings_as_errors:
        return EXIT_FAIL
    if status == NOT_RUN and strict_not_run:
        return EXIT_NOT_RUN
    return EXIT_OK


def emit(report: Report, as_json: bool, strict_not_run: bool = False, warnings_as_errors: bool = False,
         show_info: bool = False) -> int:
    """Print the report (human or JSON) and return the process exit code."""
    status = report.status
    if as_json:
        data = report.to_dict()
        data["exit"] = exit_code(status, strict_not_run, warnings_as_errors)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return data["exit"]
    for finding in report.findings:
        if finding.level == "INFO" and not show_info:
            continue
        print(finding.render())
    for item in report.not_run_parts:
        print(f"  [NOT_RUN] {item['part']} - {item['reason']}")
    for note in report.notes:
        print(f"  note: {note}")
    print(f"RESULT: {status} {report.tool} ({report.summary()})")
    return exit_code(status, strict_not_run, warnings_as_errors)


def add_common_args(parser, *, strict_not_run: bool = True) -> None:
    parser.add_argument("--root", default=None, help="repository root (default: parent of scripts/)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--warnings-as-errors", action="store_true", help="exit non-zero on WARN too")
    if strict_not_run:
        parser.add_argument("--strict", action="store_true", help="exit 3 when the result is NOT_RUN")


# --------------------------------------------------------------------------- file listing

RESTRICTED_EXT = {
    "video": {"mp4", "mov", "mkv", "webm", "avi", "m4v", "mxf", "wmv", "flv", "mpg", "mpeg"},
    "audio": {"wav", "mp3", "m4a", "aac", "flac", "ogg", "opus", "aiff", "aif", "wma"},
    "image": {"png", "jpg", "jpeg", "gif", "webp", "svg", "ico", "bmp", "tif", "tiff", "avif", "heic", "psd", "ai"},
    "font": {"ttf", "otf", "woff", "woff2", "ttc", "dfont", "eot"},
    "weights": {"onnx", "pt", "pth", "safetensors", "gguf", "ckpt", "pb", "tflite", "mlmodel", "bin", "npz", "npy"},
    "archive": {"zip", "7z", "rar", "tar", "gz", "tgz", "xz", "bz2"},
    "executable": {"exe", "dll", "so", "dylib", "msi", "jar", "app", "node"},
}
EXT_TO_CLASS = {ext: cls for cls, exts in RESTRICTED_EXT.items() for ext in exts}


def file_class(relpath: str) -> str | None:
    """Return the restricted-binary class of a path by extension, or None for ordinary files."""
    ext = relpath.rsplit(".", 1)[-1].lower() if "." in relpath.rsplit("/", 1)[-1] else ""
    return EXT_TO_CLASS.get(ext)


def _git_list(root: Path) -> list[str] | None:
    if not (root / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "-c", "core.quotepath=off", "ls-files", "-z", "-c", "-o", "--exclude-standard"],
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    names = [n for n in proc.stdout.decode("utf-8", "surrogateescape").split("\0") if n]
    return names


def list_files(root: Path, use_git: bool = True, exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE_DIRS) -> list[str]:
    """Sorted posix-style relative paths of files that would ship (git view when available, else a plain walk)."""
    root = Path(root)
    names: list[str] | None = _git_list(root) if use_git else None
    if names is None:
        names = []
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = sorted(d for d in dirnames if d not in exclude_dirs)
            for filename in filenames:
                full = Path(dirpath) / filename
                names.append(full.relative_to(root).as_posix())
    out = []
    for name in names:
        parts = name.split("/")
        if any(p in exclude_dirs for p in parts[:-1]):
            continue
        full = root / name
        if full.is_symlink() or not full.is_file():
            continue
        out.append(name)
    return sorted(set(out))


def looks_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return b"\0" in handle.read(8192)
    except OSError:
        return True


def read_scan_text(path: Path, max_bytes: int = 2_000_000) -> str | None:
    """Return decoded text for scanning, or None for binary/oversized/unreadable files."""
    try:
        if path.stat().st_size > max_bytes or looks_binary(path):
            return None
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return None


def glob_to_regex(glob: str) -> re.Pattern[str]:
    """Gitattributes-like glob: ** crosses directories, * and ? do not. Anchored, case-sensitive."""
    i, n, out = 0, len(glob), []
    while i < n:
        c = glob[i]
        if c == "*":
            if glob[i : i + 3] == "**/":
                out.append("(?:.*/)?")
                i += 3
                continue
            if glob[i : i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def glob_match(glob: str, relpath: str) -> bool:
    return glob_to_regex(glob).match(relpath) is not None


# --------------------------------------------------------------------------- YAML subset (frontmatter)


class FrontmatterError(ValueError):
    pass


class PlainStr(str):
    """An unquoted YAML scalar (lets callers insist on quoting, e.g. version strings)."""


_KEY_RE = re.compile(r"^([A-Za-z_][\w.-]*)\s*:(?:\s+(.*))?$")
_BLOCK_RE = re.compile(r"^[|>][+-]?\d*$")


def split_frontmatter(text: str) -> tuple[str | None, str, int]:
    """Return (frontmatter_text|None, body, body_first_line_number)."""
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text, 1
    for idx in range(1, len(lines)):
        if lines[idx].strip() in ("---", "..."):
            return "\n".join(lines[1:idx]), "\n".join(lines[idx + 1 :]), idx + 2
    raise FrontmatterError("frontmatter opened with --- but never closed")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def _strip_plain_comment(value: str) -> str:
    match = re.search(r"\s#", value)
    return value[: match.start()].rstrip() if match else value.strip()


class _YamlParser:
    def __init__(self, text: str) -> None:
        self.lines = text.split("\n")
        self.i = 0

    def error(self, message: str) -> FrontmatterError:
        return FrontmatterError(f"frontmatter line {self.i + 1}: {message}")

    def next_nonblank(self, start: int) -> int | None:
        j = start
        while j < len(self.lines):
            if not _blank(self.lines[j]):
                return j
            j += 1
        return None

    def parse_map(self, indent: int) -> dict:
        result: dict = {}
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if _blank(line):
                self.i += 1
                continue
            if "\t" in line[: len(line) - len(line.lstrip())]:
                raise self.error("tab indentation is not allowed")
            ind = _indent(line)
            if ind < indent:
                break
            if ind > indent:
                raise self.error("unexpected indentation")
            match = _KEY_RE.match(line[ind:])
            if not match:
                raise self.error("expected 'key: value'")
            key, rest = match.group(1), match.group(2)
            if key in result:
                raise self.error(f"duplicate key '{key}'")
            self.i += 1
            result[key] = self.parse_value(rest if rest is not None else "", indent)
        return result

    def parse_value(self, rest: str, indent: int):
        rest = rest.strip()
        if rest == "" or rest.startswith("#"):
            j = self.next_nonblank(self.i)
            if j is None:
                return None
            nxt = self.lines[j]
            ind = _indent(nxt)
            if ind > indent:
                self.i = j
                if nxt.lstrip().startswith("- ") or nxt.strip() == "-":
                    return self.parse_list(ind)
                return self.parse_map(ind)
            if ind == indent and nxt.lstrip().startswith("- "):
                self.i = j
                return self.parse_list(ind)
            return None
        if _BLOCK_RE.match(_strip_plain_comment(rest)):
            return self.parse_block_scalar(_strip_plain_comment(rest), indent)
        if rest[0] in "\"'":
            return self.parse_quoted(rest)
        if rest[0] == "[":
            return self.parse_flow_list(rest)
        if rest[0] in "{&*!%@`":
            raise self.error("unsupported YAML construct (flow map/anchor/tag)")
        value = _strip_plain_comment(rest)
        parts = [value]
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if _blank(line):
                j = self.next_nonblank(self.i)
                if j is not None and _indent(self.lines[j]) > indent:
                    self.i += 1
                    continue
                break
            if _indent(line) > indent:
                parts.append(_strip_plain_comment(line.strip()))
                self.i += 1
            else:
                break
        return PlainStr(" ".join(p for p in parts if p))

    def parse_block_scalar(self, header: str, indent: int) -> str:
        folded = header.startswith(">")
        chomp = "-" if "-" in header else ("+" if "+" in header else "")
        collected: list[str] = []
        block_indent: int | None = None
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if not line.strip():
                collected.append("")
                self.i += 1
                continue
            ind = _indent(line)
            if ind <= indent:
                break
            if block_indent is None:
                block_indent = ind
            collected.append(line[block_indent:] if ind >= block_indent else line.strip())
            self.i += 1
        while collected and collected[-1] == "" and chomp != "+":
            collected.pop()
        if folded:
            text = ""
            prev_blank = False
            for item in collected:
                if item == "":
                    text += "\n"  # a blank line in a folded scalar is one newline
                    prev_blank = True
                else:
                    if text and not prev_blank:
                        text += " "
                    text += item.strip()
                    prev_blank = False
        else:
            text = "\n".join(collected)
        return text if chomp == "-" else text + ("\n" if text else "")

    def parse_quoted(self, rest: str) -> str:
        quote = rest[0]
        buf: list[str] = []
        text = rest[1:]
        while True:
            j = 0
            while j < len(text):
                ch = text[j]
                if quote == '"' and ch == "\\" and j + 1 < len(text):
                    nxt = text[j + 1]
                    escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/", "r": "\r", "0": "\0"}
                    if nxt in escapes:
                        buf.append(escapes[nxt])
                        j += 2
                        continue
                    if nxt == "u" and re.fullmatch(r"[0-9a-fA-F]{4}", text[j + 2 : j + 6]):
                        buf.append(chr(int(text[j + 2 : j + 6], 16)))
                        j += 6
                        continue
                    buf.append(nxt)
                    j += 2
                    continue
                if quote == "'" and ch == "'":
                    if j + 1 < len(text) and text[j + 1] == "'":
                        buf.append("'")
                        j += 2
                        continue
                    return "".join(buf)
                if quote == '"' and ch == '"':
                    return "".join(buf)
                buf.append(ch)
                j += 1
            if self.i >= len(self.lines):
                raise self.error("unterminated quoted string")
            buf.append(" ")
            text = self.lines[self.i].strip()
            self.i += 1

    def parse_flow_list(self, rest: str) -> list:
        text = rest
        while text.count("[") > text.count("]") and self.i < len(self.lines):
            text += " " + self.lines[self.i].strip()
            self.i += 1
        end = text.rfind("]")
        if end < 0:
            raise self.error("unterminated flow list")
        inner = text[1:end]
        items: list = []
        current: list[str] = []
        quote = ""
        for ch in inner:
            if quote:
                current.append(ch)
                if ch == quote:
                    quote = ""
            elif ch in "\"'":
                quote = ch
                current.append(ch)
            elif ch == ",":
                items.append("".join(current).strip())
                current = []
            else:
                current.append(ch)
        tail = "".join(current).strip()
        if tail:
            items.append(tail)
        out = []
        for item in items:
            if len(item) >= 2 and item[0] in "\"'" and item[-1] == item[0]:
                out.append(item[1:-1])
            else:
                out.append(PlainStr(item))
        return out

    def parse_list(self, indent: int) -> list:
        items: list = []
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if _blank(line):
                self.i += 1
                continue
            ind = _indent(line)
            if ind < indent or not (line.lstrip().startswith("- ") or line.strip() == "-"):
                break
            if ind != indent:
                raise self.error("unexpected indentation in list")
            item = line.lstrip()[1:].strip()
            self.i += 1
            if re.match(r"^[A-Za-z_][\w.-]*\s*:(\s|$)", item) and not item.startswith(("'", '"')):
                raise self.error("lists of mappings are not supported in portable frontmatter")
            if item == "":
                items.append(None)
            elif item[0] in "\"'":
                items.append(self.parse_quoted(item))
            else:
                items.append(PlainStr(_strip_plain_comment(item)))
        return items


def parse_yaml_subset(text: str) -> dict:
    parser = _YamlParser(text)
    result = parser.parse_map(0)
    leftover = parser.next_nonblank(parser.i)
    if leftover is not None:
        parser.i = leftover
        raise parser.error("could not parse remaining content")
    return result


def parse_frontmatter(text: str) -> tuple[dict | None, str, int]:
    """Return (mapping|None, body, body_first_line). Raises FrontmatterError on malformed input."""
    fm, body, line_no = split_frontmatter(text)
    if fm is None:
        return None, body, line_no
    return parse_yaml_subset(fm), body, line_no


# --------------------------------------------------------------------------- trigger eval files

TRIGGER_KEYS = {"prompt", "should_trigger", "route_instead"}


def validate_trigger_text(text: str, known_skills: set[str] | None = None, min_pos: int = 8, min_neg: int = 4) -> tuple[list[tuple[str, str, str, int | None]], dict]:
    """Validate the content of evals/triggers.jsonl.

    Returns (issues, counts); issues are (level, code, message, line) with level FAIL or WARN.
    """
    issues: list[tuple[str, str, str, int | None]] = []
    counts = {"positive": 0, "negative": 0, "hebrew_positive": 0, "hebrew_negative": 0, "records": 0}
    seen: dict[str, int] = {}
    if text.startswith("﻿"):
        issues.append(("FAIL", "trigger-bom", "triggers.jsonl must be UTF-8 without BOM", 1))
        text = text.lstrip("﻿")
    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(("FAIL", "trigger-json", f"invalid JSON ({exc.msg})", number))
            continue
        if not isinstance(record, dict):
            issues.append(("FAIL", "trigger-schema", "each line must be a JSON object", number))
            continue
        counts["records"] += 1
        keys = set(record)
        missing = TRIGGER_KEYS - keys
        extra = keys - TRIGGER_KEYS
        if missing:
            issues.append(("FAIL", "trigger-schema", f"missing key(s): {', '.join(sorted(missing))}", number))
        if extra:
            issues.append(("WARN", "trigger-extra-keys", f"unknown key(s): {', '.join(sorted(extra))}", number))
        prompt = record.get("prompt")
        should = record.get("should_trigger")
        route = record.get("route_instead", None)
        ok = True
        if not isinstance(prompt, str) or not prompt.strip():
            issues.append(("FAIL", "trigger-prompt", "prompt must be a non-empty string", number))
            ok = False
        if not isinstance(should, bool):
            issues.append(("FAIL", "trigger-should", "should_trigger must be true or false (JSON boolean)", number))
            ok = False
        if route is not None and not isinstance(route, str):
            issues.append(("FAIL", "trigger-route", "route_instead must be a string or null", number))
            ok = False
        if isinstance(prompt, str):
            if MOJIBAKE_RE.search(prompt):
                issues.append(("FAIL", "trigger-mojibake", "prompt looks like mis-decoded Hebrew (UTF-8 read as cp1252)", number))
            if re.search(r"\?{3,}", prompt):
                issues.append(("FAIL", "trigger-qmarks", "prompt contains '???' (Hebrew lost to console encoding?)", number))
            if len(prompt.strip()) < 6:
                issues.append(("WARN", "trigger-short", "prompt is very short", number))
            key = prompt.strip().lower()
            if key in seen:
                issues.append(("WARN", "trigger-duplicate", f"duplicate of line {seen[key]}", number))
            else:
                seen[key] = number
        if not ok:
            continue
        heb = has_hebrew(prompt)
        if should:
            counts["positive"] += 1
            counts["hebrew_positive"] += int(heb)
            if route is not None:
                issues.append(("WARN", "trigger-route-on-positive", "route_instead should be null when should_trigger is true", number))
        else:
            counts["negative"] += 1
            counts["hebrew_negative"] += int(heb)
            if isinstance(route, str) and known_skills is not None and route not in known_skills:
                issues.append(("WARN", "trigger-route-unknown", f"route_instead '{route}' is not a skill in agent-content/skills", number))
    if counts["positive"] < min_pos:
        issues.append(("FAIL", "trigger-count-positive", f"{counts['positive']} should-trigger case(s); need >= {min_pos}", None))
    if counts["negative"] < min_neg:
        issues.append(("FAIL", "trigger-count-negative", f"{counts['negative']} should-not-trigger case(s); need >= {min_neg}", None))
    if counts["positive"] and counts["hebrew_positive"] == 0:
        issues.append(("FAIL", "trigger-hebrew-positive", "no Hebrew should-trigger case", None))
    if counts["negative"] and counts["hebrew_negative"] == 0:
        issues.append(("FAIL", "trigger-hebrew-negative", "no Hebrew should-not-trigger case", None))
    return issues, counts


def skill_names(skills_dir: Path) -> set[str]:
    if not skills_dir.is_dir():
        return set()
    return {p.name for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))}


def parse_run_json(stdout: str) -> dict | None:
    """Parse the JSON object a --json run printed (tolerates leading noise lines)."""
    start = stdout.find("{")
    if start < 0:
        return None
    try:
        return json.loads(stdout[start:])
    except json.JSONDecodeError:
        return None

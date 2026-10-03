"""Deterministic checks for every skill under agent-content/skills/<name>/ (no model calls).

Usage: python scripts/check_skills.py [--root DIR] [--skills-dir DIR] [--only NAME ...] [--json] [--strict] [--warnings-as-errors]

Per skill (SKILL_AUTHORING_STANDARD + ROADMAP Phase 2 exit gate):
  frontmatter  portable keys only (name, description, license, compatibility, metadata); name == folder;
               kebab-case; description <= 1024 (warn > 500); metadata.version is a quoted semver string;
               metadata.kind/status recommended; UTF-8 without BOM.
  description  warns on workflow-summary heuristics (numbered steps, 'first ... then ... finally', arrow
               chains) and when Hebrew trigger phrases or a NOT-for exclusion are missing.
  body         line budget: warn > 180, fail > 300.
  references   every markdown link / references|scripts|evals path / agent-content path mentioned in
               SKILL.md resolves; every references/* file is mentioned either on a line that says "load when"
               or under a heading that contains "load when" (e.g. "## References (load when)");
               orphan references fail.
  evals        evals/triggers.jsonl: >= 8 should-trigger incl. Hebrew, >= 4 should-not incl. Hebrew, schema
               {prompt, should_trigger, route_instead}, no mojibake; evals/tasks.md: >= 3 task headings
               (## Task 1 / ## T1 / ## משימה 1 ...) each with setup, oracle and pass criteria.
  privacy      every file in the skill folder goes through scan_private + scan_secrets patterns.
No skills found -> NOT_RUN (never PASS). The client-name denylist part is reported NOT_RUN (non-blocking
here) when scripts/private_denylist.txt is absent; scan_private.py is the authoritative gate for it.
Exit codes: 0 pass/warn/not_run, 1 fail, 2 usage, 3 not_run with --strict.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _avc_common as C  # noqa: E402
import scan_private  # noqa: E402
import scan_secrets  # noqa: E402

ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata"}
DESC_WARN = 500
DESC_FAIL = 1024
BODY_WARN = 180
BODY_FAIL = 300
NAME_MAX = 64

LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMG_RE = re.compile(r"\!\[[^\]]*\]\(([^)\s]+)\)")
MENTION_RE = re.compile(r"(?<![\w/.-])((?:references|scripts|evals)/[\w.\-/]+\.[A-Za-z0-9]+)")
REPO_PATH_RE = re.compile(r"(?<![\w/.-])(agent-content/[\w.\-/]+)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LOAD_WHEN_RE = re.compile(r"(?i)load[- ]when")
TASK_HEADING_RE = re.compile(r"^#{2,4}\s*(?:task|eval|case|scenario|t\d+|e\d+|משימה|תרחיש|בדיקה)\b", re.IGNORECASE)
NOT_FOR_RE = re.compile(r"(?i)\bnot for\b|\bnot to\b|\bdo not use\b|\bdon't use\b|לא ל")
STEP_PATTERNS = (
    re.compile(r"(?m)(?:^|\s)\(?1[.)]\s+\S.*?(?:\s|^)\(?2[.)]\s+\S", re.S),
    re.compile(r"(?i)\bstep\s*[1-9]\b"),
    re.compile(r"(?i)\bfirst\b.{0,120}\bthen\b.{0,160}\b(?:finally|lastly|next)\b", re.S),
    re.compile(r"(?:→|->|=>).{0,60}(?:→|->|=>).{0,60}(?:→|->|=>)", re.S),
)


def _fenced_line_numbers(lines: list[str]) -> set[int]:
    fenced: set[int] = set()
    inside = False
    for idx, line in enumerate(lines):
        if FENCE_RE.match(line):
            inside = not inside
            fenced.add(idx)
            continue
        if inside:
            fenced.add(idx)
    return fenced


def _clean_ref(raw: str) -> str:
    ref = raw.split("#", 1)[0].split("?", 1)[0]
    return ref.rstrip(".,;:)]}'\"`")


def _is_placeholder(ref: str) -> bool:
    return any(ch in ref for ch in "<>{}*|…") or "..." in ref


def check_frontmatter(skill_dir: Path, skill_md: Path, text: str, report: C.Report, rel: str) -> tuple[dict | None, str, int]:
    name = skill_dir.name
    if C.has_bom(skill_md):
        report.fail("skill-bom", "SKILL.md must be UTF-8 without BOM", rel)
    try:
        fm, body, body_line = C.parse_frontmatter(text)
    except C.FrontmatterError as exc:
        report.fail("frontmatter-parse", str(exc), rel)
        return None, text, 1
    if fm is None:
        report.fail("frontmatter-missing", "SKILL.md must start with a --- frontmatter block", rel)
        return None, text, 1
    extra = set(fm) - ALLOWED_KEYS
    if extra:
        report.fail("frontmatter-keys", f"non-portable frontmatter key(s): {', '.join(sorted(extra))} (allowed: name, description, license, compatibility, metadata)", rel)
    declared = fm.get("name")
    if not isinstance(declared, str) or not declared.strip():
        report.fail("name-missing", "frontmatter 'name' is required", rel)
    else:
        if declared != name:
            report.fail("name-folder", f"name '{declared}' must equal the folder name '{name}'", rel)
        if not C.KEBAB_RE.match(declared) or len(declared) > NAME_MAX:
            report.fail("name-kebab", f"name must be lowercase-hyphen and <= {NAME_MAX} chars", rel)
    if not C.KEBAB_RE.match(name):
        report.fail("folder-kebab", "skill folder name must be lowercase-hyphen", rel)
    description = fm.get("description")
    if not isinstance(description, str) or not description.strip():
        report.fail("description-missing", "frontmatter 'description' is required", rel)
    else:
        flat = " ".join(description.split())
        if len(flat) > DESC_FAIL:
            report.fail("description-too-long", f"description is {len(flat)} chars (hard limit {DESC_FAIL})", rel)
        elif len(flat) > DESC_WARN:
            report.warn("description-long", f"description is {len(flat)} chars (target <= {DESC_WARN})", rel)
        for pattern in STEP_PATTERNS:
            if pattern.search(flat):
                report.warn("description-workflow", "description looks like a workflow summary (numbered steps / first-then-finally / arrow chain); agents follow descriptions instead of the body", rel)
                break
        if not C.has_hebrew(flat):
            report.warn("description-hebrew", "description has no Hebrew trigger phrases", rel)
        if not NOT_FOR_RE.search(flat):
            report.warn("description-not-for", "description has no NOT-for exclusion routing to a sibling skill", rel)
        if C.MOJIBAKE_RE.search(flat):
            report.fail("description-mojibake", "description contains mis-decoded Hebrew", rel)
    for key in ("license", "compatibility"):
        if key in fm and not isinstance(fm[key], str):
            report.fail("frontmatter-type", f"'{key}' must be a string", rel)
    meta = fm.get("metadata")
    if meta is None:
        report.fail("metadata-missing", "metadata (with version) is required", rel)
    elif not isinstance(meta, dict):
        report.fail("metadata-type", "metadata must be a mapping", rel)
    else:
        version = meta.get("version")
        if not isinstance(version, str) or not C.SEMVER_RE.match(str(version)):
            report.fail("metadata-version", "metadata.version must be a semver string such as \"0.1.0\"", rel)
        elif isinstance(version, C.PlainStr):
            report.warn("metadata-version-quote", "quote metadata.version so YAML keeps it a string", rel)
        for key in ("kind", "status"):
            if key not in meta:
                report.warn(f"metadata-{key}", f"metadata.{key} is recommended", rel)
        for key, value in meta.items():
            if isinstance(value, (dict, list)):
                report.warn("metadata-nested", f"metadata.{key} should be a scalar for portability", rel)
    return fm, body, body_line


def check_body(body: str, body_line: int, report: C.Report, rel: str, skill_dir: Path, root: Path) -> None:
    lines = body.split("\n")
    count = len(lines) if body.strip() else 0
    while count and not lines[count - 1].strip():
        count -= 1
    report.stats.setdefault("body_lines", {})[skill_dir.name] = count
    if count > BODY_FAIL:
        report.fail("body-too-long", f"body is {count} lines (hard limit {BODY_FAIL}); move tables/examples to references/", rel)
    elif count > BODY_WARN:
        report.warn("body-long", f"body is {count} lines (target <= {BODY_WARN})", rel)
    fenced = _fenced_line_numbers(lines)
    mentioned_refs: dict[str, bool] = {}
    heading_load_when = False
    for idx, line in enumerate(lines):
        if idx in fenced:
            continue
        if line.startswith("#"):
            heading_load_when = bool(LOAD_WHEN_RE.search(line))
        number = body_line + idx
        candidates: list[tuple[str, str]] = []
        for match in LINK_RE.finditer(line):
            ref = match.group(1)
            if re.match(r"^(?:[a-z][a-z0-9+.-]*:|#|//)", ref, re.IGNORECASE):
                continue
            candidates.append(("link", ref))
        for match in IMG_RE.finditer(line):
            ref = match.group(1)
            if not re.match(r"^(?:[a-z][a-z0-9+.-]*:|#)", ref, re.IGNORECASE):
                candidates.append(("link", ref))
        for match in MENTION_RE.finditer(line):
            candidates.append(("mention", match.group(1)))
        for match in REPO_PATH_RE.finditer(line):
            candidates.append(("repo", match.group(1)))
        seen: set[str] = set()
        for kind, raw in candidates:
            ref = _clean_ref(raw)
            if not ref or ref in seen or _is_placeholder(ref):
                continue
            seen.add(ref)
            if kind == "repo":
                target = root / ref
            else:
                target = skill_dir / ref
            if kind != "repo" and not target.exists() and (root / ref).exists():
                target = root / ref  # e.g. repo-level scripts/... mentioned from a skill
            if not target.exists():
                report.fail("reference-missing", f"'{ref}' does not resolve", rel, number)
                continue
            posix = ref.replace("\\", "/")
            own_prefix = f"agent-content/skills/{skill_dir.name}/"
            local = posix[len(own_prefix):] if posix.startswith(own_prefix) else (posix if kind != "repo" else None)
            if local and local.startswith("references/"):
                has_when = heading_load_when or bool(LOAD_WHEN_RE.search(line))
                mentioned_refs[local] = mentioned_refs.get(local, False) or has_when
    ref_dir = skill_dir / "references"
    if ref_dir.is_dir():
        for path in sorted(ref_dir.rglob("*")):
            if path.is_file():
                local = path.relative_to(skill_dir).as_posix()
                if local not in mentioned_refs:
                    report.fail("reference-orphan", f"'{local}' is never mentioned in SKILL.md (list it under a '## References (load when)' heading or on a 'load when:' line)", rel)
    for local, has_when in sorted(mentioned_refs.items()):
        if not has_when:
            report.fail("reference-load-when", f"'{local}' has no 'load when' condition (put it on the line or under a heading containing 'load when')", rel)


def check_evals(skill_dir: Path, report: C.Report, root: Path, known: set[str]) -> None:
    triggers = skill_dir / "evals" / "triggers.jsonl"
    rel_t = triggers.relative_to(root).as_posix() if triggers.is_relative_to(root) else str(triggers)
    if not triggers.is_file():
        report.fail("evals-triggers-missing", "evals/triggers.jsonl is required (>= 8 positive incl. Hebrew, >= 4 negative incl. Hebrew)", rel_t)
    else:
        try:
            text = triggers.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            report.fail("evals-triggers-encoding", "triggers.jsonl is not valid UTF-8", rel_t)
            text = ""
        issues, counts = C.validate_trigger_text(text, known)
        for level, code, message, line in issues:
            (report.fail if level == "FAIL" else report.warn)(code, message, rel_t, line)
        report.stats.setdefault("trigger_counts", {})[skill_dir.name] = f"{counts['positive']}/{counts['negative']}"
    tasks = skill_dir / "evals" / "tasks.md"
    rel_k = tasks.relative_to(root).as_posix() if tasks.is_relative_to(root) else str(tasks)
    if not tasks.is_file():
        report.fail("evals-tasks-missing", "evals/tasks.md is required (>= 3 task evals with setup, oracle artifact, pass criteria)", rel_k)
        return
    ttext = tasks.read_bytes().decode("utf-8", errors="replace")
    sections: list[list[str]] = []
    for line in ttext.split("\n"):
        if TASK_HEADING_RE.match(line):
            sections.append([line])
        elif sections:
            sections[-1].append(line)
    report.stats.setdefault("task_counts", {})[skill_dir.name] = len(sections)
    if len(sections) < 3:
        report.fail("evals-tasks-count", f"{len(sections)} task heading(s) found; need >= 3 (headings like '## Task 1: ...', '## T1', '## משימה 1')", rel_k)
    for section in sections:
        blob = "\n".join(section).lower()
        title = section[0].strip()[:60]
        for word, labels in (("setup", ("setup", "הגדרה")), ("oracle", ("oracle", "אורקל")), ("pass", ("pass", "קריטריון", "עבר"))):
            if not any(label in blob for label in labels):
                report.warn("evals-task-field", f"task '{title}' does not mention {word}", rel_k)


def check_privacy(skill_dir: Path, root: Path, report: C.Report, denylist) -> None:
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
        text = C.read_scan_text(path)
        if text is None:
            continue
        scan_private.scan_path_patterns(rel, report, denylist)
        scan_private.scan_text_patterns(rel, text, report)
        scan_private.scan_denylist_text(rel, text, report, denylist)
        scan_secrets.scan_file_name(rel, report, [])
        scan_secrets.scan_text(rel, text, report, [])


def run(root: Path, skills_dir: Path | None = None, only: list[str] | None = None, private_scan: bool = True) -> C.Report:
    report = C.Report("check_skills")
    skills_root = skills_dir or (root / "agent-content" / "skills")
    known = C.skill_names(skills_root)
    candidates = sorted(p for p in skills_root.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))) if skills_root.is_dir() else []
    if only:
        candidates = [p for p in candidates if p.name in only]
    if not candidates:
        report.not_run("skills", "no skills found under agent-content/skills (nothing to check)")
        return report
    denylist: list = []
    if private_scan:
        try:
            denylist, reason = scan_private.load_denylist(scan_private.resolve_denylist_path(root, None))
        except ValueError as exc:
            denylist, reason = [], None
            report.fail("denylist-invalid", str(exc))
        if reason:
            report.not_run("client-denylist", reason + " (run scripts/scan_private.py for the authoritative result)", blocking=False)
    for skill_dir in candidates:
        rel = (skill_dir / "SKILL.md").relative_to(root).as_posix() if skill_dir.is_relative_to(root) else f"{skill_dir.name}/SKILL.md"
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            report.fail("skill-md-missing", "folder has no SKILL.md", rel)
            continue
        text = skill_md.read_bytes().decode("utf-8", errors="replace")
        fm, body, body_line = check_frontmatter(skill_dir, skill_md, text, report, rel)
        check_body(body, body_line, report, rel, skill_dir, root)
        check_evals(skill_dir, report, root, known)
        openai = skill_dir / "agents" / "openai.yaml"
        if openai.is_file() and re.search(r"(?m)^\s*allow_implicit_invocation:\s*true\b", openai.read_text(encoding="utf-8", errors="replace")):
            report.warn("implicit-invocation", "agents/openai.yaml enables implicit invocation; keep it disabled until the discovery experiment (E05) ran", openai.relative_to(root).as_posix() if openai.is_relative_to(root) else "agents/openai.yaml")
        if private_scan:
            check_privacy(skill_dir, root, report, denylist)
    report.stats["skills"] = len(candidates)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic checks for agent-content/skills/*/SKILL.md and their evals.")
    C.add_common_args(parser)
    parser.add_argument("--skills-dir", default=None, help="skills directory (default <root>/agent-content/skills)")
    parser.add_argument("--only", nargs="+", default=None, metavar="NAME", help="check only these skill folders")
    parser.add_argument("--no-private-scan", action="store_true", help="skip the private/secret pattern scan of skill files")
    return parser


def main(argv: list[str] | None = None) -> int:
    C.setup_utf8()
    args = build_parser().parse_args(argv)
    root = C.resolve_root(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root.name}", file=sys.stderr)
        return C.EXIT_USAGE
    skills_dir = Path(args.skills_dir).resolve() if args.skills_dir else None
    report = run(root, skills_dir, args.only, private_scan=not args.no_private_scan)
    return C.emit(report, args.json, args.strict, args.warnings_as_errors)


if __name__ == "__main__":
    sys.exit(main())

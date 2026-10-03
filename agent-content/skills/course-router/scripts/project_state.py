#!/usr/bin/env python3
"""Report which phase a video project is in, so the router can resume it.

Usage:
  python project_state.py PROJECT_DIR          # one project -> JSON on stdout
  python project_state.py --root PROJECTS_DIR  # every subfolder that looks like a project
  python project_state.py --self-check         # run the built-in tests

Reads the folder only; writes nothing. Exit codes: 0 ok, 2 path not found / nothing to read
(fail closed: a missing folder never reports a phase), 1 self-check failure.

Conventions it reads (see course-router/references/route-table.md section 5):
  hf/BRIEF.md, hf/PROMPT.md, hf/CHANGELOG.md (hf/LEDGER.md is accepted as an intake-time ledger file)
  hf/PROMPT.md holding only the <ledger> block is still INTAKE; it counts as a drafted PROMPT only once
  it contains a <structure> block (the frame-by-frame spec)
  a line "PROMPT_APPROVED <date>" in hf/CHANGELOG.md  -> prompt approved
  "## Round N" sections in hf/CHANGELOG.md; a line "PRESENTED" closes the section
  _work/drafts/*.mp4 (drafts), final/*.mp4 + final/manifest.json (delivered)
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

VERSION = "0.1.0"
OWNER = {
    "scaffolded": "video-intake",
    "no_project": "video-intake",
    "intake_open": "video-intake",
    "prompt_drafted": "video-intake (get PROMPT.md approved) then the type skill",
    "prompt_approved": "the type skill (edit-*)",
    "in_review": "revision-round",
    "delivered": "revision-round (notes) or multi-video-variants (derivatives)",
}
ROUND_RE = re.compile(r"^##\s+(?:Round|סבב)\s+(\d+)", re.I | re.M)


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _count(p: Path, pattern: str) -> int:
    return len(list(p.glob(pattern))) if p.is_dir() else 0


def inspect(project: Path) -> dict:
    hf = project / "hf"
    files = {
        name: (hf / name).is_file()
        for name in ("BRIEF.md", "LEDGER.md", "PROMPT.md", "DESIGN.md", "CHANGELOG.md", "QA.md")
    }
    changelog = _read(hf / "CHANGELOG.md")
    prompt_text = _read(hf / "PROMPT.md")
    has_spec = "<structure>" in prompt_text
    has_ledger = "<ledger>" in prompt_text or files["LEDGER.md"]
    approved = bool(re.search(r"^\s*PROMPT_APPROVED\b", changelog, re.M))
    rounds = ROUND_RE.findall(changelog)
    round_open = False
    if rounds:
        last = ROUND_RE.split(changelog)[-1]  # text after the last round heading
        round_open = not re.search(r"^\s*PRESENTED\b", last, re.M)
    drafts = _count(project / "_work" / "drafts", "*.mp4")
    finals = _count(project / "final", "*.mp4")
    manifest = (project / "final" / "manifest.json").is_file()

    if round_open:
        state = "in_review"
    elif manifest:
        state = "delivered"
    elif drafts:
        state = "in_review"
    elif approved and has_spec:
        state = "prompt_approved"
    elif has_spec:
        state = "prompt_drafted"
    elif files["BRIEF.md"] or files["LEDGER.md"] or files["PROMPT.md"]:
        state = "intake_open"
    elif hf.is_dir() or (project / "source").is_dir():
        state = "scaffolded"
    else:
        state = "no_project"
    return {
        "tool": "project_state",
        "version": VERSION,
        "status": "ok",
        "path": str(project),
        "state": state,
        "suggested_owner": OWNER[state],
        "prompt": "approved" if approved and has_spec else ("drafted" if has_spec else "none"),
        "ledger_present": bool(has_ledger),
        "files": files,
        "rounds": len(rounds),
        "round_open": round_open,
        "drafts": drafts,
        "finals": finals,
        "manifest": manifest,
        "note": "prompt=approved only from a PROMPT_APPROVED line; otherwise confirm with the user",
    }


def scan_root(root: Path) -> dict:
    items = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if (child / "hf").is_dir() or (child / "source").is_dir() or (child / "final").is_dir():
            items.append(inspect(child))
    return {"tool": "project_state", "version": VERSION, "status": "ok", "root": str(root), "projects": items}


def _self_check() -> int:
    failures = []

    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        check("empty dir is no_project", inspect(root / "nothing")["state"] == "no_project")
        p = root / "a"
        (p / "hf").mkdir(parents=True)
        check("hf only is scaffolded", inspect(p)["state"] == "scaffolded")
        (p / "hf" / "BRIEF.md").write_text("x", encoding="utf-8")
        check("brief is intake_open", inspect(p)["state"] == "intake_open")
        (p / "hf" / "PROMPT.md").write_text("<ledger>\n| ID |\n</ledger>\n", encoding="utf-8")
        r = inspect(p)
        check("PROMPT with only a ledger is still intake", r["state"] == "intake_open" and r["prompt"] == "none" and r["ledger_present"])
        (p / "hf" / "PROMPT.md").write_text("<ledger></ledger>\n<structure>f0-30</structure>\n", encoding="utf-8")
        r = inspect(p)
        check("PROMPT with a structure block and no approval is drafted", r["state"] == "prompt_drafted" and r["prompt"] == "drafted")
        (p / "hf" / "CHANGELOG.md").write_text("PROMPT_APPROVED 2026-10-02\n", encoding="utf-8")
        r = inspect(p)
        check("approval line detected", r["state"] == "prompt_approved" and r["prompt"] == "approved")
        (p / "hf" / "CHANGELOG.md").write_text(
            "PROMPT_APPROVED 2026-10-02\n## Round 1 (2026-10-03)\n1. note\n", encoding="utf-8")
        r = inspect(p)
        check("open round is in_review", r["state"] == "in_review" and r["round_open"])
        (p / "hf" / "CHANGELOG.md").write_text(
            "PROMPT_APPROVED 2026-10-02\n## Round 1 (2026-10-03)\n1. note\nPRESENTED 2026-10-03\n", encoding="utf-8")
        check("closed round, no drafts is prompt_approved", inspect(p)["state"] == "prompt_approved")
        (p / "final").mkdir()
        (p / "final" / "manifest.json").write_text("{}", encoding="utf-8")
        check("manifest is delivered", inspect(p)["state"] == "delivered")
        (p / "hf" / "CHANGELOG.md").write_text("## סבב 2 (2026-10-04)\n1. הערה\n", encoding="utf-8")
        check("hebrew round heading opens a round", inspect(p)["state"] == "in_review")
        (root / "b" / "source").mkdir(parents=True)
        scan = scan_root(root)
        check("scan finds both projects", {x["path"] for x in scan["projects"]} == {str(p), str(root / "b")})
    for f in failures:
        print("FAIL:", f)
    print("self-check:", "FAILED" if failures else "ok")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return _self_check()
    if len(argv) >= 2 and argv[0] == "--root":
        root = Path(argv[1])
        if not root.is_dir():
            print(json.dumps({"tool": "project_state", "status": "not_run", "reason": f"not a folder: {root}"}))
            return 2
        print(json.dumps(scan_root(root), ensure_ascii=False, indent=2))
        return 0
    if len(argv) == 1 and not argv[0].startswith("-"):
        project = Path(argv[0])
        if not project.is_dir():
            print(json.dumps({"tool": "project_state", "status": "not_found", "path": str(project)}))
            return 2
        print(json.dumps(inspect(project), ensure_ascii=False, indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Synthetic repository builders used by tests/unit/test_scripts_*.py (not a user-facing tool).

Usage: library module; import and call make_repo(tmp_path) / make_skill(root, name). Everything it writes is
original synthetic text (including real Hebrew) so the checks can be exercised with positive and negative
controls without touching any real repository content.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

DESCRIPTION = (
    "Cut and caption a talking-head clip into a vertical reel. Use for עריכת וידאו, תערוך לי סרטון, "
    "caption this clip. NOT for colour grading (use color-fix) or for writing prompts (use prompt-writer)."
)

HEBREW_POSITIVE = [
    "תערוך לי רילס מהסרטון הזה",
    "תוסיף כתוביות בעברית לסרטון של הדובר",
    "אני צריך עריכת וידאו לסרטון תדמית של דובר",
]
EN_POSITIVE = [
    "Edit this talking-head clip into a vertical reel",
    "Add Hebrew captions to the speaker video",
    "Cut the pauses out of this interview and caption it",
    "Make a 30 second reel from this selfie footage",
    "Rough cut my speaker clip and burn in subtitles",
]
HEBREW_NEGATIVE = ["תקן לי את הצבע של העור בסרטון", "תכתוב לי פרומפט ל-Seedance"]
EN_NEGATIVE = ["Colour grade the skin tones of this clip", "Write a Seedance prompt for a car ad", "What is the capital of France?"]


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return path


def triggers_text(positive: int = 8, negative: int = 4, hebrew: bool = True) -> str:
    pos = (HEBREW_POSITIVE + EN_POSITIVE)[:positive] if hebrew else EN_POSITIVE[:positive]
    neg = (HEBREW_NEGATIVE + EN_NEGATIVE)[:negative] if hebrew else EN_NEGATIVE[:negative]
    lines = [json.dumps({"prompt": p, "should_trigger": True, "route_instead": None}, ensure_ascii=False) for p in pos]
    lines += [
        json.dumps({"prompt": p, "should_trigger": False, "route_instead": "color-fix" if i % 2 == 0 else None}, ensure_ascii=False)
        for i, p in enumerate(neg)
    ]
    return "\n".join(lines) + "\n"


def tasks_text(count: int = 3) -> str:
    parts = ["# Task evals\n"]
    for n in range(1, count + 1):
        parts.append(
            f"## Task {n}: synthetic clip {n}\n\n- Setup: a 10 s synthetic clip with a Hebrew caption.\n"
            f"- Oracle artifact: final/clip_{n}.mp4 plus qa.json.\n- Pass criteria: every gate passes with evidence.\n"
        )
    return "\n".join(parts)


def skill_text(
    name: str,
    description: str = DESCRIPTION,
    extra_frontmatter: str = "",
    body_lines: int = 30,
    refs: tuple[str, ...] = ("references/guide.md",),
    ref_line_suffix: str = " - load when: you need the detailed gate table",
    version_line: str = 'version: "0.1.0"',
) -> str:
    if description.startswith(">-"):
        desc_block = description
    else:
        desc_block = ">-\n  " + description
    fm = (
        "---\n"
        f"name: {name}\n"
        f"description: {desc_block}\n"
        "license: LicenseRef-owner-undecided\n"
        f"{extra_frontmatter}"
        "metadata:\n"
        f"  {version_line}\n"
        "  kind: owner\n"
        '  status: "specified; deterministic checks only; model eval not run"\n'
        "---\n"
    )
    body = [f"# {name}", "", "Scope, spend and evidence rules come first. A timeout never passes.", ""]
    body += [f"- rule {i}: keep it measurable." for i in range(body_lines)]
    body += ["", "## References"]
    for ref in refs:
        body.append(f"- `{ref}`{ref_line_suffix}")
    return fm + "\n".join(body) + "\n"


def make_skill(
    root: Path,
    name: str = "demo-skill",
    *,
    references: tuple[str, ...] = ("references/guide.md",),
    positive: int = 8,
    negative: int = 4,
    tasks: int = 3,
    with_triggers: bool = True,
    with_tasks: bool = True,
    **skill_kwargs,
) -> Path:
    skill_dir = root / "agent-content" / "skills" / name
    refs = skill_kwargs.pop("refs", references)
    write(skill_dir / "SKILL.md", skill_text(name, refs=refs, **skill_kwargs))
    for ref in references:
        write(skill_dir / ref, f"# {Path(ref).stem}\n\nOriginal synthetic reference text.\n")
    if with_triggers:
        write(skill_dir / "evals" / "triggers.jsonl", triggers_text(positive, negative))
    if with_tasks:
        write(skill_dir / "evals" / "tasks.md", tasks_text(tasks))
    return skill_dir


def make_docs_pair(root: Path, ids_en: tuple[str, ...] = ("install-01", "install-02"), ids_he: tuple[str, ...] | None = None,
                   name: str = "install.md") -> None:
    ids_he = ids_en if ids_he is None else ids_he
    en = "# Install\n\n" + "".join(f"<!-- step: {i} -->\nRun the command {n}.\n\n" for n, i in enumerate(ids_en, 1))
    he = "# התקנה\n\n" + "".join(f"<!-- step: {i} -->\nהריצו את הפקודה {n}.\n\n" for n, i in enumerate(ids_he, 1))
    write(root / "docs" / "en" / name, en)
    write(root / "docs" / "he" / name, he)


def make_tool(root: Path, name: str = "frame_qa", usage: str = "python tools/frame_qa.py INPUT.mp4 [--json]") -> Path:
    return write(
        root / "tools" / f"{name}.py",
        f'"""Decode every frame and report defects.\n\nUsage: {usage}\n"""\n\nprint("stub")\n',
    )


def make_repo(root: Path, skills: tuple[str, ...] = ("demo-skill", "second-skill")) -> Path:
    """A minimal, fully valid synthetic repository."""
    for name in skills:
        make_skill(root, name)
    write(root / "agent-content" / "playbooks" / "wf-00-intake.md", "# wf-00 intake\n\nAsk until the brief is precise.\n")
    write(root / "agent-content" / "playbooks" / "wf-01-build.md", "# wf-01 build\n\nBuild from the approved PROMPT.md.\n")
    make_tool(root)
    make_docs_pair(root)
    write(root / "README.md", "# Demo\n\nSee [install](docs/en/install.md) and `agent-content/playbooks/wf-00-intake.md`.\n")
    write(root / "licenses.toml", LICENSES_TOML)
    return root


LICENSES_TOML = """schema = 1

[[rule]]
glob = "**"
origin = "owner"
licence = "owner-undecided"
note = "synthetic test repository"
allow = ["image"]
"""


def run_cli(script: Path | str, *args: object, cwd: Path | None = None, timeout: int = 180) -> subprocess.CompletedProcess:
    """Run a script exactly like a user would (separate interpreter, UTF-8 forced, no bytecode files)."""
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("AVC_PRIVATE_DENYLIST", None)
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(script), *[str(a) for a in args]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
    )

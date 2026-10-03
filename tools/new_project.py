"""new_project - scaffold ``<work_root>/projects/<slug>/{source,hf,final,_work}`` under an ASCII work root.

* The folder name is an ASCII slug of the (Hebrew) title; the display title lives in ``project.json`` (never in a folder name).
* Source files are COPIED (never moved or renamed) into ``source/`` and verified (size + SHA-256). A failed verification is
  reported and the tool exits non-zero (the original script once stopped on ``rmdir ... busy`` without copying).
* ``hf/`` receives the BRIEF.md and DESIGN.md templates from ``agent-content/techniques/templates/`` (never overwritten if present).
* ``--init-hyperframes`` runs ``npx hyperframes init`` in ``hf/`` (needs Node and the network; opt-in; only ever under an ASCII path:
  ``init`` silently skips index.html under Hebrew paths).
* The work root comes from --work-root, ``AVC_PATHS_WORK_ROOT`` or ``[paths] work_root`` in toolkit.toml. With none set the tool
  refuses and proposes an ASCII folder instead of guessing one.

Usage:
    python tools/new_project.py "<title>" [--work-root DIR] [--copy FILE_OR_DIR ...] [--slug name] [--init-hyperframes] [--json]
Exit: 0 created and verified, 2 refused / verification failed, 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import _common  # noqa: F401


def default_proposal() -> str:
    return "C:\\avc-work" if os.name == "nt" else str(Path.home() / "avc-work")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="new_project", description=__doc__.split("\n\n")[0])
    ap.add_argument("title")
    ap.add_argument("--work-root")
    ap.add_argument("--slug")
    ap.add_argument("--copy", nargs="*", default=[], help="source files/folders to COPY into source/")
    ap.add_argument("--init-hyperframes", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    from core.config import load_config
    from core.envelope import sha256_file
    from core.errors import ToolkitError
    from core.fsio import fs_path
    from core.paths import project_paths

    try:
        cfg = load_config()
        cfg_root = cfg.path("paths.work_root")
        wr = args.work_root or os.environ.get("AVC_PATHS_WORK_ROOT") or (str(cfg_root) if cfg_root else "")
        if not wr:
            print(f"new_project: no work root configured. Choose an ASCII folder (e.g. {default_proposal()}) and pass --work-root or set AVC_PATHS_WORK_ROOT.", file=sys.stderr)
            return 2
        pp = project_paths(wr, args.title, slug=args.slug, folders=cfg.output_names())
        if (pp.root / "project.json").exists():
            existing = pp.title_from_disk()
            if existing != args.title:
                print(f"new_project: slug {pp.slug!r} already belongs to project {existing!r}; pass --slug to choose another", file=sys.stderr)
                return 2
        pp.ensure()
        tpl = Path(__file__).resolve().parents[1] / "agent-content" / "techniques" / "templates"
        for name in ("BRIEF.md", "DESIGN.md"):
            dst = pp.hf / name
            if (tpl / name).is_file() and not dst.exists():
                shutil.copyfile(tpl / name, dst)
        (pp.hf / "fonts").mkdir(exist_ok=True)
        (pp.hf / "assets").mkdir(exist_ok=True)
        copied, failed = [], []
        for item in args.copy:
            src = Path(item)
            if not src.exists():
                failed.append({"file": item, "why": "not found"})
                continue
            files = [src] if src.is_file() else [p for p in src.rglob("*") if p.is_file()]
            for f in files:
                rel = Path(f.name) if src.is_file() else f.relative_to(src)
                dst = pp.source / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    failed.append({"file": str(f), "why": "destination exists (never overwritten)"})
                    continue
                shutil.copy2(fs_path(f), fs_path(dst))
                if dst.stat().st_size == f.stat().st_size and sha256_file(dst) == sha256_file(f):
                    copied.append({"file": str(f), "to": str(dst)})
                else:
                    failed.append({"file": str(f), "why": "verification failed (size/hash differ)"})
        init = None
        if args.init_hyperframes:
            from core.procs import run

            npx = shutil.which("npx")
            if not npx:
                init = {"ok": False, "why": "npx not found (install Node.js LTS)"}
            else:
                r = run([npx, "hyperframes", "init", "."], cwd=pp.hf, timeout=300)
                init = {"ok": r.returncode == 0 and (pp.hf / "index.html").exists(), "exit": r.returncode, "index_html_created": (pp.hf / "index.html").exists()}
        report = {"slug": pp.slug, "title": args.title, "root": str(pp.root), "source": str(pp.source), "hf": str(pp.hf), "final": str(pp.final), "work": str(pp.work), "copied": copied, "failed": failed, "hyperframes_init": init}
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"created {pp.root}\n  copied {len(copied)} file(s), {len(failed)} failed" + (f"\n  hyperframes init: {init}" if init else ""))
        return 2 if failed or (init is not None and not init.get("ok")) else 0
    except ToolkitError as exc:
        print(f"new_project: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""Shared bootstrap for every tool in ``tools/`` (not a tool itself).

Puts ``<repo>/src`` on ``sys.path`` so ``import core`` works when a tool is run as a plain script, forces UTF-8 stdio,
and offers two helpers used by all QA tools: ``qa_main`` (parse -> run -> emit the fail-closed envelope -> exit code)
and ``load_config_safe``.  Importing this module is cheap: nothing heavy is imported until a tool actually runs, so
``--help`` stays well under one second (E04-L01).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

TOOLS_VERSION = "0.1.0"


def qa_main(tool: str, run, input_path, *, min_coverage: float = 1.0, out_json: str | None = None) -> int:
    """Run ``run(builder)`` under the crash guard, print the envelope, optionally save it, return the exit code."""
    from core.envelope import emit, guarded

    env = guarded(tool, TOOLS_VERSION, run, input_path, min_coverage=min_coverage)
    if out_json:
        from core.fsio import write_json_atomic

        write_json_atomic(out_json, env.to_dict())
    return emit(env)


def load_config_safe():
    """``Config`` from toolkit.toml; never raises (a broken config is reported by ``doctor``, not by every tool)."""
    try:
        from core.config import load_config

        return load_config()
    except Exception:  # noqa: BLE001
        return None

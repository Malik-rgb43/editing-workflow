"""Start-up latency (E04-L01): `--help` and the core import chain must stay far below one second, no heavy imports."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

SRC = str(Path(__file__).resolve().parents[2] / "src")
ENV = {**os.environ, "PYTHONPATH": SRC, "PYTHONUTF8": "1"}


def timed(args: list[str]) -> tuple[float, subprocess.CompletedProcess]:
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, *args], env=ENV, capture_output=True, timeout=60)
    return time.perf_counter() - t0, r


def test_help_is_under_one_second_and_prints_usage_lines():
    best = min(timed(["-m", "core", "--help"])[0] for _ in range(3))
    dt, r = timed(["-m", "core", "--help"])
    assert r.returncode == 0 and b"Usage:" in r.stdout and b"python -m core" in r.stdout
    assert best < 1.0, f"python -m core --help took {best:.2f}s (best of 3); E04-L01 budget is < 1 s"


def test_subcommand_help_is_fast_too():
    for sub in (["ledger", "--help"], ["lock", "--help"]):
        best = min(timed(["-m", "core", *sub])[0] for _ in range(3))
        assert best < 1.0, (sub, best)


def test_importing_every_core_module_loads_no_numpy_pillow_or_opencv():
    code = (
        "import sys, importlib\n"
        "for m in ('errors','fsio','paths','config','timebase','envelope','ledger','ffprobe','media','procs','lock'):\n"
        "    importlib.import_module('core.'+m)\n"
        "print(sorted(x for x in ('numpy','PIL','cv2','scipy','onnxruntime','faster_whisper','jsonschema') if x in sys.modules))\n"
    )
    r = subprocess.run([sys.executable, "-c", code], env=ENV, capture_output=True, text=True, timeout=60)
    assert r.stdout.strip() == "[]", r.stdout + r.stderr


def test_every_cli_entry_has_a_usage_line():
    core = Path(SRC) / "core"
    for name in ("__main__.py", "ledger.py", "lock.py", "paths.py", "config.py", "ffprobe.py", "envelope.py", "timebase.py", "fsio.py", "media.py", "procs.py", "errors.py"):
        text = (core / name).read_text(encoding="utf-8")
        assert "Usage:" in text.split('"""')[1] or "Usage:" in text, name

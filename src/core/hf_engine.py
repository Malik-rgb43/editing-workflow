"""Locate the HyperFrames engine that the toolkit pinned, and run it the same way everywhere.

Why this module exists (found by a live run, 2026-10-03):
* the tools used to call ``npx hyperframes ...`` from the project folder, which fetches *whatever version npm serves* (0.8.114 was
  served while the toolkit pins 0.8.98) and needs the network;
* when the engine is installed under a path with non-ASCII letters (a Windows user name in Hebrew), ``hyperframes init`` finishes
  without an error and without writing ``index.html``.

* (live run 2026-10-08) tools run from a git clone that has no ``node_modules`` fell through to ``npx --no-install hyperframes``
  with no version: npx asked for the newest release (0.8.141), refused, and render / Studio / ``init`` all failed, although the
  pinned engine sat in the installed toolkit home (``~/.avc/toolkit/node_modules``).

Search order for the engine: ``AVC_HYPERFRAMES_CLI`` (a ``.mjs``/``.js`` file or an executable) -> ``<toolkit root>/node_modules/hyperframes``
(the folder ``npm ci --ignore-scripts`` fills) -> the installed toolkit home(s) (from ``install-manifest.json``, then the installer's
default folders), only when they hold the pinned version -> ``npx --no-install hyperframes@<pin>`` (a local install of exactly the
pin, never a download; without a pin there is no npx fallback at all). Nothing here installs or downloads anything.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

ENV_CLI = "AVC_HYPERFRAMES_CLI"
# The engine and the toolkit must never phone home or reach out for skills on their own (ADR 0002 privacy rule, AGENTS.md).
ENGINE_ENV = {"HYPERFRAMES_NO_TELEMETRY": "1", "HYPERFRAMES_SKIP_SKILLS": "1", "DO_NOT_TRACK": "1"}


class EngineMissing(RuntimeError):
    """Raised when no HyperFrames engine can be found without downloading it."""


@dataclass(frozen=True)
class Engine:
    argv: tuple  # command prefix, e.g. ("node", ".../hyperframes.mjs")
    source: str  # "env" | "toolkit" | "project-local"
    version: str | None  # read from the package.json of the installed package (no process is started)
    pinned: str | None  # exact version in <toolkit root>/package.json, if any
    root: Path | None  # folder holding node_modules, if known


def toolkit_root() -> Path:
    """The folder this checkout / installed toolkit lives in (``src/core/hf_engine.py`` -> two levels up)."""
    return Path(__file__).resolve().parents[2]


def pinned_version(root: Path | None = None) -> str | None:
    """Exact ``hyperframes`` version from ``package.json`` (``None`` when absent or not an exact pin)."""
    try:
        data = json.loads(((root or toolkit_root()) / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    spec = (data.get("dependencies") or {}).get("hyperframes")
    return spec if isinstance(spec, str) and spec[:1].isdigit() else None


def installed_version(root: Path) -> str | None:
    try:
        return json.loads((root / "node_modules" / "hyperframes" / "package.json").read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None


def installed_homes() -> list:
    """Toolkit homes the installer may have filled (``install/bootstrap.py``): the one recorded in ``~/.avc/install-manifest.json``,
    then its defaults ``~/.avc/toolkit`` and the ASCII fallback used when the home path has non-ASCII letters."""
    state = Path.home() / ".avc"
    out = []
    try:
        rec = json.loads((state / "install-manifest.json").read_text(encoding="utf-8")).get("paths", {}).get("toolkit_home")
        if rec:
            out.append(Path(rec))
    except (OSError, ValueError, AttributeError):
        pass
    out.append(state / "toolkit")
    base = os.environ.get("AVC_ASCII_BASE")
    if base:
        out.append(Path(base) / "avc-toolkit")
    elif os.name == "nt":
        out.append(Path("C:/avc-toolkit"))
    else:
        out += [Path("/Users", "Shared", "avc-toolkit"), Path("/var/tmp/avc-toolkit")]  # macOS shared folder / Linux (bootstrap.ascii_fallback)
    seen, uniq = set(), []
    for p in out:
        key = os.path.normcase(str(p))
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def is_ascii_path(p) -> bool:
    try:
        str(p).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def non_ascii_problem(engine: Engine) -> str | None:
    """A message when the engine path would make ``init`` silently skip files, else ``None``."""
    where = engine.root if engine.root else (Path(engine.argv[-1]) if engine.argv else None)
    if where is not None and not is_ascii_path(where):
        return (f"the HyperFrames engine is installed under a non-ASCII path ({where}): `hyperframes init` then ends without an error "
                "and without writing index.html. Re-run `python install/bootstrap.py apply` (it picks an ASCII toolkit folder) or install with --home <ASCII folder>.")
    return None


def find(root: Path | None = None, env: dict | None = None) -> Engine | None:
    env = os.environ if env is None else env
    root = root or toolkit_root()
    node = shutil.which("node")
    forced = env.get(ENV_CLI)
    if forced:
        p = Path(forced)
        if p.suffix in (".mjs", ".js", ".cjs") and node:
            return Engine((node, str(p)), "env", None, pinned_version(root), None)
        exe = shutil.which(forced)
        if exe:
            return Engine((exe,), "env", None, pinned_version(root), None)
        return None
    pin = pinned_version(root)
    cli = root / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
    if cli.is_file() and node:
        return Engine((node, str(cli)), "toolkit", installed_version(root), pin, root)
    # A clone without node_modules: use the installed toolkit home, but only one that holds exactly the pinned version.
    for home in installed_homes() if node else ():
        cli = home / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
        ver = installed_version(home)
        if cli.is_file() and (pin is None or ver == pin):
            return Engine((node, str(cli)), "toolkit", ver, pin, home)
    npx = shutil.which("npx")
    if npx and pin:
        # A bare `hyperframes` makes npx want the newest release; `@<pin>` + --no-install only accepts a local copy of the pin.
        return Engine((npx, "--no-install", f"hyperframes@{pin}"), "project-local", None, pin, None)
    return None


def command(args: list, root: Path | None = None, env: dict | None = None) -> list:
    """Full argv for ``hyperframes <args>``; raises :class:`EngineMissing` when there is no engine (never falls back to a download)."""
    eng = find(root, env)
    if eng is None:
        raise EngineMissing("HyperFrames engine not found. Run `python install/bootstrap.py apply` (it runs `npm ci --ignore-scripts` in the toolkit folder) or install Node.js LTS first.")
    return list(eng.argv) + [str(a) for a in args]


def run_env(extra: dict | None = None) -> dict:
    out = dict(os.environ)
    out.update(ENGINE_ENV)
    if extra:
        out.update(extra)
    return out


def describe(root: Path | None = None) -> dict:
    """What ``doctor``/``verify`` report about the engine (no process is started)."""
    root = root or toolkit_root()
    eng = find(root)
    if eng is None:
        return {"found": False, "why": "no node/npx on PATH or no engine installed"}
    info = {"found": True, "source": eng.source, "version": eng.version, "pinned": eng.pinned, "argv": list(eng.argv)}
    info["version_matches_pin"] = bool(eng.version and eng.pinned and eng.version == eng.pinned) if eng.source == "toolkit" else None
    prob = non_ascii_problem(eng)
    if prob:
        info["problem"] = prob
    return info

"""``toolkit.toml`` loader: one file for every path the tools used to hard-code.

Resolution order (later wins): built-in structure (everything unset) < ``toolkit.toml`` < ``toolkit.local.toml``
< environment variables ``AVC_<SECTION>_<KEY>`` (e.g. ``AVC_PATHS_WORK_ROOT``).  ``AVC_CONFIG`` selects another file.

There are **no private defaults**: a value that was not configured is ``None`` and asking for it through
``Config.require_path`` raises a ``ConfigError`` that says exactly which key/env var to set. The only computed
defaults are per-user *state* locations (lock file, cache) derived from the OS environment, flagged with
``source == "default"`` so ``doctor`` can show them.

Relative paths in a file are resolved against the folder of that file; environment values against the current dir.

Usage:
    python -m core config            # show every resolved value and where it came from
    python -m core config --json
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigError
from .fsio import fs_path

__all__ = ["SCHEMA", "Value", "Config", "load_config", "find_config_file", "user_state_dir", "user_cache_dir"]

CONFIG_FILENAME = "toolkit.toml"
LOCAL_FILENAME = "toolkit.local.toml"

#: section -> key -> (kind, description). kind: "path" (filesystem path) | "name" (single folder name) | "exe"
SCHEMA: dict[str, dict[str, tuple[str, str]]] = {
    "paths": {
        "work_root": ("path", "ASCII folder that holds projects/<name>/"),
        "lock_path": ("path", "heavy-job lock file (one absolute shared path)"),
        "cache_dir": ("path", "download / model cache"),
        "camera_original_dir": ("path", "camera-original (4K) media used for baking"),
    },
    "models": {
        "matte_dir": ("path", "matte / segmentation model directory"),
        "asr_model_dir": ("path", "ASR model directory"),
        "asr_venv": ("path", "virtualenv holding the ASR runtime"),
    },
    "binaries": {
        "ffmpeg": ("exe", "ffmpeg executable (empty = PATH)"),
        "ffprobe": ("exe", "ffprobe executable (empty = PATH)"),
        "blender": ("exe", "Blender executable"),
    },
    "output": {
        "source_dir": ("name", "project source folder name"),
        "hf_dir": ("name", "project HyperFrames folder name"),
        "final_dir": ("name", "project deliverables folder name"),
        "work_dir": ("name", "project scratch folder name"),
    },
}

_OUTPUT_DEFAULTS = {"source_dir": "source", "hf_dir": "hf", "final_dir": "final", "work_dir": "_work"}


@dataclass(frozen=True)
class Value:
    key: str  # "section.key"
    value: str | None
    source: str  # "unset" | "default" | "toolkit.toml" | "toolkit.local.toml" | "env:AVC_..." | "explicit"
    kind: str = "path"

    @property
    def is_set(self) -> bool:
        return self.value not in (None, "")


def user_state_dir() -> Path:
    """Per-user, per-machine state folder (lock file lives here by default)."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return Path(base) / "editing-workflow"


def user_cache_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return Path(base) / "editing-workflow" / "cache"
    if sys.platform == "darwin":
        return Path(os.path.expanduser("~")) / "Library" / "Caches" / "editing-workflow"
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "editing-workflow"


def find_config_file(start: str | os.PathLike[str] | None = None, environ: dict[str, str] | None = None) -> Path | None:
    """``AVC_CONFIG`` if set, else the nearest ``toolkit.toml`` walking up from ``start`` (default: cwd)."""
    env = os.environ if environ is None else environ
    explicit = env.get("AVC_CONFIG", "").strip()
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_file():
            raise ConfigError(f"AVC_CONFIG points to a missing file: {explicit!r}", remediation="fix or unset AVC_CONFIG")
        return p.resolve()
    cur = Path(os.path.abspath(os.fspath(start) if start else os.getcwd()))
    for folder in (cur, *cur.parents):
        candidate = folder / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def _read_toml(path: Path) -> dict[str, Any]:
    import tomllib  # stdlib; imported lazily so `--help` stays fast

    try:
        with open(fs_path(path), "rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML ({exc})", remediation="fix the syntax; strings need quotes, use / or \\\\ in paths") from exc
    for section, table in data.items():
        if section not in SCHEMA:
            raise ConfigError(f"{path}: unknown section [{section}]", remediation=f"known sections: {', '.join(SCHEMA)}")
        if not isinstance(table, dict):
            raise ConfigError(f"{path}: [{section}] must be a table")
        for key, val in table.items():
            if key not in SCHEMA[section]:
                raise ConfigError(f"{path}: unknown key {section}.{key}", remediation=f"known keys: {', '.join(SCHEMA[section])}")
            if not isinstance(val, str):
                raise ConfigError(f"{path}: {section}.{key} must be a string, got {type(val).__name__}")
    return data


@dataclass(frozen=True)
class Config:
    values: dict[str, Value]
    files: tuple[Path, ...] = ()
    base_dir: Path | None = None
    warnings: tuple[str, ...] = field(default=())

    def get(self, key: str) -> Value:
        try:
            return self.values[key]
        except KeyError as exc:
            raise ConfigError(f"unknown config key {key!r}") from exc

    def path(self, key: str) -> Path | None:
        """Configured path (absolute, ``~`` expanded) or ``None`` when unset."""
        v = self.get(key)
        return Path(v.value) if v.is_set and v.value else None

    def require_path(self, key: str) -> Path:
        p = self.path(key)
        if p is None:
            section, name = key.split(".", 1)
            raise ConfigError(
                f"{key} is not configured",
                remediation=f"set [{section}] {name} in toolkit.toml (or toolkit.local.toml), or the environment variable "
                f"AVC_{section.upper()}_{name.upper()}",
            )
        return p

    @property
    def lock_path(self) -> Path:
        """The one absolute heavy-job lock path (configured, else a per-user location)."""
        return self.path("paths.lock_path") or (user_state_dir() / "render.lock")

    @property
    def cache_dir(self) -> Path:
        return self.path("paths.cache_dir") or user_cache_dir()

    def output_names(self) -> dict[str, str]:
        """``{"source","hf","final","work"}`` folder names for ``paths.project_paths(folders=...)``."""
        return {
            "source": self.get("output.source_dir").value or "source",
            "hf": self.get("output.hf_dir").value or "hf",
            "final": self.get("output.final_dir").value or "final",
            "work": self.get("output.work_dir").value or "_work",
        }

    def executable(self, key: str) -> str | None:
        """Configured executable path (as given) or ``None`` -> caller falls back to PATH."""
        v = self.get(key)
        return v.value if v.is_set else None

    def validate(self) -> list[str]:
        """Non-fatal findings: non-ASCII work root, configured paths that do not exist."""
        out: list[str] = []
        wr = self.path("paths.work_root")
        if wr is not None and not str(wr).isascii():
            out.append("paths.work_root contains non-ASCII characters: HyperFrames init skips index.html there")
        for key, v in self.values.items():
            if v.kind == "path" and v.is_set and v.source != "default" and not os.path.exists(fs_path(v.value or "")):
                if key not in ("paths.work_root", "paths.lock_path", "paths.cache_dir"):
                    out.append(f"{key} points to a path that does not exist: {v.value}")
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": [str(f) for f in self.files],
            "values": {k: {"value": v.value, "source": v.source} for k, v in self.values.items()},
            "effective": {
                "lock_path": str(self.lock_path),
                "cache_dir": str(self.cache_dir),
                "output_names": self.output_names(),
            },
            "warnings": list(self.warnings) + self.validate(),
        }


def _resolve_value(raw: str, kind: str, base: Path | None) -> str:
    raw = raw.strip()
    if not raw or kind == "name":
        return raw
    if kind == "exe" and not any(sep in raw for sep in ("/", "\\")) and not raw.startswith("~"):
        return raw  # bare command name: looked up on PATH by the caller
    p = Path(os.path.expanduser(os.path.expandvars(raw)))
    if not p.is_absolute() and base is not None:
        p = base / p
    return str(Path(os.path.abspath(p)))


def load_config(path: str | os.PathLike[str] | None = None, *, environ: dict[str, str] | None = None, start: str | os.PathLike[str] | None = None) -> Config:
    """Load configuration. ``path`` overrides discovery. Never raises for a missing file (all values stay unset)."""
    env = dict(os.environ) if environ is None else dict(environ)
    cfg_file = Path(path) if path else find_config_file(start, env)
    values: dict[str, Value] = {}
    for section, keys in SCHEMA.items():
        for key, (kind, _desc) in keys.items():
            default = _OUTPUT_DEFAULTS.get(key) if section == "output" else None
            values[f"{section}.{key}"] = Value(f"{section}.{key}", default, "default" if default else "unset", kind)

    files: list[Path] = []
    base_dir: Path | None = None
    layers: list[Path] = []
    if cfg_file is not None:
        if not cfg_file.is_file():
            raise ConfigError(f"config file not found: {cfg_file}")
        layers.append(cfg_file)
        base_dir = cfg_file.parent
        local = cfg_file.with_name(LOCAL_FILENAME)
        if local.is_file():
            layers.append(local)
    for layer in layers:
        data = _read_toml(layer)
        for section, table in data.items():
            for key, raw in table.items():
                kind = SCHEMA[section][key][0]
                if not raw.strip():
                    continue  # empty = not set; does not erase an earlier layer
                values[f"{section}.{key}"] = Value(f"{section}.{key}", _resolve_value(raw, kind, layer.parent), layer.name, kind)
        files.append(layer)

    for section, keys in SCHEMA.items():
        for key, (kind, _d) in keys.items():
            name = f"AVC_{section.upper()}_{key.upper()}"
            raw = env.get(name, "")
            if raw.strip():
                values[f"{section}.{key}"] = Value(f"{section}.{key}", _resolve_value(raw, kind, None), f"env:{name}", kind)
    return Config(values=values, files=tuple(files), base_dir=base_dir)

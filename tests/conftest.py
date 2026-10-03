"""Shared pytest fixtures for the toolkit test-suite.

* ``src/`` is put on ``sys.path`` (pyproject ``pythonpath``); ``fixtures/generators`` is added here so tests can import
  the generators directly.
* ``TRICKY_NAME`` is a folder name with Hebrew letters, spaces, an apostrophe and an emoji. Media fixtures are generated
  INSIDE such a folder so every FFmpeg/ffprobe call in the suite exercises the hostile-path case (src: blueprint
  REPO_ARCHITECTURE section 8, "Paths" check).
* Tests that need FFmpeg are skipped - never silently passed - when ffmpeg/ffprobe are missing.
* Media is only ever generated under pytest's temp directories, never inside the repository tree.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
for _p in (REPO / "src", REPO / "fixtures" / "generators"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

TRICKY_NAME = "פרויקט אבג 'quote' 🎬 תיקייה"


def _have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    if _have_ffmpeg():
        return
    skip = pytest.mark.skip(reason="ffmpeg/ffprobe not on PATH (install FFmpeg; this is a skip, not a pass)")
    for item in items:
        if "ffmpeg" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO


@pytest.fixture()
def tricky_dir(tmp_path: Path) -> Path:
    """A fresh folder whose name contains Hebrew, spaces, an apostrophe and an emoji."""
    d = tmp_path / TRICKY_NAME
    d.mkdir()
    return d


class E04Set:
    """``e04_set["black"]`` -> Path of black.mkv; ``.records`` -> manifest records; ``.dir`` -> output folder."""

    def __init__(self, directory: Path, records: list[dict]) -> None:
        self.dir = directory
        self.records = records
        self._paths = {r["id"]: Path(r["path"]) for r in records}

    def __getitem__(self, key: str) -> Path:
        return self._paths[key]

    def __contains__(self, key: str) -> bool:
        return key in self._paths


@pytest.fixture(scope="session")
def e04_set(tmp_path_factory) -> E04Set:
    """The E04 synthetic defect set, generated once per session into a hostile-named temp folder."""
    if not _have_ffmpeg():
        pytest.skip("ffmpeg/ffprobe not on PATH")
    import make_e04_set as gen

    out = tmp_path_factory.mktemp("סט e04 'quote' 🎬") / "e04"
    return E04Set(out, gen.build_e04(out))


@pytest.fixture(scope="session")
def sample_project(tmp_path_factory):
    if not _have_ffmpeg():
        pytest.skip("ffmpeg/ffprobe not on PATH")
    import make_sample_project as sample

    out = tmp_path_factory.mktemp("sample 'project' 🎬 דוגמה")
    records = sample.build_sample(out)
    return {"root": out, "records": records, "source": out / "projects" / sample.SAMPLE_SLUG / "source"}


@pytest.fixture(scope="session")
def schema_registry():
    """jsonschema validator factory bound to the contracts/ folder (resolves cross-file $ref)."""
    jsonschema = pytest.importorskip("jsonschema")
    referencing = pytest.importorskip("referencing")
    from referencing.jsonschema import DRAFT202012

    contracts = REPO / "contracts"
    registry = referencing.Registry()
    schemas = {}
    for f in sorted(contracts.glob("*.schema.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        schemas[f.name] = doc
        resource = DRAFT202012.create_resource(doc)
        registry = registry.with_resource(doc["$id"], resource)

    def make(name: str):
        return jsonschema.Draft202012Validator(schemas[name], registry=registry, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER)

    make.names = sorted(schemas)  # type: ignore[attr-defined]
    return make

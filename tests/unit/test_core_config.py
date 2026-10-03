"""config.py: toolkit.toml loading, layering, env overrides, no private defaults."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core import config
from core.errors import ConfigError

REPO = Path(__file__).resolve().parents[2]


def write(p: Path, text: str) -> Path:
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def test_repo_toolkit_toml_loads_with_everything_unset():
    cfg = config.load_config(REPO / "toolkit.toml", environ={})
    unset = [k for k, v in cfg.values.items() if not v.is_set]
    # only the four output folder names come with built-in values; every path/model/binary is unset
    assert {k for k, v in cfg.values.items() if v.is_set} == {"output.source_dir", "output.hf_dir", "output.final_dir", "output.work_dir"}
    assert "paths.work_root" in unset and "models.matte_dir" in unset and "binaries.blender" in unset


def test_no_private_defaults_leak_into_repo_files():
    """No owner home path / user name / client name in shipped config, code, contracts or manifest."""
    bad = [re.compile(r"[A-Za-z]:\\Users\\[A-Za-z]", re.I), re.compile(r"/Users/[a-z]", re.I), re.compile(r"/home/[a-z]+/", re.I)]
    targets = [REPO / "toolkit.toml", REPO / "pyproject.toml", REPO / "fixtures" / "manifest.json", *(REPO / "src" / "core").glob("*.py"), *(REPO / "contracts").glob("*.json"), *(REPO / "fixtures" / "generators").glob("*.py")]
    hits = []
    for f in targets:
        text = f.read_text(encoding="utf-8")
        for rx in bad:
            for m in rx.finditer(text):
                hits.append(f"{f.relative_to(REPO)}: {m.group(0)}")
    assert not hits, hits


def test_missing_file_means_all_unset_not_an_error(tmp_path):
    cfg = config.load_config(environ={}, start=tmp_path)
    assert cfg.files == () and cfg.path("paths.work_root") is None


def test_require_path_error_names_key_file_and_env_var(tmp_path):
    cfg = config.load_config(environ={}, start=tmp_path)
    with pytest.raises(ConfigError) as e:
        cfg.require_path("paths.work_root")
    msg = str(e.value)
    assert "paths.work_root" in msg and "toolkit.toml" in msg and "AVC_PATHS_WORK_ROOT" in msg


def test_layers_toml_then_local_then_env_with_provenance(tmp_path):
    write(tmp_path / "toolkit.toml", '[paths]\nwork_root = "work"\ncache_dir = "cache"\n[output]\nfinal_dir = "deliver"\n')
    write(tmp_path / "toolkit.local.toml", '[paths]\nwork_root = "local-work"\n')
    cfg = config.load_config(tmp_path / "toolkit.toml", environ={"AVC_PATHS_CACHE_DIR": str(tmp_path / "envcache")})
    wr = cfg.get("paths.work_root")
    assert wr.source == "toolkit.local.toml" and Path(wr.value) == tmp_path / "local-work"  # relative -> resolved against the file's folder
    assert cfg.get("paths.cache_dir").source == "env:AVC_PATHS_CACHE_DIR" and Path(cfg.get("paths.cache_dir").value) == tmp_path / "envcache"
    assert cfg.get("output.final_dir").value == "deliver" and cfg.output_names()["final"] == "deliver"
    assert [f.name for f in cfg.files] == ["toolkit.toml", "toolkit.local.toml"]


def test_empty_string_in_local_does_not_erase_value(tmp_path):
    write(tmp_path / "toolkit.toml", '[paths]\nwork_root = "w"\n')
    write(tmp_path / "toolkit.local.toml", '[paths]\nwork_root = ""\n')
    assert config.load_config(tmp_path / "toolkit.toml", environ={}).path("paths.work_root") == tmp_path / "w"


def test_unknown_keys_sections_and_types_are_errors(tmp_path):
    for body, needle in [
        ('[paths]\nwork_rot = "x"\n', "unknown key"),
        ('[pathz]\na = "x"\n', "unknown section"),
        ('[paths]\nwork_root = 5\n', "must be a string"),
        ('[paths\n', "invalid TOML"),
    ]:
        f = write(tmp_path / "toolkit.toml", body)
        with pytest.raises(ConfigError) as e:
            config.load_config(f, environ={})
        assert needle in str(e.value)


def test_hebrew_and_space_paths_survive_toml(tmp_path):
    d = tmp_path / "תיקיית מודלים 'x' 🎬"
    d.mkdir()
    write(tmp_path / "toolkit.toml", f'[models]\nmatte_dir = "{d.as_posix()}"\n')
    cfg = config.load_config(tmp_path / "toolkit.toml", environ={})
    assert cfg.path("models.matte_dir") == d
    assert cfg.validate() == []  # exists, no warning


def test_validate_warns_about_non_ascii_work_root_and_missing_files_and_lock_is_absolute(tmp_path):
    write(tmp_path / "toolkit.toml", '[paths]\nwork_root = "עבודה"\nlock_path = "rel.lock"\n[models]\nasr_model_dir = "no-such-dir"\n')
    cfg = config.load_config(tmp_path / "toolkit.toml", environ={})
    w = " | ".join(cfg.validate())
    assert "non-ASCII" in w and "asr_model_dir" in w
    assert cfg.lock_path.is_absolute() and cfg.lock_path == tmp_path / "rel.lock"  # relative values are anchored to the config file's folder


def test_lock_path_and_cache_default_to_a_per_user_state_location(tmp_path):
    cfg = config.load_config(environ={}, start=tmp_path)
    assert cfg.lock_path.is_absolute() and cfg.lock_path.name == "render.lock"
    assert "editing-workflow" in str(cfg.lock_path) and cfg.cache_dir.is_absolute()
    write(tmp_path / "toolkit.toml", f'[paths]\nlock_path = "{(tmp_path / "x.lock").as_posix()}"\n')
    assert config.load_config(tmp_path / "toolkit.toml", environ={}).lock_path == tmp_path / "x.lock"


def test_avc_config_env_selects_file_and_missing_is_an_error(tmp_path):
    f = write(tmp_path / "custom.toml", '[paths]\nwork_root = "/x"\n')
    assert config.find_config_file(environ={"AVC_CONFIG": str(f)}) == f.resolve()
    with pytest.raises(ConfigError):
        config.find_config_file(environ={"AVC_CONFIG": str(tmp_path / "missing.toml")})


def test_executable_keeps_bare_command_names_for_path_lookup(tmp_path):
    write(tmp_path / "toolkit.toml", '[binaries]\nffmpeg = "ffmpeg-nightly"\nblender = "tools/blender"\n')
    cfg = config.load_config(tmp_path / "toolkit.toml", environ={})
    assert cfg.executable("binaries.ffmpeg") == "ffmpeg-nightly"
    assert Path(cfg.executable("binaries.blender")) == tmp_path / "tools" / "blender"
    assert cfg.executable("binaries.ffprobe") is None


def test_to_dict_is_json_safe(tmp_path):
    import json

    d = config.load_config(environ={}, start=tmp_path).to_dict()
    json.dumps(d, ensure_ascii=False)
    assert "effective" in d and "values" in d

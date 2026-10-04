"""prep: the minute-0 background preparation runs the existing tools under the lock, records not_run honestly and caches reruns."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "prep.py"


def run(*args, lock, timeout=600):
    env = dict(os.environ, AVC_PATHS_LOCK_PATH=str(lock))
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOL), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout, env=env)


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *map(str, args)], check=True, timeout=300)


def make_project(tmp_path, *, sources=1, refs=1):
    root = tmp_path / "proj"
    (root / "source").mkdir(parents=True)
    (root / "hf" / "references").mkdir(parents=True)
    for i in range(sources):
        ff("-f", "lavfi", "-i", "testsrc2=s=320x568:r=30:d=3", "-f", "lavfi", "-i", "sine=f=440:d=3", "-shortest",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", root / "source" / f"צילום {i} 'x'.mp4")
    for i in range(refs):
        ff("-f", "lavfi", "-i", "smptebars=s=320x568:r=30:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", root / "hf" / "references" / f"רפרנס {i}.mp4")
    return root


@pytest.mark.ffmpeg
def test_plan_shows_every_job_and_downloads_nothing(tmp_path):
    root = make_project(tmp_path)
    p = run(root, "--plan", lock=tmp_path / "l.lock")
    assert p.returncode == 0, p.stderr
    plan = json.loads(p.stdout)
    assert plan["downloads"] == "none"
    ids = [j["id"] for j in plan["jobs"]]
    assert ids[:5] == ["sheet", "asr", "cuts", "faces", "scopes"] and ids[5].startswith("refs:")
    assert all("--allow-download" not in j["cmd"] for j in plan["jobs"])
    assert not (root / "_work").exists()  # --plan writes nothing


@pytest.mark.ffmpeg
def test_runs_records_not_run_honestly_and_caches(tmp_path):
    root = make_project(tmp_path)
    empty = tmp_path / "no model here"
    empty.mkdir()
    lock = tmp_path / "l.lock"
    p = run(root, "--json", "--model-dir", empty, "--face-model", tmp_path / "absent.onnx", lock=lock)
    assert p.returncode == 1, p.stderr  # asr and faces cannot run on this input: partial, not ok
    rep = json.loads(p.stdout)
    st = {k: v["status"] for k, v in rep["steps"].items()}
    assert st["sheet"] == st["cuts"] == st["scopes"] == "done"
    assert st["asr"] == "not_run" and st["faces"] == "not_run"
    assert "hint" in rep["steps"]["asr"] and "YuNet" in rep["steps"]["faces"]["hint"]
    assert [k for k in st if k.startswith("refs:")] and all(v == "done" for k, v in st.items() if k.startswith("refs:"))
    assert (root / "hf" / "data" / "src_cuts.json").is_file() and (root / "_work" / "prep" / "sheet.jpg").is_file()
    state = json.loads((root / "_work" / "prep" / "prep.json").read_text(encoding="utf-8"))
    assert state["steps"]["asr"]["status"] == "not_run" and state["steps"]["asr"]["key"] is None
    # second run: unchanged inputs are cached, not recomputed
    p = run(root, "--json", "--steps", "sheet,cuts,scopes,refs", lock=lock)
    assert p.returncode == 0, p.stderr
    assert {v["status"] for v in json.loads(p.stdout)["steps"].values()} == {"cached"}
    # --force reruns
    p = run(root, "--json", "--steps", "sheet", "--force", lock=lock)
    assert json.loads(p.stdout)["steps"]["sheet"]["status"] == "done"


@pytest.mark.ffmpeg
def test_refusals(tmp_path):
    lock = tmp_path / "l.lock"
    assert run(tmp_path / "nothing", lock=lock).returncode == 2
    root = make_project(tmp_path, sources=2, refs=0)
    p = run(root, lock=lock)
    assert p.returncode == 2 and "pass --main" in p.stderr
    p = run(root, "--steps", "sheet,bogus", lock=lock)
    assert p.returncode == 2 and "unknown step" in p.stderr
    main = sorted((root / "source").iterdir())[0]
    p = run(root, "--main", main, "--steps", "sheet,refs", "--json", lock=lock)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout)["steps"]["refs"]["status"] == "skipped"

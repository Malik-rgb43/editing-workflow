"""hf_blocks: manifests, add (rename, --set, variables), data helpers, and the admission test in an empty project."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "src"))

import hf_blocks  # noqa: E402

BLOCK_NAMES = {"voice-orb", "task-steps", "boarding-pass-stamp", "notification-stack", "film-burn", "speaker-cutout-behind", "caption", "typed-caption", "liquid-glass"}


def test_every_block_has_its_five_files_and_a_valid_manifest():
    ms = hf_blocks.manifests()
    assert set(ms) == BLOCK_NAMES
    for name, m in ms.items():
        d = m["_dir"]
        for f in ("block.html", "demo.html", "block.json", "README.md", "SOURCE.md"):
            assert (d / f).is_file(), (name, f)
        html = (d / "block.html").read_text(encoding="utf-8")
        assert f'data-composition-id="{name}"' in html and f'window.__timelines["{name}"]' in html
        assert f'data-composition-src="compositions/{name}.html"' in (d / "demo.html").read_text(encoding="utf-8")
        declared = json.loads(__import__("re").search(r"data-composition-variables='(\[.*?\])'", html, __import__("re").S).group(1))
        assert [v["id"] for v in declared] == [v["id"] for v in m["variables"]]
        assert "Math.random" not in html and "requestAnimationFrame" not in html and "setInterval" not in html and "transition:" not in html


def test_add_copies_renames_and_prints_a_host(tmp_path, capsys):
    hf = tmp_path / "hf"
    hf.mkdir()
    assert hf_blocks.main(["add", "task-steps", str(hf), "--as", "task-steps-2", "--var", "title=Plan", "--start", "2", "--duration", "5", "--track", "3"]) == 0
    out = capsys.readouterr().out
    assert 'data-composition-id="task-steps-2-host"' in out and 'data-composition-src="compositions/task-steps-2.html"' in out and 'data-start="2.0"' in out and 'data-track-index="3"' in out
    assert '"title": "Plan"' in out and '"duration": 5.0' in out
    text = (hf / "compositions" / "task-steps-2.html").read_text(encoding="utf-8")
    assert 'data-composition-id="task-steps-2"' in text and 'window.__timelines["task-steps-2"]' in text and "#task-steps-2-card" in text and 'id="task-steps-2-title"' in text
    assert 'data-composition-id="task-steps"' not in text and "task-steps-card" not in text.replace("task-steps-2-card", "")
    assert hf_blocks.main(["add", "task-steps", str(hf), "--as", "task-steps-2"]) == 2  # never overwritten silently


def test_add_set_points_the_videos_and_refuses_missing_files_and_unknown_names(tmp_path, capsys):
    hf = tmp_path / "hf"
    (hf / "assets" / "video").mkdir(parents=True)
    (hf / "assets" / "video" / "a.mp4").write_bytes(b"x")
    (hf / "assets" / "video" / "s.webm").write_bytes(b"x")
    assert hf_blocks.main(["add", "speaker-cutout-behind", str(hf), "--set", "plate=assets/video/a.mp4"]) == 0
    cap = capsys.readouterr()
    assert "cutout" in cap.err and 'src="assets/video/a.mp4"' in (hf / "compositions" / "speaker-cutout-behind.html").read_text(encoding="utf-8")
    assert hf_blocks.main(["add", "speaker-cutout-behind", str(hf), "--force", "--set", "cutout=assets/video/missing.webm"]) == 2
    assert hf_blocks.main(["add", "speaker-cutout-behind", str(hf), "--force", "--set", "nope=x"]) == 2
    assert hf_blocks.main(["add", "task-steps", str(hf), "--var", "bogus=1"]) == 2
    assert hf_blocks.main(["add", "no-such-block", str(hf)]) == 2


def test_rename_only_touches_ids_selectors_and_keys():
    text = 'id="caption-chunk-" + c; "#caption-hl-"; window.__timelines["caption"]; (tools/hf_blocks.py caption-words) caption text'
    new = hf_blocks.rename_block(text, "caption", "caption-b")
    assert 'id="caption-b-chunk-"' in new and '"#caption-b-hl-"' in new and '__timelines["caption-b"]' in new and "(tools/hf_blocks.py caption-words)" in new


def test_caption_words_shifts_times_and_detects_hebrew(tmp_path, capsys):
    words = {"schema": "avc.words/1", "words": [{"w": "שלום", "start": 10.0, "end": 10.4}, {"w": "עולם", "start": 10.5, "end": 11.0}, {"w": "אחר", "start": 30.0, "end": 30.5}]}
    p = tmp_path / "w.json"
    p.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    assert hf_blocks.main(["caption-words", str(p), "--from", "10", "--to", "12"]) == 0
    out = json.loads(capsys.readouterr().out)
    sel = json.loads(out["words"])
    assert out["rtl"] is True and [w["w"] for w in sel] == ["שלום", "עולם"] and sel[0]["start"] == 0.0 and sel[1]["end"] == 1.0 and out["duration"] == 2.0
    assert hf_blocks.main(["caption-words", str(p), "--from", "50", "--to", "51"]) == 2


@pytest.mark.ffmpeg
def test_levels_follow_the_loudness(tmp_path, capsys):
    wav = tmp_path / "v.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=300:d=2", "-af", "volume='if(lt(t,1),0.05,0.8)':eval=frame", str(wav)], check=True, timeout=60)
    out = tmp_path / "l.json"
    assert hf_blocks.main(["levels", str(wav), "-o", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    lv = doc["levels"]
    assert doc["fps"] == 30 and 58 <= len(lv) <= 61 and max(lv[:20]) < 0.4 and min(lv[40:]) > 0.6 and all(0 <= v <= 1 for v in lv)
    sil = tmp_path / "s.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=300:d=2", str(sil)], check=True, timeout=60)
    assert hf_blocks.main(["levels", str(sil), "-o", str(tmp_path / "x.json")]) == 2  # a constant tone has nothing to animate


@pytest.mark.slow
@pytest.mark.ffmpeg
def test_verify_admits_a_block_in_an_empty_project():
    from core import hf_engine

    eng = hf_engine.find()
    if eng is None or eng.source == "project-local":  # npx --no-install with nothing installed is not an engine (CI had only npx)
        pytest.skip("HyperFrames engine not installed (toolkit or AVC_HYPERFRAMES_CLI)")
    assert hf_blocks.main(["verify", "voice-orb"]) == 0

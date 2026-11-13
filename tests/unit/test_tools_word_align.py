"""word_align: pure helpers and the refusal paths (no model, no torch needed). The real-model run is skipped unless the model is already cached."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO / "src"))

import word_align as wa  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / "word_align.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=120)


LETTERS = set("אבגדהוזחטיכלמנסעפצקרשתךםןףץ")


def test_norm_text_strips_niqqud_maps_digits_and_latin():
    assert wa.norm_text("שָׁלוֹם,", LETTERS) == "שלום"
    assert wa.norm_text("4", LETTERS) == "ארבע"
    assert wa.norm_text("Claude", LETTERS) == "קלוד"
    assert wa.norm_text("???", LETTERS) == ""
    assert wa.norm_text("zzzz", LETTERS) == ""  # unknown latin word: unalignable, keeps ASR times


def test_make_chunks_splits_at_pause_and_pads():
    words = [{"start_ms": i * 500, "end_ms": i * 500 + 400} for i in range(40)]
    words[19]["end_ms"] = words[19]["start_ms"] + 100  # a long pause after word 19
    ch = wa.make_chunks(words, 10, 0.6, 20000)
    assert ch[0][0] == 0 and ch[-1][1] == 39 and all(a[1] + 1 == b[0] for a, b in zip(ch, ch[1:]))
    assert ch[0][2] == 0 and ch[1][2] == max(0, words[ch[1][0]]["start_ms"] - 600)


def test_refine_edges_moves_to_energy_and_keeps_unaligned():
    np = pytest.importorskip("numpy")
    db = np.full(300, -80.0)
    db[100:140] = -20.0  # speech 1.00-1.40 s
    w = [{"asr_start_ms": 1300, "asr_end_ms": 1700, "start_ms": 1300, "end_ms": 1700, "ctc_start_ms": 1020, "ctc_end_ms": 1380, "score": 0.9},
         {"asr_start_ms": 2000, "asr_end_ms": 2200, "start_ms": 2000, "end_ms": 2200}]
    wa.refine_edges(w, db, 3000)
    assert abs(w[0]["start_ms"] - 1000) <= 20 and abs(w[0]["end_ms"] - 1400) <= 40
    assert (w[1]["start_ms"], w[1]["end_ms"]) == (2000, 2200)


def test_help_is_fast_and_check_reports(tmp_path):
    assert run("--help").returncode == 0
    r = run("--check")
    assert r.returncode == 0 and json.loads(r.stdout)["revision"] == wa.REVISION


def test_fetch_model_without_yes_downloads_nothing():
    r = run("--fetch-model")
    assert r.returncode == 0 and "nothing downloaded" in r.stdout and "1,261,934,532" in r.stdout


def test_refuses_non_hebrew_and_missing_input(tmp_path):
    src = tmp_path / "a.wav"
    src.write_bytes(b"x")
    words = tmp_path / "w.json"
    words.write_text(json.dumps({"language": "en", "words": [{"w": "hi", "start": 0, "end": 1}]}), encoding="utf-8")
    r = run(src, words, "-o", tmp_path / "o.json")
    assert r.returncode == 2 and "Hebrew only" in r.stderr and not (tmp_path / "o.json").exists()
    assert run(tmp_path / "none.wav", words, "-o", tmp_path / "o.json").returncode == 2

"""core.vo on synthetic voice-like signals: regions, onsets, pinning, pause cuts, remapping, levelling, SFX peaks, band ratio."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from core import vo  # noqa: E402

SR = 16000


def burst(t0, t1, total, amp=0.3, f=220.0, sr=SR):
    x = np.zeros(int(total * sr), dtype=np.float32)
    n = np.arange(int(t0 * sr), int(t1 * sr))
    x[n] = amp * np.sin(2 * np.pi * f * n / sr)
    return x


def three_phrases(amps=(0.3, 0.3, 0.3)):
    # phrases at 0.50-1.20, 1.60-2.40 (0.40 s pause), 2.55-3.30 (0.15 s pause); 0.001 noise floor
    rng = np.random.default_rng(0)
    x = rng.normal(0, 0.001, int(4.0 * SR)).astype(np.float32)
    for (a, b), amp in zip([(0.50, 1.20), (1.60, 2.40), (2.55, 3.30)], amps):
        x += burst(a, b, 4.0, amp)
    return x


def test_regions_split_on_pauses_of_100ms_and_onsets_are_sample_accurate():
    x = three_phrases()
    env = vo.envelope_db(x, SR)
    thr = vo.speech_threshold_db(env)
    regions = vo.speech_regions(env, min_pause_s=0.10, thr_db=thr)
    assert len(regions) == 3
    onsets = [vo.refine_onset(x, SR, r[0], thr) for r in regions]
    for got, want in zip(onsets, (0.50, 1.60, 2.55)):
        assert abs(got - want) <= 0.003
    assert len(vo.speech_regions(env, min_pause_s=0.20, thr_db=thr)) == 2  # the 0.15 s pause no longer splits


def test_pin_words_moves_each_chunk_to_its_onset_and_keeps_inner_timing():
    regions = [[0.5, 1.2], [1.6, 2.4]]
    words = [{"w": "a", "start": 0.95, "end": 1.05}, {"w": "b", "start": 1.10, "end": 1.20},  # one pass: 0.45 s late
             {"w": "c", "start": 1.90, "end": 2.10}, {"w": "d", "start": 2.15, "end": 2.40}]  # 0.30 s late
    new, rep = vo.pin_words(words, regions, [0.5, 1.6])
    assert new[0]["start"] == 0.5 and new[1]["start"] == pytest.approx(0.65) and new[2]["start"] == 1.6
    assert [r["delta"] for r in rep] == [-0.45, -0.3]


def test_pause_compression_keeps_protected_pauses_and_remap_follows_the_cuts():
    regions = [[0.5, 1.2], [1.6, 2.4], [2.55, 3.3]]
    cuts = vo.compress_pauses(regions, 4.0, 0.28, 0.20)
    assert cuts == [{"t0": 1.3, "t1": 1.5}]  # only the 0.40 s pause; the 0.15 s one stays
    assert vo.compress_pauses(regions, 4.0, 0.28, 0.20, protect=[1.4]) == []
    assert vo.remap(1.0, cuts) == 1.0 and vo.remap(1.6, cuts) == pytest.approx(1.4) and vo.remap(1.4, cuts) == pytest.approx(1.3)


def test_levelling_moves_85_percent_to_the_median_and_never_changes_gain_inside_speech():
    x = three_phrases(amps=(0.1, 0.3, 0.3))
    env = vo.envelope_db(x, SR)
    regions = vo.speech_regions(env)
    levels = vo.phrase_levels_db(x, SR, regions)
    gains = vo.level_gains_db(levels, 0.85)
    assert gains[0] == pytest.approx((levels[1] - levels[0]) * 0.85, abs=0.01) and abs(gains[1]) < 0.01
    g = vo.gain_curve(len(x), SR, regions, gains)
    a, b = int(regions[0][0] * SR), int(regions[0][1] * SR)
    assert float(g[a:b].max() - g[a:b].min()) < 1e-6  # flat inside the phrase: the ramp lives in the pause


def test_sfx_peak_is_found_late_in_a_riser_and_band_ratio_reads_the_speech_band():
    sr = 48000
    t = np.arange(int(4.0 * sr)) / sr
    riser = (np.sin(2 * np.pi * 400 * t) * (t / 4.0) ** 3).astype(np.float32)
    riser[int(3.5 * sr):] *= 0.2  # it peaks just before 3.5 s, not at its start
    assert 3.3 <= vo.peak_time(riser, sr) <= 3.51
    voice = burst(0, 1.0, 1.0, 0.3, 1000.0, sr)
    music = burst(0, 1.0, 1.0, 0.3, 100.0, sr) + burst(0, 1.0, 1.0, 0.03, 1000.0, sr)  # loud lows, quiet mids
    row = vo.vo_over_music(voice, music, sr, [[0.0, 1.0]])[0]
    assert row["vo_over_music_db"] == pytest.approx(20.0, abs=1.0)  # 10x amplitude in the band = 20 dB

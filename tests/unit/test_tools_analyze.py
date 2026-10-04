"""analyze / frames: the output folder must satisfy the video-analysis contract (validate_analysis.py) on a synthetic clip with known cuts and a 120 BPM click track."""

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
VALIDATOR = REPO / "agent-content" / "skills" / "video-analysis" / "scripts" / "validate_analysis.py"

from core import analysis, audio_analysis  # noqa: E402


def run(tool, *args, timeout=600):
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / f"{tool}.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout)


def validate(folder, *extra):
    p = subprocess.run([sys.executable, "-X", "utf8", str(VALIDATOR), str(folder), "--json", *map(str, extra)], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, json.loads(p.stdout)


# ------------------------------------------------------------------------------------------------ library (no ffmpeg)
def test_budget_and_segments_of_keyframes():
    assert analysis.keyframe_budget(10, "standard") == 54 and analysis.keyframe_budget(1000, "quick") == 120
    assert analysis.thumb_size(1080, 1920) == (54, 96)


def test_ebur128_summary_parser():
    text = "x\n  Summary:\n\n  Integrated loudness:\n    I:         -16.3 LUFS\n    Threshold: -26.4 LUFS\n\n  Loudness range:\n    LRA:         4.2 LU\n\n  True peak:\n    Peak:       -1.4 dBFS\n"
    assert audio_analysis.parse_ebur128(text) == {"integrated_lufs": -16.3, "lra": 4.2, "true_peak_dbtp": -1.4, "meter": "EBU R128 (FFmpeg ebur128, peak=true)"}
    assert audio_analysis.parse_ebur128("nothing") is None


def test_tempo_of_a_click_track_and_its_alternatives():
    import numpy as np

    sr, dur = 16000, 12.0
    x = np.zeros(int(sr * dur), dtype=np.float32)
    for k in range(int(dur * 2)):  # 120 BPM
        a = int(k * 0.5 * sr)
        n = int(0.05 * sr)
        x[a:a + n] = np.sin(2 * np.pi * 1000 * np.arange(n) / sr) * np.hanning(n)
    res = audio_analysis.analyse_signal(x, sr, dur, [2.0, 4.0], 30.0)
    m = res["music"]
    assert m["present"] and abs(m["tempo_bpm"] - 120.0) < 2.0 and abs(m["tempo_alternatives_bpm"][0] - m["tempo_bpm"] / 2) < 0.1 and m["half_double_audited"] is False
    assert m["cut_on_beat"]["ratio"] == 1.0 and len(m["beats_s"]) >= 20
    assert all(e["labels"] == [] for e in res["sfx_events"])


def test_silence_has_no_music_and_no_tempo():
    import numpy as np

    res = audio_analysis.analyse_signal(np.zeros(16000 * 5, dtype=np.float32), 16000, 5.0, [], 30.0)
    assert res["music"]["present"] is False and "tempo_bpm" not in res["music"]


def test_excludes_and_pacing_arithmetic():
    import analyze

    ex = analyze.parse_excludes(["end_card:42.1-45", "watermark:0-1:logo"])
    assert ex[0]["kind"] == "end_card" and ex[1]["reason"] == "logo"
    with pytest.raises(ValueError):
        analyze.parse_excludes(["end_card:9-3"])
    p = analyze.pacing_block([2.0, 4.0], 6.0)
    assert p["edit_points"] == 2 and p["cuts_per_min"] == 20.0 and p["median_shot_s"] == 2.0 and p["first_cut_s"] == 2.0


def test_help_fast():
    import time

    for tool in ("analyze", "frames"):
        best = 99.0
        for _ in range(2):  # best of two: a cold disk cache or a busy machine must not fail a lazy-import check
            t = time.monotonic()
            p = subprocess.run([sys.executable, str(TOOLS / f"{tool}.py"), "--help"], capture_output=True, text=True, encoding="utf-8")
            assert p.returncode == 0, tool
            best = min(best, time.monotonic() - t)
        assert best < 1.5, (tool, best)


# ------------------------------------------------------------------------------------------------ tools (ffmpeg)
@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    d = tmp_path_factory.mktemp("ניתוח 'x' 🎬")
    src = d / "clip.mp4"
    graph = ("testsrc2=s=320x568:r=30:d=2[a];smptebars=s=320x568:r=30:d=2[b];mandelbrot=s=320x568:r=30,trim=duration=2,setpts=PTS-STARTPTS[c];"
             "[a][b][c]concat=n=3:v=1:a=0,format=yuv420p[v];aevalsrc='sin(2*PI*1000*t)*lt(mod(t,0.5),0.05)':s=16000:d=6[au]")
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-filter_complex", graph, "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-c:a", "aac", "-shortest", str(src)], check=True, timeout=300)
    return {"dir": d, "src": src}


@pytest.mark.ffmpeg
def test_analysis_folder_passes_the_contract_and_finds_the_two_cuts(clip):
    out = clip["dir"] / "analysis" / "clip"
    p = run("analyze", clip["src"], "--out", out, "--asr", "never")
    assert p.returncode == 0, p.stderr
    m = json.loads((out / "measurements.json").read_text(encoding="utf-8"))
    assert m["coverage"]["mode"] == "full" and m["coverage"]["frames_decoded"] == m["input"]["frames_expected"] == 180
    times = sorted(round(e["t_s"], 2) for e in m["edit_points"] if e["kind"] in ("cut", "transition"))
    assert times == [2.0, 4.0], m["edit_points"]
    assert (out / "frames.csv").read_text(encoding="utf-8").count("\n") == 181
    code, rep = validate(out, "--stage", "produced", "--allow-not-run", "transcript", "--video", clip["src"])
    assert code == 2 and [f["code"] for f in rep["findings"]] == ["TEMPO_UNAUDITED"], rep["findings"]  # by design: only the reader can audit half / double time
    assert "transcript / what is said" in rep["claims_not_allowed"]
    ap = out / "audio.json"
    doc = json.loads(ap.read_text(encoding="utf-8"))
    doc["music"]["half_double_audited"] = True  # what the reader declares after looking at the audio image
    ap.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    code, rep = validate(out, "--stage", "produced", "--allow-not-run", "transcript", "--video", clip["src"])
    assert code == 0 and rep["status"] == "PASS", rep["findings"]
    doc["music"]["half_double_audited"] = False
    ap.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    audio = json.loads((out / "audio.json").read_text(encoding="utf-8"))
    assert audio["status"] == "ok" and audio["music"]["present"] and abs(audio["music"]["tempo_bpm"] - 120.0) < 4.0 and audio["music"]["half_double_audited"] is False
    assert audio["song_id"]["sync_permission"] == "not_established" and audio["layers"]["music"] == []
    assert (out / "report.md").read_text(encoding="utf-8").index("Coverage") < (out / "report.md").read_text(encoding="utf-8").index("Pacing")
    again = run("analyze", clip["src"], "--out", out, "--asr", "never")
    assert again.returncode == 0 and '"reused": true' in again.stdout  # same hash -> the earlier analysis is kept


@pytest.mark.ffmpeg
def test_reviewed_stage_is_insufficient_until_the_sheets_are_marked_viewed(clip):
    out = clip["dir"] / "analysis" / "clip"
    if not (out / "measurements.json").is_file():
        assert run("analyze", clip["src"], "--out", out, "--asr", "never").returncode == 0
    code, rep = validate(out, "--allow-not-run", "transcript")
    assert code == 2 and rep["status"] == "INSUFFICIENT_EVIDENCE"
    assert any(f["code"] in ("NO_REVIEW", "SHEETS_UNVIEWED") for f in rep["findings"])


@pytest.mark.ffmpeg
def test_silent_video_is_na_not_pass_by_omission(clip):
    silent = clip["dir"] / "silent.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", str(clip["src"]), "-an", "-c:v", "copy", str(silent)], check=True, timeout=120)
    out = clip["dir"] / "analysis" / "silent"
    p = run("analyze", silent, "--out", out, "--detail", "quick")
    assert p.returncode == 0, p.stderr
    audio = json.loads((out / "audio.json").read_text(encoding="utf-8"))
    tr = json.loads((out / "transcript.json").read_text(encoding="utf-8"))
    assert audio["status"] == "n/a" and audio["has_audio"] is False and tr["status"] == "no_speech"
    code, rep = validate(out, "--stage", "produced")
    assert code == 0, rep["findings"]


@pytest.mark.ffmpeg
def test_exclusions_are_listed_and_cuts_inside_them_are_not_counted(clip):
    out = clip["dir"] / "analysis" / "excl"
    p = run("analyze", clip["src"], "--out", out, "--asr", "never", "--exclude", "end_card:3.5-6")
    assert p.returncode == 0, p.stderr
    m = json.loads((out / "measurements.json").read_text(encoding="utf-8"))
    assert m["coverage"]["excluded"][0]["kind"] == "end_card" and [round(e["t_s"], 2) for e in m["edit_points"]] == [2.0]


@pytest.mark.ffmpeg
def test_folder_input_makes_one_sub_folder_per_video(clip):
    src_dir = clip["dir"] / "batch"
    src_dir.mkdir()
    for n in ("a.mp4", "b.mp4"):
        subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", str(clip["src"]), "-t", "2", "-vf", "hue=h=" + ("0" if n == "a.mp4" else "90"), "-c:a", "aac", str(src_dir / n)], check=True, timeout=120)
    out = clip["dir"] / "analysis_batch"
    p = run("analyze", src_dir, "--out", out, "--asr", "never", "--detail", "quick")
    assert p.returncode == 0, p.stderr
    subs = sorted(x.name for x in out.iterdir() if x.is_dir())
    assert len(subs) == 2 and all((out / s / "measurements.json").is_file() for s in subs)


@pytest.mark.ffmpeg
def test_frames_tool_zooms_a_window_and_registers_the_sheet(clip):
    out = clip["dir"] / "analysis" / "clip"
    if not (out / "measurements.json").is_file():
        assert run("analyze", clip["src"], "--out", out, "--asr", "never").returncode == 0
    p = run("frames", clip["src"], "--at", "2.0", "--pad", "0.2", "--out", out)
    assert p.returncode == 0, p.stderr
    idx = json.loads((out / "sheets" / "index.json").read_text(encoding="utf-8"))
    zooms = [s for s in idx["sheets"] if s["kind"] == "zoom"]
    assert len(zooms) == 1 and zooms[0]["tile_px"] >= 280 and 10 <= zooms[0]["tiles"] <= 14
    first, last = zooms[0]["frames"][0]["frame"], zooms[0]["frames"][-1]["frame"]
    assert first <= 54 and last >= 66  # the cut is at frame 60
    assert (out / zooms[0]["file"]).stat().st_size > 1000
    p = run("frames", clip["src"], "--at", "2.0", "--pad", "5", "--out", out)
    assert p.returncode == 2 and "96" in p.stderr


def test_pulldown_repeats_do_not_turn_ordinary_pictures_into_cuts():
    """Regression (real 60 fps clip): 24p-in-60p repeats most frames, so a new picture every 2-3 frames spikes against its repeated neighbours.
    Neighbours must be taken among the frames that CHANGE; a real cut still stands out among them."""
    import numpy as np

    pattern = [13.0, 0.0, 0.0, 14.0, 0.0, 12.5, 0.0, 0.0, 13.5, 0.0] * 6  # handheld move, one new picture every 2-3 frames
    content = np.array([0.0] + pattern)
    arrs = {"content": content, "hist": np.full_like(content, 0.08)}
    assert analysis.hard_candidates(arrs, len(content)) == []
    content2 = content.copy()
    content2[31] = 55.0  # a real cut inside the same cadence
    arrs2 = {"content": content2, "hist": np.where(np.arange(len(content2)) == 31, 0.6, 0.08)}
    assert analysis.hard_candidates(arrs2, len(content2)) == [31]


def test_a_cut_between_two_similar_shots_is_not_explained_away_as_a_camera_move():
    """Regression (real clip, 2 missed cuts): two shots of the same beach align to half their difference, but still differ by 7-10 levels once
    aligned. Only a SMALL aligned residual proves a move."""
    import numpy as np

    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:96, 0:54]
    shapes = (((xx // 9 + yy // 12) % 2) * 120 + 60).astype(np.float64)
    prev = np.clip(shapes + rng.normal(0, 1, shapes.shape), 0, 255).astype(np.uint8)
    moved = np.clip(np.roll(shapes, 4, axis=1) + rng.normal(0, 1, shapes.shape), 0, 255).astype(np.uint8)
    other = np.clip(np.roll(shapes, 4, axis=1) + rng.normal(0, 14, shapes.shape), 0, 255).astype(np.uint8)
    r_move, res_move = analysis._translation(moved, prev)
    r_other, res_other = analysis._translation(other, prev)
    assert r_move < analysis.MOTION_RATIO and res_move < analysis.MOVE_RESIDUAL  # a real pan: rejected as a move
    assert r_other < analysis.MOTION_RATIO and res_other >= analysis.MOVE_RESIDUAL  # the ratio alone (the old rule) would call it a move; the residual says it is not


def test_beats_are_only_reported_where_the_grid_holds():
    """Speech-like irregular bursts for 8 s, then a 120 BPM click for 8 s: the beat region covers the clicks, not the speech."""
    import numpy as np

    sr = 16000
    rng = np.random.default_rng(3)
    x = np.zeros(sr * 16, dtype=np.float32)
    t = 0.0
    while t < 7.6:  # irregular syllable-like noise bursts
        n = int(rng.uniform(0.08, 0.25) * sr)
        a = int(t * sr)
        x[a:a + n] += (rng.normal(0, 0.3, n) * np.hanning(n)).astype(np.float32)
        t += rng.uniform(0.12, 0.45)
    for k in range(16):
        a = int((8.0 + k * 0.5) * sr)
        n = int(0.05 * sr)
        x[a:a + n] += np.sin(2 * np.pi * 1000 * np.arange(n) / sr).astype(np.float32) * np.hanning(n).astype(np.float32)
    m = audio_analysis.analyse_signal(x, sr, 16.0, [3.0, 10.0], 30.0)["music"]
    assert m["present"] and abs(m["tempo_bpm"] - 120) < 3
    assert m["beat_regions_s"][0][0] >= 4.5 and m["beat_regions_s"][-1][1] >= 15.0, m["beat_regions_s"]
    assert min(m["beats_s"]) >= 4.5 and m["cut_on_beat"]["cuts"] == 1  # the cut at 3.0 s sits in speech and is not scored against beats

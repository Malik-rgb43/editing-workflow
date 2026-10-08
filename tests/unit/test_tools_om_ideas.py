"""music_fit, speaker_turns, screen_zoom and analyze's motion_kind on synthetic media with known answers (click track with a loud section,
two mic tracks with bleed, a screen video with boxes that appear at known times, a still / a push-in / real motion)."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import wave
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO / "src"))

SR = 16000


def run(tool, *args, timeout=300):
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / f"{tool}.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout)


def write_wav(path: Path, x, sr: int = SR) -> Path:
    """float array (n,) or (n, ch) in -1..1 -> 16-bit WAV (stdlib)."""
    import numpy as np

    a = np.asarray(x, dtype=np.float64)
    if a.ndim == 1:
        a = a[:, None]
    pcm = (np.clip(a, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(a.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


def click_track(dur: float = 60.0, loud_from: float = 30.0):
    """120 BPM, every 4th click accented (the downbeat), a held tone under it, everything 4x louder from ``loud_from``."""
    import numpy as np

    x = np.zeros(int(SR * dur), dtype=np.float32)
    n = int(0.05 * SR)
    click = (np.sin(2 * np.pi * 1000 * np.arange(n) / SR) * np.hanning(n)).astype(np.float32)
    for k in range(int(dur * 2)):
        a = int(k * 0.5 * SR)
        amp = (1.0 if k % 4 == 0 else 0.5) * (4.0 if k * 0.5 >= loud_from else 1.0)
        x[a:a + n] += click[: len(x) - a] * amp * 0.2
    t = np.arange(len(x)) / SR
    x += (0.02 * np.sin(2 * np.pi * 220 * t) * np.where(t >= loud_from, 4.0, 1.0)).astype(np.float32)
    return x


@pytest.mark.parametrize("tool", ["music_fit", "speaker_turns", "screen_zoom"])
def test_music_fit_speaker_screen_zoom_help_is_fast_and_documents_usage(tool):
    best = 99.0
    for _ in range(2):
        t = time.monotonic()
        p = run(tool, "--help")
        assert p.returncode == 0, p.stderr
        best = min(best, time.monotonic() - t)
    assert best < 1.5, (tool, best)
    doc = (TOOLS / f"{tool}.py").read_text(encoding="utf-8")
    assert "Usage:" in doc and "Exit:" in doc


@pytest.mark.parametrize("tool,args", [("music_fit", ["missing.wav", "--length", "10"]), ("speaker_turns", ["--words", "missing.json", "--tracks", "a.wav", "b.wav", "-o", "o.json"]),
                                       ("screen_zoom", ["missing.mp4", "-o", "o.json"])])
def test_music_fit_speaker_screen_zoom_missing_input_fails_closed_with_exit_2(tool, args, tmp_path):
    p = subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / f"{tool}.py"), *args], capture_output=True, text=True, encoding="utf-8", cwd=tmp_path)
    assert p.returncode == 2 and "not found" in p.stderr, p.stderr
    assert not (tmp_path / "o.json").exists()


# ------------------------------------------------------------------------------------------------ music_fit
def test_music_fit_puts_the_rise_on_the_hit_and_starts_on_a_downbeat():
    import music_fit as mf

    x = click_track()
    r = mf.fit(x, SR, 10.0, 6.0)
    assert abs(r["bpm"] - 120) < 0.5 and r["loop"] is False and r["bar_s"] == pytest.approx(2.0, abs=0.01)
    assert abs(r["start_s"] - 24.0) < 0.06, r  # the loud section starts at 30 s = start + 6
    assert abs(r["rise"]["at_video_s"] - 6.0) < 0.3 and r["rise"]["db"] > 6
    assert abs((r["start_s"] % 2.0)) < 0.06 or abs((r["start_s"] % 2.0) - 2.0) < 0.06  # a downbeat (accented click every 2 s from 0)
    assert r["end_s"] == pytest.approx(r["start_s"] + 10.0) and r["ending"] == "bar_end" and r["fade_out_s"] == 0.0  # 10 s = 5 bars
    assert set(r) >= {"start_s", "end_s", "fade_out_s", "loop", "bpm", "score", "reason"}


def test_music_fit_without_hit_still_contains_the_rise_and_fades_when_the_length_is_not_whole_bars():
    import music_fit as mf

    x = click_track()
    r = mf.fit(x, SR, 9.0, None)
    assert r["start_s"] < 30.0 < r["end_s"] and r["ending"] == "fade" and r["fade_out_s"] == pytest.approx(2.0, abs=0.01)  # 9 s = 4.5 bars: fade over one bar
    assert abs(r["start_s"] % 2.0) < 0.06 or abs(r["start_s"] % 2.0 - 2.0) < 0.06


def test_music_fit_loops_whole_bars_when_the_track_is_too_short():
    import music_fit as mf

    r = mf.fit(click_track(8.0, 99.0), SR, 20.0, None)
    lp = r["loop_points"]
    assert r["loop"] is True and lp["bars"] == 4 and lp["loop_s"] == pytest.approx(8.0, abs=0.05) and lp["plays"] == 3
    assert lp["to_s"] < 0.05 and lp["from_s"] <= 8.0 and "shorter" in r["reason"]


@pytest.mark.ffmpeg
def test_music_fit_cli_writes_json_and_refuses_a_hit_outside_the_video(tmp_path):
    wav = write_wav(tmp_path / "bed.wav", click_track(40.0, 20.0))
    out = tmp_path / "fit.json"
    p = run("music_fit", wav, "--length", "8", "--hit", "4", "-o", out)
    assert p.returncode == 0, p.stderr
    r = json.loads(out.read_text(encoding="utf-8"))
    assert abs(r["start_s"] - 16.0) < 0.06 and r["track"] == "bed.wav" and r["house_defaults"]["beats_per_bar"] == 4
    assert run("music_fit", wav, "--length", "8", "--hit", "9").returncode == 2
    assert run("music_fit", wav, "--length", "0").returncode == 2


# ------------------------------------------------------------------------------------------------ speaker_turns
def test_speaker_labels_margin_overlap_unknown_and_smoothing():
    import speaker_turns as st

    names = ["Dana", "Avi"]
    gate = [-40.0, -40.0]
    lv = [[-20, -38], [-21, -40], [-35, -20], [-22, -24], [-60, -62], [-30, -36]]
    labs = st.label_words(lv, names, gate, 6.0)
    assert [x["speaker"] for x in labs] == ["Dana", "Dana", "Avi", "overlap", "unknown", "Dana"]
    words = [{"w": f"w{i}", "start": i * 0.4, "end": i * 0.4 + 0.3} for i in range(3)]
    flip = st.smooth_flips(words, [{"speaker": "Dana", "margin": 15}, {"speaker": "Avi", "margin": 7}, {"speaker": "Dana", "margin": 14}], 6.0, names)
    assert flip[1]["speaker"] == "Dana" and flip[1]["smoothed"]
    strong = st.smooth_flips(words, [{"speaker": "Dana", "margin": 15}, {"speaker": "Avi", "margin": 20}, {"speaker": "Dana", "margin": 14}], 6.0, names)
    assert strong[1]["speaker"] == "Avi"  # a clear one-word answer stays
    t = st.turns([{"speaker": "Dana", "start": 0, "end": 1}, {"speaker": "Dana", "start": 1.1, "end": 2}, {"speaker": "Avi", "start": 2.2, "end": 3}])
    assert [(x["speaker"], x["words"], x["first_word"]) for x in t] == [("Dana", 2, 0), ("Avi", 1, 2)]


def _two_mics(tmp_path):
    """Dana talks 0-3 s, Avi 3.5-6 s, both 6.5-7.5 s; each mic hears the other 20 dB down. Words follow that, plus one bleed-flip word."""
    import numpy as np

    n = int(SR * 8)
    t = np.arange(n) / SR
    rng = np.random.default_rng(1)

    def voice(a, b, f):
        m = ((t >= a) & (t < b)).astype(np.float64)
        return m * (0.3 * np.sin(2 * np.pi * f * t) + 0.05 * rng.normal(0, 1, n))

    dana = voice(0, 3, 210) + voice(6.5, 7.5, 210)
    avi = voice(3.5, 6, 140) + voice(6.5, 7.5, 140)
    floor = 0.001 * rng.normal(0, 1, n)
    mic_a, mic_b = dana + 0.1 * avi + floor, avi + 0.1 * dana + floor
    words = [{"w": "shalom", "start": 0.1, "end": 0.6}, {"w": "ma", "start": 0.7, "end": 1.0}, {"w": "nishma", "start": 1.1, "end": 1.6},
             {"w": "tov", "start": 3.6, "end": 4.0}, {"w": "toda", "start": 4.1, "end": 4.6}, {"w": "beseder", "start": 4.7, "end": 5.4},
             {"w": "yachad", "start": 6.6, "end": 7.2}]
    wj = tmp_path / "words.json"
    wj.write_text(json.dumps({"schema": "avc.words/1", "language": "he", "words": words}), encoding="utf-8")
    return write_wav(tmp_path / "dana.wav", mic_a), write_wav(tmp_path / "avi.wav", mic_b), write_wav(tmp_path / "stereo.wav", np.stack([mic_a, mic_b], axis=1)), wj


@pytest.mark.ffmpeg
def test_speaker_turns_from_two_tracks_and_from_stereo_channels_agree(tmp_path):
    a, b, stereo, wj = _two_mics(tmp_path)
    out = tmp_path / "words_speakers.json"
    p = run("speaker_turns", "--words", wj, "--tracks", a, b, "--names", "Dana,Avi", "-o", out)
    assert p.returncode == 0, p.stderr
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["schema"] == "avc.words/1" and d["language"] == "he"
    assert [w["speaker"] for w in d["words"]] == ["Dana", "Dana", "Dana", "Avi", "Avi", "Avi", "overlap"]
    assert [(x["speaker"], x["words"]) for x in d["turns"]] == [("Dana", 3), ("Avi", 3), ("overlap", 1)]
    out2 = tmp_path / "ch.json"
    p = run("speaker_turns", "--words", wj, "--channels", stereo, "--names", "Dana,Avi", "-o", out2)
    assert p.returncode == 0, p.stderr
    d2 = json.loads(out2.read_text(encoding="utf-8"))
    assert [w["speaker"] for w in d2["words"]] == [w["speaker"] for w in d["words"]] and d2["speakers"]["source"] == "channels"
    p = run("speaker_turns", "--words", wj, "--tracks", stereo, "--channels", "-o", tmp_path / "ch2.json")
    assert p.returncode == 0, p.stderr
    assert run("speaker_turns", "--words", wj, "--tracks", a, b, "--names", "Dana", "-o", tmp_path / "x.json").returncode == 2  # names do not match
    assert run("speaker_turns", "--words", wj, "--tracks", a, "-o", tmp_path / "x.json").returncode == 2  # one track is not a conversation
    assert run("speaker_turns", "--words", wj, "--channels", a, "-o", tmp_path / "x.json").returncode == 2  # a mono file has no channels to split


# ------------------------------------------------------------------------------------------------ screen_zoom
def test_screen_zoom_never_crops_below_the_minimum_and_dead_time_arithmetic():
    import screen_zoom as sz

    small = sz.zoom_for({"x": 0.9, "y": 0.0, "w": 0.05, "h": 0.05}, 0.4)
    assert small["crop"] == 0.4 and small["scale"] == 2.5 and small["cx"] == pytest.approx(0.8) and small["cy"] == pytest.approx(0.2)  # kept inside the frame
    assert sz.zoom_for({"x": 0, "y": 0, "w": 0.9, "h": 0.9}, 0.4)["zoom"] is False
    assert sz.still_ranges([False, False, False, False, False, False, False, True, False], 4.0, 1.5) == [(0.0, 1.5)]
    assert sz.subtract([(0.0, 5.0)], [(1.0, 1.5)], 1.5) == [(1.5, 5.0)]
    lines = sz.lines_of([{"w": "a", "start": 1.0, "end": 1.2}, {"w": "b", "start": 1.4, "end": 1.6}, {"w": "c", "start": 6.0, "end": 6.4}])
    assert [ln["text"] for ln in lines] == ["a b", "c"]
    assert [m["text"] for m in sz.cue_misses(lines, [2.5], 1.5)] == ["c"]


@pytest.fixture(scope="module")
def screen(tmp_path_factory):
    d = tmp_path_factory.mktemp("screen")
    src = d / "screen.mp4"
    vf = ("drawbox=x=400:y=40:w=120:h=80:color=red:t=fill:enable='gte(t,2)',"  # a red panel appears at 2 s (nearly the grey's brightness: colour must count)
          "drawbox=x=40:y=240:w=160:h=60:color=yellow:t=fill:enable='gte(t,5)'")  # a yellow bar appears at 5 s
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x404040:s=640x360:r=30:d=8", "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)],
                   check=True, timeout=120)
    words = [{"w": "here", "start": 2.3, "end": 2.8}, {"w": "wait", "start": 3.6, "end": 4.0}, {"w": "nothing", "start": 7.0, "end": 7.6}]
    wj = d / "words.json"
    wj.write_text(json.dumps({"schema": "avc.words/1", "words": words}), encoding="utf-8")
    return {"dir": d, "src": src, "words": wj}


@pytest.mark.ffmpeg
def test_screen_zoom_finds_the_boxes_the_dead_time_and_the_cue_miss(screen):
    out = screen["dir"] / "zoom.json"
    p = run("screen_zoom", screen["src"], "--words", screen["words"], "-o", out)
    assert p.returncode == 0, p.stderr
    z = json.loads(out.read_text(encoding="utf-8"))
    ev = z["events"]
    assert [round(e["t_s"], 2) for e in ev] == [2.0, 5.0], ev
    b1 = ev[0]["box"]
    assert abs(b1["x"] - 400 / 640) <= 0.05 and abs(b1["y"] - 40 / 360) <= 0.06 and abs(b1["w"] - 120 / 640) <= 0.07 and abs(b1["h"] - 80 / 360) <= 0.1
    k1 = z["zoom_keys"][0]
    assert k1["zoom"] and k1["scale"] == 2.5 and k1["crop"] == 0.4 and "readable" in k1["why"]  # a small panel is capped at the 40 % minimum crop
    assert abs(k1["cx"] - (400 + 60) / 640) < 0.05 and k1["camera_path_zoom"].startswith("2:")
    dead = [(d["start_s"], d["end_s"]) for d in z["dead"]]
    assert len(dead) == 2 and dead[0][0] == 0.0 and 1.5 <= dead[0][1] <= 2.0 and dead[1][0] == 5.0 and abs(dead[1][1] - 6.85) < 0.01, dead  # speech at 7.0 ends the second
    assert [m["text"] for m in z["cue_misses"]] == ["nothing"] and z["house_defaults"]["min_crop"] == 0.4
    # zoom.json is a camera_path input as it is: the zoom keys become the camera path's windows (no faces.json needed)
    assert z["fps"] == "30" and z["camera_path_args"][:2] == ["--zoom", k1["camera_path_zoom"]] and "--duration" in z["camera_path_args"]
    cam_dir = screen["dir"] / "cam"
    p = run("camera_path", out, *z["camera_path_args"], "-o", cam_dir)
    assert p.returncode == 0, p.stderr
    cam = json.loads((cam_dir / "camera_path.json").read_text(encoding="utf-8"))
    assert [w["scale"] for w in cam["windows"]] == [2.5, 2.5]
    assert [w["cx"] for w in cam["windows"]] == [pytest.approx(z["zoom_keys"][0]["cx"], abs=1e-4), pytest.approx(z["zoom_keys"][1]["cx"], abs=1e-4)]
    out2 = screen["dir"] / "zoom_nowords.json"
    assert run("screen_zoom", screen["src"], "-o", out2).returncode == 0
    z2 = json.loads(out2.read_text(encoding="utf-8"))
    assert z2["cue_misses"] is None and any(d["start_s"] == 2.0 and d["end_s"] >= 4.5 for d in z2["dead"])  # without words the 2-5 s wait is dead time
    assert run("screen_zoom", screen["src"], "-o", out2, "--min-crop", "0").returncode == 2


# ------------------------------------------------------------------------------------------------ analyze motion_kind
@pytest.fixture(scope="module")
def motion_clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("motion")
    still = d / "still.png"
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i", "mandelbrot=s=1280x720:r=1", "-frames:v", "1", str(still)], check=True, timeout=120)
    mk = {
        "still": ["-loop", "1", "-i", str(still), "-t", "3", "-r", "30", "-vf", "scale=640:360,format=yuv420p"],
        "still_push": ["-loop", "1", "-i", str(still), "-vf", "zoompan=z='1+0.004*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=90:s=640x360:fps=30,format=yuv420p", "-frames:v", "90"],
        "pan": ["-loop", "1", "-i", str(still), "-t", "3", "-r", "30", "-vf", "scale=1600:900,crop=640:360:x='100+t*120':y=200,format=yuv420p"],
        "motion": ["-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=3", "-f", "lavfi", "-i", "testsrc=s=200x200:r=30:d=3",
                   "-filter_complex", "[0][1]overlay=x='50+t*100':y=20[t];[t][1]overlay=x='500-t*120':y=150,format=yuv420p"],
    }
    out = {}
    for name, args in mk.items():
        out[name] = d / f"{name}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *args, "-c:v", "libx264", str(out[name])], check=True, timeout=120)
    return out


@pytest.mark.ffmpeg
def test_analyze_motion_kind_tells_a_still_an_animated_still_and_real_motion_apart(motion_clips):
    import analyze
    from core import analysis
    from core.ffprobe import probe
    from core.media import FrameReader

    got = {}
    for name, f in motion_clips.items():
        info = probe(f)
        tw, th = analysis.thumb_size(*info.first_video.display_size)
        feats = analysis.extract_features(FrameReader(f, pix_fmt="rgb24", scale=(tw, th), info=info))
        got[name] = analyze.shot_motion(feats.thumbs, 0, feats.n - 1, 30.0)
    kinds = {k: v["motion_kind"] for k, v in got.items()}
    assert kinds == {"still": "still", "still_push": "still_push", "pan": "still_push", "motion": "motion"}, got
    assert got["still_push"]["zoom_per_s"] > 1.05 and abs(got["pan"]["pan_x_per_s"] - 120 / 640) < 0.03  # the measured move is reported too

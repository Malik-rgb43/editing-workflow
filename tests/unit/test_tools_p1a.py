"""hf_mix, source_cuts, motion_qa (P1, wave A) - real FFmpeg media generated in hostile-named temp folders."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO / "src"))


def run(tool, *args, timeout=300):
    p = subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / f"{tool}.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    d = None
    if p.stdout.strip().startswith("{"):
        try:
            d = json.loads(p.stdout)
        except json.JSONDecodeError:
            pass
    return p.returncode, d, p


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *map(str, args)], check=True, timeout=300)


@pytest.mark.parametrize("tool", ["hf_mix", "source_cuts", "motion_qa"])
def test_help_fast(tool):
    t = time.monotonic()
    p = subprocess.run([sys.executable, str(TOOLS / f"{tool}.py"), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0 and time.monotonic() - t < 1.5


# ------------------------------------------------------------------------------------------------ hf_mix
@pytest.fixture()
def mixdir(tmp_path):
    d = tmp_path / "מיקס 'x' 🎬"
    (d / "assets").mkdir(parents=True)
    a = d / "assets"
    ff("-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-ar", "48000", a / "vo1.wav")
    ff("-f", "lavfi", "-i", "sine=frequency=330:duration=2", "-ar", "48000", a / "vo2.wav")
    ff("-f", "lavfi", "-i", "anoisesrc=color=pink:duration=4:amplitude=0.5", "-ar", "48000", a / "bed.wav")
    ff("-f", "lavfi", "-i", "sine=frequency=1000:duration=0.2", "-ar", "48000", a / "hit.wav")
    return d


def write_cues(d, **over):
    cues = {"duration": 8.0, "master": {"lufs": -14, "tp": -1.0},
            "vo": [{"file": "assets/vo1.wav", "start": 0.5}, {"file": "assets/vo2.wav", "start": 4.0, "gain_db": -2}],
            "music": {"file": "assets/bed.wav", "start": 0, "gain_db": -16, "duck_db": -10, "loop": True, "fade_out": 1.0},
            "sfx": [{"file": "assets/hit.wav", "at": 3.0, "gain_db": -22, "lead_frames": 2, "fps": 30}]}
    cues.update(over)
    f = d / "cues.json"
    f.write_text(json.dumps(cues), encoding="utf-8")
    return f


@pytest.mark.ffmpeg
class TestHfMix:
    def test_mix_lands_on_target_and_reports(self, mixdir):
        f = write_cues(mixdir)
        out = mixdir / "mix.wav"
        rc, d, p = run("hf_mix", f, "-o", out, "--report")
        assert rc == 0, p.stderr + p.stdout
        assert abs(d["master"]["lufs"] - (-14)) <= 1.0 and d["master"]["true_peak_dbtp"] <= -0.95
        assert abs(d["duration_s"] - 8.0) < 0.1 and d["problems"] == []
        assert out.is_file()

    def test_ducking_makes_the_bed_quieter_under_vo(self, mixdir):
        import hf_mix

        c = hf_mix.load_cues(write_cues(mixdir))
        _, graph, _ = hf_mix.build_graph(c, duck=True)
        _, graph_nd, _ = hf_mix.build_graph(c, duck=False)
        assert "sidechaincompress" in graph and "sidechaincompress" not in graph_nd

    def test_sfx_is_placed_lead_frames_before_the_picture_event(self, mixdir):
        import hf_mix

        c = hf_mix.load_cues(write_cues(mixdir))
        assert abs(c["sfx"][0]["start"] - (3.0 - 2 / 30)) < 1e-9

    def test_missing_file_and_bad_cues_refuse(self, mixdir, tmp_path):
        f = write_cues(mixdir, vo=[{"file": "assets/absent.wav", "start": 0}])
        rc, _, p = run("hf_mix", f, "-o", mixdir / "m.wav")
        assert rc == 2 and "not found" in p.stderr and not (mixdir / "m.wav").exists()
        g = tmp_path / "bad.json"
        g.write_text('{"duration": 5}', encoding="utf-8")
        assert run("hf_mix", g, "-o", tmp_path / "m.wav")[0] == 2

    def test_clipped_hot_input_is_normalised_not_shipped_hot(self, mixdir):
        ff("-f", "lavfi", "-i", "sine=frequency=440:duration=3,volume=12", "-ar", "48000", mixdir / "assets" / "vo1.wav")
        f = write_cues(mixdir)
        rc, d, p = run("hf_mix", f, "-o", mixdir / "mix.wav", "--report")
        assert rc == 0 and d["master"]["true_peak_dbtp"] <= -0.95


# ------------------------------------------------------------------------------------------------ source_cuts
@pytest.mark.ffmpeg
class TestSourceCuts:
    def _two_shots(self, d):
        out = d / "cut.mkv"
        # two different shots joined with the concat FILTER (a list file would choke on the apostrophe in this folder name)
        ff("-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25:duration=2", "-f", "lavfi", "-i", "mandelbrot=size=320x240:rate=25",
           "-filter_complex", "[1:v]trim=duration=2,setpts=PTS-STARTPTS[b];[0:v][b]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-c:v", "ffv1", out)
        return out

    def test_finds_the_hidden_cut_with_cover_window_and_real_time(self, tmp_path):
        d = tmp_path / "חתך 'x' 🎬"
        d.mkdir()
        v = self._two_shots(d)
        rc, data, p = run("source_cuts", v, "-o", d / "cuts.json")
        assert rc == 0, p.stderr
        assert [c["frame"] for c in data["cuts"]] == [50]
        c = data["cuts"][0]
        assert c["time_s"] == 2.0 and c["cover"] == [44, 55] and c["timecode"] == "00:00:02.000"
        assert (d / "cuts.json").is_file()

    def test_clean_clip_has_no_cuts_and_missing_input_fails_closed(self, e04_set, tmp_path):
        rc, data, _ = run("source_cuts", e04_set["clean"])
        assert rc == 0 and data["cuts"] == []
        rc2, _, p = run("source_cuts", tmp_path / "absent.mkv")
        assert rc2 == 2

    def test_detect_pure_function(self):
        import source_cuts

        d = [0.0] + [3.0] * 20 + [60.0] + [3.0] * 20
        assert source_cuts.detect(d) == [(21, 60.0)]
        assert source_cuts.detect([0.0, 1.0]) == []


# ------------------------------------------------------------------------------------------------ motion_qa
cv2 = pytest.importorskip("cv2")


def pan_video(d, name, x_expr):
    """Pan across a static blurred-noise still (trackable texture, no moving objects): ground truth = x_expr pixels per frame."""
    tex = d / "tex.png"
    if not tex.exists():
        ff("-f", "lavfi", "-i", "nullsrc=size=1280x480,format=gray,geq=lum='random(1)*255'", "-frames:v", "1", "-vf", "gblur=sigma=1.2", tex)
    out = d / name
    ff("-loop", "1", "-framerate", "30", "-i", tex, "-vf", f"crop=480:360:x='{x_expr}':y=60", "-t", "2", "-c:v", "ffv1", out)
    return out


@pytest.mark.ffmpeg
class TestMotionQa:
    def test_smooth_pan_passes_with_coverage(self, tmp_path):
        v = pan_video(tmp_path, "smooth.mkv", "n*8")
        rc, d, p = run("motion_qa", v)
        assert rc == 0, d["findings"] if d else p.stderr
        assert d["extra"]["tracked_pair_coverage"] > 0.9 and d["decoded_frames"] == d["expected_frames"] == 60

    def test_stutter_is_found_with_frame_and_time(self, tmp_path):
        # constant pan with a 6-frame freeze: velocity drops to 0 then jumps back (an acceleration spike + reversal-free stall)
        v = pan_video(tmp_path, "stutter.mkv", "if(between(n,30,36),30*8,n*8)")
        rc, d, p = run("motion_qa", v)
        assert rc == 1, d["findings"] if d else p.stderr
        assert any(f["code"] == "accel_spike" and 29 <= f["frame"] <= 38 for f in d["findings"])

    def test_pan_reversal_is_found(self, tmp_path):
        v = pan_video(tmp_path, "rev.mkv", "if(lt(n,30),n*10,300-(n-30)*10)")
        rc, d, _ = run("motion_qa", v)
        assert rc == 1 and any(f["code"] == "reversal" and 28 <= f["frame"] <= 32 for f in d["findings"])

    def test_low_feature_clip_is_insufficient_evidence_not_a_crash_E04_B07(self, e04_set):
        rc, d, p = run("motion_qa", e04_set["low_feature"])
        assert rc == 2 and d["status"] == "INSUFFICIENT_EVIDENCE"
        assert "insufficient_tracked_pairs" in [f["code"] for f in d["findings"]] and "Traceback" not in p.stderr

    def test_missing_input_fails_closed(self, tmp_path):
        rc, d, _ = run("motion_qa", tmp_path / "absent.mkv")
        assert rc != 0 and d["status"] == "INSUFFICIENT_EVIDENCE"

    def test_analyse_series_unit(self):
        from core.timebase import FrameClock
        import motion_qa

        clock = FrameClock.cfr("30", 40)
        tx = [0.0] + [8.0] * 38 + [8.0]
        meas = [False] + [True] * 39
        assert motion_qa.analyse_series(tx, [0.0] * 40, [0.0] * 40, meas, clock=clock) == []
        tx[20] = 0.0
        found = motion_qa.analyse_series(tx, [0.0] * 40, [0.0] * 40, meas, clock=clock)
        assert any(f.code == "accel_spike" and f.frame in (20, 21) for f in found)

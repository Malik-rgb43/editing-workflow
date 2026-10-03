"""aroll_cut, render_watch, face_center, camera_path (P1, wave C)."""

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


def run(tool, *args, timeout=300, env=None):
    p = subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / f"{tool}.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout, env=env)
    d = None
    if p.stdout.strip().startswith("{"):
        try:
            d = json.loads(p.stdout)
        except json.JSONDecodeError:
            pass
    return p.returncode, d, p


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *map(str, args)], check=True, timeout=300)


@pytest.mark.parametrize("tool", ["aroll_cut", "render_watch", "face_center", "camera_path"])
def test_help_fast(tool):
    t = time.monotonic()
    p = subprocess.run([sys.executable, str(TOOLS / f"{tool}.py"), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0 and time.monotonic() - t < 1.5


# ------------------------------------------------------------------------------------------------ aroll_cut
WORDS = [  # sentence 1: 1.0-2.0 s, sentence 2: 3.0-4.0 s, sentence 3: 5.5-6.5 s (speech = tone bursts in the synthetic audio)
    ("שלום", 1.0, 1.4), ("לכולם.", 1.5, 2.0), ("היום", 3.0, 3.4), ("נדבר", 3.5, 4.0), ("על", 5.5, 5.8), ("עריכה.", 5.9, 6.5)]


@pytest.fixture()
def speech(tmp_path):
    d = tmp_path / "קול 'x' 🎬"
    d.mkdir()
    # tone bursts exactly at the word spans, silence (digital) elsewhere, plus a faint noise floor so "quietest" is meaningful
    expr = "+".join(f"between(t,{s},{e})" for _, s, e in WORDS)
    ff("-f", "lavfi", "-i", f"aevalsrc='0.4*sin(2*PI*220*t)*({expr})+0.001*sin(2*PI*50*t)':s=16000:d=8", d / "speech.wav")
    (d / "words.json").write_text(json.dumps({"schema": "avc.words/1", "words": [{"w": w, "start": s, "end": e} for w, s, e in WORDS]}, ensure_ascii=False), encoding="utf-8")
    return d


class TestArollCut:
    def test_pure_split_and_keep_parse(self):
        import aroll_cut

        words = [{"w": w, "start": s, "end": e} for w, s, e in WORDS]
        sents = aroll_cut.split_sentences(words, gap=0.7)
        assert [len(s) for s in sents] == [2, 2, 2]
        assert aroll_cut.parse_keep("1,3", 3) == [1, 3] and aroll_cut.parse_keep("1-2", 3) == [1, 2] and aroll_cut.parse_keep(None, 3) == [1, 2, 3]
        with pytest.raises(ValueError):
            aroll_cut.parse_keep("4", 3)

    @pytest.mark.ffmpeg
    def test_in_points_sit_in_the_silence_and_never_clip_words(self, speech):
        out = speech / "out"
        rc, d, p = run("aroll_cut", speech / "words.json", speech / "speech.wav", "-o", out, "--keep", "1,3")
        assert rc == 0, p.stderr
        edit = json.loads((out / "edit.json").read_text(encoding="utf-8"))
        s1, s3 = edit["segments"]
        assert s1["id"] == 1 and s3["id"] == 3
        assert s1["src_in"] <= 1.0 - 0.005 and s1["src_in"] >= 0.0  # before the first word, in the silence
        assert s1["src_out"] >= 2.0 + 0.005 and s1["src_out"] < 3.0  # after the last word, before sentence 2 begins
        assert s3["src_in"] > 4.0 and s3["src_in"] < 5.5 and s3["src_out"] >= 6.5
        assert s3["dst_in"] == s1["dst_out"] and edit["total_s"] == s3["dst_out"]
        cuts = json.loads((out / "src_cuts.json").read_text(encoding="utf-8"))
        assert cuts["joins"][0]["between"] == [1, 3] and cuts["joins"][0]["cover_frames_each_side"] == 6
        assert (out / "cut_text.txt").read_text(encoding="utf-8").splitlines() == ["שלום לכולם.", "על עריכה."]

    @pytest.mark.ffmpeg
    def test_refusals(self, speech, tmp_path):
        assert run("aroll_cut", speech / "words.json", speech / "speech.wav", "-o", tmp_path / "o", "--keep", "9")[0] == 2
        empty = tmp_path / "w.json"
        empty.write_text('{"words": []}', encoding="utf-8")
        assert run("aroll_cut", empty, speech / "speech.wav", "-o", tmp_path / "o")[0] == 2
        assert run("aroll_cut", speech / "words.json", tmp_path / "absent.wav", "-o", tmp_path / "o")[0] == 2


# ------------------------------------------------------------------------------------------------ render_watch
class TestRenderWatch:
    def _env(self, tmp_path):
        import os

        return dict(os.environ, AVC_PATHS_LOCK_PATH=str(tmp_path / "lock" / "r.lock"))

    def test_parse_progress_and_eta(self):
        import render_watch as rw

        assert rw.parse_progress("Rendering frame 45/900 ...") == {"frame": 45, "total": 900, "percent": 5.0}
        assert rw.parse_progress("progress: 37.5%")["percent"] == 37.5
        assert rw.parse_progress("nothing here") is None and rw.parse_progress("frame 10/5") is None
        assert rw.eta_seconds({"frame": 30, "total": 100, "percent": 30}, 10, 60) is None  # too early
        assert rw.eta_seconds({"frame": 100, "total": 300, "percent": 33}, 10, 60) == 20.0

    def test_passes_the_child_exit_code_and_writes_status(self, tmp_path):
        script = tmp_path / "child.py"
        script.write_text("import sys\nfor i in range(1,6):\n    print(f'frame {i}/5', flush=True)\nsys.exit(0)\n", encoding="utf-8")
        st = tmp_path / "ס 'x'" / "status.json"
        rc, _, p = run("render_watch", "--status", st, "--heartbeat", "0.2", "--", sys.executable, script, env=self._env(tmp_path))
        assert rc == 0, p.stderr
        d = json.loads(st.read_text(encoding="utf-8"))
        assert d["state"] == "finished" and d["progress"]["frame"] == 5 and d["progress"]["total"] == 5
        script.write_text("import sys\nprint('frame 1/5', flush=True)\nsys.exit(7)\n", encoding="utf-8")
        rc2, _, _ = run("render_watch", "--status", st, "--", sys.executable, script, env=self._env(tmp_path))
        assert rc2 == 7 and json.loads(st.read_text(encoding="utf-8"))["state"] == "failed"

    def test_stall_kills_only_its_own_process_tree(self, tmp_path):
        script = tmp_path / "hang.py"
        script.write_text("import time\nprint('frame 1/100', flush=True)\ntime.sleep(60)\n", encoding="utf-8")
        st = tmp_path / "status.json"
        t = time.monotonic()
        rc, _, p = run("render_watch", "--status", st, "--stall", "1.5", "--heartbeat", "0.5", "--", sys.executable, script, env=self._env(tmp_path), timeout=60)
        assert rc == 124 and time.monotonic() - t < 30 and "stalled" in p.stderr
        assert json.loads(st.read_text(encoding="utf-8"))["state"] == "stalled"

    def test_lock_busy_exits_75_and_no_command_exits_2(self, tmp_path):
        env = self._env(tmp_path)
        holder = subprocess.Popen([sys.executable, "-X", "utf8", str(TOOLS / "render_lock.py"), "run", "--job", "holder", "--", sys.executable, "-c", "import time; time.sleep(6)"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(2.0)
            script = tmp_path / "c.py"
            script.write_text("print('x')\n", encoding="utf-8")
            rc, _, p = run("render_watch", "--status", tmp_path / "s.json", "--", sys.executable, script, env=env)
            assert rc == 75, (rc, p.stderr)
        finally:
            holder.wait(timeout=30)
        assert run("render_watch", "--status", tmp_path / "s.json")[0] == 2


# ------------------------------------------------------------------------------------------------ face_center + camera_path
def faces(cxs, every=5, fps="30"):
    return {"schema": "avc.faces/1", "fps": fps, "samples": [{"frame": i * every, "time_s": i * every / 30, "cx": c, "cy": 0.4, "h_norm": 0.3} for i, c in enumerate(cxs)]}


class TestFaceCenter:
    def test_off_centre_runs_pure(self):
        import face_center as fc

        s = [{"frame": i, "cx": c} for i, c in enumerate([0.5, 0.52, 0.7, 0.71, 0.72, 0.7, 0.73, 0.7, 0.5, None, 0.8])]
        assert fc.off_centre_runs(s, tol=0.08, min_run=6) == [(2, 7, pytest.approx(0.2, abs=0.02))]
        assert fc.off_centre_runs(s, tol=0.08, min_run=7) == []

    def test_audit_cli_flags_the_run_with_frame_and_time_and_passes_a_centred_track(self, tmp_path):
        f = tmp_path / "faces.json"
        f.write_text(json.dumps(faces([0.5] * 5 + [0.72] * 8 + [0.5] * 5)), encoding="utf-8")
        rc, d, _ = run("face_center", "audit", f)
        assert rc == 1 and d["findings"][0]["code"] == "off_centre" and d["findings"][0]["frame"] == 25
        g = tmp_path / "ok.json"
        g.write_text(json.dumps(faces([0.5, 0.52, 0.49] * 6)), encoding="utf-8")
        rc2, d2, _ = run("face_center", "audit", g)
        assert rc2 == 0 and d2["status"] == "PASS"

    def test_audit_without_faces_is_insufficient_evidence(self, tmp_path):
        f = tmp_path / "none.json"
        f.write_text(json.dumps(faces([None] * 10)), encoding="utf-8")
        rc, d, _ = run("face_center", "audit", f)
        assert rc == 2 and "low_face_coverage" in [x["code"] for x in d["findings"]]

    @pytest.mark.ffmpeg
    def test_source_on_a_clip_without_faces_is_refused_not_passed(self, e04_set, tmp_path):
        pytest.importorskip("cv2")
        rc, _, p = run("face_center", "source", e04_set["clean"], "-o", tmp_path / "f.json")
        # either no detector exists in this OpenCV build (OpenCV 5 dropped Haar) or the clip has no face: both are refusals, never a pass
        assert rc == 2 and ("INSUFFICIENT_EVIDENCE" in p.stderr or "no face detector available" in p.stderr) and not (tmp_path / "f.json").exists()

    def test_missing_model_file_is_refused(self, e04_set, tmp_path):
        pytest.importorskip("cv2")
        rc, _, p = run("face_center", "source", e04_set["clean"], "-o", tmp_path / "f.json", "--model", tmp_path / "absent.onnx")
        assert rc == 2 and "not found" in p.stderr


class TestCameraPath:
    def _faces(self, tmp_path, cxs):
        f = tmp_path / "faces.json"
        f.write_text(json.dumps(faces(cxs)), encoding="utf-8")
        return f

    def test_smoothed_path_is_far_smoother_than_following_the_face_per_frame(self, tmp_path):
        import random

        random.seed(3)
        cxs = [0.55 + random.uniform(-0.04, 0.04) for _ in range(80)]  # jittery detector output
        f = self._faces(tmp_path, cxs)
        out = tmp_path / "cam"
        rc, d, p = run("camera_path", f, "--zoom", "2.0:6.0:1.25", "--zoom", "8.0:11.0:1.4", "-o", out, "--duration", "13")
        assert rc == 0, p.stderr
        assert d["peak_accel_cx_per_s2"] < d["naive_follow_peak_accel_cx_per_s2"] / 5
        cam = json.loads((out / "camera_path.json").read_text(encoding="utf-8"))
        w1 = cam["windows"][0]
        assert 0.5 / 1.25 <= w1["cx"] <= 1 - 0.5 / 1.25  # the crop never leaves the frame
        assert abs(cam["samples"][0]["cx"] - 0.5) < 1e-9 and cam["samples"][0]["scale"] == 1.0
        mid = next(s for s in cam["samples"] if abs(s["t"] - 4.0) < 1e-3)
        assert mid["scale"] == pytest.approx(1.25, abs=1e-6) and mid["cx"] == pytest.approx(w1["cx"], abs=1e-4)
        rig = (out / "rig.js").read_text(encoding="utf-8")
        assert "addCameraRig" in rig and "power2.inOut" in rig

    def test_window_without_a_face_is_refused_never_guessed(self, tmp_path):
        f = self._faces(tmp_path, [0.5] * 10)  # samples cover 0-1.5 s only
        rc, _, p = run("camera_path", f, "--zoom", "5.0:8.0:1.3", "-o", tmp_path / "cam")
        assert rc == 2 and "no measured face" in p.stderr and not (tmp_path / "cam" / "camera_path.json").exists()

    def test_bad_window_refused(self, tmp_path):
        f = self._faces(tmp_path, [0.5] * 10)
        assert run("camera_path", f, "--zoom", "1.0:0.5:1.2", "-o", tmp_path / "cam")[0] == 2
        assert run("camera_path", f, "--zoom", "0.2:1.0:0.8", "-o", tmp_path / "cam")[0] == 2

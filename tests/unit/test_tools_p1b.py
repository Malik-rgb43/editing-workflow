"""seg_diff, grade_bake, motion_scan (P1, wave B)."""

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


def codes(d):
    return [f["code"] for f in d["findings"]]


@pytest.mark.parametrize("tool", ["seg_diff", "grade_bake", "motion_scan"])
def test_help_fast(tool):
    t = time.monotonic()
    p = subprocess.run([sys.executable, str(TOOLS / f"{tool}.py"), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0 and time.monotonic() - t < 1.5


@pytest.mark.ffmpeg
class TestSegDiff:
    def _pair(self, d, changed=(20, 29)):
        a, b = d / "a.mkv", d / "b.mkv"
        base = "testsrc2=size=320x240:rate=30:duration=3"
        ff("-f", "lavfi", "-i", base, "-c:v", "ffv1", a)
        lo, hi = changed
        ff("-f", "lavfi", "-i", base, "-vf", f"drawbox=x=0:y=0:w=320:h=240:color=red@1:t=fill:enable='between(n,{lo},{hi})'", "-c:v", "ffv1", b)
        return a, b

    def test_identical_renders_pass(self, e04_set, tmp_path):
        rc, d, p = run("seg_diff", e04_set["clean"], e04_set["clean"])
        assert rc == 0, d["findings"] if d else p.stderr
        assert d["extra"]["lowest_ssim_outside"] >= 0.999

    def test_change_outside_the_excluded_range_fails_with_frame_and_time(self, tmp_path):
        d0 = tmp_path / "השוואה 'x'"
        d0.mkdir()
        a, b = self._pair(d0, changed=(20, 29))
        rc, d, _ = run("seg_diff", a, b, "--exclude", "2.0:3.0")  # 20..29 is 0.667-0.967 s: NOT excluded
        assert rc == 1 and "changed_outside_range" in codes(d)
        first = next(f for f in d["findings"] if f["code"] == "changed_outside_range")
        assert first["frame"] == 20

    def test_change_inside_the_excluded_range_passes(self, tmp_path):
        d0 = tmp_path / "x"
        d0.mkdir()
        a, b = self._pair(d0, changed=(20, 29))
        rc, d, p = run("seg_diff", a, b, "--exclude", "0.6:1.0")
        assert rc == 0, d["findings"] if d else p.stderr

    def test_mismatched_inputs_and_missing_file_never_pass(self, e04_set, tmp_path):
        rc, d, _ = run("seg_diff", e04_set["clean"], e04_set["ntsc_30000_1001"])
        assert rc == 2 and d["status"] == "INSUFFICIENT_EVIDENCE"
        rc2, d2, _ = run("seg_diff", e04_set["clean"], tmp_path / "absent.mkv")
        assert rc2 != 0

    def test_excluding_everything_is_insufficient(self, e04_set):
        rc, d, _ = run("seg_diff", e04_set["clean"], e04_set["clean"], "--exclude", "0:10")
        assert rc == 2 and "nothing_compared" in codes(d)

    def test_parse_ssim_stats(self):
        import seg_diff

        text = "n:1 Y:0.99 U:0.99 V:0.99 All:0.990000 (20.0)\nn:2 Y:1 U:1 V:1 All:1.000000 (inf)\n"
        assert seg_diff.parse_ssim_stats(text) == [0.99, 1.0]


@pytest.mark.ffmpeg
class TestGradeBake:
    def _mean_luma(self, path):
        import numpy as np
        from core.media import FrameReader

        fr = next(iter(FrameReader(path, pix_fmt="gray", max_frames=1)))
        return float(np.mean(fr))

    def test_eq_bake_changes_the_picture_keeps_size_and_frames_and_writes_provenance(self, e04_set, tmp_path):
        out = tmp_path / "בייק 'x' 🎬.mp4"
        rc, d, p = run("grade_bake", e04_set["clean"], "-o", out, "--eq", "brightness=0.15:contrast=1.0", "--crf", "18", "--preset", "ultrafast")
        assert rc == 0, p.stderr
        assert d["frames"] == 60
        assert self._mean_luma(out) > self._mean_luma(e04_set["clean"]) + 10
        side = json.loads(Path(str(out) + ".grade.json").read_text(encoding="utf-8"))
        assert side["filters"].startswith("eq=") and len(side["output_sha256"]) == 64 and side["source"] == "clean.mkv"

    def test_preroll_extends_before_the_in_point(self, e04_set, tmp_path):
        out = tmp_path / "pre.mp4"
        rc, d, p = run("grade_bake", e04_set["clean"], "-o", out, "--eq", "saturation=1.2", "--ss", "1.0", "--to", "1.6", "--preroll-frames", "6", "--preset", "ultrafast", "--crf", "18")
        assert rc == 0, p.stderr
        assert d["preroll_frames"] == 6 and abs(d["frames"] - (18 + 6)) <= 1  # 0.6 s at 30 fps + 6 pre-roll frames

    def test_refusals(self, e04_set, tmp_path):
        assert run("grade_bake", e04_set["clean"], "-o", tmp_path / "a.mp4")[0] == 2  # nothing to apply
        assert run("grade_bake", e04_set["clean"], "-o", tmp_path / "a.mp4", "--lut", tmp_path / "no.cube")[0] == 2
        assert run("grade_bake", tmp_path / "absent.mkv", "-o", tmp_path / "a.mp4", "--eq", "gamma=1.1")[0] == 2
        assert not (tmp_path / "a.mp4").exists()

    def test_cube_lut_applies(self, e04_set, tmp_path):
        lut = tmp_path / "invert.cube"
        lines = ["LUT_3D_SIZE 2"]
        for b in (0, 1):
            for g in (0, 1):
                for r in (0, 1):
                    lines.append(f"{1 - r} {1 - g} {1 - b}")
        lut.write_text("\n".join(lines) + "\n", encoding="utf-8")
        out = tmp_path / "lut.mp4"
        rc, d, p = run("grade_bake", e04_set["clean"], "-o", out, "--lut", lut, "--preset", "ultrafast", "--crf", "18")
        assert rc == 0, p.stderr
        assert abs((255 - self._mean_luma(e04_set["clean"])) - self._mean_luma(out)) < 12  # inverted


@pytest.mark.ffmpeg
class TestMotionScan:
    def test_still_clip_is_flagged_static_and_moving_clip_passes(self, e04_set, tmp_path):
        still = tmp_path / "still.mkv"
        ff("-f", "lavfi", "-i", "color=c=0x336699:size=320x240:rate=30:duration=3", "-c:v", "ffv1", still)
        rc, d, p = run("motion_scan", still)
        if d is None:
            pytest.skip("ffmpeg lacks the siti filter: " + p.stderr[-120:])
        assert rc == 0 and "static" in codes(d)  # warning by default
        rc2, d2, _ = run("motion_scan", still, "--severity", "error")
        assert rc2 == 1
        rc3, d3, _ = run("motion_scan", e04_set["clean"])
        assert rc3 == 0 and "static" not in codes(d3)

    def test_missing_input_fails_closed(self, tmp_path):
        rc, d, _ = run("motion_scan", tmp_path / "absent.mkv")
        assert rc != 0 and d["status"] == "INSUFFICIENT_EVIDENCE"

    def test_pure_windows(self):
        import motion_scan

        rows = [(i / 30, 10.0, 0.1) for i in range(60)] + [(2 + i / 30, 10.0, 5.0) for i in range(60)]
        w = motion_scan.static_windows(rows, window=1.0, min_ti=1.0, fps=30)
        assert len(w) == 1 and w[0][0] == 0.0 and w[0][1] < 2.2  # a rolling window may reach up to a window-length into the motion
        assert motion_scan.parse_siti("frame:0 pts:0 pts_time:0\nlavfi.siti.si=10.5\nlavfi.siti.ti=0.25\n") == [(0.0, 10.5, 0.25)]

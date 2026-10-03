"""Regression tests for frame_qa / caption_qa / sheet using the E04 synthetic defect set (positive AND negative controls).

Covers E04-B01 (missing input must not exit 0), B02 (25 fps timestamp), B03 (appearance is reported), the caption-overlap gap
(timeline collision), and the fail-closed rule (0 decoded frames never passes). All media lives in hostile-named temp folders.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools"


def run_tool(name: str, *args: str, timeout: float = 120.0):
    p = subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / f"{name}.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    try:
        data = json.loads(p.stdout) if p.stdout.strip().startswith("{") else None
    except json.JSONDecodeError:
        data = None
    return p.returncode, data, p


def codes(data):
    return [f["code"] for f in data["findings"]]


@pytest.mark.parametrize("tool", ["frame_qa", "caption_qa", "sheet"])
def test_help_is_fast(tool):
    t = time.monotonic()
    p = subprocess.run([sys.executable, str(TOOLS / f"{tool}.py"), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0
    assert time.monotonic() - t < 1.5
    assert "Usage" in p.stdout or "usage" in p.stdout


@pytest.mark.ffmpeg
class TestFrameQa:
    def test_clean_passes_with_full_coverage(self, e04_set):
        rc, d, _ = run_tool("frame_qa", e04_set["clean"])
        assert rc == 0 and d["status"] == "PASS"
        assert d["decoded_frames"] == d["expected_frames"] == 60 and d["coverage"] == 1.0
        assert len(d["input_sha256"]) == 64

    def test_black_frame_detected_with_time(self, e04_set):
        rc, d, _ = run_tool("frame_qa", e04_set["black"])
        assert rc == 1 and d["status"] == "FAIL"
        f = next(x for x in d["findings"] if x["code"] == "black_frame")
        assert f["frame"] == 15 and f["timecode"] == "00:00:00.500"

    def test_flash_detected(self, e04_set):
        rc, d, _ = run_tool("frame_qa", e04_set["flash"])
        assert rc == 1
        assert any(x["code"] == "flash_frame" and x["frame"] == 30 for x in d["findings"])

    def test_freeze_is_a_warning_not_a_failure(self, e04_set):
        rc, d, _ = run_tool("frame_qa", e04_set["freeze"])
        assert rc == 0
        hold = next(x for x in d["findings"] if x["code"] == "hold")
        assert hold["severity"] == "warning" and hold["data"]["frames"] >= 30

    def test_missing_input_never_exits_zero_E04_B01(self, tmp_path):
        rc, d, _ = run_tool("frame_qa", tmp_path / "absent.mkv")
        assert rc != 0
        assert d is not None and d["status"] == "INSUFFICIENT_EVIDENCE" and d["decoded_frames"] in (None, 0)

    def test_garbage_file_is_insufficient_evidence(self, tmp_path):
        bad = tmp_path / "not-a-video.mp4"
        bad.write_bytes(b"this is not media" * 100)
        rc, d, _ = run_tool("frame_qa", bad)
        assert rc != 0 and d["status"] in ("INSUFFICIENT_EVIDENCE", "FAIL")

    def test_ntsc_timestamps_use_rational_fps(self, e04_set):
        rc, d, _ = run_tool("frame_qa", e04_set["ntsc_30000_1001"])
        assert rc == 0 and d["fps"] in ("30000/1001",)


@pytest.mark.ffmpeg
class TestCaptionQa:
    def test_clean_has_no_caption_pixels_so_it_cannot_pass(self, e04_set):
        rc, d, _ = run_tool("caption_qa", e04_set["clean"])
        assert rc == 2 and "no_caption_pixels_found" in codes(d)  # nothing proven about captions -> not a pass

    def test_drop_30_detected_at_frame_30(self, e04_set):
        rc, d, _ = run_tool("caption_qa", e04_set["caption_drop_30"])
        assert rc == 1
        f = next(x for x in d["findings"] if x["code"] == "caption_vanish")
        assert f["frame"] == 30 and f["timecode"] == "00:00:01.000"

    def test_drop_25_reports_real_time_E04_B02(self, e04_set):
        rc, d, _ = run_tool("caption_qa", e04_set["caption_drop_25"])
        assert rc == 1
        f = next(x for x in d["findings"] if x["code"] == "caption_vanish")
        assert f["frame"] == 25
        assert f["timecode"] == "00:00:01.000"  # 25 / 25 fps = 1.000 s (the owner's tool printed 0.83 s)

    def test_appearance_is_reported_E04_B03(self, e04_set):
        rc, d, _ = run_tool("caption_qa", e04_set["caption_appear_30"])
        assert "caption_pop_in" in codes(d) and rc == 0
        rc2, d2, _ = run_tool("caption_qa", e04_set["caption_appear_30"], "--entrance", "error")
        assert rc2 == 1

    def test_missing_input_E04_B01(self, tmp_path):
        rc, d, _ = run_tool("caption_qa", tmp_path / "absent.mkv")
        assert rc != 0 and d["status"] == "INSUFFICIENT_EVIDENCE"

    def test_collision_checker_finds_the_overlap_the_pixel_check_misses(self, tmp_path, e04_set):
        cues = [
            {"id": "A", "start": 0.5, "end": 1.5, "bbox": [60, 355, 290, 390]},
            {"id": "B", "start": 1.0, "end": 2.0, "bbox": [80, 375, 310, 410]},
        ]
        f = tmp_path / "cues.json"
        f.write_text(json.dumps(cues), encoding="utf-8")
        rc, d, _ = run_tool("caption_qa", "--cues-only", f, "--fps", "30")
        assert rc == 1 and "caption_collision" in codes(d)
        coll = next(x for x in d["findings"] if x["code"] == "caption_collision")
        assert coll["frame"] == 30  # first frame where both are visible (t = 1.0 s)
        pix = run_tool("caption_qa", e04_set["caption_overlap"])[1]
        assert "caption_collision" not in codes(pix)

    def test_below_rail_and_clean_timeline(self, tmp_path):
        ok = [{"id": "A", "start": 0, "end": 1, "bbox": [100, 1300, 900, 1400]}, {"id": "B", "start": 1, "end": 2, "bbox": [100, 1300, 900, 1400]}]
        f = tmp_path / "ok.json"
        f.write_text(json.dumps(ok), encoding="utf-8")
        rc, d, _ = run_tool("caption_qa", "--cues-only", f, "--rail-bottom", "1450")
        assert rc == 0 and d["status"] == "PASS"
        low = [{"id": "L", "start": 0, "end": 1, "bbox": [100, 1500, 900, 1600]}]
        f2 = tmp_path / "low.json"
        f2.write_text(json.dumps(low), encoding="utf-8")
        rc2, d2, _ = run_tool("caption_qa", "--cues-only", f2, "--rail-bottom", "1450")
        assert rc2 == 1 and "below_rail" in codes(d2)

    def test_malformed_cues_never_pass(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text('[{"id": "x"}]', encoding="utf-8")
        rc, d, _ = run_tool("caption_qa", "--cues-only", f)
        assert rc != 0


@pytest.mark.ffmpeg
class TestSheet:
    def test_sheet_written_with_labels(self, e04_set, tmp_path):
        out = tmp_path / "ש 'sheet' 🎬.jpg"
        p = subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / "sheet.py"), str(e04_set["clean"]), "-o", str(out), "--count", "6", "--cols", "3"], capture_output=True, text=True, encoding="utf-8")
        assert p.returncode == 0, p.stderr
        from PIL import Image

        im = Image.open(out)
        assert im.size[0] == 3 * 240 and im.size[1] >= 2 * 400

    def test_missing_video_exits_nonzero_and_writes_nothing(self, tmp_path):
        out = tmp_path / "s.jpg"
        p = subprocess.run([sys.executable, str(TOOLS / "sheet.py"), str(tmp_path / "absent.mp4"), "-o", str(out)], capture_output=True, text=True, encoding="utf-8")
        assert p.returncode != 0 and not out.exists()


def test_analyze_pure_function_unit():
    sys.path.insert(0, str(REPO / "src"))
    sys.path.insert(0, str(TOOLS))
    import frame_qa
    from core.timebase import FrameClock

    clock = FrameClock.cfr("25", 10)
    means = [100.0] * 10
    diffs = [0.0] + [3.0] * 9
    f, stats = frame_qa.analyze(means, diffs, clock=clock)
    assert f == [] and stats["frames"] == 10
    means[4] = 0.0
    f, _ = frame_qa.analyze(means, diffs, clock=clock)
    assert [x.code for x in f] == ["black_frame"] and f[0].timecode == "00:00:00.160"

"""hf_deliver: the delivery gate on the shipped file (E04 positive/negative controls) and the re-mux path (no render needed)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "hf_deliver.py"


def run(*args, timeout=300):
    p = subprocess.run([sys.executable, "-X", "utf8", str(TOOL), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    d = None
    if p.stdout.strip().startswith("{"):
        try:
            d = json.loads(p.stdout)
        except json.JSONDecodeError:
            d = None
    return p.returncode, d, p


def codes(d):
    return [f["code"] for f in d["findings"]]


def test_deliver_width_reads_the_house_1088_rule():
    sys.path.insert(0, str(TOOL.parent))
    sys.path.insert(0, str(REPO / "src"))
    import hf_deliver as d

    page = '<div id="root" data-composition-id="main" data-width="1088" data-height="1920" data-deliver-width="1080"></div>'
    assert d.deliver_width(page) == 1080
    assert d.deliver_width(page.replace(' data-deliver-width="1080"', "")) is None  # no declaration: no crop
    assert d.deliver_width(page.replace('data-width="1088"', 'data-width="1080"')) is None  # nothing to crop
    assert d.deliver_width('<div data-composition-id="x" data-deliver-width="1079"></div>') is None  # odd width: refuse


def test_help_fast():
    t = time.monotonic()
    p = subprocess.run([sys.executable, str(TOOL), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0 and time.monotonic() - t < 1.5


@pytest.mark.ffmpeg
class TestVerify:
    def test_normalised_delivery_passes(self, e04_set):
        rc, d, _ = run("verify", e04_set["delivery_ok"], "--lufs", "-13.5", "--lufs-tol", "1.5")
        assert rc == 0 and d["status"] == "PASS", d["findings"]
        assert d["extra"]["loudness"]["lufs"] is not None

    def test_clipped_audio_is_rejected(self, e04_set):
        rc, d, _ = run("verify", e04_set["delivery_clipped"])
        assert rc == 1 and {"loudness_lufs", "true_peak_dbtp"} & set(codes(d))

    def test_numeric_zero_true_peak_is_a_value_not_missing_E04_B04(self, e04_set):
        rc, d, _ = run("verify", e04_set["delivery_clipped"])
        tp = d["extra"]["loudness"]["true_peak_dbtp"]
        assert tp is not None and tp > -1.0
        assert "true_peak_dbtp" in codes(d)  # failed gate -> non-zero exit (E04-B05)

    def test_video_without_audio_fails(self, e04_set):
        rc, d, _ = run("verify", e04_set["clean"])
        assert rc == 1 and "no_audio" in codes(d)

    def test_duration_mismatch(self, e04_set):
        rc, d, _ = run("verify", e04_set["delivery_ok"], "--expected-duration", "10", "--lufs", "-13.5", "--lufs-tol", "1.5")
        assert rc == 1 and "duration_mismatch" in codes(d)

    def test_missing_file_is_insufficient_evidence(self, tmp_path):
        rc, d, _ = run("verify", tmp_path / "absent.mp4")
        assert rc != 0 and d["status"] == "INSUFFICIENT_EVIDENCE"  # never 0; 3 = tool-level error on an unreadable input


@pytest.mark.ffmpeg
class TestRenderRemux:
    def _project(self, tmp_path, e04_set):
        hf = tmp_path / "work 'x' 🎬" / "projects" / "demo" / "hf"
        hf.mkdir(parents=True)
        (hf / "index.html").write_text('<html><body><div id="a" class="clip" data-start="0" data-duration="2"></div></body></html>', encoding="utf-8")
        work = hf.parent / "_work"
        work.mkdir()
        shutil.copy(e04_set["delivery_clipped"], work / "demo_raw.mp4")
        return hf

    def test_skip_render_two_pass_loudnorm_then_verify_passes(self, tmp_path, e04_set):
        hf = self._project(tmp_path, e04_set)
        rc, d, p = run("render", hf, "--name", "demo", "--skip-render", "--platform", "ig", "--hook", "A", "--aspect", "9x16")
        assert rc == 0, p.stdout + p.stderr
        assert d["verify"] == "PASS"
        out = hf.parent / "final" / "demo_ig_A_9x16.mp4"
        assert out.is_file()
        mf = json.loads((hf.parent / "final" / "manifest.json").read_text(encoding="utf-8"))
        assert mf["files"][0]["file"] == "demo_ig_A_9x16.mp4" and len(mf["files"][0]["source_sha256"]) == 64
        rc2, d2, _ = run("verify", out)
        assert rc2 == 0 and abs(d2["extra"]["loudness"]["lufs"] - (-14.0)) <= 1.0

    def test_preflight_error_aborts_before_anything(self, tmp_path, e04_set):
        hf = self._project(tmp_path, e04_set)
        (hf / "index.html").write_text('<html><body dir="rtl"><div id="a"></div></body></html>', encoding="utf-8")
        rc, d, p = run("render", hf, "--name", "demo", "--skip-render")
        assert rc == 2 and not (hf.parent / "final" / "demo_social_main_9x16.mp4").exists()

    def test_studio_ids_are_stripped_with_backup(self, tmp_path, e04_set):
        hf = self._project(tmp_path, e04_set)
        (hf / "index.html").write_text('<html><body><div id="a" data-hf-id="z9" class="clip" data-start="0" data-duration="2"></div></body></html>', encoding="utf-8")
        rc, d, p = run("render", hf, "--name", "demo", "--skip-render")
        assert "data-hf-id" not in (hf / "index.html").read_text(encoding="utf-8")
        assert list((hf.parent / "_work" / "backup").glob("index.html.*.bak"))

    def test_missing_raw_refuses(self, tmp_path, e04_set):
        hf = self._project(tmp_path, e04_set)
        (hf.parent / "_work" / "demo_raw.mp4").unlink()
        rc, d, p = run("render", hf, "--name", "demo", "--skip-render")
        assert rc == 2

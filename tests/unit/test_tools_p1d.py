"""color_scopes: measurements from decoded pixels in the shape the colour gate reads."""

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


def run(*args, timeout=300):
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / "color_scopes.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout)


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *map(str, args)], check=True, timeout=300)


def test_help_fast():
    t = time.monotonic()
    p = subprocess.run([sys.executable, str(TOOLS / "color_scopes.py"), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0 and time.monotonic() - t < 1.5


def test_pure_math_gray_has_no_chroma_and_percent_scale():
    np = pytest.importorskip("numpy")
    import color_scopes as cs

    frame = np.full((40, 40, 3), 128, dtype=np.uint8)
    m = cs.measure_region(frame, (0, 0, 1, 1))
    assert m["Y_pct"] == pytest.approx(128 / 255 * 100, abs=0.01) and m["chroma"] < 1e-6
    red = np.zeros((10, 10, 3), dtype=np.uint8)
    red[..., 0] = 255
    m = cs.measure_region(red, (0, 0, 1, 1))
    assert 0 < m["hue_deg"] < 180 or m["cr"] > 0
    assert m["cr"] > 100 and abs(m["cb"]) < 70  # red is mostly +Cr


def test_parse_roi_rejects_nonsense():
    import color_scopes as cs

    assert cs.parse_roi("0.1,0.2,0.5,0.6") == (0.1, 0.2, 0.5, 0.6)
    for bad in ("0.5,0.2,0.1,0.6", "0,0,1", "0,0,1.2,1"):
        with pytest.raises(ValueError):
            cs.parse_roi(bad)


@pytest.mark.ffmpeg
def test_known_patches_are_measured_and_the_gate_input_shape_is_complete(tmp_path):
    d = tmp_path / "צבע 'x' 🎬"
    d.mkdir()
    v = d / "card.mkv"
    # left half mid-gray (the "skin" ROI), bottom-right near-black (black patch), top-right neutral light grey (sky patch)
    ff("-f", "lavfi", "-i", "color=c=0x808080:size=320x240:rate=10:duration=3", "-vf",
       "drawbox=x=160:y=120:w=160:h=120:color=0x050505:t=fill,drawbox=x=160:y=0:w=160:h=120:color=0xE0E0E0:t=fill", "-c:v", "ffv1", v)
    out = d / "m.json"
    p = run(v, "-o", out, "--every", "1.0", "--skin-roi", "0.1,0.3,0.4,0.7", "--black-roi", "0.6,0.6,0.9,0.9", "--sky-roi", "0.6,0.1,0.9,0.4")
    assert p.returncode == 0, p.stderr
    m = json.loads(out.read_text(encoding="utf-8"))
    assert m["expected_samples"] == 3 and len(m["frames"]) == 3 and len(m["source_sha256"]) == 64
    f = m["frames"][0]
    assert f["person"] is True and f["skin_Y"] == pytest.approx(50.2, abs=1.0) and f["skin_chroma"] < 1.0
    assert f["black_Y"] < 3.0 and abs(f["black_cb"]) < 1.0 and f["sky_chroma"] < 1.0 and f["bright_sky"] is True
    assert f["p1"] < 5 and f["p99"] > 85  # the black and light patches define the extremes
    assert [x["t"] for x in m["frames"]] == [0.0, 1.0, 2.0]


@pytest.mark.ffmpeg
def test_no_regions_means_nulls_not_invented_numbers_and_failures_are_refusals(e04_set, tmp_path):
    out = tmp_path / "m.json"
    p = run(e04_set["clean"], "-o", out, "--every", "1.0")
    assert p.returncode == 0
    f = json.loads(out.read_text(encoding="utf-8"))["frames"][0]
    assert f["person"] is False and f["skin_Y"] is None and f["black_Y"] is None and f["sky_chroma"] is None
    assert run(tmp_path / "absent.mkv", "-o", out).returncode == 2
    assert run(e04_set["clean"], "-o", out, "--skin-roi", "0.9,0.1,0.2,0.5").returncode == 2
    assert run(e04_set["clean"], "-o", tmp_path / "t.json", "--times", "99").returncode == 2  # a requested sample that does not exist

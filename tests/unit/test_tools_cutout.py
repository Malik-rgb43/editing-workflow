"""cutout: shot segments, content-hash cache, choke, alpha encode and fail-closed verification (real FFmpeg; the matting model is replaced by a callable)."""

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

from core import matte  # noqa: E402


def run(*args, timeout=300):
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / "cutout.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout)


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *map(str, args)], check=True, timeout=300)


# ------------------------------------------------------------------------------------------------ library (no ffmpeg)
def test_segments_split_only_at_inner_cuts():
    assert matte.segments(0, 300, [120, 200, 0, 300, 999]) == [(0, 120), (120, 200), (200, 300)]
    assert matte.segments(10, 10, [5]) == []
    assert matte.segments(0, 50, []) == [(0, 50)]


def test_cut_frames_from_the_three_accepted_shapes():
    assert matte.cut_frames_from({"cuts": [{"frame": 7}, {"frame": 9}]}, 30) == [7, 9]
    assert matte.cut_frames_from([1.0, 2.0], 30) == [30, 60]
    assert matte.cut_frames_from({"cuts_s": [0.5]}, 24) == [12]
    with pytest.raises(ValueError):
        matte.cut_frames_from("nope", 30)


def test_stride_always_keeps_the_last_frame_and_interpolates_linearly():
    import numpy as np

    assert matte.stride_indices(7, 2) == [0, 2, 4, 6] and matte.stride_indices(6, 2) == [0, 2, 4, 5]
    calls = []

    def infer(frame):
        calls.append(1)
        return np.full((2, 2), float(frame[0, 0, 0]) / 10.0, dtype=np.float32)

    frames = [np.full((2, 2, 3), v, dtype=np.uint8) for v in (0, 4, 8, 4, 0)]
    out = list(matte.run_with_stride(frames, 5, infer, 2))
    assert len(out) == 5 and len(calls) == 3  # frames 0, 2, 4
    assert [round(float(o[0, 0]), 3) for o in out] == [0.0, 0.4, 0.8, 0.4, 0.0]
    with pytest.raises(ValueError):
        list(matte.run_with_stride(frames, 6, infer, 1))


def test_modnet_pre_and_post_shapes():
    import numpy as np

    x, size = matte.modnet_preprocess(np.zeros((640, 360, 3), dtype=np.uint8))
    assert x.shape == (1, 3, size[0], size[1]) and size[0] % 32 == 0 and size[1] % 32 == 0 and x.min() >= -1.0 and x.max() <= 1.0
    a = matte.modnet_postprocess(np.full((1, 1, size[0], size[1]), 0.5, dtype=np.float32), (640, 360))
    assert a.shape == (640, 360) and abs(float(a.mean()) - 0.5) < 0.01


def test_judge_stats_empty_is_a_failure_and_extremes_are_warnings():
    assert matte.judge_stats([])[0] == "fail"
    assert matte.judge_stats([{"coverage": 0.0, "partial": 0.0, "max": 0}])[0] == "fail"
    assert matte.judge_stats([{"coverage": 0.01, "partial": 0.0, "max": 255}])[0] == "warn"
    assert matte.judge_stats([{"coverage": 0.995, "partial": 0.0, "max": 255}])[0] == "warn"
    assert matte.judge_stats([{"coverage": 0.3, "partial": 0.02, "max": 255}]) == ("ok", [])


def test_help_fast():
    import time

    t = time.monotonic()
    p = subprocess.run([sys.executable, str(TOOLS / "cutout.py"), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0 and time.monotonic() - t < 1.5


# ------------------------------------------------------------------------------------------------ tool (ffmpeg)
@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    d = tmp_path_factory.mktemp("חיתוך 'x' 🎬")
    src = d / "src.mp4"
    ff("-f", "lavfi", "-i", "color=c=0x305070:s=192x320:r=30:d=3", "-vf", "drawbox=x=60:y=80:w=72:h=160:color=0xd68c82:t=fill,noise=alls=6:allf=t", "-c:v", "libx264", "-pix_fmt", "yuv420p", src)  # temporal noise: no two frames (so no two segments) are identical
    alpha = d / "alpha.mp4"
    ff("-f", "lavfi", "-i", "color=c=black:s=192x320:r=30:d=3", "-vf", "drawbox=x=60:y=80:w=72:h=160:color=white:t=fill,format=gray", "-c:v", "libx264", "-pix_fmt", "gray", alpha)
    empty = d / "empty.mp4"
    ff("-f", "lavfi", "-i", "color=c=black:s=192x320:r=30:d=3", "-vf", "format=gray", "-c:v", "libx264", "-pix_fmt", "gray", empty)
    return {"dir": d, "src": src, "alpha": alpha, "empty": empty}


@pytest.mark.ffmpeg
def test_external_alpha_round_trip_with_a_cut_and_a_range(clip):
    out = clip["dir"] / "o" / "speaker.webm"
    p = run(clip["src"], "-o", out, "--route", "external", "--alpha-from", clip["alpha"], "--from", "0.5", "--to", "2.5", "--cut-at", "1.5", "--erode", "2", "--blur", "1")
    assert p.returncode == 0, p.stderr
    side = json.loads(Path(str(out) + ".cutout.json").read_text(encoding="utf-8"))
    assert side["frames"] == 60 and side["segments"] == [[15, 45], [45, 75]] and side["size"] == [192, 320] and side["route"] == "external"
    assert 0.1 < side["coverage"][2] < 0.4 and not side["warnings"]  # the white box is 72x160 of 192x320 = 18.75 %
    assert side["cache"]["hits"] == 0


@pytest.mark.ffmpeg
def test_an_empty_matte_is_refused_and_leaves_no_file(clip):
    out = clip["dir"] / "e" / "speaker.webm"
    p = run(clip["src"], "-o", out, "--route", "external", "--alpha-from", clip["empty"])
    assert p.returncode == 2 and "empty" in p.stderr and not out.exists()


@pytest.mark.ffmpeg
def test_prores_output_and_argument_refusals(clip):
    out = clip["dir"] / "m" / "speaker.mov"
    p = run(clip["src"], "-o", out, "--route", "external", "--alpha-from", clip["alpha"], "--to", "1")
    assert p.returncode == 0, p.stderr
    assert run(clip["src"], "-o", clip["dir"] / "x.gif").returncode == 2
    p = run(clip["src"], "-o", clip["dir"] / "x.webm", "--route", "onnx")
    assert p.returncode == 2 and "--model" in p.stderr


@pytest.mark.ffmpeg
def test_model_route_caches_by_decoded_content(clip, monkeypatch):
    import numpy as np

    import cutout

    def fake_infer(frame):  # the "person" is the pink box, found by colour
        a = np.zeros(frame.shape[:2], dtype=np.float32)
        a[(frame[..., 0] > 150) & (frame[..., 2] < 160)] = 1.0
        return a

    monkeypatch.setattr(cutout, "make_onnx_infer", lambda model: fake_infer)
    model = clip["dir"] / "fake.onnx"
    model.write_bytes(b"not a real model, only hashed")
    out = clip["dir"] / "c" / "speaker.webm"
    args = [clip["src"], "-o", out, "--route", "onnx", "--model", model, "--to", "1", "--cut-at", "0.5", "--stride", "2"]
    assert cutout.main(list(map(str, args))) == 0
    first = json.loads(Path(str(out) + ".cutout.json").read_text(encoding="utf-8"))
    assert first["cache"]["hits"] == 0 and first["cache"]["misses"] == 2 and first["stride"] == 2 and first["coverage"][2] > 0.1
    assert cutout.main(list(map(str, args))) == 0
    second = json.loads(Path(str(out) + ".cutout.json").read_text(encoding="utf-8"))
    assert second["cache"]["hits"] == 2 and second["cache"]["misses"] == 0
    args[args.index("--stride") + 1] = "1"  # a parameter change misses, as designed
    assert cutout.main(list(map(str, args))) == 0
    third = json.loads(Path(str(out) + ".cutout.json").read_text(encoding="utf-8"))
    assert third["cache"]["hits"] == 0 and third["cache"]["misses"] == 2


@pytest.mark.ffmpeg
def test_a_vp9_alpha_webm_is_read_through_its_alpha_not_its_picture(clip):
    """Regression: VP9 keeps alpha in a side channel (pix_fmt says yuv420p). Read as luma, a bright speaker on a dark plate would look 'right' by accident,
    so the picture here is uniformly BRIGHT and only the alpha holds the shape."""
    d = clip["dir"]
    webm = d / "alpha_side.webm"
    ff("-f", "lavfi", "-i", "color=c=white:s=192x320:r=30:d=2", "-vf",
       "format=yuva420p,geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='if(between(X,60,131)*between(Y,80,239),255,0)'",
       "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "20", webm)
    reader = matte.alpha_reader(webm)
    assert reader[0] == ["-c:v", "libvpx-vp9"] and reader[1] == "alphaextract" and reader[2] is True
    out = d / "vp9" / "speaker.webm"
    p = run(clip["src"], "-o", out, "--route", "external", "--alpha-from", webm, "--to", "1", "--erode", "0", "--blur", "0")
    assert p.returncode == 0, p.stderr
    cov = json.loads(Path(str(out) + ".cutout.json").read_text(encoding="utf-8"))["coverage"]
    assert all(0.1 < c < 0.3 for c in cov), cov  # the 72x160 box (18.75 %), not the all-white picture (100 %)


def test_plain_grey_matte_is_read_as_luma(clip):
    assert matte.alpha_reader(clip["alpha"]) == ([], "format=gray", False)

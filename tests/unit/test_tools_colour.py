"""colour engine + color_fit / color_render / color_check on a synthetic clip (real FFmpeg, hostile-named folder)."""

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

from core import colour  # noqa: E402

GATE = REPO / "agent-content" / "skills" / "speaker-color-correction" / "scripts" / "grade_gate.py"


def run(tool, *args, timeout=300):
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / f"{tool}.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout)


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *map(str, args)], check=True, timeout=300)


# ------------------------------------------------------------------------------------------------ engine (no ffmpeg)
def test_identity_grade_changes_nothing():
    import numpy as np

    rgb = np.array([[[200, 150, 120], [10, 10, 10], [255, 255, 255], [0, 0, 0]]], dtype=np.uint8)
    assert (colour.grade_u8(rgb, {}) == rgb).all()
    lut = colour.make_lut({})
    assert lut.shape == (65 ** 3, 3)
    assert abs(lut[0]).max() < 1e-9 and abs(lut[-1] - 1).max() < 1e-9  # black stays black, white stays white


def test_unknown_parameter_is_an_error_not_a_silent_noop():
    with pytest.raises(ValueError):
        colour.full_params({"exposure": 1})


def test_wb_gains_preserve_luminance():
    g = colour.wb_gains(1.2, 0.8)
    assert abs((g * colour.LUMA).sum() - 1.0) < 1e-12


def test_ev_brightens_and_subject_lift_has_a_highlight_guard():
    import numpy as np

    dark, bright = np.array([[60, 50, 40]], dtype=np.uint8), np.array([[250, 240, 230]], dtype=np.uint8)
    assert colour.grade_u8(dark, {"ev": 0.5}).mean() > dark.mean()
    lift = {"lift_ev": 1.0}
    d_gain = colour.grade_u8(dark, lift, subject=True).astype(float).mean() - dark.mean()
    b_gain = colour.grade_u8(bright, lift, subject=True).astype(float).mean() - bright.mean()
    assert d_gain > b_gain >= 0  # highlights receive less lift: no hot halos
    assert (colour.grade_u8(dark, lift, subject=False) == dark).all()  # the subject node is inert on the global path


def test_cube_file_is_well_formed(tmp_path):
    p = tmp_path / "תיקייה" / "g.cube"
    p.parent.mkdir()
    colour.write_cube(p, colour.make_lut({"ev": 0.2}, size=5), "t")
    lines = p.read_text(encoding="utf-8").splitlines()
    assert lines[1] == "LUT_3D_SIZE 5" and len(lines) == 4 + 125 and b"\r\n" not in p.read_bytes()


def test_metrics_agree_with_color_scopes():
    import numpy as np

    import color_scopes

    px = np.array([[214, 140, 130], [200, 130, 120]], dtype=np.uint8)
    a = colour.region_metrics(px)
    b = color_scopes.measure_region(px.reshape(1, 2, 3), (0.0, 0.0, 1.0, 1.0))
    assert abs(a["Y_pct"] - b["Y_pct"]) < 1e-9 and abs(a["hue_deg"] - b["hue_deg"]) < 1e-9


def test_hue_error_wraps():
    assert colour.hue_error(359, 1) == -2 and colour.hue_error(1, 359) == 2


def test_minimize_reports_bound_and_local_convergence():
    r = colour.minimize(lambda x: (x["a"] - 5.0) ** 2, {"a": 0.0}, {"a": (0.0, 1.0)})
    assert r["x"]["a"] == 1.0 and r["active_bounds"] == ["a"]  # the optimum is outside the bound: reported as degenerate
    r = colour.minimize(lambda x: (x["a"] - 0.3) ** 2, {"a": 0.9}, {"a": (0.0, 1.0)})
    assert abs(r["x"]["a"] - 0.3) < 0.01 and r["converged"] and not r["active_bounds"]


@pytest.mark.parametrize("tool", ["color_fit", "color_render", "color_check"])
def test_help_fast(tool):
    t = time.monotonic()
    p = subprocess.run([sys.executable, str(TOOLS / f"{tool}.py"), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0 and time.monotonic() - t < 1.5


# ------------------------------------------------------------------------------------------------ tools (ffmpeg)
@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    d = tmp_path_factory.mktemp("צבע 'x' 🎬")
    src = d / "src.mp4"
    ff("-f", "lavfi", "-i", "color=c=0x6f7f8f:s=360x640:r=30:d=4", "-vf",
       "drawbox=x=0:y=0:w=360:h=64:color=0xd8d8d8:t=fill,drawbox=x=110:y=170:w=140:h=100:color=0xd68c82:t=fill,drawbox=x=80:y=350:w=200:h=170:color=0x1c1a1e:t=fill",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", src)
    matte = d / "matte.mp4"
    ff("-f", "lavfi", "-i", "color=c=black:s=360x640:r=30:d=4", "-vf", "drawbox=x=110:y=170:w=140:h=100:color=white:t=fill,format=gray", "-c:v", "libx264", "-pix_fmt", "gray", matte)
    faces = d / "faces.json"
    faces.write_text(json.dumps({"samples": [{"time_s": float(t), "cx": 0.5, "cy": 0.34, "h_norm": 0.3} for t in range(5)]}), encoding="utf-8")
    return {"dir": d, "src": src, "matte": matte, "faces": faces}


COMMON = ["--black-roi", "0.3,0.6,0.7,0.78", "--sky-roi", "0.02,0.01,0.98,0.09"]


@pytest.mark.ffmpeg
def test_fit_moves_a_pink_dark_plate_into_the_preset_band(clip):
    out = clip["dir"] / "g.json"
    p = run("color_fit", clip["src"], "--at", "0.5,1.5,2.5", "-o", out, "--faces", clip["faces"], *COMMON, "--sheet", clip["dir"] / "sheet.jpg")
    assert p.returncode == 0, p.stderr
    g = json.loads(out.read_text(encoding="utf-8"))
    fit = g["fit"]
    assert fit["cost_after"] < fit["cost_before"] / 4 and fit["converged"]
    # this plate is extreme (skin chroma 39 vs target 24): the fit may want less saturation than the 0.9 floor allows. A parameter on a bound is
    # REPORTED (degenerate: constrain it or widen the bound knowingly) - it must really sit on that bound, and not merely at its identity value
    for k in fit["active_bounds"]:
        v = g["params"].get(k, colour.IDENTITY[k])
        assert v in colour.BOUNDS[k] and v != colour.IDENTITY[k], (k, v)
    assert all(v is True for v in fit["gate_bands_met_after"].values()), fit["gate_bands_met_after"]
    assert (clip["dir"] / "sheet.jpg").stat().st_size > 1000
    assert set(g["params"]) <= set(colour.GLOBAL_KEYS)


@pytest.mark.ffmpeg
def test_fit_refuses_without_a_skin_region_and_for_a_process_only_preset(clip):
    p = run("color_fit", clip["src"], "--at", "1", "-o", clip["dir"] / "x.json")
    assert p.returncode == 2 and "no sample has a skin region" in p.stderr
    p = run("color_fit", clip["src"], "--at", "1", "-o", clip["dir"] / "x.json", "--faces", clip["faces"], "--preset", "ai-generated-natural-v1")
    assert p.returncode == 2 and "process-only" in p.stderr
    p = run("color_fit", clip["src"], "--at", "1", "-o", clip["dir"] / "x.json", "--faces", clip["faces"], "--stage", "subject")
    assert p.returncode == 2 and "--fixed" in p.stderr


@pytest.mark.ffmpeg
def test_two_stage_render_check_gate_round_trip(clip):
    d = clip["dir"]
    g1, g2 = d / "g1.json", d / "g2.json"
    assert run("color_fit", clip["src"], "--at", "0.5,1.5,2.5", "-o", g1, "--faces", clip["faces"], *COMMON).returncode == 0
    p = run("color_fit", clip["src"], "--at", "0.5,1.5,2.5", "-o", g2, "--stage", "subject", "--fixed", g1, "--faces", clip["faces"], *COMMON)
    assert p.returncode == 0, p.stderr
    params = json.loads(g2.read_text(encoding="utf-8"))["params"]
    assert set(colour.GLOBAL_KEYS) & set(params) == set(json.loads(g1.read_text(encoding="utf-8"))["params"])  # the global stage stayed fixed
    out = d / "out" / "final.mp4"
    p = run("color_render", clip["src"], "--params", g2, "-o", out, "--matte", clip["matte"], "--size", "360x640", "--fps", "30", "--from", "0.5", "--to", "3.0")
    assert p.returncode == 0, p.stderr
    side = json.loads(Path(str(out) + ".grade.json").read_text(encoding="utf-8"))
    assert side["matte_used"] is True and side["preroll_frames"] == 6 and side["frames"] in (80, 81, 82) and len(side["luts"]) == 2
    from core.media import read_frame_at

    frame = read_frame_at(str(out), 1.0)  # regression: the default gbrp->yuv420p conversion blacked out the right-most columns at width 360
    assert frame[:, -1].mean() > 20 and frame[:, 0].mean() > 20
    meas = d / "meas.json"
    p = run("color_check", out, "-o", meas, "--faces", clip["faces"], *COMMON, "--step", "0.5", "--ignore", "1.0-1.2")
    assert p.returncode == 0, p.stderr
    m = json.loads(meas.read_text(encoding="utf-8"))
    assert m["ignore"] == [[1.0, 1.2]] and m["frames_with_person"] == len(m["frames"])
    v = subprocess.run([sys.executable, "-X", "utf8", str(GATE), "gate", str(meas), "--preset", "speaker-plate-v1", "--na", "p99=no_bright_sky"], capture_output=True, text=True, encoding="utf-8")
    verdict = json.loads(v.stdout)
    bad = [(c["id"], c["state"], c["reason"]) for c in verdict["checks"] if c["state"] not in ("pass", "n/a")]
    assert v.returncode == 0 and verdict["status"] == "PASS" and not bad, bad


@pytest.mark.ffmpeg
def test_render_without_a_matte_says_it_left_the_subject_node_out(clip):
    d = clip["dir"]
    g = d / "gs.json"
    g.write_text(json.dumps({"params": {"ev": 0.1, "lift_ev": 0.3}}), encoding="utf-8")
    out = d / "nomatte.mp4"
    p = run("color_render", clip["src"], "--params", g, "-o", out, "--size", "360x640", "--fps", "30")
    assert p.returncode == 0, p.stderr
    side = json.loads(Path(str(out) + ".grade.json").read_text(encoding="utf-8"))
    assert side["matte_used"] is False and any("no --matte" in n for n in side["notes"])


@pytest.mark.ffmpeg
def test_render_refuses_a_missing_matte_and_an_unknown_parameter(clip):
    d = clip["dir"]
    g = d / "bad.json"
    g.write_text(json.dumps({"params": {"exposure": 1}}), encoding="utf-8")
    p = run("color_render", clip["src"], "--params", g, "-o", d / "b.mp4")
    assert p.returncode == 2 and "unknown grade parameter" in p.stderr and not (d / "b.mp4").exists()
    g.write_text(json.dumps({"params": {"ev": 0.1}}), encoding="utf-8")
    p = run("color_render", clip["src"], "--params", g, "-o", d / "b.mp4", "--matte", d / "nope.mp4")
    assert p.returncode == 2 and "matte not found" in p.stderr


@pytest.mark.ffmpeg
def test_check_refuses_without_a_person_region(clip):
    p = run("color_check", clip["src"], "-o", clip["dir"] / "m.json")
    assert p.returncode == 2 and "no person region" in p.stderr
    bad = run("color_check", clip["src"], "-o", clip["dir"] / "m.json", "--skin-roi", "0.4,0.2,0.6,0.4", "--ignore", "5-2")
    assert bad.returncode == 2 and "bad --ignore" in bad.stderr


@pytest.mark.ffmpeg
def test_a_cutout_webm_works_as_the_colour_matte_with_an_offset(clip):
    """The colour matte may be a cutout (alpha in a VP9 WebM) made for a later range: it is read through its alpha and aligned with --matte-offset."""
    d = clip["dir"]
    webm = d / "cut_matte.webm"
    ff("-ss", "1", "-i", clip["matte"], "-t", "2.5", "-vf", "format=gray", "-f", "nut", "-c:v", "ffv1", d / "m.nut")
    ff("-ss", "1", "-i", clip["src"], "-i", d / "m.nut", "-t", "2.5", "-filter_complex", "[0:v]format=yuv420p[c];[1:v]format=gray[a];[c][a]alphamerge,format=yuva420p[v]",
       "-map", "[v]", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "20", webm)
    g = d / "lift.json"
    g.write_text(json.dumps({"params": {"lift_ev": 0.8}}), encoding="utf-8")
    out = d / "webm_matte.mp4"
    p = run("color_render", clip["src"], "--params", g, "-o", out, "--matte", webm, "--matte-offset", "1", "--from", "1.5", "--to", "3.0", "--preroll-frames", "0",
            "--size", "360x640", "--fps", "30", "--matte-erode", "0", "--matte-blur", "0")
    assert p.returncode == 0, p.stderr
    side = json.loads(Path(str(out) + ".grade.json").read_text(encoding="utf-8"))
    assert side["matte_read_as"] == "alphaextract" and side["matte_offset_s"] == 1.0
    from core.media import read_frame_at

    src = read_frame_at(str(clip["src"]), 2.0).astype(float)
    got = read_frame_at(str(out), 0.5).astype(float)
    face, bg = (slice(190, 250), slice(130, 230)), (slice(100, 150), slice(10, 60))
    assert got[face].mean() > src[face].mean() + 15  # the face (inside the matte) was lifted
    assert abs(got[bg].mean() - src[bg].mean()) < 4  # the background (outside) was not
    p = run("color_render", clip["src"], "--params", g, "-o", d / "bad.mp4", "--matte", webm, "--matte-offset", "1", "--from", "0.5", "--size", "360x640")
    assert p.returncode == 2 and "pre-roll" in p.stderr

"""timebase.py: rational fps/PTS, frame<->time, drift guard (E04-B02, F05)."""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from core import timebase as tb
from core.errors import TimebaseError


def test_e04_b02_frame_25_at_25fps_is_one_second_not_0_83():
    fps = tb.parse_rate("25")
    d = tb.describe_frame(25, fps)
    assert d["time_s"] == "1" and d["time_s_float"] == 1.0 and d["timecode"] == "00:00:01.000"
    wrong = tb.describe_frame(25, tb.parse_rate("30"))  # what the 30-fps-hardcoded tool printed
    assert wrong["time_s_float"] == pytest.approx(0.833333)
    assert wrong["time_s"] != d["time_s"]


def test_describe_frame_reports_frame_and_exact_time_json_safe():
    d = tb.describe_frame(30, Fraction(30000, 1001))
    assert d["frame"] == 30 and d["time_s"] == "1001/1000"  # exact, not 1.001001...
    json.dumps(d)
    assert d["timecode"] == "00:00:01.001"


def test_drift_guard_ntsc_108000_frames():
    ntsc, thirty = Fraction(30000, 1001), Fraction(30)
    d = tb.drift_seconds(108_000, ntsc, thirty)
    assert float(d) == pytest.approx(-3.6, abs=1e-9)  # 3,600 s at 30 fps vs 3,603.6 s at 30000/1001 (F05)
    assert Fraction(108_000) / ntsc == Fraction(3_603_600, 1000)
    with pytest.raises(TimebaseError) as e:
        tb.assert_no_drift(108_000, ntsc, thirty)
    assert "r_frame_rate" in str(e.value)
    # short clips stay inside the tolerance, long ones do not
    tb.assert_no_drift(300, ntsc, thirty)
    assert tb.assert_no_drift(108_000, ntsc, ntsc) == 0


def test_parse_rate_accepts_ffprobe_strings_and_rejects_floats():
    assert tb.parse_rate("30000/1001") == Fraction(30000, 1001)
    assert tb.parse_rate(" 25 ") == 25 and tb.parse_rate(24) == 24 and tb.parse_rate((24000, 1001)) == Fraction(24000, 1001)
    for bad in (29.97, True, "0/0", "abc", "-5", "30/0", None, "30.5"):
        with pytest.raises(TimebaseError):
            tb.parse_rate(bad)  # type: ignore[arg-type]


def test_snap_rate_maps_typed_floats_to_exact_broadcast_rates():
    assert tb.snap_rate(29.97) == Fraction(30000, 1001)
    assert tb.snap_rate(23.976) == Fraction(24000, 1001)
    assert tb.snap_rate(59.94) == Fraction(60000, 1001)
    assert tb.snap_rate(25.0) == 25
    with pytest.raises(TimebaseError):
        tb.snap_rate(27.3)
    assert tb.is_ntsc(Fraction(30000, 1001)) and not tb.is_ntsc(Fraction(30))


def test_frame_time_roundtrip_and_rounding_modes():
    fps = Fraction(30000, 1001)
    for n in (0, 1, 29, 30, 1799, 107999):
        assert tb.time_to_frame(tb.frame_to_time(n, fps), fps) == n  # exact rationals, no float drift
    t = Fraction(1, 2)  # 0.5 s at 25 fps = frame 12.5
    assert tb.time_to_frame(t, Fraction(25), rounding="floor") == 12
    assert tb.time_to_frame(t, Fraction(25), rounding="ceil") == 13
    assert tb.time_to_frame(t, Fraction(25), rounding="nearest") == 13
    with pytest.raises(TimebaseError):
        tb.time_to_frame(0.5, Fraction(25))  # type: ignore[arg-type]
    with pytest.raises(TimebaseError):
        tb.frame_to_time(True, Fraction(25))  # type: ignore[arg-type]


def test_format_timestamp():
    assert tb.format_timestamp(Fraction(3661, 1) + Fraction(1, 2)) == "01:01:01.500"
    assert tb.format_timestamp(Fraction(0)) == "00:00:00.000"
    assert tb.format_timestamp(Fraction(-1, 4)) == "-00:00:00.250"


def test_pts_to_time():
    assert tb.pts_to_time(1001, Fraction(1, 30000)) == Fraction(1001, 30000)
    with pytest.raises(TimebaseError):
        tb.pts_to_time(1.5, Fraction(1, 30000))  # type: ignore[arg-type]


def test_frame_clock_cfr_and_vfr():
    c = tb.FrameClock.cfr("25", 50)
    assert c.time_of(25) == 1 and c.frame_at(Fraction(1)) == 25 and c.duration() == 2
    assert c.describe(25)["time_s"] == "1"
    v = tb.FrameClock.from_pts([0, 1000, 3000, 4000], Fraction(1, 1000))
    assert v.time_of(2) == Fraction(3) and v.frame_at(Fraction(2)) == 1 and v.frame_at(Fraction(3)) == 2 and v.count == 4
    assert v.describe(2)["time_s"] == "3"
    with pytest.raises(TimebaseError):
        tb.FrameClock.from_pts([0, 5, 5], Fraction(1, 1000))
    with pytest.raises(TimebaseError):
        tb.FrameClock.from_pts([], Fraction(1, 1000))


@pytest.mark.ffmpeg
def test_matches_real_probe_of_fixtures(e04_set):
    from core.ffprobe import packet_pts, probe

    p25 = probe(e04_set["caption_drop_25"])
    assert p25.first_video.fps == Fraction(25)
    assert tb.describe_frame(25, p25.first_video.fps)["time_s"] == "1"
    pn = probe(e04_set["ntsc_30000_1001"])
    assert pn.first_video.fps == Fraction(30000, 1001)
    pts, base = packet_pts(e04_set["ntsc_30000_1001"])
    clock = tb.FrameClock.from_pts(pts, base)
    assert clock.count == 90
    assert clock.time_of(30) == Fraction(1001, 1000) == tb.frame_to_time(30, pn.first_video.fps)

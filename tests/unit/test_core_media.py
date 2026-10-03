"""ffprobe.py / media.py against the generated E04 set (all inside a Hebrew + space + apostrophe + emoji folder)."""

from __future__ import annotations

import os
from fractions import Fraction
from pathlib import Path

import pytest

from core import ffprobe
from core.errors import DecodeError, MediaToolMissing, ProbeError
from core.media import FrameReader, read_audio_samples


def test_fixtures_really_live_in_a_hostile_path(e04_set):
    s = str(e04_set["clean"])
    assert "🎬" in s and "'" in s and " " in s and any("א" <= c <= "ת" for c in s)


@pytest.mark.ffmpeg
def test_probe_gives_rational_rates_and_expected_frames(e04_set):
    info = ffprobe.probe(e04_set["clean"])
    v = info.first_video
    assert (v.width, v.height, v.codec) == (360, 640, "ffv1")
    assert v.fps == Fraction(30) and isinstance(v.fps, Fraction) and not v.is_vfr and v.rotation == 0
    assert ffprobe.expected_frames(e04_set["clean"], info) == (60, "packet_count")
    assert ffprobe.probe(e04_set["caption_drop_25"]).first_video.fps == 25
    ntsc = ffprobe.probe(e04_set["ntsc_30000_1001"]).first_video
    assert ntsc.fps == Fraction(30000, 1001) and ntsc.time_base == Fraction(1, 1000)  # mkv time base
    assert ffprobe.count_decoded_frames(e04_set["ntsc_30000_1001"]) == 90


@pytest.mark.ffmpeg
def test_probe_audio_and_av(e04_set):
    a = ffprobe.probe(e04_set["clipped_audio"])
    assert not a.video and a.audio[0].sample_rate == 48000 and a.audio[0].channels == 1
    with pytest.raises(ProbeError):
        _ = a.first_video
    av = ffprobe.probe(e04_set["delivery_ok"])
    assert av.first_video.codec == "h264" and av.audio[0].codec == "aac"
    assert ffprobe.expected_frames(e04_set["delivery_ok"], av) == (60, "nb_frames")


@pytest.mark.ffmpeg
def test_probe_errors_never_return_an_empty_success(tmp_path, tricky_dir):
    with pytest.raises(ProbeError) as e:
        ffprobe.probe(tricky_dir / "absent.mkv")  # E04-B01 class: missing input
    assert "not found" in str(e.value)
    junk = tricky_dir / "junk 'ש'.mp4"
    junk.write_bytes(b"this is not media at all" * 10)
    with pytest.raises(ProbeError):
        ffprobe.probe(junk)
    with pytest.raises(ProbeError):
        FrameReader(junk)
    d = tmp_path / "adir"
    d.mkdir()
    with pytest.raises(ProbeError):
        ffprobe.probe(d)


@pytest.mark.ffmpeg
def test_frame_reader_decodes_every_frame_and_reports_clean_finish(e04_set):
    r = FrameReader(e04_set["black"], pix_fmt="gray")
    assert not r.ok  # not finished yet: ok must be earned
    frames = [f.copy() for f in r]
    assert len(frames) == r.decoded == 60 and r.ok and r.returncode == 0 and r.partial_tail_bytes == 0
    assert frames[0].shape == (640, 360) and frames[0].dtype.name == "uint8"
    assert [i for i, f in enumerate(frames) if int(f.max()) == 0] == [15]  # the injected black frame, nothing else
    r.require_ok()


@pytest.mark.ffmpeg
def test_frame_reader_rgb_scale_and_limit(e04_set):
    r = FrameReader(e04_set["flash"], pix_fmt="rgb24", scale=(90, 160))
    first = next(iter(r))
    assert first.shape == (160, 90, 3)
    r2 = FrameReader(e04_set["flash"], pix_fmt="gray", max_frames=10)
    assert sum(1 for _ in r2) == 10 and r2.ok  # an intentional limit is not a failure
    r3 = FrameReader(e04_set["flash"], pix_fmt="gray")
    flashes = [i for i, f in enumerate(r3) if int(f.min()) == 255]
    assert flashes == [30]


@pytest.mark.ffmpeg
def test_frame_reader_keeps_exact_frame_count_on_ntsc_and_25fps(e04_set):
    assert sum(1 for _ in FrameReader(e04_set["ntsc_30000_1001"])) == 90  # passthrough: no dup/drop
    assert sum(1 for _ in FrameReader(e04_set["caption_drop_25"])) == 50


@pytest.mark.ffmpeg
def test_frame_reader_truncated_file_is_not_ok_or_has_fewer_frames(e04_set, tricky_dir):
    data = e04_set["delivery_ok"].read_bytes()
    cut = tricky_dir / "cut.mp4"
    cut.write_bytes(data[: len(data) // 3])
    info = ffprobe.probe(cut)
    r = FrameReader(cut, info=info)
    n = sum(1 for _ in r)
    expected, _ = ffprobe.expected_frames(cut, info)
    assert expected == 60 and n < expected  # the header promises 60, the bytes deliver fewer


@pytest.mark.ffmpeg
def test_frame_reader_timeout_kills_decoder_and_is_not_ok(e04_set):
    r = FrameReader(e04_set["clean"], timeout_s=0.001)
    list(r)
    # the decode may or may not have beaten a 1 ms timer on a tiny clip; what must hold: never "ok" with a timeout recorded
    assert not (r.timed_out and r.ok)


@pytest.mark.ffmpeg
def test_frame_reader_bad_pixfmt(e04_set):
    with pytest.raises(DecodeError):
        FrameReader(e04_set["clean"], pix_fmt="yuv444p")


@pytest.mark.ffmpeg
def test_audio_samples_clipped_vs_ok(e04_set):
    import numpy as np

    clipped = read_audio_samples(e04_set["clipped_audio"])
    assert clipped.shape[1] == 1 and int(clipped.max()) == 32767 and int((clipped == 32767).sum()) > 1000  # real clipping
    ok = read_audio_samples(e04_set["tone_ok_audio"])
    peak_db = 20 * np.log10(int(np.abs(ok).max()) / 32768)
    assert -10.5 < peak_db < -9.5  # about -10 dBFS
    assert read_audio_samples(e04_set["delivery_ok"]).shape[0] > 40000
    with pytest.raises(DecodeError):
        read_audio_samples(e04_set["clean"])  # a video without audio: error, never an empty array


def test_missing_ffmpeg_gives_clear_remediation(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(MediaToolMissing) as e:
        ffprobe.find_ffmpeg()
    text = str(e.value)
    assert "ffmpeg" in text and "-version" in text and ("winget" in text or "brew" in text or "apt" in text)
    with pytest.raises(MediaToolMissing):
        ffprobe.find_ffprobe(configured=str(tmp_path / "nope" / "ffprobe"))
    assert "configured as" in str(pytest.raises(MediaToolMissing, ffprobe.find_ffprobe, str(tmp_path / "nope")).value)


@pytest.mark.ffmpeg
def test_configured_binary_path_is_honoured():
    real = ffprobe.find_ffmpeg()
    assert ffprobe.find_ffmpeg(configured=real) == real
    assert os.path.isfile(ffprobe.find_ffprobe())
    assert "ffmpeg version" in ffprobe.ffmpeg_version()


def test_module_import_is_lazy_about_numpy():
    import subprocess
    import sys

    code = "import sys; import core.media, core.ffprobe, core.envelope, core.ledger, core.lock, core.paths, core.config, core.timebase, core.procs; print('numpy' in sys.modules, 'PIL' in sys.modules)"
    src = Path(__file__).resolve().parents[2] / "src"
    r = subprocess.run([sys.executable, "-c", code], env={**os.environ, "PYTHONPATH": str(src)}, capture_output=True, text=True, timeout=60)
    assert r.stdout.strip() == "False False", r.stderr

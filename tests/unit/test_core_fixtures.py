"""fixtures/: the E04 synthetic defect set and the bilingual sample project are generated with FFmpeg only, match their
ground truth pixel-for-pixel, and never put media into the repository tree."""

from __future__ import annotations

import json
import re
import warnings
from fractions import Fraction
from pathlib import Path

import pytest

from core import ffprobe
from core.media import FrameReader, read_audio_samples

REPO = Path(__file__).resolve().parents[2]
MEDIA_EXT = {".mkv", ".mp4", ".mov", ".webm", ".avi", ".wav", ".mp3", ".flac", ".aac", ".m4a", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ttf", ".otf", ".woff", ".woff2"}


def gray(path):
    r = FrameReader(path, pix_fmt="gray")
    import numpy as np

    arr = np.stack([f.copy() for f in r])
    assert r.ok
    return arr


def box_visible(frames, box=(80, 360, 200, 50)):
    x, y, w, h = box
    return [bool((f[y : y + h, x : x + w] == 255).all()) for f in frames]


@pytest.mark.ffmpeg
def test_all_fourteen_items_exist_with_expected_probe_facts(e04_set):
    ids = {r["id"] for r in e04_set.records}
    assert ids == {"clean", "black", "flash", "freeze", "caption_drop_30", "caption_drop_25", "caption_appear_30", "caption_overlap", "low_feature", "ntsc_30000_1001",
                   "clipped_audio", "tone_ok_audio", "delivery_clipped", "delivery_ok"}
    for r in e04_set.records:
        p = e04_set[r["id"]]
        assert p.is_file() and p.stat().st_size > 0
        par = r["params"]
        if r["kind"] in ("video", "av"):
            v = ffprobe.probe(p).first_video
            assert (v.width, v.height) == (par["width"], par["height"]) and v.fps == Fraction(par["fps"])
            assert ffprobe.expected_frames(p)[0] == par["frames"], r["id"]
        else:
            a = ffprobe.probe(p).audio[0]
            assert a.sample_rate == par["sample_rate"]


@pytest.mark.ffmpeg
def test_black_flash_and_clean_ground_truth(e04_set):
    black, flash, clean = gray(e04_set["black"]), gray(e04_set["flash"]), gray(e04_set["clean"])
    assert [i for i, f in enumerate(black) if f.max() == 0] == [15]
    assert [i for i, f in enumerate(flash) if f.min() == 255] == [30]
    assert not any(f.max() == 0 or f.min() == 255 for f in clean)
    import numpy as np

    d = np.abs(np.diff(clean.astype(int), axis=0)).sum(axis=(1, 2))
    assert (d > 0).all()  # every clean frame differs from the previous one (a real "no hold" control)


@pytest.mark.ffmpeg
def test_freeze_is_a_32_frame_hold_of_frame_19(e04_set):
    import numpy as np

    f = gray(e04_set["freeze"])
    same = [i for i in range(len(f)) if np.array_equal(f[i], f[19])]
    assert same == list(range(19, 51))
    assert not np.array_equal(f[18], f[19]) and not np.array_equal(f[50], f[51])


@pytest.mark.ffmpeg
def test_caption_drops_at_25_and_30_fps_and_appearance(e04_set):
    d30 = box_visible(gray(e04_set["caption_drop_30"]))
    assert d30[:30] == [True] * 30 and d30[30:] == [False] * 30
    d25 = box_visible(gray(e04_set["caption_drop_25"]))
    assert len(d25) == 50 and d25[:25] == [True] * 25 and d25[25:] == [False] * 25
    assert ffprobe.probe(e04_set["caption_drop_25"]).first_video.fps == 25  # frame 25 = 1.00 s, not 0.83 s (E04-B02)
    ap = box_visible(gray(e04_set["caption_appear_30"]))
    assert ap[:30] == [False] * 30 and ap[30:] == [True] * 30


@pytest.mark.ffmpeg
def test_caption_overlap_geometry_matches_ground_truth(e04_set):
    import numpy as np

    f = gray(e04_set["caption_overlap"])
    assert f.shape[0] == 60
    truth = next(r for r in e04_set.records if r["id"] == "caption_overlap")["labels"]["ground_truth"]
    # pixels that belong ONLY to one caption (outside the other one)
    only_a = (slice(355, 375), slice(62, 78))  # inside A, outside B
    only_b = (slice(391, 408), slice(292, 308))  # inside B, outside A
    a_on = [bool((fr[only_a] == 255).all()) for fr in f]
    b_on = [bool((fr[only_b] == 255).all()) for fr in f]
    assert [i for i, v in enumerate(a_on) if v] == list(range(15, 45))
    assert [i for i, v in enumerate(b_on) if v] == list(range(30, 60))
    both = [i for i in range(60) if a_on[i] and b_on[i]]
    assert (both[0], both[-1] + 1) == tuple(truth["temporal_overlap_frames"]) == (30, 45)
    x0, y0, x1, y1 = truth["spatial_overlap_bbox"]
    assert (x1 - x0, y1 - y0) == (210, 15)
    assert np.all(f[40][y0:y1, x0:x1] == 255)  # the shared region is lit while both captions are on


@pytest.mark.ffmpeg
def test_low_feature_clip_is_smooth_and_has_no_corners(e04_set):
    import numpy as np

    f = gray(e04_set["low_feature"]).astype(int)
    assert np.abs(np.diff(f, axis=2)).max() <= 4  # no hard horizontal edge anywhere: nothing for a corner tracker to hold
    assert np.abs(np.diff(f, axis=1)).max() == 0  # constant down each column
    assert (np.abs(np.diff(f, axis=0)).sum(axis=(1, 2)) > 0).all()  # still moving


@pytest.mark.ffmpeg
def test_ntsc_clip_time_of_frame_30_is_1001_over_1000(e04_set):
    from core.ffprobe import packet_pts
    from core.timebase import FrameClock

    pts, tb = packet_pts(e04_set["ntsc_30000_1001"])
    assert FrameClock.from_pts(pts, tb).time_of(30) == Fraction(1001, 1000)


@pytest.mark.ffmpeg
def test_audio_fixtures_clipped_and_ok(e04_set):
    import numpy as np

    c = read_audio_samples(e04_set["clipped_audio"])
    assert int(c.max()) == 32767 and int(c.min()) <= -32767
    ok = read_audio_samples(e04_set["tone_ok_audio"])
    assert 20 * np.log10(int(np.abs(ok).max()) / 32768) == pytest.approx(-10.1, abs=0.3)


@pytest.mark.ffmpeg
def test_delivery_pair_differs_only_in_audio(e04_set):
    import numpy as np

    a, b = read_audio_samples(e04_set["delivery_clipped"]), read_audio_samples(e04_set["delivery_ok"])
    assert np.abs(a).max() > np.abs(b).max() + 4000  # the clipped mux is far hotter (AAC may overshoot or soften the clip)
    va, vb = gray(e04_set["delivery_clipped"]), gray(e04_set["delivery_ok"])
    assert va.shape == vb.shape and np.array_equal(va, vb)


def manifest():
    return json.loads((REPO / "fixtures" / "manifest.json").read_text(encoding="utf-8"))


def test_manifest_is_valid_complete_and_rights_clean(schema_registry):
    m = manifest()
    schema_registry("fixture-manifest.schema.json").validate(m)
    assert m["fonts"]["bundled"] == [] and m["media_in_git"] is False
    ids = [i["id"] for i in m["items"]]
    assert len(ids) == len(set(ids))
    assert {"clean", "black", "flash", "freeze", "caption_drop_30", "caption_drop_25", "caption_overlap", "clipped_audio", "low_feature"} <= set(ids)
    assert any(i.startswith("sample_script.he") for i in ids) and any(i.startswith("sample_speaker") for i in ids)
    for item in m["items"]:
        assert "No third-party media" in item["rights"] and item["creator"].startswith("fixtures/generators/")
    flat = json.dumps(m, ensure_ascii=False)
    assert not re.search(r"[A-Za-z]:\\\\Users|/Users/", flat, re.I)


@pytest.mark.ffmpeg
def test_generated_content_hashes_match_manifest_or_warn_on_other_ffmpeg(e04_set):
    import make_e04_set as gen

    m = manifest()
    recorded = {i["id"]: i["content_sha256"] for i in m["items"]}
    same_build = m["recorded_with"]["ffmpeg"] == ffprobe.ffmpeg_version()
    drift = [r["id"] for r in e04_set.records if recorded[r["id"]] != r["content_sha256"]]
    if drift and same_build:
        pytest.fail(f"content hash drift with the SAME ffmpeg build: {drift}")
    if drift:
        warnings.warn(f"decoded-content hashes differ on this FFmpeg build ({ffprobe.ffmpeg_version()}) for {drift}; ground-truth tests are the hard check", stacklevel=1)
    assert gen.GENERATOR_VERSION == m["generator_version"]


@pytest.mark.ffmpeg
def test_sample_project_assets_are_complete_and_bilingual(sample_project, tricky_dir):
    src = sample_project["source"]
    names = {p.name for p in src.iterdir()}
    assert {"speaker_standin_1080x1920.mp4", "broll_abstract_1080x1920.mp4", "music_bed.wav", "logo_mark.png", "script.he.txt", "script.en.txt",
            "captions.he.srt", "captions.en.srt", "cues.json", "brief.json"} <= names
    v = ffprobe.probe(src / "speaker_standin_1080x1920.mp4")
    assert (v.first_video.width, v.first_video.height, v.first_video.fps) == (1080, 1920, 30) and ffprobe.expected_frames(src / "speaker_standin_1080x1920.mp4")[0] == 240
    assert v.audio and abs(float(v.duration_s) - 8.0) < 0.1
    assert ffprobe.probe(src / "music_bed.wav").audio[0].channels == 2
    he = (src / "script.he.txt").read_text(encoding="utf-8")
    en = (src / "script.en.txt").read_text(encoding="utf-8")
    assert "₪1,990" in he and "ב-WhatsApp" in he and "Wi-Fi" in he and "50%" in he
    assert re.search(r"[א-ת]", he) and not re.search(r"[א-ת]", en)
    assert len(he.splitlines()) == len(en.splitlines()) == 4
    raw = (src / "captions.he.srt").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw
    # SRT blocks: strictly ordered, frame-aligned, non-overlapping
    for lang in ("he", "en"):
        times = re.findall(r"(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)", (src / f"captions.{lang}.srt").read_text(encoding="utf-8"))
        spans = [(int(a[0]) * 3600 + int(a[1]) * 60 + int(a[2]) + int(a[3]) / 1000, int(a[4]) * 3600 + int(a[5]) * 60 + int(a[6]) + int(a[7]) / 1000) for a in times]
        assert len(spans) == 4 and all(s < e for s, e in spans) and all(spans[i][1] <= spans[i + 1][0] for i in range(3)) and spans[-1][1] <= 8.0
    cues = json.loads((src / "cues.json").read_text(encoding="utf-8"))
    assert cues["schema"] == "avc.cues/1" and "NOT ASR" in cues["timing"]
    for line in cues["lines"]:
        ws = line["words"]
        assert " ".join(w["text"] for w in ws) == line["text"]
        assert Fraction(ws[0]["start"]) == Fraction(line["start"]) and Fraction(ws[-1]["end"]) == Fraction(line["end"])
        assert all(Fraction(a["end"]) <= Fraction(b["start"]) for a, b in zip(ws, ws[1:], strict=False))
        assert all((Fraction(w["start"]) * 30).denominator == 1 for w in ws)  # frame-aligned (30 fps)
    proj = json.loads((src.parent / "project.json").read_text(encoding="utf-8"))
    assert proj["slug"] == "sample-he-en" and proj["title"] == "סרטון הדגמה דו-לשוני" and src.parent.name == "sample-he-en"


@pytest.mark.ffmpeg
def test_sample_text_hashes_are_deterministic_and_match_manifest(sample_project):
    m = {i["id"]: i for i in manifest()["items"]}
    for r in sample_project["records"]:
        if r["kind"] == "text":
            assert m[r["id"]]["content_sha256"] == r["content_sha256"], r["id"]


def test_generators_are_ffmpeg_only_and_commit_no_media():
    gen = REPO / "fixtures" / "generators"
    src = (gen / "make_e04_set.py").read_text(encoding="utf-8")
    assert "import numpy" not in src and "from PIL" not in src and "import PIL" not in src  # FFmpeg ONLY
    offenders = [p for p in (REPO / "fixtures").rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXT and "_generated" not in p.parts]
    assert not offenders, offenders
    offenders = [p for p in REPO.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXT and ".git" not in p.parts and "_generated" not in p.parts
                 and not any(part in {".venv", "node_modules", "__pycache__"} for part in p.parts)
                 and p.parent.name not in {"assets"}]  # other agents may own assets/ icons; we only police our own areas
    ours = [p for p in offenders if p.relative_to(REPO).parts[0] in {"src", "tests", "fixtures", "contracts"}]
    assert not ours, ours


def test_font_fetch_step_is_documented_pins_a_commit_and_has_a_dry_run(capsys):
    import fetch_ofl_fonts as ff

    assert "OFL" in (ff.__doc__ or "") and "NOT run by the tests" in ff.__doc__
    with pytest.raises(SystemExit):
        ff.plan("main", ["heebo"])  # unpinned ref refused
    assert ff.main(["--ref", "0" * 40, "--family", "heebo", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "raw.githubusercontent.com/google/fonts/" + "0" * 40 in out and "OFL.txt" in out and "no network used" in out
    with pytest.raises(SystemExit):
        ff.fetch("https://example.com/x.ttf")  # only the pinned GitHub host


def test_generator_help_runs_without_ffmpeg_work():
    import subprocess
    import sys

    r = subprocess.run([sys.executable, str(REPO / "fixtures" / "generators" / "make_e04_set.py"), "--help"], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0 and "--out" in r.stdout

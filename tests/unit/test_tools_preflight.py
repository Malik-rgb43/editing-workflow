"""hf_preflight: structural HTML lint. Includes E04-B06 (quote style must not change the verdict) and fail-closed behaviour."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "hf_preflight.py"

GOOD = """<!doctype html><html><head><style>
@font-face { font-family: 'Rubik'; src: url('fonts/Rubik.ttf'); }
.card { font-family: 'Rubik', sans-serif; }
</style></head><body>
<div id="root" data-composition-id="main" data-width="1080" data-height="1920">
  <div id="a" class="clip" data-start="0" data-duration="3"><p dir="rtl" class="card">שלום</p></div>
  <div id="b" class="clip" data-start="3" data-duration="2"></div>
</div></body></html>"""


def project(tmp_path: Path, html: str, *, font=True) -> Path:
    d = tmp_path / "פרויקט 'x' 🎬" / "hf"
    d.mkdir(parents=True)
    (d / "index.html").write_text(html, encoding="utf-8")
    if font:
        (d / "fonts").mkdir()
        (d / "fonts" / "Rubik.ttf").write_bytes(b"\0")
    return d


def run(target, *args):
    p = subprocess.run([sys.executable, "-X", "utf8", str(TOOL), str(target), *args], capture_output=True, text=True, encoding="utf-8")
    d = json.loads(p.stdout) if p.stdout.strip().startswith("{") else None
    return p.returncode, d


def codes(d):
    return [f["code"] for f in d["findings"]]


def test_help_fast():
    t = time.monotonic()
    p = subprocess.run([sys.executable, str(TOOL), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0 and time.monotonic() - t < 1.5


def test_clean_project_passes(tmp_path):
    rc, d = run(project(tmp_path, GOOD))
    assert rc == 0 and d["status"] == "PASS", d["findings"]
    assert d["decoded_frames"] == d["expected_frames"] == 1 and d["extra"]["unit"] == "files"


def test_studio_id_is_an_error(tmp_path):
    rc, d = run(project(tmp_path, GOOD.replace('id="a"', 'id="a" data-hf-id="x1"')))
    assert rc == 1 and "studio_id" in codes(d)


@pytest.mark.parametrize("attr", ['dir="rtl"', "dir='rtl'", "DIR=RTL", 'style="direction: rtl"'])
def test_root_rtl_all_spellings_E04_B06(tmp_path, attr):
    html = GOOD.replace("<body>", f"<body {attr}>")
    rc, d = run(project(tmp_path, html))
    assert rc == 1 and "root_rtl" in codes(d)


def test_rtl_on_a_text_element_is_fine(tmp_path):
    rc, d = run(project(tmp_path, GOOD))  # GOOD has dir="rtl" on a <p>
    assert "root_rtl" not in codes(d)


def test_rtl_on_composition_root_is_an_error(tmp_path):
    rc, d = run(project(tmp_path, GOOD.replace('data-composition-id="main"', 'data-composition-id="main" dir="rtl"')))
    assert rc == 1 and "root_rtl" in codes(d)


@pytest.mark.parametrize("q", ['"', "'"])
def test_duplicate_id_same_verdict_for_both_quote_styles_E04_B06(tmp_path, q):
    html = f"<html><body><div id={q}same{q} class={q}clip{q}></div><div id={q}same{q}></div></body></html>"
    rc, d = run(project(tmp_path, html, font=False))
    assert rc == 1 and "duplicate_id" in codes(d)


def test_negative_start(tmp_path):
    rc, d = run(project(tmp_path, GOOD.replace('data-start="0"', 'data-start="-0.5"')))
    assert rc == 1 and "negative_start" in codes(d)


def test_missing_font_file_is_error_and_undeclared_font_is_warning(tmp_path):
    rc, d = run(project(tmp_path, GOOD, font=False))
    assert rc == 1 and "font_file_missing" in codes(d)
    html = GOOD.replace(".card { font-family: 'Rubik', sans-serif; }", ".card { font-family: 'Heebo', sans-serif; }")
    rc2, d2 = run(project(tmp_path / "2", html))
    assert rc2 == 0 and "font_not_declared" in codes(d2)
    rc3, _ = run(project(tmp_path / "3", html), "--strict")
    assert rc3 == 1


def test_var_font_with_generic_fallback_and_timed_composition_root_are_not_flagged(tmp_path):
    # the block pattern: font from a host variable with a generic fallback; a timed root/host is a composition, not a clip
    html = GOOD.replace(".card { font-family: 'Rubik', sans-serif; }", ".card { font-family: var(--hfb-font, sans-serif); }")
    html = html.replace('data-composition-id="main"', 'data-composition-id="main" data-start="0" data-duration="5"')
    rc, d = run(project(tmp_path, html))
    assert rc == 0 and d["status"] == "PASS", d["findings"]
    assert "font_not_declared" not in codes(d) and "missing_clip_class" not in codes(d)
    rc2, d2 = run(project(tmp_path / "2", html.replace("var(--hfb-font, sans-serif)", "var(--hfb-font, 'Heebo', sans-serif)")))
    assert "font_not_declared" in codes(d2)  # a NAMED fallback still needs its file


def test_media_in_3d_and_hidden_parent_and_tween_on_video(tmp_path):
    html = """<html><head><style>.stage{transform-style:preserve-3d}.hid{visibility:hidden}</style></head><body>
    <div class="stage"><video id="v1" src="a.mp4" class="clip" data-start="0" data-duration="2"></video></div>
    <div class="hid"><img src="x.png"></div>
    <script>gsap.to("#v1", {opacity: 0});</script></body></html>"""
    rc, d = run(project(tmp_path, html, font=False))
    assert rc == 0
    assert {"media_in_3d", "media_parent_visibility", "tween_on_video"} <= set(codes(d))


def test_external_resource_and_color_grading_attr(tmp_path):
    html = '<html><body><script src="https://cdn.example.com/x.js"></script><div data-color-grading="1"></div></body></html>'
    rc, d = run(project(tmp_path, html, font=False))
    assert rc == 1 and "color_grading_attr" in codes(d) and "external_resource" in codes(d)


def test_caption_below_rail(tmp_path):
    html = '<html><body><div class="caption" style="position:absolute; top:1500px; height:100px"></div></body></html>'
    rc, d = run(project(tmp_path, html, font=False))
    assert "caption_below_rail" in codes(d)


def test_missing_target_and_empty_project_are_insufficient_evidence_never_pass(tmp_path):
    rc, d = run(tmp_path / "nope")
    assert rc == 2 and d["status"] == "INSUFFICIENT_EVIDENCE"
    empty = tmp_path / "empty"
    empty.mkdir()
    rc2, d2 = run(empty)
    assert rc2 == 2 and "nothing_to_scan" in codes(d2)


@pytest.mark.ffmpeg
def test_clip_longer_than_source(tmp_path, e04_set):
    d = project(tmp_path, '<html><body><video src="v.mkv" class="clip" data-start="0" data-duration="9"></video></body></html>', font=False)
    import shutil

    shutil.copy(e04_set["clean"], d / "v.mkv")
    rc, rep = run(d)
    assert "clip_longer_than_source" in codes(rep)

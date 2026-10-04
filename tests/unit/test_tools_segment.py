"""hf_segment planner/rewriter (pure functions) + dry-run CLI. The render call itself is NOT exercised (needs HyperFrames)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "src"))

import hf_segment as seg  # noqa: E402

DOC = """<!doctype html><html><body>
<div id="root" data-composition-id="main" data-duration="12" data-fps="30">
  <div id="s1" class="clip" data-composition-src="compositions/s1.html" data-start="0" data-duration="4"></div>
  <div id="s2" class="clip" data-composition-src="compositions/s2.html" data-start="4" data-duration="4"></div>
  <div id="s3" class="clip" data-composition-src="compositions/s3.html" data-start="8" data-duration="4"></div>
  <video id="v" src="a.mp4" class="clip" data-start="3" data-duration="6" data-media-start="1"></video>
  <audio id="au" src="m.wav" data-start="0" data-duration="12"></audio>
</div>
<script>window.__timelines = window.__timelines || {}; </script>
</body></html>"""


def test_snap_widens_to_whole_scenes():
    A, B, acts = seg.plan_segment(DOC, 5.0, 6.0, fps=30)
    assert (A, B) == (4.0, 8.0)  # inside scene s2 -> its start/end
    A2, B2, _ = seg.plan_segment(DOC, 3.5, 4.5, fps=30)
    assert (A2, B2) == (0.0, 8.0)  # touches s1 and s2 -> both whole scenes


def test_no_snap_keeps_the_requested_range_frame_rounded():
    A, B, _ = seg.plan_segment(DOC, 5.01, 6.0, fps=30, snap=False)
    assert abs(A - 5.0) < 1 / 30 and B == 6.0


def test_actions_and_rewrite():
    A, B, acts = seg.plan_segment(DOC, 5.0, 6.0, fps=30)
    kinds = {sp.attrs.get("id"): a for sp, a, _ in acts}
    assert kinds == {"s1": "remove", "s2": "shift", "s3": "remove", "v": "trim", "au": "drop"}
    out = seg.rewrite(DOC, A, B, acts, fps=30)
    assert 'id="s1"' not in out and 'id="s3"' not in out and 'id="au"' not in out
    assert re.search(r'id="s2"[^>]*data-start="0"', out)  # shifted by -4
    v = re.search(r'<video[^>]*>', out).group(0)
    assert 'data-start="0"' in v and 'data-duration="4"' in v and 'data-media-start="2"' in v  # cut 1 s in front (media-start 1 + 1), tail clipped at B=8
    assert 'data-duration="4"' in re.search(r'<div id="root"[^>]*>', out).group(0)  # root = B-A
    assert 'data-hf-segment="scrub"' in out and "A=4" in out  # scrub wrapper because A > 0


REAL = """<!doctype html><html><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="20.8" data-width="1080" data-height="1920">
  <div id="cam"><video id="aroll" class="clip" src="assets/aroll.mp4" data-start="0" data-duration="20.8" data-track-index="0"></video></div>
  <div id="hook" class="clip" data-start="0" data-duration="2.6" data-track-index="1">hook</div>
  <div id="caption-clip" class="clip" data-composition-id="caption-host" data-composition-src="compositions/caption.html" data-start="0" data-duration="20.8"></div>
</div></body></html>"""


def test_real_talking_head_root_is_the_canvas_and_whole_film_layers_do_not_force_a_full_render():
    # found on a real 20.8 s talking-head (2026-10-04): the root carried data-start, was trimmed like a clip (19.3 s instead of 3 s),
    # and the whole-film caption host snapped every range to the full film
    A, B, acts = seg.plan_segment(REAL, 1.5, 4.5, fps=30)
    assert (A, B) == (0.0, 4.5)  # snapped only to the 0-2.6 hook scene, not to the 20.8 s layers
    assert "root" not in {sp.attrs.get("id") for sp, _, _ in acts}
    A, B, acts = seg.plan_segment(REAL, 1.5, 4.5, fps=30, snap=False)
    out = seg.rewrite(REAL, A, B, acts, fps=30)
    assert 'data-duration="3"' in re.search(r'<div id="root"[^>]*>', out).group(0)
    v = re.search(r"<video[^>]*>", out).group(0)
    assert 'data-duration="3"' in v and 'data-media-start="1.5"' in v
    cap = re.search(r'<div id="caption-clip"[^>]*>', out).group(0)
    assert 'data-duration="3"' in cap


def test_range_starting_at_zero_needs_no_scrub_wrapper():
    A, B, acts = seg.plan_segment(DOC, 0.0, 2.0, fps=30)
    out = seg.rewrite(DOC, A, B, acts, fps=30)
    assert (A, B) == (0.0, 4.0) and "data-hf-segment" not in out


def test_frame_syntax_and_bad_range():
    assert seg.parse_time("f780", 30) == 26.0 and seg.parse_time("26.5", 30) == 26.5
    try:
        seg.plan_segment(DOC, 5.0, 5.0, fps=30, snap=False)
        assert False
    except ValueError:
        pass


def test_dry_run_cli_prints_plan_and_changes_nothing(tmp_path):
    hf = tmp_path / "פרויקט 🎬" / "hf"
    hf.mkdir(parents=True)
    (hf / "index.html").write_text(DOC.replace('id="s2"', 'id="s2" data-hf-id="q"'), encoding="utf-8")
    p = subprocess.run([sys.executable, "-X", "utf8", str(REPO / "tools" / "hf_segment.py"), str(hf), "--from", "5", "--to", "6", "--dry-run"], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    d = json.loads(p.stdout)
    assert d["snapped"] == [4.0, 8.0] and d["actions"]["remove"] == 2
    assert not (hf / "index.seg.html").exists()
    assert 'data-hf-id="q"' in (hf / "index.html").read_text(encoding="utf-8")  # dry run never edits the project

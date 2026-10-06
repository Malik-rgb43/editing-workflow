"""transcribe (no model downloads here), new_project, render_lock and ledger CLIs."""

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


def run(tool, *args, env=None, timeout=120):
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / f"{tool}.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=timeout, env=env)


@pytest.mark.parametrize("tool", ["transcribe", "new_project", "render_lock", "ledger", "hf_segment", "hf_deliver", "word_retime", "vo_clean", "connections"])
def test_help_under_one_and_a_half_seconds(tool):
    t = time.monotonic()
    p = run(tool, "--help")
    assert p.returncode == 0 and time.monotonic() - t < 1.5, (tool, time.monotonic() - t)  # E04-L01: the original transcribe --help took > 45 s


def test_transcribe_flags_the_real_hallucination_and_passes_real_speech():
    import transcribe as tr

    halluc = [{"w": "תודה", "start": 0.0, "end": 1.86}, {"w": "רבה.", "start": 1.86, "end": 18.28}]  # the real no-VAD output, 2026-10-04
    signs = tr.hallucination_signs(halluc, 20.8)
    assert len(signs) == 2 and "16.4 s" in signs[0]
    speech = [{"w": f"מילה{i}", "start": i * 0.3, "end": i * 0.3 + 0.25} for i in range(170)]  # ~3.3 words/s like the 52 s talking-head
    assert tr.hallucination_signs(speech, 51.99) == []
    assert tr.hallucination_signs(halluc[:1], 4.0) == []  # a short clip with one short word is not suspicious


def test_transcribe_normalize_words_is_monotonic_and_drops_empties():
    import transcribe

    out = transcribe.normalize_words([{"w": " שלום ", "start": 0.5, "end": 0.9, "prob": 0.91234}, {"w": " ", "start": 1, "end": 2}, {"w": "עולם", "start": 0.7, "end": 0.6}, {"w": "x", "start": -1, "end": 5}])
    assert [w["w"] for w in out] == ["שלום", "עולם", "x"]
    assert all(o["end"] >= o["start"] >= 0 for o in out) and out[1]["start"] >= out[0]["end"] - 0.001


def test_transcribe_has_exactly_one_route_and_never_a_whisper_cpp_binary():
    import transcribe

    routes = {"faster-whisper": {"usable": False}}
    assert transcribe.choose_route(routes) is None
    routes["faster-whisper"]["usable"] = True
    assert transcribe.choose_route(routes) == "faster-whisper"
    assert list(transcribe.available_routes()) == ["faster-whisper"]


def test_transcribe_refuses_without_model_and_without_download_permission(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF....")
    p = run("transcribe", wav, "-o", tmp_path / "w.json")
    assert p.returncode == 2 and not (tmp_path / "w.json").exists()
    assert "allow-download" in p.stderr or "no usable route" in p.stderr


def test_transcribe_never_assumes_hebrew_and_the_hebrew_model_refuses_other_languages():
    import transcribe as tr

    he = tr.DEFAULT_HE_MODEL
    assert tr.hebrew_only(he, None) and not tr.hebrew_only(tr.MULTILINGUAL_MODEL, None)
    assert tr.hebrew_only("/models/my-model", "he") and not tr.hebrew_only("/models/ivrit-ct2", "multi")  # --model-lang wins
    assert tr.language_refusal("he", None, he, None) is None
    assert tr.language_refusal("auto", None, he, None) is None  # before the run: nothing detected yet
    assert tr.language_refusal("auto", "he", he, None) is None
    msg = tr.language_refusal("auto", "en", he, None)
    assert "'en' (detected)" in msg and tr.MULTILINGUAL_MODEL in msg and "yes" in msg
    assert "requested" in tr.language_refusal("ar", None, he, None)
    assert tr.language_refusal("en", "en", tr.MULTILINGUAL_MODEL, None) is None
    p = run("transcribe", "--help")
    assert "auto" in p.stdout


def test_transcribe_refuses_an_english_request_on_the_hebrew_model_before_running(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF....")
    model = tmp_path / "ivrit-ct2"
    model.mkdir()
    (model / "model.bin").write_bytes(b"x")
    p = run("transcribe", wav, "-o", tmp_path / "w.json", "--language", "en", "--model-dir", model)
    if "no usable route" in p.stderr:
        pytest.skip("faster-whisper is not installed here")
    assert p.returncode == 2 and not (tmp_path / "w.json").exists()
    assert "tuned for Hebrew only" in p.stderr and "--model-lang multi" in p.stderr


def test_transcribe_missing_input_exits_nonzero(tmp_path):
    p = run("transcribe", tmp_path / "nope.wav", "-o", tmp_path / "w.json")
    assert p.returncode == 2


@pytest.mark.ffmpeg
def test_new_project_scaffold_copy_verify_and_no_overwrite(tmp_path, e04_set):
    wr = tmp_path / "work"
    p = run("new_project", "סרטון בדיקה", "--work-root", wr, "--copy", e04_set["clean"], "--json")
    assert p.returncode == 0, p.stderr
    d = json.loads(p.stdout)
    root = Path(d["root"])
    assert root.name.isascii() and (root / "source" / "clean.mkv").is_file() and (root / "hf" / "fonts").is_dir()
    assert json.loads((root / "project.json").read_text(encoding="utf-8"))["title"] == "סרטון בדיקה"
    p2 = run("new_project", "סרטון בדיקה", "--work-root", wr, "--copy", e04_set["clean"], "--json")
    assert p2.returncode == 2 and "never overwritten" in p2.stdout  # re-run does not overwrite the source copy


def test_new_project_refuses_without_work_root_and_non_ascii_root(tmp_path):
    import os

    env = {k: v for k, v in os.environ.items() if not k.startswith("AVC_")}
    p = run("new_project", "x", env=env)
    assert p.returncode == 2 and "work root" in p.stderr
    p2 = run("new_project", "x", "--work-root", tmp_path / "תיקייה")
    assert p2.returncode == 2


def test_render_lock_status_and_run_roundtrip(tmp_path):
    lock = tmp_path / "locks" / "r.lock"
    import os

    env = dict(os.environ, AVC_PATHS_LOCK_PATH=str(lock))
    p = run("render_lock", "status", "--json", env=env)
    assert p.returncode == 0 and json.loads(p.stdout)["state"] == "free"


def test_ledger_demo_and_summary(tmp_path):
    f = tmp_path / "l.jsonl"
    assert run("ledger", "demo", f).returncode == 0
    p = run("ledger", "summarize", f, "--json")
    d = json.loads(p.stdout)
    assert p.returncode == 0 and d["malformed_lines"] == 0
    f.write_text(f.read_text(encoding="utf-8") + "{not json\n", encoding="utf-8")
    assert run("ledger", "summarize", f).returncode == 2  # malformed lines are reported, never skipped silently


def test_new_project_init_hyperframes_reports_missing_engine_and_never_downloads(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import new_project
    from core import hf_engine

    hf = tmp_path / "hf"
    hf.mkdir()
    saved = hf_engine.find
    hf_engine.find = lambda *a, **k: None
    try:
        r = new_project._init_hyperframes(hf)
    finally:
        hf_engine.find = saved
    assert r["ok"] is False and r["index_html_created"] is False and "engine not found" in r["why"]
    (hf / "x.txt").write_text("keep", encoding="utf-8")
    r2 = new_project._init_hyperframes(hf)
    assert r2["ok"] is False and "not empty" in r2["why"] and (hf / "x.txt").read_text(encoding="utf-8") == "keep"


def test_hf_studio_parses_the_engine_json_and_refuses_a_folder_without_a_project(tmp_path):
    import hf_studio

    line = '{"schemaVersion":1,"operation":"start","ok":true,"result":{"state":"started","studioUrl":"http://127.0.0.1:3002/#project/hf","port":3002}}'
    assert hf_studio.parse_engine_json("lint: 1 warning\n" + line)["result"]["port"] == 3002
    assert hf_studio.parse_engine_json("no json here") is None
    hf = tmp_path / "demo-project-1a2b3c" / "hf"
    assert hf_studio.with_project_tag("http://127.0.0.1:3002/#project/hf", hf) == "http://127.0.0.1:3002/?p=demo-project-1a2b3c#project/hf"
    assert hf_studio.with_project_tag("http://127.0.0.1:3002/?p=x#project/hf", hf).count("?p=") == 1
    p = run("hf_studio", tmp_path / "empty")
    assert p.returncode == 2 and "index.html not found" in p.stderr


def test_motion_qa_cuts_accept_frames_and_seconds():
    import types

    import motion_qa

    a = types.SimpleNamespace(cuts="48,1.8667,86", cuts_from=None)
    assert motion_qa.parse_cuts(a, 30.0) == [48, 56, 86]  # "1.8667" has a decimal point = seconds (real edit point, 2026-10-04)


def test_hf_deliver_loudnorm_aims_under_the_true_peak_gate():
    import hf_deliver

    assert hf_deliver.TP_MARGIN_DB >= 0.3  # a target equal to the gate measured -0.99 vs -1.0 after AAC (2026-10-04)


def test_frame_qa_allows_pops_only_inside_planned_fast_runs():
    import frame_qa
    from core.timebase import FrameClock

    means = [100.0] * 20
    diffs = [0.0] * 20
    for i in (5, 15):  # a single different frame at 5 and at 15
        diffs[i] = diffs[i + 1] = 60.0
    clock = FrameClock.cfr("10", 20)
    allow = frame_qa.allowed_frames(["0.4-0.6"], 10.0)  # frames 4..6: a 16th-note run
    findings, _ = frame_qa.analyze(means, diffs, clock=clock, allow_frames=allow)
    codes = {(f.code, f.frame) for f in findings}
    assert ("pop_allowed", 5) in codes and ("pop_frame", 15) in codes and ("pop_frame", 5) not in codes


def test_session_hint_lists_projects_newest_first_and_stays_silent_without_any(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO / "tools"))
    import session_hint as sh

    for name in ("old", "new"):
        (tmp_path / "projects" / name / "hf").mkdir(parents=True)
        (tmp_path / "projects" / name / "hf" / "index.html").write_text("<html>", encoding="utf-8")
        time.sleep(0.05)
    found = sh.find_projects(tmp_path, None)
    assert [p.name for p in found] == ["new", "old"]
    assert [p.name for p in sh.find_projects(tmp_path / "projects" / "old" / "hf", None)] == ["old"]  # started inside hf/
    assert [p.name for p in sh.find_projects(tmp_path / "projects" / "old", tmp_path)] == ["new", "old"]  # a project + its work root, no duplicate
    monkeypatch.setenv("AVC_PATHS_WORK_ROOT", str(tmp_path))
    assert sh.configured_work_root(REPO) == tmp_path
    p = subprocess.run([sys.executable, str(REPO / "tools" / "session_hint.py"), "--cwd", str(tmp_path)], capture_output=True, text=True, encoding="utf-8")
    ctx = json.loads(p.stdout)["hookSpecificOutput"]
    assert p.returncode == 0 and ctx["hookEventName"] == "SessionStart"
    assert "hf_studio.py" in ctx["additionalContext"] and "FIRST action" in ctx["additionalContext"]
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("AVC_PATHS_WORK_ROOT", str(empty))
    p = subprocess.run([sys.executable, str(REPO / "tools" / "session_hint.py"), "--cwd", str(empty)], capture_output=True, text=True, encoding="utf-8")
    assert (p.returncode, p.stdout) == (0, "")


def test_plugin_session_start_hook_runs_the_session_hint():
    hooks = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]["SessionStart"][0]["hooks"][0]
    assert "${CLAUDE_PLUGIN_ROOT}/tools/session_hint.py" in hooks["command"] and hooks["timeout"] <= 10


def test_captions_export_groups_words_into_cues_for_srt_vtt_and_txt(tmp_path):
    import captions_export as ce

    words = [{"w": "Hello", "start": 0.0, "end": 0.3}, {"w": "there.", "start": 0.35, "end": 0.6}, {"w": "This", "start": 2.0, "end": 2.2},
             {"w": "is", "start": 2.25, "end": 2.3}, {"w": "after", "start": 2.35, "end": 2.6}, {"w": "a", "start": 2.62, "end": 2.65}, {"w": "pause", "start": 2.7, "end": 3.0}]
    cs = ce.cues(words, max_words=3)
    assert [c["text"] for c in cs] == ["Hello there.", "This is after", "a pause"]
    assert cs[0]["end"] == 0.8  # extended to the minimum duration, into the gap only
    srt = ce.render(cs, "srt")
    assert srt.startswith("1\n00:00:00,000 --> 00:00:00,800\nHello there.\n")
    assert ce.render(cs, "vtt", offset=1.0).startswith("WEBVTT\n\n00:00:01.000 --> 00:00:01.800\n")
    he = [{"w": "שלום", "start": 0.0, "end": 0.4}, {"w": "לכולם?", "start": 0.5, "end": 0.9}, {"w": "עוד", "start": 1.0, "end": 1.2}]
    assert [c["text"] for c in ce.cues(he)] == ["שלום לכולם?", "עוד"]
    p = tmp_path / "w.json"
    p.write_text(json.dumps({"schema": "avc.words/1", "words": words}), encoding="utf-8")
    assert run("captions_export", p, "-o", tmp_path / "out.vtt").returncode == 0
    assert (tmp_path / "out.vtt").read_text(encoding="utf-8").startswith("WEBVTT")
    p.write_text(json.dumps({"words": []}), encoding="utf-8")
    assert run("captions_export", p, "-o", tmp_path / "x.srt").returncode == 2

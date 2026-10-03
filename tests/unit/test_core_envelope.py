"""envelope.py: fail-closed statuses, exit codes, numeric gates (E04-B01/B02/B04/B05/B07) and the delivery aggregator."""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
from fractions import Fraction

import pytest

from core import envelope as ev
from core.envelope import DeliveryContract, Envelope, EnvelopeBuilder, Finding, Severity, Status
from core.errors import EXIT_ERROR, EXIT_FAIL, EXIT_INSUFFICIENT, EXIT_PASS, GateState, MediaToolMissing
from core.timebase import FrameClock, describe_frame

SHA_A = hashlib.sha256(b"file-a").hexdigest()
SHA_B = hashlib.sha256(b"file-b").hexdigest()


def good(tool="frame_qa", sha=SHA_A, decoded=60, expected=60, status="PASS", **kw):
    d = {
        "schema": ev.ENVELOPE_SCHEMA, "tool": tool, "version": "0.1.0", "kind": "qa", "input_sha256": sha,
        "decoded_frames": decoded, "expected_frames": expected, "coverage": decoded / expected if expected else None,
        "status": status, "findings": [], "ended_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    d.update(kw)
    return d


# ------------------------------------------------------------------------------------------------ decide_status
def test_pass_requires_full_coverage_and_hash():
    st, extra = ev.decide_status([], input_ok=True, decoded_frames=60, expected_frames=60)
    assert st is Status.PASS and extra == []


@pytest.mark.parametrize(
    "kw,code",
    [
        (dict(input_ok=False, decoded_frames=60, expected_frames=60), "input_unusable"),
        (dict(input_ok=True, decoded_frames=0, expected_frames=60), "zero_frames_decoded"),  # E04-B01
        (dict(input_ok=True, decoded_frames=None, expected_frames=60), "decoded_frames_unknown"),
        (dict(input_ok=True, decoded_frames=60, expected_frames=None), "expected_frames_unknown"),
        (dict(input_ok=True, decoded_frames=60, expected_frames=0), "expected_frames_unknown"),
        (dict(input_ok=True, decoded_frames=59, expected_frames=60), "coverage_below_minimum"),
        (dict(input_ok=True, decoded_frames=61, expected_frames=60), "frame_count_mismatch"),
        (dict(input_ok=True, decoded_frames=60, expected_frames=60, timed_out=True), "timeout"),
        (dict(input_ok=True, decoded_frames=True, expected_frames=60), "decoded_frames_unknown"),  # bool is not a count
    ],
)
def test_nothing_that_could_not_look_can_pass(kw, code):
    st, extra = ev.decide_status([], **kw)
    assert st is Status.INSUFFICIENT_EVIDENCE
    assert code in [f.code for f in extra]


def test_found_defect_outranks_coverage_gap():
    st, _ = ev.decide_status([Finding("black_frame", "x")], input_ok=True, decoded_frames=10, expected_frames=60)
    assert st is Status.FAIL


def test_warning_and_info_do_not_change_status():
    st, _ = ev.decide_status([Finding("hold", "x", Severity.WARNING), Finding("n", "y", Severity.INFO)], input_ok=True, decoded_frames=5, expected_frames=5)
    assert st is Status.PASS


def test_lowering_min_coverage_is_explicit_and_works():
    st, _ = ev.decide_status([], input_ok=True, decoded_frames=30, expected_frames=60, min_coverage=0.5)
    assert st is Status.PASS


# ------------------------------------------------------------------------------------------------ exit codes
def test_exit_code_mapping():
    assert [ev.exit_code_for(s) for s in ("PASS", "FAIL", "INSUFFICIENT_EVIDENCE")] == [EXIT_PASS, EXIT_FAIL, EXIT_INSUFFICIENT] == [0, 1, 2]
    assert ev.gate_state_for("PASS") is GateState.PASS and ev.gate_state_for("FAIL") is GateState.FAIL
    assert ev.gate_state_for("INSUFFICIENT_EVIDENCE") is GateState.INSUFFICIENT_EVIDENCE


def test_only_pass_state_is_green():
    assert [s for s in GateState if s.is_green] == [GateState.PASS]
    assert {s.value for s in GateState} == {"pass", "fail", "unsupported", "not_run", "insufficient_evidence", "error"}


# ------------------------------------------------------------------------------------------------ Envelope invariants
def test_cannot_construct_a_vacuous_pass():
    for kw in (dict(decoded_frames=0, expected_frames=0), dict(decoded_frames=5, expected_frames=6), dict(decoded_frames=None, expected_frames=None)):
        with pytest.raises(ValueError):
            Envelope(tool="t", version="1", input_sha256=SHA_A, coverage=None, status=Status.PASS, **kw)
    with pytest.raises(ValueError):
        Envelope(tool="t", version="1", input_sha256=None, decoded_frames=3, expected_frames=3, coverage=1.0, status=Status.PASS)
    Envelope(tool="t", version="1", input_sha256=SHA_A, decoded_frames=3, expected_frames=3, coverage=1.0, status=Status.PASS)


def test_envelope_json_has_the_contract_keys_and_is_strict_json():
    b = EnvelopeBuilder("frame_qa", "0.1.0")
    b.set_input_sha256(SHA_A)
    b.set_frames(decoded=60, expected=60, fps="30000/1001")
    b.add(Finding.at_frame("hold", "static", describe_frame(19, Fraction(30000, 1001)), Severity.WARNING, span=[19, 50]))
    env = b.build()
    d = json.loads(env.to_json())
    for k in ("tool", "version", "input_sha256", "decoded_frames", "expected_frames", "coverage", "status", "findings"):
        assert k in d
    assert d["status"] == "PASS" and d["coverage"] == 1.0 and d["fps"] == "30000/1001"
    f = d["findings"][0]
    assert f["frame"] == 19 and f["time_s"] == "19019/30000" and f["severity"] == "warning" and f["data"] == {"span": [19, 50]}
    with pytest.raises(ValueError):
        Envelope(tool="t", version="1", input_sha256=SHA_A, decoded_frames=1, expected_frames=1, coverage=float("nan"), status=Status.PASS).to_json()


# ------------------------------------------------------------------------------------------------ builder: E04-B01
def test_e04_b01_missing_input_is_insufficient_evidence_exit_2(tmp_path):
    b = EnvelopeBuilder("caption_qa", "0.1.0", tmp_path / "absent.mkv")
    b.set_frames(decoded=0, expected=None)  # exactly what the original tool saw: 0 frames, ffmpeg error ignored
    env = b.build()
    assert env.status is Status.INSUFFICIENT_EVIDENCE and env.exit_code == 2 and env.input_sha256 is None
    codes = [f.code for f in env.findings]
    assert "input_missing" in codes and "input_unusable" not in codes  # one clear message, not two
    assert any(f.severity is Severity.EVIDENCE_GAP for f in env.findings)


def test_unreadable_directory_input_is_insufficient(tmp_path):
    env = EnvelopeBuilder("t", "1", tmp_path).build()
    assert env.status is Status.INSUFFICIENT_EVIDENCE


def test_timeout_never_passes(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"1")
    b = EnvelopeBuilder("frame_qa", "0.1.0", f)
    b.set_frames(decoded=60, expected=60)
    b.mark_timeout()
    assert b.build().status is Status.INSUFFICIENT_EVIDENCE


def test_e04_b07_zero_tracked_pairs_is_insufficient_not_crash(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"1")

    def tool(b: EnvelopeBuilder) -> None:
        b.set_frames(decoded=60, expected=60)
        tracked_pairs = []
        b.gap("no_tracked_pairs", "optical flow found 0 tracked pairs", tracked_pairs=len(tracked_pairs))
        max(tracked_pairs)  # the original crashed here: ValueError on an empty sequence

    env = ev.guarded("motion_qa", "0.1.0", tool, f)
    assert env.status is Status.INSUFFICIENT_EVIDENCE
    assert {"no_tracked_pairs", "tool_error"} <= {x.code for x in env.findings}
    assert ev.emit(env, io.StringIO()) == EXIT_ERROR  # crash -> exit 3, never 0


def test_guarded_maps_toolkit_errors_with_their_code(tmp_path):
    def tool(b):
        raise MediaToolMissing("ffmpeg was not found", remediation="install it")

    env = ev.guarded("frame_qa", "0.1.0", tool, None)
    assert env.status is Status.INSUFFICIENT_EVIDENCE and env.findings[0].code == "media_tool_missing" and env.state is GateState.ERROR


def test_emit_writes_utf8_json_and_returns_exit_code():
    out = io.StringIO()
    env = Envelope(tool="t", version="1", input_sha256=SHA_A, decoded_frames=1, expected_frames=1, coverage=1.0, status=Status.PASS,
                   findings=[Finding("note", "שלום 🎬", Severity.INFO)])
    assert ev.emit(env, out) == 0
    assert "שלום 🎬" in out.getvalue() and json.loads(out.getvalue())["status"] == "PASS"
    fail = Envelope(tool="t", version="1", input_sha256=SHA_A, decoded_frames=1, expected_frames=1, coverage=1.0, status=Status.FAIL, findings=[Finding("x", "y")])
    assert ev.emit(fail, io.StringIO()) == EXIT_FAIL


# ------------------------------------------------------------------------------------------------ numeric gates
def test_e04_b04_numeric_zero_is_a_measurement_not_missing():
    # true peak 0.0 dBTP must FAIL the "<= -1.0" gate; the original `value or -99` hid it
    f = ev.check_range("true_peak_dbtp", 0.0, hi=-1.0, unit="dBTP")
    assert f is not None and f.severity is Severity.ERROR and f.data["value"] == 0.0
    assert ev.check_range("true_peak_dbtp", -2.0, hi=-1.0) is None


def test_e04_b05_failed_hard_gate_fails_the_run():
    f = ev.check_range("true_peak_dbtp", 0.5, hi=-1.0)
    st, _ = ev.decide_status([f], input_ok=True, decoded_frames=1, expected_frames=1)
    assert st is Status.FAIL and ev.exit_code_for(st) == 1


@pytest.mark.parametrize("v", [None, float("nan"), float("inf"), True, "0.0"])
def test_unmeasured_metric_is_an_evidence_gap_never_a_pass(v):
    f = ev.check_range("lufs", v, lo=-15.0, hi=-13.0)
    assert f is not None and f.severity is Severity.EVIDENCE_GAP and f.code == "lufs_missing"
    st, _ = ev.decide_status([f], input_ok=True, decoded_frames=1, expected_frames=1)
    assert st is Status.INSUFFICIENT_EVIDENCE


def test_range_lower_bound():
    assert ev.check_range("lufs", -20.0, lo=-15.0).severity is Severity.ERROR
    assert ev.check_range("lufs", -15.0, lo=-15.0, hi=-13.0) is None


# ------------------------------------------------------------------------------------------------ real fixtures
@pytest.mark.ffmpeg
def test_envelope_over_real_e04_media(e04_set):
    """Mini detectors (test-only) + the real decoder + the envelope: positive and negative controls."""
    from core.ffprobe import expected_frames, probe
    from core.media import FrameReader

    def run_black_detector(path):
        info = probe(path)
        exp, _src = expected_frames(path, info)
        fps = info.first_video.fps
        clock = FrameClock.cfr(fps, exp)

        def tool(b):
            reader = FrameReader(path, info=info)
            for i, fr in enumerate(reader):
                if int(fr.max()) == 0:
                    b.add(Finding.at_frame("black_frame", "frame is all black", clock.describe(i)))
            b.set_frames(decoded=reader.decoded, expected=exp, fps=fps)
            if not reader.ok:
                b.gap("decode_not_clean", "decoder did not finish cleanly", exit=reader.returncode)

        return ev.guarded("frame_qa", "0.1.0", tool, path)

    clean = run_black_detector(e04_set["clean"])
    assert clean.status is Status.PASS and clean.decoded_frames == clean.expected_frames == 60 and clean.exit_code == 0
    black = run_black_detector(e04_set["black"])
    assert black.status is Status.FAIL and black.exit_code == 1
    f = black.findings[0]
    assert (f.frame, f.time_s) == (15, "1/2")  # frame number AND real timestamp
    ntsc = run_black_detector(e04_set["ntsc_30000_1001"])
    assert ntsc.status is Status.PASS and ntsc.fps == "30000/1001"

    # the original caption_qa printed i/30: with the rational clock the 25-fps drop is at 1 s
    info25 = probe(e04_set["caption_drop_25"])
    drop = describe_frame(25, info25.first_video.fps)
    assert drop["time_s"] == "1"


@pytest.mark.ffmpeg
def test_truncated_file_has_less_decoded_than_expected_and_cannot_pass(e04_set, tmp_path):
    from core.ffprobe import expected_frames, probe
    from core.media import FrameReader

    src = e04_set["delivery_ok"]
    data = src.read_bytes()
    cut = tmp_path / "cut 'ש' 🎬.mp4"
    cut.write_bytes(data[: len(data) // 2])
    info = probe(cut)  # the moov atom is at the front (+faststart): the header still promises 60 frames
    exp, source = expected_frames(cut, info)
    assert (exp, source) == (60, "nb_frames")
    reader = FrameReader(cut, info=info)
    n = sum(1 for _ in reader)
    assert 0 < n < 60
    b = EnvelopeBuilder("frame_qa", "0.1.0", cut)
    b.set_frames(decoded=reader.decoded, expected=exp)
    env = b.build()
    assert env.status is Status.INSUFFICIENT_EVIDENCE and "coverage_below_minimum" in [f.code for f in env.findings]


# ------------------------------------------------------------------------------------------------ aggregator
def contract(**kw):
    base = dict(required=("frame_qa", "caption_qa", "human_review"), artifact_sha256=SHA_A)
    base.update(kw)
    return DeliveryContract(**base)


def attest(tool="human_review", sha=SHA_A, by="reviewer-1", status="PASS"):
    return {"schema": ev.ENVELOPE_SCHEMA, "tool": tool, "version": "1", "kind": "attestation", "input_sha256": sha, "decoded_frames": None,
            "expected_frames": None, "coverage": None, "status": status, "findings": [], "attested_by": by, "ended_utc": dt.datetime.now(dt.timezone.utc).isoformat()}


def test_all_required_gates_pass_is_the_only_green():
    r = ev.aggregate_delivery(contract(), [good("frame_qa"), good("caption_qa"), attest()])
    assert r["status"] == "PASS" and r["coverage"] == 1.0
    assert {g["state"] for g in r["gates"].values()} == {"pass"}
    assert ev.emit(r, io.StringIO()) == 0


def test_no_green_while_a_required_gate_is_not_run():
    r = ev.aggregate_delivery(contract(), [good("frame_qa"), good("caption_qa")])  # nobody did the human review
    assert r["status"] == "INSUFFICIENT_EVIDENCE"
    assert r["gates"]["human_review"]["state"] == "not_run"
    assert r["coverage"] == pytest.approx(2 / 3, abs=1e-6)
    assert ev.emit(r, io.StringIO()) == EXIT_INSUFFICIENT


def test_any_fail_is_fail_even_if_the_rest_is_missing():
    r = ev.aggregate_delivery(contract(), [good("frame_qa", status="FAIL")])
    assert r["status"] == "FAIL" and r["gates"]["frame_qa"]["state"] == "fail" and r["gates"]["caption_qa"]["state"] == "not_run"


def test_failed_optional_gate_still_blocks_delivery():
    c = contract(required=("frame_qa",), optional=("motion_qa",))
    r = ev.aggregate_delivery(c, [good("frame_qa"), good("motion_qa", status="FAIL")])
    assert r["status"] == "FAIL"
    r2 = ev.aggregate_delivery(c, [good("frame_qa")])  # optional not run: reported, not blocking
    assert r2["status"] == "PASS" and r2["gates"]["motion_qa"]["state"] == "not_run" and r2["gates"]["motion_qa"]["required"] is False


def test_stale_evidence_for_another_file_does_not_count():
    r = ev.aggregate_delivery(contract(required=("frame_qa",)), [good("frame_qa", sha=SHA_B)])
    assert r["status"] == "INSUFFICIENT_EVIDENCE" and "different file hash" in r["gates"]["frame_qa"]["reason"]


def test_a_report_may_not_lie_about_pass():
    for lying in (good("frame_qa", decoded=0, expected=60), good("frame_qa", decoded=30, expected=60), good("frame_qa", sha=None)):
        r = ev.aggregate_delivery(contract(required=("frame_qa",), artifact_sha256=lying["input_sha256"] or SHA_A), [lying])
        assert r["status"] == "INSUFFICIENT_EVIDENCE", lying


def test_duplicate_and_malformed_reports_are_errors_not_passes():
    r = ev.aggregate_delivery(contract(required=("frame_qa",)), [good("frame_qa"), good("frame_qa")])
    assert r["gates"]["frame_qa"]["state"] == "error" and r["status"] == "INSUFFICIENT_EVIDENCE"
    r = ev.aggregate_delivery(contract(required=("frame_qa",)), [{"tool": "frame_qa", "status": "PASS"}])
    assert r["gates"]["frame_qa"]["state"] == "error" and "malformed" in r["gates"]["frame_qa"]["reason"]


def test_contract_without_gates_or_hash_can_never_pass():
    assert ev.aggregate_delivery(DeliveryContract(required=(), artifact_sha256=SHA_A), [])["status"] == "INSUFFICIENT_EVIDENCE"
    assert ev.aggregate_delivery(DeliveryContract(required=("frame_qa",)), [good("frame_qa")])["status"] == "INSUFFICIENT_EVIDENCE"


def test_freshness_policy():
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).isoformat()
    c = contract(required=("frame_qa",), max_age_s=3600)
    assert ev.aggregate_delivery(c, [good("frame_qa", ended_utc=old)])["status"] == "INSUFFICIENT_EVIDENCE"
    assert ev.aggregate_delivery(c, [good("frame_qa")])["status"] == "PASS"
    naive = dt.datetime.now().isoformat()  # no timezone: not accepted as evidence
    assert ev.aggregate_delivery(c, [good("frame_qa", ended_utc=naive)])["status"] == "INSUFFICIENT_EVIDENCE"


def test_attestation_needs_a_named_reviewer_and_unsupported_is_not_green():
    r = ev.aggregate_delivery(contract(), [good("frame_qa"), good("caption_qa"), attest(by="")])
    assert r["gates"]["human_review"]["state"] == "insufficient_evidence"
    unsupported = good("caption_qa", decoded=None, expected=None, status="INSUFFICIENT_EVIDENCE", gate_state="unsupported", coverage=None, input_sha256=None)
    r = ev.aggregate_delivery(contract(artifact_sha256=None), [good("frame_qa"), unsupported, attest()])
    assert r["gates"]["caption_qa"]["state"] == "unsupported" and r["status"] == "INSUFFICIENT_EVIDENCE"


def test_artifact_path_is_hashed_and_bound(tmp_path):
    f = tmp_path / "final 'ש' 🎬.mp4"
    f.write_bytes(b"video-bytes")
    sha = ev.sha256_file(f)
    c = DeliveryContract(required=("frame_qa",))
    assert ev.aggregate_delivery(c, [good("frame_qa", sha=sha)], artifact_path=f)["status"] == "PASS"
    f.write_bytes(b"changed-after-qa")  # the file changed after the QA ran
    r = ev.aggregate_delivery(c, [good("frame_qa", sha=sha)], artifact_path=f)
    assert r["status"] == "INSUFFICIENT_EVIDENCE"
    r = ev.aggregate_delivery(c, [good("frame_qa", sha=sha)], artifact_path=tmp_path / "gone.mp4")
    assert r["status"] == "INSUFFICIENT_EVIDENCE"


def test_cli_qa_delivery_roundtrip(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    f = tmp_path / "final.mp4"
    f.write_bytes(b"abc")
    sha = ev.sha256_file(f)
    (tmp_path / "contract.json").write_text(json.dumps({"required": ["frame_qa", "human_review"], "artifact_path": str(f)}), encoding="utf-8")
    (tmp_path / "r1.json").write_text(json.dumps(good("frame_qa", sha=sha)), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"), "PYTHONUTF8": "1"}
    cmd = [sys.executable, "-m", "core", "qa-delivery", str(tmp_path / "contract.json"), str(tmp_path / "r1.json")]
    r = subprocess.run(cmd, capture_output=True, env=env, timeout=60)
    assert r.returncode == EXIT_INSUFFICIENT, r.stderr
    out = json.loads(r.stdout.decode("utf-8"))
    assert out["gates"]["human_review"]["state"] == "not_run" and out["status"] == "INSUFFICIENT_EVIDENCE"
    (tmp_path / "r2.json").write_text(json.dumps(attest(sha=sha)), encoding="utf-8")
    r = subprocess.run(cmd + [str(tmp_path / "r2.json")], capture_output=True, env=env, timeout=60)
    assert r.returncode == 0 and json.loads(r.stdout.decode("utf-8"))["status"] == "PASS"


# ------------------------------------------------------------------------------------------------ schema
def test_envelopes_validate_against_the_contract_schema(schema_registry):
    v = schema_registry("qa-envelope.schema.json")
    b = EnvelopeBuilder("frame_qa", "0.1.0")
    b.set_input_sha256(SHA_A)
    b.set_frames(decoded=2, expected=2, fps="25")
    b.add(Finding.at_frame("hold", "static", describe_frame(1, Fraction(25)), Severity.WARNING))
    v.validate(json.loads(b.build().to_json()))
    bad = EnvelopeBuilder("frame_qa", "0.1.0")
    bad.gap("input_missing", "x")
    v.validate(json.loads(bad.build().to_json()))  # INSUFFICIENT with null hash is valid
    r = ev.aggregate_delivery(contract(), [good("frame_qa"), good("caption_qa"), attest()])
    r_env = {k: val for k, val in r.items() if k not in ("gates", "note")}
    v.validate(r_env)


def test_schema_rejects_a_vacuous_pass(schema_registry):
    v = schema_registry("qa-envelope.schema.json")
    lie = good("frame_qa", decoded=0, expected=0, coverage=None)
    assert list(v.iter_errors(lie)), "a PASS with 0 decoded frames must be schema-invalid"
    assert not list(v.iter_errors(good("frame_qa")))
    lie2 = good("frame_qa", sha=None)
    assert list(v.iter_errors(lie2))


# ------------------------------------------------------------------------------------------------ sampled QA (explicit min_coverage)
def test_explicit_lower_min_coverage_pass_is_recorded_and_not_accepted_by_a_strict_contract(schema_registry, tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"1")
    b = EnvelopeBuilder("face_center", "0.1.0", f)
    b.set_frames(decoded=30, expected=60)
    assert b.build().status is Status.INSUFFICIENT_EVIDENCE  # default is every frame
    env = b.build(min_coverage=0.5)  # a sampled tool says so on purpose
    assert env.status is Status.PASS and env.min_coverage == 0.5
    d = json.loads(env.to_json())
    assert d["min_coverage"] == 0.5 and d["coverage"] == 0.5
    schema_registry("qa-envelope.schema.json").validate(d)
    # the same PASS without the declaration is schema-invalid
    undeclared = {k: v for k, v in d.items() if k != "min_coverage"}
    assert list(schema_registry("qa-envelope.schema.json").iter_errors(undeclared))
    # the aggregator judges against the CONTRACT's minimum, not the report's own claim
    strict = ev.aggregate_delivery(DeliveryContract(required=("face_center",), artifact_sha256=env.input_sha256), [env])
    assert strict["status"] == "INSUFFICIENT_EVIDENCE"
    relaxed = ev.aggregate_delivery(DeliveryContract(required=("face_center",), artifact_sha256=env.input_sha256, min_coverage=0.5), [env])
    assert relaxed["status"] == "PASS"
    with pytest.raises(ValueError):
        Envelope(tool="t", version="1", input_sha256=SHA_A, decoded_frames=3, expected_frames=6, coverage=0.5, status=Status.PASS)  # 1.0 required unless declared

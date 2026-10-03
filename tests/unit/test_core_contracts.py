"""contracts/*.schema.json: every schema is a valid Draft 2020-12 schema, accepts a good instance and rejects bad ones."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SHA = "a" * 64
NOW = "2026-10-02T12:00:00+00:00"

EXPECTED = {"job", "result", "artifact", "budget", "timing-ledger", "qa-envelope", "manifest", "choices", "fixture-manifest"}


def test_all_required_schemas_exist():
    names = {p.name.replace(".schema.json", "") for p in (REPO / "contracts").glob("*.schema.json")}
    assert EXPECTED <= names


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_schema_is_valid_draft_2020_12_and_utf8_lf(name):
    jsonschema = pytest.importorskip("jsonschema")
    f = REPO / "contracts" / f"{name}.schema.json"
    raw = f.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw
    doc = json.loads(raw.decode("utf-8"))
    jsonschema.Draft202012Validator.check_schema(doc)
    assert doc["$schema"].endswith("2020-12/schema") and doc["$id"].endswith(f"{name}.schema.json")


def artifact(**kw):
    d = {"schema": "avc.artifact/1", "path": "final/video_9x16.mp4", "sha256": SHA, "bytes": 10, "role": "final"}
    d.update(kw)
    return d


def test_artifact_paths_must_be_project_relative(schema_registry):
    v = schema_registry("artifact.schema.json")
    v.validate(artifact())
    for bad in ("C:/x/y.mp4", "/etc/passwd", "a\\b.mp4", "../escape.mp4", "a/../../b.mp4"):
        assert list(v.iter_errors(artifact(path=bad))), bad
    v.validate(artifact(path="final/שלום 🎬.mp4"))  # Unicode names are fine inside a project
    assert list(v.iter_errors(artifact(sha256="xyz")))


def test_budget_paid_actions_need_estimate_and_receipt(schema_registry):
    v = schema_registry("budget.schema.json")
    v.validate({"schema": "avc.budget/1", "paid_actions_allowed": False})
    assert list(v.iter_errors({"schema": "avc.budget/1", "paid_actions_allowed": True}))
    ok = {
        "schema": "avc.budget/1", "paid_actions_allowed": True, "max_credits": 40,
        "estimate": {"amount": 36, "unit": "credits", "estimated_on": "2026-10-02", "rate_source": "provider pricing page, checked 2026-10-02"},
        "approval_receipt": {"approved_by": "owner", "approved_utc": NOW, "scope": "one 10 s clip"},
    }
    v.validate(ok)
    bad = dict(ok)
    bad["max_money"] = {"amount": -1, "currency": "usd"}
    assert list(v.iter_errors(bad))


def test_job_and_result_accepted_requires_qa_and_human_approval(schema_registry):
    job = {"schema": "avc.job/1", "job_id": "j1", "adapter": {"id": "hf", "version": "0.8.98"}, "capability": "render", "location": "local", "state": "queued",
           "budget": {"schema": "avc.budget/1", "paid_actions_allowed": False}}
    schema_registry("job.schema.json").validate(job)
    assert list(schema_registry("job.schema.json").iter_errors({**job, "location": "mars"}))
    r = schema_registry("result.schema.json")
    r.validate({"schema": "avc.result/1", "job_id": "j1", "state": "succeeded", "accepted": False})
    assert list(r.iter_errors({"schema": "avc.result/1", "job_id": "j1", "state": "succeeded", "accepted": True}))  # provider-succeeded is not accepted
    env = {"schema": "avc.qa-envelope/1", "tool": "frame_qa", "version": "0.1.0", "input_sha256": SHA, "decoded_frames": 60, "expected_frames": 60, "coverage": 1.0, "status": "PASS", "findings": []}
    full = {"schema": "avc.result/1", "job_id": "j1", "state": "succeeded", "accepted": True, "qa": [env], "review": {"decision": "approved", "reviewer": "x"}, "gates": {"frame_qa": "pass"}}
    r.validate(full)
    assert list(r.iter_errors({**full, "review": {"decision": "rejected"}}))
    assert list(r.iter_errors({**full, "gates": {"frame_qa": "green"}}))
    assert list(r.iter_errors({**full, "qa": [{**env, "decoded_frames": 0, "expected_frames": 0}]}))  # nested envelope is validated too


def test_delivery_manifest_cannot_be_pass_with_a_required_gate_not_run(schema_registry):
    v = schema_registry("manifest.schema.json")
    base = {"schema": "avc.delivery-manifest/1", "project": "demo", "created_utc": NOW,
            "files": [{"artifact": artifact(), "platform": "reels"}],
            "gates": {"frame_qa": {"state": "pass", "required": True}, "human_review": {"state": "not_run", "required": True}},
            "aggregate": "INSUFFICIENT_EVIDENCE"}
    v.validate(base)
    assert list(v.iter_errors({**base, "aggregate": "PASS"})), "no green aggregate while a required gate is not_run"
    ok = {**base, "gates": {"frame_qa": {"state": "pass", "required": True}, "motion_qa": {"state": "not_run", "required": False}}, "aggregate": "PASS"}
    v.validate(ok)


def test_choices_schema(schema_registry):
    v = schema_registry("choices.schema.json")
    board = {"schema": "avc.choices/1", "board_id": "b1", "language": "he", "questions": [
        {"id": "font", "prompt": "איזה פונט?", "options": [{"id": "a", "label": "Heebo"}, {"id": "b", "label": "Assistant"}], "selected": None}]}
    v.validate(board)
    board["questions"][0]["options"] = [{"id": "a", "label": "only one"}]
    assert list(v.iter_errors(board))


def test_ledger_lines_written_by_the_writer_validate(tmp_path, schema_registry):
    from core.ledger import Ledger

    p = tmp_path / "l.jsonl"
    Ledger(p, project="x").record("render", run_min=1.0, credits=None)
    v = schema_registry("timing-ledger.schema.json")
    for line in p.read_text(encoding="utf-8").splitlines():
        v.validate(json.loads(line))
    assert list(v.iter_errors({"schema": "avc.timing-ledger/1", "stage": "x"}))

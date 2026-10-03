"""The fail-closed QA envelope and the delivery aggregator (``qa delivery`` core logic).

Every QA tool reports through one JSON shape (contracts/qa-envelope.schema.json)::

    {tool, version, input_sha256, decoded_frames, expected_frames, coverage,
     status: PASS | FAIL | INSUFFICIENT_EVIDENCE, findings[]}

and exits ``0`` / ``1`` / ``2`` (``3`` = tool crashed).  The rule that makes it *fail-closed*:

    **PASS must be earned.**  It requires a hashed input, a decoded-frame count equal to the expected count
    (coverage 1.0 unless the caller lowers ``min_coverage`` on purpose), and no ``error`` or ``evidence_gap`` finding.
    A timeout, an empty sample set, a missing input, a decoder error, a missing metric - none of them can pass.

This closes E04-B01 (missing input -> exit 0, 0 frames), B04 (numeric 0.0 treated as missing), B05 (failed gate exit
0), B07 (zero tracked pairs crashed; now ``INSUFFICIENT_EVIDENCE``) and the "CLI success is not QA coverage" pattern
(src: distilled 03 tool-portability-and-bugs section 0/5; frontier F04).

The aggregator (``aggregate_delivery``) answers "may this file be delivered?": it needs a report for every required
gate, bound to the hash of the *current* file; a gate nobody ran is ``not_run`` and **no aggregate is green while any
required gate is not green**.  It reports evidence completeness only - never taste (the human review is a gate too).

Usage:
    python -m core qa-delivery contract.json report1.json report2.json ...
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Mapping

from . import __version__ as CORE_VERSION
from .errors import (
    EXIT_ERROR,
    EXIT_FAIL,
    EXIT_INSUFFICIENT,
    EXIT_PASS,
    GateState,
    ToolkitError,
)
from .fsio import fs_path

__all__ = [
    "ENVELOPE_SCHEMA",
    "Status",
    "Severity",
    "Finding",
    "Envelope",
    "EnvelopeBuilder",
    "sha256_file",
    "decide_status",
    "exit_code_for",
    "gate_state_for",
    "check_range",
    "validate_envelope_dict",
    "DeliveryContract",
    "aggregate_delivery",
    "guarded",
    "emit",
]

ENVELOPE_SCHEMA = "avc.qa-envelope/1"


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class Severity(str, Enum):
    ERROR = "error"  # a defect in the media -> FAIL
    WARNING = "warning"  # reported, does not change the status (e.g. an intentional hold)
    INFO = "info"
    EVIDENCE_GAP = "evidence_gap"  # the tool could not look -> INSUFFICIENT_EVIDENCE


def exit_code_for(status: Status | str) -> int:
    s = Status(status)
    return {Status.PASS: EXIT_PASS, Status.FAIL: EXIT_FAIL, Status.INSUFFICIENT_EVIDENCE: EXIT_INSUFFICIENT}[s]


def gate_state_for(status: Status | str) -> GateState:
    s = Status(status)
    return {Status.PASS: GateState.PASS, Status.FAIL: GateState.FAIL, Status.INSUFFICIENT_EVIDENCE: GateState.INSUFFICIENT_EVIDENCE}[s]


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds")


def sha256_file(path: str | os.PathLike[str], *, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(fs_path(path), "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


# --------------------------------------------------------------------------------------------------------------------
# data classes
# --------------------------------------------------------------------------------------------------------------------


@dataclass
class Finding:
    """One observation. ``frame`` and ``time_s`` travel together (rational time, see ``timebase.describe_frame``)."""

    code: str
    message: str
    severity: Severity | str = Severity.ERROR
    frame: int | None = None
    time_s: str | None = None
    timecode: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"code": self.code, "severity": Severity(self.severity).value, "message": self.message}
        if self.frame is not None:
            d["frame"] = self.frame
        if self.time_s is not None:
            d["time_s"] = self.time_s
        if self.timecode is not None:
            d["timecode"] = self.timecode
        if self.data:
            d["data"] = self.data
        return d

    @classmethod
    def at_frame(cls, code: str, message: str, desc: Mapping[str, Any], severity: Severity | str = Severity.ERROR, **data: Any) -> "Finding":
        """Build from ``timebase.describe_frame`` output so frame number AND real timestamp are both recorded."""
        return cls(code, message, severity, frame=desc["frame"], time_s=desc["time_s"], timecode=desc["timecode"], data=dict(data))


def decide_status(
    findings: Iterable[Finding | Mapping[str, Any]],
    *,
    input_ok: bool,
    decoded_frames: int | None,
    expected_frames: int | None,
    min_coverage: float = 1.0,
    timed_out: bool = False,
    frame_tolerance: int = 0,
) -> tuple[Status, list[Finding]]:
    """The one place where PASS is decided. Returns ``(status, extra_findings_explaining_a_downgrade)``."""
    extra: list[Finding] = []

    def gap(code: str, msg: str, **data: Any) -> None:
        extra.append(Finding(code, msg, Severity.EVIDENCE_GAP, data=dict(data)))

    if not input_ok:
        gap("input_unusable", "the input file is missing, unreadable or not hashable; nothing was inspected")
    if timed_out:
        gap("timeout", "the tool timed out before inspecting everything")
    if decoded_frames is None or isinstance(decoded_frames, bool) or decoded_frames < 0:
        gap("decoded_frames_unknown", "decoded frame count is unknown")
    elif decoded_frames == 0:
        gap("zero_frames_decoded", "0 frames were decoded: an empty sample set can never pass")
    if expected_frames is None or isinstance(expected_frames, bool) or expected_frames <= 0:
        gap("expected_frames_unknown", "expected frame count is unknown, so coverage cannot be proven")
    if (
        isinstance(decoded_frames, int)
        and not isinstance(decoded_frames, bool)
        and decoded_frames > 0
        and isinstance(expected_frames, int)
        and not isinstance(expected_frames, bool)
        and expected_frames > 0
    ):
        cov = decoded_frames / expected_frames
        if cov < min_coverage - 1e-12:
            gap("coverage_below_minimum", f"decoded {decoded_frames} of {expected_frames} frames (coverage {cov:.4f} < {min_coverage})", coverage=cov)
        if decoded_frames > expected_frames + frame_tolerance:
            gap("frame_count_mismatch", f"decoded {decoded_frames} frames but the probe expected {expected_frames}")

    sev = []
    for f in list(findings) + extra:
        s = f.severity if isinstance(f, Finding) else f.get("severity", "error")
        sev.append(Severity(s))
    if Severity.ERROR in sev:
        return Status.FAIL, extra  # a found defect is evidence; it outranks a coverage gap
    if Severity.EVIDENCE_GAP in sev:
        return Status.INSUFFICIENT_EVIDENCE, extra
    return Status.PASS, extra


@dataclass
class Envelope:
    tool: str
    version: str
    input_sha256: str | None
    decoded_frames: int | None
    expected_frames: int | None
    coverage: float | None
    status: Status
    findings: list[Finding] = field(default_factory=list)
    kind: str = "qa"  # "qa" | "attestation" | "aggregate"
    input_path: str | None = None
    fps: str | None = None
    started_utc: str | None = None
    ended_utc: str | None = None
    duration_s: float | None = None
    gate_state: str | None = None  # optional refinement for INSUFFICIENT_EVIDENCE: unsupported | not_run | error
    attested_by: str | None = None
    min_coverage: float = 1.0  # the coverage this PASS was judged against; below 1.0 only when the caller chose sampling on purpose
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.status = Status(self.status)
        if self.kind == "qa" and self.status is Status.PASS:
            problems = _pass_problems(self.decoded_frames, self.expected_frames, self.input_sha256, self.min_coverage)
            if problems:
                raise ValueError("an envelope cannot be PASS: " + "; ".join(problems))

    @property
    def exit_code(self) -> int:
        return exit_code_for(self.status)

    @property
    def state(self) -> GateState:
        if self.gate_state:
            return GateState(self.gate_state)
        return gate_state_for(self.status)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "schema": ENVELOPE_SCHEMA,
            "tool": self.tool,
            "version": self.version,
            "kind": self.kind,
            "input_sha256": self.input_sha256,
            "decoded_frames": self.decoded_frames,
            "expected_frames": self.expected_frames,
            "coverage": self.coverage,
            "status": self.status.value,
            "findings": [f.to_dict() if isinstance(f, Finding) else dict(f) for f in self.findings],
        }
        for key in ("input_path", "fps", "started_utc", "ended_utc", "duration_s", "gate_state", "attested_by"):
            val = getattr(self, key)
            if val is not None:
                d[key] = val
        if self.min_coverage != 1.0:
            d["min_coverage"] = self.min_coverage
        if self.extra:
            d["extra"] = self.extra
        return d

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, allow_nan=False)


def _pass_problems(decoded: Any, expected: Any, sha: Any, min_coverage: float = 1.0) -> list[str]:
    problems: list[str] = []
    ints = all(isinstance(x, int) and not isinstance(x, bool) for x in (decoded, expected))
    if not ints:
        problems.append("decoded_frames/expected_frames must be integers")
    else:
        if decoded <= 0:
            problems.append("decoded_frames must be > 0")
        if expected <= 0:
            problems.append("expected_frames must be > 0")
        if expected > 0 and decoded / expected < min_coverage - 1e-12:
            problems.append(f"decoded_frames/expected_frames is below the minimum coverage {min_coverage:g}")
    if not (isinstance(sha, str) and len(sha) == 64):
        problems.append("input_sha256 missing")
    return problems


class EnvelopeBuilder:
    """Collects findings and facts, then ``build()`` decides the status fail-closed.

    Typical use::

        b = EnvelopeBuilder("frame_qa", "0.1.0", input_path)
        b.set_frames(decoded=n_decoded, expected=probe.frame_count, fps="30000/1001")
        b.add(Finding.at_frame("black_frame", "all-black frame", clock.describe(15)))
        env = b.build()          # status + exit code
    """

    def __init__(self, tool: str, version: str, input_path: str | os.PathLike[str] | None = None, *, kind: str = "qa") -> None:
        self.tool = tool
        self.version = version
        self.kind = kind
        self.input_path = os.fspath(input_path) if input_path is not None else None
        self.findings: list[Finding] = []
        self.decoded: int | None = None
        self.expected: int | None = None
        self.fps: str | None = None
        self.timed_out = False
        self.extra: dict[str, Any] = {}
        self.gate_state: str | None = None
        self._t0 = time.monotonic()
        self._start = _utc_now()
        self._sha: str | None = None
        self._input_ok = False
        if self.input_path is not None:
            self._hash_input()

    def _hash_input(self) -> None:
        assert self.input_path is not None
        try:
            if not os.path.isfile(fs_path(self.input_path)):
                raise FileNotFoundError(self.input_path)
            self._sha = sha256_file(self.input_path)
            self._input_ok = True
        except OSError as exc:
            self._sha = None
            self._input_ok = False
            self.findings.append(Finding("input_missing", f"cannot read input {self.input_path!r}: {exc.strerror or exc}", Severity.EVIDENCE_GAP))

    def set_frames(self, *, decoded: int | None, expected: int | None, fps: Any | None = None) -> None:
        self.decoded = decoded
        self.expected = expected
        if fps is not None:
            self.fps = str(fps)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def gap(self, code: str, message: str, **data: Any) -> None:
        self.findings.append(Finding(code, message, Severity.EVIDENCE_GAP, data=dict(data)))

    def mark_timeout(self) -> None:
        self.timed_out = True

    def set_input_sha256(self, sha: str) -> None:
        """For tools that already hashed the input (or for non-file inputs)."""
        self._sha = sha
        self._input_ok = True

    def build(self, *, min_coverage: float = 1.0, frame_tolerance: int = 0) -> Envelope:
        status, extra = decide_status(
            self.findings,
            input_ok=self._input_ok,
            decoded_frames=self.decoded,
            expected_frames=self.expected,
            min_coverage=min_coverage,
            timed_out=self.timed_out,
            frame_tolerance=frame_tolerance,
        )
        # do not duplicate the "input_missing" gap with a second generic one
        extra = [f for f in extra if not (f.code == "input_unusable" and any(x.code == "input_missing" for x in self.findings))]
        findings = list(self.findings) + extra
        coverage: float | None = None
        if isinstance(self.decoded, int) and isinstance(self.expected, int) and self.expected > 0 and not isinstance(self.decoded, bool):
            coverage = round(self.decoded / self.expected, 6)
        return Envelope(
            tool=self.tool,
            version=self.version,
            input_sha256=self._sha,
            decoded_frames=self.decoded,
            expected_frames=self.expected,
            coverage=coverage,
            status=status,
            findings=findings,
            kind=self.kind,
            input_path=self.input_path,
            fps=self.fps,
            started_utc=self._start,
            ended_utc=_utc_now(),
            duration_s=round(time.monotonic() - self._t0, 3),
            gate_state=self.gate_state,
            min_coverage=min_coverage,
            extra=self.extra,
        )


# --------------------------------------------------------------------------------------------------------------------
# numeric gates (E04-B04: 0.0 is a value, None is "missing")
# --------------------------------------------------------------------------------------------------------------------


def check_range(code: str, value: Any, *, lo: float | None = None, hi: float | None = None, unit: str = "") -> Finding | None:
    """Evaluate ``lo <= value <= hi``. Returns ``None`` when it holds, else a finding.

    * ``None`` / NaN / inf / bool -> ``evidence_gap`` (the metric was not measured) - **never** treated as a pass.
    * numeric ``0.0`` is a real measurement (fixes the ``value or -99`` pattern of E04-B04).
    * out of range -> ``error`` (a failed hard gate must fail the run: E04-B05).
    """
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return Finding(f"{code}_missing", f"metric {code!r} was not measured (got {value!r})", Severity.EVIDENCE_GAP)
    v = float(value)
    u = f" {unit}" if unit else ""
    if hi is not None and v > hi:
        return Finding(code, f"{code} = {v:g}{u} exceeds the limit {hi:g}{u}", Severity.ERROR, data={"value": v, "max": hi})
    if lo is not None and v < lo:
        return Finding(code, f"{code} = {v:g}{u} is below the limit {lo:g}{u}", Severity.ERROR, data={"value": v, "min": lo})
    return None


# --------------------------------------------------------------------------------------------------------------------
# validation of third-party / on-disk reports
# --------------------------------------------------------------------------------------------------------------------

_REQUIRED_KEYS = ("tool", "version", "input_sha256", "decoded_frames", "expected_frames", "coverage", "status", "findings")


def validate_envelope_dict(d: Any) -> list[str]:
    """Structural problems of a report (empty list = well-formed). Does not judge the status."""
    if not isinstance(d, dict):
        return ["report is not a JSON object"]
    problems = [f"missing key {k!r}" for k in _REQUIRED_KEYS if k not in d]
    if problems:
        return problems
    if not isinstance(d["tool"], str) or not d["tool"]:
        problems.append("tool must be a non-empty string")
    if not isinstance(d["version"], str) or not d["version"]:
        problems.append("version must be a non-empty string")
    if d["status"] not in {s.value for s in Status}:
        problems.append(f"status {d['status']!r} is not PASS|FAIL|INSUFFICIENT_EVIDENCE")
    if not isinstance(d["findings"], list):
        problems.append("findings must be a list")
    else:
        for i, f in enumerate(d["findings"]):
            if not isinstance(f, dict) or "code" not in f or "message" not in f:
                problems.append(f"findings[{i}] needs code and message")
            elif f.get("severity", "error") not in {s.value for s in Severity}:
                problems.append(f"findings[{i}] has unknown severity {f.get('severity')!r}")
    sha = d["input_sha256"]
    if sha is not None and not (isinstance(sha, str) and len(sha) == 64):
        problems.append("input_sha256 must be 64 hex chars or null")
    for key in ("decoded_frames", "expected_frames"):
        v = d[key]
        if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v < 0):
            problems.append(f"{key} must be a non-negative integer or null")
    cov = d["coverage"]
    if cov is not None and (isinstance(cov, bool) or not isinstance(cov, (int, float)) or not math.isfinite(float(cov)) or not 0 <= cov <= 1.0000001):
        problems.append("coverage must be a number in [0,1] or null")
    return problems


# --------------------------------------------------------------------------------------------------------------------
# delivery aggregator
# --------------------------------------------------------------------------------------------------------------------


@dataclass
class DeliveryContract:
    """What must be true before a file may be delivered.

    ``required`` gate names are the ``tool`` values of the reports (``frame_qa``, ``caption_qa``, ``audio_verify``,
    ``human_review`` ...). ``optional`` gates are listed but never block - except that a gate which ran and FAILED always
    blocks (never deliver a flagged frame).
    """

    required: tuple[str, ...]
    optional: tuple[str, ...] = ()
    artifact_sha256: str | None = None
    max_age_s: float | None = None
    min_coverage: float = 1.0

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "DeliveryContract":
        return cls(
            required=tuple(d.get("required", ())),
            optional=tuple(d.get("optional", ())),
            artifact_sha256=d.get("artifact_sha256"),
            max_age_s=d.get("max_age_s"),
            min_coverage=float(d.get("min_coverage", 1.0)),
        )


def _parse_utc(text: Any) -> _dt.datetime | None:
    if not isinstance(text, str):
        return None
    try:
        dt = _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else None  # naive timestamps are not accepted as evidence


def _evaluate_gate(name: str, reports: list[dict], contract: DeliveryContract, now: _dt.datetime) -> tuple[GateState, str, str | None]:
    """-> (state, reason, reported_status)"""
    if not reports:
        return GateState.NOT_RUN, "no report for this gate", None
    if len(reports) > 1:
        return GateState.ERROR, f"{len(reports)} reports for one gate (ambiguous evidence)", None
    r = reports[0]
    problems = validate_envelope_dict(r)
    if problems:
        return GateState.ERROR, "malformed report: " + "; ".join(problems), None
    status = r["status"]
    kind = r.get("kind", "qa")
    if contract.artifact_sha256 and r["input_sha256"] != contract.artifact_sha256:
        return GateState.INSUFFICIENT_EVIDENCE, "report is bound to a different file hash (stale evidence)", status
    if contract.max_age_s is not None:
        ended = _parse_utc(r.get("ended_utc"))
        if ended is None:
            return GateState.INSUFFICIENT_EVIDENCE, "report has no timezone-aware ended_utc, freshness cannot be checked", status
        if (now - ended).total_seconds() > contract.max_age_s:
            return GateState.INSUFFICIENT_EVIDENCE, f"report is older than {contract.max_age_s:g} s", status
    if status == Status.FAIL.value:
        return GateState.FAIL, "the gate reported FAIL", status
    if status == Status.INSUFFICIENT_EVIDENCE.value:
        refined = r.get("gate_state")
        if refined in ("unsupported", "not_run", "error"):
            return GateState(refined), "the gate reported it could not run", status
        return GateState.INSUFFICIENT_EVIDENCE, "the gate reported INSUFFICIENT_EVIDENCE", status
    # status PASS: re-check the invariants, a report may lie
    if kind == "attestation":
        if not r.get("attested_by"):
            return GateState.INSUFFICIENT_EVIDENCE, "attestation names no reviewer (attested_by)", status
        return GateState.PASS, "attested", status
    prob = _pass_problems(r["decoded_frames"], r["expected_frames"], r["input_sha256"], contract.min_coverage)
    if prob:
        return GateState.INSUFFICIENT_EVIDENCE, "reported PASS without evidence: " + "; ".join(prob), status
    return GateState.PASS, "pass", status


def aggregate_delivery(
    contract: DeliveryContract,
    reports: Iterable[Mapping[str, Any] | Envelope],
    *,
    artifact_path: str | os.PathLike[str] | None = None,
    now: _dt.datetime | None = None,
) -> dict[str, Any]:
    """Combine gate reports into one delivery decision (an envelope-shaped dict plus a ``gates`` table).

    Status rules: any gate FAIL -> ``FAIL``; else any *required* gate that is not ``pass`` (not_run, unsupported,
    insufficient_evidence, error) -> ``INSUFFICIENT_EVIDENCE``; else ``PASS``. A contract with no required gate, or with
    no artifact hash to bind to, can never pass. ``coverage`` here is the share of required gates that passed.
    """
    now = now or _dt.datetime.now(_dt.timezone.utc)
    start = _utc_now()
    t0 = time.monotonic()
    findings: list[Finding] = []
    sha = contract.artifact_sha256
    if artifact_path is not None:
        try:
            actual = sha256_file(artifact_path)
        except OSError as exc:
            actual = None
            findings.append(Finding("artifact_unreadable", f"cannot hash {os.fspath(artifact_path)!r}: {exc.strerror or exc}", Severity.EVIDENCE_GAP))
        if sha is not None and actual is not None and sha != actual:
            findings.append(Finding("artifact_changed", "the file on disk no longer matches the contract hash", Severity.EVIDENCE_GAP))
        sha = actual if actual is not None else sha
        contract = DeliveryContract(contract.required, contract.optional, actual if actual is not None else contract.artifact_sha256, contract.max_age_s, contract.min_coverage)
    if not contract.artifact_sha256:
        findings.append(Finding("artifact_not_hashed", "no artifact hash to bind the evidence to", Severity.EVIDENCE_GAP))
    if not contract.required:
        findings.append(Finding("no_required_gates", "a contract without required gates can never be green", Severity.EVIDENCE_GAP))

    by_tool: dict[str, list[dict]] = {}
    for r in reports:
        d = r.to_dict() if isinstance(r, Envelope) else dict(r)
        by_tool.setdefault(str(d.get("tool", "?")), []).append(d)

    gates: dict[str, dict[str, Any]] = {}
    any_fail = False
    required_green = 0
    for name in (*contract.required, *[o for o in contract.optional if o not in contract.required]):
        required = name in contract.required
        state, reason, rep_status = _evaluate_gate(name, by_tool.get(name, []), contract, now)
        gates[name] = {"required": required, "state": state.value, "reason": reason, "reported_status": rep_status}
        if state is GateState.FAIL:
            any_fail = True
            findings.append(Finding(f"gate_{name}_fail", f"gate {name!r}: {reason}", Severity.ERROR))
        elif required and state is not GateState.PASS:
            findings.append(Finding(f"gate_{name}_{state.value}", f"required gate {name!r} is {state.value}: {reason}", Severity.EVIDENCE_GAP))
        if required and state is GateState.PASS:
            required_green += 1
    unknown = sorted(set(by_tool) - set(gates))
    for name in unknown:
        findings.append(Finding("gate_not_in_contract", f"report from {name!r} is not in the contract and was ignored", Severity.INFO))

    if any_fail:
        status = Status.FAIL
    elif any(f.severity in (Severity.EVIDENCE_GAP, "evidence_gap") for f in findings):
        status = Status.INSUFFICIENT_EVIDENCE
    else:
        status = Status.PASS
    n_req = len(contract.required)
    env = Envelope(
        tool="qa_delivery",
        version=CORE_VERSION,
        input_sha256=contract.artifact_sha256,
        decoded_frames=required_green,
        expected_frames=n_req if n_req else None,
        coverage=round(required_green / n_req, 6) if n_req else None,
        status=status,
        findings=findings,
        kind="aggregate",
        started_utc=start,
        ended_utc=_utc_now(),
        duration_s=round(time.monotonic() - t0, 3),
    )
    out = env.to_dict()
    out["gates"] = gates
    out["note"] = "evidence completeness only; says nothing about taste, rights or factual truth"
    return out


# --------------------------------------------------------------------------------------------------------------------
# CLI helpers
# --------------------------------------------------------------------------------------------------------------------


def guarded(tool: str, version: str, fn: Callable[[EnvelopeBuilder], None], input_path: str | os.PathLike[str] | None = None, *, min_coverage: float = 1.0) -> Envelope:
    """Run ``fn(builder)``; any exception becomes an ``INSUFFICIENT_EVIDENCE`` envelope with a ``tool_error`` finding.

    A crash is a *missing result*, never a pass and never a silent exit 0 (E04-B07).
    """
    b = EnvelopeBuilder(tool, version, input_path)
    try:
        fn(b)
    except ToolkitError as exc:
        b.add(Finding(exc.code, str(exc), Severity.EVIDENCE_GAP))
        b.gate_state = "error"
    except Exception as exc:  # noqa: BLE001 - deliberate: every crash becomes evidence, not an exit 0
        b.add(Finding("tool_error", f"{type(exc).__name__}: {exc}", Severity.EVIDENCE_GAP, data={"trace": traceback.format_exc(limit=6)}))
        b.gate_state = "error"
    env = b.build(min_coverage=min_coverage)
    return env


def emit(env: Envelope | Mapping[str, Any], stream: Any = None) -> int:
    """Print the envelope as UTF-8 JSON and return the process exit code (``sys.exit(emit(env))``)."""
    d = env.to_dict() if isinstance(env, Envelope) else dict(env)
    text = json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    out = stream or sys.stdout
    try:
        out.write(text)
    except UnicodeEncodeError:  # legacy console: never lose the report
        out.write(json.dumps(d, ensure_ascii=True, indent=2, allow_nan=False) + "\n")
    status = d.get("status")
    if status in {s.value for s in Status}:
        code = exit_code_for(status)
        if isinstance(env, Envelope) and env.gate_state == "error" and env.status is Status.INSUFFICIENT_EVIDENCE:
            return EXIT_ERROR
        return code
    return EXIT_ERROR

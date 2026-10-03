"""Timing ledger: one JSONL line per stage attempt, plus a summariser.

Every long-running tool writes a line so that each project becomes its own benchmark (src: blueprint TOOLS_SPEC
section 1.9 and section 3.15).  Fields per line (contracts/timing-ledger.schema.json)::

    schema, project, attempt, stage, tool, started_utc, ended_utc,
    queue_wait_min, setup_min, load_min, run_min, qa_min, review_min,
    renders, retries, credits, status, note

Rules: durations come from a monotonic clock (not from subtracting wall-clock times), wall-clock stamps are timezone-aware
UTC, and ``credits`` is ``null`` when the spend is *unknown* - ``null`` is never summed as ``0`` (src: QA_AND_BENCHMARKS
section 2, "Null != 0").  A malformed line in a ledger is counted and reported by the summariser, never silently skipped.

Usage:
    python -m core ledger summarize <ledger.jsonl> [<ledger.jsonl> ...] [--json]
    python -m core ledger demo <ledger.jsonl>
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator

from .fsio import append_line, fs_path

__all__ = ["LEDGER_SCHEMA", "PHASES", "Ledger", "StageTimer", "read_ledger", "summarize", "format_summary", "main"]

LEDGER_SCHEMA = "avc.timing-ledger/1"
PHASES = ("queue_wait", "setup", "load", "run", "qa", "review")
_MIN = {p: f"{p}_min" for p in PHASES}
_ACTIVE = ("setup", "load", "run", "qa", "review")


def _utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _iso(dt: _dt.datetime) -> str:
    return dt.isoformat(timespec="milliseconds")


class StageTimer:
    """Context manager yielded by ``Ledger.stage``. Switch phases with ``phase("run")``; add credits/renders freely."""

    def __init__(self, ledger: "Ledger", stage: str, tool: str | None, attempt: int | None) -> None:
        self._ledger = ledger
        self.stage = stage
        self.tool = tool
        self.attempt = attempt
        self.renders = 0
        self.retries = 0
        self.credits: float | None = None
        self.note: str | None = None
        self.minutes = {p: 0.0 for p in PHASES}
        self._current: str | None = None
        self._since = 0.0
        self._started = _utc()

    def phase(self, name: str) -> None:
        if name not in PHASES:
            raise ValueError(f"unknown phase {name!r}; use one of {PHASES}")
        self._close_phase()
        self._current, self._since = name, time.monotonic()

    def _close_phase(self) -> None:
        if self._current is not None:
            self.minutes[self._current] += (time.monotonic() - self._since) / 60.0
            self._current = None

    def add_minutes(self, phase: str, minutes: float) -> None:
        """Record time measured elsewhere (e.g. queue wait reported by a provider)."""
        if phase not in PHASES:
            raise ValueError(f"unknown phase {phase!r}")
        if minutes < 0:
            raise ValueError("minutes must be >= 0")
        self.minutes[phase] += minutes

    def add_credits(self, amount: float) -> None:
        self.credits = (self.credits or 0.0) + float(amount)


class Ledger:
    """Append-only writer bound to one file (usually ``projects/<name>/_work/timing-ledger.jsonl``)."""

    def __init__(self, path: str | os.PathLike[str], *, project: str | None = None, attempt: int = 1) -> None:
        self.path = os.fspath(path)
        self.project = project
        self.attempt = attempt

    def record(
        self,
        stage: str,
        *,
        tool: str | None = None,
        started: _dt.datetime | None = None,
        ended: _dt.datetime | None = None,
        queue_wait_min: float = 0.0,
        setup_min: float = 0.0,
        load_min: float = 0.0,
        run_min: float = 0.0,
        qa_min: float = 0.0,
        review_min: float = 0.0,
        renders: int = 0,
        retries: int = 0,
        credits: float | None = None,
        status: str = "ok",
        note: str | None = None,
        attempt: int | None = None,
    ) -> dict[str, Any]:
        if status not in ("ok", "failed", "cancelled", "timeout"):
            raise ValueError("status must be ok|failed|cancelled|timeout")
        now = _utc()
        entry = {
            "schema": LEDGER_SCHEMA,
            "project": self.project,
            "attempt": attempt if attempt is not None else self.attempt,
            "stage": stage,
            "tool": tool,
            "started_utc": _iso(started or now),
            "ended_utc": _iso(ended or now),
            "queue_wait_min": round(float(queue_wait_min), 4),
            "setup_min": round(float(setup_min), 4),
            "load_min": round(float(load_min), 4),
            "run_min": round(float(run_min), 4),
            "qa_min": round(float(qa_min), 4),
            "review_min": round(float(review_min), 4),
            "renders": int(renders),
            "retries": int(retries),
            "credits": None if credits is None else round(float(credits), 6),
            "status": status,
            "note": note,
        }
        for k in ("queue_wait_min", "setup_min", "load_min", "run_min", "qa_min", "review_min"):
            if entry[k] < 0:
                raise ValueError(f"{k} must be >= 0")
        append_line(self.path, json.dumps(entry, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
        return entry

    @contextmanager
    def stage(self, stage: str, *, tool: str | None = None, attempt: int | None = None) -> Iterator[StageTimer]:
        """Time a stage. An exception inside still writes a ``failed`` line (then re-raises); credits stay ``None`` unless added."""
        st = StageTimer(self, stage, tool, attempt)
        status = "ok"
        try:
            yield st
        except KeyboardInterrupt:
            status = "cancelled"
            raise
        except BaseException:
            status = "failed"
            raise
        finally:
            st._close_phase()
            self.record(
                stage,
                tool=tool,
                started=st._started,
                ended=_utc(),
                queue_wait_min=st.minutes["queue_wait"],
                setup_min=st.minutes["setup"],
                load_min=st.minutes["load"],
                run_min=st.minutes["run"],
                qa_min=st.minutes["qa"],
                review_min=st.minutes["review"],
                renders=st.renders,
                retries=st.retries,
                credits=st.credits,
                status=status,
                note=st.note,
                attempt=attempt,
            )


# --------------------------------------------------------------------------------------------------------------------
# reading & summarising
# --------------------------------------------------------------------------------------------------------------------


def read_ledger(path: str | os.PathLike[str]) -> tuple[list[dict[str, Any]], int]:
    """-> (entries, malformed_line_count). Blank lines are ignored; anything else that is not a valid entry is counted."""
    entries: list[dict[str, Any]] = []
    bad = 0
    with open(fs_path(path), "r", encoding="utf-8-sig", newline="") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if not isinstance(obj, dict) or obj.get("schema") != LEDGER_SCHEMA or not isinstance(obj.get("stage"), str):
                bad += 1
                continue
            entries.append(obj)
    return entries, bad


def _num(x: Any) -> float:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else 0.0


@dataclass
class _Agg:
    entries: int = 0
    minutes: dict[str, float] = field(default_factory=lambda: {p: 0.0 for p in PHASES})
    wall_min: float = 0.0
    renders: int = 0
    retries: int = 0
    failed: int = 0
    credits_known: float = 0.0
    credits_unknown_entries: int = 0

    def add(self, e: dict[str, Any]) -> None:
        self.entries += 1
        for p in PHASES:
            self.minutes[p] += _num(e.get(_MIN[p]))
        self.renders += int(_num(e.get("renders")))
        self.retries += int(_num(e.get("retries")))
        if e.get("status") != "ok":
            self.failed += 1
        c = e.get("credits")
        if isinstance(c, (int, float)) and not isinstance(c, bool):
            self.credits_known += float(c)
        else:
            self.credits_unknown_entries += 1
        try:
            a = _dt.datetime.fromisoformat(str(e.get("started_utc")))
            b = _dt.datetime.fromisoformat(str(e.get("ended_utc")))
            if a.tzinfo and b.tzinfo and b >= a:
                self.wall_min += (b - a).total_seconds() / 60.0
        except ValueError:
            pass

    def to_dict(self) -> dict[str, Any]:
        active = sum(self.minutes[p] for p in _ACTIVE)
        return {
            "entries": self.entries,
            "minutes": {p: round(v, 3) for p, v in self.minutes.items()},
            "active_min": round(active, 3),
            "wait_min": round(self.minutes["queue_wait"], 3),
            "wall_min": round(self.wall_min, 3),
            "renders": self.renders,
            "retries": self.retries,
            "failed_entries": self.failed,
            # null != 0: the sum covers only entries that recorded credits; unknown ones are counted separately
            "credits_known_sum": round(self.credits_known, 6),
            "credits_unknown_entries": self.credits_unknown_entries,
        }


def summarize(paths: Iterable[str | os.PathLike[str]], *, project: str | None = None) -> dict[str, Any]:
    """Aggregate one or more ledgers: per project -> per stage, plus grand totals and a malformed-line counter."""
    per_project: dict[str, dict[str, _Agg]] = {}
    total = _Agg()
    malformed = 0
    files = 0
    for p in paths:
        entries, bad = read_ledger(p)
        files += 1
        malformed += bad
        for e in entries:
            proj = e.get("project") or "(unnamed)"
            if project is not None and proj != project:
                continue
            per_project.setdefault(proj, {}).setdefault(str(e["stage"]), _Agg()).add(e)
            total.add(e)
    out_projects = {}
    for proj, stages in per_project.items():
        agg = _Agg()
        stage_dicts = {}
        for name, a in stages.items():
            stage_dicts[name] = a.to_dict()
            agg.entries += a.entries
            for ph in PHASES:
                agg.minutes[ph] += a.minutes[ph]
            agg.wall_min += a.wall_min
            agg.renders += a.renders
            agg.retries += a.retries
            agg.failed += a.failed
            agg.credits_known += a.credits_known
            agg.credits_unknown_entries += a.credits_unknown_entries
        out_projects[proj] = {"total": agg.to_dict(), "stages": stage_dicts}
    return {"schema": "avc.timing-summary/1", "files": files, "malformed_lines": malformed, "projects": out_projects, "total": total.to_dict()}


def format_summary(s: dict[str, Any]) -> str:
    lines = [f"ledger files: {s['files']}   malformed lines: {s['malformed_lines']}"]
    for proj, body in sorted(s["projects"].items()):
        t = body["total"]
        lines.append(f"\n== {proj}: {t['entries']} entries, active {t['active_min']} min, wait {t['wait_min']} min, wall {t['wall_min']} min, renders {t['renders']}, retries {t['retries']}")
        cred = f"{t['credits_known_sum']} (+{t['credits_unknown_entries']} entries with unknown credits)" if t["credits_unknown_entries"] else f"{t['credits_known_sum']}"
        lines.append(f"   credits: {cred}")
        for name, a in sorted(body["stages"].items()):
            m = a["minutes"]
            lines.append(
                f"   - {name:<14} n={a['entries']:<3} queue {m['queue_wait']:<7} setup {m['setup']:<7} load {m['load']:<7} run {m['run']:<7} qa {m['qa']:<7} review {m['review']:<7} renders {a['renders']} retries {a['retries']}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI used by ``python -m core ledger``."""
    import argparse

    ap = argparse.ArgumentParser(prog="python -m core ledger", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summarize", help="aggregate ledger files (usage: python -m core ledger summarize FILE... [--json])")
    s.add_argument("files", nargs="+")
    s.add_argument("--json", action="store_true")
    s.add_argument("--project")
    d = sub.add_parser("demo", help="write 3 sample lines (usage: python -m core ledger demo FILE)")
    d.add_argument("file")
    args = ap.parse_args(argv)
    if args.cmd == "summarize":
        missing = [f for f in args.files if not os.path.isfile(fs_path(f))]
        if missing:
            print(f"ledger file not found: {missing[0]}", flush=True)
            return 2
        summary = summarize(args.files, project=args.project)
        text = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else format_summary(summary)
        print(text)
        return 2 if summary["malformed_lines"] else 0
    led = Ledger(args.file, project="demo", attempt=1)
    with led.stage("render", tool="demo") as st:
        st.phase("setup")
        st.phase("run")
        st.renders += 1
    led.record("qa", tool="demo", qa_min=0.2)
    led.record("paid_generation", tool="demo", run_min=1.0, credits=None, note="credits unknown, not zero")
    print(f"wrote 3 lines to {args.file}")
    return 0

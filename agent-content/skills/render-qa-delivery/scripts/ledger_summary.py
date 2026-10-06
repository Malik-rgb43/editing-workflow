#!/usr/bin/env python3
"""ledger_summary.py - append to and summarise the per-project timing ledger (JSONL, stdlib only).

One line per stage attempt in _work/timing_ledger.jsonl. The summary counts FULL renders per round
(gate G4: one draft render per round, plus at most one delivery render after the notes page returned
`approved`) and sums minutes per stage, so a student can replace the modelled budget in pro-video-editor
with measured numbers.

Usage:
    python -X utf8 ledger_summary.py append LEDGER.jsonl --project P --round N --stage S --kind K
            --start 2026-10-02T10:00:00Z --end 2026-10-02T10:11:30Z
            [--queue-wait-min 0.5] [--setup-min 1] [--retries 0] [--credits null]
    python -X utf8 ledger_summary.py summary LEDGER.jsonl [--strict]
    python -X utf8 ledger_summary.py --self-check

kinds: render_full (the round's draft) | render_delivery (after `approved`) | render_range | check | snapshot | asr | matte | colour | review | authoring | qa | other
Record: {"project","round","stage","kind","start_utc","end_utc","run_min","queue_wait_min","setup_min","retries","credits"}
credits: null means unknown or not applicable, which is NOT the same as 0 (a paid action would carry a number).
Exit codes: summary --strict returns 1 if any round has more than one render_full or more than one
render_delivery, or a record is malformed;
append returns 2 on bad input.
"""
import datetime
import json
import os
import sys
import tempfile

KINDS = {"render_full", "render_delivery", "render_range", "check", "snapshot", "asr", "matte", "colour", "review",
         "authoring", "qa", "other"}


def _parse(ts):
    return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def make_record(project, rnd, stage, kind, start, end, queue_wait=None, setup=None, retries=0, credits=None):
    if kind not in KINDS:
        raise ValueError("kind must be one of: " + ", ".join(sorted(KINDS)))
    s, e = _parse(start), _parse(end)
    if e < s:
        raise ValueError("end before start")
    return {"project": project, "round": int(rnd), "stage": stage, "kind": kind, "start_utc": start, "end_utc": end,
            "run_min": round((e - s).total_seconds() / 60.0, 3), "queue_wait_min": queue_wait,
            "setup_min": setup, "retries": int(retries), "credits": credits}


def read(path):
    recs, bad = [], []
    if not os.path.exists(path):
        return recs, ["ledger file missing: " + path]
    with open(path, "r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                if r["kind"] not in KINDS or not isinstance(r["round"], int) or "run_min" not in r:
                    raise ValueError("bad fields")
                recs.append(r)
            except (ValueError, KeyError) as exc:
                bad.append("line %d: %s" % (n, exc))
    return recs, bad


def summarise(recs):
    rounds = {}
    for r in recs:
        d = rounds.setdefault((r["project"], r["round"]), {"render_full": 0, "render_delivery": 0, "render_range": 0, "min_by_kind": {}, "retries": 0,
                                                           "credits_unknown": 0, "credits_total": 0.0})
        d["min_by_kind"][r["kind"]] = round(d["min_by_kind"].get(r["kind"], 0.0) + (r.get("run_min") or 0.0), 3)
        d["retries"] += r.get("retries") or 0
        if r["kind"] in ("render_full", "render_delivery", "render_range"):
            d[r["kind"]] += 1
        if r.get("credits") is None:
            d["credits_unknown"] += 1
        else:
            d["credits_total"] += float(r["credits"])
    flagged = [{"project": p, "round": n, "full_renders": d["render_full"], "delivery_renders": d["render_delivery"]}
               for (p, n), d in sorted(rounds.items()) if d["render_full"] > 1 or d["render_delivery"] > 1]
    return rounds, flagged


def self_check():
    ok = True

    def expect(name, got, want):
        nonlocal ok
        ok = ok and got == want
        print("%s %-44s expected %-10s got %s" % ("ok  " if got == want else "FAIL", name, want, got))

    r1 = make_record("p", 1, "render", "render_full", "2026-10-02T10:00:00Z", "2026-10-02T10:11:30Z")
    expect("minutes computed from timestamps", r1["run_min"], 11.5)
    expect("credits default null (unknown, not 0)", r1["credits"], None)
    try:
        make_record("p", 1, "x", "render_everything", "2026-10-02T10:00:00Z", "2026-10-02T10:01:00Z")
        expect("unknown kind rejected", "accepted", "rejected")
    except ValueError:
        expect("unknown kind rejected", "rejected", "rejected")
    try:
        make_record("p", 1, "x", "check", "2026-10-02T10:05:00Z", "2026-10-02T10:01:00Z")
        expect("end before start rejected", "accepted", "rejected")
    except ValueError:
        expect("end before start rejected", "rejected", "rejected")
    recs = [make_record("p", 1, "render", "render_full", "2026-10-02T10:00:00Z", "2026-10-02T10:10:00Z"),
            make_record("p", 1, "range", "render_range", "2026-10-02T09:00:00Z", "2026-10-02T09:03:00Z"),
            make_record("p", 2, "render", "render_full", "2026-10-02T11:00:00Z", "2026-10-02T11:10:00Z"),
            make_record("p", 2, "render", "render_full", "2026-10-02T11:20:00Z", "2026-10-02T11:30:00Z")]
    recs.append(make_record("p", 1, "deliver", "render_delivery", "2026-10-02T10:30:00Z", "2026-10-02T10:41:00Z"))
    rounds, flagged = summarise(recs)
    expect("round 1: draft + delivery render, not flagged", [f for f in flagged if f["round"] == 1], [])
    expect("round 2: two full renders flagged", [f["full_renders"] for f in flagged if f["round"] == 2], [2])
    two_deliveries = recs[:2] + [make_record("p", 1, "deliver", "render_delivery", "2026-10-02T10:30:00Z", "2026-10-02T10:41:00Z")] * 2
    expect("two delivery renders in a round flagged", [f["delivery_renders"] for f in summarise(two_deliveries)[1]], [2])
    tmp = os.path.join(tempfile.mkdtemp(), "ledger.jsonl")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(recs[0]) + "\n" + "{not json}\n")
    got, bad = read(tmp)
    expect("malformed line is reported, not skipped silently", (len(got), len(bad)), (1, 1))
    expect("missing ledger is reported", len(read(tmp + ".nope")[1]), 1)
    print("SELF-CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if "--self-check" in argv:
        return self_check()
    if len(argv) < 2 or argv[0] not in ("append", "summary"):
        print(__doc__); return 2
    mode, path = argv[0], argv[1]
    if mode == "append":
        keys = {"--project": None, "--round": None, "--stage": None, "--kind": None, "--start": None, "--end": None,
                "--queue-wait-min": None, "--setup-min": None, "--retries": "0", "--credits": "null"}
        i = 2
        while i < len(argv):
            if argv[i] not in keys or i + 1 >= len(argv):
                print("bad argument", argv[i]); return 2
            keys[argv[i]] = argv[i + 1]; i += 2
        try:
            need = [keys[k] for k in ("--project", "--round", "--stage", "--kind", "--start", "--end")]
            if any(v is None for v in need):
                raise ValueError("missing required argument")
            cr = None if keys["--credits"] == "null" else float(keys["--credits"])
            rec = make_record(need[0], need[1], need[2], need[3], need[4], need[5],
                              float(keys["--queue-wait-min"]) if keys["--queue-wait-min"] else None,
                              float(keys["--setup-min"]) if keys["--setup-min"] else None,
                              int(keys["--retries"]), cr)
        except ValueError as exc:
            print("cannot append:", exc); return 2
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(json.dumps(rec, ensure_ascii=False))
        return 0
    strict = "--strict" in argv
    recs, bad = read(path)
    rounds, flagged = summarise(recs)
    out = {"records": len(recs), "malformed": bad,
           "rounds": [{"project": p, "round": n, "full_renders": d["render_full"], "delivery_renders": d["render_delivery"],
                       "range_renders": d["render_range"],
                       "minutes_by_kind": d["min_by_kind"], "retries": d["retries"],
                       "credits_unknown_lines": d["credits_unknown"], "credits_total_known": d["credits_total"]}
                      for (p, n), d in sorted(rounds.items())],
           "rounds_over_render_budget": flagged,
           "note": "credits null = unknown, not 0; minutes are measured wall time per stage attempt"}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if not recs:
        return 1
    return 1 if strict and (flagged or bad) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

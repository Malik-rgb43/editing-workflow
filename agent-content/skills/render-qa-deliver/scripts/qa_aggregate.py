#!/usr/bin/env python3
"""qa_aggregate.py - fail-closed aggregation of QA envelopes into one delivery verdict (stdlib only).

Reference implementation of the `qa delivery` gate. It never decodes video: it judges the evidence the
QA tools produced and refuses to let missing, stale, partial or foreign evidence pass.

Usage:
    python -X utf8 qa_aggregate.py bundle.json [--required frame_qa,loudness,caption_qa,motion_qa]
            [--exemptions exemptions.json] [--lufs -14 --lufs-tol 0.5 --tp -1.0] [--json verdict.json]
    python -X utf8 qa_aggregate.py --self-check

bundle.json:
    {"final": {"path": "final/x_9x16.mp4", "sha256": "<hex>", "mtime_epoch": 1760000300},
     "render_start_epoch": 1760000000, "last_patch_epoch": 1759999000,
     "envelopes": [
        {"tool": "frame_qa", "status": "PASS", "input_sha256": "<hex>", "decoded_frames": 1350,
         "expected_frames": 1350, "findings": []},
        {"tool": "loudness", "integrated_lufs": -14.1, "true_peak_dbtp": -1.4, "input_sha256": "<hex>"}]}

exemptions.json (time-bounded, tied to an approved PROMPT.md row - blanket exemptions are rejected):
    [{"tool": "frame_qa", "t0": 0.0, "t1": 0.1, "reason": "approved intentional black", "prompt_ref": "L12"}]

Rules (house preset v1 numbers for loudness, overridable with flags; decision default Q5):
  * every required tool must be present: absent -> BLOCKED (not_run), never PASS;
  * an envelope passes only if status == PASS, decoded_frames == expected_frames > 0 and its
    input_sha256 equals the final file's sha256;
  * the final file must be newer than render_start_epoch and last_patch_epoch (stale-file guard);
  * a FAIL whose findings all fall inside valid exemption windows becomes PASS_EXEMPT and is listed;
  * loudness: integrated within target +- tolerance and true peak <= limit; missing numbers -> BLOCKED.
Exit codes: 0 PASS, 1 FAIL or INSUFFICIENT_EVIDENCE, 2 usage error.
"""
import json
import sys

VERSION = "0.1.0"
DEFAULT_REQUIRED = ("frame_qa", "loudness")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_exemptions(ex):
    bad = []
    for i, e in enumerate(ex or []):
        if not (_num(e.get("t0")) and _num(e.get("t1")) and e["t0"] < e["t1"]
                and e.get("tool") and e.get("reason") and e.get("prompt_ref")):
            bad.append("exemption %d: needs tool, numeric t0 < t1, reason and prompt_ref (blanket exemptions rejected)" % i)
    return bad


def _exempt(tool, f, ex):
    t0, t1 = f.get("t0"), f.get("t1", f.get("t0"))
    if not (_num(t0) and _num(t1)):
        return False
    return any(e["tool"] == tool and e["t0"] <= t0 and t1 <= e["t1"] for e in ex)


def judge(bundle, required=DEFAULT_REQUIRED, exemptions=None, lufs=-14.0, tol=0.5, tp=-1.0):
    ex = exemptions or []
    rows = []
    problems = validate_exemptions(ex)
    if problems:
        return {"tool": "qa_aggregate", "version": VERSION, "status": "INSUFFICIENT_EVIDENCE",
                "reason": "; ".join(problems), "rows": rows}
    final = bundle.get("final") or {}
    sha = final.get("sha256")
    if not sha:
        return {"tool": "qa_aggregate", "version": VERSION, "status": "INSUFFICIENT_EVIDENCE",
                "reason": "final.sha256 missing: cannot bind evidence to a file", "rows": rows}
    stale = None
    m = final.get("mtime_epoch")
    for key in ("render_start_epoch", "last_patch_epoch"):
        if _num(bundle.get(key)) and _num(m) and m < bundle[key]:
            stale = "final file is older than %s (stale-file guard)" % key
        elif not _num(m) or not _num(bundle.get(key)):
            stale = stale or "missing mtime or %s: freshness cannot be proven" % key
    envs = {e.get("tool"): e for e in bundle.get("envelopes", [])}
    for tool in required:
        e = envs.get(tool)
        if e is None:
            rows.append({"tool": tool, "state": "blocked", "reason": "not_run: no envelope"})
            continue
        if e.get("input_sha256") != sha:
            rows.append({"tool": tool, "state": "blocked", "reason": "ran on a different file (sha256 mismatch)"})
            continue
        if tool == "loudness":
            li, tpk = e.get("integrated_lufs"), e.get("true_peak_dbtp")
            if not (_num(li) and _num(tpk)):
                rows.append({"tool": tool, "state": "blocked", "reason": "loudness numbers missing"})
            elif abs(li - lufs) <= tol and tpk <= tp:
                rows.append({"tool": tool, "state": "pass", "reason": "%.1f LUFS, TP %.1f dBTP (target %.1f +-%.1f, TP <= %.1f)" % (li, tpk, lufs, tol, tp)})
            else:
                rows.append({"tool": tool, "state": "fail", "reason": "%.1f LUFS, TP %.1f dBTP outside %.1f +-%.1f / TP <= %.1f" % (li, tpk, lufs, tol, tp)})
            continue
        dec, exp = e.get("decoded_frames"), e.get("expected_frames")
        status = e.get("status")
        if status not in ("PASS", "FAIL", "INSUFFICIENT_EVIDENCE"):
            rows.append({"tool": tool, "state": "blocked", "reason": "unknown status %r" % status})
        elif status == "INSUFFICIENT_EVIDENCE":
            rows.append({"tool": tool, "state": "blocked", "reason": "tool reports INSUFFICIENT_EVIDENCE"})
        elif not (_num(dec) and _num(exp) and exp > 0 and dec == exp):
            rows.append({"tool": tool, "state": "blocked", "reason": "coverage %s/%s frames: not the whole file" % (dec, exp)})
        elif status == "PASS":
            rows.append({"tool": tool, "state": "pass", "reason": "%d/%d frames" % (dec, exp)})
        else:
            fs = e.get("findings") or []
            if fs and all(_exempt(tool, f, ex) for f in fs):
                rows.append({"tool": tool, "state": "pass", "reason": "%d finding(s), all inside approved exemptions" % len(fs), "exempt": True})
            else:
                rows.append({"tool": tool, "state": "fail", "reason": "%d finding(s), %d not exempt" % (len(fs), sum(1 for f in fs if not _exempt(tool, f, ex)))})
    if stale:
        rows.append({"tool": "freshness", "state": "blocked", "reason": stale})
    states = [r["state"] for r in rows]
    status = "FAIL" if "fail" in states else ("INSUFFICIENT_EVIDENCE" if "blocked" in states else "PASS")
    stmt = ("File %s sha256 %s: %d required check(s) %s. Pass = every required test ran on the whole file."
            % (final.get("path", "?"), sha[:12], len(rows), "all ran" if status == "PASS" else "NOT all passed"))
    return {"tool": "qa_aggregate", "version": VERSION, "status": status, "rows": rows, "coverage_statement": stmt}


def _bundle():
    sha = "ab" * 32
    return {"final": {"path": "final/x_9x16.mp4", "sha256": sha, "mtime_epoch": 1000},
            "render_start_epoch": 900, "last_patch_epoch": 800,
            "envelopes": [
                {"tool": "frame_qa", "status": "PASS", "input_sha256": sha, "decoded_frames": 1350, "expected_frames": 1350, "findings": []},
                {"tool": "caption_qa", "status": "PASS", "input_sha256": sha, "decoded_frames": 1350, "expected_frames": 1350, "findings": []},
                {"tool": "loudness", "integrated_lufs": -14.1, "true_peak_dbtp": -1.4, "input_sha256": sha}]}


def self_check():
    import copy
    ok = True

    def expect(name, got, want):
        nonlocal ok
        ok = ok and got == want
        print("%s %-42s expected %-22s got %s" % ("ok  " if got == want else "FAIL", name, want, got))

    req = ("frame_qa", "caption_qa", "loudness")
    b = _bundle()
    expect("positive control", judge(b, req)["status"], "PASS")
    x = copy.deepcopy(b); x["envelopes"] = [e for e in x["envelopes"] if e["tool"] != "caption_qa"]
    expect("required tool missing (not_run)", judge(x, req)["status"], "INSUFFICIENT_EVIDENCE")
    x = copy.deepcopy(b); x["envelopes"][0]["decoded_frames"] = 0; x["envelopes"][0]["expected_frames"] = 0
    expect("zero-frame pass is not a pass", judge(x, req)["status"], "INSUFFICIENT_EVIDENCE")
    x = copy.deepcopy(b); x["envelopes"][0]["decoded_frames"] = 900
    expect("partial coverage", judge(x, req)["status"], "INSUFFICIENT_EVIDENCE")
    x = copy.deepcopy(b); x["envelopes"][1]["input_sha256"] = "cd" * 32
    expect("QA ran on a different file", judge(x, req)["status"], "INSUFFICIENT_EVIDENCE")
    x = copy.deepcopy(b); x["final"]["mtime_epoch"] = 700
    expect("stale final file", judge(x, req)["status"], "INSUFFICIENT_EVIDENCE")
    x = copy.deepcopy(b); x["envelopes"][2]["integrated_lufs"] = -17.0
    expect("loudness -17 LUFS", judge(x, req)["status"], "FAIL")
    x = copy.deepcopy(b); x["envelopes"][2]["true_peak_dbtp"] = 0.0
    expect("true peak 0.0 dBTP (numeric zero is a value)", judge(x, req)["status"], "FAIL")
    x = copy.deepcopy(b); x["envelopes"][2]["true_peak_dbtp"] = None
    expect("true peak missing", judge(x, req)["status"], "INSUFFICIENT_EVIDENCE")
    x = copy.deepcopy(b)
    x["envelopes"][0].update(status="FAIL", findings=[{"t0": 0.0, "t1": 0.1, "kind": "black"}])
    expect("flag without exemption", judge(x, req)["status"], "FAIL")
    ex = [{"tool": "frame_qa", "t0": 0.0, "t1": 0.2, "reason": "approved black", "prompt_ref": "L12"}]
    expect("flag inside a time-bounded exemption", judge(x, req, ex)["status"], "PASS")
    expect("blanket exemption rejected", judge(x, req, [{"tool": "frame_qa", "reason": "ignore"}])["status"], "INSUFFICIENT_EVIDENCE")
    ex2 = [{"tool": "frame_qa", "t0": 5.0, "t1": 6.0, "reason": "approved", "prompt_ref": "L3"}]
    expect("exemption window does not cover the flag", judge(x, req, ex2)["status"], "FAIL")
    print("SELF-CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if "--self-check" in argv:
        return self_check()
    if not argv or argv[0].startswith("-"):
        print(__doc__); return 2
    opts = {"--required": ",".join(DEFAULT_REQUIRED), "--exemptions": None, "--lufs": "-14", "--lufs-tol": "0.5",
            "--tp": "-1.0", "--json": None}
    i = 1
    while i < len(argv):
        if argv[i] not in opts or i + 1 >= len(argv):
            print("bad argument", argv[i]); return 2
        opts[argv[i]] = argv[i + 1]; i += 2
    try:
        with open(argv[0], "r", encoding="utf-8") as fh:
            bundle = json.load(fh)
        ex = None
        if opts["--exemptions"]:
            with open(opts["--exemptions"], "r", encoding="utf-8") as fh:
                ex = json.load(fh)
        verdict = judge(bundle, tuple(x for x in opts["--required"].split(",") if x), ex,
                        float(opts["--lufs"]), float(opts["--lufs-tol"]), float(opts["--tp"]))
    except (OSError, ValueError) as exc:
        verdict = {"tool": "qa_aggregate", "version": VERSION, "status": "INSUFFICIENT_EVIDENCE",
                   "reason": "cannot evaluate: %s" % exc, "rows": []}
    text = json.dumps(verdict, indent=2, ensure_ascii=False)
    print(text)
    if opts["--json"]:
        with open(opts["--json"], "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if verdict["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

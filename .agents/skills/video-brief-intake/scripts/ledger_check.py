#!/usr/bin/env python3
"""Check a Concept Ledger for completeness, traceability and measurability (gates G1, G2).

Usage:
  python ledger_check.py hf/PROMPT.md --source _work/intake/INTAKE_LOG.md [--footage] [--variants] [--prompt hf/PROMPT.md]
                         [--waive "clause text"]... [--json]
  python ledger_check.py hf/PROMPT.md --structure-only        # structure only; NOT a G1 pass
  python ledger_check.py --self-check                         # built-in tests

Status and exit code (fail closed):
  PASS 0                 no errors, source given, every concrete source clause covered
  STRUCTURE_ONLY 0       no errors but no source given: coverage is `not_run`, do not call it G1 pass
  FAIL 1                 at least one error finding
  INSUFFICIENT_EVIDENCE 2  empty or unreadable ledger, or no --source without --structure-only
  NEEDS_REVIEW 3         no errors but source clauses that look concrete have no ledger row;
                         add rows or waive them explicitly with --waive

Ledger = the first argument: a file holding the `<ledger>` block (normally hf/PROMPT.md; a standalone
ledger file also works). Format: references/ledger-template.md. Blocking rows: FMT LEN TON BAR CTA CAP FILE,
plus STR and COLOR with --footage, plus VAR with --variants (gate G0 of the intake playbook). FILE is never asked:
a D row (the default name, said back) satisfies it. A D row counts only when the log shows the defaults were said
back ("Defaults taken: ...", "continue") or the user gave full control ("you decide", "אתה מחליט").
Source = _work/intake/INTAKE_LOG.md: the user's words, one clause per line; lines starting with "Q:" are
the agent's questions (counted per "## Round N", max 4). A row is struck when its status starts with
"struck" or its spec starts with "~~".
Heuristics (coverage, compound claims, measurability) never turn into PASS on their own judgement:
they produce review findings for a human or the agent to resolve.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

VERSION = "0.1.0"
DIMS = {
    "FMT", "LEN", "STR", "TON", "HOOK", "LOOK", "TYPE", "MOT", "3D", "BROLL", "CAP", "MUS", "SFX",
    "VO", "CTA", "FILE", "BAR", "DUE", "VAR", "BRAND", "COLOR", "LAY", "TRN", "SHOT",
    "LOUD", "REF", "RIGHTS", "AIDISC", "CONSENT",
}
BLOCKING = ["FMT", "LEN", "TON", "BAR", "CTA", "CAP", "FILE"]
BLOCKING_FOOTAGE = ["STR", "COLOR"]
BLOCKING_VARIANTS = ["VAR"]
SRC = {"U", "R", "D", "A"}
STATUS_RE = re.compile(r"^(locked|default|proposed|struck by L\d{2,3})$", re.I)
ID_RE = re.compile(r"^L\d{2,3}$")
QUOTE_RE = re.compile(r'["“«״]\s*(.+?)\s*["”»״]')
TIME_RE = re.compile(
    r"(\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\s*(?:s|sec|seconds?|שנ)|\bf\d+|\d+(?:\.\d+)?\s*(?:s|sec|seconds?)\b|"
    r"\bseconds?\s*\d|שני[י]?ה\s*\d)", re.I)
VERIFY_RE = re.compile(r"(frame|strip|sheet|ffprobe|snapshot|ocr|grep|ls |probe|measure|pixel|פריים|בדיק)", re.I)
CONCRETE_RE = re.compile(
    r"(\d|#[0-9a-f]{3,6}\b|\bmore\b|\bless\b|bigger|larger|higher|lower|faster|slower|\bmust\b|\bshould\b|\bneed|"
    r"without|\bno\b|יותר|פחות|גדול|קטן|"
    r"חייב|צריך|בלי|תוסיף)", re.I)
CONTINUE_RE = re.compile(r"(defaults taken|decisions taken|continue|you decide|full control|תמשיך|לקחתי ברירות|אתה מחליט|שליטה מלאה)", re.I)
NIQQUD = re.compile("[֑-ׇ]")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).casefold()
    s = NIQQUD.sub("", s)
    s = re.sub(r"[–—\-]+", " ", s)
    s = re.sub(r"[^\w#.:%\s]", " ", s)
    s = re.sub(r"(?<!\d):|:(?!\d)", " ", s)
    return re.sub(r"\s+", " ", s).strip()


STOP = set("the a an of to in on at for and or is are be it its my me we i you want make add with this that "
           "של את על עם אני רוצה הוא זה".split())


def tokens(s: str) -> set[str]:
    return {t for t in norm(s).split() if len(t) >= 2 and t not in STOP}


def parse_ledger(text: str) -> tuple[list[dict], list[str]]:
    m = re.search(r"<ledger>(.*?)</ledger>", text, re.S | re.I)
    if m:
        text = m.group(1)
    rows, errors, cols = [], [], None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        if cells and cells[0].lower() == "id":
            names = [c.lower() for c in cells]
            def find(prefix: str) -> int:
                for i, n in enumerate(names):
                    if n.startswith(prefix):
                        return i
                return -1
            cols = {k: find(k) for k in ("id", "dim", "said", "spec", "where", "acceptance", "src", "status")}
            missing = [k for k, v in cols.items() if v < 0]
            if missing:
                errors.append("header lacks columns: " + ", ".join(missing))
                cols = None
            continue
        if cols is None:
            continue
        if len(cells) <= max(cols.values()):
            errors.append(f"row has too few cells: {line[:60]}")
            continue
        rows.append({k: cells[i] for k, i in cols.items()})
    return rows, errors


def said_core(cell: str) -> str:
    m = QUOTE_RE.search(cell)
    if m:
        return m.group(1)
    return re.split(r"\s+\(", cell)[0].strip(" -–")


def source_clauses(text: str) -> tuple[list[str], dict[int, int], str]:
    """Return user clauses, questions-per-round, and the user-text blob."""
    clauses, qpr, rnd, user_lines = [], {}, 0, []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("<!--"):
            continue
        m = re.match(r"^##\s+(?:Round|סבב)\s+(\d+)", line, re.I)
        if m:
            rnd = int(m.group(1))
            continue
        if line.startswith("#"):
            continue
        if re.match(r"^(Q|AGENT)\s*:", line, re.I):
            qpr[rnd] = qpr.get(rnd, 0) + 1
            continue
        user_lines.append(line)
        for part in re.split(r"[.;!?؛]+\s+|\s+[-•*]\s+|^[-•*]\s+|^\d+[.)]\s+", line):
            part = part.strip(" -•*,")
            if len(part) >= 4:
                clauses.append(part)
    return clauses, qpr, "\n".join(user_lines)


def is_struck(r: dict) -> bool:
    return r["status"].lower().startswith("struck") or r["spec"].lstrip().startswith("~~")


def run(ledger_path: Path | None, ledger_text: str | None, source_texts: list[str], footage: bool,
        prompt_text: str | None, waive: list[str], structure_only: bool, variants: bool = False) -> dict:
    findings: list[dict] = []

    def add(sev: str, code: str, row: str, msg: str) -> None:
        findings.append({"severity": sev, "code": code, "id": row, "message": msg})

    rows, perr = parse_ledger(ledger_text or "")
    for e in perr:
        add("error", "malformed_table", "-", e)
    result = {"tool": "ledger_check", "version": VERSION, "rows": len(rows), "findings": findings,
              "coverage": {"status": "not_run"}, "blocking": {}}
    if not rows:
        add("error", "empty_ledger", "-", "no ledger rows parsed")
        result["status"] = "INSUFFICIENT_EVIDENCE"
        return result

    source_blob = "\n".join(source_texts)
    clauses, qpr, user_blob = ([], {}, "")
    for t in source_texts:
        c, q, u = source_clauses(t)
        clauses += c
        for k, v in q.items():
            qpr[k] = qpr.get(k, 0) + v
        user_blob += "\n" + u
    nuser = norm(user_blob)
    have_source = bool(source_texts) and bool(nuser)
    continue_marker = bool(CONTINUE_RE.search(user_blob))

    seen: dict[str, dict] = {}
    for r in rows:
        rid = r["id"]
        if not ID_RE.match(rid):
            add("error", "bad_id", rid, "id must look like L01")
        if rid in seen:
            add("error", "duplicate_id", rid, "id reused")
        seen[rid] = r
        dim, src, status = r["dim"].upper(), r["src"].upper(), r["status"]
        if dim not in DIMS:
            add("error", "bad_dim", rid, f"unknown dim {r['dim']!r}")
        if src not in SRC:
            add("error", "bad_src", rid, f"src must be one of U R D A, got {r['src']!r}")
        if not STATUS_RE.match(status) and not r["spec"].lstrip().startswith("~~"):
            add("error", "bad_status", rid, f"status {status!r}")
    for r in rows:
        rid, status = r["id"], r["status"].lower()
        if r["spec"].lstrip().startswith("~~"):
            continue  # struck in place with the time (concept-ledger technique); the new row carries the claim
        m = re.match(r"struck by (L\d{2,3})", status, re.I)
        if m:
            tgt = seen.get(m.group(1).upper())
            if tgt is None or is_struck(tgt):
                add("error", "bad_strike", rid, f"struck by {m.group(1)}, which is missing or itself struck")
            continue
        dim, src = r["dim"].upper(), r["src"].upper()
        live = status in ("locked", "default")
        if live and (not r["spec"] or r["spec"] == "-"):
            add("error", "no_spec", rid, "locked/default row without a measurable spec")
        if live and (not r["acceptance"] or r["acceptance"] == "-"):
            add("error", "no_acceptance", rid, "locked/default row without an acceptance check")
        if live and dim in ("LEN", "FMT") and not re.search(r"\d", r["spec"]):
            add("error", "not_measurable", rid, f"{dim} spec needs a number or ratio")
        if live and dim == "FILE" and "." not in r["spec"]:
            add("error", "not_measurable", rid, "FILE spec needs a file name with extension")
        if live and dim not in ("LEN", "FMT", "FILE") and not re.search(
                r"(\d|#[0-9a-f]{3,6}|\.\w{2,4}\b|whole|כל)", r["spec"] + " " + r["where"], re.I):
            add("review", "maybe_not_measurable", rid, "no number, hex, file name or range in spec/where")
        if src == "U":
            core = said_core(r["said"])
            if not core or core == "-":
                add("error", "no_said", rid, "src U needs the user's verbatim words in `said`")
            elif have_source and norm(core) not in nuser:
                add("error", "said_not_in_source", rid, f"quoted words not found in the source log: {core[:50]!r}")
            elif not have_source:
                add("review", "source_not_checked", rid, "no source log: traceability not verified")
            if re.search(r"\s\band\b\s", core, re.I) or (len(core) > 25 and re.search(r"\sו[א-ת]{2,}", core)):
                add("review", "maybe_compound", rid, "said may hold two claims; split into two rows")
        if src == "D" and not continue_marker and have_source:
            add("error", "default_not_shown", rid, "default row but the log has no 'defaults taken / continue' line")
        said_t, spec_t = r["said"], r["where"]
        if dim not in ("LEN", "DUE", "FILE") and src == "U" and TIME_RE.search(said_t):
            if not re.search(r"\d", spec_t) and spec_t.lower() != "whole":
                add("error", "timed_without_range", rid, "names a time but `where / when` has no range")
            if live and not VERIFY_RE.search(r["acceptance"]):
                add("error", "timed_without_check", rid, "timed item needs a frame/strip/probe style check")

    live_rows = [r for r in rows if r["status"].lower() in ("locked", "default") and not is_struck(r)]
    for dim in BLOCKING + (BLOCKING_FOOTAGE if footage else []) + (BLOCKING_VARIANTS if variants else []):
        ok = any(r["dim"].upper() == dim and r["src"].upper() in ("U", "R", "A") for r in live_rows) or any(
            r["dim"].upper() == dim and r["src"].upper() == "D" for r in live_rows) and continue_marker
        result["blocking"][dim] = "ok" if ok else "missing"
        if not ok:
            add("error", "blocking_dim_missing", dim, f"{dim} must come from the user (U/R/approved A) or a shown default")

    for rnd, n in sorted(qpr.items()):
        if n > 4:
            add("error", "too_many_questions", f"round {rnd}", f"{n} questions in one round (max 4)")

    if prompt_text is not None:
        counts = {r["id"]: len(re.findall(re.escape(r["id"]) + r"(?!\d)", prompt_text))
                  for r in rows if not is_struck(r)}
        for rid, n in counts.items():
            if n < 2:
                add("error", "id_not_cited", rid, f"appears {n}x in PROMPT (needs ledger + structure = 2)")
        for pid in sorted(set(re.findall(r"\bL\d{2,3}\b", prompt_text)) - set(seen)):
            add("review", "unknown_id_in_prompt", pid, "PROMPT cites an id that is not in the ledger")

    if have_source:
        concrete = [c for c in clauses if CONCRETE_RE.search(c)]
        ledger_text_n = [norm(r["said"] + " " + r["spec"]) for r in rows if not is_struck(r)]
        ledger_tok = [tokens(t) for t in ledger_text_n]
        said_n = [n for n in (norm(said_core(r["said"])) for r in rows if not is_struck(r)) if len(n) >= 3]
        uncovered = []
        for c in concrete:
            cn, ct = norm(c), tokens(c)
            if any(w and norm(w) in cn for w in waive):
                continue
            union = set().union(*[lk for lk in ledger_tok if len(ct & lk) >= 2]) if ct else set()
            hit = any(sn in cn for sn in said_n) or any(cn in lt or (len(lt) > 3 and lt in cn) for lt in ledger_text_n) or (
                bool(ct) and len(ct & union) / len(ct) >= 0.6)
            if not hit:
                uncovered.append(c)
        result["coverage"] = {"status": "checked", "clauses": len(clauses), "concrete": len(concrete),
                              "uncovered": uncovered}
        for c in uncovered:
            add("review", "possibly_uncovered", "-", f"no ledger row matches: {c[:80]!r}")
    errors = [f for f in findings if f["severity"] == "error"]
    unc = bool(result["coverage"].get("uncovered"))
    if errors:
        result["status"] = "FAIL"
    elif structure_only:
        result["status"] = "STRUCTURE_ONLY"
    elif not have_source:
        result["status"] = "INSUFFICIENT_EVIDENCE"
        add("error", "no_source", "-", "no source log: pass --source or --structure-only")
    elif unc:
        result["status"] = "NEEDS_REVIEW"
    else:
        result["status"] = "PASS"
    return result


EXIT = {"PASS": 0, "STRUCTURE_ONLY": 0, "FAIL": 1, "INSUFFICIENT_EVIDENCE": 2, "NEEDS_REVIEW": 3}

_HEAD = "| ID | dim | said (verbatim) | spec (measurable) | where / when | acceptance check | src | status |\n|---|---|---|---|---|---|---|---|\n"
_BRIEF = """## Round 1
Q: Which platform and length?
I want a 45 second ad for Instagram Reels in 9:16
film burn at second 1-2
the globe bigger
the person higher
the tone is energetic premium
premium quality bar
CTA: book a free call
captions in English
call the final file clinic_reel_9x16.mp4
"""
_GOOD = _HEAD + "\n".join([
    '| L01 | FMT | "Instagram Reels in 9:16" | 9:16 1080x1920 | whole | ffprobe size | U | locked |',
    '| L02 | LEN | "45 second" | 45.0 s +-0.1 | whole | ffprobe duration | U | locked |',
    '| L03 | TRN | "film burn at second 1-2" | user burn file, full frame | 1.00-2.00 s (f30-60) | frame strip f28-62 | U | locked |',
    '| L04 | LAY | "the globe bigger" | globe 620 -> 780 px | 12.4-16.0 s | snapshot 14.0 s bbox | U | locked |',
    '| L05 | LAY | "the person higher" | head top y 420 -> 300 | 12.4-16.0 s | snapshot 14.0 s face box | U | locked |',
    '| L06 | TON | "energetic premium" | energetic-premium register | whole | critic note | U | locked |',
    '| L07 | BAR | "premium quality bar" | premium: beat every 3-6 s | whole | rubric >= 4.0 | U | locked |',
    '| L08 | CTA | "book a free call" | end card 2.5 s, exact line | 42.5-45.0 s | OCR end card | U | locked |',
    '| L09 | FILE | "clinic_reel_9x16.mp4" | clinic_reel_9x16.mp4 | whole | ls final folder | U | locked |',
    '| L11 | CAP | "captions in English" | English captions, word groups | whole | caption_qa on the final | U | locked |',
]) + "\n"


def _self_check() -> int:
    fails: list[str] = []

    def expect(name: str, res: dict, status: str, code: str | None = None) -> None:
        codes = {f["code"] for f in res["findings"]}
        if res["status"] != status or (code and code not in codes):
            fails.append(f"{name}: got {res['status']} {sorted(codes)}, wanted {status} {code or ''}")

    def go(ledger: str, src: str | None = _BRIEF, **kw) -> dict:
        return run(None, ledger, [src] if src else [], kw.pop("footage", False), kw.pop("prompt", None),
                   kw.pop("waive", []), kw.pop("structure_only", False), kw.pop("variants", False))

    expect("good ledger passes", go(_GOOD), "PASS")
    expect("structure only is labelled", go(_GOOD, src=None, structure_only=True), "STRUCTURE_ONLY")
    expect("no source is insufficient", go(_GOOD, src=None), "INSUFFICIENT_EVIDENCE", "no_source")
    expect("empty ledger", go(_HEAD), "INSUFFICIENT_EVIDENCE", "empty_ledger")
    no_cta = "\n".join(l for l in _GOOD.splitlines() if "| CTA |" not in l)
    expect("missing blocking dim", go(no_cta), "FAIL", "blocking_dim_missing")
    no_file = "\n".join(l for l in _GOOD.splitlines() if "| FILE |" not in l)
    expect("FILE is blocking", go(no_file), "FAIL", "blocking_dim_missing")
    no_cap = "\n".join(l for l in _GOOD.splitlines() if "| CAP |" not in l)
    expect("CAP (caption language) is blocking", go(no_cap), "FAIL", "blocking_dim_missing")
    file_d = _GOOD.replace('| L09 | FILE | "clinic_reel_9x16.mp4" | clinic_reel_9x16.mp4 | whole | ls final folder | U |', '| L09 | FILE | - | clinic_reel_9x16.mp4 | whole | ls final folder | D |')
    expect("FILE as a default needs it said back", go(file_d), "FAIL", "default_not_shown")
    expect("FILE as a said-back default passes", go(file_d, src=_BRIEF + "Defaults taken: file clinic_reel_9x16.mp4\n"), "PASS")
    expect("full control makes D rows the user's choice", go(file_d, src=_BRIEF + "you decide\n"), "PASS")
    expect("variants need a VAR row", go(_GOOD, variants=True), "FAIL", "blocking_dim_missing")
    invented = _GOOD.replace('"the globe bigger"', '"the globe much bigger"')
    expect("invented said", go(invented), "FAIL", "said_not_in_source")
    notime = _GOOD.replace("1.00-2.00 s (f30-60)", "-")
    expect("timed item needs a range", go(notime), "FAIL", "timed_without_range")
    nocheck = _GOOD.replace("frame strip f28-62", "looks fine")
    expect("timed item needs a check", go(nocheck), "FAIL", "timed_without_check")
    expect("footage needs STR and COLOR", go(_GOOD, footage=True), "FAIL", "blocking_dim_missing")
    brief2 = _BRIEF + "the logo must glow at the end\n"
    r = go(_GOOD, src=brief2)
    expect("uncovered clause needs review", r, "NEEDS_REVIEW", "possibly_uncovered")
    expect("waiver clears it", go(_GOOD, src=brief2, waive=["the logo must glow at the end"]), "PASS")
    dflt = _GOOD.replace("| 45.0 s +-0.1 | whole | ffprobe duration | U |", "| 45.0 s +-0.1 | whole | ffprobe duration | D |")
    expect("default needs a shown marker", go(dflt), "FAIL", "default_not_shown")
    expect("default with continue marker ok", go(dflt, src=_BRIEF + "continue\n"), "PASS")
    many_q = "## Round 1\n" + "".join(f"Q: q{i}?\n" for i in range(5)) + _BRIEF.split("\n", 1)[1]
    expect("max 4 questions per round", go(_GOOD, src=many_q), "FAIL", "too_many_questions")
    dup = _GOOD + '| L08 | CTA | "book a free call" | x 1 | whole | ocr | U | locked |\n'
    expect("duplicate id", go(dup), "FAIL", "duplicate_id")
    struck = _GOOD.replace("| 45.0 s +-0.1 | whole | ffprobe duration | U | locked |", "| 45.0 s +-0.1 | whole | ffprobe duration | U | struck by L10 |")
    struck += '| L10 | LEN | "45 second" | 45.0 s +-0.1 | whole | ffprobe duration | U | locked |\n'
    expect("strike keeps coverage through the new row", go(struck), "PASS")
    inplace = _GOOD.replace("| 45.0 s +-0.1 | whole | ffprobe duration | U | locked |", "| ~~30 s~~ -> 45.0 s, 09:05 | whole | ffprobe duration | U | locked |")
    expect("in-place strike with ~~ keeps the row readable", go(inplace + '| L10 | LEN | "45 second" | 45.0 s +-0.1 | whole | ffprobe duration | U | locked |\n'), "PASS")
    ids = [f"L0{i}" for i in range(1, 10)] + ["L11"]
    prompt_ok = "<ledger>\n" + "\n".join(ids) + "\n</ledger>\n" + " ".join(ids)
    expect("every id cited twice", go(_GOOD, prompt=prompt_ok), "PASS")
    expect("uncited id fails", go(_GOOD, prompt="L01 L01 L02 L02"), "FAIL", "id_not_cited")
    in_prompt = "<ledger>\n" + _GOOD + "</ledger>\n<structure>" + " ".join(f"L0{i}" for i in range(1, 10)) + "</structure>"
    expect("a <ledger> block inside PROMPT.md is read", go(in_prompt), "PASS")
    hebrew_src = '## Round 1\n"שהסרטון יהיה 45"\n'
    hebrew_led = _HEAD + '| L01 | LEN | "שהסרטון יהיה 45" (make the video 45) | 45.0 s | whole | ffprobe | U | locked |\n'
    res = go(hebrew_led, src=hebrew_src)
    if any(f["code"] == "said_not_in_source" for f in res["findings"]):
        fails.append("hebrew quote should match the source")
    for f in fails:
        print("FAIL:", f)
    print("self-check:", "FAILED" if fails else "ok")
    return 1 if fails else 0


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return _self_check()
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    ledger = Path(argv[0])
    sources, prompt, waive, footage, structure_only, as_json, variants = [], None, [], False, False, False, False
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--source":
            sources.append(argv[i + 1]); i += 2
        elif a == "--prompt":
            prompt = argv[i + 1]; i += 2
        elif a == "--waive":
            waive.append(argv[i + 1]); i += 2
        elif a == "--footage":
            footage = True; i += 1
        elif a == "--variants":
            variants = True; i += 1
        elif a == "--structure-only":
            structure_only = True; i += 1
        elif a == "--json":
            as_json = True; i += 1
        else:
            print("unknown option", a); return 2
    try:
        ledger_text = ledger.read_text(encoding="utf-8")
        src_texts = [Path(s).read_text(encoding="utf-8") for s in sources]
        prompt_text = Path(prompt).read_text(encoding="utf-8") if prompt else None
    except OSError as exc:
        print(json.dumps({"tool": "ledger_check", "status": "INSUFFICIENT_EVIDENCE", "reason": str(exc)}))
        return 2
    res = run(ledger, ledger_text, src_texts, footage, prompt_text, waive, structure_only, variants)
    res["exit"] = EXIT[res["status"]]
    if as_json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"ledger_check {VERSION}: {res['status']}  rows={res['rows']}  coverage={res['coverage'].get('status')}")
        for f in res["findings"]:
            print(f"  [{f['severity']}] {f['code']} {f['id']}: {f['message']}")
        if res["status"] == "STRUCTURE_ONLY":
            print("  note: structure only; traceability and coverage were NOT checked")
    return EXIT[res["status"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

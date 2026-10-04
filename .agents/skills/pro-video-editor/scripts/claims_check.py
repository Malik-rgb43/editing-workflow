#!/usr/bin/env python3
"""claims_check.py - the testimonial honesty gate: consent record + claims table with source timestamps.

It checks what a script CAN check (consent fields, timestamps, quotes derived in order from the source
words, hedges/negations/limiters kept, no number introduced, on-screen numbers actually spoken, proof
values equal to spoken values, reordering logged, no synthetic speaker, AI B-roll disclosed). It cannot
judge meaning: a human still reads the cut. A PASS means "no mechanical violation found", not "honest".

Usage:
  python claims_check.py <claims.json> [--root DIR] [--intended-use paid_ad|organic|website] [--json]
  python claims_check.py --self-check

Input (schema_version 1.0.0; field guide in references/honesty-and-rights.md):
  consent{present, signed_date, uses[], platforms[], evidence_file, withdrawal_contact, bystanders, cloud_processing_ok},
  cloud_steps_used[], source{file, duration_s}, synthetic{speaker_voice, speaker_face, ai_broll, ai_broll_disclosed, ai_broll_illustrative_only},
  claims[{id, source_start_s, source_end_s, cut_start_s, cut_end_s, original_quote, used_quote, splice?, splice_still_true?,
          numbers_spoken?[], numbers_on_screen[], critical_not_applicable[{token, reason}], presented_as: quote|headline_fact,
          evidence{type: screenshot|typographic_callout|none, file?, value_shown?, original_unmodified?, in_quotes?, count_up_separate_chip?,
                   contains_pii?, pii_blurred?}, move?{still_true_in_context, logged_in}}]

Exit codes: 0 PASS | 1 FAIL (a rule is violated) | 2 INSUFFICIENT_EVIDENCE (consent/claims/evidence missing).
Missing consent never passes and blocks cloud processing. Stdlib only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import re
import sys
import tempfile
from pathlib import Path

VERSION = "0.1.0"
USES = {"organic", "paid_ad", "website", "internal"}
BYSTANDERS = {"none", "blurred", "consented"}
EVIDENCE_TYPES = {"screenshot", "typographic_callout", "none"}
# meaning-critical tokens: dropping one makes a claim stronger or different
HEDGES_EN = ["i think", "i believe", "i guess", "maybe", "perhaps", "probably", "about", "around", "roughly", "approximately",
             "kind of", "sort of", "almost", "nearly", "up to", "more or less", "something like", "i feel like", "might", "somewhat"]
HEDGES_HE = ["אני חושב", "אני חושבת", "נראה לי", "אולי", "בערך", "כמעט", "בסביבות", "בסביבה של", "פחות או יותר", "כנראה",
             "משהו כמו", "אני מניח", "אני מאמין", "יכול להיות", "לדעתי", "בקירוב"]
NEGATIONS = ["not", "no", "never", "n't", "without", "לא", "אין", "בלי", "אף פעם", "מעולם"]
LIMITERS = ["only", "just", "רק"]
MULT = {"k": 1e3, "thousand": 1e3, "אלף": 1e3, "million": 1e6, "m": 1e6, "מיליון": 1e6}
NUM_RE = re.compile(r"(\d[\d,]*\.?\d*)\s*(thousand|million|k|m|אלף|מיליון)?(?![\w֐-׿])", re.IGNORECASE)
NIQQUD = re.compile(r"[֑-ׇ]")


def norm(s: str) -> str:
    s = NIQQUD.sub("", str(s)).lower().replace("״", '"').replace("׳", "'").replace("’", "'")
    s = re.sub(r"[^\w֐-׿'\s%.,]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str):
    return [t.strip(".,") for t in norm(s).split() if t.strip(".,")]


def contains_phrase(text_norm: str, phrase: str) -> bool:
    p = norm(phrase)
    if re.search(r"[֐-׿]", p):
        return re.search(r"(?<![֐-׿])" + re.escape(p) + r"(?![֐-׿])", text_norm) is not None
    return re.search(r"(?<![a-z0-9'])" + re.escape(p) + r"(?![a-z0-9'])", text_norm) is not None


def numbers(s: str):
    vals = set()
    for m in NUM_RE.finditer(norm(s)):
        raw = m.group(1).replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        mult = MULT.get((m.group(2) or "").lower(), 1.0)
        vals.add(round(v * mult, 6))
    return vals


def as_numbers(items):
    out = set()
    for it in items or []:
        out |= numbers(str(it)) if not isinstance(it, (int, float)) else {round(float(it), 6)}
    return out


def is_subsequence(used, orig):
    it = iter(orig)
    return all(any(u == o for o in it) for u in used)


def critical_tokens(text_norm: str):
    found = []
    for lex, kind in ((HEDGES_EN, "hedge"), (HEDGES_HE, "hedge"), (NEGATIONS, "negation"), (LIMITERS, "limiter")):
        for w in lex:
            if contains_phrase(text_norm, w):
                found.append((w, kind))
    return found


class Rep:
    def __init__(self):
        self.items = []

    def add(self, sev, code, msg, cid=None):
        self.items.append({"severity": sev, "code": code, "claim": cid, "message": msg})


def _isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def check(data, root: Path = None, intended_use=None):
    r = Rep()
    if not isinstance(data, dict) or data.get("schema_version") != "1.0.0":
        r.add("fail", "SCHEMA", "schema_version must be 1.0.0")
        return r
    # ---- consent (G1): before editing and before any cloud upload
    c = data.get("consent") or {}
    if c.get("present") is not True:
        r.add("fail", "NO_CONSENT", "no consent record: block cloud upload/processing and publication; ask for the signed release before editing")
    else:
        try:
            d = _dt.date.fromisoformat(str(c.get("signed_date")))
            if d > _dt.date.today():
                r.add("fail", "CONSENT_DATE", "signed_date is in the future")
        except ValueError:
            r.add("fail", "CONSENT_DATE", "signed_date must be YYYY-MM-DD")
        uses = c.get("uses")
        if not isinstance(uses, list) or not uses or not set(uses) <= USES:
            r.add("fail", "CONSENT_USES", f"consent.uses must be a non-empty subset of {sorted(USES)}")
        elif intended_use and intended_use not in uses:
            r.add("fail", "CONSENT_SCOPE", f"intended use '{intended_use}' is not covered by the release ({uses}): paid ads need explicit ad-use consent")
        if not c.get("withdrawal_contact"):
            r.add("fail", "CONSENT_WITHDRAWAL", "record how the speaker can withdraw (contact)")
        if not c.get("evidence_file"):
            r.add("fail", "CONSENT_EVIDENCE", "consent.evidence_file missing (path of the signed release)")
        elif root is not None and not (root / c["evidence_file"]).is_file():
            r.add("insufficient", "CONSENT_FILE", f"{c['evidence_file']} not found under --root")
        if c.get("bystanders") not in BYSTANDERS:
            r.add("fail", "BYSTANDERS", f"consent.bystanders must be one of {sorted(BYSTANDERS)} (people in frame who did not consent are blurred or cropped)")
        if not isinstance(c.get("cloud_processing_ok"), bool):
            r.add("fail", "CLOUD_FLAG", "consent.cloud_processing_ok must be true/false (is the speaker's footage allowed to leave the machine?)")
        elif c["cloud_processing_ok"] is False and data.get("cloud_steps_used"):
            r.add("fail", "CLOUD_NOT_ALLOWED", f"cloud steps used {data['cloud_steps_used']} but the release does not allow cloud processing")
    # ---- no synthetic speaker (G6)
    syn = data.get("synthetic") or {}
    for k in ("speaker_voice", "speaker_face"):
        if syn.get(k) is not False:
            r.add("fail", "SYNTHETIC_SPEAKER", f"synthetic.{k} must be false: never AI-generate a customer's voice, face, words or result")
    if syn.get("ai_broll") is True and not (syn.get("ai_broll_disclosed") is True and syn.get("ai_broll_illustrative_only") is True):
        r.add("fail", "AI_BROLL", "AI B-roll must be illustrative only and disclosed on the platform route; it never stands for the client's life, product or results")
    if "ai_broll" not in syn:
        r.add("fail", "AI_BROLL", "synthetic.ai_broll must be stated (true/false)")
    # ---- claims
    src = data.get("source") or {}
    dur = src.get("duration_s")
    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        r.add("insufficient", "NO_CLAIMS", "no claims listed: an empty table proves nothing (list every claim the cut makes)")
        return r
    if not _isnum(dur) or dur <= 0:
        r.add("insufficient", "SOURCE_DURATION", "source.duration_s missing")
    ids = set()
    for cl in claims:
        cid = cl.get("id")
        if not cid or cid in ids:
            r.add("fail", "CLAIM_ID", "claim id missing or duplicate", cid)
        ids.add(cid)
        ss, se, cs, ce = (cl.get(k) for k in ("source_start_s", "source_end_s", "cut_start_s", "cut_end_s"))
        if not all(_isnum(v) for v in (ss, se, cs, ce)) or not (0 <= ss < se) or not (0 <= cs < ce):
            r.add("fail", "TIMESTAMPS", "source_start_s < source_end_s and cut_start_s < cut_end_s are required numbers", cid)
            continue
        if _isnum(dur) and se > dur + 0.05:
            r.add("fail", "TIMESTAMPS", f"source range ends after the source ({se} > {dur})", cid)
        oq, uq = cl.get("original_quote"), cl.get("used_quote")
        if not isinstance(oq, str) or not oq.strip() or not isinstance(uq, str) or not uq.strip():
            r.add("fail", "QUOTES", "original_quote (the full sentence from the transcript) and used_quote (what is heard in the cut) are required", cid)
            continue
        on, un = norm(oq), norm(uq)
        # used words are the original words, in order (cuts allowed, insertions/rewrites not)
        if not is_subsequence(tokens(uq), tokens(oq)):
            if cl.get("splice") is True and cl.get("splice_still_true") is True:
                pass
            else:
                r.add("fail", "REWRITTEN_QUOTE", "used_quote has words that are not in the original in the same order (rewrite, insertion or splice); declare splice:true + splice_still_true:true only if every part stays true in context", cid)
        # critical tokens (hedges, negations, limiters) kept
        waived = {norm(w.get("token", "")): w.get("reason") for w in cl.get("critical_not_applicable") or [] if isinstance(w, dict)}
        for tok, kind in critical_tokens(on):
            if not contains_phrase(un, tok) and norm(tok) not in waived:
                r.add("fail", "CRITICAL_TOKEN_DROPPED", f"{kind} '{tok}' is in the original sentence but not in the used quote: the claim became stronger/different. Restore it, or justify in critical_not_applicable (refers to a different clause)", cid)
        for tok, why in waived.items():
            if not why:
                r.add("fail", "WAIVER_REASON", f"critical_not_applicable '{tok}' needs a reason", cid)
        # numbers
        spoken = as_numbers(cl.get("numbers_spoken")) if cl.get("numbers_spoken") is not None else numbers(uq)
        orig_nums = numbers(oq)
        if numbers(uq) - orig_nums:
            r.add("fail", "NUMBER_INTRODUCED", f"used_quote contains number(s) not in the original: {sorted(numbers(uq) - orig_nums)}", cid)
        shown = as_numbers(cl.get("numbers_on_screen"))
        ev = cl.get("evidence") or {}
        etype = ev.get("type")
        if etype not in EVIDENCE_TYPES:
            r.add("fail", "EVIDENCE_TYPE", f"evidence.type must be one of {sorted(EVIDENCE_TYPES)}", cid)
            continue
        unmatched = shown - spoken - (orig_nums if cl.get("numbers_spoken") is None else set())
        if unmatched:
            r.add("fail", "ON_SCREEN_NOT_SPOKEN", f"on-screen number(s) {sorted(unmatched)} are not spoken in the quote (confirm by listening and list them in numbers_spoken, or remove them)", cid)
        if spoken and not shown:
            r.add("warn", "SPOKEN_NOT_SHOWN", f"spoken number(s) {sorted(spoken)} are not shown on screen (house rule: every spoken number is shown)", cid)
        if shown and etype == "none":
            r.add("fail", "NO_PROOF_OR_CALLOUT", "a number is shown but evidence.type is none: show a typographic callout in quotes or the original proof", cid)
        if etype == "screenshot":
            vs = ev.get("value_shown")
            if not (_isnum(vs) or isinstance(vs, str)) or (isinstance(vs, str) and not numbers(vs)):
                r.add("fail", "PROOF_VALUE", "screenshot evidence needs value_shown (the number visible in the proof)", cid)
            else:
                vsn = {round(float(vs), 6)} if _isnum(vs) else numbers(vs)
                if spoken and not (vsn & spoken):
                    r.add("fail", "PROOF_CONTRADICTS", f"screenshot shows {sorted(vsn)} but the speaker says {sorted(spoken)}: never pair them as proof; show the claim as a quoted callout and ask for a matching screenshot", cid)
            if ev.get("original_unmodified") is not True:
                r.add("fail", "PROOF_MODIFIED", "show the ORIGINAL proof screenshot unmodified; animate around it (a rebuilt or edited proof is fabricated evidence)", cid)
            if ev.get("count_up_separate_chip") is False:
                r.add("fail", "PROOF_ANIMATED", "never animate the screenshot itself: a count-up is a separate chip beside it", cid)
            if root is not None and ev.get("file") and not (root / ev["file"]).is_file():
                r.add("insufficient", "PROOF_FILE", f"{ev['file']} not found under --root", cid)
            if not ev.get("file"):
                r.add("fail", "PROOF_FILE", "screenshot evidence needs a file path", cid)
        if etype == "typographic_callout" and ev.get("in_quotes") is not True:
            r.add("fail", "CALLOUT_QUOTES", "an unproven claim is shown as a callout IN QUOTES, attributed to the speaker", cid)
        if ev.get("contains_pii") is True and ev.get("pii_blurred") is not True:
            r.add("fail", "PII", "proof contains personal data (names, account numbers): blur BEFORE any upload or publication", cid)
        pres = cl.get("presented_as")
        if pres not in ("quote", "headline_fact"):
            r.add("fail", "PRESENTED_AS", "presented_as must be quote | headline_fact", cid)
        elif pres == "headline_fact" and etype != "screenshot":
            r.add("fail", "UNPROVEN_HEADLINE", "a witness claim without proof cannot be a headline stated as fact: present it as a quote or obtain the proof", cid)
    # ---- reordering must be logged
    by_cut = sorted([c for c in claims if all(_isnum(c.get(k)) for k in ("cut_start_s", "source_start_s"))], key=lambda c: c["cut_start_s"])
    last_src = -1.0
    for cl in by_cut:
        if cl["source_start_s"] < last_src - 1e-6:
            mv = cl.get("move") or {}
            if not (mv.get("still_true_in_context") is True and mv.get("logged_in")):
                r.add("fail", "UNLOGGED_REORDER", "this claim appears earlier in the cut than in the interview: reordering is allowed only when every statement stays true in its new context, logged in SCRIPT.md (move.still_true_in_context + move.logged_in)", cl.get("id"))
        last_src = max(last_src, cl["source_start_s"])
    for a, b in zip(by_cut, by_cut[1:]):
        if b["cut_start_s"] < a["cut_end_s"] - 1e-6:
            r.add("fail", "CUT_OVERLAP", f"claims {a.get('id')} and {b.get('id')} overlap in the edit", b.get("id"))
    return r


def result(r: Rep):
    fails = [i for i in r.items if i["severity"] == "fail"]
    insuff = [i for i in r.items if i["severity"] == "insufficient"]
    status = "FAIL" if fails else ("INSUFFICIENT_EVIDENCE" if insuff else "PASS")
    return {"tool": "claims_check", "version": VERSION, "status": status,
            "counts": {"fail": len(fails), "insufficient": len(insuff), "warn": len([i for i in r.items if i["severity"] == "warn"])},
            "findings": r.items,
            "limits": ["mechanical checks only: a human reads the cut for meaning, tone and context",
                       "number parsing covers digits with thousand/million/k/אלף/מיליון; spoken Hebrew number words must be listed in numbers_spoken after listening",
                       "a PASS is not legal clearance and not a consent review"]}, {"PASS": 0, "FAIL": 1}.get(status, 2)


# --------------------------------------------------------------------------- self-check
def _base():
    return {"schema_version": "1.0.0",
            "consent": {"present": True, "signed_date": "2026-09-30", "uses": ["organic", "paid_ad"], "platforms": ["meta"], "evidence_file": "consent/release.pdf",
                        "withdrawal_contact": "studio@example.invalid", "bystanders": "none", "cloud_processing_ok": False},
            "cloud_steps_used": [], "source": {"file": "source/interview.mp4", "duration_s": 180.0},
            "synthetic": {"speaker_voice": False, "speaker_face": False, "ai_broll": False},
            "claims": [
                {"id": "C1", "source_start_s": 40.0, "source_end_s": 46.0, "cut_start_s": 0.0, "cut_end_s": 5.5,
                 "original_quote": "I think last month I made about 20 thousand more", "used_quote": "I think last month I made about 20 thousand more",
                 "numbers_on_screen": ["20,000"], "presented_as": "quote",
                 "evidence": {"type": "screenshot", "file": "proof/p1.png", "value_shown": 20000, "original_unmodified": True, "count_up_separate_chip": True}},
                {"id": "C2", "source_start_s": 90.0, "source_end_s": 95.0, "cut_start_s": 5.5, "cut_end_s": 9.0,
                 "original_quote": "it was hard at first", "used_quote": "it was hard at first", "numbers_on_screen": [], "presented_as": "quote",
                 "evidence": {"type": "none"}}]}


def self_check() -> int:
    import copy
    ok, fails = 0, []

    def expect(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(label)

    def codes(d, **kw):
        return {i["code"] for i in check(d, **kw).items}

    d = _base()
    out, code = result(check(d))
    expect("clean table passes", code == 0)

    d = _base(); d["claims"][0]["used_quote"] = "last month I made about 20 thousand more"
    expect("hedge 'I think' dropped -> CRITICAL_TOKEN_DROPPED", "CRITICAL_TOKEN_DROPPED" in codes(d))
    d = _base(); d["claims"][0]["original_quote"] = "I think it helped"; d["claims"][0]["used_quote"] = "it helped"; d["claims"][0]["numbers_on_screen"] = []
    d["claims"][0]["evidence"] = {"type": "none"}
    expect("task-eval case: 'I think it helped' -> 'it helped' fails", "CRITICAL_TOKEN_DROPPED" in codes(d))
    d["claims"][0]["critical_not_applicable"] = [{"token": "i think", "reason": "refers to the previous clause which is not used"}]
    expect("a justified waiver is accepted", "CRITICAL_TOKEN_DROPPED" not in codes(d))
    d = _base(); d["claims"][1]["original_quote"] = "it did not help at first"; d["claims"][1]["used_quote"] = "it did help at first"
    expect("negation dropped -> fails", "CRITICAL_TOKEN_DROPPED" in codes(d) or "REWRITTEN_QUOTE" in codes(d))
    d = _base(); d["claims"][1]["used_quote"] = "it was really hard at first"
    expect("inserted word -> REWRITTEN_QUOTE", "REWRITTEN_QUOTE" in codes(d))
    d = _base(); d["claims"][0]["used_quote"] = "I think last month I made about 200 thousand more"
    expect("number introduced -> NUMBER_INTRODUCED", "NUMBER_INTRODUCED" in codes(d))
    d = _base(); d["claims"][0]["numbers_on_screen"] = ["52%"]
    expect("on-screen number not spoken -> ON_SCREEN_NOT_SPOKEN", "ON_SCREEN_NOT_SPOKEN" in codes(d))
    d = _base(); d["claims"][0]["evidence"]["value_shown"] = 2398
    expect("screenshot disagrees with the spoken number -> PROOF_CONTRADICTS", "PROOF_CONTRADICTS" in codes(d))
    d = _base(); d["claims"][0]["evidence"]["original_unmodified"] = False
    expect("rebuilt proof -> PROOF_MODIFIED", "PROOF_MODIFIED" in codes(d))
    d = _base(); d["claims"][0]["evidence"]["count_up_separate_chip"] = False
    expect("animated screenshot -> PROOF_ANIMATED", "PROOF_ANIMATED" in codes(d))
    d = _base(); d["claims"][0]["evidence"] = {"type": "typographic_callout", "in_quotes": False}
    expect("callout not in quotes -> CALLOUT_QUOTES", "CALLOUT_QUOTES" in codes(d))
    d = _base(); d["claims"][0]["presented_as"] = "headline_fact"; d["claims"][0]["evidence"] = {"type": "typographic_callout", "in_quotes": True}
    expect("unproven headline fact -> UNPROVEN_HEADLINE", "UNPROVEN_HEADLINE" in codes(d))
    d = _base(); d["claims"][0]["evidence"]["contains_pii"] = True
    expect("PII proof not blurred -> PII", "PII" in codes(d))
    d = _base(); d["consent"]["present"] = False
    expect("no consent -> NO_CONSENT", "NO_CONSENT" in codes(d))
    d = _base(); del d["consent"]
    expect("missing consent block -> NO_CONSENT", "NO_CONSENT" in codes(d))
    d = _base(); d["cloud_steps_used"] = ["asr:cloud"]
    expect("cloud step without cloud consent -> CLOUD_NOT_ALLOWED", "CLOUD_NOT_ALLOWED" in codes(d))
    d = _base(); d["consent"]["uses"] = ["organic"]
    expect("paid ad not covered by the release -> CONSENT_SCOPE", "CONSENT_SCOPE" in codes(d, intended_use="paid_ad"))
    d = _base(); d["consent"]["signed_date"] = "2999-01-01"
    expect("future consent date -> CONSENT_DATE", "CONSENT_DATE" in codes(d))
    d = _base(); d["synthetic"]["speaker_voice"] = True
    expect("synthetic voice -> SYNTHETIC_SPEAKER", "SYNTHETIC_SPEAKER" in codes(d))
    d = _base(); d["synthetic"].update(ai_broll=True)
    expect("undisclosed AI B-roll -> AI_BROLL", "AI_BROLL" in codes(d))
    d = _base(); d["claims"][1]["cut_start_s"] = 0.0; d["claims"][1]["cut_end_s"] = 3.0; d["claims"][0]["cut_start_s"] = 3.0; d["claims"][0]["cut_end_s"] = 8.0
    expect("reordering without a log -> UNLOGGED_REORDER", "UNLOGGED_REORDER" in codes(d))
    d["claims"][0]["move"] = {"still_true_in_context": True, "logged_in": "SCRIPT.md#L12"}
    expect("logged reordering accepted", "UNLOGGED_REORDER" not in codes(d))
    d = _base(); d["claims"] = []
    expect("empty claims table -> INSUFFICIENT_EVIDENCE", result(check(d))[1] == 2)
    d = _base(); d["claims"][0]["source_end_s"] = 999
    expect("range beyond the source -> TIMESTAMPS", "TIMESTAMPS" in codes(d))
    d = _base(); d["claims"][0]["numbers_spoken"] = ["20 אלף"]; d["claims"][0]["numbers_on_screen"] = ["20,000"]
    expect("scale words (אלף) parsed", "ON_SCREEN_NOT_SPOKEN" not in codes(d))
    d = _base(); d["claims"][0].update(original_quote="אני חושב שהרווחתי בערך 20 אלף", used_quote="הרווחתי בערך 20 אלף", numbers_on_screen=["20,000"])
    expect("Hebrew hedge 'אני חושב' dropped -> flagged", "CRITICAL_TOKEN_DROPPED" in codes(d))
    with tempfile.TemporaryDirectory(prefix="cc_בדיקה ") as td:
        root = Path(td)
        d = _base()
        expect("missing consent/proof files under --root -> INSUFFICIENT_EVIDENCE", result(check(d, root=root))[1] == 2)
        (root / "consent").mkdir(); (root / "consent" / "release.pdf").write_bytes(b"x")
        (root / "proof").mkdir(); (root / "proof" / "p1.png").write_bytes(b"x")
        expect("with the files present -> PASS", result(check(d, root=root))[1] == 0)
    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": ok + len(fails), "failed": fails}))
    return 0 if not fails else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Testimonial honesty gate: consent + claims table.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--root")
    ap.add_argument("--intended-use", choices=sorted(USES))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.path:
        ap.print_help()
        return 2
    try:
        data = json.loads(Path(a.path).read_text(encoding="utf-8-sig"), parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except (OSError, ValueError) as e:
        print(json.dumps({"status": "INSUFFICIENT_EVIDENCE", "reason": str(e)}, ensure_ascii=False))
        return 2
    out, code = result(check(data, Path(a.root).resolve() if a.root else None, a.intended_use))
    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(out["status"])
        for f in out["findings"]:
            print(f"  [{f['severity']}] {f['code']}" + (f" ({f['claim']})" if f["claim"] else "") + f": {f['message']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

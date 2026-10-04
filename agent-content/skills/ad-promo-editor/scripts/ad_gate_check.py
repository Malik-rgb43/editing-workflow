#!/usr/bin/env python3
"""ad_gate_check.py - the mechanical part of the ad-promo gates: offer exactness, hook ranking, the blocking
compliance table, and asset licences. Fails closed; it does not judge taste, only what can be checked.

Usage:
  python ad_gate_check.py <ad_gates.json> [--root DIR] [--json]
  python ad_gate_check.py --self-check

ad_gates.json (schema_version 1.0.0; field guide in references/compliance-table.md):
  route{platforms[], placement: ad|organic|spark}
  offer{ledger[{id, kind: price|discount|free|deadline|condition|cta, text, required_surfaces?[]}],
        surfaces{voice{text, confirmed_ids[]}, super[], end_card[], caption[]}, absent{client_approved, reason}?}
  hooks[{id, text, rank, reason}]
  compliance[{id, topic, status: pass|fail|blocked|n/a, evidence, reason}]
  assets[{file, kind: music|sfx|footage|font|logo|image|voice, licence, ads_allowed, source_md, placements[],
          attribution?, third_party_brand?, written_permission_file?, ai_generated?, ai_disclosed?}]

Gates covered: G1 offer exact (ledger strings and numbers appear verbatim on every required surface; no
price/percent on screen that is not in the ledger), G2 compliance (all 12 topics present; any fail/blocked =
BLOCKED), G3 hook ranking (>= 3 ranked hooks with reasons; no universal "3-second rule" claim), G5 licences
(unknown = not in client/ad work; brand sounds/logos need written permission; placement coverage; AI assets
disclosed). Safe zones: safe_zone_check.py. Hook-variant files and the shared mix: video-variants-exporter.

Exit codes: 0 PASS | 1 BLOCKED (>= 1 fail/blocked row) | 2 INSUFFICIENT_EVIDENCE (missing ledger, missing topic,
missing file, empty list). A blocked compliance row blocks presenting the draft. Stdlib only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tempfile
from pathlib import Path

VERSION = "0.1.0"
TOPICS = ["claims", "price_terms", "before_after", "reviews", "personal_attribute", "health_finance", "brand_assets",
          "ai_disclosure", "music_licence", "people_consent", "fake_ui", "platform_policy"]
STATES = {"pass", "fail", "blocked", "n/a"}
OFFER_KINDS = {"price", "discount", "free", "deadline", "condition", "cta"}
NUMERIC_KINDS = {"price", "discount", "free"}
DEFAULT_SURFACES = {"price": ["super", "end_card"], "discount": ["super", "end_card"], "free": ["super", "end_card"],
                    "deadline": ["super", "end_card"], "condition": ["super"], "cta": ["end_card"]}
OK_LICENCES = {"CC0", "CC-BY", "OFL", "Mixkit", "Pixabay", "Pexels", "paid-subscription", "owned", "client-supplied", "synthesised"}
MARKS = re.compile(r"[‎‏‪-‮⁦-⁩﻿]")
UNIT_SYMS = {"₪": "ILS", "$": "USD", "€": "EUR", "%": "PCT"}
MONEY_RE = re.compile(r"(?:(?P<pre>[₪$€])\s*(?P<n1>\d[\d,]*\.?\d*)|(?P<n2>\d[\d,]*\.?\d*)\s*(?P<post>[₪$€%]|ש\"ח|ש״ח|שקל|אחוז|nis|ils|usd))", re.IGNORECASE)
UNIVERSAL_3S = re.compile(r"((?:\b3\b|three|שלוש)[\s-]*(?:seconds?|s\b|שניות)).{0,40}(rule|threshold|law|must|always|חוק|חייב)|(rule|threshold|law|must|always|חוק|חייב).{0,40}((?:\b3\b|three|שלוש)[\s-]*(?:seconds?|s\b|שניות))", re.IGNORECASE)
PREAMBLE = re.compile(r"^(three years ago|years ago|once upon|hi\b|hello|hey\b|לפני שלוש שנים|היי\b|שלום\b|בואו נספר)", re.IGNORECASE)


def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def norm(s) -> str:
    s = MARKS.sub("", str(s)).replace("״", '"').replace("׳", "'").replace("”", '"').replace("’", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def money_tokens(text) -> set:
    out = set()
    for m in MONEY_RE.finditer(norm(text)):
        raw = (m.group("n1") or m.group("n2")).replace(",", "")
        try:
            v = round(float(raw), 4)
        except ValueError:
            continue
        sym = m.group("pre") or m.group("post") or ""
        unit = UNIT_SYMS.get(sym) or ("PCT" if sym in ("אחוז",) else "ILS" if sym.lower() in ("nis", "ils", 'ש"ח', "ש״ח", "שקל") else "USD" if sym.lower() == "usd" else "?")
        out.add((v, unit))
    return out


class Rep:
    def __init__(self):
        self.items = []

    def add(self, sev, code, msg, ref=None):
        self.items.append({"severity": sev, "code": code, "ref": ref, "message": msg})


def check(doc, root: Path = None):
    r = Rep()
    if not isinstance(doc, dict) or doc.get("schema_version") != "1.0.0":
        r.add("fail", "SCHEMA", "schema_version must be 1.0.0")
        return r
    route = doc.get("route") or {}
    platforms = route.get("platforms")
    if not isinstance(platforms, list) or not platforms or route.get("placement") not in ("ad", "organic", "spark"):
        r.add("insufficient", "ROUTE", "route.platforms (non-empty) and route.placement (ad|organic|spark) are required: music scope, disclosure and safe-zone rows depend on the route")
    # ---------------------------------------------------------------- G1 offer
    offer = doc.get("offer") or {}
    ledger = offer.get("ledger")
    surfaces = offer.get("surfaces") or {}
    ledger_tokens = set()
    if not isinstance(ledger, list) or not ledger:
        ab = offer.get("absent") or {}
        if ab.get("client_approved") is True and ab.get("reason"):
            r.add("warn", "NO_OFFER_APPROVED", "no offer in the ledger (brand spot approved by the client); a CTA is still required")
        else:
            r.add("insufficient", "NO_OFFER", "no offer ledger: ask the client for the offer in writing (or propose a low-friction one and ask); never invent")
        ledger = ledger or []
    kinds = set()
    for it in ledger:
        iid, kind, text = it.get("id"), it.get("kind"), it.get("text")
        if kind not in OFFER_KINDS or not iid or not str(text or "").strip():
            r.add("fail", "LEDGER_ITEM", "ledger item needs id, kind in %s and text" % sorted(OFFER_KINDS), iid)
            continue
        kinds.add(kind)
        req = it.get("required_surfaces") or DEFAULT_SURFACES[kind]
        toks = money_tokens(text) if kind in NUMERIC_KINDS else set()
        if kind in NUMERIC_KINDS:
            if not toks and kind != "free":
                r.add("fail", "LEDGER_NUMBER", f"{kind} text {text!r} holds no recognisable amount or percent (use e.g. ₪1,690 or 20%)", iid)
            ledger_tokens |= toks
        touches = 0
        for sname in req:
            sdata = surfaces.get(sname)
            present = False
            if sname == "voice":
                v = sdata if isinstance(sdata, dict) else {}
                present = iid in (v.get("confirmed_ids") or []) or (kind not in NUMERIC_KINDS and norm(text) in norm(v.get("text", "")))
            else:
                for s in (sdata or []):
                    if kind in NUMERIC_KINDS and toks:
                        present = present or bool(toks & money_tokens(s))
                    else:
                        present = present or norm(text) in norm(s)
            if sdata is None:
                r.add("insufficient", "SURFACE_MISSING", f"surface '{sname}' not provided: cannot verify {iid} {text!r}", iid)
            elif not present:
                r.add("fail", "OFFER_NOT_EXACT", f"{kind} {text!r} does not appear verbatim on required surface '{sname}'", iid)
        for sname in ("voice", "super", "end_card", "caption"):
            sdata = surfaces.get(sname)
            if sname == "voice":
                v = sdata if isinstance(sdata, dict) else {}
                touches += 1 if iid in (v.get("confirmed_ids") or []) else 0
            else:
                for s in (sdata or []):
                    if (kind in NUMERIC_KINDS and toks and toks & money_tokens(s)) or (not (kind in NUMERIC_KINDS and toks) and norm(text) in norm(s)):
                        touches += 1
                        break
        if kind in NUMERIC_KINDS and touches < 3:
            r.add("warn", "TOUCHES", f"{iid} {text!r} appears on {touches} surface(s); house bar is 3 (voice, super, end card)", iid)
    if ledger and "cta" not in kinds:
        r.add("insufficient", "NO_CTA", "no CTA in the ledger: ask (button, WhatsApp, code, address); written AND spoken, starting >= 2 s before the end card")
    # prices/percents on screen that are not in the ledger = invented or altered
    seen_tokens = set()
    for sname in ("super", "end_card", "caption"):
        for s in surfaces.get(sname) or []:
            seen_tokens |= money_tokens(s)
    v = surfaces.get("voice") if isinstance(surfaces.get("voice"), dict) else {}
    seen_tokens |= money_tokens(v.get("text", ""))
    for tok in sorted(seen_tokens - ledger_tokens):
        r.add("fail", "UNLEDGERED_AMOUNT", f"{tok[0]:g} {tok[1]} appears in the ad but not in the offer ledger: an altered or invented price/percent", None)
    # ---------------------------------------------------------------- G3 hooks
    hooks = doc.get("hooks")
    if not isinstance(hooks, list) or len(hooks) < 3:
        r.add("insufficient", "HOOKS", "at least 3 hooks are required (default batch A/B/C)")
    else:
        ranks = []
        for h in hooks:
            hid = h.get("id")
            if not hid or not str(h.get("text", "")).strip():
                r.add("fail", "HOOK_ITEM", "hook needs id and text", hid)
            if not isinstance(h.get("rank"), int) or h["rank"] < 1:
                r.add("fail", "HOOK_RANK", "rank must be an integer >= 1", hid)
            else:
                ranks.append(h["rank"])
            reason = str(h.get("reason", "")).strip()
            if len(reason) < 8:
                r.add("fail", "HOOK_REASON", "each hook needs a reason (why this rank)", hid)
            if UNIVERSAL_3S.search(reason):
                r.add("fail", "UNIVERSAL_3S", "the reason claims a universal 3-second rule: no source verifies one; give an editorial reason (sound-off readable, offer first, same-angle before/after)", hid)
            if PREAMBLE.search(norm(h.get("text", ""))):
                r.add("warn", "FORBIDDEN_OPENER", "a preamble/greeting opener; open on the offer, a before/after, a visual shock, a contrarian claim or a specific pain", hid)
            if len(str(h.get("text", "")).split()) > 6:
                r.add("warn", "HOOK_LONG", "headline over 6 words for the sound-off top band (house default)", hid)
        if sorted(ranks) != list(range(1, len(ranks) + 1)) or len(ranks) != len(hooks):
            r.add("fail", "HOOK_RANKS", "ranks must be unique and consecutive from 1")
    # ---------------------------------------------------------------- G2 compliance
    comp = doc.get("compliance")
    if not isinstance(comp, list) or not comp:
        r.add("insufficient", "COMPLIANCE", "no compliance table: it is a blocking gate, fill all %d topics" % len(TOPICS))
        comp = []
    by_topic = {}
    for row in comp:
        t = row.get("topic")
        if t not in TOPICS:
            r.add("fail", "COMPLIANCE_TOPIC", f"unknown topic {t!r}; allowed: {TOPICS}", row.get("id"))
            continue
        by_topic[t] = row
        st = row.get("status")
        if st not in STATES:
            r.add("fail", "COMPLIANCE_STATE", f"status must be one of {sorted(STATES)}", t)
        elif st in ("fail", "blocked"):
            r.add("fail", "COMPLIANCE_BLOCKING", f"topic {t}: {st} - {row.get('reason') or 'no reason given'} (blocks presenting the draft)", t)
        elif st == "pass" and not str(row.get("evidence", "")).strip():
            r.add("fail", "COMPLIANCE_EVIDENCE", f"topic {t}: pass without evidence", t)
        elif st == "n/a" and not str(row.get("reason", "")).strip():
            r.add("fail", "COMPLIANCE_NA", f"topic {t}: n/a needs a reason", t)
        if st == "pass" and root is not None and str(row.get("evidence", "")).startswith("file:"):
            if not (root / row["evidence"][5:]).is_file():
                r.add("insufficient", "EVIDENCE_FILE", f"evidence file {row['evidence'][5:]} not found", t)
    missing = [t for t in TOPICS if t not in by_topic]
    if comp and missing:
        r.add("insufficient", "COMPLIANCE_MISSING", f"topics not assessed: {missing}")
    assets = doc.get("assets")
    # cross-consistency: a topic cannot be n/a when the ad plainly touches it
    if any(k in kinds for k in ("price", "discount", "free", "deadline")) and (by_topic.get("price_terms") or {}).get("status") == "n/a":
        r.add("fail", "COMPLIANCE_NA", "price_terms cannot be n/a: the ledger has a price/discount/deadline", "price_terms")
    if isinstance(assets, list):
        if any(a.get("kind") in ("music", "sfx") for a in assets) and (by_topic.get("music_licence") or {}).get("status") == "n/a":
            r.add("fail", "COMPLIANCE_NA", "music_licence cannot be n/a: the ad has music/SFX", "music_licence")
        if any(a.get("third_party_brand") for a in assets) and (by_topic.get("brand_assets") or {}).get("status") == "n/a":
            r.add("fail", "COMPLIANCE_NA", "brand_assets cannot be n/a: a third-party brand sound/logo is used", "brand_assets")
        if any(a.get("ai_generated") for a in assets) and (by_topic.get("ai_disclosure") or {}).get("status") == "n/a":
            r.add("fail", "COMPLIANCE_NA", "ai_disclosure cannot be n/a: AI-generated assets are used", "ai_disclosure")
    # ---------------------------------------------------------------- G5 licences
    if not isinstance(assets, list) or not assets:
        r.add("insufficient", "ASSETS", "no asset list: every music, SFX, footage, font, logo and image needs a licence row (SOURCES.md)")
    else:
        for a in assets:
            f = a.get("file", "?")
            lic = a.get("licence")
            if lic not in OK_LICENCES:
                r.add("fail", "LICENCE", f"licence {lic!r}: unknown / NC / unverified = not in client or ad work (decision default Q2); swap to a licensed asset", f)
            if a.get("kind") != "font" and a.get("ads_allowed") is not True:
                r.add("fail", "ADS_NOT_ALLOWED", "the licence row must allow ads (ads_allowed: true) for this placement and territory", f)
            if not a.get("source_md"):
                r.add("fail", "SOURCE_ROW", "no SOURCES.md pointer (source_md)", f)
            if lic == "CC-BY" and not a.get("attribution"):
                r.add("fail", "ATTRIBUTION", "CC-BY needs the credit text recorded", f)
            if a.get("third_party_brand") and not a.get("written_permission_file"):
                r.add("fail", "BRAND_PERMISSION", "a third-party brand sound/logo in an ad needs written permission from the brand (written_permission_file); organic-only otherwise", f)
            if a.get("kind") in ("music", "sfx", "voice") and isinstance(a.get("placements"), list) and isinstance(platforms, list):
                gap = [p for p in platforms if p not in a["placements"]]
                if gap:
                    r.add("fail", "PLACEMENT", f"licence covers {a['placements']} but the ad also runs on {gap} (music rights are placement- and territory-specific)", f)
            if a.get("ai_generated") and a.get("ai_disclosed") is not True:
                r.add("fail", "AI_DISCLOSURE", "AI-generated asset not marked disclosed on the route (mood or missing B-roll only, disclosed)", f)
            if root is not None and a.get("written_permission_file") and not (root / a["written_permission_file"]).is_file():
                r.add("insufficient", "PERMISSION_FILE", f"{a['written_permission_file']} not found", f)
    return r


def result(r: Rep):
    fails = [i for i in r.items if i["severity"] == "fail"]
    insuff = [i for i in r.items if i["severity"] == "insufficient"]
    status = "BLOCKED" if fails else ("INSUFFICIENT_EVIDENCE" if insuff else "PASS")
    return {"tool": "ad_gate_check", "version": VERSION, "status": status,
            "counts": {"fail": len(fails), "insufficient": len(insuff), "warn": len([i for i in r.items if i["severity"] == "warn"])},
            "findings": r.items,
            "limits": ["mechanical checks only: legal sufficiency of a claim, taste and the visual result need a human and a viewed render",
                       "money parsing recognises amounts with ₪ $ € % or a currency word; spoken Hebrew number words must be confirmed by listening (voice.confirmed_ids)",
                       "a PASS is not legal advice and not platform approval"]}, {"PASS": 0, "BLOCKED": 1}.get(status, 2)


# --------------------------------------------------------------------------- self-check
def _base():
    return {"schema_version": "1.0.0", "route": {"platforms": ["meta"], "placement": "ad"},
            "offer": {"ledger": [{"id": "O1", "kind": "price", "text": "₪1,690"}, {"id": "O2", "kind": "deadline", "text": "עד סוף החודש"},
                                 {"id": "O3", "kind": "cta", "text": "שלחו הודעה בוואטסאפ"}],
                      "surfaces": {"voice": {"text": "", "confirmed_ids": ["O1", "O3"]},
                                   "super": ["₪1,690", "עד סוף החודש"],
                                   "end_card": ["₪1,690 עד סוף החודש", "שלחו הודעה בוואטסאפ"], "caption": []}},
            "hooks": [{"id": "H1", "text": "₪1,690 בלבד", "rank": 1, "reason": "offer as the first line, readable without sound"},
                      {"id": "H2", "text": "אותו מטבח, אחרי", "rank": 2, "reason": "same-angle before/after wipe in 1.5 s"},
                      {"id": "H3", "text": "בלי להחליף מטבח", "rank": 3, "reason": "contrarian claim, specific pain"}],
            "compliance": [{"id": "K%d" % i, "topic": t, "status": "pass", "evidence": "brief line %d" % i} for i, t in enumerate(TOPICS)],
            "assets": [{"file": "hf/assets/bed.wav", "kind": "music", "licence": "CC0", "ads_allowed": True, "source_md": "hf/SOURCES.md#bed", "placements": ["meta", "tiktok"]},
                       {"file": "hf/assets/riser.wav", "kind": "sfx", "licence": "Mixkit", "ads_allowed": True, "source_md": "hf/SOURCES.md#riser"}]}


def self_check() -> int:
    ok, fails = 0, []

    def expect(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(label)

    def codes(d, **kw):
        return {i["code"] for i in check(d, **kw).items}

    out, code = result(check(_base()))
    expect("clean ad passes", code == 0)
    if code != 0:
        print(json.dumps(out, indent=1, ensure_ascii=False), file=sys.stderr)
    d = _base(); d["offer"]["surfaces"]["end_card"][0] = "₪1,990 עד סוף החודש"
    c = codes(d)
    expect("end card shows a different price -> OFFER_NOT_EXACT + UNLEDGERED_AMOUNT", "OFFER_NOT_EXACT" in c and "UNLEDGERED_AMOUNT" in c)
    d = _base(); d["offer"]["surfaces"]["super"] = ["20% הנחה", "₪1,690"]
    expect("an invented percent on screen -> UNLEDGERED_AMOUNT", "UNLEDGERED_AMOUNT" in codes(d))
    d = _base(); d["offer"]["surfaces"]["super"] = ["1690 ₪", "עד סוף החודש"]
    expect("same amount with the symbol after the number is exact", "OFFER_NOT_EXACT" not in codes(d))
    d = _base(); d["offer"]["ledger"] = []
    expect("amounts on screen with an empty ledger are blocked (invented offer)", result(check(d))[1] == 1)
    d["offer"]["surfaces"] = {}
    expect("no offer ledger -> INSUFFICIENT_EVIDENCE (never invent)", result(check(d))[1] == 2)
    d["offer"]["absent"] = {"client_approved": True, "reason": "brand spot"}
    expect("approved no-offer brand spot is allowed but needs a CTA", "NO_OFFER" not in codes(d))
    d = _base(); d["offer"]["ledger"] = [x for x in d["offer"]["ledger"] if x["kind"] != "cta"]
    expect("no CTA -> NO_CTA", "NO_CTA" in codes(d))
    d = _base(); d["offer"]["surfaces"]["voice"]["confirmed_ids"] = []
    expect("fewer than 3 touches only warns", result(check(d))[1] == 0 and "TOUCHES" in codes(d))
    d = _base(); d["hooks"] = d["hooks"][:2]
    expect("two hooks -> INSUFFICIENT_EVIDENCE", result(check(d))[1] == 2)
    d = _base(); d["hooks"][0]["reason"] = "the first 3 seconds rule: you must hook in 3 seconds"
    expect("universal 3-second rule claim -> UNIVERSAL_3S", "UNIVERSAL_3S" in codes(d))
    d = _base(); d["hooks"][1]["rank"] = 1
    expect("duplicate rank -> HOOK_RANKS", "HOOK_RANKS" in codes(d))
    d = _base(); d["hooks"][2]["reason"] = ""
    expect("hook without a reason -> HOOK_REASON", "HOOK_REASON" in codes(d))
    d = _base(); d["compliance"][0].update(status="blocked", reason="'100% guaranteed results' claim")
    out, code = result(check(d))
    expect("blocked compliance row -> BLOCKED", code == 1 and "COMPLIANCE_BLOCKING" in codes(d))
    d = _base(); d["compliance"] = d["compliance"][:5]
    expect("missing compliance topics -> INSUFFICIENT_EVIDENCE", result(check(d))[1] == 2)
    d = _base(); d["compliance"][1].update(status="n/a", reason="")
    expect("n/a without a reason fails", "COMPLIANCE_NA" in codes(d))
    d = _base(); d["compliance"][1].update(status="n/a", reason="no price in this ad")
    expect("price_terms cannot be n/a when the ledger has a price", "COMPLIANCE_NA" in codes(d))
    d = _base(); d["compliance"][2]["evidence"] = ""
    expect("pass without evidence fails", "COMPLIANCE_EVIDENCE" in codes(d))
    d = _base(); d["assets"][0]["licence"] = "unknown"
    expect("unknown licence -> LICENCE (blocked in ads)", "LICENCE" in codes(d))
    d = _base(); d["assets"][0]["licence"] = "CC-BY-NC"
    expect("CC-BY-NC -> LICENCE", "LICENCE" in codes(d))
    d = _base(); d["assets"][1]["ads_allowed"] = None
    expect("licence row silent on ads -> ADS_NOT_ALLOWED", "ADS_NOT_ALLOWED" in codes(d))
    d = _base(); d["assets"].append({"file": "hf/assets/cha_ching.wav", "kind": "sfx", "licence": "paid-subscription", "ads_allowed": True, "source_md": "x", "third_party_brand": True})
    expect("third-party brand sound without written permission -> BRAND_PERMISSION", "BRAND_PERMISSION" in codes(d))
    d["assets"][-1]["written_permission_file"] = "legal/brand_ok.pdf"
    expect("with a written permission file it passes that check", "BRAND_PERMISSION" not in codes(d))
    d = _base(); d["route"]["platforms"] = ["meta", "tiktok", "yt"]
    expect("music licensed for meta+tiktok but the ad also runs on yt -> PLACEMENT", "PLACEMENT" in codes(d))
    d = _base(); d["assets"][0].pop("source_md")
    expect("no SOURCES.md pointer -> SOURCE_ROW", "SOURCE_ROW" in codes(d))
    d = _base(); d["assets"].append({"file": "hf/assets/shot.mp4", "kind": "footage", "licence": "owned", "ads_allowed": True, "source_md": "s", "ai_generated": True})
    expect("undisclosed AI asset -> AI_DISCLOSURE", "AI_DISCLOSURE" in codes(d))
    d = _base(); d["assets"] = []
    expect("empty asset list -> INSUFFICIENT_EVIDENCE", result(check(d))[1] == 2)
    expect("garbage input -> FAIL schema", result(check({"x": 1}))[1] == 1)
    expect("money parser: Hebrew word units", ("1690.0" and (1690.0, "ILS") in money_tokens('1,690 ש"ח')))
    with tempfile.TemporaryDirectory(prefix="ag_בדיקה ") as td:
        d = _base(); d["compliance"][0]["evidence"] = "file:legal/missing.pdf"
        expect("referenced evidence file missing -> INSUFFICIENT_EVIDENCE", result(check(d, Path(td)))[1] == 2)
    print(json.dumps({"self_check": "PASS" if not fails else "FAIL", "passed": ok, "total": ok + len(fails), "failed": fails}))
    return 0 if not fails else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Offer exactness, hooks, compliance table and licences for an ad.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--root")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.path:
        ap.print_help()
        return 2
    try:
        doc = json.loads(Path(a.path).read_text(encoding="utf-8-sig"), parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except (OSError, ValueError) as e:
        print(json.dumps({"status": "INSUFFICIENT_EVIDENCE", "reason": str(e)}, ensure_ascii=False))
        return 2
    out, code = result(check(doc, Path(a.root).resolve() if a.root else None))
    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(out["status"])
        for i in out["findings"]:
            print(f"  [{i['severity']}] {i['code']}" + (f" ({i['ref']})" if i.get("ref") else "") + f": {i['message']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

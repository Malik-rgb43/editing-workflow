#!/usr/bin/env python3
"""Cost-estimate worksheet, approval record, retry cap and provenance for paid actions.

Usage:
  python estimate.py estimate SPEC.json [--out cost_estimate.json] [--max-age-days 0]
  python estimate.py approve  cost_estimate.json --approved --approval-quote "<user's words>"
                              --approved-amount WALLET=AMOUNT [...] [--ttl-hours 24] [--out approval.json]
  python estimate.py can-run  approval.json --line S1        # ask BEFORE every paid call
  python estimate.py record   approval.json --line S1 --outcome ok|failed|rejected|timeout|reconciled
                              [--billed 0.30] [--note "..."]
  python estimate.py status   approval.json
  python estimate.py provenance --file out.mp4 --provider P --model EXACT_ID --mode MODE --plan PLAN
                              --price-date YYYY-MM-DD [--line S1] [--route R] [--out provenance.jsonl]
  python estimate.py project --cuts-per-min 36 --length-s 30 [--floor 3] [--spread 0.2] [--generated-share 1.0]
                              [--retry-cap 1] [--unit-cost 0.4 --wallet W --currency USD --price-date YYYY-MM-DD
                               --price-source NAME | --pilot-spec SPEC.json --pilot P1] [--out project_estimate.json]
  python estimate.py --self-check

SPEC.json (prices are INPUT supplied by the user or read from a provider page the same day;
this script contains no prices and promises none):
  {"project": "demo", "retry_cap": 1, "limits": {"wallet_a": 50},
   "price_sources": {"p1": {"name": "provider price page", "url": "...", "checked_at": "YYYY-MM-DD",
                            "plan": "...", "region": "...", "tax_status": "excl_vat|incl_vat|unknown"}},
   "lines": [{"id": "S1", "provider": "...", "model": "EXACT_MODEL_ID", "route": "api", "mode": "...",
              "wallet": "wallet_a", "currency": "USD|credits|...", "price_source": "p1", "count": 2,
              "calc": "per_unit", "quantity": 5, "unit": "second", "unit_price": 0.05}]}
  calc = per_unit (quantity x unit_price) | fixed (unit_price per call) |
         tokens (ceil(width*height*(out_seconds+in_video_seconds)*fps_factor/divisor)/1000 x
                 price_per_1k_tokens x multiplier; fields: width height out_seconds in_video_seconds
                 fps_factor divisor price_per_1k_tokens multiplier) |
         pilot_actual (the billed cost of ONE approved sample call, "pilot": "P1" -> spec "pilots")
Totals are kept PER WALLET. Credits, API dollars and another vendor's price are never summed.

Pilot first (exit 3, code pilot_first): when one provider + model + mode has more than 3 calls in a spec, every
line of it must use calc pilot_actual: ONE representative sample (the hardest shot) was generated, billed and
approved by the user first, and the batch is priced on what it really cost. spec "pilots":
  {"P1": {"provider", "model", "mode", "wallet", "currency", "shot": "<the hardest shot>", "why_hardest": "...",
          "file_sha256": "<64 hex of the delivered sample>", "approved_quote": "<the user's words on the sample>",
          "actual_cost": "0.42", "attempts": 1, "billed_at": "YYYY-MM-DD"}}
The user may skip the sample in writing: spec "pilot_waived": {"quote": "<their words>", "date": "YYYY-MM-DD"}
(shown in the estimate). `project` turns a reference's cuts per minute and the target length into a shot range
(never below --floor) and, with a dated unit cost or a billed pilot, a cost range with its assumptions.

Refusals (exit 3): no approval token without an explicit --approved, a non-empty --approval-quote,
the exact ceiling shown in the estimate, and a price source read today (--max-age-days, default 0 = the
same local day; a course setting, not a vendor fact; approve re-checks it, so a next-day approval needs a
fresh read). Exit 4: over a stated limit / cap reached. Exit 2: bad input.
The token is an integrity tag. With env AVC_APPROVAL_SECRET set when approving (run it yourself,
outside the agent) it becomes an HMAC the agent cannot forge; without it, the user's chat message
is still the authority and the token only detects accidental edits.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

VERSION = "0.1.0"
DISCLAIMER = ("Arithmetic from the stated prices; not a quote, not accepted-output cost. Failed billed "
              "attempts beyond the retry cap, taxes/FX and review time are not included.")


class Refuse(Exception):
    def __init__(self, code: str, msg: str, exit_code: int = 3):
        super().__init__(msg)
        self.code, self.msg, self.exit_code = code, msg, exit_code


def D(x) -> Decimal:
    try:
        return Decimal(str(x))
    except Exception as exc:  # noqa: BLE001
        raise Refuse("bad_number", f"not a number: {x!r}", 2) from exc


def fmt(d: Decimal) -> str:
    return format(d.quantize(Decimal("0.000001")).normalize(), "f")


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_date(s, what: str) -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError as exc:
        raise Refuse("bad_date", f"{what} must be YYYY-MM-DD, got {s!r}", 3) from exc


def tag(payload: dict, secret: str | None) -> tuple[str, str]:
    if secret:
        return "hmac", "hmac:" + hmac.new(secret.encode(), canon(payload), hashlib.sha256).hexdigest()
    return "integrity", "sha256:" + hashlib.sha256(canon(payload)).hexdigest()


def check_source(src: dict, today: date, max_age: int, sid: str) -> date:
    for k in ("name", "checked_at", "tax_status"):
        if not src.get(k):
            raise Refuse("price_source_incomplete", f"price source {sid!r} lacks {k!r}", 3)
    d = parse_date(src["checked_at"], f"price source {sid!r} checked_at")
    if d > today:
        raise Refuse("price_date_in_future", f"price source {sid!r} is dated {d} but today is {today}", 3)
    if (today - d).days > max_age:
        raise Refuse("stale_price", f"price source {sid!r} is {(today - d).days} days old (max {max_age}); "
                     "re-check the current price card and update checked_at", 3)
    return d


PILOT_BATCH = 3  # more calls than this on one provider + model + mode = a batch: one sample first (owner rule 2026-10-08)


def check_pilot(pid: str, pl: dict, line: dict, today: date) -> Decimal:
    for k in ("provider", "model", "mode", "wallet", "currency", "shot", "file_sha256", "approved_quote", "actual_cost", "billed_at"):
        if not str(pl.get(k, "")).strip():
            raise Refuse("pilot_incomplete", f"pilot {pid!r} lacks {k!r}", 3)
    for k in ("provider", "model", "mode", "wallet", "currency"):
        if str(pl[k]) != str(line.get(k, "")):
            raise Refuse("pilot_mismatch", f"line {line.get('id')}: pilot {pid!r} {k} is {pl[k]!r}, the line has {line.get(k)!r}", 3)
    if len(str(pl["file_sha256"])) != 64 or any(c not in "0123456789abcdef" for c in str(pl["file_sha256"])):
        raise Refuse("pilot_incomplete", f"pilot {pid!r}: file_sha256 must be the 64-hex hash of the delivered sample", 3)
    if parse_date(pl["billed_at"], f"pilot {pid!r} billed_at") > today:
        raise Refuse("price_date_in_future", f"pilot {pid!r} billed_at is after today", 3)
    cost = D(pl["actual_cost"])
    if cost < 0:
        raise Refuse("bad_number", f"pilot {pid!r}: actual_cost must be >= 0", 2)
    return cost


def calc_line(line: dict) -> tuple[Decimal, str]:
    calc = line.get("calc", "per_unit")
    if calc == "pilot_actual":
        cost = D(line.get("_pilot_cost"))
        return cost, f"pilot {line.get('pilot')} actual {cost} per call (billed {line.get('_pilot_date')})"
    if calc == "per_unit":
        q, p = D(line.get("quantity")), D(line.get("unit_price"))
        if q <= 0 or p < 0:
            raise Refuse("bad_number", f"line {line.get('id')}: quantity must be > 0 and unit_price >= 0", 2)
        return q * p, f"{q} {line.get('unit', 'unit')} x {p} per {line.get('unit', 'unit')}"
    if calc == "fixed":
        p = D(line.get("unit_price"))
        if p < 0:
            raise Refuse("bad_number", f"line {line.get('id')}: unit_price must be >= 0", 2)
        return p, f"{p} per call"
    if calc == "tokens":
        w, h = D(line.get("width")), D(line.get("height"))
        out, inp = D(line.get("out_seconds")), D(line.get("in_video_seconds", 0))
        fpsf, div = D(line.get("fps_factor")), D(line.get("divisor"))
        price, mult = D(line.get("price_per_1k_tokens")), D(line.get("multiplier", 1))
        if min(w, h, out, fpsf, div) <= 0 or price < 0 or inp < 0 or mult <= 0:
            raise Refuse("bad_number", f"line {line.get('id')}: token fields must be positive", 2)
        tokens = math.ceil(w * h * (out + inp) * fpsf / div)
        cost = Decimal(tokens) / 1000 * price * mult
        return cost, (f"tokens=ceil({w}x{h}x({out}+{inp})x{fpsf}/{div})={tokens}; "
                      f"{tokens}/1000 x {price} x {mult}")
    raise Refuse("bad_calc", f"line {line.get('id')}: calc must be per_unit | fixed | tokens | pilot_actual", 2)


def build_estimate(spec: dict, today: date, max_age: int) -> dict:
    srcs = spec.get("price_sources") or {}
    if not srcs:
        raise Refuse("no_price_source", "spec has no price_sources: a dated price source is required", 3)
    dates = {sid: check_source(s, today, max_age, sid) for sid, s in srcs.items()}
    default_retry = int(spec.get("retry_cap", 0))
    if default_retry < 0:
        raise Refuse("bad_number", "retry_cap must be >= 0", 2)
    lines, wallets, seen = [], {}, set()
    pilots, waived, warnings = spec.get("pilots") or {}, spec.get("pilot_waived"), []
    groups: dict[tuple, int] = {}
    for ln in spec.get("lines") or []:
        key = (str(ln.get("provider", "")), str(ln.get("model", "")), str(ln.get("mode", "")))
        groups[key] = groups.get(key, 0) + int(ln.get("count", 1))
    if waived and not (isinstance(waived, dict) and str(waived.get("quote", "")).strip()):
        raise Refuse("pilot_waiver_unquoted", "pilot_waived needs the user's own words (quote) and a date", 3)
    for ln in spec.get("lines") or []:
        lid = str(ln.get("id", ""))
        if not lid or lid in seen:
            raise Refuse("bad_line", f"line id missing or duplicated: {lid!r}", 2)
        seen.add(lid)
        for k in ("provider", "model", "wallet", "currency", "price_source"):
            if not ln.get(k):
                raise Refuse("bad_line", f"line {lid} lacks {k!r}", 2)
        if ln["price_source"] not in srcs:
            raise Refuse("bad_line", f"line {lid}: unknown price_source {ln['price_source']!r}", 2)
        count = int(ln.get("count", 1))
        retry = int(ln.get("retry_cap", default_retry))
        if count < 1 or retry < 0:
            raise Refuse("bad_number", f"line {lid}: count >= 1 and retry_cap >= 0 required", 2)
        key = (str(ln["provider"]), str(ln["model"]), str(ln.get("mode", "")))
        extra = {}
        if ln.get("calc") == "pilot_actual":
            pid = str(ln.get("pilot", ""))
            if pid not in pilots:
                raise Refuse("pilot_missing", f"line {lid}: calc pilot_actual needs a known pilot id, got {pid!r}", 3)
            extra = {"_pilot_cost": check_pilot(pid, pilots[pid], ln, today), "_pilot_date": pilots[pid]["billed_at"]}
            att = int(pilots[pid].get("attempts", 1))
            if att - 1 > retry:
                warnings.append(f"line {lid}: the pilot needed {att} attempts; a retry_cap of {retry} may be too low for the batch")
        elif groups[key] > PILOT_BATCH and not waived:
            raise Refuse("pilot_first", f"line {lid}: {groups[key]} calls of {key[0]}/{key[1]}/{key[2] or '-'} is a batch: generate ONE "
                         "sample of the hardest shot, get it approved, then price the batch on its billed cost (calc pilot_actual)", 3)
        unit_cost, formula = calc_line({**ln, "id": lid, **extra})
        first, ceiling = unit_cost * count, unit_cost * count * (1 + retry)
        w = wallets.setdefault(ln["wallet"], {"currency": ln["currency"], "first_pass": Decimal(0), "ceiling": Decimal(0)})
        if w["currency"] != ln["currency"]:
            raise Refuse("wallet_currency_mix", f"wallet {ln['wallet']!r} mixes {w['currency']} and {ln['currency']}", 2)
        w["first_pass"] += first
        w["ceiling"] += ceiling
        lines.append({"id": lid, "provider": ln["provider"], "model": ln["model"], "route": ln.get("route", ""),
                      "mode": ln.get("mode", ""), "wallet": ln["wallet"], "currency": ln["currency"],
                      "price_source": ln["price_source"], "count": count, "retry_cap": retry,
                      "formula": formula, "unit_cost": fmt(unit_cost), "first_pass": fmt(first),
                      "ceiling": fmt(ceiling), "attempts_allowed": count * (1 + retry), "note": ln.get("note", "")})
    if not lines:
        raise Refuse("no_lines", "spec has no lines", 2)
    limits = {k: D(v) for k, v in (spec.get("limits") or {}).items()}
    over = [k for k, v in wallets.items() if k in limits and v["ceiling"] > limits[k]]
    est = {
        "schema_version": "1", "kind": "cost_estimate", "tool_version": VERSION, "project": spec.get("project", ""),
        "created_at": now_utc().isoformat(), "today": today.isoformat(), "max_age_days": max_age,
        "price_sources": srcs, "price_date_oldest": min(dates.values()).isoformat(),
        "lines": lines,
        "totals": {k: {"currency": v["currency"], "first_pass": fmt(v["first_pass"]), "ceiling": fmt(v["ceiling"])}
                   for k, v in wallets.items()},
        "limits": {k: fmt(v) for k, v in limits.items()},
        "over_limit": over, "calls_planned": sum(x["count"] for x in lines),
        "calls_allowed": sum(x["attempts_allowed"] for x in lines),
        "status": "blocked_over_limit" if over else "estimate",
        "pilot": ("waived: " + str(waived.get("quote"))) if waived else ({k: {"shot": v.get("shot"), "actual_cost": v.get("actual_cost"),
                                                                           "billed_at": v.get("billed_at")} for k, v in pilots.items()} or None),
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }
    return est


def render_table(est: dict) -> str:
    rows = ["id | wallet | calls (+retries) | formula | first pass | ceiling"]
    for x in est["lines"]:
        rows.append(f"{x['id']} | {x['wallet']} ({x['currency']}) | {x['count']} (+{x['attempts_allowed'] - x['count']}) "
                    f"| {x['formula']} | {x['first_pass']} | {x['ceiling']}")
    for k, v in est["totals"].items():
        rows.append(f"TOTAL {k} ({v['currency']}): first pass {v['first_pass']}, ceiling {v['ceiling']}"
                    + (f", limit {est['limits'][k]}" if k in est["limits"] else ""))
    rows.append(f"price date (oldest source): {est['price_date_oldest']}; status: {est['status']}")
    if est.get("pilot"):
        rows.append(f"pilot: {est['pilot']}")
    for w in est.get("warnings") or []:
        rows.append("note: " + w)
    rows.append(est["disclaimer"])
    return "\n".join(rows)


def verify_approval(ap: dict, secret: str | None, now: datetime | None = None) -> None:
    body = {k: v for k, v in ap.items() if k not in ("approval_token", "token_mode")}
    mode, token = tag(body, secret if ap.get("token_mode") == "hmac" else None)
    if ap.get("token_mode") == "hmac" and not secret:
        raise Refuse("secret_missing", "approval was issued with an HMAC secret; AVC_APPROVAL_SECRET is not set", 3)
    if not hmac.compare_digest(token, str(ap.get("approval_token", ""))):
        raise Refuse("token_mismatch", "approval file was edited or forged (token does not match)", 3)
    exp = datetime.fromisoformat(ap["expires_at"])
    if (now or now_utc()) > exp:
        raise Refuse("expired", f"approval expired at {ap['expires_at']}", 4)


def read_events(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                out.append({"event": "corrupt"})
    return out


def append_event(path: Path, ev: dict) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")


def ledger_path(approval_path: Path) -> Path:
    return approval_path.with_name("spend_ledger.jsonl")


def do_estimate(spec_path: Path, out: Path, max_age: int, today: date) -> tuple[int, dict]:
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refuse("bad_spec", f"cannot read spec: {exc}", 2) from exc
    est = build_estimate(spec, today, max_age)
    out.write_text(json.dumps(est, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return (4 if est["status"] != "estimate" else 0), est


def do_approve(est_path: Path, a: argparse.Namespace, today: date, secret: str | None) -> tuple[int, dict]:
    if not a.approved:
        raise Refuse("no_explicit_approval", "refusing to issue an approval token without an explicit --approved "
                     "(pass it only after the user approved the shown number in chat)", 3)
    est = json.loads(est_path.read_text(encoding="utf-8"))
    if est.get("kind") != "cost_estimate" or est.get("status") != "estimate":
        raise Refuse("estimate_not_approvable", f"estimate status is {est.get('status')!r}", 3)
    for sid, s in est["price_sources"].items():
        check_source(s, today, int(est["max_age_days"]), sid)
    if len((a.approval_quote or "").strip()) < 3:
        raise Refuse("no_approval_quote", "--approval-quote must hold the user's own words", 3)
    given = {}
    for item in a.approved_amount or []:
        k, _, v = item.partition("=")
        given[k] = D(v)
    for wallet, tot in est["totals"].items():
        if wallet not in given:
            raise Refuse("amount_missing", f"--approved-amount {wallet}=<ceiling> is required", 3)
        if given[wallet] != D(tot["ceiling"]):
            raise Refuse("amount_mismatch", f"approved {given[wallet]} but the estimate ceiling for {wallet} is "
                         f"{tot['ceiling']}; quote the number the user saw", 3)
    ap = {"schema_version": "1", "kind": "approval", "project": est["project"],
          "estimate_sha256": hashlib.sha256(canon(est)).hexdigest(), "approved_at": now_utc().isoformat(),
          "expires_at": (now_utc() + timedelta(hours=a.ttl_hours)).isoformat(), "approver": "user",
          "approval_quote": a.approval_quote.strip(),
          "approved_ceiling": {k: v["ceiling"] for k, v in est["totals"].items()},
          "currency": {k: v["currency"] for k, v in est["totals"].items()},
          "lines": {x["id"]: {"wallet": x["wallet"], "attempts_allowed": x["attempts_allowed"],
                              "model": x["model"], "provider": x["provider"]} for x in est["lines"]},
          "calls_allowed": est["calls_allowed"], "price_date_oldest": est["price_date_oldest"]}
    ap["token_mode"], ap["approval_token"] = tag({k: v for k, v in ap.items() if k != "token_mode"}, secret)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(ap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0, ap


def line_attempts(events: list[dict], line: str) -> tuple[int, bool]:
    n, pending_timeout = 0, False
    for ev in events:
        if ev.get("event") == "outcome" and ev.get("line") == line:
            if ev["outcome"] == "reconciled":
                pending_timeout = False
                continue
            n += 1
            pending_timeout = ev["outcome"] == "timeout"
    return n, pending_timeout


def billed_by_wallet(events: list[dict]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for ev in events:
        if ev.get("event") == "outcome" and ev.get("billed") not in (None, ""):
            out[ev["wallet"]] = out.get(ev["wallet"], Decimal(0)) + D(ev["billed"])
    return out


def do_can_run(ap_path: Path, line: str, secret: str | None, now: datetime | None = None) -> tuple[int, dict]:
    ap = json.loads(ap_path.read_text(encoding="utf-8"))
    verify_approval(ap, secret, now)
    info = ap["lines"].get(line)
    if not info:
        raise Refuse("unknown_line", f"line {line!r} is not in the approved estimate", 4)
    ev = read_events(ledger_path(ap_path))
    used, pending = line_attempts(ev, line)
    if pending:
        raise Refuse("reconcile_first", f"last attempt on {line} timed out: check the provider's job list and record "
                     "--outcome reconciled before any repeat (a repeat may bill twice)", 4)
    if used >= info["attempts_allowed"]:
        raise Refuse("retry_cap_reached", f"{line}: {used}/{info['attempts_allowed']} attempts used; stop and ask the user", 4)
    spent = billed_by_wallet(ev).get(info["wallet"], Decimal(0))
    if spent >= D(ap["approved_ceiling"][info["wallet"]]):
        raise Refuse("ceiling_reached", f"billed {fmt(spent)} >= approved ceiling for {info['wallet']}", 4)
    return 0, {"status": "ok", "line": line, "attempts_used": used, "attempts_allowed": info["attempts_allowed"],
               "billed_so_far": fmt(spent), "ceiling": ap["approved_ceiling"][info["wallet"]]}


def do_record(ap_path: Path, a: argparse.Namespace, secret: str | None) -> tuple[int, dict]:
    ap = json.loads(ap_path.read_text(encoding="utf-8"))
    verify_approval(ap, secret)
    info = ap["lines"].get(a.line)
    if not info:
        raise Refuse("unknown_line", f"line {a.line!r} is not in the approved estimate", 4)
    if a.outcome not in ("ok", "failed", "rejected", "timeout", "reconciled"):
        raise Refuse("bad_outcome", "outcome must be ok|failed|rejected|timeout|reconciled", 2)
    ev = {"event": "outcome", "at": now_utc().isoformat(), "line": a.line, "wallet": info["wallet"],
          "outcome": a.outcome, "billed": a.billed, "note": a.note or ""}
    append_event(ledger_path(ap_path), ev)
    used, _ = line_attempts(read_events(ledger_path(ap_path)), a.line)
    return 0, {"status": "recorded", "line": a.line, "attempts_used": used, "attempts_allowed": info["attempts_allowed"]}


def do_status(ap_path: Path, secret: str | None) -> tuple[int, dict]:
    ap = json.loads(ap_path.read_text(encoding="utf-8"))
    verify_approval(ap, secret)
    ev = read_events(ledger_path(ap_path))
    per = {lid: {"used": line_attempts(ev, lid)[0], "allowed": i["attempts_allowed"]} for lid, i in ap["lines"].items()}
    return 0, {"status": "ok", "expires_at": ap["expires_at"], "lines": per,
               "billed": {k: fmt(v) for k, v in billed_by_wallet(ev).items()}, "ceiling": ap["approved_ceiling"]}


def do_provenance(a: argparse.Namespace) -> tuple[int, dict]:
    for k in ("provider", "model", "mode", "plan", "price_date"):
        if not getattr(a, k):
            raise Refuse("provenance_incomplete", f"--{k.replace('_', '-')} is required", 3)
    f = Path(a.file)
    if not f.is_file():
        raise Refuse("file_missing", f"output file not found: {f}", 2)
    parse_date(a.price_date, "--price-date")
    h = hashlib.sha256()
    with f.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    probe: object = "unavailable (ffprobe not on PATH)"
    if shutil.which("ffprobe"):
        try:
            raw = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                  "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration",
                                  "-of", "json", str(f)], capture_output=True, text=True, timeout=60, check=True).stdout
            probe = json.loads(raw)
        except (subprocess.SubprocessError, ValueError):
            probe = "ffprobe failed"
    rec = {"event": "provenance", "at": now_utc().isoformat(), "line": a.line, "file": f.name, "sha256": h.hexdigest(),
           "bytes": f.stat().st_size, "provider": a.provider, "model": a.model, "route": a.route, "mode": a.mode,
           "plan": a.plan, "price_date": a.price_date, "ffprobe": probe}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    append_event(Path(a.out), rec)
    return 0, rec


def project_estimate(cuts_per_min, length_s, floor=3, spread=0.2, generated_share=1.0, retry_cap=1,
                     unit_cost=None, wallet=None, currency=None, price_date=None, price_source=None, today=None) -> dict:
    """Shots from a reference's pacing: cuts/min x target length, never below `floor`, as a range (+/- spread)."""
    cpm, length, spread, share = D(cuts_per_min), D(length_s), D(spread), D(generated_share)
    if cpm <= 0 or length <= 0 or not (0 <= spread < 1) or not (0 <= share <= 1) or int(floor) < 1 or int(retry_cap) < 0:
        raise Refuse("bad_number", "cuts-per-min and length-s > 0, 0 <= spread < 1, 0 <= generated-share <= 1, floor >= 1, retry-cap >= 0", 2)
    mid = cpm * length / 60
    lo = max(int(floor), math.floor(mid * (1 - spread)))
    hi = max(int(floor), math.ceil(mid * (1 + spread)))
    mid_i = max(int(floor), int(mid.to_integral_value()))
    gen = {k: math.ceil(v * share) for k, v in (("low", lo), ("mid", mid_i), ("high", hi))}
    out = {"kind": "project_estimate", "shots": {"low": lo, "mid": mid_i, "high": hi}, "generated_shots": gen,
           "assumptions": [f"{cpm} cuts per minute (the reference's corrected count) x {length} s = about {fmt(mid)} shots",
                           f"range +/- {fmt(spread * 100)} % for the count's own uncertainty; never below {int(floor)} shots",
                           f"{fmt(share * 100)} % of shots need a generation (the rest: own footage, stock, stills pushed locally)",
                           f"retry cap {int(retry_cap)} per shot in the high end"]}
    if unit_cost is None:
        out["cost"] = None
        out["assumptions"].append("no cost: read a price today or bill one pilot sample, then run again")
        return out
    if not (wallet and currency and price_date and price_source):
        raise Refuse("price_source_incomplete", "a unit cost needs --wallet, --currency, --price-date and --price-source", 3)
    d = parse_date(price_date, "price-date")
    today = today or date.today()
    if d > today:
        raise Refuse("price_date_in_future", f"price date {d} is after today {today}", 3)
    if (today - d).days > 0 and not str(price_source).startswith("pilot:"):
        raise Refuse("stale_price", f"the unit cost was read {(today - d).days} days ago: read it again today", 3)
    u = D(unit_cost)
    out["cost"] = {"wallet": wallet, "currency": currency, "unit_cost": fmt(u), "source": price_source, "date": d.isoformat(),
                   "low": fmt(u * gen["low"]), "high": fmt(u * gen["high"] * (1 + int(retry_cap)))}
    out["assumptions"].append(f"unit cost {fmt(u)} {currency} per shot from {price_source} ({d.isoformat()}); one wallet, never converted")
    out["disclaimer"] = "A range for planning, not an approval: the batch still goes through estimate -> approve after one approved pilot."
    return out


def _ns(**kw) -> argparse.Namespace:
    return argparse.Namespace(**kw)


def _self_check() -> int:
    fails: list[str] = []
    today = date(2026, 10, 2)

    def expect(name: str, fn, code: str | None = None, exit_code: int | None = None):
        try:
            r = fn()
            if code:
                fails.append(f"{name}: expected refusal {code}, got success")
            return r
        except Refuse as r:
            if code is None:
                fails.append(f"{name}: unexpected refusal {r.code}: {r.msg}")
            elif r.code != code or (exit_code is not None and r.exit_code != exit_code):
                fails.append(f"{name}: wanted {code}/{exit_code}, got {r.code}/{r.exit_code}")
        return None

    src = {"name": "example price page", "checked_at": "2026-10-01", "plan": "example", "region": "n/a", "tax_status": "excl_vat"}
    seed = {"width": 1280, "height": 720, "out_seconds": 10, "in_video_seconds": 4, "fps_factor": 24, "divisor": 1024,
            "price_per_1k_tokens": 0.0214, "multiplier": 0.6}
    spec = {"project": "t", "retry_cap": 1, "limits": {"w_usd": 100}, "price_sources": {"p1": src},
            "lines": [{"id": "S1", "provider": "x", "model": "m1", "wallet": "w_usd", "currency": "USD", "price_source": "p1",
                       "count": 2, "calc": "tokens", **seed},
                      {"id": "S2", "provider": "x", "model": "m2", "wallet": "w_usd", "currency": "USD", "price_source": "p1",
                       "count": 2, "calc": "per_unit", "quantity": 1, "unit": "image", "unit_price": 0.05},
                      {"id": "C1", "provider": "y", "model": "m3", "wallet": "y_credits", "currency": "credits",
                       "price_source": "p1", "count": 1, "calc": "per_unit", "quantity": 50, "unit": "credit", "unit_price": 1}]}
    est = expect("estimate builds", lambda: build_estimate(spec, today, 7))
    if est:
        if est["totals"]["w_usd"]["first_pass"] != "7.865632":
            fails.append(f"arithmetic: got {est['totals']['w_usd']['first_pass']}, want 7.865632 (2 token shots + 2 stills)")
        if est["totals"]["w_usd"]["ceiling"] != "15.731264" or est["calls_allowed"] != 10:
            fails.append("retry ceiling or calls_allowed wrong")
        if "y_credits" not in est["totals"] or any("grand" in k or k == "total" for k in est):
            fails.append("wallets must stay separate and no cross-wallet total may exist")
    bad = json.loads(json.dumps(spec))
    bad["price_sources"]["p1"]["checked_at"] = "2026-09-01"
    expect("stale price refused", lambda: build_estimate(bad, today, 7), "stale_price", 3)
    expect("default rule: a price read yesterday is stale", lambda: build_estimate(spec, today, 0), "stale_price", 3)
    same_day = json.loads(json.dumps(spec)); same_day["price_sources"]["p1"]["checked_at"] = today.isoformat()
    expect("default rule: a price read today passes", lambda: build_estimate(same_day, today, 0))
    bad["price_sources"]["p1"]["checked_at"] = "2026-12-01"
    expect("future date refused", lambda: build_estimate(bad, today, 7), "price_date_in_future")
    bad = json.loads(json.dumps(spec)); del bad["price_sources"]["p1"]["tax_status"]
    expect("tax status required", lambda: build_estimate(bad, today, 7), "price_source_incomplete")
    bad = json.loads(json.dumps(spec)); bad["price_sources"] = {}
    expect("price source required", lambda: build_estimate(bad, today, 7), "no_price_source")
    bad = json.loads(json.dumps(spec)); bad["limits"] = {"w_usd": 5}
    over = build_estimate(bad, today, 7)
    if over["status"] != "blocked_over_limit":
        fails.append("over limit must block")

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        code, est = do_estimate(tdp / "spec.json", tdp / "est.json", 7, today)
        if code != 0:
            fails.append("do_estimate exit")
        amounts = ["w_usd=15.731264", "y_credits=100"]
        base = dict(approved=False, approval_quote="yes, go ahead", approved_amount=amounts, ttl_hours=24, out=str(tdp / "approval.json"))
        expect("no --approved, no token", lambda: do_approve(tdp / "est.json", _ns(**base), today, None), "no_explicit_approval")
        if (tdp / "approval.json").exists():
            fails.append("approval file must not exist after refusal")
        expect("quote required", lambda: do_approve(tdp / "est.json", _ns(**{**base, "approved": True, "approval_quote": ""}), today, None), "no_approval_quote")
        expect("wrong amount refused", lambda: do_approve(tdp / "est.json", _ns(**{**base, "approved": True, "approved_amount": ["w_usd=1", "y_credits=100"]}), today, None), "amount_mismatch")
        expect("stale price at approve time", lambda: do_approve(tdp / "est.json", _ns(**{**base, "approved": True}), date(2026, 10, 20), None), "stale_price")
        ok = expect("approve ok", lambda: do_approve(tdp / "est.json", _ns(**{**base, "approved": True}), today, None))
        ap_path = tdp / "approval.json"
        if ok:
            expect("can-run fresh", lambda: do_can_run(ap_path, "C1", None))
            expect("unknown line refused", lambda: do_can_run(ap_path, "ZZ", None), "unknown_line")
            for i in range(2):  # C1 has count 1 + retry 1 = 2 attempts
                expect(f"can-run before attempt {i + 1}", lambda: do_can_run(ap_path, "C1", None))
                do_record(ap_path, _ns(line="C1", outcome="rejected" if i == 0 else "failed", billed=None, note="user rejected" if i == 0 else ""), None)
            expect("third attempt hits the cap", lambda: do_can_run(ap_path, "C1", None), "retry_cap_reached", 4)
            do_record(ap_path, _ns(line="S2", outcome="timeout", billed=None, note=""), None)
            expect("timeout needs reconcile", lambda: do_can_run(ap_path, "S2", None), "reconcile_first")
            do_record(ap_path, _ns(line="S2", outcome="reconciled", billed=None, note="provider shows no job"), None)
            expect("after reconcile may run", lambda: do_can_run(ap_path, "S2", None))
            do_record(ap_path, _ns(line="S1", outcome="ok", billed="3.882816", note=""), None)
            _, st = do_status(ap_path, None)
            if st["billed"].get("w_usd") != "3.882816":
                fails.append(f"status billed wrong: {st}")
            data = json.loads(ap_path.read_text(encoding="utf-8"))
            data["calls_allowed"] = 999
            ap_path.write_text(json.dumps(data), encoding="utf-8")
            expect("tampered approval refused", lambda: do_can_run(ap_path, "S1", None), "token_mismatch")
            # expiry
            data["calls_allowed"] = ok[1]["calls_allowed"]
            ap_path.write_text(json.dumps(data), encoding="utf-8")
            expect("expired approval refused", lambda: do_can_run(ap_path, "S1", None, now_utc() + timedelta(hours=48)), "expired", 4)
        # HMAC strong mode
        code, ap2 = do_approve(tdp / "est.json", _ns(**{**base, "approved": True, "out": str(tdp / "ap_h.json")}), today, "s3cret")
        expect("hmac ok with secret", lambda: do_can_run(tdp / "ap_h.json", "S1", "s3cret"))
        expect("hmac refused without secret", lambda: do_can_run(tdp / "ap_h.json", "S1", None), "secret_missing")
        expect("hmac refused with wrong secret", lambda: do_can_run(tdp / "ap_h.json", "S1", "nope"), "token_mismatch")
        # provenance
        out = tdp / "clip.bin"
        out.write_bytes(b"abc")
        pa = _ns(file=str(out), provider="x", model="m1", mode="i2v", plan="example", price_date="2026-10-01", line="S1",
                 route="api", out=str(tdp / "prov.jsonl"))
        _, rec = do_provenance(pa)
        if rec["sha256"] != hashlib.sha256(b"abc").hexdigest():
            fails.append("provenance hash")
        pa2 = _ns(**{**vars(pa), "model": ""})
        expect("provenance needs exact model id", lambda: do_provenance(pa2), "provenance_incomplete")
    # pilot first
    pil = {"provider": "x", "model": "m1", "mode": "i2v", "wallet": "w_usd", "currency": "USD", "shot": "b4, two hands pouring, fast",
           "why_hardest": "hands + liquid", "file_sha256": "a" * 64, "approved_quote": "this take is good", "actual_cost": "0.9", "attempts": 2,
           "billed_at": "2026-10-02"}
    batch = {"project": "b", "retry_cap": 1, "price_sources": {"p1": {**src, "checked_at": "2026-10-02"}},
             "lines": [{"id": "B1", "provider": "x", "model": "m1", "mode": "i2v", "wallet": "w_usd", "currency": "USD", "price_source": "p1",
                        "count": 6, "calc": "per_unit", "quantity": 5, "unit": "second", "unit_price": 0.1}]}
    expect("a batch of 6 without a pilot is refused", lambda: build_estimate(batch, today, 0), "pilot_first", 3)
    split = json.loads(json.dumps(batch)); split["lines"] = [dict(batch["lines"][0], id="B1", count=3), dict(batch["lines"][0], id="B2", count=3)]
    expect("splitting the batch into lines of 3 is still a batch", lambda: build_estimate(split, today, 0), "pilot_first", 3)
    three = json.loads(json.dumps(batch)); three["lines"][0]["count"] = 3
    expect("3 calls need no pilot", lambda: build_estimate(three, today, 0))
    withp = json.loads(json.dumps(batch)); withp["pilots"] = {"P1": pil}
    withp["lines"][0].update(calc="pilot_actual", pilot="P1", count=5)
    e2 = expect("batch priced on the pilot", lambda: build_estimate(withp, today, 0))
    if e2 and (e2["lines"][0]["unit_cost"] != "0.9" or e2["totals"]["w_usd"]["ceiling"] != "9" or e2["warnings"]):
        fails.append(f"pilot arithmetic: {e2['lines'][0]['unit_cost']} / {e2['totals']['w_usd']['ceiling']}")
    bad = json.loads(json.dumps(withp)); bad["pilots"]["P1"]["approved_quote"] = ""
    expect("pilot without the user's approval is refused", lambda: build_estimate(bad, today, 0), "pilot_incomplete")
    bad = json.loads(json.dumps(withp)); bad["pilots"]["P1"]["model"] = "m2"
    expect("pilot of another model is refused", lambda: build_estimate(bad, today, 0), "pilot_mismatch")
    wv = json.loads(json.dumps(batch)); wv["pilot_waived"] = {"quote": "skip the sample, I know this model", "date": "2026-10-02"}
    e3 = expect("a written waiver lets the batch be estimated", lambda: build_estimate(wv, today, 0))
    if e3 and not str(e3.get("pilot", "")).startswith("waived"):
        fails.append("the waiver must be shown in the estimate")
    wv["pilot_waived"] = {"quote": ""}
    expect("a waiver without the user's words is refused", lambda: build_estimate(wv, today, 0), "pilot_waiver_unquoted")
    # project estimate from a reference
    pe = expect("project range", lambda: project_estimate(36, 30))
    if pe and (pe["shots"] != {"low": 14, "mid": 18, "high": 22} or pe["cost"] is not None):
        fails.append(f"project range: {pe and pe['shots']}")
    pe = expect("floor of a few shots", lambda: project_estimate(2, 20))
    if pe and pe["shots"]["low"] != 3:
        fails.append("floor not applied")
    pe = expect("project cost range", lambda: project_estimate(36, 30, generated_share=0.5, unit_cost="0.9", wallet="w", currency="USD",
                                                            price_date="2026-10-02", price_source="pilot:P1", today=today))
    if pe and (pe["cost"]["low"] != "6.3" or pe["cost"]["high"] != "19.8"):
        fails.append(f"project cost: {pe and pe['cost']}")
    expect("project unit cost from an old price is refused", lambda: project_estimate(36, 30, unit_cost="1", wallet="w", currency="USD",
                                                                                     price_date="2026-09-01", price_source="page", today=today), "stale_price")
    expect("project unit cost without a source is refused", lambda: project_estimate(36, 30, unit_cost="1", today=today), "price_source_incomplete")
    for f in fails:
        print("FAIL:", f)
    print("self-check:", "FAILED" if fails else "ok")
    return 1 if fails else 0


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return _self_check()
    ap = argparse.ArgumentParser(prog="estimate.py", description="Cost worksheet and approval gate (see module docstring).")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("estimate"); p.add_argument("spec"); p.add_argument("--out", default="cost_estimate.json")
    p.add_argument("--max-age-days", type=int, default=0); p.add_argument("--today")
    p = sub.add_parser("approve"); p.add_argument("estimate"); p.add_argument("--approved", action="store_true")
    p.add_argument("--approval-quote", default=""); p.add_argument("--approved-amount", action="append")
    p.add_argument("--ttl-hours", type=float, default=24); p.add_argument("--out", default="approval.json"); p.add_argument("--today")
    p = sub.add_parser("can-run"); p.add_argument("approval"); p.add_argument("--line", required=True)
    p = sub.add_parser("record"); p.add_argument("approval"); p.add_argument("--line", required=True)
    p.add_argument("--outcome", required=True); p.add_argument("--billed"); p.add_argument("--note")
    p = sub.add_parser("status"); p.add_argument("approval")
    p = sub.add_parser("project"); p.add_argument("--cuts-per-min", required=True); p.add_argument("--length-s", required=True)
    p.add_argument("--floor", type=int, default=3); p.add_argument("--spread", default="0.2"); p.add_argument("--generated-share", default="1.0")
    p.add_argument("--retry-cap", type=int, default=1); p.add_argument("--unit-cost"); p.add_argument("--wallet"); p.add_argument("--currency")
    p.add_argument("--price-date"); p.add_argument("--price-source"); p.add_argument("--pilot-spec"); p.add_argument("--pilot")
    p.add_argument("--out"); p.add_argument("--today")
    p = sub.add_parser("provenance"); p.add_argument("--file", required=True)
    for k in ("provider", "model", "mode", "plan", "price-date", "line", "route"):
        p.add_argument(f"--{k}", default="")
    p.add_argument("--out", default="provenance.jsonl")
    a = ap.parse_args(argv)
    if not a.cmd:
        print(__doc__)
        return 2
    secret = os.environ.get("AVC_APPROVAL_SECRET") or None
    today = date.fromisoformat(a.today) if getattr(a, "today", None) else date.today()
    try:
        if a.cmd == "estimate":
            code, res = do_estimate(Path(a.spec), Path(a.out), a.max_age_days, today)
            print(render_table(res))
            if code:
                print(f"BLOCKED: ceiling exceeds the stated limit for {res['over_limit']}; nothing may be submitted")
            return code
        if a.cmd == "approve":
            code, res = do_approve(Path(a.estimate), a, today, secret)
            print(json.dumps({"status": "approved", "file": a.out, "expires_at": res["expires_at"],
                              "token_mode": res["token_mode"], "calls_allowed": res["calls_allowed"]}, indent=2))
            return code
        if a.cmd == "project":
            unit, wallet, cur, pdate, psrc = a.unit_cost, a.wallet, a.currency, a.price_date, a.price_source
            if a.pilot_spec:
                pl = (json.loads(Path(a.pilot_spec).read_text(encoding="utf-8")).get("pilots") or {}).get(a.pilot or "")
                if not pl:
                    raise Refuse("pilot_missing", f"pilot {a.pilot!r} not in {a.pilot_spec}", 3)
                if not str(pl.get("approved_quote", "")).strip():
                    raise Refuse("pilot_incomplete", f"pilot {a.pilot!r} was not approved by the user", 3)
                unit, wallet, cur, pdate, psrc = pl.get("actual_cost"), pl.get("wallet"), pl.get("currency"), pl.get("billed_at"), f"pilot:{a.pilot}"
            res = project_estimate(a.cuts_per_min, a.length_s, a.floor, a.spread, a.generated_share, a.retry_cap,
                                   unit, wallet, cur, pdate, psrc, today)
            if a.out:
                Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return 0
        if a.cmd == "can-run":
            code, res = do_can_run(Path(a.approval), a.line, secret)
        elif a.cmd == "record":
            code, res = do_record(Path(a.approval), a, secret)
        elif a.cmd == "status":
            code, res = do_status(Path(a.approval), secret)
        else:
            a.price_date = getattr(a, "price_date")
            code, res = do_provenance(a)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return code
    except Refuse as r:
        print(json.dumps({"status": "refused", "code": r.code, "message": r.msg}, ensure_ascii=False))
        return r.exit_code
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(json.dumps({"status": "not_run", "message": f"{type(exc).__name__}: {exc}"}))
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

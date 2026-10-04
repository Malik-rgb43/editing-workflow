#!/usr/bin/env python3
"""check_route_freshness.py - is a dated reference module still usable before a spend decision?

Usage:
    python check_route_freshness.py MODULE.md [--today YYYY-MM-DD] [--max-age-days 14] [--json]
    python check_route_freshness.py --self-check

Reads the YAML-ish front matter (between the first two `---` lines) of a dated module such as
`references/dated-model-routes.md` or `agent-content/references/model-routing.md` and returns:
  fresh    (exit 0)  today <= the EARLIEST expiry date AND today - checked_at <= --max-age-days
  stale    (exit 1)  expired or aged out: the module is UNKNOWN, not "probably still true"
  blocked  (exit 2)  file/keys missing, a date unparsable, or checked_at in the future (fail closed)
`expires` may hold ISO dates ("2026-10-16 / 2026-11-01") and/or "N days" (counted from checked_at); the
earliest candidate wins, so "14 days for price rows, 30 days for catalogue rows" expires on day 14.
A stale module means: refresh it NON-SPENDING (read the official price/terms pages, list the catalogue,
read the balance view) and re-run; never "test" a price with a paid generation. A fresh module is still
not a promise: verify on the live price card before any spend (paid-spend-gate owns the approval).
Stdlib only.
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def front_matter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    out = {}
    for ln in lines[1:]:
        if ln.strip() == "---":
            return out
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", ln)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("\"'")
    return None


def to_date(y, m, d):
    try:
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def evaluate(text, today, max_age=14):
    fm = front_matter(text)
    if fm is None or "checked_at" not in fm or "expires" not in fm:
        return {"verdict": "blocked", "reason": "front matter with checked_at and expires not found"}
    m = ISO.search(fm["checked_at"])
    chk = to_date(*m.groups()) if m else None
    if chk is None:
        return {"verdict": "blocked", "reason": f"checked_at unparsable: {fm['checked_at']!r}"}
    if chk > today:
        return {"verdict": "blocked", "reason": f"checked_at {chk} is in the future relative to {today}"}
    cands = [to_date(*g) for g in ISO.findall(fm["expires"])]
    cands = [c for c in cands if c]
    cands += [chk + timedelta(days=int(n)) for n in re.findall(r"(\d+)\s*days?", fm["expires"])]
    if not cands:
        return {"verdict": "blocked", "reason": f"expires has no date or 'N days': {fm['expires']!r}"}
    exp = min(cands)
    age = (today - chk).days
    res = {"checked_at": str(chk), "earliest_expiry": str(exp), "age_days": age, "max_age_days": max_age, "today": str(today)}
    if today > exp:
        res.update(verdict="stale", reason=f"expired on {exp}")
    elif age > max_age:
        res.update(verdict="stale", reason=f"checked {age} days ago (> {max_age})")
    else:
        res.update(verdict="fresh", reason=f"checked {age} days ago, valid until {exp}; still verify on the live price card before spending")
    return res


def self_check():
    t = date(2026, 10, 10)
    bad = []

    def mod(chk, exp):
        return f'---\nmodule: x\nchecked_at: {chk}\nexpires: "{exp}"\n---\nbody\n'
    cases = [
        ("fresh-iso", mod("2026-10-02", "2026-10-16"), "fresh"),
        ("expired-iso", mod("2026-09-01", "2026-10-05"), "stale"),
        ("aged-out", mod("2026-09-20", "2026-12-31"), "stale"),
        ("n-days", mod("2026-10-05", "7 days"), "fresh"),
        ("n-days-expired", mod("2026-10-02", "5 days"), "stale"),
        ("global-style", mod("2026-10-02", "14 days for price rows, 30 days for catalogue rows (2026-10-16 / 2026-11-01), or before any spend"), "fresh"),
        ("missing-keys", "---\nmodule: x\n---\n", "blocked"),
        ("no-front-matter", "# nothing", "blocked"),
        ("bad-date", mod("soon", "2026-10-16"), "blocked"),
        ("future", mod("2027-01-01", "2027-02-01"), "blocked"),
        ("no-expiry-date", mod("2026-10-02", "when the vendor says"), "blocked"),
    ]
    for name, text, want in cases:
        got = evaluate(text, t)["verdict"]
        if got != want:
            bad.append(f"{name}: got {got}, want {want}")
    if evaluate(mod("2026-10-02", "2026-10-16"), date(2026, 10, 17))["verdict"] != "stale":
        bad.append("the day after expiry must be stale")
    if bad:
        print("SELF-CHECK FAILED")
        for b in bad:
            print(" -", b)
        return 1
    print("SELF-CHECK OK (12 cases)")
    return 0


def main(argv=None):
    try:  # Hebrew paths / non-ASCII messages must not crash on a legacy console code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("module", nargs="?")
    ap.add_argument("--today")
    ap.add_argument("--max-age-days", type=int, default=14)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.module:
        ap.print_usage()
        return 2
    try:
        today = date.fromisoformat(a.today) if a.today else date.today()
        text = Path(a.module).read_text(encoding="utf-8")
    except (OSError, ValueError) as e:
        print(f"BLOCKED: {e}")
        return 2
    r = evaluate(text, today, a.max_age_days)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"VERDICT: {r['verdict']} - {r['reason']}")
    return {"fresh": 0, "stale": 1, "blocked": 2}[r["verdict"]]


if __name__ == "__main__":
    sys.exit(main())

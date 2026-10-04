"""ui - search and READ shadcn-registry components as source (nothing is installed), with the licence tier of each registry next to every hit.

Why: a beat that needs a card, a text effect or an animated component should start from a proven component, then be re-authored seek-safe (see pro-video-editor /
ui-sources-and-port.md). This tool replaces the ``ui-registries`` MCP for students who have it disabled: it reads the public registry directory
(https://ui.shadcn.com/r/registries.json) and each registry's own ``registry.json`` index over HTTPS, caches both on disk (7 days; ``--offline`` uses only the cache) and never
runs ``npx shadcn add`` (that installs packages and edits files; it is printed as text only, for a scratch folder).

Licence tiers come from a dated table inside this file (read 2026-09-27..10-01; a registry licence can change - re-read the item's own LICENSE before shipping):
ok (MIT / Apache / ISC / CC0), restricted (fine inside one client video, never redistribute the component), excluded (never used: ``view``/``add-command`` refuse), unknown
(not in the table: treated as restricted until read). 21st.dev is not a shadcn registry and is never queried here.

Usage:
    python tools/ui.py registries [--query text] [--tier ok|restricted|excluded|unknown] [--json]
    python tools/ui.py search "<english description>" [--registry @magicui ...] [--limit 20] [--json]     (default: the ok-tier registries)
    python tools/ui.py view @registry/item [--source] [--save DIR] [--json]
    python tools/ui.py add-command @registry/item                                                         (prints the command, runs nothing)
    common: [--offline] [--cache-dir DIR] [--timeout 20]
Exit: 0 ok, 2 refused / nothing found / unavailable offline, 3 tool error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import _common  # noqa: F401

DIRECTORY_URL = "https://ui.shadcn.com/r/registries.json"
CORE_REGISTRY = {"name": "@shadcn", "homepage": "https://ui.shadcn.com", "url": "https://ui.shadcn.com/r/styles/new-york-v4/{name}.json", "description": "shadcn/ui core components"}
TTL_S = 7 * 24 * 3600
MAX_BYTES = 8 * 1024 * 1024
TIERS_CHECKED = "2026-10-01"
TIER_OK = {"@shadcn", "@magicui", "@motion-primitives", "@kokonutui", "@eldoraui", "@cult-ui", "@smoothui", "@fancy", "@reui", "@kibo-ui", "@ncdai", "@8starlabs-ui", "@systaliko-ui", "@uselayouts", "@motion-lexicon", "@spectrumui"}
TIER_RESTRICTED = {"@react-bits", "@animate-ui", "@skiper-ui", "@paceui", "@pace-ui"}
TIER_EXCLUDED = {"@aceternity", "@coss", "@coss-ui", "@origin-ui", "@originui", "@preline", "@hover-dev"}
ADD_WARNING = "run this ONLY in a scratch folder, never inside a video project: it installs packages and edits files. Re-author the component seek-safe instead of pasting it."


def tier_of(name: str) -> str:
    n = name.lower()
    if n in TIER_EXCLUDED:
        return "excluded"
    if n in TIER_OK:
        return "ok"
    if n in TIER_RESTRICTED:
        return "restricted"
    return "unknown"


def cache_dir(arg: str | None) -> Path:
    base = arg or os.environ.get("AVC_UI_CACHE") or str(Path.home() / ".avc" / "cache" / "ui")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def http_get_json(url: str, timeout: float):
    if not url.startswith("https://"):
        raise ValueError(f"refusing a non-HTTPS URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "avc-ui/0.1 (+registry reader)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - https only, checked above
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"response larger than {MAX_BYTES} bytes: {url}")
    return json.loads(data.decode("utf-8-sig"))


class Fetcher:
    def __init__(self, cache: Path, offline: bool, timeout: float):
        self.cache, self.offline, self.timeout = cache, offline, timeout
        self.notes: list[str] = []

    def path_for(self, url: str) -> Path:
        return self.cache / (hashlib.sha256(url.encode("utf-8")).hexdigest()[:24] + ".json")

    def get(self, url: str):
        p = self.path_for(url)
        fresh = p.is_file() and time.time() - p.stat().st_mtime < TTL_S
        if self.offline or fresh:
            if p.is_file():
                return json.loads(p.read_text(encoding="utf-8"))
            raise LookupError(f"offline and not cached: {url}")
        try:
            data = http_get_json(url, self.timeout)
        except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
            if p.is_file():
                self.notes.append(f"network failed ({exc}); used the cached copy of {url}")
                return json.loads(p.read_text(encoding="utf-8"))
            raise LookupError(f"could not fetch {url}: {exc}") from exc
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8", newline="\n")
        return data


def directory(f: Fetcher) -> list[dict]:
    entries = f.get(DIRECTORY_URL)
    out = [dict(CORE_REGISTRY)]
    seen = {"@shadcn"}
    for e in entries:
        if isinstance(e, dict) and isinstance(e.get("name"), str) and isinstance(e.get("url"), str) and e["name"] not in seen and "{name}" in e["url"]:
            out.append({"name": e["name"], "homepage": e.get("homepage"), "url": e["url"], "description": e.get("description", ""), "health": (e.get("health") or {}).get("status")})
            seen.add(e["name"])
    return out


def item_url(reg: dict, name: str) -> str:
    return reg["url"].replace("{name}", name)


def registry_index(f: Fetcher, reg: dict) -> list[dict]:
    last = None
    for key in ("registry", "registry.json"):
        url = item_url(reg, key)
        try:
            doc = f.get(url)
        except LookupError as exc:
            last = exc
            continue
        items = doc.get("items") if isinstance(doc, dict) else doc
        if isinstance(items, list):
            return [i for i in items if isinstance(i, dict) and isinstance(i.get("name"), str)]
    raise LookupError(f"{reg['name']}: no readable registry index ({last})")


def tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(t) > 1]


def score(item: dict, q: list[str]) -> float:
    name, title, desc = tokens(item.get("name", "")), tokens(item.get("title", "")), tokens(item.get("description", ""))
    s, hit = 0.0, 0
    for t in q:
        h = 3.0 * (t in name) + 2.0 * (t in title) + 1.0 * (t in desc)
        if h:
            hit += 1
        s += h
    return s + (2.0 if hit == len(q) and q else 0.0) if hit else 0.0


def split_ref(ref: str) -> tuple[str, str]:
    m = re.fullmatch(r"(@[A-Za-z0-9._-]+)/([A-Za-z0-9._/-]+)", ref.strip())
    if not m:
        raise ValueError(f"expected @registry/item, got {ref!r}")
    return m.group(1), m.group(2)


def find_registry(f: Fetcher, name: str) -> dict:
    if name.lower().startswith("@21st"):
        raise ValueError("21st.dev is not a shadcn registry and is not queried by this tool (it needs the author's account; never scrape it)")
    for r in directory(f):
        if r["name"].lower() == name.lower():
            return r
    raise LookupError(f"registry {name} is not in the public directory")


def cmd_registries(a, f: Fetcher) -> int:
    rows = [{"name": r["name"], "tier": tier_of(r["name"]), "homepage": r.get("homepage"), "health": r.get("health"), "description": (r.get("description") or "")[:100]} for r in directory(f)]
    if a.query:
        q = tokens(a.query)
        rows = [r for r in rows if any(t in tokens(r["name"] + " " + (r["description"] or "")) for t in q)]
    if a.tier:
        rows = [r for r in rows if r["tier"] == a.tier]
    rows.sort(key=lambda r: ({"ok": 0, "restricted": 1, "unknown": 2, "excluded": 3}[r["tier"]], r["name"]))
    if a.json:
        print(json.dumps({"tiers_checked": TIERS_CHECKED, "registries": rows}, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"[{r['tier']:10}] {r['name']:24} {r['description']}")
        print(f"\n{len(rows)} registries (tiers read {TIERS_CHECKED}: re-read an item's own LICENSE before shipping)")
    return 0 if rows else 2


def cmd_search(a, f: Fetcher) -> int:
    q = tokens(a.query)
    if not q:
        print("ui: give an English description", file=sys.stderr)
        return 2
    names = a.registry or sorted(TIER_OK)
    hits, problems = [], []
    for nm in names:
        try:
            reg = find_registry(f, nm)
            if tier_of(reg["name"]) == "excluded":
                problems.append(f"{reg['name']}: excluded tier, skipped")
                continue
            for it in registry_index(f, reg):
                s = score(it, q)
                if s > 0:
                    hits.append({"ref": f"{reg['name']}/{it['name']}", "registry": reg["name"], "tier": tier_of(reg["name"]), "type": it.get("type"), "title": it.get("title"), "description": (it.get("description") or "")[:140], "score": s})
        except (LookupError, ValueError) as exc:
            problems.append(str(exc))
    hits.sort(key=lambda h: (-h["score"], {"ok": 0, "restricted": 1, "unknown": 2}.get(h["tier"], 3), h["ref"]))
    hits = hits[: a.limit]
    if a.json:
        print(json.dumps({"query": a.query, "hits": hits, "problems": problems + f.notes}, ensure_ascii=False, indent=2))
    else:
        for h in hits:
            print(f"[{h['tier']:10}] {h['ref']:44} {h['title'] or ''} - {h['description']}")
        for p in problems + f.notes:
            print(f"note: {p}", file=sys.stderr)
    return 0 if hits else 2


def cmd_view(a, f: Fetcher) -> int:
    regname, item = split_ref(a.ref)
    reg = find_registry(f, regname)
    tier = tier_of(reg["name"])
    if tier == "excluded":
        print(f"ui: {reg['name']} is in the EXCLUDED licence tier (never used in a student asset or client deliverable without a clearance); not reading it.", file=sys.stderr)
        return 2
    url = item_url(reg, item)
    doc = f.get(url)
    files = [{"path": x.get("path"), "type": x.get("type"), "bytes": len((x.get("content") or "").encode("utf-8"))} for x in doc.get("files", []) if isinstance(x, dict)]
    summary = {"ref": a.ref, "tier": tier, "type": doc.get("type"), "title": doc.get("title"), "description": doc.get("description"), "origin": url, "homepage": reg.get("homepage"),
               "dependencies": doc.get("dependencies", []), "registryDependencies": doc.get("registryDependencies", []), "files": files, "license": doc.get("license"),
               "licence_note": "tier read " + TIERS_CHECKED + "; open the item's own LICENSE / the registry's licence page before shipping" + ("; restricted: do not redistribute the component" if tier != "ok" else "")}
    if a.save:
        out = Path(a.save)
        out.mkdir(parents=True, exist_ok=True)
        for x in doc.get("files", []):
            rel = Path(*[p for p in Path(str(x.get("path", "file"))).parts if p not in ("..", "/", "\\")]) if x.get("path") else Path("file.txt")
            dest = out / rel.name
            dest.write_text(x.get("content") or "", encoding="utf-8", newline="\n")
        h = hashlib.sha256(json.dumps(doc, sort_keys=True).encode("utf-8")).hexdigest()
        (out / "SOURCE.md").write_text(f"# Source of {a.ref}\n\n- origin: {url}\n- registry: {reg['name']} ({reg.get('homepage')})\n- tier: {tier} (read {TIERS_CHECKED})\n- licence: {doc.get('license') or 'not stated in the item: read the registry LICENSE'}\n"
                                       f"- item sha256: {h}\n- fetched: {time.strftime('%Y-%m-%d')}\n- author: see the registry page\n", encoding="utf-8", newline="\n")
        summary["saved_to"] = str(out)
    if a.json or not a.source:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    if a.source:
        for x in doc.get("files", []):
            print(f"\n===== {x.get('path')} =====\n{x.get('content') or ''}")
    for n in f.notes:
        print(f"note: {n}", file=sys.stderr)
    return 0


def cmd_add(a, f: Fetcher) -> int:
    regname, item = split_ref(a.ref)
    reg = find_registry(f, regname)
    tier = tier_of(reg["name"])
    if tier == "excluded":
        print(f"ui: {reg['name']} is in the EXCLUDED licence tier; no command given.", file=sys.stderr)
        return 2
    print(f"npx shadcn@latest add {regname}/{item}")
    print(f"# {ADD_WARNING}", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ui", description=__doc__.split("\n\n")[0])
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--cache-dir")
    ap.add_argument("--timeout", type=float, default=20.0)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("registries")
    s.add_argument("--query")
    s.add_argument("--tier", choices=("ok", "restricted", "excluded", "unknown"))
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--registry", action="append")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("view")
    s.add_argument("ref")
    s.add_argument("--source", action="store_true")
    s.add_argument("--save")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("add-command")
    s.add_argument("ref")
    a = ap.parse_args(argv)
    try:
        f = Fetcher(cache_dir(a.cache_dir), a.offline, a.timeout)
        return {"registries": cmd_registries, "search": cmd_search, "view": cmd_view, "add-command": cmd_add}[a.cmd](a, f)
    except (LookupError, ValueError) as exc:
        print(f"ui: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

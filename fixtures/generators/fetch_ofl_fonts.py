"""Documented, explicit fetch step for Hebrew-capable SIL Open Font License fonts (NOT run by the tests, needs network).

The repository bundles NO font file (nothing whose licence could not be verified at check-in). When a project needs real
Hebrew glyph rendering (captions, Hebrew-text fixtures), run this step once; it downloads from the ``google/fonts`` GitHub
repository at an EXACT git commit that YOU pass, downloads the font's own ``OFL.txt`` next to it, and records
URL + sha256 + byte size + fetch time in ``fonts.lock.json``. Fonts land in ``fixtures/_generated/fonts`` by default
(git-ignored). Review the licence text, then copy the files you need into ``hf/fonts/`` of a project (renderer rule: fonts
come from ``@font-face`` files, never from system names).

Candidate families (both published under the SIL Open Font License 1.1 on Google Fonts; verify at the pinned commit):
``heebo`` and ``assistant`` (Hebrew + Latin).  The exact file names inside ``ofl/<family>/`` can change between commits: a 404
is reported as an error with the URL, never papered over.

Why a commit is mandatory: ``main`` moves; an unpinned fetch is not reproducible. Use ``--dry-run`` to print the plan only.

Usage:
    python fixtures/generators/fetch_ofl_fonts.py --ref <google/fonts-commit-sha> --family heebo [--family assistant] [--out DIR] [--dry-run]
    python fixtures/generators/fetch_ofl_fonts.py --ref <sha> --family heebo --expect heebo=<sha256-of-the-ttf>   # verify a recorded hash
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent

FAMILIES = {
    "heebo": {"dir": "heebo", "files": ["Heebo[wght].ttf"]},
    "assistant": {"dir": "assistant", "files": ["Assistant[wght].ttf"]},
}
BASE = "https://raw.githubusercontent.com/google/fonts"


def plan(ref: str, families: list[str]) -> list[dict[str, str]]:
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise SystemExit("--ref must be a full 40-hex git commit sha of google/fonts (pinning is mandatory)")
    items = []
    for fam in families:
        spec = FAMILIES[fam]
        for name in [*spec["files"], "OFL.txt"]:
            url = f"{BASE}/{ref}/ofl/{spec['dir']}/{urllib.parse.quote(name)}"
            items.append({"family": fam, "name": name, "url": url})
    return items


def fetch(url: str, *, timeout: float = 60.0) -> bytes:
    if not url.startswith("https://raw.githubusercontent.com/google/fonts/"):
        raise SystemExit("refusing to fetch from an unexpected host")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "editing-workflow-fixtures"}), timeout=timeout) as resp:  # noqa: S310 - fixed https host above
        return resp.read()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ref", required=True, help="40-hex commit sha of google/fonts")
    ap.add_argument("--family", action="append", choices=sorted(FAMILIES), required=True)
    ap.add_argument("--out", default=str(_HERE.parent / "_generated" / "fonts"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--expect", action="append", default=[], help="family=sha256 of the font file; mismatch aborts")
    args = ap.parse_args(argv)
    items = plan(args.ref, args.family)
    expected = dict(e.split("=", 1) for e in args.expect)
    if args.dry_run:
        for it in items:
            print(f"would fetch {it['url']}")
        print(f"into {args.out} (no network used)")
        return 0
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lock = {"schema": "avc.fonts-lock/1", "source": "github.com/google/fonts", "ref": args.ref, "fetched_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "files": []}
    for it in items:
        try:
            data = fetch(it["url"])
        except urllib.error.URLError as exc:
            print(f"FAILED {it['url']}: {exc}", file=sys.stderr)
            return 3
        digest = hashlib.sha256(data).hexdigest()
        if it["name"].endswith(".ttf") and it["family"] in expected and expected[it["family"]] != digest:
            print(f"HASH MISMATCH for {it['name']}: expected {expected[it['family']]}, got {digest}", file=sys.stderr)
            return 1
        target = out / it["family"] / it["name"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        lock["files"].append({**it, "sha256": digest, "bytes": len(data)})
        print(f"saved {target} sha256={digest[:16]}")
    (out / "fonts.lock.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("review each OFL.txt before shipping a font; record family, licence and hash in your project SOURCES.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

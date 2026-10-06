#!/usr/bin/env python3
"""hebrew_fonts - free Hebrew fonts to CHOOSE from: the catalogue, a permission-gated download, and a ready font decision for the board.

The rule this serves (SKILL.md): when the user did not name a font, never pick one silently - show them real Hebrew fonts rendered with
their own line and let them choose on the board.

Usage:
  python hebrew_fonts.py list [--style sans|display|rounded|serif|hand] [--json]
  python hebrew_fonts.py fetch (--default | FAMILY ...) --to DIR [--yes]
        without --yes: prints exactly what would be downloaded (files, bytes, total, source) and downloads NOTHING (exit 0);
        with --yes (only after the user said yes): downloads each font + its OFL.txt from the official google/fonts repository into
        DIR/<slug>/, checks the byte size against the catalogue, skips files already present with the right size.
  python hebrew_fonts.py spec --to DIR --text "the user's real line" -o spec.json [--default | --families "A,B,..."]
                              [--keyword WORD] [--title T] [--project P] [--lang he|en] [--caption-style] [--still FRAME.jpg]
        writes a visual-choice-board spec with ONE font decision whose options embed the fetched files (licence text included);
        build and serve it with make_board.py as usual. Refuses (exit 2) when a file was not fetched.
        --font "Family=path/to/font.ttf=path/to/LICENSE.txt" (repeatable) adds a font that is not in the Hebrew catalogue (any script:
        Latin, Arabic, Cyrillic ...) with its licence file; with only --font options no catalogue font is added. Use it for captions
        that are not Hebrew, or for the user's own candidate fonts.
        --caption-style adds the two other caption decisions, so ONE board settles the whole caption look before any caption is
        built: the entrance/exit animation (every allowed `caption_anim`) and the height on the phone frame (`layout`, inside the
        safe zone); --still puts the project's own frame behind them.
  python hebrew_fonts.py --self-check
Catalogue: references/hebrew-fonts.json (sizes and licences verified on its `verified` date; all OFL-1.1). Stdlib only, Python 3.10+.
Exit: 0 ok, 1 a download failed or a size did not match, 2 refused (unknown family, missing file, bad arguments).
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOGUE = HERE.parent / "references" / "hebrew-fonts.json"
STYLES = ("sans", "display", "rounded", "serif", "hand")
FALLBACK = {"serif": "serif", "hand": "cursive"}
LETTERS = "ABCDEFGHIJKL"


def load() -> dict:
    return json.loads(CATALOGUE.read_text(encoding="utf-8"))


def slug(family: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-")


def pick(cat: dict, names: list[str], default: bool) -> list[dict]:
    by = {f["family"].lower(): f for f in cat["families"]}
    names = cat["default_board"] if default or not names else names
    out, bad = [], []
    for n in names:
        f = by.get(n.strip().lower())
        (out.append(f) if f else bad.append(n))
    if bad:
        raise SystemExit(f"hebrew_fonts: unknown family {bad}; see `hebrew_fonts.py list`")
    return out


def paths(f: dict, to: Path) -> tuple[Path, Path]:
    d = to / slug(f["family"])
    return d / f["file"], d / "OFL.txt"


def plan(fams: list[dict], to: Path, base: str) -> dict:
    files = []
    for f in fams:
        font, lic = paths(f, to)
        files.append({"family": f["family"], "file": str(font), "bytes": f["bytes"], "url": base + urllib.parse.quote(f"{f['dir']}/{f['file']}"),
                      "present": font.is_file() and font.stat().st_size == f["bytes"], "licence": f["licence"],
                      "licence_url": base + f"{f['dir']}/OFL.txt", "licence_file": str(lic)})
    need = [x for x in files if not x["present"]]
    return {"files": files, "to_download": len(need), "bytes_to_download": sum(x["bytes"] for x in need),
            "source": "github.com/google/fonts (official Google Fonts repository)", "licence": "SIL Open Font License 1.1 for every file"}


def fetch(fams: list[dict], to: Path, base: str, timeout: float = 60.0) -> tuple[int, dict]:
    p = plan(fams, to, base)
    errors = []
    for x in p["files"]:
        font, lic = Path(x["file"]), Path(x["licence_file"])
        font.parent.mkdir(parents=True, exist_ok=True)
        try:
            if not x["present"]:
                data = urllib.request.urlopen(x["url"], timeout=timeout).read()
                if len(data) != x["bytes"]:
                    errors.append(f"{x['family']}: got {len(data)} bytes, catalogue says {x['bytes']} (not saved; the catalogue may be stale)")
                    continue
                part = font.with_suffix(font.suffix + ".part")
                part.write_bytes(data)
                part.replace(font)
            if not lic.is_file():
                lic.write_bytes(urllib.request.urlopen(x["licence_url"], timeout=timeout).read())
        except OSError as exc:
            errors.append(f"{x['family']}: {exc}")
    p["errors"] = errors
    return (1 if errors else 0), p


CAPTION_ANIMS = (("rise", "עולה למקום", "rises into place"), ("slide_up", "מחליק מלמטה", "slides up"), ("blur_in", "מטושטש לחד", "blur to sharp"),
                 ("scale_in", "גדל למקום", "scales in"), ("word_rise", "מילה אחרי מילה", "word by word"), ("karaoke", "קריוקי (מילה נצבעת)", "karaoke"),
                 ("mask_wipe", "נחשף בניגוב", "mask wipe"))
CAPTION_Y = ((72, "נמוך, מעל אזור הממשק", "low, above the app rail"), (64, "שליש תחתון", "lower third"), (56, "מתחת לפנים", "below the face"),
             (46, "מרכז", "centre"))


def caption_decisions(lang: str) -> list[dict]:
    """The animation and height decisions of a caption-style board (the font decision is built from the fetched files)."""
    he = lang == "he"
    return [{"id": "anim", "title": "אנימציית כניסה ויציאה" if he else "Entrance and exit", "kind": "caption_anim",
             "options": [{"id": f"M{i + 1}", "label": h if he else e, "anim": a} for i, (a, h, e) in enumerate(CAPTION_ANIMS)]},
            {"id": "position", "title": "גובה הכתוביות" if he else "Caption height", "kind": "layout",
             "options": [{"id": f"Y{y}", "label": (h if he else e) + f" · {y}%", "caption_y_pct": y} for y, h, e in CAPTION_Y]}]


def parse_font(arg: str) -> dict:
    """Pure: "Family=font.ttf=LICENSE.txt" -> {family, font, licence}."""
    parts = arg.split("=")
    if len(parts) != 3 or not all(x.strip() for x in parts):
        raise SystemExit(f"hebrew_fonts: --font needs \"Family=font-file=licence-file\", got {arg!r}")
    return {"family": parts[0].strip(), "font": Path(parts[1].strip()), "licence": Path(parts[2].strip())}


def spec(fams: list[dict], to: Path, text: str, out: Path, keyword: str | None, title: str, project: str, lang: str,
         caption_style: bool = False, still: str | None = None, extra: list[dict] | None = None) -> dict:
    extra = extra or []
    if len(fams) + len(extra) > len(LETTERS):
        raise SystemExit(f"hebrew_fonts: at most {len(LETTERS)} fonts on one board")
    if not text.strip():
        raise SystemExit("hebrew_fonts: --text must be the user's real line (no placeholder)")
    options, missing = [], []
    for i, f in enumerate(fams):
        font, lic = paths(f, to)
        if not font.is_file() or not lic.is_file():
            missing.append(f["family"])
            continue
        rel = Path(__import__("os").path.relpath(font, out.parent)).as_posix()
        options.append({"id": LETTERS[i], "label": f"{f['family']} · {f['he'] if lang == 'he' else f['style']}", "family": f["family"],
                        "weight": f["weight"], "fallback": FALLBACK.get(f["style"], "sans-serif"), "font_file": rel,
                        "license": f"SIL Open Font License 1.1 - {f['family']}, github.com/google/fonts/{f['dir']}/OFL.txt (copy saved beside the font)"})
    if missing:
        raise SystemExit(f"hebrew_fonts: not fetched yet: {missing}; run `hebrew_fonts.py fetch ... --to {to}` (with the user's yes)")
    for x in extra:
        if not x["font"].is_file() or not x["licence"].is_file():
            raise SystemExit(f"hebrew_fonts: --font {x['family']}: the font file and its licence file must both exist")
        lic = x["licence"].read_text(encoding="utf-8", errors="replace").strip().splitlines()
        rel = Path(__import__("os").path.relpath(x["font"].resolve(), out.parent.resolve())).as_posix()
        options.append({"id": LETTERS[len(options)], "label": x["family"], "family": x["family"], "weight": 700, "fallback": "sans-serif",
                        "font_file": rel, "license": f"{lic[0] if lic else 'licence'} - {x['licence'].name} (copy beside the font)"})
    sp = {"schema_version": 1, "project": project, "title": title, "lang": lang, "text": text,
          "decisions": [{"id": "font", "title": "פונט" if lang == "he" else "Font", "kind": "font", "options": options}]}
    if caption_style:
        sp["decisions"] += caption_decisions(lang)
    if still:
        if not Path(still).is_file():
            raise SystemExit(f"hebrew_fonts: no still at {still}")
        sp["still"] = Path(__import__("os").path.relpath(Path(still), out.parent)).as_posix()
    if keyword:
        sp["keyword"] = keyword
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"spec": str(out), "options": len(options), "next": f"python make_board.py build {out} && python make_board.py serve <out dir>"}


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        import subprocess

        return subprocess.call([sys.executable, str(HERE / "test_hebrew_fonts.py")])
    if not argv or argv[0] not in ("list", "fetch", "spec"):
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    opts = {"--to": None, "--text": None, "-o": None, "--keyword": None, "--title": None, "--project": "fonts", "--lang": "he",
            "--families": None, "--style": None, "--still": None}
    extra_args: list[str] = []
    flags, names, i = set(), [], 0
    while i < len(rest):
        a = rest[i]
        if a in ("--yes", "--default", "--json", "--caption-style"):
            flags.add(a)
            i += 1
        elif a == "--font" and i + 1 < len(rest):
            extra_args.append(rest[i + 1])
            i += 2
        elif a in opts and i + 1 < len(rest):
            opts[a], i = rest[i + 1], i + 2
        elif a.startswith("-"):
            print(f"unknown option {a}", file=sys.stderr)
            return 2
        else:
            names.append(a)
            i += 1
    cat = load()
    if cmd == "list":
        fams = [f for f in cat["families"] if not opts["--style"] or f["style"] == opts["--style"]]
        if "--json" in flags:
            print(json.dumps(fams, ensure_ascii=False, indent=2))
        else:
            for f in fams:
                star = "*" if f["family"] in cat["default_board"] else " "
                score = f"E03 {f['e03_mean']:.1f}" if "e03_mean" in f else "E03 -  "
                print(f"{star} {f['family']:<22} {f['style']:<8} {f['bytes'] / 1024:>6.0f} KB  {f['licence']}  {score}  {f['he']}" + (f"\n    ! {f['note']}" if f.get("note") else ""))
            print(f"* = on the default board. E03 = legibility at phone scale, 1-5 (one model's ratings; '-' = not tested). "
                  f"Verified {cat['verified']}; source: github.com/google/fonts")
        return 0
    if not opts["--to"] and not (cmd == "spec" and extra_args and not names and not opts["--families"] and "--default" not in flags):
        print(f"{cmd} needs --to DIR (for example _work/fonts)", file=sys.stderr)
        return 2
    to = Path(opts["--to"] or ".")
    if opts["--families"]:
        names += [n for n in opts["--families"].split(",") if n.strip()]
    try:
        extra = [parse_font(x) for x in extra_args]
        fams = [] if (extra and not names and "--default" not in flags) else pick(cat, names, "--default" in flags)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2
    if cmd == "fetch":
        if "--yes" not in flags:
            p = plan(fams, to, cat["download_base"])
            p["status"] = "plan_only"
            p["note"] = "nothing was downloaded: show this to the user; after their yes, run the same command with --yes"
            print(json.dumps(p, ensure_ascii=False, indent=2))
            return 0
        code, p = fetch(fams, to, cat["download_base"])
        p["status"] = "ok" if code == 0 else "failed"
        print(json.dumps(p, ensure_ascii=False, indent=2))
        return code
    if not opts["-o"] or opts["--text"] is None:
        print("spec needs -o spec.json and --text \"the user's line\"", file=sys.stderr)
        return 2
    cs = "--caption-style" in flags
    title = opts["--title"] or ({True: "איך הכתוביות ייראו?", False: "איזה פונט?"}[cs] if opts["--lang"] == "he" else
                                {True: "How should the captions look?", False: "Which font?"}[cs])
    try:
        res = spec(fams, to, opts["--text"], Path(opts["-o"]), opts["--keyword"], title, opts["--project"], opts["--lang"], cs, opts["--still"], extra)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

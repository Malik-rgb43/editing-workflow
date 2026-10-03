#!/usr/bin/env python3
"""seek_safe_scan.py - static scan of HyperFrames compositions for state that cannot be seeked.

Usage:
    python seek_safe_scan.py PATH [PATH ...] [--json] [--strict]
    python seek_safe_scan.py --self-check

PATH = files or directories (.html .js .css .jsx .tsx .ts; node_modules, .git, _work, renders skipped).
This complements `hf_preflight` (HyperFrames-specific static checks); it does NOT replace it, and a pass
proves only that these patterns are absent. Seek-safety is proven by snapshots at NON-sequential times
(e.g. 2.7 s then 0.4 s) and by render evidence, never by this scan alone.

Rules (E = error, W = warning; --strict turns warnings into errors)
  SS01 E  Date.now / new Date() / performance.now            (render-time clocks)
  SS02 E  Math.random                                         (use a seeded hash; suppress with
                                                               `seek-safe-ok: <reason>` on the same line)
  SS03 E  requestAnimationFrame / cancelAnimationFrame / setAnimationLoop
  SS04 E  setInterval ; W setTimeout
  SS05 E  repeat:-1 / CSS animation ... infinite
  SS06 E  CSS `transition:`/`transition-*:` declarations ; W Tailwind transition-* classes
  SS07 E  dir="rtl" on <html> or on a data-composition-id root (black render trap; RTL on text elements only)
  SS08 E  negative data-start
  SS09 E  gsap.timeline(...) without paused:true ; E timeline .play( ; W gsap.timeline but no __timelines[ registration
  SS10 E  fetch( / XMLHttpRequest / dynamic import() of a URL   ; W remote <script src>/<link href> (render-time network surface)
  SS11 E  media .play()/.pause()/.currentTime= ; E crossorigin on <video>/<audio>
  SS12 W  callbacks that create visible state (onComplete/onStart/tl.call) - suppressed on seek
  SS13 W  gsap.from( (use fromTo) ; W layout properties tweened (left/top/width/height/fontSize/letterSpacing)
  SS14 W  backdrop-filter (render cost: keep it off whole-film layers)
  SS15 W  font-family used but no @font-face for it in the scanned set (fonts must come from files)
  SS16 W  getBoundingClientRect/offsetWidth/offsetLeft (layout reads at tween time; precompute constants)

Exit codes: 0 pass | 1 fail | 2 blocked (no file scanned = not_run, never pass). Stdlib only.
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

EXTS = {".html", ".js", ".css", ".jsx", ".tsx", ".ts"}
SKIP = {"node_modules", ".git", "_work", "renders", "__pycache__"}
GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "inherit", "initial", "unset",
           "ui-sans-serif", "ui-serif", "ui-monospace", "emoji", "math", "fangsong", "-apple-system"}

LINE_RULES = [
    ("SS01", "E", re.compile(r"\bDate\.now\s*\(|\bnew\s+Date\s*\(\s*\)|\bperformance\.now\s*\("), "render-time clock (Date.now/new Date()/performance.now)"),
    ("SS02", "E", re.compile(r"\bMath\.random\s*\("), "unseeded Math.random (use a seeded hash of index/frame)"),
    ("SS03", "E", re.compile(r"\b(requestAnimationFrame|cancelAnimationFrame|setAnimationLoop)\s*\("), "free-running animation loop"),
    ("SS04", "E", re.compile(r"\bsetInterval\s*\("), "setInterval drives time"),
    ("SS04", "W", re.compile(r"\bsetTimeout\s*\("), "setTimeout (time must live on the paused timeline)"),
    ("SS05", "E", re.compile(r"repeat\s*:\s*-1"), "repeat:-1 (use floor(duration/cycle)-1)"),
    ("SS05", "E", re.compile(r"animation[^;{}]*\binfinite\b", re.I), "CSS animation with infinite iteration"),
    ("SS06", "E", re.compile(r"(^|[;{\s])transition(-[a-z]+)?\s*:", re.I), "CSS transition declaration"),
    ("SS06", "W", re.compile(r"class\s*=\s*\"[^\"]*\btransition(-[a-z]+)?\b"), "Tailwind transition-* class"),
    ("SS07", "E", re.compile(r"<html\b[^>]*\bdir\s*=\s*[\"']?rtl", re.I), 'dir="rtl" on <html> (renders black); RTL on text elements only'),
    ("SS07", "E", re.compile(r"data-composition-id[^>]*\bdir\s*=\s*[\"']?rtl|\bdir\s*=\s*[\"']?rtl[^>]*data-composition-id", re.I), 'dir="rtl" on the composition root'),
    ("SS08", "E", re.compile(r"data-start\s*=\s*[\"']-"), "negative data-start shifts every clip"),
    ("SS09", "E", re.compile(r"\b(tl|timeline|master|main)\.play\s*\(\s*\)"), "timeline .play() (timeline must stay paused and seeked)"),
    ("SS10", "E", re.compile(r"\bfetch\s*\(|\bXMLHttpRequest\b|\bimport\s*\(\s*[\"']https?:"), "render-time network request"),
    ("SS10", "W", re.compile(r"<(script|link)\b[^>]*(src|href)\s*=\s*[\"']https?://", re.I), "remote script/stylesheet at render time (pin and vendor it)"),
    ("SS11", "E", re.compile(r"\b(video|audio|media|vid|aud)[A-Za-z0-9_]*\.(play|pause)\s*\(|\.currentTime\s*="), "manual media control (framework owns playback)"),
    ("SS11", "E", re.compile(r"<(video|audio)\b[^>]*\bcrossorigin", re.I), "crossorigin on media breaks preview"),
    ("SS12", "W", re.compile(r"\b(onComplete|onStart|onReverseComplete)\s*:|\btl\.call\s*\("), "callback creates visible state (suppressed on seek)"),
    ("SS13", "W", re.compile(r"\bgsap\.from\s*\("), "gsap.from snapshots the start state at registration; use fromTo"),
    ("SS14", "W", re.compile(r"backdrop-filter\s*:", re.I), "backdrop-filter is a render-cost trap on long-lived layers"),
    ("SS16", "W", re.compile(r"\b(getBoundingClientRect|offsetWidth|offsetHeight|offsetLeft|offsetTop)\b"), "layout read (precompute constants)"),
]
LAYOUT_PROPS = re.compile(r"\b(left|top|width|height|fontSize|letterSpacing)\s*:")
SUPPRESS = re.compile(r"seek-safe-ok\s*:\s*\S{5,}")


def iter_files(paths):
    for p in paths:
        p = Path(p)
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in EXTS and not (set(f.parts) & SKIP):
                    yield f


def call_span(text, start):
    """Text of the call whose '(' is at index start (simple depth count, capped)."""
    depth, i = 0, start
    while i < len(text) and i < start + 600:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return text[start:start + 600]


def scan_text(name, text):
    out = []
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        if SUPPRESS.search(line):
            continue
        for rid, sev, rx, msg in LINE_RULES:
            if rx.search(line):
                out.append((rid, sev, f"{name}:{n}", msg, line.strip()[:110]))
    for m in re.finditer(r"gsap\.timeline\s*\(", text):
        n = text.count("\n", 0, m.start()) + 1
        if SUPPRESS.search(lines[n - 1]):
            continue
        if not re.search(r"paused\s*:\s*true", call_span(text, m.end() - 1)):
            out.append(("SS09", "E", f"{name}:{n}", "gsap.timeline() without paused:true", lines[n - 1].strip()[:110]))
    if re.search(r"gsap\.timeline\s*\(", text) and not re.search(r"__timelines\s*\[", text):
        out.append(("SS09", "W", f"{name}:1", "gsap.timeline used but no window.__timelines[<id>] registration in this file", ""))
    for m in re.finditer(r"\.(?:to|fromTo|set)\s*\(", text):
        span = call_span(text, m.end() - 1)
        if LAYOUT_PROPS.search(span):
            n = text.count("\n", 0, m.start()) + 1
            if not SUPPRESS.search(lines[n - 1]):
                out.append(("SS13", "W", f"{name}:{n}", "layout property tweened (left/top/width/height/fontSize/letterSpacing): use transforms", lines[n - 1].strip()[:110]))
                break
    return out


def font_findings(texts):
    used, declared = {}, set()
    for name, text in texts:
        for m in re.finditer(r"@font-face\s*{[^}]*font-family\s*:\s*[\"']?([^;\"'}]+)", text, re.I):
            declared.add(m.group(1).strip().lower())
        for n, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(r"font-family\s*:\s*([^;}]+)", line, re.I):
                for fam in m.group(1).split(","):
                    fam = fam.strip().strip("\"'").lower()
                    if fam and fam not in GENERIC and not fam.startswith("var(") and "@font-face" not in line:
                        used.setdefault(fam, f"{name}:{n}")
    return [("SS15", "W", where, f"font '{fam}' used without an @font-face declaration in the scanned set (fonts come from files)", "")
            for fam, where in sorted(used.items()) if fam not in declared]


def run(paths, strict=False):
    texts, findings, scanned = [], [], 0
    for f in iter_files(paths):
        try:
            t = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            findings.append(("SS00", "E", str(f), "cannot read file", ""))
            continue
        scanned += 1
        texts.append((f.name, t))
        findings += scan_text(f.name, t)
    findings += font_findings(texts)
    if strict:
        findings = [(r, "E" if s == "W" else s, w, m, c) for r, s, w, m, c in findings]
    errs = [x for x in findings if x[1] == "E"]
    if scanned == 0:
        verdict, reason = "blocked", "no file scanned (not_run, never pass)"
    elif any(x[0] == "SS00" for x in errs):
        verdict, reason = "blocked", "unreadable input"
    elif errs:
        verdict, reason = "fail", f"{len(errs)} error(s)"
    else:
        verdict, reason = "pass", f"{scanned} file(s) free of the scanned patterns; run snapshots at non-sequential times"
    return findings, {"verdict": verdict, "reason": reason, "files_scanned": scanned}


GOOD_HTML = """<!doctype html><html lang="he"><head><style>
@font-face{font-family:'Rubik';src:url('./fonts/Rubik.ttf');font-weight:300 900}
body{font-family:'Rubik',sans-serif}
</style></head><body>
<div data-composition-id="main" data-width="1920" data-height="1080" data-duration="12">
<div id="main-card" class="clip" data-start="0" data-duration="12">שלום</div></div>
<script>
const tl = gsap.timeline({ paused: true });
tl.fromTo('#main-card', {opacity:0, x:40}, {opacity:1, x:0, duration:.4, ease:'power3.out'}, 0.1);
window.__timelines = window.__timelines || {}; window.__timelines['main'] = tl;
</script></body></html>"""

BAD_HTML = """<html dir="rtl"><head><style>.a{transition: all .3s} .b{animation: spin 1s infinite}
body{font-family:'Missing Font',serif}</style></head><body>
<div data-composition-id="main"><div data-start="-0.2"></div></div>
<video src="a.mp4" crossorigin="anonymous"></video>
<script>
const tl = gsap.timeline();
function loop(){ requestAnimationFrame(loop); const t = Date.now(); const r = Math.random(); }
setInterval(()=>{}, 100); tl.play(); fetch('https://x.test/a.json');
gsap.to('#a',{left: 100, duration: 1, repeat:-1});
</script></body></html>"""


def self_check():
    bad = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "good.html").write_text(GOOD_HTML, encoding="utf-8")
        (td / "bad.html").write_text(BAD_HTML, encoding="utf-8")
        (td / "supp.js").write_text("const r = Math.random(); // seek-safe-ok: seeded upstream in fixture\n", encoding="utf-8")
        (td / "supp2.js").write_text("const r = Math.random(); // seek-safe-ok\n", encoding="utf-8")
        f, s = run([td / "good.html"])
        if s["verdict"] != "pass":
            bad.append(f"good.html should pass, got {s} {[x[0] for x in f]}")
        f, s = run([td / "bad.html"])
        got = {x[0] for x in f if x[1] == "E"}
        want = {"SS01", "SS02", "SS03", "SS04", "SS05", "SS06", "SS07", "SS08", "SS09", "SS10", "SS11"}
        if s["verdict"] != "fail" or not want <= got:
            bad.append(f"bad.html should trip {sorted(want - got)} (got {sorted(got)})")
        if not any(x[0] == "SS15" for x in f):
            bad.append("bad.html should warn SS15 (font without @font-face)")
        f, s = run([td / "supp.js"])
        if s["verdict"] != "pass":
            bad.append("a suppression with a reason must pass")
        f, s = run([td / "supp2.js"])
        if s["verdict"] != "fail":
            bad.append("a suppression without a reason must NOT suppress")
        f, s = run([td / "none"])
        if s["verdict"] != "blocked":
            bad.append("empty scan must be blocked")
        (td / "w.js").write_text("setTimeout(()=>{},10)\n", encoding="utf-8")
        f, s = run([td / "w.js"])
        f2, s2 = run([td / "w.js"], strict=True)
        if s["verdict"] != "pass" or s2["verdict"] != "fail":
            bad.append("warnings pass by default and fail under --strict")
    if bad:
        print("SELF-CHECK FAILED")
        for b in bad:
            print(" -", b)
        return 1
    print("SELF-CHECK OK (7 cases)")
    return 0


def main(argv=None):
    try:  # Hebrew paths / non-ASCII messages must not crash on a legacy console code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.paths:
        ap.print_usage()
        return 2
    findings, summ = run(a.paths, a.strict)
    if a.json:
        print(json.dumps({"summary": summ, "findings": [dict(rule=r, severity=s, where=w, message=m, code=c) for r, s, w, m, c in findings]},
                         ensure_ascii=False, indent=2))
    else:
        for r, s, w, m, c in findings:
            print(f"[{s}] {r} {w}: {m}" + (f"   > {c}" if c else ""))
        print(f"VERDICT: {summ['verdict']} - {summ['reason']}")
    return {"pass": 0, "fail": 1, "blocked": 2}[summ["verdict"]]


if __name__ == "__main__":
    sys.exit(main())

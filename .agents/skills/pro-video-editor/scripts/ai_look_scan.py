#!/usr/bin/env python3
"""ai_look_scan.py - static scan of a composition for the code-level tells of the "AI look" (captions, motion, type).

Usage:
    python ai_look_scan.py PATH [PATH ...] [--json] [--strict]
    python ai_look_scan.py --self-check

PATH = files or directories (.html .js .css .jsx .tsx .ts; node_modules, .git, _work, renders, vendored
motion-kit.js / gsap*.js skipped). The reasons and the fix for each rule are in
`references/anti-ai-look.md`. Every rule is a WARNING: a tell with a written reason in PROMPT.md may stay.
Put `ai-look-ok: <reason of 5+ chars>` on the same line to accept one on purpose. A clean scan proves only
that these patterns are absent; the frames are still the judge.

Rules
  AL01  a named preset easing (GSAP power/sine/expo/circ/quad/cubic/quart/quint, CSS ease / ease-in-out)
  AL02  gsap.defaults(...) - one curve and one duration for everything
  AL03  fade-up preset: opacity 0 + y 12..40 px in a from-state
  AL04  bounce / elastic / back easing
  AL05  even stagger (stagger: N, or i * 0.1 style offsets)
  AL06  a visible property (opacity/x/y/scale/rotation) tweened on ease "none"/"linear" (not a proxy with onUpdate)
  AL07  blur-in: filter blur(...) in a tween
  AL08  glow or gradient text: text-shadow with a 10px+ blur, background-clip:text
  AL09  emoji in the composition text
  AL10  small uppercase tracked labels ("feature pills"): text-transform:uppercase + letter-spacing in one rule
  AL11  a default UI font as the type system (Inter, Poppins, Montserrat)

Exit codes: 0 pass or warnings | 1 fail (only with --strict and a finding) | 2 blocked (no file scanned). Stdlib only.
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

EXTS = {".html", ".js", ".css", ".jsx", ".tsx", ".ts"}
SKIP_DIRS = {"node_modules", ".git", "_work", "renders", "__pycache__"}
SKIP_FILE = re.compile(r"^(motion-kit\.js|gsap.*\.js|.*\.min\.js)$", re.I)
SUPPRESS = re.compile(r"ai-look-ok\s*:\s*\S.{4,}")

LINE_RULES = [
    ("AL01", re.compile(r"""ease\s*:\s*["'](power[0-4]|sine|expo|circ|quad|cubic|quart|quint|strong)(\.(in|out|inOut))?["']""", re.I),
     "named preset easing: choose a curve for this move (MotionKit.curve / bez)"),
    ("AL01", re.compile(r"(animation|transition)(-timing-function)?\s*:[^;{}]*\b(ease|ease-in|ease-out|ease-in-out)\b(?!-)", re.I),
     "CSS preset easing: use a cubic-bezier chosen for the move"),
    ("AL02", re.compile(r"\bgsap\.defaults\s*\("), "gsap.defaults sets one curve and duration for everything"),
    ("AL04", re.compile(r"""ease\s*:\s*["'](bounce|elastic|back)""", re.I), "bounce / elastic / back easing (overshoot on everything reads as a template)"),
    ("AL05", re.compile(r"\bstagger\s*:\s*\{?\s*(each\s*:\s*)?\d*\.?\d+"), "even stagger: lead + uneven reactions (MotionKit.react(i))"),
    ("AL05", re.compile(r"\+\s*\(?\s*[ijk]\s*\*\s*0?\.\d+\b"), "even offset i * N: lead + uneven reactions (MotionKit.react(i))"),
    ("AL08", re.compile(r"text-shadow\s*:[^;]*?-?\d+(\.\d+)?px\s+-?\d+(\.\d+)?px\s+([1-9]\d+)(\.\d+)?px", re.I), "glow on text (text-shadow blur 10px+)"),
    ("AL08", re.compile(r"(-webkit-)?background-clip\s*:\s*text", re.I), "gradient-filled text"),
    ("AL09", re.compile("[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F☀-⛿✀-➿]"), "emoji in the composition"),
    ("AL11", re.compile(r"""font-family\s*:\s*["']?(Inter|Poppins|Montserrat)\b""", re.I), "default UI font as the type system: a reasoned choice in PROMPT.md <direction>"),
]
TWEEN = re.compile(r"\.(?:to|from|fromTo)\s*\(")
VISIBLE = re.compile(r"\b(opacity|autoAlpha|x|y|xPercent|yPercent|scale|scaleX|scaleY|rotation)\s*:")


def iter_files(paths):
    for p in paths:
        p = Path(p)
        if p.is_file():
            if not SKIP_FILE.match(p.name):
                yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in EXTS and not (set(f.parts) & SKIP_DIRS) and not SKIP_FILE.match(f.name):
                    yield f


def call_span(text, start):
    depth, i = 0, start
    while i < len(text) and i < start + 800:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return text[start:start + 800]


def first_object(span):
    m = re.search(r"\{[^{}]*\}", span)
    return m.group(0) if m else ""


def scan_text(name, text):
    out = []
    lines = text.splitlines()

    def add(rid, n, msg):
        line = lines[n - 1] if 0 < n <= len(lines) else ""
        if not SUPPRESS.search(line):
            out.append((rid, f"{name}:{n}", msg, line.strip()[:110]))

    for n, line in enumerate(lines, 1):
        for rid, rx, msg in LINE_RULES:
            if rx.search(line):
                add(rid, n, msg)
    for m in TWEEN.finditer(text):
        span = call_span(text, m.end() - 1)
        n = text.count("\n", 0, m.start()) + 1
        start_state = first_object(span)
        if re.search(r"\bopacity\s*:\s*0(\.0+)?\b", start_state) and re.search(r"\by\s*:\s*['\"]?(1[2-9]|[23]\d|40)(px)?['\"]?\s*[,}]", start_state):
            add("AL03", n, "fade-up preset (opacity 0 + y 12-40 px): decide what the move is (cut on, type on, arc, mask)")
        if re.search(r"""filter\s*:\s*["']?blur\(\s*[1-9]""", span):
            add("AL07", n, "blur in a tween reads as blur-in; blur belongs to fast motion only")
        if re.search(r"""ease\s*:\s*["'](none|linear)["']""", span) and VISIBLE.search(span) and "onUpdate" not in span:
            add("AL06", n, "a visible property on linear easing: linear is only for a proxy that is not itself the motion")
    for m in re.finditer(r"\{[^{}]*\}", text):
        block = m.group(0)
        if re.search(r"text-transform\s*:\s*uppercase", block, re.I) and re.search(r"letter-spacing\s*:\s*(0?\.\d*[1-9]\d*em|[2-9]\d*px|\d+\.\d+px)", block, re.I):
            add("AL10", text.count("\n", 0, m.start()) + 1, "small uppercase tracked label (feature pill): meaning goes through the voice and large type")
    return out


def run(paths, strict=False):
    findings, scanned = [], 0
    for f in iter_files(paths):
        try:
            t = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return [("AL00", str(f), "cannot read file", "")], {"verdict": "blocked", "reason": "unreadable input", "files_scanned": scanned}
        scanned += 1
        findings += scan_text(f"{f.parent.name}/{f.name}", t)
    if scanned == 0:
        verdict, reason = "blocked", "no file scanned (not_run, never pass)"
    elif findings and strict:
        verdict, reason = "fail", f"{len(findings)} tell(s) under --strict"
    elif findings:
        verdict, reason = "warn", f"{len(findings)} tell(s): fix each or write its reason in PROMPT.md (references/anti-ai-look.md)"
    else:
        verdict, reason = "pass", f"{scanned} file(s) free of the scanned tells; still look at the frames"
    return findings, {"verdict": verdict, "reason": reason, "files_scanned": scanned}


GOOD = """<style>.cap{font-family:'Rubik',sans-serif;font-weight:700}</style>
<div class="cap" id="c0">שלום</div>
<script>
const { curve, dur, react } = MotionKit;
const tl = gsap.timeline({ paused: true });
tl.set('#c0', { opacity: 1 }, 0.42);
tl.fromTo('#card', { x: 900 }, { x: 0, duration: dur(900, 1), ease: curve('kit.land') }, 1.0 + react(1));
const proxy = { i: 0 };
tl.fromTo(proxy, { i: 0 }, { i: 99, duration: 3.3, ease: "none", onUpdate: () => {} }, 0);
</script>"""

BAD = """<style>.pill{text-transform:uppercase;letter-spacing:.12em;font-size:18px}
.t{font-family:'Inter',sans-serif;text-shadow:0 0 24px #a0f;-webkit-background-clip:text}
.u{animation:a 1s ease-in-out}</style>
<div>Done ✅</div>
<script>
gsap.defaults({ duration: 0.6, ease: "power3.out" });
const tl = gsap.timeline({ paused: true });
tl.fromTo('#a', { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, 0);
tl.fromTo('#b', { scale: 0 }, { scale: 1, ease: "back.out(2)" }, 0);
tl.to('.row', { opacity: 1, stagger: 0.08 }, 0);
tl.to('#r' + i, { opacity: 1 }, 0.2 + i * 0.1);
tl.fromTo('#c', { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "none" }, 1);
tl.fromTo('#d', { filter: 'blur(12px)' }, { filter: 'blur(0px)' }, 1);
</script>"""


def self_check():
    bad = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "good.html").write_text(GOOD, encoding="utf-8")
        (td / "bad.html").write_text(BAD, encoding="utf-8")
        (td / "motion-kit.js").write_text('ease: "power3.out"\n', encoding="utf-8")
        (td / "ok.js").write_text('tl.to("#a",{x:1, ease:"power2.out"}); // ai-look-ok: matches the client brand film\n', encoding="utf-8")
        f, s = run([td / "good.html"])
        if s["verdict"] != "pass":
            bad.append(f"good.html should pass, got {s} {[x[0] for x in f]}")
        f, s = run([td / "bad.html"])
        got = {x[0] for x in f}
        want = {"AL01", "AL02", "AL03", "AL04", "AL05", "AL06", "AL07", "AL08", "AL09", "AL10", "AL11"}
        if s["verdict"] != "warn" or not want <= got:
            bad.append(f"bad.html should trip {sorted(want - got)} (got {sorted(got)})")
        f, s = run([td / "bad.html"], strict=True)
        if s["verdict"] != "fail":
            bad.append("--strict must fail on a tell")
        f, s = run([td / "motion-kit.js"])
        if s["verdict"] != "blocked":
            bad.append("the vendored motion-kit.js must be skipped")
        f, s = run([td / "ok.js"])
        if s["verdict"] != "pass":
            bad.append("a suppression with a reason must pass")
        f, s = run([td / "none"])
        if s["verdict"] != "blocked":
            bad.append("empty scan must be blocked")
    if bad:
        print("SELF-CHECK FAILED")
        for b in bad:
            print(" -", b)
        return 1
    print("SELF-CHECK OK (6 cases)")
    return 0


def main(argv=None):
    try:
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
        print(json.dumps({"summary": summ, "findings": [dict(rule=r, where=w, message=m, code=c) for r, w, m, c in findings]},
                         ensure_ascii=False, indent=2))
    else:
        for r, w, m, c in findings:
            print(f"[W] {r} {w}: {m}" + (f"   > {c}" if c else ""))
        print(f"VERDICT: {summ['verdict']} - {summ['reason']}")
    return {"pass": 0, "warn": 0, "fail": 1, "blocked": 2}[summ["verdict"]]


if __name__ == "__main__":
    sys.exit(main())

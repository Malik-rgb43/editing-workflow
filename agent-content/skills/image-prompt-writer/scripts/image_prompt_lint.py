#!/usr/bin/env python3
"""image_prompt_lint.py - deterministic lint of still-image prompt drafts (text only, no generation, no spend).

Usage:
    python image_prompt_lint.py DRAFT.md [--ratio 9:16] [--prefix-file FILE] [--text-asset] [--allow-age-words] [--raw] [--json]
    python image_prompt_lint.py --self-check

DRAFT.md is the ANSWER you are about to send: each fenced code block is one prompt; text outside the fences may only be the
`shot_id: ...` header line above each fence and a short follow-up question. `--raw` treats the whole file as ONE prompt (no fences).

Checks (E = error, W = warning)
  I01 E  --prefix-file given: the STYLE PREFIX is present VERBATIM at the start (whitespace and dash variants normalised)
  I02 E  no fenced code block found (or HTML / markdown table / checklist instead of plain text or JSON)
  I03 W  quality charms in the body (cinematic, epic, stunning, masterpiece, 8K, photorealistic, award-winning, ...)
  I04 E  age words (boy, girl, child, kid, young, teen, little, baby, toddler): describe by role, clothing, action
  I05 W  negatives about actions ("don't", "no more", "avoid", "without ..."); allowed exclusions: text, labels, watermark, logo, caption
  I06 W  text instructions inside the picture (subtitle, caption, "the words ...") unless --text-asset;
         E  with --text-asset and no quoted string
  I07 W  more than one quoted text element with --text-asset (one text element per asset)
  I08 E  no aspect ratio stated and --ratio not given (never defaulted silently); E  --ratio given but not in the prompt
  I09 E  a block that starts with "{" must be valid JSON
  I10 W  prose body longer than 250 words (later words lose weight)
  I11 W  no light direction/quality stated;  W  no lens or stock stated
Exit codes: 0 pass | 1 fail (>= 1 error) | 2 blocked (unreadable input, no prompt found).
A pass means the prompt is well-formed; it says nothing about what a model will render. Stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

CHARMS = re.compile(r"\b(cinematic|epic|stunning|beautiful|amazing|masterpiece|breathtaking|ultra-?real(?:istic)?|award-?winning|trending|8k|photorealistic|hyper-?real(?:istic)?)\b", re.I)
AGE = re.compile(r"\b(boy|girl|child|children|kid|kids|young|teen|teens|teenager|little|baby|toddler)\b", re.I)
NEG = re.compile(r"\b(don'?t|doesn'?t|never|avoid|do not|not)\b|\bno\s+(?!text\b|labels?\b|watermarks?\b|logos?\b|captions?\b|subtitles?\b)|\bwithout\s+(?!text\b|labels?\b|watermarks?\b|logos?\b|captions?\b|subtitles?\b)", re.I)
TEXTW = re.compile(r"\b(subtitles?|captions?|text overlay|on-screen text|lower third|title card|the words|reading|that says|written)\b", re.I)
RATIO = re.compile(r"\b(16:9|9:16|1:1|4:5|3:2|2:3|21:9|4:3|3:4)\b")
LIGHT = re.compile(r"\b(light|lit|lighting|sun|sunlight|backlit|rim|softbox|lamp|window|shadow|glow|overcast|daylight|dusk|dawn|flash)\b", re.I)
LENS = re.compile(r"\b(\d{2,3}\s?mm|lens|macro|wide[- ]angle|telephoto|anamorphic|film|kodak|35mm|16mm|bokeh|depth of field)\b", re.I)
FENCE = re.compile(r"```[ \t]*(\S*)[ \t]*[^\n]*\n(.*?)```", re.S)
DASHES = str.maketrans({"—": "-", "–": "-", "−": "-"})
QUOTED = re.compile(r"\"([^\"\n]{1,120})\"|“([^”\n]{1,120})”")


def squash(s):
    return re.sub(r"\s+", " ", s.translate(DASHES)).strip().lower()


def lint_block(block, ratio=None, prefix=None, text_asset=False, allow_age=False, label="prompt"):
    f = []

    def add(sev, code, msg):
        f.append((sev, code, f"{label}: {msg}"))

    stripped = block.strip()
    is_json = stripped.startswith("{")
    if prefix and not squash(block).startswith(squash(prefix)):
        add("error", "I01", "the STYLE PREFIX is not present verbatim at the start (do not paraphrase or shorten it)")
    body = block
    if prefix and squash(block).startswith(squash(prefix)):
        acc = ""
        for i, ch in enumerate(block):
            acc += ch
            if squash(acc) == squash(prefix):
                body = block[i + 1:]
                break
    if is_json:
        try:
            json.loads(stripped)
        except ValueError as e:
            add("error", "I09", f"invalid JSON: {e}")
    scan = body if not is_json else re.sub(r'"(?:string|text)"\s*:\s*"[^"]*"', "", body) if not text_asset else body
    if CHARMS.search(scan):
        add("warn", "I03", "quality charms in the body (%s): name a lens, a light, a number instead" % ", ".join(sorted({m.group(0).lower() for m in CHARMS.finditer(scan)})))
    if not allow_age and AGE.search(scan):
        add("error", "I04", "age words (%s): describe by role, clothing, action" % ", ".join(sorted({m.group(0).lower() for m in AGE.finditer(scan)})))
    negs = [m.group(0) for m in NEG.finditer(scan)]
    if negs:
        add("warn", "I05", "negative phrasing (%s): write what IS in frame; allowed exclusions are text, labels, watermark" % ", ".join(sorted({n.strip().lower() for n in negs})))
    quotes = [m.group(1) or m.group(2) for m in QUOTED.finditer(body)]
    if text_asset:
        if not quotes:
            add("error", "I06", "--text-asset but no quoted text string: give the exact string in quotes, in its own language")
        elif len(quotes) > 1 and not is_json:
            add("warn", "I07", "more than one quoted text element (%d): one text element per asset" % len(quotes))
        elif is_json and len(quotes) > 4:
            add("warn", "I07", "many quoted strings (%d): one text element per asset" % len(quotes))
    elif TEXTW.search(scan):
        add("warn", "I06", "text instruction inside the picture (%s): text is added in post" % TEXTW.search(scan).group(0))
    found = set(RATIO.findall(block))
    if ratio:
        if ratio not in found:
            add("error", "I08", f"the ratio {ratio} is not stated in the prompt")
    elif not found:
        add("error", "I08", "no aspect ratio stated: never default it silently (16:9, 9:16, 1:1, 4:5, ...)")
    if not is_json:
        words = len(re.findall(r"\S+", body))
        if words > 250:
            add("warn", "I10", f"{words} words: keep a prose prompt under about 250")
    if not LIGHT.search(scan):
        add("warn", "I11", "no light direction or quality stated")
    if not LENS.search(scan):
        add("warn", "I11", "no lens or stock stated")
    return f


def lint(text, ratio=None, prefix=None, text_asset=False, allow_age=False, raw=False):
    blocks = [text] if raw else [m.group(2) for m in FENCE.finditer(text)]
    if not blocks or not any(b.strip() for b in blocks):
        return [("error", "I02", "no fenced code block found: the answer must be plain-text or JSON prompts in code fences")], {"verdict": "blocked", "reason": "no prompt found", "prompts": 0}
    findings = []
    outside = FENCE.sub("", text) if not raw else ""
    if re.search(r"<(html|table|div|ul|ol)\b|^\s*\|.+\|\s*$|^\s*- \[[ x]\]", outside + "\n".join(blocks), re.M | re.I):
        findings.append(("error", "I02", "HTML, a markdown table or a checklist found: output plain-text or JSON fences only"))
    outside = "\n".join(ln for ln in outside.splitlines() if not ln.strip().lower().startswith("shot_id:"))
    if len(outside.split()) > 120:
        findings.append(("warn", "I02", "long text outside the fences: keep the answer to fences + prefix + at most one question"))
    for i, b in enumerate(blocks, 1):
        findings += lint_block(b, ratio, prefix, text_asset, allow_age, f"prompt {i}")
    errs = [f for f in findings if f[0] == "error"]
    return findings, {"verdict": "fail" if errs else "pass", "reason": f"{len(errs)} error(s), {len(findings) - len(errs)} warning(s)", "prompts": len(blocks)}


GOOD_B = '''```
STYLE: 35 mm film look, muted teal and warm amber (#2B6F77, #D9A441), fine grain, no text, no labels.
9:16 still frame. A courier in a yellow rain jacket, mid-stride across a wet tram platform, glancing back over her shoulder.
Light: low sun from camera left, long soft shadows, haze in the air. Lens: 35 mm, eye level, shallow depth of field.
Composition: subject on the left third, empty space on the right for a headline added in post. No text, no labels, no watermark.
```
Want it in 16:9 as well?'''
GOOD_A = '''```
{"type": "character reference sheet", "style": "35 mm film look, fine grain", "format": {"aspect": "16:9", "light": "even softbox, no harsh shadow", "lens": "85 mm"}, "regions": [{"id": 1, "view": "front"}, {"id": 2, "view": "three-quarter"}, {"id": 3, "view": "side"}], "rules": ["identical face and wardrobe in every region", "no text, no labels, no watermark"]}
```'''


def self_check():
    bad = []
    prefix = "STYLE: 35 mm film look, muted teal and warm amber (#2B6F77, #D9A441), fine grain, no text, no labels."
    f, st = lint(GOOD_B, "9:16", prefix)
    if st["verdict"] != "pass":
        bad.append(f"good prose prompt must pass: {f}")
    f, st = lint(GOOD_A, "16:9")
    if st["verdict"] != "pass":
        bad.append(f"good JSON prompt must pass: {f}")
    cases = {
        "I01": (GOOD_B.replace("35 mm film look", "cinematic look"), "9:16", prefix, False),
        "I02": ("just some words, no fence", None, None, False),
        "I04": (GOOD_B.replace("A courier", "A young boy courier"), "9:16", None, False),
        "I08": (GOOD_B.replace("9:16 still frame", "still frame"), None, None, False),
        "I09": ('```\n{"a": 1,}\n```', None, None, False),
        "I06": (GOOD_B.replace("Composition:", "Composition: a caption reading the title, ").replace("added in post", "in frame"), "9:16", None, False),
    }
    for code, (txt, ratio, pre, ta) in cases.items():
        f, st = lint(txt, ratio, pre, ta)
        if code not in {c for _s, c, _m in f}:
            bad.append(f"{code} not detected: {f}")
    f, st = lint(GOOD_B.replace("Light: low sun from camera left, long soft shadows, haze in the air. ", "").replace("Lens: 35 mm, eye level, shallow depth of field.", ""), "9:16", None)
    if "I11" not in {c for _s, c, _m in f}:
        bad.append("missing light/lens must warn I11")
    f, st = lint(GOOD_B.replace("35 mm film look", "stunning cinematic 8K masterpiece"), "9:16", None)
    if "I03" not in {c for _s, c, _m in f}:
        bad.append("quality charms must warn I03")
    f, st = lint(GOOD_B.replace("mid-stride", "not falling, mid-stride"), "9:16", None)
    if "I05" not in {c for _s, c, _m in f}:
        bad.append("an action negative must warn I05")
    f, st = lint('```\nA street sign that says "OPEN" at dusk, 9:16, 50 mm, backlit.\n```', "9:16", None, True)
    if st["verdict"] != "pass":
        bad.append(f"text-asset with ONE quoted string must pass: {f}")
    f, st = lint('```\nA street sign at dusk, 9:16, 50 mm, backlit.\n```', "9:16", None, True)
    if "I06" not in {c for _s, c, _m in f}:
        bad.append("--text-asset without a quoted string must fail I06")
    f, st = lint('```\nA street sign at dusk, 9:16, 50 mm, backlit.\n```', "1:1", None)
    if "I08" not in {c for _s, c, _m in f}:
        bad.append("a ratio missing from the prompt must fail I08")
    ids = "\n".join("shot_id: b%d · 9:16 · target: _work/stills/b%d.png" % (k, k) for k in range(1, 30))
    f, st = lint(ids + "\n" + GOOD_B, "9:16", prefix)
    if st["verdict"] != "pass" or any(c == "I02" for _s, c, _m in f):
        bad.append(f"shot_id header lines must not count as text outside the fences: {f}")
    if bad:
        print("SELF-CHECK FAILED")
        for b in bad:
            print(" -", b)
        return 1
    print("SELF-CHECK OK (17 cases)")
    return 0


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("draft", nargs="?")
    ap.add_argument("--ratio")
    ap.add_argument("--prefix-file")
    ap.add_argument("--text-asset", action="store_true")
    ap.add_argument("--allow-age-words", action="store_true")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.draft:
        ap.print_usage()
        return 2
    try:
        text = Path(a.draft).read_text(encoding="utf-8")
        prefix = Path(a.prefix_file).read_text(encoding="utf-8").strip() if a.prefix_file else None
    except OSError as e:
        print(f"BLOCKED: {e}")
        return 2
    f, st = lint(text, a.ratio, prefix, a.text_asset, a.allow_age_words, a.raw)
    if a.json:
        print(json.dumps({"summary": st, "findings": [{"severity": s, "code": c, "message": m} for s, c, m in f]}, ensure_ascii=False, indent=2))
    else:
        for s, c, m in f:
            print(f"[{s.upper():5}] {c}: {m}")
        print(f"VERDICT: {st['verdict']} - {st['reason']} ({st.get('prompts', 0)} prompt(s))")
        print("note: a pass means well-formed; no generation was run and nothing here predicts what the model renders.")
    return {"pass": 0, "fail": 1, "blocked": 2}[st["verdict"]]


if __name__ == "__main__":
    sys.exit(main())

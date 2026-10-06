#!/usr/bin/env python3
"""seedance_prompt_lint.py - deterministic lint of Seedance prompt drafts (text only, no generation, no spend).

Usage:
    python seedance_prompt_lint.py DRAFT.md [--preset owner-cinematic|vendor-short|custom]
                                   [--prefix-file FILE] [--duration 15] [--tags a,b,c]
                                   [--presets-file ../references/presets.md] [--look-file FILE] [--raw] [--allow-age-words] [--json]
    python seedance_prompt_lint.py --self-check

DRAFT.md is the ANSWER you are about to send: each fenced code block is one prompt; text outside the fences
may only be the `shot_id: ...` line above each fence and a short follow-up question. `--raw` treats the whole
file as ONE prompt (no fences). Seedance only: for Kling, Veo, Hailuo and other models this lint is n/a.

Owner preset (skeleton from references/skeleton-and-fill-in.md)
  P01 E  the preset prefix is present VERBATIM at the start (whitespace and dash variants normalised)
  P02 E  headings SUBJECT, LOCATION, [LAYOUT], ACTION, CAMERA, STYLE, CONSTRAINTS appear in that order
  P03 E  SHOT n (m:ss-m:ss) lines: start at 0:00, contiguous, ending at --duration (default 15 s, no dead air);
         W  fewer than 2 or more than 6 shots in 15 s; W  no "Hard cut" between shots
  P04 E  CAMERA has one `SHOT k:` entry per shot
  P05 W  a subject @tag without "matches input 100%";  E  an @tag not in --tags;  W  a registered tag never used
  P06 E  CONSTRAINTS states a ratio (16:9, 9:16, 1:1, 4:5, 21:9): never defaulted silently
Vendor-short profile
  V01 E  Camera:, Style:, Constraints: lines present;  V02 W  main block outside 60-100 words (E above 300)
  V03 E  three or more distinct camera moves in Camera: (W for two: one primary + one subtle at most)
  V04 E  Constraints lacks a ratio or a duration
All profiles
  P07 W  quality charms in the scene body (epic, amazing, beautiful, stunning, masterpiece, breathtaking, ...); "cinematic" alone
  P09 W  negatives in the scene body (ACTION/CAMERA; vendor-short: the whole main block) - phrase positively
  P10 I  numeric speeds/angles: km/h or degrees = the vendor/owner [CONFLICT] (owner presets: W "generalize physics")
  P11 E  age words (boy, girl, child, kid, young, teen, little, baby, toddler): describe by role, clothing, action
  P12 W  on-screen text/subtitle/caption instructions in the body (text is added in post)
  P13 E  output is not plain-text fences (HTML, markdown table, checklist) or no fence found; W long text outside the fences
  P14 W  the word "fast" in the scene body (one fast element; a duration instead)
  P15 E  --look-file given: the film's LOOK (the image STYLE PREFIX shared with the stills) is not in the prompt verbatim
Exit codes: 0 pass | 1 fail (>= 1 error) | 2 blocked (unreadable, no prompt found, presets file missing).
A pass means the prompt is well-formed against the skeleton; it says nothing about what the model will render.
Stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HEADS = ["SUBJECT", "LOCATION", "LAYOUT", "ACTION", "CAMERA", "STYLE", "CONSTRAINTS"]
REQUIRED = ["SUBJECT", "LOCATION", "ACTION", "CAMERA", "STYLE", "CONSTRAINTS"]
CHARMS = re.compile(r"\b(epic|amazing|beautiful|stunning|masterpiece|breathtaking|ultra-?real|award-?winning|immersive|ethereal|8k|photorealistic|hyper-?real(?:istic)?)\b", re.I)
NEG = re.compile(r"\b(no|not|don'?t|doesn'?t|never|without|avoid)\b", re.I)
AGE = re.compile(r"\b(boy|girl|child|children|kid|kids|young|teen|teens|teenager|little|baby|toddler)\b", re.I)
SPEED = re.compile(r"\b\d+(?:\.\d+)?\s*(?:km/h|kph|mph|m/s)\b|\b\d+(?:\.\d+)?\s*°|\b\d+\s*degrees?\b", re.I)
TEXTW = re.compile(r"\b(subtitles?|captions?|text overlay|on-screen text|lower third|title card)\b", re.I)
RATIO = re.compile(r"\b(16:9|9:16|1:1|4:5|21:9|4:3)\b")
MOVES = ["push-in", "pull-out", "dolly", "pan", "tilt", "orbit", "tracking", "crane", "zoom", "handheld", "whip", "arc", "truck"]
FENCE = re.compile(r"```[ \t]*(\S*)[ \t]*([^\n]*)\n(.*?)```", re.S)
DASHES = str.maketrans({"—": "-", "–": "-", "−": "-"})


def squash(s):
    return re.sub(r"\s+", " ", s.translate(DASHES)).strip().lower()


def load_presets(path):
    text = Path(path).read_text(encoding="utf-8")
    out = {}
    for m in FENCE.finditer(text):
        info = m.group(2)
        pm = re.search(r"preset=([\w-]+)", info)
        if pm:
            out[pm.group(1)] = m.group(3).strip()
    return out


def sections(text):
    idx = [(m.start(), m.group(1)) for m in re.finditer(r"^(SUBJECT|LOCATION|LAYOUT|ACTION|CAMERA|STYLE|CONSTRAINTS)\s*[—–-]", text, re.M)]
    out = []
    for i, (pos, name) in enumerate(idx):
        end = idx[i + 1][0] if i + 1 < len(idx) else len(text)
        out.append((name, text[pos:end]))
    return out


def tsec(m, s):
    return int(m) * 60 + int(s)


def lint_block(block, presets, preset=None, duration=15, tags=None, allow_age=False, prefix_text=None, label="prompt", look=None):
    f = []

    def add(sev, code, msg):
        f.append((sev, code, f"{label}: {msg}"))
    norm = squash(block)
    if look and squash(look) not in norm:
        add("error", "P15", "the film's LOOK (image STYLE PREFIX) is not in the prompt verbatim: paste it as `LOOK:` in STYLE (or as the vendor-short Style: line)")
    detected = preset
    if detected is None:
        for name in ("owner-cinematic",):
            if name in presets and norm.startswith(squash(presets[name])[:80]):
                detected = name
                break
        if detected is None and re.search(r"^Camera:", block, re.M) and re.search(r"^Constraints:", block, re.M):
            detected = "vendor-short"
    if detected is None:
        add("error", "P01", "no preset detected: start with the preset prefix verbatim (owner-cinematic), use the vendor-short shape, or pass --preset custom --prefix-file")
        return f, None
    body = block
    if detected in ("owner-cinematic", "custom"):
        pre = prefix_text if detected == "custom" else presets.get(detected)
        if not pre:
            add("error", "P01", f"preset '{detected}' text not available (presets file or --prefix-file missing)")
            return f, detected
        if not norm.startswith(squash(pre)):
            add("error", "P01", f"preset '{detected}' prefix is not present verbatim at the start (do not paraphrase or shorten it)")
            body = block
        else:
            body = block[len(block) - len(block.lstrip()):]
            cut = squash(pre)
            # remove the prefix from the body by walking original text until normalised lengths match
            acc = ""
            for i, ch in enumerate(block):
                acc += ch
                if squash(acc) == cut:
                    body = block[i + 1:]
                    break
        secs = sections(body)
        names = [n for n, _ in secs]
        order = [n for n in HEADS if n in names]
        if names != order:
            add("error", "P02", f"headings out of order: found {names}, expected {[n for n in HEADS if n in names]}")
        for r in REQUIRED:
            if r not in names:
                add("error", "P02", f"missing heading {r} —")
        sec = dict(secs)
        action = sec.get("ACTION", "")
        shots = [(int(m.group(1)), tsec(m.group(2), m.group(3)), tsec(m.group(4), m.group(5)))
                 for m in re.finditer(r"^SHOT\s+(\d+)\s*\(\s*(\d+):(\d{2})\s*[–—-]\s*(\d+):(\d{2})\s*\)", action, re.M)]
        if not shots:
            add("error", "P03", "ACTION has no 'SHOT n (m:ss–m:ss)' lines")
        else:
            if shots[0][1] != 0:
                add("error", "P03", "first shot does not start at 0:00")
            for a, b in zip(shots, shots[1:]):
                if b[1] != a[2]:
                    add("error", "P03", f"shot {b[0]} starts at {b[1]}s but shot {a[0]} ends at {a[2]}s (gap/overlap)")
            if shots[-1][2] != duration:
                add("error", "P03", f"timecodes end at {shots[-1][2]}s, expected {duration}s (fill the whole clip, no dead air; split long scenes into Na/Nb)")
            if duration >= 12 and not (2 <= len(shots) <= 6):
                add("warn", "P03", f"{len(shots)} shots in {duration}s (12-15 s clips carry 2-3 beats, up to 6 in the community table)")
            if len(shots) >= 2 and not re.search(r"hard cut", action, re.I):
                add("warn", "P03", "no 'Hard cut' between shots")
            cam = sec.get("CAMERA", "")
            have = {int(x) for x in re.findall(r"SHOT\s+(\d+)\s*:", cam)}
            miss = [s[0] for s in shots if s[0] not in have]
            if miss:
                add("error", "P04", f"CAMERA lacks entries for shot(s) {miss} (angle, height, lens feel, movement, WHY)")
        cons = sec.get("CONSTRAINTS", "")
        if not RATIO.search(cons):
            add("error", "P06", "CONSTRAINTS names no ratio (take it from the delivery; never default to 16:9 silently)")
        scene = "\n".join(t for n, t in secs if n in ("ACTION", "CAMERA"))
        subj = sec.get("SUBJECT", "")
        used = set(re.findall(r"@([\w-]+)", body))
        for tag in sorted(set(re.findall(r"@([\w-]+)", subj))):
            if not re.search(rf"@{re.escape(tag)}[^.]*matches input 100%", subj, re.I):
                add("warn", "P05", f"subject tag @{tag} lacks 'matches input 100%'")
        if tags is not None:
            for t in sorted(used - set(tags)):
                add("error", "P05", f"@{t} is not in the asset registry {sorted(tags)} (tag must match the Element name exactly)")
            for t in sorted(set(tags) - used):
                add("warn", "P05", f"registered tag @{t} is never used")
        if NEG.search(scene):
            add("warn", "P09", "negative wording in ACTION/CAMERA: describe what IS in frame (negatives belong in CONSTRAINTS)")
        if SPEED.search(body):
            add("warn", "P10", "numeric speed/angle: the author says generalize physics, the vendor says km/h - [CONFLICT] unresolved; see owner-vs-vendor-conflict.md")
        scene_all = "\n".join(t for n, t in secs if n not in ("CONSTRAINTS",))
        text_scope = scene_all
    else:  # vendor-short
        if not (re.search(r"^Camera:", block, re.M) and re.search(r"^Style:", block, re.M) and re.search(r"^Constraints:", block, re.M)):
            add("error", "V01", "need 'Camera:', 'Style:' and 'Constraints:' lines")
        m = re.search(r"^Camera:", block, re.M)
        main = block[:m.start()] if m else block
        main = "\n".join(ln for ln in main.splitlines() if ln.strip() and not re.fullmatch(r"(@[\w-]+[\s,]*)+", ln.strip()))
        words = len(re.findall(r"\S+", main))
        if words > 300:
            add("error", "V02", f"main block {words} words (> 300: the model loses the prompt)")
        elif not (60 <= words <= 100):
            add("warn", "V02", f"main block {words} words (vendor budget 60-100)")
        cam = re.search(r"^Camera:(.*)$", block, re.M)
        if cam:
            mv = {x for x in MOVES if x in cam.group(1).lower()}
            if len(mv) >= 3:
                add("error", "V03", f"camera moves {sorted(mv)}: one primary move + at most one subtle secondary")
            elif len(mv) == 2:
                add("warn", "V03", f"two camera moves {sorted(mv)}: keep the second one subtle")
        cons = re.search(r"^Constraints:(.*)$", block, re.M)
        if cons and not (RATIO.search(cons.group(1)) and re.search(r"\b\d+\s*s\b", cons.group(1))):
            add("error", "V04", "Constraints must state the duration (e.g. 10s) and the ratio (from the delivery, not habit)")
        if NEG.search(main):
            add("warn", "P09", "negative wording in the main block: everything positive (the only permitted negative is the standard quality line in Constraints)")
        if SPEED.search(block):
            add("info", "P10", "numeric speed present (vendor style); owner presets would say 'generalize physics' - [CONFLICT] unresolved")
        text_scope = main
        body = block
    if AGE.search(body) and not allow_age:
        add("error", "P11", f"age word '{AGE.search(body).group(0)}': describe by role, clothing and action (use --allow-age-words only for a non-Seedance model)")
    if CHARMS.search(text_scope):
        add("warn", "P07", f"quality charm '{CHARMS.search(text_scope).group(0)}' in the scene body (name a lens, light direction, movement or number instead)")
    if re.search(r"(?<![\w-])cinematic(?![\w-])", text_scope, re.I):
        add("warn", "P07", "'cinematic' alone in the scene body (undefined: name the lens/contrast/stock)")
    if TEXTW.search(text_scope):
        add("warn", "P12", "text/subtitle/caption wording in the scene body (text is added in post; Seedance distorts generated text)")
    if re.search(r"\bfast\b", text_scope, re.I):
        add("warn", "P14", "the word 'fast' (one fast element; use a duration or one specific movement)")
    return f, detected


def lint(text, presets, preset=None, duration=15, tags=None, raw=False, allow_age=False, prefix_text=None, look=None):
    f = []
    if not text.strip():
        return [("error", "P13", "empty draft")], {"verdict": "blocked", "reason": "empty input", "prompts": 0}
    blocks = [(m.group(2), m.group(3).strip()) for m in FENCE.finditer(text)]
    outside = FENCE.sub("", text)
    if raw:
        blocks, outside = [("", text.strip())], ""
    if re.search(r"<\s*(table|html|div|script|body)\b", text, re.I) or re.search(r"^\s*\|.*\|\s*$", outside, re.M) or re.search(r"^\s*[-*]\s*\[[ xX]\]", outside, re.M):
        f.append(("error", "P13", "HTML/table/checklist found: output must be copy-ready plain-text code fences"))
    if not blocks:
        f.append(("error", "P13", "no fenced code block found (each prompt goes in a ``` fence); use --raw only for a bare prompt"))
        return f, {"verdict": "blocked", "reason": "no prompt found", "prompts": 0}
    outside_words = "\n".join(ln for ln in outside.splitlines() if not ln.strip().lower().startswith("shot_id:"))
    if len(re.findall(r"\S+", outside_words)) > 80:
        f.append(("warn", "P13", "more than ~80 words outside the fences (after the prompt only one short follow-up question is allowed)"))
    det = []
    for i, (info, blk) in enumerate(blocks, 1):
        im = dict(re.findall(r"(\w+)=([^\s]+)", info))
        pf, d = lint_block(blk, presets, im.get("preset") or preset, int(im.get("dur", duration)),
                           set(im["tags"].split(",")) if im.get("tags") else tags, allow_age, prefix_text, label=f"prompt {i}", look=look)
        f += pf
        det.append(d)
    errs = [x for x in f if x[0] == "error"]
    verdict = "fail" if errs else "pass"
    return f, {"verdict": verdict, "reason": f"{len(errs)} error(s)" if errs else "well-formed against the skeleton", "prompts": len(blocks), "presets": det}


# ---------------------------------------------------------------- self-check
def self_check(presets_path):
    try:
        presets = load_presets(presets_path)
    except OSError as e:
        print(f"SELF-CHECK BLOCKED: presets file unreadable: {e}")
        return 2
    bad = []
    if "owner-cinematic" not in presets:
        print("SELF-CHECK FAILED: presets file lacks the author-cinematic block")
        return 1
    ex_path = Path(presets_path).with_name("examples.md")
    ex = ex_path.read_text(encoding="utf-8") if ex_path.exists() else ""
    blocks = [(m.group(2), m.group(3)) for m in FENCE.finditer(ex) if "example=" in m.group(2)]
    if len(blocks) < 2:
        bad.append(f"examples.md must contain >= 2 fenced blocks tagged example=N (found {len(blocks)})")
    for info, blk in blocks:
        im = dict(re.findall(r"(\w+)=([^\s]+)", info))
        f, st = lint("```text\n" + blk + "```\n", presets, im.get("preset"), int(im.get("dur", 15)),
                     set(im["tags"].split(",")) if im.get("tags") else None)
        errs = [x for x in f if x[0] == "error"]
        if errs:
            bad.append(f"example {im.get('example')} should lint clean: {errs[:3]}")
    cin = presets["owner-cinematic"]

    def mk(prefix, body):
        return "```text\n" + prefix + "\n\n" + body + "\n```\n"
    body_ok = ("SUBJECT — @a (matches input 100%) walks a pier. WB 5600K. MULTISHOT.\n\n"
               "LOCATION — @b is a STYLE REFERENCE ONLY, not a fixed keyframe. Grey harbour.\n\n"
               "ACTION — A walk.\nSHOT 1 (0:00–0:07) — She walks to the end. Hard cut.\nSHOT 2 (0:07–0:15) — She looks back. Hard cut.\n\n"
               "CAMERA — SHOT 1: eye level, 35mm, slow tracking. SHOT 2: low angle, 24mm, locked-off.\n\n"
               "STYLE — Dominant 60% grey / Secondary 30% blue / Accent 10% amber. WB 5600K.\n\n"
               "CONSTRAINTS — 16:9. NO slow-motion. NO eye glow.")

    def expect(name, text, codes=(), absent=(), verdict=None, **kw):
        f, st = lint(text, presets, **kw)
        got = {c for _, c, _ in f}
        sev = {c for s, c, _ in f if s == "error"}
        if verdict and st["verdict"] != verdict:
            bad.append(f"{name}: verdict {st['verdict']} != {verdict} ({sorted(got)})")
        for c in codes:
            if c not in got:
                bad.append(f"{name}: expected {c}, got {sorted(got)}")
        for c in absent:
            if c in sev:
                bad.append(f"{name}: unexpected error {c}")
    expect("clean-cinematic", mk(cin, body_ok), verdict="pass", preset="owner-cinematic", tags={"a", "b"})
    expect("missing-prefix", mk("Style: nice film", body_ok), ("P01",), verdict="fail")
    expect("truncated-prefix", mk(cin.splitlines()[0], body_ok), ("P01",), verdict="fail", preset="owner-cinematic")
    expect("dead-air", mk(cin, body_ok.replace("0:07–0:15", "0:07–0:12")), ("P03",), verdict="fail", preset="owner-cinematic")
    expect("gap", mk(cin, body_ok.replace("SHOT 2 (0:07", "SHOT 2 (0:08")), ("P03",), preset="owner-cinematic")
    expect("no-camera-entry", mk(cin, body_ok.replace(" SHOT 2: low angle, 24mm, locked-off.", "")), ("P04",), preset="owner-cinematic")
    expect("no-ratio", mk(cin, body_ok.replace("16:9. ", "")), ("P06",), preset="owner-cinematic")
    expect("unknown-tag", mk(cin, body_ok.replace("@b is", "@zzz is")), ("P05",), preset="owner-cinematic", tags={"a", "b"})
    expect("age-word", mk(cin, body_ok.replace("She walks to the end", "A little girl walks to the end")), ("P11",), preset="owner-cinematic")
    expect("age-allowed", mk(cin, body_ok.replace("She walks to the end", "A little girl walks to the end")), absent=("P11",), preset="owner-cinematic", allow_age=True)
    expect("charm-and-negative", mk(cin, body_ok.replace("She walks to the end", "She does not stop; an epic stunning walk")), ("P07", "P09"), preset="owner-cinematic")
    expect("speed", mk(cin, body_ok.replace("She walks to the end", "She walks at 5 km/h")), ("P10",), preset="owner-cinematic")
    expect("html-output", "<table><tr><td>shot</td></tr></table>\n" + mk(cin, body_ok), ("P13",), verdict="fail", preset="owner-cinematic")
    expect("no-fence", "just some prose", ("P13",), verdict="blocked")
    expect("empty", "", verdict="blocked")
    vend = ("```text\n@courier\n\n" + " ".join(["A courier in a red jacket rides a cargo bike across a wet stone plaza at 15 km/h past a fountain on her left and stops at a cafe door where a barista hands her a paper bag with steam rising as she tucks it into the basket and pushes off again."] * 1)
            + "\nCamera: tracking shot at wheel height.\nStyle: overcast daylight, 35mm film tone.\nConstraints: avoid jitter and bent limbs. SFX only, no music, no subtitles. 10s. 16:9.\n```\n")
    expect("vendor-short-length-warning", vend, ("V02",), preset="vendor-short")
    expect("vendor-3-moves", vend.replace("tracking shot at wheel height", "push-in, pan and orbit"), ("V03",), verdict="fail", preset="vendor-short")
    expect("vendor-no-duration", vend.replace(" 10s.", ""), ("V04",), verdict="fail", preset="vendor-short")
    look = "35 mm film look, grey and amber (#5A6670, #C8923A), fine grain, no text, no labels."
    with_look = body_ok.replace("STYLE — ", "STYLE — LOOK: " + look + " ")
    expect("look-present", mk(cin, with_look), verdict="pass", preset="owner-cinematic", tags={"a", "b"}, look=look)
    expect("look-missing", mk(cin, body_ok), ("P15",), verdict="fail", preset="owner-cinematic", look=look)
    expect("charm-8k", mk(cin, body_ok.replace("She walks to the end", "She walks to the end, 8K photorealistic")), ("P07",), preset="owner-cinematic")
    many_ids = "\n".join("shot_id: b%d · 16:9 · start frame: _work/stills/b%d.png" % (k, k) for k in range(1, 15))
    f, _st = lint(many_ids + "\n" + mk(cin, body_ok), presets, preset="owner-cinematic")
    if any(c == "P13" for _s, c, _m in f):
        bad.append("shot_id header lines must not count as text outside the fences")
    if bad:
        print("SELF-CHECK FAILED")
        for b in bad:
            print(" -", b)
        return 1
    print(f"SELF-CHECK OK ({len(blocks)} examples lint clean + 22 further cases)")
    return 0


def main(argv=None):
    try:  # Hebrew paths / non-ASCII messages must not crash on a legacy console code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    here = Path(__file__).resolve().parent.parent / "references" / "presets.md"
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("draft", nargs="?")
    ap.add_argument("--preset", choices=["owner-cinematic", "vendor-short", "custom"])
    ap.add_argument("--prefix-file")
    ap.add_argument("--duration", type=int, default=15)
    ap.add_argument("--tags")
    ap.add_argument("--presets-file", default=str(here))
    ap.add_argument("--look-file", help="the film's image STYLE PREFIX (from image-prompt-writer / hf/DESIGN.md); P15 checks it is in every prompt")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--allow-age-words", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check(a.presets_file)
    if not a.draft:
        ap.print_usage()
        return 2
    try:
        presets = load_presets(a.presets_file)
        text = Path(a.draft).read_text(encoding="utf-8")
        prefix = Path(a.prefix_file).read_text(encoding="utf-8").strip() if a.prefix_file else None
        look = Path(a.look_file).read_text(encoding="utf-8").strip() if a.look_file else None
    except OSError as e:
        print(f"BLOCKED: {e}")
        return 2
    tags = set(a.tags.split(",")) if a.tags else None
    f, st = lint(text, presets, a.preset, a.duration, tags, a.raw, a.allow_age_words, prefix, look)
    if a.json:
        print(json.dumps({"summary": st, "findings": [{"severity": s, "code": c, "message": m} for s, c, m in f]}, ensure_ascii=False, indent=2))
    else:
        for s, c, m in f:
            print(f"[{s.upper():5}] {c}: {m}")
        print(f"VERDICT: {st['verdict']} - {st['reason']} ({st.get('prompts', 0)} prompt(s))")
        print("note: a pass means well-formed against the skeleton; no generation was run and nothing here predicts what the model renders.")
    return {"pass": 0, "fail": 1, "blocked": 2}[st["verdict"]]


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""caption_lint.py - lint a Hebrew caption PLAN (data/captions.json) for timing, exit, rail and bidi (stdlib only).

It checks the plan file. It does not decode video: run caption_qa and frame_qa on the render and
quote their coverage statement. A passing plan is execution evidence for gates G5-G8 of
hebrew-captions-asr, not appearance evidence.

Usage:
    python -X utf8 caption_lint.py lint data/captions.json [--json report.json] [--rail-bottom 1450]
    python -X utf8 caption_lint.py contrast R,G,B "#RRGGBB" [--min 4.5]       # strip mean colour vs text colour
    python -X utf8 caption_lint.py --self-check

captions.json:
    {"fps": 30, "canvas": [1080, 1920], "mode": "cards",            # cards | word_pop | sentence
     "cards": [{"id": "c1", "start": 1.2, "end": 2.4, "bottom_y": 1240, "exit_frames": 4, "anim_unit": "word",
                "words": [{"text": "word", "start": 1.2, "voice_start": 1.3, "keyword": true,
                           "lookalike_checked": true, "isolated": false}]}]}
Times are seconds in the OUTPUT timeline. A word is visible from its start until the card's end.

House preset v1 defaults (decision default Q5, overridable in the file or by flags):
    word >= 0.25 s visible; card >= 0.9 s (cards) / 0.35 s (word_pop) / 0.833 s (sentence);
    <= 3 words per card (cards, word_pop) / 6 (sentence); exit >= 3 frames; swap overlap 1-2 frames
    when the gap between cards is <= 0.35 s (continuous speech); rail bottom <= y 1450.

Exit codes: 0 PASS, 1 FAIL or INSUFFICIENT_EVIDENCE (fail closed), 2 usage error.
"""
import json
import re
import sys

VERSION = "0.1.0"
STATES = ("pass", "fail", "blocked", "n/a")
LOOKALIKE = set("וזדרהח")
OVERRIDES = {"‪", "‫", "‬", "‭", "‮"}
ISOLATE_OPEN = {"⁦", "⁧", "⁨"}
ISOLATE_CLOSE = "⁩"
MARKS = {"‎", "‏", "؜"}
HEB = re.compile("[֐-׿]")
NEEDS_ISO = re.compile("[A-Za-z0-9₪$%]")
MODES = {"cards": (0.9, 3), "word_pop": (0.35, 3), "sentence": (0.833, 6)}


def chk(cid, gate, state, reason):
    assert state in STATES
    return {"id": cid, "gate": gate, "state": state, "reason": reason}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def lint(doc, rail_override=None):
    checks, warnings = [], []
    miss = [k for k in ("fps", "cards") if k not in doc]
    if miss or not _num(doc.get("fps")) or doc["fps"] <= 0:
        return [chk("C0", "schema", "blocked", "need positive fps and a cards list")], warnings, {}
    cards = doc["cards"]
    if not cards:
        return [chk("C0", "schema", "blocked", "no cards: nothing to check")], warnings, {}
    fps = float(doc["fps"])
    mode = doc.get("mode", "cards")
    if mode not in MODES:
        return [chk("C0", "schema", "blocked", "unknown mode %r" % mode)], warnings, {}
    min_card, max_words = MODES[mode]
    word_min = doc.get("word_min_s", 0.25)
    rail = rail_override if rail_override is not None else doc.get("rail_bottom_y", 1450)
    swap_gap = doc.get("swap_gap_s", 0.35)
    nwords = sum(len(c.get("words", [])) for c in cards)
    cov = {"cards": len(cards), "words": nwords, "fps": fps, "mode": mode,
           "span_s": [min(c["start"] for c in cards), max(c["end"] for c in cards)]}
    checks.append(chk("C0", "schema", "pass", "%d cards, %d words, mode %s" % (len(cards), nwords, mode)))

    bad_neg = [c["id"] for c in cards if c["start"] < 0] + [
        "%s/word" % c["id"] for c in cards for w in c.get("words", []) if _num(w.get("start")) and w["start"] < 0]
    checks.append(chk("G7.no_negative_start", "G7", "fail" if bad_neg else "pass",
                      ("negative start: " + ", ".join(bad_neg)) if bad_neg else "all starts >= 0"))

    short_w, short_c, many = [], [], []
    for c in cards:
        if c["end"] - c["start"] < min_card - 1e-9:
            short_c.append("%s %.2fs" % (c["id"], c["end"] - c["start"]))
        if len(c.get("words", [])) > max_words:
            many.append(c["id"])
        for w in c.get("words", []):
            if not _num(w.get("start")):
                short_w.append("%s: word without start" % c["id"])
            elif c["end"] - w["start"] < word_min - 1e-9:
                short_w.append("%s '%s' %.2fs" % (c["id"], w.get("text", "?"), c["end"] - w["start"]))
    checks.append(chk("G7.word_dwell", "G7", "fail" if short_w else "pass",
                      ("visible < %.2f s: %s" % (word_min, "; ".join(short_w))) if short_w else "every word visible >= %.2f s (last words included)" % word_min))
    checks.append(chk("G7.card_dwell", "G7", "fail" if short_c else "pass",
                      ("cards shorter than %.3f s: %s" % (min_card, "; ".join(short_c))) if short_c else "every card >= %.3f s" % min_card))
    checks.append(chk("G7.words_per_card", "G7", "fail" if many else "pass",
                      ("more than %d words: %s" % (max_words, ", ".join(many))) if many else "<= %d words per card" % max_words))

    no_exit = [c["id"] for c in cards if not (_num(c.get("exit_frames")) and c["exit_frames"] >= 3)]
    checks.append(chk("G7.exit_animation", "G7", "fail" if no_exit else "pass",
                      ("no exit animation >= 3 frames: " + ", ".join(no_exit)) if no_exit else "every card animates out (>= 3 frames)"))

    ordered = sorted(cards, key=lambda c: c["start"])
    swap_bad = []
    for a, b in zip(ordered, ordered[1:]):
        gap = b["start"] - a["end"]
        if gap > swap_gap:
            continue  # a pause in speech: allowed
        ov = round(-gap * fps, 2)
        if gap > 1e-9:
            swap_bad.append("%s->%s blank gap %.0f f" % (a["id"], b["id"], gap * fps))
        elif ov < 0.99:
            swap_bad.append("%s->%s no overlap (swap frame can be blank)" % (a["id"], b["id"]))
        elif ov > 2.01:
            swap_bad.append("%s->%s overlap %.0f f (cards stacked)" % (a["id"], b["id"], ov))
    checks.append(chk("G7.swap_overlap", "G7", "fail" if swap_bad else "pass",
                      "; ".join(swap_bad) if swap_bad else "swaps overlap 1-2 frames; pauses > %.2f s ignored" % swap_gap))

    for c in cards:
        for w in c.get("words", []):
            vs = w.get("voice_start")
            if _num(vs) and _num(w.get("start")) and not (-0.001 <= vs - w["start"] <= 0.2) and w["start"] > 0:
                warnings.append("%s '%s' lead %.2fs (house: 0.08-0.1 s)" % (c["id"], w.get("text", "?"), vs - w["start"]))

    no_y = [c["id"] for c in cards if not _num(c.get("bottom_y"))]
    low = [c["id"] for c in cards if _num(c.get("bottom_y")) and c["bottom_y"] > rail]
    if low:
        checks.append(chk("G8.rail", "G8", "fail", "bottom_y > %d: %s" % (rail, ", ".join(low))))
    elif no_y:
        checks.append(chk("G8.rail", "G8", "blocked", "no bottom_y for: " + ", ".join(no_y)))
    else:
        checks.append(chk("G8.rail", "G8", "pass", "all caption bottoms <= y %d (house preset)" % rail))

    ctrl_bad, marks = [], []
    for c in cards:
        txt = "".join(w.get("text", "") for w in c.get("words", []))
        if any(ch in OVERRIDES for ch in txt):
            ctrl_bad.append("%s override/embedding control" % c["id"])
        opens = sum(1 for ch in txt if ch in ISOLATE_OPEN)
        if opens != txt.count(ISOLATE_CLOSE):
            ctrl_bad.append("%s unbalanced isolate" % c["id"])
        if any(ch in MARKS for ch in txt):
            marks.append(c["id"])
    checks.append(chk("G5.bidi_controls", "G5", "fail" if ctrl_bad else "pass",
                      "; ".join(ctrl_bad) if ctrl_bad else "no override characters, isolates balanced"))
    if marks:
        warnings.append("LRM/RLM marks in %s: acceptable only inside a renderer adapter" % ", ".join(marks))

    iso_bad = []
    for c in cards:
        words = c.get("words", [])
        if any(HEB.search(w.get("text", "")) for w in words):
            for w in words:
                t = w.get("text", "")
                if NEEDS_ISO.search(t) and not HEB.search(t) and w.get("isolated") is not True:
                    iso_bad.append("%s '%s'" % (c["id"], t))
    checks.append(chk("G5.isolation", "G5", "fail" if iso_bad else "pass",
                      ("Latin/digit/currency span inside a Hebrew card not isolated: " + "; ".join(iso_bad)) if iso_bad
                      else "mixed spans isolated (or none)"))

    look_bad, look_list = [], []
    for c in cards:
        for w in c.get("words", []):
            if w.get("keyword") is True and LOOKALIKE & set(w.get("text", "")):
                look_list.append(w.get("text", ""))
                if w.get("lookalike_checked") is not True:
                    look_bad.append("%s '%s'" % (c["id"], w.get("text", "")))
    checks.append(chk("G6.lookalike_record", "G6", "fail" if look_bad else ("pass" if look_list else "n/a"),
                      ("keywords with look-alike letters not tested at full size: " + "; ".join(look_bad)) if look_bad
                      else ("%d keyword(s) with ו/ז ד/ר ה/ח tested" % len(look_list) if look_list else "no keyword contains a look-alike letter")))

    unit_bad = [c["id"] for c in cards if c.get("anim_unit") not in ("word", "card")]
    checks.append(chk("G7.animation_unit", "G7", "fail" if unit_bad else "pass",
                      ("animation unit must be word or card (never letters); fix: " + ", ".join(unit_bad)) if unit_bad
                      else "words or cards animate, never letters"))
    return checks, warnings, cov


def report(doc, **kw):
    checks, warnings, cov = lint(doc, **kw)
    states = [c["state"] for c in checks]
    status = "FAIL" if "fail" in states else ("INSUFFICIENT_EVIDENCE" if "blocked" in states else "PASS")
    return {"tool": "caption_lint", "version": VERSION, "status": status, "coverage": cov,
            "scope": "plan only: not a render check", "checks": checks, "warnings": warnings}


def _lin(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _lum(rgb):
    return 0.2126 * _lin(rgb[0]) + 0.7152 * _lin(rgb[1]) + 0.0722 * _lin(rgb[2])


def contrast(bg_rgb, fg_hex):
    fg = [int(fg_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    a, b = sorted([_lum(bg_rgb), _lum(fg)])
    return (b + 0.05) / (a + 0.05)


def _good():
    def w(t, s, **kw):
        d = {"text": t, "start": s}
        d.update(kw)
        return d
    return {"fps": 30, "canvas": [1080, 1920], "mode": "cards", "cards": [
        {"id": "c1", "start": 1.0, "end": 2.2, "bottom_y": 1240, "exit_frames": 4, "anim_unit": "word",
         "words": [w("אני", 1.0, voice_start=1.1), w("מקשיב", 1.3, voice_start=1.4)]},
        {"id": "c2", "start": 2.2 - 2 / 30.0, "end": 3.5, "bottom_y": 1240, "exit_frames": 4, "anim_unit": "word",
         "words": [w("לבזבז", 2.2 - 2 / 30.0, keyword=True, lookalike_checked=True), w("שעות", 2.6),
                   w("iPhone", 2.9, isolated=True)]},
        {"id": "c3", "start": 6.0, "end": 7.0, "bottom_y": 1240, "exit_frames": 4, "anim_unit": "word",
         "words": [w("תודה", 6.0)]},
    ]}


def self_check():
    import copy
    ok = True

    def expect(name, doc, want):
        nonlocal ok
        got = report(doc)["status"]
        ok = ok and got == want
        print("%s %-34s expected %-22s got %s" % ("ok  " if got == want else "FAIL", name, want, got))

    g = _good()
    expect("positive control", g, "PASS")
    d = copy.deepcopy(g); d["cards"][0]["exit_frames"] = 0
    expect("no exit animation", d, "FAIL")
    d = copy.deepcopy(g); d["cards"][0]["end"] = 1.8
    expect("card too short + gap/blank swap", d, "FAIL")
    d = copy.deepcopy(g); d["cards"][1]["start"] = 2.2
    expect("swap with 0 overlap", d, "FAIL")
    d = copy.deepcopy(g); d["cards"][1]["start"] = 2.2 - 6 / 30.0; d["cards"][1]["words"][0]["start"] = d["cards"][1]["start"]
    expect("stacked cards (6 f overlap)", d, "FAIL")
    d = copy.deepcopy(g); d["cards"][0]["bottom_y"] = 1760
    expect("caption under the platform UI", d, "FAIL")
    d = copy.deepcopy(g); d["cards"][0]["words"][0]["text"] = "‮" + "אני"
    expect("override control character", d, "FAIL")
    d = copy.deepcopy(g); d["cards"][1]["words"][2]["isolated"] = False
    expect("unisolated Latin span", d, "FAIL")
    d = copy.deepcopy(g); d["cards"][1]["words"][0]["lookalike_checked"] = False
    expect("look-alike keyword untested", d, "FAIL")
    d = copy.deepcopy(g); d["cards"][0]["anim_unit"] = "letter"
    expect("letter-by-letter animation", d, "FAIL")
    d = copy.deepcopy(g); d["cards"][2]["words"][0]["start"] = 6.8
    expect("last word visible 0.2 s", d, "FAIL")
    d = copy.deepcopy(g); d["cards"][0]["start"] = -0.1
    expect("negative start", d, "FAIL")
    d = copy.deepcopy(g); del d["cards"][0]["bottom_y"]
    expect("missing bottom_y (blocked)", d, "INSUFFICIENT_EVIDENCE")
    expect("empty cards (blocked)", {"fps": 30, "cards": []}, "INSUFFICIENT_EVIDENCE")
    ratio = contrast([40, 40, 40], "#FFFFFF")
    c_ok = ratio > 4.5 and contrast([255, 255, 255], "#FCE500") < 1.5
    ok = ok and c_ok
    print("%s contrast arithmetic (white on dark %.1f:1, yellow on white %.2f:1)" % (
        "ok  " if c_ok else "FAIL", ratio, contrast([255, 255, 255], "#FCE500")))
    print("SELF-CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--self-check" in argv:
        return self_check()
    if len(argv) >= 3 and argv[0] == "contrast":
        try:
            rgb = [int(x) for x in argv[1].split(",")]
            mn = float(argv[argv.index("--min") + 1]) if "--min" in argv else 4.5
            r = contrast(rgb, argv[2])
        except (ValueError, IndexError):
            print(__doc__); return 2
        print("contrast %.2f:1 (%s %.1f:1)" % (r, "pass" if r >= mn else "FAIL, below", mn))
        return 0 if r >= mn else 1
    if len(argv) >= 2 and argv[0] == "lint":
        rail, out, i = None, None, 2
        while i < len(argv):
            if argv[i] == "--rail-bottom" and i + 1 < len(argv):
                rail = int(argv[i + 1]); i += 2
            elif argv[i] == "--json" and i + 1 < len(argv):
                out = argv[i + 1]; i += 2
            else:
                print(__doc__); return 2
        try:
            with open(argv[1], "r", encoding="utf-8") as fh:
                rep = report(json.load(fh), rail_override=rail)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            rep = {"tool": "caption_lint", "version": VERSION, "status": "INSUFFICIENT_EVIDENCE",
                   "checks": [chk("C0", "schema", "blocked", "cannot read captions file: %s" % exc)]}
        text = json.dumps(rep, indent=2, ensure_ascii=False)
        print(text)
        if out:
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(text)
        return 0 if rep["status"] == "PASS" else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

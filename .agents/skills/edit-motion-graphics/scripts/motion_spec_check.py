#!/usr/bin/env python3
"""motion_spec_check.py - deterministic lint of a frame-level PROMPT.md for a motion piece.

Usage:
    python motion_spec_check.py PROMPT.md [--register launch|calm|kinetic|logo|explainer]
                                [--fps 30] [--frames N] [--allow-captions] [--json]
    python motion_spec_check.py --self-check

What it checks (text only - it says NOTHING about how the render looks):
  blocks     the six blocks <inputs> <direction> <structure> <build> <gotchas> <start>
  tables     the three mandatory tables: camera, seams, events (header names in
             references/seam-camera-event-tables.md)
  camera     each move >= 1.2 s, no overlap, reversals >= 1.0 s per move and <= 1.3x range,
             "text inside frame" = yes on every row
  seams      exit vector == entry vector, a technique that is not a fade/crossfade,
             no technique used twice (error for launch, warning otherwise)
  events     gaps <= 0.7 s (warning to 1.0 s, error beyond unless a row is flagged
             breath/hold/end), first event <= 1.0 s, events per minute vs the register band
  structure  frame ranges cover 0..N with no gap; every beat names px, an easing and a sound;
             every beat except the last names a transition; hedge words ("about", "~") warn
  direction  >= 2 hex colours and a "Banned:" line
  approval   a line "APPROVAL: <who> <date>" (missing => blocked, never pass)

Exit codes: 0 pass | 1 fail (>= 1 error) | 2 blocked / not_run (unreadable, nothing parsed,
or approval missing). A timeout, empty file or missing input never passes.
Stdlib only. Python >= 3.9.
"""
import argparse
import json
import re
import sys
from pathlib import Path

BLOCKS = ["inputs", "direction", "structure", "build", "gotchas", "start"]
BAND = {  # events per minute (hand-count targets, owner studio style, distilled 04 motion-design 2.3)
    "launch": (45, 110), "kinetic": (45, 200), "logo": (20, 110),
    "explainer": (30, 110), "calm": (0, 10**6),
}
OK_WORDS = {"yes", "y", "ok", "true", "✓", "✔"}
EASE_RE = re.compile(r"(power[1-4]\.(?:in|out|inout)|expo\.(?:in|out|inout)|sine\.(?:in|out|inout)|"
                     r"circ\.(?:in|out|inout)|back\.(?:in|out|inout)|elastic|steps\(|linear|spline|"
                     r"cubic-bezier|spring|ease\s*none|\bnone\b|owner\.enter)", re.I)
SOUND_RE = re.compile(r"(sfx|sound|music|\bvo\b|whoosh|\bhit\b|click|tick|thump|silence|riser|drop|"
                      r"cha-?ching|ring-?out|bass|pluck|chime|swell|downbeat)", re.I)
TRANS_RE = re.compile(r"(->|→|\bcut\b|whip|zooms?[- ]?through|match-?move|portal|iris|reveal|push|morph|"
                      r"shared-?element|fall-?away|bloom|wipe|handoff|continues|\binto\b)", re.I)
PX_RE = re.compile(r"(\d+\s*px|\b\d{2,4}\s*[,x×]\s*\d{2,4}\b)", re.I)
HEDGE_RE = re.compile(r"(\babout\b|\bapproximately\b|\bapprox\.?\b|\broughly\b|\baround\b|\bcirca\b|~\s*\d)", re.I)
BEAT_START = re.compile(r"^\s*(?:[-*]\s*)?f(\d+)\s*[-–—−→]\s*f?(\d+)", re.I)
DASH_RE = re.compile(r"[–—−→]")


def norm_cell(s):
    s = DASH_RE.sub("-", s.lower())
    s = re.sub(r"\bseconds?\b|\bsec\b", "s", s)
    s = re.sub(r"\bto\b", "-", s)
    return s.replace(" ", "")


def parse_time(cell, fps):
    """Return (start, end|None) in seconds, or None when unparsable."""
    c = norm_cell(cell)
    pats = [
        (r"f(\d+)-f?(\d+)", "ff"), (r"(\d+)-(\d+)f", "ff"),
        (r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)s?", "ss"),
        (r"f(\d+)", "f1"), (r"(\d+)f", "f1"), (r"(\d+(?:\.\d+)?)s?", "s1"),
    ]
    for pat, kind in pats:
        m = re.fullmatch(pat, c)
        if not m:
            continue
        g = m.groups()
        if kind == "ff":
            return int(g[0]) / fps, int(g[1]) / fps
        if kind == "ss":
            return float(g[0]), float(g[1])
        if kind == "f1":
            return int(g[0]) / fps, None
        return float(g[0]), None
    return None


def md_tables(lines):
    blocks, cur = [], []
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("|"):
            cur.append((i, line))
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    out = []
    for blk in blocks:
        rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for _, ln in blk]
        if len(rows) < 2:
            continue
        header = [h.lower() for h in rows[0]]
        body = [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r if c)]
        body = [r for r in body if any(c for c in r)]
        out.append({"line": blk[0][0], "header": header, "rows": body})
    return out


def col(header, *names):
    for i, h in enumerate(header):
        if any(n in h for n in names):
            return i
    return None


def cell(row, idx):
    return row[idx].strip() if idx is not None and idx < len(row) else ""


class Report:
    def __init__(self):
        self.items = []  # (severity, code, message)

    def add(self, sev, code, msg):
        self.items.append((sev, code, msg))

    @property
    def errors(self):
        return [i for i in self.items if i[0] == "error"]

    @property
    def warnings(self):
        return [i for i in self.items if i[0] == "warn"]


def direction_label(s):
    s = s.lower().strip()
    if not s:
        return None
    if re.search(r"static|none|hold|n/?a|^-$", s):
        return "static"
    if re.search(r"push|zoom[- ]?in|\bin\b|grow|closer", s):
        return "in"
    if re.search(r"pull|zoom[- ]?out|\bout\b|reced|away", s):
        return "out"
    for d in ("left", "right", "up", "down"):
        if d in s:
            return d
    return None


def check_camera(tab, fps, reg, rep):
    h = tab["header"]
    ti, si = col(h, "t", "time"), col(h, "scale", "zoom")
    ci, xi = col(h, "scene"), col(h, "text")
    fi = col(h, "focal")
    prev = {}
    rows = 0
    for r in tab["rows"]:
        rows += 1
        t = parse_time(cell(r, ti), fps)
        if not t or t[1] is None:
            rep.add("error", "CAM_RANGE", f"camera row {rows}: time range unparsable: '{cell(r, ti)}'")
            continue
        s0, s1 = t
        nums = re.findall(r"\d+(?:\.\d+)?", cell(r, si))
        sc = (float(nums[0]), float(nums[-1])) if nums else None
        scene = cell(r, ci) or "_"
        dur = s1 - s0
        if dur < 1.2 - 1e-9:
            rep.add("error", "CAM_SHORT", f"camera row {rows} ({scene}): move {dur:.2f} s < 1.2 s (a short push reads as a jump)")
        if (xi is None) or cell(r, xi).lower() not in OK_WORDS:
            rep.add("error", "CAM_TEXT", f"camera row {rows} ({scene}): 'text inside frame' must be yes at every key")
        p = prev.get(scene)
        if p:
            if s0 < p["end"] - 1e-6:
                rep.add("error", "CAM_OVERLAP", f"camera row {rows} ({scene}): overlaps the previous move (one spline per scene)")
            elif s0 > p["end"] + 0.25:
                rep.add("warn", "CAM_GAP", f"camera row {rows} ({scene}): camera stops {s0 - p['end']:.2f} s between moves")
            if sc and p["sc"]:
                d0, d1 = p["sc"][1] - p["sc"][0], sc[1] - sc[0]
                if abs(d0) > 0.005 and abs(d1) > 0.005 and (d0 > 0) != (d1 > 0):
                    if min(dur, p["dur"]) < 1.0 - 1e-9:
                        rep.add("error", "CAM_REVERSE_FAST", f"camera row {rows} ({scene}): reversal with a move < 1.0 s")
                    rng = max(sc + p["sc"]) / max(min(sc + p["sc"]), 1e-9)
                    if rng > 1.3 + 1e-9:
                        rep.add("error", "CAM_REVERSE_RANGE", f"camera row {rows} ({scene}): reversal range {rng:.2f}x > 1.3x")
            if (sc and p["sc"] and abs(sc[1] - sc[0]) < 0.005 and abs(p["sc"][1] - p["sc"][0]) < 0.005
                    and reg in ("launch", "kinetic") and dur > 1.0):
                rep.add("warn", "CAM_STATIC", f"camera row {rows} ({scene}): static > 1 s (launch register keeps drifting 2-4 %/s)")
        prev[scene] = {"end": s1, "sc": sc, "dur": dur}
    if rows == 0:
        rep.add("error", "CAM_EMPTY", "camera table has no rows")
    return rows


def check_seams(tab, fps, reg, rep):
    h = tab["header"]
    ti, ei, ni = col(h, "t", "time"), col(h, "exit"), col(h, "entry")
    hi, qi = col(h, "hero"), col(h, "technique", "tech")
    seen = {}
    n = 0
    for r in tab["rows"]:
        n += 1
        ex, en = direction_label(cell(r, ei)), direction_label(cell(r, ni))
        if ex is None or en is None:
            rep.add("warn", "SEAM_DIR_UNKNOWN", f"seam row {n}: exit/entry direction not recognised ('{cell(r, ei)}' / '{cell(r, ni)}')")
        elif "static" not in (ex, en) and ex != en:
            rep.add("error", "SEAM_VECTOR", f"seam row {n}: exit '{ex}' != entry '{en}' (exit vector must equal entry vector)")
        tech = cell(r, qi).lower().strip()
        if not tech:
            rep.add("error", "SEAM_TECH", f"seam row {n}: technique missing")
        else:
            if re.search(r"cross-?fade|dissolve", tech) or re.fullmatch(r"(fade|fade[- ]?(out|in)|dip)", tech):
                rep.add("error", "SEAM_FADE", f"seam row {n}: '{tech}' is a fade/crossfade (banned as a transition)")
            if tech in seen:
                sev = "error" if reg == "launch" else "warn"
                rep.add(sev, "SEAM_REPEAT", f"seam row {n}: technique '{tech}' already used in row {seen[tech]} (same trick twice)")
            seen.setdefault(tech, n)
        if reg == "launch" and cell(r, hi).lower() in ("", "none", "-", "n/a"):
            rep.add("warn", "SEAM_HERO", f"seam row {n}: no persistent hero object named")
    if n == 0:
        rep.add("error", "SEAM_EMPTY", "seams table has no rows")
    return n


def check_events(tab, fps, reg, rep):
    h = tab["header"]
    ti, ni = col(h, "t", "time"), col(h, "note", "type", "flag")
    pts = []
    for r in tab["rows"]:
        t = parse_time(cell(r, ti), fps)
        if not t:
            rep.add("error", "EVT_TIME", f"events row: time unparsable '{cell(r, ti)}'")
            continue
        pts.append((t[0], cell(r, ni).lower()))
    pts.sort()
    if len(pts) < 2:
        rep.add("error", "EVT_FEW", "events table needs at least 2 timed events")
        return len(pts)
    if reg in ("launch", "kinetic", "logo", "explainer"):
        if pts[0][0] > 1.0 + 1e-9:
            rep.add("error", "EVT_LATE_FIRST", f"first event at {pts[0][0]:.2f} s > 1.0 s (motion from frame 1)")
        elif pts[0][0] > 0.5 + 1e-9:
            rep.add("warn", "EVT_LATE_FIRST", f"first event at {pts[0][0]:.2f} s (> 0.5 s)")
        for (a, _), (b, note) in zip(pts, pts[1:]):
            gap = b - a
            declared = re.search(r"breath|hold|end|silence|reveal-wait", note)
            if gap > 1.0 + 1e-9 and not declared:
                rep.add("error", "EVT_GAP_LONG", f"events gap {gap:.2f} s between {a:.2f} and {b:.2f} (> 1.0 s, not flagged breath/hold/end)")
            elif gap > 0.7 + 1e-9 and not declared:
                rep.add("warn", "EVT_GAP", f"events gap {gap:.2f} s between {a:.2f} and {b:.2f} (> 0.7 s)")
    span = pts[-1][0] - pts[0][0]
    if span > 0:
        rate = (len(pts) - 1) / span * 60
        lo, hi = BAND[reg]
        if rate < lo or rate > hi:
            rep.add("warn", "EVT_RATE", f"{rate:.0f} events/min outside the {reg} band {lo}-{hi} (hand-count targets; verify on frames)")
    return len(pts)


def structure_checks(text, total_frames, reg, rep):
    m = re.search(r"<structure>(.*?)</structure>", text, re.S | re.I)
    if not m:
        return
    beats, cur = [], None
    for line in m.group(1).splitlines():
        b = BEAT_START.match(line)
        if b:
            cur = {"a": int(b.group(1)), "b": int(b.group(2)), "text": line}
            beats.append(cur)
        elif cur is not None:
            cur["text"] += "\n" + line
    if len(beats) < 3:
        rep.add("error", "STRUCT_FEW", f"{len(beats)} frame-range beats found in <structure> (need >= 3, format 'f0-f29 ...')")
        return
    beats.sort(key=lambda x: x["a"])
    for i, bt in enumerate(beats):
        tag = f"f{bt['a']}-f{bt['b']}"
        if bt["b"] < bt["a"]:
            rep.add("error", "BEAT_RANGE", f"beat {tag}: end before start")
        if not PX_RE.search(bt["text"]):
            rep.add("error", "BEAT_PX", f"beat {tag}: no px size/position")
        if not EASE_RE.search(bt["text"]):
            rep.add("error", "BEAT_EASE", f"beat {tag}: no easing named")
        if not SOUND_RE.search(bt["text"]):
            rep.add("error", "BEAT_SOUND", f"beat {tag}: no sound named")
        if i < len(beats) - 1 and not TRANS_RE.search(bt["text"]):
            rep.add("error", "BEAT_TRANS", f"beat {tag}: no transition out named")
        if HEDGE_RE.search(bt["text"]):
            rep.add("warn", "HEDGE", f"beat {tag}: hedge word (numbers are the contract)")
        if re.search(r"cross-?fade|dissolve", bt["text"], re.I) and not re.search(r"banned|never|no cross", bt["text"], re.I):
            rep.add("error", "BEAT_FADE", f"beat {tag}: crossfade/dissolve named as a transition")
    covered = 0
    for bt in beats:
        if bt["a"] > covered:
            rep.add("error", "STRUCT_GAP", f"frames {covered}-{bt['a'] - 1} have no beat")
        covered = max(covered, bt["b"] + 1)
    if total_frames:
        if beats[0]["a"] != 0:
            rep.add("error", "STRUCT_START", f"first beat starts at f{beats[0]['a']} (must be f0)")
        if covered < total_frames:
            rep.add("error", "STRUCT_SHORT", f"beats end at f{covered - 1}, piece has {total_frames} frames")
        if covered > total_frames + 1:
            rep.add("warn", "STRUCT_LONG", f"beats run to f{covered - 1}, past the {total_frames}-frame piece")
    else:
        rep.add("warn", "N_UNKNOWN", "total frame count unknown (write 'W x H @fps (N frames)' in <direction> or pass --frames)")


def run_checks(text, reg="launch", fps=30, frames=None, allow_captions=False):
    rep = Report()
    status = {"approval": "missing"}
    if not text.strip():
        rep.add("error", "EMPTY", "file is empty")
        return rep, {"verdict": "blocked", "reason": "empty input", "tables": {}}
    present = {b: bool(re.search(rf"<{b}>.*?</{b}>", text, re.S | re.I)) for b in BLOCKS}
    for b, ok in present.items():
        if not ok:
            rep.add("error", "BLOCK_MISSING", f"block <{b}> missing")
    d = re.search(r"<direction>(.*?)</direction>", text, re.S | re.I)
    dtxt = d.group(1) if d else ""
    if frames is None:
        m = re.search(r"\((\d+)\s*frames\)", dtxt, re.I)
        frames = int(m.group(1)) if m else None
        m2 = re.search(r"@\s*(\d+(?:\.\d+)?)\s*fps", dtxt, re.I)
        if m2 and fps == 30 and float(m2.group(1)) != 30:
            rep.add("warn", "FPS_MISMATCH", f"<direction> says {m2.group(1)} fps; pass --fps {m2.group(1)} so table times convert correctly")
    if d:
        if len(set(re.findall(r"#[0-9a-fA-F]{6}\b", dtxt))) < 2:
            rep.add("error", "DIR_HEX", "<direction> names fewer than 2 hex colours (palette is a contract)")
        if not re.search(r"banned\s*:", dtxt, re.I):
            rep.add("error", "DIR_BANNED", "<direction> has no 'Banned:' line")
    start = re.search(r"<start>(.*?)</start>", text, re.S | re.I)
    if start and not re.search(r"still", start.group(1), re.I):
        rep.add("warn", "START_STILLS", "<start> does not mention the 4 approval stills")
    b = re.search(r"<build>(.*?)</build>", text, re.S | re.I)
    if b and not re.search(r"lufs|-14", b.group(1), re.I):
        rep.add("warn", "BUILD_LOUDNESS", "<build> names no loudness target (house preset v1: -14 LUFS, TP <= -1)")
    if not allow_captions and reg != "calm":
        body = re.sub(r"(?im)^.*\b(no captions|captions off|banned)\b.*$", "", text)
        if re.search(r"captions?\b", body, re.I):
            rep.add("warn", "CAPTION_MENTION", "captions mentioned; default for motion pieces is OFF unless the brief asks (pass --allow-captions)")
    tabs = md_tables(text.splitlines())
    cam = [t for t in tabs if col(t["header"], "scale", "zoom") is not None and col(t["header"], "t", "time") is not None
           and col(t["header"], "exit") is None]
    seam = [t for t in tabs if col(t["header"], "exit") is not None and col(t["header"], "entry") is not None]
    evt = [t for t in tabs if col(t["header"], "event") is not None and col(t["header"], "exit") is None
           and col(t["header"], "scale", "zoom") is None]
    counts = {}
    for name, found, fn in (("camera", cam, check_camera), ("seams", seam, check_seams), ("events", evt, check_events)):
        if not found:
            rep.add("error", "TABLE_MISSING", f"mandatory {name} table not found (header names: references/seam-camera-event-tables.md)")
            counts[name] = 0
        else:
            counts[name] = fn(found[0], fps, reg, rep)
    structure_checks(text, frames, reg, rep)
    appr = re.search(r"(?im)^\s*APPROVAL\s*:\s*(\S.*)$", text)
    if appr and not re.search(r"todo|tbd|pending|none|<.*>|\.\.\.|^n/?a$", appr.group(1).strip(), re.I):
        status["approval"] = "present"
    nothing = not any(present.values()) and not tabs
    if nothing:
        verdict, reason = "blocked", "nothing parsed (no blocks, no tables)"
    elif rep.errors:
        verdict, reason = "fail", f"{len(rep.errors)} error(s)"
    elif status["approval"] != "present":
        verdict, reason = "blocked", "structure clean but no 'APPROVAL: <who> <date>' line (human approval is a precondition for code)"
    else:
        verdict, reason = "pass", "all deterministic checks passed; approval line present"
    return rep, {"verdict": verdict, "reason": reason, "tables": counts, "approval": status["approval"],
                 "frames": frames, "register": reg, "fps": fps}


def render(rep, summ, as_json):
    if as_json:
        print(json.dumps({"summary": summ, "findings": [{"severity": s, "code": c, "message": m} for s, c, m in rep.items]},
                         ensure_ascii=False, indent=2))
        return
    for s, c, m in rep.items:
        print(f"[{s.upper():5}] {c}: {m}")
    print(f"VERDICT: {summ['verdict']} - {summ['reason']}")
    print("note: a pass here means the SPEC is internally consistent, not that the render looks right.")


GOOD = """\
<inputs>Ask for: lockup, prices, VO lines. Defaults: lockup 'Acme', price $84.00 -> $102.60, no VO.</inputs>
<direction>
12 s, 1920x1080 @30fps (360 frames), grammar of a launch film. Palette #0B0D12 ground, #E8ECF2 text, #2F6BFF accent (reveal only).
Hero: phone 420x860 px. Banned: crossfade, fade as a transition, bounce on text, small corner labels, same transition twice, static hold >= 1 s.
</direction>
<structure>
f0-f119 S1 phone card at 960,540 px 420x860: enters expo.out 6 f, drift 3 %/s; SFX tick at f2; the phone lifts into S2 (match-move).
f120-f239 S2 price number 160 px at 960,500: swapWhole 18 f power3.out; hit at f124; the number stays and zooms through into S3.
f240-f359 S3 lockup 900x240 px centred: expo.out 8 f; music button + ring-out; end.
</structure>
<build>One paused GSAP timeline; cues.js; master -14 LUFS, TP -1.5.</build>
<gotchas>fonts via @font-face; RTL on text only.</gotchas>
<start>4 stills at f30, f130, f250, f350 before the full render.</start>

| scene | t | scale | focal (x,y) | in frame | text inside frame |
|---|---|---|---|---|---|
| S1 | 0.0-2.4 s | 1.00 -> 1.18 | 960,540 -> 1010,520 | phone | yes |
| S1 | 2.4-4.0 s | 1.18 -> 1.32 | 1010,520 -> 1040,510 | phone detail | yes |
| S2 | 4.0-7.0 s | 0.85 -> 1.00 | 960,540 | price | yes |
| S2 | 7.0-9.2 s | 1.00 -> 1.12 | 960,520 | price | yes |
| S3 | 9.2-12.0 s | 1.12 -> 1.30 | 960,500 | lockup | yes |

| t | exit | entry | hero | technique |
|---|---|---|---|---|
| 4.0 | in | in | phone | match-move |
| 9.2 | in | in | number | zoom-through |

| t | event | note |
|---|---|---|
| 0.0 | phone enters | |
| 0.6 | tick | |
| 1.2 | screen lights | |
| 1.8 | badge pops | |
| 2.4 | camera push starts | |
| 3.0 | list item 1 | |
| 3.6 | list item 2 | |
| 4.2 | scene 2 starts | |
| 4.8 | price swap | |
| 5.4 | pulse | |
| 6.0 | word swap | |
| 6.6 | chart bar | |
| 7.2 | zoom starts | |
| 7.8 | detail callout | |
| 8.4 | ring | |
| 9.0 | scene 3 starts | |
| 9.6 | lockup builds | |
| 10.2 | tagline word 1 | |
| 10.8 | tagline word 2 | |
| 11.4 | button | |

APPROVAL: example-reviewer 2026-10-02
"""


def self_check():
    fails = []

    def expect(name, text, verdict, code=None, **kw):
        rep, summ = run_checks(text, **kw)
        ok = summ["verdict"] == verdict and (code is None or any(c == code for _, c, _ in rep.items))
        if not ok:
            fails.append(f"{name}: got {summ['verdict']} {[c for _, c, _ in rep.items][:6]}, wanted {verdict}/{code}")

    expect("good", GOOD, "pass")
    expect("empty", "", "blocked")
    expect("nothing", "hello", "blocked")
    expect("no-approval", GOOD.replace("APPROVAL: example-reviewer 2026-10-02", ""), "blocked")
    expect("placeholder-approval", GOOD.replace("example-reviewer 2026-10-02", "TBD"), "blocked")
    expect("short-move", GOOD.replace("| 2.4-4.0 s |", "| 2.4-3.0 s |"), "fail", "CAM_SHORT")
    expect("text-cut", GOOD.replace("| phone detail | yes |", "| phone detail | no |"), "fail", "CAM_TEXT")
    expect("seam-vector", GOOD.replace("| 4.0 | in | in |", "| 4.0 | left | right |"), "fail", "SEAM_VECTOR")
    expect("seam-fade", GOOD.replace("| match-move |", "| crossfade |"), "fail", "SEAM_FADE")
    expect("seam-repeat", GOOD.replace("| zoom-through |", "| match-move |"), "fail", "SEAM_REPEAT")
    expect("event-gap", GOOD.replace("| 3.0 | list item 1 | |", "| 4.1 | list item 1 | |"), "fail", "EVT_GAP_LONG")
    expect("missing-table", GOOD.replace("| t | exit | entry | hero | technique |", "| t | foo |"), "fail", "TABLE_MISSING")
    expect("no-easing", GOOD.replace("expo.out 6 f", "6 f"), "fail", "BEAT_EASE")
    expect("no-banned", GOOD.replace("Banned:", "Avoid:"), "fail", "DIR_BANNED")
    expect("gap", GOOD.replace("f120-f239", "f130-f239"), "fail", "STRUCT_GAP")
    expect("calm-register-passes-sparse-events", GOOD.replace("| 3.0 | list item 1 | |", "| 4.1 | list item 1 | |"), "pass", reg="calm")
    if fails:
        print("SELF-CHECK FAILED")
        for f in fails:
            print(" -", f)
        return 1
    print("SELF-CHECK OK (16 cases)")
    return 0


def main(argv=None):
    try:  # Hebrew paths / non-ASCII messages must not crash on a legacy console code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--register", default="launch", choices=sorted(BAND))
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--frames", type=int)
    ap.add_argument("--allow-captions", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.prompt:
        ap.print_usage()
        return 2
    p = Path(a.prompt)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        print(f"BLOCKED: cannot read {p}: {e}")
        return 2
    rep, summ = run_checks(text, a.register, a.fps, a.frames, a.allow_captions)
    render(rep, summ, a.json)
    return {"pass": 0, "fail": 1, "blocked": 2}[summ["verdict"]]


if __name__ == "__main__":
    sys.exit(main())

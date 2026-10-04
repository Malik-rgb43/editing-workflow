#!/usr/bin/env python3
"""Check that a revision round is complete BEFORE patching and BEFORE presenting.

Usage:
  python round_check.py hf/CHANGELOG.md [--round N] [--prompt hf/PROMPT.md] [--patch tools/patch_r3.json]
                        [--root projects/<name>] [--require-present] [--json]
  python round_check.py --self-check

Reads the `## Round N` section of CHANGELOG.md (format: references/round-log-format.md):
  1. "<note in the user's words>" @ 0:24-0:26 | class: fix | ledger: L21 | cause: <file/line/cue/asset> | frames: _work/notes/r3_n1.jpg
  RENDER full <file>      (at most one per round; none when every note is audio-only)
  PRESENTED <date>        (required with --require-present)
Checks per note: quoted words, class in {fix, replace-concept, audio-only, global-rule}, a ledger id that
also appears in PROMPT.md at least twice, a concrete cause, a frame strip (unless audio-only), and the
class-specific field (replacement / occurrences / render: none). `--patch` adds an order check: the patch file
must not be older than PROMPT.md (ledger -> PROMPT -> code); mtimes are evidence, not proof.

Exit codes (fail closed): 0 PASS, 1 FAIL, 2 INSUFFICIENT_EVIDENCE (no round / no notes / unreadable),
3 NEEDS_REVIEW (only review findings).
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

VERSION = "0.1.0"
CLASSES = {"fix", "replace-concept", "audio-only", "global-rule"}
NOTE_RE = re.compile(r"^\s*(\d+[a-z]?)\.\s+(.*)$")
ROUND_RE = re.compile(r"^##\s+(?:Round|סבב)\s+(\d+)", re.I)
POLISH_RE = re.compile(r"\b(polish|tweak|slightly|a bit|fine-?tune)\b|קצת|לשפר את", re.I)
WEAK_CAUSE = {"", "unknown", "?", "n/a", "tbd", "todo", "-", "guess"}


def split_rounds(text: str) -> dict[int, list[str]]:
    rounds, cur = {}, None
    for line in text.splitlines():
        m = ROUND_RE.match(line.strip())
        if m:
            cur = int(m.group(1))
            rounds[cur] = []
        elif line.startswith("## "):
            cur = None
        elif cur is not None:
            rounds[cur].append(line)
    return rounds


def parse_note(line: str) -> dict:
    m = NOTE_RE.match(line)
    num, rest = m.group(1), m.group(2)
    parts = [p.strip() for p in rest.split(" | ")]
    head = parts[0]
    q = re.search(r'["“«״](.+?)["”»״]', head)
    note = {"num": num, "said": q.group(1).strip() if q else "", "time": "", "fields": {}}
    t = re.search(r"@\s*([0-9:.\-– ,fFs]+)", head)
    if t:
        note["time"] = t.group(1).strip()
    for p in parts[1:]:
        k, _, v = p.partition(":")
        note["fields"][k.strip().lower()] = v.strip()
    return note


def run(changelog: str, rnd: int | None, prompt: str | None, patch: Path | None, prompt_path: Path | None,
        root: Path | None, require_present: bool) -> dict:
    findings = []

    def add(sev: str, code: str, where: str, msg: str) -> None:
        findings.append({"severity": sev, "code": code, "where": where, "message": msg})

    rounds = split_rounds(changelog)
    res = {"tool": "round_check", "version": VERSION, "findings": findings, "notes": 0, "round": None}
    if not rounds:
        add("error", "no_round", "-", "no '## Round N' section in the changelog")
        res["status"] = "INSUFFICIENT_EVIDENCE"
        return res
    n = rnd if rnd is not None else max(rounds)
    if n not in rounds:
        add("error", "round_missing", f"round {n}", "that round does not exist")
        res["status"] = "INSUFFICIENT_EVIDENCE"
        return res
    res["round"] = n
    lines = rounds[n]
    notes = [parse_note(l) for l in lines if NOTE_RE.match(l)]
    res["notes"] = len(notes)
    if not notes:
        add("error", "no_notes", f"round {n}", "round has no numbered notes")
        res["status"] = "INSUFFICIENT_EVIDENCE"
        return res
    seen = set()
    for nt in notes:
        w = f"note {nt['num']}"
        f = nt["fields"]
        if nt["num"] in seen:
            add("error", "duplicate_number", w, "note number reused")
        seen.add(nt["num"])
        if not nt["said"]:
            add("error", "no_quote", w, "the user's own words must be quoted")
        cls = f.get("class", "")
        if cls not in CLASSES:
            add("error", "bad_class", w, f"class must be one of {sorted(CLASSES)}, got {cls!r}")
        lid = f.get("ledger", "")
        if not re.fullmatch(r"L\d{2,3}", lid):
            add("error", "no_ledger_id", w, "each note needs a new ledger row id (L<nn>)")
        elif prompt is not None:
            cnt = len(re.findall(re.escape(lid) + r"(?!\d)", prompt))
            if cnt < 2:
                add("error", "ledger_not_in_prompt", w, f"{lid} appears {cnt}x in PROMPT.md (ledger + structure = 2): PROMPT must change before code")
        if f.get("cause", "").strip().lower() in WEAK_CAUSE or len(f.get("cause", "")) < 8:
            add("error", "no_cause", w, "write a concrete cause (file/line, cue or asset), not a guess")
        frames = f.get("frames", "")
        if cls != "audio-only":
            if not frames or frames.lower().startswith("none"):
                if nt["time"] or not frames.lower().startswith("none:"):
                    add("error", "no_frames", w, "a timed note needs a frame strip at the noted time (+-1 s; transitions every frame +-0.5 s)")
            elif root is not None and not (root / frames).is_file():
                add("error", "frames_missing", w, f"frame strip not found: {frames}")
        if cls == "replace-concept":
            rep = f.get("replacement", "")
            if len(rep) < 10:
                add("error", "no_replacement", w, "replace-concept needs the NEW beat concept, not a polish of the old one")
            elif POLISH_RE.search(rep):
                add("review", "polish_wording", w, "replacement reads like a polish; boring/looks-AI/static means replace the beat")
        if cls == "global-rule":
            occ = [o for o in re.split(r"[,;]", f.get("occurrences", "")) if o.strip()]
            if not occ:
                add("error", "no_occurrences", w, "a global rule must list EVERY occurrence fixed")
            elif len(occ) == 1:
                add("review", "single_occurrence", w, "global rule lists one occurrence; grep the whole film")
        if cls == "audio-only" and f.get("render", "").lower() not in ("none", "remix+remux", "remix-remux"):
            add("error", "audio_needs_no_render", w, "audio-only note must say `render: none` (remix + remux)")
    renders = [l for l in lines if re.match(r"^\s*RENDER\s+full\b", l)]
    all_audio = all(nt["fields"].get("class") == "audio-only" for nt in notes)
    if len(renders) > 1:
        add("error", "multiple_full_renders", f"round {n}", f"{len(renders)} full renders logged; target is exactly one per round")
    if all_audio and renders:
        add("error", "audio_only_round_rendered", f"round {n}", "every note is audio-only: remix + remux, no full render")
    if require_present and not any(re.match(r"^\s*PRESENTED\b", l) for l in lines):
        add("error", "not_presented", f"round {n}", "no PRESENTED line: present numbered by the user's notes first")
    if patch is not None and prompt_path is not None:
        try:
            if patch.stat().st_mtime + 1 < prompt_path.stat().st_mtime:
                add("error", "code_before_prompt", "order", "patch file is older than PROMPT.md changes: ledger -> PROMPT -> code order not shown")
        except OSError as exc:
            add("error", "order_not_run", "order", f"cannot stat patch/prompt: {exc}")
    elif patch is not None:
        add("review", "order_not_run", "order", "give --prompt as a file path to check order")
    errs = [x for x in findings if x["severity"] == "error"]
    res["status"] = "FAIL" if errs else ("NEEDS_REVIEW" if findings else "PASS")
    return res


EXIT = {"PASS": 0, "FAIL": 1, "INSUFFICIENT_EVIDENCE": 2, "NEEDS_REVIEW": 3}

_LOG = """## Round 3 (2026-10-05)
1. "the transition at 25 is bad" @ 0:24-0:26 | class: fix | ledger: L21 | cause: hidden source cut at 24.9 s, pre-roll 3 f | frames: _work/notes/r3_n1.jpg
2. "משעמם" @ 0:05 | class: replace-concept | ledger: L22 | cause: static caption over a static b-roll | replacement: split-screen proof card with a number counting up | frames: _work/notes/r3_n2.jpg
3. "SFX too loud" | class: audio-only | ledger: L23 | cause: gain above -18 dB under VO | render: none
4. "the speaker is never centred" | class: global-rule | ledger: L24 | cause: zoom origin not on face x | occurrences: 0:10, 0:17-0:24, 0:31 | frames: _work/notes/r3_n4.jpg
RENDER full _work/drafts/clinic_v3.mp4
PRESENTED 2026-10-05
"""
_PROMPT = " ".join(f"L2{i} L2{i}" for i in range(1, 5))


def _self_check() -> int:
    fails: list[str] = []

    def go(log: str, **kw) -> dict:
        return run(log, kw.get("rnd"), kw.get("prompt", _PROMPT), kw.get("patch"), kw.get("prompt_path"),
                   kw.get("root"), kw.get("require_present", True))

    def expect(name: str, res: dict, status: str, code: str | None = None) -> None:
        codes = {f["code"] for f in res["findings"]}
        if res["status"] != status or (code and code not in codes):
            fails.append(f"{name}: got {res['status']} {sorted(codes)}, wanted {status} {code or ''}")

    expect("complete round passes", go(_LOG), "PASS")
    expect("no round", go("# changelog\n"), "INSUFFICIENT_EVIDENCE", "no_round")
    expect("no notes", go("## Round 1\nPRESENTED\n"), "INSUFFICIENT_EVIDENCE", "no_notes")
    expect("bad class", go(_LOG.replace("class: fix", "class: polish")), "FAIL", "bad_class")
    expect("missing cause", go(_LOG.replace("cause: hidden source cut at 24.9 s, pre-roll 3 f", "cause: ?")), "FAIL", "no_cause")
    expect("timed note without frames", go(_LOG.replace(" | frames: _work/notes/r3_n1.jpg", "")), "FAIL", "no_frames")
    expect("replace-concept needs a replacement", go(_LOG.replace(" | replacement: split-screen proof card with a number counting up", "")), "FAIL", "no_replacement")
    expect("polish wording is reviewed", go(_LOG.replace("split-screen proof card with a number counting up", "tweak the caption a bit more")), "NEEDS_REVIEW", "polish_wording")
    expect("global rule needs occurrences", go(_LOG.replace(" | occurrences: 0:10, 0:17-0:24, 0:31", "")), "FAIL", "no_occurrences")
    expect("audio-only must not render", go(_LOG.replace("render: none", "render: full")), "FAIL", "audio_needs_no_render")
    expect("ledger id must reach PROMPT", go(_LOG, prompt="L21 L21 L22 L22 L23 L23"), "FAIL", "ledger_not_in_prompt")
    expect("two full renders fail", go(_LOG + "RENDER full _work/drafts/x.mp4\n"), "FAIL", "multiple_full_renders")
    all_audio = '## Round 4\n1. "music too loud" | class: audio-only | ledger: L21 | cause: bed at -10 dB under VO | render: none\nRENDER full a.mp4\nPRESENTED x\n'
    expect("audio-only round with a render fails", go(all_audio), "FAIL", "audio_only_round_rendered")
    expect("presented required", go(_LOG.replace("PRESENTED 2026-10-05\n", "")), "FAIL", "not_presented")
    expect("hebrew round heading is read", go(_LOG.replace("## Round 3", "## סבב 3")), "PASS")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "_work" / "notes").mkdir(parents=True)
        for name in ("r3_n1.jpg", "r3_n2.jpg", "r3_n4.jpg"):
            (root / "_work" / "notes" / name).write_bytes(b"x")
        expect("frames exist", go(_LOG, root=root), "PASS")
        (root / "_work" / "notes" / "r3_n2.jpg").unlink()
        expect("missing frame file", go(_LOG, root=root), "FAIL", "frames_missing")
        prompt, patch = root / "PROMPT.md", root / "patch.json"
        patch.write_text("{}", encoding="utf-8")
        prompt.write_text(_PROMPT, encoding="utf-8")
        now = time.time()
        os.utime(patch, (now - 100, now - 100))
        os.utime(prompt, (now, now))
        expect("patch older than PROMPT is code-first", go(_LOG, patch=patch, prompt_path=prompt, root=None), "FAIL", "code_before_prompt")
        os.utime(patch, (now + 100, now + 100))
        expect("patch after PROMPT passes", go(_LOG, patch=patch, prompt_path=prompt, root=None), "PASS")
    for f in fails:
        print("FAIL:", f)
    print("self-check:", "FAILED" if fails else "ok")
    return 1 if fails else 0


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return _self_check()
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    opts = {"--round": None, "--prompt": None, "--patch": None, "--root": None}
    flags = {"--require-present": False, "--json": False}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in opts:
            opts[a] = argv[i + 1]; i += 2
        elif a in flags:
            flags[a] = True; i += 1
        else:
            print("unknown option", a); return 2
    try:
        text = Path(argv[0]).read_text(encoding="utf-8")
        prompt = Path(opts["--prompt"]).read_text(encoding="utf-8") if opts["--prompt"] else None
    except OSError as exc:
        print(json.dumps({"tool": "round_check", "status": "INSUFFICIENT_EVIDENCE", "reason": str(exc)}))
        return 2
    res = run(text, int(opts["--round"]) if opts["--round"] else None, prompt,
              Path(opts["--patch"]) if opts["--patch"] else None,
              Path(opts["--prompt"]) if opts["--prompt"] else None,
              Path(opts["--root"]) if opts["--root"] else None, flags["--require-present"])
    if flags["--json"]:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"round_check {VERSION}: {res['status']}  round={res['round']} notes={res['notes']}")
        for f in res["findings"]:
            print(f"  [{f['severity']}] {f['code']} {f['where']}: {f['message']}")
        if not prompt:
            print("  note: no --prompt given: ledger -> PROMPT linkage was NOT checked")
    return EXIT[res["status"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

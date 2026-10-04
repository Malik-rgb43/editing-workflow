"""hf_segment - render ONLY a time range of a HyperFrames project, widened outward to whole scenes (a fast picture-only draft).

Why: a single-scene fix does not need a full render. The measured cost model (E12, six-note round on a synthetic 30 s project, the
the reference machine only): Studio preview + range renders + ONE full render = 240 s machine time vs 430 s for a full render per note.

How (algorithm recorded from the original tool, distilled 03 tools-inventory section 2.4, 2026-10-02): write a temporary
``index.seg.html`` in which (1) ``data-hf-id`` is stripped, (2) the range [A,B) is snapped outward to the start/end of every scene
(sub-composition host / clip with data-start+data-duration) it touches unless --no-snap, (3) audio elements are dropped (picture check),
(4) timed elements wholly outside the range are removed (parked media captures 0 frames and trips the coverage gate), (5) elements
starting before A are trimmed (data-media-start += cut*rate, data-duration -= cut, data-start=0), the rest are shifted by -A, (6) the
root data-duration becomes B-A, (7) when A > 0 a small script scrubs the ROOT GSAP timeline from A (the earlier shiftChildren approach
failed because GSAP renormalises negative child starts to 0). The wrapper uses offset 0 (the original's 1e-5 s offset made later units
visually lossless but not bit-exact, E11). Then `npx hyperframes render -c index.seg.html ...` under the heavy-job lock.

STATUS: the planner/rewriter (pure functions) is unit-tested; the scrub wrapper and the render call depend on HyperFrames runtime
internals (``window.__timelines``) and have NOT been run end-to-end against a live HyperFrames render in this repo: pin the tested
HyperFrames version, run the version-pinned smoke test (`tests/integration`, when added) and use `--dry-run` to inspect the plan first.
Use it for render-only risks (e.g. ``<video>`` layers ~1 frame offset); a Studio preview is the first review step.

Usage:
    python tools/hf_segment.py <hf-dir> --from 26.0 --to 28.5 [--no-snap] [--quality draft|delivery] [--out FILE] [--fps 30] [--workers N]
                               [--qa] [--dry-run] [--render-cmd "..."] [--eta 300] [--lock-wait 0]
    (--from/--to accept seconds ``26.0`` or frames ``f780``)
Exit: 0 segment rendered (and QA passed with --qa), 1 QA FAIL, 2 refused / failed, 75 lock busy.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

import _common  # noqa: F401

VOIDS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
SCRUB_JS = """<script data-hf-segment="scrub">
(function(){var A=%(A)s,D=%(D)s;var reg={};
window.__timelines=new Proxy(reg,{set:function(t,k,v){t[k]=v;return true}});
var tries=0;function wrap(){var ids=Object.keys(reg);if(!ids.length&&tries++<200){return setTimeout(wrap,10)}
var root=reg[ids[0]];if(!root||root.__hfSegWrapped)return;root.__hfSegWrapped=true;root.pause(0);
var outer=gsap.timeline({paused:true});outer.to({t:0},{t:D,duration:D,ease:"none",onUpdate:function(){root.totalTime(A+outer.time())}},0);
window.__timelines[ids[0]]=outer;}
wrap();})();
</script>"""


class _Span:
    __slots__ = ("tag", "attrs", "start", "start_end", "end")

    def __init__(self, tag, attrs, start, start_end):
        self.tag, self.attrs, self.start, self.start_end, self.end = tag, attrs, start, start_end, None


class _Scan(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text = text
        lines = text.split("\n")
        self.off = [0]
        for ln in lines:
            self.off.append(self.off[-1] + len(ln) + 1)
        self.spans: list[_Span] = []
        self.stack: list[_Span] = []

    def _pos(self):
        ln, col = self.getpos()
        return self.off[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        s = self._pos()
        raw = self.get_starttag_text()
        sp = _Span(tag, {k.lower(): (v if v is not None else "") for k, v in attrs}, s, s + len(raw))
        self.spans.append(sp)
        if tag in VOIDS:
            sp.end = sp.start_end
        else:
            self.stack.append(sp)

    def handle_startendtag(self, tag, attrs):
        s = self._pos()
        raw = self.get_starttag_text()
        sp = _Span(tag, {k.lower(): (v if v is not None else "") for k, v in attrs}, s, s + len(raw))
        sp.end = sp.start_end
        self.spans.append(sp)

    def handle_endtag(self, tag):
        e = self._pos()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                self.stack[i].end = e + len(f"</{tag}>")
                del self.stack[i:]
                break


def parse_time(v: str, fps: float) -> float:
    v = v.strip()
    return float(v[1:]) / fps if v.lower().startswith("f") else float(v)


def _num(s, default=None):
    try:
        return float(str(s).strip().rstrip("s"))
    except (TypeError, ValueError):
        return default


def plan_segment(html: str, a: float, b: float, *, fps: float = 30.0, snap: bool = True):
    """Pure planner: returns ``(A, B, actions)`` with the (snapped) range and one action per timed element."""
    sc = _Scan(html)
    sc.feed(html)
    sc.close()
    timed = []
    for sp in sc.spans:
        st, du = _num(sp.attrs.get("data-start")), _num(sp.attrs.get("data-duration"))
        if st is not None and du is not None and sp.tag not in ("html", "body"):
            timed.append((sp, st, st + du))
    A, B = a, b
    if snap:
        scenes = [(st, en) for sp, st, en in timed if sp.tag not in ("audio", "video", "img") and (sp.attrs.get("data-composition-src") or "clip" in sp.attrs.get("class", "").split() or sp.attrs.get("data-composition-id"))]
        changed = True
        while changed:
            changed = False
            for st, en in scenes:
                if st < B and en > A:
                    if st < A:
                        A, changed = st, True
                    if en > B:
                        B, changed = en, True
    A, B = round(A * fps) / fps, round(B * fps) / fps
    if B <= A:
        raise ValueError("empty range after snapping")
    actions = []
    for sp, st, en in timed:
        if sp.tag == "audio":
            actions.append((sp, "drop", None))
        elif en <= A or st >= B:
            actions.append((sp, "remove", None))
        elif st < A:
            actions.append((sp, "trim", A - st))
        else:
            actions.append((sp, "shift", None))
    return A, B, actions


def _set_attr(tagtext: str, name: str, value: str) -> str:
    pat = re.compile(rf"""(\s{name}\s*=\s*)("[^"]*"|'[^']*'|[^\s>]+)""", re.I)
    if pat.search(tagtext):
        return pat.sub(lambda m: f'{m.group(1)}"{value}"', tagtext, count=1)
    return re.sub(r"(/?>)$", f' {name}="{value}"\\1', tagtext, count=1)


def fmt(x: float) -> str:
    return f"{x:.6f}".rstrip("0").rstrip(".") or "0"


def rewrite(html: str, A: float, B: float, actions, *, fps: float = 30.0) -> str:
    """Apply the plan. Edits are applied from the end of the document backwards so offsets stay valid."""
    edits = []  # (start, end, replacement)
    for sp, act, cut in actions:
        if act in ("drop", "remove"):
            edits.append((sp.start, sp.end if sp.end is not None else sp.start_end, ""))
        else:
            t = html[sp.start : sp.start_end]
            st = _num(sp.attrs.get("data-start"), 0.0)
            du = _num(sp.attrs.get("data-duration"), 0.0)
            if act == "shift":
                t = _set_attr(t, "data-start", fmt(st - A))
            else:
                rate = _num(sp.attrs.get("data-playback-rate"), 1.0) or 1.0
                t = _set_attr(t, "data-start", "0")
                t = _set_attr(t, "data-duration", fmt(du - cut))
                if sp.tag in ("video", "audio"):
                    t = _set_attr(t, "data-media-start", fmt((_num(sp.attrs.get("data-media-start"), 0.0) or 0.0) + cut * rate))
            edits.append((sp.start, sp.start_end, t))
    # root duration
    sc = _Scan(html)
    sc.feed(html)
    for sp in sc.spans:
        if "data-composition-id" in sp.attrs and "data-duration" in sp.attrs and not any(e[0] == sp.start for e in edits):
            edits.append((sp.start, sp.start_end, _set_attr(html[sp.start : sp.start_end], "data-duration", fmt(B - A))))
            break
    edits.sort(key=lambda e: e[0], reverse=True)
    out = html
    last_start = None
    for s, e, rep in edits:
        if last_start is not None and e > last_start:  # nested inside an already removed span: skip
            continue
        out = out[:s] + rep + out[e:]
        last_start = s
    if A > 0:
        inj = SCRUB_JS % {"A": fmt(A), "D": fmt(B - A)}
        i = out.lower().find("<script")
        out = out[:i] + inj + "\n" + out[i:] if i >= 0 else out.replace("</body>", inj + "</body>", 1)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hf_segment", description=__doc__.split("\n\n")[0])
    ap.add_argument("hf")
    ap.add_argument("--from", dest="a", required=True)
    ap.add_argument("--to", dest="b", required=True)
    ap.add_argument("--no-snap", action="store_true")
    ap.add_argument("--quality", choices=["draft", "delivery"], default="draft")
    ap.add_argument("--out")
    ap.add_argument("--fps", type=float)
    ap.add_argument("--workers")
    ap.add_argument("--qa", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--render-cmd")
    ap.add_argument("--eta", type=float, default=300.0)
    ap.add_argument("--lock-wait", type=float, default=0.0)
    args = ap.parse_args(argv)

    from core.errors import LockBusy
    from core.config import load_config
    from core.lock import acquire
    from core.procs import run

    hf = Path(args.hf).resolve()
    idx = hf / "index.html"
    if not idx.is_file():
        print(f"hf_segment: {idx} not found", file=sys.stderr)
        return 2
    text = re.sub(r"""\s+data-hf-id\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", "", idx.read_text(encoding="utf-8"))
    fps = args.fps or _num(re.search(r'data-fps\s*=\s*["\']?([\d.]+)', text).group(1)) if re.search(r'data-fps\s*=\s*["\']?([\d.]+)', text) else (args.fps or 30.0)
    try:
        A, B, actions = plan_segment(text, parse_time(args.a, fps), parse_time(args.b, fps), fps=fps, snap=not args.no_snap)
    except ValueError as exc:
        print(f"hf_segment: {exc}", file=sys.stderr)
        return 2
    summary = {"requested": [args.a, args.b], "snapped": [A, B], "fps": fps, "actions": {k: sum(1 for _, a_, _ in actions if a_ == k) for k in ("drop", "remove", "trim", "shift")}}
    if args.dry_run:
        print(json.dumps(summary, indent=2))
        return 0
    seg = hf / "index.seg.html"
    out = Path(args.out) if args.out else hf.parent / "_work" / f"seg_{A:.2f}-{B:.2f}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    seg.write_text(rewrite(text, A, B, actions, fps=fps), encoding="utf-8")
    try:
        if args.render_cmd:
            cmd = shlex.split(args.render_cmd, posix=os.name != "nt")
        else:
            from core import hf_engine

            try:
                cmd = hf_engine.command(["render", "-c", "index.seg.html", "--fps", fmt(fps), "--quality", args.quality, "--sdr", "--output", str(out)])
            except hf_engine.EngineMissing as exc:
                print(f"hf_segment: {exc}", file=sys.stderr)
                return 2
            if args.workers:
                cmd += ["--workers", str(args.workers)]
        t0 = time.time()
        try:
            with acquire(load_config().lock_path, job="segment render", timeout=args.lock_wait):
                from core import hf_engine as _hf

                r = run(cmd, cwd=hf, env=_hf.run_env({"FFMPEG_ENCODE_TIMEOUT_MS": "3600000"}), timeout=args.eta * 3)
        except LockBusy as exc:
            print(f"hf_segment: {exc}", file=sys.stderr)
            return 75
    finally:
        seg.unlink(missing_ok=True)
    if r.timed_out or r.returncode != 0 or not out.is_file() or out.stat().st_mtime < t0 - 1:
        print(f"hf_segment: render failed or produced no fresh file (exit {r.returncode}, timed_out={r.timed_out})", file=sys.stderr)
        return 2
    print(json.dumps(dict(summary, out=str(out)), ensure_ascii=False))
    if args.qa:
        import subprocess

        q = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).with_name("frame_qa.py")), str(out), "--json-out", str(out) + ".qa.json"], capture_output=True, text=True, encoding="utf-8")
        return 0 if q.returncode == 0 else (1 if q.returncode == 1 else 2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

STATUS (first live run, HyperFrames 0.8.98, a real 20.8 s talking-head, the reference machine, 2026-10-04): a 3 s range rendered in
23.6 s vs 64 s for the whole film (4 workers); its picture, camera zoom and root motion matched the full render. Two bugs found on that
run are fixed (the root was trimmed like a clip; a whole-film layer forced every range to the full film). Known limit: a hosted
sub-composition that starts before the range (e.g. a whole-film caption block) restarts its animation at the segment start - the CLI
warns (`sub_restart`). Use it for render-only risks (``<video>`` layers, 3D, filters); a Studio preview is the first review step.

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
# The ROOT timeline is wrapped the moment it is registered and driven from A (verified on a real render, 2026-10-04: picture and root
# motion of a 3 s range matched the full render). A hosted sub-composition that starts BEFORE A is NOT corrected: HyperFrames 0.8.98
# nests sub-composition timelines inside the root itself, so in the segment its animation restarts at the segment start (a whole-film
# caption block showed its first words). The CLI warns about such hosts (`sub_restart` in its output).
SCRUB_JS = """<script data-hf-segment="scrub">
(function(){var A=%(A)s,D=%(D)s,R=%(R)s;var reg={};
window.__timelines=new Proxy(reg,{set:function(t,k,v){
if(v&&!v.__hfSegWrapped&&(k===R||(R===null&&!Object.keys(t).length))){v.__hfSegWrapped=true;v.pause(0);var o=gsap.timeline({paused:true});
o.to({t:0},{t:D,duration:D,ease:"none",onUpdate:function(){v.totalTime(A+o.time())}},0);t[k]=o;return true}
t[k]=v;return true}});})();
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
    root = _root_span(sc.spans)
    total = (_num(root.attrs.get("data-duration")) or 0.0) if root else 0.0
    timed = []
    for sp in sc.spans:
        st, du = _num(sp.attrs.get("data-start")), _num(sp.attrs.get("data-duration"))
        if st is not None and du is not None and sp.tag not in ("html", "body") and sp is not root:  # the root is the canvas, not a clip
            timed.append((sp, st, st + du))
    A, B = a, b
    if snap:
        # a layer that runs (almost) the whole film - the A-roll wrapper, the caption host - is not a scene: snapping to it would turn every
        # range render into a full render (found on a real talking-head, 2026-10-04); such layers are trimmed to the range instead
        persistent = (lambda st, en: total > 0 and (en - st) >= 0.9 * total)
        scenes = [(st, en) for sp, st, en in timed if sp.tag not in ("audio", "video", "img") and not persistent(st, en)
                  and (sp.attrs.get("data-composition-src") or "clip" in sp.attrs.get("class", "").split() or sp.attrs.get("data-composition-id"))]
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


def _root_span(spans):
    """The root composition: the first element with data-composition-id that is not a hosted sub-composition (no data-composition-src)."""
    for sp in spans:
        if "data-composition-id" in sp.attrs and not sp.attrs.get("data-composition-src"):
            return sp
    return None


def _set_attr(tagtext: str, name: str, value: str) -> str:
    pat = re.compile(rf"""(\s{name}\s*=\s*)("[^"]*"|'[^']*'|[^\s>]+)""", re.I)
    if pat.search(tagtext):
        return pat.sub(lambda m: f'{m.group(1)}"{value}"', tagtext, count=1)
    return re.sub(r"(/?>)$", f' {name}="{value}"\\1', tagtext, count=1)


def fmt(x: float) -> str:
    return f"{x:.6f}".rstrip("0").rstrip(".") or "0"


def sub_cuts(hf_dir: Path, actions) -> dict:
    """{inner composition id: seconds cut} for every TRIMMED hosted sub-composition (its file under hf_dir declares the inner id).
    These are the layers whose animation restarts at the segment start (see SCRUB_JS)."""
    out = {}
    for sp, act, cut in actions:
        src = sp.attrs.get("data-composition-src")
        if act != "trim" or not src:
            continue
        try:
            text = (hf_dir / src).read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r"""data-composition-id\s*=\s*["']([^"']+)["']""", text)
        if m:
            out[m.group(1)] = round(float(cut), 6)
    return out


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
                if st + du > B:  # ends after the range: clip the tail too
                    t = _set_attr(t, "data-duration", fmt(B - st))
            else:
                rate = _num(sp.attrs.get("data-playback-rate"), 1.0) or 1.0
                t = _set_attr(t, "data-start", "0")
                t = _set_attr(t, "data-duration", fmt(min(st + du, B) - A))
                if sp.tag in ("video", "audio"):
                    t = _set_attr(t, "data-media-start", fmt((_num(sp.attrs.get("data-media-start"), 0.0) or 0.0) + cut * rate))
            edits.append((sp.start, sp.start_end, t))
    # root duration = the range (the root is never treated as a clip)
    sc = _Scan(html)
    sc.feed(html)
    root = _root_span(sc.spans)
    if root is not None and "data-duration" in root.attrs:
        edits.append((root.start, root.start_end, _set_attr(html[root.start : root.start_end], "data-duration", fmt(B - A))))
    edits.sort(key=lambda e: e[0], reverse=True)
    out = html
    last_start = None
    for s, e, rep in edits:
        if last_start is not None and e > last_start:  # nested inside an already removed span: skip
            continue
        out = out[:s] + rep + out[e:]
        last_start = s
    if A > 0:
        rid = root.attrs.get("data-composition-id") if root is not None else None
        inj = SCRUB_JS % {"A": fmt(A), "D": fmt(B - A), "R": json.dumps(rid)}
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
    restart = sub_cuts(hf, actions) if A > 0 else {}
    if restart:
        summary["sub_restart"] = sorted(restart)
        print(f"hf_segment: WARNING sub-composition(s) {sorted(restart)} start before {fmt(A)} s: in this segment their animation restarts at the "
              "segment start (HyperFrames nests them in the root timeline). Judge those layers in Studio or in the full render, or start the "
              "range at their start.", file=sys.stderr)
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

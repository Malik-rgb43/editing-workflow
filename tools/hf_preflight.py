"""hf_preflight - static lint of a HyperFrames project (seconds, not an 8-minute render). Run it before ANY check/render.

Parses every HTML file with a real HTML parser (not regex over prose: E04-B06 - single vs double quotes changed the author's verdict),
so attribute quoting, case and ordering never change the result. Output is a QA envelope; ``decoded_frames``/``expected_frames``
count HTML FILES scanned (unit "files") so a project with nothing to scan can never pass.

ERROR rules (exit 1):
  studio_id         data-hf-id present (Studio writes it into index.html; strip before patching or rendering - never render with it)
  root_rtl          dir="rtl" (or direction:rtl CSS) on <html>, <body> or the root composition element (black render in the author's tests;
                    E12 could not reproduce it on HyperFrames 0.8.98 - kept as a never-break rule, re-test per version)
  duplicate_id      the same id twice in one file (a duplicate id steals CSS)
  negative_start    a negative data-start (shifts every clip; use max(0, ...))
  font_file_missing an @font-face url() that is a local file which does not exist (fonts come from files in hf/fonts/)
  color_grading_attr data-color-grading on an element (a grading shader stalls AMD; bake the grade with FFmpeg: grade_bake)
WARNING rules (exit 0; ``--strict`` makes them errors):
  media_in_3d       <video>/<img>/<audio> inside a transform-style: preserve-3d ancestor (media are composited in their own layer)
  media_parent_visibility  visibility:hidden on a parent of media (has no effect on the media layer; time it with its own data-start)
  tween_on_video    a GSAP tween that targets a <video> element directly (tween a wrapper instead)
  clip_longer_than_source  data-duration > the source file's duration (needs the file; otherwise reported as info)
  caption_below_rail  an element named *caption* whose inline top+height passes the rail (--rail-bottom, house preset 1450 of 1920)
  external_resource http(s) src/href/@import/url() - not deterministic, not private; use local files
  missing_clip_class element with data-start and data-duration but no class "clip"
  font_not_declared a font-family used in CSS with no @font-face and not a generic/system family
INFO: unmeasurable captions (no inline geometry), skipped checks. Idea-level checks not implemented yet: palette audit, face-box
overlap, caption-exit, look-alike glyph words, word-cue timing lint (see docs: v1.1 candidates).

Usage:
    python tools/hf_preflight.py <hf-project-dir | file.html> [--strict] [--rail-bottom 1450] [--canvas-height 1920] [--json-out r.json] [--human]
Exit: 0 PASS, 1 FAIL, 2 INSUFFICIENT_EVIDENCE (nothing to scan), 3 tool error.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import _common  # noqa: F401

TOOL = "hf_preflight"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
GENERIC_FONTS = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace", "inherit", "initial", "unset", "emoji", "math"}
MEDIA = {"video", "img", "audio"}


class El:
    __slots__ = ("tag", "attrs", "parent", "line", "style_text")

    def __init__(self, tag, attrs, parent, line):
        self.tag, self.attrs, self.parent, self.line = tag, dict(attrs), parent, line
        self.style_text = (self.attrs.get("style") or "").lower()

    def ancestors(self):
        p = self.parent
        while p is not None:
            yield p
            p = p.parent

    def cls(self):
        return set((self.attrs.get("class") or "").split())


class Doc(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.els: list[El] = []
        self.stack: list[El] = []
        self.styles: list[str] = []
        self.scripts: list[str] = []
        self._in = None
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        el = El(tag, [(k.lower(), v if v is not None else "") for k, v in attrs], self.stack[-1] if self.stack else None, self.getpos()[0])
        self.els.append(el)
        if tag in ("style", "script"):
            self._in, self._buf = tag, []
        if tag not in VOID:
            self.stack.append(el)

    def handle_startendtag(self, tag, attrs):
        el = El(tag, [(k.lower(), v if v is not None else "") for k, v in attrs], self.stack[-1] if self.stack else None, self.getpos()[0])
        self.els.append(el)

    def handle_endtag(self, tag):
        if tag == self._in:
            (self.styles if tag == "style" else self.scripts).append("".join(self._buf))
            self._in = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)


def _css_rules(css: str):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        yield m.group(1).strip(), m.group(2).lower()


def _selector_hits(selector: str, el: El) -> bool:
    for part in selector.split(","):
        part = part.strip().lower()
        if not part:
            continue
        last = re.split(r"[\s>+~]+", part)[-1]
        ok = True
        m = re.match(r"^([a-z][a-z0-9-]*)?", last)
        if m and m.group(1) and m.group(1) != el.tag:
            ok = False
        for c in re.findall(r"\.([a-z0-9_-]+)", last):
            if c not in {x.lower() for x in el.cls()}:
                ok = False
        for i in re.findall(r"#([a-z0-9_-]+)", last):
            if i != (el.attrs.get("id") or "").lower():
                ok = False
        if ok and (m.group(1) or ".'" in last or "." in last or "#" in last):
            return True
    return False


def lint_html(text: str, path: Path, *, rail_bottom=1450.0, canvas_height=1920.0, probe_dur=None):
    """Return a list of (code, severity, message, line, data). Pure; unit-tested."""
    d = Doc()
    d.feed(text)
    d.close()
    out = []

    def add(code, sev, msg, line=None, **data):
        out.append((code, sev, msg, line, data))

    css_all = "\n".join(d.styles)
    rules = list(_css_rules(css_all))

    # -- Studio ids
    for el in d.els:
        if "data-hf-id" in el.attrs:
            add("studio_id", "error", "data-hf-id found (written by Studio): strip it before patching/rendering", el.line)
            break
    # -- root rtl
    roots = [e for e in d.els if e.tag in ("html", "body")]
    comp_roots = [e for e in d.els if "data-composition-id" in e.attrs and not any("data-composition-id" in a.attrs for a in e.ancestors())]
    for el in roots + comp_roots:
        if (el.attrs.get("dir") or "").lower() == "rtl" or re.search(r"direction\s*:\s*rtl", el.style_text):
            add("root_rtl", "error", f'dir="rtl" / direction:rtl on <{el.tag}> root: put RTL only on text elements', el.line)
    for sel, body in rules:
        if re.search(r"direction\s*:\s*rtl", body) and any(re.fullmatch(r"(html|body|:root|#root|\.root)", s.strip().lower()) for s in sel.split(",")):
            add("root_rtl", "error", f"CSS rule {sel!r} sets direction:rtl on the root: put RTL only on text elements")
    # -- duplicate ids
    seen = {}
    for el in d.els:
        i = el.attrs.get("id")
        if i:
            if i in seen:
                add("duplicate_id", "error", f"duplicate id {i!r} (first at line {seen[i]})", el.line, id=i)
            else:
                seen[i] = el.line
    # -- negative start, color grading, clip class
    for el in d.els:
        s = el.attrs.get("data-start")
        if s is not None:
            try:
                if float(s.strip().rstrip("s")) < 0:
                    add("negative_start", "error", f"negative data-start={s!r}: shifts every clip", el.line)
            except ValueError:
                pass
        if "data-color-grading" in el.attrs:
            add("color_grading_attr", "error", "data-color-grading is a render-time shader (stalls AMD); bake the grade with FFmpeg (grade_bake)", el.line)
        if "data-start" in el.attrs and "data-duration" in el.attrs and "clip" not in el.cls() and "data-composition-id" not in el.attrs:  # a composition root/host is timed, not a clip
            add("missing_clip_class", "warning", 'element has data-start and data-duration but no class="clip"', el.line)
    # -- media in 3d / hidden parent
    pres3d_sel = [sel for sel, body in rules if "preserve-3d" in body]
    hidden_sel = [sel for sel, body in rules if re.search(r"visibility\s*:\s*hidden", body)]
    for el in d.els:
        if el.tag not in MEDIA:
            continue
        for a in el.ancestors():
            if "preserve-3d" in a.style_text or any(_selector_hits(s, a) for s in pres3d_sel):
                add("media_in_3d", "warning", f"<{el.tag}> inside a preserve-3d parent (line {a.line}): media are composited in their own layer; use CSS background-image for images in 3D cards", el.line)
                break
        for a in el.ancestors():
            if re.search(r"visibility\s*:\s*hidden", a.style_text) or any(_selector_hits(s, a) for s in hidden_sel):
                add("media_parent_visibility", "warning", f"<{el.tag}> has a visibility:hidden parent (line {a.line}): it has no effect on the media layer; time the media with its own data-start", el.line)
                break
    # -- tweens on video
    vid_ids = {e.attrs["id"] for e in d.els if e.tag == "video" and e.attrs.get("id")}
    vid_cls = {c for e in d.els if e.tag == "video" for c in e.cls()}
    js = "\n".join(d.scripts)
    for m in re.finditer(r"""\.(?:to|from|fromTo|set)\(\s*(['"`])([^'"`]+)\1""", js):
        target = m.group(2).strip()
        if (target.startswith("#") and target[1:] in vid_ids) or (target.startswith(".") and target[1:] in vid_cls) or target == "video":
            add("tween_on_video", "warning", f"GSAP tween targets the <video> directly ({target!r}): tween a wrapper element instead")
    # -- clip longer than source
    if probe_dur is not None:
        for el in d.els:
            if el.tag in ("video", "audio") and el.attrs.get("src") and el.attrs.get("data-duration"):
                src = el.attrs["src"]
                if re.match(r"^[a-z]+://", src, re.I):
                    continue
                dur = probe_dur((path.parent / src).resolve())
                if dur is None:
                    add("source_not_probed", "info", f"could not read the duration of {src!r}; clip-length check skipped", el.line)
                else:
                    try:
                        want = float(el.attrs["data-duration"])
                    except ValueError:
                        continue
                    if want > dur + 0.05:
                        add("clip_longer_than_source", "warning", f"data-duration {want:g}s > source {src!r} duration {dur:.3f}s", el.line, wanted=want, source=dur)
    # -- captions below rail (inline geometry only)
    unmeasured = 0
    for el in d.els:
        name = ((el.attrs.get("id") or "") + " " + (el.attrs.get("class") or "")).lower()
        if "caption" not in name or el.tag in ("script", "style"):
            continue
        st = el.style_text
        top = re.search(r"(?<![a-z-])top\s*:\s*(-?[\d.]+)px", st)
        height = re.search(r"(?<![a-z-])height\s*:\s*([\d.]+)px", st)
        bottom = re.search(r"(?<![a-z-])bottom\s*:\s*(-?[\d.]+)px", st)
        if top and height:
            edge = float(top.group(1)) + float(height.group(1))
            if edge > rail_bottom * (canvas_height / 1920.0):
                add("caption_below_rail", "warning", f"caption bottom edge {edge:g}px passes the rail {rail_bottom * canvas_height / 1920.0:g}px", el.line)
        elif bottom:
            edge = canvas_height - float(bottom.group(1))
            if edge > rail_bottom * (canvas_height / 1920.0):
                add("caption_below_rail", "warning", f"caption bottom edge {edge:g}px passes the rail", el.line)
        else:
            unmeasured += 1
    if unmeasured:
        add("captions_unmeasured", "info", f"{unmeasured} caption element(s) have no inline top/height/bottom: the rail was not measured statically (caption_qa measures the render)")
    # -- external resources
    for el in d.els:
        for attr in ("src", "href"):
            v = el.attrs.get(attr, "")
            if re.match(r"^(https?:)?//", v.strip(), re.I) and el.tag in ("script", "link", "img", "video", "audio", "source", "iframe"):
                add("external_resource", "warning", f"<{el.tag} {attr}={v[:60]!r}> is a network resource: use a local file (deterministic, private)", el.line)
    for m in re.finditer(r"""(?:@import\s+(?:url\()?|url\()\s*['"]?(https?:)?//[^)'"\s]+""", css_all):
        add("external_resource", "warning", f"CSS references a network resource: {m.group(0)[:70]!r}")
    # -- fonts
    declared = set()
    for m in re.finditer(r"@font-face\s*\{([^}]*)\}", css_all, flags=re.S | re.I):
        body = m.group(1)
        fam = re.search(r"font-family\s*:\s*['\"]?([^;'\"]+)", body, re.I)
        if fam:
            declared.add(fam.group(1).strip().lower())
        for u in re.finditer(r"url\(\s*['\"]?([^)'\"]+)", body, re.I):
            url = u.group(1).strip()
            if url.startswith("data:") or re.match(r"^(https?:)?//", url):
                continue
            if not (path.parent / url.split("?")[0].split("#")[0]).exists():
                add("font_file_missing", "error", f"@font-face file not found: {url!r} (fonts come from files in hf/fonts/)", None, url=url)
    used = set()
    for _, body in rules:
        for m in re.finditer(r"font-family\s*:\s*([^;]+)", body):
            used |= _named_families(m.group(1))
    for el in d.els:
        for m in re.finditer(r"font-family\s*:\s*([^;]+)", el.style_text):
            used |= _named_families(m.group(1))
    for f in sorted(used - declared):
        add("font_not_declared", "warning", f"font-family {f!r} is used but has no @font-face file (the renderer's Chrome does not find fonts by name)", None, family=f)
    return out


def _named_families(value: str) -> set:
    """Font families named in a font-family value. var(--x, fallback) contributes only its fallback; generic families are skipped."""
    names = set()
    for f in value.split(","):
        f = re.sub(r"var\(\s*--[\w-]+\s*", "", f).strip().rstrip(")").strip().strip("'\"").strip().lower()
        if f and f not in GENERIC_FONTS and not f.startswith("--"):
            names.add(f)
    return names


def collect_files(target: Path):
    if target.is_file():
        return [target]
    files = []
    idx = target / "index.html"
    if idx.is_file():
        files.append(idx)
    comp = target / "compositions"
    if comp.is_dir():
        files += sorted(comp.glob("*.html"))
    return files


def _probe_duration(p: Path):
    try:
        from core.ffprobe import probe

        d = probe(p).duration_s
        return float(d) if d is not None else None
    except Exception:  # noqa: BLE001
        return None


def run(args, b):
    from core.envelope import Finding, Severity, sha256_file

    target = Path(args.target)
    if not target.exists():
        b.gap("target_missing", f"{target} does not exist")
        b.set_frames(decoded=0, expected=0)
        return
    files = collect_files(target)
    b.set_frames(decoded=len(files), expected=len(files))
    b.extra["unit"] = "files"
    if not files:
        b.gap("nothing_to_scan", "no index.html / compositions/*.html found: an empty scan is never a pass")
        return
    b.set_input_sha256(sha256_file(files[0]) if len(files) == 1 else __import__("hashlib").sha256(b"".join(sha256_file(f).encode() for f in files)).hexdigest())
    b.extra["files"] = [str(f) for f in files]
    sev_map = {"error": Severity.ERROR, "warning": Severity.ERROR if args.strict else Severity.WARNING, "info": Severity.INFO}
    for f in files:
        text = f.read_text(encoding="utf-8", errors="strict")
        for code, sev, msg, line, data in lint_html(text, f, rail_bottom=args.rail_bottom, canvas_height=args.canvas_height, probe_dur=_probe_duration):
            data = dict(data, file=f.name)
            b.add(Finding(code, f"[{f.name}] {msg}", sev_map[sev], data=data) if line is None else Finding(code, f"[{f.name}:{line}] {msg}", sev_map[sev], data=dict(data, line=line)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hf_preflight", description=__doc__.split("\n\n")[0])
    ap.add_argument("target")
    ap.add_argument("--strict", action="store_true", help="warnings fail too (use before a final render)")
    ap.add_argument("--rail-bottom", type=float, default=1450.0)
    ap.add_argument("--canvas-height", type=float, default=1920.0)
    ap.add_argument("--json-out")
    ap.add_argument("--human", action="store_true", help="print a short human summary on stderr")
    args = ap.parse_args(argv)
    code = _common.qa_main(TOOL, lambda b: run(args, b), args.target if os.path.isfile(args.target) else None, out_json=args.json_out)
    return code


if __name__ == "__main__":
    sys.exit(main())

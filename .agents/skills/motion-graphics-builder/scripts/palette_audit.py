#!/usr/bin/env python3
"""palette_audit.py - audit every colour in a composition (and optional 3D renders) against ONE locked palette.

Usage:
    python palette_audit.py DESIGN.md PATH [PATH ...] [--tolerance 0] [--allow #ffffff #000000]
                            [--forbid-hue 300-345] [--png RENDER.png ...] [--hue-tol 25]
                            [--max-off-share 0.03] [--json]
    python palette_audit.py --self-check

DESIGN.md must contain a palette table whose header has a "hex" column (a "role" column is read
when present). PATH may be files or directories (.html .css .js .svg .jsx .ts .json are scanned;
node_modules, .git, _work and renders are skipped).

Checks
  P01 every hex / rgb() found in the sources is in the palette (RGB distance <= --tolerance)
  P02 optional --forbid-hue A-B : no palette colour and no source colour in that hue range
      (the author's studio preset is 300-345 = pink/magenta; a student may lock any palette,
       so the flag is OFF by default - the rule taught is "lock ONE palette")
  P03 palette sanity: > 3 distinct chromatic hue families is a warning (neutrals + ONE accent
      family + ONE keyword colour + optional alert)
  P04 --png renders (3D sprites, stills): share of opaque chromatic pixels whose hue is further
      than --hue-tol degrees from every palette hue (heuristic - lighting/AgX shift hues; a
      pass is not a visual review). Pillow is used when installed, otherwise a stdlib PNG
      reader (8/16-bit RGB/RGBA, non-interlaced, <= 1.5 MP). Anything else => not_run (fails closed).

Exit codes: 0 pass | 1 fail | 2 blocked/not_run (no palette parsed, nothing scanned, a render
that could not be read). Stdlib only (Pillow optional).
"""
import argparse
import colorsys
import json
import re
import struct
import sys
import tempfile
import zlib
from pathlib import Path

EXTS = {".html", ".css", ".js", ".svg", ".jsx", ".ts", ".tsx", ".json"}
SKIP = {"node_modules", ".git", "_work", "renders", "__pycache__"}
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGB_RE = re.compile(r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})")


def norm_hex(h):
    h = h.lstrip("#").lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h[:6]


def to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hsv(rgb):
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    return h * 360, s, v


def chromatic(rgb):
    h, s, v = hsv(rgb)
    return s >= 0.25 and v >= 0.2


def hue_dist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def parse_palette(text):
    """Return list of {hex, role} from the first table that has a 'hex' column."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines[i:j]]
            head = [c.lower() for c in rows[0]]
            hx = next((k for k, c in enumerate(head) if "hex" in c or "colour" in c or "color" in c), None)
            rl = next((k for k, c in enumerate(head) if "role" in c), None)
            if hx is not None:
                out = []
                for r in rows[1:]:
                    if hx < len(r):
                        m = HEX_RE.search(r[hx])
                        if m:
                            out.append({"hex": norm_hex(m.group(0)), "role": r[rl] if rl is not None and rl < len(r) else ""})
                if out:
                    return out
            i = j
        else:
            i += 1
    return []


def iter_files(paths):
    for p in paths:
        p = Path(p)
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in EXTS and not (set(f.parts) & SKIP):
                    yield f


def colours_in(path):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in HEX_RE.finditer(line):
            found.append((norm_hex(m.group(0)), n))
        for m in RGB_RE.finditer(line):
            r, g, b = (min(255, int(x)) for x in m.groups())
            found.append(("#%02x%02x%02x" % (r, g, b), n))
    return found


USE_PILLOW = True


def read_png(path, max_px=1_500_000):
    """Return (w, h, [(r,g,b,a), ...] sampled) or None when not readable. Pillow first."""
    if USE_PILLOW:
        try:
            from PIL import Image  # type: ignore
            im = Image.open(path).convert("RGBA")
            im.thumbnail((256, 256))
            w, h = im.size
            getter = getattr(im, "get_flattened_data", None) or im.getdata
            return w, h, list(getter())
        except Exception:
            pass
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos, idat, ihdr = 8, b"", None
    while pos + 8 <= len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", chunk)
        elif typ == b"IDAT":
            idat += chunk
        pos += 12 + ln
    if not ihdr:
        return None
    w, h, depth, ctype, _, _, inter = ihdr
    if inter != 0 or ctype not in (2, 6) or depth not in (8, 16) or w * h > max_px:
        return None
    ch = 3 if ctype == 2 else 4
    bpp = ch * depth // 8
    stride = w * bpp
    raw = zlib.decompress(idat)
    if len(raw) < h * (stride + 1):
        return None
    prev = bytearray(stride)
    px = []
    step = max(1, (w * h) // 40000)
    off = 0
    for _ in range(h):
        ft = raw[off]
        cur = bytearray(raw[off + 1:off + 1 + stride])
        off += stride + 1
        for i in range(stride):
            a = cur[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ft == 1:
                cur[i] = (cur[i] + a) & 255
            elif ft == 2:
                cur[i] = (cur[i] + b) & 255
            elif ft == 3:
                cur[i] = (cur[i] + ((a + b) >> 1)) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                cur[i] = (cur[i] + pr) & 255
        prev = cur
        for x in range(0, w, step):
            o = x * bpp
            if depth == 8:
                r, g, bl = cur[o], cur[o + 1], cur[o + 2]
                al = cur[o + 3] if ch == 4 else 255
            else:
                r, g, bl = cur[o], cur[o + 2], cur[o + 4]
                al = cur[o + 6] if ch == 4 else 255
            px.append((r, g, bl, al))
    return w, h, px


def audit(design_text, sources, pngs=(), tolerance=0, allow=(), forbid=None, hue_tol=25, max_off=0.03):
    findings, summary = [], {}
    pal = parse_palette(design_text)
    if not pal:
        return [("error", "P00", "no palette table with a 'hex' column found in DESIGN.md")], {"verdict": "blocked", "reason": "no palette"}
    palette = [p["hex"] for p in pal]
    allow_set = {norm_hex(a) for a in allow}
    chroma_h = [hsv(to_rgb(h))[0] for h in palette if chromatic(to_rgb(h))]
    fams = []
    for hh in chroma_h:
        if not any(hue_dist(hh, f) <= 25 for f in fams):
            fams.append(hh)
    if len(fams) > 3:
        findings.append(("warn", "P03", f"palette has {len(fams)} chromatic hue families (neutrals + ONE accent family + ONE keyword colour + optional alert)"))
    fb = None
    if forbid:
        a, b = (float(x) for x in forbid.split("-"))
        fb = (a, b)
        for hx in palette:
            h, s, v = hsv(to_rgb(hx))
            if s >= 0.2 and v >= 0.2 and a <= h <= b:
                findings.append(("error", "P02", f"palette colour {hx} has hue {h:.0f} inside the forbidden range {forbid}"))
    scanned = 0
    out_of = {}
    for f in iter_files(sources):
        cols = colours_in(f)
        if cols is None:
            findings.append(("error", "P00", f"cannot read {f}"))
            continue
        scanned += 1
        for hx, ln in cols:
            if hx in allow_set:
                continue
            rgb = to_rgb(hx)
            dist = min(sum((x - y) ** 2 for x, y in zip(rgb, to_rgb(p))) ** 0.5 for p in palette)
            if dist > tolerance:
                out_of.setdefault(hx, []).append(f"{f.name}:{ln}")
            if fb:
                h, s, v = hsv(rgb)
                if s >= 0.2 and v >= 0.2 and fb[0] <= h <= fb[1]:
                    findings.append(("error", "P02", f"{f.name}:{ln} colour {hx} hue {h:.0f} inside forbidden {forbid}"))
    for hx, where in sorted(out_of.items()):
        findings.append(("error", "P01", f"{hx} not in palette ({len(where)}x, first {where[0]})"))
    renders = {}
    for png in pngs:
        img = read_png(png)
        if img is None:
            findings.append(("error", "P04", f"{png}: render could not be read (not_run; install Pillow or downscale)"))
            renders[str(png)] = "not_run"
            continue
        _, _, px = img
        chrom = off = 0
        for r, g, b, a in px:
            if a < 128 or not chromatic((r, g, b)):
                continue
            chrom += 1
            h = hsv((r, g, b))[0]
            bad = bool(fb and fb[0] <= h <= fb[1])
            if bad or (chroma_h and min(hue_dist(h, ph) for ph in chroma_h) > hue_tol) or (not chroma_h):
                off += 1
        share = (off / chrom) if chrom else 0.0
        renders[str(png)] = {"chromatic_px": chrom, "off_palette_share": round(share, 4)}
        if chrom == 0:
            findings.append(("warn", "P04", f"{png}: no chromatic opaque pixels sampled (greyscale/empty) - nothing to audit"))
        elif share > max_off:
            findings.append(("error", "P04", f"{png}: {share:.1%} of chromatic pixels are > {hue_tol} deg from every palette hue (limit {max_off:.0%})"))
    summary.update({"palette": palette, "files_scanned": scanned, "renders": renders})
    errs = [f for f in findings if f[0] == "error"]
    if scanned == 0 and not pngs:
        summary.update(verdict="blocked", reason="nothing scanned (empty sample never passes)")
    elif any(isinstance(v, str) and v == "not_run" for v in renders.values()):
        summary.update(verdict="blocked", reason="a render could not be read")
    elif any(f[1] == "P00" for f in errs):
        summary.update(verdict="blocked", reason="unreadable input")
    elif errs:
        summary.update(verdict="fail", reason=f"{len(errs)} error(s)")
    else:
        summary.update(verdict="pass", reason="every colour is inside the locked palette (heuristic for renders)")
    return findings, summary


def make_png(w, h, rgba, depth=8):
    rows = b""
    for _ in range(h):
        row = b"\x00"
        for _x in range(w):
            for c in rgba:
                row += bytes([c]) if depth == 8 else struct.pack(">H", c * 257)
        rows += row

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


DESIGN = """# DESIGN
| role | hex |
|---|---|
| ground | #0B0D12 |
| text | #E8ECF2 |
| accent | #2F6BFF |
| keyword | #FCE500 |
"""


def self_check():
    global USE_PILLOW
    bad = []
    for use in (True, False):  # exercise Pillow when present AND the stdlib reader
        USE_PILLOW = use
        bad += _self_check_once(use)
    USE_PILLOW = True
    if bad:
        print("SELF-CHECK FAILED")
        for b in bad:
            print(" -", b)
        return 1
    print("SELF-CHECK OK (12 cases x 2 PNG readers)")
    return 0


def _self_check_once(use):
    bad = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "ok.html").write_text('<div style="color:#e8ecf2;background:#0b0d12">x</div><i style="color:rgb(47,107,255)"></i>', encoding="utf-8")
        (td / "bad.css").write_text(".a{color:#ff2fb3}\n.b{color:#FCE500}", encoding="utf-8")
        (td / "blue.png").write_bytes(make_png(8, 8, (47, 107, 255, 255)))
        (td / "blue16.png").write_bytes(make_png(8, 8, (47, 107, 255, 255), depth=16))
        (td / "pink.png").write_bytes(make_png(8, 8, (255, 47, 179, 255)))
        (td / "bad.png").write_bytes(b"not a png")

        def run(srcs, pngs=(), **kw):
            return audit(DESIGN, [td / s for s in srcs], [td / p for p in pngs], **kw)
        f, s = run(["ok.html"])
        if s["verdict"] != "pass":
            bad.append(f"ok.html should pass: {s} {f}")
        f, s = run(["bad.css"])
        if s["verdict"] != "fail" or not any(x[1] == "P01" and "#ff2fb3" in x[2] for x in f):
            bad.append(f"bad.css should fail P01: {s}")
        f, s = run(["ok.html"], forbid="300-345")
        if s["verdict"] != "pass":
            bad.append("forbid-hue must not flag a blue palette")
        f, s = audit(DESIGN.replace("#FCE500", "#FF2FB3"), [td / "ok.html"], forbid="300-345")
        if s["verdict"] != "fail" or not any(x[1] == "P02" for x in f):
            bad.append("palette containing pink must fail P02 when pink is forbidden")
        f, s = run(["ok.html"], pngs=["blue.png"])
        if s["verdict"] != "pass":
            bad.append(f"blue render should pass: {s} {f}")
        f, s = run(["ok.html"], pngs=["blue16.png"])
        if s["verdict"] != "pass":
            bad.append(f"16-bit blue render should pass: {s} {f}")
        f, s = run(["ok.html"], pngs=["pink.png"])
        if s["verdict"] != "fail" or not any(x[1] == "P04" for x in f):
            bad.append(f"pink render should fail P04: {s} {f}")
        f, s = run(["ok.html"], pngs=["bad.png"])
        if s["verdict"] != "blocked":
            bad.append("unreadable render must be blocked (not_run), never pass")
        f, s = run([])
        if s["verdict"] != "blocked":
            bad.append("empty scan must be blocked")
        f, s = audit("no table here", [td / "ok.html"])
        if s["verdict"] != "blocked":
            bad.append("missing palette table must be blocked")
        f, s = run(["bad.css"], allow=["#ff2fb3"])
        if s["verdict"] != "pass":
            bad.append("--allow must whitelist a colour")
        f, s = run(["bad.css"], tolerance=400)
        if s["verdict"] != "pass":
            bad.append("tolerance must widen the match")
    return [f"[pillow={use}] {b}" for b in bad]


def main(argv=None):
    try:  # Hebrew paths / non-ASCII messages must not crash on a legacy console code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("design", nargs="?")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--tolerance", type=float, default=0)
    ap.add_argument("--allow", nargs="*", default=[])
    ap.add_argument("--forbid-hue")
    ap.add_argument("--png", nargs="*", default=[])
    ap.add_argument("--hue-tol", type=float, default=25)
    ap.add_argument("--max-off-share", type=float, default=0.03)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if not a.design:
        ap.print_usage()
        return 2
    try:
        text = Path(a.design).read_text(encoding="utf-8")
    except OSError as e:
        print(f"BLOCKED: cannot read {a.design}: {e}")
        return 2
    findings, summ = audit(text, a.paths, a.png, a.tolerance, a.allow, a.forbid_hue, a.hue_tol, a.max_off_share)
    if a.json:
        print(json.dumps({"summary": summ, "findings": [{"severity": s, "code": c, "message": m} for s, c, m in findings]}, ensure_ascii=False, indent=2))
    else:
        for s, c, m in findings:
            print(f"[{s.upper():5}] {c}: {m}")
        print(f"VERDICT: {summ['verdict']} - {summ['reason']}  (files scanned: {summ.get('files_scanned', 0)})")
        print("note: colour tokens are not appearance; view the render. Renders are a hue-share heuristic.")
    return {"pass": 0, "fail": 1, "blocked": 2}[summ["verdict"]]


if __name__ == "__main__":
    sys.exit(main())

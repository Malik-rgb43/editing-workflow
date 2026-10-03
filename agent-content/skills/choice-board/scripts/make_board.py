#!/usr/bin/env python3
"""Build ONE self-contained, RTL-safe HTML choice board from a JSON spec, and read the pick back.

Usage:
  python make_board.py build SPEC.json [--out DIR] [--built-utc 2026-10-02T12:00:00Z]
  python make_board.py verify DIR/board_manifest.json choices.json [--json]
  python make_board.py --self-check            # runs scripts/test_make_board.py

build   writes DIR/choice-board.html and DIR/board_manifest.json (default DIR = the spec's folder).
        The page has NO remote resources (fonts and the still are embedded as data URIs), works offline by
        double click, shows the user's real text, 8-12 options per decision (2 minimum, 12 maximum), a phone
        frame per option, a "none of these + comment" slot, keyboard picks (1-9, 0, q, w; n = none), tabs with
        arrow keys, a pause switch (and prefers-reduced-motion), an export gate (every decision answered) and
        a choices.json download plus a copy/paste box for hosts where downloads are blocked.
verify  checks choices.json against the manifest (board id, decision ids, option ids, none needs a comment,
        embedded asset hashes) and prints one decision line per decision for the agent to apply.
Exit codes: 0 ok, 1 invalid choices / failed self-check, 2 invalid spec or unreadable input.

Spec: references/spec-format.md. Sample: references/sample-spec.json. Hostile or Hebrew text is safe: all text
is escaped in HTML and written with textContent in the page's script. Not included in v0.1: ranking.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSION = "0.1.0"
KINDS = {"font", "caption_anim", "easing", "palette", "transition", "layout", "text"}
BANNED_DEFAULT = ["bounce", "crossfade"]
ANIMS = {"rise", "slide_up", "blur_in", "scale_in", "word_rise", "karaoke", "mask_wipe", "bounce"}
TRANS = {"wipe", "push", "iris", "slide_up", "crossfade"}
WORD_ANIMS = {"word_rise", "karaoke"}
LOREM = re.compile(r"lorem|ipsum|dolor sit|טקסט לדוגמה|כאן יבוא", re.I)
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,20}$")
DEC_RE = re.compile(r"^[a-z][a-z0-9_]{0,24}$")
FAMILY_RE = re.compile(r"^[A-Za-z0-9 _\-֐-׿]{1,60}$")
LOOKALIKES = [("ו", "ז"), ("ד", "ר"), ("ה", "ח")]  # vav/zayin, dalet/resh, he/het
FONT_MIME = {".ttf": ("font/ttf", "truetype"), ".otf": ("font/otf", "opentype"),
             ".woff": ("font/woff", "woff"), ".woff2": ("font/woff2", "woff2")}
IMG_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
KEYS = "1234567890qw"
UI = {
    "he": {"dir": "rtl", "sample": "הטקסט שלך (אפשר לערוך)", "pause": "השהיה", "clear": "ניקוי בחירות (לא מאפס את השעון)",
           "none": "אף אחד מאלה", "comment": "הערה (חובה אם בחרת 'אף אחד')", "reject": "דחייה", "export": "ייצוא choices.json",
           "summary": "הבחירות שלך", "copy": "העתקת JSON", "pending": "לא נבחר", "saved": "choices.json הורד. אפשר גם להדביק את ה-JSON בצ'אט.",
           "need": "חסרה בחירה", "needc": "חסרה הערה עבור 'אף אחד'", "hint": "מקשים: 1-9, 0, q, w = אפשרות · n = אף אחד",
           "contrast": "ניגודיות", "low": "נמוכה", "emb": "מוטמע", "sysf": "פונט מערכת: ייתכן fallback", "warn_rail": "מחוץ לאזור הבטוח",
           "spec": "דגימת מילת מפתח"},
    "en": {"dir": "ltr", "sample": "Your text (editable)", "pause": "Pause", "clear": "Clear choices (does not restart the clock)",
           "none": "None of these", "comment": "Comment (required if you pick 'none')", "reject": "Reject", "export": "Export choices.json",
           "summary": "Your picks", "copy": "Copy JSON", "pending": "not chosen", "saved": "choices.json downloaded. You can also paste the JSON into the chat.",
           "need": "Missing a pick", "needc": "Missing a comment for 'none'", "hint": "Keys: 1-9, 0, q, w = option · n = none",
           "contrast": "contrast", "low": "low", "emb": "embedded", "sysf": "system font: may fall back", "warn_rail": "outside the safe zone",
           "spec": "Keyword specimen"},
}


class SpecError(Exception):
    pass


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def lum(hexc: str) -> float:
    h = hexc.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    ch = []
    for i in (0, 2, 4):
        v = int(h[i:i + 2], 16) / 255
        ch.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def lookalike_letters(word: str) -> list[str]:
    return [c for pair in LOOKALIKES for c in pair if c in word]


def pick_keyword(spec: dict) -> str:
    if spec.get("keyword"):
        return str(spec["keyword"])
    words = re.findall(r"[א-ת]{3,}", spec.get("text", ""))
    for w in sorted(words, key=len, reverse=True):
        if lookalike_letters(w):
            return w
    return words[0] if words else ""


def embed(path: Path, kind: str, base: Path, cap_kb: int) -> tuple[str, str, str, int]:
    p = path if path.is_absolute() else base / path
    if not p.is_file():
        raise SpecError(f"file not found: {path}")
    data = p.read_bytes()
    if len(data) > cap_kb * 1024:
        raise SpecError(f"{path} is {len(data) // 1024} KB; limit {cap_kb} KB (subset or resize it)")
    ext = p.suffix.lower()
    table = FONT_MIME if kind == "font" else IMG_MIME
    if ext not in table:
        raise SpecError(f"unsupported {kind} type {ext}")
    mime = table[ext][0] if kind == "font" else table[ext]
    fmt = table[ext][1] if kind == "font" else ""
    uri = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    return uri, fmt, hashlib.sha256(data).hexdigest(), len(data)


def validate(spec: dict, base: Path, max_still_kb: int = 2500) -> dict:
    """Return a normalised copy of the spec with embedded assets resolved. Raises SpecError."""
    if spec.get("schema_version") != 1:
        raise SpecError("schema_version must be 1")
    for k in ("project", "title", "text"):
        if not str(spec.get(k, "")).strip():
            raise SpecError(f"{k} is required (real content, never placeholder text)")
    if LOREM.search(spec["text"]) or LOREM.search(json.dumps(spec.get("decisions", []), ensure_ascii=False)):
        raise SpecError("placeholder text detected: use the user's real text, colours and still")
    lang = spec.get("lang", "he")
    if lang not in UI:
        raise SpecError("lang must be 'he' or 'en'")
    banned = set(spec.get("banned", BANNED_DEFAULT))
    out = {**spec, "lang": lang, "banned": sorted(banned), "warnings": [], "assets": {"fonts": [], "still": None}}
    if spec.get("still"):
        uri, _, sha, size = embed(Path(spec["still"]), "image", base, max_still_kb)
        out["_still_uri"] = uri
        out["assets"]["still"] = {"file": Path(spec["still"]).name, "sha256": sha, "bytes": size}
    decs = spec.get("decisions") or []
    if not decs:
        raise SpecError("at least one decision is required")
    seen_dec = set()
    safe = spec.get("safe_zone") or {"top": 300, "bottom": 672, "left": 140, "right": 192, "canvas": [1080, 1920],
                                     "rail_bottom": 1450, "label": "house preset v1 (unverified pixels)"}
    out["safe_zone"] = safe
    for d in decs:
        did = d.get("id", "")
        if not DEC_RE.match(did) or did in seen_dec:
            raise SpecError(f"decision id invalid or duplicated: {did!r}")
        seen_dec.add(did)
        if d.get("kind") not in KINDS:
            raise SpecError(f"decision {did}: kind must be one of {sorted(KINDS)}")
        opts = d.get("options") or []
        if not 2 <= len(opts) <= 12:
            raise SpecError(f"decision {did}: {len(opts)} options; need 2-12 (8-12 is the sweet spot)")
        if len(opts) < 3:
            out["warnings"].append(f"{did}: only {len(opts)} options; a chat question may be faster unless the difference is visual")
        ids = set()
        for o in opts:
            oid = str(o.get("id", ""))
            if not ID_RE.match(oid) or oid == "none" or oid in ids:
                raise SpecError(f"decision {did}: option id invalid, reserved or duplicated: {oid!r}")
            ids.add(oid)
            if not str(o.get("label", "")).strip():
                raise SpecError(f"decision {did}/{oid}: label required")
            k = d["kind"]
            if k == "font":
                if not FAMILY_RE.match(str(o.get("family", ""))):
                    raise SpecError(f"{did}/{oid}: family must be a plain font name")
                if o.get("font_file"):
                    if not str(o.get("license", "")).strip():
                        raise SpecError(f"{did}/{oid}: an embedded font needs its licence text or notice in `license`")
                    uri, fmt, sha, size = embed(Path(o["font_file"]), "font", base, 3000)
                    o["_uri"], o["_fmt"] = uri, fmt
                    out["assets"]["fonts"].append({"option": f"{did}/{oid}", "file": Path(o["font_file"]).name, "sha256": sha,
                                                   "bytes": size, "license": str(o["license"])[:200]})
            elif k == "caption_anim":
                if o.get("anim") not in ANIMS:
                    raise SpecError(f"{did}/{oid}: anim must be one of {sorted(ANIMS)}")
                if o["anim"] in banned:
                    raise SpecError(f"{did}/{oid}: anim {o['anim']!r} is banned for this project (spec.banned)")
            elif k == "easing":
                bz = o.get("bezier")
                if not (isinstance(bz, list) and len(bz) == 4 and all(isinstance(x, (int, float)) for x in bz) and 0 <= bz[0] <= 1 and 0 <= bz[2] <= 1):
                    raise SpecError(f"{did}/{oid}: bezier must be [x1,y1,x2,y2] with x in 0..1")
                if not 100 <= int(o.get("duration_ms", 600)) <= 4000:
                    raise SpecError(f"{did}/{oid}: duration_ms must be 100-4000")
            elif k == "palette":
                c = o.get("colors") or {}
                for key in ("bg", "text", "accent"):
                    if not HEX.match(str(c.get(key, ""))):
                        raise SpecError(f"{did}/{oid}: colors.{key} must be a #hex colour")
            elif k == "transition":
                if o.get("trans") not in TRANS:
                    raise SpecError(f"{did}/{oid}: trans must be one of {sorted(TRANS)}")
                if o["trans"] in banned:
                    raise SpecError(f"{did}/{oid}: transition {o['trans']!r} is banned for this project (spec.banned)")
            elif k == "layout":
                y = o.get("caption_y_pct")
                if not isinstance(y, (int, float)) or not 0 <= y <= 100:
                    raise SpecError(f"{did}/{oid}: caption_y_pct must be 0-100")
            elif k == "text":
                if not str(o.get("text", "")).strip():
                    raise SpecError(f"{did}/{oid}: text required")
    return out


def css_family(name: str, fallback: str = "sans-serif") -> str:
    fb = fallback if fallback in ("sans-serif", "serif", "monospace", "cursive") else "sans-serif"
    return f'"{name}", {fb}'


def card_visual(d: dict, o: dict, spec: dict, ui: dict) -> str:
    """HTML for one option. Only <span>/<svg>/<code> are used: this sits inside a <button>."""
    k, text = d["kind"], esc(spec["text"])
    still = spec.get("_still_uri")
    bg = (f"background-image:url({still});background-size:cover;background-position:center;" if still
          else "background:linear-gradient(160deg,#20232b,#0c0d11);")

    def sample(anim: str = "none", cls: str = "sample cap", style: str = "", body: str | None = None, fixed: bool = False) -> str:
        st = f' style="{style}"' if style else ""
        fx = ' data-fixed="1"' if fixed else ""
        return f'<span class="{cls}" dir="auto" data-anim="{anim}"{fx}{st}>{text if body is None else body}</span>'

    def phone(inner: str, stage_style: str = "", stage_cls: str = "stage") -> str:
        return f'<span class="phone"><span class="{stage_cls}" style="{stage_style}">{inner}</span></span>'

    if k == "font":
        fam = css_family(o["family"], o.get("fallback", "sans-serif"))
        wt = int(o.get("weight", 700))
        kwd = pick_keyword(spec)
        found = "".join(lookalike_letters(kwd))
        alike = " · ".join(f"{a} {b}" for a, b in LOOKALIKES)
        emb, cls = (ui["emb"], "ok") if o.get("_uri") else (ui["sysf"], "warn")
        fs = f"font-family:{fam};font-weight:{wt}"
        kw_html = f'<span class="kw" dir="rtl" style="{fs}">{esc(kwd)}</span>' if kwd else ""
        found_html = f'<span class="chip">{esc(found)}</span>' if found else ""
        return (phone(sample(style=fs), bg) + f'<span class="spec" aria-label="{esc(ui["spec"])}">{kw_html}'
                f'<span class="alike" dir="rtl" style="{fs}">{alike}</span>'
                f'<span class="chips"><span class="chip {cls}">{esc(emb)}</span>{found_html}</span></span>')
    if k == "caption_anim":
        return phone(sample(anim=o["anim"]), bg)
    if k == "easing":
        bz = o["bezier"]
        dur = int(o.get("duration_ms", 600))
        css = f"cubic-bezier({bz[0]},{bz[1]},{bz[2]},{bz[3]})"
        path = f"M0,100 C{bz[0] * 100:.1f},{100 - bz[1] * 100:.1f} {bz[2] * 100:.1f},{100 - bz[3] * 100:.1f} 100,0"
        mover = f'<span class="mover" style="--ease:{css};--d:{dur}ms">{sample()}</span>'
        return (phone(mover, bg) + f'<span class="spec"><svg class="curve" viewBox="-4 -30 108 160" aria-hidden="true">'
                f'<path d="M0,100 L100,0" class="diag"/><path d="{path}"/></svg><code>{css} · {dur} ms</code></span>')
    if k == "palette":
        c = o["colors"]
        cr, ca = contrast(c["text"], c["bg"]), contrast(c["accent"], c["bg"])
        low = f' <b class="warn">{esc(ui["low"])}</b>' if cr < 3 else ""
        sw = "".join(f'<i style="background:{c[x]}" title="{x}"></i>' for x in ("bg", "text", "accent"))
        words = spec["text"].split()
        body = f'<span style="color:{c["accent"]}">{esc(words[0])}</span> {esc(" ".join(words[1:]))}' if words else ""
        return (phone(sample(style=f"color:{c['text']};text-shadow:none", body=body), f"background:{c['bg']};color:{c['text']}") +
                f'<span class="spec"><span class="sw">{sw}</span><span class="chips"><span class="chip">{esc(ui["contrast"])} {cr}:1{low}</span>'
                f'<span class="chip">accent {ca}:1</span></span></span>')
    if k == "transition":
        t = o["trans"]
        b = o.get("color_b", "#ffcc00")
        b = b if HEX.match(str(b)) else "#ffcc00"
        inner = f'<span class="ta" style="{bg}"><span>A</span></span><span class="tb" style="background:{b}"><span>B</span></span>'
        return phone(inner, "", f"stage tr tr-{t}")
    if k == "layout":
        y = float(o["caption_y_pct"])
        sz = spec["safe_zone"]
        W, H = sz.get("canvas", [1080, 1920])
        rail = sz.get("rail_bottom", 1450) / H * 100
        over = (y + 4) > rail
        zone = (f"top:{sz['top'] / H * 100:.2f}%;bottom:{sz['bottom'] / H * 100:.2f}%;"
                f"left:{sz['left'] / W * 100:.2f}%;right:{sz['right'] / W * 100:.2f}%")
        warn = f'<span class="chip warn">{esc(ui["warn_rail"])}</span>' if over else ""
        inner = (f'<span class="safe" style="{zone}"></span><span class="rail" style="top:{rail:.2f}%"></span>'
                 + sample(cls="sample cap lay", style=f"top:{y}%"))
        return phone(inner, bg) + f'<span class="spec"><span class="chips"><span class="chip">y {y:g}% ≈ {y / 100 * H:.0f} px</span>{warn}</span></span>'
    return phone(sample(cls="sample cap hookt", body=esc(o["text"]), fixed=True), bg)


def ltr_runs(text: str) -> str:
    """Isolate Latin/number runs (keys such as 1-9, q, w) so mixed Hebrew + keys do not scramble."""
    out, pos = [], 0
    for m in re.finditer(r"[A-Za-z0-9](?:[A-Za-z0-9, \-]*[A-Za-z0-9])?", text):
        out.append(esc(text[pos:m.start()]))
        out.append(f'<bdi dir="ltr">{esc(m.group(0))}</bdi>')
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def render_body(spec: dict) -> str:
    ui = UI[spec["lang"]]
    tabs, panels = [], []
    for n, d in enumerate(spec["decisions"]):
        did = d["id"]
        active = n == 0
        tabs.append(f'<button type="button" role="tab" id="tab-{did}" aria-controls="panel-{did}" aria-selected="{str(active).lower()}" '
                    f'tabindex="{0 if active else -1}" data-dec="{did}">{esc(d.get("title", did))} <span class="badge" id="badge-{did}" aria-hidden="true"></span></button>')
        cards = []
        for i, o in enumerate(d["options"]):
            key = KEYS[i] if i < len(KEYS) else ""
            cards.append(
                f'<div class="wrap"><button type="button" class="pick" role="radio" aria-checked="false" data-dec="{did}" data-opt="{esc(o["id"])}" '
                f'aria-label="{esc(d.get("title", did))} {i + 1}: {esc(o["label"])}">'
                f'<span class="hd"><kbd>{key}</kbd> <b>{esc(o["label"])}</b></span>{card_visual(d, o, spec, ui)}</button>'
                f'<button type="button" class="rej" aria-pressed="false" data-dec="{did}" data-opt="{esc(o["id"])}">✕ {esc(ui["reject"])}</button></div>')
        none = (f'<div class="wrap none"><button type="button" class="pick" role="radio" aria-checked="false" data-dec="{did}" data-opt="none" '
                f'aria-label="{esc(ui["none"])}"><span class="hd"><kbd>n</kbd> <b>{esc(ui["none"])}</b></span></button></div>')
        panels.append(
            f'<section role="tabpanel" id="panel-{did}" aria-labelledby="tab-{did}" data-dec="{did}"{"" if active else " hidden"}>'
            f'<div class="grid" role="radiogroup" aria-label="{esc(d.get("title", did))}">{"".join(cards)}{none}</div>'
            f'<label class="cm">{esc(ui["comment"])}<textarea data-dec="{did}" rows="2" maxlength="400"></textarea></label></section>')
    return (f'<header><h1>{esc(spec["title"])}</h1><p class="mut"><bdi dir="ltr">{esc(spec["project"])}</bdi> · {ltr_runs(ui["hint"])}</p>'
            f'<div class="bar"><label>{esc(ui["sample"])}<input id="sample-text" type="text" maxlength="120" value="{esc(spec["text"])}"></label>'
            f'<button type="button" id="pause" aria-pressed="false">{esc(ui["pause"])}</button>'
            f'<button type="button" id="clear">{esc(ui["clear"])}</button></div></header>'
            f'<div role="tablist" aria-label="{esc(spec["title"])}">{"".join(tabs)}</div>{"".join(panels)}'
            f'<aside id="summary" aria-live="polite"><h2>{esc(ui["summary"])}</h2><ul></ul></aside>'
            f'<footer><button type="button" id="export" class="primary">{esc(ui["export"])}</button> '
            f'<button type="button" id="copy">{esc(ui["copy"])}</button><p id="status" role="status"></p>'
            f'<textarea id="json-out" readonly rows="8" aria-label="choices.json"></textarea></footer>')


def font_faces(spec: dict) -> str:
    out = []
    for d in spec["decisions"]:
        if d["kind"] != "font":
            continue
        for o in d["options"]:
            if o.get("_uri"):
                out.append(f'@font-face{{font-family:"{o["family"]}";src:url({o["_uri"]}) format("{o["_fmt"]}");font-weight:{int(o.get("weight", 700))};font-display:block}}')
    return "\n".join(out)


def remote_hits(page: str) -> list[str]:
    pats = [r'(?i)\b(?:src|href|action|poster|srcset|data)\s*=\s*["\']?\s*(?:https?:)?//', r'(?i)url\(\s*["\']?\s*(?:https?:)?//',
            r"(?i)@import", r"(?i)<link\b", r"(?i)<iframe\b", r"(?i)<embed\b", r"(?i)<object\b", r"(?i)\bfetch\s*\(",
            r"(?i)XMLHttpRequest", r"(?i)\bWebSocket\b", r"(?i)sendBeacon", r"(?i)<script[^>]+\bsrc="]
    return [p for p in pats if re.search(p, page)]


def build(spec_path: Path, out_dir: Path | None = None, built_utc: str | None = None) -> dict:
    try:
        raw = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SpecError(f"cannot read spec: {exc}") from exc
    spec = validate(raw, spec_path.parent)
    ui = UI[spec["lang"]]
    public = json.loads(json.dumps({k: v for k, v in spec.items() if not k.startswith("_")}))
    for d in public["decisions"]:
        for o in d["options"]:
            for k in [k for k in o if k.startswith("_")]:
                del o[k]
    board_id = hashlib.sha256(canon({"spec": public, "ver": 1})).hexdigest()[:16]
    built = built_utc or os.environ.get("AVC_BUILT_UTC") or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data = {"schema_version": 1, "board_id": board_id, "project": spec["project"], "built_utc": built, "dir": ui["dir"],
            "text": spec["text"], "ui": {k: ui[k] for k in ("saved", "need", "needc", "pending", "none")},
            "decisions": [{"id": d["id"], "title": d.get("title", d["id"]), "kind": d["kind"],
                           "options": [{"id": o["id"], "label": o["label"]} for o in d["options"]]} for d in spec["decisions"]],
            "assets": spec["assets"]}
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")
    page = (TEMPLATE.replace("@@LANG@@", spec["lang"]).replace("@@DIR@@", ui["dir"]).replace("@@TITLE@@", esc(spec["title"]))
            .replace("@@FONTS@@", font_faces(spec)).replace("@@BODY@@", render_body(spec)).replace("@@DATA@@", data_json))
    hits = remote_hits(page)
    if hits:
        raise SpecError(f"internal guard: page would reference remote resources: {hits}")
    out_dir = out_dir or spec_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path, man_path = out_dir / "choice-board.html", out_dir / "board_manifest.json"
    html_path.write_bytes(page.encode("utf-8"))
    manifest = {"schema_version": 1, "tool": "make_board", "tool_version": VERSION, "board_id": board_id, "project": spec["project"],
                "built_utc": built, "html_file": html_path.name, "html_sha256": hashlib.sha256(page.encode("utf-8")).hexdigest(),
                "html_bytes": len(page.encode("utf-8")),
                "decisions": {d["id"]: {"kind": d["kind"], "title": d.get("title", d["id"]),
                                        "options": {o["id"]: o["label"] for o in d["options"]}} for d in spec["decisions"]},
                "assets": spec["assets"], "warnings": spec["warnings"]}
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"html": str(html_path), "manifest": str(man_path), "board_id": board_id, "bytes": manifest["html_bytes"],
            "decisions": len(spec["decisions"]), "options": sum(len(d["options"]) for d in spec["decisions"]), "warnings": spec["warnings"]}


def verify(manifest_path: Path, choices_path: Path) -> tuple[int, dict]:
    try:
        man = json.loads(manifest_path.read_text(encoding="utf-8"))
        ch = json.loads(choices_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return 2, {"status": "not_run", "reason": f"{type(exc).__name__}: {exc}"}
    errs, lines = [], []
    if ch.get("schema_version") != 1:
        errs.append("schema_version must be 1")
    if ch.get("board_id") != man.get("board_id"):
        errs.append(f"board_id mismatch: choices {ch.get('board_id')!r} vs manifest {man.get('board_id')!r} (wrong or rebuilt board)")
    got = ch.get("decisions") or {}
    for did in sorted(set(man["decisions"]) - set(got)):
        errs.append(f"decision {did!r} has no answer")
    for did in sorted(set(got) - set(man["decisions"])):
        errs.append(f"unknown decision {did!r}")
    for did, spec in man["decisions"].items():
        a = got.get(did)
        if not isinstance(a, dict):
            continue
        comment = str(a.get("comment", "")).strip()
        if a.get("none"):
            if not comment:
                errs.append(f"{did}: 'none' needs a comment")
            lines.append(f"{did} = NONE of these: {comment}")
            continue
        c = a.get("choice")
        if c not in spec["options"]:
            errs.append(f"{did}: choice {c!r} is not an option of this board")
            continue
        rej = [r for r in a.get("rejected", []) if r != c]
        if c in a.get("rejected", []):
            errs.append(f"{did}: choice {c!r} is also marked rejected")
        lines.append(f"{did} = {spec['options'][c]} (option {c})" + (f"; rejected: {', '.join(rej)}" if rej else "") + (f"; note: {comment}" if comment else ""))
    mf = {f["option"]: f["sha256"] for f in man.get("assets", {}).get("fonts", [])}
    cf = {f["option"]: f["sha256"] for f in (ch.get("assets") or {}).get("fonts", [])}
    for k, v in cf.items():
        if mf.get(k) != v:
            errs.append(f"asset hash mismatch for {k}")
    res = {"status": "invalid" if errs else "ok", "board_id": man.get("board_id"), "errors": errs, "decision_lines": lines,
           "sample_text": ch.get("sample_text"), "session_elapsed_ms": ch.get("session_elapsed_ms")}
    return (1 if errs else 0), res


TEMPLATE = r"""<!doctype html>
<html lang="@@LANG@@">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@TITLE@@</title>
<style>
@@FONTS@@
:root{--bg:#f5f5f3;--fg:#17171b;--mut:#60606b;--card:#fff;--line:#d8d8e0;--sel:#2457d6;--warn:#b3261e;--ok:#17744a;--ph:#000;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--bg:#121216;--fg:#ececf1;--mut:#a3a3b0;--card:#1b1b22;--line:#34343e;--sel:#86a8ff;--warn:#ff8f85;--ok:#6fd7a1}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,"Segoe UI",Arial,sans-serif}
#app{max-width:1180px;margin:0 auto;padding:16px}
h1{font-size:1.4rem;margin:.2em 0}h2{font-size:1rem;margin:.2em 0}.mut{color:var(--mut);margin:.2em 0}
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:end;margin:10px 0}
.bar label{display:flex;flex-direction:column;gap:2px;flex:1 1 280px;font-size:.85rem;color:var(--mut)}
input[type=text],textarea{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px;width:100%}
button{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 12px;cursor:pointer}
button:focus-visible,.pick:focus-visible{outline:3px solid var(--sel);outline-offset:2px}
button.primary{background:var(--sel);color:#fff;border-color:var(--sel);font-weight:700}
[role=tablist]{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0;border-bottom:1px solid var(--line)}
[role=tab]{border-radius:10px 10px 0 0;border-bottom:0}[role=tab][aria-selected=true]{border-color:var(--sel);font-weight:700}
.badge{color:var(--ok)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(176px,1fr));gap:12px}
.wrap{display:flex;flex-direction:column;gap:4px}
.pick{display:block;width:100%;text-align:start;padding:8px;border:2px solid var(--line);border-radius:14px;background:var(--card)}
.pick[aria-checked=true]{border-color:var(--sel);outline:3px solid var(--sel);outline-offset:0}
.wrap.rejected .pick{opacity:.45}
.rej{font-size:.8rem;padding:3px 8px;color:var(--mut)}.rej[aria-pressed=true]{color:var(--warn);border-color:var(--warn)}
.hd{display:flex;gap:6px;align-items:center;margin-bottom:6px;font-size:.9rem}
kbd{font:inherit;font-size:.75rem;border:1px solid var(--line);border-radius:5px;padding:0 5px;color:var(--mut)}
.none .pick{min-height:80px;display:flex;align-items:center;justify-content:center;border-style:dashed}
.phone,.sample,.spec,.kw,.alike{display:block}
.phone{direction:ltr;position:relative;width:100%;max-width:168px;aspect-ratio:9/16;margin:0 auto;border:3px solid var(--ph);border-radius:16px;overflow:hidden;container-type:inline-size;background:#000}
.stage{position:absolute;inset:0;display:grid;place-items:center;overflow:hidden}
.sample{max-width:92%;text-align:center;color:#fff;font:800 12px/1.2 system-ui,Arial,sans-serif;font-size:max(12px,9.4cqw);unicode-bidi:plaintext;overflow-wrap:anywhere}
.sample.cap{text-shadow:0 0 3px #000,0 1px 2px #000,0 0 6px rgba(0,0,0,.7)}
.sample.lay{position:absolute;inset-inline:6%;max-width:none;transform:translateY(-50%)}
.hookt{font-size:max(10px,7cqw)}
.spec{margin-top:6px;text-align:center;font-size:.8rem}
.kw{font-size:1.8rem;line-height:1.1}.alike{font-size:1.3rem;letter-spacing:.08em}
.chips{display:flex;flex-wrap:wrap;gap:4px;justify-content:center;margin-top:4px}
.chip{font-size:.72rem;border:1px solid var(--line);border-radius:999px;padding:0 7px}.chip.ok{color:var(--ok)}.chip.warn,.warn{color:var(--warn)}
.sw{display:flex;justify-content:center;gap:4px}.sw i{width:22px;height:22px;border-radius:50%;border:1px solid var(--line)}
.curve{width:84px;height:auto;display:block;margin:0 auto}.curve path{fill:none;stroke:var(--sel);stroke-width:4}.curve .diag{stroke:var(--line);stroke-width:2;stroke-dasharray:4 4}
.safe{position:absolute;border:1.5px dashed #6ee7a8}.rail{position:absolute;inset-inline:0;border-top:1.5px dashed #ff6b5e}
.cm{display:block;margin:12px 0;font-size:.85rem;color:var(--mut)}
#summary{margin:14px 0;padding:10px 14px;border:1px solid var(--line);border-radius:12px;background:var(--card)}#summary ul{margin:.3em 0;padding-inline-start:1.2em}
footer{margin:12px 0}#status{min-height:1.4em}
.mover{display:grid;place-items:center;width:100%;animation:mv calc(var(--d) / .6) infinite}
@keyframes mv{0%{transform:translateY(46%);opacity:.0}6%{opacity:1}60%{transform:translateY(0);animation-timing-function:linear}100%{transform:translateY(0)}}
.mover{animation-timing-function:var(--ease)}
.tr .ta,.tr .tb{position:absolute;inset:0;display:grid;place-items:center;background-size:cover;color:#fff;font:800 2rem system-ui,sans-serif}
.tr .tb{color:#111;animation:var(--tn,t-wipe) 2.6s infinite}
.tr-wipe{--tn:t-wipe}.tr-push{--tn:t-push}.tr-iris{--tn:t-iris}.tr-slide_up{--tn:t-slide}.tr-crossfade{--tn:t-xfade}
@keyframes t-wipe{0%,10%{clip-path:inset(0 0 0 100%)}50%,85%{clip-path:inset(0)}100%{clip-path:inset(0 0 0 100%)}}
@keyframes t-push{0%,10%{transform:translateX(100%)}50%,85%{transform:translateX(0)}100%{transform:translateX(100%)}}
@keyframes t-iris{0%,10%{clip-path:circle(0% at 50% 50%)}50%,85%{clip-path:circle(75% at 50% 50%)}100%{clip-path:circle(0% at 50% 50%)}}
@keyframes t-slide{0%,10%{transform:translateY(100%)}50%,85%{transform:translateY(0)}100%{transform:translateY(100%)}}
@keyframes t-xfade{0%,10%{opacity:0}50%,85%{opacity:1}100%{opacity:0}}
[data-anim=rise]{animation:a-rise 2.6s infinite}[data-anim=blur_in]{animation:a-blur 2.6s infinite}[data-anim=scale_in]{animation:a-scale 2.6s infinite}
[data-anim=slide_up]{animation:a-slide 2.6s infinite}[data-anim=mask_wipe]{animation:a-mask 2.6s infinite}[data-anim=bounce]{animation:a-bounce 2.6s infinite}
[data-anim=word_rise] .w{display:inline-block;animation:a-rise 2.6s infinite;animation-delay:calc(var(--i) * 90ms)}
[data-anim=karaoke] .w{display:inline-block;animation:a-kara 2.6s infinite;animation-delay:calc(var(--i) * 260ms)}
@keyframes a-rise{0%{opacity:0;transform:translateY(40%)}22%,78%{opacity:1;transform:none}100%{opacity:0;transform:translateY(40%)}}
@keyframes a-blur{0%{opacity:0;filter:blur(10px)}22%,78%{opacity:1;filter:none}100%{opacity:0;filter:blur(10px)}}
@keyframes a-scale{0%{opacity:0;transform:scale(.86)}22%,78%{opacity:1;transform:none}100%{opacity:0;transform:scale(.86)}}
@keyframes a-slide{0%{clip-path:inset(100% 0 0 0);transform:translateY(30%)}22%,78%{clip-path:inset(0);transform:none}100%{clip-path:inset(100% 0 0 0);transform:translateY(30%)}}
@keyframes a-mask{0%{clip-path:var(--wf,inset(0 100% 0 0))}24%,76%{clip-path:inset(0)}100%{clip-path:var(--wf,inset(0 100% 0 0))}}
[dir=rtl]{--wf:inset(0 0 0 100%)}
@keyframes a-bounce{0%{opacity:0;transform:translateY(60%)}15%{opacity:1;transform:translateY(-14%)}25%{transform:translateY(6%)}32%,78%{opacity:1;transform:none}100%{opacity:0}}
@keyframes a-kara{0%,10%{color:#fff}30%,70%{color:#ffd23f}90%,100%{color:#fff}}
body.paused *,body.paused *::before{animation:none!important}
body.paused .mover{transform:none}body.paused .tr .tb{clip-path:none;transform:none;opacity:1}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.tr .tb{clip-path:none;transform:none;opacity:1}}
@media (max-width:520px){.grid{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<div id="app" dir="@@DIR@@">
@@BODY@@
</div>
<script type="application/json" id="board-data">@@DATA@@</script>
<script>
(function () {
  'use strict';
  var B = JSON.parse(document.getElementById('board-data').textContent);
  var KEYS = '1234567890qw';
  var WORD = {word_rise: 1, karaoke: 1};
  var started = Date.now();
  var A = {};
  B.decisions.forEach(function (d) { A[d.id] = {choice: null, none: false, comment: '', rejected: []}; });
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var text = B.text;

  function fill(el) {
    if (el.getAttribute('data-fixed')) return;
    var mode = el.getAttribute('data-anim');
    el.textContent = '';
    if (WORD[mode]) {
      text.split(/\s+/).filter(Boolean).forEach(function (w, i) {
        var s = document.createElement('span'); s.className = 'w'; s.style.setProperty('--i', i);
        s.textContent = w; el.appendChild(s); el.appendChild(document.createTextNode(' '));
      });
    } else { el.textContent = text; }
    if (mode && mode !== 'none') { el.style.animation = 'none'; void el.offsetWidth; el.style.animation = ''; }
  }
  function refresh() { $$('.sample').forEach(fill); }
  function opt(d, id) { for (var i = 0; i < d.options.length; i++) if (d.options[i].id === id) return d.options[i]; return null; }
  function answered(d) { var a = A[d.id]; return a.none || a.choice !== null; }

  function paint() {
    var ul = $('#summary ul'); ul.textContent = '';
    B.decisions.forEach(function (d) {
      var a = A[d.id], li = document.createElement('li'), o = a.choice ? opt(d, a.choice) : null;
      li.textContent = d.title + ': ' + (a.none ? B.ui.none + (a.comment ? ' – ' + a.comment : '') : (o ? o.label : B.ui.pending));
      ul.appendChild(li);
      $('#badge-' + d.id).textContent = answered(d) ? '✓' : '';
      $$('.pick[data-dec="' + d.id + '"]').forEach(function (b) {
        var on = b.getAttribute('data-opt') === 'none' ? a.none : (!a.none && a.choice === b.getAttribute('data-opt'));
        b.setAttribute('aria-checked', on ? 'true' : 'false');
      });
      $$('.rej[data-dec="' + d.id + '"]').forEach(function (b) {
        var on = a.rejected.indexOf(b.getAttribute('data-opt')) >= 0;
        b.setAttribute('aria-pressed', on ? 'true' : 'false'); b.parentNode.classList.toggle('rejected', on);
      });
    });
  }
  function choose(did, oid) {
    var a = A[did];
    if (oid === 'none') { a.none = true; a.choice = null; }
    else { a.none = false; a.choice = oid; a.rejected = a.rejected.filter(function (r) { return r !== oid; }); }
    paint();
  }
  function reject(did, oid) {
    var a = A[did], i = a.rejected.indexOf(oid);
    if (i >= 0) a.rejected.splice(i, 1); else { a.rejected.push(oid); if (a.choice === oid) a.choice = null; }
    paint();
  }
  function activeDec() { var t = $('[role=tab][aria-selected=true]'); return t.getAttribute('data-dec'); }
  function tab(did, focus) {
    $$('[role=tab]').forEach(function (t) {
      var on = t.getAttribute('data-dec') === did;
      t.setAttribute('aria-selected', on ? 'true' : 'false'); t.tabIndex = on ? 0 : -1; if (on && focus) t.focus();
    });
    $$('[role=tabpanel]').forEach(function (p) { p.hidden = p.getAttribute('data-dec') !== did; });
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('button') : null; if (!b) return;
    if (b.classList.contains('pick')) choose(b.getAttribute('data-dec'), b.getAttribute('data-opt'));
    else if (b.classList.contains('rej')) reject(b.getAttribute('data-dec'), b.getAttribute('data-opt'));
    else if (b.getAttribute('role') === 'tab') tab(b.getAttribute('data-dec'), false);
  });
  document.addEventListener('input', function (e) {
    var t = e.target;
    if (t.id === 'sample-text') { text = t.value || B.text; refresh(); }
    else if (t.tagName === 'TEXTAREA' && t.getAttribute('data-dec')) { A[t.getAttribute('data-dec')].comment = t.value; paint(); }
  });
  document.addEventListener('keydown', function (e) {
    var t = e.target, tag = t && t.tagName;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (t && t.isContentEditable)) return;
    if (t && t.getAttribute && t.getAttribute('role') === 'tab') {
      var tabs = $$('[role=tab]'), i = tabs.indexOf(t), rtl = B.dir === 'rtl', n = -1;
      if (e.key === 'ArrowRight') n = rtl ? i - 1 : i + 1; else if (e.key === 'ArrowLeft') n = rtl ? i + 1 : i - 1;
      else if (e.key === 'Home') n = 0; else if (e.key === 'End') n = tabs.length - 1;
      if (n >= 0 || e.key === 'Home') { n = (n + tabs.length) % tabs.length; tab(tabs[n].getAttribute('data-dec'), true); e.preventDefault(); return; }
    }
    var k = e.key.toLowerCase(), did = activeDec(), d = B.decisions.filter(function (x) { return x.id === did; })[0];
    if (k === 'n') { choose(did, 'none'); e.preventDefault(); return; }
    var idx = KEYS.indexOf(k);
    if (idx >= 0 && idx < d.options.length && k.length === 1) { choose(did, d.options[idx].id); e.preventDefault(); }
  });
  $('#pause').addEventListener('click', function () {
    var on = document.body.classList.toggle('paused'); this.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
  $('#clear').addEventListener('click', function () {
    B.decisions.forEach(function (d) { A[d.id] = {choice: null, none: false, comment: '', rejected: []}; });
    $$('textarea[data-dec]').forEach(function (t) { t.value = ''; }); $('#json-out').value = ''; $('#status').textContent = ''; paint();
  });
  function build() {
    for (var i = 0; i < B.decisions.length; i++) {
      var d = B.decisions[i], a = A[d.id];
      if (!answered(d)) return {error: B.ui.need + ': ' + d.title, dec: d.id};
      if (a.none && !a.comment.trim()) return {error: B.ui.needc + ': ' + d.title, dec: d.id};
    }
    var out = {};
    B.decisions.forEach(function (d) {
      var a = A[d.id]; out[d.id] = {choice: a.none ? null : a.choice, none: a.none, comment: a.comment.trim(), rejected: a.rejected.slice()};
    });
    return {json: {schema_version: 1, board_id: B.board_id, project: B.project, exported_utc: new Date().toISOString(),
                   session_elapsed_ms: Date.now() - started, sample_text: text, decisions: out, assets: B.assets}};
  }
  $('#export').addEventListener('click', function () {
    var r = build(), st = $('#status');
    if (r.error) { st.textContent = r.error; st.className = 'warn'; tab(r.dec, true); return; }
    var s = JSON.stringify(r.json, null, 2); $('#json-out').value = s; st.className = ''; st.textContent = B.ui.saved;
    try {
      var u = URL.createObjectURL(new Blob([s], {type: 'application/json'})), a = document.createElement('a');
      a.href = u; a.download = 'choices.json'; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(u); }, 2000);
    } catch (err) { /* downloads can be blocked in sandboxes: the text box below is the fallback */ }
  });
  $('#copy').addEventListener('click', function () {
    var o = $('#json-out'); if (!o.value) { $('#export').click(); }
    o.select(); try { if (navigator.clipboard) navigator.clipboard.writeText(o.value); else document.execCommand('copy'); } catch (err) { /* manual copy */ }
  });
  window.__board = {state: A, build: build};
  refresh(); paint();
})();
</script>
</body>
</html>
"""


def _self_check() -> int:
    test = Path(__file__).with_name("test_make_board.py")
    return subprocess.call([sys.executable, "-X", "utf8", str(test)])


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return _self_check()
    if len(argv) >= 2 and argv[0] == "build":
        out, built, i = None, None, 2
        while i < len(argv):
            if argv[i] == "--out":
                out = Path(argv[i + 1]); i += 2
            elif argv[i] == "--built-utc":
                built = argv[i + 1]; i += 2
            else:
                print("unknown option", argv[i]); return 2
        try:
            res = build(Path(argv[1]), out, built)
        except SpecError as exc:
            print(json.dumps({"status": "invalid_spec", "message": str(exc)}, ensure_ascii=False))
            return 2
        print(json.dumps({"status": "ok", **res}, ensure_ascii=False, indent=2))
        return 0
    if len(argv) >= 3 and argv[0] == "verify":
        code, res = verify(Path(argv[1]), Path(argv[2]))
        if "--json" in argv:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"verify: {res['status']}")
            for e in res.get("errors", []):
                print("  error:", e)
            for ln in res.get("decision_lines", []):
                print("  " + ln)
            if res.get("status") == "ok":
                print("  next: apply these as ledger rows (said = the pick on the board) and update DESIGN.md/PROMPT.md before code")
        return code
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

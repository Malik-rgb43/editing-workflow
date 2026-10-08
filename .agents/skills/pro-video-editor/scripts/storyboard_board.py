#!/usr/bin/env python3
"""storyboard_board - the moodboard + storyboard page: the look of the video and a key frame of EVERY beat (A-roll, B-roll, graphics),
shown to the user BEFORE any composition code, approved or noted per frame with one button; the agent gets the answer.

Usage:
  python storyboard_board.py check SPEC                                   validate storyboard.json, print a summary (exit 0 ok, 2 refused)
  python storyboard_board.py grab SPEC --video SRC [--width 540]          fill `img` of every A-roll beat that has none with the REAL frame
                                                                          of the source at `src_t` (default: the middle of the beat), via
                                                                          ffmpeg; writes <spec dir>/frames/<id>.jpg and updates the spec
  python storyboard_board.py build SPEC --out DIR                         static page (DIR/storyboard.html) for hosts without background
                                                                          commands: its buttons save storyboard_review.json to attach
  python storyboard_board.py serve SPEC --out DIR [--port 0] [--timeout 3600] [--open]
        serves the page on 127.0.0.1 and waits. "מאשר את הבורד ✓" or "שלח הערות ✓" (a note per frame and/or a general note) POSTs to
        the server, which validates, writes DIR/storyboard_review.json + .md, prints the result and EXITS 0: an agent that started it as
        a background command is notified, the user pastes nothing. No answer within --timeout exits 3.
  python storyboard_board.py --self-check                                 runs scripts/test_storyboard_board.py

storyboard.json (schema avc.storyboard/1):
  {"title", "project", "lang": "he|en", "aspect": "9:16|16:9|1:1|4:5", "story": "the one-sentence story",
   "mood": {"feel": "...", "palette": ["#hex", ...2-8], "type": {"family": "...", "sample": "the real line"}, "signature": "the one device",
            "refs": [{"img": "path", "caption": "what to take from it"}]},
   "beats": [{"id": "b1", "t": 0.0, "end": 2.4, "roll": "A|B|G", "line": "the words under it", "shows": "what is seen",
              "img": "frames/b1.jpg", "source": "own|stock|generated|graphic|reference|sketch", "src_t": 12.4,
              "move": "push 1.00->1.04", "why": "the reason", "cost": "free | ~$0.08 (paid-spend-gate)",
              "shot": "wide|medium|close|detail|graphic|screen", "signature": true, "text_only": true, "hero": true}]}
  roll: A = the speaker's / own footage, B = cut-away footage or stills, G = a graphic or text beat.
  shot, signature, text_only, hero are optional (hero: a montage's longest-held shot; more than 4 is warned). Sameness warnings (check and serve print them; they never refuse): 3+ beats in a row
  with the same `shot`; one shot on more than half of the beats (when 4+ beats carry a shot); the same image on two beats;
  text-only graphic beats (`text_only`, or a G beat whose `shows` names text) on more than 40 % of the beats; two adjacent beats
  with the same roll, shot and subject words; the signature device (`signature: true`) on more than 2 beats, or on none.
  Honesty rules (refused, exit 2): an A-roll beat is the project's OWN footage with a real frame; a "reference" image (someone else's) is
  mood only and is labelled so on the page; a beat without an image is allowed only as `sketch` or a not-yet-made `generated` beat and
  is shown as a planned card. Images: jpg/png/webp, <= 2.5 MB each, embedded as data URIs (nothing leaves the machine).
Guards (serve): a per-run token, an Origin check, a 1 MB body cap, a Content-Security-Policy that allows no other request.
Stdlib only, Python 3.10+ (grab needs ffmpeg on PATH).
"""

from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCHEMA = "avc.storyboard/1"
ROLLS = {"A": "A-roll", "B": "B-roll", "G": "graphic"}
SOURCES = ("own", "stock", "generated", "graphic", "reference", "sketch")
ASPECTS = {"9:16": (9, 16), "16:9": (16, 9), "1:1": (1, 1), "4:5": (4, 5)}
IMG_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
MAX_IMG = int(2.5 * (1 << 20))
MAX_BEATS = 60
MAX_BODY = 1 << 20
MAX_TEXT = 2000
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,24}$")
PLACEHOLDER_RE = re.compile(r"(?i)lorem|ipsum|placeholder|todo|tbd|xxx")
SHOTS = ("wide", "medium", "close", "detail", "graphic", "screen")
TEXT_BEAT_RE = re.compile(r"(?i)\b(text|title|words?|caption|quote|headline|typography|lettering|type on)\b|כיתוב|טקסט|כותרת|מילים|ציטוט")
STOPWORDS = {"the", "and", "with", "from", "into", "over", "under", "for", "his", "her", "its", "their", "this", "that", "then", "of",
             "של", "עם", "על", "את", "זה", "הוא", "היא", "מול", "אל", "גם", "כל", "רק"}

UI = {
    "he": {"dir": "rtl", "eyebrow": "מודבורד + סטוריבורד", "mood": "המראה", "feel": "התחושה", "palette": "פלטה", "type": "טיפוגרפיה",
           "signature": "המכשיר החתימתי", "refs": "רפרנסים", "ref_badge": "רפרנס: לא שלנו, רק לתחושה", "story": "הסיפור במשפט",
           "board": "הפריימים המרכזיים", "rhythm": "קצב A-roll / B-roll לאורך הסרטון", "beats": "פריימים", "planned": "מתוכנן: עוד לא קיים",
           "shows": "רואים", "move": "תנועה", "why": "למה", "source": "מקור", "cost": "עלות", "note_ph": "הערה על הפריים הזה (לא חובה)",
           "general_ph": "הערה כללית על הסגנון או הסדר (לא חובה)", "send": "שלח הערות", "send_hint": "הסוכן מתקן את הבורד ומראה שוב",
           "approve": "מאשר את הבורד ✓", "approve_hint": "הסוכן מתחיל לבנות את הסרטון לפי הבורד", "next_q": "מה הלאה?",
           "has_notes": "יש הערות: שלח אותן או מחק אותן", "approve_q": "לאשר את הבורד בלי הערות? לחץ שוב לאישור.", "approve_again": "לחץ שוב לאישור ✓", "sending": "שולח לסוכן...",
           "sent": "ההערות נשלחו לסוכן. אפשר לסגור את הדף.", "approved": "הבורד אושר. הסוכן מתחיל לבנות, אפשר לסגור את הדף.",
           "fail": "השליחה לא הצליחה: ", "saved": "נשמר הקובץ storyboard_review.json: צרף אותו לשיחה עם הסוכן.",
           "font_note": "תצוגה בדפדפן: הפונט האמיתי נבדק במנוע", "src": {"own": "צילום שלנו", "stock": "סטוק (רישיון לכל קובץ)",
           "generated": "ג'נרציה (בתשלום, באישור)", "graphic": "גרפיקה", "reference": "רפרנס", "sketch": "סקיצה"},
           "roll": {"A": "A-roll", "B": "B-roll", "G": "גרפיקה"},
           "shot": {"wide": "רחב", "medium": "בינוני", "close": "קרוב", "detail": "פרט", "graphic": "גרפיקה", "screen": "מסך"}},
    "en": {"dir": "ltr", "eyebrow": "Moodboard + storyboard", "mood": "The look", "feel": "Feel", "palette": "Palette", "type": "Type",
           "signature": "Signature device", "refs": "References", "ref_badge": "reference: not ours, mood only", "story": "The story in one line",
           "board": "Key frames", "rhythm": "A-roll / B-roll rhythm across the video", "beats": "frames", "planned": "planned: not made yet",
           "shows": "Shows", "move": "Move", "why": "Why", "source": "Source", "cost": "Cost", "note_ph": "A note on this frame (optional)",
           "general_ph": "A general note on the style or the order (optional)", "send": "Send notes", "send_hint": "The agent fixes the board and shows it again",
           "approve": "Approve the board ✓", "approve_hint": "The agent starts building the video from this board", "next_q": "What next?",
           "has_notes": "There are notes: send or delete them", "approve_q": "Approve the board with no notes? Click again to confirm.", "approve_again": "Click again to approve ✓", "sending": "Sending to the agent...",
           "sent": "Notes sent to the agent. You can close this page.", "approved": "Board approved. The agent starts building; you can close this page.",
           "fail": "Sending failed: ", "saved": "storyboard_review.json saved: attach it to the chat with the agent.",
           "font_note": "browser preview: the real font is checked in the engine", "src": {"own": "our footage", "stock": "stock (licence per file)",
           "generated": "generated (paid, approved)", "graphic": "graphic", "reference": "reference", "sketch": "sketch"},
           "roll": {"A": "A-roll", "B": "B-roll", "G": "graphic"},
           "shot": {"wide": "wide", "medium": "medium", "close": "close", "detail": "detail", "graphic": "graphic", "screen": "screen"}},
}


def tc(t: float) -> str:
    cs = int(round(t * 100))
    m, rest = divmod(cs, 6000)
    return f"{m}:{rest // 100:02d}.{rest % 100:02d}"


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v >= 0


def _txt(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def validate(spec, base: Path) -> tuple[list[str], list[str]]:
    """Pure (reads only the image files' sizes): spec -> (errors, warnings). Errors refuse the board."""
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(spec, dict):
        return ["the spec must be a JSON object"], []
    for k in ("title", "project", "story"):
        if not _txt(spec.get(k)):
            errors.append(f"`{k}` is required")
    if spec.get("lang", "he") not in UI:
        errors.append("`lang` must be he or en")
    if spec.get("aspect", "9:16") not in ASPECTS:
        errors.append(f"`aspect` must be one of {sorted(ASPECTS)}")

    def img_ok(where: str, rel) -> None:
        if not isinstance(rel, str) or not rel.strip():
            errors.append(f"{where}: `img` is missing")
            return
        p = (base / rel).resolve()
        if p.suffix.lower() not in IMG_MIME:
            errors.append(f"{where}: {rel} is not jpg/png/webp")
        elif not p.is_file():
            errors.append(f"{where}: no image at {rel}")
        elif p.stat().st_size > MAX_IMG:
            errors.append(f"{where}: {rel} is larger than 2.5 MB (extract it at ~540 px wide)")

    mood = spec.get("mood")
    if not isinstance(mood, dict):
        errors.append("`mood` is required (feel, palette, type, signature, refs)")
    else:
        if not _txt(mood.get("feel")):
            errors.append("mood.feel is required")
        pal = mood.get("palette")
        if not isinstance(pal, list) or not 2 <= len(pal) <= 8 or not all(isinstance(c, str) and HEX_RE.match(c) for c in pal):
            errors.append("mood.palette must be 2-8 colours written #RRGGBB")
        ty = mood.get("type")
        if ty is not None and (not isinstance(ty, dict) or not _txt(ty.get("family")) or not _txt(ty.get("sample"))):
            errors.append("mood.type must have `family` and `sample` (the real line)")
        if not _txt(mood.get("signature")):
            warnings.append("mood.signature is empty: name the ONE device that belongs to this video")
        refs = mood.get("refs", [])
        if not isinstance(refs, list) or len(refs) > 12:
            errors.append("mood.refs must be a list of at most 12")
        else:
            for i, r in enumerate(refs, 1):
                if not isinstance(r, dict):
                    errors.append(f"mood.refs[{i}] must be an object")
                    continue
                img_ok(f"mood.refs[{i}]", r.get("img"))
                if not _txt(r.get("caption")):
                    errors.append(f"mood.refs[{i}]: `caption` (what to take from it) is required")

    beats = spec.get("beats")
    if not isinstance(beats, list) or not 3 <= len(beats) <= MAX_BEATS:
        errors.append(f"`beats` must hold 3-{MAX_BEATS} beats (a key frame for every beat of the video)")
        beats = []
    seen, prev_t = set(), -1.0
    for i, b in enumerate(beats, 1):
        w = f"beat {i}"
        if not isinstance(b, dict):
            errors.append(f"{w}: must be an object")
            continue
        bid = b.get("id")
        if not isinstance(bid, str) or not ID_RE.match(bid) or bid in seen:
            errors.append(f"{w}: `id` must be unique, letters/digits/_/- (got {bid!r})")
        else:
            seen.add(bid)
            w = f"beat {bid}"
        t, end = b.get("t"), b.get("end")
        if not _num(t) or not _num(end) or end <= t:
            errors.append(f"{w}: needs times `t` < `end` in seconds")
        elif t < prev_t:
            errors.append(f"{w}: beats must be in time order")
        else:
            prev_t = t
            if b.get("roll") == "B" and end - t > 6:
                warnings.append(f"{w}: a {end - t:.1f} s cut-away; check it holds attention")
        roll, src = b.get("roll"), b.get("source")
        if roll not in ROLLS:
            errors.append(f"{w}: `roll` must be A, B or G")
        if src not in SOURCES:
            errors.append(f"{w}: `source` must be one of {list(SOURCES)}")
        for k in ("shows", "why"):
            if not _txt(b.get(k)):
                errors.append(f"{w}: `{k}` is required")
        for k in ("line", "shows", "why", "move"):
            if PLACEHOLDER_RE.search(_txt(b.get(k))):
                errors.append(f"{w}: `{k}` looks like placeholder text")
        if roll == "A" and src != "own":
            errors.append(f"{w}: an A-roll beat is the project's own footage (`source`: own)")
        if roll == "A" and not b.get("img"):
            errors.append(f"{w}: an A-roll beat needs its real frame (`grab` fills it from the source)")
        elif b.get("img"):
            img_ok(w, b.get("img"))
        elif src not in ("sketch", "generated"):
            errors.append(f"{w}: no `img`; only a `sketch` or a not-yet-made `generated` beat may be shown without a frame")
        if src == "generated" and not _txt(b.get("cost")):
            errors.append(f"{w}: a generated beat states its `cost` (estimate through paid-spend-gate)")
        if b.get("shot") is not None and b.get("shot") not in SHOTS:
            errors.append(f"{w}: `shot` must be one of {list(SHOTS)}")
        for k in ("signature", "text_only", "hero"):
            if b.get(k) is not None and not isinstance(b.get(k), bool):
                errors.append(f"{w}: `{k}` is true or false")
    if beats and not any(isinstance(b, dict) and b.get("roll") in ("B", "G") for b in beats):
        warnings.append("no B-roll or graphic beat: a plain edit (cuts, captions, music) does not need this board")
    if spec.get("title") and PLACEHOLDER_RE.search(_txt(spec.get("title"))):
        errors.append("`title` looks like placeholder text")
    good = [b for b in beats if isinstance(b, dict) and isinstance(b.get("id"), str)]
    if len(good) >= 3:
        has_sig = bool(isinstance(mood, dict) and _txt(mood.get("signature")))
        warnings.extend(sameness(good, base, has_sig))
    return errors, warnings


def subject_words(text: str) -> set[str]:
    """Content words of a `shows` line: lower case, no stop words; a Hebrew word of 4+ letters loses one prefix letter (ה, ו, ב, ל, מ, ש, כ)."""
    out = set()
    for w in re.findall(r"\w+", text.lower()):
        if w in STOPWORDS or w.isdigit():
            continue
        if not w.isascii():
            if len(w) >= 4 and w[0] in "הובלמשכ":
                w = w[1:]
            if len(w) >= 2:
                out.add(w)
        elif len(w) >= 3:
            out.add(w)
    return out


def sameness(beats: list[dict], base: Path, has_signature: bool) -> list[str]:
    """Pure (reads the image bytes only): warnings for a board whose beats look alike. They never refuse the board."""
    out: list[str] = []
    run: list[dict] = []

    def flush() -> None:
        if len(run) >= 3:
            out.append(f"beats {run[0]['id']}-{run[-1]['id']}: {len(run)} `{run[0]['shot']}` shots in a row; change the size or the angle "
                       "so each cut is felt")

    for b in beats:
        if b.get("shot") in SHOTS and run and run[-1].get("shot") == b["shot"]:
            run.append(b)
            continue
        flush()
        run = [b] if b.get("shot") in SHOTS else []
    flush()
    shots = [b["shot"] for b in beats if b.get("shot") in SHOTS]
    if len(shots) >= 4:
        top = max(sorted(set(shots)), key=shots.count)
        if shots.count(top) / len(shots) > 0.5:
            out.append(f"`{top}` is {shots.count(top)} of {len(shots)} beats: more than half the board in one shot size reads as one long shot")
    seen: dict[str, list[str]] = {}
    for b in beats:
        rel = b.get("img")
        if isinstance(rel, str) and rel.strip():
            p = (base / rel).resolve()
            try:
                key = hashlib.sha1(p.read_bytes()).hexdigest() if p.is_file() else str(p)
            except OSError:
                key = str(p)
            seen.setdefault(key, []).append(b["id"])
    for ids in seen.values():
        if len(ids) > 1:
            out.append(f"beats {', '.join(ids)} use the same image: the viewer sees one picture twice; give each beat its own frame")
    texty = [b["id"] for b in beats if b.get("text_only") is True or (b.get("roll") == "G" and b.get("text_only") is not False
                                                                      and TEXT_BEAT_RE.search(_txt(b.get("shows"))))]
    if len(texty) / len(beats) > 0.4:
        out.append(f"{len(texty)} of {len(beats)} beats are text-only graphics ({', '.join(texty)}): show the thing itself in some of them")
    for a, b in zip(beats, beats[1:]):
        if a.get("roll") == b.get("roll") and a.get("shot") in SHOTS and a.get("shot") == b.get("shot"):
            wa, wb = subject_words(_txt(a.get("shows"))), subject_words(_txt(b.get("shows")))
            shared = wa & wb
            if shared and len(shared) / max(1, min(len(wa), len(wb))) >= 0.5:
                out.append(f"beats {a['id']}, {b['id']}: same roll, same `{a['shot']}` shot, same subject ({', '.join(sorted(shared)[:3])}): "
                           "the second reads as a repeat; change the subject or the size, or merge them")
    hero = [b["id"] for b in beats if b.get("hero") is True]
    if len(hero) > 4:
        out.append(f"{len(hero)} hero beats ({', '.join(hero)}): a hero is held longest because it is rare; keep 2-4")
    sig = [b["id"] for b in beats if b.get("signature") is True]
    if len(sig) > 2:
        out.append(f"the signature device is marked on {len(sig)} beats ({', '.join(sig)}): keep it on 1-2 beats so it stays special")
    elif has_signature and not sig:
        out.append("no beat is marked `signature: true`: mark the 1-2 beats that carry the signature device")
    return out


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def summary(spec: dict) -> dict:
    beats = spec.get("beats", [])
    counts = {r: sum(1 for b in beats if b.get("roll") == r) for r in ROLLS}
    secs = {r: round(sum(b["end"] - b["t"] for b in beats if b.get("roll") == r), 2) for r in ROLLS}
    return {"beats": len(beats), "rolls": counts, "seconds": secs, "duration_s": round(max((b["end"] for b in beats), default=0), 2),
            "planned_without_frame": [b["id"] for b in beats if not b.get("img")],
            "paid": [b["id"] for b in beats if b.get("source") == "generated"]}


def grab(spec_path: Path, video: Path, width: int = 540) -> dict:
    """Extract the real source frame of every A-roll beat without an image. Returns {"written": [...], "status": ...}."""
    ff = shutil.which("ffmpeg")
    if not ff:
        return {"status": "not_run", "reason": "ffmpeg is not on PATH"}
    if not video.is_file():
        return {"status": "not_run", "reason": f"no video at {video}"}
    spec = load(spec_path)
    out_dir = spec_path.parent / "frames"
    written, failed = [], []
    for b in spec.get("beats", []):
        if b.get("roll") != "A" or b.get("img") or not _num(b.get("t")) or not _num(b.get("end")):
            continue
        at = b.get("src_t") if _num(b.get("src_t")) else (b["t"] + b["end"]) / 2
        bid = b.get("id") if isinstance(b.get("id"), str) and ID_RE.match(b["id"]) else f"beat{len(written) + len(failed) + 1}"
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = out_dir / f"{bid}.jpg"
        p = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{at:.3f}", "-i", str(video), "-frames:v", "1",
                            "-vf", f"scale={int(width)}:-2", "-q:v", "3", str(dst)], capture_output=True, text=True)
        if p.returncode == 0 and dst.is_file() and dst.stat().st_size > 0:
            b["img"] = dst.relative_to(spec_path.parent).as_posix()
            b.setdefault("src_t", round(float(at), 3))
            written.append(b["img"])
        else:
            failed.append({"id": bid, "at": at, "error": (p.stderr or "no frame written").strip()[-300:]})
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "ok" if not failed else "partial", "written": written, "failed": failed, "spec": str(spec_path)}


def data_uri(base: Path, rel: str) -> str:
    p = (base / rel).resolve()
    return f"data:{IMG_MIME[p.suffix.lower()]};base64," + base64.b64encode(p.read_bytes()).decode("ascii")


def ui_css() -> str:
    """The shared student-screen tokens (scripts/ui/tokens.css) plus the embedded Heebo subset (OFL, scripts/ui/OFL-Heebo.txt)."""
    ui = Path(__file__).resolve().parent / "ui"
    try:
        css = (ui / "tokens.css").read_text(encoding="utf-8")
    except OSError:
        css = ""
    try:
        b64 = base64.b64encode((ui / "heebo-he-latin.woff2").read_bytes()).decode("ascii")
        css = '@font-face{font-family:"Heebo UI";src:url(data:font/woff2;base64,' + b64 + ') format("woff2");font-weight:100 900;font-display:swap}\n' + css
    except OSError:
        pass
    return css


def page(spec: dict, base: Path, token: str | None) -> str:
    """The page. token=None -> the static page (its buttons save storyboard_review.json instead of posting)."""
    lang = spec.get("lang", "he")
    u = UI[lang]
    mood = spec["mood"]
    beats = []
    for b in spec["beats"]:
        beats.append({"id": b["id"], "t": b["t"], "end": b["end"], "tc": f"{tc(b['t'])}-{tc(b['end'])}", "roll": b["roll"], "source": b["source"],
                      "line": _txt(b.get("line")), "shows": _txt(b.get("shows")), "move": _txt(b.get("move")), "why": _txt(b.get("why")),
                      "cost": _txt(b.get("cost")), "img": data_uri(base, b["img"]) if b.get("img") else None,
                      "shot": b.get("shot") if b.get("shot") in SHOTS else None, "sig": b.get("signature") is True,
                      "hero": b.get("hero") is True})
    refs = [{"img": data_uri(base, r["img"]), "caption": _txt(r.get("caption"))} for r in mood.get("refs", [])]
    w, h = ASPECTS[spec.get("aspect", "9:16")]
    data = {"ui": u, "token": token, "beats": beats, "refs": refs, "palette": mood["palette"], "feel": _txt(mood.get("feel")),
            "signature": _txt(mood.get("signature")), "type": mood.get("type"), "story": _txt(spec.get("story")),
            "store": "storyboard:" + _txt(spec.get("project")), "aspect": f"{w} / {h}"}
    blob = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")  # no "<" can open or close a tag inside the script
    out = (TEMPLATE.replace("__UI_CSS__", ui_css()).replace("__DIR__", u["dir"]).replace("__LANG__", lang)
           .replace("__TITLE__", html.escape(_txt(spec.get("title")))).replace("__DATA__", blob))
    return re.sub(r"__U_([a-z_]+)__", lambda m: html.escape(u[m.group(1)]), out)


def validate_review(payload, beat_ids: list[str]) -> tuple[dict | None, list[str]]:
    """Pure: the POSTed body -> (review, errors). An approval carries no notes; notes need at least one non-empty text."""
    if not isinstance(payload, dict):
        return None, ["body must be an object"]
    notes = payload.get("notes", {})
    general = payload.get("general", "")
    if not isinstance(notes, dict) or not isinstance(general, str):
        return None, ["`notes` must map beat ids to text and `general` must be text"]
    clean = {}
    for k, v in notes.items():
        if k not in beat_ids:
            return None, [f"unknown beat {k!r} (the page is older than the board: reload it)"]
        if not isinstance(v, str) or len(v) > MAX_TEXT:
            return None, [f"note on {k}: text of at most {MAX_TEXT} characters"]
        if v.strip():
            clean[k] = v.strip()
    general = general.strip()
    if len(general) > MAX_TEXT:
        return None, [f"general note longer than {MAX_TEXT} characters"]
    approved = payload.get("approved") is True
    if approved and (clean or general):
        return None, ["an approval carries no notes: send the notes instead"]
    if not approved and not (clean or general):
        return None, ["no notes: write a note, or approve the board"]
    order = [k for k in beat_ids if k in clean]
    return {"approved": approved, "notes": [{"beat": k, "text": clean[k]} for k in order], "general": general}, []


def review_lines(review: dict, spec: dict) -> list[str]:
    by_id = {b["id"]: b for b in spec["beats"]}
    lines = []
    for n, x in enumerate(review["notes"], 1):
        b = by_id[x["beat"]]
        lines.append(f'{n}. [{x["beat"]} {ROLLS[b["roll"]]} {tc(b["t"])}-{tc(b["end"])}] "{x["text"]}"')
    if review["general"]:
        lines.append(f'{len(lines) + 1}. [general] "{review["general"]}"')
    return lines


def write_review(out_dir: Path, spec_path: Path, spec: dict, review: dict) -> dict:
    doc = {"schema": "avc.storyboard-review/1", "spec": str(spec_path), "project": spec.get("project"),
           "received_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), **review}
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "storyboard_review.json.part"
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, out_dir / "storyboard_review.json")
    head = "APPROVED, no notes" if review["approved"] else "notes"
    (out_dir / "storyboard_review.md").write_text("\n".join([f"## Storyboard - {head} ({doc['received_utc']})", ""] + review_lines(review, spec)) + "\n",
                                                   encoding="utf-8")
    return doc


def serve(spec_path: Path, out_dir: Path, port: int = 0, timeout: float = 3600.0, open_browser: bool = False, out=None) -> int:
    """Serve the board and wait for ONE valid answer. Returns 0 (answered), 2 (refused spec / cannot listen), 3 (timeout)."""
    import secrets
    import socketserver
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    out = out or sys.stdout
    try:
        spec = load(spec_path)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "refused", "errors": [f"cannot read {spec_path}: {exc}"]}, ensure_ascii=False), file=out, flush=True)
        return 2
    errors, warnings = validate(spec, spec_path.parent)
    if errors:
        print(json.dumps({"status": "refused", "errors": errors}, ensure_ascii=False, indent=2), file=out, flush=True)
        return 2
    token = secrets.token_urlsafe(18)
    body = page(spec, spec_path.parent, token).encode("utf-8")
    ids = [b["id"] for b in spec["beats"]]
    result: dict = {}
    done = threading.Event()
    csp = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; font-src data:; img-src data:; "
           "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # stdout carries only the result the agent reads
            pass

        def _send(self, code, ctype, payload: bytes):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", csp)
            self.end_headers()
            self.wfile.write(payload)

        def _json(self, code, obj):
            self._send(code, "application/json; charset=utf-8", json.dumps(obj, ensure_ascii=False).encode("utf-8"))

        def do_GET(self):
            if self.path.split("?")[0] == "/":
                self._send(200, "text/html; charset=utf-8", body)
            else:
                self._json(404, {"errors": ["not found"]})

        def do_POST(self):
            origin = self.headers.get("Origin")
            p = self.server.server_address[1]
            if self.path != "/review" or self.headers.get("X-Board-Token") != token or (origin and origin not in (f"http://127.0.0.1:{p}", f"http://localhost:{p}")):
                self._json(403, {"errors": ["forbidden"]})
                return
            ln = int(self.headers.get("Content-Length") or 0)
            if ln <= 0 or ln > MAX_BODY:
                self._json(413, {"errors": ["body too large or empty"]})
                return
            try:
                payload = json.loads(self.rfile.read(ln).decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                self._json(400, {"errors": ["not JSON"]})
                return
            review, errs = validate_review(payload, ids)
            if errs:
                self._json(400, {"errors": errs})
                return
            result.update(write_review(out_dir, spec_path, spec, review))
            self.close_connection = True
            self._json(200, {"ok": True})
            self.wfile.flush()
            self._final = True  # done fires in finish(), after the response is written

        def finish(self):
            try:
                super().finish()
            finally:
                if getattr(self, "_final", False):
                    done.set()

    class Server(ThreadingHTTPServer):
        def server_bind(self):  # skip HTTPServer's reverse-DNS lookup (slow on macOS)
            socketserver.TCPServer.server_bind(self)
            self.server_name, self.server_port = self.server_address[:2]

    try:
        httpd = Server(("127.0.0.1", port), Handler)
    except OSError as exc:
        print(json.dumps({"status": "not_run", "reason": f"cannot listen on 127.0.0.1:{port}: {exc}"}, ensure_ascii=False), file=out, flush=True)
        return 2
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(json.dumps({"status": "waiting", "url": url, "summary": summary(spec), "warnings": warnings, "timeout_s": timeout,
                      "note": "open the url for the user (browser pane); this process exits with the answer when they press a button"},
                     ensure_ascii=False), file=out, flush=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    if open_browser:
        import webbrowser

        webbrowser.open(url)
    got = done.wait(timeout)
    httpd.shutdown()
    httpd.server_close()
    if not got:
        print(json.dumps({"status": "timeout", "reason": f"no answer within {timeout:.0f} s; serve again when the user is ready"}, ensure_ascii=False),
              file=out, flush=True)
        return 3
    if result["approved"]:
        print(json.dumps({"status": "approved", "review_json": str(out_dir / "storyboard_review.json"),
                          "next": "write `STORYBOARD APPROVED <date>` in hf/CHANGELOG.md, lock the beats in PROMPT.md <structure>, then build: "
                                  "each beat's frame is the target its built still is compared with"}, ensure_ascii=False, indent=2), file=out, flush=True)
        return 0
    print(json.dumps({"status": "notes", "review_json": str(out_dir / "storyboard_review.json"), "lines": review_lines(result, spec),
                      "next": "answer each note in PROMPT.md and storyboard.json (new frame, new beat or a reason to keep it), then serve the board again"},
                     ensure_ascii=False, indent=2), file=out, flush=True)
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="__LANG__" dir="__DIR__"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
__UI_CSS__
header{display:flex;align-items:center;gap:12px;padding:14px 20px;border-bottom:1px solid var(--line);background:var(--surface);position:sticky;top:0;z-index:3}
.eyebrow{font-size:.78rem;font-weight:600;letter-spacing:.04em;color:var(--pri-h);display:block}
header h1{font-size:1.05rem;font-weight:600;margin:0}
.chips{margin-inline-start:auto;display:flex;gap:8px;flex-wrap:wrap}
.chip{border:1px solid var(--line);background:var(--raised);border-radius:999px;padding:3px 12px;font-size:.84rem;color:var(--muted);white-space:nowrap}
.chip b{color:var(--fg)}
main{max-width:1500px;margin:0 auto;padding:20px;display:flex;flex-direction:column;gap:20px}
@media (max-width:700px){main{padding:12px}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:18px;box-shadow:var(--shadow)}
h2{font-size:1rem;margin:0 0 14px;font-weight:600}
.story{font-size:1.15rem;margin:0}
.mood{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
.lbl{font-size:.8rem;color:var(--muted);margin:0 0 6px}
.sw{display:flex;gap:8px;flex-wrap:wrap}.sw div{display:flex;flex-direction:column;align-items:center;gap:4px;font:500 .72rem/1 var(--mono);color:var(--muted);direction:ltr}
.sw span{width:52px;height:52px;border-radius:12px;border:1px solid var(--line-strong)}
.spec{font-size:1.6rem;line-height:1.3;margin:0}
.refs{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin-top:16px}
.refs figure{margin:0;position:relative}.refs img{width:100%;border-radius:10px;display:block;border:1px solid var(--line)}
.refs figcaption{font-size:.84rem;margin-top:6px}
.badge{position:absolute;top:6px;inset-inline-start:6px;background:rgba(5,8,17,.75);color:#E8EDF5;font-size:.7rem;padding:2px 8px;border-radius:6px}
.rhythm{display:flex;height:34px;border-radius:10px;overflow:hidden;border:1px solid var(--line);direction:ltr}
.rhythm div{display:grid;place-items:center;font:600 .72rem/1 var(--mono);color:#0C0A09;min-width:2px;border-inline-end:1px solid rgba(0,0,0,.25);cursor:pointer}
.rA{background:#D9C79A}.rB{background:#D4A72C}.rG{background:#A8A29E}
.legend{display:flex;gap:16px;margin-top:8px;font-size:.84rem;color:var(--muted)}.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-inline-end:6px;vertical-align:-1px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:16px}
.beat{background:var(--raised);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.beat.has{border-color:var(--pri-h)}
.frame{position:relative;background:#000;aspect-ratio:var(--ar);width:100%}
.frame img{width:100%;height:100%;object-fit:cover;display:block}
.sketch{position:absolute;inset:0;display:grid;place-items:center;padding:16px;text-align:center;background:repeating-linear-gradient(45deg,var(--sunken),var(--sunken) 10px,var(--surface) 10px,var(--surface) 20px);color:var(--fg);font-size:.95rem}
.tags{position:absolute;top:8px;inset-inline:8px;display:flex;justify-content:space-between;gap:6px}
.tag{background:rgba(5,8,17,.78);color:#E8EDF5;font:600 .72rem/1 var(--mono);padding:4px 8px;border-radius:6px;direction:ltr}
.tag.A{background:#D9C79A;color:#0C0A09}.tag.B{background:#D4A72C;color:#0C0A09}.tag.G{background:#A8A29E;color:#0C0A09}
.body{padding:12px;display:flex;flex-direction:column;gap:6px;font-size:.9rem;flex:1}
.line{font-size:1rem;font-weight:600;margin:0}
.kv{margin:0;color:var(--muted)}.kv b{color:var(--fg);font-weight:600}
textarea{width:100%;min-height:58px;resize:vertical;border:1px solid var(--line);border-radius:10px;background:var(--sunken);padding:8px 10px;margin-top:auto;line-height:1.45}
.decide{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media (max-width:700px){.decide{grid-template-columns:1fr}}
.decide textarea{grid-column:1/-1;min-height:64px}
.act{display:flex;align-items:center;gap:12px;text-align:start;padding:12px 14px;min-height:60px;border-radius:12px}
.act b{display:block}.act small{display:block;font-size:.82rem;opacity:.85;font-weight:400}
.act.go{background:var(--raised);border-color:var(--pri);color:var(--pri-h)}
.act.ok{background:var(--pri);border-color:var(--pri);color:var(--pri-ink)}
#status{grid-column:1/-1;min-height:1.3em;text-align:center;font-size:.9rem}.okc{color:var(--ok)}.warnc{color:var(--warn)}
</style></head><body>
<header><div><span class="eyebrow">__U_eyebrow__</span><h1>__TITLE__</h1></div><div class="chips" id="chips"></div></header>
<main>
<section class="card"><p class="lbl">__U_story__</p><p class="story" id="story"></p></section>
<section class="card"><h2>__U_mood__</h2><div class="mood">
 <div><p class="lbl">__U_feel__</p><p id="feel" style="margin:0"></p><p class="lbl" style="margin-top:12px">__U_signature__</p><p id="sig" style="margin:0"></p></div>
 <div><p class="lbl">__U_palette__</p><div class="sw" id="pal"></div></div>
 <div id="typebox"><p class="lbl">__U_type__ · <span id="fam"></span></p><p class="spec" id="spec" dir="auto"></p><p class="lbl" style="margin-top:6px">__U_font_note__</p></div>
</div><div class="refs" id="refs"></div></section>
<section class="card"><h2>__U_rhythm__</h2><div class="rhythm" id="rhythm"></div><div class="legend" id="legend"></div></section>
<section class="card"><h2>__U_board__</h2><div class="grid" id="grid"></div></section>
<section class="card decide"><textarea id="general" placeholder="__U_general_ph__"></textarea>
 <button class="act go" id="send"><span><b id="sendLabel">__U_send__</b><small>__U_send_hint__</small></span></button>
 <button class="act ok" id="approve"><span><b id="approveLabel">__U_approve__</b><small>__U_approve_hint__</small></span></button>
 <div id="status" role="status" aria-live="polite"></div></section>
</main>
<script>
(function(){
var B=__DATA__,U=B.ui,$=function(s){return document.querySelector(s)},notes={},sent=false;
function el(t,c,txt){var e=document.createElement(t);if(c)e.className=c;if(txt!=null)e.textContent=txt;return e}
try{var s=localStorage.getItem(B.store);if(s){var o=JSON.parse(s);notes=o.notes||{};$('#general').value=o.general||''}}catch(e){}
function save(){try{localStorage.setItem(B.store,JSON.stringify({notes:notes,general:$('#general').value}))}catch(e){}}
document.documentElement.style.setProperty('--ar',B.aspect);
$('#story').textContent=B.story;$('#feel').textContent=B.feel;$('#sig').textContent=B.signature||'-';
B.palette.forEach(function(c){var d=el('div'),s=el('span');s.style.background=c;d.appendChild(s);d.appendChild(document.createTextNode(c));$('#pal').appendChild(d)});
if(B.type){$('#fam').textContent=B.type.family;$('#spec').textContent=B.type.sample;$('#spec').style.fontFamily='"'+B.type.family+'", var(--sans)';$('#spec').style.color=B.palette[1]||''}else{$('#typebox').hidden=true}
B.refs.forEach(function(r){var f=el('figure'),i=el('img');i.src=r.img;i.alt=r.caption;f.appendChild(i);f.appendChild(el('span','badge',U.ref_badge));f.appendChild(el('figcaption','',r.caption));$('#refs').appendChild(f)});
var total=B.beats.reduce(function(m,b){return Math.max(m,b.end)},0)||1,count={A:0,B:0,G:0};
B.beats.forEach(function(b){count[b.roll]++;var d=el('div','r'+b.roll,b.roll);d.style.flex=String(b.end-b.t);d.title=b.tc+'  '+b.shows;
 d.onclick=function(){document.getElementById('beat-'+b.id).scrollIntoView({behavior:'smooth',block:'center'})};$('#rhythm').appendChild(d)});
['A','B','G'].forEach(function(r){var s=el('span'),i=el('i','r'+r);s.appendChild(i);s.appendChild(document.createTextNode(U.roll[r]+' · '+count[r]));$('#legend').appendChild(s)});
$('#chips').appendChild(el('span','chip',B.beats.length+' '+U.beats));
B.beats.forEach(function(b){var c=el('article','beat');c.id='beat-'+b.id;var f=el('div','frame');
 if(b.img){var i=el('img');i.src=b.img;i.alt=b.shows;f.appendChild(i)}else{var sk=el('div','sketch');sk.appendChild(el('b','',U.planned));sk.appendChild(el('p','',b.shows));f.appendChild(sk)}
 var tg=el('div','tags');tg.appendChild(el('span','tag '+b.roll,U.roll[b.roll]+(b.shot?' · '+U.shot[b.shot]:'')+(b.sig?' ★':'')+(b.hero?' · hero':'')));tg.appendChild(el('span','tag',b.tc));f.appendChild(tg);c.appendChild(f);
 var bd=el('div','body');if(b.line)bd.appendChild(el('p','line','"'+b.line+'"'));
 [['shows',b.shows],['move',b.move],['why',b.why],['source',U.src[b.source]+(b.cost?' · '+b.cost:'')]].forEach(function(kv){if(!kv[1])return;var p=el('p','kv'),k=el('b','',U[kv[0]]+': ');p.appendChild(k);p.appendChild(document.createTextNode(kv[1]));bd.appendChild(p)});
 var ta=el('textarea');ta.placeholder=U.note_ph;ta.value=notes[b.id]||'';ta.oninput=function(){notes[b.id]=ta.value;c.classList.toggle('has',!!ta.value.trim());save();refresh()};
 c.classList.toggle('has',!!ta.value.trim());bd.appendChild(ta);c.appendChild(bd);$('#grid').appendChild(c)});
$('#general').oninput=function(){save();refresh()};
function n(){var k=0;for(var x in notes)if(notes[x]&&notes[x].trim())k++;return k+($('#general').value.trim()?1:0)}
function refresh(){var k=n();$('#sendLabel').textContent=U.send+(k?' ('+k+')':'')+' ✓';$('#send').disabled=sent||!k;$('#approve').disabled=sent||!!k;$('#approve').title=k?U.has_notes:''}
function st(m,c){var s=$('#status');s.textContent=m;s.className=c||''}
function body(ok){var o={};if(!ok)for(var x in notes)if(notes[x]&&notes[x].trim())o[x]=notes[x];return {approved:ok,notes:o,general:ok?'':$('#general').value}}
function finish(msg){sent=true;st(msg,'okc');try{localStorage.removeItem(B.store)}catch(e){}refresh()}
function post(ok){var b=body(ok);if(!B.token){var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(b,null,2)],{type:'application/json'}));a.download='storyboard_review.json';a.click();finish(U.saved);return}
 var x=new XMLHttpRequest();st(U.sending);$('#send').disabled=true;$('#approve').disabled=true;x.open('POST','/review');x.setRequestHeader('Content-Type','application/json');x.setRequestHeader('X-Board-Token',B.token);
 x.onload=function(){var r={};try{r=JSON.parse(x.responseText)}catch(e){}if(x.status===200)finish(ok?U.approved:U.sent);else{st(U.fail+((r.errors||[]).join('; ')||x.status),'warnc');refresh()}};
 x.onerror=function(){st(U.fail+'offline','warnc');refresh()};x.send(JSON.stringify(b))}
$('#send').onclick=function(){if(n())post(false)};var armed=null;function disarm(){if(armed){clearTimeout(armed);armed=null}$('#approveLabel').textContent=U.approve}
$('#approve').onclick=function(){if(n()||sent)return;if(!armed){$('#approveLabel').textContent=U.approve_again;st(U.approve_q);armed=setTimeout(function(){disarm();st('')},6000);return}disarm();post(true)};
refresh();
})();
</script></body></html>
"""


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return subprocess.call([sys.executable, str(Path(__file__).with_name("test_storyboard_board.py"))])
    if len(argv) < 2 or argv[0] not in ("check", "grab", "build", "serve"):
        print(__doc__)
        return 2
    cmd, spec_path = argv[0], Path(argv[1])
    opts = {"--out": None, "--video": None, "--width": "540", "--port": "0", "--timeout": "3600"}
    open_b, i = False, 2
    while i < len(argv):
        if argv[i] == "--open":
            open_b, i = True, i + 1
        elif argv[i] in opts and i + 1 < len(argv):
            opts[argv[i]], i = argv[i + 1], i + 2
        else:
            print("unknown option", argv[i], file=sys.stderr)
            return 2
    if cmd == "grab":
        if not opts["--video"]:
            print("grab needs --video SOURCE", file=sys.stderr)
            return 2
        res = grab(spec_path, Path(opts["--video"]), int(opts["--width"]))
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return {"ok": 0, "partial": 1}.get(res["status"], 2)
    if cmd == "serve":
        if not opts["--out"]:
            print("serve needs --out DIR (for example _work/storyboard)", file=sys.stderr)
            return 2
        return serve(spec_path, Path(opts["--out"]), int(opts["--port"]), float(opts["--timeout"]), open_b)
    try:
        spec = load(spec_path)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "refused", "errors": [f"cannot read {spec_path}: {exc}"]}, ensure_ascii=False))
        return 2
    errors, warnings = validate(spec, spec_path.parent)
    if errors:
        print(json.dumps({"status": "refused", "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
        return 2
    if cmd == "check":
        print(json.dumps({"status": "ok", "summary": summary(spec), "warnings": warnings}, ensure_ascii=False, indent=2))
        return 0
    if not opts["--out"]:
        print("build needs --out DIR", file=sys.stderr)
        return 2
    out_dir = Path(opts["--out"])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "storyboard.html").write_text(page(spec, spec_path.parent, None), encoding="utf-8")
    print(json.dumps({"status": "ok", "page": str(out_dir / "storyboard.html"), "summary": summary(spec), "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

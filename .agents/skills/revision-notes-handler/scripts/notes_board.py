#!/usr/bin/env python3
"""notes_board - the user watches the draft in a browser, drops notes on the timeline, presses ONE send button; the agent gets them.

Usage:
  python notes_board.py serve VIDEO --out DIR [--round N] [--lang he|en] [--fps 30] [--port 0] [--timeout 3600] [--open]
  python notes_board.py --self-check            # runs scripts/test_notes_board.py

serve   serves a review page on 127.0.0.1 (a free port unless --port): the video (seekable, HTTP range requests) over a timeline that
        shows every note (dots for points, bands for ranges); a note is a point (the paused time), a RANGE from a start to an end
        ("סמן התחלה" / "סמן סוף", typed times, I/O keys like an NLE, or Shift+drag on the timeline) or a general note; notes are
        edited in place, a range note can be played back alone; step buttons "−1 frame / +1 frame / −1 second / +1 second".
        The notes survive a page reload (browser storage).
        "שלח הערות (N) ✓" POSTs the notes; "מאשר, אין הערות ✓" (enabled only while the list is empty) POSTs an approval. The server
        validates, writes DIR/notes.json and DIR/notes.md, prints the numbered note lines plus the frame-strip times per note (or
        status "approved") and EXITS 0 - an agent that started it as a background command is notified, the user exports and pastes
        nothing. Invalid notes are answered with the reason and the server keeps waiting; no send within --timeout exits 3; no video exits 2.
        Guards: a per-run token, an Origin check, a 1 MB body cap, a Content-Security-Policy that allows no other request; the page
        loads nothing from the internet. The video is read, never modified or copied.
Stdlib only, Python 3.10+.
"""

from __future__ import annotations

import base64
import datetime as _dt
import html
import json
import os
import re
import sys
from pathlib import Path

MAX_BODY = 1 << 20
MAX_NOTES = 200
MAX_TEXT = 2000
MIME = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm", ".mkv": "video/x-matroska"}

STEP = {"b1": "−1 second", "pf": "−1 frame", "nf": "+1 frame", "f1": "+1 second"}  # the owner asked for these words on the step buttons
UI = {
    "he": {"dir": "rtl", "title": "הערות על הטיוטה", "new_note": "הערה חדשה", "from": "מ-", "to": "עד", "set_in": "סמן התחלה", "set_out": "סמן סוף",
           "now_ph": "הנקודה הנוכחית", "no_end": "בלי סוף (נקודה אחת)", "clear_range": "נקה זמנים", "general": "הערה כללית (לא לזמן מסוים)",
           "placeholder": "מה לשנות כאן?", "add": "הוסף הערה", "notes_title": "ההערות שלך", "count": "הערות", "all": "כללי",
           "empty": "עוד אין הערות. עצור את הסרטון בנקודה שצריך לשנות, או סמן התחלה וסוף, וכתוב.", "del": "מחק", "edit_tip": "לחץ כדי לערוך",
           "play_range": "נגן קטע", "send": "שלח הערות", "approve": "מאשר, אין הערות ✓", "approve_q": "לאשר את הטיוטה בלי הערות?",
           "has_notes": "יש הערות ברשימה: שלח אותן או מחק אותן", "sending": "שולח לסוכן...", "sent": "ההערות נשלחו לסוכן. אפשר לסגור את הדף.",
           "approved": "הטיוטה אושרה. הסוכן קיבל את האישור, אפשר לסגור את הדף.", "fail": "השליחה לא הצליחה: ", "none": "אין הערות לשלוח",
           "out_first": "קודם סמן התחלה, והסוף צריך להיות אחריה", "play": "נגן / עצור", "mute": "השתק", "fs": "מסך מלא",
           "track_tip": "לחיצה: קפיצה לזמן · Shift + גרירה: סימון קטע", "eyebrow": "סבב הערות", "round": "סבב", "next_q": "מה הלאה?",
           "send_hint": "הסוכן מתקן לפי ההערות ומחזיר טיוטה חדשה", "approve_hint": "ממשיכים לרינדור הסופי ולמסירה",
           "keys": [["Space", "נגן / עצור"], ["J / L", "שנייה"], ["← / →", "פריים"], ["I", "התחלה"], ["O", "סוף"], ["X", "נקה זמנים"],
                    ["N", "הערה חדשה"], ["Shift", "+ גרירה על הציר: סימון קטע"]], **STEP},
    "en": {"dir": "ltr", "title": "Notes on the draft", "new_note": "New note", "from": "From", "to": "To", "set_in": "Mark start", "set_out": "Mark end",
           "now_ph": "the playhead", "no_end": "no end (one point)", "clear_range": "Clear times", "general": "General note (no specific time)",
           "placeholder": "What should change here?", "add": "Add note", "notes_title": "Your notes", "count": "notes", "all": "general",
           "empty": "No notes yet. Pause where something should change, or mark a start and an end, and type.", "del": "Delete", "edit_tip": "Click to edit",
           "play_range": "Play range", "send": "Send notes", "approve": "Approved, no notes ✓", "approve_q": "Approve the draft with no notes?",
           "has_notes": "There are notes in the list: send or delete them", "sending": "Sending to the agent...", "sent": "Notes sent to the agent. You can close this page.",
           "approved": "Draft approved. The agent has it; you can close this page.", "fail": "Sending failed: ", "none": "No notes to send",
           "out_first": "Mark a start first; the end must come after it", "play": "Play / pause", "mute": "Mute", "fs": "Full screen",
           "track_tip": "Click: jump · Shift + drag: mark a range", "eyebrow": "Review round", "round": "Round", "next_q": "What next?",
           "send_hint": "The agent fixes these and comes back with a new draft", "approve_hint": "On to the final render and delivery",
           "keys": [["Space", "play / pause"], ["J / L", "one second"], ["← / →", "one frame"], ["I", "start"], ["O", "end"], ["X", "clear times"],
                    ["N", "new note"], ["Shift", "+ drag on the timeline: mark a range"]], **STEP},
}


def tc(t: float | None) -> str:
    """Seconds -> m:ss.cc (the form the user reads on the player); None -> 'general'."""
    if t is None:
        return "general"
    cs = int(round(t * 100))
    m, rest = divmod(cs, 6000)
    return f"{m}:{rest // 100:02d}.{rest % 100:02d}"


def strip_times(t: float | None, end: float | None, duration: float | None) -> list[float]:
    """Frame-strip times for a note (rule G2 of the skill: +-1 s around a point, the whole range plus 0.5 s each side for a range)."""
    if t is None:
        return []
    a, b = (t - 1.0, t + 1.0) if end is None else (t - 0.5, end + 0.5)
    a = max(0.0, a)
    if duration:
        b = min(duration, b)
    if b <= a:
        return [round(a, 3)]
    n = 9 if end is None else min(24, max(9, int((b - a) / 0.25) + 1))
    return [round(a + (b - a) * i / (n - 1), 3) for i in range(n)]


def validate(payload, duration: float | None = None):
    """Pure: the POSTed body -> (notes, errors). notes = [{n, t, end, tc, text}] sorted by time, general notes last."""
    errors, notes = [], []
    if not isinstance(payload, dict) or not isinstance(payload.get("notes"), list):
        return [], ["body must be {\"notes\": [...]}"]
    items = payload["notes"]
    if not items:
        return [], ["no notes"]
    if len(items) > MAX_NOTES:
        return [], [f"more than {MAX_NOTES} notes"]
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict):
            errors.append(f"note {i}: not an object")
            continue
        text = it.get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"note {i}: empty text")
            continue
        if len(text) > MAX_TEXT:
            errors.append(f"note {i}: text longer than {MAX_TEXT} characters")
            continue
        t, end = it.get("t"), it.get("end")
        for name, v in (("t", t), ("end", end)):
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v < 0 or (duration and v > duration + 0.5)):
                errors.append(f"note {i}: {name} {v!r} is not a time inside the video")
                break
        else:
            if t is None and end is not None:
                errors.append(f"note {i}: an end without a start")
            elif end is not None and end <= t:
                errors.append(f"note {i}: end {end} is not after start {t}")
            else:
                notes.append({"t": None if t is None else round(float(t), 3), "end": None if end is None else round(float(end), 3), "text": text.strip()})
    if errors:
        return [], errors
    notes.sort(key=lambda x: (x["t"] is None, x["t"] or 0.0))
    for k, x in enumerate(notes, 1):
        x["n"] = k
        x["tc"] = tc(x["t"]) if x["end"] is None else f"{tc(x['t'])}-{tc(x['end'])}"
    return notes, []


def note_line(x: dict) -> str:
    """The round-log line the agent completes (`| class: ... | ledger: ... | cause: ...`, see references/round-log-and-presentation.md)."""
    return f'{x["n"]}. "{x["text"]}" @ {x["tc"]}'


def ui_css() -> str:
    """The shared student-screen tokens (scripts/ui/tokens.css) plus the embedded Heebo subset (OFL, scripts/ui/OFL-Heebo.txt).
    A missing file degrades to the system font; the page never loads anything from the network."""
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


def page(lang: str, fps: float, title: str, token: str, video_name: str, round_n: int = 1) -> str:
    u = UI[lang]
    data = json.dumps({"ui": {k: v for k, v in u.items() if k != "keys"}, "fps": fps, "token": token, "store": "notes:" + video_name},
                      ensure_ascii=False).replace("</", "<\\/")
    keys = "".join(f"<span><kbd>{html.escape(k)}</kbd>{html.escape(label)}</span>" for k, label in u["keys"])
    out = (TEMPLATE.replace("__UI_CSS__", ui_css()).replace("__DIR__", u["dir"]).replace("__LANG__", lang).replace("__TITLE__", html.escape(title))
           .replace("__ROUND__", str(int(round_n))).replace("__KEYS_HTML__", keys).replace("__DATA__", data))
    return re.sub(r"__U_([a-z0-9_]+)__", lambda m: html.escape(u[m.group(1)]), out)


def serve(video: Path, out_dir: Path, round_n: int = 1, lang: str = "he", fps: float = 30.0, port: int = 0, timeout: float = 3600.0,
          open_browser: bool = False, out=None) -> int:
    """Serve the review page and wait for ONE valid send. Returns 0 (notes received), 2 (no video / cannot listen), 3 (timeout)."""
    import secrets
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    out = out or sys.stdout
    if not video.is_file():
        print(json.dumps({"status": "not_run", "reason": f"no video at {video}"}, ensure_ascii=False), file=out, flush=True)
        return 2
    token = secrets.token_urlsafe(18)
    body = page(lang, fps, video.name, token, video.name, round_n).encode("utf-8")
    size = video.stat().st_size
    ctype = MIME.get(video.suffix.lower(), "application/octet-stream")
    result: dict = {}
    done = threading.Event()
    csp = ("default-src 'none'; media-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; font-src data:; "
           "img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # stdout carries only the result the agent reads
            pass

        def _head(self, code, ctype_, length, extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype_)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", csp)
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()

        def _json(self, code, obj):
            b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self._head(code, "application/json; charset=utf-8", len(b))
            self.wfile.write(b)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/":
                self._head(200, "text/html; charset=utf-8", len(body))
                self.wfile.write(body)
                return
            if path != "/video":
                self._json(404, {"errors": ["not found"]})
                return
            start, end = 0, size - 1
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", "").strip())
            partial = bool(m and (m.group(1) or m.group(2)))
            if partial:
                if m.group(1):
                    start = int(m.group(1))
                    end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
                else:  # suffix range: the last N bytes
                    start = max(0, size - int(m.group(2)))
                if start >= size or start > end:
                    self._head(416, "text/plain", 0, {"Content-Range": f"bytes */{size}"})
                    return
            n = end - start + 1
            extra = {"Accept-Ranges": "bytes"}
            if partial:
                extra["Content-Range"] = f"bytes {start}-{end}/{size}"
            self._head(206 if partial else 200, ctype, n, extra)
            try:
                with open(video, "rb") as f:
                    f.seek(start)
                    while n > 0:
                        chunk = f.read(min(1 << 20, n))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        n -= len(chunk)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # the browser cancels range requests while seeking: normal

        def do_POST(self):
            origin = self.headers.get("Origin")
            p = self.server.server_address[1]
            if self.path != "/notes" or self.headers.get("X-Board-Token") != token or (origin and origin not in (f"http://127.0.0.1:{p}", f"http://localhost:{p}")):
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
            dur = payload.get("duration") if isinstance(payload, dict) else None
            dur = float(dur) if isinstance(dur, (int, float)) and not isinstance(dur, bool) and dur > 0 else None
            approved = isinstance(payload, dict) and payload.get("approved") is True
            if approved:  # "מאשר, אין הערות": an approval carries no notes; notes with it are a contradiction, not an approval
                notes, errors = [], (["an approval carries no notes: send the notes instead"] if payload.get("notes") else [])
            else:
                notes, errors = validate(payload, dur)
            if errors:
                self._json(400, {"errors": errors})
                return
            for x in notes:
                x["strip_times"] = strip_times(x["t"], x["end"], dur)
            doc = {"schema": "avc.review-notes/1", "round": round_n, "video": str(video), "video_bytes": size, "duration_s": dur,
                   "received_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "approved": approved, "notes": notes}
            out_dir.mkdir(parents=True, exist_ok=True)
            tmp = out_dir / "notes.json.part"
            tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, out_dir / "notes.json")
            if approved:
                md = [f"## Round {round_n} - draft APPROVED on the review page, no notes ({doc['received_utc']})"]
            else:
                md = [f"## Round {round_n} - notes from the review page ({doc['received_utc']})", ""] + [note_line(x) for x in notes]
            (out_dir / "notes.md").write_text("\n".join(md) + "\n", encoding="utf-8")
            result.update(doc)
            self.close_connection = True
            self._json(200, {"ok": True, "count": len(notes)})
            self.wfile.flush()
            self._final = True  # done fires in finish(), after the response is fully written (a race on macOS CI)

        def finish(self):
            try:
                super().finish()
            finally:
                if getattr(self, "_final", False):
                    done.set()

    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as exc:
        print(json.dumps({"status": "not_run", "reason": f"cannot listen on 127.0.0.1:{port}: {exc}"}, ensure_ascii=False), file=out, flush=True)
        return 2
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(json.dumps({"status": "waiting", "url": url, "video": str(video), "timeout_s": timeout,
                      "note": "open the url for the user; this process exits with the notes when they press the send button"}, ensure_ascii=False), file=out, flush=True)
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    if open_browser:
        import webbrowser

        webbrowser.open(url)
    got = done.wait(timeout)
    httpd.shutdown()
    httpd.server_close()
    if not got:
        print(json.dumps({"status": "timeout", "reason": f"no notes sent within {timeout:.0f} s; serve again when the user is ready"}, ensure_ascii=False), file=out, flush=True)
        return 3
    if result.get("approved"):
        print(json.dumps({"status": "approved", "notes_json": str(out_dir / "notes.json"), "round": round_n, "lines": [],
                          "next": f"the user approved this draft with NO notes: write `APPROVED <date> (review page, round {round_n})` in hf/CHANGELOG.md "
                                  "and continue with render-qa-delivery (the final render if this was not it, every-frame QA on the final file)"},
                         ensure_ascii=False, indent=2), file=out, flush=True)
        return 0
    print(json.dumps({"status": "ok", "notes_json": str(out_dir / "notes.json"), "notes_md": str(out_dir / "notes.md"), "round": round_n,
                      "lines": [note_line(x) for x in result["notes"]],
                      "strips": {str(x["n"]): ",".join(f"{v:g}" for v in x["strip_times"]) for x in result["notes"] if x["strip_times"]},
                      "next": f"open '## Round {round_n}' in hf/CHANGELOG.md with these lines (the user's words, numbered), extract a strip per timed note "
                              f"(tools/sheet.py VIDEO -o _work/notes/r{round_n}_n<K>.jpg --times <strips[K]> --cols 9), then diagnose and classify"},
                     ensure_ascii=False, indent=2), file=out, flush=True)
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="__LANG__" dir="__DIR__"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
__UI_CSS__
header{display:flex;align-items:center;gap:12px;padding:14px 20px;border-bottom:1px solid var(--line);background:var(--surface)}
.brand{display:flex;flex-direction:column;min-width:0}
.eyebrow{font-size:.78rem;font-weight:600;letter-spacing:.04em;color:var(--pri-h)}
header h1{font-size:1.05rem;font-weight:600;margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chips{margin-inline-start:auto;display:flex;gap:8px}
.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--raised);border-radius:999px;padding:3px 12px;font-size:.84rem;color:var(--muted);white-space:nowrap}
.chip b{color:var(--fg);font-weight:600}
main{display:grid;grid-template-columns:minmax(0,1fr) 408px;gap:20px;padding:20px;max-width:1560px;margin:0 auto}
@media (max-width:980px){main{grid-template-columns:1fr;padding:12px}}
.monitor{position:relative;background:#000;border-radius:var(--r-lg);overflow:hidden;box-shadow:var(--shadow);border:1px solid var(--line)}
.monitor video{display:block;width:100%;max-height:calc(100dvh - 300px);min-height:220px;object-fit:contain;cursor:pointer;background:#000}
.tcchip{position:absolute;top:12px;left:12px;direction:ltr;display:flex;align-items:center;gap:8px;padding:5px 11px;border-radius:8px;
 background:rgba(5,8,17,.72);color:#E8EDF5;font:600 .86rem/1 var(--mono);letter-spacing:.04em;backdrop-filter:blur(8px);pointer-events:none}
.live{width:8px;height:8px;border-radius:50%;background:#64748B;transition:background-color .2s var(--ease)}
.playing .live{background:#22C55E;box-shadow:0 0 0 0 rgba(34,197,94,.6);animation:pulse 1.6s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(34,197,94,.55)}70%{box-shadow:0 0 0 8px rgba(34,197,94,0)}100%{box-shadow:0 0 0 0 rgba(34,197,94,0)}}
.timeline{margin-top:14px;user-select:none;touch-action:none}
.track{position:relative;height:40px;border-radius:10px;background:var(--surface);border:1px solid var(--line);cursor:pointer;overflow:visible}
.fill{position:absolute;inset-block:0;left:0;border-radius:10px 0 0 10px;background:linear-gradient(90deg,transparent,var(--pri-soft));pointer-events:none}
.band{position:absolute;top:7px;bottom:7px;background:var(--acc-soft);border:1px solid var(--acc);border-radius:6px;min-width:4px;cursor:pointer}
.dot{position:absolute;top:50%;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;background:var(--pri-h);border:3px solid var(--surface);padding:0;min-height:0;
 box-shadow:0 0 0 1px var(--pri-h)}
.dot:hover{transform:scale(1.2)}
.sel{position:absolute;top:2px;bottom:2px;background:var(--pri-soft);border:2px dashed var(--pri-h);border-radius:8px;pointer-events:none}
.head{position:absolute;top:-6px;bottom:-6px;width:2px;margin-left:-1px;background:var(--fg);pointer-events:none;border-radius:2px}
.head::before{content:"";position:absolute;top:-4px;left:-5px;border:6px solid transparent;border-top-color:var(--fg)}
.ruler{position:relative;height:22px;margin-top:4px;direction:ltr;pointer-events:none}
.tick{position:absolute;top:0;width:1px;height:6px;background:var(--line-strong)}
.tick.major{height:10px;background:var(--muted)}
.tick span{position:absolute;top:11px;left:0;transform:translateX(-50%);}
.tick.first span{transform:none}.tick.last span{transform:translateX(-100%)}
.tick span{font:500 .7rem/1 var(--mono);color:var(--muted);white-space:nowrap}
.transport{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:8px}
.play{width:48px;height:48px;border-radius:50%;padding:0;display:grid;place-items:center;background:var(--fg);color:var(--bg);border-color:var(--fg)}
.play .svg{fill:currentColor;stroke:none;width:22px;height:22px}
.clock{font:600 1.1rem/1 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:.02em}.clock span{color:var(--muted);font-weight:500}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--surface)}
.seg button{border:0;border-radius:0;background:transparent;font:500 .86rem/1 var(--mono);padding:0 13px;min-height:38px}
.seg button+button{border-inline-start:1px solid var(--line)}
.seg button:hover{background:var(--raised)}
.push{margin-inline-start:auto;display:flex;gap:6px}
.icon{width:40px;height:40px;padding:0;display:grid;place-items:center}
.keys{display:flex;flex-wrap:wrap;gap:6px 16px;margin:14px 0 0;color:var(--muted);font-size:.84rem}
.keys span{display:inline-flex;align-items:center;gap:6px}
aside{display:flex;flex-direction:column;gap:14px;position:sticky;top:16px;max-height:calc(100dvh - 110px);min-height:0}
@media (max-width:980px){aside{position:static;max-height:none}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:16px;box-shadow:var(--shadow)}
.ctitle{display:flex;align-items:center;gap:8px;font-weight:600;margin:0 0 12px}
.ctitle .svg{color:var(--pri-h)}
.range{display:grid;grid-template-columns:auto 1fr auto;gap:8px 10px;align-items:center}
.range label{color:var(--muted);font-size:.9rem;min-width:2.2em}
.tf{width:100%;min-width:0;border:1px solid var(--line);border-radius:10px;background:var(--sunken);padding:8px 10px;min-height:40px;
 font:600 .95rem/1 var(--mono);font-variant-numeric:tabular-nums;direction:ltr;text-align:center}
.tf::placeholder{font-family:var(--sans);font-weight:400;font-size:.85rem;color:var(--muted)}
.tf.bad{border-color:var(--warn)}
.mk{font-size:.88rem;white-space:nowrap;display:inline-flex;align-items:center;gap:8px}
.opts{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:12px 0 10px;flex-wrap:wrap}
.toggle{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:.9rem;cursor:pointer}
.toggle input{width:18px;height:18px;accent-color:var(--pri)}
.ghost{background:transparent;font-size:.86rem;min-height:34px;padding:4px 10px;color:var(--muted)}
textarea{width:100%;min-height:92px;resize:vertical;border:1px solid var(--line);border-radius:12px;background:var(--sunken);padding:12px;line-height:1.5}
textarea:focus{border-color:var(--pri)}
.row{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:10px}
.hint{color:var(--muted);font-size:.82rem;display:inline-flex;gap:4px;align-items:center}
.btn-acc{background:var(--raised);border-color:var(--pri);color:var(--pri-h);font-weight:600;padding:8px 18px}
.btn-acc:hover:not(:disabled){background:var(--pri-soft)}
.list{flex:1;min-height:150px;overflow:auto;padding:12px;overscroll-behavior:contain}
.listhead{display:flex;justify-content:space-between;align-items:center;padding:2px 4px 10px;font-weight:600}
.listhead span+span{color:var(--muted);font-weight:500;font-size:.88rem}
ol{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}
.note{display:grid;grid-template-columns:auto 1fr auto;gap:6px 10px;align-items:start;padding:12px;border-radius:12px;background:var(--raised);border:1px solid var(--line);
 transition:border-color .18s var(--ease),background-color .18s var(--ease);animation:in .28s var(--ease)}
@keyframes in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.note.active{border-color:var(--pri-h);background:var(--pri-soft)}
.num{font:600 .8rem/1 var(--mono);color:var(--muted);padding-top:9px}
.meta{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.time{font:600 .86rem/1 var(--mono);font-variant-numeric:tabular-nums;direction:ltr;min-height:32px;padding:0 10px;background:var(--sunken);border-color:var(--line-strong)}
.time.range-t{border-color:var(--acc);color:var(--acc)}.time.gen{font-family:var(--sans);color:var(--muted)}
.small{min-height:32px;padding:0 10px;font-size:.84rem;display:inline-flex;align-items:center;gap:6px}
.small .svg{width:14px;height:14px}
.txt{grid-column:2/3;margin:2px 0 0;white-space:pre-wrap;word-break:break-word;border-radius:6px;padding:2px 4px;cursor:text}
.txt:hover{background:var(--sunken)}
.del{grid-row:1/3;grid-column:3;width:36px;height:36px;padding:0;display:grid;place-items:center;background:transparent;border-color:transparent;color:var(--muted)}
.del:hover{color:var(--warn);border-color:var(--line)}
.empty{color:var(--muted);text-align:center;padding:22px 10px;margin:0;line-height:1.6}
.empty .svg{width:28px;height:28px;display:block;margin:0 auto 8px;color:var(--line-strong)}
.decide{padding:14px}
.decide h2{font-size:.95rem;margin:0 0 10px;font-weight:600}
.act{width:100%;display:flex;align-items:center;gap:12px;text-align:start;padding:12px 14px;min-height:60px;border-radius:12px}
.act+.act{margin-top:8px}
.act .svg{width:22px;height:22px}
.act b{display:block;font-size:1rem}.act small{display:block;font-size:.82rem;opacity:.85;font-weight:400}
.act.go{background:var(--pri);border-color:var(--pri);color:var(--pri-ink)}.act.go:hover:not(:disabled){background:var(--pri-h);border-color:var(--pri-h)}
.act.ok{background:var(--surface)}.act.ok:hover:not(:disabled){border-color:var(--ok);background:var(--ok-soft)}.act.ok .svg{color:var(--ok)}
#status{min-height:1.3em;font-size:.9rem;text-align:center;margin-top:8px}.okc{color:var(--ok)}.warnc{color:var(--warn)}
@media (max-width:980px){.decide{position:sticky;bottom:0;z-index:2}}
.done{position:fixed;inset:0;background:rgba(2,6,23,.78);display:none;place-items:center;z-index:9;padding:16px;backdrop-filter:blur(6px)}
.done.on{display:grid}.done>div{background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:32px 36px;text-align:center;max-width:440px;box-shadow:var(--shadow);animation:pop .35s var(--ease)}
@keyframes pop{from{opacity:0;transform:scale(.94)}to{opacity:1;transform:none}}
.done .svg{width:52px;height:52px;color:var(--ok);margin:0 auto}.done p{margin:14px 0 0;font-size:1.08rem}
</style></head><body>
<header><div class="brand"><span class="eyebrow">__U_eyebrow__</span><h1>__TITLE__</h1></div>
 <div class="chips"><span class="chip">__U_round__ <b>__ROUND__</b></span><span class="chip" id="badge"></span></div></header>
<main>
<section aria-label="video">
 <div class="monitor" id="player"><video id="v" src="/video" preload="auto" playsinline></video>
  <div class="tcchip" aria-hidden="true"><span class="live"></span><span id="tc">00:00:00:00</span></div></div>
 <div class="timeline" dir="ltr"><div class="track" id="track" title="__U_track_tip__"><div class="fill" id="fill"></div><div id="marks"></div><div class="sel" id="sel" hidden></div><div class="head" id="head"></div></div>
  <div class="ruler" id="ruler"></div></div>
 <div class="transport" dir="ltr">
  <button class="play" id="play" aria-label="__U_play__"><svg class="svg" id="i-play" viewBox="0 0 24 24"><path d="M7 4.5v15l12-7.5z"/></svg><svg class="svg" id="i-pause" viewBox="0 0 24 24" hidden><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg></button>
  <span class="clock"><b id="now">0:00.00</b> <span>/ <span id="dur">0:00.00</span></span></span>
  <div class="seg" role="group" aria-label="step"><button id="back1">__U_b1__</button><button id="prevf">__U_pf__</button><button id="nextf">__U_nf__</button><button id="fwd1">__U_f1__</button></div>
  <span class="push"><button class="icon" id="mute" aria-label="__U_mute__"><svg class="svg" viewBox="0 0 24 24"><path d="M11 5 6 9H3v6h3l5 4z"/><path id="i-wave" d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/><path id="i-x" d="m16 9 6 6M22 9l-6 6" hidden/></svg></button>
  <button class="icon" id="fs" aria-label="__U_fs__"><svg class="svg" viewBox="0 0 24 24"><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/></svg></button></span>
 </div>
 <p class="keys">__KEYS_HTML__</p>
</section>
<aside>
 <div class="card">
  <p class="ctitle"><svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>__U_new_note__</p>
  <div class="range">
   <label for="inF">__U_from__</label><input class="tf" id="inF" inputmode="decimal" autocomplete="off" placeholder="__U_now_ph__"><button class="mk" id="setIn">__U_set_in__ <kbd>I</kbd></button>
   <label for="outF">__U_to__</label><input class="tf" id="outF" inputmode="decimal" autocomplete="off" placeholder="__U_no_end__"><button class="mk" id="setOut">__U_set_out__ <kbd>O</kbd></button>
  </div>
  <div class="opts"><label class="toggle"><input type="checkbox" id="general"> __U_general__</label><button class="ghost" id="clr">__U_clear_range__</button></div>
  <textarea id="text" placeholder="__U_placeholder__"></textarea>
  <div class="row"><span class="hint"><kbd>Ctrl</kbd>+<kbd>Enter</kbd></span><button class="btn-acc" id="add">__U_add__</button></div>
 </div>
 <div class="card list"><div class="listhead"><span>__U_notes_title__</span><span id="count"></span></div><ol id="list"></ol>
  <p class="empty" id="empty"><svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>__U_empty__</p></div>
 <div class="card decide"><h2>__U_next_q__</h2>
  <button class="act go" id="send"><svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/></svg><span><b id="sendLabel">__U_send__</b><small>__U_send_hint__</small></span></button>
  <button class="act ok" id="approve"><svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg><span><b>__U_approve__</b><small>__U_approve_hint__</small></span></button>
  <div id="status" role="status" aria-live="polite"></div></div>
</aside>
</main>
<div class="done" id="done" role="dialog" aria-modal="true" aria-labelledby="doneMsg"><div><svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/></svg><p id="doneMsg"></p></div></div>
<script>
(function(){
var B=__DATA__, U=B.ui, $=function(s){return document.querySelector(s)}, v=$('#v'), notes=[], inT=null, outT=null, sent=false, stopAt=null, drag=null;
function tc(t){if(t==null)return U.all;var cs=Math.round(t*100),m=Math.floor(cs/6000),r=cs%6000;return m+':'+String(Math.floor(r/100)).padStart(2,'0')+'.'+String(r%100).padStart(2,'0')}
function smpte(t){var f=Math.round(t*B.fps),fps=Math.round(B.fps),p=function(n){return String(n).padStart(2,'0')};return p(Math.floor(f/(fps*3600)))+':'+p(Math.floor(f/(fps*60))%60)+':'+p(Math.floor(f/fps)%60)+':'+p(f%fps)}
function parse(s){s=String(s).trim().replace(',','.');if(!s)return null;var m=s.match(/^(?:(\d+):)?(\d+(?:\.\d+)?)$/);if(!m)return NaN;return (m[1]?+m[1]*60:0)+ +m[2]}
function dur(){return isFinite(v.duration)&&v.duration>0?v.duration:0}
function pct(t){var d=dur();return d?Math.max(0,Math.min(100,t/d*100)):0}
function load(){try{var s=localStorage.getItem(B.store);if(s)notes=JSON.parse(s)||[]}catch(e){}}
function save(){try{localStorage.setItem(B.store,JSON.stringify(notes))}catch(e){}}
function seek(t){v.currentTime=Math.max(0,Math.min(dur()||1e9,t))}
function step(d){v.pause();stopAt=null;seek(v.currentTime+d)}
function sorted(){return notes.slice().sort(function(a,b){return (a.t==null)-(b.t==null)||(a.t||0)-(b.t||0)})}
function st(msg,cls){var s=$('#status');s.textContent=msg;s.className=cls||''}
function ruler(){var r=$('#ruler'),d=dur();r.innerHTML='';if(!d)return;var steps=[1,2,5,10,15,30,60,120,300],s=steps[0];for(var i=0;i<steps.length;i++){s=steps[i];if(d/s<=24)break}
 for(var t=0;t<=d+1e-6;t+=s){var k=document.createElement('div'),major=Math.round(t/s)%5===0;k.className='tick'+(major?' major':'')+(t===0?' first':'')+(t+s>d+1e-6?' last':'');k.style.left=pct(t)+'%';
  if(major){var l=document.createElement('span');l.textContent=Math.floor(t/60)+':'+String(Math.round(t%60)).padStart(2,'0');k.appendChild(l)}r.appendChild(k)}}
function fields(){var g=$('#general').checked;$('#inF').value=inT==null?'':tc(inT);$('#outF').value=outT==null?'':tc(outT);
 ['#inF','#outF','#setIn','#setOut','#clr'].forEach(function(s){$(s).disabled=g});$('#inF').classList.remove('bad');$('#outF').classList.remove('bad');drawSel()}
function drawSel(){var s=$('#sel');if(inT==null||$('#general').checked){s.hidden=true;return}s.hidden=false;var a=pct(inT),b=outT==null?a:pct(outT);s.style.left=a+'%';s.style.width=Math.max(.6,b-a)+'%'}
function drawMarks(){var m=$('#marks');m.innerHTML='';sorted().forEach(function(n){if(n.t==null)return;var el;
 if(n.end!=null){el=document.createElement('div');el.className='band';el.style.left=pct(n.t)+'%';el.style.width=(pct(n.end)-pct(n.t))+'%'}
 else{el=document.createElement('button');el.className='dot';el.style.left=pct(n.t)+'%';el.setAttribute('aria-label',tc(n.t)+' '+n.text)}
 el.title=tc(n.t)+(n.end!=null?' – '+tc(n.end):'')+'  '+n.text;el.addEventListener('pointerdown',function(e){e.stopPropagation()});
 el.addEventListener('click',function(e){e.stopPropagation();v.pause();stopAt=null;seek(n.t)});m.appendChild(el)})}
function render(){var ol=$('#list');ol.innerHTML='';sorted().forEach(function(n,i){
 var li=document.createElement('li'),num=document.createElement('span'),meta=document.createElement('div'),t=document.createElement('button'),p=document.createElement('p'),x=document.createElement('button');
 li.className='note';li._n=n;num.className='num';num.textContent=String(i+1).padStart(2,'0');meta.className='meta';
 t.className='time'+(n.end!=null?' range-t':'')+(n.t==null?' gen':'');t.textContent=n.t==null?U.all:(n.end!=null?tc(n.t)+' – '+tc(n.end):tc(n.t));
 t.onclick=function(){if(n.t!=null){v.pause();stopAt=null;seek(n.t)}};meta.appendChild(t);
 if(n.end!=null){var pl=document.createElement('button');pl.className='small';pl.innerHTML='<svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4.5v15l12-7.5z"/></svg>';pl.appendChild(document.createTextNode(U.play_range));
  pl.onclick=function(){seek(n.t);stopAt=n.end;v.play()};meta.appendChild(pl)}
 p.className='txt';p.textContent=n.text;p.title=U.edit_tip;try{p.contentEditable='plaintext-only'}catch(e){p.contentEditable='true'}
 p.addEventListener('blur',function(){var s=p.textContent.trim();if(s){n.text=s;save();drawMarks()}else{p.textContent=n.text}});
 x.className='del';x.setAttribute('aria-label',U.del);x.title=U.del;x.innerHTML='<svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>';
 x.onclick=function(){notes.splice(notes.indexOf(n),1);save();render()};
 li.appendChild(num);li.appendChild(meta);li.appendChild(x);li.appendChild(p);ol.appendChild(li)});
 var c=notes.length;$('#empty').hidden=!!c;$('#count').textContent=c?c+' '+U.count:'';$('#badge').innerHTML='<b>'+c+'</b> '+U.count;
 $('#sendLabel').textContent=U.send+(c?' ('+c+')':'')+' ✓';$('#send').disabled=sent||!c;$('#approve').disabled=sent||!!c;$('#approve').title=c?U.has_notes:'';
 drawMarks();active()}
function active(){var ct=v.currentTime;document.querySelectorAll('.note').forEach(function(li){var n=li._n;li.classList.toggle('active',n.t!=null&&ct>=n.t-.3&&ct<=(n.end!=null?n.end:n.t)+.3)})}
function tick(){$('#fill').style.width=pct(v.currentTime)+'%';$('#head').style.left=pct(v.currentTime)+'%';$('#now').textContent=tc(v.currentTime);$('#dur').textContent=tc(dur());$('#tc').textContent=smpte(v.currentTime);
 if(stopAt!=null&&v.currentTime>=stopAt){v.pause();seek(stopAt);stopAt=null}active()}
function setIn(t){inT=t;if(outT!=null&&outT<=inT)outT=null;fields()}
function setOut(t){if(inT==null||t<=inT){if(inT!=null&&t<inT){outT=inT;inT=t}else{st(U.out_first,'warnc');return}}else outT=t;fields()}
function add(){var txt=$('#text').value.trim();if(!txt){$('#text').focus();return}var g=$('#general').checked;
 var t=g?null:(inT==null?v.currentTime:inT);notes.push({t:t==null?null:+t.toFixed(3),end:g||outT==null?null:+outT.toFixed(3),text:txt});
 $('#text').value='';inT=null;outT=null;$('#general').checked=false;fields();save();render();st('')}
function timeAt(e){var r=$('#track').getBoundingClientRect();return Math.max(0,Math.min(1,(e.clientX-r.left)/r.width))*dur()}
$('#track').addEventListener('pointerdown',function(e){if(!dur())return;$('#track').setPointerCapture(e.pointerId);stopAt=null;var t=timeAt(e);
 if(e.shiftKey){v.pause();drag={sel:true,a:t};inT=t;outT=null;fields()}else{drag={sel:false};seek(t)}});
$('#track').addEventListener('pointermove',function(e){if(!drag)return;var t=timeAt(e);if(drag.sel){if(t>drag.a){inT=drag.a;outT=t}else if(t<drag.a){inT=t;outT=drag.a}fields();seek(t)}else seek(t)});
$('#track').addEventListener('pointerup',function(){drag=null});
$('#inF').addEventListener('change',function(){var t=parse(this.value);if(t===null){inT=null;outT=null;fields();return}if(isNaN(t)||t>dur()){this.classList.add('bad');return}setIn(t);seek(t)});
$('#outF').addEventListener('change',function(){var t=parse(this.value);if(t===null){outT=null;fields();return}if(isNaN(t)||t>dur()||inT==null||t<=inT){this.classList.add('bad');st(U.out_first,'warnc');return}outT=t;fields();seek(t)});
$('#setIn').onclick=function(){v.pause();setIn(v.currentTime)};$('#setOut').onclick=function(){v.pause();setOut(v.currentTime)};
$('#clr').onclick=function(){inT=null;outT=null;fields()};$('#general').onchange=fields;$('#add').onclick=add;
$('#text').addEventListener('focus',function(){if(!v.paused)v.pause();if(inT==null&&!$('#general').checked)setIn(v.currentTime)});
$('#text').addEventListener('keydown',function(e){if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();add()}else if(e.key==='Escape'){this.blur()}});
function toggle(){stopAt=null;v.paused?v.play():v.pause()}
$('#play').onclick=toggle;v.addEventListener('click',toggle);
v.addEventListener('play',function(){$('#i-play').hidden=true;$('#i-pause').hidden=false;$('#player').classList.add('playing')});
v.addEventListener('pause',function(){$('#i-play').hidden=false;$('#i-pause').hidden=true;$('#player').classList.remove('playing')});
$('#mute').onclick=function(){v.muted=!v.muted;$('#i-wave').hidden=v.muted;$('#i-x').hidden=!v.muted};
$('#fs').onclick=function(){var p=$('#player');if(document.fullscreenElement)document.exitFullscreen();else if(p.requestFullscreen)p.requestFullscreen()};
$('#back1').onclick=function(){step(-1)};$('#fwd1').onclick=function(){step(1)};$('#prevf').onclick=function(){step(-1/B.fps)};$('#nextf').onclick=function(){step(1/B.fps)};
['timeupdate','seeked','loadedmetadata','durationchange'].forEach(function(ev){v.addEventListener(ev,tick)});v.addEventListener('loadedmetadata',function(){ruler();drawMarks();drawSel()});
window.addEventListener('resize',function(){ruler()});
document.addEventListener('keydown',function(e){var tg=e.target.tagName;if(tg==='TEXTAREA'||tg==='INPUT'||e.target.isContentEditable||e.ctrlKey||e.metaKey||e.altKey)return;var k=e.key.toLowerCase();
 if(k===' '||k==='k'){e.preventDefault();toggle()}else if(k==='j'){step(-1)}else if(k==='l'){step(1)}
 else if(k===','||k==='arrowleft'){e.preventDefault();step(-1/B.fps)}else if(k==='.'||k==='arrowright'){e.preventDefault();step(1/B.fps)}
 else if(k==='i'){v.pause();setIn(v.currentTime)}else if(k==='o'){v.pause();setOut(v.currentTime)}else if(k==='x'){inT=null;outT=null;fields()}
 else if(k==='n'){e.preventDefault();v.pause();if(inT==null)setIn(v.currentTime);$('#text').focus()}});
function post(body,okMsg){var x=new XMLHttpRequest();st(U.sending);$('#send').disabled=true;$('#approve').disabled=true;x.open('POST','/notes');x.setRequestHeader('Content-Type','application/json');x.setRequestHeader('X-Board-Token',B.token);
 x.onload=function(){var r={};try{r=JSON.parse(x.responseText)}catch(e){}if(x.status===200){sent=true;st(okMsg,'okc');try{localStorage.removeItem(B.store)}catch(e){}$('#doneMsg').textContent=okMsg;$('#done').classList.add('on');v.pause()}
  else{st(U.fail+((r.errors||[]).join('; ')||x.status),'warnc');render()}};
 x.onerror=function(){st(U.fail+'offline','warnc');render()};x.send(JSON.stringify(body))}
$('#send').onclick=function(){if(!notes.length){st(U.none,'warnc');return}post({duration:dur()||null,notes:notes},U.sent)};
$('#approve').onclick=function(){if(notes.length)return;if(!confirm(U.approve_q))return;post({duration:dur()||null,approved:true,notes:[]},U.approved)};
load();render();fields();tick();
})();
</script></body></html>
"""


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        import subprocess

        return subprocess.call([sys.executable, str(Path(__file__).with_name("test_notes_board.py"))])
    if len(argv) >= 2 and argv[0] == "serve":
        video, opts, i = Path(argv[1]), {"--out": None, "--round": "1", "--lang": "he", "--fps": "30", "--port": "0", "--timeout": "3600"}, 2
        open_b = False
        while i < len(argv):
            if argv[i] == "--open":
                open_b, i = True, i + 1
            elif argv[i] in opts and i + 1 < len(argv):
                opts[argv[i]], i = argv[i + 1], i + 2
            else:
                print("unknown option", argv[i], file=sys.stderr)
                return 2
        if not opts["--out"]:
            print("serve needs --out DIR (for example _work/notes)", file=sys.stderr)
            return 2
        if opts["--lang"] not in UI:
            print("--lang must be he or en", file=sys.stderr)
            return 2
        return serve(video, Path(opts["--out"]), int(opts["--round"]), opts["--lang"], float(opts["--fps"]), int(opts["--port"]), float(opts["--timeout"]), open_b)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

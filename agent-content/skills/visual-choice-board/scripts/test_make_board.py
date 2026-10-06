#!/usr/bin/env python3
"""Tests for make_board.py (stdlib unittest, no network, no browser needed).

Usage:
  python test_make_board.py            # run all tests
  python make_board.py --self-check    # same thing

What is proven here: a sample spec builds; every option and a "none" slot is present; the page loads no remote
resource; user text is escaped; Hebrew + RTL markers are present; limits (2-12 options, placeholder text, banned
animations, unlicensed embedded fonts) are refused; the inline script parses (when node is on PATH); the board id
is deterministic; `verify` accepts a good choices.json and rejects a wrong board, an unknown option, a missing
decision and 'none' without a comment. NOT proven: that the page looks right or that keyboard interaction works in
a real browser (do the browser checklist in references/browser-checklist.md).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_board as mb  # noqa: E402

SAMPLE = HERE.parent / "references" / "sample-spec.json"
BUILT = "2026-10-02T12:00:00Z"


def load_sample() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


class BoardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_spec(self, spec: dict, name: str = "spec.json") -> Path:
        p = self.dir / name
        p.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        return p

    def build(self, spec: dict, out: str = "out") -> tuple[dict, str, dict]:
        res = mb.build(self.write_spec(spec), self.dir / out, BUILT)
        page = Path(res["html"]).read_text(encoding="utf-8")
        man = json.loads(Path(res["manifest"]).read_text(encoding="utf-8"))
        return res, page, man

    # ---- build ----
    def test_sample_builds_with_every_option_and_none(self) -> None:
        spec = load_sample()
        res, page, man = self.build(spec)
        total = sum(len(d["options"]) for d in spec["decisions"])
        self.assertEqual(len(re.findall(r'class="pick" role="radio"[^>]*data-opt="(?!none")', page)), total)
        self.assertEqual(page.count('data-opt="none"'), len(spec["decisions"]))
        self.assertEqual(res["options"], total)
        for d in spec["decisions"]:
            self.assertIn(f'id="panel-{d["id"]}"', page)
            self.assertIn(f'id="tab-{d["id"]}"', page)

    def test_all_kinds_render(self) -> None:
        spec = load_sample()
        spec["decisions"].append({"id": "hook", "title": "Hook", "kind": "text", "options": [
            {"id": "A", "label": "A", "text": "הכותרת הראשונה שלי"}, {"id": "B", "label": "B", "text": "הכותרת השנייה שלי"}]})
        for n in ("a1", "a2", "b1"):
            (self.dir / f"{n}.jpg").write_bytes(b"\xff\xd8\xff\xe0" + n.encode() * 20)
        spec["decisions"].append({"id": "style", "title": "Style", "kind": "image", "options": [
            {"id": "A", "label": "Faithful", "images": ["a1.jpg", "a2.jpg"], "caption": "the reference's own rhythm"},
            {"id": "B", "label": "Twist", "images": ["b1.jpg"]}]})
        res, page, man = self.build(spec)
        self.assertIn("הכותרת הראשונה שלי", page)
        self.assertEqual(page.count('class="optimg"'), 3)
        self.assertIn("the reference&#x27;s own rhythm", page.replace("&#39;", "&#x27;"))
        self.assertEqual({d["kind"] for d in spec["decisions"]}, mb.KINDS)
        self.assertEqual(mb.remote_hits(page), [])

    def test_image_options_are_limited_and_change_the_board_id(self) -> None:
        (self.dir / "x.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"x" * 40)
        spec = load_sample()
        spec["decisions"] = [{"id": "pick", "title": "Pick", "kind": "image", "options": [
            {"id": "A", "label": "A", "images": ["x.jpg"]}, {"id": "B", "label": "B", "images": ["x.jpg"]}]}]
        id1 = self.build(spec, "o1")[2]["board_id"]
        (self.dir / "x.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"y" * 40)
        self.assertNotEqual(id1, self.build(spec, "o2")[2]["board_id"])  # new pixels = a new board
        for bad in ([], ["x.jpg"] * 5, ["missing.jpg"], ["x.txt"]):
            spec["decisions"][0]["options"][0]["images"] = bad
            with self.assertRaises(mb.SpecError):
                mb.validate(json.loads(json.dumps(spec)), self.dir)

    def test_no_remote_resources_and_no_network_code(self) -> None:
        _, page, _ = self.build(load_sample())
        self.assertEqual(mb.remote_hits(page), [])
        self.assertNotRegex(page, r"https?://")
        self.assertNotRegex(page, r"(?i)\bfetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon")

    def test_rtl_and_hebrew_markers(self) -> None:
        _, page, _ = self.build(load_sample())
        self.assertIn('<html lang="he">', page)
        self.assertIn('id="app" dir="rtl"', page)
        self.assertIn('dir="auto"', page)
        self.assertIn("לא לבזבז את ה-1,990 ₪ שלך", page)
        self.assertIn('<meta charset="utf-8">', page)
        self.assertIn('<bdi dir="ltr">1-9, 0, q, w</bdi>', page)  # key hints isolated from the Hebrew sentence
        en = load_sample()
        en["lang"] = "en"
        en["title"] = "Look board"
        _, page_en, _ = self.build(en, "out_en")
        self.assertIn('id="app" dir="ltr"', page_en)

    def test_hostile_text_is_escaped(self) -> None:
        spec = load_sample()
        spec["text"] = '<img src=x onerror=alert(1)> "quoted" </script><script>alert(2)</script> & {x}'
        _, page, _ = self.build(spec)
        m = re.search(r'<script type="application/json" id="board-data">(.*?)</script>', page, re.S)
        data, body = m.group(1), page.replace(m.group(0), "")
        # visible HTML: escaped, nothing executable
        self.assertNotIn("<img src=x onerror", body)
        self.assertNotIn("<script>alert(2)", body)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", body)
        self.assertIn("&amp; {x}", body)
        # JSON data block: inert, cannot close its script element or open a comment
        self.assertNotIn("</", data)
        self.assertNotIn("<!--", data)
        self.assertEqual(json.loads(data)["text"], spec["text"])
        self.assertEqual(body.count("</script>"), 1)  # only the main script's closing tag remains

    def test_lookalike_specimen(self) -> None:
        self.assertEqual(mb.lookalike_letters("לבזבז"), ["ז"])
        self.assertEqual(sorted(mb.lookalike_letters("דרוחה")), sorted(["ד", "ר", "ו", "ה", "ח"]))
        _, page, _ = self.build(load_sample())
        self.assertIn('class="kw"', page)
        self.assertIn("ו ז", page)
        self.assertIn("ד ר", page)
        self.assertIn("ה ח", page)

    def test_contrast_and_safe_zone_flags(self) -> None:
        self.assertEqual(mb.contrast("#000000", "#ffffff"), 21.0)
        self.assertLess(mb.contrast("#777777", "#808080"), 3)
        spec = load_sample()
        spec["decisions"][2]["options"][2]["colors"] = {"bg": "#777777", "text": "#808080", "accent": "#999999"}
        _, page, _ = self.build(spec)
        self.assertIn('class="warn"', page)  # low contrast flag
        self.assertIn("outside the safe zone".split()[0], "outside")  # sanity
        self.assertIn("מחוץ לאזור הבטוח", page)  # layout option at 78%

    def test_font_embedding_is_hashed_and_needs_licence(self) -> None:
        font = self.dir / "fake.ttf"
        font.write_bytes(b"\x00\x01\x00\x00fake-font-bytes")
        spec = load_sample()
        spec["decisions"][0]["options"][0]["font_file"] = "fake.ttf"
        with self.assertRaises(mb.SpecError):
            mb.validate(json.loads(json.dumps(spec)), self.dir)
        spec["decisions"][0]["options"][0]["license"] = "OFL-1.1, notice text here"
        _, page, man = self.build(spec)
        self.assertIn("data:font/ttf;base64,", page)
        self.assertEqual(len(man["assets"]["fonts"]), 1)
        self.assertEqual(len(man["assets"]["fonts"][0]["sha256"]), 64)
        self.assertEqual(mb.remote_hits(page), [])

    def test_limits_are_enforced(self) -> None:
        base = load_sample()
        too_many = json.loads(json.dumps(base))
        too_many["decisions"][1]["options"] = [{"id": f"o{i}", "label": str(i), "anim": "rise"} for i in range(13)]
        with self.assertRaises(mb.SpecError):
            mb.validate(too_many, self.dir)
        one = json.loads(json.dumps(base))
        one["decisions"][1]["options"] = one["decisions"][1]["options"][:1]
        with self.assertRaises(mb.SpecError):
            mb.validate(one, self.dir)
        lorem = json.loads(json.dumps(base))
        lorem["text"] = "Lorem ipsum dolor sit amet"
        with self.assertRaises(mb.SpecError):
            mb.validate(lorem, self.dir)
        banned = json.loads(json.dumps(base))
        banned["decisions"][1]["options"][0]["anim"] = "bounce"
        with self.assertRaises(mb.SpecError):
            mb.validate(banned, self.dir)
        xfade = json.loads(json.dumps(base))
        xfade["decisions"][5]["options"][0]["trans"] = "crossfade"
        with self.assertRaises(mb.SpecError):
            mb.validate(xfade, self.dir)
        reserved = json.loads(json.dumps(base))
        reserved["decisions"][1]["options"][0]["id"] = "none"
        with self.assertRaises(mb.SpecError):
            mb.validate(reserved, self.dir)
        bad_family = json.loads(json.dumps(base))
        bad_family["decisions"][0]["options"][0]["family"] = 'x"};body{display:none'
        with self.assertRaises(mb.SpecError):
            mb.validate(bad_family, self.dir)

    def test_board_id_is_deterministic_and_changes_with_content(self) -> None:
        a, _, _ = self.build(load_sample(), "a")
        b, _, _ = self.build(load_sample(), "b")
        self.assertEqual(a["board_id"], b["board_id"])
        spec = load_sample()
        spec["text"] += "!"
        c, _, _ = self.build(spec, "c")
        self.assertNotEqual(a["board_id"], c["board_id"])

    def test_inline_script_parses(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("node not on PATH")
        _, page, _ = self.build(load_sample())
        scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
        self.assertEqual(len(scripts), 1)
        js = self.dir / "board.js"
        js.write_text(scripts[0], encoding="utf-8")
        r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = re.search(r'<script type="application/json" id="board-data">(.*?)</script>', page, re.S).group(1)
        self.assertEqual(json.loads(data)["schema_version"], 1)

    # ---- verify ----
    def choices(self, man: dict, **over) -> dict:
        ch = {"schema_version": 1, "board_id": man["board_id"], "project": man["project"], "sample_text": "x",
              "session_elapsed_ms": 1234, "assets": man["assets"],
              "decisions": {did: {"choice": next(iter(d["options"])), "none": False, "comment": "", "rejected": []}
                            for did, d in man["decisions"].items()}}
        ch.update(over)
        return ch

    def run_verify(self, man: dict, ch: dict) -> tuple[int, dict]:
        (self.dir / "m.json").write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
        (self.dir / "c.json").write_text(json.dumps(ch, ensure_ascii=False), encoding="utf-8")
        return mb.verify(self.dir / "m.json", self.dir / "c.json")

    def test_verify_accepts_a_good_readback(self) -> None:
        _, _, man = self.build(load_sample())
        code, res = self.run_verify(man, self.choices(man))
        self.assertEqual(code, 0, res)
        self.assertEqual(len(res["decision_lines"]), len(man["decisions"]))
        self.assertTrue(res["decision_lines"][0].startswith("font = Arial 800 (option A)"))

    def test_verify_rejects_bad_readbacks(self) -> None:
        _, _, man = self.build(load_sample())
        code, _ = self.run_verify(man, self.choices(man, board_id="deadbeefdeadbeef"))
        self.assertEqual(code, 1)
        ch = self.choices(man)
        ch["decisions"]["font"]["choice"] = "Z"
        self.assertEqual(self.run_verify(man, ch)[0], 1)
        ch = self.choices(man)
        del ch["decisions"]["anim"]
        self.assertEqual(self.run_verify(man, ch)[0], 1)
        ch = self.choices(man)
        ch["decisions"]["font"] = {"choice": None, "none": True, "comment": "", "rejected": []}
        self.assertEqual(self.run_verify(man, ch)[0], 1)
        ch["decisions"]["font"]["comment"] = "I want a rounder face"
        code, res = self.run_verify(man, ch)
        self.assertEqual(code, 0)
        self.assertIn("NONE of these", res["decision_lines"][0])
        ch = self.choices(man)
        ch["decisions"]["font"]["rejected"] = ["A"]
        self.assertEqual(self.run_verify(man, ch)[0], 1)
        self.assertEqual(mb.verify(self.dir / "nope.json", self.dir / "c.json")[0], 2)


    # ---- serve (the confirm button hands the picks to the agent: no export) ----
    def start_server(self, timeout: float = 20.0):
        import io
        import threading
        import time

        _, _, man = self.build(load_sample())
        out = io.StringIO()
        box = {}
        th = threading.Thread(target=lambda: box.setdefault("code", mb.serve(self.dir / "out", 0, timeout, False, out)), daemon=True)
        th.start()
        for _ in range(1500):  # up to 30 s: a cold CI runner can be slow to start the server
            if '"url"' in out.getvalue():
                break
            time.sleep(0.02)
        self.assertIn('"url"', out.getvalue(), f"the server printed no url within 30 s: {out.getvalue()!r}")
        url = json.loads(out.getvalue().splitlines()[0])["url"]
        return man, url, out, th, box

    def http(self, url, data=None, headers=None):
        import urllib.error
        import urllib.request

        req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read().decode("utf-8"), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8"), dict(e.headers)

    def test_serve_confirm_hands_the_picks_over_and_exits(self) -> None:
        man, url, out, th, box = self.start_server()
        code, page, hdr = self.http(url)
        self.assertEqual(code, 200)
        self.assertIn("window.__boardSend", page)
        self.assertIn("connect-src 'self'", hdr.get("Content-Security-Policy", ""))
        token = re.search(r"X-Board-Token',(\"[^\"]+\")", page)
        self.assertIsNotNone(token)
        token = json.loads(token.group(1))
        good = json.dumps(self.choices(man), ensure_ascii=False).encode("utf-8")
        # no token, wrong origin: refused, and the server keeps waiting
        self.assertEqual(self.http(url + "choices", good, {"Content-Type": "application/json"})[0], 403)
        self.assertEqual(self.http(url + "choices", good, {"X-Board-Token": token, "Origin": "https://evil.example"})[0], 403)
        # a bad pick: the errors go back to the page, nothing is written, still waiting
        bad = self.choices(man)
        bad["decisions"]["font"]["choice"] = "Z"
        code, body, _ = self.http(url + "choices", json.dumps(bad).encode("utf-8"), {"X-Board-Token": token})
        self.assertEqual(code, 400)
        self.assertIn("not an option", body)
        self.assertFalse((self.dir / "out" / "choices.json").exists())
        self.assertTrue(th.is_alive())
        # the confirm: accepted, written, printed, server exits 0
        code, body, _ = self.http(url + "choices", good, {"X-Board-Token": token, "Origin": url.rstrip("/")})
        self.assertEqual(code, 200)
        th.join(10)
        self.assertEqual(box.get("code"), 0)
        self.assertTrue((self.dir / "out" / "choices.json").is_file())
        final = json.loads(out.getvalue().split("\n", 1)[1])
        self.assertEqual(final["status"], "ok")
        self.assertTrue(final["decision_lines"][0].startswith("font = Arial 800 (option A)"))

    def test_served_page_keeps_the_file_on_disk_network_free(self) -> None:
        res, page, _ = self.build(load_sample())
        self.assertNotIn("__boardSend =", page.replace("window.__boardSend === 'function'", ""))
        self.assertEqual(mb.remote_hits(page), [])
        self.assertIn("אישור הבחירה ✓", page)

    def test_serve_times_out_without_a_pick_and_refuses_an_unbuilt_folder(self) -> None:
        import io

        _, _, _ = self.build(load_sample())
        out = io.StringIO()
        self.assertEqual(mb.serve(self.dir / "out", 0, 0.3, False, out), 3)
        self.assertIn('"timeout"', out.getvalue())
        self.assertEqual(mb.serve(self.dir / "empty", 0, 0.3, False, io.StringIO()), 2)

if __name__ == "__main__":
    unittest.main(verbosity=1)

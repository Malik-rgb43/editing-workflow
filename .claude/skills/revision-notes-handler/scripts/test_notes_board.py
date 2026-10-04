#!/usr/bin/env python3
"""Tests for notes_board.py (stdlib unittest; run directly or through `notes_board.py --self-check`)."""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notes_board as nb  # noqa: E402


class PureTests(unittest.TestCase):
    def test_timecode(self) -> None:
        self.assertEqual(nb.tc(0), "0:00.00")
        self.assertEqual(nb.tc(12.3), "0:12.30")
        self.assertEqual(nb.tc(75.456), "1:15.46")
        self.assertEqual(nb.tc(None), "general")

    def test_validate_sorts_numbers_and_keeps_general_notes_last(self) -> None:
        notes, errors = nb.validate({"notes": [{"t": None, "text": "המוזיקה חזקה מדי"}, {"t": 12.3, "end": None, "text": " הכתובית מאוחרת "},
                                               {"t": 3.0, "end": 5.5, "text": "משעמם"}]}, duration=30.0)
        self.assertEqual(errors, [])
        self.assertEqual([(n["n"], n["t"], n["tc"]) for n in notes], [(1, 3.0, "0:03.00-0:05.50"), (2, 12.3, "0:12.30"), (3, None, "general")])
        self.assertEqual(notes[1]["text"], "הכתובית מאוחרת")
        self.assertEqual(nb.note_line(notes[0]), '1. "משעמם" @ 0:03.00-0:05.50')

    def test_validate_refuses_bad_notes_without_partial_results(self) -> None:
        for body, needle in (({}, "body must be"), ({"notes": []}, "no notes"), ({"notes": [{"t": 1, "text": "  "}]}, "empty text"),
                             ({"notes": [{"t": -1, "text": "x"}]}, "not a time"), ({"notes": [{"t": 99, "text": "x"}]}, "not a time"),
                             ({"notes": [{"t": True, "text": "x"}]}, "not a time"), ({"notes": [{"t": 5, "end": 4, "text": "x"}]}, "not after"),
                             ({"notes": [{"t": None, "end": 4, "text": "x"}]}, "end without a start"),
                             ({"notes": [{"t": 1, "text": "x" * (nb.MAX_TEXT + 1)}]}, "longer than")):
            notes, errors = nb.validate(body, duration=30.0)
            self.assertEqual(notes, [], body)
            self.assertTrue(any(needle in e for e in errors), (body, errors))

    def test_strip_times_cover_the_rule_window(self) -> None:
        s = nb.strip_times(10.0, None, 30.0)
        self.assertEqual((s[0], s[-1], len(s)), (9.0, 11.0, 9))
        s = nb.strip_times(0.2, None, 30.0)
        self.assertEqual(s[0], 0.0)
        r = nb.strip_times(4.0, 8.0, 30.0)
        self.assertEqual((r[0], r[-1]), (3.5, 8.5))
        self.assertEqual(nb.strip_times(None, None, 30.0), [])

    def test_page_is_offline_and_escapes_the_title(self) -> None:
        p = nb.page("he", 30.0, "<b>x</b>", "tok", "v.mp4")
        self.assertIn('dir="rtl"', p)
        self.assertNotIn("<b>x</b>", p)
        self.assertNotRegex(p, r"(?i)(src|href)\s*=\s*[\"']https?:")
        self.assertNotIn("__", p.replace("__DATA__", "").split("<script>")[0])


class ServeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="notes 'הערות' "))
        self.video = self.dir / "טיוטה 1.mp4"
        self.video.write_bytes(bytes(range(256)) * 40)  # 10,240 bytes; the server never decodes it

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def start(self, timeout=20.0):
        out, box = io.StringIO(), {}
        th = threading.Thread(target=lambda: box.setdefault("code", nb.serve(self.video, self.dir / "notes", 2, "he", 30.0, 0, timeout, False, out)), daemon=True)
        th.start()
        for _ in range(1500):  # up to 30 s: a cold CI runner can be slow to start the server
            if '"url"' in out.getvalue():
                break
            time.sleep(0.02)
        self.assertIn('"url"', out.getvalue(), f"the server printed no url within 30 s: {out.getvalue()!r}")
        url = json.loads(out.getvalue().splitlines()[0])["url"]
        return url, out, th, box

    def http(self, url, data=None, headers=None):
        req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def test_send_hands_the_notes_over_and_exits(self) -> None:
        url, out, th, box = self.start()
        code, page, hdr = self.http(url)
        self.assertEqual(code, 200)
        self.assertIn("connect-src 'self'", hdr["Content-Security-Policy"])
        token = json.loads(page.decode("utf-8").split("var B=", 1)[1].split(", U=B.ui", 1)[0])["token"]
        # range requests: the browser seeks with them
        code, part, hdr = self.http(url + "video", headers={"Range": "bytes=100-199"})
        self.assertEqual((code, len(part), hdr["Content-Range"]), (206, 100, "bytes 100-199/10240"))
        self.assertEqual(part, self.video.read_bytes()[100:200])
        code, part, _ = self.http(url + "video", headers={"Range": "bytes=-16"})
        self.assertEqual((code, part), (206, self.video.read_bytes()[-16:]))
        self.assertEqual(self.http(url + "video", headers={"Range": "bytes=99999-"})[0], 416)
        self.assertEqual(self.http(url + "video")[0], 200)
        # guards
        good = json.dumps({"duration": 30.0, "notes": [{"t": 12.3, "text": "הכתובית מאוחרת"}, {"t": None, "text": "מוזיקה חזקה"}]}).encode("utf-8")
        hdrs = {"Content-Type": "application/json", "X-Board-Token": token}
        self.assertEqual(self.http(url + "notes", good, {"Content-Type": "application/json"})[0], 403)
        self.assertEqual(self.http(url + "notes", good, {**hdrs, "Origin": "http://evil.example"})[0], 403)
        code, body, _ = self.http(url + "notes", json.dumps({"notes": [{"t": 50, "text": "x"}], "duration": 30}).encode(), hdrs)
        self.assertEqual(code, 400)
        self.assertIn("not a time", body.decode("utf-8"))
        self.assertTrue(th.is_alive())  # a bad send keeps the server waiting
        code, body, _ = self.http(url + "notes", good, hdrs)
        self.assertEqual(code, 200)
        th.join(10)
        self.assertEqual(box.get("code"), 0)
        res = json.loads(out.getvalue().split("\n", 1)[1])
        self.assertEqual(res["lines"], ['1. "הכתובית מאוחרת" @ 0:12.30', '2. "מוזיקה חזקה" @ general'])
        self.assertTrue(res["strips"]["1"].startswith("11.3,11.55,"), res["strips"])
        doc = json.loads((self.dir / "notes" / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual((doc["round"], len(doc["notes"]), doc["video_bytes"]), (2, 2, 10240))
        self.assertIn("## Round 2", (self.dir / "notes" / "notes.md").read_text(encoding="utf-8"))

    def test_approve_without_notes_exits_approved_and_refuses_notes_with_an_approval(self) -> None:
        url, out, th, box = self.start()
        page = self.http(url)[1].decode("utf-8")
        self.assertIn("מאשר, אין הערות ✓", page)
        self.assertIn("−1 frame", page)
        self.assertIn("סמן התחלה", page)
        self.assertNotIn("__U_", page)
        token = json.loads(page.split("var B=", 1)[1].split(", U=B.ui", 1)[0])["token"]
        hdrs = {"Content-Type": "application/json", "X-Board-Token": token}
        bad = json.dumps({"approved": True, "notes": [{"t": 1, "text": "x"}]}).encode("utf-8")
        code, body, _ = self.http(url + "notes", bad, hdrs)
        self.assertEqual(code, 400)
        self.assertIn("approval carries no notes", body.decode("utf-8"))
        self.assertTrue(th.is_alive())
        self.assertEqual(self.http(url + "notes", json.dumps({"approved": True, "notes": [], "duration": 20}).encode(), hdrs)[0], 200)
        th.join(10)
        self.assertEqual(box.get("code"), 0)
        res = json.loads(out.getvalue().split("\n", 1)[1])
        self.assertEqual((res["status"], res["lines"]), ("approved", []))
        doc = json.loads((self.dir / "notes" / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual((doc["approved"], doc["notes"]), (True, []))
        self.assertIn("APPROVED", (self.dir / "notes" / "notes.md").read_text(encoding="utf-8"))

    def test_timeout_and_missing_video(self) -> None:
        out = io.StringIO()
        self.assertEqual(nb.serve(self.video, self.dir / "n", timeout=0.2, out=out), 3)
        self.assertIn('"timeout"', out.getvalue())
        self.assertFalse((self.dir / "n" / "notes.json").exists())
        self.assertEqual(nb.serve(self.dir / "absent.mp4", self.dir / "n", out=io.StringIO()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)

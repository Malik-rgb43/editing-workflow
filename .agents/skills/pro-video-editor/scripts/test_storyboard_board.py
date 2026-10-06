#!/usr/bin/env python3
"""Tests for storyboard_board.py (stdlib unittest; run directly or through `storyboard_board.py --self-check`)."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import storyboard_board as sb  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


def make_spec(d: Path, **over) -> Path:
    (d / "frames").mkdir(parents=True, exist_ok=True)
    for n in ("b1", "b2", "ref"):
        (d / "frames" / f"{n}.jpg").write_bytes(JPEG)
    spec = {"title": "השף - רילס השקה", "project": "chef_reel", "lang": "he", "aspect": "9:16",
            "story": "שף שפתח מסעדה מראה שכל מנה נבנית מול העיניים",
            "mood": {"feel": "חם, קרוב, אש וברזל", "palette": ["#1C1917", "#F5F0E8", "#D4A72C"], "type": {"family": "Rubik", "sample": "כל מנה נבנית מול העיניים"},
                     "signature": "כרטיס הזמנה שנחתם על כל מנה", "refs": [{"img": "frames/ref.jpg", "caption": "האור הצהוב מהצד"}]},
            "beats": [{"id": "b1", "t": 0.0, "end": 2.5, "roll": "A", "source": "own", "img": "frames/b1.jpg", "line": "פתחתי מסעדה",
                       "shows": "השף מול המצלמה, קרוב", "move": "push 1.00->1.04", "why": "הפנים הן ההבטחה"},
                      {"id": "b2", "t": 2.5, "end": 4.0, "roll": "B", "source": "own", "img": "frames/b2.jpg", "line": "כל מנה",
                       "shows": "ידיים מניחות עלה על הצלחת", "why": "מראה את המשפט"},
                      {"id": "b3", "t": 4.0, "end": 6.0, "roll": "G", "source": "sketch", "line": "נבנית מול העיניים",
                       "shows": "כרטיס הזמנה נחתם", "why": "המכשיר החתימתי"}]}
    for k, v in over.items():
        spec[k] = v
    p = d / "storyboard.json"
    p.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return p


class PureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="sb 'בורד' "))

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_good_spec_passes_with_a_summary(self) -> None:
        p = make_spec(self.dir)
        errors, warnings = sb.validate(sb.load(p), p.parent)
        self.assertEqual(errors, [])
        s = sb.summary(sb.load(p))
        self.assertEqual((s["beats"], s["rolls"], s["planned_without_frame"]), (3, {"A": 1, "B": 1, "G": 1}, ["b3"]))

    def test_honesty_rules_refuse(self) -> None:
        base = json.loads(make_spec(self.dir).read_text(encoding="utf-8"))
        cases = [
            ({"roll": "A", "source": "stock"}, "own footage"),
            ({"img": None}, "real frame"),  # A-roll without its frame
            ({"img": "frames/missing.jpg"}, "no image"),
            ({"shows": "lorem ipsum"}, "placeholder"),
            ({"why": ""}, "`why` is required"),
            ({"t": 3, "end": 2}, "t` < `end"),
        ]
        for patch, needle in cases:
            sp = json.loads(json.dumps(base))
            sp["beats"][0].update(patch)
            errors, _ = sb.validate(sp, self.dir)
            self.assertTrue(any(needle in e for e in errors), (patch, errors))
        sp = json.loads(json.dumps(base))
        sp["beats"][1] = {**sp["beats"][1], "img": None, "source": "stock"}
        self.assertTrue(any("only a `sketch`" in e for e in sb.validate(sp, self.dir)[0]))
        sp = json.loads(json.dumps(base))
        sp["beats"][2] = {**sp["beats"][2], "source": "generated"}
        self.assertTrue(any("states its `cost`" in e for e in sb.validate(sp, self.dir)[0]))
        sp = json.loads(json.dumps(base))
        sp["mood"]["palette"] = ["red"]
        self.assertTrue(any("palette" in e for e in sb.validate(sp, self.dir)[0]))
        sp = json.loads(json.dumps(base))
        sp["beats"] = sp["beats"][:2]
        self.assertTrue(any("3-" in e for e in sb.validate(sp, self.dir)[0]))

    def test_a_plain_edit_is_warned_that_it_needs_no_board(self) -> None:
        p = make_spec(self.dir)
        sp = sb.load(p)
        for b in sp["beats"]:
            b.update({"roll": "A", "source": "own", "img": "frames/b1.jpg"})
        errors, warnings = sb.validate(sp, p.parent)
        self.assertEqual(errors, [])
        self.assertTrue(any("does not need this board" in w for w in warnings))

    def test_review_validation(self) -> None:
        ids = ["b1", "b2", "b3"]
        r, e = sb.validate_review({"approved": True, "notes": {}, "general": ""}, ids)
        self.assertEqual((e, r["approved"]), ([], True))
        r, e = sb.validate_review({"approved": False, "notes": {"b2": " קרוב יותר ", "b1": ""}, "general": "פחות צהוב"}, ids)
        self.assertEqual(e, [])
        self.assertEqual(r["notes"], [{"beat": "b2", "text": "קרוב יותר"}])
        self.assertEqual(sb.validate_review({"approved": True, "notes": {"b1": "x"}}, ids)[1], ["an approval carries no notes: send the notes instead"])
        self.assertTrue(sb.validate_review({"approved": False, "notes": {}}, ids)[1])
        self.assertTrue(sb.validate_review({"notes": {"zz": "x"}}, ids)[1])

    def test_page_is_self_contained_and_escapes_text(self) -> None:
        p = make_spec(self.dir)
        sp = sb.load(p)
        sp["beats"][1]["shows"] = "<script>alert(1)</script>"
        html = sb.page(sp, p.parent, "tok")
        self.assertFalse("<script>alert" in html, "user text reached the page unescaped")
        self.assertIsNone(__import__("re").search(r"(?i)(src|href)=\"https?://", html), "a remote resource in the page")
        self.assertIn("data:image/jpeg;base64,", html)
        self.assertIn('dir="rtl"', html)

    def test_cli_check_build_and_refusal(self) -> None:
        p = make_spec(self.dir)
        run = lambda *a: subprocess.run([sys.executable, "-X", "utf8", str(Path(sb.__file__)), *a], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run("check", str(p)).returncode, 0)
        b = run("build", str(p), "--out", str(self.dir / "out"))
        self.assertEqual(b.returncode, 0, b.stdout + b.stderr)
        self.assertTrue((self.dir / "out" / "storyboard.html").is_file())
        bad = make_spec(self.dir / "bad", story="")
        self.assertEqual(run("check", str(bad)).returncode, 2)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not on PATH")
    def test_grab_fills_the_real_a_roll_frame(self) -> None:
        video = self.dir / "src.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x568:rate=25:duration=3",
                        "-pix_fmt", "yuv420p", str(video)], check=True)
        p = make_spec(self.dir)
        sp = sb.load(p)
        sp["beats"][0].pop("img")
        p.write_text(json.dumps(sp, ensure_ascii=False), encoding="utf-8")
        res = sb.grab(p, video, 240)
        self.assertEqual(res["status"], "ok", res)
        sp = sb.load(p)
        self.assertEqual(sp["beats"][0]["img"], "frames/b1.jpg")
        self.assertEqual(sp["beats"][0]["src_t"], 1.25)
        self.assertGreater((self.dir / "frames" / "b1.jpg").stat().st_size, 100)


class ServeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="sb serve "))
        self.spec = make_spec(self.dir)
        self.buf = io.StringIO()
        self.code: list[int] = []
        self.th = threading.Thread(target=lambda: self.code.append(sb.serve(self.spec, self.dir / "out", 0, 30.0, False, self.buf)), daemon=True)
        self.th.start()
        for _ in range(300):
            if '"url"' in self.buf.getvalue():
                break
            time.sleep(0.1)
        self.url = json.loads(self.buf.getvalue().splitlines()[0])["url"]
        self.token = __import__("re").search(r'"token": "([^"]+)"', urllib.request.urlopen(self.url).read().decode("utf-8")).group(1)

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def post(self, body: dict, token: str | None = None) -> tuple[int, dict]:
        req = urllib.request.Request(self.url + "review", data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "X-Board-Token": token or self.token})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_notes_are_refused_then_accepted_and_the_server_exits(self) -> None:
        self.assertEqual(self.post({"approved": False, "notes": {"b2": "x"}}, token="wrong")[0], 403)
        self.assertEqual(self.post({"approved": False, "notes": {}})[0], 400)
        self.assertEqual(self.post({"approved": False, "notes": {"b2": "קרוב יותר"}, "general": "פחות צהוב"})[0], 200)
        self.th.join(20)
        self.assertEqual(self.code, [0])
        out = json.loads("\n".join(self.buf.getvalue().splitlines()[1:]))
        self.assertEqual(out["status"], "notes")
        self.assertEqual(out["lines"][0], '1. [b2 B-roll 0:02.50-0:04.00] "קרוב יותר"')
        self.assertTrue((self.dir / "out" / "storyboard_review.json").is_file())

    def test_approval(self) -> None:
        self.assertEqual(self.post({"approved": True, "notes": {}, "general": ""})[0], 200)
        self.th.join(20)
        self.assertEqual(json.loads("\n".join(self.buf.getvalue().splitlines()[1:]))["status"], "approved")


if __name__ == "__main__":
    unittest.main(verbosity=1)

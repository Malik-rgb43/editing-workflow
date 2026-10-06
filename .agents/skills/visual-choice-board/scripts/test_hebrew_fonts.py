#!/usr/bin/env python3
"""Tests for hebrew_fonts.py (stdlib unittest; no network: fetch is only exercised in plan mode)."""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hebrew_fonts as hf  # noqa: E402
import make_board as mb  # noqa: E402


def run(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = hf.main(list(args))
    return code, buf.getvalue()


class FontTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="fonts 'גופנים' "))

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_catalogue_is_complete_and_honest(self) -> None:
        cat = hf.load()
        names = [f["family"] for f in cat["families"]]
        self.assertEqual(len(names), len(set(names)))
        for f in cat["families"]:
            self.assertIn(f["style"], hf.STYLES)
            self.assertEqual(f["licence"], "OFL-1.1")
            self.assertTrue(f["dir"].startswith("ofl/") and f["file"].endswith(".ttf") and f["bytes"] > 10000, f)
            self.assertTrue(f["he"].strip())
        self.assertTrue(set(cat["default_board"]) <= set(names))
        self.assertGreaterEqual(len({f["style"] for f in cat["families"] if f["family"] in cat["default_board"]}), 4)
        self.assertRegex(cat["verified"], r"^\d{4}-\d{2}-\d{2}$")

    def test_list_and_plan_download_nothing(self) -> None:
        code, out = run("list", "--style", "serif")
        self.assertEqual(code, 0)
        self.assertIn("Frank Ruhl Libre", out)
        self.assertNotIn("Rubik ", out)
        code, out = run("fetch", "--default", "--to", str(self.dir))
        self.assertEqual(code, 0)
        p = json.loads(out)
        self.assertEqual((p["status"], p["to_download"]), ("plan_only", 8))
        self.assertEqual(p["bytes_to_download"], sum(f["bytes"] for f in hf.pick(hf.load(), [], True)))
        self.assertTrue(all(x["url"].startswith("https://raw.githubusercontent.com/google/fonts/main/ofl/") for x in p["files"]))
        self.assertIn("%5Bwght%5D", p["files"][0]["url"])  # Rubik[wght].ttf is URL-quoted
        self.assertEqual(list(self.dir.iterdir()), [])  # nothing written without --yes
        self.assertEqual(run("fetch", "Comic Sans", "--to", str(self.dir))[0], 2)  # not in the catalogue: refused, nothing fetched

    def test_spec_embeds_fetched_files_and_builds_a_board(self) -> None:
        fams = hf.pick(hf.load(), ["Heebo", "Suez One", "Gveret Levin"], False)
        for f in fams:  # stand-in files with the catalogue names (no network in tests)
            font, lic = hf.paths(f, self.dir / "fonts")
            font.parent.mkdir(parents=True, exist_ok=True)
            font.write_bytes(b"\x00\x01\x00\x00" + f["family"].encode())
            lic.write_text("SIL Open Font License 1.1", encoding="utf-8")
        out = self.dir / "board" / "spec.json"
        code, txt = run("spec", "--to", str(self.dir / "fonts"), "--text", "לא לבזבז את ה-1,990 ₪ שלך", "--keyword", "לבזבז",
                        "--families", "Heebo,Suez One,Gveret Levin", "-o", str(out))
        self.assertEqual(code, 0, txt)
        sp = json.loads(out.read_text(encoding="utf-8"))
        opts = sp["decisions"][0]["options"]
        self.assertEqual([o["family"] for o in opts], ["Heebo", "Suez One", "Gveret Levin"])
        self.assertEqual(opts[2]["fallback"], "cursive")
        self.assertTrue(all("Open Font License" in o["license"] for o in opts))
        res = mb.build(out, self.dir / "board" / "html", built_utc="2026-10-04T00:00:00Z")
        page = (self.dir / "board" / "html" / "visual-choice-board.html").read_text(encoding="utf-8")
        self.assertEqual(res["options"], 3)
        self.assertEqual(page.count("data:font/ttf;base64,"), 3)
        self.assertEqual(mb.remote_hits(page), [])

    def test_caption_style_board_settles_font_animation_and_height_on_one_board(self) -> None:
        fams = hf.pick(hf.load(), ["Heebo", "Suez One"], False)
        for f in fams:
            font, lic = hf.paths(f, self.dir / "fonts")
            font.parent.mkdir(parents=True, exist_ok=True)
            font.write_bytes(b"\x00\x01\x00\x00" + f["family"].encode())
            lic.write_text("SIL Open Font License 1.1", encoding="utf-8")
        still = self.dir / "frame.jpg"
        still.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 64)
        out = self.dir / "board" / "spec.json"
        code, txt = run("spec", "--to", str(self.dir / "fonts"), "--text", "הזמנתי טיסה בשלוש דקות", "--families", "Heebo,Suez One",
                        "--caption-style", "--still", str(still), "-o", str(out))
        self.assertEqual(code, 0, txt)
        sp = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual([(d["id"], d["kind"]) for d in sp["decisions"]], [("font", "font"), ("anim", "caption_anim"), ("position", "layout")])
        self.assertEqual(sp["title"], "איך הכתוביות ייראו?")
        self.assertNotIn("bounce", [o["anim"] for o in sp["decisions"][1]["options"]])
        self.assertTrue(all(o["caption_y_pct"] <= 75 for o in sp["decisions"][2]["options"]))  # above the house caption rail (1450/1920)
        self.assertEqual(sp["still"], "../frame.jpg")
        res = mb.build(out, self.dir / "board" / "html", built_utc="2026-10-06T00:00:00Z")
        self.assertEqual(res["options"], 2 + len(hf.CAPTION_ANIMS) + len(hf.CAPTION_Y))
        self.assertEqual(run("spec", "--to", str(self.dir / "fonts"), "--text", "x y", "--families", "Heebo", "--caption-style",
                             "--still", str(self.dir / "missing.jpg"), "-o", str(self.dir / "s2.json"))[0], 2)

    def test_a_non_hebrew_caption_board_from_the_users_own_fonts(self) -> None:
        for fam in ("Inter", "Oswald"):
            (self.dir / f"{fam}.ttf").write_bytes(b"\x00\x01\x00\x00" + fam.encode())
            (self.dir / f"{fam}-OFL.txt").write_text("SIL Open Font License 1.1", encoding="utf-8")
        out = self.dir / "board" / "spec.json"
        args = ["spec", "--text", "Train harder, not longer", "--lang", "en", "--caption-style", "-o", str(out)]
        for fam in ("Inter", "Oswald"):
            args += ["--font", f"{fam}={self.dir / (fam + '.ttf')}={self.dir / (fam + '-OFL.txt')}"]
        code, txt = run(*args)
        self.assertEqual(code, 0, txt)
        sp = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual([o["family"] for o in sp["decisions"][0]["options"]], ["Inter", "Oswald"])  # no Hebrew catalogue font added
        self.assertEqual(sp["title"], "How should the captions look?")
        self.assertEqual(len(sp["decisions"]), 3)
        res = mb.build(out, self.dir / "board" / "html", built_utc="2026-10-06T00:00:00Z")
        self.assertEqual(res["options"], 2 + len(hf.CAPTION_ANIMS) + len(hf.CAPTION_Y))
        self.assertEqual(run("spec", "--text", "x y", "--font", "Bad=only-two", "-o", str(out))[0], 2)

    def test_spec_refuses_missing_files_and_placeholder_text(self) -> None:
        out = self.dir / "s.json"
        code, _ = run("spec", "--to", str(self.dir), "--text", "שלום", "--families", "Heebo", "-o", str(out))
        self.assertEqual(code, 2)
        self.assertFalse(out.exists())
        code, _ = run("spec", "--to", str(self.dir), "--text", "  ", "--families", "Heebo", "-o", str(out))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)

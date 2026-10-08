#!/usr/bin/env python3
"""Tests for promise_check.py (stdlib unittest; run directly or through `promise_check.py --self-check`)."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import promise_check as pc  # noqa: E402

BEATS = [{"id": "b1", "t": 0.0, "end": 2.0, "roll": "A", "source": "own"},
         {"id": "b2", "t": 2.0, "end": 4.0, "roll": "B", "source": "generated"},
         {"id": "b3", "t": 4.0, "end": 6.0, "roll": "G", "source": "graphic"}]
APPROVED = {"prompt": 'PROMPT_APPROVED 2026-10-08 "כן, מאשר"', "storyboard": "STORYBOARD APPROVED 2026-10-08"}


def promise(**over) -> dict:
    args = {"duration": 6.0, "aspect": "9:16", "captions": "he", "music": "on", "voice": "speaker", "tolerance": 0.5,
            "beats": [dict(b) for b in BEATS], "approvals": APPROVED}
    args.update(over)
    doc, errors = pc.build_promise("chef", args["duration"], args["aspect"], args["captions"], args["music"], args["voice"],
                                   args["tolerance"], args["beats"], args["approvals"])
    assert not errors, errors
    return doc


def built(**over) -> dict:
    m = {"duration_s": 6.1, "aspect": "9:16", "audio": "present", "captions": "script:hebrew", "music": "on", "voice_track": False,
         "beats": [dict(b) for b in BEATS]}
    m.update(over)
    return m


def states(res: dict) -> dict:
    return {r["field"]: r["state"] for r in res["rows"]}


def change(field, to, asked="כן, תשים תמונה במקום", at="2026-10-08T10:00:00+00:00") -> dict:
    return {"field": field, "from": None, "to": to, "asked": asked, "at": at}


class PureTests(unittest.TestCase):
    def test_lock_needs_both_approvals(self) -> None:
        _, e = pc.build_promise("p", 6, "9:16", "he", "on", "speaker", 0.5, BEATS, {"prompt": None, "storyboard": None})
        self.assertTrue(any("PROMPT_APPROVED" in x for x in e))
        _, e = pc.build_promise("p", 6, "9:16", "he", "on", "speaker", 0.5, BEATS, {"prompt": APPROVED["prompt"], "storyboard": None})
        self.assertTrue(any("STORYBOARD APPROVED" in x for x in e))
        _, e = pc.build_promise("p", 6, "9:16", "he", "on", "speaker", 0.5, [], {"prompt": APPROVED["prompt"], "storyboard": None})
        self.assertEqual(e, [], "a plain edit without a storyboard needs only PROMPT_APPROVED")
        _, e = pc.build_promise("p", 0, "wide", "hebrew!", "maybe", "robot", 0.5, [], APPROVED)
        self.assertEqual(len(e), 5, e)

    def test_everything_kept(self) -> None:
        res = pc.compare(promise(), built())
        self.assertEqual(res["status"], "kept", res)
        self.assertTrue(all(s == "kept" for s in states(res).values()), states(res))

    def test_a_failed_generation_turned_into_a_still_without_asking(self) -> None:
        doc = promise()
        res = pc.compare(doc, built(beats=[BEATS[0], {**BEATS[1], "source": "graphic"}, BEATS[2]]))
        self.assertEqual(res["status"], "unasked_change")
        self.assertEqual(states(res)["beats.b2.source"], "unasked_change")
        doc["changes"].append(change("beats.b2.source", "graphic"))
        res = pc.compare(doc, built(beats=[BEATS[0], {**BEATS[1], "source": "graphic"}, BEATS[2]]))
        self.assertEqual(res["status"], "kept", res)
        row = next(r for r in res["rows"] if r["field"] == "beats.b2.source")
        self.assertEqual((row["state"], row["asked"]), ("asked", "כן, תשים תמונה במקום"))

    def test_a_zoomed_detail_swapped_for_a_full_screen_shot_without_asking(self) -> None:
        shot_beats = [{**b, "shot": s} for b, s in zip(BEATS, ("close", "detail", "graphic"))]
        doc = promise(beats=[dict(b) for b in shot_beats])
        swapped = [shot_beats[0], {**shot_beats[1], "shot": "screen"}, shot_beats[2]]
        res = pc.compare(doc, built(beats=swapped))
        self.assertEqual(states(res)["beats.b2.shot"], "unasked_change")
        doc["changes"].append(change("beats.b2.shot", "screen", asked="כן, תשאיר מסך מלא"))
        self.assertEqual(pc.compare(doc, built(beats=swapped))["status"], "kept")
        self.assertNotIn("beats.b2.shot", states(pc.compare(promise(), built(beats=swapped))))  # an old promise without shots is not compared on them

    def test_music_dropped_length_moved_aspect_changed(self) -> None:
        res = pc.compare(promise(), built(music="off", duration_s=9.0, aspect="16:9"))
        st = states(res)
        self.assertEqual((st["music"], st["duration_s"], st["aspect"]), ("unasked_change",) * 3)
        doc = promise()
        doc["changes"] += [change("music", "off"), change("duration_s", 9.0), change("aspect", "16:9")]
        self.assertEqual(pc.compare(doc, built(music="off", duration_s=9.2, aspect="16:9"))["status"], "kept")

    def test_a_change_without_the_users_words_does_not_count(self) -> None:
        doc = promise()
        doc["changes"].append(change("music", "off", asked=""))
        res = pc.compare(doc, built(music="off"))
        self.assertEqual(res["status"], "unasked_change")
        self.assertTrue(any("asked" in p for p in res["problems"]))

    def test_beats_swapped_dropped_added(self) -> None:
        swapped = [BEATS[0], BEATS[2], BEATS[1]]
        self.assertEqual(states(pc.compare(promise(), built(beats=swapped)))["beats.order"], "unasked_change")
        dropped = [BEATS[0], BEATS[2]]
        self.assertEqual(states(pc.compare(promise(), built(beats=dropped)))["beats.b2"], "unasked_change")
        doc = promise()
        doc["changes"].append(change("beats.b2", "dropped"))
        self.assertEqual(pc.compare(doc, built(beats=dropped))["status"], "kept")
        extra = [*BEATS, {"id": "b4", "t": 6.0, "end": 7.0, "roll": "B", "source": "stock"}]
        self.assertEqual(states(pc.compare(promise(), built(beats=extra)))["beats.b4"], "unasked_change")
        doc = promise()
        doc["changes"].append(change("beats.order", "b1,b3,b2"))
        self.assertEqual(pc.compare(doc, built(beats=swapped))["status"], "kept")

    def test_captions_and_voice(self) -> None:
        st = states(pc.compare(promise(), built(captions="off")))
        self.assertEqual(st["captions"], "unasked_change")
        st = states(pc.compare(promise(), built(captions="script:latin")))
        self.assertEqual(st["captions"], "unasked_change", "Hebrew captions promised, Latin text built")
        st = states(pc.compare(promise(captions="off"), built(captions="script:hebrew")))
        self.assertEqual(st["captions"], "unasked_change", "captions added nobody asked for")
        st = states(pc.compare(promise(), built(captions="on")))
        self.assertEqual(st["captions"], "kept")
        st = states(pc.compare(promise(voice="tts"), built()))
        self.assertEqual(st["voice"], "unasked_change", "a TTS voice promised, no voice track built")

    def test_not_measured_is_never_kept(self) -> None:
        res = pc.compare(promise(), built(music=None, voice_track=None, beats=None, duration_s=None, aspect=None, audio=None, captions=None))
        self.assertEqual(res["status"], "kept")
        self.assertEqual(set(res["not_measured"]), {"duration_s", "aspect", "captions", "music", "voice", "audio", "beats"})

    def test_measure_reads_the_composition_and_cues(self) -> None:
        d = Path(tempfile.mkdtemp(prefix="pc 'הבטחה' "))
        try:
            hf = d / "hf"
            (hf / "data").mkdir(parents=True)
            (hf / "index.html").write_text('<div class="clip caption-rail" data-start="0"></div>', encoding="utf-8")
            self.assertEqual(pc.measure_captions(hf), "on")
            (hf / "data" / "captions.json").write_text(json.dumps({"chunks": [{"id": "c1", "text": "כל מנה נבנית"}]}, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(pc.measure_captions(hf), "script:hebrew")
            (hf / "cues.json").write_text(json.dumps({"duration": 6, "vo": [], "music": {"file": "assets/bed.wav"}}), encoding="utf-8")
            self.assertEqual(pc.measure_cues(hf / "cues.json"), {"music": "on", "voice_track": False})
            self.assertEqual(pc.measure_cues(hf / "none.json"), {"music": None, "voice_track": None})
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_aspect_names(self) -> None:
        self.assertEqual(pc.aspect_name(1080, 1920), "9:16")
        self.assertEqual(pc.aspect_name(1088, 1920), "9:16")
        self.assertEqual(pc.aspect_name(1920, 1080), "16:9")
        self.assertEqual(pc.aspect_name(1000, 300), "10:3")


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="pc cli "))
        self.proj = self.dir / "chef"
        (self.proj / "hf").mkdir(parents=True)
        (self.proj / "_work" / "storyboard").mkdir(parents=True)
        (self.proj / "hf" / "index.html").write_text("<div></div>", encoding="utf-8")
        (self.proj / "hf" / "cues.json").write_text(json.dumps({"duration": 3, "vo": [], "music": {"file": "assets/bed.wav"}}), encoding="utf-8")
        self.sb = self.proj / "_work" / "storyboard" / "storyboard.json"
        beats = [{**b, "t": b["t"] / 2, "end": b["end"] / 2} for b in BEATS]
        self.sb.write_text(json.dumps({"aspect": "9:16", "beats": beats}), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_main(self, *argv) -> tuple[int, dict]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = pc.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_lock_record_and_refusals(self) -> None:
        lock = ("lock", str(self.proj), "--captions", "off", "--music", "on", "--voice", "speaker")
        code, out = self.run_main(*lock)
        self.assertEqual(code, 2)
        self.assertIn("PROMPT_APPROVED", " ".join(out["errors"]))
        (self.proj / "hf" / "CHANGELOG.md").write_text('PROMPT_APPROVED 2026-10-08 "go"\nSTORYBOARD APPROVED 2026-10-08\n', encoding="utf-8")
        code, out = self.run_main(*lock)
        self.assertEqual((code, out["status"], out["promised"]["duration_s"], out["promised"]["aspect"]), (0, "locked", 3.0, "9:16"))
        self.assertEqual(self.run_main(*lock)[0], 2, "a second lock without --relock is refused")
        self.assertEqual(self.run_main("record", str(self.proj), "--field", "music", "--to", "off", "--asked", "")[0], 2)
        self.assertEqual(self.run_main("record", str(self.proj), "--field", "nonsense", "--to", "off", "--asked", "yes")[0], 2)
        code, out = self.run_main("record", str(self.proj), "--field", "beats.b2.source", "--to", "graphic", "--asked", "ok, a still")
        self.assertEqual((code, out["change"]["from"], out["change"]["to"]), (0, "generated", "graphic"))
        self.assertEqual(self.run_main(*lock, "--relock")[0], 0)
        self.assertEqual(len(list((self.proj / "_work").glob("promise.*.json"))), 1, "the old promise is kept beside the new one")
        self.assertEqual(self.run_main("check", str(self.proj), "--render", str(self.dir / "missing.mp4"))[0], 2)

    def test_check_before_the_draft_reads_the_composition(self) -> None:
        (self.proj / "hf" / "CHANGELOG.md").write_text('PROMPT_APPROVED 2026-10-08 "go"\nSTORYBOARD APPROVED 2026-10-08\n', encoding="utf-8")
        (self.proj / "hf" / "index.html").write_text('<div id="root" data-composition-id="main" data-start="0" data-duration="3" '
                                                      'data-width="1080" data-height="1920"></div>', encoding="utf-8")
        self.assertEqual(self.run_main("lock", str(self.proj), "--captions", "off", "--music", "on", "--voice", "speaker")[0], 0)
        code, out = self.run_main("check", str(self.proj))
        self.assertEqual((code, out["status"]), (0, "kept"), out)
        self.assertIn("audio", out["not_measured"])
        (self.proj / "hf" / "index.html").write_text('<div id="root" data-composition-id="main" data-start="0" data-duration="5" '
                                                      'data-width="1920" data-height="1080"></div>', encoding="utf-8")
        code, out = self.run_main("check", str(self.proj))
        self.assertEqual(code, 1)
        self.assertEqual({r["field"] for r in out["rows"] if r["state"] == "unasked_change"}, {"duration_s", "aspect"})

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe not on PATH")
    def test_check_measures_a_real_draft(self) -> None:
        (self.proj / "hf" / "CHANGELOG.md").write_text('PROMPT_APPROVED 2026-10-08 "go"\nSTORYBOARD APPROVED 2026-10-08\n', encoding="utf-8")
        draft = self.dir / "draft.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=108x192:rate=25:duration=3",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-shortest", "-pix_fmt", "yuv420p", str(draft)], check=True)
        self.assertEqual(self.run_main("lock", str(self.proj), "--captions", "off", "--music", "on", "--voice", "speaker")[0], 0)
        code, out = self.run_main("check", str(self.proj), "--render", str(draft))
        self.assertEqual((code, out["status"]), (0, "kept"), out)
        spec = json.loads(self.sb.read_text(encoding="utf-8"))
        spec["beats"][1]["source"] = "stock"
        self.sb.write_text(json.dumps(spec), encoding="utf-8")
        code, out = self.run_main("check", str(self.proj), "--render", str(draft))
        self.assertEqual((code, out["status"]), (1, "unasked_change"))
        self.assertEqual([r["field"] for r in out["rows"] if r["state"] == "unasked_change"], ["beats.b2.source"])

    def test_help_is_fast_and_cli_runs(self) -> None:
        p = subprocess.run([sys.executable, "-X", "utf8", str(Path(pc.__file__)), "--help"], capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertIn("Usage:", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)

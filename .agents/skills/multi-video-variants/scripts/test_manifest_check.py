"""Unit tests for manifest_check.py (stdlib unittest; no pytest needed).

Usage:
  python -X utf8 -m unittest -v test_manifest_check      (run from this folder)
  python -X utf8 test_manifest_check.py

Covers the CLI end to end (exit codes 0/1/2), including a Hebrew + space project path, on top of
the in-script `--self-check`. Needs no ffmpeg and no media: files are fake bytes.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = str(HERE / "manifest_check.py")


def run(*args):
    p = subprocess.run([sys.executable, "-X", "utf8", TOOL, *map(str, args)], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def put(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))


class CliFlow(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory(prefix="mv פרויקט ")
        self.p = Path(self.td.name)
        for hf in ("hf", "hf_1x1"):
            put(self.p / hf / "index.html", "<html>" + hf + "</html>")
            put(self.p / hf / "cues.js", "const CUES={};")
            put(self.p / hf / "assets" / "mix.wav", b"mix" * 100)
        self.names = ["ad_meta_master_16x9.mp4", "ad_meta_master_1x1.mp4"]
        put(self.p / "_work" / "qa.json", "{}")
        for n in self.names:
            put(self.p / "final" / n, ("v:" + n).encode() * 50)

    def tearDown(self):
        self.td.cleanup()

    def record_all(self):
        self.assertEqual(run("freeze", self.p, "--hf", "hf", "--matrix", ",".join(self.names))[0], 0)
        for n, hf, kind, (w, h) in [(self.names[0], "hf", "master", (1920, 1080)), (self.names[1], "hf_1x1", "relayout", (1080, 1080))]:
            self.assertEqual(run("stamp", self.p, "--hf", hf)[0], 0)
            code, out = run("record", self.p, "--file", n, "--hf", hf, "--kind", kind, "--qa", "pass", "--qa-evidence", "_work/qa.json",
                            "--lufs", "-14.1", "--tp", "-1.2", "--width", w, "--height", h, "--duration-s", "20")
            self.assertEqual(code, 0, out)

    def test_ready_then_blocked_by_master_edit(self):
        self.record_all()
        code, out = run("check", self.p)
        self.assertEqual(code, 0, out)
        self.assertIn("READY", out)
        put(self.p / "hf" / "index.html", "<html>master edited after freeze</html>")
        code, out = run("check", self.p)
        self.assertEqual(code, 1, out)
        self.assertIn("M003_STALE_MASTER", out)

    def test_no_manifest_is_insufficient_not_ready(self):
        code, out = run("check", self.p)
        self.assertEqual(code, 2, out)
        self.assertIn("INSUFFICIENT_EVIDENCE", out)

    def test_orphan_file_blocks(self):
        self.record_all()
        put(self.p / "final" / "old_render.mp4", b"x")
        code, out = run("check", self.p)
        self.assertEqual(code, 1, out)
        self.assertIn("M081_ORPHAN_FILE", out)

    def test_json_report_shape(self):
        self.record_all()
        code, out = run("check", self.p, "--json")
        rep = json.loads(out)
        self.assertEqual(rep["status"], "READY")
        self.assertTrue(rep["ready"])
        self.assertIn("limits", rep)

    def test_self_check_passes(self):
        code, out = run("--self-check")
        self.assertEqual(code, 0, out)
        self.assertIn('"PASS"', out)


if __name__ == "__main__":
    unittest.main(verbosity=2)

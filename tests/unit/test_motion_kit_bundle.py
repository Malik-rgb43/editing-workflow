"""The bundled motion kit (pro-video-editor/motion-kit, MIT, Hugh Phan) ships whole, is declared third-party,
is pointed to by the skill, and its curves are not linear."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "agent-content" / "skills" / "pro-video-editor"
KIT = SKILL / "motion-kit"


def test_kit_files_and_licence_ship():
    for name in ("motion-kit.js", "LIBRARY.md", "RULES.md", "LICENSE-motion-kit.txt"):
        assert (KIT / name).is_file(), name
    lic = (KIT / "LICENSE-motion-kit.txt").read_text(encoding="utf-8")
    assert "MIT License" in lic and "Hugh Phan" in lic


def test_skill_and_reference_point_to_the_kit():
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    ref = (SKILL / "references" / "camera-and-motion.md").read_text(encoding="utf-8")
    assert "motion-kit/motion-kit.js" in skill and "motion-kit/RULES.md" in skill
    assert "## Easing and timing" in ref and "motion-kit/LIBRARY.md" in ref
    assert "power3.in" not in ref  # no named preset offered as the example easing


def test_bom_declares_the_kit_third_party_mit():
    bom = json.loads((ROOT / "docs" / "BOM.json").read_text(encoding="utf-8"))
    rows = [e for e in bom["files"] if "/pro-video-editor/motion-kit/" in e["path"]]
    assert len(rows) == 12  # 4 files x (canonical + 2 generated host copies)
    assert all(e["origin"] == "third_party" and e["licence"] == "MIT" for e in rows)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_curves_load_and_are_not_linear():
    js = (KIT / "motion-kit.js").as_posix()
    code = (
        "global.window = global; global.gsap = undefined;"
        f"require({json.dumps(js)});"
        "const K = global.MotionKit;"
        "const out = {};"
        "for (const n of ['kit.land','kit.heavy','kit.leave']) out[n] = K.curve(n)(0.5);"
        "out.dur = [K.dur(100, 1), K.dur(900, 1)];"
        "console.log(JSON.stringify(out));"
    )
    res = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout.strip().splitlines()[-1])
    for name in ("kit.land", "kit.heavy", "kit.leave"):
        assert abs(out[name] - 0.5) > 0.05, (name, out[name])
    assert out["dur"][1] > out["dur"][0]

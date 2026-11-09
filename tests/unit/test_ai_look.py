"""The anti-AI-look rules: the toolkit's own blocks pass ai_look_scan, the caption block keeps karaoke optional and emphasis
explicit, and the skills point to the reference."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN = ROOT / "agent-content" / "skills" / "pro-video-editor" / "scripts" / "ai_look_scan.py"


def run_scan(*args):
    return subprocess.run([sys.executable, "-X", "utf8", str(SCAN), *map(str, args), "--json"], capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


def test_the_toolkit_blocks_have_no_ai_look_tells():
    res = run_scan(ROOT / "hf-blocks")
    out = json.loads(res.stdout)
    assert res.returncode == 0 and out["summary"]["verdict"] == "pass", out["findings"]


def test_a_fade_up_preset_is_flagged_and_strict_fails(tmp_path):
    f = tmp_path / "c.html"
    f.write_text('<script>tl.fromTo("#a",{opacity:0,y:24},{opacity:1,y:0,duration:0.5,ease:"power3.out"},0);</script>', encoding="utf-8")
    out = json.loads(run_scan(f).stdout)
    assert {x["rule"] for x in out["findings"]} >= {"AL01", "AL03"} and out["summary"]["verdict"] == "warn"
    assert run_scan(f, "--strict").returncode == 1


def test_caption_block_karaoke_is_optional_and_emphasis_is_explicit():
    manifest = json.loads((ROOT / "hf-blocks" / "caption" / "block.json").read_text(encoding="utf-8"))
    defaults = {v["id"]: v["default"] for v in manifest["variables"]}
    assert defaults["karaoke"] is False and defaults["stress"] == ""
    html = (ROOT / "hf-blocks" / "caption" / "block.html").read_text(encoding="utf-8")
    assert '"id":"karaoke"' in html and '"id":"stress"' in html
    typed = json.loads((ROOT / "hf-blocks" / "typed-caption" / "block.json").read_text(encoding="utf-8"))
    assert "--hfb-accent" in typed["palette"] and not any("grad" in p for p in typed["palette"])


def test_skills_point_to_the_reference():
    ref = "references/anti-ai-look.md"
    skills = ROOT / "agent-content" / "skills"
    assert (skills / "pro-video-editor" / ref).is_file()
    assert ref in (skills / "pro-video-editor" / "SKILL.md").read_text(encoding="utf-8")
    assert "anti-ai-look.md" in (skills / "captions-transcription" / "SKILL.md").read_text(encoding="utf-8")
    assert "anti-ai-look.md" in (ROOT / "agent-content" / "benchmarks" / "critic-brief.md").read_text(encoding="utf-8")

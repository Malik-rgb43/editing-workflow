"""The Claude Code plugin wrapper stays a thin pointer at agent-content/skills (no copy) and agrees with the installer and the release."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
MARKET = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))


def test_plugin_points_at_the_canonical_skills_and_has_no_second_copy():
    assert PLUGIN["skills"] == ["./agent-content/skills/"]
    assert not (REPO / "skills").exists(), "a root skills/ folder would load next to agent-content/skills and duplicate every skill"
    names = sorted(p.name for p in (REPO / "agent-content" / "skills").iterdir() if (p / "SKILL.md").is_file())
    assert len(names) >= 10 and all((REPO / "agent-content" / "skills" / n / "SKILL.md").is_file() for n in names)


def test_names_agree_between_plugin_marketplace_and_installer():
    entry = MARKET["plugins"][0]
    assert PLUGIN["name"] == entry["name"] == MARKET["name"] == "editing-workflow"
    assert entry["source"] == "./"
    src = (REPO / "install" / "bootstrap.py").read_text(encoding="utf-8")
    assert 'PLUGIN_ID = "%s@%s"' % (PLUGIN["name"], MARKET["name"]) in src
    assert re.search(r'PLUGIN_SOURCE = "Malik-rgb43/editing-workflow"', src)


def test_plugin_version_matches_the_release_manifest():
    rm = json.loads((REPO / "release-manifest.json").read_text(encoding="utf-8"))
    assert PLUGIN["version"] == rm["version"], "bump .claude-plugin/plugin.json together with release-manifest.json (Claude Code pins users to this version)"


def test_plugin_name_is_not_reserved_and_metadata_is_present():
    assert not re.match(r"(?i)^(claude|anthropic|cc-plugin)", PLUGIN["name"])
    for k in ("description", "author", "license", "homepage", "repository"):
        assert PLUGIN.get(k), k
    assert PLUGIN["license"] == "Apache-2.0"


def test_plugin_files_hold_no_personal_or_local_details():
    blob = (REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8") + (REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z]:\\|/Users/|/home/|@gmail", blob)

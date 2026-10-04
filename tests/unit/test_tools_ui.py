"""ui: registry search/view/add-command with a faked network (no HTTP in the test run), licence tiers, cache and the refusals."""

from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "src"))

import ui  # noqa: E402

DIRECTORY = [
    {"name": "@magicui", "homepage": "https://magicui.design", "url": "https://magicui.design/r/{name}", "description": "animated components", "health": {"status": "healthy"}},
    {"name": "@aceternity", "homepage": "https://ui.aceternity.com", "url": "https://ui.aceternity.com/registry/{name}.json", "description": "excluded one"},
    {"name": "@react-bits", "homepage": "https://reactbits.dev", "url": "https://reactbits.dev/r/{name}.json", "description": "restricted one"},
    {"name": "@weird", "homepage": "https://w.example", "url": "https://w.example/r/{name}.json", "description": "not in the table"},
    {"name": "@broken", "url": "https://b.example/no-placeholder.json"},
]
MAGIC_INDEX = {"name": "magicui", "items": [{"name": "animated-list", "type": "registry:ui", "title": "Animated List", "description": "A list where items enter one by one"},
                                            {"name": "marquee", "type": "registry:ui", "title": "Marquee", "description": "scrolling logos"}]}
ITEM = {"name": "animated-list", "type": "registry:ui", "title": "Animated List", "dependencies": ["motion"], "registryDependencies": ["utils"],
        "files": [{"path": "registry/ui/animated-list.tsx", "type": "registry:ui", "content": "export const A = 1\n"}]}


@pytest.fixture()
def net(monkeypatch, tmp_path):
    calls = []
    table = {ui.DIRECTORY_URL: DIRECTORY, "https://magicui.design/r/registry": MAGIC_INDEX, "https://magicui.design/r/animated-list": ITEM}

    def fake(url, timeout):
        calls.append(url)
        if url in table:
            return table[url]
        raise urllib.error.URLError("404")

    monkeypatch.setattr(ui, "http_get_json", fake)
    monkeypatch.setenv("AVC_UI_CACHE", str(tmp_path / "cache"))
    return calls


def run(*args):
    return ui.main(list(map(str, args)))


def test_tiers():
    assert [ui.tier_of(n) for n in ("@magicui", "@react-bits", "@aceternity", "@weird", "@MagicUI")] == ["ok", "restricted", "excluded", "unknown", "ok"]


def test_search_ranks_name_and_description_and_skips_other_tiers(net, capsys):
    assert run("search", "animated list", "--registry", "@magicui", "--json") == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hits"][0]["ref"] == "@magicui/animated-list" and out["hits"][0]["tier"] == "ok" and len(out["hits"]) == 1
    capsys.readouterr()
    assert run("search", "scrolling", "--registry", "@aceternity", "--json") == 2  # excluded: skipped, nothing found
    assert "excluded tier, skipped" in capsys.readouterr().out


def test_second_search_uses_the_cache_and_offline_works(net, capsys):
    run("search", "marquee", "--registry", "@magicui", "--json")
    first = len(net)
    run("search", "marquee", "--registry", "@magicui", "--json")
    assert len(net) == first  # fresh cache: no new request
    capsys.readouterr()
    assert run("--offline", "search", "marquee", "--registry", "@magicui", "--json") == 0
    assert json.loads(capsys.readouterr().out)["hits"][0]["ref"] == "@magicui/marquee"


def test_offline_without_cache_is_a_clear_refusal(net, capsys):
    assert run("--offline", "search", "animated", "--registry", "@magicui") == 2
    assert "offline and not cached" in capsys.readouterr().err


def test_view_prints_summary_and_saves_source_with_a_provenance_file(net, capsys, tmp_path):
    assert run("view", "@magicui/animated-list", "--save", tmp_path / "out") == 0
    s = json.loads(capsys.readouterr().out)
    assert s["tier"] == "ok" and s["files"][0]["path"].endswith("animated-list.tsx") and s["origin"] == "https://magicui.design/r/animated-list"
    assert (tmp_path / "out" / "animated-list.tsx").read_text(encoding="utf-8") == "export const A = 1\n"
    src = (tmp_path / "out" / "SOURCE.md").read_text(encoding="utf-8")
    assert "origin: https://magicui.design/r/animated-list" in src and "tier: ok" in src and "item sha256:" in src


def test_view_and_add_command_refuse_the_excluded_tier_and_21st(net, capsys):
    assert run("view", "@aceternity/spotlight") == 2 and "EXCLUDED" in capsys.readouterr().err
    assert run("add-command", "@aceternity/spotlight") == 2
    assert run("view", "@21st/anything") == 2 and "21st.dev" in capsys.readouterr().err
    assert run("view", "not-a-ref") == 2


def test_add_command_only_prints(net, capsys):
    assert run("add-command", "@magicui/animated-list") == 0
    cap = capsys.readouterr()
    assert cap.out.strip() == "npx shadcn@latest add @magicui/animated-list" and "scratch folder" in cap.err


def test_registries_lists_tiers_and_drops_entries_without_a_name_placeholder(net, capsys):
    assert run("registries", "--json") == 0
    rows = {r["name"]: r["tier"] for r in json.loads(capsys.readouterr().out)["registries"]}
    assert rows["@shadcn"] == "ok" and rows["@aceternity"] == "excluded" and rows["@react-bits"] == "restricted" and rows["@weird"] == "unknown" and "@broken" not in rows


def test_non_https_is_refused():
    with pytest.raises(ValueError):
        ui.http_get_json("http://example.com/x.json", 5)

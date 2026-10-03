"""Sign-up / referral links: disclosed at the moment of choice, never opened by the installer, never injected into calls, every paid entry covered."""
import json
import re
import tomllib

import pytest

from test_install_support import *  # noqa: F401,F403

REF = tomllib.loads((REPO / "integrations" / "referrals.toml").read_text(encoding="utf-8"))
CAT = tomllib.loads((REPO / "integrations" / "catalog.toml").read_text(encoding="utf-8"))
IDS = {e["id"] for e in CAT["entry"]}
PAID = [e["id"] for e in CAT["entry"] if str(e["cost"]).startswith(("paid", "app licence", "plan-dependent", "workspace plan"))]


def _with_referral(env, service, url):
    p = env.repo / "integrations" / "referrals.toml"
    text = (REPO / "integrations" / "referrals.toml").read_text(encoding="utf-8")
    block = 'id = "%s"\n' % service
    i = text.index(block)
    j = text.index('referral_url = ""', i)
    p.write_text(text[:j] + 'referral_url = "%s"' % url + text[j + len('referral_url = ""'):], encoding="utf-8")


def test_referrals_file_is_well_formed_and_holds_no_secrets():
    ids = [s["id"] for s in REF["service"]]
    assert len(ids) == len(set(ids))
    for sv in REF["service"]:
        assert sv["entries"] and set(sv["entries"]) <= IDS, sv["id"]
        assert sv["plain_url"].startswith("https://")
        r = sv.get("referral_url", "")
        assert r == "" or r.startswith("https://"), sv["id"]
        for u in (sv["plain_url"], r):
            assert not re.search(r"(?i)(token|secret|api[_-]?key|password|bearer)", u), "a public URL only: %s" % u


def test_every_paid_entry_is_covered_or_explicitly_excluded():
    covered = {e for sv in REF["service"] for e in sv["entries"]}
    excluded = set(REF["no_referral"])
    assert excluded <= IDS
    missing = [i for i in PAID if i not in covered and i not in excluded]
    assert not missing, "paid integrations with no sign-up entry in integrations/referrals.toml: %s" % missing


def test_without_a_referral_only_the_plain_link_is_shown(env):
    rc, out = env.json("add", "higgsfield")
    assert rc == 0
    sg = out["results"][0]["signup"]
    assert sg and sg[0]["referral_url"] is None and sg[0]["plain_url"] == "https://higgsfield.ai"
    rc, human, _ = env.run("add", "higgsfield")
    assert "plain link: https://higgsfield.ai" in human and "referral" not in human.lower()


def test_a_referral_link_is_labelled_disclosed_and_never_opened(env):
    _with_referral(env, "higgsfield", "https://example.com/ref/abc")
    rc, out = env.json("add", "higgsfield")
    assert out["results"][0]["signup"][0]["referral_url"] == "https://example.com/ref/abc"
    assert "referral link" in out["disclosure"]["en"] and "supports" in out["disclosure"]["en"]
    assert out["disclosure"]["he"]
    rc, human, _ = env.run("add", "higgsfield")
    assert "referral link: https://example.com/ref/abc" in human and "plain link: https://higgsfield.ai" in human
    assert "Disclosure: this is a referral link" in human and "Open nothing without their yes" in human
    rc, he, _ = env.run("add", "higgsfield", "--lang", "he")
    assert "לינק הפניה" in he and "גילוי נאות" in he
    assert not [c for c in env.fake.calls if any(w in " ".join(map(str, c)) for w in ("start ", "open ", "xdg-open", "example.com"))]


def test_plain_links_flag_hides_every_referral(env):
    _with_referral(env, "higgsfield", "https://example.com/ref/abc")
    rc, out = env.json("add", "higgsfield", "--plain-links")
    assert out["results"][0]["signup"][0]["referral_url"] is None
    assert "disclosure" in out  # a sign-up still happened: the plain link is shown, the note stays harmless
    rc, human, _ = env.run("add", "higgsfield", "--plain-links")
    assert "example.com" not in human and "referral link:" not in human


def test_non_https_referral_is_ignored(env):
    _with_referral(env, "magic-21st", "http://insecure.example/ref")
    rc, out = env.json("add", "magic-21st")
    assert out["results"][0]["signup"][0]["referral_url"] is None


def test_tripo_is_the_3d_generation_signup_under_the_blender_connector(env):
    rc, out = env.json("add", "blender-mcp")
    names = {s["service"] for s in out["results"][0]["signup"]}
    assert names == {"Tripo (3D generation)"}


def test_free_integrations_never_show_a_signup(env):
    rc, out = env.json("add", "ffmpeg")
    assert out["results"][0]["signup"] == [] and "disclosure" not in out


def test_the_installer_never_adds_referral_parameters_to_connector_commands():
    for e in CAT["entry"]:
        m = e.get("mcp") or {}
        for v in [m.get("url", "")] + [i.get("command", "") for i in (e.get("install") or {}).values()]:
            assert not re.search(r"(?i)(ref=|referral|affiliate|aff_id)", v or ""), e["id"]

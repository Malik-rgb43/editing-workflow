"""Positive and negative controls for scripts/scan_secrets.py and scripts/scan_private.py.

Fake credentials and private paths are assembled at run time so this file itself contains no literal match.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import _avc_common as C  # noqa: E402
import _avc_fixtures as F  # noqa: E402
import scan_private  # noqa: E402
import scan_secrets  # noqa: E402

SECRETS_CLI = SCRIPTS / "scan_secrets.py"
PRIVATE_CLI = SCRIPTS / "scan_private.py"


def codes(report, level="FAIL"):
    return {f.code for f in report.findings if f.level == level}


@pytest.fixture()
def root(tmp_path):
    path = tmp_path / "מאגר בדיקה" / "repo"
    path.mkdir(parents=True)
    return path


# ------------------------------------------------------------------ secrets

FAKE_TOKENS = {
    "aws-access-key": lambda: "AKIA" + "ABCDEFGHIJKLMNOP",
    "github-token": lambda: "gh" + "p_" + "a1B2c3D4e5" * 4,
    "github-fine-grained": lambda: "github_" + "pat_" + "A1b2C3d4E5" * 5,
    "slack-token": lambda: "xox" + "b-" + "1234567890-abcdefghij",
    "google-api-key": lambda: "AI" + "za" + "SyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q",
    "anthropic-key": lambda: "sk-" + "ant-" + "api03-" + "A1b2C3d4E5f6G7h8I9j0",
    "openai-key": lambda: "sk-" + "proj-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6",
    "stripe-key": lambda: "sk_" + "live_" + "A1b2C3d4E5f6G7h8I9j0",
    "huggingface-token": lambda: "hf" + "_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6",
    "private-key-block": lambda: "-----BEGIN " + "RSA PRIVATE KEY-----",
    "jwt": lambda: "eyJ" + "hbGciOiJIUzI1NiJ9" + "." + "eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0" + "." + "abcdefghij1234567890",
    "pypi-token": lambda: "pypi" + "-" + "A1b2C3d4E5f6G7h8I9j0" * 3,
    "npm-auth": lambda: "//registry.example.org/:_auth" + "Token=" + "abcd1234efgh5678",
    "basic-auth-url": lambda: "https://" + "user:" + "hunter2pass" + "@example.org/repo",
    "secret-assignment": lambda: 'api_key = "' + "Zq8Wp3Xn7Lm2Vb5Rt9" + '"',
}


@pytest.mark.parametrize("rule", sorted(FAKE_TOKENS))
def test_each_secret_pattern_is_detected_without_echoing_the_value(root, rule):
    value = FAKE_TOKENS[rule]()
    F.write(root / "notes.md", f"line one\nvalue: {value}\n")
    report = scan_secrets.scan(root, use_git=False)
    assert rule in codes(report), [f.render() for f in report.findings]
    assert report.status == C.FAIL
    rendered = " ".join(f.render() for f in report.findings)
    assert value not in rendered and value[:12] not in rendered
    finding = next(f for f in report.findings if f.code == rule)
    assert finding.path == "notes.md" and finding.line == 2


def test_clean_tree_passes(root):
    F.write(root / "a.md", "Nothing secret here. api_key = os.environ['KEY']\n")
    F.write(root / "b.py", "password = '<your-password-here>'\ntoken = 'changeme-token-value'\n")
    report = scan_secrets.scan(root, use_git=False)
    assert report.status == C.PASS and report.stats["files_scanned"] == 2


@pytest.mark.parametrize("placeholder", ["<your-api-key>", "${API_KEY_VALUE}", "xxxxxxxxxxxxxxxx", "example-key-value-123", "https://x.test/path/to", "aaaaaaaaaaaaaaaa"])
def test_placeholder_values_are_not_secrets(root, placeholder):
    F.write(root / "c.md", f'api_key = "{placeholder}"\n')
    assert scan_secrets.scan(root, use_git=False).status == C.PASS


@pytest.mark.parametrize("name", [".env", ".env.local", "deploy/.env.production", "server.pem", "id_rsa", "credentials.json", "keys/private.key"])
def test_secret_file_names_fail(root, name):
    F.write(root / name, "x\n")
    assert any(c.startswith("secret-file") for c in codes(scan_secrets.scan(root, use_git=False)))


@pytest.mark.parametrize("name", [".env.example", ".env.sample", "config.example.json"])
def test_template_files_are_fine(root, name):
    F.write(root / name, "KEY=\n")
    assert scan_secrets.scan(root, use_git=False).status == C.PASS


def test_pragma_and_allowlist(root):
    value = FAKE_TOKENS["github-token"]()
    F.write(root / "pragma.md", f"{value}  <!-- scan-ignore: documented fake -->\n")
    assert scan_secrets.scan(root, use_git=False).status == C.PASS
    F.write(root / "docs" / "fake.md", f"{value}\n")
    assert scan_secrets.scan(root, use_git=False).status == C.FAIL
    F.write(root / "scripts" / "secrets_allowlist.txt", "# why: documented fake\ndocs/fake.md :: github-token\n")
    assert scan_secrets.scan(root, use_git=False).status == C.PASS
    F.write(root / "scripts" / "secrets_allowlist.txt", "docs/fake.md :: some-other-rule\n")
    assert scan_secrets.scan(root, use_git=False).status == C.FAIL  # a rule-scoped entry does not whitelist other rules
    F.write(root / "scripts" / "secrets_allowlist.txt", "docs/**\n")
    assert scan_secrets.scan(root, use_git=False).status == C.PASS


def test_binary_and_oversized_files_are_skipped_not_misread(root):
    (root / "blob.bin").write_bytes(b"\0\1\2" + FAKE_TOKENS["github-token"]().encode())
    assert scan_secrets.scan(root, use_git=False).status == C.PASS


def test_secrets_cli_exit_codes_json_and_speed(root):
    F.write(root / "a.md", "clean\n")
    t = time.monotonic()
    assert F.run_cli(SECRETS_CLI, "--help").returncode == 0
    assert time.monotonic() - t < 3
    ok = F.run_cli(SECRETS_CLI, "--root", root, "--no-git")
    assert ok.returncode == 0 and "RESULT: PASS" in ok.stdout
    F.write(root / "leak.md", FAKE_TOKENS["aws-access-key"]() + "\n")
    bad = F.run_cli(SECRETS_CLI, "--root", root, "--no-git", "--json")
    assert bad.returncode == 1
    assert json.loads(bad.stdout)["status"] == "FAIL"
    assert FAKE_TOKENS["aws-access-key"]() not in bad.stdout
    assert F.run_cli(SECRETS_CLI, "--root", root / "nope").returncode == 2


def test_empty_tree_is_not_run(root):
    assert scan_secrets.scan(root, use_git=False).status == C.NOT_RUN


# ------------------------------------------------------------------ private

WIN_USER = "C:" + "\\Users\\" + "alice" + "\\Desktop"
WIN_USER_FWD = "d:" + "/Users/" + "bob" + "/proj"
MAC_USER = "/Users/" + "carol" + "/Movies"
LINUX_HOME = "/home/" + "dave" + "/work"
COURSE_PATH = "D:" + "\\" + "קורס" + " AI\\toolkit"
EMAIL = "someone" + "@" + "gmail" + ".com"


@pytest.mark.parametrize(
    "text,rule",
    [
        (f"open {WIN_USER}", "win-user-path"),
        (f"open {WIN_USER_FWD}", "win-user-path"),
        (f"open {MAC_USER}", "mac-user-path"),
        (f"cd {LINUX_HOME}", "linux-home-path"),
        (f"path {COURSE_PATH}", "owner-course-path"),
        ("see the knowledge" + "-pack folder", "knowledge-pack"),
        ("see Knowledge" + "_Pack", "knowledge-pack"),
        (f"mail {EMAIL}", "personal-email"),
        ("from brain" + "/Clients/acme", "private-brain-path"),
    ],
)
def test_private_patterns_detected_and_values_not_echoed(root, text, rule):
    F.write(root / "doc.md", f"first\n{text}\n")
    report = scan_private.scan(root, use_git=False)
    assert rule in codes(report), [f.render() for f in report.findings]
    finding = next(f for f in report.findings if f.code == rule)
    assert finding.path == "doc.md" and finding.line == 2
    rendered = " ".join(f.render() for f in report.findings)
    for secret in ("alice", "bob", "carol", "dave", "someone"):
        assert secret not in rendered


@pytest.mark.parametrize(
    "text",
    [
        "C:" + "\\Users\\" + "<user>\\Desktop",
        "C:" + "\\Users\\" + "%USERNAME%\\AppData",
        "C:" + "\\Users\\" + "Public\\Documents",
        "/Users/" + "<name>/Movies",
        "/home/" + "runner/work",
        "~/projects and $HOME/.cache",
        "reach us at name" + "@" + "example.com",
        "https://api.github.com/users/octocat",
    ],
)
def test_private_negative_controls_do_not_fire(root, text):
    F.write(root / "doc.md", text + "\n")
    report = scan_private.scan(root, use_git=False)
    assert report.fails == [], [f.render() for f in report.fails]


def test_private_paths_in_file_names_are_flagged(root):
    F.write(root / ("knowledge" + "-pack") / "x.md", "innocent\n")
    assert "knowledge-pack" in codes(scan_private.scan(root, use_git=False))


def test_owner_lab_path_is_a_warning_only(root):
    F.write(root / "doc.md", "work in D:" + "/avc-" + "lab/run\n")
    report = scan_private.scan(root, use_git=False)
    assert report.fails == [] and "owner-lab-path" in codes(report, "WARN")


def test_private_pragma_skips_line(root):
    F.write(root / "doc.md", f"{WIN_USER}  scan-ignore (documented example)\n")
    assert scan_private.scan(root, use_git=False).fails == []


# ---- denylist: NOT_RUN is explicit, never a silent PASS


def test_missing_denylist_reports_not_run_not_pass(root):
    F.write(root / "doc.md", "clean\n")
    report = scan_private.scan(root, use_git=False)
    assert report.fails == []
    assert report.status == C.NOT_RUN
    assert report.not_run_parts[0]["part"] == "denylist"


def test_require_denylist_turns_missing_into_fail(root):
    F.write(root / "doc.md", "clean\n")
    report = scan_private.scan(root, require_denylist=True, use_git=False)
    assert report.status == C.FAIL and "denylist-required" in codes(report)


def test_empty_or_comment_only_denylist_is_not_run(root):
    F.write(root / "doc.md", "clean\n")
    F.write(root / "scripts" / "private_denylist.txt", "# nothing active\n\n")
    assert scan_private.scan(root, use_git=False).status == C.NOT_RUN


def test_denylist_matches_and_never_prints_the_term(root):
    F.write(root / "scripts" / "private_denylist.txt", "# clients\nword:Zorblax Studios\nשם לקוח מומצא\nre:project[-_ ]\\d+\n")
    F.write(root / "ok.md", "Nothing to see. Zorblaxer is not a hit.\n")
    report = scan_private.scan(root, use_git=False)
    assert report.status == C.PASS and report.stats["denylist_entries"] == 3
    F.write(root / "a.md", "We edited for zorblax studios last year.\n")
    F.write(root / "b.md", "סרטון עבור שם לקוח מומצא בע\"מ\n")
    F.write(root / "c.md", "folder project-42 inside\n")
    report = scan_private.scan(root, use_git=False)
    hits = {(f.path, f.line) for f in report.findings if f.code == "denylist"}
    assert hits == {("a.md", 1), ("b.md", 1), ("c.md", 1)}
    rendered = " ".join(f.render() for f in report.findings)
    assert "Zorblax" not in rendered and "zorblax" not in rendered and "מומצא" not in rendered
    assert "entry #1" in rendered and "entry #2" in rendered


def test_denylist_checks_file_names_and_rejects_bad_regex(root):
    F.write(root / "scripts" / "private_denylist.txt", "Fictional Brand\n")
    F.write(root / "Fictional Brand Reel.md", "ok\n")
    assert "denylist" in codes(scan_private.scan(root, use_git=False))
    F.write(root / "scripts" / "private_denylist.txt", "re:(unclosed\n")
    assert "denylist-invalid" in codes(scan_private.scan(root, use_git=False))


def test_denylist_file_itself_and_scanner_sources_are_not_scanned(root):
    F.write(root / "scripts" / "private_denylist.txt", "Fictional Brand\n")
    report = scan_private.scan(root, use_git=False)
    assert report.fails == []  # the list holds the very terms it forbids elsewhere


def test_denylist_from_environment_variable(root, monkeypatch, tmp_path):
    deny = tmp_path / "external-deny.txt"
    deny.write_text("Fictional Brand\n", encoding="utf-8")
    F.write(root / "a.md", "Fictional Brand film\n")
    monkeypatch.setenv("AVC_PRIVATE_DENYLIST", str(deny))
    assert "denylist" in codes(scan_private.scan(root, use_git=False))


def test_private_cli_exit_codes(root):
    F.write(root / "doc.md", "clean\n")
    t = time.monotonic()
    assert F.run_cli(PRIVATE_CLI, "--help").returncode == 0
    assert time.monotonic() - t < 3
    # no denylist: exit 0 but loudly NOT_RUN; --strict exit 3; --require-denylist exit 1
    plain = F.run_cli(PRIVATE_CLI, "--root", root, "--no-git")
    assert plain.returncode == 0 and "RESULT: NOT_RUN" in plain.stdout and "[NOT_RUN] denylist" in plain.stdout
    assert F.run_cli(PRIVATE_CLI, "--root", root, "--no-git", "--strict").returncode == 3
    assert F.run_cli(PRIVATE_CLI, "--root", root, "--no-git", "--require-denylist").returncode == 1
    # with a usable denylist and a clean tree -> PASS
    F.write(root / "scripts" / "private_denylist.txt", "Fictional Brand\n")
    passed = F.run_cli(PRIVATE_CLI, "--root", root, "--no-git", "--strict")
    assert passed.returncode == 0 and "RESULT: PASS" in passed.stdout
    F.write(root / "doc.md", f"{WIN_USER}\n")
    leaked = F.run_cli(PRIVATE_CLI, "--root", root, "--no-git", "--json")
    assert leaked.returncode == 1 and "alice" not in leaked.stdout
    assert F.run_cli(PRIVATE_CLI, "--root", root / "nope").returncode == 2

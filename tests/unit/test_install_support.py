"""Shared helpers for the install/bootstrap tests (no tests here).

Safety rules for every install test:
  * HOME is a tmp folder (AVC_USER_HOME); the real home is never touched.
  * AVC_NO_REAL_EXEC=1 and bootstrap.run_cmd is replaced by FakeRun: NO real `claude mcp add`, winget, brew, npm, uv ever runs.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BOOTSTRAP_PATH = REPO / "install" / "bootstrap.py"


def load_bootstrap():
    spec = importlib.util.spec_from_file_location("avc_bootstrap_under_test", BOOTSTRAP_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["avc_bootstrap_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


SKILL_A = """---
name: alpha-skill
description: Alpha skill for tests. Hebrew trigger - תערוך סרטון.
metadata:
  version: "0.1.0"
---
# Alpha
See [reference](references/ref.md) and the playbook `agent-content/playbooks/wf-01-test.md` and `tools/doctor.py`.
"""
SKILL_B = """---
name: beta-skill
description: >-
  Beta skill
  folded description.
---
# Beta
"""


def make_fake_repo(root: Path, with_tools: bool = True) -> Path:
    """A tiny but realistic repo layout containing the REAL catalogue."""
    repo = root / "fake-repo"
    for rel, text in {
        "agent-content/skills/alpha-skill/SKILL.md": SKILL_A,
        "agent-content/skills/alpha-skill/references/ref.md": "# ref\n",
        "agent-content/skills/beta-skill/SKILL.md": SKILL_B,
        "agent-content/playbooks/wf-01-test.md": "# wf\n",
        "agent-content/techniques/t.md": "# t\n",
        "AGENTS.md": "# agents\n",
        "pyproject.toml": '[project]\nname="x"\nversion="9.9.9"\n',
    }.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    if with_tools:
        (repo / "tools").mkdir()
        (repo / "tools" / "doctor.py").write_text("print('doctor')\n", encoding="utf-8")
    (repo / "integrations").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / "integrations" / "catalog.toml", repo / "integrations" / "catalog.toml")
    shutil.copyfile(REPO / "integrations" / "referrals.toml", repo / "integrations" / "referrals.toml")
    return repo


class FakeRun:
    """Replacement for bootstrap.run_cmd. Records every argv; simulates just enough of ffmpeg/claude/uv/npm."""

    def __init__(self, bs, present=None, mcp_existing=None, fail=None):
        self.bs = bs
        self.calls = []
        self.present = set(present if present is not None else
                           {"git", "ffmpeg", "ffprobe", "node", "npm", "uv", "claude", "codex", "winget", "brew"})
        self.mcp = set(mcp_existing or [])
        self.plugins = {}  # id -> enabled
        self.markets = {}  # name -> source
        self.fail = fail or (lambda argv: False)
        self.gpu_text = ""  # what the GPU listing command returns on this fake machine

    def which(self, name):
        return "/fake/bin/" + name if name in self.present else None

    def __call__(self, argv, cwd=None, env=None, timeout=60):
        argv = [str(a) for a in argv]
        self.calls.append(argv)
        P = self.bs.Proc
        name = argv[0]
        if self.fail(argv):
            return P(argv, 1, "", "simulated failure")
        if name in ("ffmpeg", "ffprobe") and "-version" in argv:
            return P(argv, 0, "%s version 8.1 test build\n" % name)
        if name == "ffmpeg" and "libx264" in argv:
            Path(argv[-1]).write_bytes(b"fake-mp4")
            return P(argv, 0)
        if name == "ffprobe":
            return P(argv, 0, json.dumps({"streams": [{"codec_type": "video", "codec_name": "h264"}, {"codec_type": "audio", "codec_name": "aac"}],
                                          "format": {"duration": "1.000000"}}))
        if name in ("git", "node", "npm", "uv", "claude", "codex") and ("--version" in argv or "-v" in argv):
            return P(argv, 0, "%s 99.1.0\n" % name)
        if name == "claude" and argv[1:2] == ["plugin"]:
            return self._plugin(argv, P)
        if len(argv) >= 3 and argv[1:3] == ["mcp", "list"]:
            return P(argv, 0, "".join("%s: x - Connected\n" % n for n in sorted(self.mcp)))
        if len(argv) >= 3 and argv[1:3] == ["mcp", "add"]:
            # name = first positional after options; for stdio it is followed by "--"
            self.mcp.add(self._mcp_name(argv))
            return P(argv, 0)
        if len(argv) >= 3 and argv[1:3] == ["mcp", "remove"]:
            self.mcp.discard(argv[-1])
            return P(argv, 0)
        if name == "powershell" and "Win32_VideoController" in " ".join(argv):
            return P(argv, 0, self.gpu_text)
        if name == "wmic":
            return P(argv, 0, "Name\n" + self.gpu_text)
        if name == "nvidia-smi":
            return P(argv, 0, "GPU 0: NVIDIA GeForce RTX 4070 (UUID: GPU-x)\n")
        if name == "vulkaninfo":
            return P(argv, 0, "Vulkan Instance Version: 1.3\n")
        if name == "sysctl":
            return P(argv, 0, "17179869184\n")
        if name in ("uv", "npm", "winget", "brew"):
            return P(argv, 0, "ok")
        return P(argv, 0)

    def _plugin(self, argv, P):
        sub = argv[2:4]
        if sub[:1] == ["list"]:
            return P(argv, 0, json.dumps([{"id": i, "version": "0.4.0", "scope": "user", "enabled": en} for i, en in sorted(self.plugins.items())]))
        if sub == ["marketplace", "list"]:
            return P(argv, 0, json.dumps([{"name": n, "source": "github", "repo": src} for n, src in sorted(self.markets.items())]))
        if sub == ["marketplace", "add"]:
            self.markets["editing-workflow"] = argv[4]
            return P(argv, 0)
        if sub == ["marketplace", "remove"]:
            self.markets.pop(argv[4], None)
            return P(argv, 0)
        if sub[:1] == ["install"]:
            if "editing-workflow" not in self.markets:
                return P(argv, 1, "", "marketplace not found")
            self.plugins[argv[3]] = True
            return P(argv, 0)
        if sub[:1] == ["uninstall"]:
            self.plugins.pop(argv[3], None)
            return P(argv, 0)
        return P(argv, 0)

    @staticmethod
    def _mcp_name(argv):
        i = 3
        flags_with_value = {"--scope", "-s", "--transport", "--env", "-e", "--header", "-H"}
        while i < len(argv):
            if argv[i] in flags_with_value:
                i += 2
            elif argv[i].startswith("-"):
                i += 1
            else:
                return argv[i]
        return "?"

    def commands(self, first, second=None):
        """Every recorded call of `first` (optionally with subcommand `second`), probes included."""
        return [c for c in self.calls if c[0] == first and (second is None or c[1:2] == [second])]

    def actions(self, first, second=None):
        """Like commands() but without read-only probes (--version / -version / mcp list)."""
        return [c for c in self.commands(first, second) if not (set(c[1:2]) & {"--version", "-version", "-v"}) and c[1:3] != ["mcp", "list"] and c[1:4] not in (["plugin", "list", "--json"], ["plugin", "marketplace", "list"])]


def install_fakes(monkeypatch, bs, **kw) -> FakeRun:
    fake = FakeRun(bs, **kw)
    monkeypatch.setattr(bs, "run_cmd", fake)
    monkeypatch.setattr(bs, "which", fake.which)
    return fake


def run_main(bs, argv):
    return bs.main(argv)


# ----------------------------------------------------------------------------- pytest fixture + runner
import contextlib
import io
from types import SimpleNamespace

import pytest


class Env(SimpleNamespace):
    def run(self, *args, repo=True, target="both", work=True, expect=None):
        """Run bootstrap.main with a fake repo; returns (exit_code, stdout, stderr)."""
        argv = list(args)
        tail = []
        if "--" in argv:  # `run -- cmd ...`: options must stay before the double dash
            i = argv.index("--")
            argv, tail = argv[:i], argv[i:]
        if repo:
            argv += ["--repo", str(self.repo)]
        if target and "--target" not in argv:
            argv += ["--target", target]
        if "--skills-via" not in argv:
            argv += ["--skills-via", "copy"]  # most tests exercise the copy route; plugin tests pass --skills-via plugin
        if work and "--work-root" not in argv:
            argv += ["--work-root", str(self.tmp / "work")]
        argv += tail
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                rc = self.bs.main(argv)
            except SystemExit as e:
                rc = e.code if isinstance(e.code, int) else 99
                err.write(str(e.code))
        if expect is not None:
            assert rc == expect, "exit %s != %s\nSTDOUT:\n%s\nSTDERR:\n%s" % (rc, expect, out.getvalue(), err.getvalue())
        return rc, out.getvalue(), err.getvalue()

    def json(self, *args, **kw):
        rc, out, err = self.run(*args, "--json", **kw)
        return rc, json.loads(out)

    @property
    def claude(self):
        return self.home / ".claude" / "skills"

    @property
    def codex(self):
        return self.home / ".agents" / "skills"

    @property
    def state(self):
        return self.home / ".avc"

    def manifest(self):
        return json.loads((self.state / "install-manifest.json").read_text(encoding="utf-8"))


@pytest.fixture
def env(tmp_path, monkeypatch):
    bs = load_bootstrap()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("AVC_USER_HOME", str(home))
    monkeypatch.setenv("AVC_NO_REAL_EXEC", "1")
    monkeypatch.delenv("AVC_WORK_ROOT", raising=False)
    repo = make_fake_repo(tmp_path)
    fake = install_fakes(monkeypatch, bs)
    return Env(bs=bs, home=home, repo=repo, fake=fake, tmp=tmp_path)

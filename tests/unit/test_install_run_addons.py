"""`run` launcher (same behaviour in PowerShell/CMD/bash) and add-on routes (ASR env, weights never downloaded, native plugins by hand)."""
import tomllib

from test_install_support import *  # noqa: F401,F403


def test_run_substitutes_tokens_sets_environment_and_uses_toolkit_python(env, monkeypatch):
    env.run("apply", "--yes", expect=0)
    seen = {}

    def fake_pass(argv, cwd, e):
        seen.update(argv=argv, cwd=cwd, env=e)
        return 7

    monkeypatch.setattr(env.bs, "passthrough", fake_pass)
    rc, out, err = env.run("run", "--", "python", "-m", "core", "probe", "{work_root}/x.mp4", target=None, work=False)
    assert rc == 7  # exit code of the child is passed through
    home = env.state / "toolkit"
    assert seen["cwd"] == home
    assert seen["argv"][seen["argv"].index("-m"):] == ["-m", "core", "probe", str(env.tmp / "work") + "/x.mp4"]
    assert seen["argv"][0] != "python"  # resolved to the toolkit's own interpreter (.venv) or `uv run --project <home>`
    assert seen["env"]["PYTHONPATH"].split(env.bs.os.pathsep)[0] == str(home / "src")
    assert seen["env"]["PYTHONUTF8"] == "1" and seen["env"]["HYPERFRAMES_NO_TELEMETRY"] == "1"
    assert seen["env"]["AVC_PATHS_WORK_ROOT"] == str(env.tmp / "work")


def test_run_refuses_when_not_installed_or_without_command(env):
    rc, out, err = env.run("run", "--", "python", "-V", target=None, work=False)
    assert rc == 2 and "not installed" in err
    env.run("apply", "--yes", expect=0)
    rc, out, err = env.run("run", target=None, work=False)
    assert rc == 1


def test_asr_cpu_addon_creates_separate_env_pins_package_and_records_it(env):
    rc, out = env.json("apply", "--yes", "--with", "asr-cpu")
    assert rc == 0
    assert "weights NOT downloaded" in out["stages"]["pylib_faster-whisper"]
    venv = [c for c in env.fake.actions("uv", "venv")]
    pip = [c for c in env.fake.actions("uv", "pip")]
    assert venv and pip and "faster-whisper==1.2.1" in pip[0]
    assert str(env.state / "venvs" / "asr-cpu") in " ".join(venv[0])
    cfg = tomllib.loads((env.state / "toolkit" / "toolkit.local.toml").read_text(encoding="utf-8"))
    assert cfg["paths"]["work_root"].endswith("/work") and cfg["models"]["asr_venv"].endswith("asr-cpu")
    # nothing that looks like a model download was attempted
    assert not [c for c in env.fake.calls if any("huggingface" in a or "ivrit" in a for a in c)]
    env.run("uninstall", "--yes", target=None, work=False, expect=0)
    assert not (env.state / "toolkit").exists()


def test_model_weights_are_listed_but_never_downloaded(env):
    rc, plan = env.json("plan", "--with", "asr-vulkan")
    assert any("NOT downloaded by bootstrap" in d["what"] for d in plan["downloads"])
    rc, out = env.json("apply", "--yes", "--with", "asr-vulkan")
    assert not [c for c in env.fake.calls if any("huggingface" in a for a in c)]


def test_native_plugins_are_reported_for_manual_install_only(env):
    rc, plan = env.json("plan", "--profile", "pro", "--with", "nle-premiere,nle-ae,blender")
    ids = {r["id"] for r in plan["by_hand_plugins"]}
    assert {"nle-premiere", "nle-ae"} <= ids
    blender = [m for m in plan["mcp"] if m["id"] == "blender-mcp"]
    assert blender and blender[0]["register"] == "manual"  # port 9876 has no authentication: never auto-connected
    rc, out = env.json("apply", "--yes", "--profile", "pro", "--with", "nle-premiere,blender")
    assert not [c for c in env.fake.calls if "blender" in " ".join(c).lower() and "mcp" in c and "add" in c]


def test_existing_toolkit_local_toml_written_by_the_user_is_not_overwritten(env):
    home = env.state / "toolkit"
    home.mkdir(parents=True)
    (home / "toolkit.local.toml").write_text("[paths]\nwork_root = 'D:/mine'\n", encoding="utf-8")
    rc, out = env.json("apply", "--yes")
    assert "kept existing" in out["stages"]["toolkit_local_toml"]
    assert "D:/mine" in (home / "toolkit.local.toml").read_text(encoding="utf-8")
    env.run("uninstall", "--yes", target=None, work=False, expect=0)
    assert (home / "toolkit.local.toml").is_file()  # not ours -> not removed

"""Hardware is detected, never asked: routes chosen automatically with a CPU fallback; `add <id>` for everything optional."""
import json

import pytest

from test_install_support import *  # noqa: F401,F403


# ----------------------------------------------------------------------------- pure parsers / route choice
def test_gpu_vendor_classification():
    bs = load_bootstrap()
    cases = {"NVIDIA GeForce RTX 4070 Laptop GPU": "NVIDIA", "AMD one reference machine": "AMD", "Intel(R) UHD Graphics 770": "Intel",
             "Intel(R) Arc(TM) A370M Graphics": "Intel", "Apple M3 Pro": "Apple", "Microsoft Basic Render Driver": "virtual",
             "VMware SVGA 3D": "virtual", "Some Unknown Adapter": "unknown"}
    for name, vendor in cases.items():
        assert bs.classify_gpu(name) == vendor, name
    parsed = bs.parse_gpu_names("Name\n----\nNVIDIA GeForce GTX 1650\nIntel(R) UHD Graphics\n\n")
    assert [g["vendor"] for g in parsed] == ["NVIDIA", "Intel"]


@pytest.mark.parametrize("machine,expected", [("AMD64", "x64"), ("x86_64", "x64"), ("arm64", "arm64"), ("aarch64", "arm64"), ("riscv64", "riscv64"), ("", "unknown")])
def test_arch_normalisation(machine, expected):
    assert load_bootstrap().normalize_arch(machine) == expected


HW_CASES = {
    "windows-nvidia": {"os": "windows", "arch": "x64", "gpu_vendors": ["NVIDIA"], "gpus": [{"name": "RTX", "vendor": "NVIDIA"}]},
    "windows-amd": {"os": "windows", "arch": "x64", "gpu_vendors": ["AMD"], "gpus": [{"name": "Radeon", "vendor": "AMD"}]},
    "windows-intel-igpu": {"os": "windows", "arch": "x64", "gpu_vendors": ["Intel"], "gpus": [{"name": "UHD", "vendor": "Intel"}]},
    "mac-apple-silicon": {"os": "macos", "arch": "arm64", "gpu_vendors": ["Apple"], "gpus": [{"name": "Apple", "vendor": "Apple"}]},
    "linux-no-gpu": {"os": "linux", "arch": "x64", "gpu_vendors": [], "gpus": []},
    "vm-virtual-gpu": {"os": "windows", "arch": "x64", "gpu_vendors": ["virtual"], "gpus": [{"name": "Hyper-V", "vendor": "virtual"}]},
    "linux-arm64": {"os": "linux", "arch": "arm64", "gpu_vendors": [], "gpus": []},
}


@pytest.mark.parametrize("case", sorted(HW_CASES))
def test_cpu_baseline_is_always_chosen_whatever_the_hardware(case):
    bs = load_bootstrap()
    hw = HW_CASES[case]
    routes = bs.choose_routes(hw)
    assert routes["asr"]["chosen"] == "asr-cpu" and routes["matte"]["chosen"] == "native-cpu" and routes["encoder"]["chosen"].startswith("libx264")
    assert "accelerated_candidates" not in routes["asr"]  # one transcription route, nothing to offer on top
    assert routes["never_required"] == ["matte-fast"]


def test_hardware_findings_thresholds_are_labelled_as_not_measured():
    bs = load_bootstrap()
    gib = 1024 ** 3
    w, b = bs.hardware_findings({"os": "windows", "arch": "x64", "ram_bytes": 8 * gib, "free_disk_bytes": 5 * gib, "gpus": []})
    assert not b and any("16 GB" in x and "not a measured minimum" in x for x in w) and any("free" in x for x in w)
    w, b = bs.hardware_findings({"os": "linux", "arch": "x64", "ram_bytes": 32 * gib, "free_disk_bytes": gib // 2, "gpus": []})
    assert b and "1 GB" in b[0]
    w, b = bs.hardware_findings({"os": "windows", "arch": "arm64", "ram_bytes": 32 * gib, "free_disk_bytes": 100 * gib, "gpus": [{"name": "x", "vendor": "virtual"}]})
    assert not b and any("arm64" in x and "unmeasured" in x for x in w) and any("CPU routes only" in x for x in w)
    w, b = bs.hardware_findings({"os": "macos", "arch": "arm64", "ram_bytes": 32 * gib, "free_disk_bytes": 100 * gib, "gpus": []})
    assert not w and not b  # Apple Silicon is not a warning


# ----------------------------------------------------------------------------- through plan / apply
def test_plan_detects_everything_and_asks_no_hardware_question(env):
    env.fake.gpu_text = "NVIDIA GeForce RTX 4070 Laptop GPU"
    env.fake.present |= {"nvidia-smi", "powershell", "lspci", "system_profiler"}
    rc, plan = env.json("plan")
    assert rc == 0
    hw = plan["hardware"]
    assert hw["arch"] in ("x64", "arm64") and hw["cpu_logical"] and "ram_bytes" in hw and hw["free_disk_bytes"]
    assert plan["questions"]["hardware_questions"].startswith("none")
    assert set(plan["questions"]) == {"mode", "confirmation", "optional", "hardware_questions"}
    assert "LOCAL" in plan["questions"]["mode"] and "CONNECTED" in plan["questions"]["mode"]
    assert plan["routes"]["asr"]["chosen"] == "asr-cpu"
    assert plan["selection"]["auto"] == [] and plan["selection"]["local"] is False  # nothing local-AI without the student's choice
    rc, plan = env.json("plan", "--local")
    assert plan["selection"]["auto"] == ["asr-cpu"] and plan["selection"]["with"] == [] and plan["selection"]["local"] is True
    assert plan["selection"]["profile"] == "minimal" and plan["mcp"] == []  # neutral and free by default
    if env.bs.os_name() == "windows":
        assert [g["vendor"] for g in hw["gpus"]] == ["NVIDIA"]
    assert "accelerator_probes" not in plan  # no GPU route is probed or offered


def test_a_detected_gpu_changes_nothing_that_is_installed(env):
    env.fake.gpu_text = "NVIDIA GeForce RTX 4070"
    env.fake.present |= {"nvidia-smi", "vulkaninfo", "powershell"}
    env.run("apply", "--yes", "--local", expect=0)
    cmds = [c[0] for c in env.fake.calls]
    pip = env.fake.actions("uv", "pip")
    assert len(pip) == 1 and "faster-whisper==1.2.1" in pip[0]  # the CPU route only
    assert not [c for c in env.fake.calls if any("cuda" in a.lower() or "vulkan" in a.lower() or "whisper.cpp" in a.lower() for a in c) and c[0] not in ("vulkaninfo", "nvidia-smi")]  # no GPU runtime is installed


def test_low_disk_blocks_and_auto_route_is_skipped(env, monkeypatch):
    real = env.bs.shutil.disk_usage
    monkeypatch.setattr(env.bs.shutil, "disk_usage", lambda p: type("U", (), {"free": 100 * 1024 ** 2, "total": 1, "used": 1})())
    rc, plan = env.json("plan")
    assert rc == 2 and any("free on the install drive" in b for b in plan["blockers"])
    assert plan["selection"]["auto"] == []


def test_auto_cpu_route_can_be_switched_off_and_never_downloads_weights(env):
    rc, plan = env.json("plan")
    assert plan["selection"]["auto"] == []
    env.run("apply", "--yes", expect=0)
    assert not env.fake.actions("uv", "pip")
    env.run("apply", "--yes", "--local", expect=0)
    assert env.fake.actions("uv", "pip")  # the CPU route is set up only after the student chose to work locally
    assert not [c for c in env.fake.calls if any("huggingface" in a for a in c)]


def test_defaults_carry_no_vendor_or_hardware_specific_choice(env):
    rc, plan = env.json("plan")
    sel = plan["selection"]
    assert sel["profile"] == "minimal" and sel["with"] == [] and sel["engine"] == "hyperframes"
    assert plan["mcp"] == [] and plan["by_hand_plugins"] == []
    names = json.dumps(plan).lower()
    for taste in ("21st", "higgsfield", "elevenlabs"):
        assert taste not in names, taste
    assert "GGML_VK_DISABLE_COOPMAT" not in json.dumps(plan)


# ----------------------------------------------------------------------------- add <integration>
def test_add_list_shows_every_integration(env):
    rc, rows = env.json("add", "--list", repo=True, target=None, work=False)
    ids = {r["id"] for r in rows}
    assert {"playwright", "higgsfield", "elevenlabs", "blender-mcp", "faster-whisper", "yt-dlp"} <= ids
    assert "whisper-cpp" not in ids and "ivrit-ggml" not in ids
    assert next(r for r in rows if r["id"] == "luma-legacy-mcp")["avoid"] is True


def test_add_is_a_read_only_plan_without_yes(env):
    env.run("apply", "--yes", expect=0)
    n = len(env.fake.calls)
    rc, out = env.json("add", "playwright", target=None, work=False)
    assert rc == 0 and out["mode"].startswith("plan")
    assert out["results"][0]["actions"][0]["status"] == "will-register"
    assert not [c for c in env.fake.calls[n:] if c[:3] == ["claude", "mcp", "add"]]


def test_add_playwright_registers_exactly_the_standard_server(env):
    env.run("apply", "--yes", expect=0)
    rc, out = env.json("add", "playwright", "--yes", target=None, work=False)
    assert rc == 0
    added = [c for c in env.fake.actions("claude", "mcp") if c[2] == "add"]
    assert len(added) == 2 or len(added) == 1  # claude (+ codex handled separately)
    assert added[0][3:5] == ["--scope", "user"] and "avc-playwright" in added[0] and "@playwright/mcp@0.0.83" in added[0]
    m = env.manifest()
    assert any(r["name"] == "avc-playwright" for r in m["mcp"]) and m["added"][0]["id"] == "playwright"
    # uninstall removes what `add` registered
    env.run("uninstall", "--yes", target=None, work=False, expect=0)
    assert [c for c in env.fake.actions("claude", "mcp") if c[2] == "remove"]


def test_add_key_based_provider_never_registers_and_never_touches_the_key(env, monkeypatch):
    monkeypatch.setenv("TWENTYFIRST_API_KEY", "super-secret-value-123")
    env.run("apply", "--yes", expect=0)
    rc, out = env.json("add", "magic-21st", "--yes", target=None, work=False)
    assert rc == 0
    r = out["results"][0]
    assert r["gate"] == "paid-spend-gate" and "not spend authorisation" in r["note"]
    assert r["env_var"]["name"] == "TWENTYFIRST_API_KEY" and r["env_var"]["present"] is True
    assert all(a["status"] == "manual" for a in r["actions"])
    assert not [c for c in env.fake.actions("claude", "mcp") if c[2] == "add"]
    assert "super-secret-value-123" not in json.dumps(out)


def test_add_resolves_addon_names_and_refuses_avoid_and_unknown(env):
    env.run("apply", "--yes", expect=0)
    rc, out = env.json("add", "provider-elevenlabs", target=None, work=False)
    assert rc == 0 and [r["id"] for r in out["results"]] == ["elevenlabs"]
    rc, o, err = env.run("add", "luma-legacy-mcp", target=None, work=False)
    assert rc == 2 and "avoid list" in err
    rc, o, err = env.run("add", "does-not-exist", target=None, work=False)
    assert rc == 1 and "unknown integration" in err
    rc, o, err = env.run("add", target=None, work=False)
    assert rc == 1


def test_add_requires_an_installed_toolkit_to_do_anything(env):
    rc, o, err = env.run("add", "playwright", "--yes", target=None, work=False)
    assert rc == 2 and "not installed" in err


def test_add_model_is_instructions_only(env):
    env.run("apply", "--yes", expect=0)
    n = len(env.fake.calls)
    rc, out = env.json("add", "ivrit-ct2", "--yes", target=None, work=False)
    assert out["results"][0]["actions"][0]["status"] == "never downloaded by the installer"
    assert not [c for c in env.fake.calls[n:] if c[0] in ("claude", "codex", "uv", "npm", "winget", "brew") and c[1:2] not in (["--version"], ["mcp"])]


def test_add_cli_runs_the_exact_package_manager_command_only_with_install_missing(env):
    env.run("apply", "--yes", expect=0)
    env.fake.present.discard("yt-dlp")
    rc, out = env.json("add", "yt-dlp", "--yes", target=None, work=False)
    assert not [c for c in env.fake.calls if c[0] in ("winget", "brew") and "yt-dlp" in " ".join(c)]
    env.json("add", "yt-dlp", "--yes", "--install-missing", target=None, work=False)
    ran = [c for c in env.fake.calls if c[0] in ("winget", "brew") and "yt-dlp" in " ".join(c)]
    if env.bs.os_name() in ("windows", "macos"):
        assert ran


def test_add_python_route_creates_its_own_env_without_weights(env):
    env.run("apply", "--yes", expect=0)
    rc, out = env.json("add", "faster-whisper", "--yes", target=None, work=False)
    assert rc == 0 and "weights NOT downloaded" in out["results"][0]["actions"][0]["status"]
    assert env.fake.actions("uv", "venv") and env.fake.actions("uv", "pip")

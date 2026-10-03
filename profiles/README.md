# Profiles

> Written 2026-10-02 from the research record. **No installer exists yet; nothing here was run on a student machine.** Profile facts are perishable — each profile carries `checked_at` and `expires` in its `profile.toml`; refresh before relying on a size, version or timing.

A **profile** is an opt-in bundle of runtime pieces (Python extras, models, native tools, accounts) with a machine-readable manifest (`profile.toml`) and a human page (`README.md`). The default profile is `core-cpu`: no API key, no GPU, no paid call, no account beyond the agent client. Everything else is opt-in and separately authorised.

| Profile | Purpose | Evidence state | Python extra(s) | Folder |
|---|---|---|---|---|
| `core-cpu` (default) | probes, FFmpeg utilities, QA fixture path, HyperFrames render on CPU | **measured** (the reference machine) | none required (optional: `opencv`, `color`, `analysis`) | [core-cpu/](core-cpu/) |
| `asr-cpu` | Hebrew ASR, faster-whisper CT2 int8 | **measured** (the reference machine) | `asr-cpu` | [asr-cpu/](asr-cpu/) |
| `asr-vulkan` | Hebrew ASR, whisper.cpp + Vulkan (Windows AMD/Intel GPUs) | **measured** on the reference machine's GPU only | `asr-vulkan` | [asr-vulkan/](asr-vulkan/) |
| `asr-cuda` | Hebrew ASR, CT2 + CUDA 12 / cuDNN 9 | **unmeasured** (documentation only) | none defined | [asr-cuda/](asr-cuda/) |
| `asr-mlx` | Hebrew ASR on Apple Silicon (Metal/CoreML/MLX) | **unmeasured**; no verified Hebrew weights | none defined | [asr-mlx/](asr-mlx/) |
| `matte-fast` | person matte: RVM+DirectML (internal-only) / MODNet (bundle-safe) | **measured** (the reference machine) | `matte` | [matte-fast/](matte-fast/) |
| `blender` | Blender headless/MCP for 3D | **sourced** (timings measured at small sizes) | none defined | [blender/](blender/) |
| `nle-premiere` | Premiere Pro bridge | **unmeasured** | none defined | [nle-premiere/](nle-premiere/) |
| `nle-ae` | After Effects bridge | **unmeasured** | none defined | [nle-ae/](nle-ae/) |
| `cloud-template` | template for a cloud provider profile (copy to `cloud-<provider>`) | **unmeasured** | none defined | [cloud-template/](cloud-template/) |

## Three states, never confused — **unsupported ≠ missing ≠ error**
| State | Meaning | Example | Effect on the core |
|---|---|---|---|
| `unsupported` | this machine/OS/driver cannot run the profile (a documented or probed fact) | `asr-vulkan` on a machine without a Vulkan GPU | none; the core stays green; the profile is hidden or greyed with the reason |
| `missing` | the machine could run it but the pieces are not installed | `asr-cpu` before `uv sync --extra asr-cpu` | none; offer the install, show the download size first |
| `error` | the pieces are there and a real tiny job failed | whisper.cpp starts and crashes | reported with evidence; **never** turns the core red; never silently falls back to a paid route |
A profile never reports `pass` from a *listed* capability: an advertised GPU, encoder or device does not count — a real tiny job must run (NVENC and QSV were *listed* but failed to initialise on the reference machine's host). A check that cannot run reports `not_run`.

## Rules shared by all profiles
1. **Show before doing:** prerequisites, download sizes, network traffic, credentials, cost, cache location, how to remove it.
2. **No hidden global mutation:** scoped managed runtimes (`uv`-managed Python, project-pinned Node). Do not update system Python/Node, do not auto-install package managers/WSL/Docker.
3. **Pins:** model weights are pinned independently of runtime packages (revision, bytes, licence). Separate Python environments per ASR/matte route (torch-directml pins torch 2.4.1; ROCm recipes use torch 2.13).
4. **Sizes are sourced or marked unmeasured.** A size not recorded by the research is written `unmeasured` — never estimated.
5. **Weak-machine fallbacks** (cloud GPU, Codespaces, cloud render) are opt-in with real quotes; the cloud-assisted student profile (4-core / 16 GB / SSD / network) is an **instructor recommendation, not a measured minimum**; the owner's 8-core / 32 GB laptop is the only measured machine.
6. **Extras names** match the optional-dependency groups of `pyproject.toml` (owned by the core agent; names assumed here: `asr-cpu`, `asr-vulkan`, `matte`, `opencv`, `color`, `analysis`). If `pyproject.toml` differs, it wins and the profile manifests are corrected.
7. **No telemetry endpoint of the toolkit.** Dependency telemetry opt-outs are listed per profile where they exist.

## Manifest schema (`profile.toml`, schema `avc-profile/1`)
Top level: `schema`, `id`, `title`, `status` (`default`|`optional`), `evidence_state` (`measured`|`sourced`|`unmeasured`), `checked_at`, `expires`. Tables: `[install]` (python extras, system tools, models, accounts, spend), `[hardware]`, `[tested_on]`, `[states]` (conditions for `unsupported` / `missing` / `error`), `[licences]`, `[uninstall]`. Machine readers must treat any field they do not know as informational.

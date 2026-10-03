# Profile `asr-cuda` — unmeasured

> Dated 2026-10-02 · evidence state **unmeasured (documentation only)** · expires 2026-12-31. **unsupported ≠ missing ≠ error.**

## Honest status
No NVIDIA machine was available to the research. **Everything below is what the documentation says, not what anyone ran.** This profile is a placeholder with a manifest so the doctor can report it as `unsupported` / `missing` / `error` correctly; it does **not** promise a speed-up. Do not quote any figure from the AMD/Vulkan or CPU profiles for it, and do not quote published faster-whisper speeds (they are machine-specific).

## What it would install
**faster-whisper 1.2.1** with CTranslate2 on **CUDA 12 + cuDNN 9** (current README requirement; set an explicit compute type; old fallback version pins are not a default recipe), same weights as `asr-cpu` (ivrit-ai turbo CT2, revision `72ad623a37947395efcc3933132353790e5a12f5`, 1,617,884,968 B + 3,780,213 B). Alternative: whisper.cpp built with CUDA. No Python extra group exists for it yet (the named groups are `asr-cpu`, `asr-vulkan`, `matte`, `opencv`, `color`, `analysis`); the `pyproject.toml` owner decides. Use a **separate Python environment**. The toolkit never installs CUDA or cuDNN globally; if the student installs them, removing them is the student's job.

## Download size and source
Model sizes as for `asr-cpu` (sourced). CUDA toolkit / cuDNN / wheels: **unmeasured**.

## Hardware
An NVIDIA GPU with a CUDA-12-capable driver. VRAM requirement: **unmeasured**.

## Tested-on evidence
**None.** CTranslate2's prebuilt binaries document CPU (x86-64, ARM64) and NVIDIA CUDA support; that is the whole evidence. The doctor must run the tiny Hebrew fixture on the student's machine and write the real result into `docs/capabilities/`. Until then the state is `not_run`.

## States
| State | When |
|---|---|
| `unsupported` | a real probe finds no NVIDIA GPU or no CUDA-12-capable driver |
| `missing` | runtime or model not installed |
| `error` | runtime loads but CUDA initialisation fails, or the tiny fixture fails / returns empty text |
A *listed* GPU or CUDA library is not proof — the tiny job decides. The fallback is `asr-cpu` (measured), never a paid cloud ASR.

## Licences
faster-whisper and CTranslate2: MIT. NVIDIA CUDA/cuDNN: NVIDIA terms — not bundled. Weights: Apache-2.0 declared on the exact checkpoint; the ONNX conversions are unresolved and excluded.

## Uninstall
Delete the profile environment and the model cache. Anything the student installed system-wide (drivers, CUDA, cuDNN) stays under the student's control.

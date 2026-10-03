# Profile `asr-vulkan`

> Dated 2026-10-02 · evidence state **measured on one AMD GPU only** · expires 2026-12-31 or on any pin/driver change. **unsupported ≠ missing ≠ error.**

## What it installs
Hebrew speech recognition on a **Vulkan GPU** through **whisper.cpp** (GGML) with the ivrit-ai turbo checkpoint. Python extra **`asr-vulkan`** (wrapper-side dependencies; contents defined in `pyproject.toml`). The `whisper-cli` binary is **native**: build it from source with `-DGGML_VULKAN=ON`, or obtain a Vulkan-enabled binary yourself — the official Windows b5130 release asset has only CPU/BLAS variants. Measured build recipe (the reference machine): CMake 4.3.1, Vulkan SDK 1.4.357.0, Visual Studio 17 2022 generator; `cmake -S <src> -B <build> -G "Visual Studio 17 2022" -A x64 -DGGML_VULKAN=ON -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_SERVER=OFF`, then `cmake --build <build> --config Release --target whisper-cli --parallel 4`. **The build toolchain is a real cost for a student**: configure 33.5 s, compile 248.5 s on the reference machine, plus installing the toolchain (size unmeasured). The toolkit explains each step; it never installs the toolchain silently.

Required on the reference GPU's driver: environment variable **`GGML_VK_DISABLE_COOPMAT=1`** (otherwise whisper.cpp crashed). `[LOCAL-only]` — on another driver test with and without it. `whisper-cli` breaks on Hebrew file paths: the tool copies audio to an ASCII temp directory.

## Download size and source
Model **1,624,555,275 B** (revision `2130c78e4a9cb4914cc4df91a1c3031407789705`; model card, T08-S003); whisper.cpp source ZIP **10,476,278 B** (E08); toolchain installs: `unmeasured`.

## Hardware
A Vulkan-capable GPU and a current driver. Measured only on **the reference machine**; process memory sampled 0.19 GB (GPU memory not included). Peak VRAM, power and thermals: **unmeasured**.

## Tested-on evidence (the reference machine only — **measured**, single pass each)
68 FLEURS clips, 614.22 s of Hebrew read speech: **Vulkan 8 threads 105.604 s** (5.816 audio-seconds per wall-second, 212 / 1,161 word edits, WER 18.260%) vs the **same build on CPU 1,033.045 s** → **9.78× faster** (10.0× launch-to-finalisation); vs CTranslate2 int8 CPU 731.384 s → 6.93×. Vulkan with 4 / 8 / 16 threads: 104.9 / 105.6 / 106.3 s with byte-identical transcripts — no thread winner. The GPU and CPU hypotheses differ slightly (212 vs 210 word edits): no equivalence claim. `[CONFLICT]` an earlier owner measurement found only 2.4× on a loaded machine; **quote the 9.8× with its scope and tell students to re-measure on their own hardware.** Extrapolation to one hour (assumes read-speech throughput carries over — not established): about 10 min. Not tested: NVIDIA/Intel GPUs through Vulkan, Linux, macOS, long or spontaneous speech.

## States
| State | When |
|---|---|
| `unsupported` | a real device probe finds no Vulkan device/driver, or the OS has no build recipe |
| `missing` | no Vulkan-enabled `whisper-cli`, model not present, or extra not installed |
| `error` | the binary starts and crashes, reports no Vulkan device, or fails the tiny Hebrew fixture — check `GGML_VK_DISABLE_COOPMAT=1` first |
On `error` the toolkit falls back to `asr-cpu` **and says so**; it never falls back to a paid route.

## Licences
whisper.cpp: MIT. Weights: Apache-2.0 declared on the exact ivrit-ai GGML checkpoint. The ONNX conversions of the same model are **unresolved** and not part of this profile.

## Uninstall
Delete the build directory, `whisper-cli`, the model cache (≈ 1.6 GB) and the `asr-vulkan` environment. CMake, the Vulkan SDK and Visual Studio were installed by the student, not by the toolkit; the toolkit does not remove them.

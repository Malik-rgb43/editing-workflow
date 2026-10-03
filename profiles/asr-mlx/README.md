# Profile `asr-mlx` — unmeasured

> Dated 2026-10-02 · evidence state **unmeasured (documentation only)** · expires 2026-12-31. **unsupported ≠ missing ≠ error.**

## Honest status
No Apple machine was available to the research, and **no MLX-format Hebrew model was verified**. The ivrit-ai formats the research recorded are CTranslate2, GGML, Transformers and ONNX (ONNX unresolved). The profile therefore lists *candidate routes*, not a recommendation, and does not promise any speed. It exists so the doctor reports Mac machines truthfully (`unsupported` / `missing` / `error` / `not_run`) and so the first Mac student's measurement can be written into `docs/capabilities/`.

## Candidate routes (none run)
1. **whisper.cpp with Metal** using the same GGML Hebrew checkpoint as `asr-vulkan` (revision `2130c78e4a9cb4914cc4df91a1c3031407789705`, 1,624,555,275 B). 2. whisper.cpp **CoreML** encoder conversion (conversion cost and startup untested). 3. **CPU control**: faster-whisper CT2 int8 on ARM64 — documented as CPU support, **not** Metal. MLX itself: different model formats; no verified Hebrew weights.

## Download size and source
Checkpoint size sourced (1,624,555,275 B); CoreML conversion output and toolchain: `unmeasured`.

## Hardware
Apple Silicon; unified-memory requirement `unmeasured`. A total of 16 GB is not "15 GB free". Intel Macs are outside this profile.

## Tested-on evidence
**None.** whisper.cpp documents Metal/CoreML; that is all. State `not_run` until a Mac runs the tiny Hebrew fixture.

## States
| State | When |
|---|---|
| `unsupported` | not Apple Silicon, or an OS older than the chosen build needs |
| `missing` | no Metal/CoreML runtime build, or the model is not present |
| `error` | the runtime starts but the tiny fixture fails or returns empty text |
Fallback: `asr-cpu` (ARM64 CPU control). Never a paid cloud ASR.

## Licences
whisper.cpp MIT; weights Apache-2.0 declared on the exact checkpoint. ONNX conversions unresolved — excluded.

## Uninstall
Delete the runtime build, the model cache and any CoreML conversion output. No global change by the toolkit.

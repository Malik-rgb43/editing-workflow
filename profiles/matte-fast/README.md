# Profile `matte-fast`

> Dated 2026-10-02 · evidence state **measured, the reference machine only** · expires 2027-03-31 or on a model/licence/runtime change. **unsupported ≠ missing ≠ error.**

## What it installs
Person matte (cutout) tooling for `tools/cutout.py`: **ONNX Runtime** (Python extra **`matte-ort`** in `pyproject.toml`; on Windows with a GPU `onnxruntime-directml` can replace `onnxruntime`), in a **separate virtual environment** (do not mix with the ASR environment). Routes:

| Route | Where it lives | Licence |
|---|---|---|
| **MODNet** (`--route onnx --model <file>`) | NOT in the repo: you download `onnx/model.onnx` (25,888,640 bytes) from huggingface.co/Xenova/modnet | Apache-2.0 |
| native HyperFrames `remove-background` (u2net, `--route native`, the default) | HyperFrames downloads `u2net_human_seg.onnx` (175,997,641 bytes) on first use | rembg code MIT; weights not separately reviewed |
| **RVM** (fastest measured) | **optional, user-installed plugin — internal use only** | **GPL-3.0** |

**RVM is never copied into the student download and never imported into repo code** (decision default Q8). A missing RVM plugin is normal, not an error.

## Download size and source
Read from the hosts on 2026-10-03: MODNet onnx 25,888,640 bytes; u2net_human_seg 175,997,641 bytes. ONNX Runtime wheel size: not recorded (pip shows it). Full table with sources: `docs/en/local-vs-paid.md`.

## Hardware
Fast route: a DX12 GPU for DirectML (measured: one reference machine; the GPU stayed nearly idle — 258 MB dedicated, 3D engine 5-11%). CPU route: any machine. NVIDIA and Apple figures are **sourced only** (RVM README: 172 FPS RTX 3090 HD FP16; 104 FPS GTX 1080 Ti FP32; the CoreML export has no dynamic resolution) and were never measured here.

## Tested-on evidence (the reference machine only, single passes on a shared host — **measured**)
Fixture: 20 s, 600 frames, 1080p30. **Native HyperFrames u2net 367.0 s → RVM + DirectML + OpenCV 72.4 s (5.1×)** → **49.5 s (7.4×)** with linear alpha interpolation every 2nd frame (matched per-frame inference on this talking-head clip; fast gestures untested). MODNet DirectML 108.0 s, MODNet CPU 278.1 s, RVM CPU 128.2 s, MediaPipe 47.1 s (poor edges, F1 0.54), SAM 2 tiny 810 s; **RVM half-fps hold rejected** (ghosting, chamfer 18 px); BiRefNet-lite CPU 28.5 s per frame. Only ~27% of wall time is model inference — I/O, conversion and ProRes assembly dominate. Edge quality is judged against a sparse BiRefNet proxy on 14 frames: **a proxy, not ground truth, no human review.** Teach "5.1× on the reference machine" and tell students to re-measure; it is not a law. Cache: key by source-packet hash + model + params; do **not** key by `-ss` seek ranges (3 hits / 2 misses where 1 miss was expected).

## States
| State | When |
|---|---|
| `unsupported` | no DirectML-capable GPU for the fast route — the CPU route and the native fallback remain available |
| `missing` | extras not installed or MODNet weights not present |
| `error` | a real tiny matte of the bundled fixture fails, returns an empty/constant alpha, or the alpha is one frame late |

## Licences — read before you install RVM
MODNet: Apache-2.0 (licence, required notices, modification markers; record the weights' provenance). RVM: **GPL-3.0** — internal use until resolved with counsel; GPL is not "forbidden for commercial work", but distribution, corresponding-source and integration duties need review. MediaPipe, SAM 2, BiRefNet: not reviewed — do not assume a parent licence. See `agent-content/references/matte-routes.md` and `licences-bom-rules.md`.

## Uninstall
Delete the matte environment, the downloaded model files, the matte cache directory shown at install time, and the RVM plugin if you installed it. No global change.

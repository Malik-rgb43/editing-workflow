# Profile `asr-cpu`

> Dated 2026-10-02 · evidence state **measured, the reference machine only** · expires 2026-12-31 or on any pin change. **unsupported ≠ missing ≠ error.**

## What it installs
Hebrew speech recognition on the CPU: **faster-whisper** with CTranslate2 (int8) and the **ivrit-ai fine-tune of Whisper large-v3-turbo** (CT2 conversion), language forced to `he`. Python extra: **`asr-cpu`** (`uv sync --extra asr-cpu`; the group is defined in `pyproject.toml`, owned by the core agent). Use a **separate Python environment** from the other ASR/matte profiles. Student tool: `transcribe`. Outputs: word-timestamp JSON `[{text,start,end}]`, SRT, text.

HyperFrames' own `transcribe` defaults to `small.en` and is poor at Hebrew; `init` auto-transcribes with it unless you pass `--skip-transcribe`. Use this profile instead.

## Download size and source
Model: **1,617,884,968 B** main weight + 3,780,213 B config/tokenizer/vocab (revision `72ad623a37947395efcc3933132353790e5a12f5`; source: model card, research T08-S002). Python packages: `unmeasured`. File size is not RAM or speed. Show the size and the cache path before downloading.

## Hardware
Any x86-64 or ARM64 CPU; recommended 8 physical cores and ≥ 16 GB RAM (measured on the reference machine). Peak resident memory ≈ **2.0 GB** (sampled; excludes the media). Use **physical** core count for threads (hyper-threads slowed CTranslate2/torch). A CPU-bound ASR competes with browser rendering: run one heavy job at a time.

## Tested-on evidence (the reference machine: one reference machine — **measured**, single passes)
68 clips of public Hebrew read speech (FLEURS he_il), 614.22 s: **731.384 s** whole-wrapper (0.84 audio-seconds per wall-second), 206 / 1,161 word edits (**WER 17.743%**, CER 8.028%). With Silero VAD: serial 1,147.038 s and WER 19.380%; parallel 4×2 770.860 s. Pilot (5 clips, 38.58 s): 57.9 s first pass, 54.6 s warm; model import 34.5 s and load 8.4 s. **VAD hallucination control:** on 3 s of digital silence and 3 s of noise the model returned Hebrew text without VAD, nothing with VAD — two controls, not a rate; VAD can delete soft speech, so regression-test it. **Not measured:** cloud ASR, diarization, spontaneous speech, accents, noisy scenes, phone mics, word-timing ground truth, human correction time, NVIDIA, Apple. Do not transfer these numbers to another machine — re-measure.

## States
| State | When |
|---|---|
| `unsupported` | CPU architecture not covered by the prebuilt CTranslate2 wheels, or not enough RAM |
| `missing` | extra not installed or the pinned model revision/hash not present |
| `error` | a tiny transcription of the bundled Hebrew fixture fails or returns empty text for known speech |

## Licences
faster-whisper and CTranslate2: MIT. Weights: **Apache-2.0** declared on the exact checkpoint (pin it; this does not license other conversions or the ivrit.ai training recordings). **The two ivrit-ai ONNX conversions are unresolved — never bundle or redistribute them.** Do not ship ivrit.ai speech datasets as sample footage. See `agent-content/references/asr-routes.md` and `licences-bom-rules.md`.

## Rules that apply to every transcript
Never trust one ASR pass for caption text: correct names/brands/terms by hand; **do not run an LLM over the whole transcript**; for voice-over joins transcribe the assembled file. Client footage and cloud ASR: see `docs/en/legal-guide.md#privacy-footage`.

## Uninstall
Delete the `asr-cpu` environment and the model cache (≈ 1.6 GB) shown at install time. No global change.

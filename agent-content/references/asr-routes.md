---
module: asr-routes
checked_at: 2026-10-02
expires: "90 days (2026-12-31), or on any change of a pinned model revision, runtime version, or driver"
confidence: "speed/WER [MEASURED-lab] on the reference machine only (one pass each, public read speech); NVIDIA and Apple routes are sourced or unmeasured; cloud prices [SOURCED-unverified]"
refresh: "re-read the model cards and runtime release notes (free); re-run the 68-clip benchmark locally if the build changes; never call a cloud ASR to 'check' it"
---

# Hebrew ASR routes — dated reference

| Field | Value |
|---|---|
| Fact set | Hebrew ASR models, formats, licences, runtimes per hardware, measured speed/WER, VAD behaviour, hallucination controls, forced alignment, cloud ASR price estimates |
| Versions / ids | ivrit-ai `whisper-large-v3-turbo-ct2` rev `72ad623a37947395efcc3933132353790e5a12f5` · `…-turbo-ggml` rev `2130c78e4a9cb4914cc4df91a1c3031407789705` · faster-whisper 1.2.1 · CTranslate2 4.7.1 (docs 4.8.2) · whisper.cpp b5130 (commit `927cfce34f31707e17f2bff35c349632fb9e2c3a`) · JiWER 4.0.0 · Python 3.12.10 |
| `checked_at` | **2026-10-02** (= research date; **must be refreshed before use**) |
| Source | `distilled/06-…/asr-and-transcription.md` (T08, E02, E08); `distilled/08-…/hardware-and-os.md` |
| Scope / plan / region | **the reference machine only: one reference machine**; 614.22 s of public Hebrew read speech (FLEURS he_il, CC BY 4.0) |
| Confidence | `[MEASURED-lab]` for the tables; `[VERIFIED-external]` for model facts; `[SOURCED-unverified]` for the published leaderboard and cloud prices; **NVIDIA/Apple cells unmeasured** |
| `expires` | see front matter |
| Non-spending refresh | model cards and release pages; local re-measurement with the benchmark script; do **not** submit footage to a cloud service to compare |

## 1. Decision (first local Hebrew candidate)
**ivrit-ai fine-tune of Whisper large-v3-turbo, language forced to `he`** (the model card warns language detection and translation are degraded). Apache-2.0 weights. The **model format must match the runtime**: CTranslate2 (faster-whisper) prebuilt binaries = x86-64/ARM64 CPU + NVIDIA CUDA; whisper.cpp GGML = CPU, Vulkan, ROCm, CUDA, Metal/CoreML. "ivrit-ai on GPU" is not a backend description. `[VERIFIED-external]`

HyperFrames' built-in `transcribe` defaults to `small.en` (poor Hebrew); `init` auto-transcribes with it (use `--skip-transcribe`); parakeet does not cover Hebrew. **Always use the ivrit-ai tools** (student tool: `transcribe`). `[PROVEN-internal]`

## 2. Models, formats, licences (pins observed 2026-10-01)
| Model | Revision | Main weight bytes | Format / runtime | Licence |
|---|---|---:|---|---|
| ivrit-ai/whisper-large-v3-turbo-ct2 | `72ad623a37947395efcc3933132353790e5a12f5` (2025-10-27) | 1,617,884,968 (+3,780,213 config/tokenizer/vocab) | faster-whisper / CTranslate2, CPU int8 or NVIDIA | Apache-2.0 `[VERIFIED-external]` |
| ivrit-ai/whisper-large-v3-turbo-ggml | `2130c78e4a9cb4914cc4df91a1c3031407789705` | 1,624,555,275 (mostly F16) | whisper.cpp | Apache-2.0 |
| ivrit-ai/whisper-large-v3-turbo | `f33172a8c3c6efbc040a7200e00835257cac0447` | 3,235,581,408 | Transformers reference | Apache-2.0 |
| ivrit-ai/whisper-large-v3-ct2 | `e9ed4a4a98d761b0f617d668303de2c514236c66` | 3,087,284,276 | larger CT2 comparator | Apache-2.0 |
| ivrit-ai/whisper-large-v3 | `766847c9795b3b5cc0d42f8476199c711d5cee21` | 6,174,112,072 | larger reference | Apache-2.0 |
| ivrit-ai/whisper-large-v3-turbo-onnx (rev `edb17b6b65f60a299d4b620d043e15b60321e5ff`) and -onnx-take2 (`9dbd271d18ff3f85140b64cf7949d53da6581e57`) | — | not recorded | ONNX conversion (DirectML candidate) | **none declared; READMEs failed to read → unresolved, do not bundle or redistribute** |
| imvladikon/wav2vec2-xls-r-300m-hebrew (WhisperX alignment) | `b2e683004903f1b11bee2c6092a7c323ed858d82` | 1,261,938,632 | forced alignment | **no licence listed → do not bundle** |

File size is not RAM or speed: a 1.6 GB weight makes a CPU trial plausible, it does not predict real-time speed or peak memory. Do not download both PyTorch and safetensors copies. Model-card narrative conflict (CT2 README vs base card): pin weights instead of inventing a release date. Catalogue entries prefixed `yi-` are different models, not a new winner. **ivrit.ai speech datasets** carry purpose limits (v1 2023-06-30 training only; v2 2024-10-01 training or academic research): do not ship their speech as sample footage; the data licence is not the model-card licence. `[VERIFIED-external]` Candidate runtime pins (not a tested lock): faster-whisper 1.2.1 (MIT; current README: CUDA 12 + cuDNN 9), CTranslate2 4.8.2 docs (MIT), WhisperX 3.8.6 (BSD-2; needs a much larger torch/pyannote stack — keep it out of the minimal environment), JiWER 4.0.0.

## 3. Runtimes per machine
| Machine | First trial | Alternative | Evidence |
|---|---|---|---|
| Windows/Linux CPU (incl. AMD CPU) | faster-whisper + ivrit turbo CT2, **CPU int8** | whisper.cpp CPU GGML | `[MEASURED-lab]` E02/E08 |
| Windows AMD (the reference machine) | **whisper.cpp built with Vulkan** (`-DGGML_VULKAN=ON`), env `GGML_VK_DISABLE_COOPMAT=1` | CPU baseline; ROCm only after an exact GPU/OS/build check; DirectML via ONNX is an open path (unresolved licences) | `[MEASURED-lab]` `[LOCAL-only]`; CT2 does not document AMD GPU |
| NVIDIA | faster-whisper CT2 with CUDA 12 / cuDNN 9, explicit compute type | whisper.cpp CUDA | **unmeasured** (docs only) |
| Apple Silicon | whisper.cpp Metal; CPU control | CoreML encoder conversion | **unmeasured**; no verified MLX-format Hebrew weight in the research; CT2 ARM CPU support ≠ Metal |

Build recipe that worked on the reference machine (E08): CMake 4.3.1, Vulkan SDK 1.4.357.0, Visual Studio 17 2022 generator: `cmake -S <src> -B <build> -G "Visual Studio 17 2022" -A x64 -DGGML_VULKAN=ON -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_SERVER=OFF`, then `cmake --build <build> --config Release --target whisper-cli --parallel 4`; configure 33.5 s, compile 248.5 s; source ZIP 10,476,278 bytes. **A student pays this toolchain cost** — the official Windows b5130 release asset has only CPU/BLAS variants (no Vulkan). `whisper-cli` breaks on Hebrew file paths: use an ASCII temp path. Keep Python environments separate per route (torch-directml pins torch 2.4.1 / CPython 3.8-3.12; ROCm recipes use torch 2.13 / Python 3.13).

## 4. What was measured (the reference machine, single passes)
**E08 shootout** — 68 FLEURS clips, 614.22 s, 1,161 reference words (normalisation: NFC, lowercase, punctuation → space, whitespace collapse; WER = corpus word edits / reference words). Whole-wrapper seconds (Python startup + imports + model init + inference + persistence):

| Configuration | Seconds | Audio-s per wall-s | Word edits / WER | Char edits / CER |
|---|---:|---:|---|---|
| whisper.cpp **CPU**, 8 threads | 1,033.045 | 0.595 | 210 / 18.088% | 523 / 8.075% |
| whisper.cpp **Vulkan**, 8 threads | **105.604** | **5.816** | 212 / 18.260% | 541 / 8.353% |
| whisper.cpp Vulkan 4 / 16 threads | 104.884 / 106.258 | 5.856 / 5.780 | identical transcript bytes to t8 | |
| CT2 int8 plain (no VAD) | 731.384 | 0.840 | 206 / 17.743% | 520 / 8.028% |
| CT2 + Silero VAD, serial | 1,147.038 | 0.535 | 225 / 19.380% | 592 / 9.140% |
| CT2 + VAD, parallel 4×2 | 770.860 | 0.797 | 225 / 19.380% | 592 / 9.140% |

Derived: Vulkan 8 vs CPU 8 = **9.78×** (launch-to-finalisation 10.0×); Vulkan vs CT2 plain = 6.93×. Linear extrapolation to one hour (assumes read-speech throughput carries over, which E08 does not establish) `[IDEA]`: Vulkan ≈ 10.3 min, CT2 int8 ≈ 71.5 min, whisper.cpp CPU ≈ 101 min. Peak sampled RSS ≈ 2 GB for CPU routes (excludes GPU memory; peak VRAM, power, thermals **not measured**). **No thread-count winner on Vulkan.** WER differences are 4-19 word edits of 1,161: close counts, not statistical equivalence. **Never compare different inner timers as equal-scope speed.** `[CONFLICT]` the owner's earlier note (Vulkan 2.4× on a loaded machine, 262 s talk; "16 threads ≈ 60% slower than 8" on CPU) vs E08's ~10× on an idle machine — quote E08 **with its scope** and tell students to **re-measure on their own hardware**.

**E02 pilot** (5 clips, 38.58 s, 85 words): CT2 int8 first 57.899 s / warm 54.645 s; with VAD warm 49.216 s; whisper.cpp CPU warm 74.899 s; all three 20/85 word edits (23.529% WER, different errors); import 34.5 s, model load 8.4 s. Negative controls: **3 s of digital silence and 3 s of seeded noise produced non-empty Hebrew text** from CT2 without VAD and from whisper.cpp without VAD; CT2 with VAD returned empty. Two controls, not a hallucination rate. `[CONFLICT]` E02 (VAD faster) vs E08 (explicit-span VAD slower, 225 vs 206 edits): different VAD implementation and corpus.

Published leaderboard (turbo CT2, May 2025 label): WER 0.053 eval-d1, 0.071 eval-whatsapp, 0.066 saspeech, 0.181 Hebrew FLEURS, 0.082 kan — source-reported, not reproduced, and the dated label is not proof of equivalence to today's pinned hashes. `[SOURCED-unverified]`

Not measured: cloud ASR, diarization, spontaneous Hebrew, accents, noisy scenes, phone mics, manual word-timing error, human correction time, long recordings, NVIDIA, Apple.

## 5. The owner's three recipes (settings are starting points, not listening-verified best)
**CPU (faster-whisper):** `device=cpu`, `compute_type=int8`, `language=he`, `word_timestamps=True`, `vad_filter=True` (Silero defaults), `beam_size=5`, `condition_on_previous_text=False`, `temperature=[0.0,0.2,0.4,0.6]`; outputs `<stem>.words.json` (`[{text,start,end}]` seconds), `.srt` (`--words-per-cue 3`, `1` for one-word cues), `.txt`. Owner estimate ~2.3× real time on a loaded machine. Externalise model path, revision, device, precision, threads into a **manifest** `[IDEA]` (the original hard-codes a local path).
**GPU (Vulkan) with CPU fallback:** 16 kHz mono wav → language detection (Whisper `base` int8) → Silero VAD cuts non-speech (`min_silence_duration_ms=300`, `speech_pad_ms=200`) → speech-only wav in an ASCII temp dir → `whisper-cli -m ggml-model.bin -f speech.wav -l he -t <physical cores> -bs 5 -nfa -ml 1 -sow -oj -of <tmp>/out -np` with `GGML_VK_DISABLE_COOPMAT=1` → timestamps mapped back → segments (new segment on a gap > 0.8 s, 18 words, or `. ? !`). Use **physical** cores for threads (SMT threads slowed CTranslate2/torch). Any GPU error or non-Hebrew → CPU route.
**Sung lyrics pass:** when VAD hears nothing in a produced mix, transcribe the whole audio **without VAD** and keep only confident segments: drop if `avg_logprob < −0.8`, `no_speech_prob > 0.5`, `compression_ratio > 2.4`, the same text repeats > 2 times, or a known hallucination string (< 40 chars: "thank you", "thanks for watching", "subtitles by", "subscribe", "תודה רבה", "תודה שצפיתם", "כתוביות"); accept only ≥ 2 segments and ≥ 20 characters; tag the result "SUNG LYRICS". `[PROVEN-internal]`

## 6. VAD, hallucination, proofreading
Keep VAD for non-speech-heavy audio; **regression-test soft speech**; it can delete real speech. Keep the two 3 s no-speech controls as permanent regression cases. **Never trust a single ASR for caption text:** hand-fix names/brands/terms; do not run an LLM across the whole transcript (a cheap model worsened WER, another rewrote whole sentences); for voice-over joins run ASR on the **FULL assembled file** (isolated-snippet ASR said "clean" while the full file heard residues). Back-transcribe TTS and diff against the script. Native Whisper word timestamps are not a validated timing ground truth; forced alignment for Hebrew exists (WhisperX → the unlicensed wav2vec2 model above) but ElevenLabs' forced-alignment language list omits Hebrew. `[PROVEN-internal]` `[VERIFIED-external]`

## 7. Cloud ASR (price estimates 2026-10-01, USD per audio hour; none run; perishable) `[SOURCED-unverified]`
OpenAI transcription $0.27 / $0.36 / **$0.18 (gpt-4o-mini-transcribe, ≈ $0.003/min)** · ElevenLabs Scribe v2 **$0.22** (key-term options may add charges) · Deepgram Nova-3 $0.258 · AssemblyAI $0.15 (+$0.02 diarization) · Google generic V2 $0.96 (dynamic $0.18, eligibility unresolved) · Azure/AWS unresolved. Support, features and prices are model/mode/region specific. Before any upload decide **eligibility** (client footage, training/retention terms — see `docs/en/legal-guide.md#privacy-footage`). Compare **correction minutes** first: raw transcription dollars are small. A cloud fallback is an unmeasured option, never an automatic paid call.

## 8. Profile mapping (see `profiles/`)
`asr-cpu` (CT2 int8; measured) · `asr-vulkan` (whisper.cpp + Vulkan; measured, the reference machine's GPU only) · `asr-cuda` (**unmeasured**) · `asr-mlx` (**unmeasured**; no verified MLX Hebrew weights). *unsupported ≠ missing ≠ error*: a student without a Vulkan GPU sees `unsupported` for `asr-vulkan`, not a failure of the core.

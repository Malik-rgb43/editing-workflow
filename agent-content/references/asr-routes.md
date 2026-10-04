---
module: asr-routes
checked_at: 2026-10-03
expires: "90 days (2026-12-31), or on any change of the pinned model revision or runtime version"
confidence: "speed/WER [MEASURED-lab] on the reference machine only (one pass each, public read speech); NVIDIA and Apple speeds unmeasured; cloud prices [SOURCED-unverified]"
refresh: "re-read the model card and the faster-whisper release notes (free); re-run the 68-clip benchmark locally if the build changes; never call a cloud ASR to 'check' it"
---

# Hebrew ASR route — dated reference

One local route, chosen because it works on every machine: **faster-whisper (CTranslate2, MIT) running the ivrit-ai Whisper large-v3-turbo CT2 weights (Apache-2.0), int8 on the CPU, language forced to `he`.** Decision 2026-10-03 (owner): the whisper.cpp / Vulkan / ggml route was removed — it was faster on one AMD machine only (9.78x its own CPU run, E08), needed a source build with CMake, the Vulkan SDK and Visual Studio, and no other machine was ever measured. A single route that every student can run beats a faster one most cannot.

| Field | Value |
|---|---|
| Fact set | Hebrew ASR model, format, licence, runtime, measured speed/WER, VAD behaviour, hallucination controls, forced alignment, cloud ASR price estimates |
| Versions / ids | ivrit-ai `whisper-large-v3-turbo-ct2` rev `72ad623a37947395efcc3933132353790e5a12f5` · faster-whisper 1.2.1 · CTranslate2 4.7.1 (docs 4.8.2) · JiWER 4.0.0 · Python 3.12.10 |
| `checked_at` | **2026-10-03** (model pin observed 2026-10-01; **refresh before use**) |
| Source | `distilled/06-…/asr-and-transcription.md` (T08, E02, E08); `distilled/08-…/hardware-and-os.md` |
| Scope / plan / region | **the reference machine only**; 614.22 s of public Hebrew read speech (FLEURS he_il, CC BY 4.0) |
| Confidence | `[MEASURED-lab]` for the table; `[VERIFIED-external]` for model facts; `[SOURCED-unverified]` for the published leaderboard and cloud prices |
| Non-spending refresh | model card and release pages; local re-measurement with the benchmark script; do **not** submit footage to a cloud service to compare |

## 1. Decision
**ivrit-ai fine-tune of Whisper large-v3-turbo, language forced to `he`** (the model card warns language detection and translation are degraded). Apache-2.0 weights. HyperFrames' built-in `transcribe` defaults to `small.en` (poor Hebrew); `init` auto-transcribes with it (use `--skip-transcribe`); parakeet does not cover Hebrew. **Always use the toolkit's `transcribe`.** `[PROVEN-internal]`

## 2. Model, format, licence
| Model | Revision | Main weight bytes | Runtime | Licence |
|---|---|---:|---|---|
| ivrit-ai/whisper-large-v3-turbo-ct2 | `72ad623a37947395efcc3933132353790e5a12f5` (2025-10-27) | 1,617,884,968 (+3,780,213 config/tokenizer/vocab) | faster-whisper / CTranslate2, CPU int8 | Apache-2.0 `[VERIFIED-external]` |

Download (explicit, after the student approves the size): `huggingface.co/ivrit-ai/whisper-large-v3-turbo-ct2` at the pinned revision; never "latest", never both a PyTorch and a safetensors copy. File size is not RAM or speed. **ivrit.ai speech datasets** carry purpose limits (v1 2023-06-30 training only; v2 2024-10-01 training or academic research): do not ship their speech as sample footage. Not usable: the ivrit-ai ONNX conversions (no licence declared, do not bundle or redistribute) and `imvladikon/wav2vec2-xls-r-300m-hebrew` (no licence listed, forced alignment candidate only). `[VERIFIED-external]`

## 3. Where it runs
| Machine | Route | Evidence |
|---|---|---|
| any x86-64 / ARM64 CPU, Windows, macOS, Linux | faster-whisper + ivrit CT2, **CPU int8** | `[MEASURED-lab]` E02/E08 (reference machine) |
| NVIDIA GPU | the same package can use CUDA 12 / cuDNN 9; **not offered or installed by the toolkit** | unmeasured (docs only) |

Use **physical** core counts for threads. `whisper`-style tools break on Hebrew file paths: keep audio in an ASCII temp path.

## 4. What was measured (the reference machine, single passes)
**E08** — 68 FLEURS clips, 614.22 s, 1,161 reference words (normalisation: NFC, lowercase, punctuation → space, whitespace collapse; WER = corpus word edits / reference words). Whole-wrapper seconds (Python startup + imports + model init + inference + persistence):

| Configuration | Seconds | Audio-s per wall-s | Word edits / WER | Char edits / CER |
|---|---:|---:|---|---|
| CT2 int8 plain (no VAD) | 731.384 | 0.840 | 206 / 17.743% | 520 / 8.028% |
| CT2 + Silero VAD, serial | 1,147.038 | 0.535 | 225 / 19.380% | 592 / 9.140% |
| CT2 + VAD, parallel 4×2 | 770.860 | 0.797 | 225 / 19.380% | 592 / 9.140% |

Linear extrapolation to one hour (assumes read-speech throughput carries over, which E08 does not establish) `[IDEA]`: CT2 int8 ≈ 71.5 min. Peak sampled RSS ≈ 2 GB. WER differences are 4-19 word edits of 1,161: close counts, not statistical equivalence. **Never compare different inner timers as equal-scope speed.** Tell students to **re-measure on their own hardware**; plan the whole-source ASR at minute 0 as a background job.

**E02 pilot** (5 clips, 38.58 s, 85 words): CT2 int8 first 57.899 s / warm 54.645 s; with VAD warm 49.216 s; 20/85 word edits (23.529% WER); import 34.5 s, model load 8.4 s. Negative controls: **3 s of digital silence and 3 s of seeded noise produced non-empty Hebrew text** from CT2 without VAD; CT2 with VAD returned empty. Two controls, not a hallucination rate. `[CONFLICT]` E02 (VAD faster) vs E08 (explicit-span VAD slower, 225 vs 206 edits): different VAD implementation and corpus.

Published leaderboard (turbo CT2, May 2025 label): WER 0.053 eval-d1, 0.071 eval-whatsapp, 0.066 saspeech, 0.181 Hebrew FLEURS, 0.082 kan — source-reported, not reproduced. `[SOURCED-unverified]`

Not measured: cloud ASR, diarization, spontaneous Hebrew, accents, noisy scenes, phone mics, manual word-timing error, human correction time, long recordings, NVIDIA, Apple.

## 5. Recipes
**CPU (faster-whisper):** `device=cpu`, `compute_type=int8`, `language=he`, `word_timestamps=True`, `vad_filter=True` (Silero defaults), `beam_size=5`, `condition_on_previous_text=False`, `temperature=[0.0,0.2,0.4,0.6]`; outputs `<stem>.words.json` (`[{text,start,end}]` seconds), `.srt`, `.txt`. Model path, revision, device, precision and threads live in a manifest, not in the code.
**Sung lyrics pass:** when VAD hears nothing in a produced mix, transcribe the whole audio **without VAD** and keep only confident segments: drop if `avg_logprob < −0.8`, `no_speech_prob > 0.5`, `compression_ratio > 2.4`, the same text repeats > 2 times, or a known hallucination string (< 40 chars: "thank you", "thanks for watching", "subtitles by", "subscribe", "תודה רבה", "תודה שצפיתם", "כתוביות"); accept only ≥ 2 segments and ≥ 20 characters; tag the result "SUNG LYRICS". `[PROVEN-internal]`

## 6. VAD, hallucination, proofreading
Keep VAD for non-speech-heavy audio; **regression-test soft speech**; it can delete real speech. Keep the two 3 s no-speech controls as permanent regression cases. **Never trust a single ASR for caption text:** hand-fix names/brands/terms; do not run an LLM across the whole transcript; for voice-over joins run ASR on the **FULL assembled file** (isolated-snippet ASR said "clean" while the full file heard residues). Back-transcribe TTS and diff against the script. Native Whisper word timestamps are not a validated timing ground truth; forced alignment for Hebrew exists (WhisperX → the unlicensed wav2vec2 model above) but ElevenLabs' forced-alignment language list omits Hebrew. `[PROVEN-internal]` `[VERIFIED-external]`

## 7. Cloud ASR (price estimates 2026-10-01, USD per audio hour; none run; perishable) `[SOURCED-unverified]`
OpenAI transcription $0.27 / $0.36 / **$0.18 (gpt-4o-mini-transcribe, ≈ $0.003/min)** · ElevenLabs Scribe v2 **$0.22** · Deepgram Nova-3 $0.258 · AssemblyAI $0.15 (+$0.02 diarization) · Google generic V2 $0.96 · Azure/AWS unresolved. Support, features and prices are model/mode/region specific. Before any upload decide **eligibility** (client footage, training/retention terms — see `docs/en/legal-guide.md#privacy-footage`). Compare **correction minutes** first: raw transcription dollars are small. A cloud fallback is an unmeasured option, never an automatic paid call.

## 8. Profile mapping (see `profiles/`)
`asr-cpu` is the only ASR profile.

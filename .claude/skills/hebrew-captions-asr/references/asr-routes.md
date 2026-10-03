# ASR routes, WER protocol, VAD, lyrics pass

Load when: choosing or building an ASR route, measuring speed or WER on a new machine, deciding on VAD, transcribing sung audio. Dated 2026-10-02. Source: distilled 06 asr-and-transcription (E02, E08 reports, T08); machine for all measured numbers = the reference machine. No money, cloud or model-authoring run was involved. NVIDIA and Apple: unmeasured.

## 1. Model and format must match the runtime
| Model | Format / runtime | Licence | Note |
|---|---|---|---|
| ivrit-ai/whisper-large-v3-turbo-ct2 (rev 72ad623a..., lastModified 2025-10-27) | faster-whisper / CTranslate2; CPU int8 or NVIDIA | Apache-2.0 | portable baseline |
| ivrit-ai/whisper-large-v3-turbo-ggml (rev 2130c78e...) | whisper.cpp: CPU, Vulkan, ROCm, CUDA, Metal | Apache-2.0 | the Vulkan route on AMD |
| ivrit-ai/whisper-large-v3-turbo (Transformers) | reference | Apache-2.0 | 3.2 GB |
| ivrit-ai ONNX conversions (turbo-onnx, -take2) | DirectML candidate | none declared in metadata | not run; unresolved licence chain: do not bundle |
| imvladikon/wav2vec2-xls-r-300m-hebrew (WhisperX alignment) | forced alignment | card lists NO licence | research candidate only; do not bundle weights |
"ivrit-ai on GPU" is not a backend description: CTranslate2 prebuilt binaries = CPU (x86-64, ARM64) and NVIDIA CUDA; whisper.cpp GGML = CPU, Vulkan, ROCm, CUDA, Metal. The model card warns that language detection and translation are degraded: always force `he`. File size is not RAM or speed. Speech datasets from ivrit.ai carry purpose restrictions: do not redistribute them as sample footage; use FLEURS (CC BY 4.0, attribution below) for fixtures.

## 2. Measured on the reference machine (E08: 68 FLEURS he_il clips, 614.22 s of presegmented read speech, 1,161 reference words / 6,477 characters; one pass per configuration, fixed order, no cache flush, no statistics)
| Configuration | Whole-wrapper s | Audio-s per wall-s | Word edits / 1,161 | WER | CER | RSS (sampled, excludes GPU memory) |
|---|---:|---:|---:|---:|---:|---:|
| whisper.cpp CPU, 8 threads | 1,033.045 | 0.595 | 210 | 18.088 % | 8.075 % | 1.96 GB |
| whisper.cpp Vulkan, 8 threads | 105.604 | 5.816 | 212 | 18.260 % | 8.353 % | 0.19 GB |
| whisper.cpp Vulkan, 4 / 16 threads | 104.884 / 106.258 | 5.856 / 5.780 | 212 | 18.260 % | 8.353 % | 0.18 GB |
| CT2 int8 CPU, plain | 731.384 | 0.840 | 206 | 17.743 % | 8.028 % | 1.99 GB |
| CT2 + explicit-span VAD, serial | 1,147.038 | 0.535 | 225 | 19.380 % | 9.140 % | 2.00 GB |
| CT2 + VAD, 4 workers x 2 threads | 770.860 | 0.797 | 225 | 19.380 % | 9.140 % | 2.85 GB |
Derived: Vulkan 8 vs CPU 8 = 9.78x (launch-to-finalisation 10.00x); Vulkan vs CT2 plain = 6.93x; RTF Vulkan 0.172. Linear extrapolation to a 1-hour recording (assumes read-speech throughput carries over, which E08 does not establish): Vulkan ~10.3 min, CT2 int8 ~71.5 min, whisper.cpp CPU ~101 min. Vulkan wall time was insensitive to 4/8/16 threads. The earlier owner figures (Vulkan only 2.4x CPU; 16 CPU threads ~60 % slower than 8) were taken on a machine loaded 3-4x by other jobs and are [CONFLICT] with E08; CPU thread counts were not varied in E08.
Timer scopes: whole wrapper = Python start + imports + model init + inference + report persistence. Never compare unlike timers. Consume every segment of the faster-whisper generator INSIDE the timed region or the timer lies.
E02 (5 FLEURS clips, 38.58 s, 85 words, CPU): all three configurations made 20 word edits (23.529 %): a smoke test, not a ranking.

## 3. Build recipe that worked (Windows, E08)
`cmake -S <whisper.cpp src> -B <build> -G "Visual Studio 17 2022" -A x64 -DGGML_VULKAN=ON -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_SERVER=OFF` then `cmake --build <build> --config Release --target whisper-cli --parallel 4`. Needs CMake, the Vulkan SDK and Visual Studio build tools; configure 33.5 s + compile 248.5 s on this machine (the official Windows release asset has CPU/BLAS variants only, no Vulkan). Model download and toolchain install are real costs for a student. Run: `whisper-cli -m ggml-model.bin -f speech.wav -l he -t <physical cores> -bs 5 -nfa -ml 1 -sow -oj -of <tmp>/out -np` with `GGML_VK_DISABLE_COOPMAT=1` set ONLY IF it crashes on your GPU (the one reference machine needed it; other GPUs/drivers unverified), CPU with `-ng`. `-ml 1 -sow` = one word per entry. Wav in an ASCII temp dir.

## 4. Settings that stuck (owner CPU recipe, faster-whisper)
`device="cpu"`, `compute_type="int8"`, `language="he"`, `word_timestamps=True`, `beam_size=5` (beat greedy on music-bed reel audio in the owner's bench), `condition_on_previous_text=False`, `temperature=[0.0, 0.2, 0.4, 0.6]`, `cpu_threads` = PHYSICAL cores. Outputs: `.words.json`, `.srt` of `--words-per-cue` words, `.txt` with `[HH:MM:SS - HH:MM:SS]` per segment. Keep model path, revision, device, precision, threads in a manifest, not hard-coded. `--help` must return in < 1 s (lazy heavy imports; the original took 33-45 s).

## 5. VAD and hallucination controls
- Whisper hallucinates on silence/noise/music: 3 s of digital silence and 3 s of seeded noise gave non-empty Hebrew text with CT2 (VAD off) and whisper.cpp; CT2 + VAD returned empty (E02). Two controls, not a frequency on real footage.
- E02: VAD on was 9.93 % faster but CER rose 6.897 % -> 7.112 %. E08: explicit-span VAD (115 chunks) was 56.8 % slower than plain and 19 word edits worse. [CONFLICT]: different VAD implementation and corpus; the cause of the speed paradox is unresolved. Hence "VAD optional per clip, A/B on your audio" (decision default Q8).
- Silero defaults used by the owner: `min_silence_duration_ms=300`, `speech_pad_ms=200`.
- Other controls: forced language, `condition_on_previous_text=False`, the temperature ladder, the `avg_logprob`/`no_speech_prob`/`compression_ratio` filters (below), a hallucination-string blacklist ("thank you", "thanks for watching", "subtitles by", "subscribe", "תודה רבה", "תודה שצפיתם", "כתוביות"). Regression set for VAD: silence, music, soft speech, overlap; empty-reference WER is undefined, so report insertion counts for silence tests.

## 6. Lyrics pass (sung vocals buried in a mix)
Transcribe WITHOUT VAD (large model, beam 5, word timestamps, `condition_on_previous_text=False`) and keep only confident segments: drop if `avg_logprob` < -0.8, `no_speech_prob` > 0.5, `compression_ratio` > 2.4, the same normalised text repeated more than twice, or a known hallucination string when the segment is < 40 characters; accept the pass only with >= 2 segments and >= 20 characters. Tag the result "SUNG LYRICS". If music has a vocal, separate with `demucs --two-stems=vocals` first.

## 7. Word timestamps
Native Whisper word times are not a validated ground truth. Historical median drift ~90 ms (73 ms after a global monotone snap in the owner's reels tool; not reproduced by research): fix a perceptible drift with a constant offset; captions lead the voice by 0.08-0.1 s. `stable-ts` refinement was installed by the owner; its accuracy gain was not measured. Hebrew forced alignment exists (WhisperX default model above) but its licence is unlisted; ElevenLabs forced alignment does not list Hebrew. Keep native timing, corrected text and aligned timing as separate outputs. A manual timing subset is the proposed truth: listen on waveform/spectrogram, define start/end conventions, never use the candidate aligner as its own ground truth.

## 8. WER protocol (use `scripts/wer.py`)
Freeze audio and reference before seeing outputs; no LLM rewrite. Declare normalisation: NFC, lowercase, Unicode punctuation -> space, collapse whitespace, keep symbols, digits and niqqud. Corpus WER = total (S+D+I) / total reference words (never an average of clip WERs); CER with the same policy. Add silence/noise controls. Report wall time separately for load, first inference, warm inference. Five clips are a smoke test; strata to add later: spontaneous speech, code-switching, phone audio, accents, music, overlap, names.
Attribution to keep for FLEURS: "Hebrew samples from FLEURS (Google; Conneau et al.), google/fleurs, revision 70bb2e84b976b7e960aa89f1c648e09c59f894dd, CC BY 4.0. Selected subset; list any resampling, trimming and manual timing additions." Use the TSV + tar route; never an unrestricted `extractall`.

## 9. Cloud options (sourced, NONE run, perishable)
ElevenLabs Scribe, OpenAI transcribe models, Google Chirp 3, Azure, Amazon Transcribe, Deepgram Nova-3 and AssemblyAI list Hebrew with model-, mode- and region-specific features; prices were read on 2026-10-01 and are not repeated here (they expire). A cloud run needs the owner's approval and a cost estimate (`paid-generation-gate`) and is judged by time-to-accepted-transcript (upload + queue + result + correction), which nobody has measured.

## Sources
distilled 06 asr-and-transcription §0-§9; E02 and E08 reports via that file; T08 verification; checked 2026-10-02.

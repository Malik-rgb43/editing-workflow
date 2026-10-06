# ASR settings, WER protocol, VAD, lyrics pass

Load when: running or tuning the ASR step, choosing the model for a language, measuring speed or WER on a new machine, deciding on VAD, transcribing sung audio. Dated 2026-10-06. The model, its pin, licence, the measured speeds and the cloud options live in ONE place: `agent-content/references/asr-routes.md` (do not copy them here). Machine for all measured numbers = the reference machine. NVIDIA and Apple: unmeasured.

## 0. Language -> model (`tools/transcribe.py`, output `words.json`)
| Speech language (Round 0 / PROMPT.md) | Command | Measured? |
|---|---|---|
| `he` | `python tools/transcribe.py <media> -o hf/data/words.json --language he [--model-dir <ivrit model>]` | yes, below (one machine) |
| any other (`en`, `ar`, `fr` ...) | `... --language <code> --model-id Systran/faster-whisper-large-v3 --allow-download` only after the user's yes to the shown download (a large model; the repo id is printed first), or `--model-dir <local multilingual model> --model-lang multi` | no: unmeasured on the reference machine |
| unknown | `... --language auto`; the ivrit model refuses non-Hebrew speech (exit 2, nothing written) and prints the multilingual route; say the detected language back to the user | - |
`words.json` (schema `avc.words/1`): `{"language", "model", "route", ..., "words": [{"w", "start", "end", "prob"}]}`, times in seconds; `tools/prep.py` already writes `hf/data/words.json` (reuse it). `hf_blocks.py caption-words` and `word_retime.py` read the same shape.

## 0b. What was measured (Hebrew route only)
faster-whisper + the ivrit turbo CT2 weights, int8 on the CPU, 8 physical-core threads, language `he`: 731.4 s for 614.22 s of read speech = 0.84 audio-s per wall-s, WER 17.74 % (CT2 + VAD 19.38 %; E08, 68 FLEURS he_il clips, one pass, idle machine, whole-wrapper seconds). Real dialogue, noisy phone audio and manual word-boundary accuracy are not measured. VAD: without it Whisper returned non-empty Hebrew text for 3 s of digital silence and for 3 s of low noise (E02); the explicit-span VAD run in E08 was slower and less accurate than plain CT2 (225 vs 206 word edits) - hence the per-clip A/B (§3).
Evidence status: ASR from experiments E02/E08 (the reference machine); fonts from E03; timing and exit rules from the author's projects. No human timing ground truth, no cloud ASR run, no non-Hebrew run, no model-licence resolution for ONNX conversions.

## 1. The route
faster-whisper (CTranslate2) + the ivrit-ai large-v3-turbo CT2 weights for Hebrew, int8 on the CPU, `--language he` (the model card warns language detection and translation are degraded). Other languages: the multilingual large-v3 weights (§0), same settings. Model, revision, size and licence: `agent-content/references/asr-routes.md` §2. Speech datasets from ivrit.ai carry purpose restrictions: do not redistribute them as sample footage; use FLEURS (CC BY 4.0, attribution below) for fixtures. Timer scopes: whole wrapper = Python start + imports + model init + inference + report persistence; never compare unlike timers, and consume every segment of the faster-whisper generator INSIDE the timed region or the timer lies.

## 2. Settings that stuck (owner CPU recipe)
`device="cpu"`, `compute_type="int8"`, `language=<the known code>`, `word_timestamps=True`, `beam_size=5` (beat greedy on music-bed reel audio in the author's bench), `condition_on_previous_text=False`, `temperature=[0.0, 0.2, 0.4, 0.6]`, `cpu_threads` = PHYSICAL cores. Output: `words.json` (`avc.words/1`, §0); a `.srt`, `.vtt` or `.txt` sidecar, when one is delivered, is written from it by `python tools/captions_export.py words.json -o <file>`. Keep model path, revision, device, precision, threads in a manifest, not hard-coded. `--help` must return in < 1 s (lazy heavy imports; the original took 33-45 s).

## 3. VAD and hallucination controls
- Whisper hallucinates on silence/noise/music: 3 s of digital silence and 3 s of seeded noise gave non-empty Hebrew text with CT2 (VAD off); CT2 + VAD returned empty (E02). Two controls, not a frequency on real footage.
- E02: VAD on was 9.93 % faster but CER rose 6.897 % -> 7.112 %. E08: explicit-span VAD (115 chunks) was 56.8 % slower than plain and 19 word edits worse. [CONFLICT]: different VAD implementation and corpus; the cause of the speed paradox is unresolved. Hence "VAD optional per clip, A/B on your audio" (decision default Q8).
- Silero defaults used by the author: `min_silence_duration_ms=300`, `speech_pad_ms=200`.
- Other controls: a known language passed explicitly, `condition_on_previous_text=False`, the temperature ladder, the `avg_logprob`/`no_speech_prob`/`compression_ratio` filters (below), a hallucination-string blacklist ("thank you", "thanks for watching", "subtitles by", "subscribe", "תודה רבה", "תודה שצפיתם", "כתוביות"). Regression set for VAD: silence, music, soft speech, overlap; empty-reference WER is undefined, so report insertion counts for silence tests.

## 4. Lyrics pass (sung vocals buried in a mix)
Transcribe WITHOUT VAD (large model, beam 5, word timestamps, `condition_on_previous_text=False`) and keep only confident segments: drop if `avg_logprob` < -0.8, `no_speech_prob` > 0.5, `compression_ratio` > 2.4, the same normalised text repeated more than twice, or a known hallucination string when the segment is < 40 characters; accept the pass only with >= 2 segments and >= 20 characters. Tag the result "SUNG LYRICS". If music has a vocal, separate with `demucs --two-stems=vocals` first.

## 5. Word timestamps
Native Whisper word times are not a validated ground truth. Historical median drift ~90 ms (73 ms after a global monotone snap in the author's reels tool; not reproduced by research): fix a perceptible drift with a constant offset; captions lead the voice by 0.08-0.1 s. `stable-ts` refinement was installed by the author; its accuracy gain was not measured. Hebrew forced alignment exists (WhisperX default model, licence unlisted); ElevenLabs forced alignment does not list Hebrew. Keep native timing, corrected text and aligned timing as separate outputs. A manual timing subset is the proposed truth: listen on waveform/spectrogram, define start/end conventions, never use the candidate aligner as its own ground truth.

## 6. WER protocol (use `scripts/wer.py`)
Freeze audio and reference before seeing outputs; no LLM rewrite. Declare normalisation: NFC, lowercase, Unicode punctuation -> space, collapse whitespace, keep symbols, digits and niqqud. Corpus WER = total (S+D+I) / total reference words (never an average of clip WERs); CER with the same policy. Add silence/noise controls. Report wall time separately for load, first inference, warm inference. Five clips are a smoke test; strata to add later: spontaneous speech, code-switching, phone audio, accents, music, overlap, names.
Attribution to keep for FLEURS: "Hebrew samples from FLEURS (Google; Conneau et al.), google/fleurs, revision 70bb2e84b976b7e960aa89f1c648e09c59f894dd, CC BY 4.0. Selected subset; list any resampling, trimming and manual timing additions." Use the TSV + tar route; never an unrestricted `extractall`.

## 7. Cloud options (sourced, NONE run, perishable)
Listed with prices in `agent-content/references/asr-routes.md` §7 (dated; they expire). A cloud run needs the author's approval and a cost estimate (`paid-spend-gate`) and is judged by time-to-accepted-transcript (upload + queue + result + correction), which nobody has measured.

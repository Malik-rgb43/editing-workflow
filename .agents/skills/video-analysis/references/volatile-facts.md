---
module: video-analysis-volatile-facts
checked_at: 2026-10-02
expires: "90 days (2026-12-31); earlier on any ASR runtime, model, driver or price change"
confidence: "measured on one machine / documentary; none re-run for this module"
---

# Volatile facts for video-analysis (dated; re-check before quoting)

Load when: you are about to quote an ASR speed, a WER, a cloud price, a licence or a tool fact in advice, a report or a slide. Never copy these into an always-loaded description. The canonical ASR module is `agent-content/references/asr-routes.md` (owned elsewhere); if numbers differ, that file wins and this one is refreshed.

| Field | Value |
|---|---|
| Fact set | ASR routes and measured speed/WER, VAD behaviour, song-ID transport, OCR support, paid video-understanding options |
| Versions / ids | ivrit-ai whisper-large-v3-turbo (CT2 and GGML conversions, pinned per project); whisper.cpp b5130 for E08; faster-whisper 1.2.1; CTranslate2 4.7.1; librosa 0.11.0; PySceneDetect 0.7.1; Tesseract tessdata `heb` |
| `checked_at` | 2026-10-02 (research date; sources read 2026-10-01) |
| Machine for all measured cells | the reference machine; NVIDIA and Apple routes: unmeasured |
| Confidence | measured cells `[MEASURED-lab]` (one pass, read speech); the rest `[SOURCED-unverified]` or `[VERIFIED-external]` as tagged |
| `expires` | see front matter |
| Non-spending refresh | run the project's own `doctor` / `analyze --check`; time ONE short clip locally and record the timer scope; read official pages only; never upload footage to test a service |

## Records
| id | Fact | Version / scope | checked_at | Source | Confidence | Expiry trigger | Refresh |
|---|---|---|---|---|---|---|---|
| A1 | 614.22 s of public Hebrew read speech (68 FLEURS clips): whisper.cpp Vulkan (8 threads) 105.6 s whole-wrapper = 5.82 audio-s per wall-s; the same build on CPU 1033.0 s (9.78x slower); CTranslate2 int8 CPU 731.4 s (0.84 audio-s per wall-s) | one pass, idle machine, read speech not conversation; no accepted-transcript time; a linear extrapolation to a 1-hour file is about 10 min on Vulkan (arithmetic, not measured) | 2026-10-01 | distilled 06 asr-and-transcription §4.2 (E08) | medium | any runtime/driver/model change | time one 60 s clip per route on the student's machine; name the timer scope |
| A2 | WER on that corpus after NFC + lowercase + punctuation stripped: CPU whisper.cpp 18.09 %, Vulkan 18.26 %, CT2 17.74 %, CT2 with VAD 19.38 % (4-19 word edits of 1161; close counts, not statistical equivalence) | same set; training overlap unknown | 2026-10-01 | E08 | medium | model/normalisation change | score on a student fixture with the same normalisation |
| A3 | Historical owner figure: GPU route 2.4x faster than CPU on a 262 s talk while the machine was loaded 3-4x; 9-23 min per video in a loaded batch | not controlled; conflicts with A1 (9.78x idle) | 2026-10-01 | distilled 06 asr §3.2 | low | n/a | do not quote as a promise |
| A4 | Silero VAD removes hallucinated Hebrew text on 3 s of digital silence and of seeded noise (empty output) but made word edits worse on read speech (225 vs 206); cause unresolved | two controls, not a hallucination rate | 2026-10-01 | E02, E08 | medium | VAD config change | keep a silence/music/soft-speech regression set |
| A5 | On the reference machine's driver whisper.cpp Vulkan crashes unless `GGML_VK_DISABLE_COOPMAT=1`; `whisper-cli` breaks on Hebrew file paths (use an ASCII temp dir); 16 vs 8 CPU threads was about 60 % slower for CTranslate2/torch (not reproduced by E08, which varied only Vulkan threads) | driver/binary specific | 2026-10-01 | video-analysis notes; E08 | medium (A5 threads: low) | driver or build change | `doctor` smoke on the route; never assume on other GPUs |
| A6 | Force `language="he"` for Hebrew audio (model card: detection and translation degrade); never trust one ASR pass for names, brands, numbers; word times are predictions (median drift about 90 ms in the owner's history), not a validated ground truth | ivrit-ai fine-tune, Apache-2.0 weights; the ONNX conversions have unresolved licences | 2026-10-01 | T08 | high (forced language), medium (drift) | per project | measure on a manually aligned subset |
| A7 | Song ID: ShazamIO is reverse-engineered and sends a WAV excerpt; whether only a fingerprint leaves the machine was NOT verified; Chromaprint/AcoustID target near-identical audio; a match is not a synchronisation licence | tool as used by the owner's analyzer | 2026-10-01 | T16-S005-S007, S020-S021 | high (licence statement), low (transport) | library revision | keep `--no-song-id` for private material; read the library source |
| A8 | OCR: Tesseract has `heb.traineddata` (rolling repo); EasyOCR's inspected config lists no Hebrew recogniser; Arabic support is not Hebrew support; a model reading Hebrew on-screen text is a hypothesis needing the same benchmark | tessdata main branch | 2026-10-01 | T16-S002, S015, S035 | medium | any release | run on 10 labelled native-resolution crops, score CER |
| A9 | Gemini video understanding samples at 1 FPS by default (short transitions and fast text fall between samples): exact timing must come from local tools. Dated cost example, estimates not bills: Gemini 2.5 Flash 60 s about USD 0.008-0.012; TwelveLabs Pegasus 1.5 Analyze 60 s about USD 0.044 | prices perishable, stale-risk high | 2026-10-01 | distilled 06 §4.5 (COMPARISON) | medium | any price page change | read the official price page; paid use only through `paid-generation-gate` with a dated estimate and approval |
| A10 | Resource facts of the owner's original analyzer: thumbnails/metrics accumulate for the whole video; the hidden-source-cuts helper holds the whole decoded clip (analytic 6.17 GB for 42 min at 30 fps); the default 3 parallel jobs are not resource-aware | static/analytic review, not measured RSS | 2026-10-01 | T16 OWNER_AUDIT | medium | port rewrite | measure peak RSS on a 5-min clip before queueing long sources |

## Open conflicts (recorded, not resolved)
- [CONFLICT] The blueprint spec line "1 h audio about 6 min on the Vulkan route" does not follow from E08 (5.82 audio-s per wall-s = about 10.3 min per hour, extrapolated). Quote E08 with its scope.
- [CONFLICT] Cut detector F1 appears as 0.89 and as "0.862 to 0.890" (same data, rounding).
- [CONFLICT] Owner's confidence labels H/M/L ("measured >= 2 times") vs T16's evidence-quality/agreement proposal: `reference-style-transfer` uses the agreement definition.

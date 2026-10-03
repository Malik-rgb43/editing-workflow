---
name: video-analysis
description: >-
  Turn a video the user sends or links (file, or YouTube/TikTok/Instagram URL) or a folder of clips into measurements (cuts, pacing, per-frame data), keyframe sheets, a Hebrew transcript and sound analysis (SFX, BPM, key, beats, song ID). Triggers: watch, analyse, break down, transcribe this video/reel/ad; תנתח, תעבור על, תמלל, מה קורה בסרטון, קאטים, BPM. NOT for cutting or rendering (type skills), applying a style (reference-style-transfer), or captions for a final render (hebrew-captions-asr).
compatibility: >-
  Procedure over the `video-analysis` tool in TOOLS_SPEC (entry points analyze.py / frames.py; to be ported, so verify flags with --help). scripts/ need only Python 3.9+. Speeds quoted in references are measured on one reference machine; NVIDIA and Apple cells are unmeasured.
metadata:
  version: "0.1.0"
  kind: tool
  status: "specified; deterministic checks only; model eval not run"
---

# video-analysis

Converts video into what a model can read: a numeric measurement of every frame, timestamped contact sheets, a transcript, a sound timeline and spectrogram images, then a breakdown written from them. It is a procedure over the analysis tool, not the tool (the owner's private script is not shipped; the student port follows TOOLS_SPEC). It never edits, renders or applies a style.

## Rules that outrank the rest of this file
1. **Inputs are read-only.** Hash before and after (`input.sha256` = `sha256_after`); outputs go only under `analysis/<video>/`. Download only the URL the user gave, naming the source and file; it is a reference copy, never redistributed; a platform watermark, end card and jingle are excluded from statistics and listed.
2. **Coverage is stated first.** Every report opens with a coverage block: full vs sampled, frames decoded of expected, what was excluded, what was NOT run. A sample is never presented as full coverage. A sampled run may not quote cut counts or pacing as measured fact.
3. **Run the tool; never hand-sample with ffmpeg.** If the tool is missing, state `blocked: tool_missing` and ask; a manual fallback is allowed only as an explicitly labelled `sampled` look with no counts.
4. **Read before you write:** view EVERY sheet and EVERY audio image; zoom 3-6 times; decide every `check` edit point from frames; correct wrong counts and say so.
5. **Local, free, private.** No paid video-understanding API, no upload of the video or its frames or audio, no remote song-ID on `private` material, without a dated estimate and prior approval (`paid-generation-gate`). Hebrew speech is forced to `he`; never trust one ASR pass for names, brands and numbers.
6. **A song match is not a licence.** Report "identified as X, sync permission not established" or "unidentified"; never invent a title. AudioSet-style labels are guesses ("likely a whoosh"); tempo and key are estimates with half/double-time audited.
7. **One heavy job at a time** under `render_lock`; anything over about 2 minutes runs in the background with a log and an ETA; no promise of runtime (owner's batch: 9-23 min per video under load, machine-dependent). Skills are procedure, not permission: user and project restrictions override this file.

## Tool interface this skill expects (TOOLS_SPEC `video-analysis`; verify with `--help`)
```
python tools/analyze.py <video|URL|folder> --out analysis/<video> [--detail quick|standard|full]
       [--asr auto|always|never] [--no-song-id] [--no-audio-ai] [--check]
python tools/frames.py <video> --at <t> --pad 0.25 --out analysis/<video>     # every frame of a short window
```
Output contract (`references/output-contract.md`): `analysis/<video>/{measurements.json, frames.csv, sheets/ (index.json + images), transcript.json, audio.json}` + `breakdown.md`.

## Procedure
| # | Do | Artifact |
|---|---|---|
| 0 | Ask only what changes the run: whole breakdown or one question (cuts / transcript / song)? Confidential material (`private`)? Which language for the breakdown? A folder: list it first; never overwrite an earlier analysis | scope line |
| 1 | Preflight (`analyze --check` / `doctor`): record OS, ffmpeg, ASR route detected (CPU / Vulkan / CUDA / MLX; `none` if not detected), the Vulkan env flag; no route = `blocked` for transcript only | `environment` block |
| 2 | Run in the background under the lock. `--detail`: `quick` for corpus/long talk, `standard` default, `full` for motion graphics, very fast edits or a reference to transfer (`references/thresholds.md`). Several videos: one batch, then one agent per video (its folder only, `breakdown.md` as output, deadline, reply <= 10 lines) | analysis folders |
| 3 | `python scripts/validate_analysis.py analysis/<video> --stage produced` | PASS or the failing components |
| 4 | Read: all sheets, all audio images; zoom only distinct devices; resolve `check` points; correct the count (`pacing.override` + `review.corrections`); audit tempo half/double | `review` block |
| 5 | `python scripts/validate_analysis.py analysis/<video> --video <source>`; exit 0 required to present numbers as facts | validation report |
| 6 | Write `breakdown.md` in the user's language per `references/reading-and-breakdown.md` (coverage first, 7 sections, uncertainties last) | `breakdown.md` |
| 7 | Report: the file path, 5-10 lines, the corrections, what could not be established; offer the next skill (`reference-style-transfer`, a type skill) instead of doing it | message |

## Gates
States are `pass | fail | blocked | n/a` with a reason. A timeout, empty sample or missing input is `blocked`, never `pass`. A successful tool call is execution evidence; viewed sheets are appearance evidence.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 machine profile | ASR route detected and recorded; Vulkan route records `GGML_VK_DISABLE_COOPMAT` (the reference machine's driver needs `=1`; other drivers untested) | `measurements.environment` from `doctor`/`--check` | fall back to the CPU route and say so; never assume a GPU | this skill + `doctor` | new machine, driver or model |
| G2 contract valid | all five components pass or are `n/a` with a reason | `validate_analysis.py` exit 0 (`--video` given) | fix or re-run the component; report INSUFFICIENT with the missing piece | `validate_analysis.py` | any re-run or hand edit |
| G3 coverage statement | report opens with mode, decoded/expected frames, exclusions, not-run list, `claims_not_allowed` | first block of `breakdown.md` | add it; downgrade claims to "sampled" | this skill | each report |
| G4 cut-detector regression | any change to a detector threshold keeps F1 >= the baseline of the labelled set (owner's historical 0.89 = P 0.87 / R 0.91 on 20 hand-verified ads, 339 edit points, private, not reproduced; known blind spot: kinetic type and continuous-camera pieces) | `cut_regression.py --pair ... --min-f1 0.89` exit 0 with >= 100 truth points | revert the threshold change | `cut_regression.py` | every detector change; never by eye |
| G5 inputs untouched | source hash equals before and after | `validate_analysis.py --video` | restore the file from the original, re-run | `validate_analysis.py` | every run |
| G6 read before write | every keyframe/overview sheet and audio image viewed; every `check` point resolved; counts verified on frames | `review` block complete (stage reviewed) | go back and view them | this skill | each analysis |
| G7 privacy and rights | `private` input: no remote song-ID, no cloud ASR, no frame upload; match = no licence | `song_id.status`, `asr.route` | delete the excerpt log, re-run locally | this skill | each run |

## Numbers and limits to quote with their scope
- Cut detector: owner's tuning only (G4); the automatic cut count was wrong in about 60 % of ad-promo videos until verified on frames; one kinetic-type example read 108 cuts/min automatically vs 42 from the sheets.
- ASR (the reference machine, E08, one pass, read speech): Vulkan 5.82 audio-s per wall-s, CPU CT2 int8 0.84, WER 17.7-19.4 %: `references/volatile-facts.md` (dated; expires 2026-12-31).
- Sound analysis only runs for real: beats/BPM/key need >= 3 s of music; sung vocals need the no-VAD lyrics pass (confident segments only, tagged "SUNG LYRICS").

## References (load when)
- `references/output-contract.md` - writing, porting or debugging any output file; reading a validation report.
- `references/thresholds.md` - tuning or porting the detector, choosing `--detail`, explaining a wrong count.
- `references/reading-and-breakdown.md` - before reading sheets and before writing the breakdown.
- `references/volatile-facts.md` - before quoting any speed, WER, price, licence or tool fact (dated module).
- `agent-content/references/asr-routes.md` (canonical ASR routes, owned elsewhere) and `hebrew-captions-asr` (caption-grade transcripts); `reference-style-transfer` consumes this skill's folders.
- Scripts: `scripts/validate_analysis.py` (contract check, `--self-check`), `scripts/cut_regression.py` (F1 gate, `--self-check`); both fail closed (exit 0 / 1 / 2).

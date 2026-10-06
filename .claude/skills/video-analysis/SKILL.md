---
name: video-analysis
description: >-
  Turn a video the user sends or links (file or URL) or a folder of clips into measurements (cuts, pacing, per-frame data), keyframe sheets, a transcript (Hebrew deepest) and sound (loudness, hits, BPM, key, beats). Triggers: watch, analyse, break down, transcribe this video/reel/ad; תנתח, תעבור על, תמלל, מה קורה בסרטון, קאטים, BPM. NOT for cutting or rendering (`pro-video-editor`), applying a style (reference-style-matching), or captions for a final render (captions-transcription).
compatibility: >-
  Procedure over the toolkit's `tools/analyze.py` and `tools/frames.py` (verify flags with --help). scripts/ need only Python 3.9+. Speeds quoted in references are measured on one reference machine; NVIDIA and Apple cells are unmeasured.
metadata:
  version: "0.1.0"
  kind: tool
  status: "specified; deterministic checks only; model eval not run"
---

# video-analysis

Converts video into what a model can read: a numeric measurement of every frame, timestamped contact sheets, a transcript, a sound timeline and spectrogram images, then a breakdown written from them. It is a procedure over the analysis tools (`tools/analyze.py`, `tools/frames.py`), written for this toolkit. It never edits, renders or applies a style.

## Start: connections
If `<project>/_work/connections.json` from this session exists (written by the router or `pro-video-editor`), read it; otherwise run `python tools/connections.py -o <project>/_work/connections.json` (about 1 s, presence only) and read your own tool list (claude.ai connectors appear only there). For this skill: yt-dlp for a link the user gave, local speech recognition (faster-whisper; the multilingual model is a download shown first, with the user's yes), a hosted vision API only with the client's yes. No project (a plain "analyse this"): run it without `-o`. Say use / not needed / fallback in one line, then continue. A missing connection never stops the work; anything paid goes through `paid-spend-gate`.

## Rules that outrank the rest of this file
1. **Inputs are read-only.** Hash before and after (`input.sha256` = `sha256_after`). Outputs go only under `<out>` = `<project>/_work/analysis/<video-id>/` (the folder `tools/prep.py` writes; reuse an existing analysis there instead of re-running). No project yet: `analysis/<video-id>/` in the folder the user works in. Download only the URL the user gave, naming the source and file; it is a reference copy, never redistributed; a platform watermark, end card and jingle are excluded from statistics and listed.
2. **Coverage is stated first.** Every report opens with a coverage block: full vs sampled, frames decoded of expected, what was excluded, what was NOT run. A sample is never presented as full coverage. A sampled run may not quote cut counts or pacing as measured fact.
3. **Run the tool; never hand-sample with ffmpeg.** If the tool is missing, state `blocked: tool_missing` and ask; a manual fallback is allowed only as an explicitly labelled `sampled` look with no counts.
4. **Read before you write:** view EVERY sheet and EVERY audio image; zoom 3-6 times; decide every `check` edit point from frames; correct wrong counts and say so.
5. **Local, free, private, no assumed language.** No paid video-understanding API and no upload of the video, its frames or its audio without a dated estimate and prior approval (`paid-spend-gate`). The speech language comes from the user or Round 0 and is passed as `--language <code>`; unknown = `auto` (the default). The Hebrew-tuned model refuses non-Hebrew speech and prints the multilingual route; take it only with the user's yes for the download. Never trust one ASR pass for names, brands and numbers.
6. **No song identification.** The tool never identifies a song: write "song not identified (not run)", never a guessed title; even a title the user names grants no licence. What is measured: loudness, silences, transient hits, and BPM, key and beats as estimates with half/double time audited. A transient is not a named sound ("a hit at 3.2 s", never "a whoosh" as fact).
7. **One heavy job at a time** under `render_lock`; anything over about 2 minutes runs in the background with a log and an ETA; no promise of runtime (author's batch: 9-23 min per video under load, machine-dependent). Skills are procedure, not permission: user and project restrictions override this file.

## Tool interface (verify with `--help`)
```
python tools/analyze.py <video|folder> --out <out> [--detail quick|standard|full] [--language auto|he|en|...]
       [--asr auto|always|never] [--model-dir DIR | --allow-download] [--exclude end_card:42.1-45] [--private] [--force]
python tools/analyze.py <URL> --download --out <out>     # only the URL the user gave; ask first
python tools/analyze.py --check                          # environment
python tools/frames.py <video> --at <t> --pad 0.25 --out <out>     # every frame of a short window
```
`--language` defaults to `auto`; pass the code once it is known. No song identification and no sound-event labels are run (`--no-song-id` / `--no-audio-ai` are accepted and change nothing). Output contract (`references/output-contract.md`): `<out>/{measurements.json, frames.csv, sheets/ (index.json + images), transcript.json, audio.json}` + `breakdown.md`.

## Procedure
| # | Do | Artifact |
|---|---|---|
| 0 | Ask only what changes the run: whole breakdown or one question (cuts / transcript / sound)? Confidential material (`--private`)? The spoken language: take it from Round 0 or the user, detect it, or ask; pass `--language <code>` (the tools default to `auto`). Which language for the breakdown? A folder: list it first. An analysis already in `<out>`: reuse it, never overwrite | scope line |
| 1 | Preflight (`analyze --check` / `doctor`): record OS, ffmpeg, ASR route detected (`cpu-ct2`; `none` if the weights are not installed); no route = `blocked` for transcript only | `environment` block |
| 2 | Run in the background under the lock. `--detail`: `quick` for corpus/long talk, `standard` default, `full` for motion graphics, very fast edits or a reference to transfer (`references/thresholds.md`). Several videos: one batch, then one agent per video (its folder only, `breakdown.md` as output, deadline, reply <= 10 lines) | analysis folders |
| 3 | `python scripts/validate_analysis.py <out> --stage produced` | PASS or the failing components |
| 4 | Read: all sheets, all audio images; zoom only distinct devices; resolve `check` points; correct the count (`pacing.override` + `review.corrections`); audit tempo half/double | `review` block |
| 5 | `python scripts/validate_analysis.py <out> --video <source>`; exit 0 required to present numbers as facts | validation report |
| 6 | Write `breakdown.md` in the user's language per `references/reading-and-breakdown.md` (coverage first, 7 sections, uncertainties last) | `breakdown.md` |
| 7 | Report: the file path, 5-10 lines, the corrections, what could not be established; open the overview sheet and the audio image in the browser pane with it. For what comes next, go back through `video-request-router` (or straight to `pro-video-editor` when the user wants an edit) instead of doing it here | message |

## Gates
States are `pass | fail | blocked | n/a` with a reason. A timeout, empty sample or missing input is `blocked`, never `pass`. A successful tool call is execution evidence; viewed sheets are appearance evidence.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 machine profile | ASR route detected and recorded (`cpu-ct2` or `none`) | `measurements.environment` from `doctor`/`--check` | fall back to the CPU route and say so; never assume a GPU | this skill + `doctor` | new machine, driver or model |
| G2 contract valid | all five components pass or are `n/a` with a reason | `validate_analysis.py` exit 0 (`--video` given) | fix or re-run the component; report INSUFFICIENT with the missing piece | `validate_analysis.py` | any re-run or hand edit |
| G3 coverage statement | report opens with mode, decoded/expected frames, exclusions, not-run list, `claims_not_allowed` | first block of `breakdown.md` | add it; downgrade claims to "sampled" | this skill | each report |
| G4 language passed | the transcript's language is the one the user or Round 0 gave (`--language <code>`), or `auto` and said so | `transcript.json` `language` and `asr.language_forced` | re-run the transcript with the right code | this skill | the user names the language |
| G5 inputs untouched | source hash equals before and after | `validate_analysis.py --video` | restore the file from the original, re-run | `validate_analysis.py` | every run |
| G6 read before write | every keyframe/overview sheet and audio image viewed; every `check` point resolved; counts verified on frames | `review` block complete (stage reviewed) | go back and view them | this skill | each analysis |
| G7 privacy and rights | `private` input: no cloud ASR, no frame or audio upload; no song title claimed | `asr.route`, `input.private`, the breakdown's music line | delete any excerpt log, re-run locally; remove the title | this skill | each run |
Changing the cut detector has its own regression gate (F1 against a labelled set, `scripts/cut_regression.py`): `references/thresholds.md`, section 0.

## Numbers and limits to quote with their scope
- Cut detector: author's tuning only (`references/thresholds.md`); the automatic cut count was wrong in about 60 % of ad-promo videos until verified on frames; one kinetic-type example read 108 cuts/min automatically vs 42 from the sheets.
- ASR (the reference machine, E08, one pass, read Hebrew speech): CPU CT2 int8 0.84 audio-s per wall-s, WER 17.7-19.4 %: `references/volatile-facts.md` (dated; expires 2026-12-31). Other languages: unmeasured.
- Sound analysis only runs for real: beats/BPM/key need >= 3 s of music; sung vocals need the no-VAD lyrics pass (confident segments only, tagged "SUNG LYRICS").

## References (load when)
- `references/output-contract.md` - writing, porting or debugging any output file; reading a validation report.
- `references/thresholds.md` - tuning, porting or regression-testing the detector, choosing `--detail`, explaining a wrong count.
- `references/reading-and-breakdown.md` - before reading sheets and before writing the breakdown.
- `references/volatile-facts.md` - before quoting any speed, WER, price, licence or tool fact (dated module).
- `agent-content/references/asr-routes.md` (canonical ASR routes, owned elsewhere) and `captions-transcription` (caption-grade transcripts in any language); `reference-style-matching` consumes this skill's folders.
- Scripts: `scripts/validate_analysis.py` (contract check, `--self-check`), `scripts/cut_regression.py` (detector regression, `--self-check`); both fail closed (exit 0 / 1 / 2).

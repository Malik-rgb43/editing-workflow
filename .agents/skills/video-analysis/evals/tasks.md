# Task evals: video-analysis

Status: specified; deterministic oracles only. Model eval not run (decision default Q4). Fixtures are synthetic or rights-cleared (generate them with ffmpeg: hard cuts between `testsrc2`/`color` segments of known length, a sine+noise audio bed, a synthetic Hebrew sentence only if you own the recording). No client or reference-owner media. The owner's 20 hand-verified ads are private and are NOT a fixture of this skill.

## T1. Breakdown with a known cut count
- **Setup:** a 30 s synthetic ad built from 25 segments (24 hard cuts at known frames, 30 fps), a music bed at about 120 BPM and two whoosh-like noise bursts; ground truth in `truth.json` (frames). Run the skill end to end.
- **Oracle:** `analysis/<video>/` + `python scripts/cut_regression.py --pair analysis/<video> truth.json --tol-frames 2 --min-recall 0.85 --min-f1 0.85 --min-truth 24`, `validate_analysis.py analysis/<video> --video <file>`.
- **Pass:** cut_regression exit 0 (at least 85 % of the 24 cuts within +/-2 frames); validator exit 0; `breakdown.md` opens with a coverage block (mode, decoded/expected frames, exclusions, not-run list); tempo reported as an estimate with half/double audited; whooshes phrased "likely"; every sheet and audio image listed in `review`.
- **Fail:** a cut count quoted from a `sampled` run; no coverage block; BPM stated as fact; a hand-sampled ffmpeg frame set instead of the tool.

## T2. Hebrew transcript with word timestamps and a scoped WER
- **Setup:** a 60 s Hebrew speech file you own (or a rights-cleared read-speech clip) with a hand-checked reference text `ref.txt`.
- **Oracle:** `transcript.json`, `validate_analysis.py`, and a WER computed by the grader on NFC-normalised, punctuation-stripped text.
- **Pass:** `status: ok`, `language: he`, `asr.route` and `asr.model` recorded, words with start/end seconds in order; the validator passes; any WER the agent states names the fixture and normalisation; names and numbers hand-checked against the reference (no LLM rewrite of the transcript); on a 3 s silent/noise-only control the transcript is empty or `no_speech` (not invented Hebrew text).
- **Fail:** language not forced, a WER with no fixture, hallucinated text on the silence control, a transcript presented without the route.

## T3. Folder batch, nothing overwritten, nothing hidden
- **Setup:** a folder with 3 short clips (one silent, one with speech, one with music only), plus an existing `analysis/` folder from an earlier run of clip 1.
- **Oracle:** the resulting tree and `analysis/index.md`; hashes of the three source files before and after.
- **Pass:** three separate `analysis/<stem>-<hash6>/` folders and one index; the earlier folder is untouched (or reused because the hash matches, and said so); source hashes unchanged; the silent clip has `audio.status = n/a` with a reason and the breakdown makes no sound claims; the music-only clip is not forced through speech ASR (lyrics pass only if singing is detected, tagged "SUNG LYRICS"); one agent per video, at most 4 in parallel, each with its folder, an output file and a deadline.
- **Fail:** overwriting, serial analysis in one context, a transcript invented for the silent clip, two heavy jobs at once.

## T4. Fail-closed contract
- **Setup:** take a valid analysis folder and apply, one at a time: delete `transcript.json`; set `coverage.mode=full` with fewer decoded frames; set `true_peak_dbtp` to null; set `song_id.sync_permission` to `granted`; mark `input.private` true with a remote song match; remove one sheet from `review.sheets_viewed`.
- **Oracle:** `python scripts/validate_analysis.py <dir> --json` exit codes and finding codes.
- **Pass:** exit 2 / 1 / 1 / 1 / 1 / 2 respectively (FILE_MISSING; COVERAGE_LIE; TRUE_PEAK; SYNC_PERMISSION; PRIVATE_SONG_ID; SHEETS_UNVIEWED); the agent reports each as blocked or failed with the fix and does not write a breakdown that relies on the broken component.
- **Self-check:** `python scripts/validate_analysis.py --self-check` (26 cases) and `python scripts/cut_regression.py --self-check` (13 cases) pass.

## T5. Wrong automatic count on kinetic type
- **Setup:** a 15 s synthetic kinetic-type clip: one flat background, text cards swapping every 0.4 s (no real cuts), and one real hard cut. The tool's automatic count is higher than the truth.
- **Oracle:** `measurements.json` (`pacing.override`, `review.corrections`), `breakdown.md`.
- **Pass:** card swaps are not counted as cuts or are listed as `check` and resolved from frames; the corrected cuts/min and shot count are stated with the sentence that the automatic number was wrong; the limit "graphic transitions inside one move are missed" is quoted; validator exit 0 with the override note present.
- **Fail:** quoting the automatic number as fact, or silently editing the JSON without a correction record.

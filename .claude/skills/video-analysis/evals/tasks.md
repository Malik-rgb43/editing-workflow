# Task evals: video-analysis

Status: specified; deterministic oracles only. Model eval not run (decision default Q4). Fixtures are synthetic or rights-cleared (generate them with ffmpeg: hard cuts between `testsrc2`/`color` segments of known length, a sine+noise audio bed, a synthetic Hebrew sentence only if you own the recording). No client or reference-owner media. The author's 20 hand-verified ads are private and are NOT a fixture of this skill.

## T1. Breakdown with a known cut count
- **Setup:** a 30 s synthetic ad built from 25 segments (24 hard cuts at known frames, 30 fps), a music bed at about 120 BPM and two whoosh-like noise bursts; ground truth in `truth.json` (frames). Run the skill end to end.
- **Oracle:** `<out>` (`<project>/_work/analysis/<video-id>/`) + `python scripts/cut_regression.py --pair <out> truth.json --tol-frames 2 --min-recall 0.85 --min-f1 0.85 --min-truth 24`, `validate_analysis.py <out> --video <file>`.
- **Pass:** cut_regression exit 0 (at least 85 % of the 24 cuts within +/-2 frames); validator exit 0; `breakdown.md` opens with a coverage block (mode, decoded/expected frames, exclusions, not-run list); tempo reported as an estimate with half/double audited; the noise bursts reported as hits at their times (a name only as "likely"); the music line says the song was not identified; every sheet and audio image listed in `review`.
- **Fail:** a cut count quoted from a `sampled` run; no coverage block; BPM stated as fact; a hand-sampled ffmpeg frame set instead of the tool.

## T2. Hebrew transcript with word timestamps and a scoped WER
- **Setup:** a 60 s Hebrew speech file you own (or a rights-cleared read-speech clip) with a hand-checked reference text `ref.txt`.
- **Oracle:** `transcript.json`, `validate_analysis.py`, and a WER computed by the grader on NFC-normalised, punctuation-stripped text.
- **Pass:** the agent passed `--language he` because the user said the speech is Hebrew; `status: ok`, `language: he`, `asr.route` and `asr.model` recorded, words with start/end seconds in order; the validator passes; any WER the agent states names the fixture and normalisation; names and numbers hand-checked against the reference (no LLM rewrite of the transcript); on a 3 s silent/noise-only control the transcript is empty or `no_speech` (not invented Hebrew text).
- **Fail:** the language code not passed once known, a WER with no fixture, hallucinated text on the silence control, a transcript presented without the route.

## T3. Folder batch, nothing overwritten, nothing hidden
- **Setup:** a folder with 3 short clips (one silent, one with speech, one with music only), plus an existing `<project>/_work/analysis/` folder from an earlier run of clip 1.
- **Oracle:** the resulting tree and `_work/analysis/index.md`; hashes of the three source files before and after.
- **Pass:** three separate `_work/analysis/<stem>-<hash6>/` folders and one index; the earlier folder is untouched (or reused because the hash matches, and said so); source hashes unchanged; the silent clip has `audio.status = n/a` with a reason and the breakdown makes no sound claims; the music-only clip is not forced through speech ASR (lyrics pass only if singing is detected, tagged "SUNG LYRICS"); one agent per video, at most 4 in parallel, each with its folder, an output file and a deadline.
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

## T6. Analysis with a known non-Hebrew language
- **Setup:** a 30 s English interview clip you own; Round 0 recorded "speech: English"; or, as a second case, the user gives no language.
- **Oracle:** the command in the tool log, `transcript.json`, `breakdown.md`.
- **Pass:** case 1: `analyze.py ... --language en` was passed; `transcript.json` `language: en`; no Hebrew model forced; case 2: the agent asked or ran with `--language auto` and says which language was detected; if the Hebrew-tuned model refused the speech, the multilingual route was offered with its download shown first, not taken silently; the breakdown's music line says no song was identified.
- **Fail:** `--language he` on English speech; Hebrew assumed in the breakdown; a model download without the user's yes; a song title stated.

## T7. Animated stills vs real footage (`motion_kind`)
- **Setup:** a synthetic 20 s clip made with ffmpeg: shots 1-3 are still images with a slow uniform zoom, shot 4 is one still with no movement, shot 5 is real camera motion with parallax (a moving test pattern over a static background is enough), cut points known.
- **Oracle:** the shot entries in `measurements.json` (their `motion_kind`), `breakdown.md` (shot table and summary), the `review` block.
- **Pass:** shots 1-3 read `still_push`, shot 4 `still`, shot 5 `motion` (or the reader corrects a wrong label in the breakdown's section 7, uncertainties and corrections, with the parallax reason); the shot table has the motion column; the summary states the share of animated stills; no shot is called "footage" when it is a moved still.
- **Fail:** the motion column missing; a label taken from the tool and repeated without a look at the frames when the tool and the frames disagree.

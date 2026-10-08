# Output contract: `<project>/_work/analysis/<video-id>/` (schema_version 1.0.0)

Load when: running or porting the `analyze` tool, writing any of the JSON files by hand, reading a `validate_analysis.py` report, or handing an analysis to another skill (`reference-style-matching`, `benchmark`). The checker is `scripts/validate_analysis.py`; every rule below is enforced there unless marked "declared".

The folder lives at `<project>/_work/analysis/<video-id>/` (what `tools/prep.py` writes; `analysis/<video-id>/` when there is no project). `<video-id>` = a slug of the file stem (prep, single file) or the stem + `-` + first 6 hex of the source sha256 (batch mode: one folder per video under the parent `--out`). A re-run with the same hash may reuse the folder; `--force` recomputes. The source file is never written to; sidecar files live only inside the analysis folder.

```
<video-id>/
  measurements.json     identity, environment, coverage, edit points, pacing, review      (required)
  frames.csv            per-frame data; REQUIRED when coverage.mode = "full"
  sheets/               index.json + sheet_*.jpg, overview_*.jpg, audio_*.png, zoom_*      (required)
  transcript.json       ok | no_speech | not_run                                           (required)
  audio.json            loudness, layers, SFX, music, song id, images | n/a | not_run      (required)
  report.md, breakdown.md   human-readable results (optional; the breakdown template is in reading-and-breakdown.md)
```
All JSON: UTF-8 (no BOM required, tolerated), strict (no NaN/Infinity, no duplicate keys). Times are seconds from the first presented frame; every time that can be a frame is stored with its integer frame index too. Rational fps only (`fps_num`/`fps_den`), never a float such as 29.97.

## measurements.json
| Field | Type / rule |
|---|---|
| `schema_version` | `"1.0.0"` |
| `tool` | `{name, version, detail: quick|standard|full}` |
| `input` | `name`, `sha256`, `sha256_after` (must be equal: inputs are read-only), `size_bytes`, `duration_s` > 0, `fps_num`, `fps_den` (positive ints), `width`, `height`, `rotation`, `vfr` (bool), `frames_expected` (within 2 of duration x fps unless `vfr`), `has_audio` (bool), `private` (bool, default false: confidential material) |
| `environment` | `os`, `ffmpeg`, `asr_route` (`cpu-ct2`, `cloud:<name>`, `none`), `env` (map), plus free-form cpu/gpu/ram. A route that was not detected is `none`, never guessed |
| `coverage` | `mode`: `full` (every frame decoded: `frames_decoded == frames_expected`) or `sampled` (anything less; then no cut count or pacing may be presented as measured fact), `frames_decoded` > 0, `frames_expected`, `pts_policy` (`decoder_pts`), `excluded[]` = `{kind: end_card|watermark|intro, start_s, end_s, reason}` (platform watermarks, end cards and jingles are excluded from statistics and listed) |
| `edit_points[]` | `id` (unique), `t_s`, `frame` (consistent with `t_s` at the fps), `kind`: `cut` (hard cut or transition counted as an edit) \| `transition` \| `check` (jump cut vs graphic swap: numbers cannot tell), `type`: `hard, whip, slide, dissolve, flash, dip_black, glitch, fast_transition, unknown`, `confidence`: `auto` \| `verified` (confirmed on frames) \| `corrected` (added or retyped after reading frames), `note`. Ordered, at least 1 frame apart: a transition is ONE edit point and its frames are not shots |
| `pacing` | `edit_points` (= number of `cut`+`transition` entries), `cuts_per_min` (= that count / minutes, to 0.05), `median_shot_s` (from the edit points), `mean_shot_s`, `shortest_shot_s`, `longest_shot_s`, `first_cut_s`; optional `override: {cuts_per_min, note}` when frames show the automatic count is wrong (the equivalent of the author's `metrics_override.json`) |
| `motion_kind` (per shot) | in `measurements.json` `shots[]` (one entry per shot between edit points, with the numbers that decided it in `motion`): `still` (no motion) \| `still_push` (a still with a uniform zoom or pan) \| `motion` (real motion). A tool label, confirmed on frames by the reader (`reading-and-breakdown.md` section 2); consumed by `reference-style-matching` (feasibility of each borrowed device) |
| `holds[]`, `stepped_cadence` | static holds (`motion < 0.25` for >= 1.0 s) and repeated-frame cadence (24p in 60p, 12 fps AI footage, stop-motion): cuts are then measured on unique pictures |
| `shots[]`, `shots_method` | optional; one row per shot between counted edit points: `id`, `start_frame`, `end_frame` (inclusive), `start_s`, `end_s` (= the next shot's start), `motion_kind`: `still` \| `still_push` (one picture under a uniform zoom / pan: an animated still) \| `motion` (real motion), and `motion` (the numbers that decided it). **Declared**: a similarity-warp fit on the thumbnails with house thresholds (listed in `shots_method`), a hint to check on the sheets, not validated |
| `per_frame` | `{file: "frames.csv", columns[], rows}`; recommended columns `frame,t_s,luma,luma_std,sat,content,hist,motion,black,white,cut` |
| `review` (stage `reviewed`) | `reviewed_by` (`model`/`human`), `sheets_viewed[]` (must include every keyframe/overview sheet), `audio_images_viewed[]` (every audio image), `zoom_count`, `corrections[]` = `{edit_point, action: removed|added|retyped, reason}`. **Declared by the reader**: the script checks completeness, not that anyone looked |

`frames.csv`: header row, exactly `coverage.frames_decoded` data rows, strictly increasing `frame` and non-decreasing `t_s`, every other column finite.

## sheets/index.json
`{schema_version, sheets: [{file: "sheets/<name>", kind: keyframes|overview|audio|zoom, t_start_s, t_end_s, tiles, tile_px, frames?: [{frame, t_s, label}]}]}`.
Rules: real JPEG/PNG (magic bytes), not empty, inside `sheets/`; at least one keyframes/overview sheet; an audio image when the input has audio; in `full` mode the keyframe sheets must reach every part of the video within 2.5 s (the `standard` max gap) except listed exclusions; tiles under 160 px are warned (models misread them; the author's defaults: 16:9 3x3 of 460 px, 9:16 4x2 of 280 px, about 1.1-1.3 MP per sheet; zoom sheets keep tiles >= 280 px).

## transcript.json
`{schema_version, status, language, reason?, asr: {route, model, model_revision, vad, device, language_forced}, segments[], words[], burned_captions[]?, qa?}`.
- `status: ok` needs >= 1 segment `{start_s, end_s, text, kind: speech|sung|low_confidence|over_music, avg_logprob?, no_speech_prob?}` ordered, inside the video; `words[]` `{text, start_s, end_s}` ordered (a warning if absent: captions and joins need them); `asr.route` and `asr.model` recorded. A Hebrew label with mostly non-Hebrew text fails (wrong language forced or wrong file). Segments over music or sung lyrics are tagged, never presented as dialogue.
- `status: no_speech` needs `reason`; it must agree with `audio.json` (less than 0.8 s speech and 2.0 s singing) or, for a file with no audio stream, with `audio.status = n/a`.
- `status: not_run` needs `reason`; the validator reports INSUFFICIENT_EVIDENCE and lists "what is said" as a claim the breakdown may not make (unless the skip is declared with `--allow-not-run`).
- A `qa.wer` number must name its `wer_fixture`. Burned-in captions are authoritative for wording, the transcript for timing; flag differences.

## audio.json
`{schema_version, status: ok|n/a|not_run, has_audio, reason?, loudness, layers, sfx_events[], silences[], music, song_id, images[]}`.
- `loudness`: `integrated_lufs` in [-70, 0], `lra` >= 0, `true_peak_dbtp` a NUMBER (0.0 is a number; null fails), `meter`, `scope` (whole file; excluded end card noted).
- `layers`: `speech`, `music`, `singing` = ordered `[start_s, end_s]` lists inside the video.
- `sfx_events[]`: `{t_s, labels[], peak, likely}`; labels are AudioSet-style model guesses ("likely a whoosh"), confirmed on the spectrogram before a claim.
- `music`: `present`; when true: `tempo_bpm` in [30, 300] (an estimate), `beats_s` increasing, `half_double_audited: true` (checked against the audio image; otherwise INSUFFICIENT), `key` + `key_confidence`, `energy_arc[]`, `cut_on_beat {tolerance_s, ratio, chance}` (a ratio near chance means no sync).
- `song_id`: the toolkit's analyzer runs no song identification and always writes `skipped` (`opted_out` for private input); the other values exist for imported analyses. `status` matched | no_match | skipped | opted_out; **`sync_permission` must be exactly `"not_established"`** (a match names the track, it grants no licence); a match records `title` and `transport` (remote | local). A `private` input must be `opted_out` or `skipped`: no audio excerpt may leave the machine.
- `images[]`: spectrogram/loudness images, each an entry of `sheets/index.json`.
- `status: n/a` only for a file with no audio stream (`has_audio: false` + reason).

## Validation stages and exit codes
`validate_analysis.py <dir> --stage produced` right after the tool ran (review block not required); `--stage reviewed` (default) after the sheets were read and every `check` edit point resolved. Exit 0 PASS, 1 FAIL (a rule is broken), 2 INSUFFICIENT_EVIDENCE (a component was not run, a file is missing or empty, nothing was decoded, a sheet is unviewed). `--video <file>` re-hashes the source (G5). `--allow-not-run transcript,audio` records a deliberate skip and prints `claims_not_allowed`.

## What the contract deliberately does not promise
Cut correctness (use `cut_regression.py` on a labelled set and the frame-reading rules), transcript accuracy (WER only on a named fixture), music licence, runtime. The ported tool may add optional files (`report.md`, `breakdown.md`, thumbnails cache); consumers must ignore unknown files and fields.

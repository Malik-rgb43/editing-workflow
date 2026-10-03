# Reading the numbers, correcting them, and writing the breakdown

Load when: you have a validated analysis folder and are about to read the sheets, correct a count, or write `breakdown.md`. Source: distilled 06 reference-analysis §1.5-§1.6 (2026-10-01).

## 1. Reading discipline (the model cannot be handed numbers alone)
A model reads what it is shown. The tool gives deterministic timestamps; the model explains functions from images. Order:
1. `validate_analysis.py <dir> --stage produced` passes (or you report why not).
2. View EVERY keyframe/overview sheet and EVERY audio image before writing a word about the video. A description written after viewing some sheets is a sample, and must say so.
3. Zoom only on purpose: 3-6 zooms per video, windows under about 1 s, one instance of each distinct device. Never zoom every caption or hit.
4. Resolve every `check` edit point and every suspicious transition from the frames (kinetic type, light leak, flash, whip, slide, picture-in-picture, motion blur): retype it, remove it, or add a missed one, and write the correction into `review.corrections` with a reason.
5. If the count changed, write `pacing.override {cuts_per_min, note}` and say plainly in the breakdown: corrected shot count and cuts per minute, and that the automatic number was wrong.
6. Fill `review` (sheets viewed, audio images viewed, zoom count) and run `validate_analysis.py <dir>` (stage reviewed).

## 2. How to read each kind of number
| Kind | Rule |
|---|---|
| Measurements | cuts, shot lengths, loudness, silences, transients: report with their units and the coverage mode |
| Edit point | a hard cut or a transition = ONE event; the transition's frames are not shots |
| Frame changes NOT counted | caption/PiP/graphic swaps, camera moves/blur, flicker, type swaps on a flat field: glance at those times; zoom only when the count matters |
| `check` points | background identical: a jump cut (keep) or a PiP/product/graphic swap (not a cut). Numbers cannot tell: decide from frames |
| Estimates | tempo, beats, key: say "about 128 BPM (estimate; half/double-time audited)" |
| Model guesses | SFX, genre, mood labels: "likely a whoosh", confirmed on the spectrogram before it is a claim |
| Burned-in captions vs transcript | captions are authoritative for wording, the transcript for timing; list differences; segments tagged over-music / sung / low-confidence may be lyrics or hallucinations; a sung transcript is presented as lyrics |
| Stepped cadence | repeated frames (24p in 60p, 12 fps AI footage, stop-motion, screen recording): cuts counted on unique pictures |
| Kinetic type / continuous camera | graphic transitions inside one move are often missed: count from the sheets and correct |
| Platform downloads | watermark, end card and jingle are not part of the edit: exclude them from pacing and energy statements and list the exclusion |
| Song match | names a track, grants nothing: "identified as <title>; sync permission not established"; no match = "unidentified", never a guessed title |

## 3. Breakdown template (`breakdown.md`)
Write in the user's language; keep quoted on-screen text verbatim in its original language (Hebrew stays Hebrew, with the logical text order; do not "fix" the user's spelling in a quote). Sections, in order:
0. **Coverage statement (first, always):** mode (full / sampled), frames decoded of expected, what was excluded (end card, watermark), ASR route and model, what was NOT run (and so cannot be discussed), source sha256 (first 12), tool version, validation status and date. Never present a sample as full coverage.
1. **Summary:** what it is, length, format, aspect, style, video TYPE (talking-head, ad-promo, ugc-unboxing, testimonial, podcast-clip, tutorial-explainer, product-demo, ai-generated, motion-graphics, music-montage, vlog-lifestyle, comedy-meme, trailer-teaser).
2. **Shot-by-shot table:** `# | time | what we see | on-screen text | speech | sound | transition out`.
3. **On-screen text/captions:** text, in/out time, position (Hebrew OCR is a separate, benchmarked step; reading by a model is a hypothesis with a confidence label).
4. **Speech transcript with timestamps** (say plainly if there is none; label sung lyrics).
5. **Sound design:** music (song ID status, BPM estimate, key estimate, mood guess, energy arc, drop, cut-on-beat verdict with the chance level), SFX (time, likely sound, lands on a cut?), silences before drops, loudness (LUFS, true peak, scope).
6. **Editing analysis:** the hook (first 3 s: what, text, zoom, SFX), pacing (distribution, not only a median), transition types, picture/sound sync points, what makes it work, concrete improvements. No claim that any hook length works as a rule: no platform source verifies a 3-second threshold.
7. **Uncertainties and corrections:** every correction made to the automatic numbers, every `check` decision, every low-confidence segment.
Save as `breakdown.md` in the analysis folder. Several videos: one batch run, then one agent per video (file list: its folder only; output: its `breakdown.md`; reply at most 10 lines), then a merged `analysis/index.md` (video, folder, status, one-line type, corrected cuts/min, loudness).

## 4. Common mistakes (each happened)
Sampling frames by hand with ffmpeg instead of the tool; describing after viewing only some sheets; analysing several videos serially in one context; forcing `--lang he` / `--asr always` on a music-only video (hallucinated lyrics); zooming every caption; trusting cuts/min on kinetic type; calling an AudioSet label a fact; inventing a song name; a platform end card counted as a shot; a 42-minute source blocking the queue for hours (run long jobs in the background under the lock, in approved windows when possible).

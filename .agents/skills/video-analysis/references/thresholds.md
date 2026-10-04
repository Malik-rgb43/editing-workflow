# Detector thresholds, keyframe tiers and audio parameters

Load when: tuning or porting the cut detector, choosing `--detail`, or arguing about why a count is off. Source: the author's analyzer as documented in distilled 06 reference-analysis §1.2-§1.4 (checked 2026-10-01); `[PROVEN-internal]` unless stated; values are the author's tuning on his data, not universal constants.

**Hard rule: change a threshold only with a regression run.** Run `scripts/cut_regression.py` on a rights-cleared labelled set before and after; keep the change only if F1 does not drop below the recorded baseline for that set. Never tune by eye. Rejected ideas (owner, tested against his 20-ad ground truth): a zoom-compensated search (hurt punch-in cuts, no gain) and rejecting picture-in-picture swaps outright (hurt real jump cuts: they are flagged `check` instead).

## 1. What counts as an edit point
A hard cut OR a transition (whip, slide, dissolve, flash/light leak, glitch, fast zoom/mask transition), **each ONE event**. Not counted: caption/PiP/graphic swaps, camera moves and motion blur, boiling or flickering textures, type swaps on the same flat field. Frames inside a transition are not shots.

## 2. Features and decision rules (per frame, decoded once at a 96-px long side)
Features: `luma`, `luma_std`, `sat`, `content` (mean of |dHue|+|dSat|+|dValue|/3 against the previous frame), `hist` (half L1 distance of a 48-bin histogram / 3), `motion` (mean |dGrey|), `black` (share of pixels < 20), `white` (share > 235).

| Step | Rule | Value |
|---|---|---|
| Candidate hard cut | `content` spike over the mean of 2 neighbours each side: ratio >= 3.0 and content >= 12.0, OR (hist >= 0.4, ratio >= 1.8, content >= 10.0) | `CUT_RATIO = 3.0` |
| Verdict "cut" | mean luma jump between the two frames > 40 | cut |
| Verdict "partial" | share of thumbnail pixels changed by > 4 levels < 0.28 (verified cuts 0.35-0.96; ordinary moving frames 0.11-0.26) | caption/PiP/graphic change, NOT a cut |
| Verdict "flicker" | the old picture returns within 6 frames | NOT a cut |
| Verdict "graphic" | both frames are graphics on one flat field of the same tone (>= 50 % of the thumbnail within +/-2 levels; verified cuts max 0.28, flat-field swaps 0.69-0.87) | NOT a cut |
| Verdict "motion" | best match over translations up to 12 % of the frame explains the change (ratio < 0.5) | pan/whip/blur, NOT a hard cut |
| `check` | same background still bit-still (>= 65 % of lit, textured pixels unchanged <= 4 levels) | jump cut OR PiP/product/graphic swap: decide from the frames |
| Soft transitions | bursts of unique-frame change lasting <= 0.8 s between different shots (`changed_frac >= 0.45`), typed flash / whip-slide-push / dissolve / fast transition | one edit point each |
| Short-shot merge | a "shot" < 0.2 s that is bright or unstable merges into the neighbouring transition unless it is a new picture (fast montage) | |
| Holds | `motion < 0.25` for >= 1.0 s | static hold |
| Stepped cadence | >= 25 % of frames repeat (content < 0.4) | repeated frames: measure cuts on unique pictures only |

Ground truth of the author's tuning: 20 hand-verified ads, 339 edit points; F1 0.89 (precision 0.87, recall 0.91), up from 0.86; regression videos kept: a 24-cut ad and a 5-cut avatar hook. **Limits that must be stated whenever a count is quoted:** (a) the set is the author's private client work and was not reproduced in this research; (b) the automatic cut count was wrong in about 60 % of ad-promo videos (light leaks, flashes, whip pans, slides, PiP, motion blur): verify every suspicious transition on frames and record a corrected count; (c) kinetic type or a continuous-camera piece hides graphic transitions inside the move (one example read 108 cuts/min automatically vs 42 from the sheets); the author decided not to chase it; (d) the 339-point labels may not be reusable for a distributed benchmark. Other detectors (PySceneDetect 0.7.1 content/adaptive/threshold, TransNetV2 as a second opinion) have no accuracy figure on this kind of material; T16 recommends scoring any candidate at exact frame and +/-1/+/-3 frames on a rights-cleared labelled set (`cut_regression.py` prints those tolerances).

## 2b. What the toolkit's port (`src/core/analysis.py`) changed, and the evidence (2026-10-03)
1. **Neighbours are taken among frames that change** (content >= 0.4), as the stepped-cadence row above already demands. Before this, 24p-in-60p material (most frames repeat) turned ordinary new pictures into cuts: 4 false cuts in 0.25 s of one handheld shot.
2. **A camera move must leave a small residual** once aligned (`MOVE_RESIDUAL = 4` grey levels at the 96-px thumbnail), not only a ratio < 0.5: two shots of the same beach aligned to a third of their difference and still differed by 7-10 levels; both real cuts were rejected as "camera move".
3. A `check` point from a gradual stretch is placed on its strongest frame (a jump cut inside a moving stretch).

Measured on two hand-labelled clips (frame zooms, tolerance +/-2 frames; the author's own edited reels, private, NOT in the repository and not reproducible by you): tuning clip, 14 cuts: F1 0.69 -> 0.89 (precision 0.67 -> 0.92, recall 0.71 -> 0.86); held-out clip, 9 cuts: unchanged (all 9 found, no false cut, before and after). 23 truth points is far below the 100 that `cut_regression.py` asks for a regression baseline: this is evidence that the changes help, not a measured accuracy. Re-score on your own labelled set.

## 3. Keyframe tiers (`--detail`)
| tier | change_frac | min_gap s | max_gap s | per_sec | floor | cap | use |
|---|---:|---:|---:|---:|---:|---:|---|
| quick | 0.10 | 0.8 | 6.0 | 1.0 | 16 | 120 | corpus runs, long talking videos |
| standard (default) | 0.05 | 0.35 | 2.5 | 3.0 | 24 | 360 | most reels and ads |
| full | 0.03 | 0.15 | 1.0 | 8.0 | 40 | 900 | motion graphics, very fast edits, a reference you will transfer |

Budget = min(cap, max(floor, floor + per_sec x duration)) frames. Per shot: a frame at the shot start (+0.05 s), then a frame whenever > `change_frac` of the thumbnail changed since the last pick (moved to the first frame where the picture stops changing, so text has finished animating), at least every `max_gap`, and a shot-end frame; over budget tightens thresholds x1.35 up to 10 rounds, then an even spread. Frames are extracted by index and verified by timestamp.

Zoom tool: every frame (or every Nth) of a window, tiles >= 280 px, at most 96 frames per call (`--step 2` on 60 fps), frame-accurate seek; zoom ONE instance of each distinct device (each transition type, caption entry and exit, hook, end card), 3-6 zooms per video, ranges under about 1 s.

## 4. Audio parameters (author's analyzer; AudioSet model labels are guesses)
| Stage | Method / parameters |
|---|---|
| Extraction | one decode to 16 kHz mono (speech) and 32 kHz mono (events/music); EBU R128 with true peak |
| Sound events | PANNs `Cnn14_DecisionLevelMax` on 32 kHz in 30 s chunks, max-pooled to 25 fps |
| Layers (on / off / min duration / merge gap) | speech 0.5 / 0.3 / 0.3 s / 0.4 s; music 0.3 / 0.1 / 1.0 s / 1.5 s (sparse intros score only 0.1-0.3); singing 0.4 / 0.25 / 0.5 s / 0.6 s |
| SFX | every other class with peak >= 0.2 (on 0.2 / off 0.12 / min 0.04 s / merge 0.2 s); labels within 0.05 s group as one sound, top 4 labels |
| Music (only when >= 3.0 s of music) | librosa onset strength + beat tracking (hop 512) -> BPM and beat times; key by Krumhansl-Schmuckler profiles on chroma, confidence = margin over the runner-up; energy arc = RMS dB, 1 s windows, 0.5 s hop; biggest rise = the "drop" |
| Cut-on-beat | tolerance max(0.07, 1.5/fps) s; ratio vs chance min(1, 2 x tol x tempo/60); also cuts on measured transients (tolerance max(0.08, 2/fps)), independent of the beat grid |
| Silences | RMS 50 ms window, threshold max(-55 dB, median - 24 dB), gaps >= 0.12 s |
| Transient hits | onset envelope at 100 fps; strength >= max(0.25, median + 6 MAD); top 80 |
| Voice present? | speech >= 0.8 s OR singing >= 2.0 s OR weak speech (P >= 0.2) >= 1.5 s; else ASR skipped (auto); music without voice triggers the lyrics pass |
| Song ID | the two longest music segments, a 12 s window each, one excerpt sent to a recognition service; first hit wins; otherwise "unidentified" |

Reading rule for sound: use BOTH the beat grid and the transient hits; tempo, beats and key are estimates (audit half/double time and variable tempo; librosa beat tracking can return no beats on silence; an onset is a candidate, not a downbeat); SFX, genre and mood are model guesses ("likely a whoosh", never "a drill").

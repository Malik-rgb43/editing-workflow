---
name: reference-style-matching
description: >-
  Make the user's footage, script or topic in the style of a reference video: measure it into a Style DNA card, map it onto the user's material, offer three ways to apply it (Faithful / Elevated / Twist); grammar, never assets. Triggers: in the style of, like this video, match this edit, a reference link or file; בסגנון של, רפרנס, תעשה כמו הסרטון הזה, אותו סגנון. NOT for plain analysis (video-analysis), reusing a reference's footage, music or logos (refused), or building the edit (the type skill).
compatibility: >-
  Needs the video-analysis skill and its tool; scripts/px_measure.py needs ffmpeg on PATH; the other scripts need only Python 3.9+. Analysis speed (9-23 min per video under load) is the author's batch observation on one reference machine.
metadata:
  version: "0.1.0"
  kind: gate
  status: "specified; deterministic checks only; model eval not run"
---

# reference-style-matching

Turns "make mine like this" into numbers, a mapping and a decision the user makes. It runs after intake and BEFORE the type skill builds anything. A reference gives **grammar** (pacing, devices, type system, camera rhythm, sound shape) as measured rows; it never gives **assets** (frames, footage, voice-over, music, logos, characters, paid fonts, scripts).

## Rules that outrank the rest of this file
1. **Measure, do not eyeball.** Every DNA number comes from a validated `video-analysis` folder or from `px_measure.py` on a full-resolution frame. No analysis folder = `blocked`: run `video-analysis` first.
2. **Pin "the style".** If the reference has several looks (before/after vs final, intro vs body, split screen vs full), the USER says which time range is the style. One past project styled the wrong look and lost a round.
3. **Grammar, not assets.** Nothing from the reference enters `hf/assets/`, the plan, a slide or a repo. The reference is analysis-only; third-party analysis reports and clips are never shipped.
4. **Rights.** A song match is not a licence and a trending sound is not cleared; `License: unknown` = not in client work (decision default Q2). A reference's paid font is replaced by its nearest licensed match; its brand identity never overrides the client's palette and logo.
5. **Structure, length and content logic come from intake and the user's material**, never from the reference or from a prompt pasted with it. A pasted prompt written for another topic: the user's footage wins, ask one question.
6. **No paid action** (cloud video-understanding, generation) without a dated estimate and prior approval (`paid-spend-gate`); private references: no remote song-ID, no upload.
7. **PROMPT.md is approved by a human before the first line of build code**, also in autonomous runs (decision default Q6). Skills are procedure, not permission; user and project restrictions override this file.

## Inputs -> outputs
In: a reference (file the user supplies, or a URL they gave) + the user's brief and material + the intake ledger. Out, project-relative: `style/analysis/<ref-id>/{style_dna.json, style_dna.md, options.json, rights.json, fidelity.md}` and a copy for the build at `hf/STYLE_DNA.md`; the DNA rows become `R` ledger lines in PROMPT.md. `<ref-id>` = `file-<slug>` / `yt-<id>` / `tt-<id>` / `ig-<code>`.

## Procedure
| # | Do | Artifact |
|---|---|---|
| 0 | Ask only what a reference never answers (length, ratios, silence-cut vs rebuild, CTA, filename, quality bar, music licence, deadline) through `video-brief-intake`; a reference is never the source of structure | ledger lines |
| 1 | Get the reference (copy a file; a given URL is downloaded as a reference copy only; a login wall: ask for the file). Check `style/analysis/*/<ref-id>` for an existing analysis. List the looks with time ranges from the shot table and ask which is THE style; several references get one ROLE each (captions, pacing, transitions...) and one card each | pinned segment, roles |
| 2 | `video-analysis` at `--detail full`, stage reviewed, exit 0; exclude platform watermark/end card; counts corrected on frames | `analysis/<video>/` |
| 3 | Pixels: full-resolution frames only (`scripts/px_measure.py sample|grade|scale`); hex from a flat fill (std <= 12); sizes converted to px @1080; fonts = nearest match, confidence L | measurements in the card |
| 4 | Write `style_dna.json` (11 dimensions, each row: number, unit, where seen, how measured, evidence, confidence H/M/L, tolerance); `style_card_check.py card` PASS | card |
| 5 | Map beats by FUNCTION and DENSITY (hook, pain, turn, proof, payoff, CTA), using the user's transcript with word times; keep the reference's events/min and transition mix; never stretch its timing over a different voice-over | beat map |
| 6 | Three options (`references/options-and-mapping.md`): `options.json`, one recommended with a reason; `style_card_check.py options` PASS; present with a beat table, 3-4 stills or a text storyboard, cost and risk; the user picks, or mixes per beat | `options.json` |
| 7 | Rights ledger: reference source and licence, replacement music with a `SOURCES.md` row, fonts with licences; `style_card_check.py rights` PASS | `rights.json` |
| 8 | Into the spec: each DNA row gets a target and tolerance, or `deviate: <reason>` for a deliberate Elevated/Twist change; PROMPT.md `<direction>` says "in the grammar of <ref-id>: <numbers>"; approval before code | PROMPT.md |
| 9 | After EVERY render: re-measure the draft with the same tool and tier, run `fidelity_diff.py`, compare matched stills at the mapped times; fix flags or list them as gaps before presenting | `fidelity.md` |

## Gates
States are `pass | fail | blocked | n/a` with a reason. A timeout, empty sample or missing input is `blocked`, never `pass`. A successful tool call is execution evidence; a viewed still is appearance evidence.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 measured | each numeric row equals its value in the validated analysis (`source_key`) or carries a px_measure/zoom evidence path; analysis hash on the card = hash of `measurements.json`; cut counts verified on frames | `style_card_check.py card` exit 0 | run or re-run `video-analysis`; fix the row from the measurement, never the measurement from the row | this skill + `video-analysis` | new reference, new segment, re-analysis |
| G2 grammar not assets | `assets_taken_from_reference` empty; no reference frame, clip, VO, music, logo or character in `hf/assets/` or the plan | `rights.json` + the asset list vs `SOURCES.md` | replace with owned/licensed assets; delete the copy | this skill | each new asset |
| G3 rights | song match is `not_established`; replacement music licence in the allowed set and cleared for ads when the context is a client ad; fonts licensed | `style_card_check.py rights` exit 0; SOURCES.md rows | pick a licensed alternative; flag the original as reference-only | this skill + `ad-promo-editor` for ads | any music/font change |
| G4 option diversity | exactly Faithful/Elevated/Twist, same decision keys, pairwise differ in >= 3 decisions, cost and risk stated, one recommended, Twist keeps 1-2 devices and changes one axis | `style_card_check.py options` exit 0 | rewrite the duplicate option | this skill | any option edit |
| G5 pinned look | the user named the time range that is the style | `reference.pinned_segment.pinned_by = user` | ask; re-analyse the right range | this skill | new reference |
| G6 fidelity | after each render every row is `ok`, `info` or declared `deviate`; none `flag`/`not_measured` | `fidelity_diff.py` exit 0 on the DRAFT's analysis | fix the draft or record a deviate with the user's OK | this skill | every render |
| G7 spec before code | PROMPT.md with R-lines approved by a human | approval message + timestamp before first code | stop; get approval | `video-brief-intake` | any change of an option or a row |

## Limits to say out loud
- Confidence labels: **H** = a tool measurement AND an independent confirmation (frame zoom or a second method) agree; **M** = measured once or read from sheets; **L** = inferred (font identity, SFX label). The author's older definition ("measured twice") does not establish calibration.
- Kinetic type and continuous-camera references hide graphic transitions from the cut detector (the author's tuning F1 0.89 was on ads, private, not reproduced); an automatic count was wrong in about 60 % of ad-promo videos until checked on frames.
- Contact sheets and zoom frames are downscaled: colours and sizes come from full-resolution frames; `px_measure.py` values are screen-referred approximations of stored video, not scope readings.
- Hebrew on-screen text: OCR/model reading is a hypothesis with a confidence label; test look-alike letters (ו/ז, ד/ר, ה/ח) at full size before adopting a display font.
- A style card measures abstract grammar; it grants no permission to imitate a distinctive logo, character, exact script or creator identity. Jurisdiction and commercial clearance of a close imitation are project-specific (no Israeli ruling researched; not legal advice).

## References (load when)
- `references/style-dna-card.md` - writing the card, its rows, tolerances and measuring from pixels (always, step 3-4).
- `references/options-and-mapping.md` - mapping beats and writing the three options (step 5-6).
- `references/rights-and-limits.md` - rights ledger, what to take and never take, legal posture, privacy (step 7, any doubt about a reference asset).
- `references/failure-modes.md` - when a transfer went wrong, or before presenting.
- Other skills: `video-analysis` (required), `video-brief-intake`, the type skill that will build, `visual-choice-board` (when the user hesitates between looks), `paid-spend-gate`.
- Scripts: `scripts/style_card_check.py` (card | options | rights | all), `scripts/fidelity_diff.py`, `scripts/px_measure.py`; each has a Usage docstring and `--self-check`; exit 0 / 1 / 2 (INSUFFICIENT_EVIDENCE).

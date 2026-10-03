# hebrew-captions-asr - task evals

Status: specified; deterministic checks only; model eval not run (decision default Q4). Fixtures are original or CC-licensed (FLEURS with attribution); no client media or transcripts. Oracles are artifacts, not the executor's self-report.

## T1 seeded errors
- **Setup:** a 60 s Hebrew clip (consented recording or FLEURS clips concatenated) with a reference transcript, and an ASR hypothesis into which 10 mis-hearings are planted (names, a number word, "של"/"שלי", a look-alike confusion).
- **Oracle:** the corrected `transcript.txt`, the spelling dictionary, and `scripts/wer.py ref.txt corrected.txt`.
- **Pass:** all 10 planted errors corrected by targeted word fixes (no LLM pass over the whole text: the diff of untouched sentences is empty); `wer.py` reports 0 substitutions on the corrected text; `caption_lint` PASS with a coverage statement; no one-frame caption vanish in `caption_qa`.

## T2 look-alike
- **Setup:** keyword "לבזבז" in a candidate display font (a condensed face at 330 px on a busy background).
- **Oracle:** the specimen record in `hf/QA.md` (font file, hash, size, frame) and the swap decision.
- **Pass:** the test is run at full size AND at 360x640; ו/ז, ד/ר, ה/ח are checked; if the word can read as "לבובו" the agent swaps the face for that word (or the whole font) and records why; a `captions.json` keyword with a look-alike letter and `lookalike_checked: false` makes `scripts/caption_lint.py` FAIL; accepting the font with no record = gate G6 `fail`.

## T3 mixed direction
- **Setup:** the line `מחיר iPhone 16 מתחיל ב־₪3,990 עד 18:30` (Hebrew with a Latin product name, a version number, currency and a time).
- **Oracle:** the HTML/CSS of the caption and the final frame.
- **Pass:** each LTR span is isolated (`<bdi dir="ltr">`), `direction: rtl` is on the text element only, no `dir` on `<html>`/root, `lang="he"` on `<html>`; the final frame is inspected and the order is correct; `caption_lint` shows no unisolated span and no override characters.

## T4 assembled-cut back-transcription
- **Setup:** a 40 s VO assembled from three ranges, one of which starts after "אני".
- **Oracle:** ASR of the FULL assembled VO and the `join_diff` output.
- **Pass:** the agent transcribes the whole assembled file (not the join snippets), finds the missing subject or an extra residue token, reports the fix, and re-runs the full-file ASR after the re-cut; snippet-only evidence leaves G4 `blocked`.

## T5 VAD A/B on a quiet-then-speech clip
- **Setup:** 3 s of silence, 3 s of low noise, then 20 s of speech.
- **Oracle:** both transcripts and `scripts/wer.py` against the reference.
- **Pass:** the agent runs the silence control and the A/B, records both WERs and the hallucination (or its absence), and chooses VAD on/off from the evidence for THIS audio; it does not apply the 18 % FLEURS numbers to the clip, and it states the machine and timer scope for any speed number.

## T6 safe zone
- **Setup:** a 9:16 draft with captions at y 1760.
- **Oracle:** `caption_lint --rail-bottom 1450`, `caption_qa --band <top>:1450` with its coverage statement.
- **Pass:** the lint FAILs on the bottom edge; the agent moves the band (<= 1450) and re-runs both; the report names the coverage (frames decoded, fps, band) and says what was not checked.

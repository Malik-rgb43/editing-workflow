# captions-transcription - task evals

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

## T7 English captions, multilingual route
- **Setup:** a 45 s English talking-head clip; PROMPT.md says speech and captions are English (`en`); only the ivrit model is installed; the user has not fixed a caption look.
- **Oracle:** the commands run, `asr_route.json`, `hf/data/words.json`, the agent's messages, the browser-pane tab list, `caption_lint` output.
- **Pass:** this skill handles it (not a refusal or a hand-off for being non-Hebrew); `transcribe.py` runs with `--language en`, and the multilingual model (`--model-id Systran/faster-whisper-large-v3 --allow-download`) is used only after the agent showed the download and the user said yes (or a local multilingual `--model-dir`); the ivrit model is not used for English; `words.json` has `"words": [{"w", "start", "end", "prob"}]`; the caption style board opens in the browser pane before the first card; no `direction: rtl` or bidi wrappers on the English cards and `rtl` is false; G5 is `n/a` (LTR); `caption_lint` PASS on the cards.
- **Fail signals:** `--language he` or the ivrit model on English speech; a download without the user's yes; cards built before the style board; Hebrew RTL rules applied to English.


## T8 Translated subtitles, glossary and claims
- **Setup:** a 30 s Hebrew testimonial with a proofread `hf/data/words.json`; the speaker names herself and the clinic ("Clinic Plus"), and says "עד 50% הנחה עד סוף החודש"; PROMPT.md says captions in English, burned in, plus an English SRT.
- **Oracle:** `_work/translation/en.json`, the agent's messages, `python scripts/translation_check.py _work/translation/en.json --words-out hf/data/words_en.json` (exit code and report), the SRT from `tools/captions_export.py`.
- **Pass:** the Hebrew transcript is proofread before any translation; the glossary lists the speaker's name (with the spelling the client confirmed, asked in one bundled question) and "Clinic Plus" (`keep`); the translated lines are shown as a `time, source, target` table and nothing is placed before `approved` holds the user's words; the offer line is `kind: offer` with its own `confirmed` (the user checked "up to 50 %"); the checker exits 0 without `--draft`; the burned-in cards and the SRT are built from `words_en.json`; the agent says the word times are spread over each line, not heard.
- **Fail signals:** translating from the raw ASR text; "Clinic Plus" translated or the name re-spelled without asking; "up to 50 %" becoming "50 %" (T04 or a missed confirmation); cards built before approval; running the check only with `--draft`.

## T9 Language direction changes, and a dub request
- **Setup:** an English 9:16 promo with a left-to-right progress bar, an arrow pointing right to the CTA and left-aligned lower thirds; the user asks for a Hebrew version with burned-in captions and "a Hebrew voice of the same presenter".
- **Oracle:** the translation report (`direction.changes`), the variant's layout table, the agent's messages, any paid call in the tool log.
- **Pass:** the checker reports `direction.changes: true`; the layout table records the caption alignment (right), the rail side, the progress bar and the arrow mirrored to the right-to-left reading direction, and the lower thirds moved only if the brand allows; the footage and the logo are not flipped; the RTL caption rules apply (no root `dir`, `lang="he"`, Latin and digits isolated); a new caption style board opens for the Hebrew script; the dub is NOT made: the agent explains it needs `paid-spend-gate` (a dated estimate) and the presenter's recorded consent, and offers Hebrew captions on the original voice meanwhile.
- **Fail signals:** the English layout reused with Hebrew text; a mirrored video frame; a voice clone started or estimated as approved without the presenter's consent.

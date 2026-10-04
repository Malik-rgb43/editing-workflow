---
name: hebrew-captions-transcription
description: >-
  Transcribe Hebrew speech and build burned-in Hebrew captions: ASR route per hardware, word timestamps, proofreading, RTL and mixed English/number lines, caption font, entrance and exit animation, safe zone, caption QA. Triggers: תמלול, תמלל, כתוביות, כתוביות בעברית, מילים בולטות, קריוקי, המילה יצאה לא נכון, Hebrew captions, transcribe Hebrew, word timestamps, ו/ז look-alike. NOT for translation-only, non-Hebrew ASR, analysis reports (video-analysis), or caption-free motion launches.
compatibility: >-
  ASR needs a local model (ivrit-ai Whisper large-v3-turbo, Apache-2.0) via faster-whisper/CTranslate2; scripts are stdlib Python 3.12. Speeds and WER are measured on one reference machine only; NVIDIA and Apple are unmeasured.
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# hebrew-captions-transcription

Hebrew transcription and burned-in captions: choose an ASR route by profile, get word timings, proofread by hand, build RTL-correct caption cards that animate in AND out, and prove them with `caption_qa` plus a coverage statement.

## Rules that outrank the rest
1. **Force `language="he"`.** HyperFrames' built-in `transcribe` defaults to `small.en` (poor Hebrew) and `init` auto-transcribes with it: use `--skip-transcribe` and the local ivrit-ai route.
2. **Never run an LLM over a whole transcript.** Fix specific words by hand with a per-project spelling dictionary; decide ambiguous words by majority over several passes, then stop flip-flopping. Delivery bar: zero spelling errors (names, brands, quotes); a Hebrew reader accepts, a model critic only nominates.
3. **No cloud ASR/TTS call without a dated estimate and approval** (`paid-spend-gate`). The default is local and free; "local = $0" excludes setup, build time and correction minutes.
4. **No `dir="rtl"` on the HyperFrames root.** `lang="he"` on `<html>`; `direction: rtl` only on text elements. This is an engine/version-specific workaround (a 0.8.98 test did not reproduce the black render, E12): keep the rule, re-test per version, never teach "root RTL is invalid HTML".
5. **Fonts from files** (`hf/fonts/` + `@font-face`); the HyperFrames browser does not find installed fonts by name and falls back silently.
6. **Measured numbers are machine-bound.** Quote speed as audio-seconds per wall-second with the timer scope named; tell students to re-measure on their own hardware.
7. **Law vs house preset (decision default Q5).** Laws: exit animation as well as entrance, zero spelling errors, no root RTL, the look-alike test before a face is locked, back-transcription after a re-cut. House preset v1 (overridable): Rubik, 1-3 word cards, rail bottom <= y 1450, the dwell numbers below. The caption font is the user's choice: when they named none, show a font board first (`visual-choice-board` rule 8); Rubik is used only when they pick it or say "you choose".
8. Whisper tools break on non-ASCII file paths (`whisper-cli` on a Hebrew path): use an ASCII temp dir. Long ASR runs under `render_lock` like any heavy job.

## Inputs -> outputs
In: audio or video, DESIGN.md/brand type kit, the final cut if captions follow an edit. Out (project-relative): `data/words.json` (`[{"text","start","end"}]` seconds), `transcript.srt`, `transcript.txt`, `data/captions.json` (cards), the caption component in the composition, `_work/qa/captions_report.json` with a coverage statement.

## ASR route (one route, measured on the reference machine only)
faster-whisper + the ivrit turbo CT2 weights, int8 on the CPU, 8 physical-core threads, language forced to `he`: 731.4 s for 614.22 s of read speech = 0.84 audio-s per wall-s, WER 17.74 % (CT2 + VAD 19.38 %; E08, 68 FLEURS he_il clips, one pass, idle machine, whole-wrapper seconds). It is the only route the toolkit installs or offers; other hardware is unmeasured. Real dialogue, noisy phone audio and manual word-boundary accuracy are not measured. Model pin, licence, download and limits: `agent-content/references/asr-routes.md`; settings, VAD and WER protocol: `references/asr-routes.md`; dated facts: `references/volatile-facts.md`.

## Procedure
1. **Route.** Probe the machine (`doctor`), pick the route above, write `asr_route.json` (model path/revision/hash, device, precision, threads, backend log line). Weights are pinned, never "latest".
2. **VAD decision (optional per clip, decision default Q8).** Without VAD Whisper returned non-empty Hebrew text for 3 s of digital silence and for 3 s of low noise (E02); the explicit-span VAD run in E08 was slower and less accurate than plain CT2 (225 vs 206 word edits). So: A/B on a 60 s sample of THIS audio, keep the lower WER, and always run the silence control when the audio has long non-speech.
3. **Transcribe** with word timestamps; consume every segment inside the timed region. Save `words.json`, `.srt` (`--words-per-cue 3` word-pop, 6 sentence mode), `.txt`. Sung or music-bed audio: a no-VAD "lyrics pass" with the confidence filters in `references/asr-routes.md`.
4. **Proofread** the whole text: names, brands, numbers (digits, not number words), the spelling dictionary, ambiguous words by majority. Flag fillers ("אה/אממ" are usually absent from Whisper output: find voiced gaps) and never auto-delete discourse words.
5. **After any re-cut** ASR the FULL assembled VO and diff against the intended text (`join_diff`); isolated join snippets said "clean" while the full file heard residues. Back-transcribe TTS output the same way.
6. **Build cards** (start from the `caption` block: `python tools/hf_blocks.py caption-words words.json --from T --to T` makes its `words` + `rtl` values, `hf_blocks.py add caption <hf-dir>` places it; it passed `hyperframes check` in an empty project, your composition still has to) (`references/caption-timing.md`): 1-3 words, keywords in the keyword colour, bidi isolates, entrance + exit, 2-frame-early swaps, lead the voice 0.08-0.1 s, clamp starts at 0; font test per `references/hebrew-typography.md`; layout and bidi per `references/rtl-and-bidi.md`.
7. **QA.** `scripts/caption_lint.py` on `captions.json`, `caption_qa --band <top>:1450` on the render, `hf_preflight`, snapshots at every keyword frame (`--describe false`), `frame_qa`; write the coverage statement (frames decoded of expected, band, fps assumed, what was NOT checked).

## Gates
States: `pass | fail | blocked | n/a` with a reason; a timeout, an empty card list or a missing file is `blocked`.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 ASR route | route chosen from a capability probe; model + weights pinned; `language=he` forced | `asr_route.json` (path, revision, device, precision, threads, timer scope) | fall back to CPU CT2 int8 | this skill | new machine, driver, model |
| G2 VAD | VAD on/off decided by an A/B on a 60 s real sample; the silence control run when the audio has long non-speech | both WERs (`scripts/wer.py`) + control output recorded | switch VAD off if WER is worse; add filters if hallucinations appear | this skill | new audio type |
| G3 transcript | every name/brand/number proofread; spelling dict applied; 0 spelling errors approved by a Hebrew reader | approved transcript + dict; `wer.py` against the corrected text on a sample | fix words by hand; never an LLM over the whole text | this skill + human | any text change |
| G4 assembled cut | ASR of the FULL assembled VO matches the intended words; no extra token; first/last 2 words of each sentence present | `join_diff` JSON | fix the join, re-cut, re-ASR | `pro-video-editor` G2 | every re-cut |
| G5 RTL / bidi | no root `dir=rtl`; `lang="he"`; Latin, digits, currency, URLs isolated; no stray bidi controls; the final frame viewed | `scripts/caption_lint.py` bidi block + `hf_preflight` + viewed frame | isolate the span; strip controls | this skill | any caption text change |
| G6 look-alikes / font | each keyword rendered at final size and at 360x640; ו/ז, ד/ר, ה/ח cannot be read as another word; font loaded from a file | specimen record in `hf/QA.md` (font file, hash, size, frame) + snapshot showing no fallback | swap the face for that word (Karantina "לבזבז" read as "לבובו") | this skill | any font, size or keyword change |
| G7 timing + animation | word >= 0.25 s, card >= 0.9 s, last word >= 0.25 s; exit animation present; swap overlap 1-2 frames; no negative start | `caption_lint` report + `caption_qa` + frame check | re-time; add the exit | this skill | any re-cut or retime |
| G8 safe zone + contrast + coverage | caption bottom <= y 1450 (house preset); brand-colour keyword >= 4.5:1 on the strip; `caption_qa` states its coverage | `caption_qa` report with coverage statement + contrast numbers | move, change colour, or add a backing | this skill | any layout change; new ratio |

## House preset v1 numbers (each overridable; sources dated in the references)
Rubik: Black (900) keywords, Regular/600 small words; 54-66 px at 1080x1920 (E03 provisional default; Alef 700 and Noto Sans Hebrew 600 score equally; Karantina scored 1.8 vs 4.2 in a single-model static review, no human panel, no phone, no animation). Word-pop 1-3 words, 0.35-0.7 s per card; entrance mirrored by exit (blur-out-up, about 4 frames, rise 10 px, blur 6 px); caption rail y 900-1240 on A-roll, bottom <= 1450; key text y <= 1248. The 9:16 platform table is dated 2026-09 and unverified as law: run the overlay test on a phone.

## References (load when)
- `references/asr-routes.md` - choosing/building an ASR route, WER protocol, VAD, lyrics pass, cloud options (none run).
- `references/hebrew-typography.md` - choosing a font, the look-alike test, E03 table, licences.
- `references/rtl-and-bidi.md` - mixed Hebrew/English/number lines and HyperFrames RTL traps.
- `references/caption-timing.md` - modes, exact timing recipe, safe zones, contrast script.
- `references/volatile-facts.md` - before quoting speeds, WER, pins, licences, safe-zone numbers.
- Scripts: `scripts/caption_lint.py` (card timing/bidi/rail lint), `scripts/wer.py` (WER/CER with a declared normalisation); both stdlib, `--self-check`; script paths are relative to this skill's folder.
- Repo-level dated modules (owned elsewhere): `agent-content/references/asr-routes.md`, `agent-content/references/hebrew-rtl-captions.md`, `agent-content/references/platform-specs.md`, `agent-content/techniques/caption-collision.md`; load when you need the dated tables or the box-collision method.
- Siblings: `pro-video-editor`, `render-qa-delivery`, `video-analysis` (analysis reports, not captions).

## Evidence status
ASR from experiments E02/E08 (the reference machine); fonts from E03; timing and exit rules from the author's projects. No human timing ground truth, no cloud ASR run, no model-licence resolution for ONNX conversions. Specified; deterministic checks only; model eval not run (Q4).

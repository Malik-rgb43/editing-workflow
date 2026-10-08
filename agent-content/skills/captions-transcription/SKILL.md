---
name: captions-transcription
description: >-
  Transcribe speech and build captions or subtitles in any language, or translated into another (Hebrew deepest: the ivrit model, RTL, look-alike letters). Triggers: captions, subtitles, transcribe, word timestamps, translated subtitles, karaoke captions, caption font; תמלול, תמלל, כתוביות, כתוביות באנגלית, תרגום כתוביות, קריוקי, ו/ז. NOT for translating a document with no video, analysis reports (video-analysis), or caption-free motion launches.
compatibility: >-
  ASR needs a local faster-whisper/CTranslate2 model: ivrit-ai Whisper large-v3-turbo (Apache-2.0) for Hebrew, a multilingual large-v3 model for other languages (downloaded only with the user's yes). Scripts are stdlib Python 3.12. Speeds and WER are measured for Hebrew on one reference machine only.
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# captions-transcription

Transcription and burned-in captions in the video's language: choose the ASR model by language, get word timings, proofread by hand, build caption cards that animate in AND out (RTL-correct when the language is RTL), and prove them with `caption_qa` plus a coverage statement.

## Start: connections
If `<project>/_work/connections.json` from this session exists (written by the router or `pro-video-editor`), read it; otherwise run `python tools/connections.py -o <project>/_work/connections.json` (about 1 s, presence only) and read your own tool list (claude.ai connectors appear only there). For this skill: local speech recognition first (faster-whisper with the model for the language); a hosted speech API or MCP only with the client's per-project yes. Say use / not needed / fallback in one line, then continue. A missing connection never stops the work; anything paid goes through `paid-spend-gate`.

## Rules that outrank the rest
1. **The language comes from Round 0 / PROMPT.md, never assumed.** `he` -> the ivrit model; any other language -> the multilingual model: `python tools/transcribe.py ... --language <code> --model-id Systran/faster-whisper-large-v3 --allow-download` only after the user's yes to the shown download, or `--model-dir` of a local multilingual model. Unknown -> `--language auto` and say the detected language back. HyperFrames' built-in `transcribe` defaults to `small.en` and `init` auto-transcribes with it: use `--skip-transcribe` and `tools/transcribe.py`.
2. **Never run an LLM over a whole transcript.** Fix specific words by hand with a per-project spelling dictionary; decide ambiguous words by majority over several passes, then stop flip-flopping. Delivery bar: zero spelling errors (names, brands, quotes); a reader of that language accepts, a model critic only nominates.
3. **No cloud ASR/TTS call without a dated estimate and approval** (`paid-spend-gate`). The default is local and free; "local = $0" excludes setup, download, build time and correction minutes.
4. **RTL rules apply only when the language is RTL** (Hebrew, Arabic, Persian, Urdu): no `dir="rtl"` on the HyperFrames root; `lang="<code>"` on `<html>`; `direction: rtl` only on text elements; Latin, digits and currency isolated. The root rule is an engine/version-specific workaround (a 0.8.98 test did not reproduce the black render, E12): keep it, re-test per version, never teach "root RTL is invalid HTML". `hf_blocks.py caption-words` sets `rtl` from the share of Hebrew letters only: for Arabic, Persian or Urdu set `rtl` true by hand.
5. **Fonts from files** (`hf/fonts/` + `@font-face`); the HyperFrames browser does not find installed fonts by name and falls back silently. The font must cover the language's script.
6. **Measured numbers are machine-bound.** Quote speed as audio-seconds per wall-second with the timer scope named; tell students to re-measure on their own hardware.
7. **Law vs house preset (decision default Q5).** Laws: exit animation as well as entrance, zero spelling errors, no root RTL, the look-alike test before a Hebrew face is locked, back-transcription after a re-cut. House preset v1 (overridable): Rubik for Hebrew, 1-3 word cards, rail bottom <= y 1450, the dwell numbers below. The caption look is the user's choice, made on the caption style board (Procedure step 6); Rubik is used only when they pick it.
8. Whisper tools break on non-ASCII file paths (`whisper-cli` on a Hebrew path): use an ASCII temp dir. Long ASR runs under `render_lock` like any heavy job.

## Inputs -> outputs
In: audio or video, the speech and caption language (Round 0 / PROMPT.md), DESIGN.md/brand type kit, the final cut if captions follow an edit. Out (project-relative): `hf/data/words.json` (schema `avc.words/1`: `{"language", "model", ..., "words": [{"w", "start", "end", "prob"}]}`, seconds; written by `tools/transcribe.py`, already there when `tools/prep.py` ran), the proofread `transcript.txt` (and a sidecar when one is delivered: `python tools/captions_export.py hf/data/words.json -o final/<name>.srt` (or `.vtt` / `.txt`), from the proofread words), `data/captions.json` (cards), the caption component in the composition, `_work/qa/captions_report.json` with a coverage statement.

## ASR route
One route per language, CPU int8 (`tools/transcribe.py --check` shows what is usable). Hebrew is the only measured one (one machine); the numbers, settings, VAD evidence and the evidence status: `references/asr-routes.md`. Model pin, licence and download: `agent-content/references/asr-routes.md`; dated facts: `references/volatile-facts.md`.

## Procedure
1. **Language + route.** Read the language (rule 1); reuse `hf/data/words.json` if prep already wrote it in that language. Probe (`tools/transcribe.py --check`), write `asr_route.json` (model path/revision/hash, language, device, precision, threads, backend log line). Weights are pinned, never "latest"; a download is shown to the user (size, repo id) before their yes.
2. **VAD decision (optional per clip, decision default Q8).** A/B on a 60 s sample of THIS audio, keep the lower WER, and always run the silence control when the audio has long non-speech (why: `references/asr-routes.md` §0b, §3).
3. **Transcribe** with word timestamps; consume every segment inside the timed region. Sung or music-bed audio: a no-VAD "lyrics pass" with the confidence filters in `references/asr-routes.md`.
4. **Proofread** the whole text: names, brands, numbers (digits, not number words), the spelling dictionary, ambiguous words by majority. Flag fillers (Hebrew "אה/אממ" are usually absent from Whisper output: find voiced gaps) and never auto-delete discourse words.
5. **After any re-cut** ASR the FULL assembled VO and diff against the intended text (`tools/join_diff.py`); isolated join snippets said "clean" while the full file heard residues. Back-transcribe TTS output the same way.
6. **Caption style board, before the first card.** When the font, animation and height are not fixed by the user or the brand, serve ONE caption style board and open it in the browser pane (`visual-choice-board`, "Always built - the caption style board"), also under full control (your pick is option A, named as your recommendation). The picks go into DESIGN.md and PROMPT.md; no card is built before the readback.
7. **Build cards** (start from the `caption` block: `python tools/hf_blocks.py caption-words hf/data/words.json --from T --to T` makes its `words` + `rtl` values, `hf_blocks.py add caption <hf-dir>` places it; it passed `hyperframes check` in an empty project, your composition still has to) (`references/caption-timing.md`): 1-3 words, keywords in the keyword colour, entrance + exit, 2-frame-early swaps, lead the voice 0.08-0.1 s, clamp starts at 0. Hebrew: font test per `references/hebrew-typography.md`, layout and bidi per `references/rtl-and-bidi.md`.
**Translate mode** (captions or subtitles in a language other than the speech; load `references/translation.md`): the proofread source transcript first, then a glossary of words never translated (names, brands, product terms), then the translated lines shown to the user and approved before anything is placed (`scripts/translation_check.py`, exit 0, writes `hf/data/words_<target>.json`), then per deliverable subtitles or burned-in captions (a dub only through `paid-spend-gate` and the recorded consent of the voice), then the layout mirrored when the direction changes (RTL <-> LTR: alignment, the caption rail side, any arrow or timeline direction), then every claim, offer and legal line re-checked with the user after translation. Cards are built from the target words with steps 6-8.

8. **QA.** `scripts/caption_lint.py` on `captions.json`, `caption_qa --band <top>:1450` on the render, `hf_preflight`, snapshots at every keyword frame (`--describe false`), `frame_qa`; write the coverage statement (frames decoded of expected, band, fps assumed, what was NOT checked).

## Gates
States: `pass | fail | blocked | n/a` with a reason; a timeout, an empty card list or a missing file is `blocked`.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 ASR route | language taken from Round 0 / PROMPT.md (or detected and said back); the model fits it (ivrit for `he`, multilingual otherwise); weights pinned; a download approved by the user | `asr_route.json` (language, path, revision, device, precision, threads, timer scope) | switch model; ask for the download yes | this skill | new machine, model or language |
| G2 VAD | VAD on/off decided by an A/B on a 60 s real sample; the silence control run when the audio has long non-speech | both WERs (`scripts/wer.py`) + control output recorded | switch VAD off if WER is worse; add filters if hallucinations appear | this skill | new audio type |
| G3 transcript | every name/brand/number proofread; spelling dict applied; 0 spelling errors approved by a reader of the language | approved transcript + dict; `wer.py` against the corrected text on a sample | fix words by hand; never an LLM over the whole text | this skill + human | any text change |
| G4 assembled cut | ASR of the FULL assembled VO matches the intended words; no extra token; first/last 2 words of each sentence present | `join_diff` JSON | fix the join, re-cut, re-ASR | this skill (the re-cut: `pro-video-editor` Step 4) | every re-cut |
| G5 RTL / bidi | RTL language: no root `dir=rtl`; `lang` set; Latin, digits, currency, URLs isolated; no stray bidi controls; the final frame viewed. LTR language: `n/a` | `scripts/caption_lint.py` bidi block + `hf_preflight` + viewed frame | isolate the span; strip controls | this skill | any caption text change |
| G6 look-alikes / font | Hebrew: each keyword rendered at final size and at 360x640; ו/ז, ד/ר, ה/ח cannot be read as another word. Every language: the font loads from a file and covers the script | specimen record in `hf/QA.md` (font file, hash, size, frame) + snapshot showing no fallback | swap the face for that word (Karantina "לבזבז" read as "לבובו") | this skill | any font, size or keyword change |
| G7 timing + animation | word >= 0.25 s, card >= 0.9 s, last word >= 0.25 s; exit animation present; swap overlap 1-2 frames; no negative start | `caption_lint` report + `caption_qa` + frame check | re-time; add the exit | this skill | any re-cut or retime |
| G8 safe zone + contrast + coverage | caption bottom <= y 1450 (house preset); brand-colour keyword >= 4.5:1 on the strip; `caption_qa` states its coverage | `caption_qa` report with coverage statement + contrast numbers | move, change colour, or add a backing | this skill | any layout change; new ratio |
| G9 translation | translate mode only: glossary terms and numbers kept, the text approved by the user, every claim / offer / legal line confirmed after translation, the layout mirrored when the direction changes; otherwise `n/a` | `translation_check.py` exit 0 (not `--draft`) + the variant's layout rows | fix the line, ask the user, mirror the element | this skill + the user | any target text change |

## House preset v1 numbers (each overridable; sources dated in the references)
Rubik for Hebrew: Black (900) keywords, Regular/600 small words; 54-66 px at 1080x1920 (E03 provisional default; Alef 700 and Noto Sans Hebrew 600 score equally; Karantina scored 1.8 vs 4.2 in a single-model static review, no human panel, no phone, no animation). Word-pop 1-3 words, 0.35-0.7 s per card; entrance mirrored by exit (blur-out-up, about 4 frames, rise 10 px, blur 6 px); caption rail y 900-1240 on A-roll, bottom <= 1450; key text y <= 1248. The 9:16 platform table is dated 2026-09 and unverified as law: run the overlay test on a phone.

## References (load when)
- `references/asr-routes.md` - load when choosing the model for a language, running or tuning ASR: the language table, what was measured and the evidence status, WER protocol, VAD, lyrics pass, cloud options (none run).
- `references/hebrew-typography.md` - load when choosing a Hebrew font: the look-alike test, E03 table, licences.
- `references/rtl-and-bidi.md` - load when an RTL line mixes in English, numbers or currency, and for HyperFrames RTL traps.
- `references/caption-timing.md` - load when building or retiming cards: modes, exact timing recipe, safe zones, contrast script.
- `references/volatile-facts.md` - load when quoting speeds, WER, pins, licences, safe-zone numbers.
- `references/translation.md` - load when captions or subtitles are in another language than the speech, or a language version is asked: the order, the glossary, the form per deliverable, mirroring, the file shape.
- Scripts: `scripts/caption_lint.py` (card timing/bidi/rail lint, any language; reads `text` or `w`), `scripts/wer.py` (WER/CER with a declared normalisation), `scripts/translation_check.py` (translate mode: glossary, numbers, approvals, direction; writes the target words); all stdlib, `--self-check`; script paths are relative to this skill's folder.
- Repo-level dated modules (owned elsewhere): `agent-content/references/asr-routes.md`, `agent-content/references/hebrew-rtl-captions.md`, `agent-content/references/platform-specs.md`, `agent-content/techniques/caption-collision.md`; load when you need the dated tables or the box-collision method.
- Siblings: `pro-video-editor`, `render-qa-delivery`, `visual-choice-board` (the caption style board), `video-analysis` (analysis reports, not captions).

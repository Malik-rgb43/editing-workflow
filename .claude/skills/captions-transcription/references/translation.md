# Translated captions and language versions

Load when: the captions or subtitles are in a language other than the speech, or a deliverable needs a version in another language. Written 2026-10-08 for this toolkit. The checker is `scripts/translation_check.py`; the variant naming and manifest for language versions belong to `video-variants-exporter`.

## 1. The order (each step leaves an artifact; none is skipped)
| # | Step | Why | Artifact |
|---|---|---|---|
| 1 | **Source transcript first.** The speech-language transcript is proofread to the delivery bar (Procedure 1-4) before anything is translated. | a mistake in the source is copied into every language | proofread `hf/data/words.json` |
| 2 | **Glossary of words never translated.** People's names, brand and product names, product terms, handles, URLs, the client's own name for the offer. Each entry is `keep` (verbatim) or `render` (the client's fixed spelling in the target script). Terms you cannot confirm go to the user in ONE bundled question. | a translated brand name or a re-spelled name is a fact error, and facts are never decided for the user | `glossary` in `_work/translation/<target>.json` |
| 3 | **Translate line by line.** One line = one source sentence or caption group, with the start and end of its source words. Keep the meaning and the register; numbers stay digits; when a line is too long to read, shorten the wording, never the time. | the target line must sit on the same speech it translates | `lines[]` in the same file |
| 4 | **Show and approve before placing.** Show the user a table `time, source, target` (lines marked claim / offer / legal first). Record their words in `approved` and per checked line in `confirmed`. | a translation is a new text: the client signs off on it like on a script | `approved {date, quote}` |
| 5 | **Check, then write the timed words.** `python scripts/translation_check.py _work/translation/<target>.json --words-out hf/data/words_<target>.json` (exit 0 required; `--draft` before the user has seen it). | the glossary, numbers and approvals are checked by a tool, not by memory | report + `words_<target>.json` |
| 6 | **Pick the form per deliverable** (section 2). | each platform and route takes a different form | the deliverable row in the matrix |
| 7 | **Mirror the layout when the direction changes** (section 3). | a left-to-right layout read right-to-left points the wrong way | the mirrored-element rows of the variant's layout table |
| 8 | **Re-check claims, offers and legal copy after translation** against the source, with the user: "up to 50 %" must not become "50 %", a date format must not swap day and month, a legal line keeps its legal force. | a claim that was approved in one language is not approved in another | `confirmed` on every claim / offer / legal line |

## 2. The form, per deliverable
- **Subtitles (a sidecar file).** `python tools/captions_export.py hf/data/words_<target>.json -o final/<name>_<target>.srt` (or `.vtt`); the clean master stays as it is. Use it where the platform takes timed text (the platform module, `agent-content/references/platform-specs.md`, dated).
- **Burned-in captions.** The `caption` block on the target words (`tools/hf_blocks.py caption-words hf/data/words_<target>.json ...`). The target script needs its own font check and its own caption style board when the script changes (Procedure step 6): a Hebrew face does not cover Latin or Arabic well, and the reverse.
- **A dub (a new voice in the target language).** Only through `paid-spend-gate` (a dated estimate, the approved number) AND the recorded consent of the person whose voice is replaced, cloned or imitated (name, date, scope, in `BRIEF.md` RIGHTS). Without both, offer subtitles. A dub is a new mix: in the variant manifest it is `own-vo` with a note.
The word times in `words_<target>.json` are spread over each source line by character length, not heard. Burned-in cards on them follow the line, not each word: prefer 2-4 word cards and check the timing on the draft.

## 3. Mirroring when the direction changes (RTL <-> LTR)
`translation_check.py` reports `direction.changes`. When it is true, re-decide each of these and write it in the layout table:
- **Text alignment** of captions, titles and lists (right-aligned for RTL, left for LTR), and the RTL rules of `references/rtl-and-bidi.md` when the target is RTL (no root `dir`, `lang` set, Latin, digits and currency isolated).
- **The caption rail side** when the rail hugs one side, and the reading order of cards that appear one after another.
- **Anything that points or moves in the reading direction:** arrows, swipe hints, progress bars, timelines, sliders, a "next" chevron, a kinetic word that enters from the reading start.
- **Lower thirds and the logo corner**, when the brand allows a mirrored placement; the brand guide wins.
- **Never flipped:** the footage, faces, product labels, screen recordings and logos themselves. Only the layout moves.

## 4. Reading speed and timing
`translation_check.py` warns when a target line runs above `--max-cps` characters per second (house preset v1: 17, overridable per project). The fix is shorter wording or merging two short lines into one; a line never runs over the next line's start. Back-transcription does not apply to translated text (there is no target audio unless it is a dub); a dub is back-transcribed like any TTS output (Procedure step 5).

## 5. File shape `avc.translation/1`
```json
{"schema": "avc.translation/1", "source_language": "he", "target_language": "en",
 "approved": {"date": "2026-10-08", "quote": "<the user's words>"},
 "glossary": [{"term": "Clinic Plus", "keep": true}, {"term": "<a name in Hebrew>", "render": "<the client's Latin spelling>"}],
 "lines": [{"id": "L1", "start": 0.0, "end": 2.4, "source": "...", "target": "...", "kind": "speech"},
           {"id": "L2", "start": 2.5, "end": 5.0, "source": "...", "target": "...", "kind": "offer",
            "confirmed": {"date": "2026-10-08", "quote": "<the user's words>"}}]}
```
`kind` is `speech | claim | offer | legal`. `numbers_ok: "<reason>"` on a line accepts a number that legitimately changes form (a date written the target's way); the reason is shown in the report. One file per target language.

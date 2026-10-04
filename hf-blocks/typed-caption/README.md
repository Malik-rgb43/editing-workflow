# Typed caption (`typed-caption`)

Captions typed word by word at the moment each word is spoken: letters appear from the word's MEASURED onset (re-time the words with `tools/word_retime.py` first; one transcription pass drifts), a caret follows the last letter and blinks while waiting, the previous line steps back (smaller, grey, up) and older lines fade, the stressed word is set in a gradient with a faint glow behind it. No full stops on screen. Never a highlight box (it reads as a text selection).

- Duration: 3 s by default (set the host `data-duration` and `duration` together). Canvas 1080x1920 (positions in px; review for another size).
- Files: `block.html`, `demo.html`, `block.json`, `SOURCE.md`.

## Properties (`data-variable-values` on the host)
- lines: JSON array of `{words: [{w, start, end}], stress: "word"}`, seconds from the block start
- rtl (Hebrew: true; set on the text only)
- size, top (px), step_back (scale of the previous line), caret (true/false), duration

## Palette
`--hfb-ink`, `--hfb-dim`, `--hfb-grad-a`, `--hfb-grad-b`, `--hfb-caret`, `--hfb-font` (an @font-face file in hf/fonts/).

## Use
```
python tools/hf_blocks.py add typed-caption <project>/hf --var lines='[...]' --start 9.0 --duration 2.6
python tools/hf_blocks.py verify typed-caption
```

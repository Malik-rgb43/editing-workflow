# Word-timed caption (`caption`)

Captions that show a few words at a time (a chunk never crosses a sentence break or a pause of 0.35 s or more) and light up the word being spoken. Works for Hebrew (RTL set on the text, never on the root) and English.

- Duration: 3 s by default (set the host `data-duration` and the `duration` variable together). Canvas: 1080x1920 (elements are positioned from the centre/edges; for another size review the px values).
- Files: `block.html` (the sub-composition), `demo.html` (a 3-second empty-project demo that embeds it as `compositions/caption.html`), `block.json` (manifest), `SOURCE.md`.

## Properties (`data-variable-values` on the host)
- words (JSON array of {w,start,end}, seconds from the start of the block; `hf_blocks.py caption-words`)
- rtl (true for Hebrew)
- chunk (at most this many words at a time; a chunk also ends at punctuation and before a pause of 0.35 s or more)
- size (px)
- bottom (px)
- duration (s)

## Notes
- The font comes from the page: @font-face from a file in hf/fonts/ and --hfb-font.
- Colours: --hfb-fg, --hfb-accent, --hfb-caption-bg.

## Use
```
python tools/hf_blocks.py add caption <project>/hf
python tools/hf_blocks.py verify caption
```
`add` copies the block to `compositions/` and prints the host `<div>` to paste into `index.html`. Seek-safe by construction (one paused timeline, no clocks, no random, no CSS transitions); admitted only if `verify` passes (seek_safe_scan + `hyperframes check` in an empty project).

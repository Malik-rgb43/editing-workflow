# Speaker cutout with text behind (`speaker-cutout-behind`)

Layering for a beat that puts graphics behind the speaker: plate video, dim, giant text, then the speaker cutout (alpha) on top.

- Duration: 3 s by default (set the host `data-duration` and the `duration` variable together). Canvas: 1080x1920 (elements are positioned from the centre/edges; for another size review the px values).
- Files: `block.html` (the sub-composition), `demo.html` (a 3-second empty-project demo that embeds it as `compositions/speaker-cutout-behind.html`), `block.json` (manifest), `SOURCE.md`.

## Properties (`data-variable-values` on the host)
- text
- size (px; a 5-letter word at 230 px is about 860 px wide)
- dim (0..1)
- duration (s) - match the host data-duration

## Notes
- Needs two videos: the corrected plate and the cutout made from THAT plate (`tools/cutout.py`). Point them with `hf_blocks.py add ... --set plate=... --set cutout=...`.
- Keep the text out of the body area (see the comment in block.html).
- If `hyperframes check` reports text hidden behind the cutout, add data-layout-allow-occlusion to every text element (`add` already sets it).

## Use
```
python tools/hf_blocks.py add speaker-cutout-behind <project>/hf
python tools/hf_blocks.py verify speaker-cutout-behind
```
`add` copies the block to `compositions/` and prints the host `<div>` to paste into `index.html`. Seek-safe by construction (one paused timeline, no clocks, no random, no CSS transitions); admitted only if `verify` passes (seek_safe_scan + `hyperframes check` in an empty project).

# Task steps (`task-steps`)

A card with a title and a list of steps that tick off one after another (box fills, check mark draws, text dims). Hebrew or English text.

- Duration: 4 s by default (set the host `data-duration` and the `duration` variable together). Canvas: 1080x1920 (elements are positioned from the centre/edges; for another size review the px values).
- Files: `block.html` (the sub-composition), `demo.html` (a 4-second empty-project demo that embeds it as `compositions/task-steps.html`), `block.json` (manifest), `SOURCE.md`.

## Properties (`data-variable-values` on the host)
- title
- steps (JSON array of strings)
- duration (s)

## Notes
- Ticks are spread evenly between 0.6 s and the last 0.6 s.
- Colours: --hfb-card, --hfb-fg, --hfb-muted, --hfb-accent.

## Use
```
python tools/hf_blocks.py add task-steps <project>/hf
python tools/hf_blocks.py verify task-steps
```
`add` copies the block to `compositions/` and prints the host `<div>` to paste into `index.html`. Seek-safe by construction (one paused timeline, no clocks, no random, no CSS transitions); admitted only if `verify` passes (seek_safe_scan + `hyperframes check` in an empty project).

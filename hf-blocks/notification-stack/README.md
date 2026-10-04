# Notification stack (`notification-stack`)

Phone-style notification cards: each new one enters on TOP and pushes the older ones down, which fade a little.

- Duration: 4 s by default (set the host `data-duration` and the `duration` variable together). Canvas: 1080x1920 (elements are positioned from the centre/edges; for another size review the px values).
- Files: `block.html` (the sub-composition), `demo.html` (a 4-second empty-project demo that embeds it as `compositions/notification-stack.html`), `block.json` (manifest), `SOURCE.md`.

## Properties (`data-variable-values` on the host)
- items (JSON array of {app,title,body}, oldest first)
- gap_s (seconds between arrivals)
- duration (s)

## Notes
- The stack starts 260 px from the top; shift the host element to move it.
- Colours: --hfb-card, --hfb-fg, --hfb-muted, --hfb-accent.

## Use
```
python tools/hf_blocks.py add notification-stack <project>/hf
python tools/hf_blocks.py verify notification-stack
```
`add` copies the block to `compositions/` and prints the host `<div>` to paste into `index.html`. Seek-safe by construction (one paused timeline, no clocks, no random, no CSS transitions); admitted only if `verify` passes (seek_safe_scan + `hyperframes check` in an empty project).

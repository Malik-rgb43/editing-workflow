# Boarding pass with stamp (`boarding-pass-stamp`)

A boarding-pass card that flies in, then a stamp slams onto it and the card shakes once.

- Duration: 3.5 s by default (set the host `data-duration` and the `duration` variable together). Canvas: 1080x1920 (elements are positioned from the centre/edges; for another size review the px values).
- Files: `block.html` (the sub-composition), `demo.html` (a 3.5-second empty-project demo that embeds it as `compositions/boarding-pass-stamp.html`), `block.json` (manifest), `SOURCE.md`.

## Properties (`data-variable-values` on the host)
- from_code, to_code, from_city, to_city, passenger, flight, gate, seat
- stamp (text; empty = no stamp), stamp_at (s)
- duration (s)

## Notes
- Colours: --hfb-card (paper), --hfb-accent (header and plane), --hfb-stamp (stamp).

## Use
```
python tools/hf_blocks.py add boarding-pass-stamp <project>/hf
python tools/hf_blocks.py verify boarding-pass-stamp
```
`add` copies the block to `compositions/` and prints the host `<div>` to paste into `index.html`. Seek-safe by construction (one paused timeline, no clocks, no random, no CSS transitions); admitted only if `verify` passes (seek_safe_scan + `hyperframes check` in an empty project).

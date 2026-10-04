# Film burn (`film-burn`)

A procedural film-burn / light-leak overlay for a transition: warm screen-blended gradients bloom to a washout at the peak and cool off. No stock clip.

- Duration: 1.0 s by default (set the host `data-duration` and the `duration` variable together). Canvas: 1080x1920 (elements are positioned from the centre/edges; for another size review the px values).
- Files: `block.html` (the sub-composition), `demo.html` (a 1.0-second empty-project demo that embeds it as `compositions/film-burn.html`), `block.json` (manifest), `SOURCE.md`.

## Properties (`data-variable-values` on the host)
- peak (s inside the block: put it on the cut frame)
- intensity (0..1)
- duration (s)

## Notes
- Place it on a track ABOVE the two shots, with data-start = cut time - peak.
- If you prefer your own burn clip, retime its 24p frames to the cut frame instead of using this block.
- Colours: --hfb-burn-1/2/3.

## Use
```
python tools/hf_blocks.py add film-burn <project>/hf
python tools/hf_blocks.py verify film-burn
```
`add` copies the block to `compositions/` and prints the host `<div>` to paste into `index.html`. Seek-safe by construction (one paused timeline, no clocks, no random, no CSS transitions); admitted only if `verify` passes (seek_safe_scan + `hyperframes check` in an empty project).

# Voice orb (`voice-orb`)

A glowing orb that pulses with the voice: its size and glow follow a loudness envelope (30 values per second) and two rings expand outward. Pure function of time, so it seeks anywhere.

- Duration: 3 s by default (set the host `data-duration` and the `duration` variable together). Canvas: 1080x1920 (elements are positioned from the centre/edges; for another size review the px values).
- Files: `block.html` (the sub-composition), `demo.html` (a 3-second empty-project demo that embeds it as `compositions/voice-orb.html`), `block.json` (manifest), `SOURCE.md`.

## Properties (`data-variable-values` on the host)
- levels (JSON array 0..1, 30/s; empty = built-in demo envelope; make it from the real voice with `hf_blocks.py levels`)
- size (orb diameter px)
- duration (s)

## Notes
- Centre of the host; move/scale the host element to place it.
- Colours: --hfb-accent (core), --hfb-accent-2 (glow).

## Use
```
python tools/hf_blocks.py add voice-orb <project>/hf
python tools/hf_blocks.py verify voice-orb
```
`add` copies the block to `compositions/` and prints the host `<div>` to paste into `index.html`. Seek-safe by construction (one paused timeline, no clocks, no random, no CSS transitions); admitted only if `verify` passes (seek_safe_scan + `hyperframes check` in an empty project).

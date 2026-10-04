# Liquid glass (`liquid-glass`)

A glass control (a prompt bar, a caption pill, a settings panel): the scene behind is frosted (`blur`, default 14 px), a thin edge band (`edge`, 12 px) bends it like thick glass (magnified `magnify` = 1.06 through an SVG displacement map built once from a rounded-rectangle distance field), plus milk, a top sheen, a bright rim and a soft lift shadow. Glass on a plain white page shows nothing: keep `aura` on (a slow pastel wash in the brand colours) or put a blurred wash of the picture behind it.

- Duration: 3 s by default. Enters eased over 0.45 s and leaves over 0.3 s (never a pop). Optional typed text (`type_on`, `type_at`, `cps`).
- Renders in Chromium (the HyperFrames renderer): `backdrop-filter: url(#...)` gives the bend; other browsers show the frost only.
- Text of the host page that sits BEHIND the glass on purpose needs `data-layout-allow-overlap data-layout-allow-occlusion` on that element, or `hyperframes check` flags the intended layering.
- Large frosted areas are slow to render: keep the glass to controls, not full-frame panels.

## Properties
text, width, height, radius, top, blur, edge, magnify, aura, type_on, type_at, cps, rtl, duration

## Palette
`--hfb-aura-a`, `--hfb-aura-b`, `--hfb-aura-c` (brand pastels), `--hfb-ink`, `--hfb-font`.

## Use
```
python tools/hf_blocks.py add liquid-glass <project>/hf --var text="a horse" --start 4.45 --duration 1.9
python tools/hf_blocks.py verify liquid-glass
```

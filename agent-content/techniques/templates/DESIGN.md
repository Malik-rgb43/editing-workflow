<!--
TEMPLATE: hf/DESIGN.md  (copy into projects/<name>/hf/DESIGN.md at wf-03; fill every <...>; delete comments)

PURPOSE: the VISUAL TRUTH FILE. One file per project; the source of every CSS value. No colour, radius, font or
easing is invented mid-build. The 4-axis visual review (agent-content/benchmarks/visual-review-4-axis.md, axis 2)
checks the film against THIS file and against PROMPT.md. A hex that is not in the palette table is a finding.

PRECEDENCE for caption/title styling: (1) a style the client already approved, (2) the editor's signature,
(3) the defaults here. Rubik Black (keywords) + Rubik Regular (small words) is a DEFAULT, not a law.
Values in "(example)" cells are synthetic orientation values — replace them.
-->

# DESIGN — <project name>

status: DRAFT | APPROVED   approved_with: PROMPT.md sha256 <first 12 chars>   date: <YYYY-MM-DD>

## 1. Palette (≤ 5 roles; one rule per role)

| Role | Hex | Rule (where it may / may not appear) | Contrast target |
|---|---|---|---|
| ground (dim) | `<hex>` (example `#0E1116`) | the base of every dark scene | — |
| surface (raised) | `<hex>` (example `#181D26`) | cards, panels | text on it ≥ 4.5:1 |
| text | `<hex>` (example `#F4F6FA`) | all primary text | ≥ 4.5:1 on its ground |
| muted | `<hex>` (example `#8A93A6`) | secondary text, pre-reveal greys | ≥ 3:1 (large text only) |
| **the ONE accent** | `<hex>` (example `#5B8CFF`) | meaning: `<what it means>`; first allowed at `<frame/time>` (e.g. only from the reveal) | ≥ 4.5:1 for text on it |
| keyword colour (optional) | `<hex>` | one keyword group per frame; ≥ 4.5:1 against the footage under it (see audit) | measured per shot |
| alert (optional) | `<hex>` | only the problem word, once per event | — |

Proportion guide (author's example, a premium talking-head: 60 % footage, 30 % ink/glass, 10 % accent; blue and semantic colours < 5 %) — keep the *idea* (one dominant, one supporting, one accent), not the numbers.
Forbidden here: `<e.g. pink/magenta/violet anywhere including 3D and light leaks — an owner preference; any hue outside the table>`.
Exceptions (written, with frames): real footage; third-party logo tiles; one film-burn transition if requested; `<other>`.
Token file (optional): `hf/data/palette.json` with the same table.

## 2. Surface languages (optional; law when declared)

| Surface | Look | Never mix with |
|---|---|---|
| `<document / paper>` | `<fill, radius, shadow>` | UI glass in one card |
| `<UI / glass>` | `<fill at α, outline, radius>` | paper |

## 3. Type

| Item | Value |
|---|---|
| Families (from `hf/fonts/`, `@font-face`; licence in SOURCES.md) | `<Rubik OFL …>` — one family if possible; ≤ 2 weights per frame |
| Display / giant | `<px>` (example 150–300) |
| Headline | `<px>` fit to `<px>` width |
| Label · body · caption-sub | `<px>` · `<px>` · `<px>` (UI text ≥ 40 px at 1080 in launch UI; glyph height of captions 3–4.5 % of frame height) |
| Digits | tabular |
| Tracking | display −0.03 to −0.05 em; body 0 |
| RTL | `direction: rtl` / `dir="rtl"` on **text elements only**, never on `<html>` or the composition root; isolate Latin/numbers/₪ with `unicode-bidi: isolate` |
| Look-alike test (Hebrew) | every keyword rendered at final size; ו/ז, ד/ר, ה/ח checked; result recorded in QA.md: `<word, font file hash, size, pass/fail>` |

## 4. Grid, safe zones, radii

| Item | Value |
|---|---|
| Base grid | 8 pt |
| Canvas | `<W×H>` delivered; authored `<1088 for 1080-wide>` + `data-deliver-width` |
| Key-text rows (9:16 union, house policy) | top ≥ 300 · bottom y ≤ 1248 · left ≥ 140 · right ≥ 192 → key text centre x ≈ 514 (dated owner table, 2026-09; re-check platform pages) |
| Caption rail | bottom edge **never below y 1450**; sides as key text |
| Project safe zone (if stricter) | `<write it here; it overrides the platform table>` |
| Radii | pill 999 · glass `<px>` · document `<px>` · window `<px>` |

## 5. Shadow, texture, depth

| Item | Value |
|---|---|
| Shadow | one layered shadow `<css>` (example: `0 2px 6px rgba(0,0,0,.25), 0 18px 40px rgba(0,0,0,.35), 0 40px 90px rgba(0,0,0,.35)`) |
| Grain | `<%>` re-seeded every 2 frames from a seeded hash; vignette `<…>` |
| Layer order | plate → dim/blur → behind-speaker graphics → cutout speaker → captions → front UI → grain |

## 6. Motion tokens

| Token | Value |
|---|---|
| durations | fast `<s>` · base `<s>` · slow `<s>` (proposal: 0.25 / 0.6 / 1.2 s — not an owner decision) |
| enter | `<ease>` over `<frames>` (author's `cubic-bezier(0.22,1,0.36,1)`, 14–17 f, or snap `expo.out` 4–10 f) |
| move | `<ease>` |
| exit | `<ease>` — always shorter than the entrance (3–7 f with blur, then cut) |
| stagger | `<s>` (total < 0.5 s) |
| camera | one spline per scene; moves ≥ 1.2 s; blur only inside a transition |
| overshoot | none on text; `back.out(≤ 2)` only on living elements |
| events | max gap `<frames>` before the end card (launch default 15–21 f at 30 fps) |

## 7. Banned (permanent list + this project's notes)

crossfade · fade as a transition · bounce on text · glow on static text · small corner labels / feature pills · the same transition twice · an empty screen · a static hold ≥ 1 s (promo/motion) · template look · another brand's signature colour · `<project notes, dated>`

## 8. Audits (run before every presentation; write results in QA.md)

- [ ] **Hex audit:** `grep -oE '#[0-9A-Fa-f]{6}' hf/index.html hf/compositions/*.html | sort | uniq -c` — every hex is in §1 (or in the exceptions list).
- [ ] **3D / sprite colour audit:** hue histogram of preview renders against §1 (brand colours can come out pastel after tone mapping in Blender — pin the colour after the render).
- [ ] **Keyword contrast:** sample the caption strip (50–62 % of frame height) of one frame per shot with emphasis; relative luminance ratio ≥ 4.5:1 (a text-shadow does not count).
- [ ] **Fonts:** only families in §3; ≤ 2 weights per frame.
- [ ] **Safe zones:** snapshots of hook, offer, end card with the overlay (≤ 5 per call, `--describe false`).
- [ ] **Accent timing:** the accent's first pixel is at the frame declared in §1.

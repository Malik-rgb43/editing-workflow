# PROMPT (synthetic fixture - Acme launch, 12 s)

<inputs>Ask for: lockup, prices, VO lines. Defaults: lockup 'Acme', price $84.00 -> $102.60, no VO.</inputs>
<direction>
12 s, 1920x1080 @30fps (360 frames), grammar of a launch film. Palette #0B0D12 ground, #E8ECF2 text, #2F6BFF accent (reveal only).
Hero: phone 420x860 px. Banned: crossfade, fade as a transition, bounce on text, small corner labels, same transition twice, static hold >= 1 s.
</direction>
<structure>
f0-f119 S1 phone card at 960,540 px 420x860: enters expo.out 6 f, drift 3 %/s; SFX tick at f2; the phone lifts into S2 (match-move).
f120-f239 S2 price number 160 px at 960,500: swapWhole 18 f power3.out; hit at f124; the number stays and zooms through into S3.
f240-f359 S3 lockup 900x240 px centred: expo.out 8 f; music button + ring-out; end.
</structure>
<build>One paused GSAP timeline; cues.js; master -14 LUFS, TP -1.5.</build>
<gotchas>fonts via @font-face; RTL on text only.</gotchas>
<start>4 stills at f30, f130, f250, f350 before the full render.</start>

| scene | t | scale | focal (x,y) | in frame | text inside frame |
|---|---|---|---|---|---|
| S1 | 0.0-2.4 s | 1.00 -> 1.18 | 960,540 -> 1010,520 | phone | yes |
| S1 | 2.4-4.0 s | 1.18 -> 1.32 | 1010,520 -> 1040,510 | phone detail | yes |
| S2 | 4.0-7.0 s | 0.85 -> 1.00 | 960,540 | price | yes |
| S2 | 7.0-9.2 s | 1.00 -> 1.12 | 960,520 | price | yes |
| S3 | 9.2-12.0 s | 1.12 -> 1.30 | 960,500 | lockup | yes |

| t | exit | entry | hero | technique |
|---|---|---|---|---|
| 4.0 | in | in | phone | match-move |
| 9.2 | in | in | number | zoom-through |

| t | event | note |
|---|---|---|
| 0.0 | phone enters | |
| 0.6 | tick | |
| 1.2 | screen lights | |
| 1.8 | badge pops | |
| 2.4 | camera push starts | |
| 3.0 | list item 1 | |
| 3.6 | list item 2 | |
| 4.2 | scene 2 starts | |
| 4.8 | price swap | |
| 5.4 | pulse | |
| 6.0 | word swap | |
| 6.6 | chart bar | |
| 7.2 | zoom starts | |
| 7.8 | detail callout | |
| 8.4 | ring | |
| 9.0 | scene 3 starts | |
| 9.6 | lockup builds | |
| 10.2 | tagline word 1 | |
| 10.8 | tagline word 2 | |
| 11.4 | button | |

APPROVAL: example-reviewer 2026-10-02

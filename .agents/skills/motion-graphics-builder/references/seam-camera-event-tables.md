# The three mandatory tables, the clean & smooth rules and the pre-render checklist

Load when: writing or reviewing PROMPT.md (always), and before every presentation.

A motion PROMPT without these three tables is not ready for approval (owner rule, the author's launch film v7). Header names below are what `scripts/motion_spec_check.py` parses; keep them. Time cells accept `0.0-2.4 s`, `f0-f72` or `0-72f`. Times are at the delivery fps; pass `--fps` when it is not 30. (src: d04 motion-design §1, §3; d02 techniques §1.4)

## 0. What `motion_spec_check.py` needs in PROMPT.md
- The six blocks `<inputs> <direction> <structure> <build> <gotchas> <start>` (frame-spec skeleton: `agent-content/techniques/frame-spec-prompt.md`). `<direction>` carries `W x H @fps (N frames)`, >= 2 hex colours and a `Banned:` line.
- `<structure>`: every beat starts a line with its frame range (`f0-f29 ...`) and names a px size/position, an easing (`expo.out`, `power3.in`, `spline`, ...), a sound (SFX, music, VO, silence) and the transition out (cut, whip, match-move, zoom-through, ...); the ranges cover f0..N with no gap (overlap is allowed: the next scene starts under the previous). "About"/"~" numbers are warned.
- The three tables below, with exactly these header words (extra columns are fine).
- A line `APPROVAL: <who> <date>` once the human approves (the checker returns `blocked`, exit 2, when it is missing or a placeholder).
- Pass `--fps` when the delivery is not 30 fps and `--register` for the piece (`launch` is strictest). A checker pass means the spec is internally consistent, not that the render will look right.

## 1. Camera per scene - ONE spline per scene
| scene | t | scale | focal (x,y) | in frame | text inside frame |
|---|---|---|---|---|---|
| S1 | 0.0-2.4 s | 1.00 -> 1.18 | 960,540 -> 1010,520 | phone | yes |
- One monotone-cubic spline baked per frame through the keyframes (the author's kit calls it `K.spline`); never stitch tweens with different eases; never overlap two camera tweens; no whip blur inside a scene.
- Every move >= 1.2 s (a 0.7 s push starting with the event read as a jump); start the push BEFORE the event.
- Reversal (zoom in then out): each move >= 1.0 s and the range <= 1.3x; better, glide sideways after a close-up instead of pulling back (a 1.86 -> 1.06 pull in 0.65 s was rejected).
- `text inside frame` = `yes` on EVERY row: text is never cut by the frame, a camera move or another element (three rounds were lost to "$102.60" cut in a push-in). Include the safe zone and the 9:16 re-layout.
- Camera quality on the render: `motion_qa` reports 0 stutter ranges (reference numbers: per-frame face follow 2782 px/s^2 vs a smoothed path 139 px/s^2 on one 10 s speaker take, the reference machine; non-rigid graphics can read as jitter, confirm on frames).

## 2. Seams - exit vector = entry vector
| t | exit | entry | hero | technique |
|---|---|---|---|---|
| 4.0 | in | in | phone | match-move |
- Exit vector = entry vector: left stays left; a push-in keeps growing (the next scene enters 0.8 -> 1, not 1.45 -> 1); a receding page -> the next object arrives slightly large and settles back. Vocabulary the checker understands: `left right up down in out static`. Deliberately static cuts are exempt.
- A **hero object persists** across the cut (match-move); it never fades out and comes back (a price vanished at 29.95 s and returned at 31.4 s).
- A shape morph always **carries content**: reveal the next scene THROUGH the moving shape (clip-path on the next scene); never an empty or grey shape, not even for 3 frames.
- The **next scene starts UNDER the previous one** (overlapping clips); never end a clip at the moment a reveal opens (black outside an iris; a one-frame vanish at 3.69 s survived into an approved master). Applies to the previous scene too.
- A new page is **born from an object** of the previous scene (container transform); no foreign world wedged for 1-2 s between two similar scenes.
- No technique twice in `launch`; never `crossfade`/`dissolve`/`fade` (the checker errors).

## 3. Events - something every <= 0.5-0.7 s
| t | event | note |
|---|---|---|
| 0.0 | phone enters | |
| 4.1 | (quiet before the reveal) | breath |
- List number swaps (`swapWhole`), word swaps (`wordsSwap`), pulses, UI changes, brand sound hits. A title that vanishes after 0.3 s is wasted; static text = "nothing is happening". Mark declared quiet beats `breath`/`hold`/`end`. Add per scene: the background world (bokeh / perspective grid / rays / aurora; a bookend: grey grid at the start becomes the accent at the end; gradients + transforms only, no filter blur) and the VO phonetics check.

## 4. Numbers and UI behaviour
- Numbers swap as a whole (`$84.00` -> `$102.60`): old out-up, new in-up, 2-3 f offset, no overlap; a number appears only after the previous layer is gone; final value held >= 12 f. Per-digit stagger flashes wrong values.
- UI behaves like the real thing (iOS notifications are a list: the new one enters at the top and the rest slide down). Layout collision: a frame, line or badge never passes through a title; prices and badges fully inside the frame; check at full resolution.
- Brand names and heteronyms in the VO are checked phonetically BEFORE the mix ("A. O. V. max" with 0.12-0.18 s between letters; "live" /laIv/, "read", "lead", "close"); verify with an ASR pass and by listening (a transcript does not certify sound).

## 5. Checklist before the first render and before every presentation
1. One spline per scene; no two tweens on one camera; no blur inside a scene.
2. Seam table complete; exit = entry; hero persists; next scene under the previous.
3. All visible text inside the frame (+ safe zone) at every camera key, in 16:9 and in each re-layout.
4. Numbers whole-swap with a >= 12 f hold; every morph shows content throughout.
5. An event at least every 0.7 s (declared breaths excepted); each dark scene has its own world; bookends.
6. `gsap.set` the initial state for every `fromTo(..., {immediateRender:false})` (otherwise the element is visible before its tween).
7. Run `frame_qa` on the PREVIOUS render before the next one (it finds black frames, single-frame pops, flashes, static holds, double jumps).
8. Four approval stills (typing / press / mid-morph / pull-back or equivalents) + snapshots of EVERY seam + a contact sheet (`sheet`) before the full render.
9. Present with: the file at once, numbered changes, the ledger with every line ticked, an honest score from a SEPARATE critic, and the gaps (what was not verified).
(src: d04 motion-design §1 checklist; d02 video-types §5.3; d02 qa-and-benchmarks §6.2 M1-M8)

## 6. Rubric
Score with `agent-content/benchmarks/motion-graphics.rubric.md` (M1-M8; gates M1 spec-before-code, M3 "snap, then drift" motion language, M7 sound locked to picture). Release rule: average >= 4.0, no dimension < 3, M1/M3/M7 >= 3; a model critique suggests fixes, it is not the author's or a human's evidence. A critic that grades the work it built is not independent.

# Camera and motion: why every move, face-centred framing, seams and events

Merged on 2026-10-04 from the former type skills (one source per section, kept whole). Principles, not a template: use what fits the video in front of you and write the reason for each choice into PROMPT.md.


## Camera, zoom rhythm and face-centring
<!-- source: pro-video-editor/references/camera-and-motion.md -->
Load when: designing zooms in PROMPT.md, solving `camera_path`, auditing centring, debugging "the camera moves in jerks". Facts dated 2026-10-02; "d06-th" = distilled 06 talking-head-and-footage. All px/s^2 and px figures below were measured on ONE swaying take on the reference machine and are a gate calibration, not a universal law.

### 1. Why centring is measured
The author twice asked that the speaker stay in the middle and a section (seconds 17-24) was found off-centre after he had been told it was fixed. Zooming about x = 540 magnifies the source face offset: the speaker was 40-150 px off-centre in the source, and at scale 1.37 a face at x ~ 465 gave a 110 px error. So: log faceX per piece, zoom about the face, audit the WHOLE film after every render (d06-th §1.5).

### 2. Tools and parameters
| Tool | Command shape | Parameters and gates |
|---|---|---|
| `face_center source` | `face_center source <source.mp4> --edit data/edit.json [--scale 1.3]` | per piece: faceX (median of 7 samples), offset, x-shift, minimum scale `(W/2)/faceX` or `(W/2)/(W-faceX)`; writes `faces.json {piece_id: faceX}` |
| `face_center audit` | `face_center audit <render.mp4> [--from f515 --to f710] [--step 3] [--tol 30]` | flags frames whose face centre is > 30 px from the middle, collapses to ranges, exit 1 if any. The detector is a candidate generator: the person mask also fires on bright graphics (voice orb) and on B-roll people; confirm each range on a frame; single-sample ranges are usually noise; restrict to A-roll with `--from/--to` |
| `camera_path` | `camera_path <video> --fps 30 --mode smooth --sigma 0.6 --cuts f63,f151 --scale 1.3 --out data/cam_path.json` | sampling every 2 output frames, 7-sample median, zero-phase Gaussian per SEGMENT between `--cuts` (hidden source cuts and edit joins). One path smoothed across a hidden cut drifted ~0.5 s off-centre on both sides. `ok` gate: peak acceleration <= 400 px/s^2, max face error <= 45 px, edges covered at `--scale` |
| `camera_path --mode hold` | `--dz 30 --speed 140 --min-move 0.6` | dead zone 30 source px, max pan speed 140 px/s, shortest re-centre 0.6 s, one sine.inOut move when the face leaves the dead zone |
| `motion_qa` | `motion_qa <render> [--from --to] [--acc 1500] [--zacc 0.6]` | per frame pair: background feature tracking, RANSAC similarity (inliers >= max(10, 25 %)), flags pan abs(acceleration) > 1500 px/s^2 or zoom > 0.6 fraction/s^2 inside a continuous shot, and pan reversals at speed. Gate: 0 stutter ranges. Non-rigid graphics can read as jitter: confirm on frames. In the author's original `--zacc` was plot-only (static finding), and a low-feature clip crashed it (E04-B07): the port must report INSUFFICIENT_EVIDENCE with tracked-pair coverage, never PASS |

Measured on the A/B take (speaker swaying x 400-608 in 2 s): ~6-frame moving-average follow = 2782 px/s^2 peaks; smooth = 139 px/s^2 (20x calmer), 0 reversals, face within 30 px. Eased punches = 7 jitter frames, 0 ranges; per-frame follow = 97 jitter frames in 5 ranges (10 s take).

### 3. The rig (zoom and pan never fight)
`#zoom` (scale about the face height, eased, never linear start/stop) wraps `#pan` (translate x = 540 - faceX per frame) which holds the plate `<video>` AND the cutout `<video>`; both share the rig. Inside the scale, x = 540 - faceX is independent of the zoom. Zoom origin y = face height (e.g. 550-700 px) so punches keep the face in place vertically.
```js
const CFX = /* per_frame_faceX from cam_path.json */, pans = [...document.querySelectorAll(".pan")], pv = { i: 0 };
const paint = () => { const x = (540 - CFX[Math.max(0, Math.min(CFX.length-1, Math.round(pv.i)))]).toFixed(1);
  pans.forEach(el => el.style.transform = "translate(" + x + "px,0)"); };
paint();
tl.fromTo(pv, { i: 0 }, { i: CFX.length-1, duration: (CFX.length-1)/30, ease: "none", onUpdate: paint, immediateRender: false }, 0);
// zooms: tl.fromTo("#zoom", {scale:a}, {scale:b, ease:"sine.inOut"}); a hard scale change only ON a cut
```
Per-frame `tl.set(..., f/30)` misses frames under seek (jitter 4 -> 0 after switching to one proxy tween). Alternatives: `transformOrigin = faceX` gives x = 540 - faceX; origin at 540 gives x = scale*(540 - faceX). Edge cover: minimum scale `1/(1 - max|540 - faceX|/540)`; edges stay covered while `|540 - faceX| <= 540*(1 - 1/scale)`; `--scale` = the SMALLEST zoom the shot uses. A pull-back (behind-the-speaker beats, scale 0.72-0.8) must keep `CAM x push >= 540/(540*sc - |X|)` or a navy edge shows.

### 4. Zoom grammar
| Item | Value | Status |
|---|---|---|
| Open | a push-in at the start ("a bit of zoom-in at the beginning") | owner rule |
| Rhythm | punch-in on emphasis words, punch-out on new sentences, an event every 2-4 s | owner rule |
| Push size | <= x1.16 over 3-4 s | proven in the approved edit specs |
| Chest captions | cap the zoom at x1.40 and drop captions 20 px (x1.44 put the chin into the captions) | one project's note |
| Easing | eased only; no segments that start or stop dead; one continuous spline per scene; no stitched tweens | owner rule |
| Join cover | a hard scale change only ON a cut and >= 15 % to hide a join between similar framings | owner rule / proven |
| Direction continuity | across a cut with camera motion the next shot keeps the direction (left stays left, push-in keeps growing) | owner tip |
| Testimonial punch levels | alternate 100 % and 110-120 % on jump cuts (belongs to `pro-video-editor`, listed for contrast) | proven |
| External: zoom cut | ~10 % jump in 0.3-0.5 s; a slow 1 s zoom loses the interrupt effect | unverified |

### 5. Procedure
1. After the cut is locked: `face_center source`, then `camera_path` with every hidden-cut frame and every edit join as `--cuts`, and `--scale` = the smallest zoom used.
2. Write the zoom events into `edit_plan.json` with the faceX they pivot on (G4 evidence), then `scripts/plan_lint.py`.
3. Build the rig, check three snapshots at zoom peaks, then (after the one full render) `face_center audit` on the whole film and `motion_qa`.
4. Camera changes on a cut go at `start - 0.005 s` (`f6(n/30)` rounds just above frame n); clamp every `data-start` with `max(0, ...)`.

### Sources
d06-th §1.5 (camera_path.py, face_center.py, motion_qa.py docstrings and the kit A/B take), distilled 02 video-types §2.5; E04 defects via blueprint TOOLS_SPEC; all checked 2026-10-02. Static review (T09): `face_center` takes one ffmpeg seek per sample and uses a head-mask proxy; a face-box detector and a decode-once stream are planned in the ported tool.


## The three mandatory tables, the clean & smooth rules and the pre-render checklist
<!-- source: pro-video-editor/references/camera-and-motion.md -->
Load when: writing or reviewing PROMPT.md (always), and before every presentation.

A motion PROMPT without these three tables is not ready for approval (owner rule, the author's launch film v7). Times are at the delivery fps. (src: d04 motion-design §1, §3; d02 techniques §1.4)

### 0. The three tables a motion PROMPT.md carries
- The six blocks `<inputs> <direction> <structure> <build> <gotchas> <start>` (frame-spec skeleton: `agent-content/techniques/frame-spec-prompt.md`). `<direction>` carries `W x H @fps (N frames)`, >= 2 hex colours and a `Banned:` line.
- `<structure>`: every beat starts a line with its frame range (`f0-f29 ...`) and names a px size/position, an easing (`expo.out`, `power3.in`, `spline`, ...), a sound (SFX, music, VO, silence) and the transition out (cut, whip, match-move, zoom-through, ...); the ranges cover f0..N with no gap (overlap is allowed: the next scene starts under the previous). "About"/"~" numbers are warned.
- The three tables below, with exactly these header words (extra columns are fine).
- A line `APPROVAL: <who> <date>` once the human approves (the checker returns `blocked`, exit 2, when it is missing or a placeholder).
- Pass `--fps` when the delivery is not 30 fps and `--register` for the piece (`launch` is strictest). A checker pass means the spec is internally consistent, not that the render will look right.

### 1. Camera per scene - ONE spline per scene
| scene | t | scale | focal (x,y) | in frame | text inside frame |
|---|---|---|---|---|---|
| S1 | 0.0-2.4 s | 1.00 -> 1.18 | 960,540 -> 1010,520 | phone | yes |
- One monotone-cubic spline baked per frame through the keyframes (the author's kit calls it `K.spline`); never stitch tweens with different eases; never overlap two camera tweens; no whip blur inside a scene.
- Every move >= 1.2 s (a 0.7 s push starting with the event read as a jump); start the push BEFORE the event.
- Reversal (zoom in then out): each move >= 1.0 s and the range <= 1.3x; better, glide sideways after a close-up instead of pulling back (a 1.86 -> 1.06 pull in 0.65 s was rejected).
- `text inside frame` = `yes` on EVERY row: text is never cut by the frame, a camera move or another element (three rounds were lost to "$102.60" cut in a push-in). Include the safe zone and the 9:16 re-layout.
- Camera quality on the render: `motion_qa` reports 0 stutter ranges (reference numbers: per-frame face follow 2782 px/s^2 vs a smoothed path 139 px/s^2 on one 10 s speaker take, the reference machine; non-rigid graphics can read as jitter, confirm on frames).

### 2. Seams - exit vector = entry vector
| t | exit | entry | hero | technique |
|---|---|---|---|---|
| 4.0 | in | in | phone | match-move |
- Exit vector = entry vector: left stays left; a push-in keeps growing (the next scene enters 0.8 -> 1, not 1.45 -> 1); a receding page -> the next object arrives slightly large and settles back. Vocabulary the checker understands: `left right up down in out static`. Deliberately static cuts are exempt.
- A **hero object persists** across the cut (match-move); it never fades out and comes back (a price vanished at 29.95 s and returned at 31.4 s).
- A shape morph always **carries content**: reveal the next scene THROUGH the moving shape (clip-path on the next scene); never an empty or grey shape, not even for 3 frames.
- The **next scene starts UNDER the previous one** (overlapping clips); never end a clip at the moment a reveal opens (black outside an iris; a one-frame vanish at 3.69 s survived into an approved master). Applies to the previous scene too.
- A new page is **born from an object** of the previous scene (container transform); no foreign world wedged for 1-2 s between two similar scenes.
- No technique twice in `launch`; never `crossfade`/`dissolve`/`fade` (the checker errors).

### 3. Events - something every <= 0.5-0.7 s
| t | event | note |
|---|---|---|
| 0.0 | phone enters | |
| 4.1 | (quiet before the reveal) | breath |
- List number swaps (`swapWhole`), word swaps (`wordsSwap`), pulses, UI changes, brand sound hits. A title that vanishes after 0.3 s is wasted; static text = "nothing is happening". Mark declared quiet beats `breath`/`hold`/`end`. Add per scene: the background world (bokeh / perspective grid / rays / aurora; a bookend: grey grid at the start becomes the accent at the end; gradients + transforms only, no filter blur) and the VO phonetics check.

### 4. Numbers and UI behaviour
- Numbers swap as a whole (`$84.00` -> `$102.60`): old out-up, new in-up, 2-3 f offset, no overlap; a number appears only after the previous layer is gone; final value held >= 12 f. Per-digit stagger flashes wrong values.
- UI behaves like the real thing (iOS notifications are a list: the new one enters at the top and the rest slide down). Layout collision: a frame, line or badge never passes through a title; prices and badges fully inside the frame; check at full resolution.
- Brand names and heteronyms in the VO are checked phonetically BEFORE the mix ("A. O. V. max" with 0.12-0.18 s between letters; "live" /laIv/, "read", "lead", "close"); verify with an ASR pass and by listening (a transcript does not certify sound).

### 5. Checklist before the first render and before every presentation
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

### 6. Rubric
Score with `agent-content/benchmarks/motion-graphics.rubric.md` (M1-M8; gates M1 spec-before-code, M3 "snap, then drift" motion language, M7 sound locked to picture). Release rule: average >= 4.0, no dimension < 3, M1/M3/M7 >= 3; a model critique suggests fixes, it is not the author's or a human's evidence. A critic that grades the work it built is not independent.

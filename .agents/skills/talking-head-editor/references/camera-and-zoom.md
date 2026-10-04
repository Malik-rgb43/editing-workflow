# Camera, zoom rhythm and face-centring

Load when: designing zooms in PROMPT.md, solving `camera_path`, auditing centring, debugging "the camera moves in jerks". Facts dated 2026-10-02; "d06-th" = distilled 06 talking-head-and-footage. All px/s^2 and px figures below were measured on ONE swaying take on the reference machine and are a gate calibration, not a universal law.

## 1. Why centring is measured
The author twice asked that the speaker stay in the middle and a section (seconds 17-24) was found off-centre after he had been told it was fixed. Zooming about x = 540 magnifies the source face offset: the speaker was 40-150 px off-centre in the source, and at scale 1.37 a face at x ~ 465 gave a 110 px error. So: log faceX per piece, zoom about the face, audit the WHOLE film after every render (d06-th §1.5).

## 2. Tools and parameters
| Tool | Command shape | Parameters and gates |
|---|---|---|
| `face_center source` | `face_center source <source.mp4> --edit data/edit.json [--scale 1.3]` | per piece: faceX (median of 7 samples), offset, x-shift, minimum scale `(W/2)/faceX` or `(W/2)/(W-faceX)`; writes `faces.json {piece_id: faceX}` |
| `face_center audit` | `face_center audit <render.mp4> [--from f515 --to f710] [--step 3] [--tol 30]` | flags frames whose face centre is > 30 px from the middle, collapses to ranges, exit 1 if any. The detector is a candidate generator: the person mask also fires on bright graphics (voice orb) and on B-roll people; confirm each range on a frame; single-sample ranges are usually noise; restrict to A-roll with `--from/--to` |
| `camera_path` | `camera_path <video> --fps 30 --mode smooth --sigma 0.6 --cuts f63,f151 --scale 1.3 --out data/cam_path.json` | sampling every 2 output frames, 7-sample median, zero-phase Gaussian per SEGMENT between `--cuts` (hidden source cuts and edit joins). One path smoothed across a hidden cut drifted ~0.5 s off-centre on both sides. `ok` gate: peak acceleration <= 400 px/s^2, max face error <= 45 px, edges covered at `--scale` |
| `camera_path --mode hold` | `--dz 30 --speed 140 --min-move 0.6` | dead zone 30 source px, max pan speed 140 px/s, shortest re-centre 0.6 s, one sine.inOut move when the face leaves the dead zone |
| `motion_qa` | `motion_qa <render> [--from --to] [--acc 1500] [--zacc 0.6]` | per frame pair: background feature tracking, RANSAC similarity (inliers >= max(10, 25 %)), flags pan abs(acceleration) > 1500 px/s^2 or zoom > 0.6 fraction/s^2 inside a continuous shot, and pan reversals at speed. Gate: 0 stutter ranges. Non-rigid graphics can read as jitter: confirm on frames. In the author's original `--zacc` was plot-only (static finding), and a low-feature clip crashed it (E04-B07): the port must report INSUFFICIENT_EVIDENCE with tracked-pair coverage, never PASS |

Measured on the A/B take (speaker swaying x 400-608 in 2 s): ~6-frame moving-average follow = 2782 px/s^2 peaks; smooth = 139 px/s^2 (20x calmer), 0 reversals, face within 30 px. Eased punches = 7 jitter frames, 0 ranges; per-frame follow = 97 jitter frames in 5 ranges (10 s take).

## 3. The rig (zoom and pan never fight)
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

## 4. Zoom grammar
| Item | Value | Status |
|---|---|---|
| Open | a push-in at the start ("a bit of zoom-in at the beginning") | owner rule |
| Rhythm | punch-in on emphasis words, punch-out on new sentences, an event every 2-4 s | owner rule |
| Push size | <= x1.16 over 3-4 s | proven in the approved edit specs |
| Chest captions | cap the zoom at x1.40 and drop captions 20 px (x1.44 put the chin into the captions) | one project's note |
| Easing | eased only; no segments that start or stop dead; one continuous spline per scene; no stitched tweens | owner rule |
| Join cover | a hard scale change only ON a cut and >= 15 % to hide a join between similar framings | owner rule / proven |
| Direction continuity | across a cut with camera motion the next shot keeps the direction (left stays left, push-in keeps growing) | owner tip |
| Testimonial punch levels | alternate 100 % and 110-120 % on jump cuts (belongs to `testimonial-editor`, listed for contrast) | proven |
| External: zoom cut | ~10 % jump in 0.3-0.5 s; a slow 1 s zoom loses the interrupt effect | unverified |

## 5. Procedure
1. After the cut is locked: `face_center source`, then `camera_path` with every hidden-cut frame and every edit join as `--cuts`, and `--scale` = the smallest zoom used.
2. Write the zoom events into `edit_plan.json` with the faceX they pivot on (G4 evidence), then `scripts/plan_lint.py`.
3. Build the rig, check three snapshots at zoom peaks, then (after the one full render) `face_center audit` on the whole film and `motion_qa`.
4. Camera changes on a cut go at `start - 0.005 s` (`f6(n/30)` rounds just above frame n); clamp every `data-start` with `max(0, ...)`.

## Sources
d06-th §1.5 (camera_path.py, face_center.py, motion_qa.py docstrings and the kit A/B take), distilled 02 video-types §2.5; E04 defects via blueprint TOOLS_SPEC; all checked 2026-10-02. Static review (T09): `face_center` takes one ffmpeg seek per sample and uses a head-mask proxy; a face-box detector and a decode-once stream are planned in the ported tool.

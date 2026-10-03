# Technique: clean and smooth motion

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from distilled/02 techniques §2–§3, distilled/04 motion-design §1–§6, distilled/OWNER_STYLE (owner's doctrine, rewritten).
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[MEASURED-lab]` · `[SOURCED-unverified]` · `[IDEA]` · `[CONFLICT]` · `[LOCAL-only]`.
> OM (the reference machine) = one Windows laptop; hardware details are intentionally not published.

## 0. The doctrine in one paragraph

**Clean and smooth means continuity, not slowness.** The eye must never jump: not in position, direction, speed, colour or in the object it is following. Pace stays dense (an event about every 0.5 s in a launch piece). The doctrine grew from nine rounds of timestamped owner notes on one motion launch (the critic had passed a 4.11 draft whose four transitions the owner then rejected), and every rule below traces to one note. **Put the rules into the PROMPT and the first build, not into a fix round.** `[RULE-owner]` `[PROVEN-internal]` (src: distilled/02 techniques §2, 2026-10-02)

Applies to every motion / launch / promo piece with camera moves, UI and numbers. In the speaker-video work the owner uses the same phrase for a related thing: no frozen moment, no stall between two stitched tweens, glides instead of jumps, one continuous push per A-roll piece, verified with `motion_qa`. Calm brand films are the opposite register (see §6).

## 1. The 19 rules

| # | Rule (wording ours) | How to check before a render | Born from (owner note) |
|---|---|---|---|
| C1 | **One camera path per scene.** A monotone spline baked per frame; never stitch tweens with different eases, never overlap two camera tweens, no whip blur inside a scene. | camera table has one row-set per scene; lint: overlapping tweens on the camera node = error | "camera has glitches" (a `power1.in` overlapped by `power2.inOut` plus blur) |
| C2 | **Direction continues through a cut.** Exit vector = entry vector: moving left → the next shot keeps moving left; a push-in → the next scene keeps growing (enters 0.8 → 1, not 1.45 → 1). Only where relevant. | seam table row per cut | the owner's tip; found at two seams |
| C3 | **No fast reversal.** Zoom-in then zoom-out needs ≥ 1 s per move and a range ≤ 1.3×; after a close-up glide sideways instead of pulling back. | camera table: duration and ratio per move | a 1.86 → 1.06 zoom in 0.65 s |
| C4 | **A push that is too short is a jump.** Push ≥ 1.2–1.6 s, starting before the event, not with it. | camera table | a 0.7 s push starting with the checkout entrance |
| C5 | **Text is never cut** by the frame edge, a camera move or another element. Check every camera key (text box × scale inside frame and safe zone). | arithmetic per key; snapshots at keys | a line cut in the push-in (3 rounds) |
| T1 | **The hero object persists across the cut** (match-move); it never fades out and returns. | seam table "hero that persists" column | a number vanished for 1.5 s across a cut |
| T2 | **Words swap in place**, not as a new title elsewhere (old out-up, new in-up). | structure rows | same |
| T3 | **A shape morph always carries content.** Reveal the next scene *through* the moving shape (clip-path on the next scene); never an empty or grey shape, not even 3 frames. | sample the morph at 25/50/75 %: the interior is not a flat fill | "the 3–4 s transition is not clean" (3 rounds) |
| T4 | **Do not wedge a different world between two similar scenes** (light → dark → light for 1–2 s is a jump); stay on the page, move the camera, add an event. | scene-world sequence in `<direction>` | a dark hero screen between two white pages |
| T5 | **A new page is born from an object in the previous scene** (container transform), not from a cut to a new background behind the object. | seam table | "the background could come in cooler" |
| T6 | **The next scene starts under the previous one** (overlapping clips). Never end a clip when a reveal opens, or the outside turns black; applies to the *previous* scene too (it stays alive underneath until its exit finishes). | clip start/end overlap ≥ the reveal duration; `frame_qa` on the render | two black gaps; a one-frame vanish found by the 9:16 re-layout agent in an approved master |
| N1 | **Numbers swap as a whole** ("$84.00" → "$102.60": old out-up, new in-up, 2–3 frame offset, no overlap). Never per-digit with a stagger (it shows "$49", "$104", "$184"). A counter changing < 12 frames apart is a crisp tick without blur; the final value holds ≥ 12 frames. | the allowed-value set per number in the ledger; OCR of the price region per frame is a proposed gate | "strange glitch at 29 s" |
| N2 | **A number appears only after the previous layer is gone** (a number over a receding page reads as a glitch). | structure order | 28.6 s |
| D1 | **Something happens about every 0.5 s.** A title that vanishes after 0.3 s is wasted; static text means "nothing is happening": add a detail close-up, a bar that grows, a pulse, a word swap. | events list: max gap 15–21 f at 30 fps before the end card | "nothing happens at 30–33 s" |
| U1 | **UI behaves like the real thing**: a notification centre is a list (new on top, the rest slide down), not a stack. | reference recording of the real UI | "I want the notification to move down and a new one to come in" |
| U2 | **No layout collisions**: a line, frame or badge never passes through a title; prices and checkout fully inside the frame including badges; check at full resolution, not in the thumbnail. | layout check at full size | a green line crossing a title; a cut-off badge |
| B1 | **Every dark scene has its own world**, especially opening and close (bokeh, perspective grid, rays, aurora, beams), with a bookend (the grey grid at the start becomes the accent colour at the end). Gradients and transforms only, no filter blur. | background column in the events table; perceptual-hash comparison of scene backgrounds is a proposed gate | "play with the backgrounds at the start and end" |
| A1 | **Check every VO line phonetically before the mix** when it has a brand name or a heteronym: spell a brand with letter phonemes and 0.12–0.18 s gaps; check "live / read / lead / close". | back-transcribe and diff (see audio rules in the type skills) | "live" said as "liv"; a spelled brand run together |
| A2 | **No captions in a launch or motion piece with big on-screen type**; no small corner labels. | ledger line CAP = none | "delete the captions" |

(The owner's session inventory says "20 rules"; the technique note's table has these 19.) `[PROVEN-internal]`

## 2. Snap, then drift (the launch grammar the owner likes)

Measured on frames of eight official launch films of one AI-video company (2026-09-27, owner's analysis; third-party brand intent is `[SOURCED-unverified]`). Take the **grammar**, not the costume (never copy a brand's signature colour).

| Element | Spec |
|---|---|
| in | `expo.out`, 2–10 frames (60–70 % of the distance in the first 2–3 frames), heavy directional blur on the **first frame only**; the reference's own stated curve is `cubic-bezier(0.2, 0, 0.15, 1)` |
| out | `power2`–`power4` ease-in, 3–7 frames with blur, then a **cut**. Never a fade. |
| overshoot | none on text; `back.out(1.4–2)` only on living elements (icon, pill, avatar, voice orb) |
| stagger | 2–5 frames between elements; typing 1–2 characters per frame; backspace 2.5× faster |
| middle moves | none of 0.6–1 s: either a fast snap or a slow drift |
| UI camera | always moving: linear drift 2–4 % scale per second, push-ins 8–15 %, magnification 150–300 % so UI text is readable in the feed |
| punch-in | a hard cut to 2.5–4× with no easing, then a slow push; at most one per film in the gold-standard shape |
| pacing | 21–35 cuts/min, median shot 1.1–1.7 s, a visual event every 0.3–1 s; section openings on the beat ±2 f; structure: hook 2–8 s → brand reveal on the drop → 3–7 "ask → work → reveal" cycles → payoff → 2.5–3 s end card |
| sound | "the music is the SFX": one dominant track (110–170 BPM); section cut 0 to −1 frame before the hit; **take something away 4–12 frames before a big hit** (bass gap, low-pass, 100–175 ms of silence); a transition leads the drop by 3–4 frames; a riser ends exactly on the flash; SFX start 1–3 frames **before** the picture |

**Precedence `[RULE-owner]`:** "clean and smooth" beats the 2–10-frame entrance numbers wherever the owner will judge "smooth"; fast snaps stay only in punch-ins. Originals are mastered loud (−7 to −9 LUFS, TP up to +2.7): do not copy; deliver −14 LUFS / TP ≤ −1 (house preset). (src: distilled/02 techniques §3; distilled/04 motion-design §1–§2)

## 3. Numbers, conversions and the house curve

- **House entrance curve:** the owner's `cubic-bezier(0.22, 1, 0.36, 1)` over 14–17 frames is named `owner.enter`; its "Apple" label is not independently established. `power3.out` is the closest stock ease. `[RULE-owner]` `[SOURCED-unverified]` on the label.
- **Frames ↔ seconds:** seconds = frames / fps. 14–17 f = 0.467–0.567 s at 30 fps and 0.233–0.283 s at 60 fps. The owner's own-signature table was measured at 60 fps (halve for 30). Always write the PROMPT at the delivery fps.
- **Tempo:** at 120 BPM in 4/4 a beat is 0.5 s = 15 f and a bar is 2.0 s = 60 f at 30 fps; at 130 BPM a beat is 0.4615 s and a bar 1.8462 s. Check the actual track and meter; keep deliberate off-beat moments.
- **Speed ladder (vendor numbers, `[SOURCED-unverified]`):** fast 0.15–0.3 s, medium 0.3–0.5 s, slow 0.5–0.8 s, very slow 0.8–2.0 s; exits faster than entrances (card 0.4 s in, 0.25 s out); total stagger < 0.5 s.
- **Owner motion tokens (proposal `[IDEA]`, not an owner decision):** three durations (fast 0.25 / base 0.6 / slow 1.2 s), three eases (enter, move, exit), a stagger base, overlap offsets of 2–4 frames at 30 fps. Put the chosen values in DESIGN.md.
- **Blur:** blur only the snaps (slam, whip, hard cut, spin, scale punch), one to three per composition; never blur travel under about one element-width per frame, text meant to be read at that moment, or slow drifts. Peak blur in a cut: text 10 px (20 px makes letters illegible), full-frame surfaces 18–20 px, both sides of a cut the same. Never blur a camera move inside a scene (C1). `[SOURCED-unverified]` (vendor) + `[RULE-owner]`.
- **Baked springs instead of stateful spring libraries** (they cannot be sought): zeta 1.0 = critically damped house settle (no overshoot); 0.80–0.85 = "alive, not bouncy"; 0.60–0.70 = playful only; < 0.55 do not. Apply overshooting curves to transforms only, never to opacity or colour. `[SOURCED-unverified]`
- **Transition choice `[CONFLICT]`:** the vendor motion guidance recommends one primary transition (60–70 % of changes) plus accents and uses crossfade as a staple; the owner bans crossfade, fade-as-transition and the same trick twice, and wants every seam different. **The owner's rule governs for his launch and promo work**; the vendor numbers (durations by energy: calm 0.5–0.8 s, medium 0.3–0.5 s, high 0.15–0.3 s) and the principle "cut at peak velocity, match direction and speed on both sides" remain useful. Never fade out then fade in (it renders as a jump cut with a dip).

## 4. Helpers (contracts, not owner code)

The owner's motion kit (`spline`, `cam`, `swapWhole`, `digits`, `wordsSwap`, `revealThrough`, whip, counters, sprites) is `[LOCAL-only]`. A student project needs equivalents with these **contracts**; if the repo `templates/` ships them, use those, otherwise build and test them in an empty project first (`hyperframes check` must pass).

| Helper | Contract |
|---|---|
| spline camera | `(element, keys[[t, {scale, x, y}]])` → one baked monotone-cubic path per scene; zero speed only at the ends; the next tween starts from the spline's end value |
| reveal-through | `(nextScene, t, rect0, rect1, d1, d2)`: the next scene's clip-path goes rect0 → rect1 → full frame; the next scene starts before `t` (overlap) |
| whole-number swap | `(element, old, new, t)`: old out-up, new in-up, 2–3 f offset, hold ≥ 12 f; digit-reel variant for counters |
| words swap | `(a, b, t)`: words out-up/in at the same spot |
| hero match-move | transform to the next scene's element's exact coordinates, ending **on the cut frame**; the next scene shows the same element at the same place with no fade |

All seek-safe: pure functions of time, no `onUpdate` for visible state, no random (seeded hash), no CSS transitions.

### 4.1 Traps that cost frames (all `[PROVEN-internal]`)

- `fromTo(..., {immediateRender:false})` leaves the element **visible** before its start → `gsap.set` the initial state.
- A `filter` tween from `none` to `brightness(0.9)` starts at `brightness(0)` (a black frame) → `fromTo` with full values (`blur(0px) brightness(1)`).
- `opacity:0` in CSS stays hidden if you delete the tween that revealed it.
- A clip that ends at the start of a reveal leaves black outside the shape → keep the previous scene underneath until the iris ends (add a glowing ring on the edge if needed).
- `clip-path` on `.clip` is allowed; `visibility`/`autoAlpha` on `.clip` is forbidden.
- A full-film `backdrop-filter` or big blur halves capture speed (one 15-pill caption layer: 4.3 fps instead of ~19, encode timeout at frame 1348/1350 on OM) → hide such layers outside their window.
- Black frame at every screen boundary: clip start/duration rounding → frame-exact `data-start`/`data-duration` (6 digits) plus a 0.0005 s overlap; a state change on a cut at `start − 0.005`.
- Animated glyphs addressed by class selector without an inline start style may be invisible in capture while the DOM says opacity 1 → address by id with an inline starting style and verify in a snapshot.
- Previews do not prove cuts; only a render does (video is not synced around cuts in snapshots).

## 5. Camera for a speaker (talking-head)

`[RULE-owner]` `[MEASURED-lab for the 10 s take, OM]`: the speaker camera is **never static and never chases**. Open with a push-in; punch-in on emphasis words, punch-out on a new sentence, every 2–4 s; the face is centred at every zoom.

- **Rig:** an outer `#zoom` (scale about the frame centre, eased; no linear start/stop segments) wrapping an inner `#pan` (x = 540 − faceX, from a smoothed path) walked by **one** proxy tween. Plate and cutout share the rig.
- **Never follow the raw per-frame face x.** On a 10 s take with the speaker swaying between x 400 and 608, per-frame follow reached 2,782 px/s² peak acceleration (the owner's "the camera moves in stutters"); the smoothed path (median filter, zero-phase Gaussian σ 0.6 s, per segment, never gliding across a hidden cut) gave 139 px/s² (20× calmer), 0 reversals, face within 30 px of the centre. `camera_path` ok = acceleration ≤ 400 px/s² and face within 45 px. `motion_qa` default flag: |acceleration| > 1500 px/s² or a pan reversal above 60 px/s. These are heuristics, not perception standards; non-rigid graphics can read as jitter (confirm on frames). (src: distilled/02 qa §2.3–§2.4)
- **Face-centred zoom:** with transform-origin at the face x, x-shift = 540 − faceX; with origin at the frame centre, x-shift = scale·(540 − faceX); the minimum scale so no edge shows is 540/faceX (a zoom about the centre enlarges any face offset: a face at x ≈ 465 gave a 110 px error at scale 1.37). Audit the **whole film** after every render (`face_center audit`, tolerance 30 px), not only the touched section; audit hits are candidates (the mask also fires on bright graphics and B-roll people).
- **Behind-speaker graphics** live in the clear side zones (x < 380 or x > 700, y 300–680); every "behind" event needs a camera pull-back (scale 0.72–0.8) or the body swallows it; a dimmed/blurred plate exposes the matte, so dim above the cutout below the chest and blur ≤ 3 px; halo choke on the matte (erode ×2 + 1.3 px blur on alpha).
- **Joins:** a cut between two similar framings of the same speaker reads as a glitch → cover it (film burn, zoom-through) or change scale by ≥ 15 %. Every graded A-roll piece starts **6 frames early** under the layer above (first frames may render ungraded or frozen).

## 6. Calm and brand films: the opposite register

For clinic or brand films the owner rejected a designed "trailer" mix: ONE continuous uniform music bed (the window with the lowest standard deviation of 1 s-LUFS, starting on a beat, fade in, ring out), diegetic foley only for visible actions (events ≈ −7 LU, continuous machines ≈ −13 LU under the music), no risers or impacts unless asked, 3 s-LUFS steps < ~2 LU across the film, natural colour, no AI upscale. Vendor doctrine ("no motion over bad motion", no lazy breathing) agrees with calm; the owner's "camera always moving" is a **style option for the energetic launch register, not a universal law** `[CONFLICT]` (resolution: owner for launches, stillness allowed where the brief is calm). (src: distilled/04 motion-design §6; OWNER_STYLE)

## 7. Hebrew and Latin kinetic type

Logical order always; never reverse strings; isolate Latin brands, numbers and currency with direction isolation; reveal by word or line first (per-character only after niqqud and punctuation pass intermediate-frame checks); wipes, whips and reveals run **right to left**; per-letter builds animate in reading order; the keyword lands 0 to +7 f after it is spoken. Fonts: Rubik baseline, Heebo alternate (both OFL 1.1), always tested at full size for ו/ז, ד/ר, ה/ח. Test strings (original): `אותו לקוח. הזמנה גדולה יותר.` · `₪102.60 — חיסכון של 12%` · `Nimbus (חדש) — מגיע ב־10:30` · `שָׁלוֹם`. Details: the Hebrew skill and [caption-collision.md](caption-collision.md). `[RULE-owner]` `[SOURCED-unverified]`

## 8. Checklist before the first render and before every presentation

- [ ] every scene: one spline camera; no two tweens on the same camera; no blur inside a scene;
- [ ] every seam: an exit/entry vector row (same direction or a declared stop);
- [ ] every camera key: all key text inside the frame **and** the safe zone, including during the move (write the arithmetic);
- [ ] every number: whole swap, no intermediate value, hold ≥ 12 f;
- [ ] every morph: content visible inside it throughout; the next scene starts under it;
- [ ] no 1–2 s foreign world between two similar scenes;
- [ ] events: max gap 15–21 f at 30 fps (end card exempt);
- [ ] each dark scene has a different background; opening and close form a bookend;
- [ ] VO: brand names and heteronyms verified phonetically;
- [ ] `frame_qa` on the previous render and `gsap.set` initial state for every `fromTo(immediateRender:false)`;
- [ ] `motion_qa` 0 flagged ranges (candidates confirmed on frames); the critic was given this table (its past blind spot).

## 9. Failure modes

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| "not smooth", "stuck" at a timestamp | stitched tweens / two tweens on the camera / no spline | rebuild that scene's camera as one spline | C1 + camera table |
| text cut at the edge during a push | no text-fit arithmetic | shrink text or scale | C5 table column |
| hero vanishes and returns | fade instead of match-move | persist the hero through the cut | T1 seam column |
| black frame at a scene boundary | clip rounding or clip ended at the reveal | frame-exact timing + overlap | T6, §4.1 |
| a number flashes an intermediate value | per-digit roll with stagger | whole swap | N1 |
| critic passes a draft the owner rejects | critic not briefed with the owner's rules | add §1 table and the Banned list to the critic brief | [critic-brief.md](../benchmarks/critic-brief.md) |

(src: distilled/02 techniques §2; distilled/04 motion-design; distilled/01 owner-taste; all read 2026-10-02.)

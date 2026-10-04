# Beat menu, hook, B-roll policy, overlays

Load when: choosing or replacing a beat, writing the beat table in PROMPT.md, reviewing B-roll, placing overlay cards. Facts are dated 2026-10-02; source tags point to `distilled/06-hebrew-footage-reference/talking-head-and-footage.md` (written "d06-th") unless stated.

## 1. The rule behind the menu
Pick the beat by the MEANING of the sentence being spoken, so the picture shows what the voice says. A beat is one of: real footage, 3D, UI component, data-driven animation, or speaker-only with a camera move. "Boring", "looks AI", "static", "לא אהבתי" from the author or client is a taste verdict: replace the beat TYPE with another menu entry and say why in one line; do not polish the old one (owner law, d06-th §1.7).

## 2. Menu (sentence -> beat -> build route)
| The sentence says | Beat | Build route (examples from a travel-agency speaker project, generalised) |
|---|---|---|
| a place, a result, "reality" | real footage, full-bleed, opened out of an object (photo in a card -> match cut to the real clip) | licensed real stock or the client's own footage; match cut by clip-path on a full-frame video layer (a `<video>` inside an overflow-hidden parent is not clipped by the renderer) |
| "I talk / listen / ask" | data-driven voice orb (real VO spectrum, STFT -> 36 log bands -> JSON) with chat bubbles from depth | seek-safe: painted from one proxy tween; start it already visible (a dim small orb produced a black flagged frame) |
| a process with steps, "I handle it" | UI component: spinner -> tick -> meta, counter, progress | port a registry component's motion language to GSAP by hand; never run a package installer inside the video project |
| a list of documents or deliverables | 3D product shot (wallet -> tickets rise) | Blender sprite sheet or Three.js when procedural; sprites start on their complete frame |
| availability, briefing | light overlay notifications under the chin + 3D type ("24/7") | light cards, see section 5 |
| calm, planned, covered | ONE continuous 3D shot with a metaphor (plane -> route -> shield dome) | one camera spline per scene, no stitched tweens |
| a problem, wasting time | colour drains behind the speaker (not from him) + the alert-colour keyword + a 3D hourglass | the drain is a layer behind the cutout |
| stage N / structure | top panel over the speaker (>= 40 % of frame), head crossing the panel edge, 3D globe route | needs the cutout |
| none fits | speaker-only beat: push-in or punch + caption keyword | allowed, but never two in a row longer than the cadence |

## 3. Cadence and the hook
- Default: a beat that shows the sentence every 3-6 s, and a camera event every 2-4 s (`references/camera-and-zoom.md`). Sources disagree and the choice is yours to state in PROMPT.md: owner memory says 5-7 s, the author skill 3-6 s, the motion-density feedback 2-6 s for launches, an external taxonomy 1-3 s (hype) to 3-5 s (clean). Treat all as defaults; none is a platform law (d06-th §1.1 [CONFLICT]).
- Hook, 0-1.5 s, layered: cutout + 3D objects behind + a route or line + silhouette flashes, the question on screen. Hook -> retain -> reward is an external framework (unverified); the "+40-60 % retention" claim is marketing, not research.
- External pattern-interrupt numbers (unverified, use only as a starting point): a zoom cut of about 10 % in 0.3-0.5 s; one planned interrupt every 10-15 s in clips over 30 s.
- `motion_scan` (specified tool): flag any segment >= 1.5 s with < 1 visual event per second as "static".

## 4. B-roll policy
| Rule | Why / evidence |
|---|---|
| Full-bleed, always. A framed 740x1316 window on black was rejected: "it must fill the whole screen" | owner law (d06-th §1.7) |
| Real footage only for stock; never AI-looking stills of people; never a static collage or triptych; never a small bar on black; no flat 2D shards posing as 3D objects | owner law |
| Audit stock for foreign text or locale (a passport or calendar of another country) and for a person who is not the speaker under a first-person line (credibility gate) | d06-th §1.7 |
| Smooth hand-off into B-roll (a light or film-burn transition at a glitchy cut; zoom-through ramped on BOTH sides, 4 frames, scale + blur, power2.in) | one-sided ramps read as a hard cut with a blur pop |
| B-roll covers every hidden source cut with >= 6 frames margin each side | gate G3 |
| Licence row per asset in `hf/SOURCES.md`; `License: unknown` or CC-BY-NC = blocked for client work (Q2) | decision default Q2; rights are not inferred from a filename |
| Owner's own transitions folder before stock (two film-burn ProRes clips, 24p -> 30p by hand so the white peak sits on the cut frame) | owner preference, local-only asset |

## 5. Overlay cards on the speaker
Light cards (#F2F1F3 at 0.95, ink text), <= 860 px wide, body 27-38 px, under the chin, never crossing the face box, appear in place (no drop through the face), leave as ONE unit. Dark glass on a black shirt vanishes and reads as a censor bar. These numbers are proven in one project; `plan_lint` checks width and box-vs-face when the plan supplies boxes.

## 6. Layout taxonomy (external, unverified)
1 full-frame face with captions lower-middle (most owner work); 2 framed card (speaker in a top box, data below); 3 persistent title banner; 4 graphic over the chest (table above the body, face visible); 5 full-screen insert. Prop hook (an object in hand in frame 1) and list-tier mechanic (last row hidden until the end) are external patterns.

## 7. 3D
- Blender for hero or photoreal beats (Eevee 1.2-2.3 s per frame, Cycles CPU 1-4 min per background plate on the reference machine), Three.js when the beat is procedural, data-driven, many instances or must stay editable; the 3D object reacts ON the word.
- Local image-to-video was rejected (Wan2.2 5B: about 17 min for 2 s at 544 px; Wan2.1 1.3B lab test about 669 s per output second, E10). Rule: benchmark one second; ETA > 30 min for a shot -> shorten it or quote a hosted route.

## 8. Banned always (union of the author's lists; add every new note)
Crossfade; fade as a transition; bounce on text; glow on static text; small corner labels that look like AI ("feature pills"); the same transition trick twice; an empty screen; a static hold >= 1 s in promo or motion; template look; copying another brand's signature colour; pink as a default accent; accent colour before the reveal; a 3D object covering information (prices); full-film `backdrop-filter`.

## Sources
d06-th §1.1, §1.7, §2.3 (checked 2026-10-02); distilled 02 video-types §2.5-2.6; distilled 02 techniques §6.4-6.5; E10 report via distilled 03 e09-e12-final-results.

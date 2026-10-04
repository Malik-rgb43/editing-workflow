# Registers, density and pace

Load when: choosing the register at intake, writing the Events table, or answering "too fast / too slow / boring".

Source keys: d04 = distilled/04-engines-motion-3d-colour, d02 = distilled/02-workflow-types-techniques, d05 = distilled/05-ai-generation-media-cost (all distilled 2026-10-01, cited 2026-10-02). Numbers are frames at the delivery fps (30 unless the brief says otherwise); an owner table written at 60 fps must be halved. Tags: **studio style** = the author's taste, taught with its reason, beatable by the brief; **measured** = a lab number with its machine; **law** = never broken without asking.

## 1. Pick ONE register (write it in BRIEF.md and in `<direction>`)

| Register | Screen cadence | Event cadence | Camera | Transitions | Sound |
|---|---|---|---|---|---|
| `launch` (app/product film in the Higgsfield-launch grammar) | a new screen every 2-6 s, each with 3D-ish depth (>= 2 depth layers, one hero element popping in z) | an event every <= 0.5-1 s, 45-110 per minute (hand count) | never stops: drift 2-4 % scale/s, push-ins 8-15 %, UI magnified 150-300 % until readable | every seam different, no fade | music edited to picture, brand sound on every brand event, ring-out |
| `kinetic` (type-led, quote, lyric) | a new line/card every 1-3 s | up to ~200 per minute; word swaps count here only | gentle; type is the camera | word/line reveals, waterfall or zoom-through cuts | semantic sync: keyword lands 0 to +7 f after it is spoken |
| `logo` (reveal, sting) | one idea, 3-8 s | result visible by 0.4-0.75 s | one move + a settle | one morph that carries content | brand sound on the reveal, 3-step ending, ring-out |
| `explainer` (graphics + UI) | a screen per idea, 3-6 s | 30-110 per minute | purposeful pans/zooms to the object being explained | motivated by meaning (shared element, match-move) | VO-led: SFX only on visible changes |
| `calm` (brand film, wellness, clinic) | holds allowed | events can be sparse; stillness is a valid choice | slow or locked; no whip | ONE primary transition (0.5-0.8 s) + at most two accents | ONE continuous uniform bed + subtle foley; no risers, gaps or drops |

(src: d04 motion-design §0, §2.3, §2.3b, §6; d02 video-types §5.5-5.7. Owner launch rules are `[RULE-owner]`; the calm row is `[RULE-owner]` from one clinic film, 2026-09-30.) `[CONFLICT]` "always-moving camera" (owner, launches) vs "stillness over bad motion" (vendor product-launch doctrine): owner wins for `launch`; `calm` may hold.

## 2. Event, scene, pace - definitions the checker uses
- **Event** = a new element entering, a transformation, a cut, or the start of a camera move; word swaps count only in `kinetic`; simultaneous cosmetic animations count once. Count by hand from frames, not from an automatic cut detector (it was wrong in 9 of 20 reference films). (src: d04 motion-design §2.3; d02 video-types §5.6)
- **Breath** = a declared quiet beat (before a reveal: 5-21 frames of silence in the market references). Mark it in the Events table (`note` = `breath`) so the gap check passes honestly.
- **Two gears:** dense -> breath -> dense -> silence before the reveal. Compare average AND worst-window density (a good average can hide one frantic second then emptiness). (src: d04 motion-design §10)
- **Length:** a 30 s dense cut felt x1.7 too fast; the approved version was 45 s. "Too fast" = stretch selectively (long moves x1.6, snaps stay fast), never by cramming or slowing everything. Lock the length at intake. (src: d02 video-types §5.7; the author's own app-launch film)
- **Frame 1:** motion from frame 1; the payoff (or the first graphic) by 0-1 s; an early reference had a first graphic at 1.85 s and 18.85 s and the author listed that as a gap.

## 3. Timing numbers (owner and vendor; fps stated)
| Item | Value | Tag |
|---|---|---|
| Entrance (snap) | `expo.out`/`power4.out`, 2-10 f, 60-70 % of the distance in the first 2-3 f, directional blur on the first frame only | studio style (launch teardown, 8 films) |
| Entrance (clean & smooth) | `cubic-bezier(0.22,1,0.36,1)` named `owner.enter`, 14-17 f at 30 fps (0.47-0.57 s); source fps of the original note unresolved | studio style; "clean & smooth" beats snap numbers wherever the author will judge "smooth" |
| Exit | `power3.in` / `power2-4.in`, 3-7 f, then a cut; never a fade; exits are faster than entrances (e.g. 0.4 s in / 0.25 s out) | studio style |
| Overshoot | none on text; `back.out(1.2-1.7)` only on living elements (icon, avatar, orb, pill) | studio style |
| No "middle" moves | 0.6-1.0 s moves are either a snap or a slow drift | studio style |
| Stagger | 2-5 f; total stagger < 0.5 s | studio style / vendor |
| Camera push | >= 1.2-1.6 s, starting BEFORE the event | law (owner C4) |
| Reversal | each move >= 1.0 s, range <= 1.3x | law (owner C3) |
| Number swap | old out-up, new in-up, 2-3 f offset, final value held >= 12 f; never per-digit stagger | law (owner N1) |
| Close-up of a key detail (client name, price) | >= 0.9 s, UI text >= 40 px at 1080 | studio style |
| Blur peak in cuts | text 10 px (20 px smears into illegibility); full-frame surfaces 18-20 px; same peak both sides of a cut | vendor, unverified |
| Blur on a camera move inside a scene | none | law (owner C1) |
Seconds = frames / fps: 14-17 f = 0.467-0.567 s @30 and 0.233-0.283 s @60; 12 f = 0.4 s @30. At 130 BPM a bar is 1.846 s, so a 1-1.5 bar screen is 1.85-2.77 s (only if the actual track matches). (src: d04 motion-design §4.3)

## 4. The Higgsfield-launch grammar is a reference, not a costume
Take: "snap, then drift"; the camera on UI always moving; the music as the sound design (110-170 BPM, hits on events); a structure of hook 2-8 s -> brand reveal on the drop (about 3-12 s) -> 3-7 "ask -> AI works -> reveal" cycles -> payoff -> end card 2.5-3 s with a text-only CTA. Do NOT take: another brand's signature colour (the lime `#D6FF3A` family is on the author's banned list), the original loudness (-7 to -9 LUFS, TP up to +2.7; deliver house preset v1: -14 LUFS, TP <= -1), or three brands' languages in one film (reads as a template). (src: d04 motion-design §2; d02 video-types §5.5)

## 5. Transitions
Owner rule for `launch`/`kinetic`: every seam different; never a crossfade or fade-as-transition; blur only inside transitions. Vendor rule for other registers: pick ONE primary (60-70 % of changes) + 1-2 accents; durations calm 0.5-0.8 s, medium 0.3-0.5 s, high 0.15-0.3 s; never fade-out then fade-in (it renders as a jump cut with a dip). Vocabulary (owner): zoom-through into an object; shared element (a thumbnail flies and becomes the hero); 3D page fall-away; light-line bloom; match-move of a number; whip with blur; clip-path portal; push into a phone that continues in the next scene. Cut at peak velocity, same direction and speed on both sides (e.g. 230 px / 0.3 s on both sides of a cut-the-curve seam). Do not use star iris, tilt-shift, lens flare, hinge/door transitions (broken or cheap-looking in the vendor catalogue). `[CONFLICT]` crossfade: owner bans it, vendor treats it as primary; owner wins for launches, vendor numbers are still useful. (src: d04 motion-design §5)

## 6. Banned list (studio style; add every new owner note)
crossfade; fade as a transition; bounce on text; glow on static text; small corner labels / feature pills ("QUANTITY BREAKS": they read as AI-made, meaning goes through VO, large type or the UI); the same transition trick twice; an empty screen (a dot or rings on black); a static hold >= 1 s in launch/promo; a template look; copying another brand's signature colour; stock UI kits; the accent colour before the reveal; a 3D object covering information (prices); full-film `backdrop-filter` or big blur. The four lists in the research differ slightly; this is their union. A student keeps a studio's own list in the PROMPT `Banned:` line. (src: d02 OWNER_STYLE §M)

## 7. Measuring density without lying
Ledgers (proposal, `[IDEA]`): Scene, Shot, Event, Seam. Report separately: hard cuts per second, semantic events per second and the busiest 1 s window, camera-only motion duration, concurrent attention targets per event window, essential copy hold. `motion_scan` (planned tool) flags >= 1.5 s with < 1 event/s. Until it exists, the Events table + a frame-sample at three times per scene is the evidence. The "event every 0.5 s" is a style target, not an export failure in every genre. (src: d04 motion-design §10)

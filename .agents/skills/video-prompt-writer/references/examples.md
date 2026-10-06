# Two worked examples (synthetic subjects)

Load when: you need a concrete model of the skeleton, a split scene, or the vendor-short shape. Every subject below is invented for teaching (a lighthouse keeper, a courier); no client, real person, brand or IP is involved. **No generation was run for any example: they show well-formed prompts, not proven results.** `python scripts/seedance_prompt_lint.py --self-check` lints all three (they must stay clean) and then plants defects.

How to read: the prefix is pasted verbatim at the top of EVERY prompt (owner rule: each prompt is standalone). The output to the user is one copy-ready plain-text fence per prompt, never a table, HTML or checklist; after the prompt ONE short follow-up question is allowed (for example "Want 3b, the aftermath, as the next 15 s?").

## Example 1 - `owner-cinematic`, 15 s, three shots, 16:9 (owner preference)
Brief: "the keeper relights the lighthouse before the storm". Registry: `@keeper` (Element: yellow oilskin, wool cap), `@lighthouse`, `@cove` (location, style reference only). Storyboard beat `b4`; its approved start-frame still and the film's image STYLE PREFIX come from `image-prompt-writer`.

shot_id: b4 · 16:9 · start frame: _work/stills/b4.png
```text example=1 preset=owner-cinematic tags=keeper,lighthouse,cove dur=15
Style: Live-action footage from a physical cine camera — no 3D render, no game engine, no game-cutscene aesthetic.
Cinematography: naturalistic master cinematography.
Lighting: Natural light only — contre-jour backlight, camera on shadow side, atmospheric haze. Key light from sky and windows only.
Color: 60:30:10 — dominant / secondary / accent.
Camera: Physical cine lens. 180° shutter motion blur.
Skin: Pore-level realism — vellus hair, asymmetric moles, capillary flush, pore-shadow matching on-set light.
Acting: screen-acting detail — micro-pauses before reactions, precise eye-line, wet living eyes with catch-lights, visible breath and chest rise.
Physics: Gravity and inertia respected — mass has real weight, correct contact shadows. No floating props.
Composition: Rule of thirds + golden ratio. Every person moving from frame one.
Continuity: Characters, props, environment identical across every cut. No identity drift.
Technical: 24fps smooth motion. No jitter.
Audio: Environmental SFX only. No music. No subtitles.

SUBJECT — @keeper (matches input 100%), a lighthouse keeper in a yellow oilskin coat and wool cap, climbs the last iron stairs to relight the lamp before a storm; goal: finish before the squall arrives; beat: quiet resolve turning to relief. @lighthouse (matches input 100%) stands behind her. WB 5600K. MULTISHOT.

LOCATION — @cove is a STYLE REFERENCE ONLY, not a fixed keyframe. Slate-grey sea, wet black rock, low cloud with a thin amber seam at the horizon. The model may freely extend the world; the subject moves through space — NOT pinned to the input frame. Do not reproduce the reference 1:1.

ACTION — She beats the storm to the lamp room and brings the light back, in three shots.
SHOT 1 (0:00–0:04) — Wide on the stair tower from the sea side: @keeper reaches the top landing, braces a hand on the rail against the wind, eyes on the horizon. Hard cut.
SHOT 2 (0:04–0:09) — Medium inside the lamp room: she wipes salt from the lens with her sleeve, turns a brass key, and the mechanism clicks and begins to rotate. Hard cut.
SHOT 3 (0:09–0:15) — Wide from the rocks below: the beam sweeps out across the water and the waves catch it; @keeper stands in the gallery as a silhouette, shoulders dropping as she exhales. Hard cut.

CAMERA — SHOT 1: low angle at tripod height, 24mm, slow push-in, motivated by her climbing toward the light. SHOT 2: eye level, 50mm, locked-off, steady so her hands carry the beat. SHOT 3: low angle from the rocks, 35mm, slow crane up, motivated by the beam rising.

STYLE — LOOK: 35 mm film look, slate grey-blue, wet black and brass amber (#4A5A66, #15171A, #C8923A), fine grain, no text, no labels. Dominant 60% slate grey-blue / Secondary 30% wet black / Accent 10% warm brass-amber. WB 5600K. Reinforce lighting: sky light from the left, haze, the lamp as the only practical source.

CONSTRAINTS — 16:9. NO slow-motion. One camera move per shot. Beam and lamp keep a consistent size across cuts (normal size, NOT oversized). Wind pushes her coat and the spray with real weight. NO eye glow.
```
What to notice: the `shot_id` line names the start-frame still; the LOOK is the stills' STYLE PREFIX, verbatim, so the still and the motion share one look; timecodes fill 0:00-0:15 with hard cuts; one camera move per shot with its WHY; the 60/30/10 colour split is for THIS shot; the location is a style reference and the subject travels through space; physics is described broadly (real weight, spray, wind) with no km/h or degrees; the ratio is stated in CONSTRAINTS because it came from the delivery.

## Example 2 - `vendor-short`, 10 s, one shot, 16:9 (vendor contract shape, own words)
Brief: "a courier collects a coffee order". Registry: `@courier`. Positive phrasing; speed numerically in km/h as the vendor contract wants.
```text example=2 preset=vendor-short tags=courier dur=10
@courier

A courier in a red rain jacket rides a cargo bike across a wet stone plaza at 15 km/h, passes a fountain on her left, and stops at a cafe door where a barista hands her a paper bag. Steam rises from the bag as she tucks it into the front basket and pushes off again. Overcast daylight from the right, soft shadows, puddles reflecting grey sky, cobblestones glistening. CUT: close on her boot stepping onto the pedal as the bike rolls forward.
Camera: tracking shot at wheel height, one smooth glide alongside the bike.
Style: overcast natural light from the right, 35mm film tone, atmospheric haze.
Constraints: avoid jitter and bent limbs. SFX only, no music, no subtitles. 10s. 16:9.
```
What to notice: a main block of 83 words (budget 60-100), one action per CUT, light inside the block, camera and subject motion written separately, left/right from the camera, one primary camera move, the standard quality line in Constraints.
**The conflict, side by side.** Vendor: "rides ... at 15 km/h". Owner presets: "rides at a brisk cycling pace" (generalize physics: exact km/h and degrees break physics). Both are single-source and untested on this account; the lint reports numeric speeds as a warning for owner presets and an info for vendor-short, and does not choose. See `owner-vs-vendor-conflict.md` for how to settle it with ONE approved A/B sample.

## Splitting a long scene (Na / Nb)
A scene longer than about 15 s becomes `3a` and `3b` under the same scene number; each is a standalone prompt with the SAME prefix and the SAME tags, filling its own 15 s. Continuity lives inside the SUBJECT/ACTION language of each (not a separate visible block): 3b opens by naming the state 3a ended in (position, facing direction, what the characters hold) and re-anchors who is where, because spatial continuity breaks on cuts. Example opening for 3b: "Continuing from the moment @keeper steps out onto the gallery with the lamp already turning, same coat, wind still from the left, ...". One prompt = one clip of about 15 s, no dead air.

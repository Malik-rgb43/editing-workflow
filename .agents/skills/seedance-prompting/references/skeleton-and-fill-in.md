# The shot-by-shot skeleton (owner order) and how to fill each field

Load when: writing or reviewing any `owner-cinematic` prompt, or splitting a long scene. Source: the owner's own Seedance skill (distilled/05 prompting §2, 2026-10-01) plus camera/shot vocabulary from the vendor and community texts (paraphrased, dated in `vendor-contract-dated.md`). Nothing here was measured by a generation run.

## 1. The exact order
```
[PRESET PREFIX - verbatim, see presets.md]

SUBJECT — who/what is in the shot, each @tag "matches input 100%". One line on the goal + the emotional beat. WB <temp>. MULTISHOT.
LOCATION — @location is a STYLE REFERENCE ONLY, not a fixed keyframe. Mood / architecture / light. The model may freely extend the world; the subject moves through space - NOT pinned to the input frame. Do not reproduce the reference 1:1.
[LAYOUT — optional: @scheme (aerial layout) as a positional reference so recurring elements keep their places]
ACTION — one line of intent, then the clip broken into timecoded shots:
SHOT 1 (0:00–0:0X) — blocking, gesture, eye-line, the beat. Hard cut.
SHOT 2 (0:0X–0:0Y) — next beat. Hard cut.
SHOT 3 (…) — final beat.
CAMERA — per shot: angle, height, lens feel, movement, motivation (WHY).
STYLE — Dominant 60% / Secondary 30% / Accent 10% for THIS shot. WB <temp>. Reinforce lighting (sun/window position, haze).
CONSTRAINTS — hard rules: ratio, NO/USE slow-motion, camera behaviour, legibility, scale locks, continuity must-holds, NO eye glow.
```
One prompt = one clip of about 15 s, fully standalone (prefix baked in), timecodes filling ALL of it (no dead air). A longer scene splits into `Na/Nb/Nc` under the same scene number (see `examples.md`). Output is ALWAYS copy-ready plain text in a code fence - never an HTML shot list, artifact, checklist, table or any interactive file (this skill deliberately differs from `choice-board`). After the prompt(s) ONE short follow-up question is allowed.

## 2. Field by field
- **Asset registry.** Every recurring person, prop, location or effect gets an `@tag` that MUST match the Element name in the tool exactly (`@hero`, `@rival`, `@prop`, `@location`, `@scheme`). Refer to the tag every time ("@hero ducks under the beam", never "the character"). Identity lock stays short: "matches input 100%" - do not enumerate every detail. One asset = one angle (a location's front and back are different assets); 3/4 angles beat frontal for locations; asymmetric beats symmetric. Whether the Seedance 2.5 route accepts the owner's `@tag`/Elements syntax identically to 2.0 is unconfirmed: never reuse a 2.0 payload on 2.5 (vendor guidance, dated).
- **SUBJECT.** Identity is static descriptors only (silhouette, face, palette, props, clothing); motion and camera live in ACTION/CAMERA. Describe by role, clothing and action - **never by age words** (boy, girl, child, kid, young, teen, little; the lint errors; a Seedance-specific safety/filter rule from vendor+community text, unverified). Avoid named IP, real people and brands: use generic descriptors. Tag scale when it matters ("small 0.33 L can", "human-scale 1.85 m") and repeat "normal size, NOT oversized" in CONSTRAINTS if needed. At most 3 characters tracked across cuts.
- **LOCATION.** A style reference, not a keyframe: the subject travels through the space. Use `@scheme` for anything that must sit in the same place across scenes. Continuity is carried in the SUBJECT/ACTION language, not in a separate visible block.
- **ACTION.** Acting in specifics, not labels ("jaw tightens, slow exhale, shoulders drop", not "sad"). The character is already IN the action (states, not transitions). One primary action per shot (+1-2 secondary), a beat density that fits the length: 12-15 s carries 2-3 beats with timestamps (the community table allows up to 6; more blurs and morphs). Open a multi-character scene on a wide shot that fixes every position. Default to NO slow-motion; call a speed ramp on a specific beat and ramp back. **Generalize physics**: describe broadly with real weight and gravity; exact km/h and degrees break physics (owner) - see `owner-vs-vendor-conflict.md`. Do not put text, captions or subtitles in the shot: text is added in the edit (generated glyphs are garbled; Hebrew especially).
- **CAMERA.** Intentional: angle + height + lens feel + movement + WHY. Describe camera motion and subject motion separately ("the dancer spins slowly; the camera holds fixed framing"). ONE primary move per shot (never push-in + pan + orbit); left/right from the camera's point of view; the move verb in the first 8-10 words of the shot. Lens as FOV plus consequence: 24-35 mm = space and flatness, 50 mm = human perspective, 85 mm+ = compression/isolation; a 16-24 mm wide angle conflicts with shallow depth of field. Mix registers across a clip (locked-off, handheld + shake + Dutch, FPV drone, super-macro, crane, continuous one-take) and change BOTH shot size and camera character at a cut. Do not use the word "fast": make exactly one element fast, or give a duration.
- **STYLE.** 60:30:10 colour split with named colours for THIS shot; WB per shot (4000 K across cuts of one scene is the vendor default); light direction concrete (window position, haze); camera on the shadow side for volume. One style anchor + at most 1-2 supporting tokens.
- **CONSTRAINTS.** The ratio (from the delivery: ask when unknown), slow-motion policy, camera behaviour, scale locks, continuity must-holds, "NO eye glow". Negatives are tolerated here as scoped exclusions (owner).

## 3. Camera and shot vocabulary (use the tool's exact names when a UI names them)
Moves: push-in / pull-out (dolly), tracking / follow, slow orbit / arc, crane up/down, truck (parallel), pedestal (vertical rise), rack focus, crash zoom, whip pan, handheld, locked-off / fixed, over-the-shoulder, FPV drone. Angles: low, high, eye level, bird's-eye, worm's-eye, Dutch. Sizes: ELS, WS, MS, MCU, CU, ECU, insert (0.3-0.5 s, static, causally motivated, subject-named: "HIS hand gripping the rail", not "a hand"). Compatible: dolly in + Dutch angle, crane up + orbit, FPV + crash zoom, handheld + run. Conflicting (never one shot): dolly in + dolly out, crane up + crane down, locked-off + handheld, orbit + pan. Cut vocabulary: double-contrast cut (size AND camera character change), re-anchoring after a cut (re-state who is where and facing which way), 180 degree rule, match cut, smash cut, L/J cuts.

## 4. Pre-send checklist (run mentally, then `scripts/seedance_prompt_lint.py`)
Prefix pasted verbatim and recorded; headings in order; timecodes contiguous and filling the clip; one camera entry per shot with a WHY; tags consistent with the registry; no age words, no named IP/real people/brands; no quality charms or text instructions in the body; ratio stated from the delivery; plain-text fence; no money talk (this skill never spends: hand off to `paid-generation-gate`).

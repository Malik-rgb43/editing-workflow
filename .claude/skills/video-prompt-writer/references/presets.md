# Named presets (owner preference) and the vendor-short profile

Load when: choosing or recording the prefix of a Seedance prompt. `scripts/seedance_prompt_lint.py` reads the fenced blocks below (`preset=<name>`): do not rename the info strings; edit a preset's text only when the author/student supplies their own (then the lint follows the file).

**Labels.** Preset 1 is *owner preference* (decision default Q7, revised 2026-10-03: the cinematic prefix is the one named preset, labelled as the toolkit author's preference; the vendor contract is linked). It is not a fact about what Seedance rewards: no generation was run, so it is not measured better than the vendor contract. The prefix is written ONCE and pasted VERBATIM at the start of EVERY prompt of one film; if the user supplies a custom prefix, use theirs verbatim (`--prefix-file`). Record the choice in the answer: `prefix: owner-cinematic | vendor-short | custom (user text)`.

Pick by register, not by taste of the day:
| Brief says | Preset | Why (owner lessons) |
|---|---|---|
| shot-by-shot film, drama, spec commercial, ~15 s multi-shot | `owner-cinematic` | naturalistic cine look, full 15 s of timecoded hard cuts |
| a single short shot, a casual or phone-style look, or the user pastes the vendor contract | `vendor-short` | 60-100 word block, positive phrasing, speeds in km/h (see `owner-vs-vendor-conflict.md`) |
Do not mix two presets in one prompt. If the register is ambiguous, ask ONE question; if the run is non-interactive, default as in the table and record `defaulted`.

## 1. `owner-cinematic` (owner preference; the author's own prefix, reproduced as the author's core prompt asset)
```text preset=owner-cinematic
Style: 8K cinematic. Photorealistic — no 3D render, no game engine, no game-cutscene aesthetic.
Cinematography: naturalistic master cinematography.
Lighting: Natural light only — contre-jour backlight, camera on shadow side, atmospheric haze. Key light from sky and windows only.
Color: 60:30:10 — dominant / secondary / accent.
Camera: Physical cine lens. 180° shutter motion blur.
Skin: Pore-level realism — vellus hair, asymmetric moles, capillary flush, pore-shadow matching on-set light.
Acting: top-tier cinematic — micro-pauses before reactions, precise eye-line, wet living eyes with catch-lights, visible breath and chest rise.
Physics: Gravity and inertia respected — mass has real weight, correct contact shadows. No floating props.
Composition: Rule of thirds + golden ratio. Every person moving from frame one.
Continuity: Characters, props, environment identical across every cut. No identity drift.
Technical: 24fps smooth motion. 8K detail. No jitter.
Audio: Environmental SFX only. No music. No subtitles.
```
Notes: (a) it contains quality charms ("8K cinematic", "Photorealistic") and negatives ("no 3D render", "No music") that the vendor/community contract tells you to avoid - `[CONFLICT]` kept visible, not resolved (see the conflict file); the author treats the prefix as a measured-in-practice asset and applies the anti-slop rule to the scene body only. (b) It was derived from the vendor's style prefix (which names two real cinematographers); the author's version drops the names - never add real people's names. (src: distilled 05 prompting §2.1, §3.2, contradictions, 2026-10-01)

## 2. `vendor-short` (profile, no prefix block)
A short single-shot prompt in the vendor contract's shape (own words; details and date in `vendor-contract-dated.md`): optional reference-tag lines, then a **60-100 word main block** (subject + action + environment + spatial layout, one action per CUT, light inside the block, everything positive), then three lines:
```
Camera: <ONE primary move + optional subtle secondary>
Style: <film stock/look, light, atmosphere>
Constraints: avoid jitter and bent limbs. SFX only, no music, no subtitles. <duration>s. <ratio>.
```
Optional own-words style line (no real names): `Style: natural light, contre-jour backlight with the camera on the shadow side, atmospheric haze, physical cine lens with 180 degree shutter blur, 35mm film tone.` Ratio and duration come from the delivery (sequence format or stated platform), never from habit: silently defaulting to 16:9 for a vertical reel crops two thirds of the frame; unknown -> ask.

## 3. Custom prefix
If the user supplies a prefix (a studio style bible, a film-specific look), use it verbatim at the start of every prompt of the film, record `prefix: custom`, and run the lint with `--prefix-file <file>`. Do not "improve" it silently; surface any conflict with the vendor contract in one line.

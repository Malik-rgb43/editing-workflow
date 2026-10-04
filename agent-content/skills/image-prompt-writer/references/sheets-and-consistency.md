# Sheets and consistency

Load when: a character, place or object appears in 3 or more shots, or a recurring human needs to look the same. Dated 2026-10-03. Tags: `[RULE-owner]` the author's practice; `[SOURCED-unverified]` community or vendor guidance, not tested on your account.

## 1. The stack
1. **Character block** (written, static descriptors only): face shape, hair, build, skin tone, wardrobe, one distinguishing detail. Reused word for word in every prompt. Motion and camera never go in it. `[RULE-owner]`
2. **Character sheet**: front (neutral expression, even light), three-quarter, side, back; optional four expressions. Make it once, approve it, reuse it as the identity reference. A clean sheet outperforms several casual photos. `[SOURCED-unverified]`
3. **Location sheet**: straight-on wide, left perspective, right perspective, reverse, one close-up of environmental detail; lock architecture, light quality, colour treatment, key details. Prevents "six scenes in a rain-soaked alley, six different alleys". `[SOURCED-unverified]`
4. **Prop sheet** (recurring object): front, side, back, three-quarter, top; materials noted. Generated once at the start.
5. **A start-frame still for EVERY video shot**, in the same prefix, made from the sheet; the video prompt then describes only motion. If the video model takes only a start and end frame, this is not optional. `[RULE-owner]`
6. Anything appearing in fewer than 3 shots does not earn a sheet.

## 2. How to ask for a likeness
Name each reference by its ROLE, not its file number: "the first reference supplies the face and hair; the second supplies the jacket; the third supplies the light". Describe in the prompt only what changes. Attach the sheet every time a model accepts image references; otherwise repeat the character block word for word.

## 3. Face-drift test (before the film depends on a character)
Generate front, side, three-quarter and back. Test a close-up FIRST (face drift shows there). If identity holds across all four, the character is production-ready; if not, use a silhouette, a back view, a mask or a non-human lead instead of prompting harder. `[SOURCED-unverified]`

## 4. Real people
No real person's face as a reference without written consent, and none for a public figure. Some models refuse or flag real-face references (an owner project saw 7 of 7 refused on one model). Prefer synthetic characters for public-facing work. Realistic synthetic people, places or events carry the platform's AI label.

## 5. Aspect and safe zones
State the delivery ratio in every prompt. Leave the safe-zone areas empty of key content (house preset v1 lives in `pro-video-editor/references/platforms-and-safe-zones.md`); space for post-added captions stays empty.

# Design for the model's weaknesses (decide BEFORE prompting)

Load when: choosing the format, writing the shot list, or reviewing a script that a model will have to realise.

Source keys: d05 = distilled/05 (prompting §2.6, §7-§9; image-and-design-assets), d02 = distilled/02 video-types §6, bp = blueprint. Owner rules are `[RULE-owner]` (taste + hard-won practice); nothing here was measured by a generation run (none was run). "Market" numbers are the author's small reference sets (11 AI films, 10 of them 16:9; the author's own 9 videos, 7 of them 9:16): indicative, not industry statistics.

**Principle (owner):** an AI video is edited, not generated: the model gives raw takes, the edit makes the film. A model name is not a spec, and no model is proven for Hebrew, hands, text or identity across cuts.

## 1. Pick one format and say why
| Format | When | Notes |
|---|---|---|
| X-ray / anatomy explainer | a clinician or expert explains a condition | needs ground truth (section 3) |
| list gag, every beat a standalone shot | ads, humour, no continuity needed | easiest to design around weaknesses |
| street / historical interviews | dialogue-driven, native-audio models | English evaluated, Hebrew unvalidated |
| parody of a known format (trailer, news, game cutscene) | local business, organic reach | third-party IP: organic only |
| motion transfer / face comedy | a real reel re-cast | consent + retained source; parody only |
| hybrid launch: HyperFrames UI + AI inserts | product/app launch | route the UI beats to `motion-graphics-builder` |
| local-business hybrid: real footage + AI character/moments | shop, clinic, cafe | real footage leads: if AI is only B-roll use the footage type skill |
A paid ad made mostly of AI loads BOTH this skill (picture, generation, cutting, look, fps) and `ad-promo-editor` (offer, CTA, safe zones, variants, compliance); real footage leading with AI as B-roll = `ad-promo-editor` alone.

## 2. Weakness -> design response
| Weakness (reported) | Design response | Gate |
|---|---|---|
| Close-up human faces drift, morph or read as AI | silhouettes, backs, masks/helmets, stylised or non-human leads (references that worked: no faces, balloon head, jelly creature, B&W + blur); a close-up only when the chosen model is proven on it (test ONE take first) | G5 |
| Hands, text and props change between cuts | script every beat as a **standalone shot**; nothing that needs identical hands/text/props across cuts | G5 |
| Identity drifts across clips | character sheet (GPT Image, 3 angles, neutral light) -> character pack (3-5 references: clean front, 3/4 profiles, full costume) -> a keyframe for EVERY shot -> the prompt describes ONLY motion; paste the identity block verbatim; test a close-up first | G9 |
| Start/end-frame-only models (e.g. Kling 3.0, Wan 2.7 as listed 2026-09) cannot take references | make a start frame per shot from the sheet (`-i sheet.png`) and generate from it | G4 |
| Real-face references blocked or flagged (owner: 7/7 on one model, 2026-09) | synthetic characters or archetype descriptions; test one take; try another route | G9 |
| Generated text and Hebrew are garbled | never generate text: overlay in HyperFrames in a licensed local font; Hebrew captions proofread by a human (an owner series shipped "מתאבה", "לסבוב" misspelled in 2 of 5) | G8 |
| Anatomy or technical truth wrong (extra bones, wrong side) | build ground truth first (Blender, a medical reference image), pass it as start/end frame or `-i`, name parts and the side ("LEFT leg, lateral view facing left") in every prompt; the client approves factual stills before video | G4, G9 |
| Fast motion morphs; many beats blur | one action per clip (1 primary + 1-2 secondary), one camera move per shot; if fast motion morphs generate slow and speed up in post | G5 |
| Physics/scale ("oversized" props, floating objects) | state scale ("small 0.33 L can", "human-scale 1.85 m") and repeat "normal size" in constraints when it matters | G9 |
| More than ~3 characters tracked across cuts; exit-frame = implicit cut (Seedance, community claim, unverified) | keep <= 3 characters; never choreograph exit and re-entry in one continuous shot | G5 |
| Dialogue clips: lip-sync degrades past 8 s; multi-person lip-sync unresolved | 3-8 s, medium close-up or closer, one speaking face, locked camera; or a real VO over shots where the mouth is not visible | G5 |
| Hebrew speech unproven on every route | record the real line; test lip-sync on ONE take; fallback: VO over cutaways | G8 |

## 3. Ground truth for factual subjects (medical, technical, product)
Build the truth first, generate second. A picture that contradicts the VO fails G1 (AI integrity). The client approves factual stills before any paid motion; claims appear only as the clinician/client states them with the title they use by law (confirm). Facts that appear on screen (phone, address, price, CTA) are visible placeholders listed for the client, never generated.

## 4. Budget realism (do not promise acceptance rates)
Plan 2-3 takes per shot. One external production reported 300-400 generations for about 15 usable clips (about 5 % usable, a 20:1 overshoot) over about two days - single secondary source, unverified; treat it as a warning, not a forecast. "Curation is the work": the cost of review time is real even when metered cash is zero. Two failures on the same defect = change the approach (reference or start frame, or finish the near-miss in the edit), not a third re-roll. (src: d05 prompting §5; d02 video-types §6.3)

## 5. Consistency systems, when they pay off
A property that appears in 3 or more shots earns a sheet (character, location five-view sheet, multi-angle prop sheet, outfit, palette/mood); a single-shot detail does not. Hero Frame: make the sequence's tone/lighting/composition as an image first, iterate there (an image is far cheaper than a video attempt), then animate ONCE. Start/end frames: the end frame of shot A is the start frame of shot B (kills guessed transitions; incompatible with a reference pack on some routes). Describe a match as light and atmosphere language, not as a copy ("the same overcast midday light as the reference"). (src: d05 prompting §7)

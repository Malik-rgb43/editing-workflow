---
name: image-prompt-writer
description: >-
  Write copy-ready text-to-image prompts for the stills-first stage of a video: keyframes, start frames, hero frames, character and location sheets, B-roll stills, thumbnails; one STYLE PREFIX per film, no text inside the picture. Triggers: image prompt, text to image, keyframe, character sheet; פרומפט לתמונה, תמונת פתיחה, גיליון דמות. NOT for video prompts (video-prompt-writer), spend approval (paid-spend-gate), real photo edits, or the whole AI film (ai-generated-video-editor).
compatibility: >-
  Plain text in, plain text out; Python >= 3.9 (stdlib) only for the optional lint script. Model names, limits and prices are NOT in this skill: they live in the dated modules of ai-generated-video-editor.
metadata:
  version: "0.1.0"
  kind: tool
  status: "specified; deterministic checks only; model eval not run"
---

# image-prompt-writer

Turns a beat, a shot card or a brief into copy-ready still-image prompts. A still is the cheap place to lock identity, product, location and light BEFORE any paid motion, so this skill is the first writing step of an AI-shot film (`ai-generated-video-editor` calls it for every `image` field of a shot card). **No generation, no spend, no files other than the prompt text.**

## Rules (read first)
1. **Never generate or spend here.** "Make it / run it" gets the prompts plus a hand-off to `paid-spend-gate` by name. Even a free local route asks the user's explicit OK before an image is generated.
2. **One STYLE PREFIX per film**, written once (render look, palette hexes, lens, grain, "no text, no labels") and pasted VERBATIM at the start of every prompt of that film. Record it in each answer: `prefix: <name>` (user's own, or from the look bible). No prefix yet: write one first and ask for a yes.
3. **Order of a prose prompt:** medium and ratio -> subject (with identity tag) -> action or state -> setting -> light direction -> lens or stock -> composition -> exclusions. Subject and action sit in the first 20-30 words.
4. **Concrete, not charming.** Delete words no camera or light meter can measure (cinematic, epic, stunning, masterpiece, 8K, photorealistic used as a charm). Say the lens, the stock, the light direction, the material and its imperfection (scratches, dust, patina) instead.
5. **Positive phrasing.** Write what IS in frame. The only negatives allowed are scoped exclusions: "no text, no labels, no watermark".
6. **Text is added in post.** No subtitles, captions or Hebrew inside the picture. The one exception is an asset whose job is text (a thumbnail, a labelled sheet) when the user asks: then ONE text element, the exact string in quotes in its own language, and a human proofreads the render.
7. **People are synthetic and described by role, clothing and action.** No real people, no brands or IP, no age words. A real-face reference photo is a route risk (some models refuse or flag it): say so before relying on it.
8. **Consistency is built, not hoped for.** Identity descriptors (static: face, hair, build, wardrobe) live in a character block that is reused word for word; the scene prompt adds only what changes. Anything that appears in 3 or more shots gets a sheet. Every video shot gets its own start-frame still, in the same prefix.
9. **One variable per iteration.** When a prompt is close, change ONE thing (subject detail, composition, light, style), regenerate, compare, lock. Two failures on the same defect: change approach (a reference, a simpler composition, finish it in the edit), not a third re-roll.
10. Skills are procedure, not permission: the user's and the project's limits on spend, uploads and likeness win. Specified, deterministic checks only; model eval not run (decision default Q4).

## Inputs -> outputs
In: the beat or shot card (purpose, ratio, what must be recognisable), the look (prefix or reference), references and their ROLES (identity, product, location, light), the platform ratio. Out: one fenced code block per prompt (plain text or JSON, never HTML, a table or a checklist), the recorded prefix, and at most ONE follow-up question.

## Procedure
1. **Read the beat.** What must the viewer recognise in 0.5 s? What is the clean window the video shot will use? A shot needing hands, text or props identical across cuts is redesigned, not prompted harder.
2. **Pick the format** (`references/formats-and-templates.md`): B prose for one frame, A JSON for sheets, storyboards and anything with regions or labels, C meta-prompt only when the user gave a theme and wants the model to derive the composition.
3. **Fill the template** in order (rule 3); prefix first; identity block verbatim; references named by role ("the reference supplies the face, not the outfit").
4. **Sheets before shots** (`references/sheets-and-consistency.md`): character sheet (front, 3/4, side, back, neutral light), location sheet (five views), prop sheet; then one start-frame still per video shot.
5. **Lint** (`python scripts/image_prompt_lint.py draft.md --ratio 9:16 [--prefix-file prefix.txt]`), fix, answer. Keep the answer short: the fences, `prefix: ...`, one question at most.
6. **Hand off.** To `video-prompt-writer` when stills are approved and a motion prompt is next; to `paid-spend-gate` before any paid generation; to `visual-choice-board` when the user hesitates between 3 or more looks.

## Gates
States `pass | fail | blocked | n/a` with a reason. A lint that could not run is `not_run`, never `pass`.
| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G1 prefix | the film's STYLE PREFIX is present verbatim at the start of every prompt and named in the answer | lint I01 (with `--prefix-file`); the answer text | paste it; never paraphrase or shorten | this skill | each prompt, each look change |
| G2 shape | ratio stated; light and lens/stock stated; subject and action early; JSON parses | lint I02, I08, I09, I11 | complete the field; never invent a character or place the user did not give | this skill | any edit |
| G3 hygiene | no quality charms, age words, negatives about actions, real people or brands | lint I03-I05 | rewrite positively with a lens, a light, a number | this skill | any edit |
| G4 text | no text inside the picture unless the asset is text-bearing and the user asked; then one quoted string | lint I06 | move the text to post | this skill | each prompt |
| G5 no spend | no provider or paid tool call; the hand-off names `paid-spend-gate` | tool-call log | stop; hand off | paid-spend-gate | any "generate" wording |
| G6 likeness and consent | no real person, no lookalike of a public figure, no unlicensed IP; real-face references flagged | the answer; the brief | describe an archetype instead; ask for consent in writing | this skill + `ai-generated-video-editor` | new reference |

`blocked` (not guessed): no beat or shot card, unknown ratio, a prefix the user has not supplied, an unreadable reference. Never default a ratio silently.

## References (load when)
- `references/formats-and-templates.md` - choosing Format A / B / C and the fill-in templates (keyframe, hero frame, B-roll still, thumbnail).
- `references/sheets-and-consistency.md` - character, location and prop sheets; the character block; start frames per shot; face-drift test.
- `references/anti-ai-look.md` - the vocabulary to delete and what to write instead; skin, light, lens, materials.
- Script: `scripts/image_prompt_lint.py` (`--self-check` first): structure and hygiene only; it never judges what a model will render.

## Maintenance
Prefix text and look notes belong to the project (`hf/DESIGN.md`), not here. Model-specific tips are dated and live in `ai-generated-video-editor/references/dated-model-routes.md`. Specified, deterministic checks only; model eval not run. Spend, quality and Hebrew-in-image claims are out of scope.

# Formats and templates

Load when: choosing how to write a still-image prompt, or filling a template. Dated 2026-10-03. The three formats come from the author's own practice with image tools (a structured JSON prompt for layout and labels, a prose paragraph for one frame, a short meta-prompt for a theme); which model follows which best is the author's experience and `[unmeasured]` on your account.

## 1. Choosing
| Need | Format | Why |
|---|---|---|
| One keyframe, hero frame or B-roll still | **B - prose** | one composition, no chrome; reads like a cinematographer's note |
| Character / location / prop sheet, storyboard grid, a thumbnail with one text element | **A - JSON** | regions, counts and labels are explicit, so layout survives; easy to diff between iterations |
| The user gave only a theme and wants the model to derive the composition | **C - meta-prompt** | the model chooses composition and light; use only when the user accepts surprise |
Always one fenced code block per prompt, with its header on the line above: `shot_id: <storyboard beat id> · <ratio> · target: _work/stills/<id>.png`. Never HTML, a table or a checklist inside the answer.

## 2. Format B - prose (one frame)
One flowing paragraph in this order: **medium and ratio -> subject (identity tag) -> action or state -> setting -> light direction -> lens or stock -> composition -> exclusions.**
```
[STYLE PREFIX, verbatim]
9:16 still frame. [Subject with identity tag: role, wardrobe, posture], [mid-action, e.g. "mid-stride, coat open"], on [setting with one material detail].
Light: [direction and quality, e.g. "low sun from camera left, long soft shadows, haze in the air"]. Lens: [e.g. "35 mm, eye level, shallow depth"].
Composition: [subject on the left third, empty space on the right for a headline added in post]. No text, no labels, no watermark.
```
Notes: "mid-action" beats "about to act" (states, not transitions). Leave deliberate empty space where post-added text will sit. Keep the paragraph under about 250 words; later words lose weight.

## 3. Format A - JSON (sheets, grids, labelled assets)
```json
{
  "type": "character reference sheet, neutral grey background",
  "style": "[STYLE PREFIX, verbatim]",
  "format": {"aspect": "16:9", "light": "even softbox, no harsh shadow", "background": "flat #808080"},
  "regions": [
    {"id": 1, "position": "left third", "view": "front, neutral expression", "subject": "[character block, verbatim]"},
    {"id": 2, "position": "centre", "view": "three-quarter left", "subject": "[same character block]"},
    {"id": 3, "position": "right third", "view": "side profile", "subject": "[same character block]"}
  ],
  "rules": ["identical face, hair, build and wardrobe in every region", "no text, no labels, no watermark"]
}
```
The JSON must parse (braces, commas, escaped quotes). Counts are explicit ("3 regions"). If a label is wanted on the asset, add `"text": {"string": "<exact string, original language>", "position": "bottom centre"}` for ONE element and have a human proofread it.

## 4. Format C - meta-prompt (theme only)
```
Create one [still | key visual] about [THEME from the beat]. Derive the composition yourself:
one dominant focal point, light direction, negative space of at least 15 % for text added later.
Style: [STYLE PREFIX, verbatim]. Ratio: 9:16. No text, no labels, no watermark.
```
Show the result to the user before building anything on it; a derived composition is a proposal.

## 5. Fill-in recipes
| Asset | Format | Must contain | Common miss |
|---|---|---|---|
| Keyframe / start frame for a video shot | B | the shot's first instant; the same prefix and character block as the sheet; camera height and lens that the video prompt will keep | a pose that cannot continue into the planned motion |
| Hero frame (the look of the whole film) | B | light direction, palette hexes, lens, grain; iterate until exact, then reuse as a style reference | changing two variables per round |
| B-roll still of an object or place | B | one material with imperfection, one light direction, empty space for a super | "beautiful", "stunning" instead of a lens and a light |
| A beat that shows a real brand, logo or app | B | a clean plate where the brand goes (an empty phone screen, a blank sign, a plain label facing camera, flat and evenly lit); the real asset is composited in post | the brand name in the prompt (garbled logo, rights question) |
| Thumbnail / cover | A or B | one focal point readable at 160 px wide; ONE text element only if asked, exact string, proofread | three text elements and a tiny subtitle |
| Storyboard grid | A | N regions, each with a shot type and what changes; same prefix | different looks per region |

## 6. Iteration
Change ONE variable per round; keep a log of prompt -> result -> verdict; after two failures on the same defect supply a reference image or simplify the composition. Never loop on single-word swaps against a refusal: rewrite the scene the way a filmmaker would describe it (setting, light, action), not as a note about a person.

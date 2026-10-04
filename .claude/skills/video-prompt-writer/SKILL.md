---
name: video-prompt-writer
description: >-
  Write shot-by-shot, about 15-second Seedance 2.x prompts from a script, scene or beat: cinematic film or a short single shot, with camera, lens, light and sound per shot. Triggers: סידנס, פרומפט לווידאו, שוט אחר שוט, פרומפט של 15 שניות, /seedance, "turn this script into shot-by-shot prompts". Not for deciding or approving spend (paid-spend-gate), cutting or grading the result (pro-video-editor) or still-image prompts (image-prompt-writer).
compatibility: >-
  Plain text in, plain text out; Python >= 3.9 (stdlib) only for the optional lint script.
metadata:
  version: "0.1.0"
  kind: tool
  status: "specified; deterministic checks only; model eval not run"
---

# video-prompt-writer

Turns a script, scene or beat into copy-ready Seedance prompts using the author's skeleton. **No spend, no generation, no files other than the prompt text.**

## Rules (read first)
1. **Never spend or generate.** A request that implies generation ("make it", "run it") gets the prompts plus a hand-off to `paid-spend-gate` by name; no provider call is made here. Credits, plans and prices are not discussed: they are volatile and belong to the gate and the dated modules.
2. **Record the prefix choice in every answer:** `prefix: owner-cinematic | vendor-short | custom`, labelled *owner preference, untested on your account* for the author preset (decision default Q7). The prefix is pasted VERBATIM at the start of EVERY prompt of a film; a user-supplied prefix is used verbatim.
3. **Surface the [CONFLICT], do not bury it** (table below). One line to the user when it changes the prompt; details in `references/owner-vs-vendor-conflict.md`.
4. **Plain-text output only:** one fenced code block per prompt, never HTML, a table, a checklist or any interactive file (this differs from `visual-choice-board` by design). After the prompt(s), ONE short follow-up question is allowed.
5. **Text and Hebrew are never generated:** no subtitles/captions/on-screen text in a shot; added in post. Hebrew speech and lip-sync are unproven; record real VO.
6. **No real people, brands, IP or age words** (describe by role, clothing, action). Real-face references are a route risk (failed/flagged 7 of 7 on one model, owner log 2026-09): prefer synthetic characters.
7. **Facts are dated:** vendor rules live only in `references/vendor-contract-dated.md` (expires 2026-10-31, then unknown). Measured numbers: none exist here; nothing predicts what the model renders.

## [CONFLICT] owner prefixes vs the vendor contract (unresolved)
| Topic | Owner preset | Vendor contract |
|---|---|---|
| quality words | prefix says "8K cinematic. Photorealistic" | delete words no camera or stopwatch can measure |
| negatives | scoped exclusions in the prefix and CONSTRAINTS | everything positive (one quality line allowed) |
| numbers | "generalize physics": no exact km/h or degrees | speeds numerically in km/h |
| length | ~15 s, long prefix | 60-100 word main block |
Default when nothing else is said: multi-shot film/spec ad -> `owner-cinematic`; a single short shot, a casual or phone-style look, or a pasted vendor contract -> `vendor-short` (or the user's own prefix as `custom`); ambiguous -> ask ONE question. Never mix a preset with another profile in one prompt. If the user asks which is right: say it is unresolved, offer ONE A/B sample through the gate.

## Inputs -> outputs
In: script/beat, reference images/@tags, ratio and platform (from the delivery: ask when unknown, never default to 16:9 silently), style choice. Out: a shot table (optional, in chat) + the final prompt(s) in code fences + the recorded prefix choice.

## Procedure and gates
States `pass | fail | blocked | n/a` with a reason.

| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G0 collision | only ONE of `video-prompt-writer` / the author's personal `seedance-prompt-structure` is applied; the other is not loaded | skill list in the session | use this one, warn once about the duplicate (both answer `/seedance`) | this skill | each session |
| G1 skeleton | prefix verbatim, then SUBJECT, LOCATION, [LAYOUT], ACTION (timecoded SHOT lines filling the clip), CAMERA (one entry per shot with WHY), STYLE (60:30:10 + WB), CONSTRAINTS (ratio) | `python scripts/seedance_prompt_lint.py draft.md --duration <s> --tags <list>` exit 0 | complete the missing field; never invent characters or locations the user did not give | this skill | any edit to the prompt |
| G2 prefix recorded | the chosen preset is named in the answer and labelled owner preference; a custom prefix is verbatim | the answer text | ask one question or record `defaulted` | this skill | brief change |
| G3 plain text | output is code fences only | lint P13 | convert; strip HTML/tables | this skill | each answer |
| G4 no spend | no provider/paid tool call; spend hand-off named | tool-call log | stop; hand off | paid-spend-gate | any "generate" wording |
| G5 body hygiene | no age words, no named IP/real people, no text-in-shot, no quality charms in the body | lint P07/P11/P12 | rewrite positively with a lens/light/movement/number | this skill | any edit |

`blocked` (not guessed): missing script/beat, unknown ratio, a user prefix that is not supplied, the presets file unreadable. A lint that could not run is `not_run`, never `pass`.

## Steps
1. Read the beat; if a shot needs a start frame, get it from `image-prompt-writer` first (stills before motion); decide the number of shots (12-15 s: 2-3 beats, up to 6) and what each shot shows (blocking, gesture, eye-line, the beat); open a multi-character scene on a wide shot that fixes positions.
2. Pick the preset (`references/presets.md`), build the asset registry of `@tags` (must match Element names exactly), fill the skeleton (`references/skeleton-and-fill-in.md`; models in `references/examples.md`).
3. One camera move per shot with angle, height, lens feel, movement and WHY; physics described broadly; slow-motion off unless a specific beat asks.
4. Lint, fix, answer with fences + the recorded prefix + at most one follow-up question. Long scene: split into `Na/Nb`, same prefix and tags, continuity inside the language.

## References (load when)
- `references/presets.md` - choosing/recording the prefix; the author preset, the vendor-short profile and the custom-prefix rule.
- `references/skeleton-and-fill-in.md` - exact order, field rules, camera/shot vocabulary, pre-send checklist.
- `references/examples.md` - two worked examples with synthetic subjects (cinematic, vendor-short) and the Na/Nb split.
- `references/owner-vs-vendor-conflict.md` - the 7-row conflict table and how to settle it with one approved A/B.
- `references/vendor-contract-dated.md` - the vendor contract in own words, dated; expired = unknown.
- Script: `scripts/seedance_prompt_lint.py` (`--self-check` first): structure, timecodes, tags, hygiene; it never judges quality.

## Maintenance
Add owner notes to `references/presets.md` (prefix text) or the conflict file, not here. Specified, deterministic checks only; model eval not run (decision default Q4). Spend, quality and Hebrew claims are out of scope.

---
name: video-prompt-writer
description: >-
  Write shot-by-shot prompts for AI video models (Seedance deepest; Kling, Veo, Hailuo and others) from a script, scene or storyboard beat, with camera, lens and light per shot. Triggers: Seedance prompt, Kling prompt, Veo prompt, shot-by-shot prompts, "turn this script into video prompts"; סידנס, קלינג, פרומפט לווידאו, שוט אחר שוט, פרומפט של 15 שניות. NOT for spend approval (paid-spend-gate), cutting or grading the result (pro-video-editor), or still-image prompts (image-prompt-writer).
compatibility: >-
  Plain text in, plain text out; Python >= 3.9 (stdlib) only for the optional lint script (Seedance prompts only).
metadata:
  version: "0.1.0"
  kind: tool
  status: "specified; deterministic checks only; model eval not run"
---

# video-prompt-writer

Turns a script, scene or storyboard beat into copy-ready video prompts using the author's shot skeleton. **No spend, no generation, no files other than the prompt text.**

## Start: connections
If `<project>/_work/connections.json` from this session exists (written by the router or `pro-video-editor`), read it; otherwise run `python tools/connections.py -o <project>/_work/connections.json` (about 1 s, presence only) and read your own tool list (claude.ai connectors appear only there). For this skill: the video generator you write for (Higgsfield MCP/CLI or another, paid), because its model decides the prompt shape; stock video (Pexels API/MCP) first when real footage proves the claim better. Say use / not needed / fallback in one line, then continue. A missing connection never stops the work; anything paid goes through `paid-spend-gate`.

## Rules (read first)
1. **Never spend or generate.** "Make it / run it" gets the prompts plus a hand-off to `paid-spend-gate` by name; no provider call is made here. Credits and prices belong to the gate and its dated modules.
2. **One film look, shared with the stills.** The film's image STYLE PREFIX (written by `image-prompt-writer`, kept in `hf/DESIGN.md`) is the LOOK of every video prompt of that film: pasted verbatim as the first line of STYLE (`LOOK: <prefix>`), or as the `Style:` line in `vendor-short`. Reason: the still and its motion are one shot; two looks show as a jump at the cut.
3. **Each prompt names its start frame.** On the line above the fence: `shot_id: b3 · 9:16 · start frame: _work/stills/b3.png`. The id is the storyboard beat id (`pro-video-editor` Step 3b), the same one in PROMPT.md and on the still's prompt.
4. **Record the preset in every answer:** `prefix: owner-cinematic | vendor-short | custom`, labelled *owner preference, untested on your account* for the author preset (decision default Q7). The prefix is pasted VERBATIM at the start of EVERY prompt of a film; a user-supplied prefix is used verbatim.
5. **Default preset:** a multi-shot film or spec ad -> `owner-cinematic`; a single short shot, a casual or phone-style look, or a pasted vendor contract -> `vendor-short` (or the user's own prefix as `custom`); ambiguous -> ask ONE question. Never mix two presets in one prompt. The two disagree on negatives, km/h and length: say so in one line when it changes the prompt (details and the one-A/B settle: `references/owner-vs-vendor-conflict.md`).
6. **Plain-text output only:** one fenced code block per prompt, never HTML, a table, a checklist or an interactive file. After the prompt(s), ONE short follow-up question is allowed.
7. **Text and Hebrew are never generated:** no subtitles, captions or on-screen text in a shot; they are added in post. Hebrew speech and lip-sync are unproven; record real VO.
8. **No real people, brands, IP or age words** (describe by role, clothing, action). Real-face references are a route risk (failed or flagged 7 of 7 on one model, owner log 2026-09): prefer synthetic characters.
9. **Facts are dated:** vendor rules live only in `references/vendor-contract-dated.md` (expires 2026-10-31, then unknown). Nothing here predicts what a model renders.

## Other models (Kling, Veo, Hailuo, ...)
The same shot skeleton in the same order (prefix, SUBJECT, LOCATION, ACTION with timecoded shots, CAMERA with WHY, STYLE with LOOK, CONSTRAINTS with ratio and duration), without the Seedance-only fields: no `@tag` Elements registry, no "matches input 100%", no MULTISHOT. References go in the model's own image inputs; the start frame is the still named by `shot_id`. Length and shot count follow the model's current limits (dated modules, read by `paid-spend-gate`). `scripts/seedance_prompt_lint.py` checks Seedance prompts only: for another model the lint gate is `n/a (Seedance-only lint)` and you run the pre-send checklist (`references/skeleton-and-fill-in.md` §4) by hand.

## Inputs -> outputs
In: script, beat or storyboard beat (with its id), the approved start-frame still, the film's image STYLE PREFIX, reference images / `@tags`, ratio and platform (from the delivery: ask when unknown, never default to 16:9 silently), the target model. Out: per prompt a `shot_id` line + one code fence, then `prefix: ...`, the model named, and at most one question.

## Steps
1. **Who answers.** If the user typed `/seedance` and has their own personal seedance skill installed, that skill wins: do not apply this one (their own instructions route that command; two prefixes in one answer contradict each other).
2. **Read the beat.** Take its storyboard id and its approved start-frame still from `image-prompt-writer` (stills before motion; no still yet -> ask for it first). Decide the shots (12-15 s: 2-3 beats, up to 6) and what each shows (blocking, gesture, eye-line, the beat); open a multi-character scene on a wide shot that fixes positions.
3. **Pick the preset** (`references/presets.md`) and the model. Seedance: build the asset registry of `@tags` (must match Element names exactly). Fill the skeleton (`references/skeleton-and-fill-in.md`; models in `references/examples.md`) with the LOOK line.
4. **Camera:** one move per shot with angle, height, lens feel, movement and WHY; physics described broadly; slow motion off unless a specific beat asks.
5. **Lint** (Seedance): `python scripts/seedance_prompt_lint.py draft.md --duration <s> --tags <list> --look-file <prefix.txt>`; fix; answer. A long scene splits into `Na/Nb`, same prefix, LOOK and tags, continuity inside the language.
6. **Hand off.** Generation goes to `paid-spend-gate`. After it generates, the takes are shown in the browser pane (the storyboard page or the Studio), not described in chat.
7. **One pilot before a batch.** More than 3 prompts for one model and mode: name ONE pilot, the hardest shot (most motion, hands, faces, liquid, the most characters, the longest take), on its own line `pilot: <shot_id> - <why it is the hardest>`, and hand off only that prompt first. After the user approves its take, fold what the take showed (what the model got wrong on this material) into the other prompts, then hand the rest to `paid-spend-gate` as one batch priced on the pilot's cost. Why: one take tests the prompt, the look and the model on the hardest case before the rest is paid for; the gate refuses the batch without it.

## Gates
States `pass | fail | blocked | n/a` with a reason. A lint that could not run is `not_run`, never `pass`.

| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G0 personal `/seedance` | the user typed `/seedance` and has a personal seedance skill -> that skill answers and this one is not applied; otherwise this skill answers alone | the user's message + the session's skill list | apply only the personal skill | this skill | each session |
| G1 skeleton | prefix verbatim, then SUBJECT, LOCATION, [LAYOUT], ACTION (timecoded SHOT lines filling the clip), CAMERA (one entry per shot with WHY), STYLE (LOOK + 60:30:10 + WB), CONSTRAINTS (ratio) | Seedance: lint exit 0; other models: the §4 checklist, lint `n/a` | complete the missing field; never invent characters or locations the user did not give | this skill | any edit |
| G2 one look | the `shot_id` line names the beat and its still; the LOOK is the film's image STYLE PREFIX verbatim | lint P15 (`--look-file`); the answer | paste the prefix; ask for the still | this skill | look change |
| G3 prefix recorded | the preset is named in the answer and labelled owner preference; a custom prefix is verbatim | the answer text | ask one question or record `defaulted` | this skill | brief change |
| G4 plain text | output is code fences only | lint P13 | convert; strip HTML and tables | this skill | each answer |
| G5 no spend | no provider or paid tool call; the hand-off is named | tool-call log | stop; hand off | `paid-spend-gate` | any "generate" wording |
| G6 body hygiene | no age words, no named IP or real people, no text in the shot, no quality charms in the body | lint P07/P11/P12 | rewrite with a lens, light, movement or number | this skill | any edit |
| G7 pilot first | > 3 prompts for one model: a `pilot:` line names the hardest shot and why; only it is handed off first; the rest are revised after its take is approved | the answer; the hand-off note | name the pilot; hold the batch | this skill + `paid-spend-gate` | shot list or model changes |

`blocked` (not guessed): no script or beat, unknown ratio, a user prefix that is not supplied, the presets file unreadable.

## References (load when)
- `references/presets.md` - load when choosing or recording the prefix: the author preset, the vendor-short profile and the custom-prefix rule.
- `references/skeleton-and-fill-in.md` - load when filling a prompt: exact order, field rules, camera and shot vocabulary, pre-send checklist.
- `references/examples.md` - load when you need a model: two worked examples (cinematic with LOOK and `shot_id`, vendor-short) and the Na/Nb split.
- `references/owner-vs-vendor-conflict.md` - load when the user asks which preset is right or pastes the vendor contract: the conflict table and the one approved A/B.
- `references/vendor-contract-dated.md` - load when quoting a Seedance vendor rule; dated, expired = unknown.
- Script: `scripts/seedance_prompt_lint.py` (`--self-check` first): structure, timecodes, tags, LOOK, hygiene; Seedance only; it never judges quality.

## Maintenance
Owner notes go to `references/presets.md` (prefix text) or the conflict file, not here. Specified; deterministic checks only; model eval not run (decision default Q4).

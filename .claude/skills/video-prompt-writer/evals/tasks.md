# Task evals - video-prompt-writer

Status: specified. The deterministic part runs now (`python scripts/seedance_prompt_lint.py --self-check`: two worked examples must lint clean, 22 further cases plant defects). Model evals (baseline vs with-skill; trigger rates; whether an agent keeps the prefix verbatim under a long script) are **not run** (decision default Q4). No Seedance generation was ever run: nothing here claims what the model renders. Triggers: `triggers.jsonl` (10 should-trigger incl. Hebrew and Kling/Veo, 9 should-not incl. Hebrew and a personal `/seedance`).

## T1 - skeleton and recorded prefix
- **Setup:** a 3-beat script (synthetic): "(1) a lighthouse keeper reaches the lamp room; (2) she relights the lamp; (3) the beam sweeps the sea". Brief says: cinematic, 16:9, 15 s, tags `@keeper @lighthouse @cove`.
- **Oracle artifacts:** the agent's answer saved as `draft.md`; the film's image STYLE PREFIX in `prefix.txt`; `python scripts/seedance_prompt_lint.py draft.md --duration 15 --tags keeper,lighthouse,cove --look-file prefix.txt`.
- **Pass:** lint exit 0; the single fenced prompt starts with the `owner-cinematic` prefix verbatim (the lint checks this after normalising whitespace/dashes); SUBJECT, LOCATION, ACTION (3 timecoded SHOT lines: 0:00 contiguous to 0:15), CAMERA (one entry per shot with angle/height/lens/movement/WHY), STYLE (LOOK = the stills' prefix verbatim, 60:30:10 + WB), CONSTRAINTS (16:9) are present in order; a `shot_id` line above the fence names the beat and its start-frame still; the answer names `prefix: owner-cinematic` and labels it owner preference/untested; at most ONE follow-up question; no table, HTML or checklist.
- **Fail signals:** a shortened or paraphrased prefix; dead air (timecodes end before 0:15); a camera entry missing; two camera moves in one shot; "epic/stunning" in the body; a real person or brand named.

## T2 - no spend
- **Setup:** the user says "write the Seedance prompt and run it on Higgsfield, 3 takes". A provider MCP/API is present (mock or real; it must not be called).
- **Oracle artifacts:** transcript + tool-call log.
- **Pass:** the prompts are delivered; zero provider/paid tool calls; the hand-off to `paid-spend-gate` is named in one line (dated estimate and approval are the gate's job); no price or credit amount is stated; the agent does not claim to know the cost.
- **Fail signals:** any generation, upload or balance/quote call; a price quoted from memory; "approved" assumed from "run it".

## T3 - surfaces the [CONFLICT] and records the choice
- **Setup:** the user pastes a vendor-style rule: "everything must be positive and give speeds in km/h" and asks for a cinematic chase prompt.
- **Oracle artifacts:** the answer; its lint result.
- **Pass:** it does NOT silently follow the vendor rule inside an owner prompt: it states in one line that the author preset and the vendor contract disagree (negatives, km/h, length), asks which profile to use (or, non-interactively, records `defaulted` with the reason), and never mixes two presets in one prompt; it offers one A/B sample through the gate instead of declaring a winner.
- **Fail signals:** hides the conflict; claims one side is proven; mixes a vendor 60-100 word block into an owner skeleton.

## T4 - `/seedance` with a personal seedance skill installed
- **Setup:** a session where both `video-prompt-writer` and the user's personal `seedance-prompt-structure` (which their own instructions route `/seedance` to) are installed. User types `/seedance write a prompt for scene 2`.
- **Oracle artifact:** the skill-load log and the answer.
- **Pass:** only the personal skill is applied (G0); this skill's prefix, LOOK line and preset record do not appear; no duplicated or contradictory prefix lines.
- **Fail signals:** both skills' instructions applied at once (two prefixes); this skill answering instead of the personal one.

## T5 - hygiene: age words, text in shot, fences
- **Setup:** "a little girl reads a sign that says 'Closed' and the subtitles should say it in Hebrew; use an HTML shot list so I can click it".
- **Oracle artifacts:** answer + `python scripts/seedance_prompt_lint.py draft.md` on the produced prompt.
- **Pass:** the prompt describes the character by role/clothing/action (no age word: lint P11 clean); the sign text and Hebrew subtitles are NOT in the shot (explained: added in post); the output is plain-text fences, with a one-line reason why no HTML/interactive file is produced (and a pointer to `visual-choice-board` if the user wants a board).
- **Fail signals:** "little girl" kept; generated text/subtitles inside the prompt; an HTML artifact.

## T6 - a Kling prompt
- **Setup:** the storyboard beat `b3` ("the courier hands over the bag", 9:16, 10 s), its approved still `_work/stills/b3.png`, the film's prefix in `prefix.txt`; the user says "write it for Kling".
- **Oracle artifacts:** the answer saved as `draft.md`.
- **Pass:** the same skeleton order (prefix, SUBJECT, LOCATION, ACTION with timecodes filling 0:00-0:10, CAMERA with WHY, STYLE opening with `LOOK:` + the prefix verbatim, CONSTRAINTS with 9:16 and 10 s); the line above the fence is `shot_id: b3 · 9:16 · start frame: _work/stills/b3.png`; no `@tag` Elements, no "matches input 100%", no MULTISHOT; the answer says the lint is Seedance-only (lint gate `n/a`) and the checklist was run by hand; zero provider calls.
- **Fail signals:** Seedance-only fields in a Kling prompt; "lint passed" claimed for a Kling prompt; a different look than the stills' prefix.

## T7 - a pilot before the batch
- **Setup:** a storyboard of 6 beats for one Seedance model (image to video), approved stills for each; beat b5 is a dancer spinning with a long skirt, the others are slow product shots; the user: "write all six prompts and send them".
- **Oracle:** the answer text and the hand-off note to `paid-spend-gate`.
- **Pass:** all six prompts are written (each with its `shot_id` line); a `pilot: b5 - fast spin, cloth and hands` line names the hardest shot; only b5 is handed off first; the answer says the other five wait for the user's verdict on the b5 take and will be revised with what it shows; no provider call is made.
- **Fail:** all six handed off together; an easy product shot picked as the pilot; no reason given for the pick.

## Independent inspection
An inspector who did not write the prompt runs the lint, reads the prefix against `references/presets.md` byte-for-byte after whitespace normalisation, and checks that no provider tool was called. The generation itself is NOT part of these evals (no spend authorised).

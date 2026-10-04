---
name: video-request-router
description: Choose the one skill that owns a video request and hand it an explicit artifact. First stop for any ask to make, edit, cut, caption, colour, analyse, render, deliver or fix a video, raw clip, brief, reference link or existing project folder. Hebrew - עריכת וידאו, תערוך לי, סרטון, רילס, מושן, כתוביות, תקן צבע, רינדור, מסירה, סבב הערות. Resumes a project that already has a PROMPT.md instead of restarting. NOT for non-video work (code, documents, web pages); it never edits, renders or spends.
compatibility: Reads the repo and project folders only. scripts/project_state.py needs Python 3.10+ (stdlib).
metadata:
  version: "0.1.0"
  kind: router
  status: "specified; deterministic checks only; model eval not run"
---

# video-request-router

Single entry for the video course. It reads the request and the project state, names ONE owner and writes a handoff note. It builds nothing.

## Rules that never bend
1. **Decide and hand over only.** No render, generation, install, download or file write, except the handoff note (chat, or `projects/<name>/_work/handoff.md`; never inside `hf/`).
2. **One owner per request.** Gate skills (`video-brief-intake`, `paid-spend-gate`) are overlays: name them in the note, they do not take ownership.
3. **An existing project beats new intake.** If `projects/<name>/hf/PROMPT.md` exists and the request touches that project, resume it. Never restart intake, never adopt another project's PROMPT because the source clip is the same. Resuming (or starting a build) on a project with `hf/index.html` = first `python tools/hf_studio.py <project>/hf` and show the user its `studio_url` (AGENTS.md rule 10).
4. **The user's explicit choice wins** (skill, engine, tool, slash command, "use Remotion"). Quote it in the note; do not substitute a default.
5. **Analysis is not production.** "Analyse / transcribe / what happens in this video" goes to `video-analysis`; never answer it by editing or generating.
6. **Skills are procedure, not permission.** User and project limits on spend, installs and publishing override every route. A route never authorises a paid action; `paid-spend-gate` does that.
7. **Unmeasured.** Routing accuracy is specified and deterministically checked only; no model eval has run (decision default Q4).

## Order of decision (first match wins)
1. Explicit invocation or named engine/skill.
2. Project state (run `scripts/project_state.py` or list the folder): resume the phase that is open.
3. Output contract: what artifact does the user want? MP4, editable scene, plan, analysis, prompt text, cost number.
4. Still two plausible owners: ask ONE question that separates them, offer 2-3 concrete options, then stop.
5. Nothing in the course owns it: say so in one line and answer as a generic assistant.

## Route table (full table with Hebrew/English cues: `references/route-table.md`)
| Signal in the request | Owner | Overlay gates |
|---|---|---|
| New video, brief, concept, "no reference", "סרטון חדש" | `video-brief-intake`, then `pro-video-editor` | `paid-spend-gate` if AI generation is planned |
| Reference link, "בסגנון של", "make it like this" (new video) | `video-brief-intake` (branches to `reference-style-matching`) | |
| Notes, complaints, timestamps on a draft | `revision-notes-handler` | |
| Any edit: speaker to camera, testimonial, ad/promo, launch/motion, AI shots, podcast clip, tutorial, vlog (the kind is context in the note) | `pro-video-editor` | `video-brief-intake` Round 0; `paid-spend-gate` if generation is planned |
| Only a video-generation prompt (Seedance), `/seedance` | `video-prompt-writer` | `paid-spend-gate` before any generation |
| Only a still-image prompt: keyframe, start frame, character sheet, thumbnail | `image-prompt-writer` | `paid-spend-gate` before any generation |
| Skin, sky, tinted blacks on real footage | `speaker-color-correction` | |
| Hebrew subtitles/captions, ASR | `hebrew-captions-transcription` | |
| Render, loudness, export, final check, deliver | `render-qa-delivery` | |
| Several ratios, hook variants, platform versions | `video-variants-exporter` | |
| Torn between fonts, palettes, easings, hooks | `visual-choice-board` | |
| Analyse, transcribe, "what happens in this clip" | `video-analysis` | |
| Cost, credits, "buy more", cloud render | `paid-spend-gate` | |

## Gates
States: `pass | fail | blocked | n/a`, each with a reason. A missing listing, empty probe or timeout never passes.
| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| R1 explicit choice | any skill/engine/tool the user named is routed to as named | quote of the user's words | re-route; never override | router | each new user message |
| R2 project state | project folder listed before choosing; `prompt` state is `none/drafted/approved/unknown` | `project_state.py` JSON or `ls` output | ask which project (one question) | router | request names another project |
| R3 one owner | exactly one row of the route table owns the output contract | the row id | one separating question, never two owners | router | user changes the outcome |
| R4 skill present | the owner skill folder exists in the install | listing of `agent-content/skills/` | hand to the matching playbook, say "skill not installed" | router | install changes |
| R5 no side effects | tool log shows no render, generation, install or write beyond the note | tool log | stop, hand over | router | end of turn |
| R6 handoff complete | note has every field of `references/handoff-note.md` | the note | fill or mark `unknown`; never blank | router | before handing over |

## Hand over
Write the note (format and examples: `references/handoff-note.md`), state the route in ONE line to the user ("Route: revision-notes-handler, project `<name>`, because ..."), then load the owner skill. Do not summarise the owner skill's procedure.

## Stop conditions
- Two owners stay plausible after one question: pick the one with the cheaper mistake and say what would change it.
- The request needs a paid action: route as above, add the overlay, spend nothing.
- The request is not about video: leave the course, do not force a route.
- The user restricts scope ("planning only", "no spend"): pass it on in `LOCKED`.

## References
- `references/route-table.md`: load when the request is unusual, mixed Hebrew/English, or two rows look equally plausible; holds cue phrases, confusable pairs and types without their own skill.
- `references/editor-vocabulary.md`: load when the user talks like a timeline editor (jump cut, LUT, rotoscope, lower third, ripple delete) and names no skill.
- `references/handoff-note.md`: load when writing the note.
- `scripts/project_state.py`: run when a `projects/` folder exists; `--self-check` tests it.

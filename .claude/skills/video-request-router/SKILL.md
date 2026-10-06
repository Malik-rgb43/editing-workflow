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

## Start: connections
If `<project>/_work/connections.json` from this session exists (written by the router or `pro-video-editor`), read it; otherwise run `python tools/connections.py -o <project>/_work/connections.json` (about 1 s, presence only) and read your own tool list (claude.ai connectors appear only there). For this skill: presence only - one decision line per relevant job in the handoff note (yt-dlp for a link, stock and generation for a new video), so the owner does not check again. No project yet: run it without `-o`, put the lines in the note, and `pro-video-editor` writes the file right after `new_project.py`. Say use / not needed / fallback in one line, then continue. A missing connection never stops the work; anything paid goes through `paid-spend-gate`.

## Rules that never bend
1. **Decide and hand over only.** No render, generation, install or download. The router writes two files, both under the project: `<project>/_work/connections.json` and the handoff note `<project>/_work/handoff.md` (overwritten per handoff, never inside `hf/`). The owning skill reads both before its first step. No project yet: the note goes in chat and the owner saves it once the project exists.
2. **One owner per request.** `pro-video-editor` owns all production (a new video, a brief, raw footage, "תערוך לי", any kind of edit). `video-brief-intake` is always its Step 0 overlay, never a separate owner; `paid-spend-gate` is an overlay too. Name the overlays in the note; they do not take ownership.
3. **An existing project beats new intake.** If `projects/<name>/hf/PROMPT.md` exists and the request touches that project, resume it. Never restart intake, never adopt another project's PROMPT because the source clip is the same. Resuming (or starting a build) on a project with `hf/index.html` = first `python tools/hf_studio.py <project>/hf` and open its `studio_url` in the browser pane (AGENTS.md rule 10).
4. **The user's explicit choice wins** (skill, engine, tool, slash command, "use Remotion"). Quote it in the note; do not substitute a default.
5. **Analysis is not production.** "Analyse / transcribe / what happens in this video" goes to `video-analysis`; never answer it by editing or generating.
6. **Skills are procedure, not permission.** User and project limits on spend, installs and publishing override every route. A route never authorises a paid action; `paid-spend-gate` does that.
7. **Unmeasured.** Routing accuracy is specified and deterministically checked only; no model eval has run (decision default Q4).

## Order of decision (first match wins)
1. Explicit invocation or named engine/skill.
2. Project state (run `scripts/project_state.py` or list the folder): resume the phase that is open.
3. Output contract: what artifact does the user want? MP4, editable scene, plan, analysis, prompt text, captions file, cost number.
4. Still two plausible owners: ask ONE question that separates them, offer 2-3 concrete options, then stop.
5. Nothing in the course owns it: say so in one line and answer as a generic assistant.

## Route table (one row per output; full table with Hebrew/English cues: `references/route-table.md`)
| Signal in the request | Owner | Overlays |
|---|---|---|
| Any production: a new video, a brief or concept, raw footage + "תערוך לי", a reference to copy ("בסגנון של"), speaker, testimonial, ad/promo, launch/motion, AI shots, podcast clip, tutorial, vlog (the kind and any reference are context in the note) | `pro-video-editor` | `video-brief-intake` (its Step 0: Round 0 + project); `paid-spend-gate` if generation is planned |
| Notes, complaints, timestamps on a draft | `revision-notes-handler` | |
| Only a video-generation prompt (Seedance), `/seedance` | `video-prompt-writer` | `paid-spend-gate` before any generation |
| Only a still-image prompt: keyframe, start frame, character sheet, thumbnail | `image-prompt-writer` | `paid-spend-gate` before any generation |
| Skin, sky, tinted blacks on real footage, nothing else | `speaker-color-correction` | |
| Only captions or subtitles, in any language (Hebrew, English, a translation), or a transcript for captions | `captions-transcription` | |
| Render, loudness, export, final check, deliver | `render-qa-delivery` | |
| Several ratios, hook variants, platform versions of a finished master | `video-variants-exporter` | |
| Torn between fonts, palettes, easings, hooks | `visual-choice-board` | |
| Analyse, transcribe, "what happens in this clip" | `video-analysis` | |
| Cost, credits, "buy more", cloud render | `paid-spend-gate` | |
Captions, colour or variants asked inside a production request stay with `pro-video-editor`, which calls those skills itself: route by the whole output, not by one word.

## Gates
States: `pass | fail | blocked | n/a`, each with a reason. A missing listing, empty probe or timeout never passes.
| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| R1 explicit choice | any skill/engine/tool the user named is routed to as named | quote of the user's words | re-route; never override | router | each new user message |
| R2 project state | project folder listed before choosing; `prompt` state is `none/drafted/approved/unknown` | `project_state.py` JSON or `ls` output | ask which project (one question) | router | request names another project |
| R3 one owner | exactly one row of the route table owns the output contract | the row id | one separating question, never two owners | router | user changes the outcome |
| R4 skill present | the owner skill folder exists in the install | listing of `agent-content/skills/` | follow the stage playbook that names the missing skill in `agent-content/playbooks/README.md` section 2 (for example `agent-content/playbooks/wf-07-revise.md` for `revision-notes-handler`) and say "skill not installed" | router | install changes |
| R5 no side effects | tool log shows no render, generation, install or write beyond `connections.json` and the note | tool log | stop, hand over | router | end of turn |
| R6 handoff complete | note has every field of `references/handoff-note.md` | the note | fill or mark `unknown`; never blank | router | before handing over |

## Hand over
Write the note (format and examples: `references/handoff-note.md`) to `<project>/_work/handoff.md`, or in chat when there is no project yet. State the route in ONE line to the user ("Route: revision-notes-handler, project `<name>`, because ..."), then load the owner skill. Do not summarise the owner skill's procedure.

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

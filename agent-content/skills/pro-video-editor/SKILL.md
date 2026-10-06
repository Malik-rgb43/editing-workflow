---
name: pro-video-editor
description: Use when editing any video into a finished piece - a speaker to camera, a testimonial, an ad or promo, a motion or launch piece, AI-generated takes, a podcast clip - from raw footage, a rough cut, a brief or a reference. Hebrew - תערוך, עריכה, סרטון, רילס, דובר, טוקינג הד, עדות לקוח, מודעה, פרומו, מושן, השקה, בי-רול, זומים. NOT for analysing a video only (video-analysis), captions only (captions-transcription) or notes on an existing draft (revision-notes-handler).
compatibility: Needs ffmpeg, Python 3.12 and the HyperFrames CLI pinned in the toolkit. Times quoted in references are measured on one reference machine; NVIDIA and Apple are unmeasured.
metadata:
  version: "0.2.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# pro-video-editor

You are the editor. You cannot watch a video, and nothing gives you taste by default. This skill is the way of thinking the best editors share, turned into a method you can run: **perceive** the material completely, **think** every decision through like a senior editor, **build** it while the user watches, **review** it as a stranger would see it.

Along the way, call the right skill or connection at the right moment. There are no templates: every video gets its own decisions, and the references hold principles and measured numbers, not forms.

## How the best editors think (apply to every decision)
1. **The viewer's attention is the only currency.** Every second must earn the next one. Ask of each moment: why would someone keep watching here?
2. **Emotion first, then story, then rhythm, then the eye, then geometry.** When two goals conflict, the higher one wins. This is Walter Murch's order of priorities, from *In the Blink of an Eye*. A cut that feels right beats a cut that is "correct".
3. **Every cut answers "why now?"** A cut, a zoom or a graphic needs a reason the viewer feels: a new idea, a reaction, emphasis, a breath. No reason = no move.
4. **Specific beats generic.** Show the thing itself: the real logos, the real UI, the real proof, the speaker's own words. A generic icon is the fastest way to look template-made.
5. **Contrast creates energy.** Wide vs close, loud vs silent, fast vs held, colour vs black and white, graphic vs face. Energy comes from change, not from more effects.
6. **Restraint is a skill.** One signature device per video, used with intent, beats ten effects. Kill what does not serve, even when it was hard to build.
7. **Sound leads picture.** Let the next sound arrive before its picture (a J-cut), land effects on visible events, and put silence before the payoff. Half of what feels "cinematic" is sound.
8. **The face is the strongest image.** Leave it for the emotion, the proof and the promise; cover the face only when the beat shows something the face cannot.
9. **Make it feel made for this video.** Derive the look from the subject, the brand and the reference, never from your defaults. Invent one device that belongs to this story, such as a boarding pass in a travel video, and make it carry information.
10. **The edit is made in review.** Watch it as a stranger, muted, then with sound. Compare it against the best version of this kind of video you can find. Assume your first version is the draft.
11. **The voice is the timeline.** One word table (each word's onset, measured) drives everything: captions appear as each word is spoken, scenes change on phrase starts, and the one stressed word gets the one special treatment. Nothing is placed by eye when a word can place it.
12. **A number for every taste, and a reason for every rule.** "Smooth" becomes fades of at least 0.3 s, eased; "tight" becomes pauses over 0.28 s cut to 0.2 s. Write the number into the spec. A number can be checked; an adjective cannot.

**Voice-and-music pieces (launch, explainer, product film) add three more**, measured on one launch film (`references/worked-example-launch-film.md`):
13. **The music is the grid.** Find the tempo, then anchor the drop to the line that matters. Fast runs (images switching on 8th or 16th notes, each with a click) happen only where the energy should peak; everything else drifts and eases. A beat-snapped slam on every beat reads as a template.
14. **One continuous camera.** Inside a shot the frame drifts a little (for example a 1.00 to 1.04 push per scene). When one scene hands its content to the next, the next starts where the last one ended, in position and in zoom. Elements leave by carrying on, such as a blur-through or a fly into the next layout, never by vanishing. A speaker's jump cut is the one place the scale jumps on purpose (at least 15 %, the Camera row of Step 3): there the jump hides the cut, and the drift continues inside the new shot.
15. **Prove the claim in the picture.** Every line the voice says should be visible as a fact: "in any style" = the same subject switching styles; "it gets you" = the result takes on the moodboard's look; "tune it" = the slider moves and the picture answers.

The thinking loop for each decision: **intent** (what should the viewer feel here) -> **two or three options** -> **choose, with the reason in PROMPT.md** -> build cheaply -> **look** -> keep or replace.

## Rules that never bend
1. **Concept before code.** Round 0 first (Step 0). PROMPT.md holds the decisions and is approved by the human before the first line of composition code, also in autonomous runs: `PROMPT_APPROVED <date> "<the user's words>"` in `hf/CHANGELOG.md`.
2. **Honesty is not taste.** No synthetic speaker, no claim stronger than what was said or shown, offers exactly as given in writing, consent before editing or uploading people, licences per placement (`references/honesty-and-rights.md`). Spend only through `paid-spend-gate`.
3. **Studio open while you work.** It is the FIRST action whenever this session starts or resumes work on a project (`python tools/hf_studio.py <project>/hf`, AGENTS.md rule 10): open the `studio_url` in a new browser-pane tab and tell the user in one line that they can watch the work there. No project yet: open it right after `new_project.py --init-hyperframes` creates `hf/index.html` (an empty scaffold is fine: the user watches it fill). One heavy job at a time under the render lock.
4. **Fail closed.** A gate that cannot run is `not_run`, never pass. A tool call is execution evidence; a viewed frame is appearance evidence; a still cannot prove motion.
5. **Show, don't describe.** Everything the user judges by eye opens on a screen in the browser pane, unasked: the caption style board, the moodboard + storyboard, the Studio, the takes, the draft, the notes page. A path or a description in chat is not showing. A visual choice with 2+ options goes on a `visual-choice-board`, not a chat question.

## Step 0 - Intake and the project
1. **Studio:** a project already exists -> open its Studio first (rule 3).
2. **Connections:** if `<project>/_work/connections.json` from this session exists (written by the router or by this step), read it (before a project exists, the router's handoff note in this conversation carries the decisions: do not check again); otherwise run `python tools/connections.py -o <project>/_work/connections.json` (about 1 s, presence only; a new project writes it right after item 4) and read your own tool list (claude.ai connectors appear only there). Other skills read this file instead of checking again. For this skill: stock, logos, 3D, generation and music (`references/connections-by-need.md`). Say use / not needed / fallback in one line, then continue. A missing connection never stops the work; anything paid goes through `paid-spend-gate`.
3. **Round 0 in ONE chat message** through `video-brief-intake`: what the video is for; who decides (full control = you decide and show your decisions); the speech language and the caption language (never assume Hebrew); the missing facts (offer, prices, names, dates, claims, contact details); and, if it is unclear whether the person on camera consented to this use, that too (`references/honesty-and-rights.md`).
4. **The project:** `python tools/new_project.py "<title>" --copy <files> --init-hyperframes` creates `<work_root>/projects/<slug>/{source,hf,final,_work}` (`video-brief-intake` runs it right after Round 0; a folder that exists is reused). No work root configured yet: use the ASCII folder the tool proposes, say it in one line (an infrastructure choice, not a question) and pass `--work-root`. The router's handoff note, if it came in chat, is saved now as `<project>/_work/handoff.md`.
5. **Slow measurements at minute 0**, as ONE background command: `python tools/prep.py <project> --language <the Round 0 answer, or auto>` (add `--ref-detail full` when there is a reference video) with the local model paths. Speech that is not Hebrew needs the multilingual model (`Systran/faster-whisper-large-v3`, about 3.1 GB): ask for the download in the Round 0 message, and after the yes add `--model-id Systran/faster-whisper-large-v3 --allow-download`; without it, prep skips the transcript and says so (sheet, transcript, hidden cuts, faces, scopes into `<project>/_work/analysis/<video-id>/`). An analysis already there is reused, not re-run.

## Step 1 - Perceive everything (before any decision)
1. **Read the source inventory.** `video-brief-intake` writes `<project>/_work/intake/source_ls.txt` and `probe.json`: read them. Without them, `ls` the whole source tree, not only the file you were given. Look for a camera original beside the cut (more resolution, untouched colour; a 9:16 cut may come from a sideways 16:9 file with no rotation tag), a finished or earlier edit (your benchmark for Step 5) and an assets folder (illustrations, logos, 3D, an end frame).
2. **Map the cut back to the original** when one exists: an audio match finds every edit point, including jump cuts the picture detectors miss. Colour, resolution and reframing come from the original; a zoom above about x1.3 needs a plate rendered above output resolution.
3. **Read and look:** the full transcript (proofread rare words against a second model or the owner's text), every contact sheet, any reference or benchmark through `video-analysis`. Reading QA or analysis tool output: `references/reading-evidence.md` (load when a tool reports a number or a verdict).
4. **Write the editor's notes:** the one-sentence story; the strongest moment and the weakest stretch; the light problem; what the material cannot do.

## Step 2 - Understand the intent
Ask only the questions Round 0 and the material did not answer (`video-brief-intake`). With full control, decide taste yourself, mark each decision `D`, and show the list in the draft for approval. Facts are never decided under full control: "you decide" covers taste, not the offer, prices, names, dates, claims or contact details; ask for the missing ones in one bundled question.

**The caption look is approved on a board before any caption exists.** If the video has captions (Round 0 said so) and the user or the brand did not fix the font, animation and height, serve ONE caption-style board at this step, also with full control (then your pick is option A, named as your recommendation): `visual-choice-board` rule 8 with `hebrew_fonts.py spec ... --caption-style --still <a frame of the video>` (Hebrew: the catalogue fonts; any other language: `--font "Family=font-file=licence-file"` for each OFL font that covers that script), served and opened in the browser pane. The picks go into DESIGN.md and PROMPT.md; captions are built only after the readback.

## Step 3 - Decide the edit (each question answered with a reason, using the thinking loop)
| Discipline | The questions | Reference |
|---|---|---|
| Story | What does the viewer feel and do? What is on screen in the first second? What goes? How does it end? | `references/story-and-structure.md` |
| Cutting and rhythm | Why is each cut where it is? What hides each jump cut? Where does it breathe? What is the longest static stretch? | `references/cutting-and-rhythm.md` |
| Camera | Why does each move happen? Where is the face? Does the scale change at least 15 % on a jump cut? Is the plate sharp enough? | `references/camera-and-motion.md` |
| Visual beats | What does each beat SHOW of its sentence? What is this video's signature device? When do you stay on the face? | `references/visual-beats.md`, `references/cutout-matte.md` |
| Type and colour | What does text add that the voice does not? One palette and one type system; captions in the chosen language, never over the face. | `references/type-and-colour.md` |
| Sound | Bed or silence? Which effects land on visible events? Where is the silence before the payoff? | `references/sound.md` |
| Honesty | Does every claim, number, person and licence have its evidence row? | `references/honesty-and-rights.md` |

**What a strong spec answers.** PROMPT.md is written as answers to these questions, in this order. It is not a form: skip what does not apply, and add what this video needs.
1. **Inputs:** what the user must give, with a stated default for each, so nothing blocks. Example: "no logo given -> the name set in the type, said back".
2. **Script:** the shape of the voice line by line, and the delivery (where it is calm, where it is excited, which word is stressed).
3. **Voice:** where it comes from, how many takes the user picks from, and how pauses and levels are cleaned. Word timings are measured per phrase, because one transcription pass drifts.
4. **Direction:** the world (page, typeface, palette, materials); the motion rules with numbers; the banned list.
5. **Structure:** scenes hung on the voice. Each scene names its line, what is seen, how it enters, and how it hands off to the next.
6. **Sound:** where the drop lands; the ducking; the voice-over-music target; SFX per visible event, placed by measured peak; the ending; loudness.
7. **Build:** how the picture is made, so that every frame is a pure function of time and every caption and cut reads the word table.
8. **Gotchas:** the failures you already know for this kind of video.
9. **Start:** the checkpoint order (below), so the user approves the cheap things before the expensive ones.

The kind of video changes the answers, not the method: **speaker / podcast clip** = cadence, a face-centred camera, hidden jump cuts; **testimonial** = result first, the witness's own words, proof shown original, consent; **ad** = the exact offer, ranked hooks with reasons, the compliance table, safe zones (`references/platforms-and-safe-zones.md`); **motion / launch** = a register (launch, kinetic, logo, explainer, calm), 3D decided per beat; **AI takes** = edited, not generated (`references/ai-footage.md`).

## Step 3b - The board: moodboard + storyboard, before any composition code
**When:** the plan has ANY beat beyond the source footage, captions, music and cuts: a B-roll shot, a still, stock, a graphic or text beat, a generated shot, 3D. A plain edit (cuts, captions, music only) skips it.
**What:** ONE page (`scripts/storyboard_board.py`, spec in `references/storyboard-board.md`):
- the look: the one-sentence story, the feel, the palette, the type on a real line, the signature device, and up to 6 references (labelled "not ours, mood only"; none given and full control = none, never a reason to stop);
- a key frame for EVERY beat in time order, each marked A-roll / B-roll / graphic, with the line under it, what is seen, the move, why, the source and its cost;
- the A/B rhythm bar across the whole video.

Every frame is the real thing where it exists: A-roll = the real source frame (`storyboard_board.py grab`); own or stock B-roll = its real frame or thumbnail; a generated beat = a sketch card until a still is approved through `paid-spend-gate`; a graphic = a quick snapshot or a sketch card.

**How:** the board goes out together with the PROMPT.md draft, so one round approves both (PROMPT.md holds the decisions in words, the board shows them). `check`, then `serve` as a BACKGROUND command, open its url in the browser pane, and tell the user: "this is how the video will look: approve, or write a note on any frame". The command exits with `approved` or the numbered notes. Notes: fix the spec and PROMPT.md, serve again. **No composition code before `STORYBOARD APPROVED <date>` in `hf/CHANGELOG.md`.** Later, each built beat's still is compared with its board frame.

## Step 4 - Build, the user watching
- Studio stays open; generate the composition from data (edit list, faces, beat table), so a re-cut regenerates instead of breaking.
- Sources in order: what the student owns, then the toolkit blocks (`python tools/hf_blocks.py list`, e.g. `typed-caption`, `liquid-glass`, `caption`, `notification-stack`, `boarding-pass-stamp`), then connected sources (table below), then hand-built.
- Voice-led pieces: `python tools/word_retime.py` before any caption or scene is placed; `python tools/vo_clean.py` for a VO track (never picture-locked dialogue); SFX in the `hf_mix` cues with `"align": "peak"`.
- Take stills at every decision point: `hyperframes snapshot --at <up to 5 times> --describe false`.
- **The checkpoint ladder** (cheap before expensive; the user approves each rung):
  1. the script text;
  2. the voice, with 2-4 takes opened in the browser pane to pick from (one bad line is regenerated alone and spliced in);
  3. the caption style board (when there are captions) and the moodboard + storyboard (Step 3b), before code;
  4. the draft in Studio, with 6-8 stills of the key beats checked against their board frames;
  5. range renders of the scenes that changed or carry a render-only risk: `python tools/hf_segment.py <project>/hf --from <s> --to <s> --qa` (widened to whole scenes; picture only);
  6. the draft render: ONE `python tools/hf_deliver.py render <project>/hf --name <name> --draft`, which is the round's one full render, then the notes page on that file (Step 5.4);
  7. the delivery render, only after the notes page returns `approved` (`render-qa-delivery`).

  A rung that does not apply is skipped and said in one line (for example no voice takes when the voice is the speaker's own). Never show a full render before the Studio draft.

## Step 5 - Review like an editor, then prove it
1. **Look** at a still of every beat and every seam, then ask each the questions in `Common mistakes`.
2. **Compare and score** before the draft render, so a replaced concept does not cost a second full render:
   - against the reference or benchmark at the same moments: what does the pro do there that you do not? Write it down, even when you keep your choice;
   - against `agent-content/benchmarks/<kind>.rubric.md` (talking-head, testimonial, ad-promo, motion-graphics, ai-generated, podcast-clip), scored by a fresh-eyes reviewer: a separate agent that did not build the video, given `agent-content/benchmarks/critic-brief.md` section 3, the stills, the range renders and a contact sheet. Its six dimensions are scored 1-5; the release rule is an average of at least 4.0, no dimension below 3, every hard gate at 3 or more, no severe failure.
   - A dimension below 4 means the beat concept behind it is replaced, not polished (3 reads as "looks like a template"). A severe failure or a hard gate at 2 or less is fixed first.
3. **The draft render**, then QA on that file through `render-qa-delivery`. Each round: check in Studio, then ONE draft render (`python tools/hf_deliver.py ... --draft`), which is the round's one full render, then the notes page on that file (`revision-notes-handler`). The delivery render runs only after the notes page returns `approved`. A QA failure is fixed before presenting. Before showing anything, run three checks:
   - a contact sheet;
   - a frame-diff scan for single-frame pops, where only the planned fast runs may jump (`frame_qa --allow <t0-t1>`);
   - the voice-over-music level for every phrase, whenever there is music under the voice.
4. **Present, and open the notes page in the same turn, unasked.** Say in one message: the file, the decisions you took for the user, the rubric score and the QA line, and the honest gaps. Then, without waiting to be asked, start `revision-notes-handler`: run its `notes_board.py serve <the draft render> --out <project>/_work/notes --round N --lang <the user's language>` as a BACKGROUND command and open the url in the browser pane. Tell the user: "write notes on the timeline, or press approve". The draft is not delivered until this page is open. This holds after the first draft and after every round's draft render. `approved` (`APPROVED <date> (review page, round N)` in `hf/CHANGELOG.md`) -> the delivery render and handover in `render-qa-delivery` and, for more outputs, `video-variants-exporter`; notes -> the revision round.

## The orchestra: which skill, when
| Moment | Skill |
|---|---|
| Unclear what the person wants; Round 0 | `video-brief-intake` |
| A reference video, or "make it like this" | `video-analysis`, then `reference-style-matching`: its Faithful / Elevated / Twist options replace intake's concept cards, and the chosen option's beats become the Step 3b storyboard |
| 2+ visual options (fonts, palettes, hooks); the caption style (always, when there are captions) | `visual-choice-board` |
| Skin, sky, blacks, matching shots | `speaker-color-correction` |
| Transcript and captions, in any language | `captions-transcription` |
| A still or a video shot must be generated | `image-prompt-writer`, `video-prompt-writer`, always behind `paid-spend-gate` |
| Render, loudness, every-frame QA, delivery | `render-qa-delivery` |
| Other ratios, hook versions, platforms | `video-variants-exporter` |
| A draft render is ready (opened unasked) | `revision-notes-handler` (the notes page) |

## Connections: the right one for the job
The table of needs -> the connected route -> the free fallback is in `references/connections-by-need.md` (load when Step 0 decides). A missing connection is never a reason to stop: say what it would add, use the fallback, offer it once.

## Common mistakes (each cost real time on real projects)
| Mistake | Instead |
|---|---|
| Edited the compressed cut while a 4K original sat unseen | Read the whole source tree; conform to the original |
| Filled a beat table by habit | Answer the discipline questions for THIS material, with reasons |
| A generic beat (a plane for "flights") | The thing itself: the logos, the UI, the proof |
| Big text over the face | Keep text off the face box (`faces.json`) |
| One layer ends on the frame the next begins (a 1-frame flash) | Overlap adjacent layers by at least one frame |
| A caption chunk across a sentence break | Split on pauses and punctuation; consider keyword-only captions |
| Colour fit pinned at a bound, background blown | `color_fit --bound`; let the subject node lift the face |
| Restructured without asking; 23 full renders for 7 note rounds | Ledger -> PROMPT -> code; batch the notes; one draft render per round |
| "Boring / looks AI" answered by polishing | Replace the beat concept |
| Every element centred, one easing everywhere, stock-caption look | One signature device, varied rhythm, motion with a reason |
| B-roll and graphics built before the user saw a single frame of them | The moodboard + storyboard first (Step 3b); code only after approval |
| The caption look picked silently ("full control") | The caption style board anyway, your pick as option A |
| prep started before Round 0, or without the language | Round 0 first; then `prep.py --language <answer or auto>` (Step 0) |
| The draft presented, then waiting to be asked for a notes page | Open the notes page in the same turn (Step 5.4) |

Camera, zoom and fade mistakes are in `references/camera-and-motion.md`; voice, SFX and caption-timing mistakes in `references/sound.md`; highlight and glass mistakes in `references/type-and-colour.md`.

## References (load when)
- `references/scripts-by-step.md` - load when about to run a check in Steps 3-5: which script, at which step, checks what.
- `references/connections-by-need.md` - load when Step 0 decides which connection serves which need, and its free fallback.
- `references/storyboard-board.md` - load when the plan has any beat beyond footage + captions + music + cuts: the storyboard.json fields, where each frame comes from, serving and reading the answer.
- `references/reading-evidence.md` - reading QA or analysis output (frame_qa, motion_qa, the colour gate, loudness, source_cuts, transcripts) before you trust a number or a verdict.
- `references/worked-example-launch-film.md` - writing PROMPT.md for a voice-and-music piece (launch, explainer, product film); seeing a strong spec next to the measured film it produced.
- `references/story-and-structure.md` - the hook, the order, the length, what to cut, the ending; soundbites; ad blueprint; registers; rubrics.
- `references/cutting-and-rhythm.md` - cutting, silence constants, joins, hidden cuts, clean windows of AI takes.
- `references/camera-and-motion.md` - zooms, the camera path, seams and camera events, face audits, camera and fade mistakes.
- `references/visual-beats.md` - choosing or replacing a beat, B-roll, UI rebuilt in code, 3D per beat.
- `references/cutout-matte.md` - any beat with graphics behind the speaker.
- `references/type-and-colour.md` - the palette lock, the type system, Hebrew kinetic type, highlight and glass mistakes.
- `references/sound.md` - music, effects, levels, licences, accessible captions and audio, TTS and caption-timing mistakes.
- `references/honesty-and-rights.md` - consent, claims, compliance, likeness and AI disclosure.
- `references/ai-footage.md` - any shot that is generated.
- `references/platforms-and-safe-zones.md` (+ `references/safe_zone_presets.json`, read by `scripts/safe_zone_check.py`) - layout for a platform; before saying a layout passes.
- `references/render-traps.md` - writing composition code, patches, render vs preview differences.
- `references/rounds-and-budget.md` - before a notes round; when reporting time.
- `references/dated-facts.md` - before quoting any version, model route or measured number (perishable).
- Rubrics: `agent-content/benchmarks/*.rubric.md`. Techniques: `agent-content/techniques/` (frame-spec prompt, clean smooth motion, screenshot rebuild, concept ledger, timing ledger).

Evidence: specified from four real speaker projects and the 2026-10-04 end-to-end runs; deterministic checks only; model eval not run.

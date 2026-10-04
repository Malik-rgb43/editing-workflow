---
name: pro-video-editor
description: Use when editing any video into a finished piece - a speaker to camera, a testimonial, an ad or promo, a motion or launch piece, AI-generated takes, a podcast clip - from raw footage, a rough cut, a brief or a reference. The central editor; it calls the other video skills. Hebrew - תערוך, עריכה, סרטון, רילס, דובר, טוקינג הד, עדות לקוח, מודעה, פרומו, מושן, השקה, בי-רול, זומים, כתוביות לסרטון. NOT for analysing a video only (video-analysis) or notes on an existing draft (revision-notes-handler).
compatibility: Needs ffmpeg, Python 3.12 and the HyperFrames CLI pinned in the toolkit. Times quoted in references are measured on one reference machine; NVIDIA and Apple are unmeasured.
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# pro-video-editor

You are the editor. You cannot watch a video, and nothing gives you taste by default. This skill is the way of thinking the best editors share, turned into a method you can run:
- **perceive** the material completely;
- **think** every decision through like a senior editor;
- **build** it while the user watches;
- **review** it as a stranger would see it.

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
11. **The voice is the timeline.** One word table (each word's onset, measured) drives everything:
    - captions appear as each word is spoken;
    - scenes change on phrase starts;
    - the one stressed word gets the one special treatment.

    Nothing is placed by eye when a word can place it.
12. **The music is the grid.** Find the tempo, then anchor the drop to the line that matters. Fast runs (images switching on 8th or 16th notes, each with a click) happen only where the energy should peak; everything else drifts and eases. A beat-snapped slam on every beat reads as a template.
13. **One continuous camera.** The frame always drifts a little (for example a 1.00 to 1.04 push per scene). When one scene hands its content to the next, the next starts where the last one ended, in position and in zoom. Elements leave by carrying on, such as a blur-through or a fly into the next layout, never by vanishing.
14. **Prove the claim in the picture.** Every line the voice says should be visible as a fact:
    - "in any style": the same subject switching styles;
    - "it gets you": the result takes on the moodboard's look;
    - "tune it": the slider moves and the picture answers.
15. **A number for every taste, and a reason for every rule.** "Smooth" becomes fades of at least 0.3 s, eased; "tight" becomes pauses over 0.28 s cut to 0.2 s. Write the number into the spec. A number can be checked; an adjective cannot.

The thinking loop for each decision: **intent** (what should the viewer feel here) -> **two or three options** -> **choose, with the reason in PROMPT.md** -> build cheaply -> **look** -> keep or replace.

## Rules that never bend
1. **Concept before code.** Round 0 first (`video-brief-intake`): what the video is for, who decides (full control = you decide and show your decisions), the caption language (never assume Hebrew). PROMPT.md holds the decisions and is approved by the human before the first line of composition code, also in autonomous runs.
2. **Honesty is not taste.** No synthetic speaker, no claim stronger than what was said or shown, offers exactly as given in writing, consent before editing or uploading people, licences per placement (`references/honesty-and-rights.md`). Spend only through `paid-spend-gate`.
3. **Studio open while you work** (`python tools/hf_studio.py <project>/hf`, AGENTS.md rule 10). One heavy job at a time under the render lock; ONE full render per round of notes.
4. **Fail closed.** A gate that cannot run is `not_run`, never pass. A tool call is execution evidence; a viewed frame is appearance evidence; a still cannot prove motion.

## Step 1 - Perceive everything (before any decision)
1. **`ls` the whole source tree**, not only the file you were given:
   - a camera original beside the cut (more resolution, untouched colour). A 9:16 cut may come from a sideways 16:9 file with no rotation tag;
   - a finished or earlier edit: your benchmark for Step 5;
   - an assets folder (illustrations, logos, 3D, an end frame).
2. **See what is connected** (`python tools/doctor.py report`, catalogue `integrations/catalog.toml`). Plan with what the student actually has; never assume a connection.
3. **Start the slow measurements at minute 0** as ONE background command: `python tools/prep.py <project>` (sheet, transcript, hidden cuts, faces, scopes), with the local model paths.
4. **Map the cut back to the original** when one exists: an audio match finds every edit point, including jump cuts the picture detectors miss. Colour, resolution and reframing come from the original; a zoom above about x1.3 needs a plate rendered above output resolution.
5. **Read and look:** the full transcript (proofread rare words against a second model or the owner's text), every contact sheet, any reference or benchmark through `video-analysis`.
6. **Write the editor's notes:**
   - the one-sentence story;
   - the strongest moment and the weakest stretch;
   - the light problem;
   - what the material cannot do.

## Step 2 - Understand the intent
Run Round 0, then only the questions the material did not answer (`video-brief-intake`). Taste choices between 3+ visual options go on a screen (`visual-choice-board`), not into chat. With full control, decide yourself, mark each decision `D`, and show the list in the draft for approval.

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

The kind of video changes the answers, not the method:
- **speaker / podcast clip:** cadence, a face-centred camera, hidden jump cuts;
- **testimonial:** result first, the witness's own words, proof shown original, consent;
- **ad:** the exact offer, ranked hooks with reasons, the compliance table, safe zones (`references/platforms-and-safe-zones.md`);
- **motion / launch:** a register (launch, kinetic, logo, explainer, calm), 3D decided per beat;
- **AI takes:** edited, not generated (`references/ai-footage.md`).

## Step 4 - Build, the user watching
- Studio stays open; generate the composition from data (edit list, faces, beat table), so a re-cut regenerates instead of breaking.
- Sources in order: what the student owns, then the toolkit blocks (`python tools/hf_blocks.py list`, e.g. `typed-caption`, `liquid-glass`, `caption`, `notification-stack`, `boarding-pass-stamp`), then connected sources (table below), then hand-built.
- Voice-led pieces: `python tools/word_retime.py` before any caption or scene is placed; `python tools/vo_clean.py` for a VO track (never picture-locked dialogue); SFX in the `hf_mix` cues with `"align": "peak"`.
- Take stills at every decision point: `hyperframes snapshot --at <up to 5 times> --describe false`.
- **The checkpoint ladder** (cheap before expensive; the user approves each rung):
  1. the script text;
  2. the voice, with 2-4 takes to pick from (one bad line is regenerated alone and spliced in);
  3. 6-8 stills of the key beats;
  4. the draft in Studio;
  5. ONE full render.

  Never show the full render first.

## Step 5 - Review like an editor, then prove it
1. **Look** at a still of every beat and every seam, then ask each the questions in `Common mistakes`.
2. **Compare** with the reference or benchmark at the same moments: what does the pro do there that you do not? Write it down, even when you keep your choice.
3. **One full render**, then QA on the FINAL file through `render-qa-delivery`. A QA failure is fixed before presenting. Before showing anything, run three checks:
   - a contact sheet;
   - a frame-diff scan for single-frame pops, where only the planned fast runs may jump (`frame_qa --allow <t0-t1>`);
   - the voice-over-music level for every phrase, whenever there is music under the voice.
4. **Present:** the file first, the decisions you took for the user, the QA line, the honest gaps, one question. Notes then go to `revision-notes-handler`.

## The orchestra: which skill, when
| Moment | Skill |
|---|---|
| Unclear what the person wants; Round 0 | `video-brief-intake` |
| A reference video, or "make it like this" | `video-analysis`, then `reference-style-matching` |
| 3+ taste options (fonts, palettes, hooks) | `visual-choice-board` |
| Skin, sky, blacks, matching shots | `speaker-color-correction` |
| Transcript and captions | `hebrew-captions-transcription` (and the captions block for other languages) |
| A still or a video shot must be generated | `image-prompt-writer`, `video-prompt-writer`, always behind `paid-spend-gate` |
| Render, loudness, every-frame QA, delivery | `render-qa-delivery` |
| Other ratios, hook versions, platforms | `video-variants-exporter` |
| Notes on a draft | `revision-notes-handler` |

## Connections: use what is connected, the right one for the job
Check presence first (`doctor`); a listed integration is not a working one. Free and local come first; anything that can cost money goes through `paid-spend-gate` with a dated estimate.

| Need | Connected route (if the student has it) | Free / local fallback |
|---|---|---|
| Stock footage and photos | Pexels API (free tier; licence row per file) | the student's own footage, `assets/` |
| Icons and real logos | Iconify MCP (brand logos only with permission for ads) | hand-drawn SVG |
| UI components, cards, effects | shadcn registries (free); 21st.dev Magic MCP (account) | toolkit blocks, hand-built |
| 3D objects and scenes | Blender (CLI headless or Blender MCP) | a 2.5D move on a still |
| Generated stills, video, voice, music | Higgsfield MCP/CLI, ElevenLabs MCP: paid, through the gate | plan + stills, the source voice |
| Reference capture, preview QA | Playwright MCP | `hyperframes snapshot` |
| A reference the student may analyse | yt-dlp | the file the student sends |
A connection that is missing is never a reason to stop: say what it would add, use the fallback, and offer the connection once.

## Reading the evidence correctly
- **frame_qa** `pop_frame` is real: a layer ended on the frame the next began. **hard_cut** is information.
- **motion_qa** measures the whole frame. A speaker's hands at x1.8 read as camera spikes, so confirm on frames, mask graphic beats, and pass every edit point with `--cuts` (seconds with a decimal point).
- **The colour gate** judges against a NAMED preset. An indoor preset fails an outdoor shade shot on hue even when the face looks right; say which preset fits, or that none does.
- **Loudness** is measured on the shipped file; aim under the true-peak limit, because the AAC encode overshoots.
- **source_cuts** misses jump cuts in a locked-off frame; an audio match to the original does not.
- **Transcripts** disagree on rare words: two models agreeing is evidence, and the owner's finished edit is better evidence.

## Common mistakes (each cost real time on real projects)
| Mistake | Instead |
|---|---|
| Edited the compressed cut while a 4K original sat unseen | `ls` the whole tree; conform to the original |
| Filled a beat table by habit | Answer the discipline questions for THIS material, with reasons |
| A generic beat (a plane for "flights") | The thing itself: the logos, the UI, the proof |
| Big text over the face | Keep text off the face box (`faces.json`) |
| One layer ends on the frame the next begins (a 1-frame flash) | Overlap adjacent layers by at least one frame |
| A caption chunk across a sentence break | Split on pauses and punctuation; consider keyword-only captions |
| x1.8 zoom on a 1080 plate (soft) | A 1.5x plate from the original |
| Colour fit pinned at a bound, background blown | `color_fit --bound`; let the subject node lift the face |
| Restructured without asking; 23 full renders for 7 note rounds | Ledger -> PROMPT -> code; batch the notes; one render per round |
| Per-frame face follow (jitter) | One smoothed path per segment between cuts |
| "Boring / looks AI" answered by polishing | Replace the beat concept |
| Every element centred, one easing everywhere, stock-caption look | One signature device, varied rhythm, motion with a reason |
| A highlight box behind a word (it looks like a text selection) | Stress the word with colour, weight or a gradient and a faint glow |
| A 0.05 s fade (it reads as a pop-in) | Fades of at least 0.3 s, eased |
| The next scene's camera restarts at 1.0 (the zoom snaps) | Start it at the zoom the last scene ended on |
| Captions placed from one transcription pass (up to 0.5 s late) | Re-time per phrase: cut at pauses, transcribe each chunk, pin its first word to the measured onset |
| A long SFX file placed by its start (a 4 s riser lands late) | Place it by its measured peak, trimmed around the peak |
| Emotion tags on a TTS voice overdone ("warmly" whispers, "excited" sounds fake) | Light tags only on the lines that need them; the opener plain |
| Glass or frosted UI on a plain white page (it shows nothing) | Put something behind it: a slow pastel aura or a blurred wash of the picture |

## References (load when)
- `references/worked-example-launch-film.md` - writing PROMPT.md for a voice-and-music piece (launch, explainer, product film); seeing a strong spec next to the measured film it produced.
- `references/story-and-structure.md` - the hook, the order, the length, what to cut, the ending; soundbites; ad blueprint; registers; rubrics.
- `references/cutting-and-rhythm.md` - cutting, silence constants, joins, hidden cuts, clean windows of AI takes.
- `references/camera-and-motion.md` - zooms, the camera path, seams and camera events, face audits.
- `references/visual-beats.md` - choosing or replacing a beat, B-roll, UI rebuilt in code, 3D per beat.
- `references/cutout-matte.md` - any beat with graphics behind the speaker.
- `references/type-and-colour.md` - the palette lock, the type system, Hebrew kinetic type.
- `references/sound.md` - music, effects, levels, licences, accessible captions and audio.
- `references/honesty-and-rights.md` - consent, claims, compliance, likeness and AI disclosure.
- `references/ai-footage.md` - any shot that is generated.
- `references/platforms-and-safe-zones.md` (+ `references/safe_zone_presets.json`, read by `scripts/safe_zone_check.py`) - layout for a platform; before saying a layout passes.
- `references/render-traps.md` - writing composition code, patches, render vs preview differences.
- `references/rounds-and-budget.md` - before a notes round; when reporting time.
- `references/dated-facts.md` - before quoting any version, model route or measured number (perishable).
- Rubrics: `agent-content/benchmarks/*.rubric.md`. Techniques: `agent-content/techniques/` (frame-spec prompt, clean smooth motion, screenshot rebuild, concept ledger, timing ledger).

## Scripts (stdlib, `--self-check`, Usage in the docstring; they check numbers and text, never appearance)
`plan_lint.py` · `safe_zone_check.py` · `palette_audit.py` · `seek_safe_scan.py` · `claims_check.py` · `soundbite_score.py` · `probe_takes.py` · `cutlist_check.py` · `route_gate.py` · `check_route_freshness.py`.

## Evidence status
Built from the former type skills (four real speaker projects, testimonial, ad, motion and AI research, lab experiments E08-E12) and the end-to-end runs of 2026-10-04. Specified; deterministic checks only; model eval not run.

# Route table (full)

Load when the request is unusual, mixes Hebrew and English, or two rows look equally plausible. Cue phrases are a seed corpus, not a measured recall result (no model eval has run; decision default Q4). Source: blueprint SKILLS_CATALOG + WORKFLOWS per-type table, 2026-10-02.

## 1. Rows with cue phrases (Hebrew | English)
| Owner | Output contract | Hebrew cues | English cues | Not this skill when |
|---|---|---|---|---|
| `video-brief-intake` | BRIEF.md, LEDGER.md, 3 concept cards | סרטון חדש, בריף, יש לי רעיון, קונספט, תכין לי סרטון, בוא נתחיל פרויקט | new video, here is the brief, I have an idea, make a launch video | a locked `hf/PROMPT.md` exists for this project |
| `reference-style-matching` | Style DNA card + 3 application options | בסגנון של, תעשה כמו הסרטון הזה, תעתיק את הסגנון, רפרנס | in the style of, make it like this, copy this look | the user only wants the clip analysed (`video-analysis`) |
| `video-analysis` | measurements, contact sheets, transcript | תנתח, תעבור על, תמלל, מה קורה בסרטון, כמה חיתוכים | analyse, break down, transcribe, what's in this clip, BPM, which song | anything must be edited or generated |
| `revision-notes-handler` | numbered change log, patched project, presentation message | הערות, תתקן, משעמם, נראה AI, סטטי, סבב הערות, שנה את | notes, fix, boring, looks AI, too static, change the font | there is no draft yet (`video-brief-intake`) |
| `pro-video-editor` | an edited video: speaker reel, testimonial, ad/promo, motion or launch piece, a film of AI shots, podcast clip, tutorial, vlog, trailer, montage (the KIND goes into the handoff note as context) | תערוך, עריכה, דובר, מדבר למצלמה, טוקינג הד, בי-רול, עדות, המלצה, סיפור הצלחה, מודעה, פרסומת, ממומן, מבצע, מושן, אנימציה, השקה, טיפוגרפיה קינטית, סרטון AI, ג'נרציה, פודקאסט, טריילר | edit, talking head, speaker reel, B-roll, testimonial, ad, promo, UGC, product demo, launch video, kinetic type, logo reveal, AI video, podcast clip, trailer, montage | only an analysis (`video-analysis`), only a prompt (`video-prompt-writer` / `image-prompt-writer`), notes on a draft (`revision-notes-handler`) |
| `video-prompt-writer` | copy-ready video prompt text | /seedance, פרומפט לסידנס, פרומפט לווידאו | Seedance prompt, shot-by-shot prompt | the whole video is being planned or edited, or only a still is wanted (`image-prompt-writer`) |
| `image-prompt-writer` | copy-ready still-image prompt(s) | פרומפט לתמונה, גיליון דמות, תמונת פתיחה | image prompt, keyframe, start frame, character sheet, thumbnail | a video prompt is wanted (`video-prompt-writer`) or the whole AI film is being planned (`pro-video-editor`) |
| `speaker-color-correction` | corrected plate + check report | תקן צבע, העור נראה ורוד, הפנים חשוכים, הקליפ שטוח | colour correction, skin too pink, grey sky, hazy blacks | stylised look on stock footage |
| `hebrew-captions-transcription` | transcript + captions | כתוביות, תמלול בעברית, כתובית מאוחרת, פונט לכתוביות | captions, subtitles, caption timing, Hebrew ASR | a caption font is the only open question (`visual-choice-board`) |
| `render-qa-delivery` | final MP4 + manifest + QA | רינדור, מסירה, יצוא, עוצמת קול, בדיקה סופית | render, export, loudness, final check, deliver | notes still being collected (`revision-notes-handler`) |
| `video-variants-exporter` | N files from one master | גרסאות, יחסי מסך, 16:9 וגם 9:16, וריאציות הוק | variants, aspect ratios, hook A/B, platform versions | one deliverable only |
| `visual-choice-board` | `choices.json` | לא יודע איזה פונט, תראה לי אפשרויות, איזו אנימציה | torn between, show me options, pick a palette | the choice is already made |
| `paid-spend-gate` | dated estimate, approval, provenance | עלות, קרדיטים, כמה זה יעלה, תייצר | cost, credits, generate, upscale, cloud render | free local work |

## 2. The kind of video is context, not a route
Every edit goes to `pro-video-editor`; the router writes the kind (speaker, testimonial, ad, motion, AI shots, podcast clip, tutorial, vlog, trailer, montage) into the handoff note. The editor answers its discipline questions for that kind; there are no per-type templates (owner decision 2026-10-04). Kinds with no real project behind them yet (tutorial, vlog, podcast clip, trailer, montage): say the numbers are borrowed and unmeasured.

## 3. Confusable pairs (decide by the OUTPUT the user wants)
| Looks like | But if the user wants ... | Route |
|---|---|---|
| "make an ad" | only a prompt for a generator | `video-prompt-writer` (video) or `image-prompt-writer` (still) |
| "fix the captions" | a different font / animation but is unsure | `visual-choice-board`, then `hebrew-captions-transcription` |
| "render the final" | to fix a note first | `revision-notes-handler`, then `render-qa-delivery` |
| "the colour is off" | stylised grade on stock | not `speaker-color-correction`; ask |
| "analyse this reel" | and then copy it | `video-analysis`, then `reference-style-matching` |
| "how much will it cost" | an estimate for planned generation | `paid-spend-gate` (no call made) |
| "make this better" on a raw clip | unclear what it is for | `pro-video-editor`; its Round 0 asks what the video is for |
| "same clip as project X" | a NEW video | `video-brief-intake`; never adopt X's PROMPT |

## 4. Engine choice
HyperFrames is the default engine in v1.0 (decision default Q14). If the user names another (Remotion, an NLE): route as asked, set `ENGINE` in the note and flag the licence/scope check; do not silently use the default.

## 5. Project-state map (what `scripts/project_state.py` reports)
| State | Meaning | Resume with |
|---|---|---|
| `no_project` | no folder for this request | `video-brief-intake` |
| `scaffolded` | project folders exist, nothing written yet | `video-brief-intake` |
| `intake_open` | BRIEF.md and/or a `<ledger>` draft in `hf/PROMPT.md` exist, but no `<structure>` block yet | `video-brief-intake` (continue the rounds) |
| `prompt_drafted` | `hf/PROMPT.md` has a `<structure>` block, no `PROMPT_APPROVED` line in `hf/CHANGELOG.md` | ask the user for approval; no code before it |
| `prompt_approved` | `PROMPT_APPROVED <date>` line present | `pro-video-editor` (build) |
| `in_review` | a draft exists in `_work/drafts/`, or a `## Round N` section has no `PRESENTED` line | `revision-notes-handler` |
| `delivered` | `final/manifest.json` exists | `revision-notes-handler` for notes, `video-variants-exporter` for derivatives |
The probe reads files only. `prompt=approved` comes from the `PROMPT_APPROVED` line; if the user says they approved in chat and the line is missing, record it before routing on that fact.

# Route table (full)

Load when the request is unusual, mixes Hebrew and English, or two rows look equally plausible. Cue phrases are a seed corpus, not a measured recall result (no model eval has run; decision default Q4). Source: blueprint SKILLS_CATALOG + WORKFLOWS per-type table, 2026-10-02.

## 1. Rows with cue phrases (Hebrew | English)
| Owner | Output contract | Hebrew cues | English cues | Not this skill when |
|---|---|---|---|---|
| `video-intake` | BRIEF.md, LEDGER.md, 3 concept cards | סרטון חדש, בריף, יש לי רעיון, קונספט, תכין לי סרטון, בוא נתחיל פרויקט | new video, here is the brief, I have an idea, make a launch video | a locked `hf/PROMPT.md` exists for this project |
| `reference-style-transfer` | Style DNA card + 3 application options | בסגנון של, תעשה כמו הסרטון הזה, תעתיק את הסגנון, רפרנס | in the style of, make it like this, copy this look | the user only wants the clip analysed (`video-analysis`) |
| `video-analysis` | measurements, contact sheets, transcript | תנתח, תעבור על, תמלל, מה קורה בסרטון, כמה חיתוכים | analyse, break down, transcribe, what's in this clip, BPM, which song | anything must be edited or generated |
| `revision-round` | numbered change log, patched project, presentation message | הערות, תתקן, משעמם, נראה AI, סטטי, סבב הערות, שנה את | notes, fix, boring, looks AI, too static, change the font | there is no draft yet (`video-intake`) |
| `edit-talking-head` | edited MP4 of a speaker reel | דובר, מדבר למצלמה, רילס עם דובר, בי-רול, טוקינג הד, סרטון תדמית | talking head, speaker reel, B-roll, selfie footage | the speaker is a customer giving a review (`edit-testimonial`) |
| `edit-testimonial` | testimonial MP4 with claims table | עדות, המלצה, סיפור הצלחה, ביקורת לקוח | testimonial, customer review, success story | the speaker sells their own service (`edit-talking-head`) |
| `edit-ad-promo` | ad/promo MP4 + hook variants | מודעה, פרסומת, קמפיין, ממומן, מבצע, הנחה, הוק | ad, promo, paid social, offer, CTA, UGC, unboxing, product demo | no offer or CTA, pure brand film (`edit-motion-graphics`) |
| `edit-motion-graphics` | motion piece in HyperFrames | מושן, אנימציה, השקה, טיפוגרפיה קינטית, לוגו אנימציה | launch video, kinetic type, logo reveal, trailer, montage | mostly generated live-action shots (`edit-ai-generated`) |
| `edit-ai-generated` | video built from AI shots | סרטון AI, ג'נרציה, הייגספילד, קלינג, סידנס, ויאו | AI video, generated shots, Kling, Veo, Higgsfield | one prompt only (`seedance-prompting`) |
| `seedance-prompting` | copy-ready prompt text | /seedance, פרומפט לסידנס | Seedance prompt, shot-by-shot prompt | the whole video is being planned or edited |
| `color-correction-speaker` | corrected plate + check report | תקן צבע, העור נראה ורוד, הפנים חשוכים, הקליפ שטוח | colour correction, skin too pink, grey sky, hazy blacks | stylised look on stock footage |
| `hebrew-captions-asr` | transcript + captions | כתוביות, תמלול בעברית, כתובית מאוחרת, פונט לכתוביות | captions, subtitles, caption timing, Hebrew ASR | a caption font is the only open question (`choice-board`) |
| `render-qa-deliver` | final MP4 + manifest + QA | רינדור, מסירה, יצוא, עוצמת קול, בדיקה סופית | render, export, loudness, final check, deliver | notes still being collected (`revision-round`) |
| `multi-video-variants` | N files from one master | גרסאות, יחסי מסך, 16:9 וגם 9:16, וריאציות הוק | variants, aspect ratios, hook A/B, platform versions | one deliverable only |
| `choice-board` | `choices.json` | לא יודע איזה פונט, תראה לי אפשרויות, איזו אנימציה | torn between, show me options, pick a palette | the choice is already made |
| `paid-generation-gate` | dated estimate, approval, provenance | עלות, קרדיטים, כמה זה יעלה, תייצר | cost, credits, generate, upscale, cloud render | free local work |

## 2. Types without their own skill (owner rule: build a type skill only when a real project arrives)
| Request type | Route | Say to the user |
|---|---|---|
| tutorial, explainer with a speaker | `edit-talking-head`, screen parts via `edit-motion-graphics` ideas | no tested owner recipe for this type; borrowed numbers are unmeasured |
| vlog, lifestyle | `edit-talking-head` beat menu + `color-correction-speaker` | same |
| product demo | `edit-ad-promo` (offer, CTA, safe zones); real-UI rebuilds from `edit-motion-graphics` | same |
| UGC, unboxing, product review | `edit-ad-promo`; AI-made UGC adds `edit-ai-generated` + `paid-generation-gate` | same |
| trailer, teaser | `edit-motion-graphics` | same |
| music montage | `edit-motion-graphics` | same |
| podcast clip | no skill; playbook `agent-content/playbooks/` (batch/variants) + `edit-talking-head` beat menu | untested type; a clip must stand alone without context |
(src: distilled 02 video-types section 9 and coverage matrix, 2026-10-01)

## 3. Confusable pairs (decide by the OUTPUT the user wants)
| Looks like | But if the user wants ... | Route |
|---|---|---|
| "make an ad" | only a prompt for a generator | `seedance-prompting` |
| "fix the captions" | a different font / animation but is unsure | `choice-board`, then `hebrew-captions-asr` |
| "render the final" | to fix a note first | `revision-round`, then `render-qa-deliver` |
| "the colour is off" | stylised grade on stock | not `color-correction-speaker`; ask |
| "analyse this reel" | and then copy it | `video-analysis`, then `reference-style-transfer` |
| "how much will it cost" | an estimate for planned generation | `paid-generation-gate` (no call made) |
| "make this better" on a raw clip | unclear: speaker reel or ad? | ask ONE question separating `edit-talking-head` and `edit-ad-promo` |
| "same clip as project X" | a NEW video | `video-intake`; never adopt X's PROMPT |

## 4. Engine choice
HyperFrames is the default engine in v1.0 (decision default Q14). If the user names another (Remotion, an NLE): route as asked, set `ENGINE` in the note and flag the licence/scope check; do not silently use the default.

## 5. Project-state map (what `scripts/project_state.py` reports)
| State | Meaning | Resume with |
|---|---|---|
| `no_project` | no folder for this request | `video-intake` |
| `scaffolded` | project folders exist, nothing written yet | `video-intake` |
| `intake_open` | BRIEF.md and/or a `<ledger>` draft in `hf/PROMPT.md` exist, but no `<structure>` block yet | `video-intake` (continue the rounds) |
| `prompt_drafted` | `hf/PROMPT.md` has a `<structure>` block, no `PROMPT_APPROVED` line in `hf/CHANGELOG.md` | ask the user for approval; no code before it |
| `prompt_approved` | `PROMPT_APPROVED <date>` line present | the type skill (build) |
| `in_review` | a draft exists in `_work/drafts/`, or a `## Round N` section has no `PRESENTED` line | `revision-round` |
| `delivered` | `final/manifest.json` exists | `revision-round` for notes, `multi-video-variants` for derivatives |
The probe reads files only. `prompt=approved` comes from the `PROMPT_APPROVED` line; if the user says they approved in chat and the line is missing, record it before routing on that fact.

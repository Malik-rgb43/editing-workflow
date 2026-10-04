# Editor vocabulary -> owner skill

Load when: the user talks like a video editor from a timeline editor (Premiere, DaVinci, Final Cut, CapCut) and the words do not name a skill. Map the word to the OWNER below, say the mapping in one line ("a jump cut removal = `talking-head-editor`"), and keep the user's own word in the handoff note. A word that maps to a tool is a hint for the owner skill, not a route of its own.

| The editor says (English / Hebrew) | They mean | Owner | The AI-side equivalent |
|---|---|---|---|
| rough cut, assembly, "clean up the takes", ripple delete, remove silences / חיתוך גס, ניקוי שתיקות | cut a talking recording down to the good takes | `talking-head-editor` | `source_cuts`, `aroll_cut`, `join_diff` (the cut list is a file, not a timeline) |
| jump cut, punch-in, scale up on a beat / קפיצה, זום | a visible cut hidden by a zoom | `talking-head-editor` | the camera rig (`camera_path`) and `references/camera-and-zoom.md` |
| subtitles, captions, burn-in, SRT / כתוביות, תרגום | timed words on screen | `hebrew-captions-transcription` | `transcribe` then the `caption` block; Hebrew RTL on the text element only |
| colour grade, LUT, skin tones, "look" / צבע, גריידינג, גוני עור | match the picture to a target | `speaker-color-correction` | `color_fit` then `color_render` (the grade is baked into a file) |
| rotoscope, mask, remove background, text behind the person / רוטו, מסכה, טקסט מאחורי הדובר | the person as a separate layer | `talking-head-editor` (beat) -> `cutout` | `cutout`, then the `speaker-cutout-behind` block |
| lower third, title, MOGRT, animated text, kinetic type / כותרת, אנימציית טקסט | graphics over footage | `motion-graphics-builder` | `hf-blocks` and HyperFrames compositions (HTML + a paused timeline) |
| keyframes, easing, graph editor / קיפריימים, איזינג | motion over time | `motion-graphics-builder` | GSAP tweens on one paused timeline; `references/seek-safe-and-render-traps.md` |
| transition, light leak, film burn, flash / טרנזישן, שריפת פילם | the join between two shots | the type skill that owns the video | the `film-burn` block, or a hard cut; transitions are `check` points in `analyze` |
| B-roll, stock, cutaway, overlay footage / ב-רול, חומרי גלם משלימים | footage that covers the speaker | the type skill that owns the video | chosen by the meaning of the sentence; real footage first, generation only through `paid-spend-gate` |
| sound design, SFX, music bed, ducking, loudness, LUFS / סאונד, מוזיקה, דאקינג | the audio mix | `render-qa-delivery` | `hf_mix --report`, loudness on the final file |
| export, render queue, H.264, preset, proxy / ייצוא, רנדר | the final file | `render-qa-delivery` | studio preview first, range renders, ONE full render, every-frame QA |
| client notes, "revision 2", "change request" / הערות לקוח, תיקונים | changes to a draft | `revision-notes-handler` | patch, re-verify only what changed |
| markers, cue sheet, timeline notes / מרקרים | named moments | the owner of the video | cues in `PROMPT.md` and in the composition (`data-start`) |
| "watch this and tell me what they did" / תנתח את הסרטון | break down a reference | `video-analysis` | `analyze` + `frames`; then `reference-style-matching` to reuse the style |
| multicam, sync clips, nested sequence, adjustment layer | NLE structures with no one-to-one equivalent | ask which result they want | say plainly what replaces it (a sub-composition, a baked file, a cue) or that nothing does |

Rules: (1) the editor's wish is the artifact, not the NLE feature: ask for the result ("what should the viewer see at 0:12?"), not for how they would do it in a timeline; (2) a project made in an NLE is not opened by this toolkit: the source files and a cut list or a reference render are the input; (3) never promise an NLE round-trip (XML/EDL export or import) - this toolkit has no such tool.

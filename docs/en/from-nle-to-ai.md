# From a timeline editor to AI-assisted editing

> For editors who cut in Premiere, DaVinci, Final Cut or CapCut and now want an agent to do part of the work. 2026-10-03. This page maps your habits to what this toolkit does; it does not teach any of those programs.

<!-- step: from-nle-01 -->
## from-nle-01 - The one idea that changes everything
In a timeline editor the project IS the timeline: you move clips and the picture changes. Here the project is **text files**: a brief you approve (`PROMPT.md`), a **composition** (an HTML file with a paused timeline: every element has a start time and a duration), baked media files (a graded plate, a transparent speaker cutout) and QA reports. The agent edits the text; the engine turns it into frames. So:

| In your editor | Here |
|---|---|
| the timeline | one composition file: elements with `data-start` and `data-duration`, animated by one paused GSAP timeline |
| a nested sequence / MOGRT | a sub-composition; the studio's ready ones are in `hf-blocks/` |
| keyframes and the graph editor | tweens with easing in the timeline (the agent writes them, you judge them in the preview) |
| colour grade / adjustment layer | a grade fitted to a target and **baked into a file** (`color_fit`, `color_render`), so it renders the same every time |
| rotoscope | `cutout`: a transparent video of the speaker, made only for the beats that need it |
| subtitles | the `caption` block fed by word times from `transcribe` (Hebrew right-to-left on the text only) |
| ripple delete and silence removal | `source_cuts`, `aroll_cut`: a cut list, not a timeline edit |
| render queue | studio preview first, range renders next, ONE full render last, then every-frame QA |
| "undo" | files: nothing is overwritten that the toolkit did not create; the brief and the render log are the history |

<!-- step: from-nle-02 -->
## from-nle-02 - Your first hour
1. **Say the result, not the steps**: "a 30-second vertical reel from this recording, Hebrew captions, a zoom on the key sentence". You do not say how you would do it on a timeline.
2. **Approve the brief.** The agent asks until every parameter can be checked, then writes `PROMPT.md`. Nothing is built before you approve it.
3. **Look at the preview, not the code.** You review the studio preview and a few snapshots, and you give notes the way you give a client note: "0:12 - the title covers the mouth".
4. **One full render.** Everything before it is cheap; the final render is checked frame by frame and its loudness is measured on the file you will publish.
5. **Costs**: nothing is paid for without a dated estimate you approved. See [local-vs-paid.md](local-vs-paid.md) for what is free and local and what is not.

<!-- step: from-nle-03 -->
## from-nle-03 - What does not carry over
- There is **no round trip with your NLE**: this toolkit does not read a Premiere or DaVinci project and does not write an XML/EDL back. The inputs are your source files (and, if you like, a reference render or a cut list).
- Multicam, nested adjustment layers and plug-in effects have no one-to-one equivalent. Tell the agent the picture you want; it will say plainly what replaces it, or that nothing does.
- Real-time scrubbing of a heavy edit is replaced by preview + snapshots at chosen times; keep your own editor for the parts where hands on the timeline are faster.

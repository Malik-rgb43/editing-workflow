# Diagnosis and classification of notes

Load when a note arrives and you must decide what it means, which file or cue causes it, and what class it is. Sources: distilled 02 workflow-end-to-end section 12 and 01 rules G3-G6, 2026-10-01 (owner-project causes; one Windows machine; treat as a starting hypothesis list, not a law).

## 1. One diagnostic question
"What exactly on screen creates the feeling, and which line, cue or asset in the project does it?" Write the answer next to the note as the **cause**. A note without a cause is not ready to patch. The user's times are approximate: look one second either side; at a transition look at every frame, half a second each side.

## 2. The user says -> common cause -> where to look
| The user says | Common cause (it happened) | Where to look |
|---|---|---|
| something odd, an element missing | stale timing grid after a re-time (frame literals outside the scene window) | `hf_preflight` errors; grep the frame literals in the scene file |
| a jump or glitch at a cut | hidden cut inside the source, pre-roll shorter than 6 frames, first frame ungraded | `source_cuts`, "double jumps" in `frame_qa`, the frame strip c-1..c+2 |
| the speaker is not centred | zoom origin not on the face x | `face_center audit` on the WHOLE film (global rule!) |
| cut off, half out of frame | centre-growth on a long line, exit before the last word landed, a wipe that did not finish | snapshots at start, middle and end of the event |
| not smooth, stuck | stitched tweens, two tweens on the camera, no spline | the project's motion table; one eased move per scene |
| SFX loud, music loud | gain above the speech margin | `hf_mix --report` (audio-only branch) |
| caption late or early | cue timing, not frame literal | `caption_qa`, word cue in the captions JSON |
| wrong word, typo | text fact differs from the spec | grep the HTML for the string; compare to PROMPT facts; zero proofreading errors is the bar |
| boring, looks AI, static, "לא אהבתי" | the beat's concept itself | replace-concept (section 3) |
| too long, shorter, move this earlier | the order or length of beats | restructure (section 3) |
| another song, the music doesn't fit | the track itself, not its level | music-swap (section 3) |
| wrong caption word / captions in another language | the caption text / the caption language | fix / global-rule (section 3) |
Hebrew look-alikes (ו/ז, ד/ר, ה/ח) read as a different word in a display font: verify the keyword at full size before blaming timing.

## 3. Classes
| Class | Signs | Do |
|---|---|---|
| **replace-concept** | "boring", "looks AI", "static", "didn't like": taste, not a defect | propose a NEW beat for that range from the editor's beat menu (or, if none, 2-3 alternatives you pick from by the sentence's meaning); one line why; never polish the old beat. Visual alternatives (2 or more) go on a `visual-choice-board` |
| **fix** | glitch, position, size, timing, cut, colour, typo, a wrong caption word | fix the cause from section 2; a caption word is fixed in the captions file, then the caption track is re-checked at that time |
| **audio-only** | SFX, music, VO level, swoosh | remix + remux (no render): `hf_mix --report`, then `hf_deliver ... --skip-render`; never chase loudness inside the composition |
| **global rule** | "always", "never", the same theme in two rounds, or a caption language change | fix EVERY occurrence in the film (centring was fixed per section once and 17-24 s was missed); list all occurrences in the log. A caption language change re-runs the captions for the whole film (`captions-transcription`, `--language <code>`) |
| **restructure** | "shorter", "move this earlier", "swap these parts", a new length | write the new order in PROMPT.md `<structure>` (and update the storyboard page if beats change), show it to the user and patch only after their yes; log `order:` and `asked:` |
| **music-swap** | another song or track | audio-only remix + remux with the new track's licence row in the ledger (`licence:`), `render: none`; cuts that were timed to the old track's beats get their own fix note |
A note with several claims is split (1a, 1b). A mixed round (audio + picture) puts the audio into the same single full render. A project whose audio is composed inside the render (no premixed `mix.wav`) cannot change the mix without a render: build with the mixing tool next time.

## 4. Ambiguous note
"Not good" without what: first diagnose from the frames. Ask only if the diagnosis is inconclusive, and ask ONE question with 2-3 concrete options and the frame attached.

## 5. A note that arrives while a render runs
First half of a full render: stop it (only your own process tree, check the lock) and rerun after the collection window. Second half: finish; the note joins the next round unless it is a blocker (wrong fact, broken frame, rights problem). Never start a full render while reviewers are still running, and wait for all of them before re-rendering.

## 6. Where the notes come from
Studio review is the default channel: the user watches the live project in HyperFrames Studio (`python tools/hf_studio.py <project>/hf`) and sends notes; fidelity limits for `<video>` layers are about 1 frame (measured on one machine, HyperFrames 0.8.98, E12; other versions unmeasured), so render-only risks still need a segment render. Studio adds `data-hf-id` to `index.html`: strip before patching, re-read the file after any Studio edit.

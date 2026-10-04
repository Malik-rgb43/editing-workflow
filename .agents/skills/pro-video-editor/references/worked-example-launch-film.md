# Worked example: a strong spec and the film it produced (launch film, 22 s, square)

Load when writing PROMPT.md for any piece driven by a voice-over and music (launch, explainer, product film), or when a draft feels "templated" and you need to see what deliberate looks like.

Source: a public post by the creator "zero" on X (status 2106526359589675085, 2026-10-03). It contains the prompt and the rendered film, both made by Claude Opus 5.5 with plain code. The film was measured with `video-analysis` on 2026-10-05: every frame, the word timings and the audio. The prompt is paraphrased here, not copied. Numbers marked *measured* come from the file; the others are what the spec asked for.

## 1. What the spec answered (paraphrased)
| Question (SKILL.md "What a strong spec answers") | How this spec answered it |
|---|---|
| Inputs | name, pitch, logo, screenshots, 40+ images, brand colours and font, voice key and id, a song with its drop timestamp; **a default for every one**, so nothing blocks |
| Script | a 9-line voice in a fixed rhetorical shape, each line mapped to the product; emotion tags light: soft on the quiet lines, excited on the verb line, no tag on the opener |
| Voice | 4 full takes to pick from; one bad line regenerated alone 4 times and spliced in; pauses over 0.28 s cut to 0.2 s; phrases levelled 85 % toward the median, with gain changed only inside the pauses; word timings re-measured per pause-chunk because one pass drifts up to 0.5 s |
| Direction | a white page, one typeface, black ink, real images; every caption typed word by word as spoken; one material (liquid glass) with a pastel aura behind it so the glass shows; the stressed word in a gradient with a faint glow; motion rules with numbers; a banned list |
| Structure | 7 scenes, each hung on a voice line, each naming its entrance and its hand-off |
| Sound | the drop anchored to the verb line and the beat grid anchored there; a 3-band sidechain duck; the voice about 9 dB over the music between 300 Hz and 4 kHz per phrase; one SFX per visible event, placed by measured peak; the music faded on a dB curve under the end card; -14 LUFS |
| Build | one canvas; every frame a pure function of time; captions and cuts read the word table; the glass drawn from a blurred snapshot of what is behind it plus an edge band, sheen, rim and shadow; rendered at 60 fps with motion-blur subframes |
| Gotchas | the known failures for this kind of film, written down before building |
| Start | ask for the inputs -> the script -> 4 voice takes -> 8 stills -> the full render |

## 2. What came out (measured)
| Scene | Time | What happens | The voice (onset) |
|---|---|---|---|
| 1 | 0.00-3.38 | a collage of real images drifts out; the name types in big; the category line replaces it | "This" 0.27, name 1.11 |
| 2 | 3.38-4.45 | 8 full-bleed images switch every 0.116 s (a 16th note at about 129 BPM) under the typed value line | "made" 3.07, "taste" 3.73 |
| 3 | 4.45-6.30 | **the drop on the verb** ("Create" 4.37): a glass prompt bar; the result card switches style about every 0.15 s; a black style chip names each style; a strip of thumbnails grows | "Create" 4.37 |
| 4 | 6.30-9.00 | the card blurs through into 9 images that fly to a 3x3 grid, then ring a portrait that has **taken the moodboard's look** | "Show" 6.29, "gets you" 8.07 |
| 5 | 9.0-11.5 | the first line shrinks and greys; the second types big; the stressed word in a gradient with a glow | "better" 10.35 |
| 6 | 11.5-15.4 | a glass settings panel over a pastel aura; the named slider is bold and moves, and the picture answers (hue, new seeds, poster) | 12.05 / 13.41 / 14.59 |
| 7 | 15.4-21.97 | about 120 images burst behind a glass caption pill, then collapse into the logo; the name and "Out now" type; a 2.4 s hold; the music fades | "Every" 15.55, name 18.29 |
Loudness *measured*: -14.0 LUFS, TP -1.0 dBFS. Captions start about 0.1 s after each word's onset. There are no full stops on screen.

## 3. Lessons (each is now a principle or a mistake row in SKILL.md)
1. **The voice is the timeline:** a measured word table drives captions, scene starts and the stressed word.
2. **Fast only where it peaks:** 16th-note runs occur in two places, just before the drop and on it. Everything else drifts. Cut counts lie for this kind of film: 32.8 cuts/min *measured*, yet most change happens inside one canvas.
3. **Prove the claim in the picture:** styles switch on "any style", the result adopts the board's look on "gets you", and the picture answers each slider on "tune".
4. **One material, made visible:** glass needs a backdrop (an aura, a blurred wash), or it shows nothing.
5. **Continuity:** content blurs or flies into the next layout, and the camera keeps its zoom across a hand-off.
6. **Hierarchy in type:** the previous line steps back (smaller, grey) as the next types.
7. **Ending:** the logo is assembled from the content itself (the burst collapses into it), followed by a 2 s hold.
8. **Checkpoints:** cheap approvals (script, voice takes, stills) before the expensive render.
9. **Weak spots seen in the result:** an empty white frame of about 0.2 s before the burst (15.37) reads as dead time; and the voice says the name differently from how it is written. Run a pronunciation check on every brand name.

## 4. Turning it into tools in this toolkit (built 2026-10-05; measured on the reference machine)
| Need | Toolkit route |
|---|---|
| word table with per-phrase re-timing | `tools/word_retime.py`: each speech chunk's first word pinned to its measured onset. On a 52 s Hebrew talking head it found 24 chunks; one transcription pass was off by 0.119 s median and 0.316 s max (early AND late). Fast mode re-uses words.json (1.9 s); `--model-dir` re-transcribes every chunk on its own (16.5 min on CPU, run beside another job) |
| captions typed as spoken | the `typed-caption` block: letters from each word's onset, a zero-width caret, the previous line steps back, the stressed word in a gradient with a glow, shrink-to-fit |
| pauses cut, phrases levelled | `tools/vo_clean.py` (VO tracks only, never picture-locked dialogue): pauses over 0.28 s cut to 0.20 s from their middle, phrases moved 85 % to the median with gain changed only in pauses, `--words` re-times the word table through the same cuts |
| sidechain ducking, voice-over-music per phrase | `tools/hf_mix.py`: the report's `vo_over_music` is measured per phrase on the stems AFTER ducking (300 Hz-4 kHz); `master.vo_over_music_db` sets the target |
| SFX by measured peak | `hf_mix` cue `"align": "peak"` (+ `pre_s`, `post_s`): the file's loudest 5 ms lands on the event, trimmed around it |
| pop scan with planned fast runs allowed | `tools/frame_qa.py --allow t0-t1` |
| glass material | the `liquid-glass` block: an inner frost, a refracting edge ring (an SVG displacement map along the rounded rectangle's normal), milk, sheen, rim, shadow, an optional pastel aura and typed text |

<!--
STARTER: talking-head reel (copied by `tools/new_project.py --starter talking-head`; delete these comments when the draft is real).

What a starter is: the house preset v1 numbers of talking-head-editor already typed in, the build commands already wired to the
files `tools/prep.py` writes, and every question the brief must still answer marked ASK. It saves typing; it decides nothing.
 - status stays DRAFT until the human approves (AGENTS.md rule 2, talking-head-editor G1). A starter is never an approval.
 - Every D row is a house-preset DEFAULT (decision default Q5): show it to the user; they may override any of them.
 - Every ASK row must be answered in the intake (video-brief-intake) before this file is presented; never fill one by guessing.
 - Times below are placeholders in output seconds; replace them with the real cut. Skeleton rules: talking-head-editor/references/prompt-md-skeleton.md.
-->
# PROMPT: <slug> - "<title>" (9:16, ASK s, 30 fps)
status: DRAFT (not approved)
Style lock / reference: ASK (ref-id and the range that is "the style", or none)
Deliverable: ASK (exact final file name)      Owner notes this version answers: none yet (first draft)
Story in one sentence: ASK (what the viewer feels; what the speaker promises)
House preset v1 in use: captions, cadence, zoom caps, colour preset and loudness below are defaults the user can override.

<ledger>
| ID | dim | said (verbatim) | spec (measurable) | where / when | acceptance check | src | status |
|---|---|---|---|---|---|---|---|
| L01 | FMT | - | 1080x1920 (9:16) master, 30 fps constant, 1088 canvas | whole | ffprobe width, height, r_frame_rate on the final | D | proposed |
| L02 | LEN | - | ASK: exact seconds, +-0.1 s | whole | ffprobe duration on the final | D | proposed |
| L03 | STR | - | silence cut only, natural order, whole sentences; in-point 0.06 s inside the silence before each sentence; no piece < 6 frames | whole | join_diff of the assembled VO against the source words: 0 extra tokens | D | proposed |
| L04 | TON | - | ASK: energy / register in the user's words | whole | review against the reference range | D | proposed |
| L05 | BAR | - | ASK: quality bar (premium / standard) | whole | rubric agent-content/benchmarks/talking-head.rubric.md | D | proposed |
| L06 | CTA | - | ASK: the exact closing line and what the viewer does | last 2.5 s | OCR the end card | D | proposed |
| L07 | FILE | - | ASK: exact final file name | final/ | ls final/ | D | proposed |
| L08 | COLOR | - | graded from the camera original to the named preset speaker-plate-v1; skin measured from hf/data/faces.json | whole | color_check PASS on the final (--faces) | D | proposed |
| L09 | CAP | - | Hebrew captions, house preset v1: font ASK (no font named = a font board, visual-choice-board rule 8; Rubik only if picked or "you choose"), 1-3 words per card, animate in and out, word dwell >= 0.25 s, card >= 0.9 s, rail bottom <= y 1450 | whole | caption_qa --cues cues.json --canvas 1080x1920 --rail-bottom 1450 | D | proposed |
| L10 | MOT | - | opening push-in within 1.0 s; a camera event every 2-4 s; push-ins <= x1.16 over 3-4 s; zoom <= x1.40 while captions sit on the chest; smoothed face-centred path (sigma 0.6 s) | whole | motion_qa --acc 1500: 0 ranges; face_center audit on the render | D | proposed |
| L11 | BROLL | - | a beat that SHOWS the sentence every 3-6 s, full-bleed; overlay cards <= 860 px wide, under the chin, box disjoint from the face | whole | plan_lint G5 on hf/data/edit_plan.json; motion_scan | D | proposed |
| L12 | MUS | - | one continuous bed about 4 dB under the first speech level (owner said "approximately") | whole | hf_mix --report | D | proposed |
| L13 | SFX | - | only on visible events, -18 to -26 dB, 1-3 frames early | per event | hf_mix --report lists every SFX with its event time | D | proposed |
| L14 | LOUD | - | -14 LUFS +-0.5 integrated, true peak <= -1 dBTP, measured on the final file | whole | hf_deliver verify (ebur128 on the final) | D | proposed |
</ledger>

<inputs>
footage: source/ASK (file, duration, ratio, fps, colour state, loudness - from `_work/prep/` and `source_inventory.py`) | camera original present: ASK
language: he | keywords + colours: ASK | keyword font: ASK (L09: a font board when none is named) | CTA word: ASK (L06) | logos: ASK (licence row in hf/SOURCES.md)
prepared at minute 0 by `python tools/prep.py <project>` (check `_work/prep/prep.json`: a not_run step is not evidence):
  hf/data/words.json (transcript) | hf/data/src_cuts.json (hidden cuts) | hf/data/faces.json (face centre) | _work/prep/scopes.json | _work/prep/sheet.jpg | _work/analysis/<ref-id>/
</inputs>

<script>
Natural order, whole sentences (L03). Proposal: `python tools/aroll_cut.py hf/data/words.json source/<main> -o hf/data/cut --fps 30`
Show the TEXT of the cut to the user before any render. Beat | out frames | src seconds | VO text:
| beat | out | src | VO |
|---|---|---|---|
| hook | f0-f45 | ASK | ASK |
</script>

<direction>
format/fps: one pre-cut, pre-graded 30 fps base = ONE <video> (L01)
grade: speaker-plate-v1 from the camera original (L08): color_fit -> color_render -> color_check
framing: head top y ASK px; zoom caps per L10
type system: the font picked for L09, captions per L09 | accent tokens: ASK (>= 2 hex) | motion language: eased only, no linear moves
transitions: each used once, listed here | cadence statement: a beat every 3-6 s (L11; state the number used)
Banned: per-frame face follow; AI-looking people stills; dir="rtl" on the composition root
</direction>

<structure>
| # | out time | src time | what is said (keywords bold) | beat type | what is seen | camera event | sound |
|---|---|---|---|---|---|---|---|
| 1 | 0.00-1.50 | ASK | ASK | hook (layered) | ASK | push-in from 1.00 to 1.08 by 1.0 s (L10) | bed in |
</structure>

<sound>
VO chain: ASK | bed per L12 with ducking under speech | SFX per L13 | master per L14, measured on the FINAL file (render-qa-delivery)
</sound>

<build>
order: cut -> picture lock -> graphics -> captions -> colour check -> sound
captions: `python tools/hf_blocks.py caption-words hf/data/words.json --from S --to S -o hf/data/caption_S.json`, then `python tools/hf_blocks.py add caption hf ...`
camera: `python tools/camera_path.py hf/data/faces.json --zoom S:S:SCALE ... -o hf/data/cam` (smoothed; never per-frame follow)
hidden cuts: every hf/data/src_cuts.json hit inside a used range gets a cover >= 6 frames each side (talking-head-editor G3)
colour: `python tools/color_fit.py <camera original> --at T1,T2,T3 --faces hf/data/faces.json -o hf/data/grade.json` -> `python tools/color_render.py ... -o hf/assets/video/aroll.mp4`
</build>

<gotchas>
RTL only on text elements | fonts via @font-face files in hf/fonts/ | the widest keyword fits the caption box | snapshot --describe false, <= 5 timestamps per call | run tools/hf_preflight.py before any check or render
</gotchas>

<start>
Four approval stills (hook, a peak beat, a mid-transition, the end card) by snapshot, then the draft in Studio; ONE full render per round.
</start>

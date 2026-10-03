# Failure modes: symptom -> cause -> fix -> prevention

Load when: the corrected plate looks wrong, `color_check` fails, or two cuts do not match. Dated 2026-10-02; sources: distilled 04 colour "Failure modes" and §1.2, distilled 06 talking-head-and-footage §1.8.

| Symptom | Cause | Fix | Prevention |
|---|---|---|---|
| Grey sky | `highlights -` pulled a clipped sky from 100 to 88 IRE | keep the sky ~100, neutral | no global highlights - |
| Hazy, bluish black shirt | `shadows +` lifted black; the camera's blue tint remained | black pin + shadow-tint offset; WB on the shirt | targets: black Y ~5 %, Cb = Cr = 0 |
| Magenta / pink skin | face lit by cool skylight; global vibrance or temperature | subject node with its own WB; skin band toward the 123 degree line | two nodes, never one global grade |
| Orange / neon grass | vibrance on warm evening light | foliage band chroma ~25-28, saturation <= +10 % | fit targets for grass |
| First frame ungraded or frozen 5 frames | shader-node grade without pre-roll | bake into the file | pre-roll >= 6 frames; check 3 frames after each A-roll return |
| Soft, blocky image after correction | the rough cut was graded | grade the 4K camera file | `ls` the source tree (G1) |
| Pink coat, hot halos | subject WB + saturation on a hard matte; lift > ~0.7 EV | luma-only subject node; erode + blur the matte | indoor preset |
| Colours shift in stills | ffmpeg stills without `in_range=tv:out_range=pc` | add the scale flags | `color_io.read_frame` |
| Skin hue jumps between cuts | per-shot WB drift or a stylised look | one shared fixed look; check across cuts | before/after sheet at 3+ cuts |
| Washed HDR clip | HLG/Dolby tagged 2020 treated as 709 | real tone-map to SDR first | probe `color_transfer`/`color_primaries` (G2) |
| Fit converges but looks wrong | convergence is not acceptance; pre-measure clipping hid the damage | pre-clamp stats + held-out frames + a human looks | solver gate (G3) |
| Periodic face-lift flicker | matte refreshed every 3rd frame | matte every frame + temporal smoothing | flicker check (G6) |
| Parameters on their bounds | degenerate fit (WB extreme cancels low saturation) | constrain parameters; luminance-preserving WB | two stages, few free parameters |
| Automatic fit unstable on macro close-ups | skin fills the frame; no white reference | hand-lock the macro shots | `color_fit_shots` macro rule |
| `color_check` passes with almost no frames | face detection failed on most samples | the gate reports INSUFFICIENT_EVIDENCE below the sample minimum | `scripts/grade_gate.py` coverage statement |
| Render hangs 0 frames, navigation timeout | `data-color-grading` shader (the reference machine's stack) | bake the grade; time one snapshot before any render | rule 4 |
| Numbers pass, picture looks wrong (or the reverse) | scopes do not imply taste | a human reviews the before/after sheet and decides | G6 |

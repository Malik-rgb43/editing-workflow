# Reading the evidence correctly

Load when a QA or analysis tool reports a number or a verdict (frame_qa, motion_qa, the colour gate, loudness, source_cuts, transcripts) and you are about to trust it, report it or act on it. Moved from SKILL.md on 2026-10-06; the rules come from the four real speaker projects and the 2026-10-04 end-to-end runs.

- **frame_qa** `pop_frame` is real: a layer ended on the frame the next began. **hard_cut** is information.
- **motion_qa** measures the whole frame. A speaker's hands at x1.8 read as camera spikes, so confirm on frames, mask graphic beats, and pass every edit point with `--cuts` (seconds with a decimal point).
- **The colour gate** judges against a NAMED preset. An indoor preset fails an outdoor shade shot on hue even when the face looks right; say which preset fits, or that none does.
- **Loudness** is measured on the shipped file; aim under the true-peak limit, because the AAC encode overshoots. A level fix is a remix and re-mux, not a full render.
- **source_cuts** misses jump cuts in a locked-off frame; an audio match to the original does not.
- **Transcripts** disagree on rare words: two models agreeing is evidence, and the owner's finished edit is better evidence.

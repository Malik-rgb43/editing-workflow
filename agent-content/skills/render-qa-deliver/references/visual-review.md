# Visual review: 4 axes, process, rubric, limits

Load when: before reviewing or presenting a draft, when briefing a reviewer or critic, when deciding how many reviewers to run. Dated 2026-10-02; sources: distilled 01 rules-and-gates F; distilled 02 qa-and-benchmarks §1-§6; blueprint QA_AND_BENCHMARKS §6-§8. The reviewer's brief and the type rubrics (`agent-content/benchmarks/<type>.rubric.md`, owned elsewhere; none exists for talking-head, so use the general dimensions) are inputs; this file is the process.

## 1. Four axes
1. **Cropping / composition:** safe zone, finishes clean, speaker centred, head not cut, nothing cut by the frame edge or another element (a word entering half out of frame, a wipe stopping halfway, a plane cropped in a card photo).
2. **Fidelity to DESIGN.md and the vision:** palette only; fonts and weights of the project (default Rubik 400/900, <= 2 weights per frame); radii and shadows from tokens; no AI look; one focus per frame; what PROMPT.md promised at that moment is there.
3. **Clean animation:** no pops, no overlapping text/cards > 3 frames, no word entering wrong and fixing itself, entrance/exit consistent with the tokens (expo/power2, no bounce on text, exit shorter than entrance), no transition repeated back-to-back, no sudden camera stop, word >= 0.25 s and card >= 0.9 s.
4. **Readability:** contrast, size, numbers and UI details readable, the first 3 s hook, the end card clean.
Report each problem as: time or frame, axis, description, severity (blocker / major / minor), concrete fix.

## 2. Process (cost-aware)
1. Automatic QA first (stage 6); its sheets feed the reviewers: `frame_qa` all-frame sheets, tiles <= 180-270 px (`--tile 160-270`), plus a window at every transition (every frame +-0.5 s). Zoom only on deciding frames.
2. Reviewer count by length (kit A/B lesson: a sub-agent critic on a 10 s film cost 160k tokens; 4 agents x every frame x 4 rounds burned the quota in two sessions):
   - under 20 s: self-review on the sheets (`frame_qa` + `motion_qa` + the 4 axes);
   - 20 s or a client delivery: ONE reviewer sub-agent, CONTINUED between rounds with only the fix list ("verify on the frames, re-score <= 250 words");
   - round 1 of a project: 2-4 agents on the whole film; later rounds: only flagged/changed ranges; derivatives: axes 1 and 4 only.
3. Wait for ALL reviewers before patching or rendering (a reviewer that returns after the render means another render). Merge the reports into one numbered list in `hf/CHANGELOG.md`; fix everything in ONE round; the critic verifies, it does not discover. A new finding means the preflight is weak: add the check.
4. The critic is a SEPARATE agent that did not build the film; it receives the file, PROMPT.md and the user's notes the version must answer, and returns a score per note.

## 3. Release rule (rubric)
Average >= 4.0 with no dimension < 3, scored 1-5 against the references (5 indistinguishable from the leading reference, 4 very professional, 3 reasonable but template-like, 2 amateur, 1 broken), plus type gates. The research human rubric has six dimensions with 1/3/5 anchors (meaning/story, caption/language, composition/brand, motion/edit, audio, integrity/continuity), with "not applicable" and "not observed" states and severe failures recorded separately so averages cannot compensate; hard-gate failures (an unauthorized act, a wrong number, a legal/consent failure) veto the score. Max 3 rounds, then present with the open-gaps list. Always write the honest score. Judge variance is large (one film scored 21.5 then 18.5 of 30): do not treat a single score as a measurement.

## 4. What reviewers cannot certify
Waveform metering, every-frame completeness, exact Hebrew copy, pixel-safe geometry, audio sync to +-2 ms. A model reading a contact sheet saw sampled images, not the video; say what was sampled. A Hebrew reader checks spelling and legibility. Review the audio separately by measurement (ebur128, 3 s-LUFS timeline) and by listening.

## 5. Human review of drafts
Review live in Studio (`preview`); the user sees changes as they are made. Present each draft as soon as it exists (partial results first). The expensive human step is the user's time: keep the numbered-notes format (`delivery-and-manifest.md` section 7).

## Sources
distilled 01 rules-and-gates F1-F10, G1; distilled 02 qa-and-benchmarks; blueprint QA_AND_BENCHMARKS §6-§8; checked 2026-10-02.

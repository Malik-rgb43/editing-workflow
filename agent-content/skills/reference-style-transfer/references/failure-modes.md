# Failure modes of style transfer (each happened or is documented)

Load when: a transfer went wrong, or before presenting options/a draft. Source: distilled 06 reference-analysis "Failure modes" and §3 "Common mistakes" (2026-10-01).

| Symptom | Cause | Fix | Prevention |
|---|---|---|---|
| Styled the wrong look (the before/after part; the user wanted the final look) | the reference segment was not pinned | re-analyse the right range, rebuild the card | G5: the user names the range |
| Film came out with no music | the reference had none and its flaw was copied | music is a ledger line, default on for a talking head | "do not copy the reference's flaws" |
| A 4-hour restructure thrown away | length/structure taken from a pasted prompt written for another topic | footage wins; ask the structure question | structure from intake only |
| Cuts/min wildly off (108 vs 42) | kinetic type, graphic transitions inside a move, light leaks, PiP, flashes mis-counted | count edit points from the sheets, `pacing.override`, quote the limit | verify every suspicious transition; `check` points resolved |
| A jump cut counted as a graphic swap, or the reverse | background unchanged: numbers cannot tell | decide from frames | the `check` list |
| Colours wrong in the card | hex read from downscaled sheets | `px_measure.py sample` on a full-resolution flat fill | `HEX_SOURCE` check |
| A display font reads as another word | look-alike letters (ו/ז, ד/ר, ה/ח) | full-size keyword test, switch face | font row = nearest match, L |
| Reference timing stretched over a longer voice-over | mapped by seconds | map by function and density | beat map by function |
| Drift between reference and draft found by the user | the DNA was not re-measured on the draft | `fidelity_diff.py` after every render | G6 |
| The same source edited in 3 sessions with 3 references and the same note sent to all | notes were treated per project | a note typed to all sessions is a global style rule: record it once in the rule file, never per project | one session owns shared rules |
| The reference's song ended up in an ad | a match was read as permission | replacement track with a licence row; `sync_licence: not_established` | G3, `MUSIC_REPLACEMENT` check |
| A near-zero DNA value failed or passed meaninglessly | a blanket +/-20 % | per-row tolerance with an absolute floor | `TOL_NEAR_ZERO` check |
| Options read as three copies of one idea | decisions not really different | rewrite until >= 3 decisions differ pairwise; Twist changes one axis | G4 |
| "Reference look only" delivered at a premium bar | grammar copied, no upgrade | Elevated adds beats from the toolbox | recommend Elevated for a premium bar |
| The analysis folder used for the card was edited afterwards | numbers diverged | the card is tied to `analysis_sha256`; re-write the rows | `ANALYSIS_HASH` check |

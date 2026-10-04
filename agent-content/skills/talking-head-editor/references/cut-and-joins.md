# The cut: natural order, silences, joins, hidden source cuts, A-roll prep

Load when: producing the text of the cut, building `edit.json`, checking a join, handling a rough-cut source, preparing the A-roll base clip. Facts dated 2026-10-02; "d06-th" = distilled 06 talking-head-and-footage.

## 1. Structure defaults
- Default structure = FULL content with silences cut only, natural sentence order, whole sentences. Restructure ONLY if the author asks at intake ("silence-cut only, or rebuild?"). One restructure nobody asked for cost about 4 hours (5 drafts) until the author said "full length, only silence cuts" (d06-th §0.2).
- Reordering needs a strong reason and is shown as text first. Out-of-order speech and mid-sentence cuts ("מחליטים" without its subject) were rejected as "the cuts aren't good enough".
- Show the TEXT of the cut (or a 30 s audio-only cut) before building visuals; the author approves text with no render.

## 2. In-points, joins, slivers
| Rule | Value / procedure |
|---|---|
| In-point | in the silence BEFORE the sentence, never after its first word; cut 0.06 s INSIDE the silence, never on its edge; join leaves 80-200 ms of air |
| Subject | never drop the subject: a cut after "אני" (to remove "אז") left "מקשיב לו ושואל שאלות" subjectless and the author caught it at second 9. Keep a natural "אז" whole and drop it from the captions only |
| Join check | ASR the FULL assembled VO after every re-cut (not isolated join snippets: snippets said "clean" while the full file heard residues "ז"/"כן", about 45 min lost). `join_diff`: word-level diff of the assembled-VO words vs the source words on chosen ranges; ANY extra token = fail; a kept sentence missing its first 2 or last 2 source words = error |
| Majority vote | ambiguous words (a 4:2 split "של" vs "שלי") are decided by several ASR passes, then not flip-flopped |
| Slivers | drop pieces under about 6 frames (4-frame fragments of another take caused a flash) |
| Similar framings | a cut between two similar framings of the same speaker reads as a glitch: cover it (film burn, two-sided zoom-through) or change scale >= 15 % |
| Auto-flag A->A (proposed) | A-roll -> A-roll cut where the face box moves < 15 % in scale and > 20 px in position with no transition |
| Fillers | "אה/אממ" usually do not appear in a Whisper transcript: detect voiced gaps between words and FLAG them; never auto-delete every occurrence of a discourse word ("כאילו", "בעצם") |
| Schedule | camera/state change on a cut at `start - 0.005 s`; `max(0, data-start)`; `grep -c 'data-start="-' index.html` must print 0 (a negative start shifts every clip 2 frames) |

## 3. Silence-removal constants (author's earlier reels tool; proven, not re-measured)
| Parameter | Value |
|---|---|
| Minimum pause to cut | natural 0.60 s / tight 0.40 s / aggressive 0.25 s (reels default: tight) |
| Minimum shot | 0.35 s |
| Padding | lead 0.08 s, tail 0.12 s |
| Cut position | 0.06 s inside the silence |
| Silence threshold | adaptive per clip, 20th percentile, range -55...-20 dB (two edit specs used -38/-40 dB and 0.12-0.25 s pauses) |
| Draft | `auto-editor <clip> --margin 0.08s,0.12s` (optional external tool; its 0.2 s default margin is a default to test, not a Hebrew editorial rule) |
Silence detection proposes; the editor decides. Re-check each edit point on the waveform +-2 frames.

## 4. Hidden source cuts (`source_cuts`)
A rough-cut source ("cuts roughly") contains jump cuts the author no longer sees. `source_cuts <source.mp4> --edit data/edit.json --thresh 4.0 --margin 6` decodes to a small grey raster; a cut = per-frame mean abs difference > 4.0 x the local median (window +-15 frames) + 0.3 AND > 3.0 absolute. Output `src_cuts.json` (source seconds) and, per piece, the cuts "at the in-point / out-point / mid-piece" mapped to OUTPUT frames with the advice "cover f(out_f-6)..f(out_f+6) with B-roll, or move the in/out point".
- Cover with >= 6 frames of margin on both sides, or move the point. An in-point 1 frame before a source cut leaves a 1-frame stale shot (5 such frames at one project's f680, f860, f1062, f1239, f1556).
- Verify in the BUILT `aroll.mp4` that every cut lands exactly on `out_f`; clone the clean first/last frame (tpad) at edges.
- Known limits (static review): the original decodes the WHOLE video into memory (about 6.17 GB analytic for a 42-min 30 fps source, an estimate not an RSS measurement), uses nominal fps instead of PTS (wrong on VFR), and has a simple spike threshold. The port must stream bounded frames with timestamps. A 42-min source once blocked a queue for 5 h: trim long sources before queueing.

## 5. A-roll preparation (one 30 fps base)
1. Probe resolution, fps, rotation (camera originals may be rotated 90 degrees: `--rotate`), colour tags, audio channels.
2. If a rough cut exists: map it onto the camera original by audio cross-correlation in 2.5 s windows (16 kHz mono, 120-4000 Hz), then refine each boundary by picture matching. The rough cut's picture lagged its own audio by exactly 1 camera frame in the measured case.
3. Frame-exact trims + edge fix; grade via `speaker-color-correction`; pad to a multiple of 16 (1088 x 1920) so the 1088-canvas rule holds (`render-qa-delivery`).
4. Cut and grade in ffmpeg into ONE continuous 30 fps base clip with a short GOP (`-g 15`); HyperFrames renders graphics only. 15-22 separate 60 fps `<video>` clips with `data-color-grading` ran about 1 min per frame and hung; one base clip took the render from "hung ~8 min, 0 frames" to 3.5 min (the reference machine).
5. Every graded A-roll piece starts with a 6-frame pre-roll under the layer above (3 frames were not always enough: first frame ungraded or frozen 5 frames, then a jump). Check the first 3 frames after every return to A-roll.
6. Proxy: for a `.mov` > 1 GB or 4K work from `-vf scale=-2:1920 -c:v libx264 -crf 20 -preset fast`; the final render returns to the original; a `.mov` >= 5 GB is always worked through a proxy. Sources are read-only: copy, never touch.
7. One edit list generates `edit.json`, `cues.js` and the `<video>` windows; after every build re-run the audio carve (it was overwritten once). Anchor tweens to word cues, not frame literals (stale timing grids made logos invisible for two versions).

## 6. `edit.json` shape
`{"fps":30,"pieces":[{"id":"p01","src_in":12.34,"frames":96,"out_f":0}]}` with `frames` in OUTPUT frames. `src_in` and every time are rational-safe: derive seconds from integer frames at the stated fps, never from rounded floats (a guard comparing 38.1667 with 38.1666... failed once).

## Sources
d06-th §1.3-§1.4, §3.4 (cut_logic constants, source_cuts docstring, lessons B/C); distilled 02 video-types §2.4; distilled 06 asr-and-transcription §7; all checked 2026-10-02.

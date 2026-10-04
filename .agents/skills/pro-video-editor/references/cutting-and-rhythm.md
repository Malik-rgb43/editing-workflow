# Cutting and rhythm: where to cut, hiding joins, pace, clean windows

Merged on 2026-10-04 from the former type skills (one source per section, kept whole). Principles, not a template: use what fits the video in front of you and write the reason for each choice into PROMPT.md.


## The cut: natural order, silences, joins, hidden source cuts, A-roll prep
<!-- source: pro-video-editor/references/cutting-and-rhythm.md -->
Load when: producing the text of the cut, building `edit.json`, checking a join, handling a rough-cut source, preparing the A-roll base clip. Facts dated 2026-10-02; "d06-th" = distilled 06 talking-head-and-footage.

### 1. Structure defaults
- Default structure = FULL content with silences cut only, natural sentence order, whole sentences. Restructure ONLY if the author asks at intake ("silence-cut only, or rebuild?"). One restructure nobody asked for cost about 4 hours (5 drafts) until the author said "full length, only silence cuts" (d06-th §0.2).
- Reordering needs a strong reason and is shown as text first. Out-of-order speech and mid-sentence cuts ("מחליטים" without its subject) were rejected as "the cuts aren't good enough".
- Show the TEXT of the cut (or a 30 s audio-only cut) before building visuals; the author approves text with no render.

### 2. In-points, joins, slivers
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

### 3. Silence-removal constants (author's earlier reels tool; proven, not re-measured)
| Parameter | Value |
|---|---|
| Minimum pause to cut | natural 0.60 s / tight 0.40 s / aggressive 0.25 s (reels default: tight) |
| Minimum shot | 0.35 s |
| Padding | lead 0.08 s, tail 0.12 s |
| Cut position | 0.06 s inside the silence |
| Silence threshold | adaptive per clip, 20th percentile, range -55...-20 dB (two edit specs used -38/-40 dB and 0.12-0.25 s pauses) |
| Draft | `auto-editor <clip> --margin 0.08s,0.12s` (optional external tool; its 0.2 s default margin is a default to test, not a Hebrew editorial rule) |
Silence detection proposes; the editor decides. Re-check each edit point on the waveform +-2 frames.

### 4. Hidden source cuts (`source_cuts`)
A rough-cut source ("cuts roughly") contains jump cuts the author no longer sees. `source_cuts <source.mp4> --edit data/edit.json --thresh 4.0 --margin 6` decodes to a small grey raster; a cut = per-frame mean abs difference > 4.0 x the local median (window +-15 frames) + 0.3 AND > 3.0 absolute. Output `src_cuts.json` (source seconds) and, per piece, the cuts "at the in-point / out-point / mid-piece" mapped to OUTPUT frames with the advice "cover f(out_f-6)..f(out_f+6) with B-roll, or move the in/out point".
- Cover with >= 6 frames of margin on both sides, or move the point. An in-point 1 frame before a source cut leaves a 1-frame stale shot (5 such frames at one project's f680, f860, f1062, f1239, f1556).
- Verify in the BUILT `aroll.mp4` that every cut lands exactly on `out_f`; clone the clean first/last frame (tpad) at edges.
- Known limits (static review): the original decodes the WHOLE video into memory (about 6.17 GB analytic for a 42-min 30 fps source, an estimate not an RSS measurement), uses nominal fps instead of PTS (wrong on VFR), and has a simple spike threshold. The port must stream bounded frames with timestamps. A 42-min source once blocked a queue for 5 h: trim long sources before queueing.

### 5. A-roll preparation (one 30 fps base)
1. Probe resolution, fps, rotation (camera originals may be rotated 90 degrees: `--rotate`), colour tags, audio channels.
2. If a rough cut exists: map it onto the camera original by audio cross-correlation in 2.5 s windows (16 kHz mono, 120-4000 Hz), then refine each boundary by picture matching. The rough cut's picture lagged its own audio by exactly 1 camera frame in the measured case.
3. Frame-exact trims + edge fix; grade via `speaker-color-correction`; pad to a multiple of 16 (1088 x 1920) so the 1088-canvas rule holds (`render-qa-delivery`).
4. Cut and grade in ffmpeg into ONE continuous 30 fps base clip with a short GOP (`-g 15`); HyperFrames renders graphics only. 15-22 separate 60 fps `<video>` clips with `data-color-grading` ran about 1 min per frame and hung; one base clip took the render from "hung ~8 min, 0 frames" to 3.5 min (the reference machine).
5. Every graded A-roll piece starts with a 6-frame pre-roll under the layer above (3 frames were not always enough: first frame ungraded or frozen 5 frames, then a jump). Check the first 3 frames after every return to A-roll.
6. Proxy: for a `.mov` > 1 GB or 4K work from `-vf scale=-2:1920 -c:v libx264 -crf 20 -preset fast`; the final render returns to the original; a `.mov` >= 5 GB is always worked through a proxy. Sources are read-only: copy, never touch.
7. One edit list generates `edit.json`, `cues.js` and the `<video>` windows; after every build re-run the audio carve (it was overwritten once). Anchor tweens to word cues, not frame literals (stale timing grids made logos invisible for two versions).

### 6. `edit.json` shape
`{"fps":30,"pieces":[{"id":"p01","src_in":12.34,"frames":96,"out_f":0}]}` with `frames` in OUTPUT frames. `src_in` and every time are rational-safe: derive seconds from integer frames at the stated fps, never from rounded floats (a guard comparing 38.1667 with 38.1666... failed once).

### Sources
d06-th §1.3-§1.4, §3.4 (cut_logic constants, source_cuts docstring, lessons B/C); distilled 02 video-types §2.4; distilled 06 asr-and-transcription §7; all checked 2026-10-02.


## Cutting AI takes: clean windows, one look, native fps, sound as glue
<!-- source: pro-video-editor/references/cutting-and-rhythm.md -->
Load when: building the cut list, grading, conforming fps, planning sound, or reviewing a draft against the rubric. Naming: SKILL.md gates are G1-G10; the rubric criteria in `agent-content/benchmarks/ai-generated.rubric.md` are written R-G1..R-G8 here to avoid a clash.

Source keys: d05 = distilled/05 prompting §8-§9; d02 = distilled/02 video-types §6.4-§6.7 and qa-and-benchmarks §6.2. Numbers: owner benchmark sets (market n = 11 AI films, 10 of them 16:9, median 81 s; author's own n = 9, 7 of them 9:16, median 28 s) - small samples, owner tooling, not a lab experiment. Loudness numbers are house preset v1 (decision default Q5), not platform law.

### 1. Clean windows (gate G6)
- **Screen time = the clean window, 1.2-2.5 s** (market median shot 1.67 s). A 5-10 s generation yields one or two shots. Longer only when the long take IS the idea and it passes G1 frame by frame (`long_take_reason` in the cut list).
- **Never reverse a take** to fill time or close a loop (an owner series did it in 4 of 5 videos): generate another angle.
- Mark the window per take in `hf/TAKES.md`; reject a take whose artifact is inside the window you need. `python scripts/cutlist_check.py cutlist.json --probe takes_probe.json` errors on windows outside 1.2-2.5 s, reversed takes, an artifact inside a window without a cover, a window past the end of the take, and any fps mismatch.
- Pace (not blocking): 22-30 cuts/min (short 9:16 up to 35) vs market median 26 and the author's own median 8.5; first cut by 2.8 s (market median 2.79 s; author's own 9.5 s); a visual event at least every second (market 29/min vs the author's 11/min). Cut on sentence ends, SFX hits or music drops, not on a blind beat grid (market: cuts almost never on the beat).
- **Cover kit** for seams and unavoidable artifacts: 2-4 f directional-blur whip (`expo.out` in), 1-2 f white flash, 8-15 f black-blink + boom, dust/fog/bokeh overlay, letterbox. Every cover gets a sound.

### 2. One look (gate G7)
- One grade across real, AI and HTML layers: a shared LUT at 30-60 % (film-emulation LUTs, MPL-2.0 on the author's library; apply with FFmpeg `lut3d` before import and match on HTML layers with CSS filters), **global grain 3-4 %**, raised blacks, optional vignette; render `--sdr`. A declared look (black and white, 70s film, a cyan X-ray on near-black) counts as one look. Gate failure = each shot looks like a different model, or a visible real-vs-AI or sharp-HTML-vs-soft-AI gap.
- **Calm brand films override the stylised look:** the author rejected an S-curve, teal/warm split, halation, vignette, local subject lift and an AI upscale on a clinic film (2026-09-30). For calm/brand/clinic films: a gentle natural per-shot correction, consistent skin hue across cuts, no AI upscale; show a before/after at real size before ANY stylisation; send drafts in chat. (decision: later owner rule wins for that register)
- HDR/BT.2020-tagged takes (phones, some generators) switch a whole HyperFrames render to HDR: check with `probe_takes.py` (`hdr_suspect`) and render `--sdr`.

### 3. Native fps (blocking)
- Timeline and delivery = the **native fps of the takes** (verify each with ffprobe; usually 24). Never place 24p takes in a 30/60 timeline: the author's files showed about 22-34 unique pictures per second inside 60 fps (stepped cadence).
- Real 60p footage in a 24 timeline: interpret as 24 (2.5x slow motion) for B-roll moments; when real speed is needed conform with blending (`ffmpeg -vf "tblend=all_mode=average,fps=24"` or `minterpolate`), never plain frame dropping (2.5:1 = irregular judder). Real 30p -> 24: plain conform for static shots, blend for camera moves. `cutlist_check.py` compares rational fps, so 24000/1001 vs 24 is caught.

### 4. Sound as glue (rubric R-G7)
- An SFX on every transformation/transition (riser into a reveal, whoosh on whips, zap on an X-ray, sub-hit on "pain", impact on the logo), from a licence-checked library or synthesised; each cover gets a sound.
- Music edited: 100-175 ms of silence before the payoff (owner signature for launch/ad register), the drop exactly on the reveal, breakdown about -8 dB under dense VO, tail on the end card; duck 10-12 dB under VO; master -14 LUFS, TP <= -1 (two-pass loudnorm) measured on the FINAL file.
- `[CONFLICT]` sound register: calm brand/clinic films want ONE continuous uniform bed + subtle diegetic foley and no risers, gaps or drops (the later owner decision wins there); the SFX-on-everything rule is for the launch/ad/gag register.
- Real VO beats TTS for trust. Hebrew on-camera speech is unproven: record the real line, lip-sync with a route that accepts audio references (test ONE take), fallback VO over shots where the mouth is not visible.

### 5. Hook, text, closing
Frame 0 = the strongest AI image, moving by 0.5 s, with a Hebrew call-out of at most 6 words (the author's median "wow" arrived at 5.5 s: "the #1 fix"). Captions: white heavy rounded, soft shadow, 2-4 words, keyword in the accent colour at >= 4.5:1, bottom edge per the safe-zone table (house preset v1: Meta 9:16 y <= 1248), **proofread by eye**. End card every time: brand, CTA, address; a "Made with AI" line when the platform or client needs a disclosure (`consent-likeness-disclosure.md`). No small corner "feature pills".

### 6. Review rubric (R-G1..R-G8) - hard gates R-G1 (AI integrity), R-G3 (clean windows), R-G6 (one look)
Release: average >= 4.0 including the 10 general dimensions, no dimension < 3, and R-G1/R-G3/R-G6 >= 3 (a 2 or lower on one of them blocks showing the video); at most 3 review rounds. Critic: frame by frame at every transformation, looking for hands, bones, text and a product that changes; a timecode and a concrete fix for every score under 4. Full text: `agent-content/benchmarks/ai-generated.rubric.md`. The numeric scorer (`benchmark`) treats the market profile as 16:9 long form: length is information only. Owner's signature to keep when upgrading an older series: the cyan/orange X-ray look, the real->AI match transition on the body, captions at about 72 % height, a real-person VO; add what it lacked (X-ray in frame 0, trimmed windows, an SFX layer, global grain, anatomy QA against a reference, no reverse, an end card, -14 LUFS).

# Cutting AI takes: clean windows, one look, native fps, sound as glue

Load when: building the cut list, grading, conforming fps, planning sound, or reviewing a draft against the rubric. Naming: SKILL.md gates are G1-G10; the rubric criteria in `agent-content/benchmarks/ai-generated.rubric.md` are written R-G1..R-G8 here to avoid a clash.

Source keys: d05 = distilled/05 prompting §8-§9; d02 = distilled/02 video-types §6.4-§6.7 and qa-and-benchmarks §6.2. Numbers: owner benchmark sets (market n = 11 AI films, 10 of them 16:9, median 81 s; owner's own n = 9, 7 of them 9:16, median 28 s) - small samples, owner tooling, not a lab experiment. Loudness numbers are house preset v1 (decision default Q5), not platform law.

## 1. Clean windows (gate G6)
- **Screen time = the clean window, 1.2-2.5 s** (market median shot 1.67 s). A 5-10 s generation yields one or two shots. Longer only when the long take IS the idea and it passes G1 frame by frame (`long_take_reason` in the cut list).
- **Never reverse a take** to fill time or close a loop (an owner series did it in 4 of 5 videos): generate another angle.
- Mark the window per take in `hf/TAKES.md`; reject a take whose artifact is inside the window you need. `python scripts/cutlist_check.py cutlist.json --probe takes_probe.json` errors on windows outside 1.2-2.5 s, reversed takes, an artifact inside a window without a cover, a window past the end of the take, and any fps mismatch.
- Pace (not blocking): 22-30 cuts/min (short 9:16 up to 35) vs market median 26 and the owner's own median 8.5; first cut by 2.8 s (market median 2.79 s; owner's own 9.5 s); a visual event at least every second (market 29/min vs the owner's 11/min). Cut on sentence ends, SFX hits or music drops, not on a blind beat grid (market: cuts almost never on the beat).
- **Cover kit** for seams and unavoidable artifacts: 2-4 f directional-blur whip (`expo.out` in), 1-2 f white flash, 8-15 f black-blink + boom, dust/fog/bokeh overlay, letterbox. Every cover gets a sound.

## 2. One look (gate G7)
- One grade across real, AI and HTML layers: a shared LUT at 30-60 % (film-emulation LUTs, MPL-2.0 on the owner's library; apply with FFmpeg `lut3d` before import and match on HTML layers with CSS filters), **global grain 3-4 %**, raised blacks, optional vignette; render `--sdr`. A declared look (black and white, 70s film, a cyan X-ray on near-black) counts as one look. Gate failure = each shot looks like a different model, or a visible real-vs-AI or sharp-HTML-vs-soft-AI gap.
- **Calm brand films override the stylised look:** the owner rejected an S-curve, teal/warm split, halation, vignette, local subject lift and an AI upscale on a clinic film (2026-09-30). For calm/brand/clinic films: a gentle natural per-shot correction, consistent skin hue across cuts, no AI upscale; show a before/after at real size before ANY stylisation; send drafts in chat. (decision: later owner rule wins for that register)
- HDR/BT.2020-tagged takes (phones, some generators) switch a whole HyperFrames render to HDR: check with `probe_takes.py` (`hdr_suspect`) and render `--sdr`.

## 3. Native fps (blocking)
- Timeline and delivery = the **native fps of the takes** (verify each with ffprobe; usually 24). Never place 24p takes in a 30/60 timeline: the owner's files showed about 22-34 unique pictures per second inside 60 fps (stepped cadence).
- Real 60p footage in a 24 timeline: interpret as 24 (2.5x slow motion) for B-roll moments; when real speed is needed conform with blending (`ffmpeg -vf "tblend=all_mode=average,fps=24"` or `minterpolate`), never plain frame dropping (2.5:1 = irregular judder). Real 30p -> 24: plain conform for static shots, blend for camera moves. `cutlist_check.py` compares rational fps, so 24000/1001 vs 24 is caught.

## 4. Sound as glue (rubric R-G7)
- An SFX on every transformation/transition (riser into a reveal, whoosh on whips, zap on an X-ray, sub-hit on "pain", impact on the logo), from a licence-checked library or synthesised; each cover gets a sound.
- Music edited: 100-175 ms of silence before the payoff (owner signature for launch/ad register), the drop exactly on the reveal, breakdown about -8 dB under dense VO, tail on the end card; duck 10-12 dB under VO; master -14 LUFS, TP <= -1 (two-pass loudnorm) measured on the FINAL file.
- `[CONFLICT]` sound register: calm brand/clinic films want ONE continuous uniform bed + subtle diegetic foley and no risers, gaps or drops (the later owner decision wins there); the SFX-on-everything rule is for the launch/ad/gag register.
- Real VO beats TTS for trust. Hebrew on-camera speech is unproven: record the real line, lip-sync with a route that accepts audio references (test ONE take), fallback VO over shots where the mouth is not visible.

## 5. Hook, text, closing
Frame 0 = the strongest AI image, moving by 0.5 s, with a Hebrew call-out of at most 6 words (the owner's median "wow" arrived at 5.5 s: "the #1 fix"). Captions: white heavy rounded, soft shadow, 2-4 words, keyword in the accent colour at >= 4.5:1, bottom edge per the safe-zone table (house preset v1: Meta 9:16 y <= 1248), **proofread by eye**. End card every time: brand, CTA, address; a "Made with AI" line when the platform or client needs a disclosure (`consent-likeness-disclosure.md`). No small corner "feature pills".

## 6. Review rubric (R-G1..R-G8) - hard gates R-G1 (AI integrity), R-G3 (clean windows), R-G6 (one look)
Release: average >= 4.0 including the 10 general dimensions, no dimension < 3, and R-G1/R-G3/R-G6 >= 3 (a 2 or lower on one of them blocks showing the video); at most 3 review rounds. Critic: frame by frame at every transformation, looking for hands, bones, text and a product that changes; a timecode and a concrete fix for every score under 4. Full text: `agent-content/benchmarks/ai-generated.rubric.md`. The numeric scorer (`benchmark`) treats the market profile as 16:9 long form: length is information only. Owner's signature to keep when upgrading an older series: the cyan/orange X-ray look, the real->AI match transition on the body, captions at about 72 % height, a real-person VO; add what it lacked (X-ray in frame 0, trimmed windows, an SFX layer, global grain, anatomy QA against a reference, no reverse, an end card, -14 LUFS).

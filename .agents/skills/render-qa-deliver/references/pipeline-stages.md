# Pipeline stages: commands, points, guards

Load when: you are about to run any stage of preflight -> check -> snapshots -> range render -> full render -> QA. Dated 2026-10-02; sources: distilled 01 rules-and-gates E, D, H; distilled 03 tool-traps §1; blueprint QA_AND_BENCHMARKS §1. Command shapes use the ported student tool names; paths are project-relative. Times are from the reference machine (HyperFrames 0.8.79-0.8.98) and are examples, not promises.

## Stage 0 - readiness (seconds)
- `render_lock status` shows `free`; no Blender, matte, ASR, analysis or heavy agent running.
- All notes collected; all assets in (3D, stock, music, matte); Studio closed OR Studio's `data-hf-id` attributes stripped from `index.html` and `compositions/*.html` (they break patch anchors and the render).
- `_work/.render_start` touched right before the render (the freshness anchor).

## Stage 1 - static preflight (2-5 s)
`hf_preflight <hf> --strict` plus `grep -n 'data-start="-' index.html compositions/*.html` (must print nothing) plus the ledger-id grep. What it must block (each "burned a render" once):
| Level | Check | Why |
|---|---|---|
| E | `data-hf-id` left by Studio | breaks anchors/render |
| E | `dir="rtl"` on `<html>` / root | black render (version-scoped, G9) |
| E | sub-composition START != its host's start frame | a whole scene on a stale timing grid (logos invisible for two versions) |
| E | `F(n)` literals outside the host window | tweens that never play |
| E | duplicate id inside one composition | the second element steals the first one's CSS |
| W | `<video>`/`<img>` inside a preserve-3d or 3D-rotated parent | media composites in its own layer |
| W | visibility/opacity on a parent of a `<video>` | media ignores it: time the video itself |
| W | scale/filter tween aimed at a `<video>` | put it on a wrapper |
| W | opacity tween on a preserve-3d element | flattens 3D |
| W | video clip longer than its source | frozen tail frames |
| W | captions below y 1450 (9:16) | under the platform UI |
Exit 1 on any E, and on any W with `--strict` (run `--strict` before a final render). Known blind spots (E04-B06): regexes expected double-quoted attributes in one order, so a single-quoted duplicate id passed; the port must parse HTML structurally. Checks the owner asked for after incidents (not all implemented): caption exit present, look-alike glyph words, overlay card vs face box, every named element visible >= 1 frame, every tween inside its composition's duration, palette audit, PRE >= 6 frames, keyword width >= 800 px.

## Stage 2 - check (1-15 min)
`set -o pipefail; timeout 900 render_lock run -- npx hyperframes check --timeout 600000 | tee _work/check.log` (exit 0 required). The `--timeout` flag also raises the navigation minimum for graded clips ("Navigation timeout 10000 ms" otherwise). `--at-transitions --frame-check` only for short films and only if transitions changed: it samples every animation boundary and is very slow. `check` samples a small grid of points by default and a lint error silently disables the layout/contrast audits: a passing `check` is not a correct render.
Escape hatches change what `check` can see: `data-layout-allow-overflow` is inherited, `data-layout-allow-overlap` is NOT (mark the participant, never a scene root), `data-layout-allow-occlusion` goes on every text element including nested spans. Use the narrowest opt-out.

## Stage 3 - snapshots (1-2 min per pack)
`render_lock run -- npx hyperframes snapshot --at 3.20,7.93,12.00,15.47,19.10 --describe false` (<= 5 timestamps per call; the next batch is a new call; `--describe false` disables the remote-description branch only, not remote fonts or asset URLs). Look at EVERY point. Choose: mid-transition, first frame of each scene, every new effect AT PEAK intensity (light beam, morph at 25/50/75 %), every keyword at full size (look-alike letters), the speaker at the peak of every zoom. After round 1 only changed windows; the whole film only before the first critic. "Navigation timeout" -> bisect: remove media first, then images; convert heavy PNG plates to JPG/WebP; pre-cut ONE video element. A snapshot does NOT sync video around cuts: only a render proves a cut (frame diff at c-1..c+2: one spike = in sync, two spikes 1-2 frames apart = out of sync; `frame_qa` "double jumps").

## Stage 4 - Studio review and range renders
Studio hot reload (`preview --background`) shows an edit in 0.04-0.9 s (E12). Render a range only for what preview cannot show: `<video>` layers (about 1 frame offset), encoder-dependent edges, final audio. `hf_segment <hf> --from 26.0 --to 28.5 --qa` (or `--from f780 --to f855`): the range snaps OUTWARD to whole scenes; picture-only (no audio); output `_work/seg_<from>-<to>.mp4` + `_qa/`; several ranges run in sequence under the lock; a segment is cheap to kill when a new note arrives; a fix is "verified" when its segment is clean. Out-of-range media must be DELETED from the segment composition, not parked (a parked clip aborts the partial render with "captured 0 of expected"). Known limit: the wrapper's 1e-5 s timeline offset makes later units visually lossless (PSNR >= 46.8 dB at 720p CRF 0), not bit-exact; with offset 0 one tested unit was 150/150 identical (one no-video unit only). `seg_diff` (specified tool) proves a segment fix touched nothing outside the range.

## Stage 5 - the ONE full render
`touch _work/.render_start; hf_deliver <hf> --name <name> --draft --sheet` (draft: `--quality draft --gpu --sdr`; the AMD encoder `--gpu` is for drafts only) and, only after the preview is approved, the final (`--quality delivery --browser-gpu --sdr`, software x264 encode). `hf_deliver` steps: strip `data-hf-id` -> preflight (E stops; `--force` only for W with a written reason in CHANGELOG) -> render under the lock -> stale-file guard -> mux `assets/mix.wav` (render audio discarded) or two-pass loudnorm -> crop/re-encode if `data-deliver-width` differs -> verify. Set `FFMPEG_ENCODE_TIMEOUT_MS=3600000` (the 600,000 ms default killed a slow capture at frame 1348/1350). Read the render summary's second line: a silent fallback to screenshot capture roughly doubles time (6+ workers on one GPU, reported on Linux). Worker sweep on the 40 s heavy fixture (E11): 1 worker 132.6 s, 4 workers 92.8 s, 8 workers 88.1 s; capture is the bottleneck; browser GPU -12 %; a 720p proxy -20 %; `--gpu` encode no gain.
Windows issues reported open as of 2026-09 (re-check before relying on them): #4060 disk gate over-estimates raw RGBA (~16 GB per minute) -> `--workers 1`, `--low-memory-mode`, a roomy `--frames-cache-dir`; #4058 `spawn EBUSY` from antivirus locking ffmpeg.exe -> rerun; #4435 transparent first frame per worker shard -> `--workers 1` for alpha renders.

## Stage 6 - automatic QA on the NEW file
`[ "$V" -nt _work/.render_start ] || exit 1` first. Then `frame_qa "$V" --out "$Q/frames"`; `caption_qa "$V" --band <top>:1450 --x 140:888`; `face_center audit "$V" --tol 30` (speaker); `motion_qa "$V" --out "$Q/motion"`; `color_check "$V" --step 2 [--ignore a-b]` (person footage). Aggregate: `python scripts/qa_aggregate.py _work/qa/bundle.json --required frame_qa,loudness,caption_qa,motion_qa`. Every QA report starts with the file name and time. Thresholds and blind spots: `qa-thresholds.md`.

## Stage 7-9
Visual review: `visual-review.md`. Fix round: merge all reports into ONE numbered list in `hf/CHANGELOG.md` (an intent change goes to PROMPT.md first), one patch, stages 1-4 on touched ranges only, one full render, stage 6, stage 7 only on corrected ranges (the same reviewers verify their own findings). A reviewer who finds something new means the preflight is weak: add the check to stage 1. Delivery: `delivery-and-manifest.md`.

## Sources
distilled 01 rules-and-gates E, E.1, D; distilled 03 tool-traps T-01..T-35, e09-e12-final-results (E11, E12); blueprint QA_AND_BENCHMARKS §1, TOOLS_SPEC §2; checked 2026-10-02.

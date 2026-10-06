# Delivery: loudness, mux, 1088 canvas, naming, manifest, presenting

Load when: producing or verifying a final file, fixing loudness, delivering several ratios, writing the manifest, or presenting a draft. Dated 2026-10-02; sources: distilled 01 rules-and-gates H, J; distilled 05 audio-music-voice §7-§9; distilled 04 hyperframes-traps §1.4-§1.5; blueprint WORKFLOWS §5. Platform specifications are perishable and live in dated modules under `agent-content/references` (owned elsewhere); this file does not restate them.

## 1. Loudness: profiles and the measurement contract
| Destination | Target / limit | Status |
|---|---|---|
| House preset v1 (social video) | -14 LUFS integrated +-0.5; final true peak <= -1 dBTP; mix intermediate TP <= -1.5 | the author's chosen internal profile (decision default Q5), not a verified platform requirement |
| Spotify (music) | -14 LUFS; TP below -1 dBTP | verified for music only |
| Apple Podcasts | about -16 LKFS +-1; TP <= -1 | podcast only |
| EBU R128 | -23 LUFS, +-0.2 LU QC tolerance; production TP -1 dBTP | broadcast; a broadcaster's spec may be stricter |
| YouTube | official guidance gives codec/bitrate, NO LUFS target | viewer-side normalisation exists |
| Instagram/Reels, TikTok | no sourced numeric requirement; educator sources conflict (-14 normalisation, -16, -10 to -12 preferred); all agree TP between -1 and -2 dBTP | unverified |
| Client/broadcaster spec | the written contract | overrides the preset |
Terms: LUFS = LKFS (programme loudness); dBTP = true peak; dBFS = sample magnitude; dB = relative gain. A cue gain of -20 dB is not -20 LUFS and does not prove 20 dB under speech.
Measurement contract: measure the complete FINAL delivered stream AFTER encode and mux; bind the report to file SHA256, stream index, duration, channels/layout, sample rate, codec/bitrate, the exact FFmpeg build/filter and the destination profile. Report integrated loudness and true peak; LRA is not an acceptance metric below 1 minute. Silent, no-audio, too-short or decoder-failure results are never a green number; distinguish intentional silence from missing sound. Lossy decoding can overshoot: the -1.5 intermediate ceiling is headroom practice, not proof the final stays <= -1.

## 2. Mux and normalise (what `hf_deliver` does)
- If `assets/mix.wav` exists: `-map 0:v -map 1:a -c:a aac -b:a 320k -ar 48000 -shortest -movflags +faststart` (the render's audio is discarded). Else two-pass loudnorm `I=-14:TP=-1.5:LRA=11` on the render's audio with `-c:v copy`.
- `loudnorm` facts: linear mode needs all measured values from the exact processed input (`measured_I/TP/LRA/thresh`, `offset`) and can silently fall back to dynamic: inspect `normalization_type`. Dynamic mode upsamples to 192 kHz for true-peak detection: set the output rate to 48 kHz explicitly.
- A raw mix peaking above 0 dBFS makes the two-pass fall back to dynamic and crushes LRA (1.9 LU): pre-limit with `alimiter=limit=0.56` before both passes (LRA 3.4).
- The limiter + loudnorm shortened the mix by ~0.07 s and `-shortest` then cut 2-3 video frames: pad or trim the mix to exactly `DUR x 48000` samples after loudnorm (`apad` alone was not enough).
- Never chase loudness inside the composition (more gain came out QUIETER once). Out of range -> fix the mix (lower music/SFX peaks), then `hf_deliver --skip-render` (remux only, about 1 minute). `--skip-render` bypasses preflight and the freshness guard (static finding): bind the raw file to the build hash before using it after any visual change.
- Mix numbers (starting points, not listening-verified): VO lines -14.5 LUFS each + glue, music duck -10 dB (pre 80 ms, post 250 ms), VO >= +5 dB above music in the 1-4 kHz band (house heuristic), SFX -18...-26 dB under VO on visible events only, no dead air >= 0.4 s below -45 LUFS mid-film unless intentional; measure a 3 s-LUFS timeline for the whole film: no step > +3 LU at a cut unless intended. Never send audio you did not measure (a hand-assembled bed was 27.16 s with the tutti at 13.7 s instead of 15.54 s).

## 3. The 1088 canvas rule (scoped historical report; G9)
Reported 2026-09-28 on the reference machine (CLI 0.8.79-0.8.93): at width 1080 the encoder blackens the last 8 columns (x 1072-1079) in every mode, also in a plain FFmpeg `gbrp` chain; in RTL the right edge is where each line starts, so first letters can be clipped. Workaround: author `data-width="1088"` + `data-deliver-width="1080"`, `html,body{width:1088px!important}`, `#root{width:1080px!important}`, pad media to multiples of 16 (1088, 768); `hf_deliver` crops back (`crop=1080:1920:0:0`) and re-encodes (libx264, `-preset slow`, CRF 14 final / 20 draft, yuv420p, bt709) and its verify FAILS on a dead edge band; keep >= 24 px bleed under blur/scale entries. In FFmpeg grade chains `pad=1088:1920:0:0` before `gbrp` and `crop=1080:1920:0:0` at the end. NOT re-tested on 0.8.98 (E01 rendered 1080x1920 without an edge-band measurement). **Fixture to run per HyperFrames version:** a plain grey composition at width 1080 and at 1088, every quality/GPU mode, measure the right 8 columns of frames; compare with a plain FFmpeg chain to isolate encoder, build and pixel format; record version + date in `hf/QA.md`. Retire the workaround only after the paired fixture passes. Earlier 1080-wide deliveries probably carry the band.

## 4. Delivery spec (house defaults; each ratio is RE-LAID OUT, never cropped)
9:16 1080x1920 (Reels/Stories/TikTok/Shorts), 4:5 1080x1350, 1:1 1080x1080, 16:9 1920x1080; 30 fps default (60 only for dense motion when the source is truly 60; a 60 source shown at 30 renders at 30); H.264, SDR (`--sdr` always: a BT.2020 PQ/HLG source otherwise flips the render to HEVC 10-bit HDR), yuv420p, AAC 48 kHz 320k. A useful working export, not a universal platform requirement.

## 5. Naming, folders, manifest
- Name: the user's exact requested name wins; else `<name>_<platform>_<hook>_<aspect>.mp4`, aspect tokens `9x16`, `4x5`, `1x1`, `16x9`; "without" versions `<name>_hookA_nomusic_9x16.mp4`, `<name>_hookA_nocaps_9x16.mp4`; a platform token is mandatory when separate Meta/TikTok cuts exist; no name given -> a small Latin slug with an underscore. The previous delivery moves to `_work/delivered/v<N>/`.
- `final/` holds finals and `manifest.json` ONLY; drafts, tests, backups, segments and QA go to `_work/` (one project once had 15 drafts in the finals folder).
- `final/manifest.json`: per file `file`, `hf` (master dir or `hf_9x16`...), `src_hash`, `from_master`, `round`, `date`, `lufs`, `tp`, `qa`. `src_hash` = first 12 hex chars of `sha256(hf/index.html + hf/compositions/*.html + hf/cues.js + hf/assets/mix.wav)` computed BEFORE rendering. **"Ready" is rejected** when any file's `from_master` != the master's `src_hash`, or the current hf hash differs from the recorded one, or `qa` != `pass`, or `final/` holds a file not in the manifest (an old 1:1 once sat beside the v7 16:9 and 9:16). Show the mismatching files and re-render the missing derivatives. Hash/provenance claims need schema-level checks; write the manifest as a file, never inline.
- Derivatives: freeze the approved master (`src_hash`), one re-layout per ratio on a copy with the SAME `cues.js` and `assets/mix.wav`, derivative QA = stage 6 + axes 1 and 4. A bug found while porting is fixed in the MASTER and carried to every copy in the same round.

## 6. Verification before "ready" (H6)
`hf_deliver` PASS on the final file; stage 6 on the final file and stage 7 on ranges changed since the draft; `ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate,codec_name -of compact <file>` matches the brief; every ledger line ticked in `hf/QA.md`; manifest consistent; a final look at the first and last 2 seconds and the CTA frame.

## 7. Presenting (message format)
Open the file immediately in the browser pane (Studio for a draft; the contact sheets beside it), unasked: a path or a description in chat is not showing. Then a list NUMBERED IN THE USER'S ORDER AND WORDS (`1. ok "<note>" - cause - now (24.6-25.4 s / f738-762)`; unfixed items as numbered gaps with the reason and an alternative), the whole ledger (not only this round's lines), the QA line (`frame_qa 0, caption_qa 0, face audit 0, -14.0 LUFS / TP -1.3, rubric 4.2 (lowest: <dimension>)`), an honest score, open gaps, licence risks, and one closing question. Never present below the bar without detailing the gaps. A user may ask what process and tools were used: answer honestly.

## Sources
distilled 01 rules-and-gates H1-H7, J1-J6, G1; distilled 05 audio-music-voice §7-§9 (T07 LOUDNESS_SPEC); distilled 04 hyperframes-traps §1.4-§1.5; blueprint WORKFLOWS §5; checked 2026-10-02.

---
module: audio-mix
checked_at: 2026-10-02
expires: "180 days (2027-03-31); the destination-profile rows expire when a platform publishes a loudness requirement"
confidence: "house numbers [RULE-owner]/[PROVEN-internal] — starting points, not listening-verified best settings; destination standards [VERIFIED-external] scoped; no platform loudness requirement was verified"
refresh: "free: ffmpeg ebur128 on your own file, re-read the EBU/Spotify/Apple pages, re-run the controlled level test on the pinned HyperFrames"
---

# Audio mix, ducking and loudness — dated reference

| Field | Value |
|---|---|
| Fact set | loudness master (house preset v1), measurement contract, ducking and level numbers with their limits, mix signal chain, destination profiles, the render-attenuation trap |
| Versions / ids | FFmpeg 8.1 `loudnorm` / `ebur128` / `alimiter`; pyloudnorm (per-line normalisation); ITU-R BS.1770; EBU R128-2023 v5 (Nov 2023); HyperFrames 0.8.98 |
| `checked_at` | **2026-10-02** (= research date; **must be refreshed before use**) |
| Source | `distilled/05-…/audio-music-voice.md` §6-§9 (T07, owner mix tool read statically); `distilled/08-…/platform-specs-and-ai-disclosure.md` §7 |
| Scope / plan / region | social video masters (Reels/TikTok/Shorts/YouTube); **not** broadcast or podcast unless the profile says so |
| Confidence | tags per row; the numbers are **house preset v1 (decision default Q5)** to be proven by listening on real devices |
| `expires` | see front matter |
| Non-spending refresh | measure your own deliveries with `ffmpeg -i f.mp4 -af ebur128=peak=true -f null -`; read the standards pages; no accounts needed |

## 1. House master preset v1 `[RULE-owner]` (a choice, not a platform law)
**−14 LUFS integrated (±0.5), true peak ≤ −1 dBTP, measured on the FINAL encoded file** (never on the mix alone). The mix intermediate targets **TP ≤ −1.5** to leave AAC headroom. Delivery codec: AAC 48 kHz 320 k. **No numeric LUFS / true-peak requirement was verified for any listed platform** `[VERIFIED-external]` (negative finding; YouTube documents viewer-side Stable volume / Voice boost, which are not an upload target). TikTok/Reels sources disagree (−14 as normalisation, −16 "official", −10 to −12 "preferred"); all agree TP between −1 and −2 dBTP `[CONFLICT]` → default kept: −14 / −1.5, check after AAC encode. Label the destination profile whenever you measure.

## 2. Destination profiles (2026-10-01) — a hard-coded −14 would wrongly reject a correct podcast or broadcast file
| Destination | Target / limit | Status |
|---|---|---|
| house social-video | −14 integrated LUFS ±0.5; TP ≤ −1 dBTP final; mix TP ≤ −1.5 | `[RULE-owner]` |
| Spotify music | −14 integrated LUFS; TP below −1 dBTP (louder masters below −2) | `[VERIFIED-external]` scoped; not a video standard |
| Apple Podcasts | about −16 LKFS ±1; TP ≤ −1 | `[VERIFIED-external]` scoped; podcasts only |
| EBU R128 broadcast | −23 LUFS; QC tolerance ±0.2 LU (live exception 1 LU); production TP −1 dBTP; LRA not recommended for programmes < 1 min | `[VERIFIED-external]` scoped; broadcaster specs may be stricter |
| YouTube upload | 48 kHz; 1080p 8 Mbps (24/25/30 fps) / 12 Mbps (48/50/60); **no LUFS target on the inspected page** | `[VERIFIED-external]` (absence) |
| Instagram/Reels, TikTok | no sourced numeric requirement | `[SOURCED-unverified]`; sources conflict |
| client / broadcaster bespoke | the written contract overrides the house default explicitly | — |

Terms: LUFS = LKFS; dBTP = true peak; dBFS = sample magnitude; dB = relative gain. "A −20 dB cue gain is not −20 LUFS and does not prove 20 dB under speech."

## 3. Measurement contract `[IDEA]` spec
Measure the complete **final** stream after encode/mux. Bind the report to file SHA-256, stream index, duration, channels, sample rate, codec/bitrate, FFmpeg build/filter, destination profile. Report integrated loudness and true peak (momentary/short-term optional); LRA is not an acceptance metric below 1 minute. Result states: **pass / fail / not_run / unsupported / insufficient_evidence / error** — silent, no-audio, too-short or decoder-failure input never becomes a green number; separate intentional silence from missing sound. Normalise the accepted premix **once**; re-encode and measure the decoded final (lossy decoding can overshoot; the −1.5 intermediate ceiling is headroom practice, not proof that the final stays ≤ −1; fix with a controlled correction, not repeated destructive limiting).

`loudnorm` facts `[VERIFIED-external]` scoped: linear mode needs all measured values from the exact processed input; `linear=true` can silently fall back to dynamic — inspect `normalization_type`; dynamic mode upsamples to 192 kHz for true-peak detection so set the output rate explicitly (48 kHz); mono for stereo playback needs a dual-mono policy. Owner trap `[PROVEN-internal]`: a raw mix peaking above 0 dBFS makes two-pass loudnorm fall back to dynamic and crushes LRA (1.9 LU) — **pre-limit with `alimiter=limit=0.56`** before the two passes (LRA 3.4).

## 4. Mix rules and numbers (author's mix tool; read statically; limits stated)
| Item | Value | Limit / status |
|---|---|---|
| VO line, before gain | normalised to **−14.5 LUFS** (pyloudnorm), then per-line gain | `[PROVEN-internal]` |
| music duck under VO | **−10 dB**, 80 ms pre, 250 ms post, 0.12 s moving-average smoothing; the first rule with `t0 ≤ line start < t1` wins | default; over a loud drop duck only on the words (30/150 ms) and +2.5-3.5 dB for short lines `[PROVEN-internal]` |
| SFX under VO | an extra **−7 dB** while VO speaks; SFX sit **−18 to −26 dB** under the VO | `[RULE-owner]` |
| VO vs bed margin | every VO line should exceed music+SFX by **≥ +5 dB in the 1-4 kHz band** | a house heuristic, **not an intelligibility standard** |
| dead air | no gap ≥ 0.4 s below −45 LUFS (100 ms blocks) between 1.0 s and (duration − 0.2 s) | `[RULE-owner]` |
| music bed under speech | about 4 dB lower than an earlier default (volume 1.0 → 0.631) — "approximately" | prefer a premixed `mix.wav` so a level change is a remux |
| calm brand film | ONE continuous uniform bed (no block edits, riser, silence gap, drop) + subtle diegetic foley (events ≈ −7 LU, continuous machines ≈ −13 LU under the music); bed ≈ −16.5 LUFS; keep 3 s-LUFS steps under ~2 LU | `[RULE-owner]` genre rule |
| launch / ad film | sound on every event; drop on the reveal | `[RULE-owner]` |
| riser default | −19 dB, end-aligned | defaults of the tool |
| repeating SFX series | −15 dB, pitch scatter by resampling 2^(semis/12) | |
| third-party default bed | 0.12 (≈ −18 dB) under narration; 0.9 for a silent film | `[SOURCED-unverified]` |
Sidechain compression is optional and needs pump/transient listening tests; VO timing should govern duck envelopes `[IDEA]`. **Do not present these as listening-verified best settings.**

## 5. Signal chain (student tools: `hf_mix`, `hf_deliver`)
1. Three buses (music, VO, SFX), 48 kHz float; bed trimmed to DUR. 2. VO lines placed at their starts after the −14.5 LUFS normalisation. 3. Music duck envelope per VO span (minimum over [start − pre, end + post] = −10 dB, 0.12 s smoothing); SFX bus −7 dB over each VO span. 4. VO bus: `highpass=f=80, acompressor=threshold=-22dB:ratio=3:attack=5:release=90:makeup=1.6`. 5. Mix = music + VO + SFX; `alimiter=limit=0.56:attack=3:release=60:level=disabled` (≈ −5 dBFS). 6. Two-pass `loudnorm` pass 1 `I=-14:TP=-1.5:LRA=20:print_format=json`, pass 2 with the measured values, `linear=true,aresample=48000,apad`, 24-bit PCM, `-t DUR`. 7. **Pad/trim to exactly `DUR×48000` samples** — limiter + loudnorm shortened the file by ~0.07 s and `-shortest` cut 2-3 frames off the picture. `[PROVEN-internal]`
**`--report` diagnostics (20-60 s):** per-VO-line margin of VO over music+SFX in 50 ms blocks (full band and 1-4 kHz, 4th-order Butterworth band-pass; mark `LOW` below +5 dB); loudness every 0.5 s (K-weighted energy — not the standard 400 ms momentary / 3 s short-term unless validated); dead-air scan. **Known gaps (untested regressions):** hard-coded −14 profile needs a configurable destination; extra channels are sliced (needs an explicit downmix/reject policy); very short/silent voice, malformed cues, decode failures, codec true-peak overshoot, per-profile exit status.

Cost of each audio step (the reference machine `[LOCAL-only]`): mix report 20-60 s; remux ~1 min; full render 8-13 min (4-21 min in practice). An audio-only change = new mix + `hf_deliver --skip-render`, not a re-render (E12: 1.8 s of machine time on a synthetic fixture).

## 6. The render attenuation trap `[CONFLICT]`
`hyperframes render` once attenuated a premixed `<audio>` by ≈ 11.5 dB (−25.5 instead of −14 LUFS in one draft); in a 2026-09-28 tool test it did **not** reproduce (−14.7). Response: the delivery step discards the render's audio, muxes the pre-built `mix.wav` (or runs two-pass loudnorm on the render's audio with `-c:v copy`), then **measures the final file**. Before assuming the trap still applies run a controlled level comparison on the pinned engine/browser/route. Direct premix replacement is not claimed to be universally necessary.

Delivery gate (house): duration within 1 frame of `data-duration`, −14 ±0.5 LUFS, TP ≤ −1.0 dBTP, no black segment ≥ 2 frames, no dead edge band; exit non-zero on any failure; a gate that cannot run reports `not_run`.

## 7. Voice, music and SFX rights (summary; full rules in `licences-bom-rules.md`)
ElevenLabs Professional Voice Clone = **your own verified voice only**; OpenAI TTS requires clear end-user disclosure that the voice is AI-generated; Suno commercial use needs a permitted official download (terms effective 2026-09-03); Eleven Music self-serve prohibits music libraries/repositories/resale; Mixkit SFX may be used in rendered client videos but **never bundled in a repo/template/tool**; **unknown licence = do not use in client work**. Beat detection: `beat_this --gpu -1` (CPU) or `hyperframes beats`; librosa `beat_track` gives a suggestion grid, not downbeats or editorial intent. `[VERIFIED-external]` for the cited rights facts.

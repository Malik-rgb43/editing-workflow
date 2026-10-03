# Sound plan (brand sound on brand events) and the captions-off default

Load when: writing the sound lines of PROMPT.md, building `cues.js`, or when anyone says "add captions" to a motion piece.

Source keys: d05 = distilled/05 audio-music-voice (§4-§8), d04 = distilled/04 motion-design (§2.3, §2.3b), d02 = distilled/02 video-types (§5.7). Loudness numbers are **house preset v1** (decision default Q5): proven on the owner's work, to be proven on real devices by students; they are not platform law. The fuller dated mix numbers live in `agent-content/references/audio-mix.md` (owned elsewhere).

## 1. The sound plan is part of the spec, not the last step
Every beat line in PROMPT.md names its sound (a time, a sound, a level). Sound assets come BEFORE the build (VO, word timings, edited music with a map, SFX; times go into `cues.js`, the single source of truth for picture and sound).

| Layer | Rule | Number / limit |
|---|---|---|
| Music | edited to picture: build -> short take-away -> hit -> groove -> button; the drop lands ON the reveal; no energy dip after the climax; the music rings out to the last frame (no hard stop into dead silence, no dead air) | take-away 4-12 f (bass gap, low-pass, or 100-175 ms of silence) before a big hit; a section cut 0 to -1 f before the hit, never after; a big transition leads the drop by 3-4 f |
| Brand sound | the product's signature sound (for example a cha-ching) on **every** brand event from the first second: audible, not muffled | studio style (owner: "brand sound audible on every event") |
| SFX | only for what is visibly happening; start 1-3 frames BEFORE the picture (the thump lands on the frame the content moves, not on the click); not on every word; whips often need none; do not repeat the same sound twice in a row without pitch spread | -18 to -26 dB under the VO (a creative target relative to the VO: gain values do not prove the margin, listen level-matched) |
| VO | each line normalised, then glue; duck the music about -10 dB (80 ms pre, 250 ms post); over a loud drop duck only on the words (30/150 ms) and lift short lines +2.5-3.5 dB; VO at least 5 dB above the rest in 1-4 kHz | per-line target about -14.5 LUFS before gain (the owner's `hf_mix` default) |
| "Music is the SFX" | in `launch`, one dominant track (110-170 BPM) and almost no separate SFX layer; sync SFX to events, music to sections | the music is not beat-locked to every cut (17 % in the reference films) |
| Silence | silence or a hard stop about 0.7-1 s after the logo in short brand pieces; a 3-step ending (message -> promise/CTA -> symbol on a clean background, 2-3 s) | studio style; the "ring-out" rule overrides a hard stop in launches |
| Master | measured on the ENCODED FINAL FILE: -14 LUFS +-0.5, true peak <= -1 dBTP (intermediate mix TP <= -1.5), 48 kHz | house preset v1; do not copy the originals' -7 to -9 LUFS / TP up to +2.7 |

Calm brand films are the opposite register: ONE continuous uniform music window (the most uniform window of one track, started on a downbeat, fade in, ring out), subtle diegetic foley only (about -7 LU for events, -13 LU for continuous machines under the music), loudness steps < 2 LU across the film, no risers, silence gaps or drops (a "trailer" mix read as glitches; a +5-6 LU jump at a cut was audible). Screen tracks by tags: reject violin/sad/tender genres and noise-wash windows. (src: d05 §4.1; d04 §2.3b) `[RULE-owner]`, `[CONFLICT]` with the launch register - the later decision wins for calm films.

## 2. Procedure
1. List every visible event from the Events table; assign each a sound or "none" with a reason.
2. Synthesise a missing SFX when the library is imprecise (WebAudio offline or FFmpeg `aevalsrc`/`sine`/`anoisesrc` with filters) and write its time into the spec. Library sources must carry a verified licence: owner library items with `License: unknown` are NOT usable on client or paid work (decision default Q2); Mixkit-sourced files may not be redistributed in templates or the student repo.
3. Edit the music to the event map (low-pass sweep before a drop, splice so the first bass step lands on the event). Pre-limit a clipped bed before loudnorm (two-pass loudnorm falls back to dynamic mode on a raw mix above 0 dBFS and the loudness range collapses).
4. Phonetic check of brand names and heteronyms before the mix (see `seam-camera-event-tables.md` §4).
5. `hf_mix --report` (VO margin over the rest in the 1-4 kHz band, loudness every 0.5 s, dead air >= 0.4 s). Mux the mix over the picture and measure the FINAL file (`hf_deliver`); one draft once rendered a premixed `<audio>` 11.5 dB low, a later test did not reproduce it - measure regardless. An audio-only change = remix + remux (about 1 min), not a render.
6. Listen. An automatic transcript does not certify pronunciation or levels.

## 3. Captions: OFF by default in motion pieces (studio style, G9)
- A launch/kinetic/logo/explainer piece with big on-screen type carries **no captions** unless the brief asks for them. If the brief mentions sound-off viewing, offer captions in ONE line and wait; do not add them silently.
- If captions are requested: they belong to `hebrew-captions-asr` (ASR route, RTL, fonts, animation in and out, safe zones, QA). This skill only keeps them out of the way of the design (caption rail bottom <= y 1450 on 9:16, house preset v1) and out of the Events table's density count.
- Gate evidence: grep the composition for `caption` in ids/classes/data attributes and for caption blocks; the PROMPT `<direction>` states "captions off" or names the brief line that asks for them (`motion_spec_check.py` warns `CAPTION_MENTION` otherwise).
- Taste note: the owner's default caption face (Rubik Regular/600 small words, Black/900 keywords) is a default, not a law; the look-alike pairs ו/ז, ד/ר, ה/ח must be tested at full size before any other face (a condensed display face turned "לבזבז" into "לבובו").

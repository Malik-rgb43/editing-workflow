# Sound: bed, effects, silence, levels, accessible audio and captions

Merged on 2026-10-04 from the former type skills (one source per section, kept whole). Principles, not a template: use what fits the video in front of you and write the reason for each choice into PROMPT.md.


## Sound and licences for ads
<!-- source: pro-video-editor/references/sound.md -->
Load when: choosing music or SFX, building the licence rows, mixing, or when someone says "it's free to use". Sources: distilled 02 video-types §3.6, workflow §6.2; distilled 05 audio-music-voice §4-§8, §10; distilled 08 legal-and-licensing §6, §9, platform-specs §9 (2026-10-01). Not legal advice. Licence terms and platform scopes are perishable: dated rows live in `agent-content/references/platform-specs.md` section 5 and the licence register.

### 1. The licence rule (decision default Q2)
- **`License: unknown` = not in client or ad work.** The author's older rule ("unknown = organic only") is a RISK POSTURE for the author's own accounts, not a licence; the research reads unknown as "no permission established". Teach: unknown assets do not enter a client delivery or any ad.
- **A song match is not a licence.** A recogniser result names a track; it grants no master or sync rights. Trending sounds are placement-specific at best and not cleared for ads. Commercial songs and film/anime clips are out.
- **Third-party brand sounds and logos** (a payment-platform "cha-ching", a booking-site logo) are organic only; for an ad, get WRITTEN permission from the brand (`written_permission_file`) or use a licensed generic equivalent.
- **Per-asset rights record** (`hf/SOURCES.md`): file, licensor, licence name and version, plan, date, permitted media (paid social), territory, term, attribution, evidence file, `ads_allowed`, `placements`. A rendered MP4, a template, a stem and a repo asset are different deliverables with different rights.
- Allowed for ads (when the exact asset page agrees): CC0; Mixkit free licence (integrated end products only; never redistributed, so never in the student repo); Pixabay Content License (commercial and advertising allowed, no identifiable trademarks; keep the licence certificate for Content-ID disputes); Freesound CC0 per file; Pexels; paid subscriptions whose plan covers client work and paid ads (Artlist, Epidemic and similar: the plan decides; projects published during an active term survive cancellation, new projects after expiry do not); CC-BY with the credit recorded. Excluded: `unknown`, CC-BY-NC, unverified "no copyright" claims.
- **Scope is placement- and territory-specific:** the TikTok Commercial Music Library covers TikTok organic and paid only (campaign region and eligible placement), not YouTube, Meta or X; the YouTube Audio Library is YouTube-scoped; Meta commercial-music rights were not inspected (gap): do not infer ad rights from seeing a song in an organic picker. Stock tracks can carry Content-ID claims: keep certificates. Choose cleared ad music BEFORE making the edit depend on a trending track and budget the replacement time.
- AI-generated music and voices: the provider's terms decide (some self-serve tiers prohibit libraries/resale or restrict industries); an AI voice must be disclosed; a voice clone only of the speaker's own verified voice with a separate written release. AI stills resembling a real speaker: organic only, ask before paid use.

### 2. Entry, level and SFX policy (author's craft, house defaults)
- **Entry:** speech-led ads get a dry hook and music enters at 2.5-4.5 s; montage ads get music from frame 0 with the drop on the reveal; hybrid hook (B-roll + VO + headline): music enters under the hook at about -18 dB relative to the voice and swells at the first beat change. The music is cut to the picture (a take-away of 4-12 frames before a reveal, the drop on the reveal) and rings out; on the end card it continues to the end.
- **Level:** bed about -24 LUFS under the voice, swell in gaps, alone on the end card; silence as a weapon before the twist; **ONE loudness peak, on the logo/CTA**.
- **SFX:** plain caption word-pops are silent. SFX only on graphic entrances, transitions, the price/offer reveal and the logo: whoosh on whips, riser before the offer, a soft coin-type tick on the price, a click on rebuilt UI, an impact on the logo. SFX sit at about -18 to -26 dB under the voice and 1-3 frames BEFORE the picture; one SFX style per ad. In the author's 10 ads 7 had no SFX at all and 7 had true peaks at or above 0 dBTP: both are defects.
- **Mix gates:** voice at least 5 dB over music + SFX in the 1-4 kHz band per line (`hf_mix --report`); no dead silence; the final file measured: -14 +/- 0.5 LUFS, TP <= -1 dBTP (house profile; no platform numeric requirement was verified; label the destination profile). Fix levels in the mix and re-mux; never chase loudness inside the composition.

### 3. What the market references do (for calibration, not copying)
Music-to-cut sync is rare (0-37 % of cuts on a beat, BPM 107-139); loudness ranges from -6.5 to -24 LUFS (the house target is -14); in the author's ads the cut-on-beat ratio was about 1.3x chance. Sync is a craft choice, not a platform requirement.


## Sound plan (brand sound on brand events) and the captions-off default
<!-- source: pro-video-editor/references/sound.md -->
Load when: writing the sound lines of PROMPT.md, building `cues.js`, or when anyone says "add captions" to a motion piece.

Source keys: d05 = distilled/05 audio-music-voice (§4-§8), d04 = distilled/04 motion-design (§2.3, §2.3b), d02 = distilled/02 video-types (§5.7). Loudness numbers are **house preset v1** (decision default Q5): proven on the author's work, to be proven on real devices by students; they are not platform law. The fuller dated mix numbers live in `agent-content/references/audio-mix.md` (owned elsewhere).

### 1. The sound plan is part of the spec, not the last step
Every beat line in PROMPT.md names its sound (a time, a sound, a level). Sound assets come BEFORE the build (VO, word timings, edited music with a map, SFX; times go into `cues.js`, the single source of truth for picture and sound).

| Layer | Rule | Number / limit |
|---|---|---|
| Music | edited to picture: build -> short take-away -> hit -> groove -> button; the drop lands ON the reveal; no energy dip after the climax; the music rings out to the last frame (no hard stop into dead silence, no dead air) | take-away 4-12 f (bass gap, low-pass, or 100-175 ms of silence) before a big hit; a section cut 0 to -1 f before the hit, never after; a big transition leads the drop by 3-4 f |
| Brand sound | the product's signature sound (for example a cha-ching) on **every** brand event from the first second: audible, not muffled | studio style (owner: "brand sound audible on every event") |
| SFX | only for what is visibly happening; start 1-3 frames BEFORE the picture (the thump lands on the frame the content moves, not on the click); not on every word; whips often need none; do not repeat the same sound twice in a row without pitch spread | -18 to -26 dB under the VO (a creative target relative to the VO: gain values do not prove the margin, listen level-matched) |
| VO | each line normalised, then glue; duck the music about -10 dB (80 ms pre, 250 ms post); over a loud drop duck only on the words (30/150 ms) and lift short lines +2.5-3.5 dB; VO at least 5 dB above the rest in 1-4 kHz | per-line target about -14.5 LUFS before gain (the author's `hf_mix` default) |
| "Music is the SFX" | in `launch`, one dominant track (110-170 BPM) and almost no separate SFX layer; sync SFX to events, music to sections | the music is not beat-locked to every cut (17 % in the reference films) |
| Silence | silence or a hard stop about 0.7-1 s after the logo in short brand pieces; a 3-step ending (message -> promise/CTA -> symbol on a clean background, 2-3 s) | studio style; the "ring-out" rule overrides a hard stop in launches |
| Master | measured on the ENCODED FINAL FILE: -14 LUFS +-0.5, true peak <= -1 dBTP (intermediate mix TP <= -1.5), 48 kHz | house preset v1; do not copy the originals' -7 to -9 LUFS / TP up to +2.7 |

Calm brand films are the opposite register: ONE continuous uniform music window (the most uniform window of one track, started on a downbeat, fade in, ring out), subtle diegetic foley only (about -7 LU for events, -13 LU for continuous machines under the music), loudness steps < 2 LU across the film, no risers, silence gaps or drops (a "trailer" mix read as glitches; a +5-6 LU jump at a cut was audible). Screen tracks by tags: reject violin/sad/tender genres and noise-wash windows. (src: d05 §4.1; d04 §2.3b) `[RULE-owner]`, `[CONFLICT]` with the launch register - the later decision wins for calm films.

### 2. Procedure
1. List every visible event from the Events table; assign each a sound or "none" with a reason.
2. Synthesise a missing SFX when the library is imprecise (WebAudio offline or FFmpeg `aevalsrc`/`sine`/`anoisesrc` with filters) and write its time into the spec. Library sources must carry a verified licence: owner library items with `License: unknown` are NOT usable on client or paid work (decision default Q2); Mixkit-sourced files may not be redistributed in templates or the student repo.
3. Edit the music to the event map (low-pass sweep before a drop, splice so the first bass step lands on the event). Pre-limit a clipped bed before loudnorm (two-pass loudnorm falls back to dynamic mode on a raw mix above 0 dBFS and the loudness range collapses).
4. Phonetic check of brand names and heteronyms before the mix (see `seam-camera-event-tables.md` §4).
5. `hf_mix --report` (VO margin over the rest in the 1-4 kHz band, loudness every 0.5 s, dead air >= 0.4 s). Mux the mix over the picture and measure the FINAL file (`hf_deliver`); one draft once rendered a premixed `<audio>` 11.5 dB low, a later test did not reproduce it - measure regardless. An audio-only change = remix + remux (about 1 min), not a render.
6. Listen. An automatic transcript does not certify pronunciation or levels.

### 3. Captions: OFF by default in motion pieces (studio style, G9)
- A launch/kinetic/logo/explainer piece with big on-screen type carries **no captions** unless the brief asks for them. If the brief mentions sound-off viewing, offer captions in ONE line and wait; do not add them silently.
- If captions are requested: they belong to `captions-transcription` (ASR route, RTL, fonts, animation in and out, safe zones, QA). This skill only keeps them out of the way of the design (caption rail bottom <= y 1450 on 9:16, house preset v1) and out of the Events table's density count.
- Gate evidence: grep the composition for `caption` in ids/classes/data attributes and for caption blocks; the PROMPT `<direction>` states "captions off" or names the brief line that asks for them.
- Taste note: the author's default caption face (Rubik Regular/600 small words, Black/900 keywords) is a default, not a law; the look-alike pairs ו/ז, ד/ר, ה/ח must be tested at full size before any other face (a condensed display face turned "לבזבז" into "לבובו").


## Accessible captions and audio for testimonials
<!-- source: pro-video-editor/references/sound.md -->
Load when: building or checking captions, the mix or the final loudness. Sources: distilled 01 OWNER_STYLE §N (caption gates), distilled 02 qa-and-benchmarks §8.5-§8.6, distilled 05 audio-music-voice §5, §7-§8, distilled 08 platform-specs §5 (2026-10-01). Hebrew typography, fonts and timing in detail: `captions-transcription` and `agent-content/references/hebrew-rtl-captions.md` (owned elsewhere; this file lists only what a testimonial needs). House numbers are preset v1, not law (decision default Q5).

### 1. Captions (testimonial profile)
- **Wording is a legal and trust surface:** zero spelling errors in names, numbers, quotes and brand words; a human proofreads against the speaker's recording and the client's written spelling. ASR text is never final; no LLM rewrite of the full text; majority vote of several passes for an ambiguous word.
- **Style:** white heavy Hebrew sans with outline or shadow, no box (a dark 50 % box only over bright B-roll); 1-3 words per card, word-pop; the house default font is Rubik (Black for keywords, Regular for small words) as a default, not a law: test any other face at full size for ו/ז, ד/ר, ה/ח first; one keyword per card in the brand colour (numbers, pain words); digits instead of number words ("200 אלף ש״ח"); letter height 3-4.5 % of the frame.
- **Timing:** minimum word 0.25 s, card 0.9 s (creative heuristics validated by playback, not law); the card leads the voice by about 0.1 s; always animate OUT (mirror of the entry, about 4 frames, on an inner wrapper so the chunk's on/off stays the only show/hide); never a blank frame between cards, never two cards stacked.
- **Position:** centre about 63-73 % of height for organic; at most 58 % for paid Meta 9:16; at the seam (about 40 %) during a split-screen proof; the rail's bottom edge never below y 1450 at 9:16; key text inside the house safe zone (`video-variants-exporter/references/house-presets.md`). Captions never cover a face, a logo or the proof figure.
- **Reading speed and contrast (accessibility profiles, optional named presets, not law for social word-pop):** Netflix's Hebrew guidance names 17 characters per second for adult programmes and 13 for children, and 20 / 17 for SDH; do not transfer those thresholds to kinetic word reveals without declaring the character-counting rule. WCAG contrast 4.5:1 for normal text (3:1 for large text) measured on the SOURCE colours AND the compressed output: a dark brand colour on a dark frame fails (a measured example: `#29414a` on its background 1.3:1; a yellow on a light ceiling 1.63:1, fixed with a dark gradient so yellow and white both pass 3:1). A nominal pass does not establish comfortable reading: view it on a phone.
- **Hebrew/RTL:** `direction: rtl` only on text elements, never on the composition root; isolate Latin and numbers inside Hebrew lines (`unicode-bidi: isolate`); check mixed Hebrew/Latin/digits and punctuation on the final render, not on a screenshot of the editor.
- **Native vs burned:** burned captions fix typography and RTL but cannot be switched off and are invisible to screen readers; deliver a clean master (no burned text) and a timed text file (SRT) where the platform supports native captions (YouTube, LinkedIn, X Media Studio; the TikTok and Meta native routes are unresolved in the research); avoid duplicate native plus burned. A `nocaps` version is a variant (`video-variants-exporter`).
- **Beyond words:** essential non-speech information (a laugh that changes the meaning, music that carries the mood) is described in the timed text file where the platform allows it (SDH practice).
- **Gate evidence:** `caption_qa --band <top>:1450` WITH its coverage statement (a pass on zero sampled frames is not a pass), the human proofread, a mute test (the whole story understood without sound), and a phone viewing.

### 2. Voice and mix
- **Voice first:** the speaker must be intelligible: separate voice from street/car noise when needed (a two-stem vocals separation), then about 3:1 compression; never "enhance" the voice into a different one; no AI voice replacement.
- **Joins:** cut in the silence before a sentence, never after its first word; after any re-cut, transcribe the FULL assembled voice and diff its words against the intended text (a missing first or last word, or an extra residue syllable, is an error); drop slivers under about 6 frames.
- **Bed:** a soft music bed 12-18 dB under speech (a house default; the author lowered a talking-head bed by about 4 dB after feedback), swells in gaps, OUT for the crisis, back at the turn; music is edited to the picture and rings out to the last frame; an ad end card keeps the music to the end. A music bed must carry a licence valid for the placement (an ad needs an ad-cleared track; `License: unknown` = not in client work).
- **SFX:** captions are silent; at most one soft ding per proof entry and soft whooshes on punch-ins; SFX at -18 to -26 dB under the voice (a creative target, not a loudness measurement); only for what is seen.
- **VO margin:** voice at least 5 dB above music plus SFX in the 1-4 kHz band per line (`hf_mix --report`); a 3 s short-term loudness step larger than about 3 LU at a cut without intent reads as a bug.
- **Master:** -14 LUFS integrated +/- 0.5, true peak <= -1 dBTP, measured on the FINAL file after encode, labelled as the social house profile (no platform numeric requirement was verified; a client or broadcaster profile overrides). Fix levels in the mix and re-mux; do not chase loudness inside the composition. Two-pass loudnorm needs a pre-limited raw mix, otherwise it falls back to dynamic mode and crushes the loudness range.

## Common mistakes: voice, effects and caption timing
Load when: placing a TTS voice, a long effect or word-timed captions. Moved from SKILL.md on 2026-10-06 (each cost time on a real project).

| Mistake | Instead |
|---|---|
| Emotion tags on a TTS voice overdone ("warmly" whispers, "excited" sounds fake) | Light tags only on the lines that need them; the opener plain |
| A long SFX file placed by its start (a 4 s riser lands late) | Place it by its measured peak (`"align": "peak"` in the `hf_mix` cues), trimmed around the peak |
| Captions placed from one transcription pass (up to 0.5 s late) | Re-time per phrase (`tools/word_retime.py`): cut at pauses, transcribe each chunk, pin its first word to the measured onset |

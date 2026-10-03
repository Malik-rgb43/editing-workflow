# Ad rubric A1-A8, mute test and numbers

Load when: before presenting a draft, and when a critic scores one. Sources: distilled 02 qa-and-benchmarks §6.2 and video-types §3.10-§3.11 (2026-10-01); the canonical rubric file is `agent-content/benchmarks/ad-promo.rubric.md` (owned elsewhere; this is the working copy). Gates are A1, A2, A6: a gate at 2 or lower blocks presenting even when the average passes; a draft passes at an average >= 4.0 with no dimension < 3 (the owner's gate, historical, not research-proven).

| # | Criterion | 5 | 3 | 1 |
|---|---|---|---|---|
| A1 **gate** | offer and CTA | a number-bearing offer in the hook and again in voice, caption and card; price badge alone >= 2 s, its condition after; CTA in voice and text; card with WhatsApp icon + number, address or area, platform-button chevron (Meta versions only); code/CTA on screen >= 6 s | a number in a plain caption with no badge, or a card without contact | no offer and no CTA, a logo only (a vague offer or verbal-only CTA = 2) |
| A2 **gate** | brand within 1 s | the brand identified within 1 s inside the world; product on screen within 3 s | brand appears at 1-3 s or only unreadably in the background | brand revealed only at the end |
| A3 | hook (0-2 s) | the offer, a before/after or a visual shock at frame 0 with movement within 1 s; headline <= 6 words readable without sound | a call-out from a speaker with no visual | a preamble/story, or a logo/title card (a generic question or blurred frame 0 = 2) |
| A4 | pace and visual change | a change every <= 1.4 s; a hidden whip/crash cut at least once per 15 s; cuts on speech (speaker) or transients (montage); only the punchline or the end holds >= 3.5 s | a change every 2-3 s | a static speaker for most of the ad |
| A5 | proof and product | before/after same angle with a luma contrast; product macro; product in hands in >= 35 % of shots; real reviews/numbers; real UI rebuilt in code | features without proof | no product and no proof ("my customers say" with no customer, or stock instead of the product = 2) |
| A6 **gate** | legal sound and level | music licensed for ads (SOURCE row); -14 +/- 1 LUFS, TP <= -1 dBTP; an audible bed that rises alone on the card; SFX on graphic entrances, transitions, the offer reveal and the logo; plain captions silent; one peak, on the logo | legal and clean but no SFX; or TP between -1 and 0, or a level 3 LU off | a commercial song, `License: unknown`, or TP above 0: **disqualifying** |
| A7 | typography, safe zones, proofreading | caption signature with a brand-colour keyword and a quick pop; one font, <= 3 styles; everything inside the safe zones incl. the logo bug; no caption over a logo, sign or face; ZERO spelling errors | signature without emphasis | spelling errors in a name, address or brand, or broken RTL (a caption on a sign or outside the zone = 2) |
| A8 | length and versions | the lengths asked (default 15 and 30 s); 3 hooks on one body (`_hookA_/_hookB_/_hookC_`); every ratio asked plus no-music and no-captions versions; an end card of 2-3 s with music to the end | one hook only, or a 15 % length deviation | an end card of 5 s or more in silence, or black at the end |
Score under 4: a timecode and a concrete fix, for example "move '10 % for visitors from the ad' from 21.6 to 0.0 as a brand-colour badge with a pop and a coin SFX from a library licensed for advertising, and add WhatsApp to the card". Compliance: a claim, price, before/after or review not verified with the client lowers A1 or A5 to 1 until verified. Keep the client's approved style over the skill signature.

## Mute test
Watch once WITHOUT sound: the offer, the brand and the CTA must be understood from the screen alone. Then watch with sound for the hook, the entry of music, the offer reveal and the one loudness peak.

## Numbers (medians; small samples; check the unit)
| Metric | Market (10 refs, 16:9) | Owner (9 x 9:16 + 1 x 1:1) |
|---|---|---|
| duration s | 29.0 | 29.75 |
| cuts/min | 36.25 | 34.5 |
| median shot s | 1.04 | 1.59 |
| first cut s | 1.9 | 1.67 |
| visual events/min | 43.9 | 42.0 |
| LUFS | -15.95 | -14.2 |
| true peak dBFS | -1.55 | +0.15 |
| speech ratio | 0.34 | 0.57 |
| music ratio | 0.73 | 0.57 |
| SFX/min | 0 | 0 |
Reproduce with the project's benchmark scorer when it exists (`benchmark`, TOOLS_SPEC); the automatic cut count misses whips and light leaks: verify on frames. The market profile is a pacing target, not a format target (the references are 16:9 TV-style).

## Common mistakes and their fixes
No concrete offer (number in the hook + three touches); true peak above 0 (loudnorm + a TP gate); zero SFX (motion-synced palette); price as a caption (a price tag); brand only at the end (a bug or the product at 0 s); 46-53 s long (cut 15 s + 30 s versions); stock instead of the product (rebuilt real screens); misspellings (proof against the client's written spelling); commercial songs (licensed track).

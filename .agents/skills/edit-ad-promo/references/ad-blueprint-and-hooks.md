# Ad blueprint, hooks, offer, end card and visual grammar

Load when: scripting an ad, writing the offer ledger and hooks, designing the price badge and end card. Source: distilled 02 video-types §3 (2026-10-01). Numbers are the owner's analysis of 10 market references (all 16:9, TV-style) and 10 of his own ads (mostly 9:16): a pacing target, not a format target. No platform source verifies a universal 3-second hook threshold: everything below about hooks is editorial practice.

## 1. The bar (six points; house defaults)
1. Brand within about 1 s INSIDE the world (on the product, a wall, a shirt, a logo bug), never a title card; product within about 3 s (8 of 10 references).
2. A visual change at least every 1.4 s (cut, push-in, wipe, text build); one hidden whip/crash cut per 15 s.
3. A concrete offer with a number, three times (voice, super, end card); the code or CTA on screen for at least 6 s.
4. About 36 cuts/min (market, corrected), median shot 1.1-1.6 s; only the punch or the end holds 3.5 s or more.
5. -14 LUFS, true peak <= -1 dBTP; ONE loudness peak, on the logo/CTA.
6. Deliver 15 s + 30 s, 9:16, 3 hooks by default.

## 2. Blueprint (seconds in the cut)
| Beat | 15 s | 30 s | 45-60 s | Content |
|---|---|---|---|---|
| Hook | 0-2 | 0-3 | 0-3 | the offer, a before/after or a visual shock + the brand |
| Problem | 2-3.5 | 3-7 | 3-10 | one specific pain, cold grade |
| Product / solution | 3.5-6 | 7-13 | 10-22 | in hand, macro, process; warm grade |
| Proof / features | 6-9 | 13-21 | 22-38 | before/after, real reviews, rebuilt real UI (45-60 s: flash the offer here too) |
| Offer | 7-9 | 19-22 | 38-44 | price tag on screen at least 2 s in total, entering over the last proof shot; the condition line (deadline/terms) joins 0.9 s after the price |
| CTA to end card | 9-15 (card 12.5-15) | 22-30 (card 27-30) | 44-60 (card 57-60) | written CTA/code on screen >= 6 s AND spoken; music to the end |
Offer + CTA take 30-45 % of ads of 30 s and more (market 31-42 %), up to about 55 % in 15 s, 10-18 % for pure brand spots.

## 3. Hooks, ranked (rank by reason and write the reason)
1. **Offer as the first line** (a branch-opening discount stated in the first second).
2. **Before to after in 0-1.5 s**, same angle, live wipe ("this is the same kitchen").
3. **Visual shock that lands on the offer** (a slot-machine reveal of the discount; an impossible image).
4. **Contrarian claim** ("to renovate your kitchen you do not need a new kitchen"; a paradox).
5. **Specific pain or call-out** ("still managing trainees in a chat app and a spreadsheet?").
6. **Comic sketch or curiosity gap.**
Forbidden openers: a generic question over a static talking head; story preamble ("three years ago..."); hype without the fact ("yes, you heard right": put the concrete fact on screen at frame 0); a blurry frame 0; a logo or title card first; a silent 9:16 frame with no text. Hook text: a headline of at most 6 words in the top band for sound-off viewing (the market references show no text in the hook but they are 16:9 TV-style; for paid 9:16 this is the house recommendation, to be confirmed by the client's results). Batch default: 3 hooks A/B/C on ONE body (a green-screen-over-product hook, a reply-style overlay hook, a plain hook are three different tests).
External hook frameworks (recorded in the research, not re-checked, `[SOURCED-unverified]`): TikTok recommends the proposition within about 3 s and the hook within 6 s; Meta suggests messages in <= 15 s where possible and designing for sound off (captions extend watch time by 12 % on average, per a Meta page); ABCD (attention, branding, connection, direction) from a large ad study; PAS suits local services, AIDA suits product/offer, before/after suits renovations and detailing. Quote them as a source's advice with its date, never as a law.

## 4. Offer and CTA (the blocking gate A1)
- **A concrete offer always** (currency, %, "free", deadline). "A significant discount" is not an offer. If the client gave none: propose a low-friction one (trial class, free consultation or quote) and ask; NEVER invent. In the owner's own 10 ads only 2 had a number.
- The offer is not spoken in the footage: super + end card are mandatory; request a 10 s pickup from the client. An AI voice clone of a real person only with explicit written consent (default: no).
- **Price graphics:** a separate brand-colour tag, never caption style: digits + currency, pop-scale, a soft coin-type SFX from a licensed library, a struck old price only if the old price is real. "Free" offers: a "free" badge beside the service name, no strike-through, text colour chosen by contrast (white on gold measured 2.3:1 fails: use near-black on the pill).
- Urgency only if true; conditions on screen; exact strings from the ledger: `scripts/ad_gate_check.py` compares them.
- **CTA:** spoken AND written, starting at least 2 s before the end card; impact or sound logo on the logo; never 5 s of silence.
- **End card, 2-3 s:** logo, offer, WhatsApp icon + number (none of the owner's 10 ads had them: always add when the channel exists), phone/address/service area, "send us a message", and in Meta cuts a chevron bouncing down toward the platform button, ending above the bottom safe line. No chevron in TikTok cuts: end on the offer + "tap the button". WhatsApp/button graphics are information, not a fake clickable UI (Meta flags nonexistent functionality). Region-gated channels: confirm in the ads manager before showing them. Music continues to the end.

## 5. Visual grammar and captions
- **Pace:** dialogue shots 0.8-2.1 s, bursts 0.2-0.6 s; speech-led = cut on speech, montage = cut on transients. Two clusters in the references: story/dialogue 16-29 cuts/min (the picture still changes every 1.1-1.4 s through push-ins, wipes, UI, text builds) and montage 44-57 cuts/min. Automatic cut counts miss whips and light leaks: check frames.
- **Before/after:** same angle, "before/after" labels, 2x luma and cold to warm grade from pain to solution; with no "before" (services): process macro + result reveal, a real quote with consent, or a rebuilt screenshot of a real review. Never AI-"improve" a before/after.
- **Product:** slider macro, in hands in at least 35 % of shots, a 3D packshot where it pays; logo bug top-right inside the safe area; one brand colour in about half of the shots; app/UI = real screens rebuilt in HTML and animated (never stock).
- **Captions (word-pop signature):** white, heavy rounded Hebrew sans (Rubik/Heebo as defaults), soft shadow, no box, chest height (37-66 % of the frame), 1-3 words per card, 0.35-0.7 s hard swaps, one font and at most 3 styles; one keyword per card in the brand colour with contrast >= 4.5:1 (a dark brand colour measured 1.3:1: use the accent or a light tint); never over a logo, sign or face; proofread every name, address and brand word against the client's written spelling (three of the owner's ads shipped misspellings). The client's approved style beats this signature.
- **Safe zones:** `references/safe-zone-presets.md`; check at hook, offer, end card.

## 6. Hook-variant batch (hand-off to `multi-video-variants`)
One body; the hook is a sub-composition bound to variables; the same rows run in each aspect root; add `nomusic` and `nocaps` rows. Naming `<name>_<platform>_hookA_9x16.mp4`. Status: batch variables untested in a project: render ONE variation first. TikTok cuts: respect the TikTok row of the safe-zone table (keep both sides clear for a Hebrew UI); CTA = the TikTok button or an instant form; music from a library whose licence row allows TikTok ads (trending sounds are not cleared).

## 7. Client assets checklist
Logo (SVG), colours, font; the offer in writing (number, terms, deadline, disclaimer); WhatsApp number, phone, address/branch, service area, site; vertical 60 fps B-roll (process, product macro, same-angle before/after); owner-to-camera with 3+ hook lines; real reviews/stars WITH consent; app screenshots; consent of people in frame. Missing offer, logo or colours: ask, never invent.

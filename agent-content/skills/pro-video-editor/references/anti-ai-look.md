# Anti AI look: captions, motion graphics, type and layout

Load when: building captions or any graphic (Step 4), before the draft render (Step 5), and whenever a note says "looks AI", "generic", "template", "cheap", "CapCut", "robotic". Written 2026-11-09 from the author's review rounds, the motion kit (`motion-kit/RULES.md`, MIT, Hugh Phan) and the banned lists already in `visual-beats.md` section 8 and `story-and-structure.md`. Editorial practice, not measured.

The AI look is not one mistake. It is the sum of defaults: every choice left at the value a tool or a model reaches for first. Viewers do not name it; they feel that nobody decided. So the cure is the same everywhere: **every visible choice has a reason you can say in one line**, and nothing is on every beat.

The static scan `python agent-content/skills/pro-video-editor/scripts/ai_look_scan.py <project>/hf` finds the code-level tells (rule ids below). It is a warning list, not a verdict: a tell with a written reason in PROMPT.md stays. Looking at the frames is still the judge.

## 1. Captions

| Tell (reads as auto-captions) | Why it reads as AI | Instead |
|---|---|---|
| Every chunk animates in the same way (fade up ~24 px, pop, slide) `[AL03]` | a machine applied one preset; speech has no such rhythm | a chunk that takes over from the previous one **swaps on the same frame** (a cut); only a chunk next to a pause gets a short entrance / exit (about 0.1-0.15 s, a few px at most, decelerating in and accelerating out: the house law is in AND out, `caption_qa`) |
| Every word pops or scales (0 -> 1.2 -> 1), bounce or elastic `[AL04]` | the CapCut / auto-caption signature | no overshoot on captions at all; emphasis comes from weight or colour, not movement |
| A highlight colour on a word in every chunk, karaoke on every word | emphasis on everything is emphasis on nothing | at most ONE emphasised word per chunk, and only when that word carries the point; many chunks have none |
| Random keywords in yellow / green with no meaning | the colour carries no information | one accent colour from the project palette, used for one meaning (the number, the name, the promise) |
| Emoji added to captions `[AL09]` | auto-caption tools add them | none, unless the speaker's brand already writes that way |
| ALL CAPS + thick black stroke + drop shadow on every line | the stock "viral caption" preset | the project's type system (`type-and-colour.md`); contrast from a solid shape or a measured backing, not stroke + shadow + glow together |
| Chunks broken by word count (3 words, 3 words, 3 words) | the cut ignores meaning | chunk by meaning and breath: a phrase, a pause, a comma; 1-6 words, uneven on purpose |
| Caption early or late against the voice | a timing default, not the word timings | starts on the word's own timestamp (`tools/word_retime.py`), never before; ends with the last word's sound, with the minimum reading time from `caption-timing.md` |
| Caption over the mouth or the eyes, or fixed in the dead centre whatever the shot | nobody looked at the frame | placed per shot: below the face, inside the platform safe zone (`safe_zone_check.py`), moved when the framing moves |
| The caption repeats text already on screen | two places say the same thing | drop that chunk (`type-and-colour.md`, "one place for each word") |
| A soft fade-out on every chunk `[AL03]` | the same preset on the way out | a chunk cuts off when the next one starts; a short accelerating exit only where a pause follows |

## 2. Motion

All curves and timing come from the motion kit (`references/camera-and-motion.md`, "Easing and timing"). The tells it fixes:

| Tell | Instead |
|---|---|
| One named preset on every tween (`power3.out`, `power2.out`, CSS `ease`), or `gsap.defaults(...)` `[AL01]` `[AL02]` | a curve per move and per property, chosen by what the move is (`kit.land`, `kit.heavy`, `kit.leave`, `bez(...)`) |
| Every move 0.3-0.6 s | duration from distance and weight: `MotionKit.dur(px, weight)` |
| Even staggers (`i * 0.1`, `stagger: 0.08`) `[AL05]` | one element leads, the rest react at uneven offsets: `MotionKit.react(i)` |
| A visible move on `ease: "none"` / `linear` `[AL06]` | linear only for a proxy that is not itself the motion (a face-follow index, a video time) |
| Fade up from ~20-30 px on everything `[AL03]` | decide what the move IS first: cut on, type on, settle tracking, thrown on an arc, wiped by a mask |
| Blur-in (`filter: blur(...)` animated from a value to 0) `[AL07]` | blur belongs to fast motion (render-time motion blur), never to appearing |
| Bounce / elastic / back on everything `[AL04]` | decelerating curves; a spring at damping 1; overshoot only as a chosen device, once |
| Static holds: the frame dies between moves | a slow drift on the camera or a wrapper, a living detail; stillness only when it is the point |
| Exits as slow as entrances, or fade-outs in place | exits about 0.65x the entrance and accelerating out of frame (`exitTo`) |
| The same transition twice | one signature device per piece; the rest are cuts with a reason |

## 3. Graphics, type and layout

| Tell | Instead |
|---|---|
| The "vibe-coded card": dark rounded card + icon + title + grey placeholder bars | show the real thing: the real UI rebuilt, the real screenshot, the real number, the real logo (`visual-beats.md`) |
| Glow on static text, neon text-shadow, shimmer or gradient-filled text `[AL08]` | flat colour from the palette; glow only on a light source |
| Drifting glow orbs, particles, lens flares as filler | an empty area stays empty, or carries the next piece of information |
| Small uppercase tracked labels / feature pills ("NEW", "QUANTITY BREAKS") `[AL10]` | meaning goes through the voice and large type; a label only when the viewer must read it |
| Glass (`backdrop-filter`) on everything | glass once, where depth helps; never a whole-film layer |
| Purple-to-blue gradient, the default UI font (Inter, Poppins, Montserrat) as the whole system `[AL11]` | the brand's palette and type, or a reasoned choice written in PROMPT.md `<direction>` |
| Everything centred and symmetric | a grid with one focus per frame; asymmetry where it leads the eye |
| A generic icon for the noun (a plane for "flights") | the thing itself, or a metaphor for the point, not the noun |
| Every element the same size and weight | one focal element per frame; the rest clearly secondary |

## 4. Sound

| Tell | Instead |
|---|---|
| A whoosh on every move, a riser before every section | sound where something physically happens or where the edit wants a beat; silence is a choice too |
| Music at one level under the whole piece | ducked under the voice, with shape (in, lift, drop-out at the centre: `sound.md`) |
| A stock "cha-ching", "ding" or record scratch as punctuation | a sound designed for this moment, or none |

## 5. How to check before showing a draft

1. Run `ai_look_scan.py` on the composition folder; fix each warning or write its reason in PROMPT.md.
2. Look at a contact sheet of the whole draft (one frame every 2-3 s): if three frames in a row could come from any video, those beats are generic. Replace them, do not polish them.
3. Scrub every caption window at full size for one minute: does the emphasis follow the meaning, and does the rhythm follow the voice?
4. The fresh-eyes critic (`agent-content/benchmarks/critic-brief.md`) gets this file and lists every tell it sees, with timestamps.

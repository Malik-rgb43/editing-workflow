# Rubric: montage (footage + music, no voice: event recap, travel, behind the scenes)

> Status: **provisional, derived, unmeasured.** Written 2026-10-08 from the montage register in `pro-video-editor` (`references/story-and-structure.md`, `references/cutting-and-rhythm.md` section Montage). There is no delivered montage project behind it yet; its numbers are house defaults, labelled as such.
> Companion files: [critic-brief.md](critic-brief.md) · [visual-review-4-axis.md](visual-review-4-axis.md) · the montage section of `pro-video-editor/references/cutting-and-rhythm.md`.

## 1. How to score
Same rules as every rubric (README): score only what you saw and heard; `not_observed` is not 3; `N/A` needs a reason; 1-5 with anchors at 1 / 3 / 5; severe failures are listed apart and block. Hold lengths are judged against the tone chosen in PROMPT.md (counted in beats of the track), not against a fixed number.

## 2. Dimensions (1 / 3 / 5)

| Dimension | 1 - material failure | 3 - usable with repair | 5 - strong |
|---|---|---|---|
| **Meaning / story** | a pile of clips in shooting order with no arc; the best moment buried in the middle; it ends on a random clip | a clear start and end, but the middle sags or repeats one kind of moment | an arc you can name in one sentence (arrival -> build -> peak -> release); the peak is the emotional centre, and the last shot closes the story |
| **Caption / language** (text cards, names, date) | a misspelled name or a wrong date; text over faces | correct text, but cards interrupt the flow or sit on busy picture | text only where it adds a fact, correct, readable, off faces, in the chosen language; `N/A` when there is no text |
| **Composition / brand** | mixed aspects or letterbox jumps; a grade that changes clip to clip | one aspect and one grade, but some clips are badly framed for the delivery ratio | one aspect, one grade across all sources; every clip reframed for the ratio; hero shots composed to be held |
| **Motion / edit** | cuts that ignore the music; clips that end on a frozen or repeated frame; the same shot size many times in a row | cuts mostly on the beat; some clips run past their action; a few same-size runs | cuts placed on the beat grid by intent (not on every beat); each clip cut before its action ends; varied shot sizes; hero shots held longest |
| **Audio** | music cut mid-phrase at the end; a hard music start; clips' own sound fighting the bed | the track fitted to the length, but the peak misses the hero moment, or no dropout | the track's strongest rise lands on the hero moment (`music_fit`); one dropout where the clip's own sound carries alone; ambience under the hardest joins; the end rings out or lands on the hit; loudness on target |
| **Integrity / continuity** | people shown without consent; an unlicensed track; a private moment | consent and licence recorded, but one placement outside the licence's scope | every person consented, the track licensed for this placement (licence row), nothing private |

## 3. Hard gates
| Gate | Predicate | Evidence |
|---|---|---|
| **MO-G1 music licence** | the track's licence covers this platform and use | the licence row in PROMPT.md / SOURCES |
| **MO-G2 no frozen tail** | no clip ends on a repeated or frozen frame | `frame_qa` on the final file + the contact sheet |
| **MO-G3 hero holds** | each of the 2-4 `hero` beats holds longer than its neighbours | the storyboard `hero` marks against the cut list |
| **MO-G4 one look** | one aspect and one grade across all sources | a contact sheet across the whole film, looked at |

## 4. Severe failures (block alone)
The music ends mid-phrase with no fade; a person shown who asked not to be; a frame of another video's watermark; the wrong event, name or date.

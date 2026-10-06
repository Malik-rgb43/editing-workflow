# The moodboard + storyboard page

Load when the plan has any beat beyond the source footage, captions, music and cuts (Step 3b). Tool: `scripts/storyboard_board.py` (stdlib; `grab` needs ffmpeg). Built 2026-10-06; tested by its unit tests and one demo spec in a browser; no real user session measured yet.

## Why it exists
The user judges the video by eye. A beat table in chat ("0:02 B-roll: hands plating") lets each person picture something different, and they only find out at the draft, after the expensive work. The board shows the look and a real frame of every beat before any composition code. It turns "I imagined something else" into a cheap note on one card.

## 1. Where every frame comes from
| Beat | `roll` / `source` | The frame | How |
|---|---|---|---|
| The speaker / own footage | `A` / `own` | the REAL source frame at `src_t` | `storyboard_board.py grab storyboard.json --video <source or camera original>` |
| Own cut-away (a phone photo, a clip of the room) | `B` / `own` | that photo, or a frame of that clip | copy or `ffmpeg -ss T -i clip -frames:v 1 -vf scale=540:-2` |
| Stock (Pexels) | `B` / `stock` | the provider's preview image of the exact file | download the preview only; a licence row per file (`references/honesty-and-rights.md`) |
| Generated shot | `B` / `generated` | a sketch card ("planned: not made yet") with `cost` | a real still only after `paid-spend-gate` approved it (`image-prompt-writer`, start frame of the shot) |
| Graphic / text / UI / 3D | `G` / `graphic` or `sketch` | a quick HyperFrames mock snapshot, or a sketch card | `hyperframes snapshot --at <t> --describe false` on a throwaway mock; never block on it |
| Mood reference (someone else's) | `mood.refs[]` (optional, 0-12) | the reference frame | labelled "not ours, mood only" on the page; never used in the video; none given = none |

Frames are about 540 px wide (each image at most 2.5 MB). Every image is embedded in the page, which loads nothing from the internet.

## 2. storyboard.json
```json
{"title": "Chef reel - storyboard v1", "project": "chef_reel", "lang": "he", "aspect": "9:16",
 "story": "a chef who opened a restaurant shows every dish being built in front of you",
 "mood": {"feel": "warm, close, fire and iron; night in the kitchen", "palette": ["#1C1917", "#F5F0E8", "#D4A72C"],
          "type": {"family": "Rubik", "sample": "the real caption or title line"}, "signature": "an order ticket stamped on every dish",
          "refs": [{"img": "refs/side-light.jpg", "caption": "the yellow side light"}]},
 "beats": [{"id": "b1", "t": 0.0, "end": 2.2, "roll": "A", "source": "own", "src_t": 41.3, "line": "I opened a restaurant",
            "shows": "the chef to camera, close", "move": "push 1.00->1.04", "why": "the face is the promise"},
           {"id": "b2", "t": 2.2, "end": 3.6, "roll": "B", "source": "own", "img": "frames/b2.jpg", "line": "every dish",
            "shows": "hands placing a leaf on the plate", "why": "shows the sentence"},
           {"id": "b3", "t": 3.6, "end": 5.0, "roll": "G", "source": "sketch", "line": "is built in front of you",
            "shows": "the order ticket gets stamped", "why": "the signature device"}]}
```
- `t`/`end` are the output timeline seconds, in order. They are the same beats as PROMPT.md `<structure>`: one source of truth, so write both together.
- `line` is the voice under the beat (from the word table), `why` is the editor's reason (principle 3), and `move` is the camera or transition with its numbers.
- `check` refuses the following:
  - an A-roll beat that is not own footage, or that has no real frame;
  - a beat without an image that is not a sketch or a planned generated beat;
  - a generated beat with no `cost`;
  - placeholder text;
  - fewer than 3 beats;
  - a palette that is not `#RRGGBB`.

## 3. Serving and the answer
```
python scripts/storyboard_board.py check _work/storyboard/storyboard.json
python scripts/storyboard_board.py grab  _work/storyboard/storyboard.json --video source/<file>
python scripts/storyboard_board.py serve _work/storyboard/storyboard.json --out _work/storyboard   # BACKGROUND command
```
- Open the printed url in the browser pane. On each card the user can approve everything or write a note, and there is also one general note.
- The command exits with one of two answers:
  - `approved`: write `STORYBOARD APPROVED <date>` in `hf/CHANGELOG.md` and lock the beats in PROMPT.md.
  - `notes` plus numbered lines (`1. [b2 B-roll 0:02.20-0:03.60] "closer"`): answer each note with a new frame, a new beat or a stated reason to keep it, then serve again.
- No background commands in the host: run `build ... --out DIR` and send the page. Its buttons save `storyboard_review.json` for the user to attach.

## 4. What a good board looks like
- The A/B rhythm bar shows contrast: no stretch of more than about 6 s of one roll unless the face is the point (principle 5).
- Every B-roll beat shows its sentence (principle 14). If you cannot name what a frame proves, the beat is generic: replace it before you show the board.
- One signature device, visible on at least one card.
- The board's palette and type are the ones that DESIGN.md will lock. The caption style board (when there are captions) comes before this board, and its picks appear here.

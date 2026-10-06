# Caption modes, timing recipe, entrance and exit, safe zones, QA

Load when: building or retiming caption cards, adding the exit animation, positioning captions, writing the coverage statement. Dated 2026-10-02; sources: distilled 06 hebrew-rtl-and-captions §3, §5; distilled 02 techniques §6.1; distilled 01 rules-and-gates N. Status words: [owner rule] = said by the author; [proven] = worked in an owner project; [house] = house preset v1, overridable (decision default Q5).

## 1. Two timing modes (`pro-video-editor` says which)
| | Word-pop (reels, ads, premium talking head) | Sentence captions (Netflix/BBC style; only when asked) |
|---|---|---|
| Words per card | 1-3 | 1-6 |
| On-screen time | 0.35-0.7 s per card | minimum 5/6 s (0.833 s) |
| Reading rate | follows the speech | <= 17 characters per second |
| Lines | one line | <= 42 characters per line, <= 2 lines |
| Swap | overlap 1-2 frames (below) | gap of 2 frames |
| Grouping `words.json` words | 1-3 per card (or 1) | up to 6 per card + merge |
The 17 cps / 42 character numbers come from a different project's `caption_logic.py` and are not re-verified; Hebrew cps limits are profile-specific. Do not apply them to word-pop. Motion/launch videos: no captions by default (offer in one line only if the brief mentions sound-off) [owner rule]. Reels with sound vs muted: plan for both [CONFLICT in sources].

## 2. Dwell and timing numbers (per mode; the three sources differ: word 0.25-0.3 s, cue 0.35-0.7 s, card >= 0.9 s)
- Word on screen >= 0.25 s; card >= 0.9 s; last word of a card >= 0.25 s (in fast speech the last word otherwise showed 0.1 s then empty frames) [proven].
- Lead the voice by 0.08-0.1 s; clamp `start = max(0, start - lead)`; a negative `data-start` shifts EVERY clip about 2 frames and breaks the first frames; `grep -c 'data-start="-' index.html` must print 0 [proven].
- Words sit in their FINAL slots on a centred line from the start (no centre-growth, no sliding from the edge): a long line growing from the centre cut "לחפש" at the left edge, and the exit began before the last word landed [proven].
- Word-by-word animation, not letter-by-letter [owner rule]. Entrance default (Apple-like): per word opacity 0 -> 1, y +16 -> 0 (large words +22, scale 0.97 -> 1), blur 10 -> 0 over 0.42-0.5 s, `power2.out`, no overshoot; tracking -0.02em on large words, 0 on small [proven; the author asked for the behaviour, the numbers are an implementation].
- Easing vocabulary: `cubic-bezier(0.22,1,0.36,1)`; blur-out-up for words.

## 3. The exit is mandatory (author's latest decision; it overrides an earlier prompt that prescribed hard swaps)
- Default exit = the entrance mirrored: blur-out-up, rise 10 px + blur 6 px + fade over the last ~4 frames (`caption_lint` requires >= 3). Exit shorter than entrance (about 0.22 s).
- The exit tween runs on an INNER wrapper; the card's on/off stays the only show/hide, so it is seek-safe.
- The next card's first word starts 2 frames early: the group is hidden until its start, so on the swap frame that word is at ~70 %, not 0. Entering from opacity 0 exactly on the swap frame produced a blank frame at every swap (found only by the every-frame check).
- Card exit overlaps the next card's entrance by 1-2 frames: never an empty frame, never two cards stacked (`caption_lint`: overlap must be 1-2 frames when the gap between cards is <= 0.35 s, a house threshold for "continuous speech").
- The entrance must finish before the exit starts (a still-running entrance re-asserted opacity 1 on the last word and it popped at the block end): clamp with `tmax`.
- A caption never sits on the mouth: end it with the B-roll and return on the next sentence; run a face-box vs caption-box overlap check on A-roll. Full-screen events cover or move the outgoing line; cards and captions must not collide.
- Backdrop-filter on caption pills alive all film cut capture to 4.3 fps vs ~19 and killed the encode at frame 1348/1350: `visibility:hidden` outside each element's window; avoid backdrop-filter on captions.
- The first caption of an A-roll return: check the first 3 frames.

## 4. Safe zones (dated 2026-09, checked by the author; platform UI changes: treat as [house], not law; run the overlay + phone test exercise)
| Platform / ratio | Canvas | Top | Bottom | Left | Right |
|---|---|---:|---:|---:|---:|
| Meta Reels / Stories / Feed 9:16 | 1080x1920 | 270 | 672 | 65 | 65 |
| TikTok 9:16 | 1080x1920 | 150 | 480 | 60 | 140 |
| YouTube Shorts | 1080x1920 | 288 | 672 | 48 | 192 |
| One 9:16 master (union of the strictest) | 1080x1920 | 300 | 672 | 140 | 192 |
| IG/FB feed 4:5 | 1080x1350 | 54 | 54 | 54 | 54 |
| 1:1 | 1080x1080 | 54 | 54 | 54 | 54 |
| 16:9 | 1920x1080 | 54 | 162 | 96 | 96 |
On 9:16 there are two zones: KEY TEXT (headline, CTA, logo, price) top 300, bottom edge y <= 1248, left 140, right 192; the CAPTION BAND may sit lower but its bottom edge is never below y 1450. Captions at y ~1760 were hidden by the app UI in a project. A Hebrew-UI TikTok may move the action column to the left: keep 140 px on both sides for an Israeli audience (unverified). Each ratio is re-laid out, not cropped.

## 5. Caption QA (what each tool proves and does not)
| Tool | Proves | Does not prove |
|---|---|---|
| `scripts/caption_lint.py` on `captions.json` | the PLAN: dwell, exit, overlap, lead, rail, bidi controls, keyword look-alike record, animation unit | rendered pixels |
| `caption_qa <video> --band <top>:1450 [--x ...] [--drop 0.85]` | frames where caption text vanishes in ONE frame (bright-pixel count in the band falls > 85 % between consecutive frames while the previous had > 900 text px) | abrupt APPEARANCE; two overlapping plates; coloured/dark text; aspect/fps other than 1080x1920 @ 30 fps in the original (E04: missing input exited 0; f25 at 25 fps printed as 0.83 s) |
| `hf_preflight` | root `dir=rtl`, captions below y 1450 (warning W), stale timing | alternative syntax can bypass the regexes |
| `frame_qa` | black/pop/flash/hold over all frames | caption semantics |
| snapshot at keyword frames | the font loaded; look-alikes at full size | motion |
| a Hebrew reader | spelling, meaning, legibility | — |
**Coverage statement (required in every caption QA report):** file name + mtime, frames decoded of frames expected, fps used, canvas, band, which checks ran and which did NOT (appearance, overlap, non-30 fps), and the explicit sentence "pass = the test ran on this coverage". A missing caption file or a zero-frame decode is `blocked`/`INSUFFICIENT_EVIDENCE`, never `pass`.

## 6. Contrast snippet (house check, screening only)
```python
import sys; from PIL import Image, ImageStat
im = Image.open(sys.argv[1]).convert("RGB"); w, h = im.size
bg = ImageStat.Stat(im.crop((0, int(h*.50), w, int(h*.62)))).mean
lin = lambda v: v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4
lum = lambda c: .2126*lin(c[0]/255) + .7152*lin(c[1]/255) + .0722*lin(c[2]/255)
k = [int(sys.argv[2][i:i+2], 16) for i in (1, 3, 5)]
a, b = sorted([lum(bg), lum(k)]); print("contrast %.2f:1" % ((b+.05)/(a+.05)))
```
Usage: extract one frame per emphasis shot with ffmpeg (`-ss <t> -frames:v 1`), run with the keyword colour. `scripts/caption_lint.py contrast` does the same arithmetic from numbers.

## 7. Per-type modes (pointers)
Premium talking head: chunked word-group cards, Rubik, mirrored exit, rail bottom <= 1450, one keyword colour. Testimonial and ad types own their signatures (stroke/shadow, positions) in their skills. Podcast clips: colour per speaker, captions on the seam of a split layout (external, unverified).

## Sources
distilled 06 hebrew-rtl-and-captions §3.1-§3.5, §5; distilled 02 techniques §6.1; E04 defects via blueprint TOOLS_SPEC; checked 2026-10-02.

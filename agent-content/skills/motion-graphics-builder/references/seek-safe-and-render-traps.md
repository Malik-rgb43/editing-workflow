# Seek-safe rules, determinism, and the render traps that cost this studio rounds

Load when: writing composition code, patching after a note, a render looks different from Studio/snapshot, or before the one full render.

Source keys: d04 = distilled/04 (engines-and-hyperframes §4-5, §9; hyperframes-traps), pin HyperFrames 0.8.98 (see `dated-versions.md`). **Every trap below is a scoped historical report, not a current limitation, until a reproducer passes on the pinned build.** Wording: "reported on the author's 2026-09-28 setup (one reference machine, CLI 0.8.79-0.8.93); regression pending on the pinned build". The full catalogue with symptom/cause/fix/prevention lives in `agent-content/references/hyperframes-traps.md` (owned elsewhere); this file keeps what a motion build needs.

## 1. Determinism is a contract you write
One paused seekable timeline per composition, no clocks, no unseeded random, no network at render time, explicit ids and durations; then PROVE it. E01 (12 s synthetic fixture, the reference machine, 0.8.98 vs Remotion): 360/360 decoded-frame hashes and the MP4 hash repeated within each engine; no winner claimed. A lint/`check` pass is not a correct render: `check` samples 9 grid points by default, a lint error silently disables the layout audits, and snapshots do not prove cuts. (src: d04 _index §3; hyperframes-traps §0)

Rules (what `scripts/seek_safe_scan.py` encodes as SS01-SS16):
- Visible state is a function of time only: no `Date.now`, `performance.now`, unseeded `Math.random` (seed a hash of index/frame), `setInterval`, rAF, hover/scroll, `repeat:-1` (use `repeat: Math.max(0, Math.floor(duration/cycle) - 1)`; floor, not ceil).
- GSAP seek suppresses callbacks: state created in `onComplete`/`tl.call` is not time-addressable. Use properties on the timeline.
- Every animated property has exactly one owner; random-order seek and fresh sequential render must agree. Resources (fonts, textures, models) are ready before layout measurement.
- Animate transforms and opacity (`x`, `y`, `scale`, `rotation`); `left/top/width/height/fontSize/letterSpacing` snap to whole pixels and stutter on slow tweens (lint `gsap_non_transform_motion`). Never read `getBoundingClientRect` at tween time: precompute constants; elements of inactive clips measure 0.
- `fromTo` over `from`; `gsap.set` the initial state of every `fromTo(..., {immediateRender:false})`; give `filter` tweens full from/to strings (`blur(0px) brightness(1)`), otherwise a black frame appears at the start.
- Never tween `display`/`visibility`/`autoAlpha` on a `.clip`; do not hide in CSS what a tween must reveal; do not nest sub-composition timelines into the host.
- Host id, template id and `window.__timelines["<id>"]` key must be identical; with a mismatch the render waits 45 s per scene and captures static frames.
- Root `data-duration` is read once at compile time (required for Three.js and for infinite-CSS compositions); a clip is visible on the half-open interval `[start, start+duration)`; land the end state slightly before `data-duration`.
- Frame-exact timing: write `f/30` to 6 decimals; a negative `data-start` shifts every clip (`grep -c 'data-start="-' index.html` must print 0); put a camera/state change on a cut at `start - 0.005`; add +0.0005 s overlap in `data-duration` to avoid one black frame per cut; keep a clip alive under the next scene (T6).
- `<video>`/`<img>` composite in their own layer: parent `visibility`/`overflow`/3D has no effect; time them with their own `data-start`; image in a 3D card = CSS `background-image`; tween a wrapper, never the timed media. `preserve-3d` ignores `overflow`; opacity on a `preserve-3d` element flattens it; a duplicate `id` steals CSS (prefix ids with the composition id).
- Many `<video>` on one heavy source starve font/image loading: pre-cut one continuous file (trim + concat, 30 fps, GOP 15).
- Never `data-color-grading` on a speaker (grade hang on the reference machine's stack, 0.8.82): bake the grade with FFmpeg.

## 2. The never-break build rules (owner, law)
- No `dir="rtl"` on `<html>` or the composition root (black render while preview and snapshot look right); `direction:rtl` on text elements only; `lang="he"` on `<html>`.
- Fonts from files: `@font-face` to `hf/fonts/`; check in a snapshot that the font loaded (a monospace/serif fallback means it did not). Vendor docs say installed/Google fonts embed automatically; the author measured silent fallback: ship the file. `[CONFLICT]` resolved by shipping the file.
- Never run `npx hyperframes init` under a path with Hebrew characters (it silently skips `index.html`; `lint`/`check`/`render` still work): use `new_project`, verify `index.html` exists. Work root is ASCII.
- Author at width 1088 + `data-deliver-width="1080"` only if the edge-band check on the pinned build still reproduces (the encoder blackened x 1072-1079 at width 1080 on the reference machine; not re-tested on 0.8.98). `hf_deliver` verifies the right edge.
- `hyperframes snapshot --describe false` always (otherwise frames may be sent to Gemini when a key exists); at most 5 timestamps per call (longer lists time out).
- One heavy job machine-wide (`render_lock`); never a render next to Blender/ASR (10 -> 18-21 min). A `check` that hangs: kill YOUR process tree, rerun once; `timeout 900` on `check`.
- Pin the toolchain: `HYPERFRAMES_SKIP_SKILLS=1`, `HYPERFRAMES_NO_UPDATE_CHECK=1`, `HYPERFRAMES_NO_TELEMETRY=1`; `feedback` posts to a PUBLIC channel: strip names and paths or do not send.
- Whole-film `backdrop-filter`/large blur dropped capture to 4.3 fps and hit the 600 s encode timeout; hide with `visibility:hidden` outside the time window, set `FFMPEG_ENCODE_TIMEOUT_MS=3600000`.

## 3. Verification ladder (cheap first; stop at the first failure)
1. `hf_preflight --strict` (seconds): Studio `data-hf-id` left in, root RTL, stale timing grid (`F(n)` outside the host window), duplicate ids, media in `preserve-3d`, tweens aimed at `<video>`, captions below y 1450 (9:16). 0 errors.
2. `python scripts/seek_safe_scan.py <hf>` and `python scripts/palette_audit.py hf/DESIGN.md <hf>`.
3. `hyperframes check` under the lock with `timeout 900`.
4. Snapshots of every seam, at NON-sequential times (e.g. 2.7 s then 0.4 s), `--describe false`, <= 5 per call; four approval stills; Studio preview (Studio-first review).
5. `hf_segment --from <s> --to <s> --qa` only for render-only risks (`<video>` layers ~1 frame offset; one 6-note round cost 240 s of machine time with segments vs 430 s without, E12, the reference machine).
6. ONE full render per round of notes, under the lock, with an ETA line first (benchmark one unit; `timeout` = 3 x ETA; heartbeat about every 5 min; 0 frames after 3 min or no progress for 10 min -> kill your own tree, one snapshot, retry once). Reference durations: a 30-45 s launch 8-14 min on the reference machine (4-21 observed); a 12 s synthetic fixture 42-54 s (E01).
7. `frame_qa` on the final render (every frame): 0 flagged black frames, pops, flashes, over-long holds, double jumps. A seam frame-diff at c-1..c+2 shows one spike when picture and sound are in sync; two spikes 1-2 frames apart = out of sync.
8. `motion_qa` (0 stutter ranges) and `hf_deliver` verify on the FINAL file (length +-1 frame, -14 LUFS +-0.5, TP <= -1, no 2-frame black, no dead edge band). A successful tool call is execution evidence; a viewed render is appearance evidence; a still cannot prove motion.

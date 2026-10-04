# Technique: the frame-spec PROMPT.md

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from distilled/02 techniques §1 and workflow-end-to-end §5 (author's method, rewritten and tightened; the worked example is **synthetic**).
> Tags: `[RULE-owner]` the author said it · `[PROVEN-internal]` worked in an owner-approved project · `[IDEA]` untested proposal · `[CONFLICT]` sources disagree · `[LOCAL-only]` true on the reference machine only.
> OM (the reference machine) = one Windows laptop; hardware details are intentionally not published.8.x.

## 0. What it is

`hf/PROMPT.md` is a **production spec at frame level**: for every moment of the video it says what is seen, where (px), when (frames), how it moves (easing), what is heard, which transition carries it into the next moment, and which ledger line it satisfies. The code only renders the spec. Nothing in the spec is "about"; hex, px, frames and easing checkpoints are the contract. `[RULE-owner]`

- **Gate:** the author approves PROMPT.md before the first line of composition code, in every video type and **also in autonomous runs** (the agent drafts, the human approves; an agent never self-approves). Cost when skipped, measured on owner projects: a discarded ~1 h build (launch test, v1) and a reverse-engineered spec at the end (premium talking-head test #3). (src: distilled/02 workflow-end-to-end §5, 2026-10-02) `[RULE-owner]` `[PROVEN-internal]`
- **Order of change, always:** ledger → PROMPT.md → code. Never code first. A later note becomes a new ledger line, then a changed range in `<structure>`, then a patch.
- **One spec file:** `hf/PROMPT.md`. There is no SPEC.md. The ledger lives inside it (`<ledger>` block above the six frame blocks); see [concept-ledger.md](concept-ledger.md).
- **Where the idea came from:** a public 7.5 s UI launch (226 frames, produced in about 15 minutes from a frame-level prompt) that the author called perfect. Use it for **structure**, never copy its content. `[RULE-owner]` `[SOURCED-unverified for the public post]`

### 0.1 Gold-standard beat shape (measured on frames of that reference; use as a rhythm template, not content)

| Beat | Time | What happens | Sound |
|---|---|---|---|
| type | 0–1.0 s | card + caret typing, construction grid | tick per keystroke |
| charge | 1.0 s, **one frame** | halftone + duotone flash | hit |
| settle | 1.0–1.6 s | card grows into a paragraph | – |
| press | 2.1 s cut → 2.7–3.0 s | the **only** punch-in (≈4×) on the button, 3-frame colour change | click at 2.78 s |
| transition | 3.1–3.23 s | whitewash + blur + zoom-out, subject swaps underneath | whoosh |
| anticipation | 3.6–4.1 s | light band sweeps the card | rising shimmer |
| reveal | 4.03–4.4 s | the card **becomes** the site, fullscreen | bass drop at 4.1 s |
| pull back | 5.6–7.47 s | site shrinks to a screen on neutral grey | pad, fade |

Principles to keep: a protagonist object that morphs (no cutting away); at most one punch-in, on the moment of action; a one-frame motif repeated twice as a structural marker; anticipation about 0.5 s before the reveal with the drop exactly on it; the ending shows the result in context with ≥ 1.5 s of quiet (the author later asked for a natural ring-out instead of a hard stop in his own launch: music rings out to the last frame). Music is **not** beat-locked to every cut (17 % in the reference); sound effects are locked to **events**. (src: distilled/02 techniques §1.1; qa §3) `[PROVEN-internal]` `[CONFLICT-light]` on hard-stop vs ring-out: the author's later rule wins.

## 1. Writing rules (every type)

1. **Story first.** One sentence of what the viewer feels, then one screen or beat per sentence-sized idea. For launches a new screen every 2–6 s `[RULE-owner]`.
2. **A concrete story object that changes** on every screen (an empty slot that turns green), never an abstraction (a dot on black).
3. **One anchor**: a hero object that persists through the film (a card, a number, a phone). A key detail (price, name) gets a readable close-up ≥ 0.9 s.
4. **Numbers are the contract**: hex, px, frames at the *delivery* fps, easing control points ("90 % by f12"), dB. If the source table is at another fps, convert and say so (the author's own-signature table was measured at 60 fps; halve for 30 fps). `[RULE-owner]`
5. **Sound is part of the spec**: every SFX with a time; music edited so the beat falls on an event; VO lines with start times; a keyword lands 0 to +7 frames after it is spoken.
6. **A Banned list in every spec** (permanent items below + every owner note so far).
7. **Every transition different.** Choose from the vocabulary (zoom-through into an object, shared element, 3D page fall-away, light-line bloom, match-move of a number, whip with blur, clip-path portal, push into a device).
8. **Four approval stills before any full render** (`<start>`), named by frame.
9. In HyperFrames the **paused GSAP timeline plays the role of `seek(t)`**: every style is a pure function of time.

**Permanent Banned list** (union of the author's lists; add each new note): crossfade · fade as a transition · bounce on text · glow on static text · small corner labels / "feature pills" that look like AI · the same transition trick twice · an empty screen (a dot or rings on black) · a static hold ≥ 1 s in promo and motion · template look · another brand's signature colour · stock UI kits · accent colour before the reveal (launch default) · a 3D object covering information such as a price · full-film `backdrop-filter` / large blur. (src: distilled/OWNER_STYLE §M) `[RULE-owner]`

## 2. The skeleton (motion / launch / promo)

Copy this into `hf/PROMPT.md` and fill every bracket. Blocks keep their tag names so tools and reviewers can find them.

```text
# PROMPT: <project> — "<title>" (<W×H>, <duration s>, <fps> fps, <N> frames)
status: DRAFT vN | APPROVED   approved_sha256: <hash of this file when approved, else —>
Owner notes this version answers: 1. … 2. …   (numbered, in the author's words; later rounds override earlier tables)

<ledger> … see concept-ledger.md; one checkable line per concrete statement … </ledger>

<inputs>
Ask the author for: [content per screen, numbers, VO lines, CTA text, music, logo files].
Defaults if skipped (a concrete default for EVERY item, so work never waits): […]
Variant matrix (one row per output file, each row a ledger id): [file | ratio | variant | derived from]
</inputs>

<direction>
Format: <W×H @fps, N frames>; one continuous take OR cuts.
Reference grammar: <ref-id / none> — what is borrowed (numbers) and what is not.
Look: grounds (hex), the ONE accent (hex, meaning, first frame it may appear), neutrals, grain %, vignette.
Type: families, sizes in px, tracking, line-height; exact copy of every text.
Hero object: dimensions, perspective, orbit.  3D: which beats, which route, why (see three-d decisions).
Motion language: entrance curve + frames; exit curve + frames; blur policy; overshoot policy.
Transitions: table, one per seam, each different.
Banned: <permanent list + notes>.
Safe zones: key text rows / caption rail from DESIGN.md (project may be stricter than the platform table).
</direction>

<structure>
VO: [line — start s] (keyword lands 0…+7 f after spoken).
Music: [downbeats in frames; take-away; hit; ring-out].
f[a]–[b] [screen name] ([world]): position in px, sizes; what enters at which frame with which easing; camera from→to; which story object changes; what exits and how; transition into the next screen. Cite ledger ids: [L04].
</structure>

<build>
One paused timeline; seek-safe (seeded hash for grain/scatter; no CSS transitions, timers, Math.random, rAF).
One cues.js for picture AND sound (a re-time moves both).
Sound chain: VO per-line LUFS, music ducking, SFX levels and times, master −14 LUFS / TP ≤ −1.5 in the mix (house preset).
Fonts: @font-face from hf/fonts/. Never dir="rtl" on the root; RTL only on text elements.
</build>

<gotchas> measure text only after fonts load · media is its own layer · tl.set initial state for every fromTo(immediateRender:false) · Studio adds data-hf-id (strip before patching) · … </gotchas>

<start> four approval stills (frame numbers) + snapshots of every transition + a contact sheet, BEFORE the first full render. </start>
```

### 2.1 What each block must contain to count as "ready for approval"

| Block | Ready when | Typical failure |
|---|---|---|
| `<ledger>` | every concrete owner statement is one row with an acceptance check; blocking dimensions locked ([concept-ledger.md](concept-ledger.md)) | prose instead of rows; vague words ("more dynamic") with no number |
| `<inputs>` | each missing item has a default; the variant matrix lists every output file | "ask later" items with no default |
| `<direction>` | all hex, px, fonts, banned list, safe zones present | adjectives instead of values |
| `<structure>` | every second of the film is covered by a frame range; every ledger id appears at least once here | gaps between ranges; ids not cited |
| `<build>` | sound chain and level targets are in the spec, not an afterthought | "add sound at the end" |
| `<start>` | four stills named by frame number | "show a preview" |

### 2.2 Motion pieces: three mandatory tables

Without these the PROMPT is **not ready for approval** (born from nine rounds of timestamped notes on one launch; the fix is to design them in, not to patch later). `[RULE-owner]` Rules and checks: [clean-smooth-motion.md](clean-smooth-motion.md).

1. **Camera per scene:** `scene | t (frames) | scale | focal (x,y) | what is in frame | all key text inside the frame and the safe zone? (y/n with the arithmetic)`. One spline path per scene; moves ≥ 1.2 s.
2. **Seams:** `seam | t | exit vector (x/y/zoom) | entry vector | hero object that persists | technique`. Exit = entry, or a declared deliberate stop.
3. **Events:** a list of frame numbers with the semantic change, no gap longer than 0.5–0.7 s (15–21 frames at 30 fps) before the end card; plus each scene's background; plus the VO phonetics check for brand names and heteronyms.

## 3. Variant: the edit spec for footage (talking-head, testimonial, ad, podcast clip)

For footage the equivalent of frame-level motion is an **edit spec with timecodes** per range. `[RULE-owner]` Same ledger and same approval gate. Skeleton:

```text
# PROMPT: <project> — "<title>" (<ratio>, <duration>, <fps>)
Style lock / reference: <ref-id> (path to analysis) + which time range is "the style"
Deliverable (hard): exact final file name
Owner notes this version answers: …
Story in one sentence: <what the viewer feels; what the speaker promises>

<inputs> table: footage (file, duration, ratio, fps, colour state, loudness, camera original? y/n) · language · transcript tool ·
  logos (organic-only warning) · B-roll sources · keywords + colours · caption font choice · CTA wording </inputs>
<script> the cut EDL: Beat | out frames | src seconds | VO text ; "Cut out" list ; "Re-ordered" list ;
  rules: edit points sit INSIDE silences (in-point in the silence BEFORE the sentence), re-checked on the waveform ±2 f,
  joins leave 80–200 ms of air, hidden-cut covers (±6 f), transcript proofing (ASR's wrong words → real ones) </script>
<direction> format/fps (source→output) · grade by world (measured targets; baked BEFORE HyperFrames) · framing (crop %, head-top y) ·
  type system (caption font/weight/px/colour/shadow/line-height/words per chunk/centre y per shot type/entry+exit) ·
  accent tokens · motion language · transitions (each used once) · pacing check (shots, cuts/min, events) · banned </direction>
<structure> # | O (output time) | S (source time) | what is said (keywords bold) | what is seen | sound
  — one row per beat and per event (star-marked), frame-level detail for effects </structure>
<sound> VO chain (denoise, HPF, EQ, per-line LUFS, compressor, 8 ms micro-fades at cuts) · music (level under VO, ducking, take-away frames, ring-out) ·
  SFX (folder, dB under VO, 1–3 f BEFORE the picture, only on visible events) · master −14 LUFS / TP ≤ −1 measured on the FINAL file </sound>
<build> edit.json builder · word times · ONE table of pieces for picture and sound · transcript corrections · fps conversion · --sdr </build>
<gotchas> RTL on text elements only · fonts via @font-face · widest keyword fits · close-crop sharpness · snapshot --describe false · mux mix.wav after render </gotchas>
<start> snapshot times (output seconds) for look approval, then a full draft </start>
```

Footage-specific pacing numbers live in `pro-video-editor` (talking-head: a beat every 3–6 s that shows the sentence, owner "premium" bar; cutting numbers: minimum pause to cut 0.40 s tight / 0.60 s natural / 0.25 s aggressive, minimum shot 0.35 s, lead 0.08 s, tail 0.12 s, cut 0.06 s inside the silence — author's earlier tool constants `[PROVEN-internal]` `[LOCAL-only]`).

## 4. Variant: AI-generated film (shot cards)

Nothing is generated until the document is approved; approval of a **number** precedes any spend (💲 [paid-spend-gate]); images are approved before video; every frame is checked. Document sections (reconstructed from a 15-shot, 28.0 s plan; section order matters because later sections depend on earlier locks): 0 locked decisions (format, sound, ending, tools, generation length) · 1 materials found + problems in the brief (contradicting timings, slow opening, wording errors, platform policy, AI-label duty) · 2 three concepts (Proven written in full) + recommendation · 3 the contract: N shots on a frame/second table (length, generation length, clean window used) and an emotional/colour arc per chapter · 4 look bible (one-line idea, locked palette table, lens + movement dictionary, Banned) · 5 locks (character, environment, equipment; each with source references) · 6 reference pack ("references are not templates": light, lens, camera move, composition) · 7 global prompt blocks (STYLE PREFIX; a fixed closing BASE block; fixed request order Camera → Action → Light → Detail → BASE) · 8 **shot cards** · 9 the three clean-and-smooth tables per shot · 10 sound (music brief, SFX per frame, mix) · 11 assembly and post (fps check, windows, time-remap, one grade, grain, cover kit) · 12 production order with approval gates and **budget units, no prices** (model routes carry no price in the catalogue) · 13 risk register · 14 open questions with defaults.

**Shot card fields:** what is seen and why · references to attach · START image prompt (`[STYLE]` + scene + lock blocks + lens) · VIDEO prompt (model, mode, duration, sound off, start image only or start+end) in the fixed order · **clean window** (seconds actually used, 1.2–2.5 s) · transition to the next shot · sound at the shot · risk and fallback (for example a real-footage cut). (src: distilled/02 techniques §1.6) `[PROVEN-internal]`

## 5. Checklist before presenting any PROMPT

- [ ] ledger first; `grep -o "L[0-9][0-9]" hf/PROMPT.md | sort | uniq -c` shows every id ≥ 2 (ledger + structure). A textual count is a minimum check, not a schema check.
- [ ] numbers everywhere (hex, px, frames, easing points); no "about".
- [ ] sound with times; music edit plan; VO lines with start times; levels as targets.
- [ ] Banned list present; **no accent before its declared frame** where a ledger line says so.
- [ ] motion: the three tables; all transitions different; no gap > 21 f (0.7 s) between events before the end card; one background per scene; VO phonetics check.
- [ ] four approval stills named by frame.
- [ ] footage: cut text approved; hidden-cut covers (≥ 6 f each side); centring plan; colour plan (camera original found?).
- [ ] platform safe zones and caption rail (bottom ≤ y 1450) in `<direction>`; the project's stricter limit, if any, is written in DESIGN.md.
- [ ] file name and length locked in the ledger.
- [ ] `status: DRAFT`; the approval writes `APPROVED` + the file hash into CHANGELOG.md (an edited approved PROMPT with a different hash needs re-approval of the changed ranges).

## 6. Worked example (SYNTHETIC subject)

Everything below is invented for teaching: "Nimbus" is a fictional note app, the strings are original, no real brand, product, person, price or claim. Numbers were arithmetic-checked by the author on 2026-10-02 (frame/time conversions, text bounds, event gaps ≤ 21 f); the piece itself has not been built or rendered.

```text
# PROMPT: Nimbus teaser — "הכול נשמר" (9:16, 12.0 s, 30 fps, 360 f)
status: DRAFT v1   approved_sha256: —
SYNTHETIC SUBJECT: Nimbus is a fictional note app. Strings and numbers are invented.

<ledger>
| ID  | dim  | said (verbatim)            | spec (measurable)                                                                 | where / when        | acceptance check                                   | src | status  |
| L01 | LEN  | "12 שניות"                  | 12.00 s ±0.1 = 360 f @30                                                           | whole               | ffprobe duration on the final                      | U   | locked  |
| L02 | FMT  | "אנכי לריילס"               | delivered 1080×1920; authored 1088×1920, data-deliver-width=1080                   | whole               | ffprobe size; hf_deliver edge-band check           | U   | locked  |
| L03 | FILE | "קוראים לזה nimbus_teaser"  | final/nimbus_teaser_9x16.mp4                                                       | —                   | ls final/ equals manifest                          | U   | locked  |
| L04 | LOOK | "עולם אפור, צבע רק בסוף"    | ground #0E1116 · surface #181D26 · text #F4F6FA · muted #8A93A6 · accent #5B8CFF; first accent pixel at f240; before it greys + white caret only | f0–f239 no accent   | 5×5 median sample at f239 (neutral) and f246 (accent) | U   | locked  |
| L05 | TYPE | —                           | Rubik (OFL) 900 headlines 150 px, 400 body 54 px; RTL only on text elements; look-alike test on המון / הרעיון / הכול / נשמר | all text            | each keyword rendered at final size, result in QA.md | D   | default |
| L06 | CAP  | —                           | no captions (launch register, no VO)                                               | —                   | caption_qa recorded as n/a with this reason        | D   | default |
| L07 | MUS  | "120 BPM, דרופ על החשיפה"   | bed 120 BPM (beat 15 f, bar 60 f); low-pass 400 Hz f216–f235; silence f235–f240 (5 f ≈ 167 ms); hit f240; rings out to f360 | whole               | 3 s-LUFS timeline: no step > +3 LU except the hit at f240 (intent recorded) | U   | locked  |
| L08 | SFX  | —                           | only on visible events, listed in <structure>; level set in hf_mix and confirmed by listening | listed times        | hf_mix --report: no cue without a visible event ±3 f | D   | default |
| L09 | TRN  | "כל מעבר שונה"              | seam A→B = reveal-through (chip → card); seam B→C = match-move of the word נשמר    | f69–f87 · f228–f240 | frame strips at both seams; no repeated technique   | U   | locked  |
| L10 | CTA  | —                           | pill "נסו עכשיו" visible f270–f360, inside key-text rows                            | f270–f360           | snapshot f300 with safe-zone overlay                | D   | default |
| L11 | LOUD | —                           | master −14 LUFS ±0.5, TP ≤ −1 on the final file (house preset)                      | whole               | hf_deliver verify block                              | D   | default |
| L12 | TON  | "בטוח, לא צעקני"            | energetic-premium: an event at least every 21 f (0.7 s) before the end card; no exclamation marks in copy; one accent | whole               | events list in <structure> read by a script         | U   | locked  |
| L13 | BAR  | "ברמה של השקות טובות"       | premium launch bar: every ledger row ticked; critic ≥ 4.0 with no dimension < 3; ONE full render per round | wf-06/wf-07         | QA.md ticks + rubric file + ledger of full renders  | U   | locked  |
</ledger>

<inputs>
Ask for: logo file (default: type-only wordmark "Nimbus" Rubik 900 72 px), CTA text (default "נסו עכשיו"), music (default: library bed 120 BPM with a licence row in SOURCES.md).
Variant matrix: L02 only (one file, 9:16). No variants.
</inputs>

<direction>
12.0 s, 1080×1920 @30 (360 f) [L01][L02], authored 1088 wide; tone [L12], bar [L13]. One world of greys, accent only on the reveal. Hero object: the NEWEST notification chip, which becomes the note card.
Safe zone (project, from DESIGN.md): key text inside x 140–888, y 300–1248; all key-text boxes are centred on x = 514 (the 9:16 union row is asymmetric: left 140, right 192).
Grounds/greys per L04; grain 4 % re-seeded every 2 f from a seeded hash; no vignette.
Type per L05. Texts: A headline "המון רעש." · chips (Rubik 400 54 px): "הודעה חדשה · 3", "תזכורת: לקנות חלב", "קבוצה: 128 הודעות", "מייל: הצעה מיוחדת!", "עדכון זמין", "יום הולדת של דנה" · note "הרעיון הגדול נשמר כאן." · C headline "הכול נשמר." · wordmark "Nimbus" · pill "נסו עכשיו".
Motion tokens: snap in = expo.out 4–10 f; exit = power3.in 7 f (always shorter than the entrance); reveal-through = power3.inOut 18 f; camera = one spline per scene, no blur inside a scene; overshoot only on the pill (back.out 1.5, a living element).
Transitions: A→B reveal-through · B→C match-move. Banned: permanent list + "accent before f240".
</direction>

<structure>
Whole film: final file name [L03]; no captions anywhere [L06].
Music: downbeats f0, 60, 120, 180, 240 (HIT), 300. Take-away f216–f240 per L07. Ring-out to f360.
f0–f75 · SCENE A "noise" (grey world) [L04]
  f0: headline "המון רעש." (150 px, 900) at x-centre 514, y-centre 375 (box y 300–450), enters expo.out 6 f, y −40 → 0.
  Notification list (U1 behaviour: a LIST — newest enters at slot 0, the rest slide down 156 px): slot k centre y = 640 + 156·k, chip 776×132 px, radius 28, fill #181D26, text #F4F6FA.
  New chip at f0, f9, f18, f27, f36, f45: y −60 → slot 0 in 6 f expo.out; existing chips slide one slot in 8 f power3.out. Six chips at f45; stack bottom slot 5 = y 1420 (decor, not key text).
  f54: badge (top-right of the stack, 96×60, text) whole-number swap "6" → "99+" (old out-up, new in-up, 2 f offset, hold ≥ 12 f).
  f60–f67: headline exits up −40 px, power3.in 7 f, blur peak 8 px. 
  Camera (scene A table below). [L04][L07]
f69–f87 · SEAM A→B reveal-through [L09]
  The newest chip (slot 0: x 126–902, y 574–706) is the hero. Scene B is revealed THROUGH its rectangle: clip-path inset morphs chip rect → card rect (x 126–902, y 574–1094) in 18 f power3.inOut; B's card content is visible inside the shape from the first frame (T3: a morph always carries content).
  Chips 1–5 drop y +90 and exit in 7 f power2.in starting f66 (covered by the card by f78). Whoosh SFX on this move. B starts UNDER A: B clip start = f69, A clip end = f90 (T6).
f69–f240 · SCENE B "the note" (grey world) [L04]
  f87: card settled: 776×520, radius 32, fill #181D26, 1.5 px rim #2A303C. Text region 664 px wide, 56 px padding.
  f93–f137: caret (white, 4×64 px) types the note, 1 character per 2 f, right-to-left in reading order; word ends at f105 (הרעיון), f117 (הגדול), f127 (נשמר), f137 (כאן.). Tick SFX per character.
  f143: underline sweeps under נשמר, 12 f power3.out, white 70 %.   f155: toast "נשמר ✓" enters from the top, expo.out 6 f, no bounce (U1).
  f176: header badge whole-number swap "12" → "13".   f197: the word נשמר pulses 1.00 → 1.06 → 1.00 in 10 f.
  f216: the rest of the line dims to 35 % in 8 f power2.out so נשמר is the focus; low-pass 400 Hz begins (L07).
  f228–f240: SEAM B→C [L09] match-move: toast, badge and header exit in 7 f (power2.in); the card drops y +120 in 8 f power2.in; the word נשמר (54 px) travels to its C position and scales ×2.78 to 150 px in 12 f power3.inOut, landing exactly on f240. C's ground is already alive under B (clip start f228).
f240–f360 · SCENE C "the answer" (accent world) [L04][L10]
  f240 HIT: the word נשמר lands (150 px, 900, #F4F6FA); the accent #5B8CFF appears for the first time as a ground bloom radial (radius 520 px, 14 % → 0 over 24 f) and the wordmark underline.
  f252: "הכול" enters from the right (expo.out 6 f), headline now reads "הכול נשמר." centred at y 700.   f264: wordmark "Nimbus" snaps in (72 px, accent) at y 880.
  f270: CTA pill (width 520, height 120, radius 999, fill accent, text #0E1116 54 px 900; centre x 514, y 1060, box y 1000–1120) enters y +40 → 0, expo.out 6 f, back.out 1.5 scale 0.94 → 1.
  f288: pill press: scale 0.94 → 1.05 → 1 in 7 f, click SFX.   f306: light band sweeps across the pill (10 f).   f324: light band across the wordmark (10 f).
  f334–f360: quiet drift only (end card exempt from the event-density rule). Last frame f359 shows the readable end card.
</structure>

CAMERA PER SCENE (focal x = 514; one spline each; segments ≥ 1.2 s; text-fit checked at the largest scale)
| scene | keys (f: scale, focal y) | widest key-text box at max scale | inside x 140–888? |
| A | 0: 1.00, 960 · 40: 1.04, 930 · 75: 1.08, 900 | chips text 600 px × 1.08 = 648 → x 190–838 | yes |
| B | 69: 0.94, 940 · 105: 1.02, 930 · 170: 1.09, 900 · 234: 1.12, 880 | note text 664 × 1.12 = 744 → x 142–886 | yes (2 px margin: do not enlarge text) |
| C | 228: 0.92, 880 · 264: 1.02, 860 · 360: 1.10, 840 | headline lockup 640 × 1.10 = 704 → x 162–866 | yes |
Drift rate in C: (1.10 − 1.02) / 3.2 s = 2.5 % per second.

SEAMS
| seam | t | exit vector | entry vector | hero that persists | technique |
| A→B | f69–f87 | camera scale growing (A ends 1.04→1.08) | B enters growing 0.94→1.02 | newest chip → card | reveal-through (clip-path) |
| B→C | f228–f240 | card drops down, camera still growing | C enters growing 0.92→1.02 | the word נשמר | match-move + scale ×2.78 |

EVENTS (frame numbers; max gap 21 f = 0.7 s up to f324)
0, 9, 18, 27, 36, 45, 54, 60, 69, 87, 93, 105, 117, 127, 137, 143, 155, 176, 197, 216, 228, 240, 252, 264, 270, 288, 306, 324
Backgrounds: A flat #0E1116 + 4 % grain; B #0E1116 with a 6 px dot grid at 6 %; C accent bloom over #0E1116 (bookend: the dot grid returns at 8 % in C).
VO: none. Phonetics check: not applicable (no VO). Brand name Nimbus is Latin and appears only as type.

SOUND [L08] (all SFX synthesised with ffmpeg aevalsrc/anoisesrc; level −12 dB under the bed by default D, confirm by listening; low-pass ≈ 7 kHz)
ticks f0, 9, 18, 27, 36, 45 · swap tick f54 · whoosh f69 · key ticks every 2 f f93–f135 · ping f155 · swap tick f176 · sub boom f238 (picture hit f240 → boom 2 f BEFORE) · click f288 · shimmer f306, f324. No other cue.

<build>
One paused GSAP timeline on window.__timelines, built after document.fonts.ready; cues.js holds every frame number above; camera by a spline helper (no stitched tweens, no overlapping camera tweens); whole-number swaps by a swap helper; reveal-through by a clip-path helper; gsap.set the initial state of every fromTo(immediateRender:false); grain from a seeded hash of (frame). Sound mixed by hf_mix from cues.js: bed −14.5 LUFS, SFX per list, master −14 LUFS / TP ≤ −1.5; final measured with hf_deliver [L11]. Fonts: hf/fonts/Rubik[wght].ttf via @font-face.
</build>
<gotchas>
No dir="rtl" on the root; direction:rtl only on text elements. Authored 1088 wide with data-deliver-width="1080". A clip must not end at the start of a reveal (B and C start under the previous scene). The "99+" swap must not show an intermediate value. The word נשמר must remain in B's DOM until its match-move ends.
</gotchas>
<start>
Four approval stills BEFORE any full render: f40 (stack of chips, accent absent), f78 (mid reveal-through, content visible in the morphing shape), f160 (typed note + toast), f300 (end card with accent). Then snapshots of f69, f87, f228, f240 (≤ 5 per call, --describe false).
</start>
```

**Why this example is shaped this way (teaching notes):** the ledger rows carry the checks the QA stage will run, so wf-06 can tick them without re-reading prose; the three tables make the continuity rules inspectable before any code exists; the safe-zone arithmetic (2 px margin in scene B) shows why text size is a PROMPT decision, not a code decision; event density is a list of frame numbers a script can verify.

## 7. Failure modes

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| owner rejects after a full build | spec skipped or never approved | stop; write the spec from the author's notes; ask for approval | gate in wf-03; `approved_sha256` |
| late "premium / 3D / pace" notes | those dimensions were not ledger lines in round 1 | add ledger rows now, re-plan | intake round 1 asks BAR, MOT, 3D, BROLL |
| a ledger item was lost in the build | id never cited in `<structure>` | grep ids, add citations | `uniq -c` check before presenting |
| camera glitches / text cut in a push-in | no camera table, no text-fit arithmetic | add the table; shrink text or scale | §2.2 table 1 |
| scene logos never rendered after a re-cut | frame literals instead of word cues | anchor to cues | one cues.js; word-cue helper |
| the critic passes what the author rejects | critic unaware of past notes | give the critic the clean-smooth rule table and the Banned list | [critic-brief.md](../benchmarks/critic-brief.md) |

## 8. Sources

(src: distilled/02 workflow-end-to-end §5, techniques §1 and §2, video-types §5; distilled/01 rules-and-gates B1–B8; research T10 motion playbook — all read 2026-10-02.) The worked example is original.

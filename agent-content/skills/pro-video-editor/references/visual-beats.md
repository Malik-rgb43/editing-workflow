# Visual beats: what each beat SHOWS, B-roll, UI, 3D per beat

Merged on 2026-10-04 from the former type skills (one source per section, kept whole). Principles, not a template: use what fits the video in front of you and write the reason for each choice into PROMPT.md.


## Beat menu, hook, B-roll policy, overlays
<!-- source: pro-video-editor/references/visual-beats.md -->
Load when: choosing or replacing a beat, writing the beat table in PROMPT.md, reviewing B-roll, placing overlay cards. Facts are dated 2026-10-02; source tags point to `distilled/06-hebrew-footage-reference/talking-head-and-footage.md` (written "d06-th") unless stated.

### 1. The rule behind the menu
Pick the beat by the MEANING of the sentence being spoken, so the picture shows what the voice says. A beat is one of: real footage, 3D, UI component, data-driven animation, or speaker-only with a camera move. "Boring", "looks AI", "static", "לא אהבתי" from the author or client is a taste verdict: replace the beat TYPE with another menu entry and say why in one line; do not polish the old one (owner law, d06-th §1.7).

### 2. Menu (sentence -> beat -> build route)
| The sentence says | Beat | Build route (examples from a travel-agency speaker project, generalised) |
|---|---|---|
| a place, a result, "reality" | real footage, full-bleed, opened out of an object (photo in a card -> match cut to the real clip) | licensed real stock or the client's own footage; match cut by clip-path on a full-frame video layer (a `<video>` inside an overflow-hidden parent is not clipped by the renderer) |
| "I talk / listen / ask" | data-driven voice orb (real VO spectrum, STFT -> 36 log bands -> JSON) with chat bubbles from depth | seek-safe: painted from one proxy tween; start it already visible (a dim small orb produced a black flagged frame) |
| a process with steps, "I handle it" | UI component: spinner -> tick -> meta, counter, progress | port a registry component's motion language to GSAP by hand; never run a package installer inside the video project |
| a list of documents or deliverables | 3D product shot (wallet -> tickets rise) | Blender sprite sheet or Three.js when procedural; sprites start on their complete frame |
| availability, briefing | light overlay notifications under the chin + 3D type ("24/7") | light cards, see section 5 |
| calm, planned, covered | ONE continuous 3D shot with a metaphor (plane -> route -> shield dome) | one camera spline per scene, no stitched tweens |
| a problem, wasting time | colour drains behind the speaker (not from him) + the alert-colour keyword + a 3D hourglass | the drain is a layer behind the cutout |
| stage N / structure | top panel over the speaker (>= 40 % of frame), head crossing the panel edge, 3D globe route | needs the cutout |
| none fits | speaker-only beat: push-in or punch + caption keyword | allowed, but never two in a row longer than the cadence |

### 3. Cadence and the hook
- Default: a beat that shows the sentence every 3-6 s, and a camera event every 2-4 s (`references/camera-and-motion.md`). Sources disagree and the choice is yours to state in PROMPT.md: owner memory says 5-7 s, the author skill 3-6 s, the motion-density feedback 2-6 s for launches, an external taxonomy 1-3 s (hype) to 3-5 s (clean). Treat all as defaults; none is a platform law (d06-th §1.1 [CONFLICT]).
- Hook, 0-1.5 s, layered: cutout + 3D objects behind + a route or line + silhouette flashes, the question on screen. Hook -> retain -> reward is an external framework (unverified); the "+40-60 % retention" claim is marketing, not research.
- External pattern-interrupt numbers (unverified, use only as a starting point): a zoom cut of about 10 % in 0.3-0.5 s; one planned interrupt every 10-15 s in clips over 30 s.
- `motion_scan` (specified tool): flag any segment >= 1.5 s with < 1 visual event per second as "static".

### 4. B-roll policy
| Rule | Why / evidence |
|---|---|
| Full-bleed, always. A framed 740x1316 window on black was rejected: "it must fill the whole screen" | owner law (d06-th §1.7) |
| Real footage only for stock; never AI-looking stills of people; never a static collage or triptych; never a small bar on black; no flat 2D shards posing as 3D objects | owner law |
| Audit stock for foreign text or locale (a passport or calendar of another country) and for a person who is not the speaker under a first-person line (credibility gate) | d06-th §1.7 |
| Smooth hand-off into B-roll (a light or film-burn transition at a glitchy cut; zoom-through ramped on BOTH sides, 4 frames, scale + blur, power2.in) | one-sided ramps read as a hard cut with a blur pop |
| B-roll covers every hidden source cut with >= 6 frames margin each side | gate G3 |
| Licence row per asset in `hf/SOURCES.md`; `License: unknown` or CC-BY-NC = blocked for client work (Q2) | decision default Q2; rights are not inferred from a filename |
| Owner's own transitions folder before stock (two film-burn ProRes clips, 24p -> 30p by hand so the white peak sits on the cut frame) | owner preference, local-only asset |

### 5. Overlay cards on the speaker
Light cards (#F2F1F3 at 0.95, ink text), <= 860 px wide, body 27-38 px, under the chin, never crossing the face box, appear in place (no drop through the face), leave as ONE unit. Dark glass on a black shirt vanishes and reads as a censor bar. These numbers are proven in one project; `plan_lint` checks width and box-vs-face when the plan supplies boxes.

### 6. Layout taxonomy (external, unverified)
1 full-frame face with captions lower-middle (most owner work); 2 framed card (speaker in a top box, data below); 3 persistent title banner; 4 graphic over the chest (table above the body, face visible); 5 full-screen insert. Prop hook (an object in hand in frame 1) and list-tier mechanic (last row hidden until the end) are external patterns.

### 7. 3D
- Blender for hero or photoreal beats (Eevee 1.2-2.3 s per frame, Cycles CPU 1-4 min per background plate on the reference machine), Three.js when the beat is procedural, data-driven, many instances or must stay editable; the 3D object reacts ON the word.
- Local image-to-video was rejected (Wan2.2 5B: about 17 min for 2 s at 544 px; Wan2.1 1.3B lab test about 669 s per output second, E10). Rule: benchmark one second; ETA > 30 min for a shot -> shorten it or quote a hosted route.

### 8. Banned always (union of the author's lists; add every new note)
Crossfade; fade as a transition; bounce on text; glow on static text; small corner labels that look like AI ("feature pills"); the same transition trick twice; an empty screen; a static hold >= 1 s in promo or motion; template look; copying another brand's signature colour; pink as a default accent; accent colour before the reveal; a 3D object covering information (prices); full-film `backdrop-filter`.

### Sources
d06-th §1.1, §1.7, §2.3 (checked 2026-10-02); distilled 02 video-types §2.5-2.6; distilled 02 techniques §6.4-6.5; E10 report via distilled 03 e09-e12-final-results.


## UI and effect sourcing, the seek-safe port, screenshot rebuild, and the hf-blocks library
<!-- source: pro-video-editor/references/visual-beats.md -->
Load when: a beat needs a UI card, a text effect, an animated component, a rebuilt screenshot, or a reusable block.

Source keys: d05 = distilled/05 image-and-design-assets (§3), d04 = distilled/04 motion-design (§9), d02 = distilled/02 techniques (§4), bp = blueprint/TOOLS_SPEC (2026-10-02). Licence rows were read 2026-09-27..10-01; a registry licence can change: re-read the item's own LICENSE before shipping.

### 1. Search order - never hand-build before searching
1. `npx hyperframes catalog --query "<English description>" --json` (local, sends nothing; English only; "No searchable words" means rephrase in English).
2. `hf-blocks` (the studio's own blocks, section 5).
3. **shadcn registries - the default for students.** The `ui` tool (`python tools/ui.py search "<english description>"`, then `view @registry/item --source`; offline cache, licence tier next to every hit, `add-command` only prints the command) or the `ui-registries` MCP when the profile enables it: `search_items_in_registries`, `view_items_in_registries`, `get_item_examples_from_registries`) searches the verified-permissive registries. Items are read as source; nothing is installed.
4. **21st.dev - optional.** Q-note: the 21st.dev Magic MCP needs a paid account (on the author's account `search`/`get_component` work and AI generation is not active), so it cannot be a course default; the author prefers it first when available ("probably the best source of quality code"). Use it only when the student has an account; never scrape it; do not copy previews, media or metadata; locate the original component author and licence; `ui` marks 21st results `[restricted]`.
5. Hand-build, with the reason written in the beat card.
`[CONFLICT]` (minor): assets.md says catalog first, editing.md says 21st first; both say never hand-build before searching. (src: d05 §3.3)

### 2. Licence tiers (record in `SOURCES.md` for every adopted item: origin URL, `License:`, version/hash, date, author)
| Tier | What | Rule |
|---|---|---|
| ok | MIT/Apache/ISC/CC0 registries (examples read 2026-09-27: @shadcn, @magicui, @motion-primitives, @kokonutui, @eldoraui, @cult-ui, @smoothui, @fancy, @reui, @kibo-ui, @ncdai, @8starlabs-ui, @systaliko-ui, @uselayouts, @motion-lexicon MIT; @spectrumui Apache-2.0) | usable in a client video; keep the notice (MIT/Apache require it) |
| restricted | React Bits and Animate UI (MIT + Commons Clause), Skiper UI (free with credit), PaceUI GSAP (licence unknown) | fine inside a client video where the licence allows; never resell or redistribute the components; unknown = ask |
| excluded | Aceternity UI (forbids source redistribution), coss ui and Origin UI (AGPL-3.0), animate.css (Hippocratic), Hover.css/Hover.dev (paid/proprietary), Preline (Fair Use) | never in a student-repo asset or a client deliverable without a clearance |
Paid kits (Untitled UI) and Adobe font binaries never enter the student repo. shadcn core is MIT but registry items, their dependencies and media carry their own licences: the registry protocol is not permission for every entry. GSAP is a custom "Standard No Charge" licence (not MIT): competing visual animation builders need written consent. (src: d05 §3.1-3.2; d04 §9)

### 3. The seek-safe port (React/Tailwind -> HyperFrames HTML + GSAP)
Never paste a component; re-author it. Never run `npx shadcn add` inside a video project (installs packages, edits files; a known shadcn 4.21 bug prints `[object Promise]`).
Five iron rules (owner, 2026-09-30):
1. **No free clock:** no looping `requestAnimationFrame`, `setInterval`/`setTimeout` animation, `Date.now()`/`performance.now()`, unseeded `Math.random()`, `repeat:-1`.
2. **One paused timeline per composition:** `const tl = gsap.timeline({paused:true})`, registered last as `window.__timelines["<data-composition-id>"] = tl`, never `tl.play()`.
3. **Per-frame animation** (canvas/shader/particles) is a pure function `draw(t)` driven by a proxy tween `tl.to(state,{t:DURATION,duration:DURATION,ease:"none",onUpdate:()=>draw(state.t)},0)`.
4. **No interaction:** hover/scroll/whileHover/onClick become fixed moments on the timeline.
5. **CSS `@keyframes` only** with a finite iteration count and duration; no CSS `transition`.
Translation table: `motion.div initial/animate` -> `tl.fromTo`; `staggerChildren` -> `stagger`; spring -> baked `springEase` (critically damped zeta 1.0 house settle, 0.80-0.85 alive, 0.60-0.70 playful only, < 0.55 do not) or `power3.out`; `useState` timers -> tween a number/index; `lucide-react` -> inline SVG. Tailwind: convert classes to plain CSS in `<style>` for the final render, or use the scaffold's pinned `@tailwindcss/browser` (never `cdn.tailwindcss.com`: unpinned); no `md:`/`hover:`/`transition-*`. Fonts: `@font-face` to local files, wait for `document.fonts.ready` before measuring text. Per-letter randomness: bake the steps with `tl.set` from a seeded hash of (letter index, frame); never `onUpdate`.
Checklist: read the `.tsx` + `SOURCE.md` -> separate static vs animated -> write the final state as static HTML/CSS, then tween from the start state -> `hf_preflight`, `seek_safe_scan.py`, `check` -> snapshot at non-sequential times (e.g. 2.7 s then 0.4 s) to prove seek consistency -> credit and licence in `SOURCES.md`. (src: d05 §3.3; d04 §4.5)

### 4. Screenshot rebuild (owner rule 2026-09-27)
When a screenshot (app, dashboard, site, message) must be animated, rebuild it in HTML/CSS **identically** and animate the elements (counters count up, charts build, lists enter one by one, perfect sharpness, Hebrew/9:16 adaptation). Steps: measure (sizes, spacings, colours by eyedropper, font, radii, shadows) -> build in `hf/` (registry components or Playwright computed styles from a live site) -> **identity check**: `hyperframes snapshot --at <t> --describe false` side by side or 50 % overlay with the source at the same resolution until no visible difference -> animate seek-safe. Do NOT rebuild a testimonial's proof (revenue screenshot, client message): show the original and animate around it (push-in, marker, callout); a rebuild must be identical in every number. A very dense screenshot on screen briefly: a push-in on the image is enough. Automate (proposal): OCR the price region per frame and assert every value is in the allowed set. (src: d02 techniques §4)

### 5. The hf-blocks library (`hf-blocks/`, `tools/hf_blocks.py`)
A block is a self-contained sub-composition that has proven itself and can be dropped into the next video. Contract: (a) lives in `hf-blocks/<name>/` with `block.html`, `demo.html` (a short empty-project demo that embeds it as `compositions/<name>.html`), `block.json`, `README.md` (what it does, properties, duration), `SOURCE.md` (origin + licence); (b) is seek-safe by the five iron rules; (c) **passes `python tools/hf_blocks.py verify <name>`** = `seek_safe_scan.py` with no error AND `hyperframes check` in a throw-away project holding only the demo, before admission; (d) uses only the project palette through `--hfb-*` CSS variables (so `palette_audit.py` passes after re-theming); (e) ids are prefixed with the block name (duplicate ids steal CSS; `add --as NAME` renames them so a block can be used twice). Shipped (all seven pass `verify`): `voice-orb` (driven by the real voice: `hf_blocks.py levels`), `task-steps`, `boarding-pass-stamp`, `notification-stack` (new on top), `film-burn` (procedural overlay; or retime your own 24p burn clip to the cut frame), `speaker-cutout-behind` (plate, dim, text, cutout; needs `cutout`), `caption` (word-timed, Hebrew RTL on the text element only; `hf_blocks.py caption-words`). `python tools/hf_blocks.py add <block> <hf-dir> [--as NAME] [--set plate=assets/video/x.mp4] [--var title=Plan]` copies the block into `compositions/` and prints the host `<div>`; it never edits `index.html`. A block that fails the empty-project test is not admitted.


## Per-beat 3D decision: Blender vs Three.js vs AI-3D vs none
<!-- source: pro-video-editor/references/visual-beats.md -->
Load when: any beat wants depth, a hero object, 3D type, a product turn, or a "flat page is not good enough" note.

Source keys: d04 = distilled/04-engines-motion-3d-colour (three-d.md, motion-design.md); E10 = research/experiments/E10 (2026-10-01). Machine for every measured number: the reference machine. NVIDIA and Apple numbers are unmeasured here. The routing table is a decision aid, not a benchmark winner list. Fuller dated routes: `agent-content/references/three-d-routes.md` (owned elsewhere; assumed present).

### 1. The rule
There is no global "always Blender" rule. Owner, 2026-09-27: "usually Blender, not Three.js"; 2026-09-30: Blender is not mandatory, use Three.js when it genuinely does the job better - **decided per beat and justified in PROMPT.md**. The newer decision governs the taste question; evidence governs the facts below. `[CONFLICT]` (resolved; the older "always Blender" note is project history). (src: d04 three-d §1.3)

### 1b. Who builds the 3D: availability first (rule of 2026-10-03, toolkit author)
1. **AI-3D generation (for example Tripo) is used only if the student connected it.** "Connected" means the student chose it in the install questions (INSTALL.md install-10) and a read-only status check of the connector passes, or the student says so in this session. If it is not connected: do not suggest it, do not call it, do not start a sign-up on your own; offer it once, with its sign-up link as the installer prints it, only if the beat has no other adequate route.
2. **Without it, 3D is built with Blender** (the default builder): modelled or scripted geometry (`bpy`), or a CC0 asset (Poly Haven, Kenney, Quaternius). Blender does not turn a text prompt or a photo into a mesh by itself; a "generated" prop without a connected generator is a modelled one.
3. **Three.js inside HyperFrames when the student chooses it**, or when the beat matches the Three.js row of the table below (data-driven, procedural, many instances, 3D UI with live text, edited in rounds, exact hex). Blender is usually the better builder for photoreal hero objects, glass, metal, skin and relighting; Three.js is usually better for everything that must stay editable and seek-exact inside the composition. Neither is "always": write the reason per beat.
4. Every paid generation still goes through `paid-spend-gate`; being connected is not spend authorisation.

### 2. Decision table (smallest adequate representation wins)
| The beat needs | Route | Entry gate (evidence required) |
|---|---|---|
| real product geometry, logo/text extrusion, glass/metal/skin, a hero material on screen > 2 s, relighting you already approved | **Blender** (EEVEE for stylised; Cycles-HIP only when material fidelity needs it) -> alpha loop -> sprite sheet or WebM | ETA from measured s/frame (below); alpha checked over light AND dark; palette audit of the render |
| data-driven or procedural scene (globe + routes from a list, charts, particles with a seed), 100+ instances, 3D UI cards/phones with live HTML text, edited in rounds, camera synced to the VO, exact hex | **Three.js inside HyperFrames** (GLB from Blender is a good hybrid) | one-second `hf_segment` in delivery mode with `--browser-gpu` renders a non-blank frame; root `data-duration` set; assets loaded before seek; if blank or timeout -> Blender sprite |
| a unique hero prop with no mesh | **AI-3D** (hosted image-to-3D) **only if a generator such as Tripo is connected (section 1b)**; otherwise **Blender** (modelled, or a CC0 asset) | connected AND `paid-spend-gate` first; a clean reference image first; licence of the generator checked (below); cleanup effort accepted; manifest recorded |
| a still that needs small camera motion | a static 2D move in HyperFrames (push-in or pan) | camera move <= 2 % of frame width in the first test (proposal, not a proven threshold); inspect edges around hair, labels |
| a message or UI explanation | **none** - 2D/UI is faster, clearer, more forgiving | say so in the card |

3D wins when: a hero shot without footage (360 turn, exploded view), icons/objects for an explainer, 3D logo/text, impossible camera moves, a blockout used as a reference for AI video, assets reused across many videos. 3D loses when: good stock/footage exists, the style is flat 2D, there is no time for good lighting ("3D with bad lighting looks cheaper than good 2D"), or the content is a process/software explanation. Default: hybrid - 2D for messages and UI, one 3D moment for the hero; in a 15-30 s reel a 2-3 s alpha 3D shot gives most of the effect. (src: d04 three-d §1, §8)

### 3. The beat card (one row per 3D beat in PROMPT.md; G4 checks it)
| beat | what it shows | route | reason (one sentence) | cost/ETA | gate evidence | licence |
|---|---|---|---|---|---|---|
| S3 coin | currency hero lands on the word "revenue" | Blender | metal material on screen 2.4 s | 36 f x 1.2-2.25 s + 1-1.5 min launch | alpha over dark+light, palette audit | own asset |
A beat with no row is a gate failure. The 3D object **reacts to the word** (lands on it; the scene responds with a pulse or camera push), sits between plate and cutout, never covers information (place it inside the UI as the object itself with a contact shadow), and in `launch` the accent colour does not appear before the reveal (a grey world first). A float layer is <= 40 % and a different layout per chapter.

### 4. Blender facts that change plans (the reference machine, measured 2026-09-27/28)
- EEVEE objects 1.2-2.25 s/frame at 384-640 px; EEVEE 3D type 1.0-1.25 s/frame; Cycles-CPU background plates 51-253 s each at 1080p-class; every Blender launch costs 1-1.5 min (shader compile + camera fit) - render several assets per launch. A 48-frame 540 px EEVEE turntable took 7 min (includes setup; not a benchmark). `[MEASURED-lab/LOCAL-only]`
- One heavy renderer at a time: a Blender job next to a render doubled render time (11.5 -> 21.5 min). Batch ALL Blender work before the render; `render_lock`.
- AgX (default since Blender 4.0) turns brand colours pastel: pre-compensate the base colour or use the Standard view transform for exact hex; audit every render against DESIGN.md (pink once leaked in through 3D). Do not carry Blender 4.5 manual assumptions to the installed 5.2; read engine enums instead of hardcoding them.
- Output contract: PNG RGBA 16-bit master (or EXR, resumable) -> WebM VP9 alpha (`yuva420p`) for HyperFrames/Chrome, ProRes 4444 for Premiere/AE (Chrome cannot play ProRes); sprite sheets <= 8192 px per side with `{frames, cols, rows, w, h, loop}`; exclude the duplicate 360 degree endpoint in loops; start sprites on a whole frame; preload sheets so the first frame is not blank; the whole element enters together (scale .72 -> 1 + blur 14 -> 0 over 8 f `expo.out`), a per-glyph pop looks like shards. A sprite over text trips `text_occluded` in `check` (intended).
- A zoom-through must be two-sided: the outgoing shot also ramps (scale + blur, last 4 f, `power2.in`), otherwise it reads as a hard cut with a blur pop.

### 5. Three.js inside HyperFrames (contract summary)
Scene built synchronously; render from the seek time (`hf-seek` event / `AnimationMixer.setTime(t)`); root `data-duration` mandatory (no inference); no rAF or clock deltas; fixed renderer size and `pixelRatio`; one pinned `three` version in both importmap entries (see `dated-versions.md`); Hebrew text as an HTML/CSS 3D layer above the canvas, never `TextGeometry`; delta-integrated simulations are not random-access. WebGL in headless Chrome on AMD can stall (the grade shader did): that is why the one-second `hf_segment` gate exists. `model-viewer` and Rive are not seek-safe (own their loop). Interactive FPS is not render throughput: capture/readback/encode still apply. (src: d04 three-d §3)

### 6. AI-3D, licences and money
Hosted generators spend credits: route through `paid-spend-gate`; start from a clean image of the object. Licence gates (dated 2026-09-27..10-01, re-check): Tripo free output is non-commercial (CC BY 4.0 NC); Meshy free is CC BY 4.0 with credit; Hunyuan3D 2.1 excludes the EU, UK and South Korea for works and outputs; Stable Fast 3D needs registration and < USD 1M revenue; TripoSR is MIT. Local image-to-3D on this machine is limited to CPU models (SF3D, TripoSR); Hunyuan3D/TRELLIS need CUDA/NVIDIA >= 24 GB. A commercial grant does not validate references, trademarks, unseen rear surfaces, topology or product dimensions. Free libraries: prefer CC0 (Poly Haven, Kenney, Quaternius); Poly Pizza = per-asset CC0/CC-BY (credit); Sketchfab: reject NC, credit CC-BY, check NoAI; record URL, creator, licence, date and file hash in `SOURCES.md`. (src: d04 three-d §4-5)

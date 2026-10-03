# UI and effect sourcing, the seek-safe port, screenshot rebuild, and the hf-blocks idea

Load when: a beat needs a UI card, a text effect, an animated component, a rebuilt screenshot, or a reusable block.

Source keys: d05 = distilled/05 image-and-design-assets (§3), d04 = distilled/04 motion-design (§9), d02 = distilled/02 techniques (§4), bp = blueprint/TOOLS_SPEC (2026-10-02). Licence rows were read 2026-09-27..10-01; a registry licence can change: re-read the item's own LICENSE before shipping.

## 1. Search order - never hand-build before searching
1. `npx hyperframes catalog --query "<English description>" --json` (local, sends nothing; English only; "No searchable words" means rephrase in English).
2. `hf-blocks` (the studio's own blocks, section 5).
3. **shadcn registries - the default for students.** The planned `ui` tool (or the `ui-registries` MCP when the profile enables it: `search_items_in_registries`, `view_items_in_registries`, `get_item_examples_from_registries`) searches the verified-permissive registries. Items are read as source; nothing is installed.
4. **21st.dev - optional.** Q-note: the 21st.dev Magic MCP needs a paid account (on the owner's account `search`/`get_component` work and AI generation is not active), so it cannot be a course default; the owner prefers it first when available ("probably the best source of quality code"). Use it only when the student has an account; never scrape it; do not copy previews, media or metadata; locate the original component author and licence; `ui` marks 21st results `[restricted]`.
5. Hand-build, with the reason written in the beat card.
`[CONFLICT]` (minor): assets.md says catalog first, editing.md says 21st first; both say never hand-build before searching. (src: d05 §3.3)

## 2. Licence tiers (record in `SOURCES.md` for every adopted item: origin URL, `License:`, version/hash, date, author)
| Tier | What | Rule |
|---|---|---|
| ok | MIT/Apache/ISC/CC0 registries (examples read 2026-09-27: @shadcn, @magicui, @motion-primitives, @kokonutui, @eldoraui, @cult-ui, @smoothui, @fancy, @reui, @kibo-ui, @ncdai, @8starlabs-ui, @systaliko-ui, @uselayouts, @motion-lexicon MIT; @spectrumui Apache-2.0) | usable in a client video; keep the notice (MIT/Apache require it) |
| restricted | React Bits and Animate UI (MIT + Commons Clause), Skiper UI (free with credit), PaceUI GSAP (licence unknown) | fine inside a client video where the licence allows; never resell or redistribute the components; unknown = ask |
| excluded | Aceternity UI (forbids source redistribution), coss ui and Origin UI (AGPL-3.0), animate.css (Hippocratic), Hover.css/Hover.dev (paid/proprietary), Preline (Fair Use) | never in a student-repo asset or a client deliverable without a clearance |
Paid kits (Untitled UI) and Adobe font binaries never enter the student repo. shadcn core is MIT but registry items, their dependencies and media carry their own licences: the registry protocol is not permission for every entry. GSAP is a custom "Standard No Charge" licence (not MIT): competing visual animation builders need written consent. (src: d05 §3.1-3.2; d04 §9)

## 3. The seek-safe port (React/Tailwind -> HyperFrames HTML + GSAP)
Never paste a component; re-author it. Never run `npx shadcn add` inside a video project (installs packages, edits files; a known shadcn 4.21 bug prints `[object Promise]`).
Five iron rules (owner, 2026-09-30):
1. **No free clock:** no looping `requestAnimationFrame`, `setInterval`/`setTimeout` animation, `Date.now()`/`performance.now()`, unseeded `Math.random()`, `repeat:-1`.
2. **One paused timeline per composition:** `const tl = gsap.timeline({paused:true})`, registered last as `window.__timelines["<data-composition-id>"] = tl`, never `tl.play()`.
3. **Per-frame animation** (canvas/shader/particles) is a pure function `draw(t)` driven by a proxy tween `tl.to(state,{t:DURATION,duration:DURATION,ease:"none",onUpdate:()=>draw(state.t)},0)`.
4. **No interaction:** hover/scroll/whileHover/onClick become fixed moments on the timeline.
5. **CSS `@keyframes` only** with a finite iteration count and duration; no CSS `transition`.
Translation table: `motion.div initial/animate` -> `tl.fromTo`; `staggerChildren` -> `stagger`; spring -> baked `springEase` (critically damped zeta 1.0 house settle, 0.80-0.85 alive, 0.60-0.70 playful only, < 0.55 do not) or `power3.out`; `useState` timers -> tween a number/index; `lucide-react` -> inline SVG. Tailwind: convert classes to plain CSS in `<style>` for the final render, or use the scaffold's pinned `@tailwindcss/browser` (never `cdn.tailwindcss.com`: unpinned); no `md:`/`hover:`/`transition-*`. Fonts: `@font-face` to local files, wait for `document.fonts.ready` before measuring text. Per-letter randomness: bake the steps with `tl.set` from a seeded hash of (letter index, frame); never `onUpdate`.
Checklist: read the `.tsx` + `SOURCE.md` -> separate static vs animated -> write the final state as static HTML/CSS, then tween from the start state -> `hf_preflight`, `seek_safe_scan.py`, `check` -> snapshot at non-sequential times (e.g. 2.7 s then 0.4 s) to prove seek consistency -> credit and licence in `SOURCES.md`. (src: d05 §3.3; d04 §4.5)

## 4. Screenshot rebuild (owner rule 2026-09-27)
When a screenshot (app, dashboard, site, message) must be animated, rebuild it in HTML/CSS **identically** and animate the elements (counters count up, charts build, lists enter one by one, perfect sharpness, Hebrew/9:16 adaptation). Steps: measure (sizes, spacings, colours by eyedropper, font, radii, shadows) -> build in `hf/` (registry components or Playwright computed styles from a live site) -> **identity check**: `hyperframes snapshot --at <t> --describe false` side by side or 50 % overlay with the source at the same resolution until no visible difference -> animate seek-safe. Do NOT rebuild a testimonial's proof (revenue screenshot, client message): show the original and animate around it (push-in, marker, callout); a rebuild must be identical in every number. A very dense screenshot on screen briefly: a push-in on the image is enough. Automate (proposal): OCR the price region per frame and assert every value is in the allowed set. (src: d02 techniques §4)

## 5. The hf-blocks idea (a studio block library)
A block is a self-contained sub-composition or snippet that has proven itself once and can be dropped into the next video. Contract: (a) lives in `hf-blocks/<name>/` with `block.html`, `README.md` (what it does, props, duration), `SOURCE.md` (origin + licence), a 3-second `demo.html`; (b) is seek-safe by the five iron rules; (c) **passes `hyperframes check` and `seek_safe_scan.py` in an EMPTY project before admission**; (d) uses only the project palette through CSS variables (so `palette_audit.py` passes after re-theming); (e) ids are prefixed with the block name (duplicate ids steal CSS). Owner's seed list: voice-orb (driven by the real VO spectrum), task-steps (a 21st component that replaced a weak hand-built one), boarding-pass + stamp, iOS notification stack (a list, new on top), film-burn overlay (the owner's own transition clip beats stock; retime 24p to the cut frame), speaker-cutout with graphics behind, caption component. A block that fails the empty-project test is not admitted. (src: bp TOOLS_SPEC §3 item 13; d04 §9)

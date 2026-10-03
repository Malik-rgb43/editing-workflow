# Technique: screenshot rebuild — rebuild in code, then animate

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from distilled/02 techniques §4, distilled/01 rules-and-gates C10, distilled/04 motion-design §9.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[IDEA]` · `[SOURCED-unverified]` · `[LOCAL-only]`.

## 0. Rule

When a screenshot (an app screen, dashboard, website, chat message) has to be **animated**, rebuild it in HTML/CSS **identically** and animate the elements instead of moving a flat image. The decision is the agent's per case. `[RULE-owner]` (owner, 2026-09-27; wording: recommended, "it depends on you" — so a default, not a law)

**Why:** every element animates on its own (counters count up, charts build, typing, hover, lists enter one by one); the result is perfectly sharp at any resolution and any zoom (a launch camera magnifies UI 150–300 %); colours, Hebrew/RTL and the 9:16 re-layout survive without quality loss.

## 1. When NOT to rebuild

| Situation | What to do instead | Why |
|---|---|---|
| a testimonial's **proof** (a revenue dashboard, a client message, a result screenshot) | show the **original** and animate **around** it: push-in, marker ellipse, a separate callout chip, a count-up in a chip beside it — never animate the screenshot's own numbers | the credibility is in the original; a rebuild must be identical in numbers and details and must not beautify (see the testimonial skill's honesty rules) |
| a very dense screenshot visible for a moment | a push-in on the image is enough | a rebuild costs more than it adds |
| the screenshot's content is itself the claim and cannot be re-created exactly | original + callouts | a rebuilt "approximation" is a fabricated record |
| a third party's real UI used in a paid ad | do not copy trade dress or a real brand's screens; build an **original** UI | rights |

## 2. Procedure

1. **Measure** the source at its native resolution: box sizes, spacings, colours (an eyedropper sample = 5×5 median of a flat fill), fonts (identify the nearest match; Hebrew UI: test look-alike letters ו/ז, ד/ר, ה/ח at the shown size), radii, shadows, icon set. Write the numbers into `hf/DESIGN.md` or a comment block, never from memory.
2. **Build in HTML/CSS inside `hf/`.** UI source order: `hyperframes catalog` search first → a shadcn/other registry component (record its licence in `hf/SOURCES.md`) → by hand. The owner's workflow used 21st.dev as a *motion-language source* (curves, structure), not as importable code: components are React/Tailwind, so port the idea to HTML + a seek-safe paused timeline (no free-running rAF, no CSS transitions, no timers). 21st.dev requires a paid account on the owner's side, so student defaults are shadcn registries (src: TOOLS_SPEC §2). Do not scrape registries or copy their previews/media; locate the component's original author and licence. `[RULE-owner]` `[SOURCED-unverified]` on the licences.
3. **Identity check** before animating: `hyperframes snapshot --at <t> --describe false` (≤ 5 timestamps per call) of the rebuilt screen, then compare **side by side with the source at the same resolution** (50 % overlay or a difference image). Fix until no visible difference. A numeric threshold for the difference image is **unmeasured** (`null`); the gate is a human look at the overlay plus the diff, recorded in `hf/QA.md` with both file names.
4. **Animate** per the clean-and-smooth rules ([clean-smooth-motion.md](clean-smooth-motion.md)): one camera path, whole-number swaps, hero persistence, UI behaving like the real OS (an iOS notification centre is a **list**: the newest on top, the rest slide down). If UI behaviour is unclear, screen-record the real UI once as a reference before building.
5. **Verify numbers:** every price/number visible at any frame must be in the allowed set from the ledger (a rebuild once showed "₪1,99" for "₪1,990"; an in-between value flashed during a per-digit roll). A DOM probe of text vs the ledger's fact list is cheap and deterministic; OCR (Hebrew + English) is only for numbers inside rasters. Both are proposed gates (TOOLS_SPEC §3, item 16) — until they exist, add the check as a manual row in `hf/QA.md`.

## 3. Rules of thumb

- A rebuilt UI card is an **object**: give it perspective, depth of field, a contact shadow; a flat full-frame screenshot with a small push-in is "not good enough" for a launch (owner).
- Hebrew/RTL: `direction: rtl` only on text elements, never `dir="rtl"` on the composition root `[RULE-owner]` (a render-blackening trap on the owner's 0.8.x builds; E12 did **not** reproduce it on 0.8.98 `[CONFLICT]` — keep the rule, re-test per HyperFrames version). Fonts from `hf/fonts/` via `@font-face`.
- Keep text ≥ 40 px at 1080 in launch UI, and a key detail in close-up ≥ 0.9 s.
- Never show a real revenue total, average or "×" uplift unless the client gave it in writing; one illustrative number is labelled as illustrative in the ledger.
- Record where the screen came from and its licence in `hf/SOURCES.md`.

## 4. Failure modes

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| rebuilt UI "looks off" next to the source | spacing/colour/font guessed | measure and overlay | step 1 + step 3 |
| a number is wrong for a frame | per-digit animation or a typo in the rebuild | whole swap; allowed-value check | step 5 |
| the proof lost credibility | the original was rebuilt and prettified | use the original, animate around it | §1 |
| UI "feels fake" | stack instead of list, wrong easing, no depth | real-OS behaviour reference; add depth | step 4 |
| a 21st.dev React component pasted | not seek-safe, licence unknown | port the motion language, record the licence | step 2 |
| text blurred in the feed | not magnified enough | 150–300 % camera magnification until readable | §3 |

(src: distilled/02 techniques §4; distilled/01 rules-and-gates C10; distilled/04 motion-design §9; research E12 — read 2026-10-02.)

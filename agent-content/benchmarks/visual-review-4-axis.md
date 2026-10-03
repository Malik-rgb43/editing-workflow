# Visual review on four axes

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from the owner's `visual-review.md` (distilled/02 qa §3, rewritten) and the QA research critique (T13 OWNER_AUDIT). Added by the owner on 2026-09-29 after he found problems `frame_qa` cannot see ("designs that do not match the vision, clean animations, everything"). Runs **in addition to** `frame_qa` and `hyperframes check`.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[CONFLICT]` · `[IDEA]` · `house preset`.
> Used by: `agent-content/playbooks/wf-06-render-qa.md` stage 7. Reviewer role: [critic-brief.md](critic-brief.md) (this review is the *evidence* the critic builds on).

## 0. What it is

Reviewers look at **contact sheets of every frame** of the rendered file against the project's `hf/DESIGN.md` and `hf/PROMPT.md` and report problems on four axes. It finds what automatic tools cannot: something cut by an edge or hidden behind another element, a stray colour, a pop that is not a "pop", unreadable text.

**Inputs per reviewer:** the `frame_qa` sheets (`all_XX.jpg`, each frame labelled with its number and time; tiles ≤ 180–270 px; zoom only the deciding frames) · `hf/DESIGN.md` · `hf/PROMPT.md` (with the ledger) · the round's notes · a **time range** · an **output file** (`_work/qa/<ver>/review_<range>.md`).
**Each problem:** `time/frame · axis · precise description · severity (blocker | major | minor) · concrete proposed fix`. A reviewer returns ≤ 10 lines; detail goes in the file.

Severity: **blocker** = the film cannot ship (content lost, a wrong number, a visible glitch at a key moment); **major** = a viewer notices and it hurts the brief; **minor** = polish. Release needs **no blocker and no major** `[RULE-owner]`.

## 1. Axis 1 — composition and cropping

- Is anything cut by the frame edge that was not meant to be (a letter, word, card, icon, face, the top of a head)?
- Is anything cut by, or peeking out from behind, another element (a video object behind a card, a tip sticking out)?
- Does every wipe, split or reveal finish in a clean state (no stuck halves or triangles)?
- Is text inside the safe zone? (9:16 house policy: key text top ≥ 300, bottom y ≤ 1248, left ≥ 140, right ≥ 192; caption rail bottom **never below y 1450**; a stricter project limit in DESIGN.md wins.) Do captions avoid the face and mouth?
- Is the speaker centred and the head never cut (unless intentional)?

## 2. Axis 2 — fidelity to DESIGN.md and the vision

- Colours only from the palette table; fonts and weights only those in DESIGN.md, ≤ 2 weights per frame; radii and shadows from the tokens; the declared surface languages kept (never mixed in one card).
- Consistency: the same element type looks the same every time. **No AI look**: no small corner labels, random glow, meaningless gradient, generic stock, clutter. Hierarchy: one clear focus per frame; nothing competes with the speaker or the main title.
- The vision: what is on screen matches what PROMPT.md promised **at that moment** — no missing event, no out-of-context element; photos and B-roll in frame, sharp enough, graded consistently with the plate; the accent colour first appears at its declared frame.

## 3. Axis 3 — clean animation

- No jump or pop (an element appearing or disappearing without a transition, or changing position or size in one frame).
- No text or cards overlapping during a transition for more than 3 frames.
- No word or element entering at a wrong spot and then "fixing itself" (a centre-growth shift; an exit that starts before the last word landed).
- Entrance and exit match the motion tokens (expo/power2, no bounce on text, exit shorter than entrance).
- Shape morphs are smooth with content inside; nothing cut mid-morph.
- No transition repeated back to back; the camera is smooth with no sudden stop.
- Timing: every element holds long enough to read (a word ≥ 0.25 s, a card ≥ 0.9 s; house presets).

## 4. Axis 4 — readability and flow

Every caption readable (contrast against the footage under it, size, not blurred while it should be read); every numeric or UI detail readable at its size; the first 3 seconds grab (hook); the ending (end card) clean and legible; flow — nothing confusing the order of reading.

## 5. Process

1. `frame_qa` produces the sheets (automatic checks come **first** — seconds, no tokens).
2. **Scale the review to the film:** `< 20 s` → a **self-review** on the sheets (`frame_qa` + `motion_qa` + the four axes); `≥ 20 s` or a client delivery → **ONE reviewer** continued between rounds (message with the fix list only); the first round of a long project may split the whole film across **2–4 reviewers** by range; later rounds only **flagged or changed ranges**; derivatives (other ratios) → **axes 1 and 4 only** (axes 2–3 are inherited from the master unless the layout changed motion). `[CONFLICT]` resolved to the later, evidence-backed rule: a 10 s test with a four-axis sub-reviewer cost ~160 k tokens, and 4 agents × every frame × 4 rounds burned the quota in two sessions.
3. Merge the reports; **look yourself at every blocker/major on the sheet**; fix everything in **one** pass; re-render once; the same reviewers verify their own findings on changed ranges.
4. Wait for **all** reviewers before patching or rendering.

## 6. Limits (from the QA research; keep them in view)

- The palette rules in the owner's original file ("gold the only accent, sky for info, paper/dark-glass surfaces") belong to **one project's DESIGN.md**; they are scoped brief inputs, not universal rules. The project's DESIGN.md governs.
- The pixel margins are the owner's dated house policy, **not** the current universal platform protection (the Meta placement page could not be verified on 2026-10-01). `[SOURCED-unverified]` `[PERISHABLE]`
- "Sheets of every frame" is **not** evidence that a model inspected every frame at readable resolution; record the coverage actually inspected.
- Continuing the same reviewer can anchor it to its earlier verdict; a final blinded audit is a separate step when stakes are high.
- A reviewer is a model: it can nominate candidates; a human Hebrew reader is the authority on Hebrew copy, look-alike letters and reading comfort.

## 7. Example report lines (synthetic)

```text
00:07.20 / f216 · axis 3 · the note line dims before the word is focused; two cards overlap for 5 frames · major · start the dim at f220
00:08.00 / f240 · axis 2 · accent first appears 2 frames before the declared hit frame · minor · move the bloom to f240
00:11.10 / f333 · axis 4 · CTA pill text contrast against the accent measured below 4.5:1 · major · use #0E1116 text (already in DESIGN.md)
```

## 8. Failure modes

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| a reviewer returns a wall of text | no output file / no line limit | file + ≤ 10 lines | §0 |
| reviewers disagree on a frame | tiny tiles | zoom the deciding frame | tiles ≤ 270 px; zoom rule |
| the review misses a one-frame vanish | the sheet shows it as a cut | look at reveal frames; keep the previous scene underneath | clean-smooth T6 |
| quota burned | all-frame review on every round | §5 step 2 | length scaling |

(src: distilled/02 qa §3, §10; distilled/01 rules-and-gates F3–F5; T13 OWNER_AUDIT — read 2026-10-02.)

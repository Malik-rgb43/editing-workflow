# Concept cards, BRIEF.md and the hand-off

Load when the blocking rows are locked and you write the three concepts, `hf/BRIEF.md`, the rights facts, or the hand-off.

## 1. Three concept cards (only if the user did not already fix a concept)
| Card | Meaning |
|---|---|
| **Proven** | the pattern that already works for this type and platform; the lowest-risk route |
| **Bold** | one deliberate departure in structure, hook device or visual language |
| **Wild** | breaks a convention of the category; highest upside, highest risk; still obeys every locked row |
Cards must differ in **concept**, not polish: they differ on at least two of (hook device, structure, visual language). Regenerate the weakest card until they do.

Card template (one short paragraph each, in the user's language):
```
<Proven|Bold|Wild>: <logline in one sentence>
0-3 s: <what is seen and said>
Beats: <t0-t1 s what / t1-t2 s what / ...>   (seconds add up to the locked LEN)
Look: <palette hex x3-5, fonts>   Motion: <language>
3D / B-roll plan: <per beat, with a reason>
Obeys: <ledger ids>    Risk: <one sentence>
```
Then recommend one card with a reason in one line. Chosen elements enter the ledger as `A` rows, `proposed` until the user says yes, then `locked`. "חדש לגמרי" = nothing carried over from earlier versions except facts and the logo. A taste decision between several visual options (palette, caption look) may go to `visual-choice-board` instead of more rounds.
No cards before FMT, LEN, TON, BAR, CTA, FILE (and STR/COLOR for footage, VAR for several files) are locked.

## 2. hf/BRIEF.md
Fill the shared template `agent-content/techniques/templates/BRIEF.md` (frontmatter: type, ratios, fps, length, flow, workflow, language, ledger pointer; then Intent, Source and rights, Guards, Claims allowed, Reference). It is five lines of fact plus an intent paragraph, NOT the spec; the spec is `hf/PROMPT.md`. Every value comes from the user's message, the files, or a default marked `D` in the ledger; an unanswered field is written `OPEN: <question>`, never filled with a guess. Never invent a brand, price, claim, logo or colour.

## 3. Source and rights (G6)
- Record footage ownership and consent for any person on screen, the licence of each music/stock file, and whether the video is client work, an ad, or the student's own organic post.
- `License: unknown` material: block for client or ad work; allowed only for the student's own organic account, with a warning in the delivery message (decision default Q2).
- Third-party brand sounds, logos and likenesses: state the risk; never use a person's likeness or voice without consent.
- Rights unclear and AI generation planned: `blocked` until clarified; paid generation also needs `paid-spend-gate`.
- Never infer a licence from a file name.

## 4. Hand-off checklist (what intake passes on)
1. `_work/intake/INTAKE_LOG.md`, `source_ls.txt`, `probe.json`; the `<ledger>` in `hf/PROMPT.md`; `hf/BRIEF.md`; the chosen card; the variants rows (one row per file: ratio, hook, platform, ledger id).
2. `ledger_check.py` exit 0 (G1, G2) and, once the structure exists, `--prompt` exit 0 (G7).
3. Next owner: reference stage if a reference exists (`reference-style-matching`), else the PROMPT writer (`agent-content/techniques/frame-spec-prompt.md`), then `pro-video-editor`. Present PROMPT.md and wait; the line `PROMPT_APPROVED <date> "<the user's words>"` goes into `hf/CHANGELOG.md` only after the user's explicit yes.

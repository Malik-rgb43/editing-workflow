# Which decisions gain from a board, and which do not

Load before deciding whether to build a board and what real content to feed it. Source: distilled 07 choice-boards sections 1, 4, 9, 10 (reasoned from one scripted prototype, E13; no human participant, no hosted-Claude run and no measured time saving exist; the bundled-chat control also needs one round). The honest advantage is simultaneous visual comparison, not fewer messages.

## 1. Build when
Any choice whose options are visual (2 or more options) goes on a board: options cannot be judged from names ("Rubik Black" vs "Heebo ExtraBold"), and glyph shape or a caption's motion is judged in context. A chat question only for non-visual choices or a single option. No footage yet (motion or launch pieces): feed a snapshot of the current composition, or a plain frame in the project palette.

## 2. Table
| Decision | Why a live board beats chat | Real content to feed |
|---|---|---|
| Hebrew caption font | glyph shape and look-alikes (ו/ז, ד/ר, ה/ח) are invisible in a font name; a default font is a default, not law | the project's real caption line plus a keyword containing the look-alike letters; a mixed Hebrew/English/number line; embedded font files with licence notes |
| Caption entrance/exit, card vs word-by-word vs karaoke | motion cannot be judged from a description | the caption on the real still; exit mirrors entrance |
| Easing / motion feel | curves are felt, not described | the project's own element and duration |
| Palette (locked per project) | contrast and mood depend on the real frame; rejecting must be cheap | the actual still with the palette applied; skin tone not shifted; contrast chip |
| Transition set | candidates side by side | two real clips or stills; the user's own transition library first |
| B-roll / stock shortlist | pick N from M and reject with a reason | licensed thumbnails with source and licence shown (use `text` options with the filename; do not embed unlicensed media) |
| Hook text variants (first 2 s) | the hook decides retention | the script text + first frame, as `text` options. A motion hook (movement, cut, timing) is judged as short clips in Studio or on the notes page, not on a board |
| Layout / safe zone | one decision for several deliverables | the real frame with the platform overlay limits |

## 3. Do NOT build when
- The user already named the choice ("use Rubik, it's decided"): apply it.
- A project rule already fixes it (a locked palette, caption exit mirrored, the banned list): keep rules as constraints on the option set, not as options.
- It needs audio or long-form judgement, or it is a motion hook (show short clips in Studio or on the notes page instead).
- The options cannot be rendered without a paid generation: use a still or a draft first, and count that cost through `paid-spend-gate`.
- It would replace the deliverable of a prompt skill that forbids interactive files (the Seedance prompt skill's output must stay plain text); collect a taste decision upstream, before invoking it.

## 4. Board hygiene
1. Real content only; never placeholder text.
2. 8-12 options is the target (2-12 allowed); the "none + comment" slot is always present and is the commonest honest answer to a premature option set.
3. Options come from the project's constraints: filter by DESIGN.md and the banned list before building (a board contradicting a locked rule is a defect).
4. Phone frame 9:16 with the safe-zone overlay when the deliverable is vertical; add other ratios only when delivered.
5. Counting: the board is a time cost. Record build + open + decision time in the timing ledger and compare with a bundled-chat baseline before claiming a saving.
6. Privacy: the local HTML never leaves the machine. A hosted page is a hosted copy: no private client stills without a per-client decision, never a public link.

## 5. Failure modes
| Symptom | Cause | Fix |
|---|---|---|
| the agent cannot read the pick | the UI summary or browser storage was used instead of the file | serve the board (`make_board.py serve`): the confirm button hands the picks over; otherwise have the user save or paste `choices.json` and run `verify` |
| options differ in the final render | preview is not the engine render; font fallback | re-render a still in the real engine; embed the same font file the project uses |
| a Hebrew choice made on lorem text | placeholder content | rebuild with the real line and the look-alike keyword |
| the user cannot say "none" | too-narrow option set | the none slot is mandatory and requires a comment |
| the wrong option exported | shortcuts firing inside the text box | the page ignores typing in inputs (covered by the browser checklist) |

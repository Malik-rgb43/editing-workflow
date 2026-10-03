---
name: choice-board
description: Build one interactive HTML board that shows every option of a visual taste choice (fonts, caption animations, easings, palettes, transitions, layouts, hook variants) on the user's real text and still, and read the click back as choices.json. Use when the user hesitates between 3 or more visual options. Hebrew - לא יודע איזה פונט, תראה לי אפשרויות, איזו אנימציה, בוא נבחר, לוח בחירה. NOT for a choice already made, a single obvious option, audio judgements, or the Seedance prompt deliverable.
compatibility: scripts/make_board.py needs Python 3.10+ (stdlib only); any modern browser opens the result offline. Node is optional (syntax check in the tests).
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# choice-board

One page, every option, the user's real content, one click each, and a `choices.json` the agent can validate. The page is a local file: no account, no upload, no remote resource.

## Rules that never bend
1. **Build only when it earns its round**: 3 or more visual decisions pending, or options that cannot be judged from names. A decision already made, one obvious option, or a project rule that fixes it (locked palette, banned list) is applied, not boarded (`references/decision-types.md`).
2. **Real content only**: the user's text, colours and a footage still. Placeholder text is refused by the builder.
3. **Options come from the project's constraints**: filter by DESIGN.md and the banned list first; keep rules as constraints, not as options.
4. **No remote resources and no private upload.** Client stills and footage stay on this machine. A hosted (Artifact) copy needs a per-client decision and is optional (`references/artifact-variant.md`).
5. **The pick is a fact only after readback**: run `verify` on the file; a UI summary or a chat paraphrase is not proof. Then ledger -> PROMPT -> code.
6. A browser preview is not the final engine render; re-render one still or sample frame in the real engine before treating a font or motion pick as final.
7. Skills are procedure, not permission; unmeasured: no human or hosted-Claude time saving has been shown (E13 control: a bundled chat question also costs one round). Do not claim speed.

## Procedure
1. **Warranted?** (rule 1). If not, ask one bundled chat question or apply the stated choice.
2. **Gather**: the real caption/headline line, a keyword that contains ו/ז, ד/ר or ה/ח (for fonts), the palette/DESIGN constraints, a still frame (owned or licensed), the banned list, the safe-zone preset.
3. **Write `spec.json`** (`references/spec-format.md`, sample `references/sample-spec.json`): 8-12 options per decision (2 minimum, 12 maximum), embedded font files carry their licence text. Do not offer a font whose look-alike letters you have not seen at full size.
4. **Build**: `python scripts/make_board.py build spec.json --out <project>/_work/board`. Read the warnings it prints.
5. **Check it in a browser** (`references/browser-checklist.md`): at least items 1, 3, 4, 6 and 10. Fix the spec, rebuild. A board that fails 3, 4 or 6 is not sent.
6. **Send** the path: "open `choice-board.html` by double click, pick in every tab (digits 1-9/0/q/w, n = none), press Export, and save `choices.json` next to the project or paste the JSON here."
7. **Read back**: `python scripts/make_board.py verify <dir>/board_manifest.json choices.json`; state the decision lines to the user in one message.
8. **Apply**: ledger rows (`src` U, measurable `spec`), DESIGN.md and PROMPT.md first, then code; rejected options become banned-list candidates; then re-render one still in the engine.

## Gates
States: `pass | fail | blocked | n/a` with a reason; a missing screenshot, empty readback or unrun test never passes.
| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G1 real content | the spec's `text` is the user's line; a still is the project's own; builder refused no placeholder | `build` exit 0 + the spec | rebuild with real content | choice-board | the user edits their text |
| G2 size and shape | 2-12 options per decision (target 8-12); automatic none + comment slot; phone frame with the safe zone for vertical work; keyboard picks | build summary + checklist items 3, 5 | trim or add options | choice-board | option set changes |
| G3 readback | `verify` exits 0 and the decision lines were quoted to the user | `verify` output | ask once for the file or the pasted JSON | choice-board | any rebuild (board id changes) |
| G4 Hebrew fonts | the keyword specimen and the look-alike row were viewed for every offered font; embedded fonts have licence text | screenshot or checklist item 10 | drop the font | choice-board | font list changes |
| G5 offline and private | no remote resource request, no client asset uploaded | checklist item 1 + `remote_hits == []` in the tests | remove the reference; ask for a privacy decision | choice-board | any hosted copy |
| G6 constraints | no option violates DESIGN.md or the banned list | the spec's `banned` + a read of the options | filter, rebuild | choice-board | DESIGN.md changes |
| G7 engine check | one still or frame re-rendered in the real engine with the picked font/palette/motion | the rendered frame | re-render; adjust | choice-board | pick changes |

## Stop conditions
- The user answers in chat instead: accept it, log it as the pick (`src` U), skip the board.
- `verify` reports a board-id mismatch: the page was rebuilt after sending; ask for the export from the current board.
- Fewer than 2 options survive the constraints: say so and ask one question.

## References and scripts
- `references/spec-format.md`: load when writing the spec, building, or reading `choices.json` (fields per kind, page behaviour, readback, after-readback steps).
- `references/decision-types.md`: load when deciding whether to build a board and which real content to feed it.
- `references/browser-checklist.md`: load when a build finished and the board is about to be sent to the user.
- `references/artifact-variant.md`: load when the user asks for a hosted Claude Artifact or a client lists an Artifact tool.
- `references/sample-spec.json`: load when you need a working spec to copy (6 decisions, 20 options).
- `scripts/make_board.py` (build, verify), `scripts/test_make_board.py` (13 tests; also `make_board.py --self-check`).

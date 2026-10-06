---
name: visual-choice-board
description: Build one HTML board showing every option of a visual choice (font, caption animation, easing, palette, transition, layout, hook text) on the user's real text and still, and read the pick back. Use for any choice with 2 or more visual options, and before captions are built when their style is not fixed. Hebrew - לא יודע איזה פונט, סגנון כתוביות, תראה לי אפשרויות, איזו אנימציה, לוח בחירה. NOT for a made choice, one option, non-visual choices, a motion hook (clips in Studio), or Seedance prompts.
compatibility: scripts/make_board.py needs Python 3.10+ (stdlib only); any modern browser opens the result offline. Node is optional (syntax check in the tests).
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# visual-choice-board

One page, every option, the user's real content, one click each, and a `choices.json` the agent can validate. The page is a local file: no account, no upload, no remote resource.

## Start: connections
If `<project>/_work/connections.json` from this session exists (written by the router or `pro-video-editor`), read it; otherwise run `python tools/connections.py -o <project>/_work/connections.json` (about 1 s, presence only) and read your own tool list (claude.ai connectors appear only there). For this skill: the browser pane or Playwright MCP (to open the board for the user), the HyperFrames CLI (`snapshot` of the current composition when there is no footage still), Iconify MCP only when an option needs a real icon or logo. Say use / not needed / fallback in one line, then continue. A missing connection never stops the work; anything paid goes through `paid-spend-gate`.

## Rules that never bend
1. **Any choice whose options are visual (2 or more options) goes on a board**; a chat question only for non-visual choices or a single option. A decision already made, or a project rule that fixes it (locked palette, banned list), is applied, not boarded (`references/decision-types.md`). Hook TEXT variants are `text` options on the board; a motion hook (movement, cut, timing) cannot be judged from a still: show it as short clips in Studio or on the notes page (`revision-notes-handler`), not on a board.
   **Always built - the caption style board:** when the video has captions and the user or the brand has not fixed their font, animation and height, ONE board settles all three before any caption is built (`hebrew_fonts.py spec ... --caption-style --still <a frame of the video>`), also under full control: your pick goes first as option A, labelled as your recommendation. Serve it and open it in the browser pane at the intent step (`pro-video-editor` Step 2), not after the draft.
2. **Real content only**: the user's text, colours and a footage still. No footage yet (motion or launch pieces): a snapshot of the current composition (`snapshot --describe false`), or a plain frame in the project palette. Placeholder text is refused by the builder.
3. **Options come from the project's constraints**: filter by DESIGN.md and the banned list first; keep rules as constraints, not as options.
4. **No remote resources and no private upload.** Client stills and footage stay on this machine. A hosted (Artifact) copy needs a per-client decision and is optional (`references/artifact-variant.md`).
5. **The pick is a fact only after readback**: run `verify` on the file; a UI summary or a chat paraphrase is not proof. Then ledger -> PROMPT -> code.
6. A browser preview is not the final engine render; re-render one still or sample frame in the real engine before treating a font or motion pick as final.
7. Skills are procedure, not permission. No time saving has been measured (E13): claim none.
8. **The user names their candidate fonts** ("between these two"): board exactly those, with their files embedded when the licence allows; a font they have only installed is shown with the "system font: may fall back" chip and must be a file in `hf/fonts/` before it is used. **No font named = a font board, never a silent default.** Read the caption and on-screen language first (Round 0 / PROMPT.md). Not Hebrew: the same command with `--font "Family=font-file=licence-file"` for each OFL font that covers that script (downloaded only after the user's yes, like the Hebrew fetch), no catalogue fonts, same rules; the steps below are the Hebrew route. When the user has not named a font (and no approved style or client font fixes it), offer real Hebrew fonts rendered with their own line: `python scripts/hebrew_fonts.py fetch --default --to <project>/_work/fonts` prints what would be downloaded (8 OFL fonts, about 1.1 MB, from github.com/google/fonts); after the user's yes, the same command with `--yes`; then `hebrew_fonts.py spec --default --to <project>/_work/fonts --text "<their line>" --keyword <a word with ו/ז, ד/ר or ה/ח> --caption-style --still <a frame> -o <project>/_work/board/spec.json` (drop `--caption-style` for a title font only) and build/serve as below. Never offer system fonts for a Hebrew pick (they look alike and fall back). "You choose" from the user = the board is still shown, with your pick first as option A (the house preset Rubik for Hebrew), labelled as your recommendation. After the pick, copy that font file and its OFL.txt to `hf/fonts/`.

## Procedure
1. **Warranted?** (rule 1). If not, ask one chat question (non-visual or single option) or apply the stated choice.
2. **Gather**: the real caption/headline line, a keyword that contains ו/ז, ד/ר or ה/ח (for fonts), the palette/DESIGN constraints, a still frame (owned or licensed; no footage: a composition snapshot or a palette frame, rule 2), the banned list, the safe-zone preset.
3. **Write `spec.json`** (`references/spec-format.md`, sample `references/sample-spec.json`): 8-12 options per decision (2 minimum, 12 maximum), embedded font files carry their licence text. Do not offer a font whose look-alike letters you have not seen at full size. Fonts come from `references/hebrew-fonts.json` (19 OFL families with sizes, styles and E03 scores; `python scripts/hebrew_fonts.py list`); a font decision is generated by `hebrew_fonts.py spec` (rule 8).
4. **Build**: `python scripts/make_board.py build spec.json --out <project>/_work/board`. Read the warnings it prints.
5. **Check it in a browser** (`references/browser-checklist.md`): at least items 1, 3, 4, 6 and 10. Fix the spec, rebuild. A board that fails 3, 4 or 6 is not sent.
6. **Serve and wait (default)**: start `python scripts/make_board.py serve <dir>` as a BACKGROUND command (it prints the local url, then waits), open the url for the user (browser pane, or give them the link), and say: "pick in every tab (digits 1-9/0/q/w, n = none) and press **אישור הבחירה ✓**". The page sends the picks to the server, the server checks them with `verify`, writes `choices.json` and exits with the decision lines - the background command finishing IS the readback: the user exports and pastes nothing. A wrong pick goes back to the page with the reason and the server keeps waiting. No background commands in your host, or the user wants the file: send the path instead ("open `visual-choice-board.html` by double click"); then the same button saves `choices.json`, which they attach or paste.
7. **Read back**: with `serve`, the finished command's output already holds the verified decision lines (and `<dir>/choices.json`); otherwise run `python scripts/make_board.py verify <dir>/board_manifest.json choices.json`. State the decision lines to the user in one message.
8. **Apply**: ledger rows (`src` U, measurable `spec`), DESIGN.md and PROMPT.md first, then code; rejected options become banned-list candidates; then re-render one still in the engine.

## Gates
States: `pass | fail | blocked | n/a` with a reason; a missing screenshot, empty readback or unrun test never passes.
| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G1 real content | the spec's `text` is the user's line; the still is the project's own (no footage: a snapshot of the current composition or a plain frame in the project palette); builder refused no placeholder | `build` exit 0 + the spec | rebuild with real content | visual-choice-board | the user edits their text |
| G2 size and shape | 2-12 options per decision (target 8-12); automatic none + comment slot; phone frame with the safe zone for vertical work; keyboard picks | build summary + checklist items 3, 5 | trim or add options | visual-choice-board | option set changes |
| G3 readback | `serve` exited 0, or `verify` exits 0, and the decision lines were quoted to the user | the `serve` / `verify` output | serve timed out (exit 3; the board stays on disk): ask once whether to keep waiting, or for the file / pasted JSON; board-id mismatch: the page was rebuilt after sending, ask for a pick on the current board | visual-choice-board | any rebuild (board id changes) |
| G4 Hebrew fonts | the keyword specimen and the look-alike row were viewed for every offered font; embedded fonts have licence text | screenshot or checklist item 10 | drop the font | visual-choice-board | font list changes |
| G5 offline and private | no remote resource request, no client asset uploaded | checklist item 1 + `remote_hits == []` in the tests | remove the reference; ask for a privacy decision | visual-choice-board | any hosted copy |
| G6 constraints | no option violates DESIGN.md or the banned list | the spec's `banned` + a read of the options | filter, rebuild | visual-choice-board | DESIGN.md changes |
| G7 engine check | one still or frame re-rendered in the real engine with the picked font/palette/motion | the rendered frame | re-render; adjust | visual-choice-board | pick changes |

## Stop conditions
- The user answers in chat instead: accept it, log it as the pick (`src` U), skip the board.
- Fewer than 2 options survive the constraints: say so and ask one question.

## References and scripts
- `references/spec-format.md`: load when writing the spec, building, or reading `choices.json` (fields per kind, page behaviour, readback, after-readback steps).
- `references/decision-types.md`: load when deciding whether to build a board and which real content to feed it.
- `references/browser-checklist.md`: load when a build finished and the board is about to be sent to the user.
- `references/artifact-variant.md`: load when the user asks for a hosted Claude Artifact or a client lists an Artifact tool.
- `references/sample-spec.json`: load when you need a working spec to copy (6 decisions, 20 options).
- `references/hebrew-fonts.json`: load when a font is to be chosen (rule 8): 19 OFL Hebrew families, files, sizes, styles, E03 scores; read through `scripts/hebrew_fonts.py`.
- `scripts/ui/` (tokens.css, Heebo subset + OFL-Heebo.txt): the shared look of the student screens; both boards embed it, no network.
- `scripts/make_board.py` (build, verify), `scripts/test_make_board.py` (13 tests; also `make_board.py --self-check`).

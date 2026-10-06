# revision-notes-handler: task evals

Status: specified; deterministic checks only; model eval not run (decision default Q4). Oracles are files on disk (CHANGELOG, PROMPT with its `<ledger>`, patch file, render log) and the message sent. Fixtures are synthetic (generated test clip and a tiny HTML project), never client media.

## T1 Replace, not polish
- **Setup:** an approved project with a draft; note: "boring at 5 s" (a static caption over a static B-roll beat).
- **Oracle:** `hf/CHANGELOG.md` round section, `hf/PROMPT.md` (ledger block and structure), `python scripts/round_check.py hf/CHANGELOG.md --prompt hf/PROMPT.md --json`.
- **Pass:** the note has `class: replace-concept` and a `replacement:` that names a different beat concept (not a tweak of the old one); the new ledger id appears >= 2x in PROMPT.md and PROMPT.md was edited before any code file; `round_check` has no `polish_wording` or `no_replacement`.
- **Fail signals:** timing/easing nudged on the same beat; code edited first.

## T2 Batched round, one full render
- **Setup:** six notes arrive across two messages (a transition glitch, a font change, a typo, "SFX loud", "boring at 20 s", "the speaker is never centred").
- **Oracle:** CHANGELOG round section, render log, the presentation message.
- **Pass:** a "collecting" message was sent first; the round log has 6 numbered notes in the user's order; exactly one `RENDER full` line (0 would also be valid only if every note were audio-only); the final message is numbered 1-6 by the user's notes, shows the FULL ledger, a QA line from the new file and an explicit gap or tick per note; `round_check.py --require-present` exits 0 after `PRESENTED` is written.

## T3 Audio-only
- **Setup:** note "music too loud"; project has a premixed `mix.wav` and a cue file.
- **Oracle:** CHANGELOG, tool log, file mtimes.
- **Pass:** `class: audio-only`, `render: none`; the cue file changed, the mix tool and the remux ran; no full-render line; the new final file's loudness measured and quoted; the picture file is unchanged.

## T4 Global rule
- **Setup:** note "the speaker is not centred at 0:17" in a film where the same fault occurs at 0:10 and 0:31.
- **Oracle:** the round log `occurrences:` field and the face-centre audit output.
- **Pass:** class `global-rule`; `occurrences` lists all three places (found by auditing the whole film, not only the noted time); each occurrence verified after the patch.

## T5 Patch discipline
- **Setup:** a small HTML project whose `index.html` has `data-hf-id` attributes (as added by Studio) and a duplicated anchor string.
- **Oracle:** `python scripts/apply_patch.py patch.json` output and the file.
- **Pass:** the patch lives in a JSON file; with a non-unique anchor the tool exits 1 and writes nothing; after fixing the anchor it exits 0, ids are stripped, a backup file exists, the re-read matches.

## T6 Mid-render note
- **Setup:** a full render is running (stub process) 30 % done when a new note arrives.
- **Oracle:** the agent's actions and the process list.
- **Pass:** it stops only its own process tree (checks the lock first), rebatches the new note, reruns once after the collection window; if the render were 70 % done it finishes and logs the note for the next round unless it is a blocker.

## T7 Order check
- **Setup:** a patch file created BEFORE the PROMPT.md edit (mtimes).
- **Oracle:** `round_check.py --patch ... --prompt ...`.
- **Pass:** `code_before_prompt` error; the agent reverts, updates PROMPT first, repatches.

## T8 Restructure asks before patching
- **Setup:** an approved project with a 40 s draft; note: "too long, move the offer earlier" (the offer sits at 0:22 after two proof beats).
- **Oracle:** `hf/CHANGELOG.md` round section, `hf/PROMPT.md` (`<structure>` and ledger), the patch file mtime, the chat log, `python scripts/round_check.py hf/CHANGELOG.md --prompt hf/PROMPT.md --patch tools/patch_rN.json`.
- **Pass:** `class: restructure`; the new order is written in PROMPT.md `<structure>` and shown to the user (with the storyboard page if beats change) before any patch; the patch file is newer than the user's yes; the log line has `order:` and `asked:`; `round_check` exits 0.
- **Fail signals:** beats moved in code before the user saw the new order; `round_check` reports `restructure_not_asked` or `no_order`.

## T9 Music swap
- **Setup:** note "use a calmer song"; the project has a premixed `mix.wav` and a licensed library track chosen by the user.
- **Oracle:** CHANGELOG, the ledger, tool log, file mtimes.
- **Pass:** `class: music-swap`, `render: none`, a `licence:` field pointing at a ledger licence row; remix + remux ran; no full-render line; loudness measured on the new file; cuts timed to the old beats, if any, appear as separate fix notes.

## Deterministic checks (run now, no model)
`python scripts/round_check.py --self-check` and `python scripts/apply_patch.py --self-check` must print `self-check: ok`.

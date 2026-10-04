# Round log, ledger lines and the presentation message

Load when opening a round, writing the CHANGELOG, adding ledger rows, or composing the reply that presents the fixes. `scripts/round_check.py` parses the round log format below.

## 1. Round log (`hf/CHANGELOG.md`)
```
## Round 3 (2026-10-05)
COLLECTING until 14:35
1. "the transition at 25 is bad" @ 0:24-0:26 | class: fix | ledger: L21 | cause: hidden source cut at 24.9 s, pre-roll 3 f | frames: _work/notes/r3_n1.jpg
2. "משעמם" @ 0:05 | class: replace-concept | ledger: L22 | cause: static caption over static B-roll | replacement: split-screen proof card, number counting up | frames: _work/notes/r3_n2.jpg
3. "SFX too loud" | class: audio-only | ledger: L23 | cause: gain above -18 dB under VO | render: none
4. "the speaker is never centred" | class: global-rule | ledger: L24 | cause: zoom origin not on face x | occurrences: 0:10, 0:17-0:24, 0:31 | frames: _work/notes/r3_n4.jpg
PATCH: tools/patch_r3.json
RENDER full _work/drafts/<name>_v3.mp4
PRESENTED 2026-10-05
```
- Notes are numbered in the user's order and words (1a, 1b for split claims). Fields are separated by ` | `.
- One `RENDER full` line per round at most; none for an audio-only round.
- `PRESENTED <date>` closes the round (the router reads it to decide whether the round is still open).

## 2. Ledger rows for notes
Each note adds a row to the `<ledger>` block of `hf/PROMPT.md` (ids continue; row format: `video-brief-intake/references/ledger-template.md`; the shared rules are in `agent-content/techniques/concept-ledger.md`): `said` = the user's words with the round tag, `spec` = the measurable fix, `where / when` = the range, `acceptance check` = how the next draft proves it. Replace-concept: rewrite the range in the PROMPT structure (frames, px, easing, sound). A global rule row lists every occurrence in `where / when`. A motion note also becomes a row in the project's motion table. Then cite the new ids in PROMPT `<structure>` (each id appears at least twice). Order is always **ledger -> PROMPT -> code**.

## 3. Presentation message (file first, then this)
Send the file or Studio link immediately, then:
```
סבב 3 - <name>_v3: <path or Studio link>
ההערות שלך:
1. ✓ "<the user's words>" - סיבה: <cause>. עכשיו: <what changed> (0:24.6-0:25.4 / f738-762)
2. ✓ "<...>" - <what changed>
3. ✗ "<...>" - פער פתוח: <why> + חלופה: <alternative>
נאמנות לבריף: L01 ✓ · L02 ✓ (f30-60) · ... · L24 ✓ (סבב 3)
בדיקות: frame_qa 0 · caption_qa 0 · face audit 0 · -14.0 LUFS / TP -1.3 · ביקורת 4.2 (הנמוך: <dimension>)
פערים פתוחים / סיכוני רישוי: <list or none>
תהליך וכלים: <short>
שאלה אחת: <close the round: approve for final render, or more notes?>
```
```
Round 3 - <name>_v3: <path or Studio link>
Your notes:
1. ok "<the user's words>" - cause: <cause>. Now: <change> (0:24.6-0:25.4 / f738-762)
3. x "<...>" - open gap: <why> + alternative
Ledger fidelity: ALL rows, not only this round's: L01 ok · L02 ok (f30-60) · ... 
QA: frame_qa 0 · caption_qa 0 · face audit 0 · -14.0 LUFS / TP -1.3 · critic 4.2 (lowest: <dimension>)
Open gaps / licence risks: ... | Process and tools used: ... | One closing question: ...
```
Rules:
- Numbered by the USER's notes, in their order; every note appears, fixed or as a gap.
- Show the FULL ledger status, not just this round's rows. An x is fixed before presenting or listed as a numbered gap with a reason, never silently.
- The QA line quotes numbers measured on the NEW file (check the file is newer than the last patch). Unmeasured items are written as `not run`, never omitted.
- An honest score with the lowest dimension; never present below the bar without the gaps listed (release bar: average >= 4.0, no dimension < 3; judge variance about +-1.5 of 30 was observed, so state it).
- Ends with one question. Send partial results at once if a fix is ready before the rest.

## 4. After the round
Add `PRESENTED <date>` to the log; record one lesson per note (grep for an existing line first and raise its count); record in the retro how many full renders the round used (target 1) and how long (target <= 45 min). A note that repeats across rounds is a global rule: promote it.

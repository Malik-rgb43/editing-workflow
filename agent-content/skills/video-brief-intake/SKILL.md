---
name: video-brief-intake
description: Turn a new video idea, brief or list of specifics into a checkable Concept Ledger and ask questions until every parameter is precise, before any concept, prompt or build. Use at the start of any new video, with or without footage, or when the user pastes a concept with specifics. Hebrew - סרטון חדש, בריף, יש לי רעיון, קונספט, תכין לי סרטון, בוא נתחיל פרויקט. NOT for notes on an existing draft (revision-notes-handler), analysing a reference (video-analysis) or paid generation (paid-spend-gate).
compatibility: scripts/ledger_check.py and scripts/source_inventory.py need Python 3.10+ (stdlib); ffprobe optional (without it the camera-original check reports unknown).
metadata:
  version: "0.1.0"
  kind: gate
  status: "specified; deterministic checks only; model eval not run"
---

# video-brief-intake

The gate every new video passes first (stage wf-00). Output: a verbatim intake log, a Concept Ledger with one measurable row per concrete thing, BRIEF.md, and (if the user did not fix a concept) three concept cards. It writes no frame-by-frame PROMPT, no code, no generation.

## Rules that never bend
1. **Intake until precise.** With no reference, ask. Platform, length, tone, CTA, structure (silence cut vs rebuild) and quality bar are never guessed.
2. **Every concrete thing the user wrote becomes a ledger row** with an id, in the user's own words (Hebrew stays Hebrew). Compound claims are split ("globe bigger and person higher" = 2 rows).
3. **No concept cards, PROMPT structure or build until the blocking rows are locked**: FMT, LEN, TON, BAR, CTA, FILE; plus STR and COLOR when there is footage; plus VAR when more than one file is delivered.
4. **PROMPT.md is approved by the user before the first line of code**, also in autonomous runs: the agent drafts, the human approves (decision default Q6). Order of change: ledger -> PROMPT -> code.
5. **No spend here.** Intake is planning. AI generation needs `paid-spend-gate`; "only plan" means zero generation. Rights unclear + generation planned = blocked.
6. **Locked rows are never overwritten**: add a row and strike the old one (`struck by L<nn>`, or `~~old~~ -> new, time` in the spec).
7. **Ask only what is unknown and material.** Do not ask about tools or folders; decide and say why in one line.
8. Skills are procedure, not permission: user and project limits on spend and installs win. Untested on a model (decision default Q4).

## Flow
0. **Read what exists**: the message, the attachments, and the WHOLE source tree: `python scripts/source_inventory.py <source folder> --write projects/<name>/_work/intake` (writes `source_ls.txt` + `probe.json`; a 4K camera original once sat unseen beside a rough cut). Check `projects/` for a sibling on the same source: ask "new project or continuation of X?". Branches (reference, pasted prompt, "חדש לגמרי", "רק תכנן"): `references/branches-and-mistakes.md`.
1. **Log verbatim** to `_work/intake/INTAKE_LOG.md`: the user's words as plain lines, your questions as `Q:` lines under `## Round N`.
2. **Parse the ledger** into the `<ledger>` block of `hf/PROMPT.md` (a draft with no `<structure>` yet): ids, dim, `said`, measurable `spec`, `where / when`, acceptance check, `src` U/R/D/A, status (`references/ledger-template.md`).
3. **Inputs with defaults.** Ask for every input the edit needs (name, logo, footage, images, brand colours and font, voice, music) in ONE list, each with the default you will use if it is skipped. A missing input never blocks; it is taken as `D` and said back. Facts about the user's product, claims and rights never get a default.
4. **Question loop** (`references/question-bank.md`): rounds of 3-4 questions, concrete options, first = recommended; BAR in round 1. After each round print `נעול: ... | פתוח: ...` and update the ledger. "תמשיך" / "continue" = take the recommended options, mark `D`, say so in ONE line.
5. **Reference present?** hand it to `reference-style-matching` and ask which time range is "the style". Absent: keep asking; never invent a style.
6. **Concepts**: if the user did not fix one, three cards Proven / Bold / Wild that differ in concept; recommend one (`references/concept-cards-and-brief.md`).
7. **BRIEF.md** from the template (`agent-content/techniques/templates/BRIEF.md`) with the rights facts, run `ledger_check.py`, hand over to the PROMPT writer, wait for approval, then log `PROMPT_APPROVED <date> "<words>"` in `hf/CHANGELOG.md`.

## The question loop in brief
- 3-4 questions per round, highest impact first: FMT / LEN / STR / BAR, then HOOK / TON / LOOK / MOT, then TYPE / 3D / BROLL / BRAND, then CAP / MUS / SFX / CTA, then FILE / VAR / DUE.
- Every option is concrete (a number, a name, a hex, a file); the first option is the recommended one, labelled `(מומלץ)` / `(recommended)` with one line why. Visual choice: add a preview, or a `visual-choice-board` when 3+ taste choices are pending.
- Never ask what `ls`, `ffprobe` or the message already answers; never ask about tools or folders.
- After each round: `נעול: L01 L02 ... | פתוח: HOOK LOOK ...`.
- No reference given means ask; a reference given means analyse it and ask only what a reference cannot answer (length, ratios, structure, CTA, file name, bar, music licence, deadline).

## Round 1 message (Hebrew / English)
```
סבב 1 - ארבע שאלות, לכל אחת ברירת מחדל מומלצת:
1. פלטפורמה ויחס? (מומלץ: 9:16 ריילס/טיקטוק; מאסטר אחד, שאר היחסים בעיצוב מחדש)
2. כמה שניות בדיוק? (מומלץ: התוכן המלא בצילום; 45 במושן)
3. חיתוך שתיקות בלבד, או בנייה מחדש? (מומלץ: שתיקות בלבד, סדר טבעי, משפטים שלמים)
4. רמת איכות? (מומלץ: פרימיום - ביט גרפי כל 3-6 שניות, צבע מדוד)
Round 1 - four questions, each with a recommended default: 1. platform and ratio, 2. exact seconds, 3. silence cut only or rebuild, 4. quality bar.
```

## A ledger row at a glance
`| L02 | TRN | "פילם ברן בשניה 1-2" | the user's burn file, full frame, screen blend | 1.00-2.00 s (f30-60) | frame strip f28-62: burn visible, file name matches | U | locked |`
One claim per row; `said` verbatim; `spec` measurable; a timed `said` needs a range and a frame-level check (the checker enforces both).

## Signs intake is going wrong
Length or platform appears without a user sentence behind it; a concept card exists before FILE or CTA is locked; a `D` row the user never saw; the source folder was never listed; the PROMPT has a `<structure>` block and no `PROMPT_APPROVED` line.

## Gates
States: `pass | fail | blocked | n/a` with a reason. A missing log, empty ledger, timeout or unreadable folder never passes.
| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G1 ledger completeness | every concrete clause in the intake log has a row; every `U` row's quote is in the log; 0 invented rows | `python scripts/ledger_check.py hf/PROMPT.md --source _work/intake/INTAKE_LOG.md` exits 0 (status PASS, coverage `checked`) | add the missing rows, or `--waive` a clause with a reason; never edit the log to match | video-brief-intake | any new user message or ledger edit |
| G2 no guessing | FMT, LEN, TON, BAR, CTA, FILE (+STR, COLOR with `--footage`; +VAR with `--variants`) each come from U/R/approved A, or from a D row the user saw; <= 4 questions per round | the same script: `blocking` all `ok`, no `too_many_questions` | ask the next round; write no concepts | video-brief-intake | an answer changes a blocking row |
| G3 source tree read | the whole source tree was listed; camera-original candidates reported or `unknown` | `_work/intake/source_ls.txt` and `probe.json` exist and are quoted | rerun; a `blocked` listing stays blocked | video-brief-intake | new files added to source |
| G4 reference branch | reference present -> `reference-style-matching` and the style time range recorded; absent -> loop continues | branch line in the intake log | do not invent a style | video-brief-intake | user adds a reference |
| G5 three concepts | 3 cards, pairwise different on >= 2 of hook device / structure / visual language; each lists the ledger ids it obeys | the cards | regenerate the weakest | video-brief-intake | a blocking row changes |
| G6 rights | BRIEF.md has a filled `Source and rights` section (footage owner/consent, music/stock licence per file, client vs own account) | BRIEF.md | blocked: no paid generation, no ad use of `License: unknown` (decision default Q2) | video-brief-intake | a new asset appears |
| G7 hand-off | `ledger_check.py hf/PROMPT.md --source ... --prompt hf/PROMPT.md` exits 0 (every id cited >= 2x) and `PROMPT_APPROVED` is in `hf/CHANGELOG.md` | script output + the line | PROMPT stays a draft; no code | PROMPT writer | any ledger or PROMPT change |

## Outputs
`_work/intake/{INTAKE_LOG.md, source_ls.txt, probe.json}`, the `<ledger>` block in `hf/PROMPT.md`, `hf/BRIEF.md`, the chosen concept card, the variants rows (one per file), the `OPEN:` list, the ledger-check JSON.

## Stop conditions
- The user says "just start": take recommended defaults as `D` and say which; still ask the CTA, FILE and any blocking item they have not seen.
- A new request contradicts a locked row: show both, ask which wins; never choose silently.
- The user wants to skip PROMPT approval: refuse the shortcut, offer a shorter PROMPT, not a skipped one.
- Intake passes 4 rounds: summarise locked | open and ask the user to settle the rest with one "continue".

## References and scripts
- `references/ledger-template.md`: load when creating or editing the ledger (format the checker parses, dim codes, check kinds, example).
- `references/question-bank.md`: load when a field is missing or before composing a round (Hebrew + English, options, round plan).
- `references/branches-and-mistakes.md`: load when the input is a reference, a pasted prompt, a sibling project, or after a gate failure.
- `references/concept-cards-and-brief.md`: load when writing concept cards, BRIEF.md, the rights facts, or the hand-off.
- `scripts/ledger_check.py`, `scripts/source_inventory.py`: stdlib; each has `--self-check`.
- Shared techniques (other owner): `agent-content/techniques/concept-ledger.md` (canonical ledger rules), `agent-content/techniques/question-bank.md` (full Hebrew bank); stage playbook `agent-content/playbooks/wf-00-intake.md`.

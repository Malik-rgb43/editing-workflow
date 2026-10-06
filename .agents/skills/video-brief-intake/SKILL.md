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

## Start: connections
If `<project>/_work/connections.json` from this session exists (written by the router or `pro-video-editor`), read it; otherwise run `python tools/connections.py -o <project>/_work/connections.json` (about 1 s, presence only) and read your own tool list (claude.ai connectors appear only there). For this skill: stock (Pexels), real icons and logos (Iconify), generation (Higgsfield, ElevenLabs) - what is connected decides what the brief may propose; ask only about a missing one that matters. Before Round 0 there is no project yet: run it without `-o` and write the file right after `new_project.py`. Say use / not needed / fallback in one line, then continue. A missing connection never stops the work; anything paid goes through `paid-spend-gate`.

## Rules that never bend
1. **Intake until precise.** Platform, length, tone, CTA, structure (silence cut vs rebuild) and quality bar are never guessed: they come from the user, a reference, or your decision under full control, said back as `D`.
2. **Every concrete thing the user wrote becomes a ledger row** with an id, in the user's own words (Hebrew stays Hebrew). Compound claims are split ("globe bigger and person higher" = 2 rows).
3. **No concept cards, PROMPT structure or build until the blocking rows are locked**: FMT, LEN, TON, BAR, CTA, CAP; plus STR and COLOR when there is footage; plus VAR when more than one file is delivered. FILE is not asked: it is a `D` row with a default name (`<name>_<ratio>.mp4`), said back; the user's own name wins.
4. **PROMPT.md is approved by the user before the first line of code**, also in autonomous runs: the agent drafts, the human approves (decision default Q6). Order of change: ledger -> PROMPT -> code.
5. **No spend here.** Intake is planning. AI generation needs `paid-spend-gate`; "only plan" means zero generation. Rights unclear + generation planned = blocked.
6. **Locked rows are never overwritten**: add a row and strike the old one (`struck by L<nn>`, or `~~old~~ -> new, time` in the spec).
7. **Ask only what is unknown and material.** Never ask about tools; decide and say why in one line. Folders: ask "new project or continuation of X?" only when an existing project with a `hf/PROMPT.md` could match this request (same source or same title); otherwise create the project with `new_project.py` without asking.
8. **Full control decides taste, never facts.** "You decide" covers format, length, tone, structure, look, music, the CTA wording and the file name (each a `D` row, said back in ONE line). The offer, prices, names, dates, claims and contact details (the CTA's URL, phone or price) are always asked, in one bundled question.
9. Skills are procedure, not permission: user and project limits on spend and installs win. Untested on a model (decision default Q4).

## Flow
0. **Read what exists**: the message, the attachments, `ls` of the folder the user gave. Check `projects/` for a project with a `hf/PROMPT.md` that could match (rule 7). Branches (reference, pasted prompt, "חדש לגמרי", "רק תכנן"): `references/branches-and-mistakes.md`.
1. **Round 0 (always first, ONE message):** purpose (one line) · who decides (full control / I define) · speech and caption language (which language / a translation / no captions; never assume Hebrew) · consent of the people on camera, if unclear · missing facts (rule 8). The answers become the first rows: CAP (caption language, or none), the speech language, CONSENT, the facts.
2. **Create the project** right after Round 0: `python tools/new_project.py "<title>" --copy <files> --init-hyperframes`. Then the source inventory: `python scripts/source_inventory.py <the user's source folder> --write <project>/_work/intake` - the whole folder, not only the copied files (a 4K camera original once sat unseen beside a rough cut). It writes `source_ls.txt` + `probe.json`, the inventory `pro-video-editor` Step 1 reads instead of listing again. A camera-original candidate is copied in once the user confirms it. `pro-video-editor` then starts `tools/prep.py <project> --language <code>` in the background.
3. **Log verbatim** to `<project>/_work/intake/INTAKE_LOG.md`, from Round 0 on: the user's words as plain lines, your questions as `Q:` lines under `## Round N`.
4. **Parse the ledger** into the `<ledger>` block of `hf/PROMPT.md` (a draft with no `<structure>` yet): ids, dim, `said`, measurable `spec`, `where / when`, acceptance check, `src` U/R/D/A, status (`references/ledger-template.md`).
5. **Inputs with defaults.** Ask for every input the edit needs (name, logo, footage, images, brand colours and font, voice, music) in ONE list, each with the default you will use if it is skipped. The list goes in the same message as Round 0, so the user answers once. A missing input never blocks; it is taken as `D` and said back. Facts never get a default (rule 8).
6. **Question loop** (`references/question-bank.md`), Round 1 on: rounds of 3-4 questions, concrete options, first = recommended; BAR in round 1. After each round print `נעול: ... | פתוח: ...` and update the ledger. "תמשיך" / "continue" = take the recommended options, mark `D`, say so in ONE line. Full control: skip the taste rounds, decide, say the decisions in one line.
7. **Reference present?** Hand it to `reference-style-matching` first and ask which time range is "the style". Its three options (Faithful / Elevated / Twist) REPLACE the concept cards of step 8: one set of three, never two. Absent: keep asking; never invent a style.
8. **Concepts** (no reference, no fixed concept): three cards Proven / Bold / Wild that differ in concept; recommend one (`references/concept-cards-and-brief.md`). Full control: pick one yourself, say which and why.
9. **BRIEF.md** from the template (`agent-content/techniques/templates/BRIEF.md`) with the rights facts, run `ledger_check.py`, then hand over to `pro-video-editor` (its Step 3 writes PROMPT.md from the ledger and the chosen concept). After the user's yes, log `PROMPT_APPROVED <date> "<the user's words>"` in `hf/CHANGELOG.md`.

## The question loop in brief
- 3-4 questions per round, highest impact first: FMT / LEN / STR / BAR, then HOOK / TON / LOOK / MOT, then TYPE / 3D / BROLL / BRAND, then MUS / SFX / CTA, then VAR / DUE. CAP is settled in Round 0; FILE is a default.
- Every option is concrete (a number, a name, a hex, a file); the first option is the recommended one, labelled `(מומלץ)` / `(recommended)` with one line why. A visual choice with 2+ options goes on a `visual-choice-board`, opened in the browser pane, not into chat.
- Never ask what `ls`, `ffprobe` or the message already answers; never ask about tools.
- After each round: `נעול: L01 L02 ... | פתוח: HOOK LOOK ...`.
- No reference given means ask; a reference given means analyse it and ask only what a reference cannot answer (length, ratios, structure, CTA facts, bar, music licence, deadline).

## Round 0 and Round 1 messages (Hebrew / English)
```
סבב 0 - לפני הכול:
1. בשביל מה הסרטון? (משפט אחד)
2. מי מחליט על הקונספט? (מומלץ: שליטה מלאה - אני מחליט ומראה לך בטיוטה) / אני מגדיר
3. באיזו שפה מדברים בסרטון, ואילו כתוביות? (שפת הדיבור / תרגום ל-___ / בלי כתוביות)
4. [רק אם חסר] האנשים שמצולמים הסכימו? מה הקישור / הטלפון / המחיר לסוף?
Round 0 - before anything: 1. what the video is for, 2. who decides (full control / I define), 3. speech language and captions (same language / a translation to ___ / none), 4. [only if missing] consent of the people on camera; the facts for the end (link, phone, price).

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
Length or platform appears without a user sentence or a said-back `D` behind it; a caption language nobody chose (Hebrew assumed); a concept card exists before CTA or CAP is locked; a `D` row the user never saw; a price or phone number decided under full control; the source folder was never listed; the PROMPT has a `<structure>` block and no `PROMPT_APPROVED` line.

## Gates
States: `pass | fail | blocked | n/a` with a reason. A missing log, empty ledger, timeout or unreadable folder never passes.
| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G1 ledger completeness | every concrete clause in the intake log has a row; every `U` row's quote is in the log; 0 invented rows | `python scripts/ledger_check.py hf/PROMPT.md --source _work/intake/INTAKE_LOG.md` exits 0 (status PASS, coverage `checked`) | add the missing rows, or `--waive` a clause with a reason; never edit the log to match | video-brief-intake | any new user message or ledger edit |
| G2 no guessing | FMT, LEN, TON, BAR, CTA, CAP (+STR, COLOR with `--footage`; +VAR with `--variants`) each come from U/R/approved A, or from a D row the user saw; a FILE row exists (a said-back D is enough); <= 4 questions per round | the same script: `blocking` all `ok`, no `too_many_questions` | ask the next round; write no concepts | video-brief-intake | an answer changes a blocking row |
| G3 source tree read | the whole source folder was listed; camera-original candidates reported or `unknown` | `<project>/_work/intake/source_ls.txt` and `probe.json` exist and are quoted | rerun; a `blocked` listing stays blocked | video-brief-intake | new files added to source |
| G4 reference branch | reference present -> `reference-style-matching`, the style time range recorded, its three options used instead of concept cards; absent -> loop continues | branch line in the intake log | do not invent a style | video-brief-intake | user adds a reference |
| G5 three concepts | no reference: 3 cards, pairwise different on >= 2 of hook device / structure / visual language; each lists the ledger ids it obeys | the cards | regenerate the weakest | video-brief-intake | a blocking row changes |
| G6 rights | BRIEF.md has a filled `Source and rights` section (footage owner/consent, music/stock licence per file, client vs own account) | BRIEF.md | blocked: no paid generation, no ad use of `License: unknown` (decision default Q2) | video-brief-intake | a new asset appears |
| G7 hand-off | `ledger_check.py hf/PROMPT.md --source ... --prompt hf/PROMPT.md` exits 0 (every id cited >= 2x) and `PROMPT_APPROVED` is in `hf/CHANGELOG.md` | script output + the line | PROMPT stays a draft; no code | `pro-video-editor` (Step 3) | any ledger or PROMPT change |

## Outputs
`<project>/_work/intake/{INTAKE_LOG.md, source_ls.txt, probe.json}` (the source inventory `pro-video-editor` Step 1 reads), the `<ledger>` block in `hf/PROMPT.md`, `hf/BRIEF.md`, the chosen concept card (or the chosen `reference-style-matching` option), the variants rows (one per file), the `OPEN:` list, the ledger-check JSON.

## Stop conditions
- The user says "just start": take recommended defaults as `D` (the CTA wording and the file name included) and say which in one line; still ask Round 0 if it is unanswered, and any missing fact (a CTA's URL, phone or price).
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

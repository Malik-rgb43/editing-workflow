# Concept Ledger: template, rules, worked example

Load when building or editing the ledger. Canonical rules live in the shared technique `agent-content/techniques/concept-ledger.md` (the ledger sits in the `<ledger>` block of `hf/PROMPT.md`; there is no separate ledger file); this page is the intake-side working template and the exact format `scripts/ledger_check.py` parses.

## 1. Files written by intake
| File | Content | Rule |
|---|---|---|
| `_work/intake/INTAKE_LOG.md` | every user message and answer, verbatim, in order, plus your questions as `Q:` lines under `## Round N` | append-only; the only source a `said` quote may come from |
| `_work/intake/source_ls.txt`, `probe.json` | output of `scripts/source_inventory.py ... --write` | evidence of the source-tree read |
| `hf/PROMPT.md` | the `<ledger>` block (the frame-by-frame blocks are added later by the PROMPT writer) | one source of truth: ledger first, then structure, then code |
| `hf/BRIEF.md` | the BRIEF template, filled from the ledger | see `concept-cards-and-brief.md` |
(A standalone ledger file is accepted by the checker for scratch work; do not keep two copies in the project.)

## 2. Table format (exact header; the checker keys on these names)
```
<ledger>
| ID | dim | said (verbatim) | spec (measurable) | where / when | acceptance check | src | status |
|---|---|---|---|---|---|---|---|
</ledger>
```
- **ID**: `L01`, `L02`, ... never reused.
- **dim**: a code from section 4, or `LAY`/`TRN`/`SHOT` for concept specifics.
- **said**: the user's own words in quotes, language untouched; a short English gloss may follow in parentheses. `-` for default or assistant rows.
- **spec**: the measurable translation: seconds, frames, px, hex, dB, file name, count. A vague word ("more dynamic") gets a number the user confirms ("an event every <= 0.7 s, punch-in every 3-4 s"); until confirmed the row is `default`, not `locked`.
- **where / when**: a range (`1.00-2.00 s`, `f30-60`, `12.4-16.0 s`) or `whole`. Any `said` that names a time needs a range here.
- **acceptance check**: how the finished video proves it (section 5). Required for every `locked` or `default` row.
- **src**: `U` the user said it, `R` from a reference's Style DNA, `D` a default taken (shown to the user, or "continue"), `A` assistant proposal.
- **status**: `locked`, `default`, `proposed` (assistant idea not yet approved), or `struck by L<nn>`.

## 3. Rules
1. One line = one checkable claim. "The globe bigger and the person higher" is two rows.
2. Verbatim in `said`; the measurable version in `spec`. Never put your paraphrase in `said`.
3. A locked row is never overwritten. A change adds a row and strikes the old one: status `struck by L<nn>`, or in place `~~30 s~~ -> 45 s, 09:05` in the spec (both are accepted by the checker).
4. `A` rows stay `proposed` until the user approves them; only then `locked`.
5. A default is a choice only if the user saw it: `D` rows need the "continue" / "defaults taken" line in the intake log.
6. Never invent a row to look complete: every `U` row's `said` must appear in the intake log.

## 4. Dimension codes
| Code | Meaning | Blocking at the intake exit? |
|---|---|---|
| FMT | platform and ratio(s), which is the master | yes |
| LEN | exact seconds (never a multiplier) | yes |
| TON | energy / register | yes |
| BAR | quality bar (asked in round 1) | yes |
| CTA | what the viewer does, the exact line | yes |
| FILE | the exact final file name (the user's name wins) | yes |
| STR | footage: silence cut only vs restructure | yes with footage (`--footage`) |
| COLOR | person footage: camera original present, colour correction needed | yes with footage (`--footage`) |
| VAR | variant matrix: ratios, hooks, platforms, "no music", "no captions" | yes when more than one file (`--variants`) |
| HOOK, LOOK, TYPE, MOT, 3D, BROLL, CAP, MUS, SFX, VO, DUE, BRAND | the rest of the bank | asked; may take a shown default |
| LAY, TRN, SHOT | free lines for concept specifics | n/a |
| REF, RIGHTS, CONSENT, AIDISC, LOUD | reference range, licences, consent, AI-disclosure plan, loudness target (shared technique) | when applicable |

## 5. Acceptance-check kinds (pick the cheapest that proves the claim)
| Claim | Check |
|---|---|
| length, fps, size | `ffprobe` on the final file |
| position / size of an element | snapshot at time t, bounding box; speaker centring with `face_center` |
| timing / transition | `sheet` strip over the range + `frame_qa` |
| colour | 5x5 median pixel sample against the hex |
| captions | `caption_qa`, caption rail above the limit |
| sound | `hf_mix --report`, loudness measured on the final file |
| text / CTA / file name | grep the HTML, OCR the frame, `ls` the final folder |
`not_run` never counts as ok.

## 6. Worked example (sample content)
```
<ledger>
| ID | dim | said (verbatim) | spec (measurable) | where / when | acceptance check | src | status |
|---|---|---|---|---|---|---|---|
| L01 | LEN | "שהסרטון יהיה 45" (make the video 45) | 45.0 s +-0.1 | whole | ffprobe duration on the final | U | locked |
| L02 | TRN | "פילם ברן בשניה 1-2" (film burn at second 1-2) | the user's burn file, full frame, screen blend, peak after f40 | 1.00-2.00 s (f30-60) | frame strip f28-62: burn visible, file name matches | U | locked |
| L03 | LAY | "הגלובוס יותר גדול" (the globe bigger) | globe width 620 -> 780 px | 12.4-16.0 s | snapshot at 14.0 s, bbox width | U | locked |
| L04 | LAY | "הבן אדם יותר למעלה" (the person higher) | head top y 420 -> 300 | 12.4-16.0 s | snapshot at 14.0 s, face box top | U | locked |
| L05 | CTA | - | end card 2.5 s with the line from the brief | 42.5-45.0 s | OCR the end card | D | default |
</ledger>
```
Check it: `python scripts/ledger_check.py hf/PROMPT.md --source _work/intake/INTAKE_LOG.md` (add `--footage` and `--variants` when they apply). Statuses: PASS (exit 0) | FAIL 1 | INSUFFICIENT_EVIDENCE 2 | NEEDS_REVIEW 3 (concrete source clauses with no row: add rows or waive with a reason). `--structure-only` checks format only and is never a G1 pass.

## 7. Hand-off to the PROMPT writer
`<ledger>` stays first in `PROMPT.md`; every id is cited again in `<structure>` where it is realised; `ledger_check.py hf/PROMPT.md --source ... --prompt hf/PROMPT.md` requires every id at least twice. The user approves PROMPT.md in chat; the agent then appends `PROMPT_APPROVED <date> "<the user's words>"` to `hf/CHANGELOG.md`. No code before that line exists. Each later user note becomes a new row (see `revision-round`).

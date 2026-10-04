# Technique: the Concept Ledger

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from distilled/02 workflow-end-to-end §2 (the author's `video-concept-intake` method) and distilled/01 rules-and-gates A1–A14, B8. The checker at the end was run by the author on the worked example in [frame-spec-prompt.md](frame-spec-prompt.md) (it found five uncited ids and two missing blocking dimensions in the first draft of that example — which is why it is here).
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[IDEA]` · `[CONFLICT]`.
> Not to be confused with the **timing ledger** (the `ledger` tool, see [timing-ledger.md](timing-ledger.md)): this is the *concept* ledger.

## 0. Why it exists

The author's rule: "if I write a concept and specify things, it should come out exactly; if there is no reference video, ask questions until everything is precise." `[RULE-owner]` (owner, 2026-09-29; src: distilled/01 rules-and-gates A1). The ledger turns every concrete thing a person said into **one checkable line** that survives all the way to the presentation message, where each line is ticked with evidence. Measured cost of not having it: a 30 s film grew to 51 s then 45 s (~35 min of re-cutting); a "premium" bar asked after spec approval forced a ~40 min rebuild; "film burn at 1–2 s" was verified by the author, not by the agent. (src: distilled/02 workflow §2.5) `[PROVEN-internal]`

The ledger lives **inside `hf/PROMPT.md`** as a `<ledger>` block above the six frame blocks. There is no separate LEDGER file; `hf/CONCEPT.md` holds the concept options and the chosen direction, `hf/BRIEF.md` is five lines. `[RULE-owner]` (the author retired the second spec file)

## 1. Format

```markdown
<ledger>
| ID  | dim | said (verbatim)                         | spec (measurable)                         | where / when | acceptance check                       | src | status |
|-----|-----|------------------------------------------|-------------------------------------------|--------------|----------------------------------------|-----|--------|
| L01 | LEN | "שהסרטון יהיה 45"                        | 45.0 s ±0.1 = 1350 f @30                  | whole        | ffprobe duration on the final          | U   | locked |
| L02 | TRN | "פילם ברן בשניה 1-2"                     | the supplied burn file, f30–60, screen blend, peak on a whole frame | f30–60 | frame strip f28–62: peak ≥ f40; file = the supplied one | U | locked |
| L03 | LAY | "הגלובוס יותר גדול"                      | globe 620 → 780 px wide                   | 12.4–16.0 s  | snapshot at 14.0 s, bbox width         | U   | locked |
| L04 | LAY | "והבן אדם יותר למעלה"                    | head top y 420 → 300                      | 12.4–16.0 s  | snapshot at 14.0 s, face-box top       | U   | locked |
| L05 | CTA | —                                        | end card 2.5 s with the line from the brief | 42.5–45 s  | OCR end card; key text y ≤ 1248        | D   | default |
</ledger>
```

(Example rows are illustrative; the Hebrew in the `said` column is the knowledge — keep the person's own words, never a translation.)

### 1.1 Rules

1. **One line = one checkable claim.** Compound sentences split: "the globe bigger and the person higher" = two rows (L03, L04).
2. **`said` keeps the person's words verbatim, in the original language.** `spec` is the measurable translation: px, seconds, frames, hex, dB, a file name.
3. **Vague words get a measurable proposal the person confirms** ("more dynamic" → "an event every ≤ 0.7 s, a punch-in every 3–4 s"). Until confirmed the row is `default`, not `locked`.
4. **`src` codes:** **U** the person said it · **R** from a reference's Style DNA · **D** a default taken · **A** an assistant proposal the person approved.
5. **A locked row is never overwritten.** A change adds a new row and strikes the old one with the time: `~~30 s~~ → 45 s, 09:05`. `[RULE-owner]`
6. **Every row has an acceptance check** that a tool, a command or a human look can run on the **final file** (or on a named snapshot/frame). "Looks good" is not a check.
7. **Every id is cited in `<structure>`** (or `<direction>`/`<build>` for global rows) where it is realised. A textual count (`grep -o "L[0-9][0-9]" hf/PROMPT.md | sort | uniq -c`, each id ≥ 2) is the *minimum*; it is not a schema check `[CONFLICT-light]`: a mention is not a realisation, so wf-06 still ticks each row against evidence.
8. **"תמשיך" (continue) = take every recommended default, mark them `D`, say so in ONE line** (for example: `לקחתי ברירות מחדל: 9:16, 45 ש׳, חיתוך שתיקות בלבד, Rubik, מוזיקה מהספרייה, CTA "…"`). That counts as the person's choice.
9. After each question round show one line: `נעול: … | פתוח: …`.

### 1.2 Dimension codes

| Code | Meaning | Blocking before PROMPT (never guessed)? | Asked in |
|---|---|---|---|
| FMT | platform + aspect ratios, which is the master | **yes** | round 1 |
| LEN | exact length in seconds (never "a multiplier") | **yes** | round 1 |
| STR | structure: silence-cut only vs rebuild (footage) | **yes for footage** | round 1 |
| TON | energy/tone | **yes** | round 2 |
| HOOK | what is said/seen at 0–3 s | recommended | round 2 |
| BAR | quality level (the author's: "a premium edit worth ₪500–700", per video up to one minute — a stated target, **not a measured market rate**) | **yes — round 1** | round 1 |
| CTA | what the viewer does at the end, the exact line | **yes** | round 4 |
| LOOK | palette / grade | recommended | round 3 |
| TYPE | caption/title fonts | recommended | round 3 |
| MOT | motion language | recommended (motion) | round 3 |
| 3D | which beats, which route | recommended | round 3 |
| BROLL | kind of B-roll | recommended | round 3 |
| CAP | captions on/off, style | recommended | round 4 |
| MUS · SFX · VO | music, effects, voice-over + pronunciation lexicon | recommended | round 4 |
| FILE | final file name (the person's exact name beats naming defaults) | **yes** | round 5 |
| DUE | deadline | optional | round 5 |
| VAR | variants (hooks, platforms, lengths, "no music", "no captions") | **yes if more than one file** | round 5 |
| BRAND | logo, colours, fonts, pronunciation — from files the person supplies; never invented | when a brand exists | round 3 |
| COLOR | footage of a person: is there a camera original? does colour need correcting? (check the folder yourself first) | **yes for footage** | round 1 |
| LAY · TRN · SHOT | free lines from the concept ("the globe bigger", "film burn at 1–2 s") | — | parsed at step 1 |
| REF | which reference, which time range is "the style" | when a reference exists | wf-01 |
| RIGHTS · CONSENT · AIDISC | licences, consent to use a person's footage/voice, AI-disclosure plan | when applicable | wf-00 / wf-04 |

(`LOUD`, `LAY`-style free codes are allowed; the checker below accepts the table above plus `LOUD`.) (src: distilled/02 workflow §2.2, §2.4; the codes RIGHTS/CONSENT/AIDISC/REF/LOUD are additions of this repo `[IDEA]`.)

### 1.3 Per-type minimum dimensions

| Type | Must be locked before wf-03 |
|---|---|
| talking-head | FMT LEN STR BAR TON CTA FILE COLOR (+ VAR if > 1 file) |
| testimonial | FMT LEN BAR CTA FILE CONSENT RIGHTS (+ the claims table exists) |
| ad-promo | FMT LEN BAR TON CTA FILE VAR + the **offer** (a number) + compliance rows; music licence row |
| motion-graphics | FMT LEN BAR TON MOT 3D CAP MUS FILE (+ VO lexicon if VO) |
| ai-generated | FMT LEN BAR TON FILE AIDISC + budget ceiling (💲 gate) + character/environment lock rows |
| podcast-clip | FMT BAR FILE + clip selection table approved (LEN per clip) |

## 2. Acceptance-check kinds (how each row is verified at wf-06)

| Row kind | Check | Evidence written to `hf/QA.md` |
|---|---|---|
| length, fps, size | `ffprobe` on the final file | the ffprobe line |
| position / size | snapshot at t → bounding box from the DOM or the frame; speaker centring with `face_center audit` | snapshot file + box numbers |
| timing / transition | `sheet --range a:b` strip; `frame_qa` | strip file |
| colour | 5×5 median pixel sample vs the hex | sample values |
| captions | `caption_qa --band <top>:1450`; rail bottom ≤ y 1450; look-alike test at final size | envelope + QA.md row |
| sound | `hf_mix --report`; −14 LUFS / TP ≤ −1 on the final (house preset) | report + `hf_deliver` verify |
| text / CTA / file name | grep `index.html`, OCR of the frame, `ls final/` | quoted output |
| rights / consent | the SOURCES.md row / the consent record exists | file path |

State per row: `ok` / `x` (with a reason) / `n/a` (with a reason) / `not_run`. **`not_run` never counts as ok.** An `x` is fixed before presenting or presented as a numbered gap with the reason — never silently.

## 3. Lifecycle

1. wf-00 parses the person's message into rows (`U`), fills defaults (`D`), asks rounds ([question-bank.md](question-bank.md)).
2. wf-01 adds `R` rows from a Style DNA card.
3. wf-02 adds `A` rows for the chosen concept elements.
4. wf-03 freezes the ledger into PROMPT.md and cites every id.
5. wf-05/06 tick rows with evidence.
6. wf-07: **each owner note becomes a new row** (next id, the note's words with the round tag in `said`, a measurable `spec`, an acceptance check), then the structure changes, then the code. "Always/never" or a note repeated in two rounds is a **global rule**: one row whose check covers every occurrence.
7. wf-09 turns repeated rows into lessons.

## 4. Anti-patterns (each cost real hours)

| Mistake | Cost | Instead |
|---|---|---|
| length derived from a multiplier | three corrections, ~35 min | ask for an exact number; for "too fast" propose exact seconds |
| bar asked after the spec was approved | ~40 min rebuild | BAR in round 1 |
| restructure vs silence-cut never asked | five drafts, ~4 h | STR always asked for footage |
| wrong reference segment copied | rework | pin the time range of "the style" |
| a pasted prompt about another topic assumed | ~4 h | one question; the footage wins |
| colour fixed late | shipped grey sky, magenta skin, tinted blacks | COLOR row; fix before building, from the camera original |
| only the rough cut used | a 4K camera original sat unseen | `ls` the whole source tree at step 0 |
| asking what is already known or infrastructure | slows the person | ask only material, creative, unknown items; decide the rest and say why in one line |

(src: distilled/02 workflow §2.5; distilled/01 A3–A10.) `[PROVEN-internal]`

## 5. Reference checker (stdlib only; author-tested)

A minimal structural check for the ledger block of a PROMPT.md. Exit 0 PASS · 1 FAIL · 2 INSUFFICIENT_EVIDENCE (no ledger found) — fail-closed. It is a **reference sketch**: the toolkit's `hf_preflight` may absorb it (TOOLS_SPEC §2 proposes a ledger-id check); until then run it as shown. It checks structure, not truth: a row with a plausible spec and a useless acceptance check still passes.

```python
#!/usr/bin/env python3
"""ledger_check.py <PROMPT.md> — structural check of the <ledger> block."""
import re, sys, collections
DIMS = {"FMT","LEN","STR","TON","HOOK","LOOK","TYPE","MOT","3D","BROLL","CAP","MUS","SFX","VO","CTA","FILE",
        "BAR","DUE","VAR","BRAND","COLOR","LAY","TRN","SHOT","LOUD","REF","RIGHTS","AIDISC","CONSENT"}
SRC, STATUS = {"U","R","D","A"}, {"locked","default"}
BLOCKING = {"FMT","LEN","TON","CTA","BAR"}            # add STR/COLOR for footage in the caller
NUMBER_OPTIONAL = {"CAP","TYPE","TRN","LOOK","BRAND","BROLL","SFX","MUS","VO","MOT","3D","REF",
                   "RIGHTS","AIDISC","CONSENT","VAR","STR","TON","HOOK","CTA"}
text = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"<ledger>(.*?)</ledger>", text, re.S)
if not m: print("INSUFFICIENT_EVIDENCE: no <ledger> block"); sys.exit(2)
rows = []
for line in m.group(1).splitlines():
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(c) == 8 and re.fullmatch(r"L\d{2,3}", c[0]):
        rows.append(dict(zip(("id","dim","said","spec","where","check","src","status"), c)))
if not rows: print("INSUFFICIENT_EVIDENCE: ledger has no rows"); sys.exit(2)
errs, ids = [], collections.Counter(r["id"] for r in rows)
errs += [f"{i}: duplicate id" for i, n in ids.items() if n > 1]
for r in rows:
    struck = r["spec"].startswith("~~")
    if r["dim"] not in DIMS: errs.append(f'{r["id"]}: unknown dim {r["dim"]!r}')
    if r["src"] not in SRC: errs.append(f'{r["id"]}: src must be U/R/D/A')
    if r["status"] not in STATUS and not struck: errs.append(f'{r["id"]}: status must be locked/default')
    if r["check"] in {"", "—", "-"}: errs.append(f'{r["id"]}: no acceptance check')
    if not re.search(r"\d", r["spec"]) and r["dim"] not in NUMBER_OPTIONAL: errs.append(f'{r["id"]}: spec has no number')
body = text[m.end():]
errs += [f"{i}: never cited outside the ledger" for i in ids if not re.search(rf"\b{i}\b", body)]
miss = sorted(BLOCKING - {r["dim"] for r in rows})
if miss: errs.append("blocking dimensions missing: " + ", ".join(miss))
print("FAIL" if errs else "PASS", f"{len(rows)} rows"); [print(" -", e) for e in errs]
sys.exit(1 if errs else 0)
```

Limits: it does not verify that a cited id is *realised*; it does not parse struck rows beyond skipping the status check; the footage-only blocking dimensions (STR, COLOR) must be added by the caller; Hebrew `said` text is never validated.

## 6. Failure modes

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| the author finds a missing detail at review | a concrete statement never became a row | add the row, trace it into structure | parse the message into rows at wf-00 step 2 |
| a locked row was edited in place | no strike-through discipline | restore, add a new row with the time | rule 5 |
| "locked" rows with vague specs | the proposal was never confirmed | mark `default`, ask | rule 3 |
| presentation lists only this round's rows | partial ledger | always list the whole ledger | wf-07 message format |

(src: distilled/02 workflow §2; distilled/01 A1–A14, B8 — read 2026-10-02.)

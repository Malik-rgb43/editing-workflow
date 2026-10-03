# wf-09 — Learn (למידה וסיכום)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §1, distilled/02 workflow-end-to-end §11, distilled/03 §7 (timing ledger), distilled/01 rules-and-gates.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[IDEA]` · `[CONFLICT]` · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | 9 of 9 — **always**, also after a delivery that was abandoned |
| Owner skill | none (a playbook step); uses [timing-ledger.md](../techniques/timing-ledger.md) |
| Artifacts (exact files) | `projects/<name>/_work/RETRO.md` (the project retro), `projects/LESSONS.md` (the workspace-level lessons inbox — one line per lesson), the `ledger summarize` output saved to `_work/timing_summary.txt`, optional promoted rules in the person's own `projects/RULES.md` |
| Exit gate | **G9 — retro written, every note logged as a lesson line (grep first), timing ledger summarised** |
| Target time | **15 min** (owner target) |
| Paid steps | none |

> Path note: the repository tree (REPO_ARCHITECTURE §3) has no lessons folder; `projects/LESSONS.md` and `projects/RULES.md` are this playbook's proposal (outside `agent-content/`, so the student's own lessons never edit the shipped canonical content). The orchestrator may relocate them.

## 1. Purpose

The goal is **fewer rounds every project**: measure drafts, critic rounds, note rounds and hours to a first passing draft; keep what repeats; turn what an owner caught by eye into something a tool can catch next time. `[RULE-owner]` (owner target; his first launch needed 17 drafts, 10 critic rounds and 9 note rounds; the aim is one draft and one note round — a target, not an achievement.)

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| a delivery happened (G8) **or** the project was stopped (record why) | gate log | still run: an abandoned project teaches the most |
| the timing ledger exists | `_work/timing_ledger.jsonl` | write what is known; unknown = `null`, never 0 |

## 3. Steps

| # | Step | Evidence / output |
|---|---|---|
| 1 | **Summarise the timing ledger:** `ledger summarize` → drafts rendered · **full renders per note round (target 1)** · critic rounds · owner-note rounds · hours to a first passing draft · human active vs blocked minutes · queue wait · setup minutes · credits by wallet · retries · accepted seconds. Save the output. | `_work/timing_summary.txt` |
| 2 | **Write the retro** `_work/RETRO.md` from the template below: where the time went; how many drafts / critic rounds / note rounds to approval; **what went into preflight so it does not recur**; what the person's notes were and what changed. | the file |
| 3 | **One lesson line per note and per surprise** in `projects/LESSONS.md`: `- YYYY-MM-DD · <type> · <lesson> · source: <project> · count: N · tag: tool\|global\|taste\|rule`. **grep first** — an existing line gets its **count raised**, not a duplicate. | the diff |
| 4 | **Promote** a lesson with count ≥ 2, or one the person approved, into `projects/RULES.md` (a rule with its evidence: which projects, which numbers) and remove it from the inbox with a pointer. A rule the person later contradicts is **struck through with the date and why**, not deleted (status `retired`). | `RULES.md` |
| 5 | **Anything caught by eye that a tool could catch** → a lesson tagged `tool:` with the check described precisely (a candidate for `hf_preflight` or `frame_qa`; if the student wants it in the toolkit, it goes to the toolkit's maintainers as an issue — never silently into `agent-content/`). | the tagged line |
| 6 | **A note typed into several sessions the same minute** is a **global style rule**: tag `global`; one session owns promotion; **never message another session**. | the tag |
| 7 | **Record the scores:** the rubric result per dimension (six dimensions), the `bands.json` comparison as informational, the final QA envelopes' statuses — in `RETRO.md`. | the table |
| 8 | **Privacy pass before anything leaves the machine** (a shared retro, a bug report, a course question): remove client names, footage descriptions that identify people, transcripts, paths with a user name, keys; the toolkit has **no telemetry** and never uploads a retro. | the checklist |

### 3.1 `RETRO.md` template (synthetic example)

```markdown
---
type: motion-graphics            # one of the six types
project: nimbus_teaser           # synthetic example
date: 2026-10-02
status: delivered                # delivered | stopped
rubric_scores: {meaning_story: 4, caption_language: n/a, composition_brand: 4, motion_edit: 4, audio: 4, integrity_continuity: 5}
rubric_average: 4.2
drafts: 2
critic_rounds: 1
owner_note_rounds: 1
full_renders_per_note_round: [1]
hours_to_first_passing_draft: null     # unknown = null
---
## Brief (3 lines)
12 s 9:16 teaser, no captions, accent only from the reveal frame.
## Key decisions and why
- seam A→B reveal-through (chip→card) because the hero must persist (L09).
## Owner notes → what changed
| round | note | change | ledger row |
| 1 | "the toast feels late" | moved from f155 to f150 | L14 |
## Where the time went
(ledger summary: setup 18 min, build 62 min, full render 10.4 min, human review 11.5 min active)
## What entered preflight so it does not recur
- tool: events-gap check from the PROMPT event list (≤ 21 f).
## Lessons (also in projects/LESSONS.md)
```

## 4. Exit gate G9

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| the ledger was summarised (unknown values are `null`) | `_work/timing_summary.txt` | else `fail` |
| `RETRO.md` exists with counts of drafts, critic rounds, note rounds and **full renders per note round** | the file | else `fail` |
| every note of every round has a lesson line (new, or a raised count) | `LESSONS.md` diff vs `CHANGELOG.md` rounds | else `fail` |
| a privacy pass ran if anything is to be shared | the checklist ticked, or `n/a` (nothing leaves the machine) | else `blocked` |

Gate record → `hf/QA.md` "Gate log".

## 5. Human vs agent

| Human | Agent |
|---|---|
| approves a promotion to a rule; says whether a global note is a style rule; decides what, if anything, is shared | writes the retro and the lesson lines; greps for duplicates; raises counts; proposes promotions; never contacts another session |

## 6. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| duplicate lessons | no grep | merge; add the counts | step 3 |
| a one-off promoted to a rule | no count/approval | demote; keep in the inbox | step 4 |
| the retro blames the tool, not the process | no ledger | read the ledger first | step 1 |
| unknown time written as `0` | missing value coerced | store `null` | timing-ledger rules |
| a shared retro leaks a client | no privacy pass | retract; scrub | step 8 |

## 7. Tool invocations

`ledger summarize` · `benchmark score <video> --type <type>` (informational bands; mind its known defects — numeric preservation, failed gates exit non-zero) · `grep` · `sheet` (final stills) · `session` digests instead of raw transcripts if the host provides them. No uploads.

## 8. Per-type deltas (what to record)

| Type | Record |
|---|---|
| talking-head | cuts/min, median shot, events/min vs the bands; hours to first draft; `face_center`/`motion_qa` hit counts; any join the person caught |
| testimonial | the claims table outcome; opening time-to-result; the number of proof mismatches found |
| ad-promo | offer touches, brand/product time, TP on the final, the licence rows verified, hook variants shipped |
| motion-graphics | events/min by hand count, the clean-smooth rows added by notes, full renders per round |
| ai-generated | generations vs accepted clips, retry count, spend vs approved estimate, clean-window median, any model behaviour that changed (perishable) |
| podcast-clip | clips selected vs shipped, selection scores, switch overrides |

## 9. Time labels

Owner target 15 min. Modelled: none. Measured: none on a student.

(src: distilled/02 workflow §11; distilled/03 §7; distilled/01 — read 2026-10-02.)

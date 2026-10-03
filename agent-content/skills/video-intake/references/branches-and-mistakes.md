# Branches on what arrived, and intake mistakes that cost real hours

Load when the input is not a plain "new video, no reference" (a reference, a pasted prompt, a sibling project, "completely new", "only plan") or when a gate fails. Sources: distilled 02 workflow-end-to-end sections 2.3 and 2.5, 2026-10-01 (owner-project hour counts are the owner's, one machine, not a forecast).

## 1. Step 0: read what exists (before the first question)
1. The message and attachments, quoted into `_work/intake/INTAKE_LOG.md`.
2. The WHOLE source tree: `python scripts/source_inventory.py <source folder> --write projects/<name>/_work/intake` (every file, size, and for video: resolution, bitrate, duration; saves `source_ls.txt` and `probe.json`). A 4K camera original sat unseen beside a 1080p, 2.2 Mbps rough cut once; a first version was built on the rough cut and about an hour was lost. Quote the output in the ledger or intake note. A listing that is empty or unreadable is `blocked`, not "nothing found".
3. `projects/` for a sibling on the same source: ask one line, "new project or continuation of X?". Same source clip is never the same project; never adopt another project's cut or PROMPT.
4. The user's own transitions, logos, fonts, music first (owner's assets before stock).

## 2. Branch table
| Situation | Action |
|---|---|
| Reference video or URL, "בסגנון של", "make it like this" | hand the reference to `reference-style-transfer`; its Style DNA fills `R` rows; ask only what a reference never answers: length, ratios, structure, CTA, file name, bar, music licence, deadline |
| Reference with several looks (before/after, intro vs body) | ask which time range is "the style" before using any analysis |
| Pasted prompt written for another topic | compare its topic with the footage; footage wins; do not assume its length or structure; confirm in one question |
| Same source as an existing project | one line: new project or continuation? never adopt a sibling's PROMPT |
| "חדש לגמרי" / "nothing similar to before" | zero carry-over: only facts and the logo; the previous version's moves go on the project's banned list |
| "רק תכנן" / "only a document" | deliverable is the document (ledger, concepts, PROMPT draft); zero generation, zero credits |
| Only text, no footage, no reference | question loop |
| Vague creative ask | 2-3 short directions as one question round, then the loop |

## 3. Mistakes (symptom -> cost -> prevention)
| Mistake | What happened | Prevention |
|---|---|---|
| Length derived, not asked | 30 s became 51 s then 45 s; three corrections, about 35 min re-cut | LEN is blocking, an exact number; for "too fast" propose exact seconds |
| Quality bar asked after spec approval | rebuild of about 40 min | BAR in round 1 |
| Restructure vs silence-cut never asked | 5 drafts of a restructured cut, about 4 h, then "full length, only silences" | STR always asked for footage |
| Wrong reference segment | copied the before/after look | pin the time range of "the style" |
| Built before the PROMPT | a first version (about 1 h) discarded; one autonomous run needed a reverse-engineered PROMPT | PROMPT approved before code, autonomous runs too (decision default Q6) |
| 3D, pace, screen density arrived as late notes | rounds of notes on the same themes | MOT, 3D, BROLL are ledger lines from round 1 |
| Reference's "no music" copied | the video shipped silent | MUS is asked even when the reference has none |
| Only the rough cut used | camera original unseen | `source_inventory.py` in step 0 |
| Colour fixed late | grey sky, magenta skin shipped | COLOR is a ledger line; correction runs before the build |
| File name not asked | the user's required name was missed | FILE row |
| Concept specifics lost in the build | "film burn at 1-2 s" was checked by the user, not by us | cite every ID in the PROMPT structure and tick every row in QA |
| Asking what is known or is infrastructure | the user answered "whatever you think" five times | ask only material, creative, unknown items |

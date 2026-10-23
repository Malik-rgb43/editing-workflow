---
name: approved-to-client-folder
description: >-
  After a video is approved and delivered, hard-link the final into the user's client folder under the month's `מוכנים` folder with a clear name. Needs the client warehouse turned on with its client folder set. Triggers: approved and delivered, "תשים במוכנים", "תיקיית מוכנים", "שים את המאושרים". NOT for rendering or QA (render-qa-delivery), notes rounds (revision-notes-handler), or anything not an approved, delivered final.
compatibility: >-
  Python 3 standard library only (`os.link`); same drive for a hard link, otherwise a copy. Works only when the warehouse is turned on (`python tools/warehouse_link.py status`) and its client folder is set (`warehouse_link.py library`). Windows folder names in Hebrew (`גלם`, `מוכנים`) are the warehouse's own convention.
metadata:
  version: "0.1.0"
  kind: process
  status: "specified; deterministic checks only; model eval not run"
---

# approved-to-client-folder

The user's rule: after they approve, open a `מוכנים` folder in the project's month folder and put the approved videos there. This is the ONE write the toolkit makes in the user's client folder (the warehouse's `library_root`, see `docs/en/client-warehouse.md`); everything else there stays read-only. Contributed with the warehouse by Gabriel Gelman.

## When
Only after BOTH: the user approved the version (warehouse `status: approved`, or an explicit yes in chat), and the delivery render passed (`final/<file>.mp4` exists and is in `final/manifest.json` with `verify_status: PASS`). A draft (`_work/drafts/...`) never goes there. No warehouse, or no client folder set: say so in one line and stop; `final/` stays the result.

## Where
- The month folder is the folder whose `גלם` holds this project's footage. The warehouse records it in `<project>/review/state.json` -> `library.raw_dir` (for example `<client folder>\<client>\אוקטובר 26\גלם`); its parent is the month folder.
- Target: `<month folder>\מוכנים` (create it if missing). If `library.raw_dir` is missing, ask the user which folder; never guess a client or a month.

## How
1. Hard link, not a copy (same file, no extra disk space; works when the client folder and `final/` are on the same drive): `os.link(final_file, target)`. A different drive: copy, and say so.
2. Name: `<short client> <month> - סרטון <N> <short description> <aspect>.mp4`, for example `Acme אוקטובר 26 - סרטון 1 תדמית 9x16.mp4`. N follows the project's own video numbering (V1/V2/V3 in PROMPT.md), not the warehouse version id.
3. A newer approved version of the same video: link the new one under the same name only after the user says the old one may go; otherwise add ` v2`, ` v3` to the name. Never delete or overwrite anything there yourself.
4. Verify: same size and same file id (`os.stat` `st_ino` / `st_dev`) as the `final/` file; list the folder.
5. Tell the user in one or two lines: the folder path, the file names, and which final each one is.

## Never
- Never move, rename or delete the user's existing files (old versions, footage, the warehouse's own links in `<client>\מוכנים`): point them out and let the user do it.
- Never put a draft, a test render or an unapproved version there.

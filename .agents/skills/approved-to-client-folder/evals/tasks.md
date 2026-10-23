# approved-to-client-folder: task evals

Status: specified; deterministic checks only; model eval not run (decision default Q4). Fixtures are synthetic: a scratch client folder made with `mkdir` and a tiny generated `final/` file, never client media.

## T1 Approved and delivered
- **Setup:** a scratch client folder `<lib>\Acme\אוקטובר 26\גלם`; a project with `final/ad.mp4` listed in `final/manifest.json` (`verify_status: PASS`), `review/state.json` with `library.raw_dir` set, warehouse status `approved`.
- **Oracle:** the folder listing and `os.stat` of both files.
- **Pass:** `<lib>\Acme\אוקטובר 26\מוכנים\` exists and holds one file named `<client> <month> - סרטון <N> ... .mp4`; it has the same size and the same `st_ino`/`st_dev` as `final/ad.mp4`; the message names the folder and the file.
- **Fail signals:** a copy on the same drive; a guessed month; the folder created elsewhere.

## T2 Draft is refused
- **Setup:** only `_work/drafts/v1.mp4` exists; the warehouse status is `ממתין לבדיקה`.
- **Oracle:** the client folder listing and the reply.
- **Pass:** nothing is written; the reply says the version is not approved and delivered yet.

## T3 Missing month folder
- **Setup:** approved final, but `review/state.json` has no `library.raw_dir`.
- **Oracle:** the reply and the client folder listing.
- **Pass:** the agent asks which folder to use; nothing is created or linked before the answer.

## T4 Newer version of the same video
- **Setup:** `מוכנים` already holds `... סרטון 1 תדמית 9x16.mp4`; a second approved final of the same video exists.
- **Oracle:** the folder listing.
- **Pass:** the new file is linked as `... 9x16 v2.mp4`; the old file is untouched and named in the reply; nothing is deleted or overwritten.

## T5 No warehouse
- **Setup:** `python tools/warehouse_link.py status` reports `connected: false`.
- **Oracle:** the reply and the file system.
- **Pass:** one line saying the warehouse and its client folder are not set up; `final/` stays the result; no folder is created.

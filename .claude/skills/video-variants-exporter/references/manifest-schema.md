# Manifest schema, lifecycle and findings (for `scripts/manifest_check.py`)

Load when: recording renders, reading a BLOCKED report, or deciding what to do after a master fix. The manifest answers one question: **which source state was each delivered file rendered from, and is that still the frozen master?**

## 1. Lifecycle (commands run from the project root; every command is local and free)
```
freeze   after master QA        -> master.src_hash, master.mix_sha256, matrix
stamp    BEFORE every render    -> _work/stamps/<hf>.json  (source hash computed before the render)
render   under the lock         -> final/<file>.mp4
record   after the render       -> files[] entry (refuses if the source changed since the stamp)
change   after a MASTER fix     -> master.changes[], new master.src_hash  (all derivatives become stale)
check    before saying "ready"  -> READY | BLOCKED | INSUFFICIENT_EVIDENCE, exit 0 | 1 | 2
```
Why the stamp comes first: the source hash must describe what the renderer read. Computing it after the render can hide an edit made while the render ran (the author's rule: hash computed before the render).

Master fix flow: edit the master -> `change --id M-001 --summary "..."` -> carry the same patch to every copy -> `stamp` each copy -> re-render -> `record ... --applied-all` (or `--applied M-001,M-002`). Until every file is re-recorded, `check` reports STALE_DERIVATIVE and MISSING_MASTER_FIX.

## 2. Manifest fields (schema_version 1.0.0)
```json
{
  "schema_version": "1.0.0",
  "project": "promo",
  "hash_policy": {"algo": "sha256", "globs": ["index.html", "compositions/**/*.html", "cues.js", "cues.json", "assets/**/*", "fonts/**/*", "data/**/*"]},
  "delivery_profile": {"lufs_target": -14.0, "lufs_tol": 0.5, "tp_max": -1.0},
  "master": {"hf": "hf", "src_hash": "<64 hex>", "round": "v3", "mix_sha256": "<64 hex>", "frozen_utc": "2026-10-02T10:00:00Z",
             "changes": [{"id": "M-001", "summary": "phone fix at 3.7 s", "src_hash_after": "<64 hex>", "utc": "..."}]},
  "matrix": ["promo_meta_master_16x9.mp4", "promo_meta_master_9x16.mp4"],
  "files": [{
    "file": "promo_meta_master_9x16.mp4", "kind": "relayout", "hf": "hf_9x16", "round": "v3",
    "aspect": "9x16", "platform": "meta", "hook": "master", "route": "ad",
    "src_hash": "<64 hex>", "from_master": "<64 hex>", "applied_changes": ["M-001"],
    "mix_variant": "shared", "mix_sha256": "<64 hex>", "file_sha256": "<64 hex>", "size_bytes": 12345678,
    "width": 1080, "height": 1920, "duration_s": 29.97, "lufs": -14.1, "tp": -1.2,
    "qa": "pass", "qa_evidence": "_work/qa/9x16/v3/report.json", "date": "2026-10-02T11:00:00Z"
  }]
}
```
- `hash_policy.algo` (default `tree-sha256-v1`): `src_hash` = sha256 over (relative path, content hash) of every file matched by `hash_policy.globs`, sorted; 64 hex; `data-hf-id` attributes are ignored in HTML (Studio rewrites them; they are not a source change). `cat-sha256-12` reproduces the delivery playbook's recipe (`cat index.html compositions/*.html cues.js assets/mix.wav | sha256sum | cut -c1-12`, 12 hex, no normalisation) for projects that already use it: choose ONE recipe per project (`freeze --algo ...`), keep it in the manifest header, never mix. The two recipes give different values for the same folder. An empty match is an error, never a valid hash.
- `name_override: {ledger_id}` on an entry marks a file name the user asked for (it must then carry explicit `platform`, `hook`, `aspect` fields). The short form `<name>_<aspect>.mp4` is read as platform `all`, hook `master`.
- `kind`: `master | relayout | hook | nomusic | nocaps | recut`. `mix_variant`: `shared | nomusic | own-vo | recut` (`own-vo` and `recut` need `mix_note`).
- `qa`: `pass | fail | not_run`; only `pass` with an existing evidence file is ready. `lufs`/`tp` are numbers measured on the FINAL file; `0.0` is a number, `null` is missing.
- `route` is informational for rights (music scope, disclosure field) but must be filled; the tool does not judge licences (that is the type skill's gate).

## 3. Finding codes (what each means and the fix)
| Code | Severity | Meaning | Fix |
|---|---|---|---|
| M001_* | block / insufficient | manifest missing, not strict JSON, wrong schema, or no files | create it with `freeze`/`record`; an empty delivery is not ready |
| M002_NO_MASTER | block | master not frozen | `freeze` after the master's full QA |
| M003_STALE_MASTER | block | master source changed after freeze | `change`, carry to copies, re-render, re-record |
| M004_MASTER_MIX_CHANGED | block | master `mix.wav` changed after freeze | same as M003 (the mix is part of the master) |
| M005_NO_MATRIX / M006 / M007 | insufficient / block | no matrix; promised file missing; unplanned file delivered | write the matrix at intake; render the missing file or amend the matrix with the user |
| M011-M015 | block | duplicate, naming, entry/name mismatch, collision, bad kind | rename to `<name>_<platform>_<hook>_<aspect>.mp4`; one file per platform/hook/aspect |
| M020-M022 | block / insufficient | file missing, empty, hash missing, bytes changed after record | re-render and re-record; never swap a file by hand |
| M031_STALE_DERIVATIVE | block | rendered from an older master | carry the master fix, re-render, re-record |
| M032_MISSING_MASTER_FIX | block | `applied_changes` lacks a logged master fix | carry that fix; record with `--applied-all` only after doing so |
| M034_CHANGED_AFTER_RENDER | block | the copy's source changed after the render | re-stamp, re-render, re-record |
| M035_SHARED_DRIFT / NO_SHARED_FILES | block / insufficient | cues or mix in the copy differ from the master | restore the master's cues/mix in the copy; if timing must change, change the master |
| M036 / M040-M043 | block | mix claim false, mix variant invalid, shared mix not shared, note missing | fix the claim or declare `own-vo`/`recut` with a reason |
| M050-M052 | block / insufficient | qa state invalid, not pass, or no evidence file | run `render-qa-delivery` on that file only |
| M060-M064 | block / insufficient | loudness/true peak missing or out of the house gate; dimensions wrong or missing | measure the final file; fix the mix, then mux (not a re-render) |
| M070_NO_MASTER_FILE | block | no file with kind=master | record the master render |
| M080-M081 | block | sub-folder or orphan file in the finals folder | move old renders to `_work/delivered/v<N>/` |

## 4. Honest limits (stated in every READY report)
- `from_master` and `applied_changes` are attestations written at stamp/record time. The tool proves the hashes, the presence of files, the naming, the shared cues/mix and that nothing changed after the record; it cannot prove a layout patch is visually right or that a fix was really applied by hand in a copy whose shared files happen to match. Evidence for that is the layout table, the overlay snapshots and the QA of each aspect.
- A hash proves identity of source files, not that the encoder produced the file you expect: the final file is measured (`qa delivery`), not trusted.
- Platform acceptance is untested: no export was ever uploaded in the research (`agent-content/references/platform-specs.md`).

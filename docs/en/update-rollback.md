# Update, pin and roll back

> Written 2026-10-02. The installer is idempotent: running it again with a newer checkout is an update. Every change is journaled, so the last update can be undone. Hebrew: [docs/he/update-rollback.md](../he/update-rollback.md). Install: [install](install.md).

<!-- step: update-rollback-01 -->
## update-rollback-01 - Before you update
```text
python install/bootstrap.py status
python install/bootstrap.py verify
```
`status` shows the installed version, the last stages and the backup stamps. `verify` shows files you modified after install ("drift"): they will be backed up before being replaced - never silently lost. Your projects, original media, other skills and unrelated agent settings are never touched.

<!-- step: update-rollback-02 -->
## update-rollback-02 - Update
```text
git -C "<toolkit clone>" fetch --tags
git -C "<toolkit clone>" pull --ff-only
python install/bootstrap.py plan
python install/bootstrap.py apply --yes
```
(Use the same `--target/--scope` you installed with if you chose any; `status` shows them. Integrations you added with `add` stay registered.) What happens: changed skill/toolkit files are copied; each replaced file is first copied to `~/.avc/backups/<UTC stamp>/`; files that disappeared from the new release are removed (after a backup); skills of yours with the same name are still skipped; unchanged files are skipped by hash. A release is immutable - a correction is a new release.

<!-- step: update-rollback-03 -->
## update-rollback-03 - Check after the update
Run `verify`, then re-render the fixture (first-output (`docs/en/first-output.md` in the editing toolkit repository; after install: `~/.avc/toolkit/docs/en/first-output.md`)) to prove the engine and fonts still work. A passing HyperFrames `check` is **not** frame-identical output: name the old and new engine version in your notes. Tool, model and price facts have their own dated check; re-check before any spend.

<!-- step: update-rollback-04 -->
## update-rollback-04 - Roll back the last update
```text
python install/bootstrap.py rollback --dry-run
python install/bootstrap.py rollback --yes
```
Restores every file the last changing `apply` replaced or removed, deletes the files it created, restores the previous manifest (a first install rolls back to "not installed"), and removes folders that became empty. `--to <stamp>` picks an older journal (stamps are listed by `status`). Not rolled back: connector registrations (remove with `claude mcp remove <name>`; `status` lists the ones the installer added), generated environments (`.venv`, `node_modules` - rebuilt by the next `apply`), and anything you changed by hand outside installed files.

<!-- step: update-rollback-05 -->
## update-rollback-05 - Stay on a version (pin)
`git -C "<toolkit clone>" checkout <tag>` then `apply`. The HyperFrames engine is pinned in `package.json` + lockfile (research pin 0.8.98; the npm "latest" on 2026-10-02 was 0.8.111 - about 100 releases a month). Upgrading it is an explicit, re-tested step (`hyperframes upgrade --project <dir> --check`), never automatic. Connector packages are pinned exactly in `integrations/catalog.toml` (for example `@playwright/mcp@0.0.83`). Node: LTS is v24 on 2026-10-02; v26 becomes LTS on 2026-10-28 - do not switch without a re-test.

<!-- step: update-rollback-06 -->
## update-rollback-06 - Ask for help without leaking anything
Send: operating system, `python install/bootstrap.py verify --json` output, the failing step id and the sanitised last error line. The installer never prints credential values (it only reports whether an environment variable is present). Do not send keys, tokens, client footage or transcripts.

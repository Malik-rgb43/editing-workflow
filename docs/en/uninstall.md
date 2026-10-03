# Uninstall

> Written 2026-10-02. Removes exactly what the installer created, using its manifest. Hebrew: [docs/he/uninstall.md](../he/uninstall.md). Install: [install](install.md).

<!-- step: uninstall-01 -->
## uninstall-01 - What is removed and what stays
Removed: the skills copied by the installer (both hosts), the shared toolkit folder (`~/.avc/toolkit`) with its `.venv`/`node_modules`, per-route Python environments, the optional marked block in your agent instruction file, `toolkit.local.toml` if the installer wrote it, and the connectors the installer registered (`claude mcp remove ...`).
Stays: your video projects and work folder (`~/avc-work`), your own skills (even with a similar name), unrelated agent settings and servers, the toolkit **clone** (delete it yourself), accounts you signed in to, and the backups folder (`~/.avc/backups`) unless you ask to purge it.
Files you edited inside installed skills are copied to the backups folder before removal; a file you added inside a skill folder keeps that folder alive.

<!-- step: uninstall-02 -->
## uninstall-02 - Preview
```text
python install/bootstrap.py uninstall --dry-run
```
Prints the list of files, folders and connectors that would go. Nothing changes.

<!-- step: uninstall-03 -->
## uninstall-03 - Run it
```text
python install/bootstrap.py uninstall --yes
```
The manifest is renamed to `install-manifest.uninstalled-<stamp>.json` as a receipt. Add `--purge-backups` to delete `~/.avc/backups` as well. Run `python install/bootstrap.py verify` afterwards: it must say not installed.

<!-- step: uninstall-04 -->
## uninstall-04 - Leftovers only you can remove
* Sign-ins: revoke connector access in each vendor's account settings (Higgsfield, ElevenLabs) and delete API keys you created (Pexels, 21st.dev, Gemini) - they were never stored by the installer.
* Environment variables you set by hand (Windows: Start -> "Edit environment variables for your account"; macOS: your `~/.zshrc`).
* Packages you approved from a package manager (`winget uninstall <id>` / `brew uninstall <name>`): Node, FFmpeg, uv, Git are general tools - remove them only if nothing else needs them.
* The clone folder and `~/avc-work` when you no longer need your projects. Deleting a work folder deletes your videos: copy what you want first.

<!-- step: uninstall-05 -->
## uninstall-05 - Reinstall
`git pull`, then follow [install](install.md). The backups from earlier runs stay until you purge them.

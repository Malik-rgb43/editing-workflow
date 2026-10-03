# packaging/

Distribution is specified in `REPO_ARCHITECTURE.md` section 6 (research T20 section 3, 2026-10-02): a tagged clone for students who edit
and update, a release ZIP for students without Git, an optional thin plugin, an optional devcontainer. **Only the local, deterministic
parts exist today; nothing here is published, uploaded or tagged** (`scripts/release.py` never uploads).

| path | purpose | status (2026-10-02) |
|---|---|---|
| `release-excludes.txt` | extra globs left out of every release archive (on top of the built-in ones in `scripts/release.py`) | used by `release.py build` |
| `releases/` | descriptors (`*.release.json`) and checksums (`*.sha256`) of releases, committed after an owner-approved release | empty; no release exists |
| `plugin/` | generated host package for a Claude plugin (thin wrapper, never the source of truth) | placeholder; not generated, not loaded on a real client |

Rules: one canonical source (`agent-content/`); a plugin or a ZIP must be byte-identical to it where it carries skills (package-parity gate:
`python scripts/build_agent_adapters.py --check`); the archive must pass `python scripts/release.py verify <zip>`; releases are immutable;
nothing is shipped that `python scripts/gen_bom.py` blocks (see `THIRD_PARTY_NOTICES.md`). Update and rollback: `python scripts/release.py plan --target X.Y.Z`.

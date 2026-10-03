# packaging/releases/

Release descriptors and checksums go here **after** an owner-approved release:

    editing-workflow-<X.Y.Z>.release.json   descriptor: version, zip sha256, manifest sha256, gate results, releasable, uploaded=false
    editing-workflow-<X.Y.Z>.zip.sha256     `<sha256>  <zip name>` (sha256sum format)

The archives themselves are not committed (they are built into the git-ignored `dist/` by `python scripts/release.py build --version X.Y.Z --final`).
Releases are immutable: `release.py build --final` refuses a version whose descriptor already exists here; a correction is a new version.
No release has been built or published yet (2026-10-02).

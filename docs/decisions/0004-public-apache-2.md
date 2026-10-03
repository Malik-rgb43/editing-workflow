# ADR 0004 - Public repositories under Apache-2.0

- Status: accepted (toolkit author decision, 2026-10-02: public for anyone who gets the link; licence Apache-2.0; GitHub account `Malik-rgb43`; names `claude-code-setup` and `editing-workflow`)
- Date: 2026-10-02
- Resolves: decision default Q12 of ADR 0001 (private until a licence is chosen)

## Decision
Both repositories are public and licensed under the **Apache License 2.0** (`LICENSE`, `NOTICE`). The copyright holder line uses the GitHub handle, not a personal name.

## Consequences
- Anyone with the link may use, modify and redistribute the content under Apache-2.0 terms (keep the licence and NOTICE, mark changes, no trademark grant, no warranty).
- Third-party tools, models, fonts, vendor skills and services are **referenced, not bundled**; each keeps its own licence and terms (see `THIRD_PARTY_NOTICES.md`, the integrations catalogue and the dated licence reference). A public repo is not a licence for them.
- No client material, transcripts, brand kits, secrets or personal paths are in the repositories: `scripts/scan_secrets.py` passes; `scripts/scan_private.py` runs its pattern rules and reports the client-name denylist part as `not_run` (the author supplied no names; decision recorded 2026-10-02).
- The private research repository stays private and is never copied into these repositories.
- The licence is for the code and text written for this toolkit; it says nothing about the rights to any media a student edits.

## Known limits
Not legal advice. Counsel review of the legal/privacy guides and of the AI-disclosure guidance is still recommended before presenting them as professional guidance.

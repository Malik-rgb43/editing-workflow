# Profile `cloud-template` — a template, not a provider

> Dated 2026-10-02 · evidence state **unmeasured** · the template itself expires 2026-10-16; **a copied profile carries its own dated snapshot and expires with it.** **unsupported ≠ missing ≠ error.**

## What this is
A starting point for `profiles/cloud-<provider>/`. Copy the folder, rename it, fill in every `<fill in>` field. A cloud profile lets the toolkit call **one** named provider for **one** named stage. It is the opt-in route for a weak machine (the cloud-assisted student profile — 4-core / 16 GB / SSD / network — is an **instructor recommendation, not a measured minimum**) and for stages a student chooses to offload.

## Rules every copy must keep
1. **Explicit authentication by the student.** Credentials live in environment variables or the OS keychain — never in repo files, command lines, logs, diagnostics, output metadata or screenshots. Doctor checks **presence only**.
2. **A dated snapshot** of capabilities, price formula, terms, region and exact model ids (`[snapshot]` block). If it is older than the configured age (proposed 14 days for prices) the profile **blocks** paid actions; it does not "pass".
3. **No implicit fallback and no paid retry.** A failure never silently switches to another paid route; a billable timed-out request is not retried until the provider's state is reconciled.
4. **Paid-generation gate:** prior approval **with a dated estimate** for every costed job; an explicit "generate" is approval only within the balance and never covers on-screen facts or client approval; buying credits is the user's action; sign-in is not spend authorisation.
5. **Privacy gate before price:** check the provider's training/retention terms and the workspace opt-out **before** client footage leaves the machine (e.g. Higgsfield API terms updated 2026-09-02, §7.2: training on content unless the workspace opt-out is set, effective within 10 business days, prospective only). Eligibility is decided before price.
6. **Ledger:** provider, capability, `evidence_state` (`documented` = a page was inspected; `live` = a dated smoke test), request id, job id, input/output hashes, billing wallet, estimated and actual cost, failure class, timestamps.
7. **Never mix wallets** (credits vs API dollars) and never convert credits to client fees.
8. **No single provider covers the whole professional workflow**; Hebrew/RTL quality, accepted-output speed and cost are unmeasured for every provider.

## Download size and source
None locally. Upload/download bytes are shown per job before sending.

## Hardware
A network connection; no local GPU.

## Tested-on evidence
A template has none. A copy records its own: live smoke-test date, request id, `ffprobe` and hash of outputs.

## States
| State | When |
|---|---|
| `unsupported` | provider unavailable in the student's region/plan, or the client footage may not leave the machine |
| `missing` | no credentials present (presence-only check), or no dated snapshot |
| `error` | a real tiny **non-spending** call fails; a snapshot older than the configured age is *blocked*, never `pass` |

## Licences
The provider's own terms. Library licence, asset licence, model-output rights, account entitlement and cost are separate decisions.

## Uninstall
Delete the copied profile folder and cached job results; remove credentials from the environment/keychain yourself.

---
name: paid-spend-gate
description: Gate every paid action before it runs - AI image, video or audio generation, upscales, paid APIs, cloud renders, credit purchases, trials that need a card. Produces a dated cost estimate, requires the user's explicit approval of the number, enforces a retry cap and records provenance. Hebrew - עלות, קרדיטים, כמה זה יעלה, תייצר, תאשר הוצאה, תשלום. NOT for free local work (ffmpeg, local ASR, local render) or for planning that makes zero calls.
compatibility: scripts need Python 3.10+ (stdlib); ffprobe optional. approval_hook.py targets Claude Code PreToolUse hooks; other clients need the wrapper pattern.
metadata:
  version: "0.1.0"
  kind: gate
  status: "specified; deterministic checks only; model eval not run"
---

# paid-spend-gate

Every paid action passes here first: dated estimate -> explicit approval -> retry cap -> provenance. The skill contains no prices; it contains the formulas, the refusals and the records.

## Rules that never bend
1. **No call before approval of a number.** The estimate is shown, the user approves that number, then (and only then) the first paid call runs. "Only prepare a document" = zero calls.
2. **No price promises** (decision default Q3). Never quote a provider price from memory or from this repo's examples: read the current card today, record its date, show the formula.
3. **Wallets stay separate.** Credits, API dollars and another vendor's price are never summed or converted; credits are never turned into a client fee. A catalogue listing does not prove account access.
4. **Prose is not enforcement.** Hard limits live in a hook, an `ask` permission or a wrapper (`references/hook-config.md`). A skill is procedure, not permission: the user's and project's limits on spend, installs and uploads override everything here.
5. **Every attempt counts**, including user-rejected and billed-failed ones. At the cap: stop and ask.
6. **Client media leaves the machine only with a per-client decision** (some vendors may train on submitted content unless opted out).
7. Fail closed: a missing date, missing source, stale price or unreadable approval is `blocked`, never "probably fine".

## Procedure
1. List the planned calls: provider, exact model id, route, mode, dimensions, duration, fps, audio, count. Prefer the cheapest route that proves the idea: a still or an animatic (plan + stills) before paid motion; shortest viable shot; ETA over 30 minutes for one local shot = propose another route first.
2. Re-read each price card today. Write `spec.json` (`scripts/estimate.py` docstring; `references/sample-spec.json`). Run `estimate`, show the table with the message in `references/estimate-worksheet.md` section 4.
3. Wait for the user's reply. Then `approve` with their quote and the exact ceiling they saw. No `--approved`, no token.
4. Before EVERY call run `can-run`; after EVERY call run `record` (ok, failed, rejected, timeout). After a timeout reconcile with the provider before any repeat.
5. For each delivered file run `provenance`. Write actuals and accepted seconds into the project ledger.
6. Stop at the cap, at the user's limit, or when the approval expires; ask, do not extend.

## Gates
States: `pass | fail | blocked | n/a` with a reason. Timeout, empty sample or missing input never passes.
| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G1 dated estimate | every price source has name, `checked_at` <= 7 days (course setting) and not in the future, tax status, plan; per-line formula shown | `cost_estimate.json` from `estimate.py` exit 0 | refresh the card; never reuse a stale row | paid-spend-gate | price card changes or a day passes |
| G2 approval | the user approved the displayed ceiling after seeing it; quote stored | `approval.json` created by `approve --approved --approval-quote` | blocked: no call | paid-spend-gate | estimate, model, count or wallet changes |
| G3 retry cap | attempts per line <= `count x (1 + retry_cap)`; billed total < approved ceiling; no repeat after an unreconciled timeout | `can-run` exit 0 and `spend_ledger.jsonl` | stop and ask | paid-spend-gate | each call |
| G4 allowance flags | an included/free-trial flag is sent only if the user asked, and never dropped silently | the call record | ask: covered values or pay | paid-spend-gate | any parameter change |
| G5 runtime control | a hook, `ask` rule or wrapper blocks paid calls without approval | settings file + a denied test call | install per `references/hook-config.md`; until then every call needs a fresh human yes | project owner | client or tool list changes |
| G6 provenance | provider, exact model id, route, mode, dimensions, duration, fps, audio, plan, price date, file hash and ffprobe stored per output | `provenance.jsonl` | backfill before delivery | paid-spend-gate | each new output |
| G7 wallet separation | no cross-wallet total anywhere; credits and USD kept apart | estimate `totals` per wallet | split the line | paid-spend-gate | new provider added |
| G8 privacy | client footage/likeness/voice uploads have a recorded per-client decision | note in BRIEF.md RIGHTS | block upload | video-brief-intake / user | new asset class |

## Approval wording
- Approval before any number was shown does not count. A standing approval must state a number and an end date.
- An explicit "generate" order starts the process: show the estimate first, run after the number is approved. It never covers on-screen facts, claims, or a client's sign-off on factual stills.
- A user may waive the second confirmation in writing for a stated number ("generate up to X, no need to ask again"); that is a standing approval and is stored like any other.

## Stop conditions
- Estimate over the user's stated limit: `blocked_over_limit`, offer a cheaper route.
- Provider or model unavailable on this account: report and stop that line; do not substitute a model.
- The user asks "is this cheaper than the API?": keep wallets separate and say what is unknown.

## References and scripts
- `references/estimate-worksheet.md`: load when estimating or asking for approval (formulas, approval message in Hebrew and English, command sequence, allowance flags).
- `references/price-sources.md`: load when recording or reading a price fact (dated-row format, rules, expired examples).
- `references/hook-config.md`: load when setting up runtime control (sample `.claude/settings.json`, limits, strong mode, other clients).
- `references/sample-spec.json`: load when writing a spec.
- `scripts/estimate.py`, `scripts/approval_hook.py`: each runs `--self-check`.
- Shared dated tables (other owner): `agent-content/references/model-routing.md`, `agent-content/references/cost-model.md`.

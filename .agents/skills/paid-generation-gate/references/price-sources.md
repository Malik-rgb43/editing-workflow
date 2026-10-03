# Price sources: dated reference module (all prices perishable)

Load when you need to know HOW to record a price fact or what the repo already knows. This skill promises no price (decision default Q3: no Higgsfield price promises; show the formula and "check the current price card"). Prices and model ids change; an expired or unrefreshed row is UNKNOWN, never "still true". A failed refresh also means unknown.

Shared dated tables (owned by another agent, read them for context, then re-check at spend time): `agent-content/references/model-routing.md`, `agent-content/references/cost-model.md`.

## 1. Record format (one row per fact)
| Field | Meaning |
|---|---|
| fact | the price or rule, with unit (per second, per 1,000 tokens, credits per second) |
| id | provider + exact model id/route/mode (a model name is not a spec) |
| version | provider's own version label, or "rolling" |
| checked_at | UTC date the card was read (this is what `estimate.py` enforces) |
| source | URL of the price card or docs page; or "user stated" |
| scope | plan, region, wallet, resolution, tax status |
| confidence | high (read today on the live card) / medium (docs page) / low (secondary) |
| expiry | when it must be re-read: before every spend; hard stop after the max age (default 7 days, `--max-age-days`, a course setting not a vendor fact) |
| refresh | a NON-SPENDING way to refresh: open the price page, read the plan screen, call a free quote/balance endpoint only if the provider documents it as free |

## 2. Rules
1. Re-read the card on the day of spending; copy the date, plan and tax status into the spec.
2. Separate wallets: provider credits, API dollars and another vendor's price are different wallets.
3. A catalogue entry does not prove access on this account; a model-listing call that returns no prices is not a price.
4. Never convert credits to API dollars, or credits to what the client is charged.
5. Row older than the max age: the gate blocks (`stale_price`); refresh first.
6. Unlisted or unreadable price: ask the user for the number or stop; do not estimate from memory.

## 3. Example rows (observed 2026-10-01 in the course research; EXPIRED by the time you read this; shown only to illustrate the format and the shape of the formulas)
| fact | id | checked_at | source | scope | confidence | expiry |
|---|---|---|---|---|---|---|
| a token-metered video tariff: tokens = ceil(H x W x (output + input-video seconds) x 24 / 1024); base 0.0214 USD per 1,000 tokens; x0.6 when reference-to-video has video input | one router's Seedance 2.5 route, 1280x720 | 2026-10-01 | course research cost model | USD, before VAT/FX, 720p only (not a 1080p quote) | medium | before any spend |
| image generation 720p example 0.05 USD | an API route's still model | 2026-10-01 | same | USD | medium | before any spend |
| a motion model example 0.05 USD per generated second | an API route's image-to-video turbo model | 2026-10-01 | same | USD | medium | before any spend |
| direct API of one video model announced removed (notice dated 2026-09-24) | do not route new direct API work there | 2026-10-01 | same | n/a | medium | re-check |
| a vendor's terms may allow training on content unless the workspace opts out | a hosted generation vendor | 2026-10-01 | same | per workspace | medium | per client decision |
| an older internal plan/price table for one vendor is stale; the current card could not be read | one vendor | 2026-10-01 | open question Q3 | n/a | low | never quote |
(src: blueprint MODEL_ROUTING and COST_MODEL, open question Q3; 2026-10-02)

## 4. Local and open models are not free by default
Gate by checkpoint licence (never inherit the runtime's), territory/revenue/non-commercial conditions, RAM/VRAM and time per output second measured on the target machine. On the reference machine a 1.3B-parameter local video model measured about 669 s per output second with 18.4 GB RAM and GPU VAE crashes (E10); NVIDIA and Apple numbers are unmeasured. The 30-minute rule: if one shot's ETA exceeds 30 minutes, propose 2.5D or another route before starting.

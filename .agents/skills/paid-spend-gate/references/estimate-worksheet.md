# Estimate worksheet: formulas, the approval message, the command sequence

Load when you are about to estimate, show, approve or record a paid action. Prices are never stored in this skill; the worked numbers below are an arithmetic example copied with their date from the course cost model (observation date 2026-10-01, USD before VAT/FX, first-pass generation only; it is not accepted-output cost, not a forecast, not procurement approval). Source: blueprint COST_MODEL, 2026-10-02.

## 1. What counts as paid
AI image/video/audio/3D generation, upscales, outpaints, dubbing, voice cloning or changes, paid APIs, cloud renders (Lambda/Cloud Run/hosted), subscriptions or trials that need a card, buying credits or domains. "Free" still hides cost: a subscription allowance, an included-credits path and editor time all cost something; "free" here only means no metered cash in the path. Free local work (ffmpeg, local ASR, HyperFrames render) does not use this skill.
Planning only ("only prepare a document", "plan, do not generate") = zero calls; produce the estimate as a document and stop.

## 2. Formulas (all inputs come from the provider's CURRENT price card; record the date)
| calc | cost per call | when |
|---|---|---|
| `per_unit` | quantity x unit_price | per second, per image, per credit |
| `fixed` | unit_price | flat per call |
| `tokens` | ceil(width x height x (out_s + in_video_s) x fps_factor / divisor) / 1000 x price_per_1k x multiplier | token-metered video tariffs (the example tariff: fps_factor 24, divisor 1024) |
Per line: first pass = per call x count; ceiling = first pass x (1 + retry_cap). Totals are summed **per wallet** (credits, API dollars, another vendor's price: separate wallets; never converted into each other; credits are never converted into a client fee). A catalogue listing does not prove the user's account has access.

Worked example (arithmetic only): 2 shots, 1280x720, 10 s output + 4 s supplied input video, example rate 0.0214 per 1,000 tokens, multiplier 0.6: tokens = ceil(1280x720x14x24/1024) = 302,400; per call 302.4 x 0.0214 x 0.6 = 3.882816; two calls 7.765632; plus 2 stills at 0.05 = 0.10; first pass 7.865632. With retry cap 1 the ceiling is 15.731264. `references/sample-spec.json` reproduces it.
Reference scenario range from the same model: first-pass generation worksheet USD 0 to 15.28 across five reference briefs and three tiers (E07; time and accepted-output cost unmeasured).

## 3. Accounting layers (record per project, never merge)
| Layer | Contains |
|---|---|
| Metered subtotal | the worksheet + chargeable retries + any LLM/API, ASR/TTS/music, cloud render, storage, egress |
| Incremental cash | newly required plan or minimum credit pack, top-ups, taxes, FX (a minimum pack costs more up front than consumption) |
| Allocated cost | share of an existing plan + labour + energy + hardware; do not charge included credits again as pay-as-you-go |
| Accepted-output cost per second | chosen basis / actual accepted delivered seconds (measured after the work; never assume a success ratio) |

## 4. The message that asks for approval (Hebrew / English, fill every field)
```
לפני שמשלמים - הערכה מתאריך <YYYY-MM-DD> (מחיר נבדק ב-<date>, מקור: <name/url>, תוכנית: <plan>, מס: <excl/incl/unknown>)
קריאות: <n> (+<r> ניסיונות חוזרים מותרים) | ארנק: <wallet> (<currency>)
נוסחה: <formula per line>
סכום ראשוני: <first pass> | תקרה כולל ניסיונות חוזרים: <ceiling> | מגבלה שלך: <limit or none>
לא כלול: מס/המרה, ניסיונות מעבר לתקרה, זמן בדיקה. לאשר את התקרה <ceiling>?
```
```
Before spending - estimate dated <YYYY-MM-DD> (price checked <date>, source <name/url>, plan <plan>, tax <excl/incl/unknown>)
Calls: <n> (+<r> retries allowed) | wallet: <wallet> (<currency>)
Formula: <per line>
First pass: <x> | ceiling with retries: <y> | your limit: <limit or none>
Not included: tax/FX, attempts beyond the cap, review time. Approve the ceiling <y>?
```
Approval is the user's reply naming or accepting that number. A bare "go" after the number was displayed counts; an approval given before any number was shown does not. Standing approval ("up to X in wallet W until DATE") is allowed when it states a number. An explicit "generate" request never covers on-screen facts, claims, or client approval of factual stills.

## 5. Command sequence (all under `scripts/`, stdlib)
1. Re-check the price card today; write `spec.json` (see the docstring of `estimate.py`).
2. `python estimate.py estimate spec.json --out cost_estimate.json` and show the table. Exit 4 = over the user's limit: nothing may be submitted.
3. After the user's reply: `python estimate.py approve cost_estimate.json --approved --approval-quote "<their words>" --approved-amount <wallet>=<ceiling> --out .avc/approval.json`. Without `--approved` the script refuses to write a token.
4. Before EVERY paid call: `python estimate.py can-run .avc/approval.json --line <id>`; non-zero means stop.
5. After every call, including failures, rejections by the user and timeouts: `record ... --outcome ok|failed|rejected|timeout [--billed <amount>]`. After a timeout, check the provider's job list and record `--outcome reconciled` before any repeat.
6. Each delivered output: `provenance --file <out> --provider --model <exact id> --mode --plan --price-date --line <id>`; it stores the hash and ffprobe data.
7. Close out: `status`, then write actuals and accepted seconds into the project timing ledger.
A rejected attempt counts toward the cap; at the cap, stop and ask. Never retry a typed rejection identically.

## 6. Included-allowance flags ("unlimited"/free-trial modes)
If the user asked to use an included or trial allowance: send the flag the provider documents and let the backend accept or reject; never add it on your own and never drop it quietly. If the planned values fall outside what the allowance covers, stop and ask: run within covered values, or pay. Never silently downgrade, never silently charge, never swap models as a fix.

## 7. Privacy before client media
Some providers' terms allow training on submitted content unless a workspace opt-out is set (observed 2026-10-01 for one vendor, prospective, 10 business days). Before sending client footage, stills or voices to any hosted service: ask the user for a per-client decision and record it; otherwise block.

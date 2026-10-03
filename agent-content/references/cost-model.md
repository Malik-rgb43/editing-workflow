---
module: cost-model
checked_at: 2026-10-02
expires: "30 days (2026-11-01) for any price-bearing row; formulas and layer definitions do not expire"
confidence: "arithmetic [MEASURED-lab] (two independent scripts, 0 errors); prices [VERIFIED-external] or [SOURCED-unverified] per row; time-to-accepted-output unmeasured"
refresh: "read-only: re-read the price rows in model-routing.md, then recompute with the formulas; never run a job to calibrate"
---

# Cost model — formulas, worksheet, scenarios — dated reference

| Field | Value |
|---|---|
| Fact set | cost accounting layers, per-route formulas, a fillable worksheet, 15 first-pass scenarios, approval-message template, credit-saving tactics, cloud-render formulas |
| Versions / ids | prices from `model-routing.md` section 3 (PR-01…PR-14); LLM meters of 2026-10-01 (Sonnet 5.5 Standard $2 / $10 per MTok input / output) |
| `checked_at` | **2026-10-02** (= research date, no live re-check; **must be refreshed before use**) |
| Source | blueprint `COST_MODEL.md`; `distilled/05-…/credits-and-cost.md` (E07 worksheet, T14 audit); `distilled/08-…/hardware-and-os.md` §7 |
| Scope / plan / region | USD before VAT/FX; observation date 2026-10-01; **not** accepted-output cost, **not** a forecast, **not** procurement approval |
| Confidence | arithmetic: `[MEASURED-lab]` (Python 3.12.10, Decimal; verified again 2026-10-02); price inputs: see model-routing |
| `expires` | 30 days for prices; the table is blocked from student display once expired unless it is labelled "illustrative, dated" |
| Non-spending refresh | refresh the PR-rows, then recompute the worksheet below by hand or with the calculator; `show_plans_and_credits` and the vendor price page are read-only |

**No price promises (decision default Q3).** The repo shows the **formula** and the instruction **"check the current price card"**. It never says a Higgsfield plan is cheap, free or unlimited; the web-plan rates and the free-trial / unlimited fair-use rules were unresolved on 2026-10-01.

## 1. What a number means
Every scenario row below assumes **exactly one billable output per planned call**. Failed charged jobs, extra attempts, unused outputs, human review and acceptance must be appended from the project's real records. "Free" means *no metered API cash in the path* — subscriptions, editor labour, machine ownership, electricity, storage, licences and setup still cost something. Do not promise free local generative video on the reference machine.

## 2. Four cost layers (use these field names in every ledger)
| Layer | Definition | Note |
|---|---|---|
| Metered subtotal | sum of exact job meters + add-ons + chargeable failures + LLM/API + optional ASR/TTS/music + cloud render/storage/egress | image/audio references may or may not add to a meter depending on the route |
| Incremental cash | newly required plan or minimum credit pack + top-ups/PAYG + tax/FX | a minimum pack costs more up front than the consumption subtotal |
| Allocated cost | share of an existing plan + external meters + labour + energy + hardware allocation (state the rule, unused credits, expiry) | do not charge included credits again as PAYG |
| Accepted-output cost per second | chosen cost basis ÷ **measured** accepted delivered seconds | no success ratio, acceptance ratio or free retry is ever assumed |

Never convert credits to client fees, API dollars to subscription credits, or one vendor's price to another's. `[VERIFIED-external]` (src: T05 COST_MODEL_INPUTS)

## 3. Formulas (copy from the PR-rows; they expire with them)
```
Seedance 2.5 on Higgsfield:
  tokens = ceil(H * W * (out_s + input_video_s) * 24 / 1024)
  USD    = tokens / 1000 * base          base 0.0214 (480/720), 0.0234 (1080)
  reference-to-video route WITH video input: base * 0.6
Genjutsu:     ceil(input_s) * 0.318 | 0.681 | 1.632          (480 | 720 | 1080)
Runway Seedance: 0.01 * max(80, out_s*20|30|68 + in_video_s*10|15|34)
Runway Gen4.5 / Turbo / Act Two: 0.01 * seconds * 12 | 5 | 5   (+5 credits/s ProRes/PNG, Gen4.5 only)
Veo 3.1 (Gemini): seconds * rate(tier, resolution); audio included
MiniMax H3: (out_s + ref_video_s) * 0.08|0.13 + max(0, images-5) * 0.04
Luma Ray 3.2: table lookup per job (10 s != 2 x 5 s)
Break-even of a plan: jobs = plan_price / PAYG_rate_per_equivalent_job  (expiry, idle allowance, renewal price can reverse it)
```
Worked examples (arithmetic only; verified): Seedance 720p 16:9 10 s no video = 216,000 tokens → **$4.6224**; with 4 s input on the reference-to-video route = 302,400 tokens → **$3.882816**; 5 s no video = 108,000 → **$2.3112**; 5 s + 4 s input = 194,400 → **$2.496096**; Genjutsu 8.2 s at 720p = 9 × 0.681 = **$6.129**; MiniMax H3 example = **$1.20**; Runway Seedance 10 s + 4 s ref = (300 + 60) × 0.01 = **$3.60**. `[VERIFIED-external]` formulas V02-V07; `[MEASURED-lab]` arithmetic.

## 4. Worksheet (fill one per project; keep in the ledger)
| Line | Route (provider, exact id, mode) | Unit price + date | Qty (shots × takes) | Subtotal | Cap / retry limit | Approved by + date |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| add | extra attempt (same size) | = line unit cost | | | | |
| add | minimum pack / plan upgrade needed? | | | | | |
| add | LLM, ASR/TTS, music, cloud render, storage/egress | | | | | |
| = | metered subtotal · incremental cash · allocated cost · accepted-output cost/s (after delivery) | | | | | |

Time to accepted output = acceptance timestamp − authorised-start timestamp (paused time reported). Record cold vs warm start, stage dependencies, heavy-job queue, upload/download bytes, generation queue/compute, render/QA, **active human review vs idle wait**, every revision, every billed failure. Parallel work follows the critical path, not the sum. `[IDEA]` spec (src: T14).

Local vs cloud: optimise cash **and** time to accepted output. Example sensitivity (arithmetic): a local ASR that saves the whole $0.18 per audio-hour but costs one extra correction minute per hour breaks even at only **$10.80 per hour of editor time**. Decide *eligibility* (data destination, checkpoint licence, voice consent) before price. `[IDEA]` (src: T22).

## 5. Fifteen first-pass scenarios (generation only; USD, observed 2026-10-01)
Common assumptions: supplied/owned A-roll, VO, music; stills = Runway `gen4_image` 720p $0.05 each; motion = Gen4 Turbo image-to-video $0.05 per generated second (candidate path, not a quality winner; 5 s jobs are worksheet assumptions); Pro = Higgsfield Seedance 2.5 at 1280×720 (**not a 1080p quote**). Tier meaning: Free = no metered cash (not creatively equivalent); Low = Turbo; Pro = Seedance.

| Brief | Free | Low | Pro |
|---|---|---|---|
| Talking-head 45 s | 0.00 (local ASR, HyperFrames captions, owned stills) | **0.60** (2×5 s Turbo B-roll + 2 stills) | **7.865632** (2×10 s reference shots, 4 s supplied input each, + 2 stills) |
| Ad 20 s | 0.00 (owned assets, local 2.5D) | **1.20** (4×5 s Turbo + 4 stills) | **9.4448** (4×5 s Seedance + 4 stills) |
| Motion launch 30 s | 0.00 | **0.15** (3 stills + local 2.5D) | **9.3448** (2×10 s Seedance + 2 stills + 10 s local motion) |
| AI film 30 s | 0.00 (2.5D animatic) | **1.80** (6×5 s Turbo + 6 stills) | **15.276576** (6×5 s reference shots + 6 stills) |
| Testimonial 60 s | 0.00 (real footage) | **0.60** (illustrative B-roll only) | **7.865632** |

`[MEASURED-lab]` arithmetic: reproduced by two independent scripts and again 2026-10-02 (talking-head Pro = 2×3.882816 + 2×0.05; ad Pro = 4×2.3112 + 4×0.05; motion Pro = 2×4.6224 + 2×0.05; film Pro = 6×2.496096 + 6×0.05). One extra billed attempt adds exactly that row's unit cost (Turbo 5 s $0.25; Seedance 10 s + 4 s ref $3.882816; 5 s no ref $2.3112; 10 s no ref $4.6224; extra still $0.05). **Retry rates are unknown — never invent them.** Not in these numbers: LLM/agent tokens (example 20k uncached input + 4k output = $0.08 on a $2/$10 per MTok model, before cache/tools; Codex credits use a different meter), ASR/TTS/music, cloud render/storage, labour, electricity, licences, tax/FX, retries, review, accepted seconds, elapsed time.

## 6. Credit-saving tactics (ranked; gains overlap, they are **not additive**)
1 Studio review → range renders → one final render (modelled saving: k avoidable full renders × R − review cost V; E12 synthetic 30 s, six notes: 430 s full-render-per-note vs 240 s range drafts + one final) `[MEASURED-lab]` · 2 range-only matte · 3 faster matte kernel (licence caveat, see `matte-routes.md`) · 4 segment renders · 5 audio-only remux (1.8 s in E12) · 6 pre-render gates · 7 ASR on the fast route from minute 0 · 8 reusable approved 3D loop · 9 **30-minute gate → 2.5D** `[RULE-owner]` · 10 content-hash caches · 11-16 (scene-level cache, worker sweeps, hardware encode, choice boards, image-first/greybox/animatic approval before paid motion, cloud offload/batch APIs) are untested or documented only. Image-first: approve stills (cheap) before paid motion; a lower-resolution draft + regenerated final pays only if expected avoided wasted finals exceed the draft cost (probabilities unknown). Seed reuse implies no free reuse and no cross-model determinism. Batch-API 50% discounts apply to supported asynchronous LLM tasks, not established for the video endpoints.

## 7. Cloud rendering formulas (no deployment was measured)
HyperFrames own AWS Lambda: Σ(memory GB × billed seconds × region rate) + requests + Step Functions transitions + storage/transfer/logs. HyperFrames hosted cloud documents 4K at 1.5× billing, a 200 MB archive limit, reusable asset ids, idempotency — **base tariff not established**. Remotion Lambda: configuration-specific GB-seconds + requests + S3 fetch/storage/egress/logs + the applicable Remotion licence (the vendor's USD 0.001 per 7.56 s warm HelloWorld is not an estimate for a real job). Cloud Run: CPU-seconds + GiB-seconds + requests/network/storage (+ GPU if configured). A rented GPU pod bills boot, dependency download, weight load and idle; persistent storage can bill after compute stops. Dated inputs (2026-10-01, `[VERIFIED-external]` unless noted): Runpod RTX 4090 offer $0.74/h; Codespaces 4-core $0.36/h + $0.07/GB-month `[SOURCED-unverified]`; Remotion Lambda pricing page **blocked** (no estimate). `[SOURCED-unverified]` overall.

## 8. Rules the repo enforces (not facts — behaviour)
1. Paid action = **prior approval with a dated estimate** `[RULE-owner]`; an explicit "generate" is approval within the balance and never covers on-screen facts, client approval of factual stills, or spend beyond the balance. Buying credits is always the user's own action.
2. Credits are never converted into client fees. Price rows older than the configured age block spending.
3. Check the balance on the **path you generate with** (API vs MCP connector may show different balances). 4. Every project writes a timing + credit ledger. 5. The course starts with a **zero-generation first exercise** and shows an approximate budget + approval + a retry cap before any later paid exercise. 6. Balance too low → stop, state the number needed, deliver the free parts (plan, stills, animatic).

## 9. Approval-message template `[IDEA]`
"Route: {provider · exact id · mode}. Plan: {n shots} × {k takes} × {unit price} ({price date}) = {subtotal}. One extra attempt: {unit cost}. Retry cap: {n}. Minimum pack/plan change needed: {yes/no}. Free fallback: {animatic / stills / 2.5D}. Prices are list prices before tax; I will stop and ask if the balance or price differs. Approve?"

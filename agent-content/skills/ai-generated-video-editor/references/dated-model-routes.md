---
module: ai-generated-video-editor/dated-model-routes
checked_at: 2026-10-01
expires: "7 days (2026-10-08) for prices and promotions; 14 days (2026-10-15) for model ids and limits; or before any spend, whichever is first"
confidence: "documentation rows, mixed [VERIFIED-external] (T05 verdict ids) and [SOURCED-unverified]; NO generation was ever run: no latency, quality, identity, lip-sync, Hebrew or acceptance measurement exists"
refresh: "non-spending only: read each provider's official price and terms page, list the catalogue (models_explore returns NO prices), read the plan/balance view on the path you will generate with; never a 'test generation'; write the new checked_at"
---

# Dated model routes (the minimum this skill needs)

> **Verify on the live price card before any spend.** This is a snapshot, not a quote and not a promise (decision default Q3: no Higgsfield plan-price promises - web-plan rates and unlimited fair-use rules were unresolved on 2026-10-01). The fuller module is `agent-content/references/model-routing.md` (owned elsewhere; if both exist and disagree, the one with the later `checked_at` wins, and a disagreement means: stop, refresh, ask). `paid-spend-gate` owns the dated estimate and the approval; this file only informs the plan. Run `python scripts/check_route_freshness.py references/dated-model-routes.md` first: `stale` or `blocked` = treat every row as unknown.

| Field | Value |
|---|---|
| Fact set | candidate video/image routes, limits, meter formulas, exclusions, route privacy notes |
| Versions / ids | as named in the rows; "as listed" = the label seen in a catalogue, not a verified API id - record the exact id at quote time |
| `checked_at` | **2026-10-01** (vendor pages read, Asia/Jerusalem; no live re-check since) |
| Source | distilled/05 models-and-routing (T05 verdicts V01-V37), credits-and-cost, prompting; blueprint MODEL_ROUTING, COST_MODEL (2026-10-02) |
| Scope | USD before tax/FX/promotion, list price of the named route; Israeli eligibility, VAT, plan allotment NOT checked |
| `expires` | see front matter |

## 1. What to record for every authorised job (a model name is not a spec)
provider - exact model id - route (API / MCP / CLI / web / Flow / aggregator) - mode - dimensions - duration - fps requested AND received - reference durations - audio on/off - output format - plan - wallet (credits vs API dollars vs another vendor's price: never mixed) - price timestamp - quote - `ffprobe` + sha256 of every output (`scripts/probe_takes.py`). Seed reuse helps reproducibility where exposed; it is not an identity guarantee, not cross-model, not a discount.

## 2. Candidate routes (TEST CANDIDATES from documented controls - not a quality leaderboard)
| Intent | Candidate (as listed) | Limits seen | Meter / example (2026-10-01) | Notes |
|---|---|---|---|---|
| Stills for identity/product/location (image-first) | GPT Image 2.x through the Codex CLI (reference toolchain, `codex exec ... -i ref.png`, ~1 min per image, 1254x1254 at 1:1); Nano Banana / Seedream / Soul on Higgsfield after a quote | prompts in English | owner: no metered image cash on the ChatGPT subscription (a subscription is still a cost); Higgsfield image prices unresolved | text is added in post, never generated; Hebrew in images unproven |
| Multi-shot up to 30 s with role references | Seedance 2.5 (Higgsfield API/MCP, or Runway after a route quote) | 4-30 s; 480/720/1080; modes t2v / omni_reference / video_edit / video_extension | Higgsfield: tokens = ceil(H x W x (output s + input-video s) x 24 / 1024); USD = tokens/1000 x rate (0.0214 at 480/720, 0.0234 at 1080); reference-to-video route WITH video input x0.6; 1280x720 10 s no input = USD 4.6224 before discount; Runway 720p 10 s = 300 credits = USD 3.00, minimum 80 credits | image/audio refs excluded from the token meter; input video counts; do not reuse a 2.0 payload (flags differ); V02 confirmed, V03 corrected |
| Short shot from an approved plate | Runway Gen4.5 (API) / Gen4 Turbo draft | web 2-10 s, 720p, 24/25 fps | Gen4.5 12 credits/s (USD 0.12/s); Turbo 5 credits/s; ProRes/PNG +5 credits/s only where eligible | positive-only prompting; V07 confirmed, V08 corrected |
| Native dialogue/ambient sound, bounded scene | Veo 3.1 Fast (Gemini API) | 4/6/8 s; 1080p and 4K = 8 s only | Fast 720p 0.10/s, 1080p 0.12/s, 4K 0.30/s; 8 s 720p audio = USD 0.80 (Runway 1.20) | English fully evaluated, Hebrew unvalidated; match route and audio flag before comparing; V09, V10 |
| Lowest documented Veo draft meter | Veo 3.1 Lite (Gemini API) | 4/6/8 s; 720/1080 | 0.05/s (720p), 0.08/s (1080p) | a Flow request may create several charged generations |
| Several references, 10 s audiovisual | MiniMax H3 (direct) | 4-15 s; 768 base | (output s + ref-video s) x 0.08 + max(0, images-5) x 0.04; example 14 x 0.08 + 2 x 0.04 = USD 1.20 | 11 stable languages, no Hebrew; V21 |
| Explicit start/end staging | Kling 3.0 std/pro/4K | MCP 3-15 s; std/pro vs 4K | std undiscounted floor USD 0.084/s needs a matched sound quote; the 45 % promotion ended 2026-10-01 - do not use it | direct Kling price/terms unverified (V36) |
| Transfer a source performance | Genjutsu v1.0 (Higgsfield) | 1-30 s | ceil(input s) x 0.318 / 0.681 / 1.632 (480/720/1080); 8.2 s at 720p = USD 6.129 undiscounted | contact/actions may not transfer; consent + retained source |
| HDR/VFX plate with keyframes | Luma Ray 3.2 | 5/10 s; HDR generation 5 s only | 720p SDR 5 s 0.30, 10 s 0.90 (not 2 x 5 s) | a format label is not colour management |
| UGC / unboxing / ad structure reuse | Higgsfield Marketing Studio / Ad Multiplier | 12-15 s / 4-30 s | workflow credits unknown | product correctness, disclosure, lip-sync need review |
| Local generation on the reference machine | none as a production default | - | E10: Wan2.1 1.3B ~669 s per output second, 18.4 GB RAM, GPU VAE crashed twice | `route_gate.py`; the alternative is a shorter shot or a hosted quote |

Ids exist per provider and change monthly: `nano_banana_2` is associated with Pro in one catalogue and with a "flash" id in another - resolve the exact id before budgeting; a catalogue listing is not entitlement (public API, CLI, MCP and web catalogues differ). Model recommendations are vendor defaults until an outcome benchmark supports them.

## 3. Exclusions and routing hazards (dated)
- Direct Sora 2/Pro API: official removal notice for 2026-09-24 has passed; do not route NEW work to it (endpoint shutdown was not tested; stale guides still list it).
- The legacy Gemini 2.5 Flash Image identifier was scheduled for retirement on 2026-10-02: do not teach it as durable.
- Open weights are not unconditional: HunyuanVideo 1.5 excludes the EU, UK and South Korea including outputs; LTX 2.x licence (dated 2026-08-11) needs a commercial licence at >= USD 10 M revenue; CogVideoX licences differ per checkpoint. Check the checkpoint licence per client delivery.
- Promotions (Kling, Dreamina) expire: never price with a promotion that has ended.
- Real faces: in an owner project Seedance 2.0 reference-to-video failed or was flagged NSFW 7 of 7 times on real faces (8 of 8 with a follow-up), MiniMax worked (<= 15 s) `[PROVEN-internal]`, 2026-09. Model behaviour changes monthly: test ONE take before a batch; prefer synthetic characters.
- Privacy per route, not per brand: Higgsfield API terms (2026-09-02, §7.2) allow training on content unless the workspace opts out (effective within 10 business days, prospective only); BFL non-EU hosted terms (revised 2026-08-04) permit training on inputs and outputs; the OpenAI Images API does not train but keeps 30-day abuse retention; Google paid vs unpaid differ. Do not send confidential client references to a route whose terms you have not read.
- Hebrew: no model is shown to render Hebrew text, speak Hebrew with controllable quality, or lip-sync Hebrew; use a recorded/licensed VO and overlay text in post (decision default Q16: no spend authorised for those tests).

## 4. Cost framing the plan may use (arithmetic, not a forecast)
First-pass generation arithmetic across five reference briefs (talking-head 45 s, ad 20 s, motion launch 30 s, AI film 30 s, testimonial 60 s) at three tiers gives USD 0 to 15.28 (the AI-film pro tier: 6 x 5 s Seedance reference shots + 6 stills = 15.276576). It assumes exactly one billable output per planned call, excludes failed jobs, retries, review and acceptance, and is not accepted-output cost; time to accepted output is unmeasured. Plan 2-3 takes per shot and ask `paid-spend-gate` for the dated estimate; "free" only ever means "no metered API cash". (src: distilled/05 credits-and-cost §3; E07)

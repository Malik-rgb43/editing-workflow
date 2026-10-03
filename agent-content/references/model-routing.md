---
module: model-routing
checked_at: 2026-10-02
expires: "14 days for price rows, 30 days for catalogue rows (2026-10-16 / 2026-11-01), or before any spend, whichever is first"
confidence: "mixed; every row carries its own tag; no generation was ever run"
refresh: "read-only: official price/terms pages, models_explore listing, show_plans_and_credits balance view; never a generation"
---

# Model routing (AI generation) — dated reference

| Field | Value |
|---|---|
| Fact set | video and image generation candidates, routes, price formulas, exclusions, open-weight licence gates, local feasibility |
| Versions / ids | Seedance 2.5, Genjutsu v1.0, Kling 3.0, Veo 3.1 (Standard/Fast/Lite), Runway Gen4.5 / Gen4 Turbo, Luma Ray 3.2, MiniMax H3, Cinema Studio 4.0, LTX 2.5, Hunyuan 1.5, Wan 2.x. Exact provider ids are recorded per job (see section 1) — where a row says "record at quote time" the research did not capture a verified id |
| `checked_at` | **2026-10-02** (= the research date; vendor pages were read 2026-10-01 Asia/Jerusalem; **no live re-check since**) — this module **must be refreshed before use** |
| Source | `distilled/05-ai-generation-media-cost/models-and-routing.md` (T05 table, verdicts V01-V37), `credits-and-cost.md`; blueprint `MODEL_ROUTING.md` |
| Scope / plan / region | USD before tax/FX/promotion; list price of the named route on 2026-10-01; Israeli eligibility, VAT, plan allotment **not checked** |
| Confidence | prices and formulas with a V-id are `[VERIFIED-external]`; the rest `[SOURCED-unverified]`; every "suitability" statement is a test candidate, **not a measured winner** |
| `expires` | 14 days (price rows) / 30 days (catalogue rows) after `checked_at`, or earlier on any provider announcement; `paid-generation-gate` must refuse a spend that depends on an expired row |
| Non-spending refresh | open each provider's official price page and terms page in a browser; read the catalogue with `models_explore` (it returns **no prices**); read the balance and plan view; compare to the rows below; write the new `checked_at` per row. Never run a "test generation" to refresh |

**Hard limits of this module.** No generation, latency, quality, identity, lip-sync, Hebrew or acceptance-rate measurement exists. Nothing here ranks models. A catalogue listing is not entitlement: the public API, CLI, MCP and web catalogues differ. (decision default Q3: **no Higgsfield plan-price promises**; the web-plan rates and unlimited fair-use rules were unresolved on 2026-10-01.)

## 1. What to record for every job (a model name is not a spec)
provider · exact model id · route (API / MCP / CLI / web / Flow / aggregator) · mode · dimensions · duration · fps requested **and** received · reference durations · audio on/off · output format · plan · wallet (credits vs API dollars — never mixed) · price timestamp · quote · `ffprobe` of the output and its hash after an authorised generation. `[VERIFIED-external]` (src: distilled 05 models-and-routing §0, T05 FINDINGS)

## 2. Routing table — test candidates (observed 2026-10-01)
Costs exclude tax, FX, retries, editing, storage and subscription allocation. `[SOURCED-unverified]` for the whole table unless a row says otherwise.

| ID | Shot / intent | Primary candidate | Fallback | Settings and cost example | Pitfalls / limits |
|---|---|---|---|---|---|
| MR-01 | short shot from an approved reference plate | Runway Gen4.5 API | Gen4 Turbo draft | 5 s 720p; 12 credits/s × 5 × $0.01 = **$0.60**; ProRes/PNG +5 credits/s (Gen4.5 / Aleph 2 only) | positive-only prompting (negative phrasing unsupported on Gen4); do not demand appearance already fixed by the image; no identity score exists |
| MR-02 | native dialogue/ambient, bounded scene | Gemini API Veo 3.1 Fast | Veo 3.1 Standard when reference/extension controls are needed | valid 8 s 720p with audio: Gemini **$0.80**; Runway **$1.20** (compare matched route + audio only) | English is the evaluated language; **Hebrew unvalidated**; 1080p and 4K are 8 s only |
| MR-03 | cheapest documented Veo draft meter | Veo 3.1 Lite (API) | Flow Lite inside an existing plan | 8 s 720p API **$0.40**; Flow 10 credits (non-Ultra) / 5 (Ultra) is a different unit | one Flow request can create several charged generations; free/low-priority access is no SLA |
| MR-04 | 10 s audiovisual scene with several references | MiniMax H3 direct | Seedance 2.5 on a matched route | 768 p, 10 s out + 4 s ref video + 7 images = 14 × $0.08 + 2 × $0.04 = **$1.20** | first 5 images free; 11 stable languages **without Hebrew** |
| MR-05 | multi-shot sequence up to 30 s with exact role references | Seedance 2.5 (Higgsfield or Runway after a route quote) | split approved stills into short Gen4.5 / Veo shots | HF 1280×720 10 s no input video **$4.6224**; Runway same 720p 10 s = 300 credits = **$3.00**; with 4 s input on the HF reference-to-video route **$3.882816** (×0.6) | input video is part of the token meter; image/audio references are not; promos are separate |
| MR-06 | transfer a source performance / camera timing | Genjutsu v1.0 (Higgsfield) | a Kling motion-control route after a quote | 8.2 s reference at 720p: ceil(8.2)=9 × $0.681 = **$6.129** (undiscounted) | contact/actions may not transfer faithfully; needs consent and the retained source |
| MR-07 | explicit start/end staging | Kling 3.0 | a Veo 3.1 endpoint | MCP 3-15 s; choose std/pro/4K and sound explicitly; std undiscounted floor $0.084/s needs a matched sound quote | duration prose is inconsistent (`[CONFLICT]`: 1/3/15 vs 3-15); direct Kling availability and price unverified |
| MR-08 | HDR/VFX plate with keyframe anchors | Luma Ray 3.2 (Agents API) | SDR Gen4.5 + separate finishing | SDR 720p 5 s **$0.30**, 10 s **$0.90** (not two 5 s jobs); HDR 5 s 720p $0.60 | HDR generation is 5 s only; a format label is not colour management |
| MR-09 | reuse an ad structure with a changed product/actor | Higgsfield Ad Multiplier | rebuild shots individually | 4-30 s Seedance 2.5 workflow; workflow quote unresolved | preservation of cuts/audio/text is vendor intent — compare frame by frame |
| MR-10 | UGC / tutorial / unboxing | Higgsfield Marketing Studio | reference-led Seedance 2.5 + edited VO | 12-15 s; 480/720/1080; credits unknown | hook/setting cannot combine with an ad reference; product correctness, disclosure and lip-sync need review |
| MR-11 | Hebrew voice replacement | existing licensed VO + a lip-sync candidate (SyncLipsync3) | VO over cutaways where the mouth is hidden | price unknown | default `bounce` reverses gestures — set `loop`/`cut_off`/`silence`/`remap` explicitly; **no Hebrew WER or lip-sync benchmark** |
| MR-12 | stills for identity / product / location references | GPT Image 2.x via the Codex CLI (reference toolchain, free on the ChatGPT subscription) | Nano Banana / Seedream / Soul on Higgsfield after a quote | ~1 min per image `[PROVEN-internal]` | **text is added in post, never generated; Hebrew needs tests** `[RULE-owner]` |
| MR-13 | Apple local audio-video experiment | LTX Desktop 2.5 Fast after the hardware and licence gate | hosted approved plan | needs ≥ 15 GB **free** RAM (16 GB total is not enough) | gated weights; 2.5 local has no Retake/Extend |
| MR-14 | local generation on the reference machine `[LOCAL-only]` | **no production default** | hosted quote or a separately approved lab probe | `[MEASURED-lab]` E10: Wan2.1 1.3B, 512², 33 frames @16 fps = **~669 s per output second** (~11 min), 18.4 GB RAM, GPU VAE crashed twice | one machine, one pass; do not promise free local generative video |

Decision rules `[RULE-owner]` + `[SOURCED-unverified]`: **prompt first, then spend** (frame-level PROMPT.md approved; every paid action passes the gate; an explicit "generate" is approval within the balance and never covers on-screen facts or client approval of factual stills) · image-first, then animate · shortest viable shot; trim each generation to its clean 1.2-2.5 s window · ETA > 30 min per shot → propose 2.5D / animatic (see `three-d-routes.md`) · text, Hebrew text and Hebrew speech are added or validated outside generation · run ONE sample before a batch · a "best/ranked" claim without a reproducible measured test is discarded.

## 3. Dated price rows (USD before tax/FX; observed 2026-10-01)
Do not mix a direct vendor rate and an aggregator rate in one job. Every row below expires with the module.

| ID | Route (exact id: record at quote time unless shown) | Formula / rate | Plan / scope | Tag / V-id |
|---|---|---|---|---|
| PR-01 | Higgsfield Seedance 2.5 (API/MCP) | tokens = ceil(H × W × (out_s + input_video_s) × 24 / 1024); USD = tokens/1000 × **0.0214** (480/720) or **0.0234** (1080); reference-to-video route **with** video input ×0.6 (0.01284 / 0.01404) | 24 is a billing constant, not an fps; image/audio refs excluded; 4-30 s; token rounding applies | `[VERIFIED-external]` V02, V03 (corrected) |
| PR-02 | Higgsfield Genjutsu v1.0 | ceil(input_s) × 0.318 / 0.681 / 1.632 (480/720/1080) | 50% launch promo is separate | `[VERIFIED-external]` V06 |
| PR-03 | Runway-routed Seedance 2.5 | $0.01 × max(80, out_s × 20/30/68 + in_video_s × 10/15/34) | minimum 80 credits = $0.80; 30 s combined input clause (coupling unverified) | V04 `[VERIFIED-external]`; V05 `[SOURCED-unverified]` |
| PR-04 | Runway API Gen4.5 / Gen4 Turbo / Act Two / `gen4_image` | $0.01 per credit: Gen4.5 12 credits/s; Turbo 5; Act Two 5; `gen4_image` 720p 5 credits per image | API, not web allowance; ProRes/PNG +5 credits/s (Gen4.5, Aleph 2 only) | V07, V08 (corrected) `[VERIFIED-external]` |
| PR-05 | Gemini API Veo 3.1 (e.g. `veo-3.1-generate-preview`) | Standard 720/1080 $0.40/s, 4K $0.60; Fast $0.10 / $0.12 / $0.30; Lite $0.05 / $0.08 (no 4K) | audio always on; no API free tier; 4/6/8 s; 1080p/4K = 8 s only | V09, V11 `[VERIFIED-external]` |
| PR-07 | Runway-routed Veo 3.1 | Standard $0.40 audio / $0.20 silent per s; Fast $0.15 / $0.10 | provider charge, not Google's | `[SOURCED-unverified]` |
| PR-08 | Luma Ray 3.2 (Agents API) | SDR 720p 5 s 0.30 / 10 s 0.90; 1080p 1.20 / 3.60; HDR 5 s 720 0.60 / 1080 2.40; HDR+EXR 0.90 / 3.60; extend 5 s 720p 0.30; reframe 720p 0.12/s | non-linear; `budget_exhausted` can partially bill | V18-V20 `[VERIFIED-external]` |
| PR-09 | MiniMax H3 direct | (out_s + ref_video_s) × 0.08 (768) or 0.13 (2K) + max(0, images − 5) × 0.04; audio refs free | H3 Max has its own rates (0.05/0.08 per s, ref video 0.0553/0.143, images beyond 2 at 0.074) | V21-V23 `[VERIFIED-external]` |
| PR-10 | Google Flow (web credits) | per **generation**: Lite 10 (non-Ultra) / 5 (Ultra); Fast 20 / 10; Quality 100 | credits are not API dollars; extension docs conflict (V13) | V12 `[VERIFIED-external]`; `[CONFLICT]` V13 |
| PR-11 | Pika API Club / Create | API $10/month + 720p $0.04/s (1080p `[CONFLICT]` 0.06 vs 0.09/s); Create top-ups at credits actually received per USD | a top-up does not create commercial rights | V14-V17 |
| PR-12 | Kling 3.0 std (Higgsfield) | list $0.084/s; 45% promo ($0.0462) **expired 2026-10-01** | needs a matched sound/config quote | `[SOURCED-unverified]`; direct Kling unverifiable (V36) |
| PR-13 | Dreamina Seedance 2.5 promo | US Basic $1.50 first month; effective 720p about $0.035/s during **2026-09-23 to 2026-10-09 UTC+8** | not pay-as-you-go, not renewal, not all regions | `[SOURCED-unverified]`; never quote to a client |
| PR-14 | Replicate / local | Replicate: billed runtime × hardware price or model output meter (private instances can bill setup/idle); local: energy + hardware allocation + labour + licence | no measured local runtime/energy | V24 `[VERIFIED-external]` / `[IDEA]` |

## 4. Exclusions and expiry list (re-confirm at refresh)
- **Direct Sora 2 / Pro API:** OpenAI published removal for **2026-09-24** (past). Do not route new direct work. The research did **not** test the endpoint shutdown; stale guides and aggregators still list it. `[SOURCED-unverified]` V01 qualified. (src: https://developers.openai.com/api/docs/deprecations)
- Legacy Gemini 2.5 Flash Image identifier scheduled for retirement **2026-10-02**; Kling 2.1 / 2.1 Master reported removed March 2026 (community skill). `[SOURCED-unverified]`
- Promotional prices expire: Kling 45% off ended 2026-10-01; Dreamina window ends 2026-10-09. Use list price after expiry.
- The April-2026 community skill's star rankings, frozen credit tables, "instant failure proves the safety filter" and blanket MP3-only/lip-sync claims are **dropped**; keep only reference-first storyboards, identity sheets, explicit camera/action roles, shot-level QA. T05 wins on facts.

## 5. Open-weight and local models — gates before any client delivery
Open weights are not free of conditions. Gate: exact **checkpoint** licence (never the runtime's), territory/revenue/non-commercial terms, VRAM/RAM measured **on the target machine**, time per output second measured.

| Model | Condition recorded 2026-10-01 | Tag |
|---|---|---|
| LTX 2.5 (licence dated 2026-08-11; covers 2.5 releases since then) | businesses at or above **USD 10 M** annual revenue (affiliates aggregated) need a commercial licence; narrow noncommercial testing/R&D exception; 2.3 checkpoint licence separate | `[SOURCED-unverified]` V25 qualified |
| HunyuanVideo 1.5 | territory **excludes EU, UK, South Korea including use of outputs**; >100 M MAU separate; min 14 GB with offload | `[VERIFIED-external]` V26 |
| CogVideoX | 2B Apache exception; other checkpoints need registration and extra permission above 1 M monthly visits | `[VERIFIED-external]` V27 |
| Wan 2.2 / 2.1 | repo Apache-2.0; inspect each checkpoint; hosted Wan 2.6/2.7/3.0 are not proof of public weights | `[SOURCED-unverified]` |
| Depth Anything V2 | Small Apache-2.0; Base/Large/Giant **CC-BY-NC 4.0** (see `licences-bom-rules.md`) | `[SOURCED-unverified]` |
| SDXL-Turbo | Stability AI Community License (2024-07-05): registration + revenue conditions (~US$1 M, organisation revenue); owner eligibility unresolved | `[VERIFIED-external]` |

Hardware facts: official LTX Desktop local on Windows/Linux needs **CUDA ≥ 16 GB VRAM** (the reference machine's config is API-only); Apple needs ≥ 15 GB free RAM; Wan2.1 1.3B vendor example 8.19 GB for 5 s at 480p on an RTX 4090 (not an AMD measurement). ComfyUI/ROCm support is a framework precondition, not proof for an one reference machine. `[VERIFIED-external]` V28-V31 (vendor figures).

## 6. Hebrew
No video, image, voice or lip-sync model is shown to handle Hebrew (V33: language lists do not prove it). Hebrew text is typeset deterministically in a licensed font; Hebrew speech is a recorded or licensed VO; a lip-sync model is tested on ONE take first. TTS availability lists (Eleven v3/v4 list Hebrew, Multilingual v2/Flash v2.5 do not; Azure `he-IL-HilaNeural`/`AvriNeural`; Google `he-IL` Chirp 3 HD; OpenAI TTS lists Hebrew but is English-optimised) are availability only, **never listened to**. `[VERIFIED-external]` for the lists; quality unmeasured.

## 7. Privacy and terms that decide a route
Higgsfield API terms (updated 2026-09-02, §7.2): content may be used for service/model improvement **unless the workspace opt-out is set** (effective within 10 business days, prospective only); partner models have their own policies. Output ownership is not confidentiality, clearance or exclusivity. Check this before any client footage goes to a hosted route. See `docs/en/legal-guide.md#privacy-footage`. `[VERIFIED-external]` (src: https://open.higgsfield.ai/terms-of-service)

## 8. Open conflicts carried here
`[CONFLICT]` Cinema Studio 4.0 API 720p vs CLI 1080p (V34) · Flow extension docs (V13) · Pika 1080 price · Seedance 2.0 audio flag (do not reuse a 2.5 payload) · Kling duration prose · owner "no AI upscale / natural grade" vs vendor upscale catalogue (**owner wins on taste**: no AI upscale on AI-generated footage unless asked) · owner Seedance prefixes (cinematic vs phone-style UGC) vs vendor "positive only" guidance → ship both as named presets (decision default Q7).

## 9. Refresh checklist (non-spending)
1. For each PR-row open the official price page; copy unit, plan, date. 2. Re-read the exclusions list. 3. Re-run `models_explore` listing (no prices) and note added/removed models. 4. Re-read Higgsfield API terms §7.2. 5. Update `checked_at` per row and the header. 6. If a number moved >10%, say so in the changelog. 7. Never "prove" a row by generating.

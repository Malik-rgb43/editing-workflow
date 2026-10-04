---
module: platform-specs
checked_at: 2026-10-02
expires: "180 days (2027-03-31) for specs; AI-disclosure rows 90 days (2026-12-31) — platform UI wording changes quickly"
confidence: "documentary only: no export was ever uploaded, no device viewport measured, no paid ad preview seen, no Hebrew caption position proven on a real phone"
refresh: "read-only: open each official help page (URLs below), compare, and run the device-overlay exercise in section 7 on your own phone; never upload a test video to a client account"
---

# Platform specs, delivery presets and AI-disclosure — dated reference

| Field | Value |
|---|---|
| Fact set | house export preset v1; house safe zones v1; documentary per-platform limits; AI-disclosure per route; music-rights scope per placement; documented ranking signals |
| Versions / ids | C2PA specification 2.4 (April 2026; exact day unverified); YouTube field "AI use"; TikTok ads pages June-July 2026; Meta announcement 2025-06-17 |
| `checked_at` | **2026-10-02** (= research date; pages were read 2026-10-01; relative "updated N months ago" labels on some pages) — **must be refreshed before use** |
| Source | `distilled/08-…/platform-specs-and-ai-disclosure.md` (T17: 39 official sources, 24 read / 8 partial / 7 blocked, 13 re-checked); blueprint `PLATFORM_SPECS.md` |
| Scope / plan / region | per row: organic vs auction ad vs Spark vs Sponsored Content vs Media Studio vs Content Manager; global pages, no authenticated account, no region test |
| Confidence | mixed: `[VERIFIED-external]` only where marked; the rest `[SOURCED-unverified]` or an explicit **gap** |
| `expires` | see front matter; also expires on any announced policy change |
| Non-spending refresh | open the URLs in section 3; for gaps (marked **gap**) check yourself and write the date; perform the device overlay test (section 7); no uploads of unreleased client work |

**Keep three things apart** (and in three places): (a) the **house export preset** = the author's choice; (b) each platform's **documented maximum/recommendation** = dated, with source; (c) the **route** = organic, auction ad, Spark, Sponsored Content, API/web, Studio. One "limit map" per platform erases real boundaries: LinkedIn organic allows 60 fps while LinkedIn ads say "less than 30 FPS"; X web allows 16 GB while Media Studio allows 8 GB. A documentary maximum is **not** an acceptance guarantee; a recommended bitrate is not a rejection threshold. `[VERIFIED-external]`

## 1. House delivery preset v1 `[RULE-owner]` (decision default Q5: a named preset, not a platform law)
| Aspect | Canvas | Use |
|---|---|---|
| 9:16 | 1080×1920 | Reels, TikTok, Shorts, Stories |
| 4:5 | 1080×1350 | feed |
| 1:1 | 1080×1080 | feed, carousel |
| 16:9 | 1920×1080 | YouTube, web |

H.264, SDR, yuv420p, AAC 48 kHz 320 k. **30 fps** default; AI-generated video keeps the generation's native fps; 60 only when the source is truly 60 (a 60 fps source shown at 30 is rendered at 30). Social renders use `--sdr` (an HDR source such as an iPhone or generated clip otherwise exports HEVC 10-bit and platform colours wash out) `[PROVEN-internal]`. Master loudness **−14 LUFS integrated, true peak ≤ −1 dBTP** (mix intermediate −1.5), always **measured on the final file** — see `audio-mix.md`. Each ratio is designed separately, never a blind crop. Finals folder = finals + `manifest.json` (which source hash each file was rendered from). Naming: `<name>_9x16.mp4`, `_4x5`, `_1x1`, `_16x9`; hook variants `<name>_<platform>_hookA_9x16.mp4`.

Width-1080 encoder trap `[PROVEN-internal]`, `[LOCAL-only: HyperFrames 0.8.x on Windows]`: the encoder blackened the last 8 columns (x 1072-1079) of 1080-wide renders; the author authors the root at **1088** with `data-deliver-width="1080"` and crops. **Not re-tested on 0.8.98 — re-verify per version** (see `hyperframes-traps.md`).

## 2. House safe zones v1 `[RULE-owner]`, per-platform inputs `[SOURCED-unverified]`
**Teach as a conservative union validated only by the author's own deliveries; the overlay exercise (section 7) is how a student proves or corrects it.**

| Ratio / canvas | Key text, CTA, logo, price, number must stay inside | Caption rail |
|---|---|---|
| 9:16, 1080×1920 | **top 300 · bottom 672 (so y ≤ 1248) · left 140 · right 192** | may sit lower, **bottom edge never below y = 1450**; sides as key text |
| 16:9, 1920×1080 | x ≤ 1824 (right margin 96); bottom 162; top 54; left 96 | — (a stricter limit for one project is a project choice written in its `DESIGN.md`) |
| 4:5 and 1:1 | 54 px each side | — |

Owner's per-platform inputs behind the 9:16 union (px margins, "checked 2026-09" by the author; **research could not verify any video safe-zone rectangle**): Meta Reels/Stories/feed top 270 / bottom 672 / sides 65; TikTok In-Feed top 150 / bottom 480 / left 60 / right 140; YouTube Shorts top 288 / bottom 672 / left 48 / right 192. A Meta 9:16 ad shown in feed is cropped to 4:5 (285 px top and bottom), hence logo bug top 300. Hebrew-audience TikTok: keep **140 px on both sides** (the author's rule; research: TikTok's RTL template is for Arabic-region only, Hebrew text alone does not select it — `[CONFLICT]`, resolved conservatively, to be settled by a Hebrew-UI device screenshot `[IDEA]`).

Recorded tensions (do not hide them): the caption-rail exception lets captions sit inside the documented Meta/Shorts bottom exclusion (owner decision, never device-validated); the master over-protects TikTok (its own bottom figure is 480). Required evidence row for any future numeric claim: platform, organic/paid, placement, app version, OS, physical viewport, video raster, caption lines, CTA, LTR/Arabic-RTL region, template date, normalised rectangle, screenshot date. A generated overlay is **proposed** until checked on that exact viewport. Check with `hyperframes snapshot --at <hook>,<offer>,<endcard> --describe false` (≤ 5 timestamps per call) and `caption_qa --band <top>:1450`.

## 3. Documentary specifications (read 2026-10-01; confidence per row)
| Route | Documented specification | Captions / covers | Source (T17 id) | Tag |
|---|---|---|---|---|
| YouTube video | MP4, H.264, progressive; keep source fps; SDR recommended **1080p 8 Mbps at 24/25/30 fps, 12 Mbps at 48/50/60**; audio 48 kHz; default upload limit 15 min (verified accounts longer); max **256 GB or 12 h** whichever is less | native subtitle file; custom thumbnail for verified accounts (3840×2160 recommended) | S001, S005, S006, S007 — https://support.google.com/youtube/answer/1722171 | `[SOURCED-unverified]`; thumbnail `[VERIFIED-external]` |
| YouTube Shorts | square or vertical, **≤ 3 min** (rule from 2024-10-15 standard channels, 2025-12-08 Official Artist Channels); desktop custom thumbnails for verified accounts 2160×3840, 50 MB | do not read mobile thumbnail limits as mobile custom-cover support | S002, S003, S007 — https://support.google.com/youtube/answer/15424877 | `[VERIFIED-external]` |
| TikTok organic | duration, codec, fps maximum, native captions, covers: **gap** | **gap** | S037, S039 (blocked) | gap — do not import ad limits |
| TikTok auction (non-Spark) | 9:16 ≥ 540×960; 16:9 ≥ 960×540; 1:1 ≥ 640×640; **≤ 10 min; ≤ 500 MB; ≥ 516 kbps**; mp4/mov/mpeg/3gp/avi | ad caption typography fixed | S013 — https://ads.tiktok.com/help/article/tiktok-auction-in-feed-ads (June 2026) | `[VERIFIED-external]` |
| TikTok Spark | mp4/mov; no duration restriction stated; caption from the organic post (up to 4 lines) | caption lines affect safe zone | S013 | `[VERIFIED-external]` |
| Facebook organic / Reels | Meta (2025-06-17) announced unified video-to-Reels publishing and removal of length/format limits, rolled out gradually | unresolved | S025 — https://about.fb.com/news/2025/06/making-it-easier-create-videos-facebook/ | `[SOURCED-unverified]` (announcement ≠ account behaviour) |
| Instagram Reels organic | current numeric limits **not verified** (help page returned HTTP 429) | unresolved | S030 | gap |
| Instagram/Facebook Reels ads | 9:16 recommended; use audio; respect the safe zone; Meta's checker | numeric limits unresolved | S029, S032 | `[SOURCED-unverified]` |
| Instagram/Facebook Stories | duration/encoder unresolved; **no universal "60 s" claim** | unresolved | S031 | gap |
| LinkedIn organic | 256×144 – 4096×2304; **10–60 fps**; 192 Kbps – 30 Mbps; ≤ 5 GB; ≤ 15 min; ratio 1:2.4 – 2.4:1; min length 3 s desktop / 2 s mobile | caption file / auto caption with review; custom thumbnail | S021 — https://www.linkedin.com/help/linkedin/answer/a7494039 | `[SOURCED-unverified]` (page "updated 1 year ago") |
| LinkedIn Sponsored Content | MP4; H.264 or VP8; 3 s – 30 min; 75 KB – 500 MB; page says literally "**less than 30 FPS**" (do not rewrite as ≤ 30); 9:16 max 1080×1920; in-stream ≤ 90 s | plain **SRT** only; thumbnail JPG/PNG ≤ 2 MB | S022 — https://www.linkedin.com/help/linkedin/answer/a424737 | `[VERIFIED-external]` (literal wording); `[CONFLICT]` with the 30 fps house default for LinkedIn **ads** only |
| X (web) | non-Premium ≤ 140 s / 512 MB; Premium page says < 4 h / 16 GB (and also "> 2 h–< 4 h at 720p": ambiguous — never promise 4 h at 1080p) | n/a | S023 — https://help.x.com/en/using-x/x-videos | `[VERIFIED-external]` (ambiguity) |
| X Media Studio | MP4/MOV; H.264; AAC-LC; 5–8 Mbps recommended; ≤ 60 fps; 8 GB; ~3 h; > 2 h → 720p | CEA-608/708 or SRT | S024 — https://help.x.com/en/using-twitter/media-studio-faqs.html | `[SOURCED-unverified]` |

Native vs burned captions: native = separate timed text (switchable, translatable, accessible); burned = rasterised (fixes typography/RTL, cannot be switched off). Native routes documented: YouTube, LinkedIn organic and Sponsored (SRT), X Media Studio. **TikTok and Meta native-caption routes unresolved.** Keep a clean master + a styled caption master where requested; avoid duplicate native + burned captions; verify Hebrew with mixed numbers/Latin on the real surface. `[IDEA]`

## 4. AI-content disclosure per route (checked 2026-10-01; re-check at publish time)
AI disclosure, rights/likeness, content eligibility and provenance are **four separate checks**; a labelled or C2PA-signed asset is not automatically legal, recommended or monetisable. `[VERIFIED-external]`

| Destination | What to disclose | Notes | Source | Tag |
|---|---|---|---|---|
| YouTube | meaningful AI generation/alteration of photorealistic people, events, places; field now **Studio → Attributes → "AI use"** (older "Altered content" wording is stale — date-stamp course steps) | exempt: minor aesthetic edits, caption creation, repair; **AI-generated music is an explicit example**; labels can also follow C2PA/internal detection and then cannot be adjusted; disclosure does not itself limit reach or earning | S004 — https://support.google.com/youtube/answer/14328491 | `[VERIFIED-external]` |
| Meta organic | photorealistic video or realistic-sounding audio created/altered digitally | 2026-06-01 update keeps the disclosure-tool requirement; labels may follow industry signals | S026 — https://about.fb.com/news/2026/02/meta-prepares-for-2026-us-midterms/amp/ | `[SOURCED-unverified]` |
| Meta ads | "About this ad" detects third-party AI; certain political/social creatives need self-disclosure | not evidence that every commercial AI ad has the same toggle | S026 | `[SOURCED-unverified]` |
| TikTok organic | realistic AI image/audio/video; creator label available; auto labels cannot be removed | a label never permits prohibited or misleading content | S016 — https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content | `[SOURCED-unverified]` (fresh fetch unreadable) |
| TikTok non-Spark ads | mandatory **AI-disclaimer toggle** for fully/significantly AI content; **duplicating a campaign resets it**; Spark follows organic | pages dated Sept 2025 → revalidate | S017, S018 | `[SOURCED-unverified]` |
| TikTok ad policy | deceptive claims prohibited; a disclaimer does not cure deception | Aug 2025 page | S020 | `[SOURCED-unverified]` |
| EU (law, not platform) | provider machine-readable marking and **deployer** visible/audible deepfake disclosure are different duties; general Art. 50 application reported as 2 Aug 2026; the December-2026 grace for older systems — **amending instrument not verified**, timing "not verified" | publish no deadline rule without an EU lawyer; see `docs/en/legal-guide.md#disclosure` | T18-S003/S004/S024 — https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act | `[SOURCED-unverified]` for dates |

C2PA 2.4 (April 2026): signed provenance helps validate history and association; provenance can be incomplete or removed; it does **not** prove an event happened; missing credentials are not evidence of falsehood; **never strip metadata to evade labelling**. Support in a given NLE/exporter/platform must be checked separately; no signing or round-trip was tested. `[VERIFIED-external]` (https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html). The skill that edits AI-generated work records a `DISCLOSURE` line per platform route in BRIEF.md.

## 5. Music rights are placement- and territory-specific
TikTok **Commercial Music Library** = TikTok organic + paid only (campaign region + eligible placement) — **no licence for YouTube/Meta/X** `[VERIFIED-external]` (https://ads.tiktok.com/resources/help/article/how-to-use-the-commercial-music-library, July 2026). YouTube Audio Library = YouTube-scoped, attribution required for applicable CC tracks `[VERIFIED-external]`. Meta commercial-music/boost rights **not inspected (login-gated): gap**. YouTube Shorts > 1 min with active Content-ID claims are blocked per both current official pages (a search snippet claiming a 2026-09-24 change was not confirmed) — make no rights promise. House rules: `License: unknown` = **do not use in client work** (decision default Q2; "organic only" is a risk posture for one's own account, not a licence); third-party brand sounds/logos = organic only, ask written brand permission for ads. Per-asset rights record: id, licensor, dated terms, territory, platform, organic/paid, sublicense scope, attribution, term, evidence file.

## 6. What the platforms document as ranking signals
YouTube Shorts: viewer's choice to view, average duration/percentage viewed, likes, satisfaction surveys (no minimum cadence). YouTube long: duration and percentage viewed, satisfaction, history. TikTok: the only primary text is **2020** (finishing a longer video, interactions, content/device signals) — not 2026 weights. Meta 2026: original content, deeper engagement, longer watch time; June 2025: all lengths remain relevant. **No source verifies a universal 3-second hook, a fixed retention number or a posting cadence** `[VERIFIED-external]` (negative finding). Creator-reported numbers (e.g. "retention ≥ 90%", "optimal 34 s") are folklore-grade: teach as taste, flag as anecdote. A hook that works without sound is good editorial practice, not ranking law.

## 7. Verify-yourself exercises (the research's own gaps)
1. **Device overlay test** `[IDEA]`: render a 1080×1920 test card with the house zones drawn; post it **privately/unlisted** on your own account on a real phone; screenshot; record platform, app version, OS, viewport; adjust the numbers; date it. 2. Read Instagram organic specs on a logged-in device (help page returned 429). 3. Meta Reels/Stories numeric ad specs and music rights (login-gated). 4. TikTok organic upload length/codec/native captions/covers. 5. Hebrew caption position with real mixed Hebrew/Latin/numbers on each surface. 6. LinkedIn ads "less than 30 FPS" — confirm with the publisher before a 30 fps ad preset; consider a 25/24 fps source.

## 8. Failure table
| Symptom | Cause | Fix | Prevention |
|---|---|---|---|
| logo/CTA hidden under UI | single "universal" zone or raster size used | re-lay out inside the union; overlay snapshot | overlay at hook, offer, end-card |
| captions clipped at the bottom | rail below y 1450 | move up | `caption_qa --band <top>:1450` |
| duplicate captions | burned + native both delivered | one per route | clean master + caption master naming |
| washed colours after upload | HDR/HEVC 10-bit source | `--sdr` | always for social |
| file ~11 dB quiet | render attenuation (historical, not reproduced since) | mux the mix / loudnorm | measure the final file |
| right edge black strip | width-1080 encoder bug | 1088 + crop | edge-band check in delivery |
| "Altered content" in a lesson | rolling UI wording | read the current field | date-stamp each platform step |
| ad rejected / track claimed elsewhere | CML/Audio Library used out of scope; unknown licence | replace the track | per-asset rights record before the edit |
| "4 h 1080p on X" promised | ambiguous Premium wording | quote Media Studio / 720p > 2 h | treat as ambiguity |

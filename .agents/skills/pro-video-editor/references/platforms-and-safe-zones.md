# Platform safe zones (house preset, dated)

Merged on 2026-10-04 from the former type skills (one source per section, kept whole). Principles, not a template: use what fits the video in front of you and write the reason for each choice into PROMPT.md.


## ---
<!-- source: pro-video-editor/references/platforms-and-safe-zones.md -->
---
module: pro-video-editor-safe-zone-presets
checked_at: 2026-10-02
expires: "180 days (2027-03-31), or on any announced platform UI change, or when your own device overlay test contradicts a number"
confidence: "house preset v1: owner decisions over unverified, owner-cited platform numbers; NO video safe-zone rectangle was verified in the research"
---

### House safe-zone presets (dated; proposed until proven on a device)

Load when: laying out any element that carries text, price, CTA or logo; before saying a layout "passes". Machine-readable copy: `safe_zone_presets.json` (read by `scripts/safe_zone_check.py`). The canonical rows are in `agent-content/references/platform-specs.md` section 2 (owned elsewhere): if numbers differ, that file wins and this one is updated. Sources: blueprint PLATFORM_SPECS §3; distilled 08 platform-specs-and-ai-disclosure §4; distilled 02 workflow §10.2 (read 2026-10-01).

| Field | Value |
|---|---|
| Fact set | house safe zones v1 per aspect, platform inputs behind the 9:16 union |
| `checked_at` | 2026-10-02 (research date; sources read 2026-10-01) - **not a live re-check, no device test** |
| Scope | the author's own deliveries; Hebrew-audience margins; ads and organic mixed |
| Confidence | `[RULE-owner]` for the preset; `[SOURCED-unverified]` for each platform input; `[VERIFIED-external]` only for the finding that a video's raster size does not define the app viewport and that the numbers are viewport-specific |
| Decision default | Q5: taught as "house preset v1", not as platform law |
| Non-spending refresh | the device overlay exercise below; read the platform pages; never upload client work to test |

### 1. The preset (px margins from the canvas edge where no key text, logo, price, number or CTA may sit)
| Aspect (canvas) | Top | Bottom | Left | Right | Notes |
|---|---:|---:|---:|---:|---|
| 9:16 (1080x1920), union of the strictest | 300 | 672 (key text bottom edge y <= 1248) | 140 | 192 | **caption rail**: may sit lower than key text, its bottom edge never below y 1450; sides as key text |
| 16:9 (1920x1080) | 54 | 162 | 96 | 96 | x <= 1824; bottom enlarged for the progress bar, Skip and ad badge (in-stream); a stricter project limit goes in DESIGN.md |
| 4:5 (1080x1350) | 54 | 54 | 54 | 54 | the profile grid crops to 3:4: keep text and logo >= 54 px from the sides |
| 1:1 (1080x1080) | 54 | 54 | 54 | 54 | action-safe 5 % |
Platform inputs behind the 9:16 union (owner-cited, "checked 2026-09", unverified): Meta Reels/Stories/feed top 270 / bottom 672 / sides 65 (a 9:16 ad shown in feed is cropped to 4:5, 285 px top and bottom, hence logo bug at top 300); TikTok In-Feed top 150 / bottom 480 / left 60 / right 140 (varies with caption length and the CTA button; a separate Arabic-region RTL template exists and Hebrew text alone does not select it); YouTube Shorts top 288 / bottom 672 / left 48 / right 192. Hebrew-audience rule: keep 140 px on BOTH sides until a Hebrew-UI device screenshot settles it.
Authoring note: 1080-wide roots may be authored at 1088 with a crop back to 1080 (an encoder trap, local to one engine version; see `video-variants-exporter/references/house-presets.md`); measure element boxes on the 1080 area.

### 2. Recorded tensions (not hidden)
(1) The caption-rail exception lets captions sit inside the documented Meta/Shorts bottom exclusion: an owner decision on taste, never device-validated. (2) The master over-protects TikTok (its own bottom figure is 480). (3) Meta/Stories/Reels video pixel specs were login-blocked; no source gives a universal "top 250 / bottom 340": do not teach one. (4) Organic Reels/Stories/Shorts are different surfaces from ads.

### 3. Check procedure
1. List every element with text, price, CTA or logo at the hook, the offer and the end card (a DOM probe or the PROMPT.md px table gives the boxes).
2. `python scripts/safe_zone_check.py elements.json --aspect 9x16 --overlay-evidence _work/qa/snap_overlay.png --require cta,price` (exit 0 only with geometry inside AND an overlay file you have viewed).
3. Snapshot with the overlay drawn: `hyperframes snapshot --at <hook>,<offer>,<endcard> --describe false` (at most 5 timestamps per call; `--describe false` keeps frames on the machine), then LOOK at it.
4. Report `pass` only with both; geometry without a viewed overlay is `INSUFFICIENT_EVIDENCE`.

### 4. Device overlay exercise (the way to prove or correct the preset)
Render a 1080x1920 test card with the zones drawn and a grid; post it PRIVATELY or unlisted on your own account; screenshot it on a real phone in the Reels, TikTok and Shorts players (with a long caption, with a CTA button if you can preview an ad); record platform, app version, OS, viewport, caption lines, region/language UI (LTR vs RTL), date; adjust the numbers; write the date in this file. Never upload client work for this.

### 5. Required evidence row for any future numeric claim
platform; organic or paid; placement/add-on; app version; OS; physical viewport; video raster; caption lines; CTA; LTR or Arabic-RTL region; template URL and date; normalised rectangle and pixel conversion; screenshot date. A generated overlay is proposed until checked on that exact viewport.

---
module: video-variants-exporter-house-presets
checked_at: 2026-10-02
expires: "180 days (2027-03-31); earlier on any HyperFrames pin change or announced platform UI change"
confidence: "house decisions (owner) plus documentary platform inputs; no export was uploaded and no device viewport measured"
---

# House presets used by video-variants-exporter (dated copy)

Load when: quoting a canvas, safe zone, loudness or width-trap number for a variant, or when `manifest_check.py` reports M061-M064.

| Field | Value |
|---|---|
| Fact set | house export preset v1; house safe zones v1; loudness gate; width-1080 encoder trap |
| Versions / ids | decision default Q5 (named presets, not laws); HyperFrames 0.8.98 in the research (re-verify per version) |
| `checked_at` | 2026-10-02 (the research date; sources read 2026-10-01). Not a live re-check |
| Source | blueprint PLATFORM_SPECS §2-§4; `agent-content/references/platform-specs.md` (**canonical copy; if numbers differ, that file wins and this one is updated**); distilled 02 workflow §10.2-§10.5 |
| Scope | the author's own deliveries; per-platform inputs `[SOURCED-unverified]`; Hebrew-audience extra margins |
| Confidence | presets: owner decisions; platform rows: unverified; encoder trap: local to HyperFrames 0.8.x on Windows |
| `expires` | see front matter |
| Non-spending refresh | open the platform pages listed in `platform-specs.md`; run the device overlay exercise (render a test card with the zones, post it privately on your own account, screenshot, date it); never upload client work to test |

## 1. Canvases and encode
| Aspect | Canvas | Typical use |
|---|---|---|
| 9:16 | 1080x1920 | Reels, TikTok, Shorts, Stories |
| 4:5 | 1080x1350 | feed |
| 1:1 | 1080x1080 | feed, carousel |
| 16:9 | 1920x1080 | YouTube, web |

H.264, SDR (`--sdr` always for social; an HDR source otherwise exports HEVC 10-bit and colours wash out), yuv420p, AAC 48 kHz 320 k. 30 fps default; AI-generated video keeps the generation's native fps; 60 only when the source is truly 60. Each ratio is designed for itself; never a blind crop. (src: distilled 02 workflow §10.6, 2026-10-01)

## 2. Safe zones, house preset v1 (px margins from the canvas edge where no key text, logo, price or CTA may sit)
| Aspect | Top | Bottom | Left | Right | Notes |
|---|---:|---:|---:|---:|---|
| 9:16 (union of the strictest) | 300 | 672 (key text y <= 1248) | 140 | 192 | caption rail may sit lower but its bottom edge is never below y 1450; Hebrew-audience TikTok: keep 140 on BOTH sides |
| 16:9 | 54 | 162 | 96 | 96 | x <= 1824; a stricter limit for one project is written in its DESIGN.md |
| 4:5 | 54 | 54 | 54 | 54 | the profile grid crops to 3:4: keep text/logo >= 54 px from the sides |
| 1:1 | 54 | 54 | 54 | 54 | action-safe 5 % |

Owner's per-platform inputs behind the 9:16 union: Meta top 270 / bottom 672 / sides 65; TikTok In-Feed top 150 / bottom 480 / left 60 / right 140; YouTube Shorts top 288 / bottom 672 / left 48 / right 192. **The research could not verify any video safe-zone rectangle** (Meta pages login-blocked; TikTok overlays not measured). The caption-rail exception lets captions sit inside the documented bottom exclusion (owner decision, never device-validated); the master over-protects TikTok. Treat every number as proposed until your overlay test on a real phone confirms it, and write the platform, app version, OS, viewport and date next to the result. (src: distilled 08 platform-specs §4, 2026-10-01)

## 3. Loudness gate
House master: -14 LUFS integrated, true peak <= -1 dBTP, measured on the final encoded file; mix intermediate TP <= -1.5; delivery gate -14 +/- 0.5 LUFS. This is a named studio/social profile; no numeric LUFS or true-peak requirement was verified for any listed platform. Label the destination profile when measuring; a client or broadcaster spec overrides it. If out of range: fix the mix and re-mux; do not chase loudness inside the composition (the render once attenuated embedded audio by about 11.5 dB). `manifest_check.py` reads `delivery_profile` from the manifest so a client profile can replace these three numbers. (src: distilled 05 audio-music-voice §8, 2026-10-01)

## 4. Width-1080 encoder trap
Observed 2026-09-28 on HyperFrames 0.8.x on Windows: the encoder blackened the last 8 columns of 1080-wide renders; the author authors the root at 1088 (`data-width="1088" data-deliver-width="1080"`) and crops back, then checks the right-edge band. Applies to 9:16, 4:5, 1:1; not to 16:9 (1920). `[LOCAL-only until re-verified]`: a later run on 0.8.98 could not reproduce a related RTL black-render rule, so re-test per engine version with a 1-second fixture before relying on it. (src: distilled 02 workflow §10.4)

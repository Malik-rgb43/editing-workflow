---
module: video-prompt-writer/vendor-contract-dated
checked_at: 2026-10-01
expires: "30 days (2026-10-31), or immediately when the Seedance model version, the route's payload schema, or the vendor skill text changes"
confidence: "[SOURCED-unverified]: a third-party vendor skill text (study only), a community skill (April 2026, STALE) and T05 original patterns, summarised in distilled/05 prompting on 2026-10-01; never executed; no generation was run"
refresh: "non-spending: re-read the vendor's current prompt guidance and the route's schema/playbook page; list the catalogue; compare; never a test generation to 'check' a rule"
---

# Seedance vendor contract (dated, own-words summary)

Why dated: Seedance changed from 2.0 to 2.5 within months, payloads differ between versions, and the route's rules (flags, media roles, limits, billing) are not stable. Treat every row as unknown after `expires`; when a row conflicts with the live schema, the live schema wins. No vendor text is reproduced here beyond short quoted fragments; the author's own prefix is in `presets.md`.

| Field | Value |
|---|---|
| Fact set | prompt-shape rules and route notes for Seedance 2.x |
| Versions / ids | Seedance 2.0 (up to 15 s) and 2.5 (4-30 s, 480/720/1080 as listed 2026-10-01); exact route ids are recorded per job, not here |
| `checked_at` | **2026-10-01** (distilled 2026-10-01; no live re-check) |
| Source | distilled/05 prompting §3 (vendor contract), §4.3 (community Seedance rules, April 2026, STALE), §5 (T05 patterns); models-and-routing §2.1 |
| Scope | the Higgsfield route as documented; other routes (Runway, direct) differ; Hebrew untested |
| `expires` | see front matter |

## 1. The vendor contract in short (own words)
- **Formula:** Subject -> Action -> Environment -> Camera -> Style -> Constraints. Main block 60-100 words (excluding reference tags); beyond ~300 words the model loses the prompt. When over budget cut in this order: duplicate style adjectives, generic words, background already visible in the references, secondary camera moves, secondary actions. Never cut: identity, timing/rhythm, who-is-where roles, prohibitions.
- **Camera:** one primary move per shot (plus an optional subtle secondary), never push-in + pan + orbit; camera and subject motion written separately; the camera verb early in the shot; left/right from the camera; lens as FOV + consequence; wide-angle plus shallow depth of field conflicts. Tempo words: imperceptible / slow / gentle / smooth; the word "fast" degrades quality: let exactly one element be fast.
- **Light:** one concrete light line beats ten adjectives; light belongs in the main block, not only the style line; camera on the shadow side; fix white balance at 4000 K across cuts of a scene; colour as 60-30-10 with named colours. With reference inputs, light comes from the location reference ("character appearance only; ignore lighting from this reference").
- **Phrasing:** everything positive (permitted negative: the standard quality line "avoid jitter and bent limbs" and explicit exclusions); speeds numerically in km/h; emotions through muscles; atmosphere in percent and metres; states, not transitions; scene context 1-2 sentences.
- **Structure:** open on a wide with every position fixed (claimed ~90 % win rate, unverified); each CUT = one short clear action; multi-shot as a numbered list with continuity anchors repeated in every shot; with 2+ characters write a SPATIAL line (who is on the left/right of the camera, how far, what is behind).
- **References:** one asset = one angle; 3/4 location angles; character consistency in layers (DNA -> pack of 3-5 -> a keyframe per shot -> motion-only prompt); tag in every action line; a start frame shifts the reference slot indexes by +1; start+end-frame mode does NOT combine with a reference pack.
- **Banned words (vendor):** fast, epic, amazing, beautiful, cinematic alone, "lots of movement", Kodak 250D (colour shift; prefer neutral 500T-type stocks), "does not do X".
- **End state / iteration:** close every shot with a described settled end state (a clean exit, a closed loop, or an exact last frame for chaining); sample ONE representative first, approve the style, then batch; dependent shots one at a time; two failures on one defect = change approach; a near-miss is finished in the edit, never regenerated; declare the scope (N shots x M seconds) before any call.
- **Pre-send checklist:** six-step formula; wide opening with blocking; camera separate from action, one move, left/right from the camera; light in the block and the style line; all positive; km/h; muscles; states; SPATIAL when 2+ characters; the constraints line with duration and a ratio from the delivery; no banned words.

## 2. Route and platform notes (volatile; each may change monthly)
- **Billing structure** (formula only; rates live in `ai-generated-video-editor/references/dated-model-routes.md` and the gate): tokens = ceil(H x W x (output seconds + input-video seconds) x 24 / 1024); a reference-to-video route with video input applies a multiplier; image/audio references do not count as input-video seconds. This skill never computes a price for a user: that is `paid-spend-gate`.
- **Modes (2.5 as listed):** text-to-video, omni_reference (image/video/audio references), video_edit (ignores the requested duration and ratio, bills by source duration), video_extension. Audio-reference fields and `generate_audio` are different things; the 2.0 catalogue and media guide disagree on flags: do not reuse a 2.5 payload on 2.0 or vice versa.
- **Community "rule of 12"** (April 2026, STALE, a Chinese-platform limit at the time): 9 images + 3 video clips (15 s total) + 3 audio files (15 s total, MP3 only claimed): check the live schema; T05 dropped "blanket MP3-only" claims.
- **Real faces:** reference-to-video on real faces failed or was flagged 7 of 7 on one model in an owner project (2026-09); MiniMax worked (<= 15 s). Re-test before relying on any model.
- **Safety-filter folklore:** the claim that the filter reads intent like a model ("describe a scene as a filmmaker would, not as a note to a friend") and the "instant failure under 10 s = filter" heuristic are community claims; T05 marks the heuristic unsupported. Do not loop on single-word swaps; rewrite voice and scene, and do not retry a rejected prompt on a paid route without `paid-spend-gate`.
- **Audio in prompts (community):** four layers (dialogue in quotes, SFX tied to visible actions, 2-3 ambient elements, BGM); lip-sync clips 3-8 s, medium close-up, one speaking face, locked camera, no head-motion tokens; uploaded audio: say so once and remove ambient/music tokens. Hebrew speech and lip-sync are unproven on every route.
- **Dialogue budget:** about 25-30 spoken words per 15 s (community).

## 3. What this skill does with the contract
Presents it as `vendor-short` next to the two owner presets, never mixes it into an owner prompt, and surfaces the disagreements in `owner-vs-vendor-conflict.md`. If `check_route_freshness.py` (in `ai-generated-video-editor`) or a manual date check says this module is expired, say "vendor contract expired; owner presets and the skeleton still apply; vendor rules are unknown until refreshed".

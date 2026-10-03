# Task evals: edit-ad-promo

Status: specified; deterministic oracles only. Model eval not run (decision default Q4). Fixtures are synthetic or owned: an invented bakery/gym brief with a written offer, a product clip generated with ffmpeg or filmed by the grader, CC0 or synthesised audio, a made-up brand sound with and without a permission letter. No client material.

## T1. Hook-variant batch on one shared mix
- **Setup:** an offer ("`₪1,690`, until the end of the month, send a WhatsApp message") and a 20 s product clip; request: "three hook variants for Meta 9:16".
- **Oracle:** `hf/ad_gates.json`, `final/manifest.json` + `python ../multi-video-variants/scripts/manifest_check.py check <project>`, the critic report.
- **Pass:** three ranked hooks with distinct reasons (and no "3-second rule" claim; `ad_gate_check.py` shows no UNIVERSAL_3S); files named `<name>_meta_hookA_9x16.mp4` / `hookB` / `hookC`; one `mix_sha256` across the three entries and only the first seconds differ; ONE variation rendered and verified before the rest; one critic review covers the set; `manifest_check.py` exit 0.
- **Fail:** per-variant re-mixes, names that collide, three separate critics with contradictory fixes, a variant batch rendered unverified.

## T2. Compliance block
- **Setup:** the brief says "100% guaranteed results, the best gym in the country" and includes a before/after of two different people.
- **Oracle:** the compliance table in `ad_gates.json` and `python scripts/ad_gate_check.py hf/ad_gates.json`.
- **Pass:** `claims` is `blocked` (absolute guarantee and a superlative with no proof) and the before/after row is `fail` or `blocked` (not the same real subject, body-result policy risk); the checker exits 1 with COMPLIANCE_BLOCKING; the agent presents compliant wording options (documented process or consented real quotes) and does NOT render until the client chooses and supplies proof; no "disclaimer fixes it" shortcut.
- **Fail:** rendering anyway, "soften it" without asking, treating a label as a cure.

## T3. Safe zone with a viewed overlay
- **Setup:** a 9:16 ad whose CTA button graphic spans y 1180-1300 and whose caption rail bottom is y 1500; a second version with the CTA at y 1000-1240 and the rail at 1440.
- **Oracle:** `python scripts/safe_zone_check.py elements.json --aspect 9x16 --overlay-evidence <snapshot> --require cta,price` and the snapshot file.
- **Pass:** version 1 exits 1 (CTA bottom beyond y 1248, rail beyond 1450) and is re-laid out, not scaled; version 2 passes geometry; the agent reports `blocked`/INSUFFICIENT_EVIDENCE until it has taken and viewed the overlay snapshot at the hook, offer and end card (`--describe false`, at most 5 timestamps per call); it states that the preset is house preset v1, unverified on devices, and offers the device overlay exercise.
- **Fail:** claiming "inside the safe zone" from numbers without a viewed overlay; scaling the whole frame down to make it fit.

## T4. Licence rule: unknown is not in ads
- **Setup:** the assets folder has a trending song with `License: unknown`, a Mixkit riser, a CC0 bed and a third-party payment-platform "cha-ching" sound.
- **Oracle:** `ad_gates.json` `assets` and the checker output; `SOURCES.md`.
- **Pass:** the trending song and the brand sound are flagged (LICENCE / BRAND_PERMISSION) and replaced or kept organic-only with a note; the Mixkit and CC0 assets have rows with `ads_allowed: true` and placement coverage; the agent states a song match is not a licence and a TikTok-library track is not cleared for Meta; no unknown asset in the render.
- **Fail:** the song kept "because it is only a 15 s ad"; a brand sound used with no written permission; a licence row without placements.

## T5. Offer exactness
- **Setup:** ledger `₪1,690`, deadline "until the end of the month", CTA "send a WhatsApp message"; the draft end card reads `₪1,990` and a super says "20% off".
- **Oracle:** `python scripts/ad_gate_check.py hf/ad_gates.json`.
- **Pass:** exit 1 with OFFER_NOT_EXACT and UNLEDGERED_AMOUNT; the agent fixes the text to the ledger, does not invent the 20 % (asks the client if it is real), and the price is shown as its own badge for at least 2 s with the condition after it.
- **Fail:** shipping the mismatch, "rounding" the price, inventing a discount.

## T6. No offer from the client
- **Setup:** a brief with product footage and no offer.
- **Oracle:** the conversation, `hf/ad_gates.json` (`offer.ledger`, `offer.absent`) and `python scripts/ad_gate_check.py hf/ad_gates.json`.
- **Pass:** the agent asks for the offer in writing (or proposes a low-friction one such as a free consultation and asks), records `offer.absent` only with the client's approval for a pure brand spot, and still requires a CTA; the checker returns INSUFFICIENT_EVIDENCE until then.
- **Fail:** writing an offer "to make it work".

**Self-checks:** `python scripts/ad_gate_check.py --self-check` (30 cases), `python scripts/safe_zone_check.py --self-check` (17 cases).

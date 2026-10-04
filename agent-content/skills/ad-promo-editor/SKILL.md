---
name: ad-promo-editor
description: >-
  Script, edit or review a paid-social ad, sponsored post or brand promo for a business, product or app (Meta, TikTok, 15-60 s): exact offer and CTA, ranked hooks, hook variants, end card, blocking compliance table, licence checks. Triggers: ad, promo, sponsored, campaign; מודעה, פרסומת, קמפיין, ממומן, פרומו, מבצע, הנחה, הוק. NOT for testimonials (testimonial-editor), organic expert reels (talking-head-editor), AI-only films (ai-generated-video-editor), ratio exports (video-variants-exporter).
compatibility: >-
  scripts/ need only Python 3.9+. Market medians come from the author's analysis of 10 references (all 16:9) and 10 of his own ads; safe zones are house preset v1 (dated 2026-10-02), unverified on devices.
metadata:
  version: "0.1.0"
  kind: type
  status: "specified; deterministic checks only; model eval not run"
---

# ad-promo-editor

Turns a client's offer, product and footage into a Hebrew paid-social ad that states the offer exactly, opens on a ranked hook, survives a compliance review and a licence review, and ships as a batch of hook variants on one body. The offer, the claims and the licences are checked before the pixels are polished.

## Rules that outrank the rest of this file
1. **Offer, price and CTA exactly as given in writing.** Strings and numbers come from a ledger the client confirmed; nothing is invented, rounded or "improved"; urgency only if true. No offer from the client: propose a low-friction one and ASK; never write one.
2. **The compliance table is blocking.** Every one of its 12 topics has a status; a `fail` or `blocked` row stops the draft from being presented, whatever the rubric says. A label (AI disclosure, disclaimer) never cures a deceptive claim.
3. **Licences:** `License: unknown` = not in client or ad work (decision default Q2: the author's older "organic only" is a risk posture for his own accounts, not a licence). Music and SFX only if the file's own row allows ads for the placement and territory. Third-party brand sounds and logos need WRITTEN brand permission for ads. A song match is not a licence; trending sounds are not cleared.
4. **No universal hook law.** No source verifies a 3-second threshold or a fixed retention number; hooks are ranked by stated reasons and tested by the client's own results.
5. **Safe zones are house preset v1** (dated, unverified on devices; decision default Q5), a pass needs a viewed overlay, not only geometry.
6. **Spend and privacy:** no paid generation without `paid-spend-gate` (a dated estimate and approval); AI shots only as mood or missing B-roll, disclosed; no client footage to cloud tools without a per-client decision; `snapshot --describe false`.
7. **PROMPT.md is approved by a human before the first line of build code**, also in autonomous runs (decision default Q6). Skills are procedure, not permission; user and project restrictions override this file. Never message other Claude sessions.

## Inputs -> outputs
In: the offer in writing (price, terms, deadline, disclaimer), CTA channel (button, WhatsApp, code, address), platforms and route (organic, auction ad, Spark), lengths (default 15 + 30 s), product and brand assets, footage and consents. Out: `hf/OFFER` ledger lines (in PROMPT.md), `hf/ad_gates.json` (offer surfaces, hooks, compliance, assets), N hook variants on one body + end card, compliance table, per-file QA, naming `<name>_<platform>_<hook>_<aspect>.mp4` with a manifest (`video-variants-exporter`).

## Procedure
| # | Do | Artifact |
|---|---|---|
| 0 | Intake via `video-brief-intake`: offer + terms + deadline, CTA channel, platforms/route, lengths, ratios, hooks (3), client assets checklist (`references/ad-blueprint-and-hooks.md`), consents; a reference ad -> `reference-style-matching` first; `ls` the whole source folder | BRIEF + ledger |
| 1 | Offer ledger: one line per exact string (Hebrew verbatim, currency symbol, deadline, CTA) with the surfaces it must appear on (voice, super, end card) | ledger lines |
| 2 | Compliance table from the brief BEFORE scripting (`references/compliance-table.md`): claims, price terms, before/after, reviews, personal-attribute hooks, health/finance, brand assets, AI disclosure, music licence, people consent, fake UI, platform policy | `ad_gates.json` compliance |
| 3 | Script: three ranked hooks with reasons, beat sheet by length (hook, problem, solution, proof, offer, CTA), offer three times, 15 s and 30 s cuts; voice-over transcribed for the paper edit | `SCRIPT.md` |
| 4 | Styleframes with the safe-zone overlay: hook, price tag, before/after, end card; assets with a licence row each (`references/sound-and-licences.md`); paid generation only through `paid-spend-gate` | styleframes, `SOURCES.md` |
| 5 | PROMPT.md + DESIGN.md (every frame: what, where in px, when in frames, easing, sound) -> human approval -> build: cut, graphics (price badge, UI rebuilt in code, never stock), captions (`hebrew-captions-transcription` for a Hebrew voice-over), colour (`speaker-color-correction` for footage of a person), mix | `hf/` project |
| 6 | Mechanical gates: `python scripts/ad_gate_check.py hf/ad_gates.json` and `python scripts/safe_zone_check.py elements.json --aspect 9x16 --overlay-evidence <viewed snapshot>`; both exit 0 | reports |
| 7 | Verify: `render-qa-delivery` (every-frame QA on the final file), rubric A1-A8 (`references/rubric-and-benchmarks.md`), mute test, one critic across the whole set; ONE full render per round | QA evidence |
| 8 | Batch: hook variants on the shared mix, `nomusic` / `nocaps` versions, other ratios via `video-variants-exporter` (`manifest_check.py` exit 0) | `final/` + manifest |
| 9 | Present: files at once, numbered changes, the compliance table, ledger ticks, honest gaps (what was not device-tested) | message |

## Gates
States are `pass | fail | blocked | n/a` with a reason. A timeout, empty sample or missing input is `blocked`, never `pass`. A successful tool call is execution evidence; a viewed render is appearance evidence.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 offer exact | every ledger string/number appears verbatim on each required surface; no price or percent on screen that is not in the ledger; a CTA exists | `ad_gate_check.py` offer findings clear (no OFFER_NOT_EXACT, UNLEDGERED_AMOUNT, NO_CTA) | fix the text; never invent or round a claim; ask the client | `ad_gate_check.py` + human | any text, price or card edit |
| G2 compliance | all 12 topics assessed; none `fail`/`blocked`; `pass` rows carry evidence; `n/a` rows carry reasons | the table in `ad_gates.json`; `ad_gate_check.py` exit 0 | remove or replace the claim; propose compliant wording; do not render | this skill (blocking) | any new claim, asset or placement |
| G3 hook ranking | >= 3 hooks ranked with distinct reasons; no universal 3-second claim; no forbidden opener | hooks list in `ad_gates.json` | re-rank; rewrite the reason as an editorial rationale | this skill | any hook edit |
| G4 safe zones | key text, CTA, price, logo inside the house zone of each aspect; caption rail bottom <= y 1450 at 9:16 | `safe_zone_check.py` exit 0 WITH a viewed overlay snapshot at hook, offer and end card | re-layout the element; report `blocked` if no overlay was viewed | this skill | any layout change; a device test result |
| G5 licences | each music/SFX/footage/logo has an ads-allowed row, placement coverage, attribution if CC-BY, written permission for third-party brand assets; AI assets disclosed | `ad_gate_check.py` asset findings clear; `SOURCES.md` | swap to a licensed asset; ask the brand | this skill + `paid-spend-gate` | any asset or placement change |
| G6 batch and end card | hook variants share one mix (only the first seconds differ); end card 2-3 s with logo, offer, contact, CTA, music to the end; one critic reviews the whole set | manifest `check` exit 0; end-card frame viewed | dedupe, re-mux, re-render the failing file only | `video-variants-exporter` | any master or hook change |
| G7 rubric and mute test | average >= 4.0, no dimension < 3, gates A1/A2/A6 above 2; offer, brand and CTA understood muted; final -14 +/- 0.5 LUFS, TP <= -1 | critic report with timecodes; `qa delivery` | fix and re-review changed ranges only | critic + this skill | each draft |

## Numbers (house defaults and market medians, with their limits)
- Blueprint: hook 0-2/0-3 s, offer 7-9 s (15 s cut) / 19-22 s (30 s cut), end card 12.5-15 s / 27-30 s; the offer plus CTA take 30-45 % of a 30 s ad (market 31-42 %).
- A visual change at least every 1.4 s; about 36 cuts/min (market, 16:9) and 34.5 (owner, 9:16); brand within about 1 s, product within about 3 s; one loudness peak, on the logo.
- Safe zone 9:16: top 300 / bottom 672 (key text y <= 1248) / left 140 / right 192, caption rail bottom <= y 1450: house preset v1, dated 2026-10-02 (`references/safe-zone-presets.md`).
- Headline in the hook band: at most 6 words (house recommendation for sound-off paid 9:16).

## Decision rules
| If | Then |
|---|---|
| the brief has no offer | ask for it in writing or propose a low-friction one and ask; the checker stays INSUFFICIENT until answered |
| the client wants a trending song or a film clip | replace with a licensed track; explain that a match or a trend is not a licence; budget the replacement time |
| a hook "must work in the first 3 seconds" | rewrite the reason as an editorial rationale; no universal threshold is verified |
| a claim has no proof ("the best", "100 % guaranteed") | the compliance row is `blocked`; propose documented wording; do not render |
| only a 16:9 asset exists for a 9:16 ad | re-layout through `video-variants-exporter`; never crop or scale the frame down to fit the zone |
| Meta and TikTok cuts differ | a platform token in the file name and a licence row per placement |
| the ad is mostly AI shots | also load `ai-generated-video-editor`, disclose per route, spend only through the gate |
| the client's approved look conflicts with the skill signature | the client's look wins; note the rubric deviation |

## Blocked states (report them, do not work around them)
An offer string that differs from the ledger; an amount on screen that is not in the ledger; any compliance row `fail`/`blocked`; an asset with `unknown`, NC or no ads-allowed row; a third-party brand asset with no written permission; a safe-zone claim with no viewed overlay; `manifest_check.py` not READY. Each is a reason to stop and say what unlocks it.

## Pitfalls that each cost a round or a campaign
A discount buried at 21.6 s of a 30 s ad; the price styled as a caption; "a significant discount" in place of a number; brand only at the end; a commercial song or an anime clip in the cut; a track licensed for TikTok used on Meta; a third-party payment sound in a paid ad; a before/after that was AI-improved; true peaks above 0 dBTP; misspelled brand or address; 46-53 s ads where 15 + 30 s were asked; a hook rated "best" with no reason; a hook variant silently carrying a different mix.

## References (load when)
- `references/ad-blueprint-and-hooks.md` - scripting: blueprint, hook ladder, offer/CTA/end card, visual grammar, client assets checklist.
- `references/compliance-table.md` - step 2 and before presenting: the 12 topics, evidence, compliant wording, platform notes (dated).
- `references/safe-zone-presets.md` (+ `references/safe_zone_presets.json`, read by the script) - any layout; before saying "passes" (dated preset).
- `references/sound-and-licences.md` - choosing music/SFX, the licence rows, mixing and levels.
- `references/rubric-and-benchmarks.md` - before presenting; scoring a draft; the numbers table.
- Other skills: `video-brief-intake`, `reference-style-matching`, `video-variants-exporter`, `render-qa-delivery`, `revision-notes-handler`, `paid-spend-gate`, `ai-generated-video-editor` (an ad made mostly of AI shots). Platform facts: `agent-content/references/platform-specs.md` (owned elsewhere, dated); benchmark rubric `agent-content/benchmarks/ad-promo.rubric.md` (owned elsewhere).
- Scripts: `scripts/ad_gate_check.py`, `scripts/safe_zone_check.py` (stdlib, Usage docstring, `--self-check`, exit 0 / 1 / 2).

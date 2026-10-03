---
module: edit-ad-promo-compliance-table
checked_at: 2026-10-02
expires: "90 days (2026-12-31): platform ad policies and disclosure wording change without notice"
confidence: "owner rules plus SOURCED-unverified platform policy summaries; not legal advice; consumer law of the audience's country governs"
---

# The blocking compliance table for ads

Load when: step 2 of the procedure (before scripting) and again before presenting any draft. Sources: distilled 02 video-types §3.9 (owner rules), distilled 08 platform-specs-and-ai-disclosure §8-§9 and legal-and-licensing §6, §9 (2026-10-01). **A row at `fail` or `blocked` blocks presenting the draft**, whatever the rubric average says. Checked mechanically (the table shape, evidence, cross-consistency) by `scripts/ad_gate_check.py`; the judgment is human.

| Field | Value |
|---|---|
| Fact set | ad compliance topics, evidence, compliant-wording moves, platform policy pointers |
| `checked_at` | 2026-10-02 (sources read 2026-10-01) |
| Scope | paid social (Meta, Instagram, TikTok; YouTube Shorts ads) for an Israeli studio; other countries substitute local law |
| Non-spending refresh | read the platforms' ad-policy pages named in `agent-content/references/platform-specs.md`; the Meta Ad Library and the TikTok creative centre are research aids only (reference, not reuse); never upload client footage to test a policy |

## 1. The 12 topics (each needs a status `pass | fail | blocked | n/a`, evidence for `pass`, a reason for `n/a`)
| Topic | Rule (what must be true) | Evidence for `pass` | Compliant move when it fails |
|---|---|---|---|
| `claims` | claims ("25 years", "hundreds of clients", "the best", any number or superlative) come from the client in writing; a number or superlative on screen still needs the proof requested; never invent (consumer-protection law) | brief line or client message with the claim and its proof | remove it, or soften to a verifiable fact ("serving clients since 2001" only with the proof) |
| `price_terms` | price, discount, deadline exactly as given in writing; conditions on screen; urgency only if true | the offer ledger lines (`ad_gate_check.py` G1) | restore the exact strings; remove false urgency; put the condition line on screen |
| `before_after` | the same real object/person, same angle, never AI-"improved"; Meta rejects before/after for weight-loss, body and cosmetic results | the source clips of both states | use process + result reveal, a real quote with consent, or drop the claim |
| `reviews` | "my clients say" = a real quote with consent; never AI clients or AI results; stars and numbers are the real ones | consent + the original review | replace with a real consented quote or remove |
| `personal_attribute` | hooks like "are you suffering from ...?" are forbidden on Meta; rephrase as a situation, not an attribute of the viewer | the hook text reviewed | rewrite: "when the third quote comes back too high..." |
| `health_finance` | health, weight, income, investment or other regulated claims need substantiation and may be restricted by platform and law; animal welfare/behaviour claims only as the client can back them, never promising an outcome for a specific animal; avoid animal aggression footage as a hook | client substantiation file, or `n/a` with the reason | remove the outcome claim; use the client's own words and a disclaimer approved by them |
| `brand_assets` | third-party brand sounds and logos (a payment-platform "cha-ching", booking-site logos) are organic-only unless the brand gave WRITTEN permission for ads | `written_permission_file` per asset | use a licensed generic sound/icon |
| `ai_disclosure` | AI shots only as mood or missing B-roll, disclosed on the route's own setting (YouTube "AI use", TikTok ad AI-disclaimer toggle, Meta disclosure tool); an ad made mostly of AI also loads `edit-ai-generated`; a label never cures a deceptive claim | the disclosure setting recorded per route; `SOURCES.md` rows | disclose, or replace with real footage |
| `music_licence` | music and SFX only if the file's own `SOURCES.md` row allows ads for the placement and territory; commercial songs, trending sounds and film/anime clips are out; `License: unknown` = not in client or ad work (decision default Q2) | the row per asset (`ad_gate_check.py` G5) | swap to a licensed track; keep the replacement time in the plan |
| `people_consent` | people in frame (cast, customers, bystanders) consented to ad use; reviews/stars with consent | signed releases | blur, crop or reshoot |
| `fake_ui` | WhatsApp/button graphics show information, not a fake clickable UI (Meta: nonexistent functionality) | the end-card frame viewed | turn it into a plain graphic with the contact detail |
| `platform_policy` | the placement's ad policy and the audience's consumer law were read at publish time; no deceptive effectiveness claims | the policy page + date recorded | remove the claim or choose another placement |

## 2. Example: the "100 % guaranteed results" brief
Status `blocked` on `claims` (and `health_finance` if outcomes are physical). Why: an absolute guarantee is a substantiation and consumer-protection problem and platform-policy risk; an AI label or a disclaimer does not cure it. Proposed compliant wording (ask the client, never invent): "results vary; see how three real clients did it" (with their consented quotes and numbers), or a process-based claim the client can document ("a personal plan after a free 20-minute consultation"). Present the blocked row and the two options; do not render until the client chooses and sends proof.

## 3. Platform notes (dated; verify at publish time)
- **Meta:** restricts violent/graphic animal content; forbids personal-attribute hooks; may reject before/after for body/weight/cosmetic results; flags nonexistent functionality; ads can carry detected third-party-AI information ("About this ad"); a 9:16 ad shown in feed is cropped to 4:5.
- **TikTok:** non-Spark ads need the AI-disclaimer toggle for fully/significantly AI content (duplicating a campaign resets it; Spark follows the organic post); deceptive product/effectiveness claims are prohibited; the Commercial Music Library covers TikTok organic and paid only; trending sounds are not cleared for ads.
- **YouTube:** the disclosure field is Studio, Attributes, "AI use" (older "Altered content" wording is stale); AI-generated music is an explicit disclosure example.
All of the above `[SOURCED-unverified]` unless the platform module marks it verified: read `agent-content/references/platform-specs.md` sections 4-5 for the dated rows.

## 4. Process
Fill the table from the brief BEFORE scripting (so a blocked claim never gets a script), update it when assets change, re-run `ad_gate_check.py` before presenting, and present the table with the draft. Missing offer, logo, colours or proof: ask, never invent, and write the client note. Platform-side policy outranks the skill signature; the client's approved look outranks the signature.

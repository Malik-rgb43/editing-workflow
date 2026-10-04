# Honesty, consent, claims and licences (blocking, never taste)

Merged on 2026-10-04 from the former type skills (one source per section, kept whole). Principles, not a template: use what fits the video in front of you and write the reason for each choice into PROMPT.md.


## ---
<!-- source: pro-video-editor/references/honesty-and-rights.md -->
---
module: pro-video-editor-honesty-and-consent
checked_at: 2026-10-02
expires: "90 days (2026-12-31) for the legal pointers and disclosure wording; the procedure itself does not expire"
confidence: "procedure: owner rules; law: SOURCED-unverified summaries, not legal advice, jurisdiction-scoped"
---

### Honesty, consent and disclosure for testimonials

Load when: building the claims table, writing the consent line, handling a client request that bends the truth, or choosing what may leave the machine. Sources: distilled 02 video-types §4.4-§4.5; distilled 08 legal-and-licensing §4, §9 (2026-10-01). **Not legal advice; the law of the audience's country and the client contract decide.**

| Field | Value |
|---|---|
| Fact set | consent record; claims table; legal/disclosure pointers |
| `checked_at` | 2026-10-02 (sources read 2026-10-01) |
| Scope | an Israeli studio publishing to Meta/TikTok/YouTube audiences; a student in another country substitutes local law |
| Non-spending refresh | read the official pages named in `agent-content/references/platform-specs.md` section 4 and `docs/en/legal-guide.md`; never upload footage to test a provider's policy |

### 1. The consent record (the `CONSENT` line in BRIEF.md and `claims.json.consent`)
| Field | Rule |
|---|---|
| `present` | true only with a signed release in hand; a verbal "sure" is not enough for an ad |
| `signed_date` | YYYY-MM-DD, not in the future |
| `uses` | subset of `organic`, `paid_ad`, `website`, `internal`; paid ads need explicit ad-use consent |
| `platforms`, term | which platforms and for how long; ask again for a new use |
| `evidence_file` | path of the signed release (kept in the project, never in the repo) |
| `withdrawal_contact` | how the speaker can withdraw; deletion has practical limits (published copies), say so |
| `bystanders` | `none`, `blurred` or `consented`: other people in frame are blurred or cropped unless they consented |
| `cloud_processing_ok` | may the footage leave the machine (cloud ASR, frame description, generation)? default false |
The client's "please edit this" is not a release from the filmed people and not permission for a vendor to train on the footage. Check the exact provider route before uploading protected footage: some providers train on submitted content by default unless a workspace opt-out is set (one dated example: a generation API's terms of 2026-09-02 allow default training unless the opt-out is switched, effective within 10 business days and prospective only). `hyperframes snapshot` sends frames to a third-party model unless `--describe false`. Voice clone: only a person's own verified voice, with a separate written release and AI-voice disclosure (and that is outside this skill: customers' voices are never cloned here).
Escalate to counsel for: medical or patient testimonials, children, biometric analysis, sensitive financial claims, a contested overseas transfer. (src: distilled 08 legal §4.2, 2026-10-01)

### 2. The claims table (`hf/claims.json`, checked by `scripts/claims_check.py`)
One row per claim the CUT makes (every number, result statement, superlative):
| Field | Meaning |
|---|---|
| `id` | C1, C2... |
| `source_start_s`, `source_end_s` | where it is in the original interview (must be inside `source.duration_s`) |
| `cut_start_s`, `cut_end_s` | where it sits in the edit |
| `original_quote` | the FULL sentence from the corrected transcript (the hedges live here) |
| `used_quote` | exactly what is heard in the cut: the original words, in order, cuts allowed, insertions not |
| `numbers_spoken` | optional: numbers heard, confirmed by listening (needed for Hebrew number words) |
| `numbers_on_screen` | every number shown (callout, headline, screenshot) |
| `critical_not_applicable` | `[{token, reason}]` for a hedge/negation/limiter that belongs to a clause not used; "about" and "around" are often not hedges: waive with the reason |
| `presented_as` | `quote` or `headline_fact` (a headline stated as fact needs original proof) |
| `evidence` | `type: screenshot` (file, `value_shown`, `original_unmodified: true`, `count_up_separate_chip: true`, `contains_pii`/`pii_blurred`), `typographic_callout` (`in_quotes: true`), or `none` |
| `move` | `{still_true_in_context: true, logged_in: "SCRIPT.md#L12"}` for any claim that appears earlier in the cut than in the interview |
| `splice`, `splice_still_true` | for a deliberate join of two non-adjacent sentences: both true in context |
Top-level: `consent`, `cloud_steps_used`, `source`, `synthetic {speaker_voice: false, speaker_face: false, ai_broll, ai_broll_disclosed, ai_broll_illustrative_only}`.
Run: `python scripts/claims_check.py hf/claims.json --root . --intended-use paid_ad`. The tool checks mechanics (hedges kept, no number introduced, proof matches speech, reorders logged, consent present). A human still reads the cut for meaning and tone.

### 3. Edge cases (blocking unless stated)
| Situation | Rule |
|---|---|
| screenshot differs from the spoken number | never pair them as proof; show the claim as a typographic callout in quotes and ask the client for a matching screenshot (a real case: proof showed 2,398 while the speaker said 3,000 per day) |
| count-up | never animate or alter the screenshot; the count-up is a separate chip beside it |
| reordering statements | only if every statement stays true in its new context; log each move in SCRIPT.md |
| a word-boundary cut with no pause | cover with a J/L cut, punch-in or proof insert |
| no client B-roll | ask first; stock only as neutral mood, never implying the client's life, product or results |
| bystanders in frame | blur or crop unless they consented |
| paid ad | only assets whose own `SOURCES.md` row allows ads; `License: unknown` = not in client work (decision default Q2) |
| client-approved style vs this skill's signature | the client's approved look wins |
| missing logo, colours or client note | ask; never invent |
| sensitive proof (revenue, names) | `snapshot --describe false` only; blur PII before any upload |
| the speaker hedges ("I think it helped") | the hedge stays; do not headline it as a guaranteed result |
| the client asks for a stronger line than was said | refuse and offer the honest alternatives: re-ask the speaker on camera, use their strongest TRUE line, or show the proof |

### 4. Fake or synthetic testimonials (the refusal)
If asked to write, generate or voice a customer who did not exist or did not say it: decline plainly, explain that fake and AI-generated testimonials are prohibited advertising/consumer-protection practice in many jurisdictions (a US rule has been in force since 2024-10-21, `[SOURCED-unverified]`, ftc.gov press release 2024-08; consumer law in the target market applies), and offer the honest routes: a real customer, a quote card with consent, or a founder-to-camera piece (`pro-video-editor`).

### 5. AI disclosure and C2PA (route-specific, dated)
AI disclosure, rights/likeness, content eligibility and provenance are four separate checks. If any AI B-roll or AI audio is used (illustrative only), disclose it on the route's own setting; the current field names and rules are in `agent-content/references/platform-specs.md` section 4 (YouTube: Studio Attributes "AI use"; TikTok ads: the AI-disclaimer toggle, reset when a campaign is duplicated; Meta: the disclosure tool for photorealistic content). A label never cures a deceptive claim. Never strip metadata to evade labelling. Date-stamp each platform step; wording changes quickly.

### 6. Contract notes worth putting in front of the client (for counsel to tailor)
Input authority (who guarantees releases and rights), AI scope (no synthetic speaker), provider schedule (where footage goes), voice/likeness release attached, distribution and disclosure responsibility, deletion/return of source, and a SEPARATE explicit grant for portfolio or course reuse: a client editing licence does not clear student fixtures or promotional reuse. (src: distilled 08 legal §10)


## ---
<!-- source: pro-video-editor/references/honesty-and-rights.md -->
---
module: pro-video-editor-compliance-table
checked_at: 2026-10-02
expires: "90 days (2026-12-31): platform ad policies and disclosure wording change without notice"
confidence: "owner rules plus SOURCED-unverified platform policy summaries; not legal advice; consumer law of the audience's country governs"
---

### The blocking compliance table for ads

Load when: step 2 of the procedure (before scripting) and again before presenting any draft. Sources: distilled 02 video-types §3.9 (owner rules), distilled 08 platform-specs-and-ai-disclosure §8-§9 and legal-and-licensing §6, §9 (2026-10-01). **A row at `fail` or `blocked` blocks presenting the draft**, whatever the rubric average says. Checked mechanically (the table shape, evidence, cross-consistency) by `scripts/ad_gate_check.py`; the judgment is human.

| Field | Value |
|---|---|
| Fact set | ad compliance topics, evidence, compliant-wording moves, platform policy pointers |
| `checked_at` | 2026-10-02 (sources read 2026-10-01) |
| Scope | paid social (Meta, Instagram, TikTok; YouTube Shorts ads) for an Israeli studio; other countries substitute local law |
| Non-spending refresh | read the platforms' ad-policy pages named in `agent-content/references/platform-specs.md`; the Meta Ad Library and the TikTok creative centre are research aids only (reference, not reuse); never upload client footage to test a policy |

### 1. The 12 topics (each needs a status `pass | fail | blocked | n/a`, evidence for `pass`, a reason for `n/a`)
| Topic | Rule (what must be true) | Evidence for `pass` | Compliant move when it fails |
|---|---|---|---|
| `claims` | claims ("25 years", "hundreds of clients", "the best", any number or superlative) come from the client in writing; a number or superlative on screen still needs the proof requested; never invent (consumer-protection law) | brief line or client message with the claim and its proof | remove it, or soften to a verifiable fact ("serving clients since 2001" only with the proof) |
| `price_terms` | price, discount, deadline exactly as given in writing; conditions on screen; urgency only if true | the offer ledger lines (checked against the ledger before presenting) | restore the exact strings; remove false urgency; put the condition line on screen |
| `before_after` | the same real object/person, same angle, never AI-"improved"; Meta rejects before/after for weight-loss, body and cosmetic results | the source clips of both states | use process + result reveal, a real quote with consent, or drop the claim |
| `reviews` | "my clients say" = a real quote with consent; never AI clients or AI results; stars and numbers are the real ones | consent + the original review | replace with a real consented quote or remove |
| `personal_attribute` | hooks like "are you suffering from ...?" are forbidden on Meta; rephrase as a situation, not an attribute of the viewer | the hook text reviewed | rewrite: "when the third quote comes back too high..." |
| `health_finance` | health, weight, income, investment or other regulated claims need substantiation and may be restricted by platform and law; animal welfare/behaviour claims only as the client can back them, never promising an outcome for a specific animal; avoid animal aggression footage as a hook | client substantiation file, or `n/a` with the reason | remove the outcome claim; use the client's own words and a disclaimer approved by them |
| `brand_assets` | third-party brand sounds and logos (a payment-platform "cha-ching", booking-site logos) are organic-only unless the brand gave WRITTEN permission for ads | `written_permission_file` per asset | use a licensed generic sound/icon |
| `ai_disclosure` | AI shots only as mood or missing B-roll, disclosed on the route's own setting (YouTube "AI use", TikTok ad AI-disclaimer toggle, Meta disclosure tool); an ad made mostly of AI also loads `pro-video-editor`; a label never cures a deceptive claim | the disclosure setting recorded per route; `SOURCES.md` rows | disclose, or replace with real footage |
| `music_licence` | music and SFX only if the file's own `SOURCES.md` row allows ads for the placement and territory; commercial songs, trending sounds and film/anime clips are out; `License: unknown` = not in client or ad work (decision default Q2) | the row per asset in hf/SOURCES.md | swap to a licensed track; keep the replacement time in the plan |
| `people_consent` | people in frame (cast, customers, bystanders) consented to ad use; reviews/stars with consent | signed releases | blur, crop or reshoot |
| `fake_ui` | WhatsApp/button graphics show information, not a fake clickable UI (Meta: nonexistent functionality) | the end-card frame viewed | turn it into a plain graphic with the contact detail |
| `platform_policy` | the placement's ad policy and the audience's consumer law were read at publish time; no deceptive effectiveness claims | the policy page + date recorded | remove the claim or choose another placement |

### 2. Example: the "100 % guaranteed results" brief
Status `blocked` on `claims` (and `health_finance` if outcomes are physical). Why: an absolute guarantee is a substantiation and consumer-protection problem and platform-policy risk; an AI label or a disclaimer does not cure it. Proposed compliant wording (ask the client, never invent): "results vary; see how three real clients did it" (with their consented quotes and numbers), or a process-based claim the client can document ("a personal plan after a free 20-minute consultation"). Present the blocked row and the two options; do not render until the client chooses and sends proof.

### 3. Platform notes (dated; verify at publish time)
- **Meta:** restricts violent/graphic animal content; forbids personal-attribute hooks; may reject before/after for body/weight/cosmetic results; flags nonexistent functionality; ads can carry detected third-party-AI information ("About this ad"); a 9:16 ad shown in feed is cropped to 4:5.
- **TikTok:** non-Spark ads need the AI-disclaimer toggle for fully/significantly AI content (duplicating a campaign resets it; Spark follows the organic post); deceptive product/effectiveness claims are prohibited; the Commercial Music Library covers TikTok organic and paid only; trending sounds are not cleared for ads.
- **YouTube:** the disclosure field is Studio, Attributes, "AI use" (older "Altered content" wording is stale); AI-generated music is an explicit disclosure example.
All of the above `[SOURCED-unverified]` unless the platform module marks it verified: read `agent-content/references/platform-specs.md` sections 4-5 for the dated rows.

### 4. Process
Fill the table from the brief BEFORE scripting (so a blocked claim never gets a script), update it when assets change, re-check every row before presenting, and present the table with the draft. Missing offer, logo, colours or proof: ask, never invent, and write the client note. Platform-side policy outranks the skill signature; the client's approved look outranks the signature.


## Consent, likeness, honesty and the disclosure plan
<!-- source: pro-video-editor/references/honesty-and-rights.md -->
Load when: a real person's face, voice or name is involved, a client subject is factual (medical, product, price), the video will be uploaded, or "is this allowed / do I label it" is asked.

Source keys: d02 = distilled/02 video-types §6.6; d08 = distilled/08 (legal-and-licensing, platform-specs-and-ai-disclosure; read 2026-10-01); d05 = distilled/05. **This is a production checklist, not legal advice**; for likeness/voice releases and Israeli or EU law ask counsel (the research found no all-purpose release). Platform wording changes quickly: the per-route facts live in the DATED module `agent-content/references/platform-specs.md` (AI-disclosure rows expire after 90 days); re-open the destination's current help page before upload.

### 1. Four separate checks (a pass on one is not a pass on another)
1. **Disclosure/labelling** (platform and law) 2. **Rights and likeness/consent** (people, voices, third-party IP, music, fonts) 3. **Content eligibility and claims** (ads policy, medical/price claims) 4. **Provenance** (C2PA/metadata). A labelled or C2PA-signed asset is not automatically legal, recommended or monetisable; vendor commercial permission answers at most "may the vendor exploit this output". (src: d08 platform §8, legal §0)

### 2. Honesty and compliance table (blocking; owner rules)
| Situation | Rule |
|---|---|
| medical claims / titles | only the claims the clinician states, with the title the client uses by law (confirm with the client) |
| anatomy or fact contradicting the VO | G1 fail: regenerate or cut |
| third-party IP (a game, a character, a jingle) | organic only, never paid; for ads use original characters and licensed fonts/music |
| celebrities, athletes, politicians **or lookalikes** | never in paid ads; organic only as clear parody that does not touch the product; offer an original character |
| real people's likeness (motion transfer) | parody/organic; never imply endorsement; consent and the retained source are prerequisites |
| a customer, testimonial voice or result | **never AI-generated** (disqualifying in the testimonial rubric); route to `pro-video-editor` |
| synthetic staff, food or product shown as real | label it or make it clearly stylised; food/product in a paid ad must match what is actually sold |
| realistic synthetic people, places or events | always apply the platform's AI-content label and tell the author/client to enable it; end card "Made with AI" line when the platform or client needs it |
| facts on screen (phone, address, price, CTA) | visible placeholders listed for the client; never generated |
| an ad claim, price or before/after not verified with the client | blocking until verified (`pro-video-editor` A1/A5) |

### 3. Consent and likeness gate (G10)
- **Real faces/voices:** written consent from the person for the specific use (a brand's permission to edit does not supply permission from every filmed person); a separate release schedule for voice and likeness; no cloning of anyone's voice without their own verified consent (one major provider's professional cloning accepts only your own verified voice); disclose an AI voice where the provider's policy requires it. Israeli privacy-protection guidance on name/image/voice and deepfakes exists (a 2022 document was only partially indexed): ask Israeli counsel for client work.
- **References you upload:** client product shots or faces sent to a hosted route are a privacy decision per route: Higgsfield API terms may train on content unless the workspace opts out (effective within 10 business days, prospective only); BFL non-EU hosted terms permit training; OpenAI Images API no training but 30-day retention (dated 2026-10-01 in `dated-model-routes.md`). Read the route's current terms first; use synthetic references when unsure.
- **Motion transfer / lip-sync:** consent for the source performer; the retained source; do not imply endorsement.
- **Minors:** Seedance-style prompts avoid age words (route filter behaviour, a community claim, unverified; describe by role, clothing and action). Skill safety default (not from the research): do not generate realistic children for ads or testimonials; stop and ask the human.

### 4. Disclosure plan (one table per project; fill from the dated platform module)
```
destination      | what must be disclosed (per platform-specs.md)      | where/how (setting name as of checked_at) | who enables | done
YouTube          | meaningful AI generation/alteration of photorealistic people, events, places | Studio -> Attributes -> "AI use" (older name "Altered content" is stale) | owner | [ ]
Meta organic     | photorealistic video or realistic audio created/altered | the platform disclosure tool | owner | [ ]
TikTok organic   | realistic AI image/audio/video | creator AI label | owner | [ ]
TikTok non-Spark ad | fully AI / significantly modified | AI disclaimer toggle (duplicating a campaign RESETS it) | agency/owner | [ ]
EU audience      | provider marking + deployer visible/audible deepfake disclosure are separate duties (Art. 50 reported applying 2 Aug 2026; amending instrument unverified) | ask counsel | client | [ ]
```
Rules: AI music is an explicit disclosure example on YouTube; automatic labels (C2PA/internal detection) cannot be removed or adjusted; **never strip metadata to evade labelling**; record the AI stages and rights in a production manifest (provider, model id, route, date, reference rights); inspect final-export metadata; a disclosure label does not cure a deceptive claim (TikTok deceptive-practices policy). Treat the row wording as `checked_at` of the platform module, not today: if that module is past its `expires`, say so and ask the human to check the live help page.

### 5. Output of this step
A `DISCLOSURE` line in the delivery note: destinations, the setting to enable, who enables it, the `checked_at` of the module used; a consent list (person, use, release on file yes/no); a claims list (each factual claim with its approver). Any `no` on consent/claims = blocked for that destination, with what would unlock it. A missing platform module or an expired one = `blocked` for the disclosure line, not "none required".

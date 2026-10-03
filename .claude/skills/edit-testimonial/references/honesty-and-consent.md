---
module: edit-testimonial-honesty-and-consent
checked_at: 2026-10-02
expires: "90 days (2026-12-31) for the legal pointers and disclosure wording; the procedure itself does not expire"
confidence: "procedure: owner rules; law: SOURCED-unverified summaries, not legal advice, jurisdiction-scoped"
---

# Honesty, consent and disclosure for testimonials

Load when: building the claims table, writing the consent line, handling a client request that bends the truth, or choosing what may leave the machine. Sources: distilled 02 video-types §4.4-§4.5; distilled 08 legal-and-licensing §4, §9 (2026-10-01). **Not legal advice; the law of the audience's country and the client contract decide.**

| Field | Value |
|---|---|
| Fact set | consent record; claims table; legal/disclosure pointers |
| `checked_at` | 2026-10-02 (sources read 2026-10-01) |
| Scope | an Israeli studio publishing to Meta/TikTok/YouTube audiences; a student in another country substitutes local law |
| Non-spending refresh | read the official pages named in `agent-content/references/platform-specs.md` section 4 and `docs/en/legal-guide.md`; never upload footage to test a provider's policy |

## 1. The consent record (the `CONSENT` line in BRIEF.md and `claims.json.consent`)
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

## 2. The claims table (`hf/claims.json`, checked by `scripts/claims_check.py`)
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

## 3. Edge cases (blocking unless stated)
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

## 4. Fake or synthetic testimonials (the refusal)
If asked to write, generate or voice a customer who did not exist or did not say it: decline plainly, explain that fake and AI-generated testimonials are prohibited advertising/consumer-protection practice in many jurisdictions (a US rule has been in force since 2024-10-21, `[SOURCED-unverified]`, ftc.gov press release 2024-08; consumer law in the target market applies), and offer the honest routes: a real customer, a quote card with consent, or a founder-to-camera piece (`edit-talking-head`).

## 5. AI disclosure and C2PA (route-specific, dated)
AI disclosure, rights/likeness, content eligibility and provenance are four separate checks. If any AI B-roll or AI audio is used (illustrative only), disclose it on the route's own setting; the current field names and rules are in `agent-content/references/platform-specs.md` section 4 (YouTube: Studio Attributes "AI use"; TikTok ads: the AI-disclaimer toggle, reset when a campaign is duplicated; Meta: the disclosure tool for photorealistic content). A label never cures a deceptive claim. Never strip metadata to evade labelling. Date-stamp each platform step; wording changes quickly.

## 6. Contract notes worth putting in front of the client (for counsel to tailor)
Input authority (who guarantees releases and rights), AI scope (no synthetic speaker), provider schedule (where footage goes), voice/likeness release attached, distribution and disclosure responsibility, deletion/return of source, and a SEPARATE explicit grant for portfolio or course reuse: a client editing licence does not clear student fixtures or promotional reuse. (src: distilled 08 legal §10)

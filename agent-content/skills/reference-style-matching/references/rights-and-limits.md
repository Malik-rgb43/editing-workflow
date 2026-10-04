---
module: reference-style-matching-rights
checked_at: 2026-10-02
expires: "180 days (2027-03-31) for the legal posture; earlier on any change of music/font licence terms"
confidence: "design policy from official guidance read 2026-10-01; not legal advice; no Israeli ruling on style imitation or AI-output ownership was found"
---

# Rights, privacy and limits of style transfer

Load when: procedure step 7, or any time an asset, song, font, logo or person from a reference could reach the plan. Sources: distilled 06 reference-analysis §3 "What NOT to copy" and §4.6; distilled 08 legal-and-licensing §6 and §9; T16 findings (2026-10-01). Jurisdiction and commercial clearance are project-specific; counsel decides disputed cases.

| Field | Value |
|---|---|
| Fact set | what may be taken from a reference; rights ledger; music/font posture; legal framing |
| `checked_at` | 2026-10-02 (sources read 2026-10-01) |
| Source | US Copyright Office circulars 14 and 33 and the AI Part 2 report (human authorship, derivative works) as read by T16; WIPO copyright page; the author's rule "grammar not assets" |
| Scope | design policy for a studio; Israel-specific clearance NOT established |
| Confidence | official US guidance `[VERIFIED-external]` for the idea/expression distinction; everything about close imitation is a project-specific unknown |
| Non-spending refresh | read the official pages; ask counsel for any close imitation, a client ad built on a reference, or a creator-identifiable look |

## 1. What to take and what never to take
| Take (grammar, as measured rows) | Never take (assets and identity) |
|---|---|
| pacing, event density, transition types, camera rhythm | the reference's footage, frames, voice-over, music, logos, characters, on-screen people |
| type system: size, weight, position, motion | a paid font the studio does not license: use the nearest licensed match (OFL / Adobe web kit / bought) |
| palette STRUCTURE (ground + one accent) | the reference's brand identity when the client has one (client colours win); another brand's signature colour |
| music BPM and energy SHAPE: choose a licensed library track | the reference's song; a trending sound (organic-only at best, `License: unknown` = not in client work) |
| SFX types and levels | third-party brand sounds or logos in ads: ask for written brand permission, otherwise out |
Also do not copy: the platform watermark, end card and jingle; the reference's flaws (its "improvements" list, an absent music bed); its length and structure; looks outside the pinned segment; its safe zones when our platform differs; AI-looking stills of people; exact scripts or distinctive creator identity.

## 2. Rights ledger per reference (`rights.json`, checked)
Record: `context` (`client_ad | client_organic | own_organic | study`), the reference's source URL or file, creator, acquisition authority (user-supplied / downloaded as a reference copy), licence (`unknown` is the honest default), `use: analysis-only`, `assets_taken_from_reference: []`, `music` (the reference song's status with `sync_licence: not_established`, and the REPLACEMENT track with file, `SOURCES.md` pointer, licence, `ads_allowed`, territory), `fonts` (file, licence), `logos_brands.reference_logos_used: false`, `people_likeness.reference_people_used: false`, `distribution` (`reference_in_student_repo: false`, `analysis_reports_shipped: false`).
Allowed replacement licences in the checker: CC0, CC-BY (credit kept), OFL (fonts), Mixkit (rendered client videos only, never redistributed), Pixabay, Pexels, paid subscription (plan matches the use), owned, synthesised. `unknown` and CC-BY-NC are blocked for client work. For a client ad the licence row must allow ads for that placement and territory (a TikTok Commercial Music Library track is TikTok-only).

## 3. Legal framing (design policy, not a safe harbour)
- US official guidance distinguishes original expression from ideas and methods; derivative-work contributions are protected without granting permission for the underlying work; AI copyrightability guidance addresses human authorship, not permission to reproduce reference content. This supports borrowing ABSTRACT pacing and composition principles while rebuilding original expression; it does not make close imitation safe.
- A measurable card confers no permission to reuse expression. Do not reproduce distinctive logos, branded characters, exact scripts, sound recordings, identifiable creator impersonation or proprietary assets just because the measurements are abstracted.
- Song identification (a recogniser match, a fingerprint) names a track; it is not a master or sync licence. Trending sounds are placement-specific at best.
- Israel: no ruling on AI-output ownership or on style imitation was found; the Copyright Act text read was an English translation superseded by later text. Do not promise a client exclusivity in anything derived from a reference.
- Never place a reference clip, a third-party analysis report or private client footage into the student repo or any course material.

## 4. Privacy of the reference and of the user's material
A private or confidential reference (a client's unreleased cut, a competitor's unreleased ad): analyse locally only; `--no-song-id`; no frame or audio upload to a video-understanding service; `snapshot --describe false` on any HyperFrames snapshot (frames otherwise go to a third-party model). A paid video-understanding service (dated prices in `video-analysis/references/volatile-facts.md`) needs a dated estimate and prior approval, and still cannot supply exact Hebrew subtitle timing, sub-second cut ground truth or music rights.

## 5. Limits of the method (say them when relevant)
Kinetic type and continuous-camera references hide graphic transitions from the cut detector; the automatic cut count was wrong in about 60 % of ad-promo videos until checked on frames. Sheets and zoom frames are downscaled. Camera push scale from face-width ratios is confounded by subject distance. Hebrew OCR from a model is a hypothesis; the dedicated OCR route has a Hebrew model, other popular OCR libraries may not (verify per version). A sample of one reference is one sample: a style is a distribution, not a median.

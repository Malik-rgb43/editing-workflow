# Consent, likeness, honesty and the disclosure plan

Load when: a real person's face, voice or name is involved, a client subject is factual (medical, product, price), the video will be uploaded, or "is this allowed / do I label it" is asked.

Source keys: d02 = distilled/02 video-types §6.6; d08 = distilled/08 (legal-and-licensing, platform-specs-and-ai-disclosure; read 2026-10-01); d05 = distilled/05. **This is a production checklist, not legal advice**; for likeness/voice releases and Israeli or EU law ask counsel (the research found no all-purpose release). Platform wording changes quickly: the per-route facts live in the DATED module `agent-content/references/platform-specs.md` (AI-disclosure rows expire after 90 days); re-open the destination's current help page before upload.

## 1. Four separate checks (a pass on one is not a pass on another)
1. **Disclosure/labelling** (platform and law) 2. **Rights and likeness/consent** (people, voices, third-party IP, music, fonts) 3. **Content eligibility and claims** (ads policy, medical/price claims) 4. **Provenance** (C2PA/metadata). A labelled or C2PA-signed asset is not automatically legal, recommended or monetisable; vendor commercial permission answers at most "may the vendor exploit this output". (src: d08 platform §8, legal §0)

## 2. Honesty and compliance table (blocking; owner rules)
| Situation | Rule |
|---|---|
| medical claims / titles | only the claims the clinician states, with the title the client uses by law (confirm with the client) |
| anatomy or fact contradicting the VO | G1 fail: regenerate or cut |
| third-party IP (a game, a character, a jingle) | organic only, never paid; for ads use original characters and licensed fonts/music |
| celebrities, athletes, politicians **or lookalikes** | never in paid ads; organic only as clear parody that does not touch the product; offer an original character |
| real people's likeness (motion transfer) | parody/organic; never imply endorsement; consent and the retained source are prerequisites |
| a customer, testimonial voice or result | **never AI-generated** (disqualifying in the testimonial rubric); route to `testimonial-editor` |
| synthetic staff, food or product shown as real | label it or make it clearly stylised; food/product in a paid ad must match what is actually sold |
| realistic synthetic people, places or events | always apply the platform's AI-content label and tell the author/client to enable it; end card "Made with AI" line when the platform or client needs it |
| facts on screen (phone, address, price, CTA) | visible placeholders listed for the client; never generated |
| an ad claim, price or before/after not verified with the client | blocking until verified (`ad-promo-editor` A1/A5) |

## 3. Consent and likeness gate (G10)
- **Real faces/voices:** written consent from the person for the specific use (a brand's permission to edit does not supply permission from every filmed person); a separate release schedule for voice and likeness; no cloning of anyone's voice without their own verified consent (one major provider's professional cloning accepts only your own verified voice); disclose an AI voice where the provider's policy requires it. Israeli privacy-protection guidance on name/image/voice and deepfakes exists (a 2022 document was only partially indexed): ask Israeli counsel for client work.
- **References you upload:** client product shots or faces sent to a hosted route are a privacy decision per route: Higgsfield API terms may train on content unless the workspace opts out (effective within 10 business days, prospective only); BFL non-EU hosted terms permit training; OpenAI Images API no training but 30-day retention (dated 2026-10-01 in `dated-model-routes.md`). Read the route's current terms first; use synthetic references when unsure.
- **Motion transfer / lip-sync:** consent for the source performer; the retained source; do not imply endorsement.
- **Minors:** Seedance-style prompts avoid age words (route filter behaviour, a community claim, unverified; describe by role, clothing and action). Skill safety default (not from the research): do not generate realistic children for ads or testimonials; stop and ask the human.

## 4. Disclosure plan (one table per project; fill from the dated platform module)
```
destination      | what must be disclosed (per platform-specs.md)      | where/how (setting name as of checked_at) | who enables | done
YouTube          | meaningful AI generation/alteration of photorealistic people, events, places | Studio -> Attributes -> "AI use" (older name "Altered content" is stale) | owner | [ ]
Meta organic     | photorealistic video or realistic audio created/altered | the platform disclosure tool | owner | [ ]
TikTok organic   | realistic AI image/audio/video | creator AI label | owner | [ ]
TikTok non-Spark ad | fully AI / significantly modified | AI disclaimer toggle (duplicating a campaign RESETS it) | agency/owner | [ ]
EU audience      | provider marking + deployer visible/audible deepfake disclosure are separate duties (Art. 50 reported applying 2 Aug 2026; amending instrument unverified) | ask counsel | client | [ ]
```
Rules: AI music is an explicit disclosure example on YouTube; automatic labels (C2PA/internal detection) cannot be removed or adjusted; **never strip metadata to evade labelling**; record the AI stages and rights in a production manifest (provider, model id, route, date, reference rights); inspect final-export metadata; a disclosure label does not cure a deceptive claim (TikTok deceptive-practices policy). Treat the row wording as `checked_at` of the platform module, not today: if that module is past its `expires`, say so and ask the human to check the live help page.

## 5. Output of this step
A `DISCLOSURE` line in the delivery note: destinations, the setting to enable, who enables it, the `checked_at` of the module used; a consent list (person, use, release on file yes/no); a claims list (each factual claim with its approver). Any `no` on consent/claims = blocked for that destination, with what would unlock it. A missing platform module or an expired one = `blocked` for the disclosure line, not "none required".

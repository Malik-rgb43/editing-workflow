# Legal guide for AI video editing — student edition

> **This is not legal advice.** It is a study guide written on **2026-10-02** from research read on **2026-10-01**. It was written for an editor working in **Israel**, with notes on the **United States** and the **European Union** because AI-video work usually crosses borders. If you work in another country, replace the local-law parts with your own law — this guide cannot do that for you. Terms of vendors and platforms change often; every dated statement here must be re-checked on the day you generate, download or publish. Nothing here creates a licence, authorises an upload, or clears any asset. Qualified counsel must decide the specific gates named in section 13 before the affected activity.
>
> Evidence tags: `[VERIFIED-external]` confirmed against a primary source and re-checked · `[SOURCED-unverified]` one source, not re-checked · `[IDEA]` a proposal · `[MEASURED-lab]` measured in the research (not used for legal points). Source pointers are to the research record (`distilled/08`, `T18`) and to the official pages named in the text.

<a id="scope"></a>
## 1. What this guide is and is not

**It is:** a map of the questions a professional AI video editor must be able to answer, with the current official positions we found, their dates and their limits. **It is not:** a contract, a release form, a licence, an opinion on your project, or a promise that anything listed is safe. Where we found no source, we say "not found" instead of guessing.

How to use it: read sections 2-5 once; use sections 6-10 when a project touches AI output, disclosure, client footage, voices or music; use section 11 when you write or review a client agreement; use section 12 before you deliver or publish. Section 14 lists what the research could not verify.

<a id="six-questions"></a>
## 2. The six rights questions — keep them separate

Every asset, model output and delivery raises six different questions. A paid plan answers **at most the first one**.

| # | Question | What a "yes" needs |
|---|---|---|
| 1 | May I exploit this output commercially under the vendor's terms? | the exact route, model, plan and date; vendor terms (and partner-model terms) |
| 2 | Is the result protected by copyright, and who owns it? | human authorship in the result (section 6); a written assignment or licence from you to the client |
| 3 | Does it infringe a third party's rights? | your own checks; no vendor guarantee covers this (many vendors give no output warranty) |
| 4 | May I depict this person or imitate this voice? | the person's written consent for the specific use (section 9) |
| 5 | May I upload this footage to this service? | the client's and filmed people's permission and the provider's data terms (section 8) |
| 6 | For the course repository: may the file be **redistributed**? | an explicit licence that allows redistribution (sections 3-4) |

A rendered MP4, an editable project, a template, a model checkpoint and a repository asset are **different deliverables with different rights**. For every asset, model and font keep a record: source, file hash, rightsholder, licence name and version, account plan, date obtained, permitted media, territory, term, required credit, and where the evidence is stored. `[IDEA]` (src: T18 LEGAL_GUIDE §1)

<a id="repo-contents"></a>
## 3. What the repository may and may not contain

The course repository is distributed to students, so the strictest question (6) applies to everything in it. `[SOURCED-unverified]` (src: blueprint SECURITY_AND_LICENSING §2)

**May contain (bundle):** original examples and code written for the course; exact, permissively licensed components **with their notices**; individually documented fonts under the SIL Open Font Licence, CC0 or CC-BY files — **only** when the non-copyright rights (privacy, publicity, moral rights) of anything depicted are also cleared.

**Link, do not bundle:** proprietary services; restricted libraries; model weights or conversions whose licence chain is unresolved; files from Mixkit, ElevenLabs Music, Artlist or Suno; Adobe and Apple fonts; **FFmpeg binaries** (the course gives install instructions because LGPL, GPL and non-free builds carry different duties and codec patents are a separate question); vendor skill texts (study only, never copied).

**Never ships:** client or owner footage, transcripts, session logs, memory files, brand kits, analyses of third-party videos, and **any file whose licence is unknown**.

**Before every release** the maintainers generate a file-level bill of materials from the actual pinned tree, reconcile it with the research register, close every unresolved row the tree contains, include notices, and test that no restricted stock, client recording, proprietary font or unlicensed checkpoint entered the download. As of 2026-10-01 **none of the 392 register rows was cleared** and 114 were unresolved, so the default is *link, not bundle*. (The register is a candidate list, not a software bill of materials.)

<a id="licence-obligations"></a>
## 4. What each kind of licence asks of you

| Licence | You must | You must not |
|---|---|---|
| **MIT** | keep the copyright and permission notices; check the dependencies separately | assume the dependencies are also MIT |
| **Apache-2.0** | include the licence, required notices and mark your modifications | imply a trademark grant or endorsement |
| **GPL / AGPL** | review distribution, corresponding-source and (for network use) integration duties before shipping | treat it as "forbidden for commercial work" — it is not — or embed it unnoticed |
| **SIL OFL (fonts)** | keep family credit, licence text and reserved names | sell the font file on its own |
| **CC-BY** | credit creator, source and licence; say what you changed | add restrictions; assume it clears privacy or publicity rights |
| **CC-BY-NC** | stay non-commercial | use it in client work |
| **Proprietary stock, music, fonts** | use inside the finished video as the licence allows | redistribute the source files |
| **Model weights and conversions** | read the licence of the **exact checkpoint** and where it came from | assume it inherits the licence of the code that runs it |

Examples from the research (dated 2026-10-01, `[SOURCED-unverified]` unless marked): HyperFrames is Apache-2.0; three.js and shadcn/ui core are MIT; **GSAP is under its own no-charge licence, not MIT**, and a competing visual animation builder needs written consent; **Remotion has a custom licence** (free for qualified individuals and very small for-profits; version-5 terms were announced as "upcoming") `[VERIFIED-external]`; FFmpeg is LGPL 2.1+ at baseline, with optional GPL or non-free parts; Depth Anything V2 is Apache-2.0 only for the Small model, the larger ones are non-commercial; Tencent Hunyuan 3D 2.1 excludes the EU, UK and South Korea; the person-matting model RVM is GPL-3.0 (so the course treats it as an optional, user-installed, internal-use plugin); SDXL-Turbo needs registration and has a revenue condition `[VERIFIED-external]`. The ONNX conversions of the Hebrew speech model have **no declared licence — do not redistribute them** `[VERIFIED-external]`.

<a id="unknown-licence"></a>
## 5. The rule for "licence: unknown"

**An unknown licence means no permission has been established. Do not use it in client work.** (course decision default Q2.) Some editors keep a looser personal rule — "unknown means organic only, on my own account" — but that is a **risk you accept for yourself**, not a permission, and it never covers ads, clients, or the course repository. Never swap an unknown licence for the licence of a "parent" project. A track you hear in a platform's trending list, a brand's jingle, a logo or a screenshot of someone's product is not licensed to you by the platform; brand sounds and logos are at best organic, and for ads you need written permission from the brand. `[SOURCED-unverified]` (src: T18 FINDINGS; blueprint SECURITY_AND_LICENSING §4)

<a id="ai-output"></a>
## 6. Who owns AI output? Positions by country (and their limits)

**United States.** The Copyright Office's report *Copyright and Artificial Intelligence, Part 2: Copyrightability* (**2025-01-29**) supports protection for **human expression** inside AI-assisted work, including a human's creative selection, arrangement and modification of AI material. It does **not** extend copyright to purely AI-generated material, and **prompting alone** ordinarily does not give enough creative control under the technology it examined. Registration guidance (**2023-03-16**) asks you to disclose more-than-minimal AI-generated material and exclude it from the claim. `[VERIFIED-external]` (src: https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf, https://copyright.gov/ai/ai_policy_guidance.pdf). These are agency reports and guidance, not statutes, and the research filed or assessed no registration. A 2024 report on digital replicas is a historical policy report — its recommendations are not enacted law, and it clears no imitation of a celebrity, no misleading endorsement and no state publicity right `[SOURCED-unverified]`.

**European Union.** Who is the author of AI output under EU copyright law was **not researched**. The AI Act's transparency rules (section 7) are about disclosure, not ownership.

**Israel.** The Copyright Act text the research could read was an **English translation that is explicitly superseded**; the current consolidated version could not be retrieved. Its general structure (originality; commissioned works; assignments and exclusive licences must be in writing) is useful for contract design, not as a certificate of current law. **No Israeli court ruling on who owns AI output was found.** `[VERIFIED-external]` for the limits (src: T18-S022, S023).

**What to do in practice:** keep the scripts, edit decisions, compositing steps and project versions that show **your human contribution**; sell a **written assignment or exclusive licence of the rights you actually hold**; say honestly that protection of purely AI-generated parts is uncertain; and **never promise a client "exclusive copyright in every generated pixel or voice."** `[IDEA]` + `[VERIFIED-external]` for the US position.

<a id="disclosure"></a>
## 7. Telling the audience it is AI — platforms, the EU, provenance

Four checks are separate: **AI disclosure, rights and likeness, content eligibility, and provenance.** A label never cures a prohibited or misleading claim, and a labelled or provenance-signed asset is not automatically legal or monetisable. `[VERIFIED-external]` (src: T17 FINDINGS)

- **YouTube:** disclose meaningful AI generation or alteration of realistic people, events or places; the field is now **Studio → Attributes → "AI use"** (older "Altered content" instructions are stale); AI-generated music is an explicit example. `[VERIFIED-external]` (https://support.google.com/youtube/answer/14328491)
- **Meta (organic):** disclose photorealistic video or realistic-sounding audio created or altered digitally. **TikTok (organic):** label realistic AI media; automatic labels cannot be removed. **TikTok (ads, not Spark):** a mandatory AI-disclaimer toggle, and duplicating a campaign resets it. `[SOURCED-unverified]` (TikTok pages dated September 2025 or unreadable to the verifier — re-check).
- **C2PA / Content Credentials** (specification 2.4, April 2026): signed provenance helps show a file's history; it does not prove an event happened; missing credentials are not evidence of falsehood; **never strip metadata to avoid a label.** `[VERIFIED-external]`
- **EU AI Act, Article 50:** the *provider* of a generator must mark synthetic output in a machine-readable way, and the *deployer* (you, when you publish a realistic "deepfake") must disclose it visibly or audibly. These are **different duties**; embedded metadata alone does not meet the second. The Commission describes general application from **2 August 2026**; institutions also report a December 2026 grace period for older systems. The legal instrument for that grace period was **not verified** and the consolidated text could not be read — **timing: not verified. Publish no deadline rule without an EU lawyer.** Whether an export for a European client triggers a duty depends on the actual deployment. `[SOURCED-unverified]` for dates (https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act, https://www.consilium.europa.eu/en/policies/artificial-intelligence-act/timeline-artificial-intelligence/)
- **Israel:** the research did **not** examine an Israeli AI-labelling rule (not researched) — ask Israeli counsel. Platform rules and consumer-protection rules still apply to misleading claims.

For AI-generated work, write the **disclosure plan for each platform route** in the project brief (`DISCLOSURE` line). Platform steps change — date every instruction.

<a id="privacy-footage"></a>
## 8. Client footage and cloud tools — checks before you upload

A client saying "please edit this" is **not** a release from the people filmed, and it is **not** permission for a vendor to train on the footage. `[SOURCED-unverified]` (src: T18-S007, S020)

**Check, in this order, before footage leaves your machine:**
1. **Eligibility before price.** May this footage go to a third party at all (confidential, medical, minors, employees, biometric, intimate content → stop and ask counsel; section 13)?
2. **Roles.** In an instructed edit the client is usually the "controller" and you the "processor"; if you use the footage for your own portfolio, dataset or training, you may become a controller. The label in the contract does not decide it — the real purposes do. (EDPB guidance; applies where the GDPR applies.)
3. **Who is filmed.** A brand's permission to edit does not supply permission from every person on screen. Identifiable footage is personal data; biometric analysis needs its own assessment.
4. **The exact provider route.** Payment is not confidentiality. Examples as of the research date: **Higgsfield API terms (updated 2 September 2026, §7.2) allow training on content unless the workspace opt-out is switched on; it takes effect within 10 business days and is not retroactive** `[VERIFIED-external]` (https://open.higgsfield.ai/terms-of-service). **Suno's terms (revised 2026-08-10, effective 2026-09-03) grant it broad rights over uploaded content, voice and likeness** `[SOURCED-unverified]` (https://suno.com/terms). OpenAI and Anthropic retention depends on the endpoint, the agreement and the workspace; consumer chat settings do not clear API or connector use `[SOURCED-unverified]`.
5. **Your own tools that upload without asking.** **`hyperframes snapshot` sends frames to Gemini for an AI description when a Gemini/Google key is present — always run it with `--describe false`**, in groups of at most five timestamps. That flag disables only that branch: remote fonts and remote asset URLs are separate network paths. `[PROVEN-internal]` + `[VERIFIED-external]` (src: distilled 04/08)
6. **Transfers and deletion.** If the GDPR applies, moving data outside the EEA needs a valid mechanism plus the other duties; Israel's adequacy status (if relevant to your transfer) is not permission to send data on to any model vendor. Write down retention and deletion, including backups and public links.
7. **Local first.** A local route (for example the CPU or Vulkan transcription profiles) avoids sending the audio — but only if downloads, telemetry, remote assets, plugins and logs are also controlled. A local model that calls a web tool can still send data out.

**Israel.** The Privacy Protection Law, **Amendment 13**, was approved on 5 August 2024 and came into force on **14 August 2025** (indexed official snippet; the gazette text was not authenticated). It widens definitions and enforcement, changes database registration and notification rules, and creates data-protection-officer duties for specified organisations. A smaller registration burden does not remove duties of security, lawful processing and purpose. Do not assume a small editor must appoint an officer — work out your real role. `[VERIFIED-external]` partial (src: T18-S006).

<a id="voice-likeness"></a>
## 9. Voice and likeness

- **A written release for a specific use.** Treat capture, training or cloning, generated speech, dubbing and publication as **separate activities**. A release should name the person and recording rights; the provider, model and where data is stored; permitted scripts or topics; languages; territory, media and term; paid advertising; compensation; permitted edits and approvals; withdrawal and deletion limits; and any sublicence. Exclude unrelated training, public voice libraries and future endorsements unless explicitly agreed. `[IDEA]` (src: T18 LEGAL_GUIDE §6)
- **Cloning a voice:** ElevenLabs Professional Voice Clone allows only **your own verified voice** — someone else's consent does not let you create their clone in your account `[VERIFIED-external]`. Use the voice owner's own documented route.
- **Disclose synthetic voices:** OpenAI's text-to-speech terms require clear disclosure to end users that the voice is AI-generated `[SOURCED-unverified]`; in the EU, realistic deepfake-style content needs visible or audible disclosure independent of metadata (section 7).
- **Israel:** before cloning a speaker or placing someone's likeness in an advertisement, have Israeli counsel assess the current Privacy Protection Law, defences, performers' rights and any sensitive context. The research found official discussion of profitable use of name, image and voice but could not read the full document `[SOURCED-unverified]` (src: T18-S025).
- **Data licences are not model licences:** the Hebrew speech datasets published by ivrit.ai carry purpose limits (training / academic research) and restrict identifiable voice simulation — do not use them as sample footage or as a voice-cloning fixture `[SOURCED-unverified]`.

<a id="assets"></a>
## 10. Music, sound effects, stock, fonts, models

| Item | What it gives | What it does not give |
|---|---|---|
| Mixkit sound effects | use in finished end products | redistribution; including them in a repo, tool or template |
| Eleven Music (self-serve plans) | commercial use per plan | libraries or repositories of the music; resale |
| Artlist | assets inside finished projects, per plan | feeding assets to AI services that claim output ownership; stand-alone libraries |
| Suno | commercial use through a permitted official download on the right plan | confidentiality; repo clearance |
| Poly Haven | CC0 assets | the site's text, thumbnails and API |
| TikTok Commercial Music Library | TikTok organic and paid, in the chosen region and placement | YouTube, Meta, X |
| YouTube Audio Library | YouTube; some tracks need attribution | other platforms |
| Adobe Fonts | finished video and graphics | transferring font files; shipping them |
| Apple San Francisco | Apple-platform UI mock-ups | video work in general |
| open-weight video models | read each checkpoint | "open" is not "free for every client" — LTX 2.5 needs a commercial licence from USD 10 M revenue; HunyuanVideo 1.5 excludes the EU, UK and South Korea including use of outputs |

`[VERIFIED-external]` for the Adobe Fonts, Eleven Music, Artlist and TikTok library statements; `[SOURCED-unverified]` for the rest (dated 2026-10-01). Per asset, keep a record (section 2). **Choose cleared ad music before the edit depends on a trending track.** Epidemic Sound, Musicbed, Soundstripe and Udio were **not reviewed**. A font installed on your machine is not proof that you may redistribute it.

<a id="contract-checklist"></a>
## 11. Contract checklist for an AI-editing service (to take to counsel)

This is a list of topics to discuss and tailor — **not boilerplate to paste**. `[IDEA]` (src: T18 LEGAL_GUIDE §9)

1. **Deliverables and acceptance:** MP4, stems, subtitles, editable source, templates, resolutions, revisions, objective acceptance checks.
2. **Input authority:** who answers for recordings, music, logos, performers and releases; how missing rights are found before processing.
3. **AI scope:** what enhancement, generation, dubbing or cloning is allowed and forbidden; human editorial approval.
4. **Provider schedule:** approved accounts, models, data locations, subprocessors, training controls and retention; approval when the risk changes.
5. **Voice and likeness:** attach the release schedule (section 9); script and topic approvals; no implied endorsements.
6. **Ownership and licences:** transfer or license only what you hold; reserve third-party assets, reusable tools and your pre-existing materials; **disclose that protection of purely AI-generated parts is uncertain**.
7. **Distribution and disclosure:** who is responsible for platform labels, visible disclosure and keeping provenance.
8. **Cost and retries:** approved spend, number of attempts, billing per accepted output, approval for expensive changes.
9. **Confidentiality and deletion:** source files, prompts, logs, public links, backups, practical limits to deletion, incidents.
10. **Risk allocation:** warranties, indemnities, limits, insurance, disputes, local-law requirements — against the real risk; **do not copy a vendor's broad customer indemnity into your client contract unchanged**.
11. **Termination and updates:** continued use of delivered output, return of source, revocation of access, changed provider terms.
12. **Portfolio and course reuse:** only with a **separate, explicit grant** — a client's editing licence does not clear student fixtures or promotion.

<a id="release-gate"></a>
## 12. Your own gate before you deliver or publish

For every client project, before delivery: (1) the rights record exists for every asset, model and font used; (2) you hold the consent and releases you need and the footage was uploaded only to routes you checked; (3) the platform disclosure plan is written and, where it applies, done; (4) no asset with an unknown licence is in the final; (5) a human approved the result; (6) you re-read any rolling terms on the **date** you generated, downloaded and published. Keep the evidence file with the project. If you cannot complete a step, the project is **not ready** — it is never "probably fine".

<a id="when-counsel"></a>
## 13. When to ask counsel (concrete triggers, not "always")

Medical or patient footage · children · employee monitoring · biometric identification · intimate content · a contested international transfer · voice cloning or an identifiable person's synthetic performance in an ad · a client contract that allocates AI risk or indemnities · any EU-facing deepfake-style content with a deadline question · bundling a GPL/AGPL component in something you distribute · publishing the course repository.

<a id="gaps"></a>
## 14. What the research could not verify

EU authorship of AI output · the operative EU instrument and date for the Article 50 grace period (EUR-Lex was blocked) · Israel's current consolidated Copyright Act and any AI-output ruling · the Amendment 13 gazette text and transition clauses · direct GDPR statute text (EDPB guidance was used) · per-provider data-processing, retention and indemnity terms for your upload route (OpenAI and Anthropic only partly read) · Meta's commercial-music rights (login-gated) · account-specific music rights · the licences of the larger part of the 392 register rows. A same-family reviewer re-checked 13 of 30 claims — this is **not** legal clearance.

<a id="refresh"></a>
## 15. Refresh

Dated 2026-10-02; re-check before every cohort and before every release (`agent-content/references/licences-bom-rules.md` holds the dated component facts; `agent-content/references/platform-specs.md` holds the dated disclosure steps). Hebrew counterpart: `docs/he/legal-guide.md` (same section ids). The privacy and security rules for the toolkit itself are in `docs/en/privacy-and-security.md`.

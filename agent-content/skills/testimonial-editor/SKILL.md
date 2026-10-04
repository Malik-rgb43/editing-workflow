---
name: testimonial-editor
description: >-
  Edit a customer testimonial, client review, student success story or case-study video from consented interview, Zoom or selfie footage into a short, honest, result-first cut with original proof and accessible captions. Triggers: testimonial, customer review, success story, endorsement video; עדות, המלצה, ביקורת לקוח, סיפור הצלחה, תלמיד ממליץ. NOT for the expert's own reel (talking-head-editor), paid offer ads (ad-promo-editor), or a fake or AI-generated testimonial (refused).
compatibility: >-
  scripts/ need only Python 3.9+. Market medians quoted in references come from the author's analysis of 10 references (9 of them 16:9), a small sample; the author's own numbers are a different format (9:16 selfie UGC).
metadata:
  version: "0.1.0"
  kind: type
  status: "specified; deterministic checks only; model eval not run"
---

# testimonial-editor

Turns a real customer's recorded words into a 30-90 s video a stranger can trust: the result first, in the customer's own words, with proof on screen, nothing stronger than what they said, accessible captions, and a clean ending. The skill's job is as much to refuse a dishonest cut as to make a fast one.

## Rules that outrank the rest of this file
1. **Consent first.** A `CONSENT` line in BRIEF.md (speaker, permitted uses organic / paid ad / website, platforms, term, signed date, evidence file, withdrawal contact, bystanders, cloud processing allowed) exists BEFORE editing and BEFORE any cloud upload (cloud ASR, frame description, generation). No consent line = `blocked`: only local read-only preparation continues; ask for the signed release. Ad use needs explicit ad-use consent; "please edit this" is not a release from the people filmed.
2. **No synthetic speaker.** Never generate, clone or alter a customer's voice, face, words or result with AI (no voice clone, no AI lip-sync that changes words, no invented review). This is refused, not routed. (A US rule banning fake and AI-generated testimonials has been in force since 2024-10-21; src: distilled 02 video-types §4.4, `[SOURCED-unverified]`; the target market's law governs.)
3. **Nothing stronger than the witness said or the evidence shows.** Hedges ("I think", "about", "בערך"), negations and limiters ("only", "רק") stay. Every number on screen was spoken; a spoken number is never "proven" by a screenshot that shows a different one. Reorder only where every statement stays true in its new context, and log each move.
4. **Proof is shown original.** Real screenshots and photos appear unmodified (the one exception to the screenshot-rebuild technique); animate AROUND them; a count-up is a separate chip. Blur personal data (names, account numbers) before any upload or publication.
5. **Result first.** The cut opens on a number or an extreme moment from the customer, with proof on screen by about 2 s; name and age go to a lower-third at 1-4 s.
6. **Local, free, private.** No paid action without a dated estimate and approval (`paid-spend-gate`); `snapshot --describe false` always; sensitive proof never leaves the machine unblurred. Illustrative AI B-roll only if disclosed on the platform route; stock B-roll is neutral mood and never stands for the client's life, product or results.
7. **PROMPT.md is approved by a human before the first line of build code**, also in autonomous runs (decision default Q6). House numbers (caption position, -14 LUFS, rail y 1450) are house preset v1, not platform law (decision default Q5). Skills are procedure, not permission.

## Inputs -> outputs
In: consented recording (selfie, Zoom, filmed interview; original file, not a WhatsApp copy), transcript, result evidence (screenshots, photos), brand assets, lengths and platforms. Out: a 30-45 s and/or 60-90 s cut + captions + proof overlays, `hf/SCRIPT.md` (timecoded paper edit and move log), `hf/soundbites.json`, `hf/claims.json` (claims table with source timestamps), the consent record, `final/<name>_<platform>_<hook>_<aspect>.mp4` + manifest (`video-variants-exporter` when there are several).

## Procedure
| # | Do | Artifact |
|---|---|---|
| 0 | Intake via `video-brief-intake`: lengths, platforms and route (organic vs ad), speaker lower-third text (name, age, role, credential), CTA in the customer's words, brand assets, consent line; `ls` the whole source folder (a camera original may sit beside the compressed one) | BRIEF.md + ledger |
| 1 | Transcribe locally (forced Hebrew; `hebrew-captions-transcription` route); hand-fix names and numbers; no LLM rewrite of the transcript | `words.json`, `transcript.txt` |
| 2 | Split into sentences by word times; score each 0-2 on specific / emotion / contrast / standalone / provable (+2 if it kills an objection); `scripts/soundbite_score.py` ranks them and proposes hook, close, body and three hook options | `soundbites.json` + table |
| 3 | Paper edit, NO render: timecoded text of the cut in `hf/SCRIPT.md`, blueprint by length (`references/blueprint-and-numbers.md`), result first, every move logged; show the text and get approval | `SCRIPT.md` |
| 4 | Claims table: every claim with source timestamps, original and used quote, numbers spoken and shown, evidence, presentation; `scripts/claims_check.py hf/claims.json --intended-use organic|paid_ad` must PASS (G1-G3) | `claims.json` |
| 5 | Proof: ask the client for matching originals; place them in `hf/assets/proof/` (PII blurred); where no matching proof exists use a typographic callout in quotes, not a screenshot | proof assets |
| 6 | Picture and voice prep: colour from the camera original for night/car/Zoom footage (`speaker-color-correction`); separate voice from noise, about 3:1 compression; trim silences inside kept segments to about 0.40 s; cover word-boundary cuts with a J/L cut, punch-in or proof insert; driving footage is flagged and a reshoot requested | clean plate and voice |
| 7 | PROMPT.md + DESIGN.md (every frame: what, where in px, when in frames, easing, sound) -> approval -> build: lower-third, optional persistent result headline, punch-ins, split-screen proof, captions, bed, end card | `hf/` project |
| 8 | Verify: `render-qa-delivery`; re-run `claims_check.py` on the final timeline if the cut changed; mute test; rubric T1-T8 (gates T1, T2, T5, `references/blueprint-and-numbers.md`); one full render per round | QA evidence |
| 9 | Present: the file at once, numbered changes, the claims table, the consent line, honest gaps; variants and ratios via `video-variants-exporter` | message |

## Gates
States are `pass | fail | blocked | n/a` with a reason. A timeout, empty sample or missing input is `blocked`, never `pass`. A successful tool call is execution evidence; a viewed render is appearance evidence.
| Gate | Predicate | Evidence | If false | Owner | Recheck when |
|---|---|---|---|---|---|
| G1 consent | complete consent record covering the intended use; cloud steps only if allowed | BRIEF `CONSENT` line; `claims_check.py` consent block exit 0 | block upload and publication; ask for the release | this skill | any new use (paid ad), platform or processing route |
| G2 honest claims | no hedge, negation or limiter dropped; no number introduced; used words are the original words in order; every on-screen number spoken; reorders logged | `claims_check.py` exit 0 on the current cut | restore the words, cut the claim, or soften the presentation | `claims_check.py` + human reading | every re-cut |
| G3 no synthetic speaker | no AI voice/face/words/result; any AI B-roll illustrative and disclosed | `synthetic` block in `claims.json`; SOURCES.md rows | remove it; disclose or replace | this skill | any new asset |
| G4 result first | result or extreme moment within the first seconds with proof by about 2 s; soundbites scored; hook line <= about 4.5 s with the number by 3 s | scoring table; frame at 0-3 s viewed | re-order within meaning-preserving limits | this skill | any re-cut |
| G5 proof originals | each shown number has an original proof or a quoted callout; screenshots unmodified; PII blurred | proof files; `claims_check.py` PROOF_* and PII codes | replace rebuilt proof with the original; ask the client | this skill | new proof asset |
| G6 captions and audio | accurate captions (zero spelling errors in names, numbers, quotes), contrast and reading rules, rail <= y 1450, voice intelligible, final -14 +/- 0.5 LUFS and TP <= -1 measured on the final file | `caption_qa --band <top>:1450` coverage statement, human proofread, `qa delivery` | repair | `hebrew-captions-transcription`, `render-qa-delivery` | any caption or mix change |
| G7 rubric and mute test | rubric average >= 4.0, no dimension < 3, gates T1/T2/T5 > 2; the whole story understood muted | critic report with timecodes | fix and re-review changed ranges | critic + this skill | each draft |

## Numbers (defaults, with their limits; details in references)
- Lengths: 30-45 s social/ad cut, 60-90 s long cut; market median 47 s (10 references, 9 in 16:9). Visual change at least every 3 s (market 19.7 cuts/min, median shot about 2.4 s); the author's own selfie testimonials ran 55 s with a shot of 4.85 s: the gap to close, not a target.
- Lower-third once at 1-4 s; end on the strongest emotional line on the face, then CTA/logo in <= 3 s with no trailing black.
- Captions: word-pop 1-3 words, always an animated exit, digits for numbers, centre about 63-73 % of height for organic and <= 58 % for paid Meta 9:16 (author's placement; verify on a real device).
- Music bed 12-18 dB under speech, out for the crisis, back at the turn; SFX at most one soft ding per proof entry; house master -14 LUFS, TP <= -1.

## Decision rules
| If | Then |
|---|---|
| the client asks for a stronger line than the speaker said | refuse; offer a re-ask on camera, the strongest TRUE line, or the proof |
| a spoken number has no matching screenshot | typographic callout in quotes, ask the client for the original proof; never pair it with a different number |
| the strongest line is a hedge ("I think it helped") | keep the hedge; lead with another claim, a pain or a twist; never headline it as a guarantee |
| no sentence carries a number | open on a pain or twist, say why; never invent one |
| consent covers organic only but a paid ad is wanted | the ad version is `blocked`; the organic cut may proceed; ask for ad-use consent |
| footage is dark, noisy or filmed while driving | fix what is fixable (colour, voice); flag the rest and ask for a reshoot; do not hide it in an ad |
| the speaker is a minor, or the result is medical or financial | stop and escalate to the user: consent and claims need counsel before any edit goes public |
| the user wants AI B-roll | illustrative only, disclosed on the route, through `paid-spend-gate`; never the client's life or result |

## Blocked states (report them, do not work around them)
No consent line; consent narrower than the intended use; a claim with `CRITICAL_TOKEN_DROPPED`, `PROOF_CONTRADICTS` or `NUMBER_INTRODUCED`; synthetic speaker requested; PII proof unblurred and headed for upload; transcript not hand-checked; a `not_run` QA gate. Each is a reason to stop and say what unlocks it.

## Pitfalls that each cost time or trust
Name and age first with the result at 40-74 % of the video; 81-225 s left uncut; a screenshot of one number shown beside another spoken number; hedge cut out so "I think it helped" became "it helped"; proof rebuilt in HTML; a lone static shot of 16-56 s; an equal 3-way Zoom stack instead of the speaker full-frame; driving footage in an ad; a hook promising a number that arrives at 30 s; AI B-roll presented as the client's life.

## References (load when)
- `references/blueprint-and-numbers.md` - writing the paper edit, choosing hooks, visual grammar, rubric T1-T8, market vs owner medians.
- `references/soundbite-scoring.md` - scoring sentences, worked example, interview technique for the brief.
- `references/honesty-and-consent.md` - consent record, claims table fields, edge-case rules, release schedule, disclosure and legal pointers, what to say when asked for a fake.
- `references/accessible-captions-and-audio.md` - captions, contrast, reading speed profiles, native vs burned, voice clean-up, levels.
- Other skills: `video-brief-intake`, `hebrew-captions-transcription`, `speaker-color-correction`, `render-qa-delivery`, `revision-notes-handler`, `video-variants-exporter`, `paid-spend-gate`; platform disclosure rows live in `agent-content/references/platform-specs.md`; benchmark rubric `agent-content/benchmarks/testimonial.rubric.md` (owned elsewhere; the condensed T1-T8 here is the working copy).
- Scripts: `scripts/soundbite_score.py`, `scripts/claims_check.py` (both stdlib, Usage docstring, `--self-check`, exit 0 / 1 / 2).

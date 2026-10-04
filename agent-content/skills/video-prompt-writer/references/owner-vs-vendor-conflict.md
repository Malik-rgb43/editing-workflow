# [CONFLICT] owner prefixes vs the vendor contract - surfaced, not resolved

Load when: the user asks "which is right", pastes the vendor contract, complains that a prompt "breaks the rules", or before recording a preset choice.

Status: **unresolved by evidence.** Every claim below is single-source and was never executed here (no generation was run, spend was zero). The research tagged these as `[CONFLICT]` in distilled/05 prompting (Contradictions) and Q7 (decision default, revised 2026-10-03: ship the cinematic owner prefix as the one named preset, labelled as an owner preference; link the vendor contract). The skill's job is to make the choice explicit and recorded, never to hide it.

| # | Topic | Owner preset (`owner-cinematic`) | Vendor contract (`vendor-short`; dated, see `vendor-contract-dated.md`) | What this skill does |
|---|---|---|---|---|
| C1 | Quality charms | the cinematic prefix opens "8K cinematic. Photorealistic" and ends "8K detail"; quality charms the vendor contract says to delete | delete words no camera, light meter or stopwatch can measure (cinematic, epic, stunning, beautiful, masterpiece, 8K...); name a lens, light direction, movement or number | keep the author prefix as a unit (exempt from the lint's charm check); apply the anti-slop rule to the scene body |
| C2 | Negatives | scoped exclusions are fine: "no 3D render, no game engine", "NO eye glow", "No music. No subtitles."; tight rule: a negative about an ACTION makes things worse | everything positive; only the quality line "avoid jitter and bent limbs" and explicit exclusions; community: Seedance 2.0/Cinema Studio 3.0 do not support negative-prompt syntax (Veo does) | negatives only in the prefix and CONSTRAINTS; the lint warns on negatives in ACTION/CAMERA (owner) or the whole main block (vendor-short) |
| C3 | Numbers | "generalize physics": describe broadly with real weight and gravity; exact km/h and degrees break physics | give speeds numerically in km/h ("the car passes at 60 km/h"); abstract fast/slow is not understood; atmosphere in percent and metres | warn on numbers in owner presets, info in vendor-short; do not pick a winner |
| C4 | Length | ~15 s prompts with a long prefix (hundreds of words) | 60-100 word main block, past 300 words the model loses the prompt; community: 30-100 words, under 200 | not comparable: different tools and budgets; the author prefix is long by design; never mix the two budgets in one prompt |
| C5 | Beat density | fill all 15 s; 2-3 shots in practice | 12-15 s: 2-3 beats; community has two tables (up to 6 beats in 12-15 s) | lint warns outside 2-6 shots |
| C6 | Real faces | n/a | reference-to-video with real faces failed/flagged 7/7 on one model in an owner project (2026-09); MiniMax worked | use synthetic characters; test ONE take before a batch (a paid action: `paid-spend-gate`) |
| C7 | Age words | owner skeleton: describe by role/clothing | Seedance rule: never age words (boy, girl, child, kid, young, teen, little); the same community text uses age ranges for non-Seedance models | treat as Seedance-specific; lint errors unless `--allow-age-words` |

## How to settle it (the only honest way)
Not by argument and not by authority: by ONE controlled sample, approved through `paid-spend-gate`: the same shot, same references, same route and settings, two prompts that differ in exactly ONE variable (for example numeric speed vs "brisk pace", or prefix on vs off). The author picks by looking. One pair is an anecdote, not a result: record the route/model id, price timestamp and both outputs (ffprobe + sha256) so a later pair can add evidence. Until then the skill labels every preset "owner preference" and says "untested on this account".

## One-line wording for the user
"The author preset (cinematic film) and the vendor-short profile disagree on quality words, negatives and km/h. I used `<preset>` (owner preference, untested on your account) and recorded it; tell me if you want the other one."

## What never changes between presets
Plain-text fence output; standalone prompts; tags that match Element names exactly; timecodes filling the clip; text and Hebrew added in post; no real names/brands/IP; no spend decisions here.

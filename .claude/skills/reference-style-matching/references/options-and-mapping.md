# Mapping the reference onto the user's material, and the three options

Load when: procedure steps 5-6. Source: distilled 06 reference-analysis §3 steps 4-6 (2026-10-01). Checked by `scripts/style_card_check.py options`.

## 1. Map by function and density, never by seconds
1. Get the user's transcript with word times (`transcribe`, forced Hebrew; names and numbers hand-checked). Structure (silence-cut vs rebuild), length and ratios come from the intake ledger, NOT from the reference.
2. Label each reference beat by FUNCTION: `hook, pain, turn, proof, payoff, cta, other`. Label each user sentence by function.
3. Map function to function. Keep the reference's DENSITY (events/min, transition mix, zoom rhythm). Do not stretch the reference's timing over a different voice-over length.
4. Where the reference has no beat for a user function (or the user has no material for a reference beat), say so in the beat map and decide: drop the device, or ask for material.

| Ref beat (t) | Function | Ref device | User beat (t from words) | User line | Mapped device |
|---|---|---|---|---|---|
| 0.0-1.4 | hook | number slams in, punch 115 % | 0.0-2.1 | "..." | same, on the user's number |

Beat-map rows go in `style_dna.json` `beat_map[]` (`function` and `mapped_device` are required).

## 2. The three options (always three; the user picks one or mixes per beat)
`options.json` holds exactly `Faithful`, `Elevated`, `Twist` in that order. All three decide the same keys (at least 6: for example `pacing, hook, transitions, type, camera, palette, sound, broll, structure`) so they can be compared; any two differ in at least 3 of those decisions.

| Option | What it is | Hard rule (checked) |
|---|---|---|
| **Faithful** | the closest translation of the reference's grammar onto the user's material | every DNA row within its tolerance; `deviate_rows` empty |
| **Elevated** | the reference's grammar plus upgrades from the toolbox | `upgrades[]`, each `{device_row, upgrade, why}`: it names the DNA row it upgrades and why; upgrades are chosen by the MEANING of the beat |
| **Twist** | a bold reinterpretation | keeps 1-2 signature devices (`kept_devices`: DNA row ids) and changes exactly ONE axis (`changed_axis`: world, medium, pov or structure) |
Every option also carries: `pitch` (one line and what the viewer feels), `decisions{}`, `cost`, `risk` (render time; any paid step with a dated estimate via `paid-spend-gate`; what could fail and the fallback), `keeps_ledger: true` (it obeys every locked ledger line: length, structure, ratios, filename, brand), `borrowed_devices` (DNA row ids). Exactly one option has `recommended: true` and a `recommend_reason` (Elevated when the bar is premium, otherwise the one that fits the brief).

What each option ships to the user: a beat table (`time -> what we see -> reference device borrowed -> tool`), 3-4 key stills (a quick mock + `snapshot --describe false`, at most 5 timestamps per call) or a text storyboard, and the cost/risk. Ask the user to choose Faithful / Elevated / Twist / "mix per beat" (a mix = a per-beat pick table made after the three exist). If the hesitation is purely aesthetic (fonts, easings, palettes), build a `visual-choice-board` instead of asking in chat.

A user who has already chosen an option (and said so) does not need the three-option ceremony repeated: record the chosen option and proceed (T16: the compulsory ceremony is dropped for a decided user; the checks on the chosen option stay).

## 3. Elevated toolbox (pick by meaning; say why per beat)
- 3D: a modelling tool for photoreal or hero objects and lighting; a procedural 3D engine for data-driven, many-instance or 3D UI pieces (must be seek-safe in the render engine).
- UI/component motion language (curves, blur-out-up words, sequential chat with typing dots) re-implemented in the engine's seek-safe animation library; third-party registry components need their own licence check.
- Data-driven animation (counters, charts from real numbers); the user's own transitions before stock; cutout with graphics behind the speaker; a spline camera or shared motion kit.
- Never "reference look only" at a premium bar: the reference's grammar is the floor, B-roll and motion-graphics beats are added (that is what makes it Elevated).
Type skills own the build: `talking-head-editor`, `ad-promo-editor`, `motion-graphics-builder`, `ai-generated-video-editor`, `testimonial-editor`.

## 4. Into the spec
1. `hf/STYLE_DNA.md` = the card + beat map + chosen option; each row keeps its tolerance or `deviate: <reason>`.
2. The rows become `R` ledger lines (one line = one checkable claim; `src: R`; the user's Hebrew wording verbatim where it exists); every ledger id appears at least twice in PROMPT.md (`grep -o "R[0-9][0-9]" hf/PROMPT.md | sort | uniq -c`).
3. PROMPT.md `<direction>` states "in the grammar of <ref-id>: <numbers>". PROMPT.md is approved by a human before the first line of build code.

## 5. Side-by-side check after each render
1. Re-run `video-analysis` on the draft with the SAME `--detail` and tool version; `fidelity_diff.py style_dna.json --draft analysis/<draft>` (rows without `source_key` come from `--manual` values measured with `px_measure.py` or a zoom).
2. Matched stills at the mapped times (`sheet --at t1,t2,t3,t4` on reference and draft): compare type size and position, grade, density.
3. Fix every `flag`, or list it as a gap with the user's OK; `not_measured` rows block "ready". The ledger goes to `fidelity.md` and `hf/QA.md`.

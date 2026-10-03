# Task evals: reference-style-transfer

Status: specified; deterministic oracles only. Model eval not run (decision default Q4). Fixtures are synthetic or rights-cleared (an ffmpeg-generated 15 s "reference" with known cut rate, a known flat-colour accent text card and a known loudness is enough). A real third-party reference may be used by a person in a private session, but its frames, clip and analysis never enter fixtures or the repo.

## T1. The DNA card is built from measurements
- **Setup:** a 10-20 s synthetic reference: cuts every 1.1 s (cuts/min about 54), a flat `#F2C230` accent block with caption text at a known position, a 128 BPM bed. Run `video-analysis` (reviewed, exit 0) then the skill up to the card.
- **Oracle:** `style/analysis/<ref-id>/style_dna.json`; `python scripts/style_card_check.py card style_dna.json --root .`; `px_measure.py sample` on the accent block.
- **Pass:** exit 0; all 11 dimensions have a row or an `na_reason`; the pacing row has `source_key` and equals the analysis value; the accent hex row says `source: fullres_png`, `flat_fill_std <= 12` and equals `#F2C230` within 3 levels per channel; the BPM row is an estimate with its tolerance; the font row is a nearest match with confidence L and a licence; the pinned segment is `pinned_by: user`; cut count was verified on frames (analysis `review` present).
- **Fail:** a number typed from looking at a sheet; a hex from a contact sheet; a font "identified" with confidence H; a card with no analysis hash.

## T2. Three options that really differ
- **Setup:** the T1 card plus a user brief (a 20 s offer video, user footage, a user-chosen palette).
- **Oracle:** `options.json` and `python scripts/style_card_check.py options options.json --card style_dna.json`.
- **Pass:** exit 0; Faithful / Elevated / Twist in that order; the same decision keys; any two differ in at least 3 decisions; each states cost and risk; exactly one recommended with a reason; Elevated lists upgrades that name a DNA row and why; Twist keeps 1-2 devices and changes exactly one axis; the user's palette is recorded as a `deviate` where it overrides a reference colour; the beat map maps by function (hook, pain, turn, proof, payoff, CTA), not by seconds.
- **Fail:** two near-identical options; Twist changing two axes; no cost/risk; options that ignore a locked ledger line (length, ratio, filename).

## T3. Rights guard
- **Setup:** the reference uses a recognisable trending song and a paid display font; the user's context is a client ad.
- **Oracle:** `rights.json` and `python scripts/style_card_check.py rights rights.json`; the plan's asset list.
- **Pass:** exit 0; the reference song is `sync_licence: not_established` and flagged reference-only; a licensed or owned replacement exists with a `SOURCES.md` pointer and `ads_allowed: true`; the paid font is replaced by its nearest licensed match with a licence; `assets_taken_from_reference` is empty; no reference frame, clip, logo or voice is in the asset list; the report says a song match is not a licence and a trending sound is not cleared.
- **Fail:** the original track kept "because it matches the tempo"; an `unknown` licence; reference frames used as B-roll; a third-party analysis report shipped in a repo folder.

## T4. Fidelity ledger after a render
- **Setup:** the T1 card, an Elevated option chosen with two `deviate` rows, and two drafts: one inside the tolerances, one with cuts/min 60 % above the card.
- **Oracle:** `python scripts/fidelity_diff.py style_dna.json --draft analysis/<draft> --manual manual.json --out fidelity.md` (exit code and table).
- **Pass:** the first draft exits 0 (rows ok / info / deviate); the second exits 1 with the pacing row `flag` and a fix; a row with no draft measurement is `not_measured` and exits 2 (never ok); deviate rows are reported with their reasons; the agent fixes or lists the gap before presenting and does not claim "matches the reference" when a row is flagged.
- **Fail:** a blanket "looks the same"; skipping the re-measurement; counting `not_measured` as a pass.

## T5. The user has not pinned the style
- **Setup:** a reference with a before/after segment (0-8 s) and a final look (8-25 s); the user says only "like this".
- **Oracle:** the conversation and `reference.pinned_segment`.
- **Pass:** the agent lists the looks with time ranges (from the shot table) and asks which is THE style before building the card; the card's `pinned_by` is `user`; analysis rows are limited to the pinned range.
- **Fail:** analysing the whole video as one style; the agent choosing the segment itself.

**Self-checks:** `python scripts/style_card_check.py --self-check` (21 cases), `python scripts/fidelity_diff.py --self-check` (14), `python scripts/px_measure.py --self-check` (11; needs ffmpeg, reports NOT_RUN otherwise).

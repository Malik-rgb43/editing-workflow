# agent-content/benchmarks — rubrics, bands, critic and briefs

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint QA_AND_BENCHMARKS and research T13. **Design only: no runner exists; proposed fixture quantities and thresholds are not validated.** Acceptance thresholds belong in a preregistered owner contract; the historical kit A/B bars (+0.5 rating, 20 % savings, average ≥ 4) are historical, not research-proven standards.

| File | What it is |
|---|---|
| `talking-head.rubric.md` · `testimonial.rubric.md` · `ad-promo.rubric.md` · `motion-graphics.rubric.md` · `ai-generated.rubric.md` · `podcast-clip.rubric.md` | per-type rubrics in the **six dimensions** (meaning/story · caption/language · composition/brand · motion/edit · audio · integrity/continuity), anchors at 1/3/5, hard gates, severe-failure list, mapping to the owner's original criteria. Talking-head and podcast-clip are **derived and provisional** (the owner has no rubric for them) |
| `bands.json` | per-type metric bands (market and owner profiles, p25/median/p75, `n`), each with a source and a `house_preset` flag; QA tool thresholds; delivery profile. **Descriptive, not a quality score.** Unmeasured = `null` |
| `critic-brief.md` | the independent critic: creator ≠ verifier, changed ranges only after round 1, coverage declared, evidence classes, output contract |
| `visual-review-4-axis.md` | the four-axis review on all-frame sheets, severities, length scaling |
| `briefs/B01.md … B06.md` | the fixed benchmark briefs (anonymised, **synthetic assets only**): B01 talking head 45 s (HE/EN) · B02 vertical product ad 20 s · B03 motion launch 30 s · B04 AI film 30 s (frozen pool, no spend) · B05 testimonial 60 s · B06 engine fixture 12 s |

**Release rule (owner gate) used by every rubric:** average of scored dimensions ≥ 4.0, no dimension < 3, every hard gate ≥ 3, no severe failure, automatic QA all `PASS` with coverage; max 3 critic rounds; a dimension without evidence is `not_observed` (never 3); a check that could not run is `not_run` / `INSUFFICIENT_EVIDENCE` (never PASS). **A pass must mean the test ran on its coverage.**

**Two kinds of result are never mixed:** *technical QA pass rate* (all required gates / all assigned trials, with unsupported/blocked/failed disclosed) and *creative quality* (per-dimension human ratings and blinded preference). Within-engine hashes show repeatability for that pin; cross-engine SSIM is not creative equivalence. Independent human evaluation (Hebrew-fluent readers/listeners + target-audience viewers) is the primary creative endpoint; a model critique is secondary unless calibrated. Evaluator corpus ≠ toolkit-tuning examples. B01–B05 exist in Hebrew and English forms of equivalent complexity (not machine-translated).

Open gates before any claim: a held-out natural-video corpus, actual Claude trials, an independent human Hebrew/accessibility study, calibrated critic reliability, local VLM feasibility, authenticated Meta/Stories templates, final social-transcode and phone checks, cross-OS install, final version/licence review. (src: QA_AND_BENCHMARKS §9)

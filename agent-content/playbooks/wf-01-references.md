# wf-01 — References and style (רפרנסים וסגנון)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from blueprint WORKFLOWS §1, distilled/02 workflow-end-to-end §3, distilled/06 reference-analysis, distilled/01 rules-and-gates A6/C9.
> Legend: see [README.md](README.md). `[RULE-owner]` · `[PROVEN-internal]` · `[SOURCED-unverified]` · `[IDEA]` · `[CONFLICT]` · 💲 = paid step · OM = the reference machine (one Windows laptop; hardware details are intentionally not published).

| Field | Value |
|---|---|
| Stage | 1 of 9 |
| Owner skills | `reference-style-transfer` (a reference video to transfer), `video-analysis` (measurements, sheets, transcript, audio), `choice-board` (visual hesitation) |
| Artifacts (exact files) | `hf/STYLE_DNA.md` (+ 3 options, the chosen one marked) **or** `hf/references/MOODBOARD.md`; reference files under `hf/references/`; analysis folders under `_work/analysis/<ref-id>/` (`report.md`, `analysis.json`, `breakdown.md`, `metrics_override.json`) |
| Exit gate | **G1 — the person picked an option and the time range that "is the style"** |
| Target time | **15–30 min** (owner target). Analysis runtime is separate and measured only on OM: 9–23 min per video under load; a 140-video batch estimated at 4–5 h took about 9 h (CPU/RAM contention, 6 GB free) `[PROVEN-internal]` `[LOCAL-only]` |
| Paid steps | optional cloud video-understanding of a reference 💲 (none was run in the research; price/quality unverified) — default is **local** analysis |

## 1. Purpose and rule

Collect references at the level of the best in the world **before** designing, animating, grading or generating — "no reference, no execution." `[RULE-owner]` Take a reference's **grammar** (pacing, devices, type system, camera, sound shape) and **measure** it; never take its assets. With no reference video, run the moodboard path. Owner notes sent to several sessions on the same source were the same notes each time: they are **global style rules** (wf-09), not per-project fixes.

## 2. Entry gate

| Predicate | Evidence | If false |
|---|---|---|
| G0 passed (ledger locked) | gate log | back to wf-00 |
| a reference was named, or the ledger says "none" | ledger rows REF / the answer | ask (wf-00 branch table) |
| the person has the right to analyse the reference (their own file, a public link used for analysis only) | the person's statement; SOURCES.md row "reference only" | analyse a stills/metadata description instead; **never** reuse the reference's footage, frames, VO, music or logos |

## 3. Path A — a reference video exists (`reference-style-transfer`)

| # | Step | Who | Evidence / output |
|---|---|---|---|
| 1 | **Get the reference and pin the segment.** A local file is copied; a link is fetched only for analysis (update the downloader first — an old binary returned 403; an Instagram login wall → find the same video elsewhere). If it was already analysed (`ls _work/analysis/*/<ref-id>`) reuse it. **Several looks → list them with time ranges and ask with stills as previews.** Several references → give each a **role** (A = captions + type, B = pacing + transitions), one DNA card each. | agent + **human picks the range/role** | `hf/references/<ref-id>.mp4`; the range in `STYLE_DNA.md` |
| 2 | **Analyse** with `video-analysis` (measurements, cut detection on unique frames, keyframe sheets, transcript, LUFS, sound events, BPM/key/beats). **View every sheet and every audio image.** Exclude the platform watermark and end card from all numbers. **Correct the automatic cut count from the sheets** and write `metrics_override.json` — kinetic type, light leaks, whips, flashes, PiP and motion blur are mis-counted (wrong in about 60 % of ads; examples: 108 vs 42 and 89 vs 56 cuts/min; kinetic-type launches 44 % under to 67 % over). Zoom ONE instance of each distinct device frame by frame. A busy main context delegates steps 2–3 to a sub-agent that returns ≈ 10 lines. | agent | `_work/analysis/<ref-id>/…`, `breakdown.md` |
| 3 | **Style DNA card** — every row has a **number, where seen, how measured, confidence** H (measured ≥ 2 times) / M (once, read from sheets) / L (inferred, e.g. a font's identity). Dimensions: pacing (cuts/min, median shot, an event every N s) · hook anatomy (frame-0 content, first word/text/motion times) · transitions (type × count, frames, direction) · camera (punch-in %, push duration, pivot) · type (nearest font, px at 1080, weights, hex, position, words per card, entry/exit) · colour/grade (luma p1/p50/p99, saturation, skin hue, accent hex) · B-roll (types, % of runtime, full-bleed vs card) · layering (cutout, behind-speaker graphics, depth order) · sound (BPM, energy arc, music dB under VO, SFX per minute and dB) · end card · safe zones. Measure from pixels, not memory (5×5 median on a flat fill for hex; a scale conversion to 1080 px for sizes). **Font identity is `L`**: run the look-alike test (ו/ז, ד/ר, ה/ח) at final size on the chosen Hebrew font even if the reference's font looked right. | agent | `_work/analysis/<ref-id>/style_dna.md` |
| 4 | **Map the reference's beats onto the person's material:** transcript with word times (`transcribe`); the structure comes from the **ledger**, not the reference; label each reference beat and each of the person's sentences by function (hook, pain, turn, proof, payoff, CTA); map by **function and density, never by seconds**; never stretch the reference's timing over a different VO length. | agent | the beat map table |
| 5 | **Always three creative options:** **Faithful** (closest translation; all DNA rows within the stated tolerance), **Elevated** (the grammar + upgrades from our toolbox; each upgrade names the reference device it upgrades), **Twist** (keep 1–2 signature devices, change one axis). Each option: a one-line pitch, a beat table (`time → what we see → reference device borrowed → tool`), 3–4 key stills (a quick HF mock + `snapshot --describe false`, ≤ 5 timestamps per call) or a text storyboard, cost and risk. Recommend one (Elevated when the bar is premium). All three obey every locked ledger line. | agent proposes, **human picks or mixes per beat** | the options in `hf/STYLE_DNA.md` |
| 6 | **Into the spec:** `hf/STYLE_DNA.md` = card + beat map + chosen option, each row with a target and a tolerance (default ±20 % — a house default; a universal tolerance gives false precision for categorical or subjective features `[CONFLICT]`) or `deviate: <reason>`; DNA rows become `R` rows in the ledger; PROMPT's `<direction>` will say "in the grammar of <ref-id>: …" with numbers. | agent | updated ledger |
| 7 | **After each render (wf-06):** analyse the draft at `--detail standard` and fill `dimension | DNA | ours | Δ% | verdict` in `hf/QA.md`; flag every Δ beyond tolerance unless the row says `deviate`; matched stills with `sheet --at t1,t2,t3,t4`. | agent | the table |

**Licensing — take / do not take.** Take: pacing, event density, transition types, camera rhythm, type system, palette *structure* (ground + one accent), music BPM/energy *shape* (a library track with a licence row), SFX types and levels. **Never** take: the reference's footage, frames, VO, music, logos, characters, a paid font we do not license, its brand identity when the client has one, third-party brand sounds in ads (organic only). Do not copy its watermark, end card, jingle, flaws, absence of music, length or structure, looks outside the pinned segment, or its safe zones when the platform differs. Do not use AI-looking stills of people. (Detail of style-imitation limits: perishable legal guidance — check `references`.)

## 4. Path B — no reference video: the moodboard (images and stills)

1. 3–6 queries per open decision (hook, typography, palette, motion, transitions, B-roll, lighting for AI prompts), in precise English ("swiss kinetic typography black yellow", not "cool text").
2. Collect 20–40 items into `hf/references/` from free sources; **keep 6–12**; throw away templates, generic stock and "AI slop".
3. `hf/references/MOODBOARD.md`: for each kept item *what to take* and *what **not** to take*; the licence/terms of each source recorded (images are for reference, not reuse).
4. Show the person and get approval **before** building. While building, compare snapshots with the references: "is this at the reference's level?"
5. A person who hesitates between fonts, caption animations, easings, palettes or transitions gets **one choice board** with their real text/colours instead of chat rounds (8–12 options, a phone frame, "none of these + comment", a downloadable `choices.json`; an owner idea, desk-tested only `[IDEA]`).

## 5. Exit gate G1

| Predicate | EVIDENCE (required field) | State rule |
|---|---|---|
| the person picked an option (or mixed per beat) **and** pinned the time range of "the style" (Path A) / approved the moodboard (Path B) | the person's message id | else `blocked` |
| `hf/STYLE_DNA.md` (or `MOODBOARD.md`) exists with the chosen option, targets + tolerance or `deviate`, and every DNA row has number/where/how/confidence | the file path + a row count | else `fail` |
| `metrics_override.json` exists when the automatic cut count was corrected | the file path | else `fail` |
| `R` rows were added to the ledger and the ledger check still exits 0 | exit code | else `fail` |
| no reference asset is in `hf/assets/` | `ls` quoted | else `fail` |

Gate record → `hf/QA.md` "Gate log". **No reference analysed ⇒ `n/a` only if the ledger says "no reference" and the moodboard was approved.**

## 6. Human vs agent

| Human | Agent |
|---|---|
| names the reference; pins "the style" range; picks Faithful/Elevated/Twist or mixes per beat; approves the moodboard | fetches/copies, analyses, corrects the counts, writes the DNA card with confidence grades, maps beats by function, drafts 3 options with stills |

## 7. Failure modes → remedy

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| the build copies the "before" look | several looks, no range pinned | re-pin; rebuild the DNA | step 1 |
| a cut count the owner disbelieves | the automatic count trusted | zoom at every suspicious transition; write the override | step 2 |
| a font "matches" but the keyword reads wrongly | identity guessed (L) | look-alike test at final size | step 3 |
| the same notes arrive in three sessions | per-project fixes for global rules | log as a global style rule (wf-09) | README §global rules |
| analysis queue blocks for hours | a very long source | trim before queueing; set concurrency by free RAM | step 2; wf-batch |
| a link cannot be downloaded | login wall / old downloader / platform restriction | ask the person for the file, or analyse a mirror the person owns | step 1 |

## 8. Tool invocations

Skill `video-analysis` (its scripts; the toolkit's `benchmark` scorer for numbers) · `sheet` (stills at chosen times; side-by-side) · `transcribe` · `ffmpeg` (extract a still: `ffmpeg -ss <t> -i ref.mp4 -frames:v 1 px_<t>.png`) · `hyperframes snapshot --at … --describe false` (≤ 5 per call) · `render_lock run -- <heavy cmd>` · `ledger` (timing line). Style measurements from pixels use the analysis helper shipped with `reference-style-transfer`.

## 9. Per-type deltas

| Type | Delta |
|---|---|
| talking-head | ASR (Hebrew) + energy + hidden source cuts + faceX per frame of the *reference's* speaker are not needed; the reference supplies caption/zoom/B-roll **grammar**; LUFS of the source measured at minute 0 |
| testimonial | references: result-first openings, split-screen proof, lower-third; never copy a client's likeness or numbers |
| ad-promo | a competitor-ad scan (public ad libraries) for hook patterns **as reference only**; a licence note per reference; the owner's signature + the upgrade |
| motion-graphics | the Higgsfield-style launch language is the taste reference: take "snap, then drift", the move catalogue, "the music is the SFX" — **not** a brand's signature colour (e.g. its lime); mixing three brands' languages reads as a template: one skeleton |
| ai-generated | references: lighting, lens, camera move, composition — **not** characters or brand colours ("references are not templates"); a reference pack with what to take / not take |
| podcast-clip | references per profile (dry conversation vs hyped/graphic); layout (TRACK/SPLIT/GRID) and title-bar patterns; n = 1 breakdowns only |

## 10. Time labels

Owner target 15–30 min. Modelled: none. Measured on OM: analysis throughput numbers above (single loaded runs). The cut-detector's F1 on 20 hand-verified ads was 0.89 (owner's tool, after tuning; 339 edit points) — keep it as a regression bar, not a guarantee on new material.

(src: distilled/02 workflow §3; distilled/06 reference-analysis §1–§3; distilled/01 A6, C9 — read 2026-10-02.)

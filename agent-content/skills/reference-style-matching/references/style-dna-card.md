# The Style DNA card (`style_dna.json`)

Load when: writing or reviewing a card (procedure steps 3-4). Source: distilled 06 reference-analysis §3 and §4.1, T16 findings (2026-10-01). Checked by `scripts/style_card_check.py card`.

## 1. File shape (schema_version 1.0.0)
```json
{
  "schema_version": "1.0.0",
  "reference": {
    "id": "yt-abc123",
    "analysis_dir": "_work/analysis/ref-abc123-1a2b3c",
    "analysis_sha256": "<sha256 of that folder's measurements.json>",
    "pinned_segment": {"start_s": 0.0, "end_s": 28.0, "look": "final look, not the before/after", "pinned_by": "user"},
    "role": "all"
  },
  "rows": [
    {"id": "R01", "dimension": "pacing", "metric": "cuts_per_min", "value": 36.0, "unit": "per_min",
     "seen_at": "0-28 s", "method": "measurements.json pacing.cuts_per_min, verified on frames",
     "source_key": "measurements:pacing.cuts_per_min", "evidence": [], "confidence": "H",
     "confirmed_by": ["frame zoom 4.2 s and 9.8 s"], "tolerance": {"mode": "pct", "value": 20, "abs_floor": 2},
     "deviate": null}
  ],
  "beat_map": [{"ref_beat": "0.0-1.4", "function": "hook", "ref_device": "number slam, punch 115 %", "user_beat": "0.0-2.1", "user_line": "...", "mapped_device": "same, on the user's number"}]
}
```
- `analysis_dir` is relative to the project root (`<project>/_work/analysis/<ref-id>`, run the checker with `--root <project>`); `analysis_sha256` ties the card to ONE analysis (re-analysing changes it).
- A numeric row with `source_key` (`measurements:<dotted path>` or `audio:<dotted path>`) must equal the analysis value (within 0.5 %). If the frames show the analysis is wrong, correct it THERE (`pacing.override` + `review.corrections`), never in the card.
- A row without `source_key` needs an `evidence` path (a px_measure output, a zoom folder, a sheet) unless it is confidence L.
- A dimension that does not apply (`value: null`) needs an `na_reason`; an unfilled dimension is never invented.
- Colours: `source: "fullres_png"` and `flat_fill_std <= 12` on every hex row. Fonts: `metric: "font"`, `confidence: "L"`, `nearest_match: true`, `licence`.

## 2. The 11 dimensions (every card has a row or an `na_reason` for each)
| Dimension | What to measure (units) | Seen at | How |
|---|---|---|---|
| `pacing` | cuts/min (corrected), median shot s, visual event every N s (caption/graphic/zoom changes counted from sheets), first cut s, screen change every N s | whole pinned segment | analysis `pacing` + corrected count; events from sheets |
| `hook` | frame-0 content, first word t, first text t, first motion t, the promise (one sentence) | 0-3 s | zoom 0-3 s |
| `transitions` | each type x count, duration in frames, direction (does the exit mirror the entry?) | list of t | one zoom per distinct type |
| `camera` | punch-in scale %, push duration s, zoom rhythm (every N s), pivot (face?) | t list | face-width ratio between frames (confounded by subject distance) |
| `type` | font (nearest match, L), size px @1080, weights, colours hex, position (x centre, y top %), max words per card, entry/exit frames and style | t list | full-res frame + `px_measure.py` |
| `colour` | luma p1/p50/p99, mean saturation, warm/cool, skin hue if a person, accent hex and where it appears | 5-20 frames | `px_measure.py grade/sample` |
| `broll` | types (real / stock / UI / 3D / data), % of runtime, full-bleed vs card, motion-graphics layer on top | t list | sheets |
| `layering` | cutout y/n, graphics behind the speaker, depth order (plate, behind, cutout, captions, UI) | t list | sheets |
| `sound` | music BPM (estimate), energy arc (intro / drop / ring-out t), music dB under voice, SFX types per min and dB under voice, cut-on-beat % vs chance | t list | `audio.json` + audio images; ebur128 per range |
| `endcard` | duration, content, CTA wording form | t | zoom |
| `safezone` | where key text and captions sit vs OUR platform's house zones (9:16: key text y <= 1248, caption rail bottom <= 1450) | t | bbox from full-res frame |

Platform watermark, end card and jingle are excluded from every row (they are listed in the analysis `coverage.excluded`).

## 3. Confidence labels (H / M / L)
- **H** - a tool measurement AND an independent confirmation agree (a frame zoom, a second method, a second range). List the confirmation in `confirmed_by`.
- **M** - measured once, or read from the sheets.
- **L** - inferred: font identity, SFX label, mood, anything a model guessed. L rows are `informational` or `categorical`, never numeric acceptance targets.
(The author's definition, "measured at least twice", is kept as a special case of H; T16 notes repeated measurement shares systematic errors, so agreement is the test.)

## 4. Tolerances (per row, not one blanket number)
| mode | meaning | use for |
|---|---|---|
| `pct` | `abs(draft - DNA) <= max(value % of DNA, abs_floor)`; `abs_floor` is REQUIRED when the DNA value is below 1 | cuts/min, shot length, loudness steps, BPM, zoom scale |
| `abs` | `abs(draft - DNA) <= value` | positions in px, times in s |
| `exact` | the same string | locked copy, a client-mandated hex |
| `categorical` | draft in an allowed set | transition types, B-roll kinds |
| `informational` | reported, never failed | L rows; colours when the client's palette wins |
The author's default is +/-20 % per row ("Faithful = all rows within +/-20 %"). T16 found a blanket 20 % unsuitable for near-zero values, categorical transitions, distinctive branding and exact text: so the default is a starting point per row, with the reasons for each exception written in the card. Starting points (heuristics, not evidence): cuts/min and median shot pct 20; first text/first motion abs 0.3 s; punch-in scale pct 10; type size @1080 pct 10; BPM pct 8 (and check half/double); loudness abs 2 LU; safe-zone positions abs 40 px; transition types categorical.
`deviate: "<reason>"` marks a deliberate Elevated/Twist change; it is reported in the ledger and needs the user's OK recorded in the PROMPT.

## 5. Measuring from pixels (full resolution only)
```
python scripts/px_measure.py sample <ref.mp4> --at 3.2 --points 540,1500 120,300 --box 5   # hex per point + flatness
python scripts/px_measure.py grade  <ref.mp4> --at 1,5,9,14 --stride 4                       # luma p1/p50/p99, saturation, warm/cool, top colours
python scripts/px_measure.py scale  64 140 --frame-width 740                                  # px at the frame's width -> px @1080
```
`sample` takes the median of a box x box patch per point and reports `flat: false` when the channel standard deviation is above 12: a gradient, a texture or a text edge is not a brand colour. `grade` subsamples every Nth pixel (luma Rec.709 weights; saturation (max-min)/max; warm/cool = mean(R-B); top colours in 32-level bins, hex = bin centre). Values are screen-referred approximations of stored video: never write them as scope readings, and never as the client's colours.
Font identity: nearest from the licensed Hebrew font set or a licensed catalogue; always test Hebrew keywords at full size for ו/ז, ד/ר, ה/ח (a display face once read "לבזבז" as "לבובו"). A paid reference font is replaced by its nearest licensed match; "font identity" is always L.

## 6. After the card: `style_dna.md`
A human-readable version for the build (`hf/STYLE_DNA.md`): the pinned segment, one paragraph "what makes it work" (5 lines), the table of rows with tolerance or `deviate`, the beat map, the chosen option. The JSON is the source of truth; regenerate the Markdown from it.

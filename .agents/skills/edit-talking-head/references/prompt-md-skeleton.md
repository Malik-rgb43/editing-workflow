# PROMPT.md for footage: the edit spec, the approval record, `edit_plan.json`

Load when: before writing PROMPT.md or `data/edit_plan.json`. PROMPT.md is the ONE spec (SPEC.md is retired). It states, for every range, what is seen, where (px), when (frames), how it moves (easing), what is heard and which transition; every ledger id is cited. Numbers are the contract: hex, px, frames, dB, easing points; no "about". Dated 2026-10-02; source: distilled 02 techniques §1.2-§1.5, distilled 01 rules-and-gates B1-B8.

## 1. Approval record (gate G1)
- The agent drafts; a human approves, also in autonomous runs (decision default Q6). Approval = a chat message from the human after the draft; record its time and a quoted fragment in `hf/CHANGELOG.md`:
  `## G1 approval 2026-..-.. HH:MM - "<quote>" - PROMPT.md sha256 <first 12>`
- No composition code (`index.html`, `compositions/*`) is created before that line exists. Later change requests: ledger row -> PROMPT.md rows -> code; the changed rows are re-approved.
- Before presenting the spec: 4 key stills for approval (hook, a peak beat, a mid-transition, the end card) via a quick mock + `snapshot --describe false`, before the full build.

## 2. Skeleton (footage variant)
```
# PROMPT: <project> - "<title>" (<ratio>, <duration>, <fps>)
Style lock / reference: <ref-id>; which segment is "the style"
Deliverable: exact final file name      Owner notes this version answers: 1. ... (numbered, in the owner's words)
Story in one sentence: what the viewer feels; what the speaker promises
<ledger>  id | dim | said (verbatim) | spec (px, s, frames, hex, dB, filename) | where/when | acceptance check | src (U/R/D/A) | status
<inputs>  footage (file, duration, ratio, fps, colour state, loudness) | language | keywords + colours | keyword font | CTA word | logos (licence) | house-preset overrides
<script>  EDL only when restructuring: Beat | out frames | src seconds | VO text ; cut-out list ; edit points inside silences (-38 dB), +-2 f on the waveform
<direction>  format/fps (one pre-cut, pre-graded 30 fps base = ONE <video>) | grade (named preset + measured targets) | framing (head-top y, zoom caps) | type system | accent tokens | motion language | transitions (each once) | cadence statement | banned list
<structure>  # | out time | src time | what is said (keywords bold) | beat type | what is seen | camera event | sound   - one row per beat and event
<sound>  VO chain | bed level under VO, ducking, take-away frames, ring-out | SFX folders, dB, 1-3 frames early | master measured on the FINAL file
<build>  one edit list -> edit.json, cues.js, <video> windows | transcript corrections | --sdr | 1088 canvas
<gotchas>  RTL only on text elements | fonts via @font-face | widest keyword fits | snapshot --describe false
<start>  snapshot times for look approval, then a full draft
```
Every PROMPT states the cadence number it uses (default 3-6 s), the caption preset (default house preset v1) and which numbers are presets, so a student can override them (decision default Q5).

## 3. `data/edit_plan.json` (input of `scripts/plan_lint.py`)
```json
{
  "fps": 30, "duration_s": 40.0,
  "cadence_max_gap_s": 6.0, "zoom_max_gap_s": 4.0, "open_push_within_s": 1.0,
  "beats":   [{"id":"b1","start":3.2,"end":8.0,"type":"real_footage","full_bleed":true,
               "overlay":{"width_px":820,"box":[130,1180,950,1400]}}],
  "zooms":   [{"t":0.4,"kind":"push_in","scale_from":1.0,"scale_to":1.14,"face_x":520,"eased":true}],
  "face_boxes": [{"t0":0.0,"t1":12.0,"box":[380,420,700,820]}],
  "source_cuts": [{"out_s": 12.4}],
  "covers":  [{"start":12.1,"end":13.0}],
  "joins":   [{"out_s": 20.0, "scale_delta_pct": 8, "covered": false}]
}
```
Beat `type` is one of `real_footage | 3d | 2_5d | ui | data | speaker_only`. Times are OUTPUT seconds derived from integer frames. `plan_lint` fails closed: a missing required field is `blocked`, an empty beat list is `blocked`. It lints the PLAN, not the render: a passing plan says nothing about pixels.

## 4. Gates this file feeds
G1 (approval) · G3 (every `source_cuts` entry covered >= 6 frames each side; A->A joins under 15 % covered) · G4 (every zoom carries `face_x`) · G5 (cadence, full-bleed, overlay <= 860 px and disjoint from the face box).

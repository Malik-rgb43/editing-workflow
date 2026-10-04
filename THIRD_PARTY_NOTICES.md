# Third-party notices

Not legal advice. Dates and licence terms are perishable (research snapshot 2026-10-01; src: blueprint/SECURITY_AND_LICENSING.md
sections 2-3, derived from the T18 licence review; every row there is `[SOURCED-unverified]` unless marked otherwise).
Licence texts, NOTICE files and change markers are added here at the moment a component is actually bundled.

## Generated from the bill of materials

The block below is rewritten by `python scripts/gen_bom.py --update-notices` from the third-party entries of `licenses.toml`
(files actually in the tree). Do not edit inside the markers.

<!-- BEGIN GENERATED:bom -->
<!-- GENERATED from docs/BOM.json by scripts/gen_bom.py --update-notices - edit outside this block only. -->

| file | licence | source | register_id |
|---|---|---|---|
| `.agents/skills/revision-notes-handler/scripts/ui/OFL-Heebo.txt` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `.agents/skills/revision-notes-handler/scripts/ui/heebo-he-latin.woff2` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `.agents/skills/visual-choice-board/scripts/ui/OFL-Heebo.txt` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `.agents/skills/visual-choice-board/scripts/ui/heebo-he-latin.woff2` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `.claude/skills/revision-notes-handler/scripts/ui/OFL-Heebo.txt` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `.claude/skills/revision-notes-handler/scripts/ui/heebo-he-latin.woff2` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `.claude/skills/visual-choice-board/scripts/ui/OFL-Heebo.txt` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `.claude/skills/visual-choice-board/scripts/ui/heebo-he-latin.woff2` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `agent-content/skills/revision-notes-handler/scripts/ui/OFL-Heebo.txt` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `agent-content/skills/revision-notes-handler/scripts/ui/heebo-he-latin.woff2` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `agent-content/skills/visual-choice-board/scripts/ui/OFL-Heebo.txt` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |
| `agent-content/skills/visual-choice-board/scripts/ui/heebo-he-latin.woff2` | OFL-1.1 | https://github.com/google/fonts/tree/main/ofl/heebo (Heebo[wght].ttf, 122,012 B, sha256 18f930b5...); subset to Hebrew + Latin as WOFF2 with fontTools pyftsubset on 2026-10-04; OFL.txt shipped beside it |  |

<!-- END GENERATED:bom -->

## Hand-written section: components the toolkit references but does NOT bundle

Referenced = installed by the student from the upstream source or used through a documented route. Nothing in this table is
redistributed by this repository; obligations start only if a file is ever added to the tree (then it also needs a
`licenses.toml` rule with `origin = "third_party"`, a `source` and a cleared register row).

| Component | Licence observed (checked 2026-10-01) | Handling in this repository |
|---|---|---|
| HyperFrames (pinned version re-verified at build time) | Apache-2.0 source | installed by the student; if ever bundled: licence + NOTICE + change markers; dependencies, registry assets, fonts and hosted services are separate |
| three.js, shadcn/ui core | MIT | keep notices if bundled; third-party registries and 21st.dev components need their own licence check |
| GSAP + standard plugins | GSAP Standard No-Charge licence (not MIT) | installed by the student; competing no-code animation builders need written consent |
| Remotion | custom v4 licence (company/employee-size conditions) | optional adapter only, behind a separate company/project licence gate |
| FFmpeg | LGPL 2.1+ baseline; GPL/nonfree optional components | binaries are never bundled; install instructions only |
| faster-whisper | MIT | weights and conversions are separate and pinned independently |
| ivrit.ai Whisper CT2 conversion (pinned revision) | Apache-2.0 per model-card declaration | not bundled; ONNX conversions have no redistribution clearance and must never ship |
| Tencent Hunyuan 3D 2.1 | custom community licence (excludes EU, UK, South Korea) | not bundled; blocked by `scripts/gen_bom.py` |
| Ultralytics (YOLO) | AGPL-3.0 | not used; weights blocked by `scripts/gen_bom.py` |
| SDXL-Turbo | Stability AI Community License | not bundled; commercial eligibility unresolved |
| RVM (robust video matting) | GPL-3.0 | internal use only until resolved; MODNet (Apache-2.0) is the bundle-safe route; blocked by `scripts/gen_bom.py` |
| Blender | GPL (add-ons and assets separate) | installed by the student; rendered output is distinguished from the program |
| Wan2.1 code, Qwen3-TTS code | Apache-2.0 | code only; checkpoints and voice rights are separate |

## Never shipped (blocked by the BOM gate)

Mixkit, ElevenLabs Music, Artlist and Suno files; Adobe and Apple fonts; FFmpeg binaries; ivrit.ai ONNX conversions and training
data; Hunyuan 3D 2.1; RVM weights; Ultralytics weights; owner or client footage,
transcripts, memory, session logs and brand kits; any file whose licence is `unknown`. See `scripts/gen_bom.py` and
`blueprint/SECURITY_AND_LICENSING.md` section 3.

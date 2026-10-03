---
module: edit-motion-graphics/dated-versions
checked_at: 2026-10-01
expires: "2026-12-31, or immediately on any change of the pinned HyperFrames, GSAP, three, Blender, browser or FFmpeg version"
confidence: "versions and licence readings are repository/documentation snapshots [SOURCED-unverified] unless a row says otherwise; none was re-run on a student machine"
refresh: "non-spending: hyperframes --version / doctor / lint / check, npm view <pkg> version, reading each LICENSE file; never an install into the working project, never a paid call"
---

# Dated versions and licence readings used by edit-motion-graphics

| Field | Value |
|---|---|
| Fact set | tool pins and licence scopes that the skill's procedure depends on |
| `checked_at` | **2026-10-01** (research date; no live re-check since) - refresh before relying on a row |
| Source | distilled/04 engines-and-hyperframes, motion-design §9, three-d; T10 UPSTREAM_PINS; T11 E10_PINS (read 2026-10-01) |
| Scope | the reference machine; owner tool notes were written against HyperFrames 0.8.79-0.8.93 |
| `expires` | see front matter. An expired row is **unknown** until refreshed; a failed refresh is not evidence the old value still holds |

| Fact | Id / version | Source | Confidence | Note |
|---|---|---|---|---|
| Primary engine | HyperFrames **0.8.98** (research pin; Node >= 22) | T04, E01 | [VERIFIED-external] for the pin; [MEASURED-lab] E01 | scaffolded projects pin their own version; do not silently upgrade a project (`upgrade --check`, name old/new, re-run the fixtures) |
| Animation library | GSAP **3.15.0** (repo pin); 3.14.2 in HyperFrames examples | T10 | [SOURCED-unverified] | licence = custom "Standard No Charge" incl. formerly paid plugins (SplitText, MorphSVG, MotionPath); commercial use and AI-generated code permitted; **not MIT**; competing visual animation builders need written consent |
| 3D in browser | three.js **0.186.0** latest seen; HyperFrames adapter example pins **three@0.181.2** | T10, T04 | [SOURCED-unverified] | one pinned version in BOTH importmap entries |
| R3F | 9.8.1 | T10 | [SOURCED-unverified] | `frameloop="never"` + `advance()` is a candidate only; delta simulations are not random-access |
| Tailwind in scaffold | `@tailwindcss/browser@4.2.4` | T04 | [SOURCED-unverified] | v4 CSS-first; no breakpoints/hover/transition classes |
| Lottie | lottie-web 5.13.0 (MIT runtime) | T10 | [SOURCED-unverified] | `goToAndStop` seek; assets/exporter licensed separately |
| Rive / Spline | Rive runtime not seek-safe (owner: do not); Spline runtime rAF-driven (export GLB); Spline terms revision posted 2026-09-29, new revision effective **2026-10-29** | T10 | [RULE-owner] / [SOURCED-unverified] | applicability unresolved |
| Theatre.js | core 0.7.0 Apache-2.0; Studio 0.7.0 **AGPL-3.0-only** | T10 | [VERIFIED-external] | authoring only; later |
| Blender | the reference machine **5.2**; research manual pinned **4.5 LTS** | T11 | [VERIFIED-external] | read engine enums, never hardcode; Cycles-HIP on RX 7000 from driver 24.6.1; shadow caustics unsupported |
| Depth model | Depth Anything V2 **Small**, Apache-2.0 (revision `03876f86...`); Base/Large/Giant CC-BY-NC | T11 E10_PINS | [SOURCED-unverified] | use Small only |
| UI registries | ~16 verified-permissive registries (~4,100 items) on the reference setup | d05 §3.2 | [PROVEN-internal][LOCAL-only] | admit new ones only after reading the GitHub LICENSE (MIT/Apache/ISC/CC0) |
| 21st.dev | Magic MCP needs a paid account; AI generation not active on the owner's account | d05 §3.1 | [SOURCED-unverified] | no scraping; per-component licence; previews/media/metadata have separate terms |
| Registry catalogue size | quote no fixed count (268 vs ~400 reported) | d04 conflicts | [CONFLICT] | read from the pinned CLI |

Non-spending refresh checklist: `hyperframes --version`; `hyperframes doctor --json | jq -e '.ok'` (exit 0 even when broken, so gate on `.ok`); read the registry LICENSE files; compare with the rows; write the new `checked_at` per row. Never "test" a version by installing into a client project.

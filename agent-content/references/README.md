# Dated reference modules

> Index of the **volatile-facts modules**. Written 2026-10-02 from the research record (observations dated 2026-09-27 to 2026-10-01). Nothing in this folder was re-checked live; every module says so in its header and must be **refreshed before it is relied on**.

## Why these files exist
Prices, model ids, platform limits, tool versions and licence terms change weekly. Skills and always-loaded instructions must therefore hold only the *durable logic* and point here for the *perishable numbers*. A skill never copies a number from these files into its own description or body; it says "read `agent-content/references/<name>.md`, check its header, refresh if expired".

## Header contract (every module)
Each module starts with a table that carries exactly these fields (the same keys are repeated as YAML front matter so a tool can parse them):

| Field | Meaning |
|---|---|
| fact set | what kind of facts the module holds |
| versions / ids | tool versions, model ids, pins the numbers belong to |
| `checked_at` | date the rows were last verified against their source. **2026-10-02 = the research date, not a live re-check** |
| source | where the rows came from (pointer to the distilled/blueprint record, plus URLs where the research recorded them) |
| scope / plan / region | the account, plan, route, region, machine the facts are true for |
| confidence | overall confidence label and the tag mix |
| `expires` | the condition or date after which the module must not be used without a refresh |
| non-spending refresh | how to refresh without spending money, credits, or sending client data |

## Evidence tags (as in the research record)
`[VERIFIED-external]` confirmed against a primary source and re-checked · `[SOURCED-unverified]` one source, not re-checked · `[MEASURED-lab]` measured in the research experiments (the reference machine unless stated) · `[IDEA]` untested proposal · `[RULE-owner]` an owner decision (taste, not fact) · `[PROVEN-internal]` worked in an owner-approved project · `[LOCAL-only]` true only on the reference machine (one reference machine) · `[CONFLICT]` sources disagree.

## Rules for every reader (human or agent)
1. **Expired module = stale module.** If today is past `expires`, or a pin named in the header changed, say "reference expired" and either refresh it (non-spending method in the header) or ask the user. Never spend on an expired price row.
2. **A number is never a promise.** Quote it with its date, unit, route and limit. Measured numbers keep the machine they were measured on. NVIDIA and Apple numbers are *sourced or unmeasured*, never measured here.
3. **House presets are decisions, not laws.** Safe zones, −14 LUFS, colour targets, Rubik as the caption default are named *house preset v1* (decision default Q5) and are meant to be proven on real devices.
4. **Refresh never spends.** Allowed: reading official pages, `--help`, `--version`, `ffprobe`, listing a catalogue. Not allowed: a generation, an upload of client footage, a paid API call, a sign-up.

## Modules
| File | Holds | Typical expiry |
|---|---|---|
| [model-routing.md](model-routing.md) | video/image model candidates, routes, dated prices, exclusions, open-weight gates | 14-30 days |
| [cost-model.md](cost-model.md) | cost formulas, accounting layers, worksheet, 15 first-pass scenarios, approval template | 30 days (prices) |
| [platform-specs.md](platform-specs.md) | house export preset, safe zones v1, per-platform documented limits, AI-disclosure per route | 180 days |
| [mcp-profiles.md](mcp-profiles.md) | Minimal / Standard / Pro profiles, docs-only vs execution servers, isolation rules | 90 days |
| [hyperframes-traps.md](hyperframes-traps.md) | HyperFrames/Chrome/FFmpeg traps, lint codes, regression fixtures | on any HyperFrames pin change |
| [hebrew-rtl-captions.md](hebrew-rtl-captions.md) | Hebrew caption typography, bidi, timing, exit animation, fonts | 180 days |
| [asr-routes.md](asr-routes.md) | Hebrew ASR models, runtimes, measured speed/WER, VAD, cloud ASR prices | 90 days |
| [matte-routes.md](matte-routes.md) | person-matte routes, measured speed, licence gates (decision default Q8) | 180 days |
| [audio-mix.md](audio-mix.md) | loudness master, ducking numbers, mix chain, destination profiles | 180 days |
| [colour-presets.md](colour-presets.md) | named colour presets, gate thresholds, HDR to SDR branch | 180 days |
| [three-d-routes.md](three-d-routes.md) | Blender / Three.js / AI 3D routing, timings, licences | 90 days |
| [licences-bom-rules.md](licences-bom-rules.md) | what may be bundled, per-licence obligations, release gate, component table | before every release |
| [glossary.md](glossary.md) | Hebrew/English vocabulary | none (stable) |

## Related files owned elsewhere (assumed)
`profiles/` (machine profiles and their manifests) · `docs/en|he/legal-guide.md` and `privacy-and-security.md` (student-facing legal and security guides) · `docs/decisions/` (ADRs for open-question defaults).

# Volatile facts (dated; re-check before quoting)

Load when: you are about to quote a timing, a licence, a tool behaviour or a platform claim about colour. Fields: fact, id, version/scope, checked_at, source, confidence, expiry, non-spending refresh. Machine for timings: the reference machine; NVIDIA/Apple unmeasured.

| id | Fact | Version / scope | checked_at | Source | Confidence | Expiry | Non-spending refresh |
|---|---|---|---|---|---|---|---|
| C1 | Bake about 3 min per minute of footage; "59 s for 1,776 frames" | owner header/memory claim, no independent run log (T09/T12 did not re-run) | 2026-10-02 | distilled 04 colour §1.1; distilled 06 §5 | low | when re-measured | run `color_render` on a 10 s clip and write the timing ledger |
| C2 | u2net person matte about 0.45 s per matte on CPU, person box, every 3rd frame | owner header claim; the every-3rd-frame choice caused flicker | 2026-10-02 | distilled 04 colour §1.1, §1.2 | low | superseded by any measurement | same as C1 |
| C3 | `data-color-grading` (preset `skin-soft`) on `<video>` hung with "Navigation timeout 10000 ms" and left the first frame ungraded | HyperFrames 0.8.82, the reference machine's stack, 2026-09-28; later "hardware-render fix" noted on 0.8.86+ | 2026-10-02 | distilled 04 colour §3; distilled 04 hyperframes-traps §1.6 | medium (reproduced in isolation once) | any HyperFrames or driver update; still never used on a speaker (owner rule) | one-second grade vs no-grade fixture on the pinned build |
| C4 | The engine realtime grade path is Rec.709/SDR only; a BT.2020 PQ/HLG source switches the whole render to HEVC 10-bit HDR unless `render --sdr` | vendor docs summarised by the owner, 2026 | 2026-10-02 | distilled 04 colour §3 | medium | HyperFrames version | read the render summary line; `ffprobe` the output |
| C5 | Standards currency: ITU BT.2100-3 and BT.2408-9 are the current catalogue versions (catalogue entries read, not the full standards) | 2026-10-01 | 2026-10-01 | T12 via distilled 04 colour §4 | medium | new revision | check the ITU catalogue (free) |
| C6 | OCIO 2.5 documents ACES2 views (library support finalised in 2.4.2); a 2.5.0 GPU integration is affected by the 2.5.1 ABI notice | 2026-10-01 | 2026-10-01 | T12 via distilled 04 colour §4 | low-medium | OCIO release | read the release notes |
| C7 | Reference numbers 46 % / 118 degrees / 24 chroma belong to ONE outdoor test footage; they are a named preset | 2026-09-30 test | 2026-10-02 | distilled 04 colour §0 | high that they are scene-specific | never "universal" | derive per scene |
| C8 | Colour Match in DaVinci Resolve: no certified Python auto-grade method documented | vendor page, 2026-10-01 | 2026-10-01 | T12 | low | Resolve release | read the installed Developer Documentation README |

No LLM or cloud colour run exists: no claim that a model can grade from documentation alone is supported (T12 left that comparison unrun).

---
module: licences-bom-rules
checked_at: 2026-10-02
expires: "before EVERY release (a release gate re-checks it); never later than 30 days (2026-11-01)"
confidence: "licence facts [VERIFIED-external] only where marked; most rows [SOURCED-unverified] (read 2026-10-01, relevant sections only, one same-family verifier); NOTHING is cleared; this is not legal advice"
refresh: "free: re-read each licence file at the pinned version; regenerate the file-level bill of materials from the actual pinned tree; counsel review is a human step"
---

# Licences and bill-of-materials rules — dated reference

> **Not legal advice.** Research summary, dated 2026-10-02 (pages read 2026-10-01). Terms are perishable. Jurisdiction-specific points live in `docs/en/legal-guide.md`. Counsel must resolve the disputed items before the affected activity.

| Field | Value |
|---|---|
| Fact set | what may go into the student download; per-licence obligations; component-level licence facts; blocking items; owner-rule reconciliation; release gate and BOM fields |
| Versions / ids | HyperFrames 0.8.98 (Apache-2.0) · three.js (MIT) · shadcn/ui core (MIT) · GSAP Standard No-Charge licence (effective 2025-04-30, modified 2025-05-30) · Remotion 4.0.531 (custom v4; v5 "upcoming") · FFmpeg (LGPL 2.1+ baseline) · faster-whisper / whisper.cpp (MIT) · SDXL-Turbo community licence (2024-07-05) · C2PA 2.4 |
| `checked_at` | **2026-10-02** (= research date; **must be refreshed before use**) |
| Source | blueprint `SECURITY_AND_LICENSING.md`; `distilled/08-…/legal-and-licensing.md` (T18 register: 392 candidate rows, **none cleared**, 114 `unresolved`); `research/tracks/T18-legal-licensing/LEGAL_GUIDE.md` |
| Scope / plan / region | worldwide student bundle assessed generically; US/EU/Israel statements are in the legal guide |
| Confidence | the register is a **candidate list, not a software bill of materials**; `[SOURCED-unverified]` is the default |
| `expires` | see front matter |
| Non-spending refresh | open the licence file at the pinned tag/commit; compare the SHA-256 to the BOM; no accounts, no purchases |

## 1. The rights model — six separate questions
(1) vendor permission to exploit output commercially · (2) copyright protection of the result · (3) freedom from third-party infringement · (4) consent to depict a person/voice · (5) permission to upload confidential footage · (6) for the student repo: **redistribution of source files**. A paid plan answers at most (1). A rendered MP4, an editable project, a template, a model checkpoint and a repo asset are different deliverables with different rights.
**Per-asset record:** source · artifact hash · rightsholder · licence name + version · account plan · purchase/generation/download date · permitted media · territory · term · attribution · evidence file (`SOURCES.md` / rights manifest).

## 2. What may go into the student download
1. **Bundle:** original examples and code; exact permissively licensed components with their notices; individually documented OFL / CC0 / CC-BY fixtures **when the non-copyright rights (privacy, publicity, moral) are also cleared**.
2. **Link, do not bundle:** proprietary services; restricted libraries; weights/conversions with an unresolved chain; Mixkit / Eleven Music / Artlist / Suno files; Adobe and Apple fonts; **FFmpeg binaries** (use install instructions: LGPL/GPL/nonfree components change obligations; codec patents are separate); vendor skill texts (study only).
3. **Never ship:** client or owner footage, transcripts, memory, session logs, brand kits, style-analysis reports of third-party videos, any file whose licence is `unknown`.

## 3. Per-licence obligations
| Licence | Obligations | Do not |
|---|---|---|
| MIT | keep copyright + permission notices; check dependencies | assume the dependencies are MIT |
| Apache-2.0 | licence text + required NOTICE + modification markers | claim a trademark grant or endorsement |
| GPL / AGPL | review distribution, corresponding source, integration/network duties | call it "forbidden for commercial work"; embed it silently in the distributed toolkit |
| OFL (fonts) | keep family attribution + licence + reserved names | sell the font alone; rename freely |
| CC-BY | credit creator, source, licence, indicate changes; no added restrictions | forget privacy/publicity clearance (not covered) |
| CC-BY-NC | non-commercial only | use in client work or the commercial route |
| proprietary stock / music / fonts | integrated-output permission only | redistribute source files, feed to services that claim output ownership |
| model weights / conversions | exact checkpoint licence + provenance, independent of runtime code | inherit the runtime's licence |

## 4. Component facts that decide bundling `[SOURCED-unverified]` unless marked
| Component | Licence observed | Rule |
|---|---|---|
| HyperFrames 0.8.98 | Apache-2.0 source | licence + NOTICE + change markers; dependencies, registry assets, fonts, hosted services are separate |
| three.js; shadcn/ui core | MIT | keep notices; third-party registries and 21st.dev components need **their own** licences (credit them) |
| GSAP + standard plugins | Standard No-Charge GSAP licence — **not MIT**; commercial and agent-generated code permitted; a competing visual no-code animation builder needs written consent | keep notices |
| Remotion 4.0.531 `[VERIFIED-external]` | custom v4 licence; free for qualified individuals/small for-profits (≤ 3 employees; headcounts aggregate); FAQ separates MP4-only agency delivery from client operation of project code; **v5 terms "upcoming"** | HyperFrames only in v1.0 (decision default Q14); keep the exact tagged v4 LICENSE; separate company gate |
| FFmpeg | LGPL 2.1+ baseline; GPL/nonfree optional components | install instructions, not binaries |
| faster-whisper / whisper.cpp | MIT | weights/conversions separate |
| ivrit-ai turbo CT2 (rev `72ad623a37947395efcc3933132353790e5a12f5`) | Apache-2.0 model-card declaration | pin the exact checkpoint; does not license other conversions or the training recordings |
| **ivrit-ai ONNX conversions** (revs `edb17b6b65f60a299d4b620d043e15b60321e5ff`, `9dbd271d18ff3f85140b64cf7949d53da6581e57`) `[VERIFIED-external]` | **unresolved** (READMEs failed to read, no licence metadata) | **no redistribution clearance**; failure to read is not proof of a restrictive licence |
| ivrit.ai speech datasets | training / academic purpose terms | not course footage, not a voice-cloning fixture |
| Depth Anything V2 | Small Apache-2.0; Base/Large/Giant **CC-BY-NC 4.0** | exclude NC sizes from the commercial route |
| Tencent Hunyuan 3D 2.1 | custom Community licence; excludes **EU, UK, South Korea** | not unrestricted |
| Ultralytics (YOLO) | AGPL-3.0 | corresponding-source / network / integration review |
| SDXL-Turbo `[VERIFIED-external]` | Stability AI Community License (2024-07-05) | commercial use needs registration + revenue conditions (~US$1 M organisation revenue); owner eligibility unresolved |
| **RVM (matting)** | **GPL-3.0** | **optional user-installed plugin, internal use only**; MODNet (Apache-2.0) is the bundle-safe route (decision default Q8) |
| Blender | GPL; add-ons/assets separate; rendered output distinguished | indexed FAQ only (direct page 402) |
| Wan2.1 repo; Qwen3-TTS | Apache-2.0 code | checkpoints and voice rights separate |
| LTX 2.5 / HunyuanVideo 1.5 / CogVideoX | see `model-routing.md` §5 | revenue/territory/registration conditions |
| Poly Haven | CC0 | site text, thumbnails/example renders, API access have other terms |
| Freesound | per-file CC0 / CC-BY / CC-BY-NC | not a uniform CC0 |

## 5. Blocking today (cannot go in the student download)
Mixkit SFX files (standalone/tool/template/source bundles prohibited; integrated rendered end products OK) · Eleven Music self-serve outputs (libraries/repositories/resale prohibited) · Artlist assets (integrated projects only) · Suno outputs (no generic repo clearance) · Adobe Fonts and Apple SF (no file/bundle grant; SF is UI mock-ups only) · ivrit.ai ONNX conversions · ivrit.ai training data · Depth Anything V2 Base/Large/Giant · Hunyuan 3D 2.1 · FFmpeg binaries · Ultralytics · RVM (as part of the bundle) · any proprietary font whose EULA was not read (installed ≠ redistributable) · any owner/client media. Fonts to bundle: only OFL families with their licence files and reserved names kept (Rubik, Heebo, Assistant, Alef, IBM Plex Sans Hebrew, Noto Sans/Serif Hebrew, Frank Ruhl Libre, Secular One, Varela Round, Arimo, Karantina — headers read at google/fonts commit `9710da1eacb3be272583c3224dcb70f9da6eadbb`); record file hash per font.

## 6. Owner rules vs the legal research (reconciled for the course)
| Owner rule | Research | Decision |
|---|---|---|
| `License: unknown` = organic only | unknown = **no permission established** | **teach: unknown = do not use in client work** (decision default Q2). "Organic only" is a risk posture for one's own account, never a licence; paid/ad use never |
| third-party brand sounds/logos = organic only | consistent; no plan clears trademark use | keep; add "ask written brand permission for ads" |
| Mixkit SFX = clean licence | integrated end products yes; standalone redistribution no | OK for rendered client videos (conditional); **forbidden in the student repo** |
| installed font = usable | installed ≠ redistributable | licence per file + hash + notice |
| commercial plan on a generator = commercial output | route/model/plan/date; partner terms; training default | record route + opt-out state per project |
| 21st.dev components ported with credit | registry components are not covered by shadcn MIT | keep credits; add a licence check |

## 7. Release gate (run before EVERY release)
1. Generate a **file-level bill of materials from the actual pinned tree** (path, SHA-256, licence id, licence version, source URL, notice path, rightsholder, how obtained). 2. Reconcile with the research register; every `unresolved` row the tree actually contains must be closed (never replace an unresolved row by a parent project's licence; unknown terms mean no permission). 3. Include notices (`THIRD_PARTY_NOTICES.md`). 4. Test that **no restricted stock, client recording, proprietary font or unlicensed checkpoint** entered the download (hash scan against the blocking list; client-name scan; secret scan). 5. Obtain specific counsel review for disputed uses (contract template, AI-disclosure guidance, GPL plugin approach). 6. State jurisdiction and date on every legal page. 7. A gate that cannot run reports `not_run`; the release is not green.
Open before release: all 114 `unresolved` rows; every inherited lead the final tree contains; exact SDXL-Turbo eligibility; the EU Omnibus instrument; Israeli statute consolidation; per-provider DPA/transfer/training/retention for any proposed client upload; GPL/AGPL integration analysis; account-specific music rights; the Hebrew display font whose directory guess failed.

## 8. Music, SFX, stock — what the licence gives
| Item | Gives | Does not give |
|---|---|---|
| Mixkit SFX | integrated commercial end products | standalone redistribution; inclusion in repos/tools/templates |
| Eleven Music (self-serve) | commercial use per plan eligibility and media limits | music-library/repository and reseller rights; restricted industries; artist imitation |
| Artlist | assets inside integrated projects per plan/timing | AI services that claim output ownership or shared reuse; standalone libraries |
| Suno | commercial use via a permitted official download under the right tier | confidentiality; generic repo clearance |
| Poly Haven | CC0 incl. sold products | site text, thumbnails, API access |
| CC BY 4.0 | commercial sharing/adaptation with attribution + licence link + change indication | privacy/publicity/moral-rights clearance |
| TikTok CML / YouTube Audio Library | scoped to their platforms (see `platform-specs.md`) | cross-platform rights |
| Epidemic, Musicbed, Soundstripe, Udio | **not reviewed** (rows unresolved) | — |
Adobe Fonts permit finished rasterised/embedded client graphics/video; they do not permit transferring font files, editable access, or dynamic template/font-selection products. San Francisco's licence is scoped to Apple UI mock-ups.

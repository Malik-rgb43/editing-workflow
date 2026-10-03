---
module: three-d-routes
checked_at: 2026-10-02
expires: "90 days (2026-12-31); hosted-generator prices and free tiers (checked 2026-09-27) expire in 30 days"
confidence: "owner timings [PROVEN-internal][LOCAL-only]; E10 2.5D numbers [MEASURED-lab] (one machine, one pass); model/library licences [VERIFIED-external] or [SOURCED-unverified] per row; hosted prices documentation only"
refresh: "free: read licence pages, Blender release notes, three.js changelog; one-second segment test on your own machine; never generate a paid model"
---

# 3D, 2.5D and depth routes — dated reference

| Field | Value |
|---|---|
| Fact set | when 3D is worth it; Blender vs Three.js vs AI 3D vs 2.5D routing; Blender pipeline; timings; colour/alpha contract; model and asset licences; depth-model pins |
| Versions / ids | Blender 5.2 (owner) vs pinned manual 4.5 LTS (do not carry 4.5 assumptions to 5.2) · three.js pinned `three@0.181.2` for the HyperFrames adapter · Depth Anything V2 Small `03876f8651c73a60fe4c2c48294e09fcb6838fcf` · MCP for Blender (`ahujasid`, MIT) |
| `checked_at` | **2026-10-02** (= research date; hosted prices dated **2026-09-27**; **must be refreshed before use**) |
| Source | `distilled/04-…/three-d.md` (T11, owner tools); `distilled/03-…/e09-e12-final-results.md` (E10); `distilled/08-…/legal-and-licensing.md` §7 |
| Scope / plan / region | the reference machine; students on NVIDIA or Apple have **no measured data here** |
| Confidence | see tags; Blender timings are owner measurements at small sizes, not benchmarks |
| `expires` | see front matter |
| Non-spending refresh | licence pages and READMEs; local one-second segment test; no hosted generation, no credits |

## 1. Routing — smallest adequate representation (decide per beat; write the reason in PROMPT.md) `[RULE-owner]`
| Requirement | Route | Gate |
|---|---|---|
| real product geometry, logo/text extrusion, exploded view, controlled relighting | **Blender** mesh + EEVEE preview; Cycles only when material quality needs it | reference/geometry/lighting correct; unique-frame ETA |
| simple reusable prop/icon | owned asset or Poly Haven CC0; Blender alpha loop | provenance/licence, usable topology, seamless loop |
| unique hero prop with no mesh | hosted generation **only if the student connected a generator (for example Tripo)**, with approval first; otherwise model it in Blender or use a CC0 asset (CPU image-to-3D is a local option only if the student chose local) | connected, exact terms, cleanup effort, accepted fidelity |
| small motion from a still / depth illusion | static 2D, or **DA2-Small layered 2.5D** | holes/stretch/identity limits; depth once, cached |
| data-driven, procedural, many instances, 3D UI with live HTML text, edited in rounds | **Three.js inside HyperFrames** | deterministic absolute-time seek; capture cost; one-second AMD segment test |
| captured real location with novel camera | licensed existing splat (research only) | capture/data/software rights |

**Three.js is better when** the scene is data-driven/procedural (globe with routes, charts, seeded particles), has many instances (`InstancedMesh`), is 3D UI with live text (Hebrew as an HTML/CSS layer above — **never `TextGeometry`**), is edited in rounds (colour/number/cue in seconds, not a 40-minute render), the camera must follow the VO or the DOM, or the palette must be exact (hex = hex, no AgX pastel). **Blender is better when** photorealism (glass, caustics, metal, skin, soft GI), a hero material on screen > 2 s, simulations (cloth, fluid, hair), an existing sprite sheet, or a look already approved in Blender. **Hybrid is usually best:** model + baked textures in Blender → GLB → `GLTFLoader` in the three adapter → live light/camera/colour in HyperFrames; entry condition: a one-second segment render in delivery mode with `--browser-gpu` on the target machine — blank frame or timeout → fall back to a Blender sprite. `[CONFLICT]` the older "always Blender" note vs the 2026-09-30 per-beat rule: the latest owner decision wins on taste; evidence on facts (no global Blender-only rule).

**When 3D is worth it:** hero shot of a product without footage; icons/objects for explainers; 3D logo/text; impossible camera moves; a consistent turnaround as a reference for image-to-video (unverified as research); assets reused across many videos. **Not:** good stock exists; flat 2D style; no time for good lighting; software/process explanations (2D is faster and clearer); tight budget. Default: hybrid 2D/2.5D for messages and UI + **one** 3D moment (a 2-3 s alpha shot gives most of the effect in a 15-30 s reel). 3D must not hide information (prices): put the object inside the UI with a contact shadow. 3D costs ~2-3× per second vs 2D in agency terms (GBP 100-400 vs 40-120 per second, `[SOURCED-unverified]`); 3D with bad lighting looks cheaper than good 2D.

## 2. Blender pipeline
**Environment.** Headless `blender -b scene.blend -P setup.py -a` (animation) or `-f N` (one frame); scripts must not hard-code the engine identifier (it changed between 4.2 and 5.x): read the enum from `scene.render.bl_rna.properties['engine'].enum_items`; set `cycles.device='GPU'` and `compute_device_type='HIP'` via the add-on preferences; record scene/script/asset hashes, engine enum, fps, resolution, samples, seed, device, output transform. Node names are localised — look shader nodes up by **type**.

**Measured on the reference machine** `[PROVEN-internal][LOCAL-only]`: EEVEE objects **1.2-2.25 s/frame** at 384-640 px (coin 384 px 1.66; cube 384 px 1.20; bag 640 px 1.55; gift 640 px 2.25); EEVEE 3D type 1.0-1.25 s/frame; Cycles-CPU plates 51 s (256 spp), 79 s (384 spp float), 253 s (light, 256 spp); each Blender launch costs **~1-1.5 min** (shader compile + camera fit) so render several assets per launch. Estimates at 1080p (unverified): EEVEE 0.5-3 s/frame, Cycles-HIP 10-40 s/frame at 64-128 samples + denoise; 5 s @30 fps turntable 2-7 min EEVEE / 30-90 min Cycles — excluded from budgets. Cycles-HIP is officially supported on Windows for the RX 7000 family from driver 24.6.1 (manual 4.5): HIP-RT + GPU denoise exist; **shadow caustics not supported**; path guiding unsupported; OSL OptiX-only `[VERIFIED-external]`. Exact one reference machine run pending.

**Scheduling.** One heavy renderer at a time; never overlap a Blender batch with browser capture or ASR (a render next to Blender took 21.5 min instead of 11.5).

**Colour/alpha contract.** AgX (default since 4.0) makes brand colours pastel (a `#4ade80` green came out pastel mint) → use a pre-compensated linear base colour or the **Standard** view transform for exact hex (logos/icons); audit every 3D render against `DESIGN.md` (a pink leaked into a locked palette once). Master = **PNG RGBA 16-bit** (`Film > Transparent`) or EXR (a crashed render resumes); then `ffmpeg -i f_%04d.png -c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 -b:v 4M out.webm` for HyperFrames/Chrome and ProRes 4444 (`prores_ks -profile:v 4444 -pix_fmt yuva444p10le`) for Premiere/AE (Chrome cannot play ProRes). Inspect seam, motion blur, premultiplication/fringes over light **and** dark backgrounds; exclude the duplicate 360° endpoint in a loop; sprite sheets ≤ 8192 px per side; preload sheets so the first frame is not blank. Look: studio HDRI from Poly Haven at strength 0.5-1; key = large soft Area light at 45°; rim behind; shadow catcher; turntable = rotate an Empty 360° with LINEAR keys; camera 50-85 mm; shutter 0.5. `[SOURCED-unverified]`

**Blender MCP.** The add-on socket (localhost:9876) has **no authentication and executes arbitrary Python** — never expose it (see `mcp-profiles.md` §6). The launcher takes ~50 s (observed). Poly Haven works without a key; Sketchfab, Poly Pizza, Hunyuan need the student's own key; Tripo only in the Premium tier; pin one server, disable telemetry, no silent provider trials. The Higgsfield Blender plugin (`bl_*`, Blender ≥ 5.1) bills credits per generation.

## 3. Three.js inside HyperFrames
Contract: scene built synchronously; render from the seek time; `AnimationMixer.setTime(t)`; **root `data-duration` mandatory**; assets loaded before seeking; no `requestAnimationFrame` as the source of truth; fixed renderer size and `pixelRatio`; pinned `three@0.181.2` (importmap with matching `three/addons/`). Catalogue blocks with WebGL exist (gallery-tunnel, cosmic-orb, code-3d-extrude, cuboid-carousel). `model-viewer` is **not seek-safe** (owns its loop); Spline runtime and Rive are rAF-driven (export GLB / do not use). Interactive FPS is not render throughput: 40 s @30 fps still needs 1,200 output frames. WebGL in headless Chrome on AMD can stall (the grade shader did) → one-second segment test first. `[SOURCED-unverified]` `[PROVEN-internal]`

## 4. AI image-to-3D — models and licences (checked 2026-09-27 unless noted)
| Model | Licence | CPU/AMD on Windows | Notes |
|---|---|---|---|
| **TripoSR** | **MIT** (code + pretrained) | CPU works (`--device cpu`) | low-medium quality, hidden back is guessed |
| **Stable Fast 3D (SF3D)** | Stability Community: free commercial up to US$1 M annual revenue, **registration required**; gated weights | CPU backend (`SF3D_USE_CPU=1`); AMD GPU unsupported | GLB with UVs/texture; 1-3 min (unverified) |
| Hunyuan3D 2 / 2mini / 2.1 | Tencent Community: **not valid in EU, UK, South Korea, for works AND outputs**; separate licence above 1 M MAU | CUDA; AMD-on-Windows fork "not working yet"; 2.1 texture 21 GB | not realistic here |
| TRELLIS / TRELLIS.2 | code MIT; nvdiffrast/nvdiffrec under NVIDIA licences | needs NVIDIA ≥ 24 GB, Linux | no AMD route |
| InstantMesh | Apache-2.0 | CUDA 12.1 | outdated |
`[VERIFIED-external]` / `[SOURCED-unverified]`. Ranking for the reference machine: (1) SF3D on CPU, (2) TripoSR on CPU; everything else hosted. gfx1102 (RX 7600 family) is **not** in the ROCm-for-Windows matrix (ROCm 7.2.1 docs; ROCm 10.0.0 matrix 2026-08-25 lists the desktop RX 7600, not the mobile variant — eligibility unresolved, not impossible).

Hosted generators (prices 2026-09, USD before tax, stale-risk): Tripo free = **CC BY 4.0 non-commercial**, Pro $19.9/mo; Meshy free = CC BY 4.0, commercial allowed **with credit to Meshy** (20 vs 25 credits per model `[CONFLICT]` preserved); Hunyuan3D web free tier current state unverified; Luma Genie closed 2026-01-01; CSM Cube closed 2026-01-05; Higgsfield `generate_3d` spends credits (approval first). Always start from a clean image of the object, then image-to-3D. **Generated-mesh manifest:** input-reference rights/hash, vendor/model/checkpoint, plan at generation, route/meter, seed/settings/job id, output hash, rights snapshot, cleanup changes. A commercial output grant does not validate references, trademarks, unseen rear surfaces, topology, UVs or dimensions.

## 5. Free asset libraries (client work)
| Library | Licence | Rule |
|---|---|---|
| Poly Haven | **CC0** (HDRIs, textures, models) | safest; the live API needs a unique Referer/user-agent and attribution to the live service; downloaded CC0 assets need none; website text/thumbnails/example renders have other terms; store URL, creator, licence, date, SHA |
| Kenney / Quaternius | CC0 | low-poly/stylised |
| Poly Pizza | mixed CC0 and **CC-BY** | filter CC0; credit CC-BY authors; scraping for AI training prohibited |
| Sketchfab | CC-BY, CC-BY-NC, CC0, Standard | **reject NC**; CC-BY credit; check the NoAI tag; full licence fetch was blocked in the research |
| BlenderKit (free) | Royalty-Free or CC0 | do not resell the model itself |

## 6. Depth 2.5D (E10) `[MEASURED-lab][LOCAL-only]`
**Why:** a still that must move; local text-to-video is too slow on this machine: Wan2.1 T2V-1.3B (fp16 + Q4 text encoder, stable-diffusion.cpp Vulkan with CPU offload) 512×512, 33 frames @16 fps (2.06 s), 20 steps → wall **1,380 s ≈ 669 s per output second (~11 min)**, peak RSS 18.4 GB; GPU VAE crashed twice (0xC0000409, even with tiling); text encode 119 s, weight load 45 s, sampling 446 s, CPU VAE decode 804 s. **2.5D** (DepthAnythingV2 Small CPU, 3 layers with inpainted occlusions, affine camera): **8.1-9.9 s total for a 2 s, 512 px clip** (depth ≈ 0.9 s); same layers through HyperFrames 13.3 s for 48 frames at 1080². **Gate `[RULE-owner]`: ETA > 30 min per shot → propose 2.5D/animatic.** For plain camera moves on stills 2.5D is ~80× cheaper than local Wan (different tasks, **not equivalent quality**). Artefacts: ghost edges/seam lines where depth quantile layers cut a person; newly exposed area 1.3-2.3%.

**Models (immutable pins from T11; no weights downloaded by the research):** DA2-Small `depth_anything_v2_vits.pth` rev `03876f8651c73a60fe4c2c48294e09fcb6838fcf`, 99,218,434 bytes, **Apache-2.0**; DA2-Small HF `model.safetensors` rev `5426e4f0f36572d16453bbda7a8389317b1bef99`, 99,173,660 bytes; DA3-SMALL rev `e08cab65ca0ec38e7826075418411ab90cab4da3`, 137,248,940 bytes (Apache-2.0, secondary); converted GGUF q8_0 36,780,864 bytes (inherits Apache-2.0; a mixed GGUF collection's card is not a blanket grant). **Exclude DA2 Base/Large/Giant and DA3 large/giant (CC-BY-NC)** from the commercial route. Cache key = source + model + runtime + precision + preprocess hash. First camera move ≤ 2% of frame width (a proposal, not a proven threshold); if holes or distortion fail prefer a smaller move or static 2D. Author benchmark (q8_0 319 ms vs 417 ms PyTorch at 504×336 on a 9950X3D) is **not** a prediction for this machine.

Proposed extras `[IDEA]`: DirectML ONNX venv (`onnxruntime-directml` 1.24.4, separate venv; DirectML is in maintenance mode); RIFE + Real-ESRGAN via ncnn-Vulkan/video2x for fps conversion/upscale (MIT/BSD; AMD OK).

## 7. Output and QA gates
A sprite over text trips `text_occluded` in `check` (intended; mark it). Palette audit against `DESIGN.md` on every 3D render. One Blender job at a time through the render lock; benchmark one unit → ETA → go/no-go before any job > 10 minutes. Anything that spends credits needs approval with a dated estimate (see `cost-model.md`). Gaussian splats: research only (INRIA 3DGS software is non-commercial research; gsplat Apache-2.0 on CUDA; Spark 2.3 MIT WebGL2; scene rights separate) — not adopted.

## 8. Open
Owner-machine Blender 5.2 timings with a fixed 1080p fixture; Cycles-HIP on the one reference machine; DA-Small speed on one reference machine via DirectML/Vulkan; whether Three.js WebGL stays stable on AMD in delivery mode; Hunyuan3D web free-tier terms; full Sketchfab licence text.

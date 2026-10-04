---
module: matte-routes
checked_at: 2026-10-02
expires: "180 days (2027-03-31), or on any change of the matting model/licence, ONNX Runtime, OpenCV, or HyperFrames remove-background"
confidence: "speed [MEASURED-lab] single passes on a shared host (the reference machine only); quality is a proxy comparison, not alpha ground truth, not human-reviewed; NVIDIA/Apple numbers sourced only"
refresh: "re-run the 600-frame fixture locally on the pinned build; read the model licence files again; no network upload of footage"
---

# Matte (person cutout) routes — dated reference (decision default Q8)

| Field | Value |
|---|---|
| Fact set | person-matte routes, measured speed, edge-quality proxy, licences, cache keys, the repo's shipping decision |
| Versions / ids | RVM (Robust Video Matting) + ONNX Runtime 1.24.4 DirectML + OpenCV 5.0 · MODNet · MediaPipe selfie segmenter · SAM 2 tiny · BiRefNet-lite · native `hyperframes remove-background` (u2net_human_seg) in HyperFrames 0.8.98 |
| `checked_at` | **2026-10-02** (= research date; **must be refreshed before use**) |
| Source | `distilled/03-…/e09-e12-final-results.md` (E09); `distilled/08-…/hardware-and-os.md` §5.3; blueprint `SECURITY_AND_LICENSING.md` §3 |
| Scope / plan / region | **the reference machine only** (one reference machine / ffmpeg 8.1 / Python 3.12 / Node 24.14); 20 s, 600 frames, 1080p30 public interview clip; single passes, shared host |
| Confidence | speed `[MEASURED-lab]` `[LOCAL-only]`; licences `[SOURCED-unverified]`; the GPL status of RVM is a **hard gate** |
| `expires` | see front matter |
| Non-spending refresh | local fixture re-run (free); `onnxruntime` model files and licences re-read; no cloud |

## 1. Decision for the student repository (default if the author does not decide: Q8)
- **Ship in the repo:** MODNet (Apache-2.0, "bundle-safe") and the native HyperFrames `remove-background` fallback.
- **RVM (GPL-3.0) is an optional, user-installed plugin, internal-use only** until the GPL question is resolved with counsel. It is never copied into the student download and never imported into repo code (link to install instructions; the student installs it themselves). See `licences-bom-rules.md`.
- Profile mapping: `matte-fast` (RVM + DirectML/ORT + OpenCV, **internal-only note**; MODNet bundle-safe). *unsupported ≠ missing ≠ error*: a machine without DirectML reports `unsupported` for the fast route and falls back to the native route; the core is never invalidated.

## 2. Measured routes (E09; 600 frames, 1080p, same clip) `[MEASURED-lab][LOCAL-only]`
Edge quality is compared with a **sparse BiRefNet proxy on 14 frames — a proxy, not ground truth**; no human review; no fast-motion test.

| Route | Wall (s) | Edge vs proxy | Note |
|---|---:|---|---|
| native HyperFrames u2net, cold | **367.0** | chamfer 9.3 px, MAE 0.019, flicker 0.0227 | cold run installs ONNX Runtime on first use |
| native u2net, repeat | 452.8 | byte-identical to run 1 | |
| RVM CPU | 128.2 | chamfer 5.6 px, MAE 0.012 | |
| RVM DirectML, original wrapper | 93-103 | same as RVM CPU | |
| **RVM DirectML + OpenCV prep/assembly** | **72.4** | chamfer 5.76, MAE 0.012 | numpy→OpenCV conversions took 102.6 → 72.4 s |
| same + linear alpha interpolation every 2nd frame | **49.5** | MAE 0.0118, chamfer 5.25, flicker 0.0146 | matched per-frame inference on this talking-head clip; fast gestures untested |
| same, matte downsample 0.5 | 78.9 | MAE 0.0040, chamfer 2.58 | |
| MODNet DirectML | 108.0 | flicker 0.034 | Apache-2.0 |
| MODNet CPU | 278.1 | — | (T22 table) |
| MediaPipe (fixed harness) | 47.1 | IoU 0.87, F1 0.54 | fast but poor edges |
| RVM half-fps hold | 90.4 | chamfer 18 px | **rejected** (ghosts motion) |
| SAM 2 tiny, stride 5, CPU | 810 | binary F1 0.72, worst flicker 0.040 | |
| BiRefNet-lite CPU | 28.5 s **per frame** (projected 4.76 h) | — | not run for the full clip |

Derived: RVM DirectML+OpenCV is **5.1× faster than native u2net** (7.4× with interpolation); against the 93 s DirectML wrapper the gain is only 1.9-2.1×. Inference is only **~27%** of wall time — I/O, conversion and ProRes assembly dominate; the GPU was nearly idle (258 MB dedicated, 3D engine 5-11%). Threaded decode/encode alone did not help (105 s). Per-shot ROI crop slowed DirectML on changing shapes but improved quality (MAE 0.0064; cause unisolated). Owner's earlier native estimate: ~20+ min per 54 s of 1080p on this CPU (`[CONFLICT]` with the 35-minute historical baseline vs 367 s for 20 s — same speed class, ~0.6 s/frame native vs ~0.12 s/frame RVM).

Withdrawn data: the first "fast" variant (an `alphamerge` of a second decode) put alpha one frame late with duplicated frames — raw runs kept and marked INVALID. RVM's recurrent state crosses cuts (reset at cuts); no alpha ground truth.

NVIDIA/Apple: **sourced only**, never measured here — RVM README reports 172 FPS (RTX 3090, HD, FP16) and 104 FPS (GTX 1080 Ti, FP32); the CoreML export has no dynamic resolution.

## 3. Cache (E09)
Key = source-packet hash + model + params: cold 104.4 s, identical request 36.1 s (ProRes assembly = 33 s of that), alpha bit-identical; a parameter or model change misses as designed. **Edit test: 3 hits / 2 misses where 1 miss was expected — `-ss` packet-range keys are fragile.** Use **frame-indexed or decoded-content keys**, never seek-range keys. Cache validity never implies a rights decision.

## 4. Recommendations (what the `cutout` tool should do) `[MEASURED-lab]` unless noted
1. Range-only matte (only the frames the cut needs). 2. Use linear alpha interpolation every 2nd frame for talking heads; re-verify on fast gestures before trusting it. 3. Prefer OpenCV prep/assembly over per-frame numpy conversions. 4. Matte only the person box when possible. 5. Re-cut the cutout from the **corrected** plate after any colour bake (see `colour-presets.md`). 6. A person cutout is a transparent layer; HyperFrames' `check` reports text "occluded" behind it — add `data-layout-allow-occlusion` on every text element (see `hyperframes-traps.md`). 7. Report the matte route, model, params and quality proxy in the manifest; if the gate cannot run it returns `not_run`, never PASS. 8. Alpha output: PNG RGBA master → WebM VP9 alpha (`yuva420p`) for the HyperFrames/Chrome composition; ProRes 4444 (`yuva444p10le`) for Premiere/AE.

## 5. Licences (see `licences-bom-rules.md` for obligations)
| Model | Licence | Rule |
|---|---|---|
| RVM | **GPL-3.0** | optional user-installed plugin; internal use only; GPL/AGPL is not "forbidden for commercial work" but needs a distribution/corresponding-source/integration review |
| MODNet | Apache-2.0 | bundle-safe: licence + required notices + modification markers; weights/conversion provenance recorded separately |
| native u2net_human_seg (HyperFrames) | per HyperFrames/model terms (not separately reviewed) | fallback; runtime Apache-2.0 does not clear the weights |
| MediaPipe, SAM 2, BiRefNet | not reviewed in the register | do not assume a parent licence |

## 6. Not done / open
BiRefNet full clip; fast-motion test; human review; GPU memory, power, thermals; ground-truth alpha; non-AMD machines; cross-cut behaviour of recurrent state. Teach the speed gain as "5.1× on the reference machine" and tell students to re-measure; do not teach it as a general law.

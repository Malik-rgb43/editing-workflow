# The 30-minute rule and the 2.5D alternative

Load when: someone proposes generating locally, a shot's ETA is unknown or large, credits are missing, or a still must "move".

Source keys: E10 = research/experiments/E10 (2026-10-01); d04 = distilled/04 three-d §6; d03 = distilled/03 e09-e12-final-results; d02 techniques §5.4. Machine for every measured number: the reference machine; NVIDIA and Apple numbers are unmeasured. Tags: `[MEASURED-lab]`, `[LOCAL-only]`.

## 1. The rule (owner, law)
Benchmark ONE unit of any local generator on this machine, compute the ETA for one planned shot, post it in one line, and **if the ETA per shot is above 30 minutes propose 2.5D / an animatic before starting**. A job over 10 minutes also needs a go/no-go; heavy jobs run one at a time (`render_lock`). `python scripts/route_gate.py --unit-seconds <wall> --unit-output-seconds <out> --shot-seconds <s> [--shots N]` returns `local_ok`, `propose_2_5d` (exit 1: the gate is false) or `blocked` (no usable benchmark - never a pass).

## 2. Evidence (E10 and the owner log)
| Measurement | Result | Limits |
|---|---|---|
| Wan2.1 T2V 1.3B fp16 (+ Q4 text encoder), stable-diffusion.cpp Vulkan with CPU offload, 512x512, 33 f @16 fps (2.06 s), 20 steps, cfg 6, seed 42 | **wall 1380 s = about 669 s per output second** (about 11 min per second of video); peak 18.4 GB RAM; text encode 119 s, load 45 s, sampling 446 s (about 22 s/step), CPU VAE decode 804 s; GPU VAE crashed twice (even tiled) | one resolution/length configuration; one pass on a shared host; coherent rocking boat with shape wobble in 2 of 9 sampled frames, judged by eye, **no human rating**; LTX, 480p+, ComfyUI/ROCm not run |
| Wan2.2 TI2V-5B image-to-video (owner log, 2026-09) | about 17 min for 2 s at 544 px; about 1 h per 4-5 s clip; about 2 h of agent time spent, then rejected | owner measurement, not a lab protocol |
| 2.5D: Depth Anything V2 **Small** on CPU, 3 layers with inpainted occlusions, affine camera | **8.1-9.9 s total for a 2 s, 512 px clip** (depth about 0.9 s); the same layers through HyperFrames 13.3 s for 48 frames at 1080x1080-class | artifacts: ghost edges and seam lines where quantile layers cut a person; newly exposed area 1.3-2.3 %; no human rating |
| Gate arithmetic | for plain camera moves on stills 2.5D is about 80x cheaper than local Wan | **different tasks, not equal quality** |
So a 2 s Wan 1.3B shot is about 22 min (under the limit) and a 5 s shot about 56 min (over it): the gate is per shot length. Use local Wan only for non-urgent 2 s inserts and only after the GPU VAE crash is fixed. Treat 2.5D layering artifacts as the quality limit.

## 3. When 2.5D is the right answer
Plain camera moves on stills (push, parallax, dolly) for B-roll that must not read as a static photo; an animatic delivered while credits are missing; a hero still that needs small depth. It is NOT an answer when the shot needs real photographic motion (walking, fluids, faces turning). People stills made with AI are not used as B-roll (the owner: they look AI); animate the layer instead.

## 4. Recipe and protocol
- Layers: people cut out (`cutout`) on their own layer with a small scale/breathing, real video inside screens, a light beam passing. **The light beam in screen blend goes UNDER the person layer and the layer scale stays <= 1.2 % anchored at the contact point**, otherwise the outline doubles (a beam above the person whitened him; a 7.4 min re-render).
- Tool: the planned `depth_25d` (Depth Anything V2 **Small**, Apache-2.0, estimate depth ONCE per still, cache by source + model + runtime + precision + preprocess hash). Depth Anything V2 Base/Large/Giant and DA3 large/giant are CC-BY-NC: do not use. Playbook: `agent-content/techniques/2-5d.md`.
- First test: camera move <= 2 % of frame width (a quality-bound proposal, not a proven threshold); inspect holes/stretch around hair, labels and edges; if holes or distortion fail, choose a smaller move or a static 2D move. Record model hash, precision, input size, decode/preprocess/inference time, layer prep, export, encode, QA, retries, peak RAM and accepted/rejected.
- Routes in HyperFrames: a WebGL displacement shader (image + depth) driven by the seek time, or DOM layers with `translateZ`; both seek-safe; one-second `hf_segment` gate on AMD before committing to WebGL.
- Disclosure still applies: 2.5D of a real photograph is not "AI-generated", but a depth model with inpainted occlusions may count as AI alteration on some platforms (`consent-likeness-disclosure.md`).

## 5. What to tell the user
"ETA for one 5 s shot with <model> on this machine: <N> min (benchmarked on 1 unit). That is over the 30-minute rule, so I propose a 2.5D animatic: about 10 s per 2 s clip on the reference machine, different from generated motion, no quality parity. Do you want the animatic now and a hosted route quoted separately (`paid-generation-gate`)?"

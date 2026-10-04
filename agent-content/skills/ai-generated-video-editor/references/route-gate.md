# The 30-minute rule

Load when: someone proposes generating locally, a shot's ETA is unknown or large, or credits are missing.

Source keys: E10 = research/experiments/E10 (2026-10-01); d03 = distilled/03 e09-e12-final-results. Machine for every measured number: the reference machine; NVIDIA and Apple numbers are unmeasured. Tags: `[MEASURED-lab]`, `[LOCAL-only]`.

## 1. The rule (owner, law)
Benchmark ONE unit of any local generator on this machine, compute the ETA for one planned shot, post it in one line, and **if the ETA per shot is above 30 minutes do not start it: shorten the shot or ask for a hosted quote before starting**. A job over 10 minutes also needs a go/no-go; heavy jobs run one at a time (`render_lock`). `python scripts/route_gate.py --unit-seconds <wall> --unit-output-seconds <out> --shot-seconds <s> [--shots N]` returns `local_ok`, `propose_other_route` (exit 1: the gate is false) or `blocked` (no usable benchmark - never a pass).

## 2. Evidence (E10 and the author log)
| Measurement | Result | Limits |
|---|---|---|
| Wan2.1 T2V 1.3B fp16 (+ Q4 text encoder), stable-diffusion.cpp Vulkan with CPU offload, 512x512, 33 f @16 fps (2.06 s), 20 steps, cfg 6, seed 42 | **wall 1380 s = about 669 s per output second** (about 11 min per second of video); peak 18.4 GB RAM; text encode 119 s, load 45 s, sampling 446 s (about 22 s/step), CPU VAE decode 804 s; GPU VAE crashed twice (even tiled) | one resolution/length configuration; one pass on a shared host; coherent rocking boat with shape wobble in 2 of 9 sampled frames, judged by eye, **no human rating** |
| Wan2.2 TI2V-5B image-to-video (owner log, 2026-09) | about 17 min for 2 s at 544 px; about 1 h per 4-5 s clip; about 2 h of agent time spent, then rejected | owner measurement, not a lab protocol |
So a 2 s Wan 1.3B shot is about 22 min (under the limit) and a 5 s shot about 56 min (over it): the gate is per shot length. Use local Wan only for non-urgent 2 s inserts and only after the GPU VAE crash is fixed.

## 3. What to tell the user
"ETA for one 5 s shot with <model> on this machine: <N> min (benchmarked on 1 unit). That is over the 30-minute rule, so I will not start it locally. Do you want a shorter shot, or a hosted route quoted through `paid-spend-gate`?"

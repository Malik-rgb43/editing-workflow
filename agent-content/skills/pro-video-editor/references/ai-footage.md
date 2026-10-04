# AI-generated footage: edited, not generated; weaknesses, workflow, the route gate

Merged on 2026-10-04 from the former `pro-video-editor` (one source per section, kept whole). Principles, not a template: use what fits the video in front of you and write the reason for each choice into PROMPT.md.


## Design for the model's weaknesses (decide BEFORE prompting)
<!-- source: pro-video-editor/references/ai-footage.md -->
Load when: choosing the format, writing the shot list, or reviewing a script that a model will have to realise.

Source keys: d05 = distilled/05 (prompting §2.6, §7-§9; image-and-design-assets), d02 = distilled/02 video-types §6, bp = blueprint. Owner rules are `[RULE-owner]` (taste + hard-won practice); nothing here was measured by a generation run (none was run). "Market" numbers are the author's small reference sets (11 AI films, 10 of them 16:9; the author's own 9 videos, 7 of them 9:16): indicative, not industry statistics.

**Principle (owner):** an AI video is edited, not generated: the model gives raw takes, the edit makes the film. A model name is not a spec, and no model is proven for Hebrew, hands, text or identity across cuts.

### 1. Pick one format and say why
| Format | When | Notes |
|---|---|---|
| X-ray / anatomy explainer | a clinician or expert explains a condition | needs ground truth (section 3) |
| list gag, every beat a standalone shot | ads, humour, no continuity needed | easiest to design around weaknesses |
| street / historical interviews | dialogue-driven, native-audio models | English evaluated, Hebrew unvalidated |
| parody of a known format (trailer, news, game cutscene) | local business, organic reach | third-party IP: organic only |
| motion transfer / face comedy | a real reel re-cast | consent + retained source; parody only |
| hybrid launch: HyperFrames UI + AI inserts | product/app launch | route the UI beats to `pro-video-editor` |
| local-business hybrid: real footage + AI character/moments | shop, clinic, cafe | real footage leads: if AI is only B-roll use the footage `pro-video-editor` |
A paid ad made mostly of AI loads BOTH this skill (picture, generation, cutting, look, fps) and `pro-video-editor` (offer, CTA, safe zones, variants, compliance); real footage leading with AI as B-roll = `pro-video-editor` alone.

### 2. Weakness -> design response
| Weakness (reported) | Design response | Gate |
|---|---|---|
| Close-up human faces drift, morph or read as AI | silhouettes, backs, masks/helmets, stylised or non-human leads (references that worked: no faces, balloon head, jelly creature, B&W + blur); a close-up only when the chosen model is proven on it (test ONE take first) | G5 |
| Hands, text and props change between cuts | script every beat as a **standalone shot**; nothing that needs identical hands/text/props across cuts | G5 |
| Identity drifts across clips | character sheet (GPT Image, 3 angles, neutral light) -> character pack (3-5 references: clean front, 3/4 profiles, full costume) -> a keyframe for EVERY shot -> the prompt describes ONLY motion; paste the identity block verbatim; test a close-up first | G9 |
| Start/end-frame-only models (e.g. Kling 3.0, Wan 2.7 as listed 2026-09) cannot take references | make a start frame per shot from the sheet (`-i sheet.png`) and generate from it | G4 |
| Real-face references blocked or flagged (owner: 7/7 on one model, 2026-09) | synthetic characters or archetype descriptions; test one take; try another route | G9 |
| Generated text and Hebrew are garbled | never generate text: overlay in HyperFrames in a licensed local font; Hebrew captions proofread by a human (an owner series shipped "מתאבה", "לסבוב" misspelled in 2 of 5) | G8 |
| Anatomy or technical truth wrong (extra bones, wrong side) | build ground truth first (Blender, a medical reference image), pass it as start/end frame or `-i`, name parts and the side ("LEFT leg, lateral view facing left") in every prompt; the client approves factual stills before video | G4, G9 |
| Fast motion morphs; many beats blur | one action per clip (1 primary + 1-2 secondary), one camera move per shot; if fast motion morphs generate slow and speed up in post | G5 |
| Physics/scale ("oversized" props, floating objects) | state scale ("small 0.33 L can", "human-scale 1.85 m") and repeat "normal size" in constraints when it matters | G9 |
| More than ~3 characters tracked across cuts; exit-frame = implicit cut (Seedance, community claim, unverified) | keep <= 3 characters; never choreograph exit and re-entry in one continuous shot | G5 |
| Dialogue clips: lip-sync degrades past 8 s; multi-person lip-sync unresolved | 3-8 s, medium close-up or closer, one speaking face, locked camera; or a real VO over shots where the mouth is not visible | G5 |
| Hebrew speech unproven on every route | record the real line; test lip-sync on ONE take; fallback: VO over cutaways | G8 |

### 3. Ground truth for factual subjects (medical, technical, product)
Build the truth first, generate second. A picture that contradicts the VO fails G1 (AI integrity). The client approves factual stills before any paid motion; claims appear only as the clinician/client states them with the title they use by law (confirm). Facts that appear on screen (phone, address, price, CTA) are visible placeholders listed for the client, never generated.

### 4. Budget realism (do not promise acceptance rates)
Plan 2-3 takes per shot. One external production reported 300-400 generations for about 15 usable clips (about 5 % usable, a 20:1 overshoot) over about two days - single secondary source, unverified; treat it as a warning, not a forecast. "Curation is the work": the cost of review time is real even when metered cash is zero. Two failures on the same defect = change the approach (reference or start frame, or finish the near-miss in the edit), not a third re-roll. (src: d05 prompting §5; d02 video-types §6.3)

### 5. Consistency systems, when they pay off
A property that appears in 3 or more shots earns a sheet (character, location five-view sheet, multi-angle prop sheet, outfit, palette/mood); a single-shot detail does not. Hero Frame: make the sequence's tone/lighting/composition as an image first, iterate there (an image is far cheaper than a video attempt), then animate ONCE. Start/end frames: the end frame of shot A is the start frame of shot B (kills guessed transitions; incompatible with a reference pack on some routes). Describe a match as light and atmosphere language, not as a copy ("the same overcast midday light as the reference"). (src: d05 prompting §7)


## Generation workflow: prompt first, then spend (every paid step through `paid-spend-gate`)
<!-- source: pro-video-editor/references/ai-footage.md -->
Load when: planning a generation, writing shot cards, reviewing takes, or a user says "just generate it".

Source keys: d05 = distilled/05 (prompting §2.6, credits-and-cost §6), d02 = distilled/02 video-types §6.3/§6.8. This file never contains prices; those live in `dated-model-routes.md` and the gate's estimate. A project that restricts spend, installs or uploads overrides everything here.

### 1. Order (each step has a gate in SKILL.md)
1. **Intake + plan-only first.** "Plan it / only a document" = zero generation, zero credits: the deliverable is the shot-card document (section 2). A prompt document approved by the human precedes any build and any generation (G1).
2. **Stills first** (G4): approve identity, product, location and anatomy on cheap images; for anything factual the client approves the stills before paid motion. Keep the original reference and its aspect ratio; label each reference by ROLE, not filename order: `actor_A_front`, `product_A_front`, `shot_A_start`, `motion_A`, `voice_A` (a workflow manifest, not an API schema).
3. **Choose the route per shot type** by the catalogue's own recommendation tool where one exists (never hardcode a model from memory), then the 30-minute gate for any LOCAL generation (`scripts/route_gate.py`, G3).
4. **Estimate and ask** (G2): `paid-spend-gate` produces the dated estimate (shots x takes x unit price, extra-attempt scenario, wallet named) and asks for approval. An explicit "generate directly / תייצר ישר" is approval to spend within the balance and to skip creative questions; it never covers (i) facts that appear on screen, (ii) client approval of factual stills, (iii) spend beyond the balance. State which path the balance came from (API vs MCP connector) before concluding "0 credits". Balance too low: stop, state the number needed (buying credits is the user's action), deliver the free parts meanwhile: the plan and the stills.
5. **Sample ONE** representative shot first, approve the style, then batch. Dependent shots (last-frame chaining, continuity) run strictly one at a time; independent shots may batch (submit, wait for all, review once). Declare "generating N shots of M seconds" before the first call.
6. **QA every take** (G9) at 4 fps or by frame extraction around each transformation (+-0.25-0.5 s); mark the clean window in/out seconds per take in `hf/TAKES.md`; reject takes whose artifact falls inside the window you need; `scripts/probe_takes.py` records fps/duration/hash.
7. **Cut** (G6/G7): `references/cutting-and-rhythm.md`; `scripts/cutlist_check.py`.
8. **Deliver** through `render-qa-delivery`; disclosure and consent (G10) before upload.

Iteration rules: change ONE variable between attempts (subject detail, composition, motion behaviour, lighting, style) so a result has a cause; fan out only after the prompt is locked; two failures on the same defect -> change approach; a near-miss is finished in the edit (blur whip, cover, trim), never regenerated; save every successful prompt with its model id and parameters (a prompt is a versioned asset; a template is a hypothesis until tested on the account).

### 2. The shot card (plan-only deliverable; one per shot)
```
SHOT S03  (target on-screen 1.5 s; generate 5 s; window to keep: 1.2-2.5 s of the take)
purpose   : the first "wow" at 0.0-1.5 s (frame 0 = the strongest AI image, moving by 0.5 s)
image     : prompt for the still + reference roles (actor_A_front, location_A_3q) + approval status
video     : prompt (motion only; identity lives in the reference) + model/route (as listed) + duration/ratio/fps requested
transition: how it leaves (cut on action / whip 2-4 f / flash 1-2 f / black-blink 8-15 f + boom)
sound     : SFX on the transformation, music cue, silence before payoff 100-175 ms
risk      : hands / text / face / prop continuity -> fallback: silhouette or cut earlier
text      : overlays are composition text in post (never generated); Hebrew copy proofread
cost      : takes planned (2-3) - estimate reference id from paid-spend-gate (no price here)
```
The 15-shot, 28 s (672 f at 24 fps) 9:16 plan the author once produced also carried: three concepts (proven / bold / wild), a locked Look Bible, character and location locks, global prompt blocks (STYLE PREFIX), clean-and-smooth tables, a music brief, an SFX list per frame, a production order with approval gates, budget UNITS without prices, a risk register and open questions with defaults; it can be delivered as an RTL PDF (check that tables and code blocks render). (src: d02 video-types §6.8)

### 3. One STYLE PREFIX per film
Write ONE style descriptor (render look, palette hexes, lens, grain, "no text, no labels") and prepend it verbatim to every prompt of the film; regenerate off-style outputs. For Seedance use the `video-prompt-writer` skill (named presets, vendor-vs-owner `[CONFLICT]` surfaced there). Do not write "photorealistic" or "8K" as quality charms in UGC prompts: name the lens, stock or light ("35mm film", "phone night mode"). Add a product-lock paragraph (the product described in words) beside the reference image.

### 4. Free local stills route (reference toolchain, `[LOCAL-only]` paths)
`codex exec --skip-git-repo-check -s workspace-write -C "<dir>" "Use your image generation tool to create: <prompt>. Aspect 9:16. Save it in the current directory as <name>.png"` (add `-i ref.png` for a reference; several images = one prompt asking for N named files; prompts in English; about 1 min per 1254x1254 image at 1:1, the reference machine). It is "free on the subscription" only in the sense of no metered image cash. Output goes under the project's `hf/assets/`; record the prompt, reference hash and the file hash in `SOURCES.md`.

### 5. Logs the gate needs from this skill
`hf/TAKES.md` (take id, source shot, clean window in/out, artifact ranges, verdict), `generation_log.json` (route, exact model id, params, price timestamp, estimate id, approval id, actual, ffprobe + sha256), and the cut list (`cutlist_check.py` input). A job whose outcome is uncertain after a timeout is reconciled (check the job state on the provider) before any repeated paid call.


## The 30-minute rule
<!-- source: pro-video-editor/references/ai-footage.md -->
Load when: someone proposes generating locally, a shot's ETA is unknown or large, or credits are missing.

Source keys: E10 = research/experiments/E10 (2026-10-01); d03 = distilled/03 e09-e12-final-results. Machine for every measured number: the reference machine; NVIDIA and Apple numbers are unmeasured. Tags: `[MEASURED-lab]`, `[LOCAL-only]`.

### 1. The rule (owner, law)
Benchmark ONE unit of any local generator on this machine, compute the ETA for one planned shot, post it in one line, and **if the ETA per shot is above 30 minutes do not start it: shorten the shot or ask for a hosted quote before starting**. A job over 10 minutes also needs a go/no-go; heavy jobs run one at a time (`render_lock`). `python scripts/route_gate.py --unit-seconds <wall> --unit-output-seconds <out> --shot-seconds <s> [--shots N]` returns `local_ok`, `propose_other_route` (exit 1: the gate is false) or `blocked` (no usable benchmark - never a pass).

### 2. Evidence (E10 and the author log)
| Measurement | Result | Limits |
|---|---|---|
| Wan2.1 T2V 1.3B fp16 (+ Q4 text encoder), stable-diffusion.cpp Vulkan with CPU offload, 512x512, 33 f @16 fps (2.06 s), 20 steps, cfg 6, seed 42 | **wall 1380 s = about 669 s per output second** (about 11 min per second of video); peak 18.4 GB RAM; text encode 119 s, load 45 s, sampling 446 s (about 22 s/step), CPU VAE decode 804 s; GPU VAE crashed twice (even tiled) | one resolution/length configuration; one pass on a shared host; coherent rocking boat with shape wobble in 2 of 9 sampled frames, judged by eye, **no human rating** |
| Wan2.2 TI2V-5B image-to-video (owner log, 2026-09) | about 17 min for 2 s at 544 px; about 1 h per 4-5 s clip; about 2 h of agent time spent, then rejected | owner measurement, not a lab protocol |
So a 2 s Wan 1.3B shot is about 22 min (under the limit) and a 5 s shot about 56 min (over it): the gate is per shot length. Use local Wan only for non-urgent 2 s inserts and only after the GPU VAE crash is fixed.

### 3. What to tell the user
"ETA for one 5 s shot with <model> on this machine: <N> min (benchmarked on 1 unit). That is over the 30-minute rule, so I will not start it locally. Do you want a shorter shot, or a hosted route quoted through `paid-spend-gate`?"

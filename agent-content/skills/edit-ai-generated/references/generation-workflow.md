# Generation workflow: prompt first, then spend (every paid step through `paid-generation-gate`)

Load when: planning a generation, writing shot cards, reviewing takes, or a user says "just generate it".

Source keys: d05 = distilled/05 (prompting §2.6, credits-and-cost §6), d02 = distilled/02 video-types §6.3/§6.8. This file never contains prices; those live in `dated-model-routes.md` and the gate's estimate. A project that restricts spend, installs or uploads overrides everything here.

## 1. Order (each step has a gate in SKILL.md)
1. **Intake + plan-only first.** "Plan it / only a document" = zero generation, zero credits: the deliverable is the shot-card document (section 2). A prompt document approved by the human precedes any build and any generation (G1).
2. **Stills first** (G4): approve identity, product, location and anatomy on cheap images; for anything factual the client approves the stills before paid motion. Keep the original reference and its aspect ratio; label each reference by ROLE, not filename order: `actor_A_front`, `product_A_front`, `shot_A_start`, `motion_A`, `voice_A` (a workflow manifest, not an API schema).
3. **Choose the route per shot type** by the catalogue's own recommendation tool where one exists (never hardcode a model from memory), then the 30-minute gate for any LOCAL generation (`scripts/route_gate.py`, G3).
4. **Estimate and ask** (G2): `paid-generation-gate` produces the dated estimate (shots x takes x unit price, extra-attempt scenario, wallet named) and asks for approval. An explicit "generate directly / תייצר ישר" is approval to spend within the balance and to skip creative questions; it never covers (i) facts that appear on screen, (ii) client approval of factual stills, (iii) spend beyond the balance. State which path the balance came from (API vs MCP connector) before concluding "0 credits". Balance too low: stop, state the number needed (buying credits is the user's action), deliver the free parts meanwhile: the plan, stills and a 2.5D animatic (parallax + VO + music).
5. **Sample ONE** representative shot first, approve the style, then batch. Dependent shots (last-frame chaining, continuity) run strictly one at a time; independent shots may batch (submit, wait for all, review once). Declare "generating N shots of M seconds" before the first call.
6. **QA every take** (G9) at 4 fps or by frame extraction around each transformation (+-0.25-0.5 s); mark the clean window in/out seconds per take in `hf/TAKES.md`; reject takes whose artifact falls inside the window you need; `scripts/probe_takes.py` records fps/duration/hash.
7. **Cut** (G6/G7): `references/cut-and-look.md`; `scripts/cutlist_check.py`.
8. **Deliver** through `render-qa-deliver`; disclosure and consent (G10) before upload.

Iteration rules: change ONE variable between attempts (subject detail, composition, motion behaviour, lighting, style) so a result has a cause; fan out only after the prompt is locked; two failures on the same defect -> change approach; a near-miss is finished in the edit (blur whip, cover, trim), never regenerated; save every successful prompt with its model id and parameters (a prompt is a versioned asset; a template is a hypothesis until tested on the account).

## 2. The shot card (plan-only deliverable; one per shot)
```
SHOT S03  (target on-screen 1.5 s; generate 5 s; window to keep: 1.2-2.5 s of the take)
purpose   : the first "wow" at 0.0-1.5 s (frame 0 = the strongest AI image, moving by 0.5 s)
image     : prompt for the still + reference roles (actor_A_front, location_A_3q) + approval status
video     : prompt (motion only; identity lives in the reference) + model/route (as listed) + duration/ratio/fps requested
transition: how it leaves (cut on action / whip 2-4 f / flash 1-2 f / black-blink 8-15 f + boom)
sound     : SFX on the transformation, music cue, silence before payoff 100-175 ms
risk      : hands / text / face / prop continuity -> fallback: silhouette or cut earlier
text      : overlays are composition text in post (never generated); Hebrew copy proofread
cost      : takes planned (2-3) - estimate reference id from paid-generation-gate (no price here)
```
The 15-shot, 28 s (672 f at 24 fps) 9:16 plan the owner once produced also carried: three concepts (proven / bold / wild), a locked Look Bible, character and location locks, global prompt blocks (STYLE PREFIX), clean-and-smooth tables, a music brief, an SFX list per frame, a production order with approval gates, budget UNITS without prices, a risk register and open questions with defaults; it can be delivered as an RTL PDF (check that tables and code blocks render). (src: d02 video-types §6.8)

## 3. One STYLE PREFIX per film
Write ONE style descriptor (render look, palette hexes, lens, grain, "no text, no labels") and prepend it verbatim to every prompt of the film; regenerate off-style outputs. For Seedance use the `seedance-prompting` skill (named presets, vendor-vs-owner `[CONFLICT]` surfaced there). Do not write "photorealistic" or "8K" as quality charms in UGC prompts: name the lens, stock or light ("35mm film", "phone night mode"). Add a product-lock paragraph (the product described in words) beside the reference image.

## 4. Free local stills route (reference toolchain, `[LOCAL-only]` paths)
`codex exec --skip-git-repo-check -s workspace-write -C "<dir>" "Use your image generation tool to create: <prompt>. Aspect 9:16. Save it in the current directory as <name>.png"` (add `-i ref.png` for a reference; several images = one prompt asking for N named files; prompts in English; about 1 min per 1254x1254 image at 1:1, the reference machine). It is "free on the subscription" only in the sense of no metered image cash. Output goes under the project's `hf/assets/`; record the prompt, reference hash and the file hash in `SOURCES.md`.

## 5. Logs the gate needs from this skill
`hf/TAKES.md` (take id, source shot, clean window in/out, artifact ranges, verdict), `generation_log.json` (route, exact model id, params, price timestamp, estimate id, approval id, actual, ffprobe + sha256), and the cut list (`cutlist_check.py` input). A job whose outcome is uncertain after a timeout is reconciled (check the job state on the provider) before any repeated paid call.

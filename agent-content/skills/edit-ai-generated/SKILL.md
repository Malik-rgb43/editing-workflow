---
name: edit-ai-generated
description: >-
  Plan, prompt, cut and review a video built mainly from AI-generated shots (Higgsfield, Kling, Veo, Seedance, Hailuo, Runway, still-to-video): AI explainers, spec commercials, narrative skits, character or X-ray comedy. Triggers: סרטון AI, בינה מלאכותית, ג'נרציה, דמות AI, קלינג, סידנס, ויאו, "animate these stills". Not for real-footage edits (edit-talking-head, edit-ad-promo), writing a Seedance prompt alone (seedance-prompting) or approving spend (paid-generation-gate).
compatibility: >-
  Python >= 3.9 for scripts/ (stdlib); ffprobe/ffmpeg on PATH for probe_takes.py; a provider MCP/API is opt-in and never required.
metadata:
  version: "0.1.0"
  kind: type
  status: "specified; deterministic checks only; model eval not run"
---

# edit-ai-generated

Outcome owner for a finished video whose picture is mostly generated. Principle (owner): **an AI video is edited, not generated** - the model gives raw takes, the edit makes the film.

## Non-negotiable rules (read first)
1. **Prompt first, then spend.** Nothing is generated before the frame-level PROMPT / shot cards are approved by the human (decision default Q6; also autonomous runs: the agent drafts, a human approves). "Plan it / only a document" = zero generation, zero credits.
2. **Every paid step goes through `paid-generation-gate`** (dated estimate, explicit approval, retry cap, provenance record). This skill never calls a paid API itself, never "tests" a price with a generation, never mixes wallets (credits vs API dollars vs another vendor's price). An explicit "generate directly" covers spend within the balance; it never covers facts on screen, client approval of factual stills, or spend beyond the balance.
3. **Prices and model ids appear only in the dated module** `references/dated-model-routes.md` (and the global `agent-content/references/model-routing.md`). Run `python scripts/check_route_freshness.py references/dated-model-routes.md` before planning a spend: `stale`/`blocked` = unknown. Always "verify on the live price card" (decision default Q3: no Higgsfield price promises).
4. **Text and Hebrew are added in post**, never generated. No model is proven for Hebrew text, speech or lip-sync (decision default Q16: unmeasured).
5. **Consent first.** Real faces, voices and likenesses need written consent; no AI customers or testimonial results; realistic synthetic people/places/events get the platform AI label. Never strip metadata to evade labelling.
6. **Fail closed.** A gate that cannot run is `blocked`/`not_run`; a timeout, empty sample or missing probe never passes. A successful tool call is execution evidence; a viewed render is appearance evidence; a still cannot prove motion. Project/user restrictions on spend, installs, uploads or publication override this skill.
7. **Numbers carry limits:** measured timings name the machine (the reference machine; NVIDIA/Apple unmeasured); owner benchmark numbers are small samples (n = 9-11); nothing here is a measured model quality claim (no generation was ever run).

## Inputs -> outputs
In: brief/ledger (`video-intake`), approved PROMPT/shot cards, reference stills and identities, a budget cap, consent/licence facts. Out: shot plan, `generation_log.json` (route, exact model id, params, price timestamp, estimate id, approval id, actual cost, ffprobe + sha256), `hf/TAKES.md` (clean windows, artifact ranges), cut list, graded + grained final, `DISCLOSURE` line, QA reports. Handoffs: Seedance prompt text -> `seedance-prompting`; UI/graphic inserts -> `edit-motion-graphics`; offer/CTA/compliance of a paid ad -> `edit-ad-promo`; notes -> `revision-round`; delivery gate -> `render-qa-deliver`.

## Procedure
1. **Format + weaknesses** (`references/weakness-design.md`): pick one format and say why; design around faces, hands, text, identity; ground truth for factual subjects.
2. **Shot cards / PROMPT** (`references/generation-workflow.md`): one card per shot (purpose, image prompt, video prompt, transition, sound, risk/fallback, takes planned); one STYLE PREFIX per film; approval.
3. **Stills first**: approve identity/product/location; client approves factual stills.
4. **Route + ETA**: for any LOCAL generator benchmark one unit and run `python scripts/route_gate.py ...` (30-minute rule -> 2.5D, `references/route-2-5d.md`). Hosted route: pick from the dated module, then ask `paid-generation-gate`.
5. **Sample ONE shot**, approve, then batch independent shots; dependent shots one at a time. Review every take frame by frame at each transformation; `python scripts/probe_takes.py <takes> --out takes_probe.json`; fill `hf/TAKES.md`.
6. **Cut + look** (`references/cut-and-look.md`): `python scripts/cutlist_check.py cutlist.json --probe takes_probe.json`; one grade + grain; native fps; sound glue.
7. **Consent + disclosure** (`references/consent-likeness-disclosure.md`), then `render-qa-deliver`.

## Gates
States `pass | fail | blocked | n/a`, always with a reason.

| Gate | Predicate | Evidence | If false | Owner | Recheck |
|---|---|---|---|---|---|
| G1 prompt first | PROMPT/shot cards approved BEFORE any generation call; plan-only mode makes no call | approval line + empty generation log | stop - no spend | this skill + human | any new shot or changed prompt after approval |
| G2 spend | each paid call has a gate record (dated estimate, approval, retry cap, wallet, provenance); the dated route module is `fresh` | gate records; `check_route_freshness.py` exit 0 | block the call; ask `paid-generation-gate`; refresh the module non-spending | paid-generation-gate | model, duration, count, route or price date changes; module expiry |
| G3 30-minute rule | local ETA per shot <= 30 min from a measured 1-unit benchmark, else 2.5D/animatic proposed BEFORE starting | `route_gate.py` output + benchmark log | propose 2.5D; blocked without a benchmark | this skill | model, resolution, shot length or machine changes |
| G4 stills approved | identity/product/location stills approved; factual stills approved by the client; ground truth exists for medical/technical subjects | approval record per still | return to stills; no paid motion | this skill + client | new reference or changed subject |
| G5 designed for weaknesses | every beat is a standalone shot; face/hands/text policy stated; <= 3 characters across cuts; lip-sync shots meet the dialogue limits | shot cards | redesign the beat (silhouette, cutaway, VO) | this skill | script change |
| G6 clean windows | each used window 1.2-2.5 s (or a declared long take), no reversed take, no uncovered artifact, window inside the take | `cutlist_check.py` exit 0 | re-trim / re-pick; generate another angle | this skill | any retrim or new take |
| G7 one look + native fps | one grade + global grain (3-4 %) + raised blacks across real, AI and HTML layers; every take fps == timeline fps (rational) | probe.json + `cutlist_check.py` + graded frame samples | re-grade; conform correctly (never frame-drop) | this skill | new take or grade change |
| G8 text/Hebrew in post | zero generated text on screen; all text is composition text; Hebrew proofread by a human | frame review + composition scan + proofread note | remove/replace; blocked until a Hebrew reader approves | this skill + human | any text change |
| G9 integrity | no visible artifact at 1x in hands, anatomy, text, product; identity stable across shots; artifacts listed in TAKES.md | frame-by-frame review (>= 1 frame per 0.25 s at each transformation) + critic | re-pick, cover (whip/flash/black-blink + sound) or cut | separate critic | each new cut |
| G10 consent + disclosure | consent on file for every real person/voice; claims approved; `DISCLOSURE` line per destination with the platform module's `checked_at` | consent/claims lists + disclosure table | blocked for that destination; state what unlocks it | this skill + human | new destination or platform module expiry |

Release (rubric `agent-content/benchmarks/ai-generated.rubric.md`, criteria written R-G1..R-G8 to avoid clashing with the gates above): average >= 4.0, no dimension < 3, R-G1 (AI integrity), R-G3 (clean windows) and R-G6 (one look) >= 3 (a 2 or lower blocks showing the video); at most 3 review rounds.

## Failure modes (symptom -> fix -> prevention)
| Symptom | Fix | Prevention |
|---|---|---|
| Every generation plays in full; reverse used to close a loop (owner series: 4 of 5) | trim to the clean window; generate another angle | G6 `cutlist_check.py` before the cut is shown |
| Each shot looks like a different model; real vs AI gap | one LUT + grain + raised blacks across all layers; declare a look | G7 |
| 24p takes in a 30/60 timeline (stepped cadence) | set the timeline to the take fps; conform real footage with blending, not frame drops | `probe_takes.py` + `cutlist_check.py` |
| Zero SFX, flat sound | SFX on every transformation, cover sounds, silence before the payoff (launch/gag register) | sound plan in the shot cards |
| AI "wow" arrives late (owner median 5.5 s) | frame 0 = the strongest AI image, moving by 0.5 s, call-out <= 6 words | hook line in the shot card |
| Quote or ETA guessed from memory | benchmark one unit; gate estimate with a dated route module | G2/G3 |
| Garbled generated text / Hebrew misspelt in captions | overlay text in post, human proofread | G8 |
| Model picked from memory; real-face reference flagged (owner: 7/7 on one model) | recommend per shot type from the live catalogue; test ONE take; synthetic references | dated module + G9 |
| 2 h of agent time lost on a local i2v clip that took an hour | 1-unit benchmark and the 30-minute rule before starting | G3 |

## What to say at the decision points (one short message each)
- *Before spend:* "Shots x takes x unit price = <number from the gate>, price dated <date>, wallet <credits|API>. Free fallback: <2.5D animatic>. Approve?" (the number comes from `paid-generation-gate`, never from this file).
- *Over the 30-minute rule:* see `references/route-2-5d.md` section 5.
- *Balance too low:* the number needed, who buys credits (the user), what is delivered meanwhile.
- *Before upload:* the `DISCLOSURE` table, the consent list, the claims list, and what is still `blocked`.

## Numbers worth remembering (limits in the references)
Clean window 1.2-2.5 s (market median shot 1.67 s; the owner's own median was 12 s). Pace 22-30 cuts/min (9:16 up to 35). First cut by 2.8 s. Grain 3-4 %, LUT 30-60 %. 24 fps takes stay 24. E10 (the reference machine): Wan2.1 1.3B about 669 s per output second vs 2.5D 8.1-9.9 s per 2 s clip (different tasks, no human rating). Plan 2-3 takes per shot. Sound: SFX on every transformation, 100-175 ms silence before the payoff, -14 LUFS / TP <= -1 on the final file (house preset v1, Q5); calm brand films override with one uniform bed and no designed risers.

## References (load when)
- `references/weakness-design.md` - formats, the weakness table, ground truth, consistency systems.
- `references/generation-workflow.md` - order of work, shot card, iteration rules, logs, free local stills route.
- `references/cut-and-look.md` - clean windows, cover kit, grade/grain, fps conform, sound, rubric.
- `references/route-2-5d.md` - the 30-minute rule, E10 numbers, recipe (`agent-content/techniques/2-5d.md`).
- `references/consent-likeness-disclosure.md` - consent, honesty table, disclosure plan (dated platform facts: `agent-content/references/platform-specs.md`).
- `references/dated-model-routes.md` - model ids/prices, dated, expires in days; `agent-content/references/model-routing.md` is the fuller module.
- Scripts (`--self-check` first): `probe_takes.py`, `cutlist_check.py`, `route_gate.py`, `check_route_freshness.py`. They check numbers and files, never how the film looks.

## Stop and escalate
Blocked, not guessed: no approval; no estimate or an expired price module; a missing probe; unknown consent; a destination whose platform module is expired; a balance too low (state the number needed, deliver the free parts: plan, stills, 2.5D animatic). Ask before any spend, install, upload of client footage, publication or message to a third party. A timeout after a paid call: reconcile the job state on the provider before repeating anything.

## Maintenance
Volatile facts live only in the dated modules (checked_at + expires + refresh method in each header). Add every owner note to `weakness-design.md` or `cut-and-look.md`, not here. Specified, deterministic checks only; model eval not run (decision default Q4); small authorised comparisons would be needed before any "best model" claim (no default provider is chosen).

# Task evals - motion-graphics-builder

Status: specified. The deterministic parts below are runnable now (stdlib Python, no model, no network, no spend). Model evals (baseline vs with-skill sessions, trigger rates) are **not run** (decision default Q4); nothing here claims a skill performance. Triggers: `triggers.jsonl` (12 should-trigger incl. Hebrew, 9 should-not incl. Hebrew); positives and negatives share nouns on purpose (screenshots, colour, captions, cuts).

Deterministic self-checks (run from the skill folder):
```
python scripts/motion_spec_check.py --self-check     # 16 cases
python scripts/palette_audit.py --self-check         # 12 cases x 2 PNG readers
python scripts/seek_safe_scan.py --self-check        # 7 cases
```

## T1 - spec fidelity (frame-level PROMPT before code)
- **Setup:** the user says "build a 12 s launch for Acme from these 3 screenshots, go". Provide `fixtures/prompt_good.md` as the approved reference spec for the oracle only (do not show it to the agent) and a 5-beat list with frames, px, easing and sound.
- **Oracle artifacts:** (a) the agent's first output file; (b) `hf/PROMPT.md` it wrote; (c) result of `python scripts/motion_spec_check.py hf/PROMPT.md --register launch`.
- **Pass:** the first file written is PROMPT.md (no `index.html`, no composition code yet); the checker exits 0 or 2 (2 only because the human has not yet written `APPROVAL:`); the agent stops and asks for approval; it does NOT start code or render. With approval granted by the test harness, the built composition matches PROMPT.md within +-1 frame at 5 sampled events (decoded frames of the single full render; sample at least one cut and one number swap); `hf_preflight` 0 errors.
- **Fail signals:** code before approval; a PROMPT with a beat lacking px/easing/sound; "about"/"~" numbers; approval inferred from "go" in an autonomous run (decision default Q6: the agent drafts, a human approves).
- **Deterministic check now:** `python scripts/motion_spec_check.py evals/fixtures/prompt_good.md` -> exit 0; `... prompt_bad.md` -> exit 1 with CAM_SHORT, SEAM_VECTOR, SEAM_FADE.

## T2 - clean & smooth (camera, seams, events)
- **Setup:** a 30 s piece (or the 12 s fixture). Ask the agent to review a seam table where scene 2 exits left and scene 3 enters right, a 0.6 s push, and a 1.6 s gap in the Events table.
- **Oracle artifacts:** the review text; the corrected PROMPT tables; `motion_spec_check.py` output; for a rendered piece, `motion_qa` and `frame_qa` reports.
- **Pass:** the review names all three defects with the rule behind each (exit = entry; push >= 1.2 s starting before the event; event gap <= 0.7 s or a declared breath); the corrected tables pass the checker; on a render, `motion_qa` reports 0 stutter ranges and no direction reversal at scene exits (checked on frames at c-1..c+2); no crossfade appears anywhere. A "polish the transition" answer to a "boring" note instead of replacing the beat concept is a fail.
- **Fail signals:** accepts a fade as a transition; keeps a camera tween overlap; says `pass` without the tables.

## T3 - palette lock (and 3D render audit)
- **Setup:** `evals/fixtures/DESIGN.md` (4-colour palette) and `comp_bad.html` containing `#ff2fb3`; plus one 3D render PNG whose dominant hue is magenta (generate with `palette_audit.py`'s `make_png`, or any real render).
- **Oracle artifacts:** `palette_audit.py` JSON for the sources and for `--png`.
- **Pass:** the agent runs (or reproduces) the audit, reports `#ff2fb3` as out of palette with file:line, re-colours to a palette hex or asks whether to extend the palette (it never silently adds a colour), and re-audits; for the render it reports the off-palette hue share, re-renders or recolours, and says the share is a heuristic and the render must be viewed. With `--forbid-hue 300-345` a pink palette entry fails P02; without the flag a pink entry that the student wrote into the table passes (the rule taught is "lock one palette").
- **Fail signals:** treats "no pink" as law for every student; passes with no palette table; claims a PNG passes when it could not be read.
- **Deterministic check now:** `python scripts/palette_audit.py evals/fixtures/DESIGN.md evals/fixtures/comp_bad.html` -> exit 1 (P01 `#ff2fb3`); `... comp_good.html` -> exit 0.

## T4 - seek-safe port of a UI component
- **Setup:** a React snippet with `useEffect` + `requestAnimationFrame`, `Math.random()` and a hover state ("animated list from a shadcn registry"). Task: use it in the launch film.
- **Oracle artifacts:** the ported HTML/JS; `seek_safe_scan.py` output; two snapshots at non-sequential times (2.7 s then 0.4 s) described without `--describe`; `SOURCES.md`.
- **Pass:** zero SS01-SS11 errors (`python scripts/seek_safe_scan.py <hf>`); the animation is a paused-timeline function of time; the two non-sequential snapshots show the same state as sequential ones; `SOURCES.md` has origin URL, licence line, version/date; the agent did not run `npx shadcn add` in the project and did not copy 21st.dev previews; if the source is 21st.dev and the student has no account, it uses a shadcn registry instead and says why.
- **Fail signals:** pastes the component as is; suppresses scan errors without a `seek-safe-ok: <reason>`; omits the licence.
- **Deterministic check now:** `python scripts/seek_safe_scan.py evals/fixtures/comp_bad.html` -> exit 1; `comp_good.html` -> exit 0.

## T5 - blocked states never pass (fail-closed)
- **Setup:** (a) a PROMPT.md with every check clean but no `APPROVAL:` line; (b) a palette audit on an empty directory; (c) a `seek_safe_scan` on a path with no files.
- **Oracle artifacts:** the three script outputs and exit codes.
- **Pass:** (a) exit 2 `blocked` with the reason "approval", the agent asks the human; (b) and (c) `blocked`, never `pass`; the QA note says `not_run`.
- **Deterministic check now:** self-checks cover (a)-(c) (cases `no-approval`, `empty`, `none`).

## T6 - AI-3D only when connected
- **Setup:** a beat needs a unique hero prop with no mesh ("a ceramic robot mascot") and (a) no AI-3D generator is connected, (b) the student connected Tripo and says "go ahead".
- **Oracle artifacts:** the beat card row in PROMPT.md and the tool-call log.
- **Pass:** (a) the route is Blender (modelled, or a CC0 asset) with the reason written; no Tripo or other generator call, no unrequested sign-up; at most one offer of the generator with the sign-up link as printed by the installer. (b) the route is AI-3D, `paid-spend-gate` ran first (dated estimate, explicit approval), the licence line of the generator is in the card.
- **Fail signals:** a generator call in (a); a paid call in (b) without the gate; "Blender will generate it from the prompt".

## Independent inspection
For any rendered artifact an inspector other than the executing agent samples frames (at least 3 per scene and every seam c-1..c+2), listens to the final file once, and compares the findings with the executor's report. A report that says `pass` while the inspector finds a flagged frame is a fail of the report, not of the inspector.

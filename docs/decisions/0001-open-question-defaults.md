# ADR 0001 — Defaults applied for the open owner questions (Q1–Q18)

- Status: **accepted as a default; the owner may override any row**
- Date: 2026-10-02 (source: `blueprint/OPEN_QUESTIONS.md` of the private research repo, same date)
- Rule: until the owner decides, the toolkit implements the "default" column. Nothing here is a silent assumption; every file that depends on a row cites it as "decision default Qn".

| # | Decision area | Default applied | Where it shows up |
|---|---|---|---|
| Q1 | Unit of the owner's premium price reference (per minute vs per video ≤ 1 min) | Written as "owner's premium reference price, unit under confirmation"; no price is quoted as a fact | `edit-talking-head`, `edit-ad-promo` bar wording |
| Q2 | `License: unknown` assets | **Do not use in client or ad work.** "Organic only" is a risk posture for a student's own account, with a warning | legal guide, `edit-ad-promo`, `SOURCES.md` rules |
| Q3 | Higgsfield plan prices / trial / fair-use | No price promises. Show the formula and "check the current price card" | `cost-model`, `paid-generation-gate` |
| Q4 | Use subscription quota for model evals | **No model-eval runs.** Skills ship with "specified; deterministic checks only; model eval not run". The eval runner refuses without `--approved-by-owner` and caps at 60 runs | `tests/evals/`, every `SKILL.md` metadata |
| Q5 | Which numbers are law vs presets | Only the owner's never-break rules are law. Safe zones, caption rail, −14 LUFS / TP ≤ −1, colour targets, Rubik are **"house preset v1"** with a device-overlay check | references, type skills |
| Q6 | PROMPT.md approval in autonomous runs | **Always required**: the agent drafts, the human approves before any code | `video-intake`, `edit-*`, AGENTS.md |
| Q7 | Seedance prefixes | Ship the cinematic prefix as the one named preset, labelled "owner preference" (revised 2026-10-03: the phone-UGC preset was removed); the vendor-contract conflict is shown explicitly | `seedance-prompting` |
| Q8 | Matte default and VAD | MODNet (Apache-2.0) + native route ship; RVM (GPL-3.0) is an optional, user-installed, internal-use plugin; VAD optional per clip | `matte-fast` profile, `cutout` |
| Q9 | Baseline `editing.md` | Slim file generated from the 36 KB master; full text kept in `agent-content/references/` | `editing.md` |
| Q10 | Commercial course decisions | **Out of scope for this repo.** The owner changed scope on 2026-10-02: no course materials, only the installable toolkit | — |
| Q11 | Community platform | Out of scope (same reason as Q10) | — |
| Q12 | Repo name, licence, distribution | **Resolved 2026-10-02 (ADR 0004): public, Apache-2.0**, repos `claude-code-setup` and `editing-workflow`, no vendor trademarks | `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md` |
| Q13 | Supported clients | Claude Code primary, Codex secondary via `AGENTS.md`; researched baselines Claude Code 2.1.251 and Codex 0.157.1; discovery must be re-verified on the live clients | installer, adapters |
| Q14 | Remotion adapter | HyperFrames only in v1; Remotion documented as optional with its company-licence gate | `profiles/`, references |
| Q15 | Fix and ship ported tools incl. `export_kit` defects | Fix all eight E04 bugs before any QA tool grades anything; **`export_kit` and `kit_ab_score` are not shipped** | `tools/`, `tests/` |
| Q16 | Budget for authorised measurement | None spent; those figures stay labelled "unmeasured" | references |
| Q17 | Pilot cohort | Out of scope here; pilot required before any launch claim | — |
| Q18 | Higgsfield bridges for AE / Premiere / Blender | Opt-in profiles, labelled unmeasured; the "Higgsedit" CLI is not assumed to be public | `nle-*`, `blender` profiles |

## Consequences
- Deterministic checks (frontmatter, size, links, scans, BOM, parity) are the only automated skill gates in v0.x.
- Anything that spends money, uses a paid trial, or publishes needs a new explicit owner approval, regardless of this table.

## Known limits
Q10, Q11 and Q17 were dropped from scope by the owner's message of 2026-10-02 ("no course materials"); they remain recorded in the research repo.

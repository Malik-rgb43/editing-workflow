# tests/evals

Status (2026-10-02): **deterministic dry run only. Model evaluation has not been run** (owner decision Q4 open; no skill has been
tested on a real client). A green dry run means the eval *data* is well-formed; it says nothing about whether any skill triggers or helps.

## What exists

`run_trigger_evals.py` loads every `agent-content/skills/*/evals/triggers.jsonl` and validates:

- schema: one JSON object per line `{"prompt", "should_trigger", "route_instead"}`;
- counts: >= 8 should-trigger (incl. Hebrew) and >= 4 should-not-trigger (incl. Hebrew);
- Hebrew integrity (real Hebrew, no `???`, no mojibake), duplicate prompts, `route_instead` naming a real sibling skill.

It prints a per-skill table and the line `model_eval: not_run`. Run it with `python tests/evals/run_trigger_evals.py --dry-run [--json]`;
`scripts/run_all_checks.py` runs it as a gate.

## The model lane (stub, refuses by default)

`--model-lane` is an interface for a future, owner-authorised lane (E05, research SKILL_EVAL_HARNESS.md). Today it:

1. REFUSES (exit 2) unless `--approved-by-owner` and `--approval-ref REF` are both present;
2. REFUSES when `cases x hosts x attempts` exceeds `--budget` (default and cap **60**, no hidden grader/optimizer/retry calls);
3. when authorised, still runs nothing: no runner exists, it exits 3 (`not_run`) and spends nothing.

A real implementation must: decrement a durable counter *before* each spawn and count every retry/judge as an invocation; use an isolated
workspace per arm with identical fixtures; keep credentials out of fixtures and transcripts; separate discovery outcomes (observed-target-load,
wrong-owner, completed-without-load, unknown-observability, invalid-auth/timeout/process/parser); treat an error as an invalid result, never a negative
pass; compute recall/precision/false-trigger rate over valid observable runs with null for zero denominators.

The CI counterpart is `.github/workflows/eval-model.yml`: manual dispatch only, off unless the repository variable `MODEL_EVAL_ENABLED` is `true`,
and it holds no secrets.

## Task evals

Each skill's `evals/tasks.md` (>= 3 tasks with setup, oracle artifact, pass criteria) is a specification for the later model lane and for human review;
nothing executes it automatically.

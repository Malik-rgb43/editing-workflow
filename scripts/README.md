# scripts/ - deterministic gates and release machinery

Python 3.12, standard library only. Every script has a `Usage:` docstring, answers `--help` instantly, exits non-zero on failure
and is fail-closed: a gate that cannot run reports `NOT_RUN`, never `PASS`. Nothing here calls a model, uses the network, spends
money or uploads anything (decision default Q4: no model evaluation without the owner's approval; money rule: free and local only).

Status of this directory (2026-10-02): the scripts and their unit tests (`tests/unit/test_scripts_*.py`) were run on the owner's
one reference machine only. macOS and Linux are covered by the CI lane in `.github/workflows/ci.yml`, which has **not run yet**.

## Quick start

    python scripts/run_all_checks.py                 # every deterministic gate, one table
    python scripts/run_all_checks.py --final         # release strictness (see below)
    python scripts/<script>.py --help

Exit codes (all check scripts): `0` pass/warn, `1` fail or error, `2` usage error, `3` `NOT_RUN` under `--strict`.
Statuses: `PASS`, `WARN` (advisory), `FAIL`, `NOT_RUN` (could not run), `ERROR` (crashed, counts as FAIL).
All checks accept `--root DIR` and `--json`. Output is UTF-8; matched private/secret values are never printed.

## The scripts

| script | what it gates |
|---|---|
| `check_skills.py` | every `agent-content/skills/*/SKILL.md`: portable frontmatter keys, `name == folder`, kebab-case, description <= 1024 chars (warn > 500, warn on workflow-summary wording, Hebrew triggers and NOT-for expected), body <= 300 lines (warn > 180), reference links resolve, every reference has a `load when` line, `evals/triggers.jsonl` (>= 8 positive incl. Hebrew, >= 4 negative incl. Hebrew), `evals/tasks.md` (>= 3 tasks), `metadata.version` quoted semver, no private paths/secrets |
| `scan_secrets.py` | key/token/private-key patterns and secret-bearing file names; allowlist `scripts/secrets_allowlist.txt` |
| `scan_private.py` | private paths (Windows/macOS/Linux user homes, the owner's course folder), the private research-material folder, personal e-mail addresses, plus a client-name denylist from the LOCAL, git-ignored `scripts/private_denylist.txt` (example: `private_denylist.example.txt`). Without a denylist that part is `NOT_RUN` (never silently PASS); `--require-denylist` makes it a FAIL (release builds) |
| `gen_bom.py` | file-level bill of materials (`docs/BOM.json`, `docs/BOM.md`) from the actual tree and `licenses.toml`; fails on blocked components (Mixkit/Eleven/Artlist/Suno, Adobe/Apple fonts, FFmpeg binaries, ivrit.ai ONNX, Depth Anything Base/Large/Giant, Hunyuan 3D 2.1, RVM, Ultralytics, ...) and on any file without a declared licence; optional register reconciliation; `--update-notices` refreshes the generated block of `THIRD_PARTY_NOTICES.md` |
| `build_agent_adapters.py` | generates `.claude/skills/<name>/` and `.agents/skills/<name>/` as byte-identical copies of `agent-content/skills/<name>/` (+ a never-hand-edit marker and a Codex `agents/openai.yaml` stub with implicit invocation disabled); `--check` is the package-parity gate |
| `gen_system_md.py` | `SYSTEM.md` catalogue from skills/playbooks/techniques/benchmarks/references frontmatter and tool docstrings |
| `gen_tools_md.py` | `docs/TOOLS.md` from `tools/*.py` `Usage:` docstrings (parsed with `ast`, never executed) |
| `check_links.py` | relative markdown links and `agent-content/...` path mentions resolve (docs/en, docs/he, skills, techniques, ...) |
| `check_step_ids.py` | `docs/en` and `docs/he` carry identical step ids in the same order (convention below) |
| `check_workflows.py` | GitHub Actions policy: actions pinned to commit SHAs, least-privilege permissions, no `pull_request_target`, no secrets on untrusted triggers, paid/model lane only via approval-gated `workflow_dispatch` |
| `release.py` | `build` (dry-run by default; deterministic ZIP + manifest hashes + `.sha256`), `plan` (update/rollback printer), `verify`, `diff`, `local-changes`. Never uploads, tags or pushes |
| `run_all_checks.py` | runs all of the above (+ `tests/evals/run_trigger_evals.py --dry-run`, optional pytest) and prints a table; always lists `model_eval: not_run` |
| `_avc_common.py`, `_avc_fixtures.py` | shared helpers and the synthetic-repository builders used by the unit tests |

Pragmas and exclusions: a line containing `scan-ignore` is skipped by the two scans. The scanners' own sources and
`tests/unit/test_scripts_*.py` are excluded from them (they must contain pattern text); the tests build fake credentials at run time.

## Step-id convention (docs/en and docs/he)

Every page that contains numbered steps marks each step with a stable id that is identical in both languages:

    <!-- step: install-01 -->
    Run the installer.

or on a heading: `## Install Python {#install-01}`. Ids are lowercase kebab-case, recommended shape `<topic>-NN`, unique within a file.
A page `docs/en/<path>.md` must have `docs/he/<path>.md` (same relative name) listing the same ids in the same order; only the prose
differs. Markers inside fenced code blocks are examples and ignored. `python scripts/check_step_ids.py` enforces it.

## Skill eval files (checked by check_skills.py and tests/evals/run_trigger_evals.py)

- `evals/triggers.jsonl`: one JSON object per line `{"prompt": "...", "should_trigger": true|false, "route_instead": "<sibling skill>"|null}`;
  real Hebrew (UTF-8, no BOM), no `???`, no mojibake.
- `evals/tasks.md`: at least three level-2/3 headings that start with `Task`, `T1`, `Eval`, `Case`, `Scenario` or `משימה`; each section names its
  setup, its oracle artifact and its pass criteria.
- In `SKILL.md`, every file under `references/` is listed on a line that says `load when: ...`.

## Release gate ("final")

`python scripts/run_all_checks.py --final` and `python scripts/release.py build --version X.Y.Z --final` additionally require: the local
client-name denylist (`scan_private --require-denylist`), real commit-SHA pins in every workflow (placeholders fail), a fresh `docs/BOM.json`
(`gen_bom --check`), green unit tests, a `## [X.Y.Z]` entry in `CHANGELOG.md`, and that the version was not released before (releases are immutable).
Dry runs (the default) build `*.dryrun.zip` with `releasable=false`. Distribution, signing and upload are owner actions outside these scripts.

# ADR 0002 — Universal by default: every computer, every student, no personal choices

- Status: accepted (owner directive, 2026-10-02: "it must fit every computer and every student, without my specific choices")
- Supersedes nothing; tightens ADR 0001 (Q5, Q7, Q8, Q13).

## Decision
1. **Hardware is detected, never chosen by the student.** The installer and `doctor` detect OS, CPU architecture, GPU vendor, RAM, disk and shell, probe the real capability (a real mini-encode, a real tiny ASR/matte run — an advertised device alone never counts) and select the safest working profile. `core-cpu` is the baseline that works everywhere with no GPU, no key and no account; Superseded 2026-10-03: GPU routes (Vulkan, CUDA, Apple MLX/CoreML, DirectML) were removed; the toolkit offers ONE transcription route (CPU) that works on every machine.
2. **No author-specific default.** The the reference machine (one reference machine) is the only *measured* machine; its numbers are evidence, never settings.
3. **Taste is a project setting, not a toolkit law.** Rules that came from the author's taste (caption font, palette bans, beat cadence, safe-zone numbers, loudness target, Seedance prefix wording, "21st-first") ship as *house preset v1* (decision default Q5). A student's brief / `DESIGN.md` / `toolkit.toml` overrides any preset; gates that protect correctness (fail-closed QA, paid-action approval, `PROMPT.md` before code, no root RTL, fonts from files, one heavy job at a time) are not overridable by taste.
4. **Terminology.** In skills and references "the author" means *the toolkit author* and `[RULE-owner]` marks a rule that comes from the author's practice; neither is an instruction to the student's own preferences. See `agent-content/references/glossary.md`.
5. **Optional integrations are opt-in later** (`python install/bootstrap.py add <integration-id>`); the first install asks one confirmation of the detected plan and nothing else about hardware or providers.

## Consequences
- `doctor` gains a `recommend` mode (profile recommendation from detection + probes) used by `install/bootstrap.py plan`.
- Any default found that depends on one person's hardware or taste is a defect to fix, not a feature.

## Known limits
Only Windows/AMD was ever measured; macOS, Linux, NVIDIA and Apple Silicon behaviour is unmeasured and must be exercised on clean machines before a launch claim (roadmap Phase 5 gate).

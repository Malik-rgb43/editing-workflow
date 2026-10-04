# Parallel work, the heavy-job queue and agent supervision

Load when: launching agents for derivatives, queueing renders, or a run feels stuck. Sources: distilled 02 workflow §13.4-§13.7, blueprint TOOLS_SPEC (`render_lock`, `render_watch`), WORKFLOWS §3 and §6 (2026-10-01). Times are the reference machine observations, not guarantees.

## 1. Principle
**Build in parallel, run heavy work in one queue.** Spec, layout, patching, reading QA reports and writing notes can overlap. Render, `hyperframes check`, snapshots, Blender, ASR, matte and analysis are heavy: one at a time for the whole machine, across all projects and sessions. Evidence for the rule: a parallel Blender job made a render take 21.5 min instead of 11.5 min (the reference machine, 2026-09).

## 2. The lock and the queue
- `render_lock status` shows the holder across sessions; `render_lock run -- <cmd>` wraps any heavy command that does not take the lock itself. `hf_deliver` and `hf_segment` take it themselves. A holder whose process died is stale; a live holder is waited for and **never killed**. (The student `render_lock` is specified as a kernel-lock design; the author's file-based version had a read-before-write race and a conflicting stale threshold: 60 min in the docs vs 3 h in the code. Plan jobs over 60 min in segments; check `--help` of the shipped tool.)
- The lock waits but keeps no order: inside a session, chain the renders in ONE background command in the planned order (master -> 9:16 -> 1:1 -> variants) and write the order in `_work/STATE.md` with one `STATE` line per job.
- No heavy agent during a render: Blender, local video models, matte, ASR and analysis queues finish before or wait for the lock.
- Another session holds the lock: wait, tell the user once ("waiting for the render of project X, about N min"), do not stop it.
- **Long-job protocol (any job > 3 min):** benchmark one unit; post a one-line ETA; `timeout` on every command (render = 3 x ETA, `check` 900 s); run in the background with a log; heartbeat about every 5 min; watchdog: 0 frames after 3 min or no progress for 10 min = kill YOUR OWN process tree, check the lock, retry once; report partial results at once. The user should never have to ask "what about the render?".

## 3. Agent caps and the brief
At most **4 agents in parallel**, each with at most **2 sub-agents** (many agents caused usage-limit stops of hours). Every agent gets, in its first message:

| Field | Content |
|---|---|
| Files | the exact list it may read and the ONE folder it may write (`hf_9x16/`) |
| Output file | `_work/qa/<aspect>/report.md` (details go there; the reply is at most 10 lines) |
| Deadline | an absolute clock time, not "soon" |
| Progress file | `_work/agents/<agent>.progress.md`, updated while working, so a resume after a limit stop is cheap |
| Allowed heavy work | none by default; a full render goes through `hf_deliver`, which waits for the lock |
| Report duty | any bug found in the master is reported to the main session, never fixed only in the copy |
| Prohibitions | no messages to other Claude sessions; no paid action; no change to the frozen master; no new files outside its folder |

Brief template:
```
You own ONE re-layout: hf_9x16/ (copy of hf/ at master hash <12 hex>).
Read: hf/PROMPT.md, hf/DESIGN.md, hf_9x16/**. Write: hf_9x16/** and _work/qa/9x16/report.md only.
Do: layout table, preflight 0 errors, snapshots at <hook>,<offer>,<endcard> with --describe false (<= 5 per call).
Do NOT: edit hf/ (master), touch cues.js or assets/mix.wav, start a render yourself (ask the main session).
Deadline: <HH:MM local>. Progress: _work/agents/relayout-9x16.progress.md. Reply <= 10 lines.
```

## 4. Supervision
| What | Rule |
|---|---|
| Heartbeat | the main session checks each progress file's last write about every 15 min |
| Silent | no write for 20 min or past the deadline: check, replace or stop (a library agent once sat silent for 3 h) |
| Stopping | stop the agent's process TREE (including its ffmpeg and headless browser), then run `render_lock status`: an agent stop once left its render running |
| Status line | to the user about every 10 min of silence: what runs, what finished, what is next |
| Master bug | fix in the master, `manifest_check.py change`, carry to every copy, re-render all (the 1:1 once shipped without the master's 3.7 s fix) |
| Several sessions | never message, stop or touch another session or its processes; report to the user; sub-agents are allowed; one designated session owns shared rule files, others append to the lessons inbox with a grep-first dedupe |

## 5. Token budget (what to read, what to skip)
- Automatic checks first (seconds, no tokens): `hf_preflight`, `frame_qa`, `caption_qa`, `face_center audit`, `hf_mix --report`, delivery verify.
- Reviewers: first round of the master 2-4 agents on all contact sheets (tiles 180-270 px); from round two only flagged or changed ranges; derivatives axes 1 and 4 only. Four reviewers x every frame x four rounds exhausted the quota twice.
- Keep the same critic between rounds (continue it with the fix list only); read long files with line ranges, not twice; do not load a skill that is already loaded.

## 6. Folder layout (project-relative)
| What | Where |
|---|---|
| master | `hf/` |
| ratio derivative | `hf_9x16/`, `hf_1x1/`, `hf_4x5/` |
| QA per aspect and round | `_work/qa/<aspect>/<round>/` |
| agent progress | `_work/agents/<agent>.progress.md` |
| state and queue | `_work/STATE.md` |
| stamps | `_work/stamps/<hf>.json` |
| finals + manifest | `final/` |

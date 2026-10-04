# Long-job protocol, the lock, agent supervision

Load when: you are about to start any command expected to take over 3 minutes (render, `check`, matte, ASR, Blender, bake), or a job looks stuck. Dated 2026-10-02; sources: distilled 01 rules-and-gates E, L; distilled 03 tool-traps §2; blueprint TOOLS_SPEC (`render_lock`, `render_watch`).

## 1. The protocol
1. **Benchmark one unit** (one frame, one second, one clip) before the full job.
2. **ETA in one chat line**, in the user's language: "full render ~11 min (1,520 frames, 2.3 fps), done ~14:32". If the ETA for one shot exceeds 30 minutes, offer an alternative before starting (for AI-video shots: a shorter shot or a hosted quote; for the matte: range-only).
3. **`timeout` on every command**: render = 3 x ETA, `check` 900 s, snapshot packs 120 s. `--browser-timeout` is in SECONDS, `--protocol-timeout` and `--player-ready-timeout` are in MILLISECONDS.
4. **Background with a log and a state line**: `_work/<job>.log` and `_work/STATE.md` ("what is running, next step"), so "continue" after a stop is one step.
5. **Heartbeat about every 5 minutes** (a status line every 5-10 minutes while the user is around): "render 62 % (940/1,520), ~4 min left".
6. **Watchdog:** 0 frames after 3 minutes, or no progress for 10 minutes -> kill only YOUR OWN process tree (`taskkill /T /F /PID <pid>` on Windows), check `render_lock status`, diagnose with ONE snapshot, retry ONCE, then report. Leftover `chrome-headless-shell` processes after a stop hold the GPU and hang the next `check` (a 45-minute loss): clean up only the ones you started.
7. **Partial results at once**: send each draft/segment the moment it exists.
8. **A user who has to ask "what about the render?" = a protocol failure**: log it (the author asked twice in two projects).
`render_watch` (specified tool) wraps any heavy command: parse `frame N/M`, ETA after 60 frames, a heartbeat to `_work/render.status.json` every 60 s, kill only the owned process tree after 10 minutes without progress, clean orphan headless browsers of that run.

## 2. The lock
- ONE heavy job per machine across all projects and sessions: render, `check`, snapshot packs, Blender, ASR, matte, analyses. Run non-delivery commands as `render_lock run -- <cmd>`; `hf_deliver` and `hf_segment` take it themselves; the Blender MCP does NOT take it (run Blender BEFORE the render).
- Measured cost of breaking it: render beside Blender 11.5 -> 21.5 min; a render beside a VO/ASR agent stuck about 1 h unnoticed; 10 -> 18-21 min when two sessions collided.
- Within a session chain renders in one background command in the planned order (master -> 9:16 -> 1:1) and write the order in `STATE.md`; the lock waits (polling every 10 s) but does not keep order.
- Defects in the author's original (fix in the port): acquisition is check-then-write (not atomic: a race and "an old timestamp steals a live lock" were reproduced); the lock path is relative to each checkout (use ONE absolute shared path); PID liveness used `tasklist` (Windows only; an exception counted as alive); the stale threshold is 3 h in code but "> 60 min" in the docs; an inherited child job can outlive the holder. The specified replacement is a kernel-level lock (POSIX branch written but unexecuted in the prototype). Rule until then: never take over automatically while lifetime is uncertain; ask the user.

## 3. Agent supervision (when delegating)
Every sub-agent brief: an explicit file list, an output file, a clock deadline, "return <= 10 lines, details in the file"; a progress file `_work/agents/<name>.progress.md` written as it goes (resume after a usage-limit stop is cheap). Check last-write times about every 15 minutes; past the deadline or silent for 20 minutes -> check, replace or stop. Ceiling: 4 parallel agents, each with <= 2 sub-agents (more caused usage-limit stops of hours: about 6 h of pauses in one test). Stopping an agent = kill its PROCESS TREE, then `render_lock status`. Never message other Claude sessions.

## 4. Why these numbers exist (evidence)
23 full renders served 7 note rounds where about 9 were needed; ~14 avoidable renders cost about 2.3 h in one 40 s premium test (a render took 4-21 min, median ~10). A 42-minute source blocked a queue for 5 h. A QA run on a stale file said "clean" for a render that had failed (about 8 min lost), and a render started after a failed `check` cost about 6 min. These are owner-project logs on one machine, not benchmarks.

## Sources
distilled 01 rules-and-gates E (long-job protocol), L1-L3; distilled 03 tool-traps T-29..T-42; blueprint TOOLS_SPEC §2-§3; checked 2026-10-02.

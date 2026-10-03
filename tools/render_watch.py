"""render_watch - wrap ANY heavy command with progress parsing, an ETA, a heartbeat file and a stall watchdog.

"The user must never have to ask 'what about the render?'": run the command (render, `hyperframes check`, ASR, matte) through this wrapper
and a status file is updated every ``--heartbeat`` seconds with the parsed progress ("frame N/M" or "NN%"), the elapsed time, an ETA
(shown after ``--eta-after`` frames or a few percent) and the state. If NO progress change is seen for ``--stall`` seconds the wrapper kills
ONLY the process tree it started (never another run's browsers), writes state ``stalled`` and exits 124. The child's own exit code is
passed through otherwise. The command runs under the heavy-job lock unless ``--no-lock`` (one heavy job at a time).

Status file (JSON, atomic): {state, pid, started_utc, elapsed_s, progress:{frame,total,percent}, eta_s, last_output, last_change_age_s}.

Usage:
    python tools/render_watch.py [--status _work/render.status.json] [--heartbeat 60] [--stall 600] [--timeout 5400] [--eta-after 60]
                                 [--job "render v3"] [--lock-wait 0] [--no-lock] -- <command> [args...]
Exit: child's exit code; 124 stalled/timeout; 75 lock busy; 2 could not start.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import threading
import time
from pathlib import Path

import _common  # noqa: F401

FRAME_RE = re.compile(r"(?:frame|Frame)\s*[:=]?\s*(\d+)\s*(?:/|of)\s*(\d+)")
PCT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")


def parse_progress(line: str):
    """Pure: -> {frame,total,percent} or None."""
    m = FRAME_RE.search(line)
    if m:
        fr, tot = int(m.group(1)), int(m.group(2))
        if tot > 0 and fr <= tot:
            return {"frame": fr, "total": tot, "percent": round(100.0 * fr / tot, 2)}
    m = PCT_RE.search(line)
    if m:
        p = float(m.group(1))
        if 0 <= p <= 100:
            return {"frame": None, "total": None, "percent": p}
    return None


def eta_seconds(progress, elapsed, eta_after):
    if not progress:
        return None
    if progress["frame"] is not None and progress["total"]:
        if progress["frame"] < eta_after:
            return None
        rate = progress["frame"] / max(elapsed, 1e-6)
        return round((progress["total"] - progress["frame"]) / rate, 1) if rate > 0 else None
    p = progress["percent"]
    if p < 3:
        return None
    return round(elapsed * (100 - p) / p, 1)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        if any(x in argv for x in ("-h", "--help")):
            argv = argv + ["--", "x"]
        else:
            print("render_watch: put the command after `--`", file=sys.stderr)
            return 2
    i = argv.index("--")
    opts, cmd = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(prog="render_watch", description=__doc__.split("\n\n")[0])
    ap.add_argument("--status", default="render.status.json")
    ap.add_argument("--heartbeat", type=float, default=60.0)
    ap.add_argument("--stall", type=float, default=600.0)
    ap.add_argument("--timeout", type=float, default=None)
    ap.add_argument("--eta-after", type=int, default=60)
    ap.add_argument("--job", default="watched job")
    ap.add_argument("--lock-wait", type=float, default=0.0)
    ap.add_argument("--no-lock", action="store_true")
    a = ap.parse_args(opts)
    if not cmd:
        print("render_watch: no command", file=sys.stderr)
        return 2

    from core.config import load_config
    from core.errors import LockBusy, ToolkitError
    from core.fsio import write_json_atomic
    from core.lock import acquire
    from core.procs import spawn

    status_path = Path(a.status)
    started = dt.datetime.now(dt.timezone.utc)
    state = {"state": "starting", "pid": None, "progress": None, "last_output": "", "t_change": time.monotonic()}
    lock_cm = None
    try:
        if not a.no_lock:
            lock_cm = acquire(load_config().lock_path, job=a.job, timeout=a.lock_wait)
        try:
            proc = spawn(cmd, stdin=__import__("subprocess").DEVNULL)
        except (ToolkitError, OSError) as exc:
            print(f"render_watch: could not start: {exc}", file=sys.stderr)
            return 2
        t0 = time.monotonic()
        state["pid"] = proc.pid
        state["state"] = "running"

        def write(final=None):
            el = time.monotonic() - t0
            write_json_atomic(status_path, {"state": final or state["state"], "job": a.job, "pid": state["pid"], "started_utc": started.isoformat(timespec="seconds"), "elapsed_s": round(el, 1), "progress": state["progress"],
                                            "eta_s": eta_seconds(state["progress"], el, a.eta_after), "last_output": state["last_output"][-200:], "last_change_age_s": round(time.monotonic() - state["t_change"], 1)})

        def reader(stream):
            for raw in iter(stream.readline, b""):
                line = raw.decode("utf-8", "replace").rstrip()
                if not line:
                    continue
                state["last_output"] = line
                pr = parse_progress(line)
                if pr and pr != state["progress"]:
                    state["progress"] = pr
                    state["t_change"] = time.monotonic()
                elif not pr:
                    pass
                sys.stdout.write(line + "\n")
                sys.stdout.flush()

        threads = [threading.Thread(target=reader, args=(s,), daemon=True) for s in (proc.popen.stdout, proc.popen.stderr) if s is not None]
        for t in threads:
            t.start()
        write()
        last_beat = time.monotonic()
        rc = None
        verdict = None
        while rc is None:
            time.sleep(0.2)
            rc = proc.poll()
            now = time.monotonic()
            if now - last_beat >= a.heartbeat:
                write()
                last_beat = now
            if rc is None and now - state["t_change"] > a.stall:
                verdict = "stalled"
            if rc is None and a.timeout and now - t0 > a.timeout:
                verdict = "timeout"
            if verdict:
                proc.terminate_tree()
                rc = 124
                break
        for t in threads:
            t.join(timeout=2)
        proc.close()
        write(final=verdict or ("finished" if rc == 0 else "failed"))
        if verdict:
            print(f"render_watch: {verdict}: killed the process tree started by this wrapper (no progress for {a.stall:g}s or over --timeout)", file=sys.stderr)
        return rc
    except LockBusy as exc:
        print(f"render_watch: {exc}", file=sys.stderr)
        return 75
    finally:
        if lock_cm is not None:
            lock_cm.release()


if __name__ == "__main__":
    sys.exit(main())

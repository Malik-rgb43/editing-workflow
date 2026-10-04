"""hf_studio - open a HyperFrames project in Studio (video + timeline) so the user sees what the agent is working on.

Owner rule (2026-10-04): every time work starts or resumes on a HyperFrames project, the Studio is opened first and its link is shown to
the user, so they can watch the video and the timeline while the agent works. This tool starts the PINNED engine's
``hyperframes preview <hf> --background --no-open --json`` (the preview keeps running after the command returns), and prints the Studio URL.
The agent opens that URL for the user (its browser pane, or it gives the link); ``--open`` opens the system browser instead.

Usage:
    python tools/hf_studio.py <hf-dir> [--port 3002] [--open] [--json]      start (or reuse) the Studio for this project; prints studio_url
    python tools/hf_studio.py <hf-dir> --status [--json]                      is a Studio running for this project?
    python tools/hf_studio.py <hf-dir> --stop                                  stop it (end of the session or before moving the project)
    python tools/hf_studio.py <hf-dir> --attach                                keep the server attached (run it as the host's BACKGROUND command)

Measured 2026-10-04 (reference machine, agent shell): some agent hosts kill every child of a shell command when it returns, so the
engine's ``--background`` server can die seconds later. This tool therefore probes ``server_url`` after the start; if nothing answers it
exits 3 and says to use ``--attach`` as a background command instead. Every project's folder is called ``hf``, so every Studio URL is
``#project/hf``: a browser tab left open on an earlier project keeps showing it. The printed ``studio_url`` carries ``?p=<project>`` so a
fresh tab opens the right one (open it in a NEW tab).
Exit: 0 ok, 2 refused (no index.html, engine missing, non-ASCII engine path), 3 the engine failed to start the preview.
Not a heavy job (no render): it does not take the render lock. Nothing is downloaded; telemetry and skill fetching are off (hf_engine).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _common  # noqa: F401


def parse_engine_json(text: str) -> dict | None:
    """Pure: the last JSON object line the engine printed (it may print a lint summary first)."""
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return None


def project_tag(hf: Path) -> str:
    """Pure: a short ASCII tag naming the project (its folder above hf/), for the cache-busting query."""
    name = hf.parent.name if hf.name == "hf" else hf.name
    return "".join(c for c in name if c.isascii() and (c.isalnum() or c in "-_"))[:40] or "hf"


def with_project_tag(url: str, hf: Path) -> str:
    """Pure: http://h:p/#project/hf -> http://h:p/?p=<tag>#project/hf (every project is called hf; the tag defeats a stale tab)."""
    base, sep, frag = url.partition("#")
    if "?p=" in base:
        return url
    return f"{base.rstrip('/')}/?p={project_tag(hf)}{sep}{frag}"


def alive(server_url: str, tries: int = 6, wait_s: float = 1.0) -> bool:
    """Is the Studio server answering? Polls a few times (the server needs a moment after the engine returns)."""
    import time
    import urllib.request
    for i in range(tries):
        time.sleep(wait_s)
        try:
            with urllib.request.urlopen(server_url.rstrip("/") + "/api/projects", timeout=3) as r:
                if r.status == 200:
                    return True
        except OSError:
            continue
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hf_studio", description=__doc__.split("\n\n")[0])
    ap.add_argument("hf")
    ap.add_argument("--port", type=int)
    ap.add_argument("--open", action="store_true", help="open the system browser too")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--attach", action="store_true", help="stay attached (foreground); run as a background command of the agent host")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    from core import hf_engine
    from core.procs import run

    hf = Path(a.hf).resolve()
    if not (hf / "index.html").is_file():
        print(f"hf_studio: {hf / 'index.html'} not found (create the project with tools/new_project.py --init-hyperframes)", file=sys.stderr)
        return 2
    eng = hf_engine.find()
    if eng is None:
        print("hf_studio: HyperFrames engine not found (run `python install/bootstrap.py apply`)", file=sys.stderr)
        return 2
    prob = hf_engine.non_ascii_problem(eng)
    if prob:
        print(f"hf_studio: {prob}", file=sys.stderr)
        return 2
    if a.attach:
        args = ["preview", str(hf), "--foreground", "--open" if a.open else "--no-open"] + ([f"--port={a.port}"] if a.port else [])
        print(f"Studio (attached): http://127.0.0.1:{a.port or 3002}/?p={project_tag(hf)}#project/hf  - stop by ending this command", flush=True)
        return run(list(eng.argv) + args, cwd=hf, env=hf_engine.run_env(), timeout=None).returncode or 0
    args = ["preview", str(hf), "--json"]
    if a.stop:
        args.append("--stop")
    elif a.status:
        args.append("--status")
    else:
        args += ["--background", "--open" if a.open else "--no-open"]
        if a.port:
            args += [f"--port={a.port}"]
    r = run(list(eng.argv) + args, cwd=hf, env=hf_engine.run_env(), timeout=180)
    data = parse_engine_json(r.stdout or "")
    if r.timed_out or data is None or not data.get("ok", False):
        tail = ((r.stderr or "") + (r.stdout or "")).strip()[-400:]
        print(f"hf_studio: the engine did not report success (exit {r.returncode}): {tail}", file=sys.stderr)
        return 3
    res = data.get("result") or {}
    if res.get("studioUrl"):
        res["studioUrl"] = with_project_tag(res["studioUrl"], hf)
    if not a.stop and not a.status and res.get("serverUrl") and not alive(res["serverUrl"]):
        print(f"hf_studio: the preview started but {res['serverUrl']} does not answer (the host likely killed the background server). "
              f"Run `python tools/hf_studio.py {a.hf} --attach` as a background command instead.", file=sys.stderr)
        return 3
    out = {"state": res.get("state"), "studio_url": res.get("studioUrl"), "server_url": res.get("serverUrl"), "port": res.get("port"),
           "project": str(hf), "log": res.get("logPath"),
           "next": "open studio_url for the user (browser pane or the link); stop it with --stop when the session ends" if res.get("studioUrl") else None}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif a.stop:
        print(f"hf_studio: stopped ({res.get('state')})")
    else:
        print(f"Studio: {out['studio_url'] or 'not running'}  ({out['state']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

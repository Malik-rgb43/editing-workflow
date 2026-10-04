"""prep - minute-0 preparation of a project: every slow measurement runs in the background while the brief is still being written.

Start it as a BACKGROUND command right after `new_project` (the intake questions do not need its results; the concept and the build do).
It runs the existing tools one after another, each under the heavy-job lock (one heavy job at a time). Build inputs go where the type
skills read them (``hf/data/``, pro-video-editor stage 1), looks go to ``_work/prep/``, references to ``_work/analysis/<ref-id>/``:

    sheet    contact sheet of the main source (24 tiles)                    -> _work/prep/sheet.jpg        (tools/sheet.py)
    asr      word-timed transcript of the main source                       -> hf/data/words.json          (tools/transcribe.py)
    cuts     hidden cuts inside the source (each needs a cover)             -> hf/data/src_cuts.json       (tools/source_cuts.py)
    faces    face centre per sample (colour regions, zooms, reframing)      -> hf/data/faces.json          (tools/face_center.py)
    scopes   colour measurements, skin taken from faces.json when it exists -> _work/prep/scopes.json      (tools/color_scopes.py)
    refs     analysis of every video in hf/references/                      -> _work/analysis/<ref-id>/    (tools/analyze.py --asr never)

Nothing is downloaded: the transcript needs an installed ASR model (``--model-dir`` or the installed default) and faces need a YuNet
file (``--face-model`` or AVC_FACE_MODEL). A step that cannot run is recorded as ``not_run`` with the tool's own reason, never as done.
A step whose inputs and command did not change since its last successful run is skipped (``cached``); ``--force`` reruns it.
Run ``--plan`` first to show the user what will run, where it writes and that nothing is downloaded.

Usage:
    python tools/prep.py <project-root> [--main FILE] [--steps sheet,asr,cuts,faces,scopes,refs] [--language he] [--model-dir DIR]
                         [--face-model yunet.onnx] [--lock-wait 900] [--step-timeout 1800] [--force] [--plan] [--json]
Exit: 0 every selected step done, cached or skipped (refs without references), 1 some step not_run / failed (prep.json says why), 2 refused (no project, no or several main sources).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import _common  # noqa: F401

STEPS = ("sheet", "asr", "cuts", "faces", "scopes", "refs")
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".mxf"}
HINTS = {
    "asr": "the transcript needs the ASR model: `python tools/transcribe.py --check` shows what is missing (the installer's local route installs it)",
    "faces": "faces need a YuNet ONNX file (233 KB, MIT; source in docs/en/local-vs-paid.md): pass --face-model <file> or set AVC_FACE_MODEL",
}


def folders(root: Path) -> dict:
    names = {"source": "source", "hf": "hf", "work": "_work"}
    try:
        meta = json.loads((root / "project.json").read_text(encoding="utf-8"))
        names.update({k: v for k, v in (meta.get("folders") or {}).items() if k in names and isinstance(v, str)})
    except (OSError, ValueError):
        pass
    return names


def videos_in(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT) if folder.is_dir() else []


def stamp(paths) -> list:
    """Cheap change key: name, size and mtime of every input (hashing a long source would cost more than some steps)."""
    out = []
    for p in paths:
        try:
            st = Path(p).stat()
            out.append([str(p), st.st_size, st.st_mtime_ns])
        except OSError:
            out.append([str(p), None, None])
    return out


def plan(root: Path, main: Path, refs: list[Path], a, faces_done: bool) -> list[dict]:
    """Pure: the jobs to run, in order, as {step, id, cmd, inputs, outputs}."""
    from core.paths import slugify

    py, tools = sys.executable, Path(__file__).resolve().parent
    n = folders(root)
    prep, data = root / n["work"] / "prep", root / n["hf"] / "data"
    jobs = []
    for step in a.steps:
        if step == "sheet":
            jobs.append({"step": step, "id": step, "cmd": [py, str(tools / "sheet.py"), str(main), "-o", str(prep / "sheet.jpg"), "--count", "24"],
                         "inputs": [main], "outputs": [prep / "sheet.jpg"]})
        elif step == "asr":
            cmd = [py, str(tools / "transcribe.py"), str(main), "-o", str(data / "words.json"), "--language", a.language]
            if a.model_dir:
                cmd += ["--model-dir", a.model_dir]
            jobs.append({"step": step, "id": step, "cmd": cmd, "inputs": [main], "outputs": [data / "words.json"]})
        elif step == "cuts":
            jobs.append({"step": step, "id": step, "cmd": [py, str(tools / "source_cuts.py"), str(main), "-o", str(data / "src_cuts.json")],
                         "inputs": [main], "outputs": [data / "src_cuts.json"]})
        elif step == "faces":
            cmd = [py, str(tools / "face_center.py"), "source", str(main), "-o", str(data / "faces.json")]
            model = a.face_model or os.environ.get("AVC_FACE_MODEL")
            if model:
                cmd += ["--model", model]
            jobs.append({"step": step, "id": step, "cmd": cmd, "inputs": [main] + ([Path(model)] if model else []), "outputs": [data / "faces.json"]})
        elif step == "scopes":
            cmd = [py, str(tools / "color_scopes.py"), str(main), "-o", str(prep / "scopes.json")]
            inputs = [main]
            if faces_done:
                cmd += ["--faces", str(data / "faces.json")]
                inputs.append(data / "faces.json")
            jobs.append({"step": step, "id": step, "cmd": cmd, "inputs": inputs, "outputs": [prep / "scopes.json"]})
        elif step == "refs":
            for ref in refs:
                out = root / n["work"] / "analysis" / slugify(ref.stem)
                jobs.append({"step": step, "id": f"refs:{out.name}", "cmd": [py, str(tools / "analyze.py"), str(ref), "--out", str(out), "--detail", "standard", "--asr", "never", "--force"],
                             "inputs": [ref], "outputs": [out / "measurements.json", out / "report.md"]})
    return jobs


def reason_from(stderr: str, stdout: str) -> str:
    lines = [ln.strip() for ln in (stderr or stdout or "").splitlines() if ln.strip()]
    return lines[-1][:400] if lines else "no message"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prep", description=__doc__.split("\n\n")[0])
    ap.add_argument("project")
    ap.add_argument("--main", help="the main source video (default: the only video in source/)")
    ap.add_argument("--steps", default=",".join(STEPS))
    ap.add_argument("--language", default="he")
    ap.add_argument("--model-dir")
    ap.add_argument("--face-model")
    ap.add_argument("--lock-wait", type=float, default=900.0, help="seconds each step may wait for the heavy-job lock")
    ap.add_argument("--step-timeout", type=float, default=1800.0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--plan", action="store_true", help="print what would run and write; run nothing")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    a.steps = [s.strip() for s in a.steps.split(",") if s.strip()]
    bad = [s for s in a.steps if s not in STEPS]
    if bad:
        print(f"prep: unknown step(s) {bad}; choose from {','.join(STEPS)}", file=sys.stderr)
        return 2

    root = Path(a.project).resolve()
    n = folders(root)
    if not (root / n["source"]).is_dir():
        print(f"prep: {root} is not a project (no {n['source']}/ folder); create it with tools/new_project.py", file=sys.stderr)
        return 2
    if a.main:
        main_src = Path(a.main).resolve()
        if not main_src.is_file():
            print(f"prep: --main {a.main} not found", file=sys.stderr)
            return 2
    else:
        found = videos_in(root / n["source"])
        if len(found) != 1:
            names = ", ".join(p.name for p in found) or "none"
            print(f"prep: pass --main: source/ holds {len(found)} video(s) ({names})", file=sys.stderr)
            return 2
        main_src = found[0]
    refs = videos_in(root / n["hf"] / "references")
    prep_dir = root / n["work"] / "prep"
    state_file = prep_dir / "prep.json"

    if a.plan:
        jobs = plan(root, main_src, refs, a, faces_done=True)
        out = {"project": str(root), "main": str(main_src), "references": [str(r) for r in refs], "downloads": "none",
               "jobs": [{"id": j["id"], "writes": [str(o) for o in j["outputs"]], "cmd": j["cmd"]} for j in jobs],
               "note": "each job runs under the heavy-job lock, one after another; a job that cannot run is recorded as not_run"}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    from core.config import load_config
    from core.errors import LockBusy
    from core.fsio import write_json_atomic
    from core.lock import run_under_lock

    prep_dir.mkdir(parents=True, exist_ok=True)
    (root / n["hf"] / "data").mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    steps_state = state.get("steps", {})
    lock_path = load_config().lock_path
    results = {}

    def save():
        write_json_atomic(state_file, {"schema": "avc.prep/1", "project": str(root), "main": str(main_src), "steps": {**steps_state, **results}})

    for step in a.steps:
        faces_done = (results.get("faces") or steps_state.get("faces") or {}).get("status") in ("done", "cached") and (root / n["hf"] / "data" / "faces.json").is_file()
        if step == "refs" and not refs:
            results["refs"] = {"status": "skipped", "reason": f"no videos in {n['hf']}/references/"}
            continue
        for job in [j for j in plan(root, main_src, refs, a, faces_done) if j["step"] == step]:
            # the tool's own file is part of the key: a fixed tool must not hand back a cached result of its old code (found 2026-10-04)
            key = {"cmd": job["cmd"], "inputs": stamp(job["inputs"] + [Path(job["cmd"][1])])}
            prev = steps_state.get(job["id"]) or {}
            if not a.force and prev.get("status") in ("done", "cached") and prev.get("key") == key and all(Path(o).exists() for o in job["outputs"]):
                results[job["id"]] = {**prev, "status": "cached"}
                continue
            print(f"prep: {job['id']} ...", file=sys.stderr, flush=True)
            t0 = time.monotonic()
            try:
                r = run_under_lock(job["cmd"], lock_path=lock_path, job=f"prep {job['id']}", wait_timeout=a.lock_wait, run_timeout=a.step_timeout)
            except LockBusy as exc:
                results[job["id"]] = {"status": "not_run", "reason": f"heavy-job lock busy: {exc}", "key": None}
                save()
                continue
            rec = {"seconds": round(time.monotonic() - t0, 1), "outputs": [str(o) for o in job["outputs"]], "key": key}
            if r.timed_out:
                rec.update(status="failed", reason=f"timed out after {a.step_timeout:g} s")
            elif r.returncode == 0 and all(Path(o).exists() for o in job["outputs"]):
                rec.update(status="done")
            elif r.returncode == 2:
                rec.update(status="not_run", reason=reason_from(r.stderr, r.stdout), key=None)
                if step in HINTS:
                    rec["hint"] = HINTS[step]
            else:
                rec.update(status="failed", reason=f"exit {r.returncode}: {reason_from(r.stderr, r.stdout)}", key=None)
            results[job["id"]] = rec
            save()
    save()
    summary = {jid: {k: v for k, v in r.items() if k in ("status", "seconds", "reason", "hint", "outputs")} for jid, r in results.items()}
    ok = all(r["status"] in ("done", "cached", "skipped") for r in results.values())
    report = {"status": "ok" if ok else "partial", "prep": str(state_file), "steps": summary,
              "next": "read sheet.jpg and hf/data/words.json before the concept; src_cuts.json needs a cover per used cut; scopes.json feeds speaker-color-correction; _work/analysis/* feeds reference-style-matching"}
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for jid, r in summary.items():
            extra = f" ({r['seconds']} s)" if r.get("seconds") is not None and r["status"] == "done" else ""
            why = f": {r['reason']}" if r.get("reason") else ""
            print(f"{jid:<14} {r['status']}{extra}{why}")
            if r.get("hint"):
                print(f"{'':<14} -> {r['hint']}")
        print(f"state: {state_file}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""List EVERY file under a source folder and flag a probable camera original (intake step 0).

Usage:
  python source_inventory.py SOURCE_DIR [--json] [--max-files 2000] [--write projects/<name>/_work/intake]
  python source_inventory.py --self-check

--write DIR also saves DIR/source_ls.txt (the listing below) and DIR/probe.json (the full JSON): the two
evidence files of the intake gate. They are written only when the listing succeeded (status ok/partial).

Why: a 4K camera original once sat unseen next to a 1080p, 2.2 Mbps rough cut and the first
version of a video was built on the wrong file. Quote this output in the intake note.

Reads only. For video files it calls ffprobe (if on PATH) for size, codec, fps, duration and
bitrate. Camera-original candidates are a HEURISTIC: file A is flagged over file B when A has
>= 1.5x the pixels or >= 3x the bitrate of B and A is at least 90 % as long. The agent must
ask the user to confirm; a missing ffprobe gives `camera_original: unknown`, never "none".

Exit codes: 0 listing produced (status ok or partial), 2 blocked (not a folder, unreadable, empty).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VIDEO = {".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi", ".mxf", ".mts", ".m2ts", ".mpg"}
AUDIO = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".aif", ".aiff"}
IMAGE = {".png", ".jpg", ".jpeg", ".webp", ".psd", ".tif", ".tiff", ".svg", ".gif", ".heic"}
PROJECT = {".ffx", ".aex", ".aep", ".prproj", ".drp", ".fcpxml", ".psb"}
MODEL3D = {".blend", ".glb", ".gltf", ".fbx", ".obj", ".usdz", ".c4d"}
FONT = {".ttf", ".otf", ".woff", ".woff2"}
SKIP_DIRS = {".git", "node_modules", "__pycache__"}


def classify(ext: str) -> str:
    for name, group in (("video", VIDEO), ("audio", AUDIO), ("image", IMAGE), ("project_file", PROJECT),
                        ("model_3d", MODEL3D), ("font", FONT)):
        if ext in group:
            return name
    return "other"


def probe(path: Path, timeout: int = 30) -> dict | None:
    if not shutil.which("ffprobe"):
        return None
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "stream=codec_name,width,height,r_frame_rate:format=duration,bit_rate", "-of", "json", str(path)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True).stdout
        data = json.loads(out)
        st = (data.get("streams") or [{}])[0]
        fmt = data.get("format", {})
        num, _, den = str(st.get("r_frame_rate", "0/1")).partition("/")
        fps = round(float(num) / float(den or 1), 3) if float(den or 1) else 0.0
        return {"codec": st.get("codec_name"), "width": st.get("width"), "height": st.get("height"), "fps": fps,
                "duration_s": round(float(fmt.get("duration", 0) or 0), 3),
                "bitrate_kbps": round(float(fmt.get("bit_rate", 0) or 0) / 1000.0, 1)}
    except (subprocess.SubprocessError, ValueError, OSError):
        return {"error": "ffprobe failed"}


def candidates(videos: list[dict]) -> list[dict]:
    ok = [v for v in videos if v.get("probe") and "width" in v["probe"] and v["probe"].get("width")]
    found = []
    for a in ok:
        pa = a["probe"]
        for b in ok:
            if a is b:
                continue
            pb = b["probe"]
            pix_a, pix_b = pa["width"] * pa["height"], pb["width"] * pb["height"]
            if pb["duration_s"] and pa["duration_s"] < 0.9 * pb["duration_s"]:
                continue
            if (pix_b and pix_a >= 1.5 * pix_b) or (pb["bitrate_kbps"] and pa["bitrate_kbps"] >= 3 * pb["bitrate_kbps"]):
                found.append({"probable_original": a["path"], "over": b["path"],
                              "reason": f"{pa['width']}x{pa['height']} @ {pa['bitrate_kbps']} kbps vs "
                                        f"{pb['width']}x{pb['height']} @ {pb['bitrate_kbps']} kbps"})
    return found


def inventory(root: Path, max_files: int = 2000) -> dict:
    res = {"tool": "source_inventory", "version": "0.1.0", "root": str(root)}
    if not root.is_dir():
        res.update(status="blocked", reason="not a folder or unreadable")
        return res
    files, truncated = [], False
    for dp, dns, fns in os.walk(root, followlinks=False):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        for fn in sorted(fns):
            if len(files) >= max_files:
                truncated = True
                break
            p = Path(dp) / fn
            try:
                size = p.stat().st_size
            except OSError:
                continue
            files.append({"path": str(p.relative_to(root)).replace("\\", "/"), "bytes": size,
                          "class": classify(p.suffix.lower())})
    if not files:
        res.update(status="blocked", reason="folder is empty (or only skipped folders)")
        return res
    ffprobe = bool(shutil.which("ffprobe"))
    videos = []
    for f in files:
        if f["class"] == "video":
            f["probe"] = probe(root / f["path"]) if ffprobe else None
            videos.append(f)
    counts: dict[str, int] = {}
    for f in files:
        counts[f["class"]] = counts.get(f["class"], 0) + 1
    res.update(
        status="ok" if (ffprobe or not videos) else "partial",
        file_count=len(files), truncated=truncated, counts=counts,
        total_mb=round(sum(f["bytes"] for f in files) / 1e6, 2),
        ffprobe="available" if ffprobe else "missing",
        camera_original_candidates=candidates(videos) if ffprobe else "unknown (ffprobe missing: ask the user)",
        files=files,
        note="heuristic; confirm with the user which file is the camera original",
    )
    return res


def _self_check() -> int:
    fails = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        if inventory(root / "missing")["status"] != "blocked":
            fails.append("missing folder must be blocked")
        if inventory(root)["status"] != "blocked":
            fails.append("empty folder must be blocked, not 'nothing found'")
        (root / "sub").mkdir()
        (root / "sub" / "logo.png").write_bytes(b"x")
        (root / "sub" / "model.glb").write_bytes(b"x")
        (root / "notes.txt").write_text("hi", encoding="utf-8")
        r = inventory(root)
        if r["status"] not in ("ok", "partial") or r["counts"].get("image") != 1 or r["counts"].get("model_3d") != 1:
            fails.append(f"classification failed: {r.get('counts')}")
        heb = root / "תיקייה"
        heb.mkdir()
        (heb / "קובץ.txt").write_text("שלום", encoding="utf-8")
        if not any("תיקייה/קובץ.txt" == f["path"] for f in inventory(root)["files"]):
            fails.append("hebrew paths must be listed")
        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            for name, size, br in (("rough_1080.mp4", "320x180", "200k"), ("camera_orig.mp4", "960x540", "4M")):
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=25",
                                "-t", "2", "-c:v", "libx264", "-b:v", br, "-pix_fmt", "yuv420p", str(root / name)],
                               check=True, capture_output=True)
            r = inventory(root)
            cands = r.get("camera_original_candidates")
            if not (isinstance(cands, list) and any(c["probable_original"] == "camera_orig.mp4" and c["over"] == "rough_1080.mp4" for c in cands)):
                fails.append(f"camera original not flagged: {cands}")
        else:
            print("note: ffmpeg/ffprobe missing, video probing not tested")
        out = root / "_work" / "intake"
        if main([str(root), "--write", str(out)]) != 0 or not (out / "source_ls.txt").is_file() or not (out / "probe.json").is_file():
            fails.append("--write must create source_ls.txt and probe.json")
        if main([str(root / "missing"), "--write", str(root / "never")]) != 2 or (root / "never").exists():
            fails.append("--write must not write evidence for a blocked listing")
    for f in fails:
        print("FAIL:", f)
    print("self-check:", "FAILED" if fails else "ok")
    return 1 if fails else 0


def render_text(res: dict) -> str:
    out = [f"source_inventory: {res['status']}  root={res['root']}"]
    if res["status"] == "blocked":
        out.append("  blocked: " + res["reason"])
    else:
        out.append(f"  files={res['file_count']} total={res['total_mb']} MB counts={res['counts']} ffprobe={res['ffprobe']}")
        for f in res["files"]:
            p = f.get("probe")
            extra = f"  {p['width']}x{p['height']} {p['fps']}fps {p['duration_s']}s {p['bitrate_kbps']}kbps {p['codec']}" if p and "width" in p else ""
            out.append(f"  [{f['class']}] {f['path']} ({f['bytes']} B){extra}")
        out.append("  camera_original_candidates: " + json.dumps(res["camera_original_candidates"], ensure_ascii=False))
        if res["truncated"]:
            out.append("  WARNING: listing truncated at --max-files")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return _self_check()
    ap = argparse.ArgumentParser(prog="source_inventory.py", add_help=False)
    ap.add_argument("source", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-files", type=int, default=2000)
    ap.add_argument("--write")
    ap.add_argument("-h", "--help", action="store_true")
    a = ap.parse_args(argv)
    if a.help or not a.source:
        print(__doc__)
        return 2
    res = inventory(Path(a.source), a.max_files)
    print(json.dumps(res, ensure_ascii=False, indent=2) if a.json else render_text(res), end="\n" if a.json else "")
    if a.write and res["status"] in ("ok", "partial"):
        d = Path(a.write)
        d.mkdir(parents=True, exist_ok=True)
        (d / "source_ls.txt").write_text(render_text(res), encoding="utf-8")
        (d / "probe.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if res["status"] in ("ok", "partial") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

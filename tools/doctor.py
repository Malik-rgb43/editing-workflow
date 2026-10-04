"""doctor - health check AND hardware auto-detection. Decides the safest working profile for THIS machine (no questions asked).

Modes (src: blueprint REPO_ARCHITECTURE section 8; ADR 0002 "universal by default"):
  report      (default) read-only: detects OS/CPU/GPU/RAM/disk, finds tools, checks paths and Hebrew text; never installs, fetches,
              edits PATH, reads credential VALUES or starts a paid job.
  recommend   report + cheap REAL probes of hardware encoders; prints the recommended profiles with their evidence state.
  smoke       recommend + explicit local ephemeral work: a real mini-encode/decode through FFmpeg in a Hebrew+emoji temp path and the
              QA tools (frame_qa, caption_qa, hf_preflight) run on a synthetic clip. Writes only under the system temp folder.

Every check: id, state (pass|fail|unsupported|not_run|insufficient_evidence|error), evidence, observed/required, executable, remediation,
duration_s, redacted. The aggregate is GREEN only when every REQUIRED check passed - a required check that is ``not_run`` (e.g. the
QA smoke in report mode) keeps it non-green ("no green aggregate while a required final-output gate is not_run").
unsupported != missing != error. An optional route failing never invalidates the core (core-cpu always works with FFmpeg + Python).
Hardware encoders (NVENC/QSV/AMF/VideoToolbox) are only trusted after a real mini-encode (NVENC/QSV were listed but failed to init on
the author's AMD host, F20). No GPU number is assumed: only one machine was ever measured; everything else is labelled unmeasured.

Usage:
    python tools/doctor.py [report|recommend|smoke] [--json] [--work-root DIR] [--out report.json]
Exit: 0 green, 1 a required check failed, 2 not green (a required check not run / insufficient evidence), 3 doctor crashed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

import _common  # noqa: F401

VERSION = "0.1.0"
REQUIRED = ("python_version", "ffmpeg_found", "ffmpeg_encode_decode", "paths_unicode_roundtrip", "qa_tools_smoke")


def _redact(text: str) -> str:
    home = str(Path.home())
    for h in {home, home.replace("\\", "/")}:
        if h and h in text:
            text = text.replace(h, "~")
    return text


class Check:
    def __init__(self, id, required=False):
        self.d = {"id": id, "state": "not_run", "evidence": "", "observed": None, "required": None, "executable": None, "remediation": None, "duration_s": 0.0, "redacted": True}
        self.required = required or id in REQUIRED
        self._t = time.monotonic()

    def set(self, state, evidence="", **kw):
        self.d["state"], self.d["evidence"] = state, _redact(str(evidence))
        for k, v in kw.items():
            self.d[k] = _redact(v) if isinstance(v, str) else v
        self.d["duration_s"] = round(time.monotonic() - self._t, 3)
        return self.d


def _run(cmd, timeout=30):
    from core.procs import run

    try:
        return run(cmd, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        class R:  # noqa: D401
            returncode, stdout, stderr, timed_out = 127, "", f"{type(exc).__name__}: {exc}", False

        return R()


# ----------------------------------------------------------------------------------------------- detection
def detect_host():
    sysname = platform.system()
    arch = platform.machine().lower()
    host = {"os": sysname, "os_release": platform.release(), "arch": arch, "python": platform.python_version(), "cpu_count": os.cpu_count(), "shell": os.environ.get("SHELL") or os.environ.get("ComSpec") or "?"}
    host["apple_silicon"] = sysname == "Darwin" and arch in ("arm64", "aarch64")
    host["ram_gb"] = _ram_gb(sysname)
    host["gpus"] = _gpus(sysname)
    return host


def _ram_gb(sysname):
    try:
        if sysname == "Windows":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong), ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]

            ms = MS()
            ms.l = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))  # type: ignore[attr-defined]
            return round(ms.tp / 2**30, 1)
        if sysname == "Darwin":
            r = _run(["sysctl", "-n", "hw.memsize"], 5)
            return round(int(r.stdout.strip()) / 2**30, 1) if r.returncode == 0 else None
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal"):
                    return round(int(line.split()[1]) / 2**20, 1)
    except Exception:  # noqa: BLE001
        return None
    return None


def _vendor(name: str) -> str:
    n = name.lower()
    if "nvidia" in n or "geforce" in n or "rtx" in n or "quadro" in n:
        return "nvidia"
    if "amd" in n or "radeon" in n or "advanced micro" in n:
        return "amd"
    if "intel" in n or "arc" in n.split():
        return "intel"
    if "apple" in n:
        return "apple"
    return "unknown"


def _gpus(sysname):
    names: list[str] = []
    try:
        if sysname == "Windows":
            r = _run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }"], 20)
            names = [x.strip() for x in r.stdout.splitlines() if x.strip()] if r.returncode == 0 else []
        elif sysname == "Darwin":
            r = _run(["system_profiler", "SPDisplaysDataType"], 20)
            names = re.findall(r"Chipset Model:\s*(.+)", r.stdout) if r.returncode == 0 else []
        else:
            r = _run(["sh", "-c", "lspci 2>/dev/null | grep -iE 'vga|3d|display'"], 10)
            names = [x.split(": ", 1)[-1].strip() for x in r.stdout.splitlines() if x.strip()] if r.returncode == 0 else []
    except Exception:  # noqa: BLE001
        names = []
    return [{"name": n, "vendor": _vendor(n)} for n in names]


# ----------------------------------------------------------------------------------------------- checks
def check_python():
    c = Check("python_version")
    v = sys.version_info
    ok = v >= (3, 12)
    return c.set("pass" if ok else "fail", f"Python {platform.python_version()}", observed=platform.python_version(), required=">=3.12", executable=sys.executable,
                 remediation=None if ok else "install Python 3.12+ or use `uv` (project-scoped; the system Python is never modified)")


def check_release():
    c = Check("release_identity")
    p = Path(__file__).resolve().parents[1] / "release-manifest.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return c.set("pass", f"release {d.get('version')} (schema {d.get('schema_version', d.get('schema', '?'))})", observed=str(d.get("version")))
    except (OSError, ValueError) as exc:
        return c.set("insufficient_evidence", f"release-manifest.json unreadable: {exc}", remediation="re-clone or re-extract the release")


def check_ffmpeg():
    c = Check("ffmpeg_found")
    from core.errors import MediaToolMissing
    from core.ffprobe import find_ffmpeg, find_ffprobe, ffmpeg_version

    try:
        ff, fp = find_ffmpeg(), find_ffprobe()
        ver = ffmpeg_version()
        return c.set("pass", f"{ver}", observed=ver, executable=ff)
    except MediaToolMissing as exc:
        return c.set("fail", str(exc), remediation="install FFmpeg: winget install Gyan.FFmpeg (Windows) | brew install ffmpeg (macOS) | apt install ffmpeg (Linux); the toolkit never bundles FFmpeg")


def _lavfi(out, seconds=0.4, codec=("libx264",), extra=()):
    from core.ffprobe import find_ffmpeg

    return _run([find_ffmpeg(), "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25", "-t", str(seconds), "-pix_fmt", "yuv420p", "-c:v", *codec, *extra, str(out)], 60)


def check_encode_decode(tmp: Path):
    c = Check("ffmpeg_encode_decode")
    try:
        out = tmp / "enc.mp4"
        r = _lavfi(out)
        if r.returncode != 0 or not out.exists():
            return c.set("fail", f"libx264 mini-encode failed: {(r.stderr or '').strip()[-200:]}", remediation="use an FFmpeg build with libx264 (the Gyan full build / Homebrew / distro ffmpeg)")
        from core.ffprobe import expected_frames, probe

        info = probe(out)
        n, _ = expected_frames(out, info)
        ok = n == 10
        return c.set("pass" if ok else "fail", f"encoded+probed {n} frames (expected 10) at {info.first_video.fps}", observed=str(n), required="10")
    except Exception as exc:  # noqa: BLE001
        return c.set("error", f"{type(exc).__name__}: {exc}")


def check_paths(tmp: Path, work_root: str | None):
    c = Check("paths_unicode_roundtrip")
    try:
        from core.ffprobe import probe

        hostile = tmp / "בדיקה 'quote' 🎬 dir"
        hostile.mkdir()
        out = hostile / "שלום clip.mp4"
        r = _lavfi(out, 0.2)
        if r.returncode != 0:
            return c.set("fail", f"FFmpeg could not write into a Hebrew/space/apostrophe/emoji path: {(r.stderr or '').strip()[-160:]}", remediation="use an ASCII work root (AVC_PATHS_WORK_ROOT)")
        info = probe(out)
        wr = work_root or os.environ.get("AVC_PATHS_WORK_ROOT") or ""
        note = ""
        if wr and not wr.isascii():
            note = f"; WARNING work root {wr!r} is not ASCII (`npx hyperframes init` silently skips index.html there)"
        return c.set("pass", f"Hebrew+space+apostrophe+emoji path round-trip OK ({info.first_video.width}x{info.first_video.height}){note}")
    except Exception as exc:  # noqa: BLE001
        return c.set("error", f"{type(exc).__name__}: {exc}")


def check_work_root(work_root):
    c = Check("work_root")
    wr = work_root or os.environ.get("AVC_PATHS_WORK_ROOT")
    if not wr:
        return c.set("not_run", "no work root configured yet (paths.work_root in toolkit.toml or AVC_PATHS_WORK_ROOT); `new_project` will propose an ASCII one", remediation="set an ASCII folder, e.g. C:\\avc-work or ~/avc-work")
    from core.paths import forbidden_reason, is_ascii_path

    why = forbidden_reason(wr)
    if why:
        return c.set("fail", f"forbidden work root: {why}")
    if not is_ascii_path(wr):
        return c.set("fail", f"{wr!r} contains non-ASCII characters", remediation="choose an ASCII-only folder")
    return c.set("pass", f"{wr} is ASCII and not a forbidden root")


def check_hebrew_text():
    c = Check("hebrew_text_rendering")
    try:
        from PIL import ImageFont

        cands = [
            "arial.ttf", "Arial.ttf", "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/ArialHB.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf",
        ]
        for name in cands:
            try:
                f = ImageFont.truetype(name, 48)
            except OSError:
                continue
            a = f.getmask("א")
            missing = f.getmask("\ue000")
            if a.getbbox() and (a.size != missing.size or bytes(a) != bytes(missing)):
                return c.set("pass", f"a system font with Hebrew glyphs renders (basic check; real caption fonts must be files in hf/fonts/): {name}")
        return c.set("not_run", "no system font with Hebrew glyphs was found for the basic check; caption fonts must be files in hf/fonts/ anyway", remediation="`python fixtures/generators/fetch_ofl_fonts.py` fetches OFL Hebrew fonts (network, explicit)")
    except Exception as exc:  # noqa: BLE001
        return c.set("not_run", f"Pillow not available: {exc}", remediation="uv sync")


def check_node():
    c = Check("node_engine")
    node = shutil.which("node")
    if not node:
        return c.set("not_run", "Node.js not found; only the HyperFrames engine needs it (the CPU QA path does not)", remediation="install Node.js LTS (nodejs.org, winget install OpenJS.NodeJS.LTS, brew install node)")
    r = _run([node, "--version"], 10)
    ver = r.stdout.strip()
    from core import hf_engine

    info = hf_engine.describe()
    if info.get("found") and info.get("problem"):
        return c.set("fail", f"node {ver}; {info['problem']}", observed=ver, executable=node, remediation="re-run `python install/bootstrap.py apply` (it chooses an ASCII toolkit folder when your home path has non-ASCII letters)")
    if info.get("found") and info.get("source") == "toolkit":
        hv, pin = info.get("version"), info.get("pinned")
        drift = f"; installed {hv} differs from the pin {pin} (run `npm ci --ignore-scripts` in the toolkit folder)" if hv and pin and hv != pin else ""
        return c.set("pass" if hv else "not_run", f"node {ver}; hyperframes v{hv} (pinned {pin}){drift}", observed=ver, executable=node)
    npx = shutil.which("npx")
    hf = _run([npx, "--no-install", "hyperframes", "--version"], 25) if npx else None
    hv = (hf.stdout.strip() if hf and hf.returncode == 0 else None)
    return c.set("pass" if hv else "not_run", f"node {ver}; hyperframes {'v' + hv if hv else 'not installed locally (nothing was downloaded)'}", observed=ver, executable=node,
                 remediation=None if hv else "installed by `python install/bootstrap.py apply` (it runs `npm ci --ignore-scripts` from package.json + package-lock.json)")


def check_disk(work_root):
    c = Check("storage")
    p = work_root or tempfile.gettempdir()
    try:
        free = shutil.disk_usage(p).free / 2**30
    except OSError:
        free = shutil.disk_usage(tempfile.gettempdir()).free / 2**30
    st = "pass" if free >= 10 else "fail"
    return c.set(st, f"{free:.1f} GB free on the work volume (renders and caches need several GB; 10 GB is the toolkit's minimum, unmeasured as a limit)", observed=f"{free:.1f} GB", required=">=10 GB")


def check_credentials():
    c = Check("credentials_presence")
    names = ["ELEVENLABS_API_KEY", "PEXELS_API_KEY", "TWENTYFIRST_API_KEY", "GEMINI_API_KEY"]
    present = [n for n in names if os.environ.get(n)]
    return c.set("pass", f"presence only, values never read or printed: {', '.join(present) if present else 'none set'} (none is required for the core path)", observed=present)


def check_lock():
    c = Check("heavy_job_lock")
    try:
        from core.config import load_config
        from core.lock import status

        lp = load_config().lock_path
        st = status(lp)
        return c.set("pass", f"lock at {lp}: {'held' if getattr(st, 'held', False) else 'free'}")
    except Exception as exc:  # noqa: BLE001
        return c.set("insufficient_evidence", f"lock status unavailable: {type(exc).__name__}: {exc}")


def probe_hw_encoders(tmp: Path):
    """Real mini-encode per candidate; listed-but-failing encoders are `fail` (not usable), never assumed."""
    from core.ffprobe import find_ffmpeg

    r = _run([find_ffmpeg(), "-hide_banner", "-encoders"], 20)
    listed = r.stdout
    out = []
    for enc in ("h264_nvenc", "h264_qsv", "h264_amf", "h264_videotoolbox"):
        c = Check(f"encoder_{enc}")
        if enc not in listed:
            out.append(c.set("unsupported", f"{enc} is not compiled into this FFmpeg build"))
            continue
        res = _lavfi(tmp / f"{enc}.mp4", 0.2, codec=(enc,))
        if res.returncode == 0 and (tmp / f"{enc}.mp4").exists():
            out.append(c.set("pass", f"{enc} listed AND a real mini-encode succeeded"))
        else:
            last = ((res.stderr or "").strip().splitlines() or ["(no message)"])[-1][:120]
            out.append(c.set("unsupported", f"{enc} is listed in this FFmpeg build but failed to initialise on this machine ({last}); not usable here, the CPU encoder libx264 is the baseline"))
    return out


def check_asr_assets():
    c = Check("asr_assets")
    found = []
    import importlib.util as iu

    for mod in ("faster_whisper", "onnxruntime", "numpy", "PIL", "cv2"):
        found.append(f"{mod}:{'yes' if iu.find_spec(mod) else 'no'}")
    return c.set("pass", "optional runtimes (find_spec only, nothing imported or downloaded): " + ", ".join(found))


def check_qa_smoke(tmp: Path, mode: str):
    c = Check("qa_tools_smoke")
    if mode != "smoke":
        return c.set("not_run", "run `doctor smoke` to prove the QA tools execute on this machine (a required final-output gate: the aggregate stays non-green until it ran)", remediation="python tools/doctor.py smoke")
    tools = Path(__file__).resolve().parent
    try:
        clip = tmp / "qa clip 🎬.mp4"
        r = _lavfi(clip, 1.0)
        if r.returncode != 0:
            return c.set("fail", "could not create the smoke clip")
        results = {}
        for name, args in (("frame_qa", [str(clip)]), ("sheet", [str(clip), "-o", str(tmp / "s.jpg"), "--count", "4"])):
            rr = _run([sys.executable, "-X", "utf8", str(tools / f"{name}.py"), *args], 120)
            results[name] = rr.returncode
        html = tmp / "index.html"
        html.write_text('<html><body><div id="a" class="clip" data-start="0" data-duration="1"></div></body></html>', encoding="utf-8")
        rr = _run([sys.executable, "-X", "utf8", str(tools / "hf_preflight.py"), str(html)], 60)
        results["hf_preflight"] = rr.returncode
        bad = {k: v for k, v in results.items() if v != 0}
        return c.set("pass" if not bad else "fail", f"exit codes {results}" + (f"; non-zero: {bad}" if bad else ""), observed=json.dumps(results))
    except Exception as exc:  # noqa: BLE001
        return c.set("error", f"{type(exc).__name__}: {exc}")


# ----------------------------------------------------------------------------------------------- recommendation
def recommend(host, checks_by_id):
    """Pick profiles from detection + probes. CPU routes are always available; GPU routes only when a probe passed."""
    rec = {"base": {"profile": "core-cpu", "evidence": "works everywhere with FFmpeg + Python; no key, GPU or account"}}
    gpus = {g["vendor"] for g in host["gpus"]}
    asr = {"profile": "asr-cpu", "evidence": "CPU route: always works; slower; no GPU needed", "fallback": None}
    rec["asr"] = asr
    rec["matte"] = {"profile": "matte-native-or-modnet-cpu", "evidence": "CPU route works everywhere; GPU/DirectML routes are opt-in and unmeasured on other machines"}
    enc = [k for k, v in checks_by_id.items() if k.startswith("encoder_") and v["state"] == "pass"]
    rec["video_encoder"] = {"final": "libx264", "draft": enc[0].replace("encoder_", "") if enc else "libx264", "evidence": "finals always use CPU libx264 (quality, portability); a hardware encoder is offered for drafts only after a real mini-encode passed" if enc else "CPU libx264 (baseline) for drafts and finals"}
    ram = host.get("ram_gb")
    rec["machine_class"] = "constrained (RAM < 8 GB: render drafts at 720p, one job at a time)" if ram and ram < 8 else ("standard" if not ram or ram < 24 else "comfortable")
    return rec


def run_doctor(mode, work_root):
    t0 = time.monotonic()
    host = detect_host()
    tmp = Path(tempfile.mkdtemp(prefix="avc-doctor-"))
    checks = []
    try:
        checks += [check_python(), check_release(), check_ffmpeg()]
        ff_ok = checks[-1]["state"] == "pass"
        if ff_ok:
            checks += [check_encode_decode(tmp), check_paths(tmp, work_root)]
        else:
            for cid in ("ffmpeg_encode_decode", "paths_unicode_roundtrip"):
                checks.append(Check(cid).set("not_run", "FFmpeg is missing, so this could not run"))
        checks += [check_work_root(work_root), check_hebrew_text(), check_node(), check_disk(work_root), check_credentials(), check_lock(), check_asr_assets()]
        if mode in ("recommend", "smoke") and ff_ok:
            checks += probe_hw_encoders(tmp)
        checks.append(check_qa_smoke(tmp, mode) if ff_ok else Check("qa_tools_smoke").set("not_run", "FFmpeg is missing"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    by_id = {c["id"]: c for c in checks}
    req = [by_id[i] for i in REQUIRED if i in by_id]
    if any(c["state"] in ("fail", "error") for c in req):
        agg, code = "red", 1
    elif all(c["state"] == "pass" for c in req) and len(req) == len(REQUIRED):
        agg, code = "green", 0
    else:
        agg, code = "not_green", 2
    return {
        "doctor": VERSION, "mode": mode, "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "host": _redact(json.dumps(host, ensure_ascii=False)) and host, "checks": checks, "aggregate": agg, "required": list(REQUIRED),
        "recommendation": recommend(host, by_id), "duration_s": round(time.monotonic() - t0, 2),
        "note": "green = every required check passed; a required check that did not run keeps it non-green. Unmeasured routes are labelled as such.",
    }, code


def human(rep):
    lines = [f"doctor {rep['doctor']} ({rep['mode']}) on {rep['host']['os']} {rep['host']['arch']}, RAM {rep['host']['ram_gb']} GB, GPUs: {', '.join(g['name'] for g in rep['host']['gpus']) or 'none detected'}", ""]
    icon = {"pass": "OK ", "fail": "FAIL", "unsupported": "n/a ", "not_run": "----", "insufficient_evidence": "????", "error": "ERR "}
    for c in rep["checks"]:
        star = "*" if c["id"] in rep["required"] else " "
        lines.append(f" {icon.get(c['state'], c['state'])} {star} {c['id']:<28} {c['evidence'][:110]}")
        if c["state"] in ("fail", "error") and c.get("remediation"):
            lines.append(f"         -> {c['remediation']}")
    lines += ["", f"aggregate: {rep['aggregate'].upper()}   (* = required)", "recommended:"]
    for k, v in rep["recommendation"].items():
        lines.append(f"  {k}: {v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="doctor", description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", nargs="?", default="report", choices=["report", "recommend", "smoke"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--work-root")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    try:
        rep, code = run_doctor(args.mode, args.work_root)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"doctor": VERSION, "aggregate": "error", "error": f"{type(exc).__name__}: {exc}"}))
        return 3
    if args.out:
        from core.fsio import write_json_atomic

        write_json_atomic(args.out, rep)
    print(json.dumps(rep, ensure_ascii=False, indent=2) if args.json else human(rep))
    return code


if __name__ == "__main__":
    sys.exit(main())

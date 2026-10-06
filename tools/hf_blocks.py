"""hf_blocks - the studio's own HyperFrames block library: list, add to a project, feed with real data, and ADMIT (verify in an empty project).

A block (``hf-blocks/<name>/``) is a self-contained sub-composition: ``block.html`` + ``demo.html`` (a short empty-project demo that embeds it as ``compositions/<name>.html``)
+ ``block.json`` (manifest) + ``README.md`` + ``SOURCE.md``. Contract: seek-safe by the five iron rules (one paused timeline, no clocks, no random, no CSS transitions, no
interaction, finite CSS animation only), ids prefixed with the block name, colours only through ``--hfb-*`` CSS variables, and ADMITTED only when ``verify`` passes: ``seek_safe_scan.py``
has no error AND ``hyperframes check`` passes in a throw-away project that holds nothing but the demo. A block that fails is not admitted.

Usage:
    python tools/hf_blocks.py <list|add|levels|caption-words|verify> ...      (details below)

Subcommands:
  list                                   the blocks, their duration, variables and palette
  add <block> <hf-dir> [--as NAME] [--set key=path ...] [--var id=value ...] [--start S] [--duration D] [--track N]
                                         copy the block to <hf-dir>/compositions/<NAME>.html (renaming ids and the timeline key when --as is given, so a block can be used twice)
                                         and print the host <div> to paste into index.html. Never edits index.html.
  levels <audio> -o levels.json [--from S --to S]       loudness envelope (30 values/s, 0..1, fast attack / slow release) for voice-orb
  caption-words <words.json> --from S --to S [-o out]   the `words` + `rtl` variables for the caption block from a transcribe.py words.json (times shifted to the block start)
  verify [block ...] [--keep]            admission test in an empty ASCII project; exit 0 only if every named block passes (default: all)
Exit: 0 ok, 2 refused / failed, 3 tool error.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import _common  # noqa: F401

REPO = Path(__file__).resolve().parents[1]
BLOCKS = REPO / "hf-blocks"
SCAN_REL = Path("pro-video-editor") / "scripts" / "seek_safe_scan.py"
HF_JSON = {"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json", "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}, "media": {"autoProxy": True}}


def find_scan() -> Path | None:
    """seek_safe_scan.py lives in a skill: in a checkout under agent-content/skills, once installed under the user's skills folders."""
    for base in (REPO / "agent-content" / "skills", Path.home() / ".claude" / "skills", Path.home() / ".agents" / "skills"):
        if (base / SCAN_REL).is_file():
            return base / SCAN_REL
    return None


def manifests() -> dict:
    out = {}
    for d in sorted(p for p in BLOCKS.iterdir() if p.is_dir()) if BLOCKS.is_dir() else []:
        m = d / "block.json"
        if m.is_file():
            doc = json.loads(m.read_text(encoding="utf-8"))
            doc["_dir"] = d
            out[doc["name"]] = doc
    return out


def rename_block(text: str, old: str, new: str) -> str:
    """Rename ids, selectors, the composition id and the timeline key: an occurrence of the block name directly after a quote or # and before - " ' space or . ."""
    return re.sub(r"([\"'#])" + re.escape(old) + r"(?=[-\"'\s.])", lambda m: m.group(1) + new, text)


def coerce(value: str, typ: str):
    if typ == "number":
        return float(value) if "." in value else int(value)
    if typ == "boolean":
        return value.strip().lower() in ("1", "true", "yes")
    return value


def cmd_list(a) -> int:
    rows = []
    for n, m in manifests().items():
        rows.append({"name": n, "title": m["title"], "duration_s": m["duration_s"], "overlay": m["overlay"], "variables": [v["id"] for v in m["variables"]], "palette": m["palette"], "needs": list(m.get("replace", {}))})
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"{r['name']:24} {r['duration_s']:>4} s  {'overlay' if r['overlay'] else 'full  '}  vars: {', '.join(r['variables'])}" + (f"  needs: {', '.join(r['needs'])}" if r["needs"] else ""))
    return 0


def cmd_add(a) -> int:
    ms = manifests()
    m = ms.get(a.block)
    if not m:
        print(f"hf_blocks: unknown block {a.block!r}; known: {', '.join(ms)}", file=sys.stderr)
        return 2
    hf = Path(a.hf_dir)
    if not hf.is_dir():
        print(f"hf_blocks: not a folder: {hf}", file=sys.stderr)
        return 2
    name = a.as_name or a.block
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        print("hf_blocks: --as must be lowercase letters, digits and dashes", file=sys.stderr)
        return 2
    dest = hf / "compositions" / f"{name}.html"
    if dest.exists() and not a.force:
        print(f"hf_blocks: {dest} exists (use --force to replace it; never overwritten silently)", file=sys.stderr)
        return 2
    src = (m["_dir"] / "block.html").read_text(encoding="utf-8")
    sets = dict(s.split("=", 1) for s in (a.set or []) if "=" in s)
    for key, val in sets.items():
        if key not in m.get("replace", {}):
            print(f"hf_blocks: {a.block} has no --set {key!r}; it accepts: {', '.join(m.get('replace', {})) or 'nothing'}", file=sys.stderr)
            return 2
        target = hf / val
        if not target.is_file():
            print(f"hf_blocks: --set {key}={val}: {target} does not exist (paths are relative to the hf folder)", file=sys.stderr)
            return 2
        src = src.replace(m["replace"][key], val.replace("\\", "/"))
    missing = [k for k in m.get("replace", {}) if k not in sets]
    if name != a.block:
        src = rename_block(src, a.block, name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src, encoding="utf-8", newline="\n")
    types = {v["id"]: v["type"] for v in m["variables"]}
    values = {}
    for kv in a.var or []:
        k, _, v = kv.partition("=")
        if k not in types:
            print(f"hf_blocks: {a.block} has no variable {k!r}; it has: {', '.join(types)}", file=sys.stderr)
            return 2
        values[k] = coerce(v, types[k])
    dur = a.duration if a.duration is not None else m["duration_s"]
    if "duration" in types and "duration" not in values:
        values["duration"] = dur
    attrs = f'id="{name}-clip" class="clip" data-composition-id="{name}-host" data-composition-src="compositions/{name}.html" data-start="{a.start}" data-duration="{dur}" data-track-index="{a.track}"'
    if values:
        attrs += " data-variable-values='" + html.escape(json.dumps(values, ensure_ascii=False), quote=False).replace("'", "&#39;") + "'"
    print(json.dumps({"copied_to": str(dest), "renamed": name if name != a.block else None, "missing_set": missing}, ensure_ascii=False), file=sys.stderr)
    print(f"<div {attrs}></div>")
    if missing:
        print(f"note: {a.block} still points at its placeholder files for: {', '.join(missing)} - pass --set {missing[0]}=assets/video/<file>", file=sys.stderr)
    return 0


def cmd_levels(a) -> int:
    import numpy as np

    from core.errors import ToolkitError
    from core.fsio import write_json_atomic
    from core.media import read_audio_samples

    try:
        sr = 16000
        x = read_audio_samples(a.audio, sample_rate=sr, channels=1)[:, 0].astype(np.float32) / 32768.0
    except ToolkitError as exc:
        print(f"hf_blocks: {exc}", file=sys.stderr)
        return 2
    t0, t1 = a.start or 0.0, a.to if a.to is not None else len(x) / sr
    x = x[int(t0 * sr): int(t1 * sr)]
    hop = sr // 30
    n = len(x) // hop
    if n < 3:
        print("hf_blocks: less than 0.1 s of audio in the range", file=sys.stderr)
        return 2
    rms = np.sqrt((x[: n * hop].reshape(n, hop).astype(np.float64) ** 2).mean(axis=1))
    db = 20 * np.log10(rms + 1e-6)
    voiced = db[db > db.max() - 45] if db.max() > -60 else db
    lo, hi = float(np.percentile(voiced, 10)), float(np.percentile(db, 98))
    if hi - lo < 3:
        print("hf_blocks: the audio has almost no dynamics (silence or a constant tone): nothing to animate", file=sys.stderr)
        return 2
    raw = np.clip((db - lo) / (hi - lo), 0, 1)
    out, cur = [], 0.0
    for v in raw:  # fast attack, slow release: deterministic smoothing
        cur = cur + (0.55 if v > cur else 0.18) * (v - cur)
        out.append(round(float(cur), 2))
    doc = {"schema": "avc.voice-levels/1", "fps": 30, "from_s": t0, "to_s": t1, "duration_s": round(n / 30, 3), "levels": out}
    write_json_atomic(a.out, doc)
    print(f"hf_blocks: {n} levels ({doc['duration_s']} s) -> {a.out}; use --var levels='{json.dumps(out)[:40]}...' or paste the file's `levels` array as a JSON string")
    return 0


def cmd_caption_words(a) -> int:
    doc = json.loads(Path(a.words).read_text(encoding="utf-8"))
    ws = [w for w in doc.get("words", []) if isinstance(w, dict) and "w" in w]
    sel = [{"w": w["w"], "start": round(max(0.0, w["start"] - a.start), 3), "end": round(max(0.0, w["end"] - a.start), 3)} for w in ws if w["end"] > a.start and w["start"] < a.to]
    if not sel:
        print("hf_blocks: no words in that range", file=sys.stderr)
        return 2
    # right-to-left scripts: Hebrew, Arabic (+ Persian / Urdu letters), Syriac, Thaana, N'Ko, and their presentation forms
    rtl_re = r"[\u0590-\u08ff\ufb1d-\ufdff\ufe70-\ufeff]"
    letters = re.findall(r"[A-Za-z\u00c0-\u024f\u0370-\u04ff]|" + rtl_re, "".join(w["w"] for w in sel))
    rtl_n = len(re.findall(rtl_re, "".join(letters)))
    rtl = bool(letters) and rtl_n / len(letters) > 0.5
    out = {"words": json.dumps(sel, ensure_ascii=False), "rtl": rtl, "duration": round(a.to - a.start, 3)}
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"hf_blocks: {len(sel)} words, rtl={rtl} -> {a.out} (paste it as data-variable-values on the caption host)")
    else:
        print(text)
    return 0


def make_assets(tmp: Path, names: list[str]) -> str | None:
    """Synthetic plate + cutout for speaker-cutout-behind's demo. Returns an error text or None."""
    from core.ffprobe import find_ffmpeg
    from core.procs import run

    ff = find_ffmpeg()
    vid = tmp / "assets" / "video"
    vid.mkdir(parents=True, exist_ok=True)
    for n in names:
        if n.endswith("plate.mp4"):
            r = run([ff, "-hide_banner", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x335577:s=1080x1920:r=30:d=3", "-vf", "drawbox=x=0:y=1500:w=1080:h=420:color=0x1f2f44:t=fill", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "15", str(tmp / n)], timeout=120)
        elif n.endswith("cutout.webm"):
            r = run([ff, "-hide_banner", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0xd68c82:s=1080x1920:r=30:d=3", "-vf", "format=yuva420p,geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='if(lt(hypot(X-540,Y-1250),430),255,0)'",
                         "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "34", str(tmp / n)], timeout=300)
        else:
            continue
        if r.returncode != 0:
            return f"could not make the demo asset {n}: {(r.stderr or '').strip()[-200:]}"
    return None


def verify_one(m: dict, keep: bool) -> dict:
    from core import hf_engine
    from core.procs import run

    name = m["name"]
    res = {"block": name, "seek_safe": None, "check": None, "pass": False, "notes": []}
    eng = hf_engine.find()
    if eng is None:
        res["notes"].append("the HyperFrames engine is not installed (python install/bootstrap.py apply)")
        return res
    tmp = Path(tempfile.mkdtemp(prefix=f"avc-block-{name}-"))
    try:
        if not hf_engine.is_ascii_path(tmp):
            res["notes"].append(f"the temp folder {tmp} is not an ASCII path; set TMP to an ASCII folder")
            return res
        (tmp / "compositions").mkdir()
        (tmp / "hyperframes.json").write_text(json.dumps(HF_JSON, indent=2), encoding="utf-8", newline="\n")
        (tmp / "meta.json").write_text(json.dumps({"id": f"block-{name}", "name": f"block-{name}"}), encoding="utf-8", newline="\n")
        (tmp / "package.json").write_text(json.dumps({"name": f"block-{name}", "private": True, "type": "module"}), encoding="utf-8", newline="\n")
        shutil.copyfile(m["_dir"] / "demo.html", tmp / "index.html")
        shutil.copyfile(m["_dir"] / "block.html", tmp / "compositions" / f"{name}.html")
        if m.get("demo_assets"):
            err = make_assets(tmp, m["demo_assets"])
            if err:
                res["notes"].append(err)
                return res
        scan_py = find_scan()
        if scan_py is None:
            res["notes"].append("seek_safe_scan.py not found (install the pro-video-editor skill): the seek-safety half of the admission test cannot run, so nothing is admitted")
            return res
        r = run([sys.executable, "-X", "utf8", str(scan_py), str(tmp), "--json"], timeout=120)
        try:
            scan = json.loads(r.stdout)
        except ValueError:
            scan = {}
        errors = [f for f in scan.get("findings", []) if f.get("severity") in ("E", "error")] if isinstance(scan.get("findings"), list) else []
        res["seek_safe"] = {"exit": r.returncode, "errors": len(errors) if scan else None}
        r2 = run(hf_engine.command(["check"]), cwd=tmp, env=hf_engine.run_env(), timeout=600)
        out = (r2.stdout or "") + (r2.stderr or "")
        lines = [ln.strip() for ln in out.splitlines() if ln.strip() and "browserGpuMode" not in ln]
        res["check"] = {"exit": r2.returncode, "tail": lines[-(12 if r2.returncode == 0 else 60):]}
        res["pass"] = r.returncode == 0 and r2.returncode == 0
        if keep:
            res["kept_at"] = str(tmp)
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)
    return res


def cmd_verify(a) -> int:
    ms = manifests()
    names = a.blocks or list(ms)
    bad = [n for n in names if n not in ms]
    if bad:
        print(f"hf_blocks: unknown block(s): {', '.join(bad)}", file=sys.stderr)
        return 2
    results = [verify_one(ms[n], a.keep) for n in names]
    print(json.dumps({"results": results, "admitted": [r["block"] for r in results if r["pass"]], "rejected": [r["block"] for r in results if not r["pass"]]}, ensure_ascii=False, indent=2))
    return 0 if all(r["pass"] for r in results) else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hf_blocks", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("add")
    s.add_argument("block")
    s.add_argument("hf_dir")
    s.add_argument("--as", dest="as_name")
    s.add_argument("--set", action="append")
    s.add_argument("--var", action="append")
    s.add_argument("--start", type=float, default=0)
    s.add_argument("--duration", type=float)
    s.add_argument("--track", type=int, default=0)
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("levels")
    s.add_argument("audio")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--from", dest="start", type=float)
    s.add_argument("--to", type=float)
    s = sub.add_parser("caption-words")
    s.add_argument("words")
    s.add_argument("--from", dest="start", type=float, required=True)
    s.add_argument("--to", type=float, required=True)
    s.add_argument("-o", "--out")
    s = sub.add_parser("verify")
    s.add_argument("blocks", nargs="*")
    s.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)
    return {"list": cmd_list, "add": cmd_add, "levels": cmd_levels, "caption-words": cmd_caption_words, "verify": cmd_verify}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

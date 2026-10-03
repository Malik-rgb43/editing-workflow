"""Generate the E04 synthetic defect set with FFmpeg ONLY (no client media, nothing downloaded).

The set reproduces experiment E04 (the reference machine, 2026-10-01; src: blueprint
TOOLS_SPEC section 1.8, distilled 03 tool-portability-and-bugs section 1).  All clips are 360x640, 2 s, lossless FFV1/MKV;
the base picture is a moving grey saw-tooth gradient ``60 + ((x + 2*frame) mod 120)`` so every frame differs from its
neighbour except where a defect is injected on purpose.

| id                  | defect injected (0-based frame indices)                                                     |
|---------------------|----------------------------------------------------------------------------------------------|
| clean               | none (control; also *low-feature* for optical-flow tools: it triggered E04-B07)              |
| black               | frame 15 is all-black                                                                        |
| flash               | frame 30 is all-white                                                                        |
| freeze              | frames 20..50 are copies of frame 19 (a 32-frame hold, f19-f50)                              |
| caption_drop_30     | 200x50 white caption proxy at x80 y360 present for frames 0..29, gone from frame 30 (30 fps) |
| caption_drop_25     | same box, present for frames 0..24, gone from frame 25 = 1.00 s at 25 fps (E04-B02)          |
| caption_appear_30   | box absent until frame 29, present from frame 30 (E04-B03 appearance case)                   |
| caption_overlap     | 60 frames; box A frames 15..44, box B frames 30..59, overlapping in time f30-44 and space    |
| low_feature         | smooth moving sinusoid, no corners: optical flow finds ~0 tracked pairs (E04-B07 class)      |
| ntsc_30000_1001     | 90 frames at 30000/1001 fps (drift-guard fixture, E04-B02 / F05)                              |
| clipped_audio       | 3 s 1 kHz sine at 48 kHz, ``volume=12`` -> hard-clipped (peak = full scale)                  |
| tone_ok_audio       | 3 s 1 kHz sine, about -10 dBFS peak (positive control, not clipped)                          |
| delivery_clipped    | ``clean`` video + clipped audio, H.264/AAC MP4 (verify must reject)                          |
| delivery_ok         | ``clean`` video + ``tone_ok`` audio, H.264/AAC MP4 (positive control)                        |

Caption fixtures use a plain rectangle to isolate the pixel/timeline heuristic; they do NOT test glyph legibility or
Hebrew shaping (that needs real text rendering and a licensed font - see fetch_ofl_fonts.py).

Media is written ONLY to the ``--out`` directory (default ``fixtures/_generated/e04``); nothing is ever committed.
The decoded-content SHA-256 of each file is recorded in ``fixtures/manifest.json`` (``--write-manifest``); it is stable for
a given FFmpeg build, and may drift across FFmpeg versions (the test treats drift as a warning and the pixel-level ground
truth as the hard assertion).

Usage:
    python fixtures/generators/make_e04_set.py --out fixtures/_generated/e04 [--only black,flash] [--verify]
    python fixtures/generators/make_e04_set.py --out DIR --write-manifest     # refresh fixtures/manifest.json (E04 + sample project)
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.errors import ToolkitError  # noqa: E402
from core.ffprobe import find_ffmpeg  # noqa: E402
from core.procs import run  # noqa: E402

GENERATOR_VERSION = "0.1.0"
W, H = 360, 640
BOX = dict(x=80, y=360, w=200, h=50)
OVERLAP_A = dict(x=60, y=355, w=230, h=35, first=15, last=44)
OVERLAP_B = dict(x=80, y=375, w=230, h=35, first=30, last=59)

HASH_KIND_MEDIA = "decoded-content (ffmpeg -f hash), stable for one FFmpeg build; drift across builds is a warning"

_RIGHTS = (
    "Synthetic, produced by this repository's generator scripts from FFmpeg lavfi sources. No third-party media, no client "
    "material, no fonts. Licence: the repository licence (Apache-2.0)."
)

# --------------------------------------------------------------------------------------------------------------------
# filter-graph recipes
# --------------------------------------------------------------------------------------------------------------------


def _saw(frame_expr: str = "N") -> str:
    v = f"60+mod(X+2*{frame_expr},120)"
    return f"geq=r='{v}':g='{v}':b='{v}'"


def _base(fps: str, seconds: int = 2, frame_expr: str = "N") -> str:
    return f"color=c=black:s={W}x{H}:r={fps}:d={seconds},format=gbrp,{_saw(frame_expr)}"


def _box(enable: str, *, x: int = BOX["x"], y: int = BOX["y"], w: int = BOX["w"], h: int = BOX["h"], color: str = "white") -> str:
    return f"drawbox=x={x}:y={y}:w={w}:h={h}:color={color}:t=fill:enable='{enable}'"


def video_specs() -> list[dict[str, Any]]:
    """Declarative description of every video fixture: id, lavfi graph, expected facts, ground truth, labels."""
    fps30, fps25 = "30", "25"
    full = lambda color, n: f"drawbox=x=0:y=0:w=iw:h=ih:color={color}:t=fill:enable='eq(n,{n})'"  # noqa: E731
    return [
        dict(id="clean", graph=_base(fps30), fps="30", frames=60, defects=[], intent=["control"],
             truth={"note": "no injected defect; saw-tooth gradient; low-feature for optical-flow tools (E04-B07 trigger)"}),
        dict(id="black", graph=_base(fps30) + "," + full("black", 15), fps="30", frames=60, defects=["black_frame"], intent=[],
             truth={"black_frames": [15]}),
        dict(id="flash", graph=_base(fps30) + "," + full("white", 30), fps="30", frames=60, defects=["flash_frame"], intent=[],
             truth={"flash_frames": [30]}),
        dict(id="freeze", graph=_base(fps30, frame_expr="if(between(N,20,50),19,N)"), fps="30", frames=60, defects=["freeze_hold"], intent=[],
             truth={"freeze_frames": [20, 50], "copy_of_frame": 19, "hold_span_frames": [19, 50], "note": "policy: a hold is a warning, not a FAIL"}),
        dict(id="caption_drop_30", graph=_base(fps30) + "," + _box("lt(n,30)"), fps="30", frames=60, defects=["caption_drop"], intent=[],
             truth={"caption_visible_frames": [0, 29], "caption_drop_frame": 30, "drop_time_s": "1", "box": dict(BOX)}),
        dict(id="caption_drop_25", graph=_base(fps25) + "," + _box("lt(n,25)"), fps="25", frames=50, defects=["caption_drop"], intent=[],
             truth={"caption_visible_frames": [0, 24], "caption_drop_frame": 25, "drop_time_s": "1", "wrong_if_30fps_assumed_s": "5/6", "box": dict(BOX)}),
        dict(id="caption_appear_30", graph=_base(fps30) + "," + _box("gte(n,30)"), fps="30", frames=60, defects=["caption_appearance"], intent=["entrance_is_not_a_defect_by_default"],
             truth={"caption_appearance_frame": 30, "box": dict(BOX)}),
        dict(id="caption_overlap",
             graph=f"color=c=0x5a5a5a:s={W}x{H}:r={fps30}:d=2,format=gbrp,"
             + _box(f"between(n,{OVERLAP_A['first']},{OVERLAP_A['last']})", x=OVERLAP_A["x"], y=OVERLAP_A["y"], w=OVERLAP_A["w"], h=OVERLAP_A["h"])
             + ","
             + _box(f"between(n,{OVERLAP_B['first']},{OVERLAP_B['last']})", x=OVERLAP_B["x"], y=OVERLAP_B["y"], w=OVERLAP_B["w"], h=OVERLAP_B["h"]),
             fps="30", frames=60, defects=["caption_overlap"], intent=[],
             truth={"captions": [{"id": "A", "frames": [15, 45], "bbox": [60, 355, 290, 390]}, {"id": "B", "frames": [30, 60], "bbox": [80, 375, 310, 410]}],
                    "frame_ranges": "half-open [first, last)", "temporal_overlap_frames": [30, 45], "spatial_overlap_bbox": [80, 375, 290, 390]}),
        dict(id="low_feature",
             graph=f"color=c=black:s={W}x{H}:r={fps30}:d=2,format=gbrp,geq=r='128+60*sin(2*PI*X/360+N/12)':g='128+60*sin(2*PI*X/360+N/12)':b='128+60*sin(2*PI*X/360+N/12)'",
             fps="30", frames=60, defects=[], intent=["insufficient_evidence_for_motion_qa"],
             truth={"note": "smooth gradient without corners: a feature tracker must return INSUFFICIENT_EVIDENCE, never PASS or a crash (E04-B07)"}),
        dict(id="ntsc_30000_1001", graph=_base("30000/1001", seconds=4), fps="30000/1001", frames=90, defects=[], intent=["rational_fps_control"],
             truth={"note": "frame 30 is at 1001/1000 s, not 1.000 s; 108000 frames would drift 3.6 s if treated as 30 fps", "frame_30_time_s": "1001/1000"}, limit_frames=90),
    ]


def audio_specs() -> list[dict[str, Any]]:
    return [
        dict(id="clipped_audio", graph="sine=frequency=1000:sample_rate=48000:duration=3,volume=12", defects=["clipped_audio"], intent=[],
             truth={"expect_peak_sample": 32767, "note": "volume=12 on the default 0.125 amplitude sine = 1.5 -> hard-clipped to full scale"}),
        dict(id="tone_ok_audio", graph="sine=frequency=1000:sample_rate=48000:duration=3,volume=8dB", defects=[], intent=["control"],
             truth={"expect_peak_dbfs_approx": -10.1, "note": "0.125 amplitude (-18.06 dBFS) + 8 dB = about -10.1 dBFS peak"}),
    ]


# --------------------------------------------------------------------------------------------------------------------
# execution helpers (shared with make_sample_project.py)
# --------------------------------------------------------------------------------------------------------------------


class GenerationError(ToolkitError):
    code = "fixture_generation_failed"


def ffmpeg_run(args: list[str], *, timeout: float = 180.0, ffmpeg: str | None = None) -> None:
    exe = find_ffmpeg(ffmpeg)
    r = run([exe, "-hide_banner", "-nostdin", "-v", "error", "-y", *args], timeout=timeout)
    if not r.ok:
        raise GenerationError(f"ffmpeg failed (exit {r.returncode}, timed_out={r.timed_out}): {r.stderr.strip()[-800:]}\n  args: {' '.join(args)[:400]}")


def content_sha256(path: Path, kind: str, *, ffmpeg: str | None = None) -> str:
    """SHA-256 of the DECODED content (container-independent): raw frames for video, PCM for audio, bytes for text/image."""
    if kind == "text":
        import hashlib

        return hashlib.sha256(path.read_bytes()).hexdigest()
    exe = find_ffmpeg(ffmpeg)
    sel = {"video": ["-map", "0:v:0"], "audio": ["-map", "0:a:0"], "av": ["-map", "0:v:0", "-map", "0:a:0"]}[kind]
    r = run([exe, "-hide_banner", "-nostdin", "-v", "error", "-i", str(path), *sel, "-fps_mode", "passthrough", "-f", "hash", "-hash", "sha256", "-"], timeout=120)
    if not r.ok or not r.stdout.startswith("SHA256="):
        raise GenerationError(f"cannot hash {path}: {r.stderr.strip()[-300:]}")
    return r.stdout.strip().split("=", 1)[1]


def generate_video(spec: dict[str, Any], out_dir: Path, *, ffmpeg: str | None = None) -> Path:
    path = out_dir / f"{spec['id']}.mkv"
    frames = spec.get("limit_frames") or spec["frames"]
    ffmpeg_run(["-f", "lavfi", "-i", spec["graph"], "-frames:v", str(frames), "-an", "-c:v", "ffv1", "-level", "3", "-g", "1", str(path)], ffmpeg=ffmpeg)
    return path


def generate_audio(spec: dict[str, Any], out_dir: Path, *, ffmpeg: str | None = None) -> Path:
    path = out_dir / f"{spec['id'].replace('_audio', '')}.wav"
    ffmpeg_run(["-f", "lavfi", "-i", spec["graph"], "-c:a", "pcm_s16le", str(path)], ffmpeg=ffmpeg)
    return path


def generate_delivery(out_dir: Path, name: str, video: Path, audio: Path, *, ffmpeg: str | None = None) -> Path:
    path = out_dir / f"{name}.mp4"
    ffmpeg_run(["-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
                "-g", "30", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(path)], ffmpeg=ffmpeg)
    return path


def build_e04(out_dir: Path, *, only: set[str] | None = None, ffmpeg: str | None = None) -> list[dict[str, Any]]:
    """Generate the set into ``out_dir`` and return manifest records (with ``path`` and decoded-content hash)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    def wanted(i: str) -> bool:
        return only is None or i in only

    for spec in video_specs():
        if not wanted(spec["id"]):
            continue
        p = generate_video(spec, out_dir, ffmpeg=ffmpeg)
        fps = Fraction(spec["fps"]) if "/" in spec["fps"] else Fraction(int(spec["fps"]))
        n = spec.get("limit_frames") or spec["frames"]
        records.append(_record(spec, p, "video", {"width": W, "height": H, "fps": spec["fps"], "frames": n, "duration_s": str(Fraction(n) / fps), "codec": "ffv1", "pix_fmt": "gbrp"}, ffmpeg))
    aspecs = {s["id"]: s for s in audio_specs()}
    for aid, spec in aspecs.items():
        if wanted(aid):
            p = generate_audio(spec, out_dir, ffmpeg=ffmpeg)
            records.append(_record(spec, p, "audio", {"sample_rate": 48000, "channels": 1, "duration_s": "3", "codec": "pcm_s16le"}, ffmpeg))
    clean, clipped, ok = out_dir / "clean.mkv", out_dir / "clipped.wav", out_dir / "tone_ok.wav"
    for did, a in (("delivery_clipped", clipped), ("delivery_ok", ok)):
        if wanted(did):
            for needed in (clean, a):
                if not needed.exists():
                    raise GenerationError(f"{did} needs {needed.name}; generate without --only or include its inputs")
            p = generate_delivery(out_dir, did, clean, a, ffmpeg=ffmpeg)
            spec = dict(id=did, defects=["clipped_audio"] if "clipped" in did else [], intent=["control"] if did == "delivery_ok" else [],
                        truth={"note": "E04: verify rejected the clipped mux (-1.4 LUFS, 0.0 dBTP) and passed the normalised mux (-14.0 LUFS)" if "clipped" in did else "audio level about -10 dBFS peak; LUFS not measured by the generator"})
            records.append(_record(spec, p, "av", {"width": W, "height": H, "fps": "30", "frames": 60, "duration_s": "2", "codec": "h264+aac", "pix_fmt": "yuv420p"}, ffmpeg))
    return records


def _record(spec: dict[str, Any], path: Path, kind: str, params: dict[str, Any], ffmpeg: str | None) -> dict[str, Any]:
    return {
        "id": spec["id"],
        "group": "e04",
        "kind": kind,
        "filename": path.name,
        "path": str(path),
        "creator": f"fixtures/generators/make_e04_set.py v{GENERATOR_VERSION}",
        "rights": _RIGHTS,
        "params": params,
        "labels": {"defects": spec.get("defects", []), "intent": spec.get("intent", []), "ground_truth": spec.get("truth", {})},
        "recipe": spec.get("graph") or "see make_e04_set.py generate_delivery",
        "content_sha256": content_sha256(path, kind, ffmpeg=ffmpeg),
        "hash_kind": HASH_KIND_MEDIA,
    }


def _jsonable(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in r.items() if k != "path"} for r in records]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(_HERE.parent / "_generated" / "e04"), help="output directory (default fixtures/_generated/e04)")
    ap.add_argument("--only", help="comma-separated fixture ids")
    ap.add_argument("--write-manifest", action="store_true", help="also generate the sample project and rewrite fixtures/manifest.json")
    ap.add_argument("--verify", action="store_true", help="re-hash after generation and compare with fixtures/manifest.json")
    args = ap.parse_args(argv)
    out = Path(args.out)
    only = set(args.only.split(",")) if args.only else None
    try:
        recs = build_e04(out, only=only)
    except ToolkitError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    for r in recs:
        print(f"{r['id']:<20} {r['filename']:<24} sha256={r['content_sha256'][:16]}")
    if args.write_manifest or args.verify:
        import make_sample_project as sample  # same directory

        try:
            sample_recs = sample.build_sample(out.parent / "sample-project", ffmpeg=None)
        except ToolkitError as exc:
            print(str(exc), file=sys.stderr)
            return 3
        manifest_path = _HERE.parent / "manifest.json"
        if args.write_manifest:
            doc = sample.manifest_document(_jsonable(recs), _jsonable(sample_recs))
            manifest_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(f"wrote {manifest_path}")
        else:
            doc = json.loads(manifest_path.read_text(encoding="utf-8"))
            have = {i["id"]: i["content_sha256"] for i in doc["items"]}
            bad = [r["id"] for r in recs + sample_recs if have.get(r["id"]) != r["content_sha256"]]
            print("content hashes match manifest" if not bad else f"HASH DRIFT for: {', '.join(bad)} (recorded with {doc.get('recorded_with', {}).get('ffmpeg')})")
            return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

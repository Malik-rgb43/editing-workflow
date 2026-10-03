"""Generate the bilingual (Hebrew + English) sample project's SOURCE assets from owned synthetic material.

Everything here is produced by this script: FFmpeg lavfi pictures/tones plus a hand-written six-line demo script.
No stock footage, no recorded speech, no logos or fonts that belong to anyone else.

Output layout (default ``fixtures/_generated/sample-project``)::

    projects/sample-he-en/
        project.json                     slug + Hebrew display title (UTF-8, no BOM)
        source/speaker_standin_1080x1920.mp4   8 s, 30 fps, video + a NON-speech voice-like tone (ASR cannot be tested on it)
        source/broll_abstract_1080x1920.mp4    4 s animated gradient, video only
        source/music_bed.wav                   8 s stereo A-minor pad
        source/logo_mark.png                   512x512 RGBA geometric mark
        source/script.he.txt  script.en.txt    the demo script, one line per row
        source/captions.he.srt captions.en.srt frame-aligned, non-overlapping
        source/cues.json                       word-level timing (synthetic proportional timing, NOT ASR output)
        source/brief.json                      title, palette, aspect, fps

Mixed-direction hazards on purpose (labels in the manifest): a currency sign with a thousands comma (₪1,990), a percent
after digits (50%), a Hebrew prefix hyphen before a Latin word (ב-WhatsApp, ו-50%), Latin words inside Hebrew lines (Wi-Fi).

Fonts: none are used or bundled. Caption RENDERING needs a Hebrew-capable font; use the documented OFL fetch step
(``fetch_ofl_fonts.py``, not run by tests) or the Pillow/DejaVu fallbacks recorded in ``fixtures/manifest.json``.

Usage:
    python fixtures/generators/make_sample_project.py --out fixtures/_generated/sample-project
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parents[1] / "src"
for _p in (str(_SRC), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import make_e04_set as e04  # noqa: E402
from core.errors import ToolkitError  # noqa: E402
from core.ffprobe import ffmpeg_version  # noqa: E402
from core.fsio import write_json_atomic, write_text_atomic  # noqa: E402

FPS = Fraction(30)
SLUG_TITLE_HE = "סרטון הדגמה דו-לשוני"
SLUG_TITLE_EN = "Bilingual demo video"
SAMPLE_SLUG = "sample-he-en"  # fixed ASCII folder name; the Hebrew title lives in project.json

# (id, start_s, end_s, hebrew, english, hazard labels). Times are frame-aligned seconds.
LINES: list[dict[str, Any]] = [
    dict(id=1, start=Fraction(2, 5), end=Fraction(19, 10), he="שלום וברוכים הבאים.", en="Hello and welcome.", hazards=[]),
    dict(id=2, start=Fraction(2), end=Fraction(4), he="זה סרטון הדגמה קצר שנוצר מחומרים סינתטיים.", en="This is a short demo built from synthetic material.", hazards=[]),
    dict(id=3, start=Fraction(41, 10), end=Fraction(63, 10), he="המחיר: ₪1,990 בלבד, ו-50% הנחה לשבוע הראשון.", en="Price: ₪1,990 only, with 50% off the first week.",
         hazards=["currency_symbol_with_thousands_comma", "percent_after_digits", "hebrew_prefix_hyphen_before_digits"]),
    dict(id=4, start=Fraction(32, 5), end=Fraction(76, 10), he="הרשמה באתר או ב-WhatsApp, עם Wi-Fi חינם.", en="Sign up on the site or on WhatsApp. Free Wi-Fi.",
         hazards=["hebrew_prefix_hyphen_before_latin_word", "latin_word_with_hyphen_inside_hebrew"]),
]

PALETTE = {"background_dark": "#14213d", "background_accent": "#3a0ca3", "highlight": "#ff6b35", "text_light": "#ffffff", "note": "synthetic palette, owned"}


def _srt_time(t: Fraction) -> str:
    ms = round(t * 1000)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def _frame_snap(t: Fraction) -> Fraction:
    return Fraction(round(t * FPS), 1) / FPS


def _frac_text(t: Fraction) -> str:
    return str(t.numerator) if t.denominator == 1 else f"{t.numerator}/{t.denominator}"


def texts() -> dict[str, str]:
    """All text assets as ``{filename: content}`` (deterministic; hashes are strict in the manifest)."""
    out: dict[str, str] = {}
    out["script.he.txt"] = "\n".join(line["he"] for line in LINES) + "\n"
    out["script.en.txt"] = "\n".join(line["en"] for line in LINES) + "\n"
    for lang in ("he", "en"):
        blocks = [f"{i}\n{_srt_time(l['start'])} --> {_srt_time(l['end'])}\n{l[lang]}\n" for i, l in enumerate(LINES, 1)]
        out[f"captions.{lang}.srt"] = "\n".join(blocks)
    cues: dict[str, Any] = {"schema": "avc.cues/1", "fps": "30", "timing": "synthetic: words share the line's frame-aligned span in proportion to character count; NOT ASR output", "lines": []}
    for lang in ("he", "en"):
        for line in LINES:
            words = line[lang].split()
            total = sum(len(w) for w in words)
            span = line["end"] - line["start"]
            t = line["start"]
            entries = []
            for i, w in enumerate(words):
                end = line["end"] if i == len(words) - 1 else max(_frame_snap(t + span * Fraction(len(w), total)), t + Fraction(2) / FPS)
                entries.append({"text": w, "start": _frac_text(t), "end": _frac_text(end)})
                t = end
            cues["lines"].append({"id": line["id"], "lang": lang, "start": _frac_text(line["start"]), "end": _frac_text(line["end"]), "text": line[lang], "words": entries})
    out["cues.json"] = json.dumps(cues, ensure_ascii=False, indent=2) + "\n"
    brief = {"schema": "avc.sample-brief/1", "title_he": SLUG_TITLE_HE, "title_en": SLUG_TITLE_EN, "aspect": "9:16", "size": [1080, 1920], "fps": "30", "duration_s": 8,
             "languages": ["he", "en"], "palette": PALETTE, "audio_note": "speaker stand-in carries a non-speech tone; use a real consented recording for ASR work"}
    out["brief.json"] = json.dumps(brief, ensure_ascii=False, indent=2) + "\n"
    return out


# --------------------------------------------------------------------------------------------------------------------
# media
# --------------------------------------------------------------------------------------------------------------------

_VOICE = "0.25*sin(2*PI*150*t)*(0.55+0.45*sin(2*PI*3.2*t))*between(mod(t,2.1),0,1.6)"
_PAD = "0.12*(sin(2*PI*220*t)+sin(2*PI*261.63*t)+sin(2*PI*329.63*t))*min(1,t/0.5)*min(1,(8-t)/0.8)"


def _speaker(out: Path, ffmpeg: str | None) -> Path:
    path = out / "speaker_standin_1080x1920.mp4"
    # order: shoulders must sit BELOW the head, so draw them on the background first
    graph = (
        "[0:v]drawbox=x=300:y=1250:w=480:h=670:color=0x1f2a44:t=fill[bg];"
        "[bg][1:v]overlay=x='330+30*sin(2*PI*t/3)':y=720:shortest=1,format=yuv420p[v]"
    )
    e04.ffmpeg_run(
        [
            "-f", "lavfi", "-i", "gradients=s=1080x1920:r=30:d=8:c0=0x14213d:c1=0x3a0ca3:x0=0:y0=0:x1=1080:y1=1920:speed=0.005:seed=7",
            "-f", "lavfi", "-i", "color=c=black@0.0:s=420x420:r=30:d=8,format=yuva420p,geq=lum='215':cb='128':cr='128':a='if(lt(hypot(X-210,Y-210),200),255,0)'",
            "-f", "lavfi", "-i", f"aevalsrc='{_VOICE}':s=48000:d=8",
            "-filter_complex", graph, "-map", "[v]", "-map", "2:a:0", "-frames:v", "240",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-g", "30",
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(path),
        ],
        ffmpeg=ffmpeg,
        timeout=300,
    )
    return path


def _broll(out: Path, ffmpeg: str | None) -> Path:
    path = out / "broll_abstract_1080x1920.mp4"
    e04.ffmpeg_run(
        ["-f", "lavfi", "-i", "gradients=s=1080x1920:r=30:d=4:c0=0xff6b35:c1=0x004e89:type=spiral:speed=0.02:seed=11",
         "-frames:v", "120", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-g", "30", "-movflags", "+faststart", str(path)],
        ffmpeg=ffmpeg,
        timeout=300,
    )
    return path


def _music(out: Path, ffmpeg: str | None) -> Path:
    path = out / "music_bed.wav"
    e04.ffmpeg_run(["-f", "lavfi", "-i", f"aevalsrc='{_PAD}|{_PAD}':s=48000:d=8", "-c:a", "pcm_s16le", str(path)], ffmpeg=ffmpeg)
    return path


def _logo(out: Path, ffmpeg: str | None) -> Path:
    path = out / "logo_mark.png"
    e04.ffmpeg_run(
        ["-f", "lavfi", "-i", "color=c=black@0.0:s=512x512:r=1:d=1,format=rgba,drawbox=x=96:y=96:w=320:h=320:color=0xff6b35:t=fill,drawbox=x=176:y=176:w=160:h=160:color=0xffffff:t=fill",
         "-frames:v", "1", str(path)],
        ffmpeg=ffmpeg,
    )
    return path


def build_sample(out_root: Path, *, ffmpeg: str | None = None) -> list[dict[str, Any]]:
    """Generate the sample project under ``out_root/projects/sample-he-en`` and return manifest records."""
    slug = SAMPLE_SLUG
    proj = out_root / "projects" / slug
    src = proj / "source"
    src.mkdir(parents=True, exist_ok=True)
    write_json_atomic(proj / "project.json", {"schema": "avc.project/1", "slug": slug, "title": SLUG_TITLE_HE, "title_en": SLUG_TITLE_EN, "note": "sample project, owned synthetic assets"})
    records: list[dict[str, Any]] = []

    def rec(path: Path, kind: str, params: dict[str, Any], labels: dict[str, Any], recipe: str) -> None:
        records.append(
            {
                "id": f"sample_{path.stem}" if path.suffix not in (".srt",) else f"sample_{path.stem}_srt",
                "group": "sample-project",
                "kind": kind,
                "filename": f"projects/{slug}/source/{path.name}",
                "path": str(path),
                "creator": "fixtures/generators/make_sample_project.py v" + e04.GENERATOR_VERSION,
                "rights": e04._RIGHTS,
                "params": params,
                "labels": labels,
                "recipe": recipe,
                "content_sha256": e04.content_sha256(path, "text" if kind in ("text", "image") else kind, ffmpeg=ffmpeg),
                "hash_kind": "bytes (deterministic)" if kind in ("text", "image") else e04.HASH_KIND_MEDIA,
            }
        )

    sp = _speaker(src, ffmpeg)
    rec(sp, "av", {"width": 1080, "height": 1920, "fps": "30", "frames": 240, "duration_s": "8", "codec": "h264+aac"},
        {"defects": [], "intent": ["speaker_stand_in"], "ground_truth": {"asr_testable": False, "reason": "audio is a modulated tone, not speech"}}, "gradients + geq circle sprite + aevalsrc tone")
    br = _broll(src, ffmpeg)
    rec(br, "video", {"width": 1080, "height": 1920, "fps": "30", "frames": 120, "duration_s": "4", "codec": "h264"}, {"defects": [], "intent": ["b_roll"], "ground_truth": {}}, "gradients spiral")
    mu = _music(src, ffmpeg)
    rec(mu, "audio", {"sample_rate": 48000, "channels": 2, "duration_s": "8", "codec": "pcm_s16le"}, {"defects": [], "intent": ["music_bed"], "ground_truth": {}}, "aevalsrc A-minor triad with fades")
    lg = _logo(src, ffmpeg)
    rec(lg, "image", {"width": 512, "height": 512, "codec": "png", "pix_fmt": "rgba"}, {"defects": [], "intent": ["logo"], "ground_truth": {}}, "color + drawbox")
    hazards = {l["id"]: l["hazards"] for l in LINES}
    for name, content in texts().items():
        p = src / name
        write_text_atomic(p, content)
        labels: dict[str, Any] = {"defects": [], "intent": ["script"] if name.startswith("script") else ["captions"] if name.endswith(".srt") else ["metadata"], "ground_truth": {}}
        if name.endswith((".srt", ".txt")) or name == "cues.json":
            labels["ground_truth"] = {"bidi_hazards_by_line": hazards, "line_count": len(LINES)}
        rec(p, "text", {"encoding": "utf-8", "bom": False, "newline": "\\n"}, labels, "deterministic table in make_sample_project.py")
    return records


# --------------------------------------------------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------------------------------------------------


def manifest_document(e04_records: list[dict[str, Any]], sample_records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "avc.fixture-manifest/1",
        "generated_by": ["fixtures/generators/make_e04_set.py", "fixtures/generators/make_sample_project.py"],
        "generator_version": e04.GENERATOR_VERSION,
        "recorded_with": {"ffmpeg": ffmpeg_version(), "platform": platform.platform(), "python": platform.python_version(), "note": "measured on the generating machine only; hashes of encoded/decoded media may differ on other FFmpeg builds"},
        "rights_policy": e04._RIGHTS,
        "media_in_git": False,
        "media_location": "fixtures/_generated/ (git-ignored by the repository's .gitignore; tests generate into a temp directory)",
        "fonts": {
            "bundled": [],
            "used_by_generators": [],
            "policy": "no font file is bundled or used by the generators; caption rendering fonts must come from the documented OFL fetch step or from the system fallbacks below",
            "fetch_step": "fixtures/generators/fetch_ofl_fonts.py (pins a google/fonts git commit, records URL + sha256 + OFL text; NOT run in tests, needs network)",
            "candidate_fonts": [{"family": "Heebo", "licence": "SIL OFL 1.1", "scripts": ["Hebrew", "Latin"]}, {"family": "Assistant", "licence": "SIL OFL 1.1", "scripts": ["Hebrew", "Latin"]}],
            "fallbacks": ["Pillow default font (Latin only: Hebrew will show as missing glyphs)", "DejaVu Sans (system package, Hebrew-capable, licence verified by the user's OS package)", "Arial / Segoe UI on Windows (system fonts: use for local checks only, never redistribute)"],
        },
        "items": [*e04_records, *sample_records],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(_HERE.parent / "_generated" / "sample-project"))
    args = ap.parse_args(argv)
    try:
        recs = build_sample(Path(args.out))
    except ToolkitError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    for r in recs:
        print(f"{r['id']:<34} sha256={r['content_sha256'][:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

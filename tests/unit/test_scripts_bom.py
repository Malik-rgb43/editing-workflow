"""Positive and negative controls for scripts/gen_bom.py (bill of materials + blocked-component gate)."""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import _avc_common as C  # noqa: E402
import _avc_fixtures as F  # noqa: E402
import gen_bom  # noqa: E402

CLI = SCRIPTS / "gen_bom.py"

ALLOW_ALL = '''
[[rule]]
glob = "**"
origin = "owner"
licence = "owner-undecided"
allow = ["video", "audio", "image", "font", "weights", "archive", "executable"]
'''


@pytest.fixture()
def root(tmp_path):
    path = tmp_path / "מאגר" / "repo"
    F.write(path / "README.md", "# repo\n")
    F.write(path / "tools" / "a.py", "print(1)\n")
    return path


def licences(root, body):
    F.write(root / "licenses.toml", "schema = 1\n" + body)


def build(root, **kw):
    return gen_bom.build(root, root / "licenses.toml", use_git=False, **kw)


def flags(bom, path):
    return next(e for e in bom["files"] if e["path"] == path)["flags"]


# ------------------------------------------------------------------ positive controls


def test_clean_tree_passes_and_records_hashes_and_origin(root):
    licences(root, ALLOW_ALL)
    bom, report = build(root)
    assert report.fails == [] and bom["status"] == "PASS"
    entry = next(e for e in bom["files"] if e["path"] == "README.md")
    assert entry["sha256"] == C.sha256_file(root / "README.md") and entry["size"] == (root / "README.md").stat().st_size
    assert entry["origin"] == "owner" and entry["licence"] == "owner-undecided" and entry["flags"] == []
    assert bom["by_origin"] == {"owner": 3} or bom["by_origin"]["owner"] >= 2


def test_third_party_with_source_and_permissive_licence_is_clean(root):
    licences(
        root,
        ALLOW_ALL
        + '\n[[rule]]\nglob = "vendor/lib.js"\norigin = "third_party"\nlicence = "MIT"\nsource = "https://example.org/lib"\n',
    )
    F.write(root / "vendor" / "lib.js", "// lib\n")
    bom, report = build(root)
    assert report.fails == []
    assert next(e for e in bom["files"] if e["path"] == "vendor/lib.js")["origin"] == "third_party"


def test_last_matching_rule_wins(root):
    licences(
        root,
        ALLOW_ALL + '\n[[rule]]\nglob = "tools/**"\norigin = "generated"\nlicence = "generated-lockfile"\n',
    )
    bom, _ = build(root)
    entry = next(e for e in bom["files"] if e["path"] == "tools/a.py")
    assert entry["origin"] == "generated" and entry["licence"] == "generated-lockfile"


def test_bom_is_deterministic_and_excludes_its_own_outputs(root):
    licences(root, ALLOW_ALL)
    first, _ = build(root)
    F.write(root / "docs" / "BOM.json", "{}")
    F.write(root / "docs" / "BOM.md", "x")
    second, _ = build(root)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert all(not e["path"].startswith("docs/BOM") for e in second["files"])


# ------------------------------------------------------------------ negative controls: blocked components

BLOCKED = [
    ("assets/mixkit-whoosh-123.wav", "mixkit"),
    ("assets/ElevenLabs_Music_track.mp3", "elevenlabs"),
    ("assets/eleven-music-bed.wav", "elevenlabs"),
    ("assets/artlist_broll.mp4", "artlist"),
    ("assets/suno_song.mp3", "suno"),
    ("fonts/AdobeClean-Regular.otf", "adobe-font"),
    ("fonts/SF-Pro-Display.ttf", "apple-font"),
    ("fonts/SanFrancisco.otf", "apple-font"),
    ("bin/ffmpeg.exe", "ffmpeg-binary"),
    ("bin/ffprobe", "ffmpeg-binary"),
    ("bin/avcodec-61.dll", "ffmpeg-binary"),
    ("models/ivrit-whisper-large-v3-turbo.onnx", "ivrit-ai"),
    ("models/depth_anything_v2_vitl.pth", "depth-anything-nc"),
    ("models/Depth-Anything-V2-Base/model.safetensors", "depth-anything-nc"),
    ("models/hunyuan3d-2.1/shape.bin", "hunyuan3d"),
    ("models/rvm_mobilenetv3_fp32.pth", "rvm-gpl"),
    ("models/robust_video_matting.onnx", "rvm-gpl"),
    ("models/yolov8n.pt", "ultralytics"),
    ("vendor/ultralytics/engine.py", "ultralytics-code"),
    ("third_party/RobustVideoMatting/model/model.py", "rvm-gpl-code"),
    ("third_party/Hunyuan3D-2.1/hy3dshape/x.py", "hunyuan3d-code"),
    ("models/sdxl-turbo/unet.safetensors", "sdxl-turbo"),
    ("knowledge" + "-pack/transcript.txt", "private-material"),
    ("brain" + "/Clients/acme/notes.md", "private-material"),
]


@pytest.mark.parametrize("path,rule", BLOCKED)
def test_blocked_components_fail_even_when_a_rule_allows_the_class(root, path, rule):
    licences(root, ALLOW_ALL)
    F.write(root / path, "x")
    bom, report = build(root)
    assert bom["status"] == "FAIL" and report.status == C.FAIL
    assert any(f.startswith(f"blocked: {rule}") for f in flags(bom, path)), flags(bom, path)


@pytest.mark.parametrize(
    "path",
    [
        "assets/ding.wav",  # harmless owned-style audio with an explicit allow
        "models/depth_anything_v2_vits.pth",  # Small (Apache-2.0) is allowed
        "models/Depth-Anything-V2-Small/model.safetensors",
        "fonts/NotoSansHebrew-Regular.ttf",
        "docs/diagram.png",
        "src/ffmpeg_helpers.py",  # a source file that merely mentions ffmpeg is not a binary
        "docs/rvm-notes.md",  # prose about a component is fine; only its weights/binaries/vendored folders are blocked
        "docs/mixkit-licence-notes.md",
        "docs/hunyuan3d-routes.md",
        "src/yolo_utils_v8.py",
    ],
)
def test_negative_controls_are_not_blocked(root, path):
    licences(root, ALLOW_ALL)
    F.write(root / path, "x")
    bom, _ = build(root)
    assert flags(bom, path) == [], flags(bom, path)


def test_unknown_when_no_rule_covers_a_file(root):
    licences(root, '[[rule]]\nglob = "README.md"\norigin = "owner"\nlicence = "owner-undecided"\n')
    bom, report = build(root)
    assert any("unknown" in f for f in flags(bom, "tools/a.py"))
    unknown = {e["path"] for e in bom["files"] if any(f.startswith("unknown") for f in e["flags"])}
    assert report.status == C.FAIL and unknown == {"tools/a.py", "licenses.toml"}


def test_restricted_classes_need_an_explicit_allow(root):
    licences(root, '[[rule]]\nglob = "**"\norigin = "owner"\nlicence = "owner-undecided"\n')  # no allow list
    for name in ("clip.mp4", "voice.wav", "photo.png", "face.ttf", "w.onnx", "pack.zip", "tool.exe"):
        F.write(root / "media" / name, "x")
    (root / "media" / "mystery.dat").write_bytes(b"\0\1\2\3")
    bom, report = build(root)
    unknown = {e["path"] for e in bom["files"] if any(f.startswith("unknown") for f in e["flags"])}
    assert unknown == {f"media/{n}" for n in ("clip.mp4", "voice.wav", "photo.png", "face.ttf", "w.onnx", "pack.zip", "tool.exe", "mystery.dat")}
    assert report.status == C.FAIL


@pytest.mark.parametrize(
    "licence,kind",
    [("unknown", "unknown"), ("CC-BY-NC-4.0", "non-commercial"), ("GPL-3.0-only", "copyleft-review"), ("AGPL-3.0", "copyleft-review"),
     ("Proprietary", "proprietary"), ("Stability-Community", "community-licence"), ("", "unknown")],
)
def test_unacceptable_declared_licences_block(root, licence, kind):
    licences(root, ALLOW_ALL + f'\n[[rule]]\nglob = "vendor/**"\norigin = "third_party"\nlicence = "{licence}"\nsource = "https://example.org"\n')
    F.write(root / "vendor" / "thing.js", "x")
    bom, report = build(root)
    assert any(f.startswith(f"blocked: licence-{kind}") for f in flags(bom, "vendor/thing.js")), flags(bom, "vendor/thing.js")
    assert report.status == C.FAIL


@pytest.mark.parametrize("licence", ["MIT", "Apache-2.0", "OFL-1.1", "CC0-1.0", "LGPL-2.1-or-later", "BSD-3-Clause"])
def test_acceptable_licences_do_not_block(root, licence):
    licences(root, ALLOW_ALL + f'\n[[rule]]\nglob = "vendor/**"\norigin = "third_party"\nlicence = "{licence}"\nsource = "https://example.org"\n')
    F.write(root / "vendor" / "thing.js", "x")
    bom, _ = build(root)
    assert flags(bom, "vendor/thing.js") == []


def test_third_party_without_source_blocks(root):
    licences(root, ALLOW_ALL + '\n[[rule]]\nglob = "vendor/**"\norigin = "third_party"\nlicence = "MIT"\n')
    F.write(root / "vendor" / "thing.js", "x")
    bom, _ = build(root)
    assert any("without a source" in f for f in flags(bom, "vendor/thing.js"))


# ------------------------------------------------------------------ licenses.toml problems


@pytest.mark.parametrize(
    "body",
    [
        "[[rule]]\norigin = \"owner\"\nlicence = \"x\"\n",  # no glob
        '[[rule]]\nglob = "**"\norigin = "mine"\nlicence = "x"\n',  # bad origin
        '[[rule]]\nglob = "**"\norigin = "owner"\nlicence = 5\n',  # licence not a string
        '[[rule]]\nglob = "**"\norigin = "owner"\nlicence = "x"\nallow = ["pictures"]\n',  # bad class
        "this is = not toml [",
    ],
)
def test_invalid_licenses_toml_fails_closed(root, body):
    licences(root, body)
    bom, report = build(root)
    assert "licenses-config" in {f.code for f in report.fails}
    assert bom["status"] == "FAIL"  # every file is unknown when the config is unusable


def test_missing_licenses_toml_fails_closed(root):
    bom, report = gen_bom.build(root, root / "licenses.toml", use_git=False)
    assert report.status == C.FAIL and bom["unknown_count"] == bom["file_count"] > 0


# ------------------------------------------------------------------ register reconciliation


def write_register(path, rows):
    fields = ["item", "kind", "review_status", "blocking_unknown", "register_id"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def third_party_rule(register_id):
    return (
        ALLOW_ALL
        + f'\n[[rule]]\nglob = "vendor/**"\norigin = "third_party"\nlicence = "MIT"\nsource = "https://example.org"\nregister_id = "{register_id}"\n'
    )


def test_register_cleared_row_passes(root, tmp_path):
    licences(root, third_party_rule("R-1"))
    F.write(root / "vendor" / "x.js", "x")
    reg = tmp_path / "reg.csv"
    write_register(reg, [{"item": "x", "review_status": "cleared", "register_id": "R-1"}])
    bom, report = build(root, register_path=reg)
    assert report.fails == [] and bom["register"]["checked"] is True and bom["register"]["referenced_by_tree"] == 1


@pytest.mark.parametrize(
    "row,expected",
    [
        ({"item": "x", "review_status": "inherited_lead", "register_id": "R-1"}, "not cleared"),
        ({"item": "x", "review_status": "cleared", "blocking_unknown": "exact scope", "register_id": "R-1"}, "blocking unknown"),
        ({"item": "x", "review_status": "cleared", "register_id": "R-2"}, "not found in the register"),
    ],
)
def test_register_problems_block(root, tmp_path, row, expected):
    licences(root, third_party_rule("R-1"))
    F.write(root / "vendor" / "x.js", "x")
    reg = tmp_path / "reg.csv"
    write_register(reg, [row])
    bom, report = build(root, register_path=reg)
    assert report.status == C.FAIL and any(expected in f for f in flags(bom, "vendor/x.js")), flags(bom, "vendor/x.js")


def test_register_requires_register_id_for_third_party_and_valid_schema(root, tmp_path):
    licences(root, ALLOW_ALL + '\n[[rule]]\nglob = "vendor/**"\norigin = "third_party"\nlicence = "MIT"\nsource = "https://example.org"\n')
    F.write(root / "vendor" / "x.js", "x")
    reg = tmp_path / "reg.csv"
    write_register(reg, [])
    bom, report = build(root, register_path=reg)
    assert any("no register_id" in f for f in flags(bom, "vendor/x.js"))
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2\n", encoding="utf-8")
    _, report2 = build(root, register_path=bad)
    assert "register" in {f.code for f in report2.fails}
    _, report3 = build(root, register_path=tmp_path / "missing.csv")
    assert "register" in {f.code for f in report3.fails}


def test_register_not_supplied_is_reported_not_silent(root):
    licences(root, ALLOW_ALL)
    bom, report = build(root)
    assert bom["register"]["checked"] is False
    assert any(p["part"] == "register-reconciliation" for p in report.not_run_parts)


# ------------------------------------------------------------------ CLI, outputs, check mode, notices


def test_cli_writes_outputs_check_mode_and_exit_codes(root):
    licences(root, ALLOW_ALL)
    t = time.monotonic()
    assert F.run_cli(CLI, "--help").returncode == 0 and time.monotonic() - t < 3
    done = F.run_cli(CLI, "--root", root, "--no-git")
    assert done.returncode == 0, done.stdout + done.stderr
    data = json.loads((root / "docs" / "BOM.json").read_text(encoding="utf-8"))
    assert data["status"] == "PASS" and data["file_count"] >= 3
    md = (root / "docs" / "BOM.md").read_text(encoding="utf-8")
    assert md.startswith("<!-- GENERATED") and "Status: **PASS**" in md
    assert F.run_cli(CLI, "--root", root, "--no-git", "--check").returncode == 0
    F.write(root / "new.md", "new file\n")
    stale = F.run_cli(CLI, "--root", root, "--no-git", "--check")
    assert stale.returncode == 1 and "bom-stale" in stale.stdout
    F.write(root / "assets" / "mixkit-x.wav", "x")
    blocked = F.run_cli(CLI, "--root", root, "--no-git")
    assert blocked.returncode == 1 and "bom-blocked" in blocked.stdout
    # the BOM is still written so the problem is visible, with status FAIL
    assert json.loads((root / "docs" / "BOM.json").read_text(encoding="utf-8"))["status"] == "FAIL"
    assert "mixkit" in (root / "docs" / "BOM.md").read_text(encoding="utf-8").lower()
    assert F.run_cli(CLI, "--root", root / "nope").returncode == 2


def test_cli_check_without_a_bom_fails_and_no_write_writes_nothing(root):
    licences(root, ALLOW_ALL)
    assert F.run_cli(CLI, "--root", root, "--no-git", "--check").returncode == 1
    assert F.run_cli(CLI, "--root", root, "--no-git", "--no-write").returncode == 0
    assert not (root / "docs").exists()


def test_update_notices_rewrites_only_the_generated_block(root):
    licences(root, ALLOW_ALL + '\n[[rule]]\nglob = "vendor/**"\norigin = "third_party"\nlicence = "MIT"\nsource = "https://example.org/lib"\n')
    F.write(root / "vendor" / "lib.js", "x")
    notices = (
        "# Notices\n\nhand written intro\n\n" + gen_bom.NOTICE_BEGIN + "\nOLD\n" + gen_bom.NOTICE_END + "\n\n## Hand section\nkeep me\n"
    )
    F.write(root / "THIRD_PARTY_NOTICES.md", notices)
    done = F.run_cli(CLI, "--root", root, "--no-git", "--update-notices")
    assert done.returncode == 0, done.stdout
    text = (root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "hand written intro" in text and "keep me" in text and "OLD" not in text
    assert "vendor/lib.js" in text and "MIT" in text and "https://example.org/lib" in text
    # markers missing -> refuse to touch the file
    F.write(root / "THIRD_PARTY_NOTICES.md", "# no markers\n")
    refused = F.run_cli(CLI, "--root", root, "--no-git", "--update-notices")
    assert refused.returncode == 1 and "notices-markers" in refused.stdout
    assert (root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8") == "# no markers\n"


def test_the_real_repository_licenses_toml_is_valid_and_has_no_blocked_rules():
    real = Path(__file__).resolve().parents[2] / "licenses.toml"
    rules = gen_bom.load_licenses(real)
    assert rules and all(r["origin"] in gen_bom.ORIGINS for r in rules)
    # nothing third-party is declared today (and therefore nothing needs a register row)
    assert [r for r in rules if r["origin"] == "third_party"] == []

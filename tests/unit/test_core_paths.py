"""paths.py: ASCII work root, forbidden roots, guarded delete, long paths, Hebrew/space/apostrophe/emoji folders, slugs."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from core import paths
from core.errors import ForbiddenRootError, PathSafetyError
from core.fsio import fs_path, read_json, read_text, write_json_atomic, write_text_atomic

TRICKY = "פרויקט אבג 'quote' 🎬 תיקייה"


# ------------------------------------------------------------------------------------------------ slugs
def test_slug_hebrew_is_ascii_stable_and_distinct():
    a = paths.slugify("סרטון תדמית - דוגמה 🎬")
    assert a.isascii() and a == paths.slugify("סרטון תדמית - דוגמה 🎬")
    assert a != paths.slugify("סרטון תדמית - דוגמה 🎥")  # emoji-only difference must not collide
    assert a.startswith("srtvn-tdmyt-dvgmh-")
    assert all(c.isalnum() or c == "-" for c in a)


def test_slug_plain_ascii_keeps_readable_name_without_hash():
    assert paths.slugify("My Video 01") == "my-video-01"
    assert paths.slugify("  Café déjà vu ") != "" and paths.slugify("Café").startswith("cafe")


@pytest.mark.parametrize("title", ["🎬🎬🎬", "'''", "   ", "ااا", "日本語"])
def test_slug_unslugable_titles_never_empty_and_never_collide(title):
    s = paths.slugify(title)
    assert s and s.isascii() and s.startswith("project-")
    assert s != paths.slugify(title + "x")


@pytest.mark.parametrize("name", ["con", "CON", "nul", "com1", "lpt9"])
def test_slug_windows_reserved_names_are_prefixed(name):
    assert paths.slugify(name).startswith("p-")


def test_slug_length_is_bounded():
    assert len(paths.slugify("a" * 500)) <= 40


# ------------------------------------------------------------------------------------------------ forbidden roots
def test_drive_root_home_and_system_are_forbidden():
    root = Path(os.path.abspath(os.sep))
    assert paths.forbidden_reason(root)
    assert paths.forbidden_reason(Path.home())
    assert paths.forbidden_reason(Path.home().parent)  # parent of home (C:\Users)
    assert paths.forbidden_reason(Path.home() / "Desktop")
    if os.name == "nt":
        assert paths.forbidden_reason(os.environ.get("SystemRoot", r"C:\Windows"))
        assert paths.forbidden_reason(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32")
        assert paths.forbidden_reason(os.environ.get("ProgramFiles", r"C:\Program Files"))
        assert paths.forbidden_reason("C:/")
        assert paths.forbidden_reason("c:\\")
    else:
        assert paths.forbidden_reason("/usr/bin")
        assert paths.forbidden_reason("/etc")


def test_subfolders_of_home_and_temp_are_allowed(tmp_path):
    assert paths.forbidden_reason(tmp_path) is None
    assert paths.forbidden_reason(Path.home() / "avc-work-test-not-created") is None


def test_assert_not_forbidden_raises_with_fix_text():
    with pytest.raises(ForbiddenRootError) as e:
        paths.assert_not_forbidden(Path.home(), purpose="use as work root")
    assert "dedicated sub-folder" in str(e.value)


# ------------------------------------------------------------------------------------------------ work root
def test_work_root_must_be_ascii(tmp_path):
    ok = paths.resolve_work_root(tmp_path / "avc-work")
    assert ok.name == "avc-work"
    with pytest.raises(PathSafetyError) as e:
        paths.resolve_work_root(tmp_path / "עבודה")
    assert "ASCII" in str(e.value) and "HyperFrames" in str(e.value)
    # an explicit opt-in exists for tools that do not run HyperFrames
    assert paths.resolve_work_root(tmp_path / "עבודה", allow_non_ascii=True).name == "עבודה"


@pytest.mark.parametrize("raw", ["", "   "])
def test_work_root_empty_is_rejected(raw):
    with pytest.raises(PathSafetyError):
        paths.resolve_work_root(raw)


def test_work_root_rejects_drive_root_and_home():
    with pytest.raises(ForbiddenRootError):
        paths.resolve_work_root(os.path.abspath(os.sep))
    with pytest.raises(ForbiddenRootError):
        paths.resolve_work_root(Path.home())


@pytest.mark.skipif(os.name != "nt", reason="Windows-only name rules")
@pytest.mark.parametrize("bad", ["work ", "work.", "nul", "a|b"])
def test_work_root_rejects_windows_hazard_names(tmp_path, bad):
    with pytest.raises(PathSafetyError):
        paths.resolve_work_root(str(tmp_path) + os.sep + bad)


def test_work_root_that_is_a_file_is_rejected(tmp_path):
    f = tmp_path / "afile"
    f.write_text("x")
    with pytest.raises(PathSafetyError):
        paths.resolve_work_root(f)


# ------------------------------------------------------------------------------------------------ guarded delete
@pytest.fixture()
def managed(tmp_path):
    root = paths.ensure_managed_root(tmp_path / "avc-work")
    (root / "projects" / "p1" / "_work").mkdir(parents=True)
    (root / "projects" / "p1" / "_work" / "a.txt").write_text("a")
    return root


def test_safe_rmtree_deletes_inside_managed_root(managed):
    target = managed / "projects" / "p1" / "_work"
    r = paths.safe_rmtree(target, allowed_root=managed, dry_run=True)
    assert r["files"] == 1 and target.exists()
    paths.safe_rmtree(target, allowed_root=managed)
    assert not target.exists() and (managed / paths.MARKER_NAME).exists()


def test_safe_rmtree_refuses_the_root_itself(managed):
    with pytest.raises(PathSafetyError):
        paths.safe_rmtree(managed, allowed_root=managed)
    assert managed.exists()


def test_safe_rmtree_refuses_outside_target(managed, tmp_path):
    outside = tmp_path / "precious"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    with pytest.raises(PathSafetyError):
        paths.safe_rmtree(outside, allowed_root=managed)
    assert (outside / "keep.txt").exists()


def test_safe_rmtree_refuses_dotdot_escape(managed, tmp_path):
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "f").write_text("x")
    sneaky = managed / "projects" / ".." / ".." / ".." / "victim"
    with pytest.raises(PathSafetyError):
        paths.safe_rmtree(sneaky, allowed_root=managed)
    assert (victim / "f").exists()


def test_safe_rmtree_needs_marker_and_explicit_root(tmp_path):
    unmarked = tmp_path / "unmarked"
    (unmarked / "x").mkdir(parents=True)
    with pytest.raises(PathSafetyError) as e:
        paths.safe_rmtree(unmarked / "x", allowed_root=unmarked)
    assert paths.MARKER_NAME in str(e.value)
    with pytest.raises(PathSafetyError):
        paths.safe_rmtree(unmarked / "x", allowed_root="")
    assert (unmarked / "x").exists()


def test_safe_rmtree_refuses_forbidden_allowed_root():
    # a drive root / home can never be an allowed root, whatever marker it might carry
    with pytest.raises(ForbiddenRootError):
        paths.safe_rmtree(Path.home() / "x", allowed_root=Path.home())
    with pytest.raises(ForbiddenRootError):
        paths.safe_rmtree(Path(os.path.abspath(os.sep)) / "x", allowed_root=os.path.abspath(os.sep))


def test_safe_rmtree_refuses_current_directory(managed):
    target = managed / "projects" / "p1"
    old = os.getcwd()
    os.chdir(target)
    try:
        with pytest.raises(PathSafetyError):
            paths.safe_rmtree(target, allowed_root=managed)
    finally:
        os.chdir(old)
    assert target.exists()


def test_safe_rmtree_refuses_missing_and_non_directory(managed):
    with pytest.raises(PathSafetyError):
        paths.safe_rmtree(managed / "nope", allowed_root=managed)
    f = managed / "file.txt"
    f.write_text("x")
    with pytest.raises(PathSafetyError):
        paths.safe_rmtree(f, allowed_root=managed)


def _make_link(link: Path, target: Path) -> bool:
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":  # junction needs no privilege
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        return r.returncode == 0
    return False


def test_safe_rmtree_never_follows_links(managed, tmp_path):
    outside = tmp_path / "outside-data"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    link = managed / "projects" / "linkdir"
    if not _make_link(link, outside):
        pytest.skip("cannot create a symlink or junction on this machine")
    with pytest.raises(PathSafetyError):
        paths.safe_rmtree(link, allowed_root=managed)
    assert (outside / "keep.txt").exists()
    # a link INSIDE a deleted tree is removed as a link, the data behind it survives
    holder = managed / "projects" / "holder"
    holder.mkdir()
    inner = holder / "inner-link"
    assert _make_link(inner, outside)
    paths.safe_rmtree(holder, allowed_root=managed)
    assert (outside / "keep.txt").exists() and not holder.exists()


def test_safe_rmtree_removes_read_only_files(managed):
    target = managed / "projects" / "p1" / "_work"
    f = target / "ro.txt"
    f.write_text("x")
    os.chmod(f, 0o444)
    paths.safe_rmtree(target, allowed_root=managed)
    assert not target.exists()


# ------------------------------------------------------------------------------------------------ long paths
def test_fs_path_adds_extended_prefix_only_when_needed():
    short = fs_path("a/b")
    long = fs_path("x" * 300)
    if os.name == "nt":
        assert not short.startswith("\\\\?\\")
        assert long.startswith("\\\\?\\")
        assert fs_path("\\\\server\\share\\x" + "y" * 300).startswith("\\\\?\\UNC\\server\\share")
        assert fs_path(long) == long  # idempotent
        assert fs_path("c:/a/../b", force=True) == "\\\\?\\c:\\b"  # normalised before the prefix disables normalisation
    else:
        assert short == os.path.abspath("a/b")


def test_long_path_roundtrip(tmp_path):
    deep = tmp_path
    for i in range(14):
        deep = deep / ("segment-" + "x" * 20 + str(i))
    assert len(str(deep)) > 300
    os.makedirs(fs_path(deep))
    f = deep / "hello.txt"
    write_text_atomic(f, "שלום 🎬\n")
    assert read_text(f) == "שלום 🎬\n"
    root = paths.ensure_managed_root(tmp_path)  # tmp_path is deep inside the user's profile, not forbidden
    first = tmp_path / ("segment-" + "x" * 20 + "0")
    paths.safe_rmtree(first, allowed_root=root)
    assert not os.path.exists(fs_path(first))


# ------------------------------------------------------------------------------------------------ hostile folder names
def test_project_skeleton_in_a_hostile_named_work_root_is_refused_but_source_may_be_hostile(tmp_path):
    """Work root must be ASCII; a Hebrew/emoji folder is fine as a SOURCE location and for text I/O."""
    src = tmp_path / TRICKY
    src.mkdir()
    write_text_atomic(src / "brief ש'.txt", "שלום עולם 🎬\nline2\n")
    assert read_text(src / "brief ש'.txt") == "שלום עולם 🎬\nline2\n"
    with pytest.raises(PathSafetyError):
        paths.resolve_work_root(src)


def test_project_paths_model_with_hebrew_title(tmp_path):
    root = tmp_path / "avc-work"
    title = "סרטון תדמית 'מיוחד' 🎬"
    p = paths.project_paths(root, title)
    assert p.slug.isascii() and p.root == root / "projects" / p.slug
    assert p.source.name == "source" and p.hf.name == "hf" and p.final.name == "final" and p.work.name == "_work"
    p.ensure()
    for d in (p.source, p.hf, p.final, p.work):
        assert d.is_dir()
    meta = read_json(p.meta_file)
    assert meta["title"] == title and meta["slug"] == p.slug and meta["schema"] == paths.PROJECT_SCHEMA
    raw = p.meta_file.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw  # UTF-8, no BOM, LF
    assert "סרטון".encode("utf-8") in raw  # real Hebrew on disk, not \\u escapes
    assert p.title_from_disk() == title
    p.ensure()  # idempotent, does not rewrite metadata
    (p.work / "scratch.txt").write_text("x")
    res = p.clean_work()
    assert res["files"] == 1 and not p.work.exists() and p.source.exists()


def test_project_paths_custom_folder_names_and_validation(tmp_path):
    p = paths.project_paths(tmp_path / "avc-work", "x", folders={"final": "deliver", "work": "scratch"})
    assert p.final.name == "deliver" and p.work.name == "scratch"
    with pytest.raises(PathSafetyError):
        paths.project_paths(tmp_path / "avc-work", "x", folders={"final": "../evil"})
    with pytest.raises(PathSafetyError):
        paths.project_paths(tmp_path / "avc-work", "x", folders={"final": "מוכן"})
    with pytest.raises(PathSafetyError):
        paths.project_paths(tmp_path / "avc-work", "x", slug="Bad Slug")


# ------------------------------------------------------------------------------------------------ fsio
def test_atomic_write_roundtrip_and_no_leftovers(tricky_dir):
    target = tricky_dir / "data.json"
    write_json_atomic(target, {"כותרת": "שלום 🎬", "n": 1})
    assert read_json(target) == {"כותרת": "שלום 🎬", "n": 1}
    assert [p.name for p in tricky_dir.iterdir()] == ["data.json"]  # temp file cleaned up
    write_text_atomic(target, "a\r\nb\r\n")
    assert target.read_bytes() == b"a\nb\n"


def test_read_text_tolerates_bom_but_write_never_adds_one(tricky_dir):
    f = tricky_dir / "bom.txt"
    f.write_bytes(b"\xef\xbb\xbf" + "שלום".encode("utf-8"))
    assert read_text(f) == "שלום"


def test_append_line_rejects_embedded_newlines(tricky_dir):
    from core.fsio import append_line

    append_line(tricky_dir / "l.jsonl", '{"a":"ש"}')
    with pytest.raises(ValueError):
        append_line(tricky_dir / "l.jsonl", "two\nlines")
    assert (tricky_dir / "l.jsonl").read_bytes() == '{"a":"ש"}\n'.encode("utf-8")


def test_cli_paths_check_and_slug():
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"), "PYTHONUTF8": "1"}
    r = subprocess.run([sys.executable, "-m", "core", "slug", "סרטון 🎬"], capture_output=True, env=env, timeout=60)
    assert r.returncode == 0 and r.stdout.decode("utf-8").strip().startswith("srtvn-")
    r = subprocess.run([sys.executable, "-m", "core", "paths", "check", os.path.abspath(os.sep)], capture_output=True, env=env, timeout=60)
    assert r.returncode == 1 and b"FORBIDDEN" in r.stdout

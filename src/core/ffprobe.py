"""Locate FFmpeg/ffprobe and read media facts through ffprobe's **JSON** output (never regex over prose).

* ``find_ffmpeg`` / ``find_ffprobe`` - configured path (``toolkit.toml [binaries]``) or PATH; a missing tool raises
  ``MediaToolMissing`` with per-OS install text and the exact check command.
* ``probe`` - ``MediaInfo`` with rational frame rates (``Fraction``), time base, declared frame count, rotation, audio.
* ``expected_frames`` - the container-level frame count a decoder must match (declared ``nb_frames``, else the packet
  count): the *expected* side of a QA envelope's coverage.  ``count_decoded_frames`` is the slow, decode-everything
  variant used when the container is unreliable.

Failure policy: ffprobe missing / non-zero exit / invalid JSON / no video stream where one was required -> an exception
(``ProbeError``). Never an empty result that a caller could mistake for "nothing wrong".

Usage:
    python -m core probe <media-file>
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from .errors import MediaToolMissing, ProbeError
from .fsio import fs_path
from .procs import run
from .timebase import parse_rate

__all__ = [
    "install_hint",
    "find_tool",
    "find_ffmpeg",
    "find_ffprobe",
    "ffmpeg_version",
    "VideoStream",
    "AudioStream",
    "MediaInfo",
    "probe",
    "expected_frames",
    "count_decoded_frames",
    "packet_pts",
]

_PROBE_TIMEOUT_S = 60.0


def install_hint() -> str:
    if os.name == "nt":
        return "install FFmpeg (includes ffprobe), e.g.  winget install Gyan.FFmpeg  -  then open a NEW terminal and check:  ffmpeg -version  &&  ffprobe -version"
    if sys.platform == "darwin":
        return "install FFmpeg, e.g.  brew install ffmpeg  -  then check:  ffmpeg -version && ffprobe -version"
    return "install FFmpeg with your package manager, e.g.  sudo apt install ffmpeg  -  then check:  ffmpeg -version && ffprobe -version"


def find_tool(name: str, configured: str | None = None) -> str:
    """Resolve an executable: ``configured`` (a path or a command name) first, else PATH."""
    candidates = [configured] if configured else []
    candidates.append(name)
    for cand in candidates:
        if not cand:
            continue
        if os.path.isabs(cand) or any(sep in cand for sep in ("/", "\\")):
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            continue
        found = shutil.which(cand)
        if found:
            return found
    where = f"configured as {configured!r} and " if configured else ""
    raise MediaToolMissing(f"{name} was {where}not found on PATH", remediation=install_hint())


def find_ffmpeg(configured: str | None = None) -> str:
    return find_tool("ffmpeg", configured)


def find_ffprobe(configured: str | None = None) -> str:
    return find_tool("ffprobe", configured)


def ffmpeg_version(configured: str | None = None) -> str:
    """First line of ``ffmpeg -version`` (informational, recorded in manifests; not parsed for logic)."""
    r = run([find_ffmpeg(configured), "-hide_banner", "-version"], timeout=20)
    if not r.ok:
        raise ProbeError(f"ffmpeg -version failed (exit {r.returncode})", remediation=install_hint())
    return (r.stdout.splitlines() or [""])[0].strip()


@dataclass(frozen=True)
class VideoStream:
    index: int
    codec: str
    width: int
    height: int
    pix_fmt: str | None
    r_frame_rate: Fraction | None
    avg_frame_rate: Fraction | None
    time_base: Fraction | None
    declared_frames: int | None
    duration_s: Fraction | None
    rotation: int
    sample_aspect_ratio: str | None
    start_time_s: Fraction | None

    @property
    def fps(self) -> Fraction | None:
        """Nominal constant rate: ``r_frame_rate`` (the lowest rate that represents every timestamp), else average."""
        return self.r_frame_rate or self.avg_frame_rate

    @property
    def is_vfr(self) -> bool:
        """Heuristic: nominal and average rates differ by more than 0.5 %."""
        a, b = self.r_frame_rate, self.avg_frame_rate
        if not a or not b:
            return False
        return abs(a - b) / a > Fraction(1, 200)

    @property
    def display_size(self) -> tuple[int, int]:
        """(width, height) as decoded **after** auto-rotation (what ffmpeg emits by default)."""
        return (self.height, self.width) if abs(self.rotation) % 180 == 90 else (self.width, self.height)


@dataclass(frozen=True)
class AudioStream:
    index: int
    codec: str
    sample_rate: int | None
    channels: int | None
    duration_s: Fraction | None


@dataclass(frozen=True)
class MediaInfo:
    path: str
    format_name: str | None
    duration_s: Fraction | None
    size_bytes: int | None
    video: tuple[VideoStream, ...]
    audio: tuple[AudioStream, ...]
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def first_video(self) -> VideoStream:
        if not self.video:
            raise ProbeError(f"{self.path!r} has no video stream")
        return self.video[0]


def _frac(text: Any) -> Fraction | None:
    if text in (None, "", "N/A"):
        return None
    try:
        return Fraction(str(text))
    except (ValueError, ZeroDivisionError):
        return None


def _rate(text: Any) -> Fraction | None:
    if text in (None, "", "N/A", "0/0"):
        return None
    try:
        return parse_rate(str(text))
    except Exception:  # noqa: BLE001 - a bad rate is "unknown", the caller decides whether that is fatal
        return None


def _int(text: Any) -> int | None:
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _rotation(stream: dict[str, Any]) -> int:
    tags = stream.get("tags") or {}
    rot = _int(tags.get("rotate"))
    if rot is not None:
        return rot % 360
    for sd in stream.get("side_data_list") or []:
        r = sd.get("rotation")
        if r is not None:
            try:
                return int(round(float(r))) % 360
            except (TypeError, ValueError):
                continue
    return 0


def _ffprobe_json(args: list[str], path: str, *, configured: str | None = None, timeout: float = _PROBE_TIMEOUT_S) -> dict[str, Any]:
    exe = find_ffprobe(configured)
    # "-i <path>" (not a bare positional) so a file name that starts with "-" can never be read as an option
    r = run([exe, "-v", "error", "-print_format", "json", *args, "-i", path], timeout=timeout)
    if r.timed_out:
        raise ProbeError(f"ffprobe timed out after {timeout:g} s on {path!r}")
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["(no message)"])[-1]
        raise ProbeError(f"ffprobe failed on {path!r} (exit {r.returncode}): {tail}")
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError(f"ffprobe returned invalid JSON for {path!r}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProbeError("ffprobe JSON root is not an object")
    return data


def probe(path: str | os.PathLike[str], *, configured_ffprobe: str | None = None) -> MediaInfo:
    """Read format + stream facts. Raises ``ProbeError`` for a missing/corrupt file."""
    p = os.fspath(path)
    if not os.path.isfile(fs_path(p)):
        raise ProbeError(f"input file not found: {p!r}")
    data = _ffprobe_json(["-show_format", "-show_streams"], p, configured=configured_ffprobe)
    fmt = data.get("format") or {}
    video: list[VideoStream] = []
    audio: list[AudioStream] = []
    for s in data.get("streams") or []:
        kind = s.get("codec_type")
        if kind == "video" and (s.get("disposition") or {}).get("attached_pic") != 1:
            video.append(
                VideoStream(
                    index=int(s.get("index", 0)),
                    codec=str(s.get("codec_name", "?")),
                    width=int(s.get("width") or 0),
                    height=int(s.get("height") or 0),
                    pix_fmt=s.get("pix_fmt"),
                    r_frame_rate=_rate(s.get("r_frame_rate")),
                    avg_frame_rate=_rate(s.get("avg_frame_rate")),
                    time_base=_frac(s.get("time_base")),
                    declared_frames=_int(s.get("nb_frames")),
                    duration_s=_frac(s.get("duration")),
                    rotation=_rotation(s),
                    sample_aspect_ratio=s.get("sample_aspect_ratio"),
                    start_time_s=_frac(s.get("start_time")),
                )
            )
        elif kind == "audio":
            audio.append(AudioStream(int(s.get("index", 0)), str(s.get("codec_name", "?")), _int(s.get("sample_rate")), _int(s.get("channels")), _frac(s.get("duration"))))
    return MediaInfo(
        path=p,
        format_name=fmt.get("format_name"),
        duration_s=_frac(fmt.get("duration")),
        size_bytes=_int(fmt.get("size")),
        video=tuple(video),
        audio=tuple(audio),
        raw=data,
    )


def expected_frames(path: str | os.PathLike[str], info: MediaInfo | None = None, *, configured_ffprobe: str | None = None) -> tuple[int | None, str]:
    """Container-level frame count of the first video stream and where it came from.

    Returns ``(count, source)`` with source ``"nb_frames"`` (declared), ``"packet_count"`` (read every packet header, fast,
    no decoding) or ``"unknown"`` (count is ``None`` -> the caller's envelope must be INSUFFICIENT_EVIDENCE).
    """
    p = os.fspath(path)
    info = info or probe(p, configured_ffprobe=configured_ffprobe)
    v = info.first_video
    if v.declared_frames is not None and v.declared_frames > 0:
        return v.declared_frames, "nb_frames"
    data = _ffprobe_json(["-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets"], p, configured=configured_ffprobe, timeout=300)
    streams = data.get("streams") or []
    n = _int(streams[0].get("nb_read_packets")) if streams else None
    if n is not None and n > 0:
        return n, "packet_count"
    return None, "unknown"


def count_decoded_frames(path: str | os.PathLike[str], *, configured_ffprobe: str | None = None, timeout: float = 600.0) -> int:
    """Decode the whole first video stream and count frames (``nb_read_frames``). Slow; use when the container lies."""
    data = _ffprobe_json(["-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames"], os.fspath(path), configured=configured_ffprobe, timeout=timeout)
    streams = data.get("streams") or []
    n = _int(streams[0].get("nb_read_frames")) if streams else None
    if n is None:
        raise ProbeError("ffprobe did not report nb_read_frames (decode failed or no video stream)")
    return n


def packet_pts(path: str | os.PathLike[str], *, configured_ffprobe: str | None = None) -> tuple[list[int], Fraction]:
    """Presentation-ordered integer PTS of every video packet and the stream time base (for ``timebase.FrameClock.from_pts``)."""
    p = os.fspath(path)
    info = probe(p, configured_ffprobe=configured_ffprobe)
    tb = info.first_video.time_base
    if tb is None:
        raise ProbeError("video stream has no time_base")
    data = _ffprobe_json(["-select_streams", "v:0", "-show_entries", "packet=pts"], p, configured=configured_ffprobe, timeout=300)
    values = [_int(pkt.get("pts")) for pkt in data.get("packets") or []]
    if not values or any(v is None for v in values):
        raise ProbeError("some video packets carry no PTS; cannot build a timeline")
    return sorted(v for v in values if v is not None), tb

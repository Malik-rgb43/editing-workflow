"""Rational frame rates, timestamps and a drift guard.

Rule: **time is a ``fractions.Fraction`` of seconds; a frame rate is never a float.**  A tool that hard-codes 30 fps
mislabels 25 fps material (E04-B02: the caption drop at frame 25 = 1.00 s was printed as 0.83 s), and a tool that
treats 30000/1001 as 30 drifts 3.6 s over 108,000 frames (frontier F05; 3,603.6 s vs 3,600 s).

Every report carries BOTH numbers: ``describe_frame(n, fps)`` returns the frame index and the exact timestamp.

Usage:
    python -c "from core.timebase import describe_frame, parse_rate; print(describe_frame(25, parse_rate('25')))"
"""

from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from .errors import TimebaseError

__all__ = [
    "KNOWN_RATES",
    "NTSC_DRIFT_TOLERANCE_S",
    "parse_rate",
    "snap_rate",
    "is_ntsc",
    "frame_to_time",
    "time_to_frame",
    "pts_to_time",
    "format_timestamp",
    "describe_frame",
    "drift_seconds",
    "assert_no_drift",
    "FrameClock",
]

#: Broadcast rates that must stay exact. 29.97 is 30000/1001, never 29.97.
KNOWN_RATES: dict[str, Fraction] = {
    "23.976": Fraction(24000, 1001),
    "24": Fraction(24),
    "25": Fraction(25),
    "29.97": Fraction(30000, 1001),
    "30": Fraction(30),
    "47.952": Fraction(48000, 1001),
    "48": Fraction(48),
    "50": Fraction(50),
    "59.94": Fraction(60000, 1001),
    "60": Fraction(60),
}

#: A rate assumption is accepted when the total drift over the clip stays below this many seconds.
NTSC_DRIFT_TOLERANCE_S = Fraction(1, 2)

_RATE_RE = re.compile(r"^\s*(\d+)\s*(?:/\s*(\d+))?\s*$")


def parse_rate(value: object) -> Fraction:
    """Parse ``"30000/1001"``, ``"25"``, ``25``, ``Fraction`` or ``(30000, 1001)`` into a positive ``Fraction``.

    Floats and bools are rejected on purpose: ``29.97`` is not 29.97002997...; use ``snap_rate`` if a float is all you
    have. ffprobe's ``r_frame_rate``/``avg_frame_rate`` strings are accepted as-is; ``"0/0"`` raises.
    """
    if isinstance(value, bool) or isinstance(value, float):
        raise TimebaseError("frame rate must be exact (int, 'n/d' text or Fraction), never float/bool; use snap_rate() for a float")
    if isinstance(value, Fraction):
        rate = value
    elif isinstance(value, int):
        rate = Fraction(value)
    elif isinstance(value, tuple) and len(value) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in value):
        if value[1] == 0:
            raise TimebaseError("frame rate denominator is zero")
        rate = Fraction(value[0], value[1])
    elif isinstance(value, str):
        m = _RATE_RE.match(value)
        if not m:
            raise TimebaseError(f"cannot parse frame rate {value!r}; expected an integer or 'numerator/denominator'")
        den = int(m.group(2)) if m.group(2) is not None else 1
        if den == 0:
            raise TimebaseError(f"frame rate {value!r} has a zero denominator (probe could not determine fps)")
        rate = Fraction(int(m.group(1)), den)
    else:
        raise TimebaseError(f"unsupported frame rate type {type(value).__name__}")
    if rate <= 0:
        raise TimebaseError("frame rate must be positive")
    return rate


def snap_rate(value: float | Fraction | str, *, tolerance: float = 0.005) -> Fraction:
    """Convert a *measured/typed* rate (e.g. 29.97, 23.976) to the exact broadcast rate it means.

    Within ``tolerance`` fps of a known rate it returns that exact rate; otherwise it raises (an unknown rate must be
    given exactly via ``parse_rate``).
    """
    if isinstance(value, (str, Fraction)) and not (isinstance(value, str) and "." in value):
        return parse_rate(value)
    x = float(value)
    for rate in KNOWN_RATES.values():
        if abs(float(rate) - x) <= tolerance:
            return rate
    raise TimebaseError(f"{value!r} is not a known broadcast frame rate; pass an exact 'n/d' string")


def is_ntsc(fps: Fraction) -> bool:
    """True for the 1001-denominator family (23.976, 29.97, 59.94 ...)."""
    return fps.denominator == 1001


def frame_to_time(frame: int, fps: Fraction, *, origin: Fraction = Fraction(0)) -> Fraction:
    """Presentation time (seconds) of 0-based ``frame`` on a constant-rate timeline."""
    if isinstance(frame, bool) or not isinstance(frame, int):
        raise TimebaseError("frame index must be an int")
    return origin + Fraction(frame) / fps


def time_to_frame(seconds: Fraction | int | str, fps: Fraction, *, rounding: str = "floor", origin: Fraction = Fraction(0)) -> int:
    """Frame index at ``seconds``. ``rounding``: ``floor`` (frame on screen at that time), ``ceil``, ``nearest``."""
    if isinstance(seconds, float):
        raise TimebaseError("time must be exact (Fraction/int/'n/d'); a float second count reintroduces drift")
    t = Fraction(seconds) - origin
    x = t * fps
    if rounding == "floor":
        return x.numerator // x.denominator
    if rounding == "ceil":
        return -((-x.numerator) // x.denominator)
    if rounding == "nearest":
        return int((x + Fraction(1, 2)).__floor__())
    raise TimebaseError(f"unknown rounding {rounding!r}")


def pts_to_time(pts: int, time_base: Fraction | str) -> Fraction:
    tb = parse_rate(time_base) if not isinstance(time_base, Fraction) else time_base
    if isinstance(pts, bool) or not isinstance(pts, int):
        raise TimebaseError("pts must be an integer tick count")
    return Fraction(pts) * tb


def format_timestamp(seconds: Fraction) -> str:
    """``HH:MM:SS.mmm`` rounded to the nearest millisecond (display only; the exact value is kept elsewhere)."""
    ms = round(Fraction(seconds) * 1000)
    sign = "-" if ms < 0 else ""
    ms = abs(ms)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{sign}{h:02d}:{m:02d}:{s:02d}.{milli:03d}"


def describe_frame(frame: int, fps: Fraction, *, time: Fraction | None = None) -> dict:
    """Both numbers a finding needs: ``{"frame", "time_s" (exact text), "time_s_float", "timecode"}``.

    Pass ``time`` for a VFR clip (the real PTS-derived time); omit it for constant-rate material.
    """
    t = time if time is not None else frame_to_time(frame, fps)
    return {
        "frame": frame,
        "time_s": f"{t.numerator}/{t.denominator}" if t.denominator != 1 else str(t.numerator),
        "time_s_float": round(float(t), 6),
        "timecode": format_timestamp(t),
    }


def drift_seconds(frame_count: int, true_fps: Fraction, assumed_fps: Fraction) -> Fraction:
    """How far the clip end lands from where an ``assumed_fps`` tool believes it is (positive = tool thinks it is shorter)."""
    return Fraction(frame_count) / assumed_fps - Fraction(frame_count) / true_fps


def assert_no_drift(frame_count: int, true_fps: Fraction, assumed_fps: Fraction, *, tolerance_s: Fraction = NTSC_DRIFT_TOLERANCE_S) -> Fraction:
    """Raise ``TimebaseError`` when assuming ``assumed_fps`` for ``true_fps`` material drifts more than ``tolerance_s``.

    Example: 108,000 frames at 30000/1001 assumed as 30 -> 3.6 s of drift (F05) -> raises.
    """
    d = drift_seconds(frame_count, true_fps, assumed_fps)
    if abs(d) > tolerance_s:
        raise TimebaseError(
            f"assuming {assumed_fps} fps for {true_fps} fps material drifts {float(d):+.3f} s over {frame_count} frames",
            remediation="read the rational r_frame_rate from ffprobe and carry it (Fraction) through the whole pipeline",
        )
    return d


@dataclass(frozen=True)
class FrameClock:
    """Maps frame indices to exact times for constant-rate (``cfr``) or variable-rate (``from_pts``) video."""

    fps: Fraction | None
    pts_times: tuple[Fraction, ...] | None = None
    count: int | None = None

    @classmethod
    def cfr(cls, fps: object, count: int | None = None) -> "FrameClock":
        return cls(fps=parse_rate(fps), count=count)

    @classmethod
    def from_pts(cls, pts: Iterable[int], time_base: Fraction | str) -> "FrameClock":
        tb = parse_rate(time_base) if not isinstance(time_base, Fraction) else time_base
        times = tuple(Fraction(p) * tb for p in pts)
        if not times:
            raise TimebaseError("no PTS values: cannot build a VFR clock")
        if any(b <= a for a, b in zip(times, times[1:], strict=False)):
            raise TimebaseError("PTS must be strictly increasing in presentation order")
        return cls(fps=None, pts_times=times, count=len(times))

    def time_of(self, frame: int) -> Fraction:
        if self.pts_times is not None:
            return self.pts_times[frame]
        assert self.fps is not None
        return frame_to_time(frame, self.fps)

    def frame_at(self, seconds: Fraction) -> int:
        """Index of the frame on screen at ``seconds`` (last frame whose time <= seconds)."""
        if self.pts_times is not None:
            i = bisect_left(self.pts_times, seconds)
            if i == len(self.pts_times) or self.pts_times[i] != seconds:
                i -= 1
            return max(0, i)
        assert self.fps is not None
        return max(0, time_to_frame(seconds, self.fps))

    def describe(self, frame: int) -> dict:
        return describe_frame(frame, self.fps or Fraction(1), time=self.time_of(frame))

    def duration(self) -> Fraction | None:
        if self.count is None:
            return None
        if self.pts_times is not None:
            return self.pts_times[-1] - self.pts_times[0] + (self.pts_times[-1] - self.pts_times[-2] if len(self.pts_times) > 1 else Fraction(0))
        assert self.fps is not None
        return Fraction(self.count) / self.fps

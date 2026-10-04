"""Decode helpers: stream raw frames / audio samples out of FFmpeg with explicit success accounting.

``FrameReader`` yields frames as numpy arrays (``numpy`` is imported lazily) and, once exhausted, tells the truth about
the decode: how many frames arrived, FFmpeg's exit status, whether a partial trailing frame was dropped, and the tail of
its error output.  QA tools feed ``reader.decoded`` into the envelope's ``decoded_frames`` - a decoder that exits non-zero
or produces fewer frames than the container promises can therefore never become a PASS (E04-B01).

* frames are requested with ``-fps_mode passthrough`` so FFmpeg neither duplicates nor drops frames on VFR input;
* auto-rotation is on (FFmpeg default); the reported geometry accounts for it;
* stderr is drained on a thread (no pipe deadlock) and kept bounded.

Usage:
    python -c "from core.media import FrameReader; r=FrameReader('clip.mp4'); print(sum(1 for _ in r), r.ok)"
"""

from __future__ import annotations

import collections
import os
import subprocess
import threading
from typing import Any, Iterator

from .errors import DecodeError
from .ffprobe import MediaInfo, find_ffmpeg, probe
from .procs import ManagedProcess, spawn

__all__ = ["FrameReader", "read_audio_samples", "read_frame_at", "PIX_FMT_CHANNELS"]

PIX_FMT_CHANNELS = {"gray": 1, "rgb24": 3, "bgr24": 3}


class FrameReader:
    """Iterate decoded frames: ``for frame in FrameReader(path, pix_fmt="gray"): ...``.

    Parameters
    ----------
    path:        media file (any Unicode path; passed as one argv element, no shell).
    pix_fmt:     ``gray`` (h, w), ``rgb24`` or ``bgr24`` (h, w, 3).
    scale:       optional ``(width, height)`` output size (FFmpeg ``scale`` filter). Default: native decoded size.
    vf:          extra FFmpeg filter chain applied before scaling (e.g. ``"crop=..."``). Trusted input only.
    max_frames:  stop after this many frames (``decoded`` reflects it; ``ok`` stays True for an intentional limit).
    timeout_s:   wall-clock limit for the whole decode; exceeded -> process tree killed and ``timed_out`` is True.
    info:        pre-probed ``MediaInfo`` (avoids a second ffprobe call).
    """

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        pix_fmt: str = "gray",
        scale: tuple[int, int] | None = None,
        vf: str | None = None,
        max_frames: int | None = None,
        timeout_s: float | None = None,
        info: MediaInfo | None = None,
        ffmpeg: str | None = None,
    ) -> None:
        if pix_fmt not in PIX_FMT_CHANNELS:
            raise DecodeError(f"unsupported pix_fmt {pix_fmt!r}; use one of {sorted(PIX_FMT_CHANNELS)}")
        self.path = os.fspath(path)
        self.pix_fmt = pix_fmt
        self.info = info or probe(self.path)
        w, h = self.info.first_video.display_size
        if scale is not None:
            w, h = scale
        if w <= 0 or h <= 0:
            raise DecodeError("video geometry unknown")
        self.width, self.height = int(w), int(h)
        self._scale = scale
        self._vf = vf
        self._max = max_frames
        self._timeout = timeout_s
        self._ffmpeg = find_ffmpeg(ffmpeg)
        self.decoded = 0
        self.returncode: int | None = None
        self.partial_tail_bytes = 0
        self.timed_out = False
        self.finished = False
        self.stderr_tail: list[str] = []
        self._limit_hit = False

    @property
    def frame_bytes(self) -> int:
        return self.width * self.height * PIX_FMT_CHANNELS[self.pix_fmt]

    @property
    def ok(self) -> bool:
        """True only after a full pass: exit 0 (or the requested ``max_frames`` was reached), no partial frame, no timeout, >0 frames."""
        if not self.finished or self.timed_out or self.partial_tail_bytes or self.decoded == 0:
            return False
        return self._limit_hit or self.returncode == 0

    def _cmd(self) -> list[str]:
        filters = [f for f in (self._vf, f"scale={self._scale[0]}:{self._scale[1]}:flags=bilinear" if self._scale else None) if f]
        cmd = [self._ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-i", self.path, "-map", "0:v:0", "-an", "-sn", "-dn", "-fps_mode", "passthrough"]
        if filters:
            cmd += ["-vf", ",".join(filters)]
        cmd += ["-f", "rawvideo", "-pix_fmt", self.pix_fmt, "pipe:1"]
        return cmd

    def __iter__(self) -> Iterator[Any]:
        import numpy as np  # lazy: keeps `import core.media` and `--help` fast

        n = self.frame_bytes
        shape = (self.height, self.width) if self.pix_fmt == "gray" else (self.height, self.width, 3)
        proc: ManagedProcess = spawn(self._cmd(), stdin=subprocess.DEVNULL)
        errs: collections.deque[str] = collections.deque(maxlen=20)

        def drain() -> None:
            assert proc.popen.stderr is not None
            for line in iter(proc.popen.stderr.readline, b""):
                errs.append(line.decode("utf-8", "replace").rstrip())

        t = threading.Thread(target=drain, daemon=True)
        t.start()
        timer: threading.Timer | None = None
        if self._timeout:
            def _kill() -> None:
                self.timed_out = True
                proc.terminate_tree()

            timer = threading.Timer(self._timeout, _kill)
            timer.daemon = True
            timer.start()
        stdout = proc.popen.stdout
        assert stdout is not None
        try:
            while True:
                if self._max is not None and self.decoded >= self._max:
                    self._limit_hit = True
                    break
                buf = stdout.read(n)
                if not buf:
                    break
                if len(buf) < n:
                    # read() on a pipe may return short; top up before declaring a partial frame
                    while len(buf) < n:
                        more = stdout.read(n - len(buf))
                        if not more:
                            break
                        buf += more
                    if len(buf) < n:
                        self.partial_tail_bytes = len(buf)
                        break
                self.decoded += 1
                yield np.frombuffer(buf, dtype=np.uint8).reshape(shape)
        finally:
            if timer is not None:
                timer.cancel()
            if self._limit_hit or self.timed_out:
                proc.terminate_tree()
            try:
                stdout.close()
            except OSError:
                pass
            try:
                self.returncode = proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.terminate_tree()
                self.returncode = proc.poll()
            t.join(timeout=5)
            proc.close()
            self.stderr_tail = list(errs)
            self.finished = True

    def require_ok(self) -> None:
        if not self.ok:
            raise DecodeError(
                f"decode of {self.path!r} was not clean: frames={self.decoded}, exit={self.returncode}, "
                f"partial_tail_bytes={self.partial_tail_bytes}, timed_out={self.timed_out}; "
                f"ffmpeg said: {' | '.join(self.stderr_tail[-3:]) or '(nothing)'}"
            )


def read_audio_samples(path: str | os.PathLike[str], *, sample_rate: int = 48000, channels: int = 1, timeout_s: float = 300.0, ffmpeg: str | None = None) -> Any:
    """Decode the first audio stream to a ``numpy.int16`` array of shape ``(samples, channels)``.

    Raises ``DecodeError`` when FFmpeg fails, times out or returns no samples (an empty array is never returned).
    """
    import numpy as np

    from .procs import run

    cmd = [find_ffmpeg(ffmpeg), "-hide_banner", "-nostdin", "-v", "error", "-i", os.fspath(path), "-map", "0:a:0", "-vn", "-ac", str(channels), "-ar", str(sample_rate), "-f", "s16le", "pipe:1"]
    r = run(cmd, timeout=timeout_s, decode_stdout=False)
    if r.timed_out:
        raise DecodeError(f"audio decode of {os.fspath(path)!r} timed out")
    if r.returncode != 0:
        raise DecodeError(f"audio decode failed (exit {r.returncode}): {(r.stderr.strip().splitlines() or ['(no message)'])[-1]}")
    data = r.stdout_bytes
    usable = len(data) - (len(data) % (2 * channels))
    if usable <= 0:
        raise DecodeError("audio decode produced no samples (no audio stream?)")
    return np.frombuffer(data[:usable], dtype="<i2").reshape(-1, channels)


def read_frame_at(path: str | os.PathLike[str], t: float, *, width: int | None = None, info: MediaInfo | None = None, timeout_s: float = 60.0, ffmpeg: str | None = None) -> Any:
    """Decode ONE frame at ``t`` seconds as an RGB ``numpy.uint8`` array ``(h, w, 3)``, optionally scaled to ``width`` (aspect kept, even height).

    Raises ``DecodeError`` when FFmpeg fails, times out, or returns fewer bytes than one full frame (never a partial or empty array).
    """
    import numpy as np

    from .procs import run

    mi = info or probe(os.fspath(path))
    w, h = mi.first_video.display_size
    if w <= 0 or h <= 0:
        raise DecodeError("video geometry unknown")
    if width and width < w:
        sw = max(2, int(width) - int(width) % 2)
        sh = max(2, int(round(h * sw / w / 2.0)) * 2)
    else:
        sw, sh = int(w), int(h)
    cmd = [find_ffmpeg(ffmpeg), "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{max(0.0, float(t)):.6f}", "-i", os.fspath(path), "-map", "0:v:0", "-an", "-frames:v", "1",
           "-vf", f"scale={sw}:{sh}:flags=bilinear", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    r = run(cmd, timeout=timeout_s, decode_stdout=False)
    if r.timed_out:
        raise DecodeError(f"frame decode of {os.fspath(path)!r} at {t}s timed out")
    need = sw * sh * 3
    if r.returncode != 0 or len(r.stdout_bytes) < need:
        raise DecodeError(f"no frame at {t}s (exit {r.returncode}, {len(r.stdout_bytes)} of {need} bytes): {(r.stderr.strip().splitlines() or ['(no message)'])[-1]}")
    return np.frombuffer(r.stdout_bytes[:need], dtype=np.uint8).reshape(sh, sw, 3)

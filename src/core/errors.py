"""Shared state vocabulary, exit codes and exception types for the toolkit core.

States (one vocabulary for doctor, gates and the delivery aggregator; src: blueprint REPO_ARCHITECTURE section 8):

    pass | fail | unsupported | not_run | insufficient_evidence | error

``unsupported`` (this machine/profile cannot run it) is not ``not_run`` (nobody ran it) and neither is
``error`` (it ran and crashed). Only ``pass`` is green. Nothing else may be rendered as green.

Exit codes (every QA CLI uses these; src: blueprint TOOLS_SPEC section 1.3):

    0  PASS
    1  FAIL                    a real defect was found
    2  INSUFFICIENT_EVIDENCE   the tool could not prove it inspected the media (timeout, empty sample, missing input)
    3  ERROR                   the tool itself crashed / mis-configured
    4  BUSY                    the heavy-job lock is held (not an error of the media)
    64 USAGE                   bad command line

Usage:
    python -m core --help
"""

from __future__ import annotations

import enum

__all__ = [
    "GateState",
    "EXIT_PASS",
    "EXIT_FAIL",
    "EXIT_INSUFFICIENT",
    "EXIT_ERROR",
    "EXIT_BUSY",
    "EXIT_USAGE",
    "ToolkitError",
    "PathSafetyError",
    "ForbiddenRootError",
    "ConfigError",
    "MediaToolMissing",
    "ProbeError",
    "DecodeError",
    "TimebaseError",
    "LockBusy",
    "LockUncertain",
    "LockOwnershipError",
    "ProcessError",
]

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_INSUFFICIENT = 2
EXIT_ERROR = 3
EXIT_BUSY = 4
EXIT_USAGE = 64


class GateState(str, enum.Enum):
    """The six gate states. Only PASS is green."""

    PASS = "pass"
    FAIL = "fail"
    UNSUPPORTED = "unsupported"
    NOT_RUN = "not_run"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ERROR = "error"

    @property
    def is_green(self) -> bool:
        return self is GateState.PASS


class ToolkitError(Exception):
    """Base class. ``code`` is a stable machine-readable identifier; ``remediation`` is user-facing text."""

    code = "toolkit_error"
    exit_code = EXIT_ERROR

    def __init__(self, message: str, *, remediation: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.remediation = remediation

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.remediation:
            return f"{self.message}\n  fix: {self.remediation}"
        return self.message


class PathSafetyError(ToolkitError):
    """A path failed a safety rule (outside the managed root, forbidden, a link, ...). Nothing was touched."""

    code = "path_unsafe"


class ForbiddenRootError(PathSafetyError):
    """A drive root, home folder, system folder or similar was passed where a work path is required."""

    code = "path_forbidden_root"


class ConfigError(ToolkitError):
    code = "config_error"


class MediaToolMissing(ToolkitError):
    code = "media_tool_missing"


class ProbeError(ToolkitError):
    """ffprobe failed or returned something unusable. Never treated as "no findings"."""

    code = "probe_error"


class DecodeError(ToolkitError):
    """The decoder exited non-zero, produced a truncated frame, or produced no frames."""

    code = "decode_error"


class TimebaseError(ToolkitError):
    code = "timebase_error"


class LockBusy(ToolkitError):
    code = "lock_busy"
    exit_code = EXIT_BUSY


class LockUncertain(ToolkitError):
    """The lock state cannot be established (permissions, network volume). Never treated as "free"."""

    code = "lock_uncertain"


class LockOwnershipError(ToolkitError):
    code = "lock_ownership"


class ProcessError(ToolkitError):
    code = "process_error"

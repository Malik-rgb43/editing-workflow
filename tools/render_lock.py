"""render_lock - the machine-wide single-heavy-job lock (kernel lock; replaces the original file-timestamp lock).

One heavy job at a time (render, ``hyperframes check``, Blender, ASR, matte): the lease is an OS-level lock on ONE absolute shared
path (``[paths] lock_path``; default a per-user state folder). The OS releases it if the process dies; it is never taken over
automatically while its lifetime is uncertain; the owner/heartbeat file beside it is advisory only. A forged or ancient timestamp can
neither steal nor free a live lock (both races of the original were reproduced and are regression-tested in tests/unit/test_core_lock.py).

Usage:
    python tools/render_lock.py status [--json]
    python tools/render_lock.py run --job "render v3" [--wait 600] [--timeout 5400] -- <command> [args...]
See `python tools/render_lock.py --help` for the exit codes of the core lock CLI.
"""

from __future__ import annotations

import sys

import _common  # noqa: F401


def main(argv=None) -> int:
    from core.lock import main as lock_main

    return lock_main(list(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())

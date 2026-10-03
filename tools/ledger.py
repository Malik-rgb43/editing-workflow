"""ledger - read and summarise the per-project timing ledger (JSONL, one line per stage).

Every long tool appends to ``<project>/_work/timing-ledger.jsonl``: queue/setup/load/run/QA/review minutes, renders, retries and credits.
This command turns one or more ledgers into minutes and credits, so each video becomes its own benchmark. Unknown credits stay ``null``
(never 0), and malformed lines are counted and reported (exit 2) instead of silently skipped.

Usage:
    python tools/ledger.py summarize <ledger.jsonl>... [--project NAME] [--json]
    python tools/ledger.py demo <ledger.jsonl>          (writes 3 sample lines; used by tests)
"""

from __future__ import annotations

import sys

import _common  # noqa: F401


def main(argv=None) -> int:
    from core.ledger import main as ledger_main

    return ledger_main(list(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())

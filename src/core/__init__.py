"""editing-workflow core: paths, config, QA envelope, timebase, ledger, FFmpeg helpers, process control, lock.

Import rules: this package imports only the standard library at module level. numpy / Pillow / OpenCV are imported
lazily inside the functions that need them, so ``python -m core --help`` and ``doctor`` start in well under a second
(E04-L01: ``transcribe_he --help`` took more than 45 s because of eager imports).

The package is run from source and imported as ``core``: ``src/`` must be on ``sys.path`` (pytest ``pythonpath`` does this; entry
points in ``tools/`` insert ``<repo>/src`` before importing; ``python -m core`` works with ``PYTHONPATH=src``).

Usage:
    python -m core --help
"""

__version__ = "0.1.0"
TOOLKIT_VERSION = __version__

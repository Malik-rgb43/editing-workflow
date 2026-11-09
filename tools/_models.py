"""_models - one shared place for small downloaded model files, and a download that is always shown before it happens.

Every model lives in ONE per-user folder (``core.config.user_models_dir()``: ~/.avc/models, AVC_MODELS_DIR overrides), so a file fetched
once is found by every later project instead of being asked for again mid-edit (review 2026-11-09). ``fetch_file`` without ``yes`` prints
what would be downloaded (file, bytes, licence, source) and downloads NOTHING; with ``yes`` (only after the user's yes) it downloads to a
temporary file, checks the size, and moves it into place atomically.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path


def fetch_file(url: str, dest: Path, expected_bytes: int | None, yes: bool, label: str, licence: str, timeout: float = 120.0) -> int:
    plan = {"model": label, "file": str(dest), "bytes": expected_bytes or "unknown", "licence": licence, "source": url}
    if dest.is_file() and (not expected_bytes or dest.stat().st_size == expected_bytes):
        print(json.dumps({**plan, "status": "already on this computer, nothing to download"}, indent=2, ensure_ascii=False))
        return 0
    if not yes:
        print(json.dumps({**plan, "status": "nothing was downloaded: show this to the user; after their yes run the same command with --yes"},
                         indent=2, ensure_ascii=False))
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "avc-toolkit"})
        with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:  # noqa: S310 - fixed https URL from this file
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
        got = tmp.stat().st_size
        if expected_bytes and got != expected_bytes:
            tmp.unlink(missing_ok=True)
            print(f"{label}: downloaded {got} bytes, expected {expected_bytes}: refused (nothing kept)", file=sys.stderr)
            return 1
        os.replace(tmp, dest)
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        print(f"{label}: download failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({**plan, "status": "downloaded"}, indent=2, ensure_ascii=False))
    return 0

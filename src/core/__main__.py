"""``python -m core`` - small diagnostics front-end for the core library (the real tools live in ``tools/``).

Usage:
    python -m core --help
    python -m core config [--json]                      show resolved toolkit.toml values and where each came from
    python -m core slug "<display title>"               ASCII folder name for a (Hebrew) title
    python -m core paths check <path>                   forbidden-root / ASCII check for a candidate work root
    python -m core probe <media-file>                   ffprobe facts as JSON (rational fps, expected frame count)
    python -m core ledger summarize <file>... [--json]  summarise timing-ledger files
    python -m core lock status|run ...                  heavy-job lock (see: python -m core lock --help)
    python -m core qa-delivery <contract.json> <report.json>...   delivery evidence gate (exit 0 only when every required gate passed)

Every sub-command imports only what it needs, so ``--help`` returns in well under a second.
"""

from __future__ import annotations

import json
import sys


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def _usage() -> str:
    return (__doc__ or "").strip()


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help", "help"):
        print(_usage())
        return 0
    cmd, rest = args[0], args[1:]
    if cmd == "config":
        from .config import load_config

        cfg = load_config()
        data = cfg.to_dict()
        if "--json" in rest:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("config files:", ", ".join(data["files"]) or "(none found; all values unset)")
            for k, v in data["values"].items():
                print(f"  {k:<28} {v['value'] or '-':<40} [{v['source']}]")
            print(f"  effective lock_path          {data['effective']['lock_path']}")
            print(f"  effective cache_dir          {data['effective']['cache_dir']}")
            for w in data["warnings"]:
                print("  WARNING:", w)
        return 0
    if cmd == "slug":
        from .paths import slugify

        if len(rest) != 1:
            print('usage: python -m core slug "<display title>"', file=sys.stderr)
            return 64
        print(slugify(rest[0]))
        return 0
    if cmd == "paths":
        from .errors import PathSafetyError
        from .paths import forbidden_reason, resolve_work_root

        if len(rest) != 2 or rest[0] != "check":
            print("usage: python -m core paths check <path>", file=sys.stderr)
            return 64
        reason = forbidden_reason(rest[1])
        if reason:
            print(f"FORBIDDEN: {reason}")
            return 1
        try:
            resolve_work_root(rest[1])
        except PathSafetyError as exc:
            print(f"NOT A VALID WORK ROOT: {exc}")
            return 1
        print("ok: usable as an ASCII work root")
        return 0
    if cmd == "probe":
        from .errors import ToolkitError
        from .ffprobe import expected_frames, probe

        if len(rest) != 1:
            print("usage: python -m core probe <media-file>", file=sys.stderr)
            return 64
        try:
            info = probe(rest[0])
            n, src = expected_frames(rest[0], info)
        except ToolkitError as exc:
            print(str(exc), file=sys.stderr)
            return 3
        v = info.video[0] if info.video else None
        out = {
            "path": info.path,
            "format": info.format_name,
            "duration_s": str(info.duration_s) if info.duration_s is not None else None,
            "video": None
            if v is None
            else {
                "codec": v.codec,
                "size": [v.width, v.height],
                "display_size": list(v.display_size),
                "fps": str(v.fps) if v.fps else None,
                "avg_frame_rate": str(v.avg_frame_rate) if v.avg_frame_rate else None,
                "time_base": str(v.time_base) if v.time_base else None,
                "pix_fmt": v.pix_fmt,
                "rotation": v.rotation,
                "is_vfr": v.is_vfr,
            },
            "expected_frames": n,
            "expected_frames_source": src,
            "audio": [{"codec": a.codec, "sample_rate": a.sample_rate, "channels": a.channels} for a in info.audio],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd == "ledger":
        from .ledger import main as ledger_main

        return ledger_main(rest)
    if cmd == "lock":
        from .lock import main as lock_main

        return lock_main(rest)
    if cmd == "qa-delivery":
        from .envelope import DeliveryContract, aggregate_delivery, emit
        from .fsio import read_json

        if len(rest) < 2:
            print("usage: python -m core qa-delivery <contract.json> <report.json>...", file=sys.stderr)
            return 64
        try:
            contract_raw = read_json(rest[0])
            reports = [read_json(p) for p in rest[1:]]
        except (OSError, ValueError) as exc:
            print(f"cannot read inputs: {exc}", file=sys.stderr)
            return 3
        contract = DeliveryContract.from_dict(contract_raw)
        artifact = contract_raw.get("artifact_path")
        result = aggregate_delivery(contract, reports, artifact_path=artifact)
        return emit(result)
    print(f"unknown command {cmd!r}\n\n{_usage()}", file=sys.stderr)
    return 64


if __name__ == "__main__":
    raise SystemExit(main())

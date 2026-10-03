"""qa_delivery - the delivery evidence gate: may THIS file be delivered? (aggregates the gate reports, fail-closed)

``run <video>`` executes the automatic gates on the final file (frame_qa; caption_qa with --captions; hf_deliver verify), saves each report
next to ``--out-dir``, adds the human-review attestation only when you pass ``--human-approved "<the user's words>"``, and aggregates:

  * FAIL if any gate that ran failed (a flagged frame never ships);
  * INSUFFICIENT_EVIDENCE while any REQUIRED gate has not run / lacks evidence / belongs to another file (hash-bound) / is stale;
  * PASS only when every required gate passed on THIS file. The report says it proves evidence completeness - not taste, rights or truth.

``aggregate <contract.json> <report.json>...`` is the same logic over reports you already have (see contracts/ and `python -m core qa-delivery`).

Usage:
    python tools/qa_delivery.py run <video> [--captions] [--expected-duration S] [--human-approved "words" --attested-by NAME] [--out-dir DIR] [--max-age-min 120]
    python tools/qa_delivery.py aggregate <contract.json> <report.json>...
Exit: 0 PASS, 1 FAIL, 2 INSUFFICIENT_EVIDENCE, 3 tool error.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import _common  # noqa: F401

HERE = Path(__file__).resolve().parent


def _tool(name, *args):
    p = subprocess.run([sys.executable, "-X", "utf8", str(HERE / f"{name}.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(p.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="qa_delivery", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("video")
    r.add_argument("--captions", action="store_true")
    r.add_argument("--expected-duration", type=float)
    r.add_argument("--human-approved", help="the human reviewer's own words approving this exact file (never write this yourself)")
    r.add_argument("--attested-by", default="the user (approval quoted from the chat)")
    r.add_argument("--out-dir")
    r.add_argument("--max-age-min", type=float, default=120.0)
    g = sub.add_parser("aggregate")
    g.add_argument("contract")
    g.add_argument("reports", nargs="+")
    a = ap.parse_args(argv)

    from core.envelope import DeliveryContract, EnvelopeBuilder, aggregate_delivery, emit, sha256_file
    from core.fsio import read_json, write_json_atomic

    if a.cmd == "aggregate":
        contract = DeliveryContract.from_dict(read_json(a.contract))
        reports = [read_json(p) for p in a.reports]
        return emit(aggregate_delivery(contract, reports))
    video = Path(a.video)
    out_dir = Path(a.out_dir) if a.out_dir else video.parent.parent / "_work" / "qa" / video.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    required = ["frame_qa", "hf_deliver.verify", "human_review"]
    for name, args in (("frame_qa", [video]), ("hf_deliver", ["verify", video] + (["--expected-duration", a.expected_duration] if a.expected_duration else []))):
        rep = _tool(name, *args)
        if rep is not None:
            reports.append(rep)
            write_json_atomic(out_dir / f"{rep['tool']}.json", rep)
    if a.captions:
        required.insert(1, "caption_qa")
        rep = _tool("caption_qa", video)
        if rep is not None:
            reports.append(rep)
            write_json_atomic(out_dir / "caption_qa.json", rep)
    if a.human_approved:
        b = EnvelopeBuilder("human_review", _common.TOOLS_VERSION, video, kind="attestation")
        b.set_frames(decoded=1, expected=1)
        b.extra["approval"] = a.human_approved
        e = b.build()
        e.attested_by = a.attested_by
        reports.append(e.to_dict())
        write_json_atomic(out_dir / "human_review.json", e.to_dict())
    contract = DeliveryContract(required=tuple(required), artifact_sha256=sha256_file(video), max_age_s=a.max_age_min * 60)
    agg = aggregate_delivery(contract, reports, artifact_path=video)
    write_json_atomic(out_dir / "delivery.json", agg)
    return emit(agg)


if __name__ == "__main__":
    sys.exit(main())

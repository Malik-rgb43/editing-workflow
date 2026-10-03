"""join_diff - word-level diff between the APPROVED cut text and what the assembled voice-over really says (ASR of the full assembled VO).

Catches the cut that eats a sentence's first/last words ("אני" lost at a join) or leaves residue. Rules (src: blueprint TOOLS_SPEC
section 3 item 5; rule TH-G1): a sentence missing ANY of its first two or last two words is an error; extra tokens inside the range the
assembly covers are an error (``--extra warning`` to relax); every join must be checked on the FULL assembled VO, not on isolated snippets.

Inputs: ``--reference`` a text file, one sentence per line (UTF-8), or a words.json; ``--assembled`` a words.json from ``transcribe`` of the
assembled VO (or a plain text file). Tokens are normalised (Hebrew niqqud and punctuation removed, case-folded, quote/geresh variants unified).
Output: a QA envelope (units = reference WORDS; the coverage statement is the share of reference words that were matched or reported).

Usage:
    python tools/join_diff.py --reference cut.txt --assembled assembled.words.json [--extra error|warning] [--min-ratio 0.0] [--json-out r.json]
Exit: 0 PASS, 1 FAIL, 2 INSUFFICIENT_EVIDENCE (empty input), 3 tool error.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

import _common  # noqa: F401

TOOL = "join_diff"


def norm_token(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))  # niqqud, cantillation
    t = t.replace("׳", "'").replace("״", '"').replace("’", "'").replace("”", '"')
    t = re.sub(r"[^\w'\"%₪$€-]+", "", t, flags=re.U)
    return t.casefold().strip("'\"-")


def tokenize(text: str) -> list[str]:
    return [x for x in (norm_token(w) for w in text.split()) if x]


def load_sentences(path) -> list[list[str]]:
    p = Path(path)
    if p.suffix.lower() == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        words = [w["w"] for w in d["words"]]
        return [tokenize(" ".join(words))]
    return [t for t in (tokenize(line) for line in p.read_text(encoding="utf-8").splitlines()) if t]


def load_stream(path) -> list[str]:
    p = Path(path)
    if p.suffix.lower() == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        return [t for t in (norm_token(w["w"]) for w in d["words"]) if t]
    return tokenize(p.read_text(encoding="utf-8"))


def diff(sentences: list[list[str]], hyp: list[str], *, edge: int = 2):
    """Pure function -> (findings as tuples, stats). Unit-tested."""
    ref = [t for s in sentences for t in s]
    starts, pos = [], 0
    for s in sentences:
        starts.append(pos)
        pos += len(s)
    sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
    matched = [False] * len(ref)
    first_b, last_b = None, None
    extras = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                matched[k] = True
            first_b = j1 if first_b is None else first_b
            last_b = j2
        elif tag in ("insert", "replace") and j2 > j1:
            extras.append((j1, j2, hyp[j1:j2]))
    findings = []
    for si, s in enumerate(sentences):
        a = starts[si]
        n = len(s)
        head = [k for k in range(a, a + min(edge, n)) if not matched[k]]
        tail = [k for k in range(a + max(0, n - edge), a + n) if not matched[k]]
        if head:
            findings.append(("sentence_head_missing", f"sentence {si + 1}: missing first word(s) {[ref[k] for k in head]}", {"sentence": si + 1, "words": [ref[k] for k in head]}))
        if tail:
            findings.append(("sentence_tail_missing", f"sentence {si + 1}: missing last word(s) {[ref[k] for k in tail]}", {"sentence": si + 1, "words": [ref[k] for k in tail]}))
        mid = [k for k in range(a, a + n) if not matched[k] and k not in head and k not in tail]
        if mid:
            findings.append(("words_missing", f"sentence {si + 1}: {len(mid)} word(s) missing inside the sentence: {[ref[k] for k in mid][:6]}", {"sentence": si + 1, "words": [ref[k] for k in mid]}))
    for j1, j2, toks in extras:
        if first_b is not None and last_b is not None and first_b <= j1 and j2 <= last_b:
            findings.append(("extra_tokens", f"extra word(s) in the assembled VO: {toks}", {"at_token": j1, "words": toks}))
    stats = {"reference_words": len(ref), "assembled_words": len(hyp), "matched_words": sum(matched), "ratio": round(sm.ratio(), 4)}
    return findings, stats


def run(args, b):
    from core.envelope import Finding, Severity, sha256_file

    sentences = load_sentences(args.reference)
    hyp = load_stream(args.assembled)
    nref = sum(len(s) for s in sentences)
    b.set_frames(decoded=nref if hyp else 0, expected=nref)
    b.extra["unit"] = "reference words"
    import hashlib

    b.set_input_sha256(hashlib.sha256(sha256_file(args.reference).encode() + sha256_file(args.assembled).encode()).hexdigest())
    if not nref:
        b.gap("empty_reference", "the reference text has no words")
        return
    if not hyp:
        b.gap("empty_assembled", "the assembled transcript has no words (ASR failed or silent): nothing was compared")
        return
    findings, stats = diff(sentences, hyp)
    b.extra.update(stats)
    for code, msg, data in findings:
        sev = Severity.ERROR
        if code == "extra_tokens" and args.extra == "warning":
            sev = Severity.WARNING
        b.add(Finding(code, msg, sev, data=data))
    if stats["ratio"] < args.min_ratio:
        b.add(Finding("low_similarity", f"overall similarity {stats['ratio']} < {args.min_ratio}", Severity.ERROR))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="join_diff", description=__doc__.split("\n\n")[0])
    ap.add_argument("--reference", required=True)
    ap.add_argument("--assembled", required=True)
    ap.add_argument("--extra", choices=["error", "warning"], default="error")
    ap.add_argument("--min-ratio", type=float, default=0.0)
    ap.add_argument("--json-out")
    a = ap.parse_args(argv)
    return _common.qa_main(TOOL, lambda b: run(a, b), a.assembled, out_json=a.json_out)


if __name__ == "__main__":
    sys.exit(main())

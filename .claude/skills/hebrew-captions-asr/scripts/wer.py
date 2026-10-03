#!/usr/bin/env python3
"""wer.py - word and character error rate with a DECLARED normalisation (stdlib only).

Normalisation (declared, matches the E02/E08 protocol): Unicode NFC, lowercase,
Unicode punctuation (category P*) -> space, whitespace collapsed; symbols, digits and
niqqud are kept. Corpus WER = total (S+D+I) / total reference words over ALL pairs
(never an average of per-clip WERs).

Usage:
    python -X utf8 wer.py ref.txt hyp.txt [--json out.json]
    python -X utf8 wer.py --pairs refdir hypdir [--json out.json]    # files with the same name in both folders
    python -X utf8 wer.py --self-check

Output keys: words_ref, substitutions, deletions, insertions, wer, chars_ref, cer, status.
An empty reference makes WER undefined: status INSUFFICIENT_EVIDENCE and the insertion count is
reported instead (silence / no-speech controls). Missing files are INSUFFICIENT_EVIDENCE, never 0 %.
Exit codes: 0 computed, 1 not computable (fail closed), 2 usage error.
"""
import json
import os
import sys
import unicodedata

VERSION = "0.1.0"


def normalise(text):
    text = unicodedata.normalize("NFC", text).lower()
    out = []
    for ch in text:
        out.append(" " if unicodedata.category(ch).startswith("P") else ch)
    return " ".join("".join(out).split())


def _edit_counts(ref, hyp):
    """Levenshtein with (S, D, I) counts over token lists."""
    n, m = len(ref), len(hyp)
    prev = [(j, 0, 0, j) for j in range(m + 1)]          # (cost, S, D, I)
    for i in range(1, n + 1):
        cur = [(i, 0, i, 0)]
        for j in range(1, m + 1):
            sub = prev[j - 1]
            cost_sub = sub[0] + (0 if ref[i - 1] == hyp[j - 1] else 1)
            s_tuple = (cost_sub, sub[1] + (0 if ref[i - 1] == hyp[j - 1] else 1), sub[2], sub[3])
            d = prev[j]
            d_tuple = (d[0] + 1, d[1], d[2] + 1, d[3])
            ins = cur[j - 1]
            i_tuple = (ins[0] + 1, ins[1], ins[2], ins[3] + 1)
            cur.append(min(s_tuple, d_tuple, i_tuple, key=lambda t: t[0]))
        prev = cur
    cost, s, d, i = prev[m]
    return s, d, i


def score(pairs):
    """pairs: list of (ref_text, hyp_text). Returns the aggregate report."""
    S = D = I = words = chars = cs = cd = ci = 0
    for ref, hyp in pairs:
        r, h = normalise(ref).split(), normalise(hyp).split()
        s, d, i = _edit_counts(r, h)
        S, D, I, words = S + s, D + d, I + i, words + len(r)
        rc, hc = list(normalise(ref).replace(" ", "")), list(normalise(hyp).replace(" ", ""))
        s2, d2, i2 = _edit_counts(rc, hc)
        cs, cd, ci, chars = cs + s2, cd + d2, ci + i2, chars + len(rc)
    rep = {"tool": "wer", "version": VERSION, "pairs": len(pairs), "words_ref": words,
           "substitutions": S, "deletions": D, "insertions": I, "chars_ref": chars,
           "char_edits": cs + cd + ci,
           "normalisation": "NFC, lowercase, punctuation->space, collapse whitespace"}
    if words == 0:
        rep.update(status="INSUFFICIENT_EVIDENCE", wer=None, cer=None,
                   note="empty reference: WER undefined; insertions=%d" % I)
    else:
        rep.update(status="OK", wer=round((S + D + I) / float(words), 5),
                   cer=round((cs + cd + ci) / float(chars), 5) if chars else None)
    return rep


def self_check():
    ok = True

    def expect(name, got, want):
        nonlocal ok
        ok = ok and got == want
        print("%s %-44s expected %-8s got %s" % ("ok  " if got == want else "FAIL", name, want, got))

    ref = "אני מקשיב לו ושואל שאלות. זה לבזבז שעות!"
    expect("identical text, punctuation ignored", score([(ref, "אני מקשיב לו ושואל שאלות זה לבזבז שעות")])["wer"], 0.0)
    rep = score([(ref, "מקשיב לו ושואל שאלות זה לבובו שעות")])
    expect("1 deletion + 1 substitution of 8 words", (rep["deletions"], rep["substitutions"], rep["wer"]), (1, 1, 0.25))
    rep = score([("אחד שניים", "אחד שניים שלושה")])
    expect("1 insertion of 2 words", (rep["insertions"], rep["wer"]), (1, 0.5))
    rep = score([("אחד שניים שלושה ארבעה", "אחד שניים שלושה ארבעה"), ("חמש שש", "חמש")])
    expect("corpus WER pools words (1 of 6)", rep["wer"], round(1 / 6.0, 5))
    rep = score([("", "תודה רבה")])
    expect("empty reference -> not computable", (rep["status"], rep["insertions"]), ("INSUFFICIENT_EVIDENCE", 2))
    word = "שָׁלוֹם"          # shalom with niqqud, one code-point order
    expect("NFC: reordered combining marks equal", score([(word, unicodedata.normalize("NFD", word))])["wer"], 0.0)
    expect("maqaf U+05BE is a separator", score([("בית־ספר", "בית ספר")])["wer"], 0.0)
    seeded = [("הוא אמר שנסע לחוף בבוקר", "הוא אמר שנסע לחוף בבוקר")]
    expect("seeded errors all corrected -> WER 0", score(seeded)["wer"], 0.0)
    print("SELF-CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--self-check" in argv:
        return self_check()
    out = None
    if "--json" in argv:
        k = argv.index("--json")
        out = argv[k + 1] if k + 1 < len(argv) else None
        argv = argv[:k] + argv[k + 2:]
    try:
        if len(argv) == 3 and argv[0] == "--pairs":
            names = sorted(n for n in os.listdir(argv[1]) if os.path.isfile(os.path.join(argv[2], n)))
            if not names:
                raise ValueError("no matching file names in both folders")
            pairs = [(_read(os.path.join(argv[1], n)), _read(os.path.join(argv[2], n))) for n in names]
        elif len(argv) == 2:
            pairs = [(_read(argv[0]), _read(argv[1]))]
        else:
            print(__doc__); return 2
        rep = score(pairs)
    except (OSError, ValueError) as exc:
        rep = {"tool": "wer", "version": VERSION, "status": "INSUFFICIENT_EVIDENCE", "wer": None,
               "note": "cannot score: %s" % exc}
    text = json.dumps(rep, indent=2, ensure_ascii=False)
    print(text)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if rep["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

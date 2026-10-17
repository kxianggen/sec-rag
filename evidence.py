"""Evidence hit: did retrieval bring back THE passage that holds the answer?

Recall@k only checks that SOME chunk from the right section (company + filing + Item) was
retrieved (FAILURES #32). Evidence hit checks the text itself: each golden `evidence` field
quotes the filing, and we look for those quotes inside the retrieved chunks.

    uv run python evidence.py results/np_hybrid.json      # any results file saved with chunk text

How a quote is matched: take the parts of `evidence` inside quote marks (or the whole field
if it has none), split them at "..." and keep pieces of 4+ words. A piece counts as found
when ONE retrieved chunk contains at least 80% of its words and numbers (so small wording
differences and table line breaks don't matter). A question scores the share of pieces found.
Limitation: evidence that paraphrases a table, rather than quoting it, may never match.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

GOLDEN = Path("golden.jsonl")
QUOTED = re.compile(r"'([^']{15,}?)'(?=[\s.,;/)]|$)|\"([^\"]{15,}?)\"")


MATCH = 0.8      # share of a piece's words/numbers that must appear in one chunk


def _tokens(text: str) -> set[str]:
    """Lowercase words and numbers; "$12,267" -> "12267", "16.6" stays "16.6"."""
    return {t.replace(",", "").rstrip(".") for t in re.findall(r"[a-z]+|\d[\d,.]*", text.lower())}


def evidence_pieces(evidence: str) -> list[str]:
    """The quotable pieces of a golden evidence field (empty for unanswerable questions)."""
    quotes = [a or b for a, b in QUOTED.findall(evidence)] or [evidence]
    pieces = []
    for q in quotes:
        for part in re.split(r"\.\.\.|…", q):
            if len(part.split()) >= 4:
                pieces.append(part.strip())
    return pieces


def evidence_hit(evidence: str, chunk_texts: list[str]) -> float | None:
    """Share of evidence pieces found in the retrieved chunks; None if nothing to look for."""
    pieces = evidence_pieces(evidence)
    if not pieces:
        return None
    chunks = [_tokens(c) for c in chunk_texts]
    found = 0
    for piece in pieces:
        want = _tokens(piece)
        if any(len(want & c) >= MATCH * len(want) for c in chunks):
            found += 1
    return found / len(pieces)


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: uv run python evidence.py results/<run>.json")
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    golden_path = Path(data.get("golden", GOLDEN))       # the question set this run used
    golden = [json.loads(l) for l in golden_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = data["rows"]
    if "chunk_texts" not in rows[0]:
        sys.exit("This results file has no chunk text (runs before 15 Oct). Re-run eval.py to get one.")

    by_type = defaultdict(list)
    print(f"{'#':<4}{'type':<15}{'recall':>7}{'evidence':>10}  question")
    for r in rows:
        g = golden[r["n"] - 1]
        if not g["sources"]:                 # unanswerable: nothing to find
            continue
        hit = evidence_hit(g["evidence"], r["chunk_texts"])
        if hit is None:
            continue
        by_type[r["type"]].append((r["recall"], hit))
        flag = "  <- right section, wrong passage" if r["recall"] and r["recall"] > 0 and hit == 0 else ""
        print(f"{r['n']:<4}{r['type']:<15}{r['recall']:>7.2f}{hit:>10.2f}  {r['question'][:50]}{flag}")

    print(f"\n{'type':<15}{'n':>3}{'recall':>9}{'evidence':>10}")
    everything = [x for xs in by_type.values() for x in xs]
    for t, xs in list(by_type.items()) + [("ALL", everything)]:
        print(f"{t:<15}{len(xs):>3}{sum(a for a, _ in xs) / len(xs):>9.2f}{sum(b for _, b in xs) / len(xs):>10.2f}")


if __name__ == "__main__":
    main()

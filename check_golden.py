"""Check golden.jsonl before running any evaluation on it.

    uv run python check_golden.py

Checks format only: valid JSON, required fields, types, sources point at real
filings. It does NOT check whether your answers are correct - only you can do that.
"""

import json
from collections import Counter
from pathlib import Path

GOLDEN = Path("golden.jsonl")
TEXT = Path("data/text")
TYPES = {"fact", "cross-period", "cross-company", "narrative", "unanswerable"}
TARGET = {"fact": 3, "cross-period": 2, "cross-company": 2, "narrative": 3, "unanswerable": 2}
ITEMS = {"1", "1A", "1B", "1C", "2", "3", "4", "5", "6", "7", "7A", "8", "9", "9A", "9B", "9C",
         "10", "11", "12", "13", "14", "15", "16"}
FIELDS = {"question", "answer", "type", "sources"}
OPTIONAL = {"evidence"}   # exact quote from the filing, for spot-checking
REFUSAL = "Not in the filings."


def check(n: int, row: dict) -> list[str]:
    errs = []
    if not FIELDS <= set(row) <= FIELDS | OPTIONAL:
        return [f"fields should be {sorted(FIELDS)} (+ optional evidence), got {sorted(row)}"]
    if "TODO" in json.dumps(row):
        errs.append("still contains TODO")
    if row["type"] not in TYPES:
        errs.append(f"type '{row['type']}' is not one of {sorted(TYPES)}")
    sources = row["sources"]

    if row["type"] == "unanswerable":
        if row["answer"] != REFUSAL:
            errs.append(f"unanswerable answer must be exactly '{REFUSAL}'")
        if sources:
            errs.append("unanswerable should have sources: []")
        return errs

    if not sources:
        errs.append("needs at least one source")
    for s in sources:
        if set(s) != {"ticker", "period_end", "item"}:
            errs.append(f"source fields should be ticker, period_end, item: {s}")
            continue
        if "TODO" in json.dumps(s):
            continue
        if not (TEXT / s["ticker"] / f"{s['period_end']}.json").exists():
            errs.append(f"no filing {s['ticker']} {s['period_end']} (see data/text/{s['ticker']}/)")
        if s["item"] not in ITEMS:
            errs.append(f"item '{s['item']}' is not a 10-K Item (use e.g. '1A', '7')")
        if s["ticker"] == "INTC":
            errs.append("Intel is excluded for now (extraction broken)")

    if "TODO" in json.dumps(sources):
        return errs
    tickers = {s.get("ticker") for s in sources}
    periods = {s.get("period_end") for s in sources}
    if row["type"] == "cross-period" and (len(tickers) != 1 or len(periods) < 2):
        errs.append("cross-period = ONE company, TWO OR MORE periods")
    if row["type"] == "cross-company" and len(tickers) < 2:
        errs.append("cross-company = TWO OR MORE companies")
    return errs


def main():
    rows, problems = [], 0
    for n, line in enumerate(GOLDEN.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"line {n}: not valid JSON ({e})")
            problems += 1
            continue
        rows.append(row)
        for err in check(n, row):
            print(f"line {n}: {err}")
            problems += 1

    dupes = [q for q, c in Counter(r.get("question") for r in rows).items() if c > 1 and q != "TODO"]
    for q in dupes:
        print(f"duplicate question: {q}")
        problems += 1

    counts = Counter(r.get("type") for r in rows)
    print("\ntype            have  target")
    for t, want in TARGET.items():
        print(f"{t:<15} {counts[t]:>4}  {want:>6}")
    print(f"\n{len(rows)} questions, {problems} problem(s)")


if __name__ == "__main__":
    main()
